/* SPDX-License-Identifier: GPL-2.0-only */
/** @file gl_backend.cpp Depth-tested mesh pass, isolated from upstream UI GL state. */

#include "../stdafx.h"
#include "gl_backend.hpp"
#include "sprite_textures.hpp"
#include "instance_batcher.hpp"
#include "indexed_mesh.hpp"
#include "voxel_visibility_worker.hpp"
#include "voxel_volume.hpp"
#include "profiling.h"
#include "vulkan_backend.h"
#include "../gfx_func.h"
#include "../debug.h"
#include <map>
#include <unordered_map>

#ifdef WITH_OPENGL

#ifdef _WIN32
#include <windows.h>
#endif
#define GL_GLEXT_PROTOTYPES
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION
#include <OpenGL/gl3.h>
#else
#include <GL/gl.h>
#endif
#include "../3rdparty/opengl/glext.h"
#include "../video/opengl.h"

extern GetOGLProcAddressProc GetOGLProcAddress;

namespace Renderer3D {

#define R3D_GL_FUNCTIONS(X) \
	X(glGetIntegerv) X(glIsEnabled) X(glGetFloatv) X(glGetBooleanv) X(glGetBooleani_v) X(glGetError) \
	X(glGenFramebuffers) X(glBindFramebuffer) X(glDeleteFramebuffers) X(glCheckFramebufferStatus) \
	X(glGenRenderbuffers) X(glBindRenderbuffer) X(glRenderbufferStorage) X(glFramebufferRenderbuffer) X(glDeleteRenderbuffers) \
	X(glGenTextures) X(glDeleteTextures) X(glBindTexture) X(glTexImage2D) X(glTexImage3D) X(glTexSubImage2D) X(glTexSubImage3D) X(glTexParameteri) X(glFramebufferTexture2D) \
	X(glGenBuffers) X(glDeleteBuffers) X(glBindBuffer) X(glBufferData) X(glBufferSubData) \
	X(glGenVertexArrays) X(glDeleteVertexArrays) X(glBindVertexArray) \
	X(glCreateShader) X(glShaderSource) X(glCompileShader) X(glGetShaderiv) X(glGetShaderInfoLog) X(glDeleteShader) \
	X(glCreateProgram) X(glAttachShader) X(glBindAttribLocation) X(glBindFragDataLocation) X(glLinkProgram) X(glGetProgramiv) X(glGetProgramInfoLog) X(glDeleteProgram) \
	X(glUseProgram) X(glGetUniformLocation) X(glUniform4f) X(glUniform2f) X(glUniform1f) X(glUniform1i) X(glUniformMatrix4fv) \
	X(glEnableVertexAttribArray) X(glVertexAttribPointer) X(glVertexAttribIPointer) X(glViewport) X(glDisable) X(glEnable) \
	X(glClearColor) X(glClearDepth) X(glClear) X(glDepthFunc) X(glDepthMask) X(glColorMaski) X(glCullFace) \
	X(glDrawArrays) X(glDrawArraysInstanced) X(glDrawElementsInstanced) X(glTexBuffer) X(glDrawBuffers) X(glReadBuffer) X(glClearBufferuiv) X(glReadPixels) X(glPixelStorei) X(glActiveTexture)

#define R3D_GL_PRESENT_FUNCTIONS(X) \
	X(glFenceSync) X(glWaitSync) X(glClientWaitSync) X(glDeleteSync) X(glFlush) X(glBlendFuncSeparate) X(glBlendEquationSeparate) X(glScissor)

#define DECLARE_GL(name) static decltype(&name) r_##name = nullptr;
R3D_GL_FUNCTIONS(DECLARE_GL)
R3D_GL_PRESENT_FUNCTIONS(DECLARE_GL)
#undef DECLARE_GL

static GLuint program = 0, vertex_array = 0, vertex_buffer = 0;
static GLuint visible_program = 0, visible_vertex_array = 0;
static GLint maximum_buffer_texels = 0, subpixel_precision = 0;
static GLuint atlas_colour = 0, atlas_remap = 0;
struct TextureBuffer {
	GLuint buffer = 0, texture = 0;
	size_t capacity = 0;
	void Destroy()
	{
		if (texture) r_glDeleteTextures(1,&texture);
		if (buffer) r_glDeleteBuffers(1,&buffer);
		buffer = texture = 0; capacity = 0;
	}
	void Upload(GLenum format, const void *data, size_t bytes)
	{
		/* A new object preserves queued readers. OpenGL defers deletion until
		 * submitted draws stop referencing the old texture/buffer storage. */
		Destroy();
		r_glGenBuffers(1,&buffer); r_glBindBuffer(GL_ARRAY_BUFFER,buffer);
		r_glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(bytes),data,GL_STATIC_DRAW);
		r_glGenTextures(1,&texture); r_glBindTexture(GL_TEXTURE_BUFFER,texture);
		r_glTexBuffer(GL_TEXTURE_BUFFER,format,buffer);
		capacity = bytes;
	}
	void Update(GLenum format, const void *data, size_t bytes)
	{
		/* Frame slots reuse their completed storage. Replacing a large texture
		 * buffer every frame caused sustained driver memory growth on Apple GL. */
		if (!buffer) r_glGenBuffers(1,&buffer);
		r_glBindBuffer(GL_ARRAY_BUFFER,buffer);
		bool resized = bytes > capacity || capacity == 0;
		if (resized) {
			capacity = (std::max<size_t>({16,bytes,capacity+capacity/2})+15)/16*16;
			r_glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(capacity),nullptr,GL_DYNAMIC_DRAW);
		}
		if (bytes != 0) r_glBufferSubData(GL_ARRAY_BUFFER,0,static_cast<GLsizeiptr>(bytes),data);
		if (!texture) r_glGenTextures(1,&texture);
		r_glBindTexture(GL_TEXTURE_BUFFER,texture);
		if (resized) r_glTexBuffer(GL_TEXTURE_BUFFER,format,buffer);
	}
};
static std::array<TextureBuffer,2> instance_frames;
struct VisibleMeshBuffer { PackedVoxelLookup lookup; TextureBuffer format; };
static std::unordered_map<const PackedVoxelMesh *,VisibleMeshBuffer> visible_meshes;
struct MeshBuffer {
	GLuint vao = 0, buffer = 0, indices = 0;
	GLenum index_type = GL_UNSIGNED_INT;
	size_t bytes = 0;
	uint64_t last_use = 0;
	void Destroy() const
	{
		r_glDeleteVertexArrays(1,&vao);
		r_glDeleteBuffers(1,&buffer);
		if (indices != 0) r_glDeleteBuffers(1,&indices);
	}
};
using MeshBuffers = std::unordered_map<const std::vector<Vertex> *,MeshBuffer>;
static MeshBuffers meshes;
static uint64_t mesh_generation = 0;

void TrimMeshCache(uint64_t budget)
{
	if (Vulkan::Active()) { Vulkan::TrimMeshCache(budget); return; }
	uint64_t bytes = 0;
	std::vector<MeshBuffers::iterator> cold;
	for (auto entry = meshes.begin(); entry != meshes.end(); ++entry) {
		bytes += entry->second.bytes;
		if (entry->second.last_use != mesh_generation) cold.push_back(entry);
	}
	if (bytes <= budget) return;
	std::ranges::sort(cold,[](const auto &a,const auto &b) { return a->second.last_use < b->second.last_use; });
	uint64_t retired = 0;
	for (auto entry : cold) {
		if (bytes <= budget) break;
		bytes -= entry->second.bytes; retired += entry->second.bytes;
		/* GL retains storage referenced by queued commands until their completion. */
		entry->second.Destroy(); meshes.erase(entry);
	}
	if (retired != 0) Debug(driver,2,"OpenTT3D: retired {} cold OpenGL mesh bytes; {} resident bytes / {} meshes",retired,bytes,meshes.size());
}
struct TransientMeshBuffers {
	MeshBuffers buffers;
	~TransientMeshBuffers() { for (const auto &[mesh,buffer] : buffers) buffer.Destroy(); }
};
static InstanceBatcher instance_staging;
struct InstanceBatch {
	const std::vector<Vertex> *mesh; GLuint vao; GLint first; GLsizei count;
	bool indexed, cull_back, transparent, both_passes; GLenum index_type;
	const PackedVoxelMesh *packed = nullptr;
	const VisibleMeshBuffer *visible = nullptr;
	GLuint vertices = 0, indices = 0;
};
static std::vector<InstanceBatch> instance_batches;
static bool functions_loaded = false, initialization_failed = false;
struct Target {
	GLuint framebuffer = 0, depth = 0, colour = 0, picking = 0;
	int width = 0, height = 0;
	VoxelVisibilityCache visibility;
	std::unique_ptr<VoxelVisibilityWorker> visibility_worker;
	struct VisibleChunk { TextureBuffer storage; GLuint indices = 0; GLsizei count = 0; };
	struct VisiblePage {
		std::vector<std::array<uint32_t,7>> transforms;
		std::vector<VisibleChunk> chunks;
		size_t triangles = 0, vertices = 0;
		~VisiblePage() { for (auto &chunk : chunks) { chunk.storage.Destroy(); if (chunk.indices) r_glDeleteBuffers(1,&chunk.indices); } }
	};
	struct VisibleStream {
		struct Geometry { std::vector<uint32_t> vertices, indices; uint64_t used = 0; };
		struct Page { size_t first; std::shared_ptr<VisiblePage> storage; };
		std::vector<std::array<uint32_t,7>> transforms;
		std::vector<Page> pages;
		std::map<std::array<uint32_t,7>,Geometry> geometry;
		uint64_t generation = 0;
		size_t triangles = 0, vertices = 0;
		void Clear() { pages.clear(); }
	};
	std::array<std::unordered_map<const std::vector<Vertex> *,VisibleStream>,2> visible_streams;
	bool visibility_reported = false;
	std::chrono::steady_clock::time_point memory_reported{};
	void ClearVisibility()
	{
		for (auto &layer : visible_streams) {
			for (auto &[mesh,stream] : layer) stream.Clear();
			layer.clear();
		}
	}
	void Destroy()
	{
		visibility_worker.reset(); ClearVisibility();
		if (framebuffer) r_glDeleteFramebuffers(1,&framebuffer);
		if (depth) r_glDeleteRenderbuffers(1,&depth);
		if (colour) r_glDeleteTextures(1,&colour);
		if (picking) r_glDeleteTextures(1,&picking);
		*this = {};
	}
};
static Target readback_target, presentation_target;
static std::map<const void *,Target> viewport_targets;
struct Region { const void *key; int sx, sy, width, height, dx, dy; };
static std::vector<Region> regions;
static GLuint composite_program = 0, composite_vao = 0;
static GLuint prepared_texture = 0;
static GLsync presentation_ready = nullptr, presentation_consumed = nullptr;
static std::array<GLsync,2> frame_complete{};
static std::array<GLsync,2> frame_consumed{};
struct PaletteTexture { GLuint name = 0; std::array<Colour,256> colours{}; bool valid = false; };
static std::array<PaletteTexture,2> frame_palettes;
static unsigned frame_slot = 0;
static unsigned prepared_slot = 0;
static OpenGL::PresentationCapture presentation_capture;

bool HasOpenGLBackend()
{
	return OpenGLBackend::Get() != nullptr && IsOpenGLVersionAtLeast(3, 2) && !initialization_failed;
}

