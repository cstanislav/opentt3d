/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_packed_mesh.hpp Lossless palette-voxel vertex streams. */
#ifndef RENDERER3D_VOXEL_PACKED_MESH_HPP
#define RENDERER3D_VOXEL_PACKED_MESH_HPP

#include "geometry.hpp"
#include <bit>
#include <cstdlib>
#include <map>
#include <memory>
#include <numeric>
#include <unordered_map>

namespace Renderer3D {

struct PackedVoxelMesh {
	/* Six vec4 records: origin/company, step, coordinate/normal bit widths,
	 * colour/opacity, texture region, surface/object/texture YZ; then normals. */
	std::vector<uint32_t> format;
	std::vector<uint32_t> vertices;
	bool pixel_cull = false;
	bool StandardPalette() const
	{
		const auto one = std::bit_cast<uint32_t>(1.0f);
		return format[12] == one && format[13] == one && format[14] == one && format[15] == one &&
			format[16] == 0 && format[17] == 0 && format[18] == one && format[19] == one &&
			format[20] == (static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT) && format[21] == 0 &&
			format[22] == std::bit_cast<uint32_t>(0.5f) && format[23] == std::bit_cast<uint32_t>(-3.0f);
	}
	Vertex Decode(uint32_t packed) const
	{
		Vertex result;
		std::array<float,3> position{};
		unsigned shift = 0;
		for (unsigned axis = 0; axis < 3; ++axis) {
			unsigned bits = format[8+axis], coordinate = (packed>>shift)&((1U<<bits)-1);
			volatile float scaled = static_cast<float>(coordinate)*std::bit_cast<float>(format[4+axis]);
			position[axis] = scaled+std::bit_cast<float>(format[axis]);
			shift += bits;
		}
		result.position = {position[0],position[1],position[2]};
		unsigned normal = (packed>>shift)&((1U<<format[11])-1);
		result.normal = {std::bit_cast<float>(format[24+normal*4]),std::bit_cast<float>(format[25+normal*4]),std::bit_cast<float>(format[26+normal*4])};
		unsigned colour = packed>>(shift+format[11]);
		result.texture = {(colour+0.5f)/256,std::bit_cast<float>(format[22]),std::bit_cast<float>(format[23])};
		result.colour = {std::bit_cast<float>(format[12]),std::bit_cast<float>(format[13]),std::bit_cast<float>(format[14])};
		result.opacity = std::bit_cast<float>(format[15]);
		result.company_colour = std::bit_cast<float>(format[3]);
		result.texture_region = {std::bit_cast<float>(format[16]),std::bit_cast<float>(format[17]),std::bit_cast<float>(format[18]),std::bit_cast<float>(format[19])};
		result.surface = static_cast<SurfaceMode>(format[20]); result.object_id = format[21];
		return result;
	}
};

/** An encoding is accepted only if every reconstructed vertex word agrees with
 * its source, including signed zeros, exact normals and all material fields. */
inline std::shared_ptr<const PackedVoxelMesh> PackVoxelMesh(std::span<const Vertex> source, std::array<int,3> size, Vec3 origin, Vec3 step, bool pixel_cull = false)
{
	if (source.empty() || (static_cast<uint32_t>(source.front().surface)&15U) != static_cast<uint32_t>(SurfaceMode::Palette)) return {};
	using Words = std::array<uint32_t,20>;
	static_assert(sizeof(Vertex) == sizeof(Words));
	auto packed = std::make_shared<PackedVoxelMesh>();
	packed->pixel_cull = pixel_cull;
	auto &format = packed->format;
	format.resize(24);
	const auto &first = source.front();
	std::array<float,3> o{origin.x,origin.y,origin.z}, s{step.x,step.y,step.z};
	unsigned position_bits = 0;
	for (unsigned axis = 0; axis < 3; ++axis) {
		if (size[axis] <= 0 || size[axis] > 1024 || !std::isfinite(o[axis]) || !std::isfinite(s[axis]) || s[axis] <= 0) return {};
		format[axis] = std::bit_cast<uint32_t>(o[axis]); format[4+axis] = std::bit_cast<uint32_t>(s[axis]);
		format[8+axis] = std::bit_width(static_cast<unsigned>(size[axis]));
		position_bits += format[8+axis];
	}
	if (position_bits+8 > 32) return {};
	format[3] = std::bit_cast<uint32_t>(first.company_colour);
	format[12] = std::bit_cast<uint32_t>(first.colour.r); format[13] = std::bit_cast<uint32_t>(first.colour.g); format[14] = std::bit_cast<uint32_t>(first.colour.b);
	format[15] = std::bit_cast<uint32_t>(first.opacity);
	format[16] = std::bit_cast<uint32_t>(first.texture_region.left); format[17] = std::bit_cast<uint32_t>(first.texture_region.top);
	format[18] = std::bit_cast<uint32_t>(first.texture_region.right); format[19] = std::bit_cast<uint32_t>(first.texture_region.bottom);
	format[20] = static_cast<uint32_t>(first.surface); format[21] = first.object_id;
	format[22] = std::bit_cast<uint32_t>(first.texture.y); format[23] = std::bit_cast<uint32_t>(first.texture.z);
	std::map<std::array<uint32_t,3>,unsigned> normals;
	for (const auto &vertex : source) {
		auto key = std::bit_cast<std::array<uint32_t,3>>(vertex.normal);
		auto [entry,inserted] = normals.try_emplace(key,static_cast<unsigned>(normals.size()));
		if (inserted) { format.insert(format.end(),key.begin(),key.end()); format.push_back(0); }
		if (position_bits+std::bit_width(static_cast<unsigned>(normals.size()-1))+8 > 32) return {};
	}
	format[11] = std::bit_width(static_cast<unsigned>(normals.size()-1));
	packed->vertices.reserve(source.size());
	bool exact_products = true;
	for (const auto &vertex : source) {
		std::array<float,3> p{vertex.position.x,vertex.position.y,vertex.position.z};
		uint32_t word = 0;
		unsigned shift = 0;
		for (unsigned axis = 0; axis < 3; ++axis) {
			if (!std::isfinite(p[axis])) return {};
			double coordinate = std::round((static_cast<double>(p[axis])-o[axis])/s[axis]);
			if (coordinate < 0 || coordinate > size[axis]) return {};
			float product = static_cast<float>(coordinate)*s[axis];
			exact_products &= static_cast<double>(product) == coordinate*static_cast<double>(s[axis]);
			word |= static_cast<uint32_t>(coordinate)<<shift;
			shift += format[8+axis];
		}
		unsigned normal = normals.at(std::bit_cast<std::array<uint32_t,3>>(vertex.normal));
		word |= normal<<shift; shift += format[11];
		if (!std::isfinite(vertex.texture.x) || vertex.texture.x < 0 || vertex.texture.x >= 1) return {};
		word |= static_cast<uint32_t>(vertex.texture.x*256)<<shift;
		if (std::bit_cast<Words>(packed->Decode(word)) != std::bit_cast<Words>(vertex)) return {};
		packed->vertices.push_back(word);
	}
	format[7] = exact_products ? 1U : 0U;
	return packed;
}

/** Recover an exact dyadic coordinate lattice from already-authored geometry.
 * This is storage encoding only; the final full-word roundtrip remains required. */
inline std::shared_ptr<const PackedVoxelMesh> AutoPackVoxelMesh(std::span<const Vertex> source, bool pixel_cull = false)
{
	if (source.empty() || (static_cast<uint32_t>(source.front().surface)&15U) != static_cast<uint32_t>(SurfaceMode::Palette)) return {};
	std::array<float,3> low{INFINITY,INFINITY,INFINITY}, high{-INFINITY,-INFINITY,-INFINITY};
	for (const auto &vertex : source) {
		std::array<float,3> point{vertex.position.x,vertex.position.y,vertex.position.z};
		for (unsigned axis = 0; axis < 3; ++axis) {
			if (!std::isfinite(point[axis])) return {};
			low[axis] = std::min(low[axis],point[axis]); high[axis] = std::max(high[axis],point[axis]);
		}
	}
	std::array<uint32_t,3> units{};
	for (const auto &vertex : source) {
		std::array<float,3> point{vertex.position.x,vertex.position.y,vertex.position.z};
		for (unsigned axis = 0; axis < 3; ++axis) {
			double offset = (static_cast<double>(point[axis])-low[axis])*256;
			if (offset < 0 || offset > UINT32_MAX || offset != std::floor(offset)) return {};
			units[axis] = std::gcd(units[axis],static_cast<uint32_t>(offset));
		}
	}
	std::array<float,3> step{};
	std::array<int,3> size{};
	for (unsigned axis = 0; axis < 3; ++axis) {
		step[axis] = units[axis] == 0 ? 1.0f : units[axis]/256.0f;
		double extent = (static_cast<double>(high[axis])-low[axis])/step[axis];
		if (extent > 1024) return {};
		size[axis] = std::max(1,static_cast<int>(std::ceil(extent)));
	}
	return PackVoxelMesh(source,size,{low[0],low[1],low[2]},{step[0],step[1],step[2]},pixel_cull);
}

inline bool VoxelPixelCullEnabled()
{
	static const bool enabled = [] { const char *setting = std::getenv("OPENTT3D_VOXEL_CULL"); return setting != nullptr && std::string_view(setting) == "1"; }();
	return enabled;
}

inline bool PackedVoxelMeshesEnabled()
{
	static const bool enabled = [] { const char *setting = std::getenv("OPENTT3D_VOXEL_PACKED"); return setting != nullptr && std::string_view(setting) == "1"; }();
	return enabled || VoxelPixelCullEnabled();
}

struct IndexedPackedVoxelMesh {
	std::vector<uint32_t> vertices;
	std::vector<uint16_t> indices;
};

struct PackedVoxelLookup {
	std::vector<uint32_t> vertices, indices;
	unsigned bits = 0;
};

inline PackedVoxelLookup MakePackedVoxelLookup(std::span<const uint32_t> source)
{
	PackedVoxelLookup result;
	if (source.empty()) return result;
	std::unordered_map<uint32_t,uint32_t> unique;
	result.indices.reserve(source.size());
	for (uint32_t word : source) {
		auto [entry,inserted] = unique.try_emplace(word,static_cast<uint32_t>(result.vertices.size()));
		if (inserted) result.vertices.push_back(word);
		result.indices.push_back(entry->second);
	}
	result.bits = std::max<unsigned>(1,std::bit_width(static_cast<unsigned>(result.vertices.size()-1)));
	return result;
}

/** Index a retained original triangle stream without sharing vertices across
 * distinct instances. Chunk resets preserve the current instance identity. */
class IndexedVoxelVisibility {
	struct Reference { uint64_t generation = 0; uint32_t index = 0; };
	const PackedVoxelLookup &lookup;
	std::vector<Reference> references;
	uint64_t generation = 0;
	uint32_t instance = 0;
	void Advance()
	{
		if (++generation == 0) { for (auto &reference : references) reference.generation = 0; generation = 1; }
	}
public:
	std::vector<std::array<uint32_t,2>> vertices; ///< Original packed word and local instance.
	std::vector<uint32_t> indices;
	explicit IndexedVoxelVisibility(const PackedVoxelLookup &lookup) : lookup(lookup), references(lookup.vertices.size()) { Advance(); }
	void BeginInstance(uint32_t value) { instance = value; Advance(); }
	void Clear() { vertices.clear(); indices.clear(); Advance(); }
	void Add(uint64_t triangle)
	{
		uint64_t mask = (uint64_t{1}<<lookup.bits)-1;
		for (unsigned corner = 0; corner < 3; ++corner) {
			size_t source = (triangle>>(corner*lookup.bits))&mask;
			auto &reference = references.at(source);
			if (reference.generation != generation) {
				if (vertices.size() >= UINT32_MAX) throw std::length_error("Indexed voxel visibility exceeds its reference range");
				reference = {generation,static_cast<uint32_t>(vertices.size())};
				vertices.push_back({lookup.vertices[source],instance});
			}
			indices.push_back(reference.index);
		}
	}
};

inline IndexedPackedVoxelMesh IndexPackedVoxelMesh(std::span<const uint32_t> source)
{
	IndexedPackedVoxelMesh result;
	std::unordered_map<uint32_t,uint16_t> unique;
	unique.reserve(std::min<size_t>(source.size(),UINT16_MAX));
	result.indices.reserve(source.size());
	for (uint32_t word : source) {
		auto found = unique.find(word);
		if (found == unique.end()) {
			if (result.vertices.size() == UINT16_MAX) return {};
			found = unique.emplace(word,static_cast<uint16_t>(result.vertices.size())).first;
			result.vertices.push_back(word);
		}
		result.indices.push_back(found->second);
	}
	if (result.vertices.size()*sizeof(uint32_t)+result.indices.size()*sizeof(uint16_t) >= source.size()*sizeof(uint32_t)) return {};
	return result;
}

inline auto &PackedVoxelMeshRegistry()
{
	static std::unordered_map<const std::vector<Vertex> *,std::shared_ptr<const PackedVoxelMesh>> meshes;
	return meshes;
}

/** Call only after an immutable procedural mesh reaches its stable owner. */
inline void RegisterPackedVoxelMesh(const std::vector<Vertex> &mesh, bool pixel_cull = false)
{
	if (!PackedVoxelMeshesEnabled() || mesh.empty()) return;
	if (auto packed = AutoPackVoxelMesh(mesh,pixel_cull)) PackedVoxelMeshRegistry().emplace(&mesh,std::move(packed));
}

inline const PackedVoxelMesh *FindPackedVoxelMesh(const std::vector<Vertex> *source)
{
	if (!PackedVoxelMeshesEnabled()) return nullptr;
	auto &meshes = PackedVoxelMeshRegistry();
	auto found = meshes.find(source);
	return found == meshes.end() ? nullptr : found->second.get();
}

} // namespace Renderer3D
#endif
