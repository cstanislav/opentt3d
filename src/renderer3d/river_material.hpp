/* SPDX-License-Identifier: GPL-2.0-only */
/** @file river_material.hpp Lossless independent source-paint validation for river diagnostics. */
#ifndef RENDERER3D_RIVER_MATERIAL_HPP
#define RENDERER3D_RIVER_MATERIAL_HPP

#include "river_geometry.hpp"

namespace Renderer3D {

template <typename Pixel> bool SameRiverSourcePixel(const Pixel &a, const Pixel &b)
{
	return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a && a.m == b.m;
}

/** Owners 0/1 are absence/visible original paint and must stay byte-exact.
 * Only explicit relief-owned texels may expose the retained lower water stack.
 * Neutral brightness and exact source palette entries remain independent from
 * the rendered phase. This structural check is not source/artwork approval. */
template <typename Pixel> bool ValidOriginalRiverPaint(unsigned climate, std::span<const Pixel> source,
	std::span<const Pixel> water, std::span<const uint8_t> owners)
{
	if (climate >= 4 || source.empty() || source.size() != water.size() || source.size() != owners.size()) return false;
	unsigned relief = 0;
	for (size_t i = 0; i < source.size(); ++i) {
		const auto &a = source[i], &b = water[i];
		if (owners[i] == 0) {
			if (a.a != 0 || !SameRiverSourcePixel(a,b)) return false;
		} else if (owners[i] == 1) {
			if (a.a != 255 || !SameRiverSourcePixel(a,b)) return false;
		} else if (owners[i] == 2) {
			if (a.a != 255 || b.a != 255 || b.r != b.g || b.r != b.b ||
					!((b.m >= 245 && b.m <= (climate == 3 ? 249 : 254)) || b.m == (climate == 3 ? 157 : 201))) return false;
			++relief;
		} else return false;
	}
	return relief != 0;
}

} // namespace Renderer3D
#endif