std::string BackendDescription()
{
	if (Vulkan::Active()) return Vulkan::Description();
	return HasOpenGLBackend() ? "OpenGL: " + OpenGLBackend::Get()->GetDriverName() : "unavailable";
}

size_t PersistentMeshCount()
{
	return Vulkan::Active() ? Vulkan::GetMeshCacheStats().meshes : meshes.size();
}

static bool LoadFunctions()
{
	if (functions_loaded) return true;
#define LOAD_GL(name) \
	r_##name = reinterpret_cast<decltype(r_##name)>(GetOGLProcAddress(#name)); \
	if (r_##name == nullptr) { Debug(driver, 0, "OpenTT3D: missing OpenGL function " #name); return false; }
	R3D_GL_FUNCTIONS(LOAD_GL)
	R3D_GL_PRESENT_FUNCTIONS(LOAD_GL)
#undef LOAD_GL
	functions_loaded = true;
	return true;
}

int MaximumFramebufferSize()
{
	if (Vulkan::Active()) return Vulkan::MaximumImageSize();
	if (!HasOpenGLBackend() || !LoadFunctions()) return 0;
	GLint texture_limit = 0, renderbuffer_limit = 0, viewport_limit[2]{};
	r_glGetIntegerv(GL_MAX_TEXTURE_SIZE, &texture_limit);
	r_glGetIntegerv(GL_MAX_RENDERBUFFER_SIZE, &renderbuffer_limit);
	r_glGetIntegerv(GL_MAX_VIEWPORT_DIMS, viewport_limit);
	return std::min({texture_limit, renderbuffer_limit, viewport_limit[0], viewport_limit[1]});
}

/** The upstream driver keeps a mapped pixel-unpack buffer and several GL bindings. */
struct StateGuard {
	GLint draw_fbo, read_fbo, renderbuffer, vao, array_buffer, pack_buffer, unpack_buffer;
	GLint active_texture, texture_1d[6], texture_2d[6], texture_array[6], texture_buffer[6], old_program, viewport[4], depth_func, cull_mode;
	int texture_units = VoxelPixelCullEnabled() ? 6 : 4;
	GLint blend_src_rgb, blend_dst_rgb, blend_src_alpha, blend_dst_alpha, blend_equation_rgb, blend_equation_alpha;
	GLint scissor_box[4];
	GLint pack_alignment, pack_row_length, pack_skip_rows, pack_skip_pixels, unpack_alignment, unpack_row_length;
	GLfloat clear_colour[4], clear_depth;
	GLboolean depth_mask, colour_mask[4], id_mask[4], depth_test, blend, cull, scissor, srgb, primitive_restart;

	StateGuard()
	{
		r_glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw_fbo);
		r_glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read_fbo);
		r_glGetIntegerv(GL_RENDERBUFFER_BINDING, &renderbuffer);
		r_glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
		r_glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &array_buffer);
		r_glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &pack_buffer);
		r_glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING, &unpack_buffer);
		r_glGetIntegerv(GL_ACTIVE_TEXTURE, &active_texture);
		for (int unit = 0; unit < texture_units; ++unit) {
			r_glActiveTexture(GL_TEXTURE0 + unit);
			r_glGetIntegerv(GL_TEXTURE_BINDING_1D, &texture_1d[unit]);
			r_glGetIntegerv(GL_TEXTURE_BINDING_2D, &texture_2d[unit]);
			r_glGetIntegerv(GL_TEXTURE_BINDING_2D_ARRAY, &texture_array[unit]);
			r_glGetIntegerv(GL_TEXTURE_BINDING_BUFFER, &texture_buffer[unit]);
		}
		r_glActiveTexture(GL_TEXTURE0);
		r_glGetIntegerv(GL_CURRENT_PROGRAM, &old_program);
		r_glGetIntegerv(GL_VIEWPORT, viewport);
		r_glGetIntegerv(GL_SCISSOR_BOX,scissor_box);
		r_glGetIntegerv(GL_DEPTH_FUNC, &depth_func);
		r_glGetIntegerv(GL_CULL_FACE_MODE,&cull_mode);
		r_glGetIntegerv(GL_BLEND_SRC_RGB,&blend_src_rgb); r_glGetIntegerv(GL_BLEND_DST_RGB,&blend_dst_rgb);
		r_glGetIntegerv(GL_BLEND_SRC_ALPHA,&blend_src_alpha); r_glGetIntegerv(GL_BLEND_DST_ALPHA,&blend_dst_alpha);
		r_glGetIntegerv(GL_BLEND_EQUATION_RGB,&blend_equation_rgb); r_glGetIntegerv(GL_BLEND_EQUATION_ALPHA,&blend_equation_alpha);
		r_glGetIntegerv(GL_PACK_ALIGNMENT, &pack_alignment);
		r_glGetIntegerv(GL_PACK_ROW_LENGTH, &pack_row_length);
		r_glGetIntegerv(GL_PACK_SKIP_ROWS, &pack_skip_rows);
		r_glGetIntegerv(GL_PACK_SKIP_PIXELS, &pack_skip_pixels);
		r_glGetIntegerv(GL_UNPACK_ALIGNMENT, &unpack_alignment);
		r_glGetIntegerv(GL_UNPACK_ROW_LENGTH, &unpack_row_length);
		r_glGetFloatv(GL_COLOR_CLEAR_VALUE, clear_colour);
		r_glGetFloatv(GL_DEPTH_CLEAR_VALUE, &clear_depth);
		r_glGetBooleanv(GL_DEPTH_WRITEMASK, &depth_mask);
		r_glGetBooleanv(GL_COLOR_WRITEMASK, colour_mask);
		r_glGetBooleani_v(GL_COLOR_WRITEMASK,1,id_mask);
		depth_test = r_glIsEnabled(GL_DEPTH_TEST);
		blend = r_glIsEnabled(GL_BLEND);
		cull = r_glIsEnabled(GL_CULL_FACE);
		scissor = r_glIsEnabled(GL_SCISSOR_TEST);
		srgb = r_glIsEnabled(GL_FRAMEBUFFER_SRGB);
		primitive_restart = r_glIsEnabled(GL_PRIMITIVE_RESTART);
	}

	~StateGuard()
	{
		r_glBindFramebuffer(GL_DRAW_FRAMEBUFFER, draw_fbo);
		r_glBindFramebuffer(GL_READ_FRAMEBUFFER, read_fbo);
		r_glBindRenderbuffer(GL_RENDERBUFFER, renderbuffer);
		r_glBindVertexArray(vao);
		r_glBindBuffer(GL_ARRAY_BUFFER, array_buffer);
		r_glBindBuffer(GL_PIXEL_PACK_BUFFER, pack_buffer);
		r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER, unpack_buffer);
		for (int unit = 0; unit < texture_units; ++unit) {
			r_glActiveTexture(GL_TEXTURE0 + unit);
			r_glBindTexture(GL_TEXTURE_1D, texture_1d[unit]);
			r_glBindTexture(GL_TEXTURE_2D, texture_2d[unit]);
			r_glBindTexture(GL_TEXTURE_2D_ARRAY, texture_array[unit]);
			r_glBindTexture(GL_TEXTURE_BUFFER, texture_buffer[unit]);
		}
		r_glActiveTexture(active_texture);
		r_glUseProgram(old_program);
		r_glViewport(viewport[0], viewport[1], viewport[2], viewport[3]);
		r_glScissor(scissor_box[0],scissor_box[1],scissor_box[2],scissor_box[3]);
		r_glDepthFunc(depth_func);
		r_glCullFace(cull_mode);
		r_glBlendFuncSeparate(blend_src_rgb,blend_dst_rgb,blend_src_alpha,blend_dst_alpha);
		r_glBlendEquationSeparate(blend_equation_rgb,blend_equation_alpha);
		r_glDepthMask(depth_mask);
		r_glColorMaski(0,colour_mask[0], colour_mask[1], colour_mask[2], colour_mask[3]);
		r_glColorMaski(1,id_mask[0],id_mask[1],id_mask[2],id_mask[3]);
		r_glPixelStorei(GL_PACK_ALIGNMENT, pack_alignment);
		r_glPixelStorei(GL_PACK_ROW_LENGTH, pack_row_length);
		r_glPixelStorei(GL_PACK_SKIP_ROWS, pack_skip_rows);
		r_glPixelStorei(GL_PACK_SKIP_PIXELS, pack_skip_pixels);
		r_glPixelStorei(GL_UNPACK_ALIGNMENT, unpack_alignment);
		r_glPixelStorei(GL_UNPACK_ROW_LENGTH, unpack_row_length);
		r_glClearColor(clear_colour[0], clear_colour[1], clear_colour[2], clear_colour[3]);
		r_glClearDepth(clear_depth);
		Set(GL_DEPTH_TEST, depth_test); Set(GL_BLEND, blend); Set(GL_CULL_FACE, cull);
		Set(GL_SCISSOR_TEST, scissor); Set(GL_FRAMEBUFFER_SRGB, srgb);
		Set(GL_PRIMITIVE_RESTART,primitive_restart);
	}

	static void Set(GLenum state, bool enabled) { if (enabled) r_glEnable(state); else r_glDisable(state); }
};

static GLuint Compile(GLenum type, const char *source)
{
	GLuint shader = r_glCreateShader(type);
	r_glShaderSource(shader, 1, &source, nullptr);
	r_glCompileShader(shader);
	GLint success = 0;
	r_glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
	if (success) return shader;
	char log[2048]{};
	r_glGetShaderInfoLog(shader, sizeof(log), nullptr, log);
	Debug(driver, 0, "OpenTT3D shader: {}", log);
	r_glDeleteShader(shader);
	return 0;
}

