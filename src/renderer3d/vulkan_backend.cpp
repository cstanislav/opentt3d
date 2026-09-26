/* SPDX-License-Identifier: GPL-2.0-only */
/** @file vulkan_backend.cpp Persistent meshes, instancing, render targets and swapchain composition. */
#include "../stdafx.h"
#include "vulkan_backend.h"
#include "indexed_mesh.hpp"
#include <renderer3d_vulkan_shaders.hpp>
#include "sprite_textures.hpp"
#include "instance_batcher.hpp"
#include "voxel_volume.hpp"
#include "voxel_packed_mesh.hpp"
#include "voxel_visibility.hpp"
#include "voxel_visibility_worker.hpp"
#include "profiling.h"
#include "../gfx_func.h"
#include "../palette_func.h"
#include "../debug.h"
#include <map>
#include <memory>
#include <unordered_map>
#include <utility>
#ifdef __APPLE__
#include "../os/macosx/autorelease_pool.hpp"
#endif

namespace Renderer3D::Vulkan {
namespace {

void Check(VkResult result, const char *operation)
{
	if (result != VK_SUCCESS) throw std::runtime_error(fmt::format("{}: Vulkan result {}", operation, static_cast<int>(result)));
}

VKAPI_ATTR VkBool32 VKAPI_CALL ValidationMessage(VkDebugUtilsMessageSeverityFlagBitsEXT severity, VkDebugUtilsMessageTypeFlagsEXT, const VkDebugUtilsMessengerCallbackDataEXT *data, void *)
{
	Debug(driver, 0, "OpenTT3D: Vulkan validation {}: {}", (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) != 0 ? "error" : "warning", data->pMessage);
	return VK_FALSE;
}

struct Buffer {
	VkDevice device = VK_NULL_HANDLE;
	VkBuffer handle = VK_NULL_HANDLE;
	VkDeviceMemory memory = VK_NULL_HANDLE;
	void *mapped = nullptr;
	VkDeviceSize size = 0, used = 0;
	~Buffer()
	{
		if (mapped != nullptr) vkUnmapMemory(device, memory);
		if (handle != VK_NULL_HANDLE) vkDestroyBuffer(device, handle, nullptr);
		if (memory != VK_NULL_HANDLE) vkFreeMemory(device, memory, nullptr);
	}
};

struct Image {
	VkDevice device = VK_NULL_HANDLE;
	VkImage handle = VK_NULL_HANDLE;
	VkDeviceMemory memory = VK_NULL_HANDLE;
	VkImageView view = VK_NULL_HANDLE;
	VkFormat format = VK_FORMAT_UNDEFINED;
	VkImageLayout layout = VK_IMAGE_LAYOUT_UNDEFINED;
	uint32_t width = 0, height = 0, layers = 1;
	VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT;
	~Image()
	{
		if (view != VK_NULL_HANDLE) vkDestroyImageView(device, view, nullptr);
		if (handle != VK_NULL_HANDLE) vkDestroyImage(device, handle, nullptr);
		if (memory != VK_NULL_HANDLE) vkFreeMemory(device, memory, nullptr);
	}
};

struct Target {
	VkDevice device;
	std::unique_ptr<Image> colour, ids, depth;
	VkFramebuffer framebuffer = VK_NULL_HANDLE;
	VoxelVisibilityCache visibility;
	bool visibility_reported = false;
	std::unique_ptr<VoxelVisibilityWorker> visibility_worker;
	struct VisibleStream { std::unique_ptr<Buffer> buffer; std::vector<std::array<uint32_t,7>> transforms; size_t triangles = 0; };
	std::unordered_map<const std::vector<Vertex> *,VisibleStream> visible_streams;
	~Target() { if (framebuffer != VK_NULL_HANDLE) vkDestroyFramebuffer(device, framebuffer, nullptr); }
};

struct Frame {
	VkCommandPool commands = VK_NULL_HANDLE;
	VkCommandBuffer command = VK_NULL_HANDLE;
	VkDescriptorPool descriptors = VK_NULL_HANDLE;
	VkFence fence = VK_NULL_HANDLE;
	VkSemaphore acquired = VK_NULL_HANDLE;
	VkQueryPool timestamps = VK_NULL_HANDLE;
	bool timed = false;
	std::vector<std::unique_ptr<Buffer>> arena;
	std::vector<std::unique_ptr<Buffer>> retired_buffers;
};

struct Slice { VkBuffer buffer; VkDeviceSize offset; void *data; };
struct Region { Target *target; int sx, sy, width, height, dx, dy; };
struct SwapImage { VkImage image; VkImageView view; VkFramebuffer framebuffer; VkSemaphore complete; };
struct WorldPush {
	std::array<float, 16> projection;
	std::array<float, 4> camera, water;
	std::array<uint32_t, 4> mode{};
};
static_assert(sizeof(WorldPush) == 112);
struct CompositePush { std::array<float, 4> destination, source; std::array<uint32_t, 4> mode{}; };

class Context {
public:
	VkInstance instance = VK_NULL_HANDLE;
	VkDebugUtilsMessengerEXT messenger = VK_NULL_HANDLE;
	VkSurfaceKHR surface = VK_NULL_HANDLE;
	VkPhysicalDevice physical = VK_NULL_HANDLE;
	VkPhysicalDeviceProperties properties{};
	VkPhysicalDeviceMemoryProperties memory_properties{};
	VkDevice device = VK_NULL_HANDLE;
	VkQueue graphics = VK_NULL_HANDLE, presentation = VK_NULL_HANDLE;
	uint32_t graphics_family = 0, present_family = 0;
	uint32_t timestamp_bits = 0;
	VkSampler sampler = VK_NULL_HANDLE;
	VkDescriptorSetLayout world_layout = VK_NULL_HANDLE, composite_layout = VK_NULL_HANDLE;
	VkPipelineLayout world_pipeline_layout = VK_NULL_HANDLE, composite_pipeline_layout = VK_NULL_HANDLE;
	VkRenderPass world_pass = VK_NULL_HANDLE, screen_pass = VK_NULL_HANDLE;
	VkPipeline opaque_pipeline = VK_NULL_HANDLE, transparent_pipeline = VK_NULL_HANDLE, composite_pipeline = VK_NULL_HANDLE;
	VkPipeline opaque_palette_pipeline = VK_NULL_HANDLE, transparent_palette_pipeline = VK_NULL_HANDLE;
	VkPipeline voxel_pipeline = VK_NULL_HANDLE;
	VkPipeline voxel_slice_pipeline = VK_NULL_HANDLE;
	std::array<VkPipeline,8> packed_pipelines{};
	std::array<VkPipeline,2> visible_pipelines{};
	VkSwapchainKHR swapchain = VK_NULL_HANDLE;
	VkFormat screen_format = VK_FORMAT_UNDEFINED;
	VkExtent2D swap_extent{};
	std::vector<SwapImage> swap_images;
	std::array<Frame, 2> frames;
	unsigned frame_index = 0;
	VkFence readback_fence = VK_NULL_HANDLE;
	bool recording = false, swap_dirty = false;
	int width = 0, height = 0, pitch = 0;
	std::vector<Colour> video;
	std::vector<uint8_t> animation;
	std::unique_ptr<Image> atlas, remap, palette, ui, ui_animation;
	std::unordered_map<const void *, std::unique_ptr<Target>> targets;
	std::vector<std::unique_ptr<Target>> retired;
	std::unique_ptr<Target> readback_target;
	/* Immutable meshes share append-only pages. Existing slices are never moved
	 * or overwritten while either submitted frame can still reference them. */
	std::vector<std::unique_ptr<Buffer>> mesh_arena;
	struct MeshStorage { Slice storage; VkDeviceSize index_offset; uint32_t source_vertices, stored_vertices; bool indexed; VkIndexType index_type; };
	std::unordered_map<const std::vector<Vertex> *, MeshStorage> meshes;
	std::unordered_map<const VoxelVolume *,std::unique_ptr<Buffer>> volumes;
	std::unordered_map<const PackedVoxelMesh *,std::unique_ptr<Buffer>> packed_formats;
	struct VisibilityLookup { std::unique_ptr<Buffer> buffer; std::vector<uint32_t> indices; unsigned bits; };
	std::unordered_map<const PackedVoxelMesh *,VisibilityLookup> visibility_lookups;
	std::unique_ptr<Buffer> empty_volume;
	/* Retain an explicit diagnostic control for like-for-like allocation tests. */
	bool pool_meshes = [] {
		const char *setting = std::getenv("OPENTT3D_MESH_POOL");
		return setting == nullptr || std::string_view(setting) != "0";
	}();
	InstanceBatcher instance_staging;
	struct Batch { VkBuffer mesh; VkDeviceSize offset, index_offset; uint32_t vertices, first, count; bool transparent, indexed, cull_back, both_passes; VkIndexType index_type; VkDescriptorBufferInfo volume{}; uint32_t volume_mode = 0, packed_mode = 0; bool visible = false; VkDescriptorBufferInfo triangles{}, lookup{}; };
	std::vector<Batch> instance_batches;
	struct VisibleSpan { std::span<const uint64_t> triangles; uint32_t instance; };
	std::vector<VisibleSpan> visible_spans;
	std::vector<Region> regions;
	bool screen_transfer = false;
	PresentationCapture capture;

	~Context() { Shutdown(); }
	Frame &Current() { return frames[frame_index]; }
	VkCommandBuffer Command() { return Current().command; }

	uint32_t MemoryType(uint32_t bits, VkMemoryPropertyFlags wanted)
	{
		for (uint32_t i = 0; i < memory_properties.memoryTypeCount; ++i) {
			if ((bits & (1U << i)) != 0 && (memory_properties.memoryTypes[i].propertyFlags & wanted) == wanted) return i;
		}
		throw std::runtime_error("Vulkan memory type is unavailable");
	}

