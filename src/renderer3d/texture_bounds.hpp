/* SPDX-License-Identifier: GPL-2.0-only */
/** @file texture_bounds.hpp Texture registration bounds, independent of mesh topology. */
#ifndef RENDERER3D_TEXTURE_BOUNDS_HPP
#define RENDERER3D_TEXTURE_BOUNDS_HPP

#include <algorithm>

namespace Renderer3D {

struct InkBounds {
	int left, top, width, height;
};

/** Some base-set sprites contain a detached one-pixel mark at the image edge. */
template <typename AlphaAt>
bool IsIsolatedEdgeTexel(int width, int height, int x, int y, const AlphaAt &alpha)
{
	if (x > 0 && y > 0 && x + 1 < width && y + 1 < height) return false;
	for (int dy = -1; dy <= 1; ++dy) {
		for (int dx = -1; dx <= 1; ++dx) {
			if (dx == 0 && dy == 0) continue;
			int nx = x + dx, ny = y + dy;
			if (nx >= 0 && ny >= 0 && nx < width && ny < height && alpha(nx, ny) != 0) return false;
		}
	}
	return true;
}

/** Ignore detached edge marks for registration, while retaining true tiny sprites. */
template <typename AlphaAt>
InkBounds FindInkBounds(int width, int height, const AlphaAt &alpha)
{
	int left = width, top = height, right = 0, bottom = 0;
	int all_left = width, all_top = height, all_right = 0, all_bottom = 0;
	for (int y = 0; y < height; ++y) {
		for (int x = 0; x < width; ++x) {
			if (alpha(x, y) == 0) continue;
			all_left = std::min(all_left, x); all_top = std::min(all_top, y);
			all_right = std::max(all_right, x + 1); all_bottom = std::max(all_bottom, y + 1);
			if (IsIsolatedEdgeTexel(width, height, x, y, alpha)) continue;
			left = std::min(left, x); top = std::min(top, y);
			right = std::max(right, x + 1); bottom = std::max(bottom, y + 1);
		}
	}
	if (right <= left) {
		left = all_left; top = all_top; right = all_right; bottom = all_bottom;
	}
	return {left, top, std::max(0, right - left), std::max(0, bottom - top)};
}

} // namespace Renderer3D
#endif