static bool Initialize()
{
	if (program != 0) return true;
	/* Apple's CPU rasterizer can drop perspective triangles crossing several clip
	 * planes (including positive-W triangles). Clip them explicitly before they
	 * reach that rasterizer; keep the original homogeneous W and interpolants. */
	bool software_clip = OpenGLBackend::Get()->GetDriverName().find("Apple Software Renderer") != std::string::npos;
	if (const char *value = std::getenv("OPENTT3D_GL_SOFTWARE_CLIP")) software_clip = std::string_view(value) == "1";
	const char *vertex_source = R"GLSL(#version 150
#ifdef SOFTWARE_CLIP
#define lit_colour clip_lit_colour
#define uv_page clip_uv_page
#define alpha clip_alpha
#define uv_region clip_uv_region
#define material_surface clip_material_surface
#define pick_id clip_pick_id
#endif
#ifdef GL_ARB_gpu_shader5
#extension GL_ARB_gpu_shader5 : enable
#define ROTATION_PRECISE precise
#else
#define ROTATION_PRECISE
#endif
#ifdef VOXEL_VISIBLE
uniform usamplerBuffer voxel_vertices;
uniform samplerBuffer voxel_format;
uniform vec4 voxel_bits;
#else
in vec3 position;
in vec3 normal;
in vec3 colour;
in vec3 texture_coord;
in float opacity;
in vec4 texture_region;
in uint surface_mode;
in uint object_id;
#endif
uniform vec4 camera;
uniform mat4 view_projection;
uniform samplerBuffer instance_data;
uniform int instanced;
uniform int instance_base;
out vec3 lit_colour;
out vec3 uv_page;
out float alpha;
flat out vec4 uv_region;
flat out uint material_surface;
flat out uint pick_id;
vec2 canonical_rotate(vec2 value, float cs, float sn) {
    // A precise matrix multiply can still fuse its internal dot products on
    // Apple's GL driver. Explicit products retain the CPU reference rounding.
    ROTATION_PRECISE vec2 products = value * cs;
    ROTATION_PRECISE vec2 cross_products = value.yx * sn;
    ROTATION_PRECISE vec2 result = vec2(products.x - cross_products.x, cross_products.y + products.y);
    return result;
}
vec2 canonical_pitch(vec2 value, vec3 pitch) {
    ROTATION_PRECISE vec2 products = value * pitch.x;
    ROTATION_PRECISE vec2 cross_products = value.yx * pitch.zy;
    ROTATION_PRECISE vec2 result = vec2(products.x - cross_products.x, cross_products.y + products.y);
    return result;
}
void main() {
#ifdef VOXEL_VISIBLE
    uvec2 reference = texelFetch(voxel_vertices, gl_VertexID).xy;
    uint encoded = reference.x;
    uvec4 widths = uvec4(voxel_bits);
    uvec3 coordinate = uvec3(encoded & ((1u << widths.x) - 1u),
        (encoded >> widths.x) & ((1u << widths.y) - 1u),
        (encoded >> (widths.x + widths.y)) & ((1u << widths.z) - 1u));
    uint normal_shift = widths.x + widths.y + widths.z;
    uint normal_index = (encoded >> normal_shift) & ((1u << widths.w) - 1u);
    // CPU qualification proves every product exact, including its decoded word.
    // Float texture-buffer views preserve the original origin/step/normal bits
    // without requiring post-GL3.2 shader bit-encoding extensions.
    vec3 position = vec3(coordinate) * texelFetch(voxel_format, 1).xyz + texelFetch(voxel_format, 0).xyz;
    vec3 normal = texelFetch(voxel_format, 6 + int(normal_index)).xyz;
    vec3 colour = vec3(1.0);
    vec3 texture_coord = vec3((float(encoded >> (normal_shift + widths.w)) + 0.5) / 256.0, 0.5, -3.0);
    float opacity = 1.0;
    vec4 texture_region = vec4(0.0, 0.0, 1.0, 1.0);
    uint surface_mode = 69u, object_id = 0u;
    int instance_index = int(reference.y);
#else
    int instance_index = gl_InstanceID;
#endif
    vec3 p = position;
    vec3 n = normal;
    vec3 uv = texture_coord;
    uint surface_value = surface_mode & ~16u;
    if (uv.z >= 0.0 && (surface_value & 15u) != 2u && (surface_value & 15u) != 4u && (surface_mode & 16u) == 0u) uv.xy -= texture_region.xy;
    float opacity_value = opacity;
    vec4 region = texture_region;
    uint object_value = object_id;
    if (instanced != 0) {
        int base = (instance_base + instance_index) * 7;
        vec4 origin = texelFetch(instance_data, base);
        vec4 scale_center = texelFetch(instance_data, base + 1);
        vec4 mirror = texelFetch(instance_data, base + 2);
        vec4 transform = texelFetch(instance_data, base + 3);
        region = texelFetch(instance_data, base + 4);
        vec4 identity = texelFetch(instance_data, base + 5);
        vec4 pitch = texelFetch(instance_data, base + 6);
        vec3 local = vec3((position.xy - scale_center.zw) * scale_center.x, position.z * scale_center.y);
        n = normalize(normal / vec3(scale_center.x, scale_center.x, scale_center.y));
        bool longitudinal = (uint(identity.z) & 16u) != 0u;
        if (longitudinal) {
            local.x *= mirror.z;
            n = normalize(n / vec3(mirror.z, 1.0, 1.0));
        }
        bool authored_sample = identity.w > 1.5 && texture_coord.z >= 0.0;
        vec3 sample_position = authored_sample ? texture_coord : position;
        if (!authored_sample && (uint(identity.z) & 1u) == 0u && dot(n, vec3(1.0, 1.0, 2.0)) < -0.001) {
            if (n.x < -0.1) sample_position.x = mirror.x - sample_position.x;
            if (n.y < -0.1) sample_position.y = mirror.y - sample_position.y;
        }
        sample_position = vec3((sample_position.xy - scale_center.zw) * scale_center.x, sample_position.z * scale_center.y);
        if (longitudinal) sample_position.x *= mirror.z;
        if (pitch.y != 0.0) {
            local.xz = canonical_pitch(local.xz - vec2(0.0, pitch.w), pitch.xyz) + vec2(0.0, pitch.w);
            sample_position.xz = canonical_pitch(sample_position.xz - vec2(0.0, pitch.w), pitch.xyz) + vec2(0.0, pitch.w);
            n.xz = canonical_pitch(n.xz, pitch.xzy);
            n = normalize(n);
        }
        bool canonical_yaw = (uint(identity.z) & 8u) != 0u;
        float cs = canonical_yaw ? mirror.x : cos(mirror.w);
        float sn = canonical_yaw ? mirror.y : sin(mirror.w);
        mat2 yaw = mat2(cs, sn, -sn, cs);
        if (canonical_yaw) {
            local.xy = canonical_rotate(local.xy, cs, sn);
            n.xy = canonical_rotate(n.xy, cs, sn);
            sample_position.xy = canonical_rotate(sample_position.xy, cs, sn);
        } else {
            local.xy = yaw * local.xy;
            n.xy = yaw * n.xy;
            sample_position.xy = yaw * sample_position.xy;
        }
        p = origin.xyz + local + n * (longitudinal ? 0.0 : mirror.z);
        bool local_bias = (uint(identity.z) & 32u) != 0u;
        vec2 bias = transform.xy - (local_bias || uint(identity.y + 0.5) == 2u ? vec2(0) : region.xy);
        uv = vec3(bias + vec2(2.0 * (sample_position.y - sample_position.x), sample_position.x + sample_position.y - sample_position.z) * transform.z, transform.w);
        if (identity.w > 0.5 && identity.w < 1.5) uv = vec3(bias + texture_coord.xy * transform.z, transform.w);
        if (identity.w > 1.5 && texture_coord.z < -2.5) uv = vec3(texture_coord.xy * (region.zw - region.xy), transform.w);
        if (identity.w > 2.5) uv = vec3(texture_coord.xy, transform.w);
        if (identity.w > 3.5) uv.xy *= transform.xy;
        opacity_value = origin.w;
        object_value = uint(identity.x) | ((uint(identity.z) & 2u) != 0u ? 0x80000000u : 0u);
        if (texture_coord.z < -3.5) uv.z = -1;
        surface_value = uint(identity.y + 0.5) | (surface_mode & 96u);
    }
    gl_Position = view_projection * vec4(p - camera.xyz, 1.0);
    if ((surface_value & 15u) == 2u) {
        float finite_point = texture_coord.z < -1.5 ? 0.0 : 1.0;
        gl_Position = view_projection * vec4(p - camera.xyz * finite_point, finite_point);
        uv = vec3(texture_coord.xy, finite_point);
    }
    vec3 lighting_normal = (surface_value & 32u) != 0u ? vec3(n.xy, n.z / 0.408248290463863) : n;
    float light = 0.66 + 0.34 * max(dot(normalize(lighting_normal), normalize(vec3(-0.45, -0.65, 1.0))), 0.0);
    if ((surface_value & 32u) != 0u) light /= 0.66 + 0.34 * normalize(vec3(-0.45, -0.65, 1.0)).z;
    if ((surface_value & 64u) != 0u) light = 1.0;
    if ((surface_value & 15u) == 5u) surface_value |= uint(floor(uv.x * 1024.0 + 0.0001)) << 8;
    lit_colour = colour * light;
    uv_page = uv;
    alpha = opacity_value;
    uv_region = region;
    material_surface = surface_value;
    pick_id = object_value;
}
)GLSL";
	const char *fragment_source = R"GLSL(#version 150
in vec3 lit_colour;
in vec3 uv_page;
in float alpha;
flat in vec4 uv_region;
flat in uint material_surface;
flat in uint pick_id;
uniform sampler2DArray colour_atlas;
uniform sampler2DArray remap_atlas;
uniform sampler2D palette;
uniform int transparent_pass;
uniform vec4 water_material;
uniform vec4 camera;
out vec4 output_colour;
out uint output_id;
void main() {
    uint surface = material_surface & 15u;
    if (surface == 5u && !gl_FrontFacing) discard;
    if ((alpha < 0.99) != (transparent_pass != 0)) discard;
    vec4 colour = vec4(lit_colour, alpha);
    // Explicit reversed depth avoids OpenGL's [-1,1] to [0,1] cancellation at long range.
    gl_FragDepth = camera.w * gl_FragCoord.w * (surface == 2u ? uv_page.z : 1.0);
    if (uv_page.z >= 0.0) {
        vec3 uv = uv_page;
        if (surface == 2u) {
            vec2 cell = fract(uv.xy / max(uv.z, 1e-20)) * 16.0;
            uv.z = water_material.z;
            uv.xy = water_material.xy - uv_region.xy + vec2(2.0 * (cell.y - cell.x), cell.x + cell.y) * water_material.w;
        }
        vec2 extent = (uv_region.zw - uv_region.xy) * 1024.0;
        vec2 local = surface == 4u ? fract(uv.xy) * extent : uv.xy * 1024.0;
        if (surface == 5u) local = vec2(float((material_surface >> 8) & 255u) + 0.5, 0.5);
        if (surface == 0u && (local.x < 0.0 || local.y < 0.0 || local.x >= extent.x || local.y >= extent.y)) discard;
        // Interpolate sprite-local UVs; integer atlas offsets must not change nearest-texel ties.
        ivec2 texel = clamp(ivec2(floor(local + 0.0001)), ivec2(0), ivec2(extent + 0.5) - 1) + ivec2(uv_region.xy * 1024.0 + 0.5);
        ivec3 address = ivec3(texel, int(uv.z + 0.5));
        colour = texelFetch(colour_atlas, address, 0);
        vec2 remap = floor(texelFetch(remap_atlas, address, 0).rg * 255.0 + 0.5);
        if (remap.x > 0.0) {
            vec3 rgb = floor(texture(palette, vec2((remap.x + 0.5) / 256.0, 0.5)).rgb * 255.0 + 0.5);
            rgb = floor(rgb * remap.y / 128.0);
            vec3 excess = max(rgb - 255.0, vec3(0));
            float overbright = floor((excess.r + excess.g + excess.b) / 2.0);
            colour.rgb = min(rgb + floor(overbright * max(vec3(255.0) - rgb, vec3(0)) / 256.0), vec3(255.0)) / 255.0;
        }
        if ((material_surface & 32u) != 0u) colour.rgb *= lit_colour;
        colour.a *= alpha;
    }
    if (colour.a < 0.01) discard;
    if (surface == 3u) colour.rgb = vec3(0);
    output_colour = colour;
    output_id = pick_id;
}
)GLSL";
	const char *geometry_source = R"GLSL(#version 150
