/* SPDX-License-Identifier: GPL-2.0-only */
/** @file atlas_allocator.hpp Stable-coordinate rectangular atlas packing. */
#ifndef RENDERER3D_ATLAS_ALLOCATOR_HPP
#define RENDERER3D_ATLAS_ALLOCATOR_HPP
#include <algorithm>
#include <limits>
#include <optional>
#include <vector>

namespace Renderer3D {

class AtlasAllocator {
public:
	struct Area { int x, y, width, height; };
	explicit AtlasAllocator(int size) : free{{0, 0, size, size}} {}
	/** Seed disjoint empty areas after an offline, height-sorted shelf repack. */
	void ResetFreeAreas(std::vector<Area> areas) { free = std::move(areas); }
	int Score(int width, int height) const
	{
		int score = std::numeric_limits<int>::max();
		for (auto rect : free) if (rect.width >= width && rect.height >= height) score = std::min(score, std::min(rect.width - width, rect.height - height));
		return score;
	}
	std::optional<Area> Allocate(int width, int height)
	{
		std::optional<Area> best;
		int score = std::numeric_limits<int>::max();
		for (auto rect : free) {
			if (rect.width < width || rect.height < height) continue;
			int candidate = std::min(rect.width - width, rect.height - height);
			if (candidate < score) { score = candidate; best = Area{rect.x, rect.y, width, height}; }
		}
		if (!best) return std::nullopt;
		Area used = *best;
		std::vector<Area> remaining;
		for (auto rect : free) {
			if (used.x >= rect.x + rect.width || used.x + width <= rect.x || used.y >= rect.y + rect.height || used.y + height <= rect.y) {
				remaining.push_back(rect);
				continue;
			}
			if (used.x > rect.x) remaining.push_back({rect.x, rect.y, used.x - rect.x, rect.height});
			if (used.y > rect.y) remaining.push_back({rect.x, rect.y, rect.width, used.y - rect.y});
			if (used.x + width < rect.x + rect.width) remaining.push_back({used.x + width, rect.y, rect.x + rect.width - used.x - width, rect.height});
			if (used.y + height < rect.y + rect.height) remaining.push_back({rect.x, used.y + height, rect.width, rect.y + rect.height - used.y - height});
		}
		free.clear();
		for (size_t i = 0; i < remaining.size(); ++i) {
			Area a = remaining[i];
			bool contained = false;
			for (size_t j = 0; j < remaining.size(); ++j) {
				if (i == j) continue;
				Area b = remaining[j];
				if (b.x <= a.x && b.y <= a.y && b.x + b.width >= a.x + a.width && b.y + b.height >= a.y + a.height &&
					(i > j || b.x != a.x || b.y != a.y || b.width != a.width || b.height != a.height)) { contained = true; break; }
			}
			if (!contained) free.push_back(a);
		}
		return best;
	}
private:
	std::vector<Area> free;
};

} // namespace Renderer3D
#endif
