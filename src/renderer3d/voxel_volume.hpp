/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_volume.hpp Immutable full-cell volume data and reference ray queries. */
#ifndef RENDERER3D_VOXEL_VOLUME_HPP
#define RENDERER3D_VOXEL_VOLUME_HPP

#include "geometry.hpp"
#include <bit>
#include <cstdlib>
#include <memory>
#include <unordered_map>

namespace Renderer3D {

struct VoxelRayHit {
	double distance;
	std::array<int,3> cell;
	unsigned face;
	uint8_t colour;
};

/** Word-addressable, backend-independent volume. Header words0..2 are grid size,
 * 3 material count,4..6 origin,7 cell offset,8..10 cell step,11 material offset,
 * 12..14 occupied lower cell bound,16..18 upper bound,20 surface-acceleration offset,
 * 21..22 immutable floating one/zero for exact shader arithmetic.
 * Floats retain their bits. Surface words pack16-bit material,6-bit exposed-face
 * mask and8-bit Chebyshev distance to the nearest exposed cell.
 * Two16-bit cell material IDs share one word; each material has six8-bit colours
 * packed into two words. Cell0 remains empty. The original mesh stays available. */
struct VoxelVolume {
	static constexpr unsigned HEADER_WORDS = 24;
	std::vector<uint32_t> words;
	std::vector<Vertex> bounds;
	std::vector<Vertex> slices;

	std::array<int,3> Size() const { return {static_cast<int>(words.at(0)),static_cast<int>(words.at(1)),static_cast<int>(words.at(2))}; }
	Vec3 Origin() const { return {std::bit_cast<float>(words.at(4)),std::bit_cast<float>(words.at(5)),std::bit_cast<float>(words.at(6))}; }
	Vec3 Step() const { return {std::bit_cast<float>(words.at(8)),std::bit_cast<float>(words.at(9)),std::bit_cast<float>(words.at(10))}; }
	uint16_t Get(int x, int y, int z) const
	{
		auto size = Size();
		if (x < 0 || y < 0 || z < 0 || x >= size[0] || y >= size[1] || z >= size[2]) return 0;
		size_t index = (static_cast<size_t>(z)*size[1]+y)*size[0]+x;
		return (words.at(words.at(7)+(index>>1)) >> (16*(index&1))) & 0xFFFFU;
	}
	uint8_t Colour(uint16_t material, unsigned face) const
	{
		if (material == 0 || material > words.at(3) || face >= 6) throw std::out_of_range("Invalid voxel volume material face");
		return (words.at(words.at(11)+2*(material-1)+(face>>2)) >> (8*(face&3))) & 0xFFU;
	}