layout(triangles) in;
layout(triangle_strip, max_vertices = 21) out;
in vec3 clip_lit_colour[];
in vec3 clip_uv_page[];
in float clip_alpha[];
flat in vec4 clip_uv_region[];
flat in uint clip_material_surface[];
flat in uint clip_pick_id[];
out vec3 lit_colour;
out vec3 uv_page;
out float alpha;
flat out vec4 uv_region;
flat out uint material_surface;
flat out uint pick_id;
struct ClipVertex { vec4 position; vec3 colour; vec3 uv; float opacity; };
ClipVertex polygon[12];
ClipVertex temporary[12];
float plane_distance(vec4 p, int plane) {
    if (plane == 0) return p.w + p.x;
    if (plane == 1) return p.w - p.x;
    if (plane == 2) return p.w + p.y;
    if (plane == 3) return p.w - p.y;
    if (plane == 4) return p.w + p.z;
    return p.w - p.z;
}
ClipVertex interpolate(ClipVertex a, ClipVertex b, float t) {
    return ClipVertex(mix(a.position,b.position,t),mix(a.colour,b.colour,t),mix(a.uv,b.uv,t),mix(a.opacity,b.opacity,t));
}
void emit_vertex(int i) {
    vec4 p = polygon[i].position;
    // Round an intersection onto its clip plane, rather than outside it.
    gl_Position = vec4(clamp(p.xyz,vec3(-p.w),vec3(p.w)),p.w);
    lit_colour = polygon[i].colour;
    uv_page = polygon[i].uv;
    alpha = polygon[i].opacity;
    // Preserve the original provoking vertex, including complete picking IDs.
    uv_region = clip_uv_region[2];
    material_surface = clip_material_surface[2];
    pick_id = clip_pick_id[2];
    EmitVertex();
}
void main() {
    for (int i=0;i<3;++i) polygon[i] = ClipVertex(gl_in[i].gl_Position,clip_lit_colour[i],clip_uv_page[i],clip_alpha[i]);
    int count = 3;
    for (int plane=0;plane<6;++plane) {
        int size = 0;
        ClipVertex previous = polygon[count-1];
        float previous_distance = plane_distance(previous.position,plane);
        for (int i=0;i<count;++i) {
            ClipVertex current = polygon[i];
            float distance = plane_distance(current.position,plane);
            if ((distance >= 0.0) != (previous_distance >= 0.0)) {
                temporary[size++] = interpolate(previous,current,previous_distance/(previous_distance-distance));
            }
            if (distance >= 0.0) temporary[size++] = current;
            previous = current;
            previous_distance = distance;
        }
        if (size < 3) return;
        count = size;
        for (int i=0;i<count;++i) polygon[i] = temporary[i];
    }
    // Six clipping planes can increase a triangle to at most nine vertices.
    for (int i=1;i<count-1;++i) {
        emit_vertex(0);emit_vertex(i);emit_vertex(i+1);EndPrimitive();
    }
}
)GLSL";
	std::string source(vertex_source);
	if (software_clip) source.insert(source.find('\n')+1,"#define SOFTWARE_CLIP\n");
	GLuint vertex = Compile(GL_VERTEX_SHADER, source.c_str());
	GLuint fragment = Compile(GL_FRAGMENT_SHADER, fragment_source);
	GLuint geometry = software_clip ? Compile(GL_GEOMETRY_SHADER,geometry_source) : 0;
	if (!vertex || !fragment || (software_clip && !geometry)) {
		r_glDeleteShader(vertex); r_glDeleteShader(fragment); r_glDeleteShader(geometry);
		return false;
	}
	program = r_glCreateProgram();
	r_glAttachShader(program, vertex); r_glAttachShader(program, fragment);
	if (geometry != 0) r_glAttachShader(program,geometry);
	r_glBindAttribLocation(program, 0, "position");
	r_glBindAttribLocation(program, 1, "normal");
	r_glBindAttribLocation(program, 2, "colour");
	r_glBindAttribLocation(program, 3, "texture_coord");
	r_glBindAttribLocation(program, 4, "opacity");
	r_glBindAttribLocation(program, 5, "texture_region");
	r_glBindAttribLocation(program, 6, "surface_mode");
	r_glBindAttribLocation(program, 7, "object_id");
	r_glBindFragDataLocation(program, 0, "output_colour");
	r_glBindFragDataLocation(program, 1, "output_id");
	r_glLinkProgram(program);
	r_glDeleteShader(vertex);
	GLint success = 0;
	r_glGetProgramiv(program, GL_LINK_STATUS, &success);
	if (!success) {
		char log[2048]{};
		r_glGetProgramInfoLog(program, sizeof(log), nullptr, log);
		Debug(driver, 0, "OpenTT3D program: {}", log);
		r_glDeleteProgram(program); program = 0;
		r_glDeleteShader(fragment);
		r_glDeleteShader(geometry);
		return false;
	}
	if (VoxelPixelCullEnabled()) {
		source.insert(source.find('\n')+1,"#define VOXEL_VISIBLE\n");
		GLuint visible_vertex = Compile(GL_VERTEX_SHADER,source.c_str());
		if (!visible_vertex) { r_glDeleteShader(fragment); r_glDeleteShader(geometry); return false; }
		visible_program = r_glCreateProgram();
		r_glAttachShader(visible_program,visible_vertex); r_glAttachShader(visible_program,fragment);
		if (geometry != 0) r_glAttachShader(visible_program,geometry);
		r_glBindFragDataLocation(visible_program,0,"output_colour");
		r_glBindFragDataLocation(visible_program,1,"output_id");
		r_glLinkProgram(visible_program); r_glDeleteShader(visible_vertex);
		r_glGetProgramiv(visible_program,GL_LINK_STATUS,&success);
		if (!success) {
			char log[2048]{}; r_glGetProgramInfoLog(visible_program,sizeof(log),nullptr,log);
			Debug(driver,0,"OpenTT3D visible voxel program: {}",log);
			r_glDeleteShader(fragment); r_glDeleteShader(geometry); return false;
		}
		r_glGenVertexArrays(1,&visible_vertex_array);
		r_glGetIntegerv(GL_MAX_TEXTURE_BUFFER_SIZE,&maximum_buffer_texels);
		r_glGetIntegerv(GL_SUBPIXEL_BITS,&subpixel_precision);
		Debug(driver,1,"OpenTT3D: OpenGL exact voxel visibility enabled, {} buffer texels / {} subpixel bits",maximum_buffer_texels,subpixel_precision);
	}
	r_glDeleteShader(fragment);
	r_glDeleteShader(geometry);
	if (software_clip) Debug(driver,1,"OpenTT3D: explicit homogeneous clipping enabled for OpenGL software rasterization");
	r_glGenVertexArrays(1, &vertex_array);
	r_glGenBuffers(1, &vertex_buffer);
	r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0);
	r_glGenTextures(1, &atlas_colour); r_glGenTextures(1, &atlas_remap);
	for (auto [texture, format, channels] : {std::tuple{atlas_colour, GL_RGBA8, GL_RGBA}, std::tuple{atlas_remap, GL_RG8, GL_RG}}) {
		r_glBindTexture(GL_TEXTURE_2D_ARRAY, texture);
		r_glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
		r_glTexParameteri(GL_TEXTURE_2D_ARRAY, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
		r_glTexImage3D(GL_TEXTURE_2D_ARRAY, 0, format, ATLAS_SIZE, ATLAS_SIZE, ATLAS_PAGES, 0, channels, GL_UNSIGNED_BYTE, nullptr);
	}
	for (auto &palette : frame_palettes) {
		r_glGenTextures(1,&palette.name);
		r_glBindTexture(GL_TEXTURE_2D,palette.name);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
		r_glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,256,1,0,GL_BGRA,GL_UNSIGNED_INT_8_8_8_8_REV,nullptr);
	}
	Textures().MarkAllDirty();
	Debug(driver, 1, "OpenTT3D: depth-tested mesh renderer initialized");
	return true;
}

static void VertexLayout()
{
	for (GLuint attribute = 0; attribute < 8; ++attribute) r_glEnableVertexAttribArray(attribute);
	r_glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, position)));
	r_glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, normal)));
	r_glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, colour)));
	r_glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, texture)));
	r_glVertexAttribPointer(4, 1, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, opacity)));
	r_glVertexAttribPointer(5, 4, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, texture_region)));
	r_glVertexAttribIPointer(6, 1, GL_UNSIGNED_INT, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, surface)));
	r_glVertexAttribIPointer(7, 1, GL_UNSIGNED_INT, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, object_id)));
}

static const MeshBuffer &GetMesh(const std::vector<Vertex> *mesh, MeshBuffers &storage)
{
	auto [found, inserted] = storage.try_emplace(mesh);
	if (inserted) {
		Profile::Scope upload_time(Profile::Section::MeshUpload);
		IndexedMesh indexed;
		std::vector<uint16_t> short_indices;
		if (IndexImmutableMeshes()) { Profile::Scope timing(Profile::Section::MeshIndex); indexed = IndexMesh(*mesh); short_indices = indexed.ShortIndices(); }
		const auto &data = indexed.indices.empty() ? *mesh : indexed.vertices;
		size_t index_bytes = short_indices.empty() ? indexed.indices.size()*sizeof(uint32_t) : short_indices.size()*sizeof(uint16_t);
		r_glGenVertexArrays(1, &found->second.vao);
		r_glGenBuffers(1, &found->second.buffer);
		r_glBindVertexArray(found->second.vao);
		r_glBindBuffer(GL_ARRAY_BUFFER, found->second.buffer);
		r_glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(data.size()*sizeof(Vertex)),data.data(),GL_STATIC_DRAW);
		VertexLayout();
		if (!indexed.indices.empty()) {
			r_glGenBuffers(1,&found->second.indices);
			r_glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,found->second.indices);
			found->second.index_type = short_indices.empty() ? GL_UNSIGNED_INT : GL_UNSIGNED_SHORT;
			r_glBufferData(GL_ELEMENT_ARRAY_BUFFER,static_cast<GLsizeiptr>(index_bytes),short_indices.empty() ? static_cast<const void *>(indexed.indices.data()) : short_indices.data(),GL_STATIC_DRAW);
		}
		Profile::AddMeshUpload(data.size()*sizeof(Vertex)+index_bytes);
		found->second.bytes = data.size()*sizeof(Vertex)+index_bytes;
	}
	found->second.last_use = mesh_generation;
	return found->second;
}

static bool EnsureTarget(Target &target, int width, int height, bool world)
{
	if (!target.framebuffer) r_glGenFramebuffers(1,&target.framebuffer);
	r_glBindFramebuffer(GL_FRAMEBUFFER,target.framebuffer);
	if (target.width == width && target.height == height) return true;
	r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
	r_glActiveTexture(GL_TEXTURE0);
	auto texture = [&](GLuint &name, GLenum format, GLenum channels, GLenum type, GLenum attachment) {
		if (!name) r_glGenTextures(1,&name);
		r_glBindTexture(GL_TEXTURE_2D,name);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
		r_glTexImage2D(GL_TEXTURE_2D,0,format,width,height,0,channels,type,nullptr);
		r_glFramebufferTexture2D(GL_FRAMEBUFFER,attachment,GL_TEXTURE_2D,name,0);
	};
	texture(target.colour,GL_RGBA8,GL_RGBA,GL_UNSIGNED_BYTE,GL_COLOR_ATTACHMENT0);
	if (world) {
		texture(target.picking,GL_R32UI,GL_RED_INTEGER,GL_UNSIGNED_INT,GL_COLOR_ATTACHMENT1);
		if (!target.depth) r_glGenRenderbuffers(1,&target.depth);
		r_glBindRenderbuffer(GL_RENDERBUFFER,target.depth);
		r_glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT32F,width,height);
		r_glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,target.depth);
	}
	const GLenum buffers[] = {GL_COLOR_ATTACHMENT0,GL_COLOR_ATTACHMENT1};
	r_glDrawBuffers(world ? 2 : 1,buffers);
	if (r_glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) return false;
	target.width = width; target.height = height;
	return true;
}

