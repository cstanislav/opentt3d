/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_mesh_cache.hpp Lossless, scene-pinned CPU voxel surface residency. */
#ifndef RENDERER3D_VOXEL_MESH_CACHE_HPP
#define RENDERER3D_VOXEL_MESH_CACHE_HPP

#include "voxel_geometry.hpp"

namespace Renderer3D {

/** A bounded column lift supports sloped objects without scaling their height.
 * Zero support leaves every position/normal/bound word untouched. */
inline void ApplyVoxelSupport(VoxelMesh &mesh, const std::array<float,4> &support)
{
	if (support == std::array<float,4>{}) return;
	if (support[3] < 0 || std::ranges::any_of(support,[](float value) { return !std::isfinite(value); })) throw std::invalid_argument("Invalid voxel support plane");
	if (mesh.vertices.empty()) return;
	if (mesh.vertices.size()%3 != 0) throw std::invalid_argument("Voxel support needs complete triangles");
	auto height = [&](const Vertex &vertex) { return support[0]*vertex.position.x+support[1]*vertex.position.y+support[2]; };
	std::vector<Vertex> lifted;
	lifted.reserve(mesh.vertices.size());
	auto emit = [&](const std::vector<Vertex> &polygon, bool sloped) {
		for (size_t corner = 1; corner+1 < polygon.size(); ++corner) {
			std::array<Vertex,3> triangle{polygon[0],polygon[corner],polygon[corner+1]};
			Vec3 a = triangle[1].position-triangle[0].position, b = triangle[2].position-triangle[0].position;
			Vec3 cross{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};
			if (Dot(cross,cross) == 0) continue;
			for (auto &vertex : triangle) {
				vertex.position.z += std::clamp(height(vertex),0.0f,support[3]);
				/* Inverse-transpose of the column shear. Constant lifts and vertical
				 * faces retain their original normal words and all authored paint. */
				if (sloped && vertex.normal.z != 0) vertex.normal = Normalize({vertex.normal.x-support[0]*vertex.normal.z,vertex.normal.y-support[1]*vertex.normal.z,vertex.normal.z});
				lifted.push_back(vertex);
			}
		}
	};
	auto clip = [&](const std::vector<Vertex> &polygon, float bound, bool above) {
		std::vector<Vertex> result;
		if (polygon.empty()) return result;
		Vertex previous = polygon.back();
		float previous_height = height(previous);
		bool previous_inside = above ? previous_height >= bound : previous_height <= bound;
		for (const auto &vertex : polygon) {
			float current_height = height(vertex);
			bool inside = above ? current_height >= bound : current_height <= bound;
			if (inside != previous_inside) {
				/* Voxel faces have constant palette/paint attributes. Only the
				 * position interpolates when a greedy face crosses a support join. */
				Vertex crossing = vertex;
				float t = (bound-previous_height)/(current_height-previous_height);
				crossing.position = previous.position+(vertex.position-previous.position)*t;
				result.push_back(crossing);
			}
			if (inside) result.push_back(vertex);
			previous = vertex; previous_height = current_height; previous_inside = inside;
		}
		return result;
	};
	for (size_t first = 0; first < mesh.vertices.size(); first += 3) {
		std::vector<Vertex> triangle(mesh.vertices.begin()+first,mesh.vertices.begin()+first+3);
		float low = std::min({height(triangle[0]),height(triangle[1]),height(triangle[2])});
		float high = std::max({height(triangle[0]),height(triangle[1]),height(triangle[2])});
		if (high <= 0 || low >= support[3]) emit(triangle,false);
		else if (low >= 0 && high <= support[3]) emit(triangle,true);
		else {
			emit(clip(triangle,0,false),false);
			emit(clip(clip(triangle,0,true),support[3],false),true);
			emit(clip(triangle,support[3],true),false);
		}
	}
	mesh.vertices = std::move(lifted);
	mesh.low = mesh.high = mesh.vertices.front().position;
	for (const auto &vertex : mesh.vertices) {
		const Vec3 &p = vertex.position;
		mesh.low = {std::min(mesh.low.x,p.x),std::min(mesh.low.y,p.y),std::min(mesh.low.z,p.z)};
		mesh.high = {std::max(mesh.high.x,p.x),std::max(mesh.high.y,p.y),std::max(mesh.high.z,p.z)};
	}
}

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
	bool lod_preserve_occupancy = false;
	std::array<float,4> support{}; ///< Additional column lift; source cells and paint remain original.
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
				auto restored = entry.reduction == 1 ? grid.Mesh(entry.merged) : grid.ReducedMesh(entry.reduction,entry.lod_preserve_occupancy);
				ApplyVoxelSupport(restored,entry.support);
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