	std::unique_ptr<Buffer> MakeBuffer(VkDeviceSize size, VkBufferUsageFlags usage)
	{
		auto buffer = std::make_unique<Buffer>();
		buffer->device = device; buffer->size = std::max<VkDeviceSize>(size, 16);
		VkBufferCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
		create.size = buffer->size; create.usage = usage; create.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
		Check(vkCreateBuffer(device, &create, nullptr, &buffer->handle), "create buffer");
		VkMemoryRequirements requirements;
		vkGetBufferMemoryRequirements(device, buffer->handle, &requirements);
		VkMemoryAllocateInfo allocation{}; allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
		allocation.allocationSize = requirements.size;
		allocation.memoryTypeIndex = MemoryType(requirements.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
		Check(vkAllocateMemory(device, &allocation, nullptr, &buffer->memory), "allocate buffer");
		Check(vkBindBufferMemory(device, buffer->handle, buffer->memory, 0), "bind buffer");
		Check(vkMapMemory(device, buffer->memory, 0, VK_WHOLE_SIZE, 0, &buffer->mapped), "map buffer");
		return buffer;
	}

	Slice AllocateIn(std::vector<std::unique_ptr<Buffer>> &arena, VkDeviceSize bytes, VkDeviceSize alignment = 16)
	{
		bytes = std::max<VkDeviceSize>(bytes, 16);
		for (auto &buffer : arena) {
			VkDeviceSize offset = (buffer->used + alignment - 1) / alignment * alignment;
			if (offset + bytes > buffer->size) continue;
			buffer->used = offset + bytes;
			return {buffer->handle, offset, static_cast<std::byte *>(buffer->mapped) + offset};
		}
		VkDeviceSize capacity = std::max<VkDeviceSize>(4 * 1024 * 1024, (bytes + 4095) / 4096 * 4096);
		arena.push_back(MakeBuffer(capacity, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_INDEX_BUFFER_BIT | VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT));
		auto &buffer = arena.back();
		buffer->used = bytes;
		return {buffer->handle, 0, buffer->mapped};
	}

	Slice Allocate(VkDeviceSize bytes, VkDeviceSize alignment = 16) { return AllocateIn(Current().arena, bytes, alignment); }

	MeshCacheStats MeshUsage() const
	{
		MeshCacheStats stats{meshes.size(), mesh_arena.size()};
		stats.pooled = pool_meshes;
		for (const auto &buffer : mesh_arena) {
			stats.used_bytes += buffer->used;
			stats.capacity_bytes += buffer->size;
		}
		for (const auto &[key,mesh] : meshes) {
			stats.source_vertices += mesh.source_vertices; stats.stored_vertices += mesh.stored_vertices;
			if (mesh.indexed) { ++stats.indexed_meshes; stats.index_bytes += mesh.source_vertices*(mesh.index_type == VK_INDEX_TYPE_UINT16 ? sizeof(uint16_t) : sizeof(uint32_t)); }
		}
		return stats;
	}

	std::unique_ptr<Image> MakeImage(uint32_t w, uint32_t h, VkFormat format, VkImageUsageFlags usage, uint32_t layers = 1, VkImageAspectFlags aspect = VK_IMAGE_ASPECT_COLOR_BIT)
	{
		auto image = std::make_unique<Image>();
		image->device = device; image->width = w; image->height = h; image->format = format; image->layers = layers; image->aspect = aspect;
		VkImageCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
		create.imageType = VK_IMAGE_TYPE_2D; create.format = format; create.extent = {w, h, 1};
		create.mipLevels = 1; create.arrayLayers = layers; create.samples = VK_SAMPLE_COUNT_1_BIT;
		create.tiling = VK_IMAGE_TILING_OPTIMAL; create.usage = usage; create.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
		Check(vkCreateImage(device, &create, nullptr, &image->handle), "create image");
		VkMemoryRequirements requirements;
		vkGetImageMemoryRequirements(device, image->handle, &requirements);
		VkMemoryAllocateInfo allocation{}; allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
		allocation.allocationSize = requirements.size;
		allocation.memoryTypeIndex = MemoryType(requirements.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
		Check(vkAllocateMemory(device, &allocation, nullptr, &image->memory), "allocate image");
		Check(vkBindImageMemory(device, image->handle, image->memory, 0), "bind image");
		VkImageViewCreateInfo view{}; view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
		view.image = image->handle; view.viewType = layers > 1 ? VK_IMAGE_VIEW_TYPE_2D_ARRAY : VK_IMAGE_VIEW_TYPE_2D;
		view.format = format; view.subresourceRange = {aspect, 0, 1, 0, layers};
		Check(vkCreateImageView(device, &view, nullptr, &image->view), "create image view");
		return image;
	}

	void Transition(Image &image, VkImageLayout layout)
	{
		if (image.layout == layout) return;
		VkImageMemoryBarrier barrier{}; barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
		barrier.oldLayout = image.layout; barrier.newLayout = layout;
		barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
		barrier.image = image.handle; barrier.subresourceRange = {image.aspect, 0, 1, 0, image.layers};
		VkPipelineStageFlags source = VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, destination = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
		if (image.layout == VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL) { source = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT; barrier.srcAccessMask = VK_ACCESS_SHADER_READ_BIT; }
		if (image.layout == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL) { source = VK_PIPELINE_STAGE_TRANSFER_BIT; barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT; }
		if (image.layout == VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL) { source = VK_PIPELINE_STAGE_TRANSFER_BIT; barrier.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT; }
		if (layout == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL) { destination = VK_PIPELINE_STAGE_TRANSFER_BIT; barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT; }
		else if (layout == VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL) { destination = VK_PIPELINE_STAGE_TRANSFER_BIT; barrier.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT; }
		else barrier.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
		vkCmdPipelineBarrier(Command(), source, destination, 0, 0, nullptr, 0, nullptr, 1, &barrier);
		image.layout = layout;
	}

	void Upload(Image &image, const void *data, uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t channels, uint32_t row_pixels, uint32_t layer = 0)
	{
		Slice staging = Allocate(static_cast<VkDeviceSize>(w) * h * channels, 4);
		for (uint32_t row = 0; row < h; ++row) {
			std::memcpy(static_cast<std::byte *>(staging.data) + static_cast<size_t>(row) * w * channels,
				static_cast<const std::byte *>(data) + static_cast<size_t>(row) * row_pixels * channels, static_cast<size_t>(w) * channels);
		}
		Transition(image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
		VkBufferImageCopy copy{};
		copy.bufferOffset = staging.offset; copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, layer, 1};
		copy.imageOffset = {static_cast<int32_t>(x), static_cast<int32_t>(y), 0}; copy.imageExtent = {w, h, 1};
		vkCmdCopyBufferToImage(Command(), staging.buffer, image.handle, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
		Transition(image, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
	}

	void Begin()
	{
		if (recording) return;
		Frame &frame = Current();
		Check(vkWaitForFences(device, 1, &frame.fence, VK_TRUE, UINT64_MAX), "wait frame");
		frame.retired_buffers.clear();
		if (frame.timed) {
			uint64_t ticks[2]{};
			Check(vkGetQueryPoolResults(device, frame.timestamps, 0, 2, sizeof(ticks), ticks, sizeof(uint64_t), VK_QUERY_RESULT_64_BIT), "read GPU timestamps");
			uint64_t mask = timestamp_bits == 64 ? UINT64_MAX : (uint64_t{1} << timestamp_bits) - 1;
			Profile::AddGPUTime(((ticks[1] - ticks[0]) & mask) * properties.limits.timestampPeriod / 1000000.0);
			frame.timed = false;
		}
		if (!retired.empty()) { Check(vkDeviceWaitIdle(device), "retire viewports"); retired.clear(); }
		Check(vkResetCommandPool(device, frame.commands, 0), "reset commands");
		Check(vkResetDescriptorPool(device, frame.descriptors, 0), "reset descriptors");
		for (auto &buffer : frame.arena) buffer->used = 0;
		regions.clear();
		VkCommandBufferBeginInfo begin{}; begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
		begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
		Check(vkBeginCommandBuffer(frame.command, &begin), "begin frame");
		if (frame.timestamps != VK_NULL_HANDLE) {
			vkCmdResetQueryPool(frame.command, frame.timestamps, 0, 2);
			vkCmdWriteTimestamp(frame.command, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, frame.timestamps, 0);
		}
		recording = true;
	}

	/** Readback/tooling only. Interactive frames never wait for a full image copy. */
	void Flush()
	{
		if (!recording) return;
		Check(vkEndCommandBuffer(Command()), "end readback commands");
		Check(vkResetFences(device, 1, &readback_fence), "reset readback fence");
		VkSubmitInfo submit{}; submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
		submit.commandBufferCount = 1; submit.pCommandBuffers = &Current().command;
		Check(vkQueueSubmit(graphics, 1, &submit, readback_fence), "submit readback");
		Check(vkWaitForFences(device, 1, &readback_fence, VK_TRUE, UINT64_MAX), "wait readback");
		Current().retired_buffers.clear();
		Check(vkResetCommandPool(device, Current().commands, 0), "reset readback commands");
		Check(vkResetDescriptorPool(device, Current().descriptors, 0), "reset readback descriptors");
		for (auto &buffer : Current().arena) buffer->used = 0;
		VkCommandBufferBeginInfo begin{}; begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
		begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
		Check(vkBeginCommandBuffer(Command(), &begin), "resume frame");
	}

	VkDescriptorSet Descriptor(VkDescriptorSetLayout layout, std::span<Image *const> images, const VkDescriptorBufferInfo *storage = nullptr, const VkDescriptorBufferInfo *volume = nullptr, const VkDescriptorBufferInfo *triangles = nullptr, const VkDescriptorBufferInfo *lookup = nullptr)
	{
		VkDescriptorSetAllocateInfo allocate{}; allocate.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
		allocate.descriptorPool = Current().descriptors; allocate.descriptorSetCount = 1; allocate.pSetLayouts = &layout;
		VkDescriptorSet result;
		Check(vkAllocateDescriptorSets(device, &allocate, &result), "allocate descriptor set");
		std::array<VkDescriptorImageInfo, 3> image_info{};
		std::array<VkWriteDescriptorSet, 7> writes{};
		for (size_t i = 0; i < images.size(); ++i) {
			image_info[i] = {sampler, images[i]->view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
			writes[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
			writes[i].dstSet = result; writes[i].dstBinding = static_cast<uint32_t>(i);
			writes[i].descriptorCount = 1; writes[i].descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
			writes[i].pImageInfo = &image_info[i];
		}
		if (storage != nullptr) {
			writes[3].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
			writes[3].dstSet = result; writes[3].dstBinding = 3; writes[3].descriptorCount = 1;
			writes[3].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; writes[3].pBufferInfo = storage;
		}
		VkDescriptorBufferInfo empty{empty_volume ? empty_volume->handle : VK_NULL_HANDLE,0,16};
		if (storage != nullptr) {
			const VkDescriptorBufferInfo *resources[] = {volume,triangles,lookup};
			for (unsigned i = 0; i < 3; ++i) {
				auto &write = writes[4+i];
				write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
				write.dstSet = result; write.dstBinding = 4+i; write.descriptorCount = 1;
				write.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; write.pBufferInfo = resources[i] != nullptr ? resources[i] : &empty;
			}
		}
		vkUpdateDescriptorSets(device, storage != nullptr ? 7 : static_cast<uint32_t>(images.size()), writes.data(), 0, nullptr);
		return result;
	}

	VkShaderModule Shader(std::span<const uint32_t> code)
	{
		VkShaderModuleCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
		create.codeSize = code.size_bytes(); create.pCode = code.data();
		VkShaderModule module;
		Check(vkCreateShaderModule(device, &create, nullptr, &module), "create shader module");
		return module;
	}

	VkPipeline Pipeline(VkRenderPass pass, VkPipelineLayout layout, bool world, bool transparent, bool cull_back = false, unsigned volume = 0, unsigned packed = 0, bool visible = false)
	{
		VkShaderModule vertex = Shader(world ? (visible ? (packed == 2 ? std::span<const uint32_t>(Shaders::vk_world_visible_fast_vert) : std::span<const uint32_t>(Shaders::vk_world_visible_vert)) : packed == 2 ? std::span<const uint32_t>(Shaders::vk_world_packed_fast_vert) : packed ? std::span<const uint32_t>(Shaders::vk_world_packed_vert) : std::span<const uint32_t>(Shaders::vk_world_vert)) : std::span<const uint32_t>(Shaders::vk_composite_vert));
		VkShaderModule fragment = Shader(world ? (volume == 2 ? std::span<const uint32_t>(Shaders::vk_voxel_slice_frag) : volume ? std::span<const uint32_t>(Shaders::vk_voxel_frag) : std::span<const uint32_t>(Shaders::vk_world_frag)) : std::span<const uint32_t>(Shaders::vk_composite_frag));
		VkPipelineShaderStageCreateInfo stages[2]{};
		stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
		stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT; stages[0].module = vertex; stages[0].pName = "main";
		stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
		stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT; stages[1].module = fragment; stages[1].pName = "main";
		VkVertexInputBindingDescription binding{0, static_cast<uint32_t>(packed ? sizeof(uint32_t) : sizeof(Vertex)), VK_VERTEX_INPUT_RATE_VERTEX};
		const VkVertexInputAttributeDescription packed_attributes[] = {{0,0,VK_FORMAT_R32_UINT,0}};
		const VkVertexInputAttributeDescription attributes[] = {
			{0, 0, VK_FORMAT_R32G32B32_SFLOAT, offsetof(Vertex, position)}, {1, 0, VK_FORMAT_R32G32B32_SFLOAT, offsetof(Vertex, normal)},
			{2, 0, VK_FORMAT_R32G32B32_SFLOAT, offsetof(Vertex, colour)}, {3, 0, VK_FORMAT_R32G32B32_SFLOAT, offsetof(Vertex, texture)},
			{4, 0, VK_FORMAT_R32_SFLOAT, offsetof(Vertex, opacity)}, {5, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertex, texture_region)},
			{6, 0, VK_FORMAT_R32_UINT, offsetof(Vertex, surface)}, {7, 0, VK_FORMAT_R32_UINT, offsetof(Vertex, object_id)},
		};
		VkPipelineVertexInputStateCreateInfo input{}; input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
		if (world && !visible) { input.vertexBindingDescriptionCount = 1; input.pVertexBindingDescriptions = &binding; input.vertexAttributeDescriptionCount = packed ? 1 : std::size(attributes); input.pVertexAttributeDescriptions = packed ? packed_attributes : attributes; }
		VkPipelineInputAssemblyStateCreateInfo assembly{}; assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
		assembly.topology = world ? VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST : VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP;
		assembly.primitiveRestartEnable = !world; // Metal strips always enable restart; this pass has no indices.
		VkPipelineViewportStateCreateInfo viewport{}; viewport.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
		viewport.viewportCount = viewport.scissorCount = 1;
		VkPipelineRasterizationStateCreateInfo raster{}; raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
		raster.polygonMode = VK_POLYGON_MODE_FILL; raster.cullMode = cull_back ? VK_CULL_MODE_BACK_BIT : VK_CULL_MODE_NONE; raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE; raster.lineWidth = 1;
		VkPipelineMultisampleStateCreateInfo multisample{}; multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
		multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
		VkPipelineDepthStencilStateCreateInfo depth{}; depth.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
		depth.depthTestEnable = world; depth.depthWriteEnable = world && !transparent; depth.depthCompareOp = VK_COMPARE_OP_GREATER_OR_EQUAL;
		VkPipelineColorBlendAttachmentState blending[2]{};
		blending[0].colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
		blending[0].blendEnable = transparent || !world;
		blending[0].srcColorBlendFactor = world ? VK_BLEND_FACTOR_SRC_ALPHA : VK_BLEND_FACTOR_ONE;
		blending[0].dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
		blending[0].colorBlendOp = VK_BLEND_OP_ADD; blending[0].alphaBlendOp = VK_BLEND_OP_ADD;
		blending[0].srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE; blending[0].dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
		blending[1].blendEnable = VK_FALSE; // Integer picking attachments never blend.
		blending[1].colorWriteMask = transparent ? 0 : VK_COLOR_COMPONENT_R_BIT;
		VkPipelineColorBlendStateCreateInfo blend{}; blend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
		blend.attachmentCount = world ? 2 : 1; blend.pAttachments = blending;
		const VkDynamicState dynamic_states[] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
		VkPipelineDynamicStateCreateInfo dynamic{}; dynamic.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
		dynamic.dynamicStateCount = 2; dynamic.pDynamicStates = dynamic_states;
		VkGraphicsPipelineCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
		create.stageCount = 2; create.pStages = stages; create.pVertexInputState = &input; create.pInputAssemblyState = &assembly;
		create.pViewportState = &viewport; create.pRasterizationState = &raster; create.pMultisampleState = &multisample;
		create.pDepthStencilState = &depth; create.pColorBlendState = &blend; create.pDynamicState = &dynamic;
		create.layout = layout; create.renderPass = pass;
		VkPipeline result = VK_NULL_HANDLE;
		VkResult status = vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &create, nullptr, &result);
		vkDestroyShaderModule(device, vertex, nullptr); vkDestroyShaderModule(device, fragment, nullptr);
		Check(status, "create graphics pipeline");
		return result;
	}

	void CreateWorldPass()
	{
		VkAttachmentDescription attachments[3]{};
		for (auto &attachment : attachments) {
			attachment.samples = VK_SAMPLE_COUNT_1_BIT; attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR; attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
			attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE; attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
			attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
		}
		attachments[0].format = VK_FORMAT_R8G8B8A8_UNORM; attachments[0].finalLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
		attachments[1].format = VK_FORMAT_R32_UINT; attachments[1].finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
		attachments[2].format = VK_FORMAT_D32_SFLOAT; attachments[2].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
		VkAttachmentReference colours[] = {{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL}, {1, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL}};
		VkAttachmentReference depth{2, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
		VkSubpassDescription subpass{};
		subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS; subpass.colorAttachmentCount = 2; subpass.pColorAttachments = colours; subpass.pDepthStencilAttachment = &depth;
		VkSubpassDependency dependencies[2]{};
		dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL; dependencies[0].dstSubpass = 0;
		dependencies[0].srcStageMask = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_LATE_FRAGMENT_TESTS_BIT;
		dependencies[0].srcAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT | VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
		dependencies[0].dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
		dependencies[0].dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT | VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
		dependencies[1].srcSubpass = 0; dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
		dependencies[1].srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
		dependencies[1].srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
		dependencies[1].dstStageMask = VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_TRANSFER_BIT;
		dependencies[1].dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_TRANSFER_READ_BIT;
		VkRenderPassCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
		create.attachmentCount = 3; create.pAttachments = attachments; create.subpassCount = 1; create.pSubpasses = &subpass;
		create.dependencyCount = 2; create.pDependencies = dependencies;
		Check(vkCreateRenderPass(device, &create, nullptr, &world_pass), "create world pass");
	}

	std::unique_ptr<Target> MakeTarget(uint32_t w, uint32_t h)
	{
		auto target = std::make_unique<Target>(); target->device = device;
		target->colour = MakeImage(w, h, VK_FORMAT_R8G8B8A8_UNORM, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
		target->ids = MakeImage(w, h, VK_FORMAT_R32_UINT, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
		target->depth = MakeImage(w, h, VK_FORMAT_D32_SFLOAT, VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT, 1, VK_IMAGE_ASPECT_DEPTH_BIT);
		VkImageView views[] = {target->colour->view, target->ids->view, target->depth->view};
		VkFramebufferCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
		create.renderPass = world_pass; create.attachmentCount = 3; create.pAttachments = views; create.width = w; create.height = h; create.layers = 1;
		Check(vkCreateFramebuffer(device, &create, nullptr, &target->framebuffer), "create world framebuffer");
		return target;
	}

	void ConfigureDevice()
	{
		uint32_t count = 0;
		Check(vkEnumeratePhysicalDevices(instance, &count, nullptr), "enumerate devices");
		std::vector<VkPhysicalDevice> devices(count);
		Check(vkEnumeratePhysicalDevices(instance, &count, devices.data()), "enumerate devices");
		for (auto candidate : devices) {
			uint32_t family_count = 0;
			vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, nullptr);
			std::vector<VkQueueFamilyProperties> families(family_count);
			vkGetPhysicalDeviceQueueFamilyProperties(candidate, &family_count, families.data());
			std::optional<uint32_t> draw, present;
			for (uint32_t i = 0; i < family_count; ++i) {
				VkBool32 supported = VK_FALSE;
				Check(vkGetPhysicalDeviceSurfaceSupportKHR(candidate, i, surface, &supported), "query presentation support");
				if ((families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0) draw = i;
				if (supported) present = i;
				if (draw && present && *draw == *present) break;
			}
			if (draw && present) { physical = candidate; graphics_family = *draw; present_family = *present; timestamp_bits = families[*draw].timestampValidBits; break; }
		}
		if (physical == VK_NULL_HANDLE) throw std::runtime_error("No Vulkan graphics/presentation device");
		vkGetPhysicalDeviceProperties(physical, &properties);
		vkGetPhysicalDeviceMemoryProperties(physical, &memory_properties);
		std::vector<const char *> extensions{VK_KHR_SWAPCHAIN_EXTENSION_NAME};
		uint32_t extension_count = 0;
		Check(vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, nullptr), "query device extensions");
		std::vector<VkExtensionProperties> available(extension_count);
		Check(vkEnumerateDeviceExtensionProperties(physical, nullptr, &extension_count, available.data()), "query device extensions");
		for (const auto &extension : available) if (std::strcmp(extension.extensionName, "VK_KHR_portability_subset") == 0) extensions.push_back("VK_KHR_portability_subset");
		float priority = 1;
		VkDeviceQueueCreateInfo queues[2]{};
		for (auto &queue : queues) { queue.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO; queue.queueCount = 1; queue.pQueuePriorities = &priority; }
		queues[0].queueFamilyIndex = graphics_family; queues[1].queueFamilyIndex = present_family;
		VkPhysicalDeviceFeatures supported;
		vkGetPhysicalDeviceFeatures(physical, &supported);
		if (!supported.independentBlend) throw std::runtime_error("Vulkan independent attachment blending is required");
		VkPhysicalDeviceFeatures features{}; features.independentBlend = VK_TRUE;
		VkDeviceCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
		create.queueCreateInfoCount = graphics_family == present_family ? 1 : 2; create.pQueueCreateInfos = queues;
		create.enabledExtensionCount = static_cast<uint32_t>(extensions.size()); create.ppEnabledExtensionNames = extensions.data(); create.pEnabledFeatures = &features;
		Check(vkCreateDevice(physical, &create, nullptr, &device), "create device");
		vkGetDeviceQueue(device, graphics_family, 0, &graphics); vkGetDeviceQueue(device, present_family, 0, &presentation);
		for (auto &frame : frames) {
			if (timestamp_bits != 0) {
				VkQueryPoolCreateInfo query{}; query.sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO;
				query.queryType = VK_QUERY_TYPE_TIMESTAMP; query.queryCount = 2;
				Check(vkCreateQueryPool(device, &query, nullptr, &frame.timestamps), "create timestamp query pool");
			}
			VkCommandPoolCreateInfo pool{}; pool.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
			pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT; pool.queueFamilyIndex = graphics_family;
			Check(vkCreateCommandPool(device, &pool, nullptr, &frame.commands), "create command pool");
			VkCommandBufferAllocateInfo command{}; command.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
			command.commandPool = frame.commands; command.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; command.commandBufferCount = 1;
			Check(vkAllocateCommandBuffers(device, &command, &frame.command), "allocate command buffer");
			VkDescriptorPoolSize sizes[] = {{VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, 4096 * 3}, {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4096 * 4}};
			VkDescriptorPoolCreateInfo descriptors{}; descriptors.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
			descriptors.maxSets = 4096; descriptors.poolSizeCount = 2; descriptors.pPoolSizes = sizes;
			Check(vkCreateDescriptorPool(device, &descriptors, nullptr, &frame.descriptors), "create descriptor pool");
			VkFenceCreateInfo fence{}; fence.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO; fence.flags = VK_FENCE_CREATE_SIGNALED_BIT;
			Check(vkCreateFence(device, &fence, nullptr, &frame.fence), "create frame fence");
			VkSemaphoreCreateInfo semaphore{}; semaphore.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
			Check(vkCreateSemaphore(device, &semaphore, nullptr, &frame.acquired), "create acquire semaphore");
		}
		VkFenceCreateInfo fence{}; fence.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
		Check(vkCreateFence(device, &fence, nullptr, &readback_fence), "create readback fence");
		VkSamplerCreateInfo sampling{}; sampling.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
		sampling.magFilter = sampling.minFilter = VK_FILTER_NEAREST; sampling.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
		sampling.addressModeU = sampling.addressModeV = sampling.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE; sampling.maxLod = 0;
		Check(vkCreateSampler(device, &sampling, nullptr, &sampler), "create sampler");
		VkDescriptorSetLayoutBinding bindings[7]{};
		for (uint32_t i = 0; i < 7; ++i) {
			bindings[i].binding = i; bindings[i].descriptorCount = 1;
			bindings[i].descriptorType = i >= 3 ? VK_DESCRIPTOR_TYPE_STORAGE_BUFFER : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
			bindings[i].stageFlags = i >= 5 ? VK_SHADER_STAGE_VERTEX_BIT : i >= 3 ? VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT : VK_SHADER_STAGE_FRAGMENT_BIT;
		}
		VkDescriptorSetLayoutCreateInfo layout{}; layout.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
		layout.bindingCount = 7; layout.pBindings = bindings;
		Check(vkCreateDescriptorSetLayout(device, &layout, nullptr, &world_layout), "create world descriptor layout");
		layout.bindingCount = 3;
		Check(vkCreateDescriptorSetLayout(device, &layout, nullptr, &composite_layout), "create composition descriptor layout");
		VkPushConstantRange constants{VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(WorldPush)};
		VkPipelineLayoutCreateInfo pipeline_layout{}; pipeline_layout.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
		pipeline_layout.setLayoutCount = 1; pipeline_layout.pSetLayouts = &world_layout; pipeline_layout.pushConstantRangeCount = 1; pipeline_layout.pPushConstantRanges = &constants;
		Check(vkCreatePipelineLayout(device, &pipeline_layout, nullptr, &world_pipeline_layout), "create world pipeline layout");
		constants.size = sizeof(CompositePush); pipeline_layout.pSetLayouts = &composite_layout;
		Check(vkCreatePipelineLayout(device, &pipeline_layout, nullptr, &composite_pipeline_layout), "create composition pipeline layout");
		CreateWorldPass();
		opaque_pipeline = Pipeline(world_pass, world_pipeline_layout, true, false);
		transparent_pipeline = Pipeline(world_pass, world_pipeline_layout, true, true);
		opaque_palette_pipeline = Pipeline(world_pass,world_pipeline_layout,true,false,true);
		transparent_palette_pipeline = Pipeline(world_pass,world_pipeline_layout,true,true,true);
		if (VoxelVolumesEnabled()) {
			if (VoxelSlicesEnabled()) voxel_slice_pipeline = Pipeline(world_pass,world_pipeline_layout,true,false,true,2);
			else voxel_pipeline = Pipeline(world_pass,world_pipeline_layout,true,false,true,1);
		}
		if (PackedVoxelMeshesEnabled()) for (unsigned i = 0; i < packed_pipelines.size(); ++i) packed_pipelines[i] = Pipeline(world_pass,world_pipeline_layout,true,(i&1U) != 0,(i&2U) != 0,0,i >= 4 ? 2 : 1);
		if (VoxelPixelCullEnabled()) for (unsigned i = 0; i < visible_pipelines.size(); ++i) visible_pipelines[i] = Pipeline(world_pass,world_pipeline_layout,true,false,true,0,i+1,true);
		if (VoxelVolumesEnabled()) Debug(driver,1,"OpenTT3D: experimental full-cell voxel volumes, Vulkan subpixel precision {} bits",properties.limits.subPixelPrecisionBits);
		empty_volume = MakeBuffer(16,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
		std::memset(empty_volume->mapped,0,16);
		atlas = MakeImage(ATLAS_SIZE, ATLAS_SIZE, VK_FORMAT_R8G8B8A8_UNORM, VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT, ATLAS_PAGES);
		remap = MakeImage(ATLAS_SIZE, ATLAS_SIZE, VK_FORMAT_R8G8_UNORM, VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT, ATLAS_PAGES);
		palette = MakeImage(256, 1, VK_FORMAT_B8G8R8A8_UNORM, VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
		Begin();
		Transition(*atlas, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
		Transition(*remap, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
		auto palette_snapshot = SnapshotPalette();
		Upload(*palette, palette_snapshot.palette, 0, 0, 256, 1, 4, 256);
		Flush();
		Textures().MarkAllDirty();
		Debug(driver, 1, "OpenTT3D: Vulkan instanced renderer initialized on {}", properties.deviceName);
	}

	void DestroySwapchain()
	{
		for (const auto &image : swap_images) {
			vkDestroyFramebuffer(device, image.framebuffer, nullptr); vkDestroyImageView(device, image.view, nullptr); vkDestroySemaphore(device, image.complete, nullptr);
		}
		swap_images.clear();
		if (swapchain != VK_NULL_HANDLE) vkDestroySwapchainKHR(device, swapchain, nullptr);
		swapchain = VK_NULL_HANDLE;
	}

	void MakeSwapchain()
	{
		if (recording) Flush();
		Check(vkDeviceWaitIdle(device), "resize swapchain");
		DestroySwapchain();
		VkSurfaceCapabilitiesKHR capabilities;
		Check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical, surface, &capabilities), "surface capabilities");
		screen_transfer = (capabilities.supportedUsageFlags & VK_IMAGE_USAGE_TRANSFER_SRC_BIT) != 0;
		uint32_t count = 0;
		Check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical, surface, &count, nullptr), "surface formats");
		std::vector<VkSurfaceFormatKHR> formats(count);
		Check(vkGetPhysicalDeviceSurfaceFormatsKHR(physical, surface, &count, formats.data()), "surface formats");
		if (formats.empty()) throw std::runtime_error("Vulkan surface has no colour format");
		auto chosen = formats.front();
		for (auto format : formats) if (format.format == VK_FORMAT_B8G8R8A8_UNORM || format.format == VK_FORMAT_R8G8B8A8_UNORM) { chosen = format; break; }
		if (chosen.format == VK_FORMAT_UNDEFINED) chosen.format = VK_FORMAT_B8G8R8A8_UNORM;
		if (chosen.format != VK_FORMAT_B8G8R8A8_UNORM && chosen.format != VK_FORMAT_R8G8B8A8_UNORM) throw std::runtime_error("Vulkan surface requires an unorm format for exact UI colours");
		if (screen_format != chosen.format) {
			if (composite_pipeline) vkDestroyPipeline(device, composite_pipeline, nullptr);
			if (screen_pass) vkDestroyRenderPass(device, screen_pass, nullptr);
			screen_format = chosen.format;
			VkAttachmentDescription attachment{};
			attachment.format = screen_format; attachment.samples = VK_SAMPLE_COUNT_1_BIT; attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
			attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE; attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
			attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE; attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED; attachment.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
			VkAttachmentReference colour{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
			VkSubpassDescription subpass{}; subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS; subpass.colorAttachmentCount = 1; subpass.pColorAttachments = &colour;
			VkSubpassDependency dependency{}; dependency.srcSubpass = VK_SUBPASS_EXTERNAL; dependency.dstSubpass = 0;
			dependency.srcStageMask = dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT; dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
			VkRenderPassCreateInfo pass{}; pass.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
			pass.attachmentCount = 1; pass.pAttachments = &attachment; pass.subpassCount = 1; pass.pSubpasses = &subpass; pass.dependencyCount = 1; pass.pDependencies = &dependency;
			Check(vkCreateRenderPass(device, &pass, nullptr, &screen_pass), "create screen pass");
			composite_pipeline = Pipeline(screen_pass, composite_pipeline_layout, false, true);
		}
		swap_extent = capabilities.currentExtent;
		if (swap_extent.width == UINT32_MAX) swap_extent = {std::clamp(static_cast<uint32_t>(width), capabilities.minImageExtent.width, capabilities.maxImageExtent.width), std::clamp(static_cast<uint32_t>(height), capabilities.minImageExtent.height, capabilities.maxImageExtent.height)};
		if (swap_extent.width == 0 || swap_extent.height == 0) { swap_dirty = true; return; }
		uint32_t image_count = capabilities.minImageCount + 1;
		if (capabilities.maxImageCount != 0) image_count = std::min(image_count, capabilities.maxImageCount);
		uint32_t families[] = {graphics_family, present_family};
		VkSwapchainCreateInfoKHR create{}; create.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
		create.surface = surface; create.minImageCount = image_count; create.imageFormat = screen_format; create.imageColorSpace = chosen.colorSpace;
		create.imageExtent = swap_extent; create.imageArrayLayers = 1; create.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
		if (screen_transfer) create.imageUsage |= VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
		create.imageSharingMode = graphics_family == present_family ? VK_SHARING_MODE_EXCLUSIVE : VK_SHARING_MODE_CONCURRENT;
		if (graphics_family != present_family) { create.queueFamilyIndexCount = 2; create.pQueueFamilyIndices = families; }
		create.preTransform = capabilities.currentTransform;
		create.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
		for (auto alpha : {VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR, VK_COMPOSITE_ALPHA_INHERIT_BIT_KHR, VK_COMPOSITE_ALPHA_PRE_MULTIPLIED_BIT_KHR, VK_COMPOSITE_ALPHA_POST_MULTIPLIED_BIT_KHR}) {
			if ((capabilities.supportedCompositeAlpha & alpha) != 0) { create.compositeAlpha = alpha; break; }
		}
		create.presentMode = VK_PRESENT_MODE_FIFO_KHR; create.clipped = VK_TRUE;
		Check(vkCreateSwapchainKHR(device, &create, nullptr, &swapchain), "create swapchain");
		Check(vkGetSwapchainImagesKHR(device, swapchain, &count, nullptr), "query swapchain images");
		std::vector<VkImage> images(count);
		Check(vkGetSwapchainImagesKHR(device, swapchain, &count, images.data()), "query swapchain images");
		for (VkImage image : images) {
			SwapImage slot{};
			slot.image = image;
			VkImageViewCreateInfo view{}; view.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
			view.image = image; view.viewType = VK_IMAGE_VIEW_TYPE_2D; view.format = screen_format; view.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
			Check(vkCreateImageView(device, &view, nullptr, &slot.view), "create swapchain view");
			VkFramebufferCreateInfo framebuffer{}; framebuffer.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
			framebuffer.renderPass = screen_pass; framebuffer.attachmentCount = 1; framebuffer.pAttachments = &slot.view;
			framebuffer.width = swap_extent.width; framebuffer.height = swap_extent.height; framebuffer.layers = 1;
			Check(vkCreateFramebuffer(device, &framebuffer, nullptr, &slot.framebuffer), "create swapchain framebuffer");
			VkSemaphoreCreateInfo semaphore{}; semaphore.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
			Check(vkCreateSemaphore(device, &semaphore, nullptr, &slot.complete), "create presentation semaphore");
			swap_images.push_back(slot);
		}
		swap_dirty = false;
	}

	void Resize(int w, int h)
	{
		w = std::max(w, 1); h = std::max(h, 1);
		if (w == width && h == height && !swap_dirty) return;
		if (recording) Flush();
		Check(vkDeviceWaitIdle(device), "resize UI buffer");
		width = w; height = h; pitch = (w + 3) & ~3;
		video.assign(static_cast<size_t>(pitch) * h, Colour(0, 0, 0)); animation.assign(static_cast<size_t>(pitch) * h, 0);
		ui = MakeImage(w, h, VK_FORMAT_B8G8R8A8_UNORM, VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
		ui_animation = MakeImage(w, h, VK_FORMAT_R8_UNORM, VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT);
		_screen.width = w; _screen.height = h; _screen.pitch = pitch; _screen.dst_ptr = nullptr;
		MakeSwapchain();
	}

	void UploadAtlas()
	{
		for (size_t i = 0; i < Textures().pages.size(); ++i) {
			auto &page = Textures().pages[i];
			if (page.dirty_right <= page.dirty_left) continue;
			int x = page.dirty_left, y = page.dirty_top, w = page.dirty_right - x, h = page.dirty_bottom - y;
			size_t offset = static_cast<size_t>(y) * ATLAS_SIZE + x;
			Upload(*atlas, page.rgba.data() + offset * 4, x, y, w, h, 4, ATLAS_SIZE, static_cast<uint32_t>(i));
			Upload(*remap, page.remap.data() + offset * 2, x, y, w, h, 2, ATLAS_SIZE, static_cast<uint32_t>(i));
			page.dirty_left = page.dirty_top = ATLAS_SIZE; page.dirty_right = page.dirty_bottom = 0;
		}
		auto palette_snapshot = SnapshotPalette();
		Upload(*palette, palette_snapshot.palette, 0, 0, 256, 1, 4, 256);
	}

	void Render(Target &target, const Scene &scene, const Camera &camera, bool diagnostic = false)
	{
		Profile::Scope timing(Profile::Section::Backend);
		Profile::AddGeometry(scene.VertexCount());
		Begin(); UploadAtlas();
		Slice vertices = Allocate(scene.vertices.size() * sizeof(Vertex));
		if (!scene.vertices.empty()) std::memcpy(vertices.data, scene.vertices.data(), scene.vertices.size() * sizeof(Vertex));
		bool transparent_vertices = std::any_of(scene.vertices.begin(), scene.vertices.end(), [](const Vertex &vertex) { return vertex.opacity < 0.99f; });
		instance_staging.Build(scene.instances,true);
		auto &records = instance_staging.records;
		auto &batches = instance_batches;
		batches.clear();
		const auto volume_frustum = camera.Frustum();
		bool pixel_cull = VoxelPixelCullEnabled() && !camera.first_person && camera.pixels_per_unit < 0.5f;
		static const bool synchronous_visibility = [] { const char *setting = std::getenv("OPENTT3D_VOXEL_CULL_SYNC"); return setting != nullptr && std::string_view(setting) == "1"; }();
		bool asynchronous = pixel_cull && !diagnostic && !synchronous_visibility;
		if (asynchronous) {
			if (!target.visibility_worker) target.visibility_worker = std::make_unique<VoxelVisibilityWorker>();
			target.visibility_worker->SetCamera(camera,properties.limits.subPixelPrecisionBits);
			if (auto message = target.visibility_worker->TakeError(); !message.empty()) Debug(driver,1,"OpenTT3D: voxel visibility preparation retained mesh fallback: {}",message);
		} else if (target.visibility_worker) target.visibility_worker->Cancel();
		if (!pixel_cull || target.visibility.Begin(camera,properties.limits.subPixelPrecisionBits,records.size())) {
			for (auto &[mesh,stream] : target.visible_streams) if (stream.buffer) Current().retired_buffers.push_back(std::move(stream.buffer));
			target.visible_streams.clear();
			if (!pixel_cull) target.visibility.Clear();
			if (!diagnostic) target.visibility_reported = false;
		}
		uint64_t tested_vertices = 0, retained_vertices = 0;
		unsigned waiting_visibility = 0;
		size_t visibility_budget = 32;
		for (const auto &batch : instance_staging.batches) {
			const auto *mesh = batch.mesh;
			VkDescriptorBufferInfo volume_storage{};
			uint32_t volume_mode = 0;
			if (const auto *volume = FindVoxelVolume(mesh); volume != nullptr && !volume->bounds.empty() &&
					std::all_of(records.begin()+batch.first,records.begin()+batch.first+batch.count,[&](const InstanceData &data) {
						return VolumeInstanceCompatible(data) && VolumeOutsideNearPlane(*volume,data,volume_frustum);
					})) {
				auto [entry,inserted] = volumes.try_emplace(volume);
				if (inserted) {
					entry->second = MakeBuffer(volume->words.size()*sizeof(uint32_t),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
					std::memcpy(entry->second->mapped,volume->words.data(),volume->words.size()*sizeof(uint32_t));
					Debug(driver,2,"OpenTT3D: full-cell voxel {} replaces {} mesh vertices with {} proxy vertices, {} bytes",VoxelSlicesEnabled() ? "slices" : "volume",mesh->size(),VoxelSlicesEnabled() ? volume->slices.size() : volume->bounds.size(),entry->second->size);
				}
				volume_storage = {entry->second->handle,0,entry->second->size};
				volume_mode = VoxelSlicesEnabled() ? 2 : 1;
				mesh = VoxelSlicesEnabled() ? &volume->slices : &volume->bounds;
			}
			const auto *packed = FindPackedVoxelMesh(mesh);
			if (packed != nullptr) {
				auto [entry,inserted] = packed_formats.try_emplace(packed);
				if (inserted) {
					entry->second = MakeBuffer(packed->format.size()*sizeof(uint32_t),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
					std::memcpy(entry->second->mapped,packed->format.data(),packed->format.size()*sizeof(uint32_t));
				}
				volume_storage = {entry->second->handle,0,entry->second->size};
			}
			if (pixel_cull && packed != nullptr && packed->pixel_cull && packed->StandardPalette() && std::all_of(records.begin()+batch.first,records.begin()+batch.first+batch.count,VolumeInstanceCompatible)) {
				auto [entry,inserted] = visibility_lookups.try_emplace(packed);
				auto &lookup = entry->second;
				if (inserted) {
					auto indexed = MakePackedVoxelLookup(packed->vertices);
					lookup.bits = indexed.bits; lookup.indices = std::move(indexed.indices);
					lookup.buffer = MakeBuffer((indexed.vertices.size()+1)*sizeof(uint32_t),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
					static_cast<uint32_t *>(lookup.buffer->mapped)[0] = lookup.bits;
					std::memcpy(static_cast<uint32_t *>(lookup.buffer->mapped)+1,indexed.vertices.data(),indexed.vertices.size()*sizeof(uint32_t));
				}
				if (lookup.bits <= 21 && batch.count <= (uint64_t{1}<<(64-lookup.bits*3))) {
					auto &cached = target.visible_streams[mesh];
					auto matches = [&](std::span<const std::array<uint32_t,7>> transforms) {
						if (transforms.size() != batch.count) return false;
						for (size_t i = 0; i < batch.count; ++i) if (transforms[i] != VoxelVisibilityTransform(records[batch.first+i])) return false;
						return true;
					};
					bool unchanged = matches(cached.transforms);
					bool prepare_now = !asynchronous;
					if (!unchanged && asynchronous) {
						if (auto ready = target.visibility_worker->Take(*mesh)) {
							for (size_t i = 0; i < ready->transforms.size(); ++i) target.visibility.AdoptPacked(*mesh,ready->transforms[i],std::move(ready->geometry[i]));
						}
						size_t missing = 0;
						for (size_t i = 0; i < batch.count && missing <= visibility_budget; ++i) missing += !target.visibility.HasPacked(*mesh,records[batch.first+i]);
						if (missing <= visibility_budget) { prepare_now = true; visibility_budget -= missing; }
						else {
							target.visibility_worker->Request(*mesh,PackedVoxelMeshRegistry().at(mesh),std::span(records).subspan(batch.first,batch.count),records.size());
							++waiting_visibility;
						}
					}
					if (!unchanged && prepare_now) {
						visible_spans.clear();
						cached.triangles = 0; cached.transforms.clear(); cached.transforms.reserve(batch.count);
						for (size_t index = batch.first; index < batch.first+batch.count; ++index) {
							auto triangles = target.visibility.PackedTriangles(*mesh,records[index],lookup.indices,lookup.bits);
							visible_spans.push_back({triangles,static_cast<uint32_t>(index-batch.first)});
							cached.triangles += triangles.size();
							cached.transforms.push_back(VoxelVisibilityTransform(records[index]));
						}
						if (cached.buffer) Current().retired_buffers.push_back(std::move(cached.buffer));
						if (cached.triangles != 0) {
							cached.buffer = MakeBuffer(cached.triangles*sizeof(VisibleVoxelTriangle),VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
							auto *destination = static_cast<VisibleVoxelTriangle *>(cached.buffer->mapped);
							for (const auto &span : visible_spans) {
								uint64_t instance_bits = static_cast<uint64_t>(span.instance)<<(lookup.bits*3);
								for (uint64_t triangle : span.triangles) {
									uint64_t word = triangle|instance_bits;
									*destination++ = {static_cast<uint32_t>(word),static_cast<uint32_t>(word>>32)};
								}
							}
						}
						unchanged = true;
					}
					if (unchanged) {
						size_t triangle_count = cached.triangles;
						tested_vertices += static_cast<uint64_t>(mesh->size())*batch.count;
						retained_vertices += triangle_count*3;
						if (triangle_count == 0) continue;
						VkDeviceSize alignment = std::max<VkDeviceSize>(16,properties.limits.minStorageBufferOffsetAlignment);
						size_t chunk = std::min<VkDeviceSize>(properties.limits.maxStorageBufferRange,static_cast<uint64_t>(UINT32_MAX/3)*sizeof(VisibleVoxelTriangle))/alignment*alignment/sizeof(VisibleVoxelTriangle);
						for (size_t first = 0; first < triangle_count; first += chunk) {
							size_t count = std::min(chunk,triangle_count-first);
							VkDescriptorBufferInfo triangles{cached.buffer->handle,first*sizeof(VisibleVoxelTriangle),count*sizeof(VisibleVoxelTriangle)};
							VkDescriptorBufferInfo vertices{lookup.buffer->handle,0,lookup.buffer->size};
							batches.push_back({VK_NULL_HANDLE,0,0,static_cast<uint32_t>(count*3),static_cast<uint32_t>(batch.first),1,false,false,true,false,VK_INDEX_TYPE_UINT16,volume_storage,0,packed->format[7] != 0 ? 2U : 1U,true,triangles,vertices});
						}
						continue;
					}
				}
			}
			auto found = meshes.find(mesh);
			if (found == meshes.end()) {
				Profile::Scope upload_time(Profile::Section::MeshUpload);
				IndexedMesh indexed;
				IndexedPackedVoxelMesh indexed_packed;
				std::vector<uint16_t> short_indices;
				if (IndexImmutableMeshes()) {
					Profile::Scope timing(Profile::Section::MeshIndex);
					if (packed != nullptr) { indexed_packed = IndexPackedVoxelMesh(packed->vertices); short_indices = std::move(indexed_packed.indices); }
					else { indexed = IndexMesh(*mesh); short_indices = indexed.ShortIndices(); }
				}
				bool use_indices = !indexed.indices.empty() || !short_indices.empty();
				VkIndexType index_type = short_indices.empty() ? VK_INDEX_TYPE_UINT32 : VK_INDEX_TYPE_UINT16;
				const auto &data = use_indices ? indexed.vertices : *mesh;
				size_t vertex_bytes = data.size()*sizeof(Vertex), index_bytes = short_indices.empty() ? indexed.indices.size()*sizeof(uint32_t) : short_indices.size()*sizeof(uint16_t);
				const void *vertex_data = data.data();
				size_t stored_vertices = data.size();
				if (packed != nullptr) {
					const auto &words = use_indices ? indexed_packed.vertices : packed->vertices;
					vertex_data = words.data(); stored_vertices = words.size(); vertex_bytes = words.size()*sizeof(uint32_t);
				}
				size_t bytes = vertex_bytes+index_bytes;
				Slice storage;
				if (pool_meshes) {
					storage = AllocateIn(mesh_arena, bytes);
				} else {
					mesh_arena.push_back(MakeBuffer(bytes, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_INDEX_BUFFER_BIT));
					auto &buffer = mesh_arena.back();
					buffer->used = bytes;
					storage = {buffer->handle, 0, buffer->mapped};
				}
				if (vertex_bytes != 0) std::memcpy(storage.data,vertex_data,vertex_bytes);
				if (index_bytes != 0) std::memcpy(static_cast<std::byte *>(storage.data)+vertex_bytes,short_indices.empty() ? static_cast<const void *>(indexed.indices.data()) : short_indices.data(),index_bytes);
				found = meshes.emplace(mesh,MeshStorage{storage,storage.offset+vertex_bytes,static_cast<uint32_t>(mesh->size()),static_cast<uint32_t>(stored_vertices),use_indices,index_type}).first;
				if (packed != nullptr) Debug(driver,2,"OpenTT3D: lossless packed voxel mesh {} source vertices / {} stored, {} bytes",mesh->size(),stored_vertices,bytes);
				Profile::AddMeshUpload(bytes);
			}
			const auto &stored = found->second;
			batches.push_back({stored.storage.buffer,stored.storage.offset,stored.index_offset,stored.source_vertices,static_cast<uint32_t>(batch.first),static_cast<uint32_t>(batch.count),batch.transparent,stored.indexed,instance_staging.PaletteOnly(batch),batch.both_passes,stored.index_type,volume_storage,volume_mode,packed == nullptr ? 0U : packed->format[7] != 0 ? 2U : 1U});
		}
		if (tested_vertices != 0 && waiting_visibility == 0 && !target.visibility_reported) {
			Debug(driver,1,"OpenTT3D: conservative pixel visibility retains {} of {} voxel vertices with original triangle/instance order",retained_vertices,tested_vertices);
			target.visibility_reported = true;
		}
		Slice instances = Allocate(records.size() * sizeof(InstanceData), std::max<VkDeviceSize>(16, properties.limits.minStorageBufferOffsetAlignment));
		std::memcpy(instances.data, records.data(), records.size() * sizeof(InstanceData));
		VkDescriptorBufferInfo storage{instances.buffer, instances.offset, records.size() * sizeof(InstanceData)};
		Image *images[] = {atlas.get(), remap.get(), palette.get()};
		VkDescriptorSet set = Descriptor(world_layout, images, &storage);
		VkClearValue clear[3]{};
		clear[0].color = camera.first_person || camera.pitch < 20 ? VkClearColorValue{{0.52f, 0.70f, 0.86f, 1}} : VkClearColorValue{{0, 0, 0, 1}};
		clear[1].color.uint32[0] = 0; clear[2].depthStencil = {0, 0};
		VkRenderPassBeginInfo begin{}; begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
		begin.renderPass = world_pass; begin.framebuffer = target.framebuffer; begin.renderArea.extent = {static_cast<uint32_t>(camera.width), static_cast<uint32_t>(camera.height)};
		begin.clearValueCount = 3; begin.pClearValues = clear;
		vkCmdBeginRenderPass(Command(), &begin, VK_SUBPASS_CONTENTS_INLINE);
		VkViewport viewport{0, 0, static_cast<float>(camera.width), static_cast<float>(camera.height), 0, 1};
		VkRect2D scissor{{0, 0}, begin.renderArea.extent};
		vkCmdSetViewport(Command(), 0, 1, &viewport); vkCmdSetScissor(Command(), 0, 1, &scissor);
		vkCmdBindDescriptorSets(Command(), VK_PIPELINE_BIND_POINT_GRAPHICS, world_pipeline_layout, 0, 1, &set, 0, nullptr);
		WorldPush push{camera.Matrix(), {camera.focus.x, camera.focus.y, camera.focus.z, camera.Near()}, {scene.water.uv_origin.x, scene.water.uv_origin.y, scene.water.uv_origin.z, scene.water.uv_scale}, {}};
		auto water = push.water;
		Vec3 eye = camera.focus_offset+camera.Unrotate(Camera::World(camera.Back()*camera.Distance()));
		VkDescriptorSet bound_set = set;
		for (unsigned pass = 0; pass < 2; ++pass) {
			VkPipeline bound = pass == 0 ? opaque_pipeline : transparent_pipeline;
			vkCmdBindPipeline(Command(),VK_PIPELINE_BIND_POINT_GRAPHICS,bound);
			push.mode = {0, pass, 0, static_cast<uint32_t>(camera.width) | (static_cast<uint32_t>(camera.height)<<16)};
			push.water = water;
			if (bound_set != set) { vkCmdBindDescriptorSets(Command(),VK_PIPELINE_BIND_POINT_GRAPHICS,world_pipeline_layout,0,1,&set,0,nullptr); bound_set = set; }
			vkCmdPushConstants(Command(), world_pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
			vkCmdBindVertexBuffers(Command(), 0, 1, &vertices.buffer, &vertices.offset);
			if (pass == 0 || transparent_vertices) vkCmdDraw(Command(), static_cast<uint32_t>(scene.vertices.size()), 1, 0, 0);
			push.mode[0] = 1;
			vkCmdPushConstants(Command(), world_pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
			for (const auto &batch : batches) {
				if (!batch.both_passes && batch.transparent != (pass != 0)) continue;
				bool volume = batch.volume_mode != 0;
				VkPipeline pipeline = batch.visible ? visible_pipelines[batch.packed_mode-1] : batch.packed_mode != 0 ? packed_pipelines[pass+(batch.cull_back ? 2 : 0)+(batch.packed_mode == 2 ? 4 : 0)] : volume ? (batch.volume_mode == 2 ? voxel_slice_pipeline : voxel_pipeline) : batch.cull_back ? (pass == 0 ? opaque_palette_pipeline : transparent_palette_pipeline) : (pass == 0 ? opaque_pipeline : transparent_pipeline);
				if (pipeline != bound) { vkCmdBindPipeline(Command(),VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline); bound = pipeline; }
				VkDescriptorSet descriptor = batch.volume.buffer != VK_NULL_HANDLE ? Descriptor(world_layout,images,&storage,&batch.volume,batch.visible ? &batch.triangles : nullptr,batch.visible ? &batch.lookup : nullptr) : set;
				if (descriptor != bound_set) { vkCmdBindDescriptorSets(Command(),VK_PIPELINE_BIND_POINT_GRAPHICS,world_pipeline_layout,0,1,&descriptor,0,nullptr); bound_set = descriptor; }
				if (push.mode[2] != batch.volume_mode) {
					push.mode[2] = batch.volume_mode;
					push.water = volume ? std::array<float,4>{eye.x,eye.y,eye.z,static_cast<float>(properties.limits.subPixelPrecisionBits)} : water;
					vkCmdPushConstants(Command(),world_pipeline_layout,VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,0,sizeof(push),&push);
				}
				if (!batch.visible) vkCmdBindVertexBuffers(Command(), 0, 1, &batch.mesh, &batch.offset);
				if (batch.indexed) {
					vkCmdBindIndexBuffer(Command(),batch.mesh,batch.index_offset,batch.index_type);
					vkCmdDrawIndexed(Command(),batch.vertices,batch.count,0,0,batch.first);
				} else vkCmdDraw(Command(),batch.vertices,batch.count,0,batch.first);
			}
		}
		vkCmdEndRenderPass(Command());
		target.colour->layout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL; target.ids->layout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
		target.depth->layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
	}

	void DrawComposite(Image &image, CompositePush push)
	{
		Image *images[] = {&image, ui_animation.get(), palette.get()};
		VkDescriptorSet set = Descriptor(composite_layout, images);
		vkCmdBindDescriptorSets(Command(), VK_PIPELINE_BIND_POINT_GRAPHICS, composite_pipeline_layout, 0, 1, &set, 0, nullptr);
		vkCmdPushConstants(Command(), composite_pipeline_layout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(push), &push);
		vkCmdDraw(Command(), 4, 1, 0, 0);
	}

	void Present(bool use_animation)
	{
		Begin();
		if (swap_dirty || swapchain == VK_NULL_HANDLE) MakeSwapchain();
		if (swapchain == VK_NULL_HANDLE) { Flush(); return; }
		uint32_t index;
		VkResult acquire;
		{
			Profile::Scope acquire_time(Profile::Section::SwapchainAcquire);
			acquire = vkAcquireNextImageKHR(device, swapchain, UINT64_MAX, Current().acquired, VK_NULL_HANDLE, &index);
			if (acquire == VK_ERROR_OUT_OF_DATE_KHR) {
				MakeSwapchain();
				acquire = vkAcquireNextImageKHR(device, swapchain, UINT64_MAX, Current().acquired, VK_NULL_HANDLE, &index);
			}
		}
		if (acquire != VK_SUCCESS && acquire != VK_SUBOPTIMAL_KHR) Check(acquire, "acquire swapchain image");
		{
			Profile::Scope upload_time(Profile::Section::PresentationUpload);
			Upload(*ui, video.data(), 0, 0, width, height, 4, pitch);
			Upload(*ui_animation, animation.data(), 0, 0, width, height, 1, pitch);
			auto palette_snapshot = SnapshotPalette();
			Upload(*palette, palette_snapshot.palette, 0, 0, 256, 1, 4, 256);
		}
		VkClearValue clear{}; clear.color.float32[3] = 1;
		VkRenderPassBeginInfo begin{}; begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
		begin.renderPass = screen_pass; begin.framebuffer = swap_images[index].framebuffer; begin.renderArea.extent = swap_extent; begin.clearValueCount = 1; begin.pClearValues = &clear;
		vkCmdBeginRenderPass(Command(), &begin, VK_SUBPASS_CONTENTS_INLINE);
		VkViewport viewport{0, 0, static_cast<float>(swap_extent.width), static_cast<float>(swap_extent.height), 0, 1};
		VkRect2D scissor{{0, 0}, swap_extent};
		vkCmdSetViewport(Command(), 0, 1, &viewport); vkCmdSetScissor(Command(), 0, 1, &scissor);
		vkCmdBindPipeline(Command(), VK_PIPELINE_BIND_POINT_GRAPHICS, composite_pipeline);
		for (const auto &region : regions) {
			CompositePush push{{2.0f * region.dx / width - 1, 2.0f * region.dy / height - 1, 2.0f * region.width / width, 2.0f * region.height / height},
				{static_cast<float>(region.sx) / region.target->colour->width, static_cast<float>(region.sy) / region.target->colour->height,
				static_cast<float>(region.width) / region.target->colour->width, static_cast<float>(region.height) / region.target->colour->height}, {}};
			DrawComposite(*region.target->colour, push);
		}
		DrawComposite(*ui, {{-1, -1, 2, 2}, {0, 0, 1, 1}, {use_animation ? 1U : 0U, 0, 0, 0}});
		vkCmdEndRenderPass(Command());
		if (Current().timestamps != VK_NULL_HANDLE) vkCmdWriteTimestamp(Command(), VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, Current().timestamps, 1);
		std::unique_ptr<Buffer> captured;
		if (capture) {
			captured = MakeBuffer(static_cast<VkDeviceSize>(swap_extent.width) * swap_extent.height * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
			VkImageMemoryBarrier barrier{};
			barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
			barrier.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT; barrier.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
			barrier.oldLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR; barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
			barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
			barrier.image = swap_images[index].image; barrier.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
			vkCmdPipelineBarrier(Command(), VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 0, nullptr, 1, &barrier);
			VkBufferImageCopy copy{};
			copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1}; copy.imageExtent = {swap_extent.width, swap_extent.height, 1};
			vkCmdCopyImageToBuffer(Command(), barrier.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, captured->handle, 1, &copy);
			barrier.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT; barrier.dstAccessMask = 0;
			std::swap(barrier.oldLayout, barrier.newLayout);
			VkBufferMemoryBarrier host{};
			host.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
			host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT; host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
			host.srcQueueFamilyIndex = host.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
			host.buffer = captured->handle; host.size = VK_WHOLE_SIZE;
			vkCmdPipelineBarrier(Command(), VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT | VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0, 0, nullptr, 1, &host, 1, &barrier);
		}
		Check(vkEndCommandBuffer(Command()), "end presentation commands");
		Check(vkResetFences(device, 1, &Current().fence), "reset frame fence");
		VkPipelineStageFlags wait_stage = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
		VkSubmitInfo submit{}; submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
		submit.waitSemaphoreCount = 1; submit.pWaitSemaphores = &Current().acquired; submit.pWaitDstStageMask = &wait_stage;
		submit.commandBufferCount = 1; submit.pCommandBuffers = &Current().command; submit.signalSemaphoreCount = 1; submit.pSignalSemaphores = &swap_images[index].complete;
		{
			Profile::Scope submit_time(Profile::Section::QueueSubmit);
			Check(vkQueueSubmit(graphics, 1, &submit, Current().fence), "submit frame");
		}
		Current().timed = Current().timestamps != VK_NULL_HANDLE;
		VkPresentInfoKHR present{}; present.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
		present.waitSemaphoreCount = 1; present.pWaitSemaphores = &swap_images[index].complete; present.swapchainCount = 1; present.pSwapchains = &swapchain; present.pImageIndices = &index;
		VkResult status;
		{
			Profile::Scope present_time(Profile::Section::QueuePresent);
			status = vkQueuePresentKHR(presentation, &present);
		}
		if (status == VK_ERROR_OUT_OF_DATE_KHR || status == VK_SUBOPTIMAL_KHR) swap_dirty = true; else Check(status, "present frame");
		if (captured) {
			Check(vkWaitForFences(device, 1, &Current().fence, VK_TRUE, UINT64_MAX), "wait presentation capture");
			std::vector<Colour> pixels(static_cast<size_t>(swap_extent.width) * swap_extent.height);
			const auto *bytes = static_cast<const uint8_t *>(captured->mapped);
			bool bgra = screen_format == VK_FORMAT_B8G8R8A8_UNORM;
			for (size_t i = 0; i < pixels.size(); ++i) pixels[i] = Colour(bytes[i * 4 + (bgra ? 2 : 0)], bytes[i * 4 + 1], bytes[i * 4 + (bgra ? 0 : 2)], bytes[i * 4 + 3]);
			Debug(driver, 1, "OpenTT3D: captured Vulkan presentation with {} GPU viewport regions", regions.size());
			auto callback = std::exchange(capture, {});
			callback(swap_extent.width, swap_extent.height, std::move(pixels));
		}
		recording = false; regions.clear(); frame_index = (frame_index + 1) % frames.size();
	}

	void CopyImage(Image &image, Buffer &buffer, uint32_t x, uint32_t y, uint32_t w, uint32_t h)
	{
		Transition(image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);
		VkBufferImageCopy copy{};
		copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1}; copy.imageOffset = {static_cast<int32_t>(x), static_cast<int32_t>(y), 0}; copy.imageExtent = {w, h, 1};
		vkCmdCopyImageToBuffer(Command(), image.handle, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, buffer.handle, 1, &copy);
		VkBufferMemoryBarrier barrier{}; barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
		barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT; barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
		barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
		barrier.buffer = buffer.handle; barrier.offset = 0; barrier.size = VK_WHOLE_SIZE;
		vkCmdPipelineBarrier(Command(), VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0, 0, nullptr, 1, &barrier, 0, nullptr);
	}

	void Shutdown()
	{
		if (device != VK_NULL_HANDLE) {
			vkDeviceWaitIdle(device);
			targets.clear(); retired.clear(); readback_target.reset(); meshes.clear(); mesh_arena.clear();
			volumes.clear(); packed_formats.clear(); visibility_lookups.clear(); empty_volume.reset();
			DestroySwapchain();
			atlas.reset(); remap.reset(); palette.reset(); ui.reset(); ui_animation.reset();
			for (auto &frame : frames) {
				frame.arena.clear();
				frame.retired_buffers.clear();
				if (frame.descriptors) vkDestroyDescriptorPool(device, frame.descriptors, nullptr);
				if (frame.commands) vkDestroyCommandPool(device, frame.commands, nullptr);
				if (frame.fence) vkDestroyFence(device, frame.fence, nullptr);
				if (frame.acquired) vkDestroySemaphore(device, frame.acquired, nullptr);
				if (frame.timestamps) vkDestroyQueryPool(device, frame.timestamps, nullptr);
			}
			if (readback_fence) vkDestroyFence(device, readback_fence, nullptr);
			for (auto pipeline : {opaque_pipeline,transparent_pipeline,opaque_palette_pipeline,transparent_palette_pipeline,voxel_pipeline,voxel_slice_pipeline,composite_pipeline}) if (pipeline) vkDestroyPipeline(device,pipeline,nullptr);
			for (auto pipeline : packed_pipelines) if (pipeline) vkDestroyPipeline(device,pipeline,nullptr);
			for (auto pipeline : visible_pipelines) if (pipeline) vkDestroyPipeline(device,pipeline,nullptr);
			if (world_pass) vkDestroyRenderPass(device, world_pass, nullptr);
			if (screen_pass) vkDestroyRenderPass(device, screen_pass, nullptr);
			if (world_pipeline_layout) vkDestroyPipelineLayout(device, world_pipeline_layout, nullptr);
			if (composite_pipeline_layout) vkDestroyPipelineLayout(device, composite_pipeline_layout, nullptr);
			if (world_layout) vkDestroyDescriptorSetLayout(device, world_layout, nullptr);
			if (composite_layout) vkDestroyDescriptorSetLayout(device, composite_layout, nullptr);
			if (sampler) vkDestroySampler(device, sampler, nullptr);
			vkDestroyDevice(device, nullptr);
		}
		if (surface) vkDestroySurfaceKHR(instance, surface, nullptr);
		if (messenger) reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance, "vkDestroyDebugUtilsMessengerEXT"))(instance, messenger, nullptr);
		if (instance) vkDestroyInstance(instance, nullptr);
	}
};

std::unique_ptr<Context> context;
std::string error;

template <typename Operation>
bool Try(Operation operation)
{
	try { operation(); return true; }
	catch (const std::exception &exception) { error = exception.what(); Debug(driver, 0, "OpenTT3D: Vulkan rendering failed: {}", error); return false; }
}

} // namespace

bool CreateInstance(std::span<const char *const> required)
{
	Destroy();
	return Try([&] {
		context = std::make_unique<Context>();
		uint32_t count = 0;
		Check(vkEnumerateInstanceExtensionProperties(nullptr, &count, nullptr), "enumerate instance extensions");
		std::vector<VkExtensionProperties> available(count);
		Check(vkEnumerateInstanceExtensionProperties(nullptr, &count, available.data()), "enumerate instance extensions");
		std::vector<const char *> extensions(required.begin(), required.end());
		bool portability = false;
		for (const auto &extension : available) if (std::strcmp(extension.extensionName, VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME) == 0) {
			extensions.push_back(VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME); portability = true;
		}
		VkApplicationInfo app{}; app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
		app.pApplicationName = "OpenTT3D"; app.apiVersion = VK_API_VERSION_1_1;
		VkInstanceCreateInfo create{}; create.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
		create.pApplicationInfo = &app; create.flags = portability ? VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR : 0;
		const char *validation = std::getenv("OPENTT3D_VULKAN_VALIDATION");
		bool validate = validation != nullptr && std::string_view(validation) == "1";
		const char *layer = "VK_LAYER_KHRONOS_validation";
		VkDebugUtilsMessengerCreateInfoEXT debug{}; debug.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
		debug.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
		debug.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT | VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
		debug.pfnUserCallback = ValidationMessage;
		VkValidationFeatureEnableEXT synchronization = VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT;
		VkValidationFeaturesEXT features{}; features.sType = VK_STRUCTURE_TYPE_VALIDATION_FEATURES_EXT;
		features.pNext = &debug; features.enabledValidationFeatureCount = 1; features.pEnabledValidationFeatures = &synchronization;
		if (validate) {
			extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
			extensions.push_back(VK_EXT_VALIDATION_FEATURES_EXTENSION_NAME);
			create.enabledLayerCount = 1; create.ppEnabledLayerNames = &layer; create.pNext = &features;
		}
		create.enabledExtensionCount = static_cast<uint32_t>(extensions.size()); create.ppEnabledExtensionNames = extensions.data();
		Check(vkCreateInstance(&create, nullptr, &context->instance), "create instance");
		if (validate) {
			auto create_debug = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(context->instance, "vkCreateDebugUtilsMessengerEXT"));
			if (create_debug == nullptr) throw std::runtime_error("Vulkan validation messenger is unavailable");
			Check(create_debug(context->instance, &debug, nullptr, &context->messenger), "create validation messenger");
			Debug(driver, 1, "OpenTT3D: Vulkan synchronization validation enabled");
		}
	});
}

VkInstance Instance() { return context == nullptr ? VK_NULL_HANDLE : context->instance; }
bool SetSurface(VkSurfaceKHR surface) { return Try([&] { context->surface = surface; context->ConfigureDevice(); }); }
bool Active() { return context != nullptr && context->device != VK_NULL_HANDLE; }
void Destroy() { context.reset(); }
const std::string &LastError() { return error; }
std::string Description() { return Active() ? fmt::format("Vulkan: {}", context->properties.deviceName) : "unavailable"; }
int MaximumImageSize() { return Active() ? static_cast<int>(context->properties.limits.maxImageDimension2D) : 0; }
MeshCacheStats GetMeshCacheStats() { return Active() ? context->MeshUsage() : MeshCacheStats{}; }
bool Resize(int width, int height) { return Active() && Try([&] { context->Resize(width, height); }); }
void *VideoBuffer() { if (!Active()) return nullptr; if (!Try([] { context->Begin(); })) return nullptr; return context->video.data(); }
uint8_t *AnimationBuffer() { return Active() ? context->animation.data() : nullptr; }
bool Present(bool animation) { return Active() && Try([&] { context->Present(animation); }); }
bool CapturePresentation(PresentationCapture callback)
{
	if (!Active() || !context->screen_transfer || context->capture) return false;
	context->capture = std::move(callback);
	return true;
}

bool RenderViewport(const void *key, const Scene &scene, const Camera &camera)
{
	return Active() && Try([&] {
		context->Begin();
		auto &target = context->targets[key];
		if (target == nullptr || target->colour->width != static_cast<uint32_t>(camera.width) || target->colour->height != static_cast<uint32_t>(camera.height)) {
			if (target) context->retired.push_back(std::move(target));
			target = context->MakeTarget(camera.width, camera.height);
		}
		context->Render(*target, scene, camera);
	});
}

void ComposeViewport(const void *key, int sx, int sy, int width, int height, int dx, int dy)
{
	if (!Active()) return;
	auto found = context->targets.find(key);
	if (found != context->targets.end()) context->regions.push_back({found->second.get(), sx, sy, width, height, dx, dy});
}

void ForgetViewport(const void *key)
{
	if (!Active()) return;
	auto found = context->targets.find(key);
	if (found != context->targets.end()) { context->retired.push_back(std::move(found->second)); context->targets.erase(found); }
}

uint32_t ReadObjectId(const void *key, int x, int y)
{
	if (!Active()) return 0;
	auto found = context->targets.find(key);
	if (found == context->targets.end() || x < 0 || y < 0 || x >= static_cast<int>(found->second->ids->width) || y >= static_cast<int>(found->second->ids->height)) return 0;
	uint32_t result = 0;
	Try([&] {
		context->Begin();
		auto buffer = context->MakeBuffer(4, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
		context->CopyImage(*found->second->ids, *buffer, x, y, 1, 1);
		context->Flush();
		std::memcpy(&result, buffer->mapped, sizeof(result));
	});
	return result;
}

bool Readback(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels, std::vector<uint32_t> *ids)
{
#ifdef __APPLE__
	/* A console verification can perform thousands of synchronous MoltenVK
	 * readbacks without returning to Cocoa's event-loop pool. Retire each call's
	 * temporary Metal objects after its fence and buffer destructors complete. */
	CocoaAutoreleasePool autorelease_pool;
#endif
	return Active() && Try([&] {
		context->Begin();
		auto &target = context->readback_target;
		if (target == nullptr || target->colour->width != static_cast<uint32_t>(camera.width) || target->colour->height != static_cast<uint32_t>(camera.height)) {
			context->Flush(); target = context->MakeTarget(camera.width, camera.height);
		}
		context->Render(*target, scene, camera,true);
		Profile::Scope timing(Profile::Section::Readback);
		size_t size = static_cast<size_t>(camera.width) * camera.height;
		auto colour = context->MakeBuffer(size * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
		auto picking = ids == nullptr ? nullptr : context->MakeBuffer(size * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT);
		context->CopyImage(*target->colour, *colour, 0, 0, camera.width, camera.height);
		if (picking) context->CopyImage(*target->ids, *picking, 0, 0, camera.width, camera.height);
		context->Flush();
		pixels.resize(size * 4); if (ids != nullptr) ids->resize(size);
		/* Preserve the existing bottom-up readback API used by gallery/screenshots. */
		for (int row = 0; row < camera.height; ++row) {
			size_t source = static_cast<size_t>(camera.height - 1 - row) * camera.width, destination = static_cast<size_t>(row) * camera.width;
			std::memcpy(pixels.data() + destination * 4, static_cast<const std::byte *>(colour->mapped) + source * 4, static_cast<size_t>(camera.width) * 4);
			if (ids != nullptr) std::memcpy(ids->data() + destination, static_cast<const std::byte *>(picking->mapped) + source * 4, static_cast<size_t>(camera.width) * 4);
		}
	});
}

} // namespace Renderer3D::Vulkan