static bool RenderTarget(Target &target, const Scene &scene, const Camera &camera, std::vector<uint8_t> *pixels = nullptr, std::vector<uint32_t> *picking = nullptr, const Colour *colours = _cur_palette.palette)
{
	Profile::Scope backend_time(Profile::Section::Backend);
	Profile::AddGeometry(scene.VertexCount());
	if (!HasOpenGLBackend() || camera.width <= 0 || camera.height <= 0) return false;
	OpenGLBackend::Get()->ActivateRenderContext();
	if (!LoadFunctions()) { initialization_failed = true; return false; }
	/* Cocoa's backing context can have a pending error from presenting before its
	 * first drawable exists. Attribute only errors from this pass to this pass. */
	for (GLenum error = r_glGetError(); error != GL_NO_ERROR; error = r_glGetError()) {
		Debug(driver, 2, "OpenTT3D: pre-existing OpenGL error before mesh pass ({})", error);
	}
	StateGuard state;
	++mesh_generation;
	/* Declared after the state guard so temporary VAOs/buffers are retired
	 * before restoring the caller's bindings, including on an early return. */
	TransientMeshBuffers transient;
	if (!Initialize()) { initialization_failed = true; return false; }
	const int maximum = MaximumFramebufferSize();
	if (camera.width > maximum || camera.height > maximum) return false;
	r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0);
	r_glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
	r_glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
	r_glPixelStorei(GL_UNPACK_ROW_LENGTH, ATLAS_SIZE);
	for (size_t i = 0; i < Textures().pages.size(); ++i) {
		auto &page = Textures().pages[i];
		if (page.dirty_right <= page.dirty_left) continue;
		int x = page.dirty_left, y = page.dirty_top, w = page.dirty_right - x, h = page.dirty_bottom - y;
		size_t offset = static_cast<size_t>(y) * ATLAS_SIZE + x;
		r_glActiveTexture(GL_TEXTURE0);
		r_glBindTexture(GL_TEXTURE_2D_ARRAY, atlas_colour);
		r_glTexSubImage3D(GL_TEXTURE_2D_ARRAY, 0, x, y, static_cast<GLint>(i), w, h, 1, GL_RGBA, GL_UNSIGNED_BYTE, page.rgba.data() + offset * 4);
		r_glActiveTexture(GL_TEXTURE1);
		r_glBindTexture(GL_TEXTURE_2D_ARRAY, atlas_remap);
		r_glTexSubImage3D(GL_TEXTURE_2D_ARRAY, 0, x, y, static_cast<GLint>(i), w, h, 1, GL_RG, GL_UNSIGNED_BYTE, page.remap.data() + offset * 2);
		page.dirty_left = page.dirty_top = ATLAS_SIZE; page.dirty_right = page.dirty_bottom = 0;
	}
	r_glPixelStorei(GL_UNPACK_ROW_LENGTH, 0);
	r_glActiveTexture(GL_TEXTURE2);
	/* Updating an in-use palette serialized the entire previous world draw on
	 * Apple's GL driver. Reuse only the frame slot whose completion fence retired,
	 * and avoid re-uploading unchanged colours for secondary viewports/readbacks. */
	auto &palette = frame_palettes[frame_slot];
	r_glBindTexture(GL_TEXTURE_2D,palette.name);
	if (!palette.valid || std::memcmp(palette.colours.data(),colours,sizeof(palette.colours)) != 0) {
		Profile::Scope timing(Profile::Section::PaletteUpload);
		r_glTexSubImage2D(GL_TEXTURE_2D,0,0,0,256,1,GL_BGRA,GL_UNSIGNED_INT_8_8_8_8_REV,colours);
		std::copy_n(colours,palette.colours.size(),palette.colours.begin());
		palette.valid = true;
	}
	r_glActiveTexture(GL_TEXTURE0);
	if (!EnsureTarget(target,camera.width,camera.height,true)) return false;
	r_glViewport(0, 0, camera.width, camera.height);
	r_glDisable(GL_BLEND); r_glDisable(GL_CULL_FACE); r_glDisable(GL_SCISSOR_TEST); r_glDisable(GL_FRAMEBUFFER_SRGB);
	r_glDisable(GL_PRIMITIVE_RESTART);
	r_glCullFace(GL_BACK);
	r_glEnable(GL_DEPTH_TEST); r_glDepthFunc(GL_GEQUAL); r_glDepthMask(GL_TRUE);
	r_glColorMaski(0,GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	r_glColorMaski(1,GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	if (camera.first_person || camera.pitch < 20) r_glClearColor(0.52f, 0.70f, 0.86f, 1);
	else r_glClearColor(0, 0, 0, 1);
	r_glClearDepth(0);
	r_glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	const GLuint zero[4]{};
	r_glClearBufferuiv(GL_COLOR, 1, zero);
	r_glActiveTexture(GL_TEXTURE0); r_glBindTexture(GL_TEXTURE_2D_ARRAY, atlas_colour);
	r_glActiveTexture(GL_TEXTURE1); r_glBindTexture(GL_TEXTURE_2D_ARRAY, atlas_remap);
	r_glActiveTexture(GL_TEXTURE2); r_glBindTexture(GL_TEXTURE_2D, palette.name);
	auto matrix = camera.Matrix();
	for (GLuint shader : {program,visible_program}) if (shader != 0) {
		r_glUseProgram(shader);
		r_glUniform1i(r_glGetUniformLocation(shader,"colour_atlas"),0);
		r_glUniform1i(r_glGetUniformLocation(shader,"remap_atlas"),1);
		r_glUniform1i(r_glGetUniformLocation(shader,"palette"),2);
		r_glUniform1i(r_glGetUniformLocation(shader,"instance_data"),3);
		r_glUniform4f(r_glGetUniformLocation(shader,"camera"),camera.focus.x,camera.focus.y,camera.focus.z,camera.Near());
		r_glUniform4f(r_glGetUniformLocation(shader,"water_material"),scene.water.uv_origin.x,scene.water.uv_origin.y,scene.water.uv_origin.z,scene.water.uv_scale);
		r_glUniformMatrix4fv(r_glGetUniformLocation(shader,"view_projection"),1,GL_FALSE,matrix.data());
		if (shader == visible_program) {
			r_glUniform1i(r_glGetUniformLocation(shader,"voxel_vertices"),4);
			r_glUniform1i(r_glGetUniformLocation(shader,"voxel_format"),5);
			r_glUniform1i(r_glGetUniformLocation(shader,"instanced"),1);
		}
	}
	r_glBindVertexArray(vertex_array);
	r_glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer);
	r_glBufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(scene.vertices.size() * sizeof(Vertex)), scene.vertices.data(), GL_STREAM_DRAW);
	VertexLayout();
	static const bool split_opacity = [] { const char *value = std::getenv("OPENTT3D_GL_SPLIT_OPACITY"); return value == nullptr || std::string_view(value) != "0"; }();
	instance_staging.Build(scene.instances,split_opacity);
	auto &records = instance_staging.records;
	auto &batches = instance_batches;
	batches.clear();
	bool pixel_cull = scene.persistent_meshes && visible_program != 0 && maximum_buffer_texels > 0 && !camera.first_person && camera.pixels_per_unit < 0.5f;
	static const bool synchronous_visibility = [] { const char *value = std::getenv("OPENTT3D_VOXEL_CULL_SYNC"); return value != nullptr && std::string_view(value) == "1"; }();
	bool asynchronous = pixel_cull && pixels == nullptr && !synchronous_visibility;
	if (asynchronous) {
		if (!target.visibility_worker) target.visibility_worker = std::make_unique<VoxelVisibilityWorker>();
		target.visibility_worker->SetCamera(camera,subpixel_precision);
		if (auto error = target.visibility_worker->TakeError(); !error.empty()) Debug(driver,1,"OpenTT3D: OpenGL visibility retained mesh fallback: {}",error);
	} else if (target.visibility_worker) target.visibility_worker->Cancel();
	if (pixel_cull && target.visibility.Begin(camera,subpixel_precision,records.size())) {
		target.ClearVisibility();
		if (pixels == nullptr) target.visibility_reported = false;
	} else if (!pixel_cull) {
		target.ClearVisibility(); target.visibility.Clear();
	}
	size_t visibility_budget = 32;
	uint64_t tested_vertices = 0, retained_vertices = 0, indexed_vertices = 0;
	unsigned waiting_visibility = 0;
	for (const auto &batch : instance_staging.batches) {
		const auto *packed = pixel_cull ? FindPackedVoxelMesh(batch.mesh) : nullptr;
		if (packed != nullptr && packed->pixel_cull && packed->format[7] != 0 && packed->StandardPalette() &&
				std::all_of(records.begin()+batch.first,records.begin()+batch.first+batch.count,VolumeInstanceCompatible)) {
			auto [entry,inserted] = visible_meshes.try_emplace(packed);
			auto &storage = entry->second;
			if (inserted) storage.lookup = MakePackedVoxelLookup(packed->vertices);
			const auto &lookup = storage.lookup;
			if (lookup.bits <= 21 && batch.count <= (uint64_t{1}<<(64-lookup.bits*3)) && batch.mesh->size() <= static_cast<size_t>(std::numeric_limits<GLsizei>::max()) &&
					lookup.vertices.size() <= static_cast<size_t>(maximum_buffer_texels) && packed->format.size()/4 <= static_cast<size_t>(maximum_buffer_texels)) {
				r_glActiveTexture(GL_TEXTURE4);
				if (!storage.format.buffer) {
					storage.format.Upload(GL_RGBA32F,packed->format.data(),packed->format.size()*sizeof(uint32_t));
				}
				/* Parent and child batches may share a mesh. Keep separate objects so
				 * staging a child cannot delete a parent's not-yet-submitted stream. */
				auto &cached = target.visible_streams[records[batch.first].ChildLayer()][batch.mesh];
				bool unchanged = cached.transforms.size() == batch.count;
				for (size_t i = 0; unchanged && i < batch.count; ++i) unchanged = cached.transforms[i] == VoxelVisibilityTransform(records[batch.first+i]);
				bool prepare_now = !asynchronous;
				if (!unchanged && asynchronous) {
					if (auto ready = target.visibility_worker->Take(*batch.mesh)) {
						for (size_t i = 0; i < ready->transforms.size(); ++i) if (!cached.geometry.contains(ready->transforms[i])) target.visibility.AdoptPacked(*batch.mesh,ready->transforms[i],std::move(ready->geometry[i]));
					}
					size_t missing = 0;
					for (size_t i = 0; i < batch.count && missing <= visibility_budget; ++i) missing += !cached.geometry.contains(VoxelVisibilityTransform(records[batch.first+i])) && !target.visibility.HasPacked(*batch.mesh,records[batch.first+i]);
					if (missing <= visibility_budget) { prepare_now = true; visibility_budget -= missing; }
					else {
						target.visibility_worker->Request(*batch.mesh,PackedVoxelMeshRegistry().at(batch.mesh),std::span(records).subspan(batch.first,batch.count),records.size(),scene.instances[batch.source].source_lease);
						++waiting_visibility;
					}
				}
				if (!unchanged && prepare_now) {
					auto previous = std::move(cached.pages);
					cached.transforms.clear(); cached.transforms.reserve(batch.count); cached.triangles = cached.vertices = 0;
					for (size_t i = 0; i < batch.count; ++i) cached.transforms.push_back(VoxelVisibilityTransform(records[batch.first+i]));
					++cached.generation;
					std::map<std::array<uint32_t,7>,std::vector<std::shared_ptr<Target::VisiblePage>>> anchors;
					for (const auto &page : previous) anchors[page.storage->transforms.front()].push_back(page.storage);
					auto reusable = [&](size_t first) {
						std::shared_ptr<Target::VisiblePage> result;
						auto found = anchors.find(cached.transforms[first]);
						if (found != anchors.end()) for (const auto &page : found->second) {
							size_t count = page->transforms.size();
							/* Merge small interior fragments on the next edit instead of
							 * accumulating one draw per historical insertion/removal. */
							if (count < 64 && first+count != batch.count) continue;
							if (count <= batch.count-first && (!result || count > result->transforms.size()) &&
									std::equal(page->transforms.begin(),page->transforms.end(),cached.transforms.begin()+first)) result = page;
						}
						return result;
					};
					IndexedVoxelVisibility indexer(lookup);
					size_t limit = std::min<size_t>(maximum_buffer_texels,std::numeric_limits<GLsizei>::max());
					for (size_t first = 0; first < batch.count;) {
						auto page = reusable(first);
						if (!page) {
							/* Keep old ordered subsequences intact after insertions/removals.
							 * A page's local instance references are rebased at draw time. */
							constexpr size_t page_instances = 256;
							size_t end = std::min(first+page_instances,batch.count);
							for (size_t next = first+1; next < end; ++next) if (reusable(next)) { end = next; break; }
							page = std::make_shared<Target::VisiblePage>();
							page->transforms.assign(cached.transforms.begin()+first,cached.transforms.begin()+end);
							std::vector<const Target::VisibleStream::Geometry *> groups;
							size_t vertex_count = 0, index_count = 0;
							for (size_t i = first; i < end; ++i) {
								const auto &instance = records[batch.first+i];
								auto [entry,inserted] = cached.geometry.try_emplace(cached.transforms[i]);
								auto &geometry = entry->second;
								if (inserted) {
									Profile::Scope timing(Profile::Section::MeshIndex);
									indexer.Clear();
									for (uint64_t triangle : target.visibility.PackedTriangles(*batch.mesh,instance,lookup.indices,lookup.bits)) indexer.Add(triangle);
									geometry.vertices.reserve(indexer.vertices.size());
									for (auto vertex : indexer.vertices) geometry.vertices.push_back(vertex[0]);
									geometry.indices = indexer.indices;
									/* The indexed CPU cache now owns this transform. Retaining
									 * its intermediate triangle list duplicates every live edit. */
									target.visibility.Forget(*batch.mesh,instance);
								}
								geometry.used = cached.generation;
								groups.push_back(&geometry);
								vertex_count += geometry.vertices.size(); index_count += geometry.indices.size();
							}
							std::vector<std::array<uint32_t,2>> vertices;
							std::vector<uint32_t> indices;
							vertices.reserve(std::min(vertex_count,limit)); indices.reserve(std::min(index_count,static_cast<size_t>(std::numeric_limits<GLsizei>::max())));
							auto flush = [&] {
								if (indices.empty()) return;
								Profile::Scope timing(Profile::Section::MeshUpload);
								auto &chunk = page->chunks.emplace_back();
								chunk.count = static_cast<GLsizei>(indices.size());
								chunk.storage.Upload(GL_RG32UI,vertices.data(),vertices.size()*sizeof(vertices.front()));
								r_glGenBuffers(1,&chunk.indices); r_glBindBuffer(GL_ARRAY_BUFFER,chunk.indices);
								r_glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(indices.size()*sizeof(uint32_t)),indices.data(),GL_STATIC_DRAW);
								Profile::AddMeshUpload(vertices.size()*sizeof(vertices.front())+indices.size()*sizeof(uint32_t));
								page->triangles += indices.size()/3; page->vertices += vertices.size(); vertices.clear(); indices.clear();
							};
							for (size_t i = 0; i < groups.size(); ++i) {
								const auto &geometry = *groups[i];
								if (vertices.size()+geometry.vertices.size() > limit || indices.size()+geometry.indices.size() > static_cast<size_t>(std::numeric_limits<GLsizei>::max())) flush();
								uint32_t offset = static_cast<uint32_t>(vertices.size());
								for (uint32_t vertex : geometry.vertices) vertices.push_back({vertex,static_cast<uint32_t>(i)});
								size_t start = indices.size(); indices.resize(start+geometry.indices.size());
								std::transform(geometry.indices.begin(),geometry.indices.end(),indices.begin()+start,[offset](uint32_t index) { return offset+index; });
							}
							flush();
						}
						cached.pages.push_back({first,page});
						cached.triangles += page->triangles; cached.vertices += page->vertices;
						first += page->transforms.size();
					}
					unchanged = true;
					/* Reused pages still need their CPU index data for future partial
					 * edits. Mark them too, then release every obsolete transform. */
					for (const auto &transform : cached.transforms) {
						auto found = cached.geometry.find(transform);
						if (found != cached.geometry.end()) found->second.used = cached.generation;
					}
					std::erase_if(cached.geometry,[&](const auto &entry) { return entry.second.used != cached.generation; });
				}
				if (unchanged) {
					tested_vertices += static_cast<uint64_t>(batch.mesh->size())*batch.count;
					retained_vertices += cached.triangles*3;
					indexed_vertices += cached.vertices;
					for (const auto &page : cached.pages) for (const auto &chunk : page.storage->chunks) batches.push_back({batch.mesh,visible_vertex_array,static_cast<GLint>(batch.first+page.first),chunk.count,true,true,false,false,GL_UNSIGNED_INT,packed,&storage,chunk.storage.texture,chunk.indices});
					continue;
				}
			}
		}
		const auto &buffer = GetMesh(batch.mesh,scene.persistent_meshes ? meshes : transient.buffers);
		batches.push_back({batch.mesh,buffer.vao,static_cast<GLint>(batch.first),static_cast<GLsizei>(batch.count),buffer.indices != 0,instance_staging.PaletteOnly(batch),batch.transparent,batch.both_passes,buffer.index_type});
	}
	if (tested_vertices != 0 && waiting_visibility == 0 && !target.visibility_reported) {
		Debug(driver,1,"OpenTT3D: OpenGL conservative pixel visibility retains {} of {} voxel vertices ({} indexed vertices) with original triangle/instance order",retained_vertices,tested_vertices,indexed_vertices);
		target.visibility_reported = true;
	}
	static const bool memory_debug = [] { const char *value = std::getenv("OPENTT3D_MEMORY_DEBUG"); return value != nullptr && std::string_view(value) == "1"; }();
	if (memory_debug && std::chrono::steady_clock::now()-target.memory_reported >= std::chrono::seconds(2)) {
		target.memory_reported = std::chrono::steady_clock::now();
		size_t indexed_bytes = 0, page_bytes = 0, page_count = 0, transform_count = 0, mesh_bytes = 0, source_bytes = 0;
		for (const auto &[mesh,buffer] : meshes) { mesh_bytes += buffer.bytes; source_bytes += mesh->capacity()*sizeof(Vertex); }
		for (const auto &layer : target.visible_streams) for (const auto &[mesh,stream] : layer) {
			transform_count += stream.geometry.size(); page_count += stream.pages.size();
			for (const auto &[key,geometry] : stream.geometry) indexed_bytes += (geometry.vertices.capacity()+geometry.indices.capacity())*sizeof(uint32_t);
			for (const auto &page : stream.pages) page_bytes += page.storage->vertices*8+page.storage->triangles*12;
		}
		Debug(driver,1,"OpenTT3D: GL memory bytes source {} mesh_gpu {} dynamic_gpu {} instance_gpu {} visibility {} worker {} indexed {} page_gpu {} pages {} transforms {}",
			source_bytes,mesh_bytes,scene.vertices.size()*sizeof(Vertex),instance_frames[0].capacity+instance_frames[1].capacity,target.visibility.MemoryBytes(),target.visibility_worker ? target.visibility_worker->MemoryBytes() : 0,indexed_bytes,page_bytes,page_count,transform_count);
	}
	r_glActiveTexture(GL_TEXTURE3);
	instance_frames[frame_slot].Update(GL_RGBA32F,records.data(),records.size()*sizeof(InstanceData));
	const GLint instanced_location = r_glGetUniformLocation(program, "instanced");
	const GLint base_location = r_glGetUniformLocation(program, "instance_base");
	const GLint visible_base_location = visible_program ? r_glGetUniformLocation(visible_program,"instance_base") : -1;
	const GLint bits_location = visible_program ? r_glGetUniformLocation(visible_program,"voxel_bits") : -1;
	auto draw = [&](bool transparent) {
		for (GLuint shader : {program,visible_program}) if (shader != 0) {
			r_glUseProgram(shader);
			r_glUniform1i(r_glGetUniformLocation(shader,"transparent_pass"),transparent ? 1 : 0);
		}
		GLuint shader = program;
		r_glUseProgram(shader);
		bool cull = false;
		r_glDisable(GL_CULL_FACE);
		r_glUniform1i(instanced_location, 0);
		r_glBindVertexArray(vertex_array);
		GLuint bound_vao = vertex_array;
		const PackedVoxelMesh *bound_packed = nullptr;
		r_glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(scene.vertices.size()));
		r_glUniform1i(instanced_location, 1);
		for (const auto &batch : batches) {
			/* Instance opacity replaces vertex opacity. Preserve the existing mesh
			 * and within-pass order, but do not submit a second vertex pass whose
			 * every fragment would be discarded. Vulkan uses the same partition. */
			if (!batch.both_passes && batch.transparent != transparent) continue;
			GLuint selected = batch.visible ? visible_program : program;
			if (shader != selected) { shader = selected; r_glUseProgram(shader); }
			if (cull != batch.cull_back) { StateGuard::Set(GL_CULL_FACE,batch.cull_back); cull = batch.cull_back; }
			if (bound_vao != batch.vao) { bound_vao = batch.vao; r_glBindVertexArray(bound_vao); }
			if (batch.visible != nullptr) {
				r_glUniform1i(visible_base_location,batch.first);
				if (bound_packed != batch.packed) {
					bound_packed = batch.packed;
					const auto &format = batch.packed->format;
					r_glUniform4f(bits_location,format[8],format[9],format[10],format[11]);
					r_glActiveTexture(GL_TEXTURE5); r_glBindTexture(GL_TEXTURE_BUFFER,batch.visible->format.texture);
				}
				r_glActiveTexture(GL_TEXTURE4); r_glBindTexture(GL_TEXTURE_BUFFER,batch.vertices);
				r_glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,batch.indices);
				r_glDrawElementsInstanced(GL_TRIANGLES,batch.count,GL_UNSIGNED_INT,nullptr,1);
				continue;
			}
			r_glUniform1i(base_location,batch.first);
			if (batch.indexed) r_glDrawElementsInstanced(GL_TRIANGLES,static_cast<GLsizei>(batch.mesh->size()),batch.index_type,nullptr,batch.count);
			else r_glDrawArraysInstanced(GL_TRIANGLES,0,static_cast<GLsizei>(batch.mesh->size()),batch.count);
		}
	};
	draw(false);
	r_glEnable(GL_BLEND); r_glDepthMask(GL_FALSE);
	r_glColorMaski(1,GL_FALSE,GL_FALSE,GL_FALSE,GL_FALSE);
	draw(true);
	TrimMeshCache(MeshCacheBudgetBytes());
	if (pixels != nullptr) {
		Profile::Scope readback_time(Profile::Section::Readback);
		pixels->resize(static_cast<size_t>(camera.width) * camera.height * 4);
		r_glPixelStorei(GL_PACK_ALIGNMENT, 1); r_glPixelStorei(GL_PACK_ROW_LENGTH, 0);
		r_glPixelStorei(GL_PACK_SKIP_ROWS, 0); r_glPixelStorei(GL_PACK_SKIP_PIXELS, 0);
		r_glReadBuffer(GL_COLOR_ATTACHMENT0);
		r_glReadPixels(0, 0, camera.width, camera.height, GL_RGBA, GL_UNSIGNED_BYTE, pixels->data());
		if (picking != nullptr) {
			picking->resize(static_cast<size_t>(camera.width)*camera.height);
			r_glReadBuffer(GL_COLOR_ATTACHMENT1);
			r_glReadPixels(0,0,camera.width,camera.height,GL_RED_INTEGER,GL_UNSIGNED_INT,picking->data());
			r_glReadBuffer(GL_COLOR_ATTACHMENT0);
		}
	}
	GLenum error = r_glGetError();
	if (error != GL_NO_ERROR) {
		Debug(driver, 0, "OpenTT3D: OpenGL rendering failed ({})", error);
		return false;
	}
	return true;
}

