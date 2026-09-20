/* SPDX-License-Identifier: GPL-2.0-only */
/** @file camera.hpp Orthographic camera in OpenTTD world units. */

#ifndef RENDERER3D_CAMERA_HPP
#define RENDERER3D_CAMERA_HPP

#include "geometry.hpp"

namespace Renderer3D {

struct ScreenPoint {
	float x, y, depth;
};

/** Fixed-pitch dimetric projection: (2(y-x), x+y-z), matching RemapCoords. */
struct Camera {
	Vec3 focus{};
	float pixels_per_unit = 1;
	int width = 0, height = 0;
	unsigned rotation = 0;

	Vec3 Rotate(Vec3 p) const
	{
		switch (rotation & 3) {
			case 1: return {-p.y, p.x, p.z};
			case 2: return {-p.x, -p.y, p.z};
			case 3: return {p.y, -p.x, p.z};
			default: return p;
		}
	}

	Vec3 Unrotate(Vec3 p) const
	{
		Camera inverse = *this;
		inverse.rotation = (4 - rotation) & 3;
		return inverse.Rotate(p);
	}

	ScreenPoint Project(Vec3 position) const
	{
		Vec3 p = Rotate(position - focus);
		return {width * 0.5f + 2 * (p.y - p.x) * pixels_per_unit,
			height * 0.5f + (p.x + p.y - p.z) * pixels_per_unit,
			p.x + p.y + 2 * p.z};
	}

	/** Intersect the screen ray with a horizontal plane at a given world Z. */
	Vec3 Unproject(float x, float y, float z) const
	{
		float sx = (x - width * 0.5f) / pixels_per_unit;
		float sy = (y - height * 0.5f) / pixels_per_unit + z - focus.z;
		Vec3 p{(sy - sx * 0.5f) * 0.5f, (sy + sx * 0.5f) * 0.5f, z - focus.z};
		return focus + Unrotate(p);
	}

	/** Conservative ground-plane bounds for a viewport and possible object heights. */
	std::array<Vec3, 8> FrustumCorners(float minimum_z, float maximum_z, float margin) const
	{
		return {Unproject(-margin, -margin, minimum_z), Unproject(width + margin, -margin, minimum_z),
			Unproject(-margin, height + margin, minimum_z), Unproject(width + margin, height + margin, minimum_z),
			Unproject(-margin, -margin, maximum_z), Unproject(width + margin, -margin, maximum_z),
			Unproject(-margin, height + margin, maximum_z), Unproject(width + margin, height + margin, maximum_z)};
	}
};

} // namespace Renderer3D

#endif
