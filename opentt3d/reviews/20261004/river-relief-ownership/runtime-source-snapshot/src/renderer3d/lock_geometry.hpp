/* SPDX-License-Identifier: GPL-2.0-only */
/** @file lock_geometry.hpp Original lock owners and doubled-terrain support only. */
#ifndef RENDERER3D_LOCK_GEOMETRY_HPP
#define RENDERER3D_LOCK_GEOMETRY_HPP

#include "geometry.hpp"

namespace Renderer3D {

/** Original sprite order is SE,NE,SW,NW, not the public direction enum order. */
inline std::optional<unsigned> OriginalLockWallOrdinal(unsigned part, unsigned direction, unsigned face, unsigned elevation)
{
	if (part >= 3 || direction >= 4 || face >= 2 || elevation >= 2) return {};
	constexpr unsigned directions[] = {1,0,2,3};
	return elevation*24+part*8+face*4+directions[direction];
}

template <typename HasOwner>
bool CompleteOriginalLockWallFamily(unsigned climate, HasOwner has_owner)
{
	if (climate >= 4) return false;
	for (unsigned owner = 0; owner < 48; ++owner) if (!has_owner(owner,climate)) return false;
	return true;
}

/** Classic's extra source chooses the elevated GROUP before per-wall offsets;
 * the default source instead adds24 to each offset. Both retain the original
 * undoubled upper-part threshold. This uses the existing selection, not a second
 * GRF callback or a fixed/load-specific dynamic sprite ID. */
inline std::optional<uint32_t> OriginalClassicLockFamilyBase(uint32_t selected_base, bool default_source, unsigned part, int source_height)
{
	if (part >= 3 || source_height < 0 || source_height%8 != 0) return {};
	unsigned group_offset = !default_source && source_height > (part == 2 ? 8 : 0) ? 24 : 0;
	if (selected_base < group_offset) return {};
	return selected_base-group_offset;
}

/** Both already-selected sources must belong to the same original elevation.
 * Never rerun feature/offset callbacks or infer ownership from sorting extents. */
inline std::optional<std::array<unsigned,2>> SelectOriginalLockWalls(unsigned part, unsigned direction,
	uint32_t base, const std::array<uint32_t,2> &images, bool original_family, bool complete_family)
{
	if (!original_family || !complete_family || part >= 3 || direction >= 4) return {};
	for (unsigned elevation = 0; elevation < 2; ++elevation) {
		std::array<unsigned,2> owners{*OriginalLockWallOrdinal(part,direction,0,elevation),*OriginalLockWallOrdinal(part,direction,1,elevation)};
		if (images[0] >= base && images[1] >= base && images[0]-base == owners[0] && images[1]-base == owners[1]) return owners;
	}
	return {};
}

/** Raise each middle-wall column by the additional rendered terrain height.
 * Its original column height, XY registration and separate upper/lower owners
 * remain intact; multiplying the object's entire Z dimension would be wrong. */
inline std::array<float,4> OriginalLockMiddleSupport(unsigned direction)
{
	if (direction >= 4) throw std::out_of_range("Invalid original lock direction");
	const float extra = TERRAIN_HEIGHT_SCALE-1;
	switch (direction) {
		case 0: return {-0.5f*extra,0,8*extra,8*extra};
		case 1: return {0,0.5f*extra,0,8*extra};
		case 2: return {0.5f*extra,0,0,8*extra};
		default: return {0,-0.5f*extra,8*extra,8*extra};
	}
}
}
#endif