bool RenderScene(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels, std::vector<uint32_t> *picking)
{
	if (Vulkan::Active()) return Vulkan::Readback(scene,camera,pixels,picking);
	return RenderTarget(readback_target,scene,camera,&pixels,picking);
}

namespace OpenGL {
bool Active()
{
	static const bool enabled = [] { const char *value = std::getenv("OPENTT3D_GL_PRESENTATION"); return value == nullptr || std::string_view(value) != "0"; }();
	return enabled && !Vulkan::Active() && HasOpenGLBackend();
}

bool WaitForFrame()
{
	for (GLsync *fence : {&frame_complete[frame_slot],&frame_consumed[frame_slot]}) {
		if (*fence == nullptr) continue;
		for (;;) {
			GLenum result = r_glClientWaitSync(*fence,GL_SYNC_FLUSH_COMMANDS_BIT,1000000000);
			if (result == GL_WAIT_FAILED) return false;
			if (result == GL_ALREADY_SIGNALED || result == GL_CONDITION_SATISFIED) break;
		}
		r_glDeleteSync(*fence); *fence = nullptr;
	}
	return true;
}

unsigned FrameSlot() { return frame_slot; }

void BeginFrame() { regions.clear(); }

bool RenderViewport(const void *key, const Scene &scene, const Camera &camera)
{
	return Active() && RenderTarget(viewport_targets[key],scene,camera);
}

void ComposeViewport(const void *key, int sx, int sy, int width, int height, int dx, int dy)
{
	if (width > 0 && height > 0 && viewport_targets.contains(key)) regions.push_back({key,sx,sy,width,height,dx,dy});
}

uint32_t ReadObjectId(const void *key, int x, int y)
{
	auto found = viewport_targets.find(key);
	if (found == viewport_targets.end() || x < 0 || y < 0 || x >= found->second.width || y >= found->second.height) return 0;
	OpenGLBackend::Get()->ActivateRenderContext();
	Profile::Scope timing(Profile::Section::Readback);
	StateGuard state;
	const Target &target = found->second;
	r_glBindFramebuffer(GL_READ_FRAMEBUFFER,target.framebuffer);
	r_glBindBuffer(GL_PIXEL_PACK_BUFFER,0);
	r_glPixelStorei(GL_PACK_ALIGNMENT,1); r_glPixelStorei(GL_PACK_ROW_LENGTH,0);
	r_glPixelStorei(GL_PACK_SKIP_ROWS,0); r_glPixelStorei(GL_PACK_SKIP_PIXELS,0);
	r_glReadBuffer(GL_COLOR_ATTACHMENT1);
	uint32_t id = 0;
	r_glReadPixels(x,target.height-1-y,1,1,GL_RED_INTEGER,GL_UNSIGNED_INT,&id);
	return id;
}

void ForgetViewport(const void *key)
{
	std::erase_if(regions,[key](const Region &region) { return region.key == key; });
	auto found = viewport_targets.find(key);
	if (found == viewport_targets.end()) return;
	OpenGLBackend::Get()->ActivateRenderContext();
	StateGuard state;
	found->second.Destroy();
	viewport_targets.erase(found);
}

static bool InitializeComposite()
{
	if (composite_program) return true;
	const char *vertex_source = R"GLSL(#version 150
uniform vec4 destination;
uniform vec4 source;
out vec2 uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(destination.xy + p * destination.zw, 0, 1);
    uv = source.xy + p * source.zw;
}
)GLSL";
	const char *fragment_source = R"GLSL(#version 150
