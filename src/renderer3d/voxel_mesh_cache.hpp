/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_mesh_cache.hpp Lossless, scene-pinned CPU voxel surface residency. */
#ifndef RENDERER3D_VOXEL_MESH_CACHE_HPP
#define RENDERER3D_VOXEL_MESH_CACHE_HPP

#include "voxel_geometry.hpp"

namespace Renderer3D {

/** Independently encoded spans keep tall or widely separated surfaces within the
 * palette format's coordinate bits. The ordered stream still roundtrips word for
 * word. Unsupported coordinate lattices retain the authoring-source fallback. */
struct VoxelRestoration {
	std::vector<std::shared_ptr<const PackedVoxelMesh>> chunks;
	size_t vertices = 0;
	uint64_t Bytes() const
	{
		uint64_t bytes = chunks.capacity()*sizeof(chunks.front());
		for (const auto &chunk : chunks) bytes += (chunk->vertices.capacity()+chunk->format.capacity())*sizeof(uint32_t);
		return bytes;
	}
	bool Encode(std::span<const Vertex> source, uint64_t limit)
	{
		/* Triangle-aligned spans usually need fewer coordinate and normal bits
		 * than a whole surface. Subdivide only when exact packing requires it. */
		size_t span = std::min<size_t>(4095,source.size());
		while (!source.empty()) {
			auto packed = AutoPackVoxelMesh(source.first(span));
			if (!packed) {
				if (span <= 3) return false;
				span = std::max<size_t>(3,(span/6)*3);
				continue;
			}
			chunks.push_back(std::move(packed));
			if (Bytes() > limit) return false;
			vertices += span;
			source = source.subspan(span);
			span = std::min<size_t>(4095,source.size());
		}
		return true;
	}
};

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
	mutable std::unique_ptr<VoxelRestoration> restoration;
	std::shared_ptr<const void> lease = std::make_shared<uint8_t>(0);
	mutable uint64_t last_use = 0;
};

/** Single renderer-thread cache. Live scenes and diagnostic scopes pin every
 * stream they inspect; the soft budget may be exceeded by active geometry. */
class VoxelMeshCache {
	std::vector<const VoxelCachedSurface *> entries;
	uint64_t budget;
	mutable uint64_t bytes = 0, restoration_bytes = 0, generation = 0, rebuilds = 0, packed_rebuilds = 0;
	void DropRestoration(const VoxelCachedSurface &entry) const
	{
		if (!entry.restoration) return;
		uint64_t stored = entry.restoration->Bytes();
		bytes -= stored; restoration_bytes -= stored;
		entry.restoration.reset();
	}
	void RetainRestoration(const VoxelCachedSurface &entry, uint64_t target) const
	{
		/* A bounded exact vertex encoding avoids remeshing small animated states
		 * on their first appearance. Large or unrepresentable streams keep their
		 * retained authoring-source fallback. This storage is part of the same
		 * CPU budget, not an additional unbounded geometry cache. */
		uint64_t limit = std::min<uint64_t>(target/4,256ULL*1024*1024);
		if (entry.restoration || entry.surface.vertices.empty() || entry.surface.vertices.size() > 512*1024 ||
			entry.surface.vertices.size()*sizeof(uint32_t)+256 > limit) return;
		auto packed = std::make_unique<VoxelRestoration>();
		if (!packed->Encode(entry.surface.vertices,limit)) return;
		uint64_t stored = packed->Bytes();
		while (restoration_bytes+stored > limit) {
			const VoxelCachedSurface *oldest = nullptr;
			for (auto candidate : entries) if (candidate->restoration && (oldest == nullptr || candidate->last_use < oldest->last_use)) oldest = candidate;
			if (oldest == nullptr) break;
			DropRestoration(*oldest);
		}
		entry.restoration = std::move(packed);
		bytes += stored; restoration_bytes += stored;
	}
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
			if (entry.restoration) {
				const auto &packed = *entry.restoration;
				entry.surface.vertices.reserve(packed.vertices);
				for (const auto &chunk : packed.chunks) for (uint32_t vertex : chunk->vertices) entry.surface.vertices.push_back(chunk->Decode(vertex));
				++packed_rebuilds;
			} else {
				auto grid = (entry.lod_source != nullptr ? entry.lod_source : entry.source.get())->Expand(materials);
				auto restored = entry.reduction == 1 ? grid.Mesh(entry.merged) : grid.ReducedMesh(entry.reduction);
				if (restored.occupied != entry.surface.occupied || restored.exposed_faces != entry.surface.exposed_faces ||
					restored.quads != entry.surface.quads || restored.low != entry.surface.low || restored.high != entry.surface.high) {
					throw std::runtime_error("Retired voxel surface changed its immutable geometry");
				}
				entry.surface.vertices = std::move(restored.vertices);
			}
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
			RetainRestoration(*entry,target);
			bytes -= entry->surface.vertices.capacity()*sizeof(Vertex);
			std::vector<Vertex>{}.swap(entry->surface.vertices);
		}
		/* Forced retirement must also release compressed streams. They are not
		 * referenced by scene leases, so an active surface never pins a duplicate. */
		if (bytes > target) for (auto entry : entries) {
			DropRestoration(*entry);
			if (bytes <= target) break;
		}
	}
	uint64_t ResidentBytes() const { return bytes; }
	uint64_t RestorationBytes() const { return restoration_bytes; }
	uint64_t Rebuilds() const { return rebuilds; }
	uint64_t PackedRebuilds() const { return packed_rebuilds; }
	bool IsPinned(const VoxelCachedSurface &entry) const { return entry.lease.use_count() > 1; }
};

} // namespace Renderer3D
#endif
