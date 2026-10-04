/* SPDX-License-Identifier: GPL-2.0-only */
/** @file camera.hpp Perspective camera calibrated to OpenTTD's familiar view angle. */

#ifndef RENDERER3D_CAMERA_HPP
#define RENDERER3D_CAMERA_HPP

#include "geometry.hpp"
#include <limits>
#include <numbers>

namespace Renderer3D {

struct ScreenPoint {
	float x, y, depth;
	bool visible = true;
};

/** Rectilinear pinhole camera with square pixels. OpenTTD's height coordinates
 * are sprite-height units, not ground-distance units. Calibrating that scale
 * preserves the familiar tile proportions without an anamorphic projection. */
struct Camera {
	bool operator==(const Camera &) const = default;
	Vec3 focus{};
	float pixels_per_unit = 1;
	int width = 0, height = 0;
	float rotation = 0; ///< Continuous yaw in quarter turns; retained when dragging ends.
	float vertical_fov = 24;
	int image_width = 0, image_height = 0; ///< Full image size; zero means the viewport size.
	int crop_x = 0, crop_y = 0; ///< Top-left of this framebuffer in the full image.
	float pitch = 30; ///< Degrees below the horizon.
	bool first_person = false; ///< In this mode focus is the eye, rather than an orbit pivot.
	uint32_t hidden_object = 0; ///< Hide the camera vehicle's body in a cab view.
	uint32_t tunnel_entrance = UINT32_MAX; ///< Presentation-only hint for Cab/inspection inside a tunnel.
	Vec3 focus_offset{}; ///< Low focus bits, applied after subtracting the coarse world origin.
	static constexpr float WORLD_Z_SCALE = 0.408248290463863f;
	static constexpr float INV_SQRT2 = 0.707106781186548f;
	static constexpr float ART_SCALE = 2.82842712474619f;
	int FilmWidth() const { return image_width > 0 ? image_width : width; }
	int FilmHeight() const { return image_height > 0 ? image_height : height; }

	/** Restrict rasterization without changing the eye or the projection. */
	Camera Cropped(int x, int y, int crop_width, int crop_height) const
	{
		Camera result = *this;
		result.image_width = this->FilmWidth();
		result.image_height = this->FilmHeight();
		result.crop_x += x;
		result.crop_y += y;
		result.width = crop_width;
		result.height = crop_height;
		return result;
	}

	Vec3 Rotate(Vec3 p) const
	{
		float angle = rotation * std::numbers::pi_v<float> * 0.5f;
		float cs = std::cos(angle), sn = std::sin(angle);
		return {p.x * cs - p.y * sn, p.x * sn + p.y * cs, p.z};
	}

	Vec3 Unrotate(Vec3 p) const
	{
		Camera inverse = *this;
		inverse.rotation = -rotation;
		return inverse.Rotate(p);
	}

	static Vec3 Physical(Vec3 p) { return {p.x, p.y, p.z * WORLD_Z_SCALE}; }
	static Vec3 World(Vec3 p) { return {p.x, p.y, p.z / WORLD_Z_SCALE}; }
	static Vec3 Right() { return {-INV_SQRT2, INV_SQRT2, 0}; }
	Vec3 Up() const
	{
		float angle = pitch * std::numbers::pi_v<float> / 180;
		return {-std::sin(angle) * INV_SQRT2, -std::sin(angle) * INV_SQRT2, std::cos(angle)};
	}
	Vec3 Back() const
	{
		float angle = pitch * std::numbers::pi_v<float> / 180;
		return {std::cos(angle) * INV_SQRT2, std::cos(angle) * INV_SQRT2, std::sin(angle)};
	}
	float FocalPixels() const { return std::max(1, FilmHeight()) / (2 * std::tan(vertical_fov * std::numbers::pi_v<float> / 360)); }
	float Distance() const
	{
		return first_person ? 0 : FocalPixels() / (ART_SCALE * pixels_per_unit);
	}
	float Near() const { return 0.05f; } // Reversed floating depth supports a stable near plane at every dolly distance.
	/** Keep a small displacement instead of rounding it into a large world position. */
	void SetFocusRelative(Vec3 origin, Vec3 displacement)
	{
		focus = origin+displacement;
		Vec3 rounded_displacement = focus-origin;
		focus_offset = (origin-(focus-rounded_displacement))+(displacement-rounded_displacement);
	}
	void TranslateFocus(Vec3 displacement) { SetFocusRelative(focus,focus_offset+displacement); }
	Vec3 Eye() const { return focus + (focus_offset+Unrotate(World(Back() * Distance()))); }
	float PixelScaleAt(Vec3 position) const
	{
		float depth = Distance() - Dot(Physical(Rotate((position - focus)-focus_offset)), Back());
		return FocalPixels() / (ART_SCALE * std::max(Near(), depth));
	}

	ScreenPoint Project(Vec3 position) const
	{
		Vec3 p = Physical(Rotate((position - focus)-focus_offset));
		float depth = Distance() - Dot(p, Back());
		float magnification = FocalPixels() / std::max(depth, 0.0001f);
		return {FilmWidth() * 0.5f + Dot(p, Right()) * magnification - crop_x,
			FilmHeight() * 0.5f - Dot(p, Up()) * magnification - crop_y, depth,
			depth >= Near()};
	}