uniform sampler2D image;
in vec2 uv;
out vec4 colour;
void main() { colour = texture(image, uv); }
)GLSL";
	GLuint vertex = Compile(GL_VERTEX_SHADER,vertex_source), fragment = Compile(GL_FRAGMENT_SHADER,fragment_source);
	if (!vertex || !fragment) { r_glDeleteShader(vertex); r_glDeleteShader(fragment); return false; }
	composite_program = r_glCreateProgram();
	r_glAttachShader(composite_program,vertex); r_glAttachShader(composite_program,fragment);
	r_glBindFragDataLocation(composite_program,0,"colour");
	r_glLinkProgram(composite_program);
	r_glDeleteShader(vertex); r_glDeleteShader(fragment);
	GLint success = 0;
	r_glGetProgramiv(composite_program,GL_LINK_STATUS,&success);
	if (!success) { r_glDeleteProgram(composite_program); composite_program = 0; return false; }
	r_glGenVertexArrays(1,&composite_vao);
	return true;
}

bool PreparePresentation(int width, int height, const std::function<void()> &draw_ui)
{
	prepared_texture = 0;
	if (!Active() || (regions.empty() && !presentation_capture)) return true;
	OpenGLBackend::Get()->ActivateRenderContext();
	if (!LoadFunctions()) return false;
	StateGuard state;
	/* The driver normally waits before taking the game-state lock. Explicit review
	 * captures may also submit here; they must respect the same bounded queue. */
	if (!WaitForFrame()) return false;
	/* Cocoa consumes this shared texture in a second context. GPU-side waits retain
	 * ordering without a full-image readback or a CPU fence wait in normal frames. */
	if (presentation_consumed) {
		r_glWaitSync(presentation_consumed,0,GL_TIMEOUT_IGNORED);
		r_glDeleteSync(presentation_consumed); presentation_consumed = nullptr;
	}
	if (presentation_ready) { r_glDeleteSync(presentation_ready); presentation_ready = nullptr; }
	if (width <= 0 || height <= 0 || !InitializeComposite() || !EnsureTarget(presentation_target,width,height,false)) return false;
	r_glViewport(0,0,width,height);
	r_glDisable(GL_DEPTH_TEST); r_glDisable(GL_BLEND); r_glDisable(GL_CULL_FACE);
	r_glDisable(GL_SCISSOR_TEST); r_glDisable(GL_FRAMEBUFFER_SRGB);
	r_glColorMaski(0,GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
	r_glClearColor(0,0,0,1); r_glClear(GL_COLOR_BUFFER_BIT);
	r_glUseProgram(composite_program); r_glBindVertexArray(composite_vao);
	r_glActiveTexture(GL_TEXTURE0);
	r_glUniform1i(r_glGetUniformLocation(composite_program,"image"),0);
	/* Presentation texture row zero is the top, like the original UI texture. */
	r_glEnable(GL_SCISSOR_TEST);
	for (const Region &region : regions) {
		auto found = viewport_targets.find(region.key);
		if (found == viewport_targets.end()) continue;
		const Target &target = found->second;
		r_glScissor(region.dx,region.dy,region.width,region.height);
		r_glBindTexture(GL_TEXTURE_2D,target.colour);
		r_glUniform4f(r_glGetUniformLocation(composite_program,"destination"),2.0f*region.dx/width-1,2.0f*region.dy/height-1,2.0f*region.width/width,2.0f*region.height/height);
		r_glUniform4f(r_glGetUniformLocation(composite_program,"source"),float(region.sx)/target.width,1.0f-float(region.sy)/target.height,float(region.width)/target.width,-float(region.height)/target.height);
		r_glDrawArrays(GL_TRIANGLES,0,3);
	}
	/* The original driver's shaders own UI palette/brightness behaviour. */
	r_glDisable(GL_SCISSOR_TEST);
	r_glEnable(GL_BLEND);
	r_glBlendEquationSeparate(GL_FUNC_ADD,GL_FUNC_ADD);
	/* Blitter colour over the transparent viewport canvas is premultiplied. */
	r_glBlendFuncSeparate(GL_ONE,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);
	draw_ui();
	if (presentation_capture) {
		Profile::Scope timing(Profile::Section::Readback);
		std::vector<Colour> pixels(static_cast<size_t>(width)*height);
		r_glBindBuffer(GL_PIXEL_PACK_BUFFER,0);
		r_glPixelStorei(GL_PACK_ALIGNMENT,1); r_glPixelStorei(GL_PACK_ROW_LENGTH,0);
		r_glPixelStorei(GL_PACK_SKIP_ROWS,0); r_glPixelStorei(GL_PACK_SKIP_PIXELS,0);
		r_glReadBuffer(GL_COLOR_ATTACHMENT0);
		r_glReadPixels(0,0,width,height,GL_BGRA,GL_UNSIGNED_INT_8_8_8_8_REV,pixels.data());
		auto callback = std::move(presentation_capture); presentation_capture = {};
		callback(width,height,std::move(pixels));
		Debug(driver,1,"OpenTT3D: captured OpenGL presentation with {} GPU viewport regions",regions.size());
	}
	if (GLenum error = r_glGetError(); error != GL_NO_ERROR) { Debug(driver,0,"OpenTT3D: OpenGL presentation failed ({})",error); return false; }
	prepared_texture = presentation_target.colour;
	prepared_slot = frame_slot;
	presentation_ready = r_glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);
	frame_complete[frame_slot] = r_glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);
	frame_slot = (frame_slot+1)%frame_complete.size();
	r_glFlush();
	return true;
}

uint32_t PresentationTexture()
{
	if (prepared_texture && presentation_ready) r_glWaitSync(presentation_ready,0,GL_TIMEOUT_IGNORED);
	return prepared_texture;
}

void FinishPresentation()
{
	if (!prepared_texture) return;
	if (presentation_consumed) r_glDeleteSync(presentation_consumed);
	presentation_consumed = r_glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);
	/* The layer's hardware cursor also samples the driver's per-frame UI palette. */
	if (frame_consumed[prepared_slot]) r_glDeleteSync(frame_consumed[prepared_slot]);
	frame_consumed[prepared_slot] = r_glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0);
	r_glFlush();
}

bool CapturePresentation(PresentationCapture callback)
{
	if (!Active() || presentation_capture) return false;
	presentation_capture = std::move(callback);
	return true;
}