	/** Query the first front-facing occupied-cell entry. Starting within a solid
	 * does not turn its back faces into visible surfaces; later disjoint solids
	 * are still considered. The parameter follows the supplied, unnormalized ray. */
	std::optional<VoxelRayHit> Trace(Vec3 ray_origin, Vec3 ray_direction, double minimum = 0, double maximum = INFINITY) const
	{
		if (!std::isfinite(ray_origin.x+ray_origin.y+ray_origin.z+ray_direction.x+ray_direction.y+ray_direction.z) ||
				Dot(ray_direction,ray_direction) == 0 || !std::isfinite(minimum) || std::isnan(maximum) || maximum < minimum) throw std::invalid_argument("Invalid voxel ray");
		Vec3 origin = Origin(), step = Step();
		std::array<double,3> o{(static_cast<double>(ray_origin.x)-origin.x)/step.x,(static_cast<double>(ray_origin.y)-origin.y)/step.y,(static_cast<double>(ray_origin.z)-origin.z)/step.z};
		std::array<double,3> d{static_cast<double>(ray_direction.x)/step.x,static_cast<double>(ray_direction.y)/step.y,static_cast<double>(ray_direction.z)/step.z};
		double enter = -INFINITY, leave = maximum;
		unsigned face = 0;
		for (unsigned axis = 0; axis < 3; ++axis) {
			double low = words.at(12+axis), high = words.at(16+axis);
			if (d[axis] == 0) { if (o[axis] < low || o[axis] >= high) return {}; continue; }
			double a = (low-o[axis])/d[axis], b = (high-o[axis])/d[axis];
			if (a > b) std::swap(a,b);
			if (a >= enter) { enter = a; face = axis*2+(d[axis] < 0); }
			leave = std::min(leave,b);
		}
		double time = std::max(enter,minimum);
		if (!(time < leave)) return {};
		std::array<int,3> cell{}, direction{};
		std::array<double,3> next{}, delta{};
		for (unsigned axis = 0; axis < 3; ++axis) {
			direction[axis] = d[axis] > 0 ? 1 : d[axis] < 0 ? -1 : 0;
			double p = o[axis]+d[axis]*time;
			if (direction[axis] != 0) p = std::nextafter(p,direction[axis] > 0 ? INFINITY : -INFINITY);
			cell[axis] = static_cast<int>(std::floor(p));
			if (direction[axis] == 0) { next[axis] = delta[axis] = INFINITY; continue; }
			double boundary = cell[axis]+(direction[axis] > 0);
			next[axis] = (boundary-o[axis])/d[axis];
			delta[axis] = std::abs(1/d[axis]);
		}
		bool entering = enter >= minimum;
		auto size = Size();
		for (unsigned visited = 0; visited < static_cast<unsigned>(size[0]+size[1]+size[2]+3) && time < leave; ++visited) {
			uint16_t material = Get(cell[0],cell[1],cell[2]);
			if (material == 0) entering = true;
			else if (entering) return VoxelRayHit{time,cell,face,Colour(material,face)};
			unsigned axis = next[0] < next[1] ? 0 : 1;
			if (next[2] <= next[axis]) axis = 2;
			time = next[axis]; next[axis] += delta[axis];
			cell[axis] += direction[axis]; face = axis*2+(direction[axis] < 0);
		}
		return {};
	}
};

inline bool VoxelSlicesEnabled()
{
	static const bool enabled = [] { const char *setting = std::getenv("OPENTT3D_VOXEL_SLICES"); return setting != nullptr && std::string_view(setting) == "1"; }();
	return enabled;
}

inline bool VoxelVolumesEnabled()
{
	static const bool enabled = [] { const char *setting = std::getenv("OPENTT3D_VOXEL_VOLUMES"); return setting != nullptr && std::string_view(setting) == "1"; }();
	return enabled || VoxelSlicesEnabled();
}

inline auto &VoxelVolumeRegistry()
{
	static std::unordered_map<const std::vector<Vertex> *,std::shared_ptr<const VoxelVolume>> volumes;
	return volumes;
}

inline const VoxelVolume *FindVoxelVolume(const std::vector<Vertex> *mesh)
{
	if (!VoxelVolumesEnabled()) return nullptr;
	auto &volumes = VoxelVolumeRegistry();
	auto found = volumes.find(mesh);
	return found == volumes.end() ? nullptr : found->second.get();
}

inline bool VolumeInstanceCompatible(const InstanceData &data)
{
	return data.origin_opacity[3] == 1 && data.mirror_layer_heading[2] == 0 && data.mirror_layer_heading[3] == 0 && data.pitch[1] == 0 &&
		data.identity[3] == 2 && (static_cast<uint32_t>(data.identity[1])&79U) == 69U && (static_cast<uint32_t>(data.identity[2])&17U) == 1U &&
		data.scale_center[0] > 0 && data.scale_center[1] > 0;
}

/** Front-face volume proxies need a completely unclipped near boundary. Keep
 * the ordinary mesh path for eye/near-plane intersections, including open
 * interiors. Positive axis scales and zero yaw are checked by the caller. */
inline bool VolumeOutsideNearPlane(const VoxelVolume &volume, const InstanceData &data, const ClipVolume &frustum)
{
	Vec3 origin = volume.Origin(), step = volume.Step();
	std::array<float,3> o{origin.x,origin.y,origin.z}, s{step.x,step.y,step.z};
	const auto &plane = frustum.planes[4];
	std::array<float,3> focus{frustum.origin.x,frustum.origin.y,frustum.origin.z};
	double nearest = plane[3];
	for (unsigned axis = 0; axis < 3; ++axis) {
		float cell = plane[axis] < 0 ? volume.words.at(16+axis)+1.0f : static_cast<float>(volume.words.at(12+axis))-1.0f;
		float point = o[axis]+cell*s[axis];
		float local = axis < 2 ? (point-data.scale_center[axis+2])*data.scale_center[0] : point*data.scale_center[1];
		float world = data.origin_opacity[axis]+local;
		nearest += static_cast<double>(plane[axis])*(world-focus[axis]);
	}
	return nearest > 0.01;
}

} // namespace Renderer3D
#endif
