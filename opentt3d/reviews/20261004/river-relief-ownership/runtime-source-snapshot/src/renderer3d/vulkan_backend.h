/* SPDX-License-Identifier: GPL-2.0-only */
/** @file vulkan_backend.h GPU-resident world targets and UI presentation. */
#ifndef RENDERER3D_VULKAN_BACKEND_H
#define RENDERER3D_VULKAN_BACKEND_H

#include "camera.hpp"
#include "../gfx_type.h"
#include <functional>
#include <string>
#ifdef WITH_VULKAN
#include <vulkan/vulkan.h>
#endif

namespace Renderer3D::Vulkan {

/** One-shot capture of the actual presented image, in top-down native colours. */
using PresentationCapture = std::function<void(int, int, std::vector<Colour>)>;

struct MeshCacheStats {
	size_t meshes = 0, buffers = 0;
	uint64_t used_bytes = 0, capacity_bytes = 0;
	uint64_t source_vertices = 0, stored_vertices = 0, index_bytes = 0;
	size_t indexed_meshes = 0;
	bool pooled = false;
	bool operator==(const MeshCacheStats &) const = default;
};

/** Synchronous diagnostic uploads may retain one largest page plus this scratch budget. */
inline constexpr uint64_t READBACK_ARENA_SCRATCH_BYTES = 32ULL * 1024 * 1024;
struct ReadbackArenaStats {
	size_t buffers = 0;
	uint64_t capacity_bytes = 0, largest_bytes = 0;
};

#ifdef WITH_VULKAN
bool CreateInstance(std::span<const char *const> extensions);
VkInstance Instance();
bool SetSurface(VkSurfaceKHR surface);
bool Active();
void Destroy();
const std::string &LastError();
std::string Description();
int MaximumImageSize();
MeshCacheStats GetMeshCacheStats();
void TrimMeshCache(uint64_t budget);
ReadbackArenaStats GetReadbackArenaStats();
bool Resize(int width, int height);
void *VideoBuffer();
uint8_t *AnimationBuffer();
bool Present(bool animation);
bool CapturePresentation(PresentationCapture callback);
bool RenderViewport(const void *key, const Scene &scene, const Camera &camera);
void ComposeViewport(const void *key, int source_x, int source_y, int width, int height, int destination_x, int destination_y);
uint32_t ReadObjectId(const void *key, int x, int y);
void ForgetViewport(const void *key);
bool Readback(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels, std::vector<uint32_t> *ids);
#else
inline bool Active() { return false; }
inline std::string Description() { return "unavailable"; }
inline int MaximumImageSize() { return 0; }
inline MeshCacheStats GetMeshCacheStats() { return {}; }
inline void TrimMeshCache(uint64_t) {}
inline ReadbackArenaStats GetReadbackArenaStats() { return {}; }
inline bool CapturePresentation(PresentationCapture) { return false; }
inline bool RenderViewport(const void *, const Scene &, const Camera &) { return false; }
inline void ComposeViewport(const void *, int, int, int, int, int, int) {}
inline uint32_t ReadObjectId(const void *, int, int) { return 0; }
inline void ForgetViewport(const void *) {}
inline bool Readback(const Scene &, const Camera &, std::vector<uint8_t> &, std::vector<uint32_t> *) { return false; }
#endif

} // namespace Renderer3D::Vulkan
#endif
