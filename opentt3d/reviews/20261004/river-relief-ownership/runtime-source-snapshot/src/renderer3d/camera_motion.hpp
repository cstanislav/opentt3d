/* SPDX-License-Identifier: GPL-2.0-only */
/** @file camera_motion.hpp Frame-rate-independent presentation interpolation. */
#ifndef RENDERER3D_CAMERA_MOTION_HPP
#define RENDERER3D_CAMERA_MOTION_HPP
#include <algorithm>
#include <cmath>

namespace Renderer3D {

inline float SmoothValue(float current, float target, float rate, float seconds)
{
	return std::lerp(current, target, -std::expm1(-rate * std::max(0.0f, seconds)));
}

/** Angles are quarter turns; always take the short path through wraparound. */
inline float SmoothHeading(float current, float target, float rate, float seconds)
{
	return SmoothValue(current, current + std::remainder(target - current, 4.0f), rate, seconds);
}

} // namespace Renderer3D
#endif