	Ray ScreenRay(float x, float y) const
	{
		float sx = (x + crop_x - FilmWidth() * 0.5f) / FocalPixels();
		float sy = (FilmHeight() * 0.5f - y - crop_y) / FocalPixels();
		return {Eye(), Normalize(Unrotate(World(Right() * sx + Up() * sy - Back())))};
	}

	/** Move parallel to the ground until a world point projects to the given pixel. */
	std::optional<Vec3> FocusForAnchor(Vec3 anchor, float x, float y, Vec3 *residual = nullptr) const
	{
		Camera local = *this;
		local.focus = {}; local.focus_offset = {};
		auto current = local.ScreenRay(x, y).AtZ((anchor.z-focus.z)-focus_offset.z);
		if (!current.has_value()) return std::nullopt;
		local.SetFocusRelative(anchor,*current*-1);
		if (residual != nullptr) *residual = local.focus_offset;
		return local.focus;
	}

	/** Rigid orbit about any picked point, preserving its pixel and eye distance.
	 * The pivot need not be at the film centre or at the focus altitude. */
	Camera Orbited(Vec3 pivot, float yaw_delta, float pitch_delta) const
	{
		Vec3 relative = Physical(Rotate((focus - pivot)+focus_offset));
		Vec3 components{Dot(relative, Right()), Dot(relative, Up()), Dot(relative, Back())};
		Camera result = *this;
		result.rotation = std::fmod(rotation + yaw_delta, 4.0f);
		if (result.rotation < 0) result.rotation += 4;
		result.pitch = std::clamp(pitch + pitch_delta, 3.0f, 89.0f);
		result.SetFocusRelative(pivot,result.Unrotate(World(Right() * components.x + result.Up() * components.y + result.Back() * components.z)));
		return result;
	}

	/** Infinite-far, reversed-depth matrix in OpenGL clip coordinates. Vulkan
	 * emits Near directly as clip Z to avoid subtracting large depth values. */
	std::array<float, 16> Matrix() const
	{
		std::array<float, 16> result{};
		const float d = Distance();
		const float focal = FocalPixels();
		const Vec3 right = Right(), up = Up(), back = Back();
		const float offset_x = (FilmWidth() - 2.0f * crop_x - width) / width;
		const float offset_y = (2.0f * crop_y + height - FilmHeight()) / height;
		const Vec3 basis[] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
		for (int column = 0; column < 3; ++column) {
			Vec3 p = Physical(Rotate(basis[column]));
			float depth = -Dot(p, back);
			result[column * 4] = 2 * Dot(p, right) * focal / width + offset_x * depth;
			result[column * 4 + 1] = 2 * Dot(p, up) * focal / height + offset_y * depth;
			result[column * 4 + 2] = -depth;
			result[column * 4 + 3] = depth;
		}
		Vec3 shift = Physical(Rotate(focus_offset*-1));
		float depth = d-Dot(shift,back);
		result[12] = offset_x*depth+2*Dot(shift,right)*focal/width;
		result[13] = offset_y*depth+2*Dot(shift,up)*focal/height;
		result[14] = 2 * Near() - depth;
		result[15] = depth;
		return result;
	}

	ClipVolume Frustum(float pixel_margin = 0) const
	{
		ClipVolume result{focus, {}};
		auto matrix = Matrix();
		for (unsigned axis = 0; axis < 2; ++axis) {
			float margin = axis == 0 ? 2 * pixel_margin / width : axis == 1 ? 2 * pixel_margin / height : 0;
			for (unsigned sign = 0; sign < 2; ++sign) for (unsigned column = 0; column < 4; ++column) {
				result.planes[axis * 2 + sign][column] = matrix[column * 4 + 3] * (1 + margin) + (sign == 0 ? 1 : -1) * matrix[column * 4 + axis];
			}
		}
		for (unsigned column = 0; column < 4; ++column) result.planes[4][column] = matrix[column * 4 + 3];
		result.planes[4][3] -= Near();
		result.planes[5] = {0, 0, 0, 1}; // No far-distance culling plane.
		return result;
	}
};

/** Fixed-lens six-unit-eye view shared by isolated and joined asset reviews. */
inline Camera StreetReviewCamera(Vec3 low, Vec3 high, int width, int height, float rotation)
{
	Camera camera{{},1,width,height,rotation};
	camera.first_person = true; camera.pitch = -10; camera.vertical_fov = 40;
	Vec3 centre = (low+high)*0.5f;
	float radius = std::max(high.x-low.x,high.y-low.y)*0.5f;
	float distance = radius+std::max({24.0f,(high.z-low.z)*Camera::WORLD_Z_SCALE*1.85f,radius*2.5f});
	Vec3 back = camera.Unrotate({Camera::INV_SQRT2,Camera::INV_SQRT2,0});
	camera.focus = Vec3{centre.x,centre.y,low.z+6}+back*distance;
	return camera;
}

} // namespace Renderer3D
#endif
