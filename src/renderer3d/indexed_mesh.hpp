/* SPDX-License-Identifier: GPL-2.0-only */
/** @file indexed_mesh.hpp Exact immutable-vertex reuse without retriangulation. */
#ifndef RENDERER3D_INDEXED_MESH_HPP
#define RENDERER3D_INDEXED_MESH_HPP

#include "geometry.hpp"
#include <bit>
#include <cstdlib>
#include <stdexcept>
#include <type_traits>
#include <unordered_map>

namespace Renderer3D {

inline bool IndexImmutableMeshes()
{
	static const bool enabled = [] {
		const char *value = std::getenv("OPENTT3D_INDEXED_MESHES");
		return value == nullptr || std::string_view(value) != "0";
	}();
	return enabled;
}

struct IndexedMesh {
	std::vector<Vertex> vertices;
	std::vector<uint32_t> indices; ///< Empty means the original stream is smaller.
	std::vector<uint16_t> ShortIndices() const
	{
		/* Leave the fixed primitive-restart sentinel unused on GL contexts that
		 * support it; larger meshes retain the full 32-bit path. */
		if (vertices.size() > UINT16_MAX) return {};
		return {indices.begin(),indices.end()};
	}
};

/** Preserve every attribute bit, triangle order and provoking vertex. In
 * particular, palette/shadow boundaries, UV seams, picking IDs and signed zero
 * must never be welded merely because their positions agree. */
inline IndexedMesh IndexMesh(std::span<const Vertex> source)
{
	static_assert(sizeof(Vertex) == 20*sizeof(uint32_t)); // All fields are 32-bit, with no padding.
	static_assert(std::is_trivially_copyable_v<Vertex>);
	using Words = std::array<uint32_t,20>;
	struct Hash {
		std::span<const Vertex> source;
		size_t operator()(uint32_t index) const
		{
			uint64_t hash = 0xcbf29ce484222325ULL;
			for (uint32_t word : std::bit_cast<Words>(source[index])) { hash ^= word; hash *= 0x100000001b3ULL; }
			return static_cast<size_t>(hash ^ (hash>>32));
		}
	};
	struct Equal {
		std::span<const Vertex> source;
		bool operator()(uint32_t a, uint32_t b) const { return std::bit_cast<Words>(source[a]) == std::bit_cast<Words>(source[b]); }
	};
	if (source.size() > UINT32_MAX) throw std::length_error("Immutable mesh exceeds 32-bit index space");
	IndexedMesh result;
	if (source.empty()) return result;
	/* Keys reference the immutable input rather than storing another 80-byte
	 * vertex in each hash node. Temporary storage dies after the GPU upload. */
	std::unordered_map<uint32_t,uint32_t,Hash,Equal> unique(0,Hash{source},Equal{source});
	unique.reserve(source.size());
	result.vertices.reserve(source.size()/2);
	result.indices.reserve(source.size());
	for (size_t i = 0; i < source.size(); ++i) {
		auto [entry,inserted] = unique.try_emplace(static_cast<uint32_t>(i),static_cast<uint32_t>(result.vertices.size()));
		if (inserted) result.vertices.push_back(source[i]);
		result.indices.push_back(entry->second);
	}
	if (result.vertices.size()*sizeof(Vertex)+result.indices.size()*sizeof(uint32_t) >= source.size()*sizeof(Vertex)) return {};
	return result;
}

} // namespace Renderer3D
#endif
