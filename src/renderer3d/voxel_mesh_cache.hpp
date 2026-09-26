/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_mesh_cache.hpp Lossless, scene-pinned CPU voxel surface residency. */
#ifndef RENDERER3D_VOXEL_MESH_CACHE_HPP
#define RENDERER3D_VOXEL_MESH_CACHE_HPP

#include "voxel_geometry.hpp"

namespace Renderer3D {

/** The vector object and its metadata keep their address for the catalogue's
 * lifetime. GPU cache keys therefore survive retirement of its CPU allocation. */
struct VoxelCachedSurface {
	std::unique_ptr<VoxelSource> source;
	mutable VoxelMesh surface;
	bool merged = true;
	const VoxelSource *lod_source = nullptr;
	unsigned reduction = 1;
	mutable std::array<std::unique_ptr<VoxelCachedSurface>,4> lods;
private:
	friend class VoxelMeshCache;
	std::shared_ptr<const void> lease = std::make_shared<uint8_t>(0);
	mutable uint64_t last_use = 0;
};

/** Single renderer-thread cache. Live scenes and diagnostic scopes pin every
 * stream they inspect; the soft budget may be exceeded by active geometry. */
class VoxelMeshCache {
	std::vector<const VoxelCachedSurface *> entries;
	uint64_t budget;
	mutable uint64_t bytes = 0, generation = 0, rebuilds = 0;
public:
	explicit VoxelMeshCache(uint64_t budget) : budget(budget) {}
	void Register(const VoxelCachedSurface &entry)
	{
		entries.push_back(&entry);
		bytes += entry.surface.vertices.capacity()*sizeof(Vertex);
		entry.last_use = ++generation;
		Trim(budget);
	}
	std::shared_ptr<const void> Pin(const VoxelCachedSurface &entry, const std::vector<VoxelMaterial> &materials) const
	{
		auto lease = entry.lease;
		entry.last_use = ++generation;
		if (entry.surface.vertices.empty() && entry.surface.occupied != 0) {
			auto grid = (entry.lod_source != nullptr ? entry.lod_source : entry.source.get())->Expand(materials);
			auto restored = entry.reduction == 1 ? grid.Mesh(entry.merged) : grid.ReducedMesh(entry.reduction);
			if (restored.occupied != entry.surface.occupied || restored.exposed_faces != entry.surface.exposed_faces ||
				restored.quads != entry.surface.quads || restored.low != entry.surface.low || restored.high != entry.surface.high) {
				throw std::runtime_error("Retired voxel surface changed its immutable geometry");
			}
			entry.surface.vertices = std::move(restored.vertices);
			bytes += entry.surface.vertices.capacity()*sizeof(Vertex);
			++rebuilds;
			/* Already resident draws do not scan the catalogue. If an active scene
			 * exceeds the budget, the next cache miss retires newly unpinned data. */
			Trim(budget);
		}
		return lease;
	}
	void Trim(uint64_t target) const
	{
		if (bytes <= target) return;
		std::vector<const VoxelCachedSurface *> cold;
		for (auto entry : entries) if (entry->lease.use_count() == 1 && entry->surface.vertices.capacity() != 0) cold.push_back(entry);
		std::ranges::sort(cold,[](auto a,auto b) { return a->last_use < b->last_use; });
		for (auto entry : cold) {
			if (bytes <= target) break;
			bytes -= entry->surface.vertices.capacity()*sizeof(Vertex);
			std::vector<Vertex>{}.swap(entry->surface.vertices);
		}
	}
	uint64_t ResidentBytes() const { return bytes; }
	uint64_t Rebuilds() const { return rebuilds; }
	bool IsPinned(const VoxelCachedSurface &entry) const { return entry.lease.use_count() > 1; }
};

} // namespace Renderer3D
#endif