void VerifyPresentation()
{
	if (!Active()) return;
	OpenGLBackend::Get()->ActivateRenderContext();
	if (!LoadFunctions()) throw std::runtime_error("OpenGL presentation verification: missing functions");
	StateGuard state;
	static const int keys[2]{};
	struct Cleanup {
		std::vector<Region> saved_regions = std::move(regions);
		PresentationCapture saved_capture = std::move(presentation_capture);
		unsigned saved_slot = frame_slot;
		GLuint ui = 0;
		~Cleanup()
		{
			for (const int &key : keys) ForgetViewport(&key);
			if (ui) r_glDeleteTextures(1,&ui);
			regions = std::move(saved_regions); presentation_capture = std::move(saved_capture);
			frame_slot = saved_slot;
			for (auto &palette : frame_palettes) palette.valid = false;
			prepared_texture = 0;
		}
	} cleanup;
	r_glGenTextures(1,&cleanup.ui);
	size_t checked = 0;
	for (Point size : {Point{281,207},Point{383,251}}) {
		Camera camera{{8,8,6},4,191,137,0.17f};
		std::array<std::vector<uint8_t>,2> reference;
		for (unsigned view = 0; view < 2; ++view) {
			Scene scene;
			scene.Quad({0,0,6},{16,0,6},{16,16,6},{0,16,6},view == 0 ? Rgb{1,0,0} : Rgb{0,1,0});
			for (auto &vertex : scene.vertices) vertex.object_id = 71+view;
			if (!RenderViewport(&keys[view],scene,camera) || !RenderScene(scene,camera,reference[view])) throw std::runtime_error("OpenGL presentation verification: render failed");
			if (ReadObjectId(&keys[view],95,68) != 71+view) throw std::runtime_error("OpenGL presentation verification: another viewport/readback replaced its ID target");
		}
		regions.clear();
		ComposeViewport(&keys[0],7,9,153,111,13,17);
		ComposeViewport(&keys[1],3,5,53,57,101,89);
		ComposeViewport(&keys[0],17,25,31,31,-3,size.y-11);
		std::vector<Colour> expected(static_cast<size_t>(size.x)*size.y,Colour(0,0,0));
		for (const Region &region : regions) {
			const auto &pixels = reference[region.key == &keys[0] ? 0 : 1];
			for (int y = 0; y < region.height; ++y) for (int x = 0; x < region.width; ++x) {
				int dx = region.dx+x, dy = region.dy+y;
				if (dx < 0 || dy < 0 || dx >= size.x || dy >= size.y) continue;
				size_t source = (static_cast<size_t>(camera.height-1-region.sy-y)*camera.width+region.sx+x)*4;
				expected[static_cast<size_t>(dy)*size.x+dx] = Colour(pixels[source],pixels[source+1],pixels[source+2]);
			}
		}
		std::vector<Colour> ui(expected.size(),Colour(0,0,0,0));
		for (int y = 0; y < size.y; ++y) for (int x = 0; x < size.x; ++x) {
			if (y >= 7 && x >= 5 && ((x/13+y/11)%7 != 0)) continue;
			size_t index = static_cast<size_t>(y)*size.x+x;
			expected[index] = ui[index] = Colour((x*7)%256,(y*13)%256,(x+y)%256);
		}
		/* The original 32bpp blitter retains premultiplied colour when glyphs or
		 * translucent UI cover a transparent viewport canvas. Do not apply alpha twice. */
		for (int y = 35; y < 149; ++y) for (int x = 80; x < 147; ++x) {
			size_t index = static_cast<size_t>(y)*size.x+x;
			if (ui[index].a != 0) continue;
			unsigned alpha = 64*(1+x%3);
			Colour overlay(alpha/2,alpha/4,alpha/8,alpha), background = expected[index];
			ui[index] = overlay;
			expected[index] = Colour(overlay.r+(background.r*(255-alpha)+127)/255,
				overlay.g+(background.g*(255-alpha)+127)/255,overlay.b+(background.b*(255-alpha)+127)/255);
		}
		r_glActiveTexture(GL_TEXTURE0); r_glBindTexture(GL_TEXTURE_2D,cleanup.ui);
		r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
		r_glPixelStorei(GL_UNPACK_ROW_LENGTH,0); r_glPixelStorei(GL_UNPACK_ALIGNMENT,1);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
		r_glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,size.x,size.y,0,GL_BGRA,GL_UNSIGNED_INT_8_8_8_8_REV,ui.data());
		std::vector<Colour> actual;
		presentation_capture = [&](int width, int height, std::vector<Colour> pixels) {
			if (width != size.x || height != size.y) throw std::runtime_error("OpenGL presentation verification: wrong extent");
			actual = std::move(pixels);
		};
		if (!PreparePresentation(size.x,size.y,[&] {
			r_glActiveTexture(GL_TEXTURE0); r_glBindTexture(GL_TEXTURE_2D,cleanup.ui);
			r_glUniform4f(r_glGetUniformLocation(composite_program,"destination"),-1,-1,2,2);
			r_glUniform4f(r_glGetUniformLocation(composite_program,"source"),0,0,1,1);
			r_glDrawArrays(GL_TRIANGLES,0,3);
		})) throw std::runtime_error("OpenGL presentation verification: composition failed");
		if (actual.size() != expected.size() || std::memcmp(actual.data(),expected.data(),expected.size()*sizeof(Colour)) != 0) throw std::runtime_error("OpenGL presentation verification: clipping, orientation or UI colour differs from CPU reference");
		checked += expected.size();
	}
	Debug(driver,1,"OpenTT3D: OpenGL resident composition matches {} exact CPU RGBA pixels across clipped/overlapping viewports, UI masks and resized targets",checked);
	/* Exercise changing, repeated and returning colours on both in-flight slots.
	 * The local snapshots never write the game's palette or animation state. */
	static const std::vector<Vertex> palette_quad = [] {
		Scene scene;
		scene.Quad({0,0,6},{16,0,6},{16,16,6},{0,16,6},{1,1,1});
		for (auto &vertex : scene.vertices) {
			vertex.texture = {239.5f/256,0.5f,-3};
			vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT);
		}
		return scene.vertices;
	}();
	Scene palette_scene;
	InstanceData material;
	UsePaletteMaterial(material);
	material.SetObjectId(73);
	palette_scene.instances.push_back({&palette_quad,material});
	Camera palette_camera{{8,8,6},4,191,137,0.17f};
	const Colour phases[] = {Colour(173,37,101),Colour(47,188,89),Colour(18,54,215)};
	const size_t instance_counts[] = {1,513,2049,17,4097,1};
	std::array<size_t,2> instance_capacities{};
	std::array<Colour,256> snapshot;
	std::copy_n(_cur_palette.palette,snapshot.size(),snapshot.begin());
	for (unsigned phase = 0; phase < 12; ++phase) {
		frame_slot = phase%frame_palettes.size();
		if (!WaitForFrame()) throw std::runtime_error("OpenGL palette verification: frame fence wait failed");
		InstanceData outside = material;
		outside.origin_opacity = {1000000,1000000,0,1};
		palette_scene.instances.assign(instance_counts[phase%std::size(instance_counts)],{&palette_quad,outside});
		/* The visible record is last, exercising fresh nonzero offsets after
		 * growing, shrinking and returning to an earlier instance count. */
		palette_scene.instances.back().data = material;
		snapshot[239] = phases[(phase/2)%std::size(phases)];
		std::vector<uint8_t> pixels;
		std::vector<uint32_t> ids;
		if (!RenderTarget(viewport_targets[&keys[0]],palette_scene,palette_camera,&pixels,&ids,snapshot.data())) throw std::runtime_error("OpenGL palette verification: render failed");
		size_t centre = 68*191+95;
		Colour expected = snapshot[239];
		if (ids[centre] != 73 || pixels[centre*4] != expected.r || pixels[centre*4+1] != expected.g || pixels[centre*4+2] != expected.b) throw std::runtime_error("OpenGL palette verification: a frame slot retained stale animation colours");
		if (phase == 5) for (size_t i = 0; i < instance_frames.size(); ++i) instance_capacities[i] = instance_frames[i].capacity;
		if (phase > 5 && instance_frames[frame_slot].capacity != instance_capacities[frame_slot]) throw std::runtime_error("OpenGL instance verification: repeated frame uploads grew resident storage");
	}
	Debug(driver,1,"OpenTT3D: 12 OpenGL frame-slot palette snapshots preserve changing and returning animation colours without game-palette writes");
	Debug(driver,1,"OpenTT3D: OpenGL frame-slot instance uploads retain bounded storage and fresh offsets across 1/513/2049/17/4097/1 records");
}
} // namespace OpenGL

void DestroyOpenGLResources()
{
	if (functions_loaded) {
		if (presentation_consumed) { r_glWaitSync(presentation_consumed,0,GL_TIMEOUT_IGNORED); r_glDeleteSync(presentation_consumed); }
		if (presentation_ready) r_glDeleteSync(presentation_ready);
		for (GLsync fence : frame_complete) if (fence) r_glDeleteSync(fence);
		for (GLsync fence : frame_consumed) if (fence) r_glDeleteSync(fence);
		for (auto &[key,target] : viewport_targets) target.Destroy();
		readback_target.Destroy(); presentation_target.Destroy();
		r_glDeleteProgram(composite_program); r_glDeleteVertexArrays(1,&composite_vao);
		r_glDeleteProgram(program);
		r_glDeleteProgram(visible_program); r_glDeleteVertexArrays(1,&visible_vertex_array);
		for (auto &[packed,storage] : visible_meshes) storage.format.Destroy();
		for (auto &buffer : instance_frames) buffer.Destroy();
		r_glDeleteVertexArrays(1, &vertex_array); r_glDeleteBuffers(1, &vertex_buffer);
		r_glDeleteTextures(1, &atlas_colour); r_glDeleteTextures(1, &atlas_remap);
		for (auto &palette : frame_palettes) r_glDeleteTextures(1,&palette.name);
		for (const auto &[mesh,buffer] : meshes) buffer.Destroy();
	}
	meshes.clear();
	visible_meshes.clear();
	instance_staging = {};
	instance_batches = {};
	program = vertex_array = vertex_buffer = 0;
	visible_program = visible_vertex_array = 0; maximum_buffer_texels = subpixel_precision = 0;
	atlas_colour = atlas_remap = 0;
	frame_palettes = {};
	viewport_targets.clear(); regions.clear();
	composite_program = composite_vao = prepared_texture = 0;
	presentation_ready = presentation_consumed = nullptr;
	frame_complete = {}; frame_consumed = {}; frame_slot = prepared_slot = 0;
	presentation_capture = {};
	functions_loaded = initialization_failed = false;
}

} // namespace Renderer3D

#else
namespace Renderer3D {
bool HasOpenGLBackend() { return false; }
int MaximumFramebufferSize() { return Vulkan::MaximumImageSize(); }
std::string BackendDescription() { return Vulkan::Description(); }
bool RenderScene(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels, std::vector<uint32_t> *ids) { return Vulkan::Readback(scene, camera, pixels, ids); }
void TrimMeshCache(uint64_t budget) { Vulkan::TrimMeshCache(budget); }
void DestroyOpenGLResources() {}
namespace OpenGL {
bool Active() { return false; }
bool WaitForFrame() { return true; }
unsigned FrameSlot() { return 0; }
void BeginFrame() {}
bool RenderViewport(const void *, const Scene &, const Camera &) { return false; }
void ComposeViewport(const void *, int, int, int, int, int, int) {}
uint32_t ReadObjectId(const void *, int, int) { return 0; }
void ForgetViewport(const void *) {}
bool PreparePresentation(int, int, const std::function<void()> &) { return false; }
uint32_t PresentationTexture() { return 0; }
void FinishPresentation() {}
bool CapturePresentation(PresentationCapture) { return false; }
void VerifyPresentation() {}
}
}
#endif

namespace Renderer3D {
bool HasRenderBackend() { return Vulkan::Active() || HasOpenGLBackend(); }
}
