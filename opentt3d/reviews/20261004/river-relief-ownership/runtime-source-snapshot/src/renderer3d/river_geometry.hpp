/* SPDX-License-Identifier: GPL-2.0-only */
/** @file river_geometry.hpp Separate original river relief and doubled-terrain support. */
#ifndef RENDERER3D_RIVER_GEOMETRY_HPP
#define RENDERER3D_RIVER_GEOMETRY_HPP

#include "geometry.hpp"

namespace Renderer3D {

/** These are upstream slope bits, not dynamic sprite IDs or evidence of relief
 * in an arbitrary source. Flat water has no fabricated raised decoration. */
inline bool IsOriginalRiverReliefSlope(unsigned slope) { return slope == 3 || slope == 6 || slope == 9 || slope == 12; }

/** Only the observed complete Classic flat-first selector protocol is eligible.
 * A callback redirect, changed flags or alternate/custom owner retains originals. */
inline std::optional<unsigned> SelectOriginalRiverRelief(unsigned slope, uint32_t base, uint32_t image,
	unsigned requested, unsigned resolved, unsigned flags, bool original, bool complete)
{
	if (!original || !complete || !IsOriginalRiverReliefSlope(slope) || flags != 1 || base == 0 || base > 0xFFFFFFU-4) return {};
	unsigned offset = slope == 6 ? 1 : slope == 12 ? 2 : slope == 3 ? 3 : 4;
	if (requested != offset || resolved != offset || image != base+offset) return {};
	return slope;
}

template <typename HasOwner> bool CompleteOriginalRiverReliefFamily(unsigned climate, HasOwner has_owner)
{
	if (climate >= 4) return false;
	for (unsigned slope : {3U,6U,9U,12U}) if (!has_owner(slope,climate)) return false;
	return true;
}

/** Add only the extra displayed slope elevation. Column heights, footprint,
 * original face paint and the independently animated water never scale. */
inline std::array<float,4> OriginalRiverReliefSupport(unsigned slope)
{
	const float extra = TERRAIN_HEIGHT_SCALE-1;
	switch (slope) {
		case 3: return {0.5f*extra,0,0,8*extra};
		case 6: return {0,0.5f*extra,0,8*extra};
		case 9: return {0,-0.5f*extra,8*extra,8*extra};
		case 12: return {-0.5f*extra,0,8*extra,8*extra};
		default: throw std::out_of_range("Invalid original river relief slope");
	}
}

} // namespace Renderer3D
#endif
