/* SPDX-License-Identifier: GPL-2.0-only */
/** @file viewport_3d.cpp Read-only scene adapter and upstream framebuffer composition. */

#include "../stdafx.h"
#include "viewport_3d.h"
#include "gl_backend.hpp"
#include "world_capture.h"
#include "sprite_textures.hpp"
#include "profiling.h"
#include "camera_motion.hpp"
#include "vulkan_backend.h"
#include "tunnel_capture.h"
#include "../blitter/factory.hpp"
#include "../debug.h"
#include "../gfx_func.h"
#include "../fileio_func.h"
#include "../house.h"
#include "../landscape.h"
#include "../town_map.h"
#include "../vehicle_base.h"
#include "../video/video_driver.hpp"
#include "../viewport_func.h"
#include "../window_func.h"
#include "../window_gui.h"
#include "../zoom_func.h"
#include "../texteff.hpp"
#include "../strings_func.h"
#include "../table/strings.h"

#include <cstdlib>
#include <cstdio>
#include <bit>
#include <filesystem>
#include <fstream>
#include <unordered_map>

namespace Renderer3D {

/** Development opt-in. Activation is intentionally separate from saved game settings. */
static bool requested = [] {
	const char *value = std::getenv("OPENTT3D_RENDERER");
	return value != nullptr && std::string_view(value) == "1";
}();
static float rotation = 0;

struct Frame {
	int left, top, width, height;
	ZoomLevel zoom;
	std::vector<Colour> pixels;
	std::vector<uint32_t> picking;
	uint64_t epoch = 0, texture_generation = 0;
	bool gpu_resident = false;
	Camera camera;
	mutable Point pick_point{-1,-1};
	mutable uint64_t pick_epoch = UINT64_MAX;
	mutable uint32_t pick_id = 0;
};
static std::unordered_map<const Viewport *, Frame> frames;
static uint64_t frame_epoch = 0;
static unsigned readback_depth = 0;
static bool middle_pressed = false;
static const Viewport *orbit_viewport = nullptr;
struct OrbitGesture { Camera camera; Vec3 pivot; float yaw = 0, tilt = 0; bool cab = false; };
static std::optional<OrbitGesture> orbit_gesture;

struct CameraPosition {
	double fraction_x = 0, fraction_y = 0; ///< Sub-virtual-pixel scroll remainder.
	std::optional<Vec3> fixed_focus; ///< Exact pivot at a terrain discontinuity, or a screenshot snapshot.
	Vec3 focus_offset{};
	double center_x = 0, center_y = 0;
	float terrain_height = 0;
	bool track_terrain = false;
	bool free_orbit = false;
	float pitch = 30;
	float zoom_current = std::numeric_limits<float>::quiet_NaN(), zoom_target = 0;
	ZoomLevel legacy_zoom = ZoomLevel::Normal;
	struct Anchor { Vec3 point; Vec3 focus; float zoom; Vec3 focus_offset; };
	std::optional<Anchor> zoom_anchor;
	std::optional<Camera> grounded_camera; ///< Last pose whose dolly range was rebased against terrain.
	std::optional<Camera> snapshot;
	struct Cab { VehicleID vehicle; Vec3 eye; float heading, look_offset = 0, look_pitch = 0; };
	std::optional<Cab> cab;
};
static std::unordered_map<const Viewport *, CameraPosition> camera_positions;
static constexpr float MIN_CAMERA_ZOOM = -6; // Street-level dolly range, independent of the legacy sprite zoom.
static constexpr float VIEWPORT_VERTICAL_FOV = 40; // One fixed lens for orbit and Cab; zoom moves the eye.
static void UpdateCameraMotion(float seconds);
static Profile::Clock::time_point last_camera_tick{};

void BeginReadback()
{
	++readback_depth;
	frames.clear();
	MarkWholeScreenDirty();
}

void EndReadback()
{
	assert(readback_depth != 0);
	--readback_depth;
	frames.clear();
	MarkWholeScreenDirty();
}

void ForgetViewport(const Viewport *viewport)
{
	/* Windows can be deleted on the game thread while Paint uses GPU targets. */
	if (Vulkan::Active()) VideoDriver::GetInstance()->QueueOnMainThread([viewport] { Vulkan::ForgetViewport(viewport); });
	else if (HasOpenGLBackend()) VideoDriver::GetInstance()->QueueOnMainThread([viewport] { OpenGL::ForgetViewport(viewport); });
	if (orbit_viewport == viewport) { orbit_viewport = nullptr; orbit_gesture.reset(); }
	frames.erase(viewport);
	camera_positions.erase(viewport);
}

bool IsEnabled()
{
	return requested && HasRenderBackend() && BlitterFactory::GetCurrentBlitter()->GetScreenDepth() == 32;
}

bool SetEnabled(bool enabled)
{
	if (enabled && (!HasRenderBackend() || BlitterFactory::GetCurrentBlitter()->GetScreenDepth() != 32)) return false;
	requested = enabled;
	rotation = 0;
	frames.clear();
	camera_positions.clear();
	orbit_viewport = nullptr;
	orbit_gesture.reset();
	middle_pressed = false;
	MarkWholeScreenDirty();
	return true;
}

float GetRotation() { return rotation; }

void RotateCamera(float quarter_turns)
{
	if (Window *window = GetMainWindow(); window != nullptr && window->viewport != nullptr &&
		(orbit_viewport == nullptr || orbit_viewport == window->viewport.get())) {
		auto found = camera_positions.find(window->viewport.get());
		if (found != camera_positions.end() && found->second.cab.has_value() && window->viewport->follow_vehicle == found->second.cab->vehicle) {
			found->second.cab->look_offset = std::remainder(found->second.cab->look_offset + quarter_turns, 4.0f);
			frames.erase(window->viewport.get());
			window->SetDirty();
			return;
		}
	}
	rotation = std::fmod(rotation + quarter_turns, 4.0f);
	if (rotation < 0) rotation += 4;
	for (auto &[viewport, position] : camera_positions) position.zoom_anchor.reset();
	frames.clear();
	MarkWholeScreenDirty();
}

void ResetCameraRotation()
{
	for (auto &[viewport, position] : camera_positions) {
		position.pitch = 30;
		if (position.cab) { position.cab->look_offset = 0; position.cab->look_pitch = 0; }
	}
	orbit_gesture.reset();
	rotation = 0;
	frames.clear();
	MarkWholeScreenDirty();
}

static Vec3 CabEye(const Vehicle &vehicle)
{
	float height = vehicle.type == VEH_SHIP ? 12 : vehicle.type == VEH_AIRCRAFT ? 8 : 6;
	return {static_cast<float>(vehicle.x_pos), static_cast<float>(vehicle.y_pos), RenderVehicleZ(vehicle) + height};
}

bool IsFirstPerson(VehicleID vehicle)
{
	if (!IsEnabled()) return false;
	const Window *window = GetMainWindow();
	if (window == nullptr || window->viewport == nullptr || window->viewport->follow_vehicle != vehicle) return false;
	auto found = camera_positions.find(window->viewport.get());
	return found != camera_positions.end() && found->second.cab.has_value() && found->second.cab->vehicle == vehicle;
}

bool ToggleFirstPerson(VehicleID id)
{
	const Vehicle *vehicle = Vehicle::GetIfValid(id);
	Window *window = GetMainWindow();
	if (!IsEnabled() || vehicle == nullptr || !vehicle->IsPrimaryVehicle() || window == nullptr || window->viewport == nullptr) return false;
	if (IsFirstPerson(id)) {
		camera_positions[window->viewport.get()].cab.reset();
	} else {
		window->viewport->follow_vehicle = id;
		auto &position = camera_positions[window->viewport.get()];
		position.zoom_anchor.reset();
		position.zoom_target = position.zoom_current = GetEffectiveZoom(*window->viewport);
		position.cab = CameraPosition::Cab{id, CabEye(*vehicle), to_underlying(vehicle->direction) * 0.5f};
	}
	frames.erase(window->viewport.get());
	window->SetDirty();
	SetWindowDirty(WC_VEHICLE_VIEW, id.base());
	return true;
}

void CancelFirstPerson(const Viewport &viewport)
{
	auto found = camera_positions.find(&viewport);
	if (found != camera_positions.end()) found->second.cab.reset();
	frames.erase(&viewport);
}

void ReplaceCameraVehicle(VehicleID previous, VehicleID replacement)
{
	for (auto &[viewport, position] : camera_positions) {
		if (position.cab.has_value() && position.cab->vehicle == previous) position.cab->vehicle = replacement;
	}
}

void BeginFrame()
{
	OpenGL::BeginFrame();
	/* Keep the last visible ID buffer for input; refresh colour/geometry at most
	 * once per draw tick. Screenshot strips are never retained in this cache. */
	++frame_epoch;
	std::erase_if(frames, [](const auto &entry) {
		return entry.second.epoch + 1 < frame_epoch || entry.second.texture_generation != TextureGeneration();
	});
	auto now = Profile::Clock::now();
	float seconds = last_camera_tick == Profile::Clock::time_point{} ? 1.0f / 60 : std::chrono::duration<float>(now - last_camera_tick).count();
	last_camera_tick = now;
	BeginCaptureFrame(std::clamp(seconds, 0.0f, 0.1f));
	if (IsEnabled()) UpdateCameraMotion(std::clamp(seconds, 0.0f, 0.1f));
	/* Upstream dirty rectangles are projected for the original camera. Until
	 * perspective invalidation is implemented, repaint each draw tick. */
	if (IsEnabled()) MarkWholeScreenDirty();
}

/** Smooth only the camera pivot; gameplay picking still uses upstream integer heights. */
static float CameraGroundHeight(float x, float y)
{
	x = std::clamp(x, 0.0f, Map::MaxX() * 16.0f - 1);
	y = std::clamp(y, 0.0f, Map::MaxY() * 16.0f - 1);
	int ix = static_cast<int>(std::floor(x)), iy = static_cast<int>(std::floor(y));
	int nx = std::min(ix + 1, static_cast<int>(Map::MaxX() * TILE_SIZE - 1));
	int ny = std::min(iy + 1, static_cast<int>(Map::MaxY() * TILE_SIZE - 1));
	return TerrainZ(std::lerp(std::lerp(static_cast<float>(GetSlopePixelZ(ix, iy)), static_cast<float>(GetSlopePixelZ(nx, iy)), x - ix),
		std::lerp(static_cast<float>(GetSlopePixelZ(ix, ny)), static_cast<float>(GetSlopePixelZ(nx, ny)), x - ix), y - iy));
}

float GetEffectiveZoom(const Viewport &vp)
{
	auto found = camera_positions.find(&vp);
	if (found == camera_positions.end() || !std::isfinite(found->second.zoom_current)) return to_underlying(vp.zoom);
	return found->second.zoom_current;
}

static Camera MakeCamera(const Viewport &vp)
{
	auto position = camera_positions.find(&vp);
	const CameraPosition offset = position == camera_positions.end() ? CameraPosition{} : position->second;
	if (offset.snapshot.has_value()) return *offset.snapshot;
	const float sx = (vp.virtual_left + vp.virtual_width * 0.5 + offset.fraction_x) / ZOOM_BASE;
	const float sy = (vp.virtual_top + vp.virtual_height * 0.5 + offset.fraction_y) / ZOOM_BASE;
	Camera camera;
	camera.focus = {(sy - sx * 0.5f) * 0.5f, (sy + sx * 0.5f) * 0.5f, 0};
	/* Keep the legacy scroll coordinates as the unrotated projection of the pivot. */
	Point ground = InverseRemapCoords2(static_cast<int>(sx * ZOOM_BASE), static_cast<int>(sy * ZOOM_BASE), true);
	if (ground.x >= 0 && ground.y >= 0 && ground.x < static_cast<int>(Map::MaxX() * TILE_SIZE) && ground.y < static_cast<int>(Map::MaxY() * TILE_SIZE)) {
		float z = GetSlopePixelZ(ground.x, ground.y);
		for (unsigned iteration = 0; iteration < 16; ++iteration) {
			float height = CameraGroundHeight(camera.focus.x + z * 0.5f, camera.focus.y + z * 0.5f)/TERRAIN_HEIGHT_SCALE;
			if (std::abs(height - z) < 0.0001f) break;
			z = std::lerp(z, height, 0.5f);
		}
		camera.focus = camera.focus + Vec3{z * 0.5f, z * 0.5f, TerrainZ(z)};
	}
	/* An aircraft or bridge vehicle must remain centred at its actual elevation,
	 * including in vehicle/news viewports and after rotating the camera. */
	bool following = false;
	for (const Window *window : Window::Iterate()) {
		if (window->viewport.get() != &vp) continue;
		if (const Vehicle *vehicle = Vehicle::GetIfValid(window->viewport->follow_vehicle); vehicle != nullptr) {
			camera.focus = {static_cast<float>(vehicle->x_pos), static_cast<float>(vehicle->y_pos), RenderVehicleZ(*vehicle)};
			/* Ordinary following stays above the landscape while the vehicle is
			 * underground; only an explicit Cab view enters the modeled bore. */
			if (vehicle->vehstatus.Test(VehState::Hidden) && IsVehicleInTunnel(*vehicle) && (!offset.cab || offset.cab->vehicle != vehicle->index)) camera.focus.z = CameraGroundHeight(camera.focus.x,camera.focus.y);
			following = true;
		}
		break;
	}
	if (!following && offset.fixed_focus && offset.free_orbit) {
		/* Orbit focus can be above/outside the map. Keep legacy scrolling bounded,
		 * and apply its subsequent displacement to the independent 3D focus. */
		double dx = (vp.virtual_left + vp.virtual_width * 0.5 + offset.fraction_x - offset.center_x) / ZOOM_BASE;
		double dy = (vp.virtual_top + vp.virtual_height * 0.5 + offset.fraction_y - offset.center_y) / ZOOM_BASE;
		camera.SetFocusRelative(*offset.fixed_focus,offset.focus_offset+Vec3{static_cast<float>((dy - dx * 0.5) * 0.5), static_cast<float>((dy + dx * 0.5) * 0.5), 0});
	} else if (!following && offset.fixed_focus.has_value() &&
		offset.center_x == vp.virtual_left + vp.virtual_width * 0.5 + offset.fraction_x &&
		offset.center_y == vp.virtual_top + vp.virtual_height * 0.5 + offset.fraction_y &&
		(!offset.track_terrain || std::abs(CameraGroundHeight(offset.fixed_focus->x, offset.fixed_focus->y) - offset.terrain_height) < 0.001f)) {
		camera.focus = *offset.fixed_focus;
		camera.focus_offset = offset.focus_offset;
	}
	float zoom = GetEffectiveZoom(vp);
	camera.pixels_per_unit = ZOOM_BASE * std::exp2(-zoom);
	camera.vertical_fov = VIEWPORT_VERTICAL_FOV;
	camera.width = vp.width;
	camera.height = vp.height;
	camera.rotation = rotation;
	camera.pitch = offset.pitch;
	if (following && offset.cab.has_value()) {
		const auto &cab = *offset.cab;
		/* A stale cab state must never override a newly selected follow target. */
		for (const Window *window : Window::Iterate()) {
			if (window->viewport.get() != &vp || window->viewport->follow_vehicle != cab.vehicle) continue;
			camera.focus = cab.eye;
			camera.rotation = cab.heading + cab.look_offset;
			camera.pitch = 2 + cab.look_pitch;
			camera.first_person = true;
			camera.hidden_object = cab.vehicle.base() + 1;
			if (const Vehicle *vehicle = Vehicle::GetIfValid(cab.vehicle); vehicle != nullptr && IsVehicleInTunnel(*vehicle)) camera.tunnel_entrance = vehicle->tile.base();
			break;
		}
	}
	return camera;
}

float GetPitch(const Viewport &vp) { return MakeCamera(vp).pitch; }

static void PinFocus(const Viewport &vp, Vec3 focus, bool track_terrain, Vec3 residual = {})
{
	CameraPosition &position = camera_positions[&vp];
	position.fixed_focus = focus;
	position.focus_offset = residual;
	position.center_x = vp.virtual_left + vp.virtual_width * 0.5 + position.fraction_x;
	position.center_y = vp.virtual_top + vp.virtual_height * 0.5 + position.fraction_y;
	position.track_terrain = track_terrain;
	position.free_orbit = !track_terrain;
	position.terrain_height = track_terrain ? CameraGroundHeight(focus.x, focus.y) : 0;
	position.grounded_camera.reset();
}

/** An off-centre orbit can put its mathematical focus far above the ground.
 * Re-express the SAME eye/orientation with a ground-facing focus so a stale
 * zoom number cannot prevent the player from descending to street level. */
static void RebaseOrbitZoom(const Viewport &vp)
{
	auto found = camera_positions.find(&vp);
	if (found == camera_positions.end()) return;
	auto &position = found->second;
	if (!position.free_orbit || position.cab || position.snapshot || position.zoom_anchor || position.zoom_current != position.zoom_target) return;
	Camera before = MakeCamera(vp);
	if (position.grounded_camera && *position.grounded_camera == before) return;
	/* Terrain picking uses integer gameplay heights. Do not continually change
	 * the zoom limit for sub-unit rounding at an otherwise grounded focus. */
	if (std::abs(before.focus.z-CameraGroundHeight(before.focus.x,before.focus.y)) < 2) {
		position.grounded_camera = before;
		return;
	}
	Point hit = PickTerrain(vp,vp.left+vp.width/2,vp.top+vp.height/2,false);
	float height = hit.x < 0 ? 0 : TerrainZ(GetSlopePixelZ(hit.x,hit.y));
	auto ground = before.ScreenRay(vp.width*0.5f,vp.height*0.5f).AtZ(height);
	if (!ground) { position.grounded_camera = before; return; }
	float distance = Dot(Camera::Physical(before.Rotate(before.Eye()-*ground)),before.Back());
	if (distance <= 0.05f) { position.grounded_camera = before; return; }
	float zoom = std::log2(distance * Camera::ART_SCALE * ZOOM_BASE / before.FocalPixels());
	if (!std::isfinite(zoom)) return;
	Camera changed = before;
	changed.pixels_per_unit = ZOOM_BASE * std::exp2(-zoom);
	changed.TranslateFocus(before.Unrotate(Camera::World(before.Back()*(before.Distance()-changed.Distance()))));
	position.zoom_current = position.zoom_target = zoom;
	position.legacy_zoom = vp.zoom;
	PinFocus(vp,changed.focus,false,changed.focus_offset);
	position.grounded_camera = MakeCamera(vp);
	frames.erase(&vp);
}

static void ApplyZoomAnchor(const Viewport &vp, const CameraPosition::Anchor &anchor)
{
	float ratio = std::exp2(GetEffectiveZoom(vp)-anchor.zoom);
	Camera changed;
	changed.SetFocusRelative(anchor.point,((anchor.focus-anchor.point)+anchor.focus_offset)*ratio);
	PinFocus(vp,changed.focus,false,changed.focus_offset);
	frames.erase(&vp);
}

void CopyViewportCamera(const Viewport &source, const Viewport &destination)
{
	if (!IsEnabled()) return;
	const float dx = (destination.virtual_left - source.virtual_left + (destination.virtual_width - source.virtual_width) * 0.5f) / ZOOM_BASE;
	const float dy = (destination.virtual_top - source.virtual_top + (destination.virtual_height - source.virtual_height) * 0.5f) / ZOOM_BASE;
	Camera copy = MakeCamera(source);
	copy.TranslateFocus({(dy - dx * 0.5f) * 0.5f, (dy + dx * 0.5f) * 0.5f, 0});
	copy.width = destination.width;
	copy.height = destination.height;
	copy.pixels_per_unit *= std::exp2(static_cast<float>(to_underlying(source.zoom) - to_underlying(destination.zoom)));
	camera_positions[&destination].snapshot = copy;
}

/** Keyboard/edge panning uses a constant speed at the focal plane. */
Point UnrotateScroll(Point delta)
{
	if (!IsEnabled()) return delta;
	for (auto &[viewport, position] : camera_positions) position.zoom_anchor.reset();
	Camera camera;
	camera.rotation = rotation;
	Vec3 world = camera.Unrotate({delta.y * 0.5f - delta.x * 0.25f, delta.y * 0.5f + delta.x * 0.25f, 0});
	return {static_cast<int>(std::lround(2 * (world.y - world.x))), static_cast<int>(std::lround(world.x + world.y))};
}

static void SetScrollPosition(ViewportData &vp, Point position)
{
	vp.virtual_left = vp.scrollpos_x = vp.dest_scrollpos_x = position.x;
	vp.virtual_top = vp.scrollpos_y = vp.dest_scrollpos_y = position.y;
}

static void SetPreciseScrollPosition(ViewportData &vp, double x, double y)
{
	Point integral{static_cast<int>(std::lround(x)), static_cast<int>(std::lround(y))};
	CameraPosition &position = camera_positions[&vp];
	position.fraction_x = x - integral.x;
	position.fraction_y = y - integral.y;
	SetScrollPosition(vp, integral);
}

bool HandleMiddleOrbit(bool pressed, Point cursor, Point delta)
{
	if (!pressed || !IsEnabled()) {
		middle_pressed = false;
		orbit_viewport = nullptr;
		orbit_gesture.reset();
		return false;
	}
	if (!middle_pressed) {
		middle_pressed = true;
		Window *window = FindWindowFromPt(cursor.x, cursor.y);
		orbit_viewport = window == nullptr ? nullptr : IsPtInWindowViewport(window, cursor.x, cursor.y);
		if (orbit_viewport == nullptr) return false;
		Camera camera = MakeCamera(*orbit_viewport);
		if (camera.first_person) {
			orbit_gesture = OrbitGesture{camera, camera.focus, 0, 0, true};
			return true;
		}
		float x = cursor.x - orbit_viewport->left + 0.5f, y = cursor.y - orbit_viewport->top + 0.5f;
		Point terrain = PickTerrain(*orbit_viewport, cursor.x, cursor.y, false);
		std::optional<Vec3> pivot;
		if (terrain.x != -1) pivot = camera.ScreenRay(x, y).AtZ(TerrainZ(GetSlopePixelZ(terrain.x, terrain.y)));
		else if (!_settings_game.construction.freeform_edges) pivot = camera.ScreenRay(x, y).AtZ(0);
		if (!pivot) return true; // Sky has no clicked surface to orbit around.
		window->viewport->CancelFollow(*window);
		auto &position = camera_positions[orbit_viewport];
		position.zoom_current = position.zoom_target = GetEffectiveZoom(*orbit_viewport);
		position.legacy_zoom = orbit_viewport->zoom;
		position.zoom_anchor.reset();
		PinFocus(*orbit_viewport, camera.focus, false, camera.focus_offset);
		orbit_gesture = OrbitGesture{camera, *pivot};
		return true;
	}
	if (orbit_viewport == nullptr) return false;
	if (!orbit_gesture || (delta.x == 0 && delta.y == 0)) return true;
	auto &gesture = *orbit_gesture;
	auto &position = camera_positions[orbit_viewport];
	float sensitivity = 100.0f / std::max(100, _gui_scale);
	float yaw = delta.x * sensitivity / 256, tilt = delta.y * sensitivity * 0.25f;
	if (gesture.cab) {
		if (position.cab) {
			position.cab->look_offset = std::remainder(position.cab->look_offset + yaw, 4.0f);
			position.cab->look_pitch = std::clamp(position.cab->look_pitch + tilt, -87.0f, 83.0f);
		}
	} else {
		float target_yaw = gesture.yaw + yaw, target_tilt = gesture.tilt + tilt;
		Camera changed = gesture.camera.Orbited(gesture.pivot, target_yaw, target_tilt);
		auto above_ground = [&](const Camera &candidate) {
			Vec3 eye = candidate.Eye();
			float ground = eye.x >= 0 && eye.y >= 0 && eye.x < Map::MaxX() * 16.0f && eye.y < Map::MaxY() * 16.0f ? CameraGroundHeight(eye.x, eye.y) : 0;
			return eye.z >= ground + 1;
		};
		if (!above_ground(changed)) {
			float lo = 0, hi = 1;
			for (unsigned i = 0; i < 16; ++i) {
				float mid = (lo + hi) * 0.5f;
				if (above_ground(gesture.camera.Orbited(gesture.pivot, gesture.yaw + yaw * mid, gesture.tilt + tilt * mid))) lo = mid; else hi = mid;
			}
			target_yaw = gesture.yaw + yaw * lo; target_tilt = gesture.tilt + tilt * lo;
			changed = gesture.camera.Orbited(gesture.pivot, target_yaw, target_tilt);
		}
		gesture.yaw = target_yaw;
		gesture.tilt = changed.pitch - gesture.camera.pitch; // No accumulated dead travel at the tilt limits.
		rotation = changed.rotation;
		position.pitch = changed.pitch;
		PinFocus(*orbit_viewport, changed.focus, false, changed.focus_offset);
	}
	frames.clear();
	for (Window *window : Window::Iterate()) if (window->viewport.get() == orbit_viewport) RebuildViewportOverlay(window);
	MarkWholeScreenDirty();
	return true;
}

/** Solve both scroll coordinates while the terrain-based orbit pivot changes height. */
static void AnchorViewport(ViewportData &vp, Vec3 anchor, float x, float y)
{
	if (camera_positions[&vp].free_orbit) {
		Vec3 residual;
		if (auto focus = MakeCamera(vp).FocusForAnchor(anchor, x, y, &residual)) PinFocus(vp, *focus, false, residual);
		frames.erase(&vp);
		return;
	}
	camera_positions[&vp].fixed_focus.reset();
	/* An exact planar solution is a useful first step before accounting for the
	 * change of ground height at the destination pivot. */
	Camera before = MakeCamera(vp);
	if (auto focus = before.FocusForAnchor(anchor, x, y); focus.has_value()) {
		const CameraPosition position = camera_positions[&vp];
		double sx = vp.scrollpos_x + position.fraction_x, sy = vp.scrollpos_y + position.fraction_y;
		Vec3 delta = *focus - before.focus;
		auto previous = before.Project(anchor);
		SetPreciseScrollPosition(vp, sx + 2.0 * (delta.y - delta.x) * ZOOM_BASE, sy + (delta.x + delta.y) * ZOOM_BASE);
		auto projected = MakeCamera(vp).Project(anchor);
		if (!projected.visible || std::hypot(projected.x - x, projected.y - y) > std::hypot(previous.x - x, previous.y - y)) SetPreciseScrollPosition(vp, sx, sy);
	}
	for (unsigned iteration = 0; iteration < 20; ++iteration) {
		const CameraPosition position = camera_positions[&vp];
		const double sx = vp.scrollpos_x + position.fraction_x, sy = vp.scrollpos_y + position.fraction_y;
		const auto projected = MakeCamera(vp).Project(anchor);
		const float error = std::hypot(projected.x - x, projected.y - y);
		if (error < 0.1f) break;
		/* The height derivative matters after rotation: a planar unprojection
		 * alone can oscillate across a slope instead of converging to the cursor. */
		const double step = 1.0;
		SetPreciseScrollPosition(vp, sx + step, sy);
		auto along_x = MakeCamera(vp).Project(anchor);
		SetPreciseScrollPosition(vp, sx, sy + step);
		auto along_y = MakeCamera(vp).Project(anchor);
		SetPreciseScrollPosition(vp, sx, sy);
		const double a = (along_x.x - projected.x) / step, b = (along_y.x - projected.x) / step;
		const double c = (along_x.y - projected.y) / step, d = (along_y.y - projected.y) / step;
		const double determinant = a * d - b * c;
		if (std::abs(determinant) < 1e-10) break;
		const double dx = ((x - projected.x) * d - b * (y - projected.y)) / determinant;
		const double dy = (a * (y - projected.y) - (x - projected.x) * c) / determinant;
		bool improved = false;
		for (double gain = 1; gain >= 1.0 / 256; gain *= 0.5) {
			SetPreciseScrollPosition(vp, sx + dx * gain, sy + dy * gain);
			auto candidate = MakeCamera(vp).Project(anchor);
			if (candidate.visible && std::hypot(candidate.x - x, candidate.y - y) < error) {
				improved = true;
				break;
			}
		}
		if (!improved) {
			SetPreciseScrollPosition(vp, sx, sy);
			break;
		}
	}
	Camera camera = MakeCamera(vp);
	auto projected = camera.Project(anchor);
	if (std::hypot(projected.x - x, projected.y - y) >= 0.1f) {
		/* At a retaining wall there may be no terrain-centred solution between
		 * its upper and lower surfaces. Keep the nearby altitude and solve the
		 * anchor exactly. External scrolling or changed ground releases this pivot. */
		Vec3 residual;
		if (auto focus = camera.FocusForAnchor(anchor, x, y, &residual); focus.has_value()) {
			SetPreciseScrollPosition(vp, 2.0 * (focus->y - focus->x) * ZOOM_BASE - vp.virtual_width * 0.5,
				(focus->x + focus->y - focus->z/TERRAIN_HEIGHT_SCALE) * ZOOM_BASE - vp.virtual_height * 0.5);
			PinFocus(vp, *focus, true, residual);
		}
	}
	frames.erase(&vp);
}

bool CanZoom(const Viewport &vp, bool in)
{
	if (MakeCamera(vp).first_person) return false;
	RebaseOrbitZoom(vp);
	auto found = camera_positions.find(&vp);
	float target = GetEffectiveZoom(vp);
	if (found != camera_positions.end() && std::isfinite(found->second.zoom_current)) target = found->second.zoom_target;
	return in ? target > MIN_CAMERA_ZOOM : target < to_underlying(_settings_client.gui.zoom_max);
}

bool SetZoom(Window &window, float level, bool instant, std::optional<Point> cursor)
{
	if (!IsEnabled() || window.viewport == nullptr || !std::isfinite(level)) return false;
	ViewportData &vp = *window.viewport;
	if (MakeCamera(vp).first_person) return false;
	RebaseOrbitZoom(vp);
	if (instant && !cursor.has_value()) {
		vp.virtual_left = vp.scrollpos_x;
		vp.virtual_top = vp.scrollpos_y;
	}
	Camera before = MakeCamera(vp);
	float current = GetEffectiveZoom(vp);
	CameraPosition &position = camera_positions[&vp];
	/* An orbit may legitimately move outside the ordinary dolly range. Allow
	 * incremental travel back into it instead of snapping on the next wheel step. */
	float target = std::clamp(level,std::min(MIN_CAMERA_ZOOM,current),std::max(current,static_cast<float>(to_underlying(_settings_client.gui.zoom_max))));
	position.zoom_anchor.reset();
	Point cursor_point = cursor.value_or(Point{vp.left+vp.width/2,vp.top+vp.height/2});
	Point hit = PickTerrain(vp,cursor_point.x,cursor_point.y,false);
	float x = cursor ? cursor->x-vp.left+0.5f : vp.width*0.5f;
	float y = cursor ? cursor->y-vp.top+0.5f : vp.height*0.5f;
	float ground_z = hit.x >= 0 ? TerrainZ(GetSlopePixelZ(hit.x,hit.y)) : 0;
	if (auto point = before.ScreenRay(x,y).AtZ(ground_z)) {
		position.zoom_anchor = CameraPosition::Anchor{*point,before.focus,current,before.focus_offset};
		if (cursor) vp.CancelFollow(window);
	} else {
		Vec3 ground = before.focus;
		ground.z = CameraGroundHeight(ground.x,ground.y);
		position.zoom_anchor = CameraPosition::Anchor{ground,before.focus,current,before.focus_offset};
	}
	double cx = vp.virtual_left + position.fraction_x + vp.virtual_width * 0.5;
	double cy = vp.virtual_top + position.fraction_y + vp.virtual_height * 0.5;
	vp.zoom = static_cast<ZoomLevel>(std::clamp(static_cast<int>(std::lround(target)), static_cast<int>(to_underlying(ZoomLevel::Min)), static_cast<int>(to_underlying(ZoomLevel::Max))));
	vp.virtual_width = ScaleByZoom(vp.width, vp.zoom);
	vp.virtual_height = ScaleByZoom(vp.height, vp.zoom);
	SetPreciseScrollPosition(vp, cx - vp.virtual_width * 0.5, cy - vp.virtual_height * 0.5);
	PinFocus(vp, before.focus, !position.free_orbit, before.focus_offset);
	position.legacy_zoom = vp.zoom;
	position.zoom_current = instant ? target : current;
	position.zoom_target = target;
	if (instant && position.zoom_anchor.has_value()) {
		auto anchor = *position.zoom_anchor;
		ApplyZoomAnchor(vp,anchor);
		position.zoom_anchor.reset();
	}
	frames.erase(&vp);
	RebuildViewportOverlay(&window);
	window.InvalidateData();
	window.SetDirty();
	return true;
}

bool Zoom(Window &window, bool in, std::optional<Point> cursor)
{
	if (!IsEnabled() || window.viewport == nullptr || !CanZoom(*window.viewport, in)) return false;
	auto found = camera_positions.find(window.viewport.get());
	float target = GetEffectiveZoom(*window.viewport);
	if (found != camera_positions.end() && std::isfinite(found->second.zoom_current)) target = found->second.zoom_target;
	return SetZoom(window, target + (in ? -0.5f : 0.5f), false, cursor);
}

bool ZoomAtCursor(Window &window, bool in, Point cursor)
{
	if (!IsEnabled() || window.viewport == nullptr) return false;
	Zoom(window, in, cursor);
	return true;
}

static void UpdateCameraMotion(float seconds)
{
	for (Window *window : Window::Iterate()) {
		if (window->viewport == nullptr) continue;
		auto found = camera_positions.find(window->viewport.get());
		if (found == camera_positions.end()) continue;
		ViewportData &vp = *window->viewport;
		CameraPosition &position = found->second;
		if (position.cab.has_value()) {
			auto &cab = *position.cab;
			const Vehicle *vehicle = Vehicle::GetIfValid(cab.vehicle);
			if (vehicle == nullptr || vp.follow_vehicle != cab.vehicle) {
				position.cab.reset();
			} else {
				Vec3 target = CabEye(*vehicle), delta = target - cab.eye;
				if (Dot(delta, delta) > 256 * 256) cab.eye = target;
				cab.eye = {SmoothValue(cab.eye.x, target.x, 24, seconds), SmoothValue(cab.eye.y, target.y, 24, seconds), SmoothValue(cab.eye.z, target.z, 24, seconds)};
				cab.heading = SmoothHeading(cab.heading, to_underlying(vehicle->direction) * 0.5f, 12, seconds);
			}
		}
		if (!std::isfinite(position.zoom_current)) {
			position.zoom_current = position.zoom_target = to_underlying(vp.zoom);
			position.legacy_zoom = vp.zoom;
			position.zoom_anchor.reset();
		}
		position.legacy_zoom = vp.zoom; // Legacy/DPI bookkeeping must not reset the 3D dolly.
		if (position.zoom_current == position.zoom_target) continue;
		position.zoom_current = SmoothValue(position.zoom_current, position.zoom_target, 16, seconds);
		if (std::abs(position.zoom_current - position.zoom_target) < 0.0005f) position.zoom_current = position.zoom_target;
		if (position.zoom_anchor.has_value()) {
			auto anchor = *position.zoom_anchor;
			ApplyZoomAnchor(vp,anchor);
		}
		if (position.zoom_current == position.zoom_target) position.zoom_anchor.reset();
		frames.erase(&vp);
		window->SetDirty();
	}
}

bool ScrollAtCursor(Window &window, Point delta, Point cursor)
{
	if (!IsEnabled() || window.viewport == nullptr) return false;
	ViewportData &vp = *window.viewport;
	camera_positions[&vp].zoom_anchor.reset();
	vp.CancelFollow(window);
	SetScrollPosition(vp, {vp.scrollpos_x, vp.scrollpos_y});
	Point hit = PickTerrain(vp, cursor.x, cursor.y, false);
	const float x = cursor.x - vp.left + 0.5f, y = cursor.y - vp.top + 0.5f;
	const Camera camera = MakeCamera(vp);
	float z = hit.x == -1 ? camera.focus.z : TerrainZ(GetSlopePixelZ(hit.x, hit.y));
	auto anchor = camera.ScreenRay(x + delta.x, y + delta.y).AtZ(z);
	if (anchor.has_value()) {
		AnchorViewport(vp, *anchor, x, y);
	} else {
		Point shift = UnrotateScroll({ScaleByZoom(delta.x, vp.zoom), ScaleByZoom(delta.y, vp.zoom)});
		SetScrollPosition(vp, {vp.scrollpos_x + shift.x, vp.scrollpos_y + shift.y});
	}
	RebuildViewportOverlay(&window);
	window.SetDirty();
	return true;
}

ViewportSign ProjectSign(const Viewport &vp, const ViewportSign &sign, int x, int y, int z)
{
	if (!IsEnabled()) return sign;
	ViewportSign result = sign;
	Point original = RemapCoords(x, y, z);
	Camera camera = MakeCamera(vp);
	auto p = camera.Project({static_cast<float>(x), static_cast<float>(y), TerrainZ(z)});
	float margin = std::max(sign.width_normal, sign.width_small) + 256.0f;
	if (!p.visible || p.x < -margin || p.y < -margin || p.x > vp.width + margin || p.y > vp.height + margin || !TunnelLabelVisible(camera,{static_cast<float>(x),static_cast<float>(y),TerrainZ(z)})) {
		result.center = result.top = -INT_MAX / 4;
		return result;
	}
	result.center = vp.virtual_left + ScaleByZoom(static_cast<int>(std::lround(p.x)), vp.zoom) + sign.center - original.x;
	result.top = vp.virtual_top + ScaleByZoom(static_cast<int>(std::lround(p.y)), vp.zoom) + sign.top - original.y;
	return result;
}

ViewportSign ProjectSign(const Viewport &vp, const ViewportSign &sign, TileIndex tile)
{
	if (!IsEnabled() || tile == INVALID_TILE) return sign;
	int x = TileX(tile) * TILE_SIZE, y = TileY(tile) * TILE_SIZE;
	return ProjectSign(vp, sign, x, y, GetSlopePixelZ(x, y));
}

bool FocusReferenceModel()
{
	if (Map::Size() == 0) return false;
	for (uint y = 0; y < Map::MaxY(); ++y) {
		for (uint x = 0; x < Map::MaxX(); ++x) {
			TileIndex tile = TileXY(x, y);
			if (IsTileType(tile, MP_HOUSE) && GetHouseBuildingStage(tile) == TOWN_HOUSE_COMPLETED &&
				(GetHouseType(tile) == 1 || GetHouseType(tile) == 2)) {
				Debug(driver, 1, "OpenTT3D: reference house {} at {},{}", GetHouseType(tile), x, y);
				ScrollMainWindowToTile(tile, true);
				return true;
			}
		}
	}
	return false;
}

static bool CaptureScene(const Viewport &vp, const Camera &camera, Scene &scene)
{
	Profile::Scope capture_time(Profile::Section::Capture);
	for (unsigned attempt = 0; attempt < 2; ++attempt) {
		try {
			BeginCapture(camera);
			CollectViewport3D(vp);
		} catch (const AtlasFull &) {
			if (IsCapturing()) FinishCapture();
			if (attempt != 0) {
				Debug(driver, 0, "OpenTT3D: viewport rendering failed: visible textures exceed the compacted atlas");
				return false;
			}
			Debug(driver, 2, "OpenTT3D: repacking fragmented sprite atlas");
			Textures().Repack();
			continue;
		} catch (...) {
			if (IsCapturing()) FinishCapture();
			throw;
		}
		scene = FinishCapture();
		return true;
	}
	return false;
}

/** Stream GPU tiles into a caller-owned image/strip, with top-down CPU coordinates. */
static bool RenderTo(const Viewport &vp, const Camera &camera, Colour *destination, int pitch, std::vector<uint32_t> *picking = nullptr)
{
	const int limit = std::min(4096, MaximumFramebufferSize());
	if (limit <= 0) return false;
	if (picking != nullptr) picking->resize(static_cast<size_t>(camera.width) * camera.height);
	std::vector<uint8_t> pixels;
	std::vector<uint32_t> ids;
	for (int top = 0; top < camera.height; top += limit) {
		for (int left = 0; left < camera.width; left += limit) {
			Camera tile = camera.Cropped(left, top, std::min(limit, camera.width - left), std::min(limit, camera.height - top));
			Scene scene;
			if (!CaptureScene(vp, tile, scene)) return false;
			if (!RenderScene(scene, tile, pixels, picking == nullptr ? nullptr : &ids)) return false;
			RecycleCapture(scene);
			Profile::Scope composite_time(Profile::Section::Composite);
			for (int y = 0; y < tile.height; ++y) {
				size_t source = static_cast<size_t>(tile.height - 1 - y) * tile.width;
				Colour *row = destination + static_cast<size_t>(top + y) * pitch + left;
				for (int x = 0; x < tile.width; ++x) {
					size_t offset = (source + x) * 4;
					row[x] = Colour(pixels[offset], pixels[offset + 1], pixels[offset + 2]);
				}
				if (picking != nullptr) {
					std::copy_n(ids.data() + source, tile.width, picking->data() + static_cast<size_t>(top + y) * camera.width + left);
				}
			}
		}
	}
	return true;
}

static bool RenderingFailed()
{
	Debug(driver, 0, "OpenTT3D: viewport rendering failed");
	requested = false;
	rotation = 0;
	frames.clear();
	MarkWholeScreenDirty();
	return false;
}

bool DrawViewport(const Viewport &vp, const DrawPixelInfo &dpi)
{
	if (!IsEnabled() || Map::Size() == 0 || vp.width <= 0 || vp.height <= 0) return false;
	const int left = UnScaleByZoom(dpi.left - (vp.virtual_left & ScaleByZoom(-1, vp.zoom)), vp.zoom);
	const int top = UnScaleByZoom(dpi.top - (vp.virtual_top & ScaleByZoom(-1, vp.zoom)), vp.zoom);
	const int width = UnScaleByZoom(dpi.width, vp.zoom), height = UnScaleByZoom(dpi.height, vp.zoom);
	if (width <= 0 || height <= 0) return true;
	/* Upstream's screenshot writer requests small strips. Never allocate a colour
	 * or picking buffer for the complete world image, which can exceed GPU limits. */
	if (_screen_disable_anim) {
		Camera camera = MakeCamera(vp).Cropped(left, top, width, height);
		if (!RenderTo(vp, camera, static_cast<Colour *>(dpi.dst_ptr), dpi.pitch)) return RenderingFailed();
		return true;
	}
	bool gpu = (Vulkan::Active() || OpenGL::Active()) && readback_depth == 0 && vp.width <= MaximumFramebufferSize() && vp.height <= MaximumFramebufferSize();
	Camera camera = MakeCamera(vp);
	auto it = frames.find(&vp);
	/* Legacy following scrolls can change between dirty-rectangle passes without
	 * moving the smoothed 3D eye. Reuse the target when its actual camera matches. */
	if (it == frames.end() || it->second.epoch != frame_epoch || it->second.camera != camera || it->second.gpu_resident != gpu) {
		Frame frame{vp.virtual_left, vp.virtual_top, vp.width, vp.height, vp.zoom, {}, {}, 0, 0, false, camera};
		frame.epoch = frame_epoch;
		frame.texture_generation = TextureGeneration();
		frame.gpu_resident = gpu;
		if (gpu) {
			Scene scene;
			if (!CaptureScene(vp,camera,scene) || !(Vulkan::Active() ? Vulkan::RenderViewport(&vp,scene,camera) : OpenGL::RenderViewport(&vp,scene,camera))) return RenderingFailed();
			RecycleCapture(scene);
		} else {
			frame.pixels.resize(static_cast<size_t>(vp.width) * vp.height);
			if (!RenderTo(vp, camera, frame.pixels.data(), vp.width, &frame.picking)) return RenderingFailed();
		}
		it = frames.insert_or_assign(&vp, std::move(frame)).first;
	}
	it->second.left = vp.virtual_left; it->second.top = vp.virtual_top; it->second.zoom = vp.zoom;
	const auto &pixels = it->second.pixels;
	const int x_begin = std::max(0, -left), x_end = std::min(width, vp.width - left);
	if (gpu) {
		int y_begin = std::max(0, -top), y_end = std::min(height, vp.height - top);
		if (x_end > x_begin && y_end > y_begin) {
			ptrdiff_t offset = static_cast<Colour *>(dpi.dst_ptr) - static_cast<Colour *>(_screen.dst_ptr);
			auto compose = Vulkan::Active() ? Vulkan::ComposeViewport : OpenGL::ComposeViewport;
			compose(&vp, left + x_begin, top + y_begin, x_end - x_begin, y_end - y_begin,
				static_cast<int>(offset % _screen.pitch) + x_begin, static_cast<int>(offset / _screen.pitch) + y_begin);
			for (int y = y_begin; y < y_end; ++y) std::fill_n(static_cast<Colour *>(dpi.dst_ptr) + y * dpi.pitch + x_begin, x_end - x_begin, Colour(0, 0, 0, 0));
		}
	}
	/* Composite only this clipped region. Upstream paints windows and labels later. */
	for (int y = 0; !gpu && y < height; ++y) {
		if (top + y < 0 || top + y >= vp.height || x_end <= x_begin) continue;
		auto *destination = static_cast<Colour *>(dpi.dst_ptr) + y * dpi.pitch + x_begin;
		std::copy_n(pixels.data() + static_cast<size_t>(top + y) * vp.width + left + x_begin, x_end - x_begin, destination);
	}
	/* 40bpp's palette-animation plane must not reinterpret new RGB viewport pixels. */
	if (BlitterFactory::GetCurrentBlitter()->NeedsAnimationBuffer()) {
		if (auto *animation = VideoDriver::GetInstance()->GetAnimBuffer(); animation != nullptr) {
			ptrdiff_t offset = static_cast<Colour *>(dpi.dst_ptr) - static_cast<Colour *>(_screen.dst_ptr);
			for (int y = 0; y < height; ++y) std::fill_n(animation + offset + y * dpi.pitch, width, uint8_t{0});
		}
	}
	return true;
}

Point PickTerrain(const Viewport &vp, int screen_x, int screen_y, bool clamp_to_map)
{
	if (screen_x < vp.left || screen_y < vp.top || screen_x >= vp.left + vp.width || screen_y >= vp.top + vp.height) return {-1, -1};
	Camera camera = MakeCamera(vp);
	Ray ray = camera.ScreenRay(screen_x - vp.left + 0.5f, screen_y - vp.top + 0.5f);
	double enter = 0, leave = std::numeric_limits<double>::infinity();
	float maximum_z = TerrainZ(_settings_game.construction.map_height_limit * TILE_HEIGHT + 2 * TILE_HEIGHT);
	if (ray.ClipBox({0, 0, 0}, {Map::MaxX() * 16.0f - 0.001f, Map::MaxY() * 16.0f - 0.001f, maximum_z}, enter, leave)) {
		/* Two-level DDA skips tiles above/below the ray, then intersects the exact
		 * upstream integer-pixel height field. No geometry or command approximation. */
		/* Ray distances can exceed 4096 at far zoom levels. A float increment of
		 * 0.0001 then rounds to zero and traps the DDA in one cell. Keep traversal
		 * and cell classification in double precision, including cancellation at
		 * map coordinates far from the origin. */
		auto exit_cell = [](double position, double direction, int cell, int size) {
			if (std::abs(direction) < 1e-8) return std::numeric_limits<double>::infinity();
			return ((direction > 0 ? (cell + 1) * size : cell * size) - position) / direction;
		};
		auto cell_at = [](double position, double direction, double distance, int size) {
			return static_cast<int>(std::floor((position + direction * distance) / size));
		};
		for (double t = enter; t <= leave;) {
			int tx = cell_at(ray.origin.x, ray.direction.x, t + 0.001, 16);
			int ty = cell_at(ray.origin.y, ray.direction.y, t + 0.001, 16);
			if (tx < 0 || ty < 0 || tx >= static_cast<int>(Map::MaxX()) || ty >= static_cast<int>(Map::MaxY())) break;
			double end = std::min({static_cast<double>(leave), exit_cell(ray.origin.x, ray.direction.x, tx, 16), exit_cell(ray.origin.y, ray.direction.y, ty, 16)});
			TileIndex tile = TileXY(tx, ty);
			if (IsValidTile(tile) && std::min(ray.origin.z + ray.direction.z * t, ray.origin.z + ray.direction.z * end) <= TerrainZ(GetTileMaxPixelZ(tile) + 2 * TILE_HEIGHT)) {
				for (double u = t; u <= end;) {
					int x = cell_at(ray.origin.x, ray.direction.x, u + 0.0001, 1);
					int y = cell_at(ray.origin.y, ray.direction.y, u + 0.0001, 1);
					if (x < 0 || y < 0 || x >= static_cast<int>(Map::MaxX() * TILE_SIZE) || y >= static_cast<int>(Map::MaxY() * TILE_SIZE)) break;
					double next = std::min({end, exit_cell(ray.origin.x, ray.direction.x, x, 1), exit_cell(ray.origin.y, ray.direction.y, y, 1)});
					float height = TerrainZ(GetSlopePixelZ(x, y));
					/* A shallow ray can enter a higher integer-height cell through its
					 * vertical face without ever crossing that cell's top plane. */
					if (ray.origin.z + ray.direction.z * u <= height) return {x, y};
					double hit = (height - static_cast<double>(ray.origin.z)) / ray.direction.z;
					if (hit >= u - 0.001 && hit <= next + 0.001) return {x, y};
					u = std::max(next + 0.0001, u + 0.0001);
				}
			}
			t = std::max(end + 0.001, t + 0.001);
		}
	}
	if (!clamp_to_map) return {-1, -1};
	Vec3 p = ray.AtZ(0).value_or(camera.focus);
	const int minimum = _settings_game.construction.freeform_edges ? TILE_SIZE : 0;
	return {std::clamp(static_cast<int>(p.x), minimum, static_cast<int>(Map::MaxX() * TILE_SIZE - 1)),
		std::clamp(static_cast<int>(p.y), minimum, static_cast<int>(Map::MaxY() * TILE_SIZE - 1))};
}

static uint32_t ReadViewportObjectId(const Viewport &vp, int screen_x, int screen_y, const Frame **used_frame = nullptr)
{
	if (screen_x < vp.left || screen_y < vp.top || screen_x >= vp.left + vp.width || screen_y >= vp.top + vp.height) return 0;
	auto found = frames.find(&vp);
	if (found == frames.end() || found->second.texture_generation != TextureGeneration()) return 0;
	const Frame &frame = found->second;
	if (frame.width != vp.width || frame.height != vp.height) return 0;
	/* Pick the image actually displayed. Following/zoom may already have a
	 * newer target pose while input still belongs to the previous presentation. */
	if (used_frame != nullptr) *used_frame = &frame;
	Point point{screen_x-vp.left,screen_y-vp.top};
	if (frame.pick_epoch == frame.epoch && frame.pick_point.x == point.x && frame.pick_point.y == point.y) return frame.pick_id;
	uint32_t id = 0;
	if (frame.gpu_resident) id = Vulkan::Active() ? Vulkan::ReadObjectId(&vp,point.x,point.y) : OpenGL::ReadObjectId(&vp,point.x,point.y);
	else {
		size_t index = static_cast<size_t>(point.y)*vp.width+point.x;
		if (index < frame.picking.size()) id = frame.picking[index];
	}
	frame.pick_point = point; frame.pick_epoch = frame.epoch; frame.pick_id = id;
	return id;
}

Point PickMap(const Viewport &vp, int screen_x, int screen_y, bool clamp_to_map)
{
	const Frame *frame = nullptr;
	uint32_t id = ReadViewportObjectId(vp,screen_x,screen_y,&frame);
	TileIndex tile = INVALID_TILE;
	if ((id & TILE_PICK_ID) != 0) {
		tile = TileIndex{id & ~TILE_PICK_ID};
	} else if (id != 0) {
		if (const Vehicle *vehicle = Vehicle::GetIfValid(VehicleID{id-1}); vehicle != nullptr && vehicle->x_pos >= 0 && vehicle->y_pos >= 0 &&
			vehicle->x_pos < static_cast<int>(Map::MaxX()*16) && vehicle->y_pos < static_cast<int>(Map::MaxY()*16)) tile = TileVirtXY(vehicle->x_pos,vehicle->y_pos);
	}
	if (frame != nullptr && IsValidTile(tile)) {
		int x = TileX(tile)*16, y = TileY(tile)*16;
		Point point{x+8,y+8};
		Ray ray = frame->camera.ScreenRay(screen_x-vp.left+0.5f,screen_y-vp.top+0.5f);
		for (unsigned i = 0; i < 3; ++i) {
			auto ground = ray.AtZ(TerrainZ(GetSlopePixelZ(point.x,point.y)));
			if (!ground) break;
			point = {std::clamp(static_cast<int>(std::floor(ground->x)),x,x+15),std::clamp(static_cast<int>(std::floor(ground->y)),y,y+15)};
		}
		return point;
	}
	return PickTerrain(vp,screen_x,screen_y,clamp_to_map);
}

Vehicle *PickVehicle(const Viewport &vp, int screen_x, int screen_y)
{
	uint32_t id = ReadViewportObjectId(vp,screen_x,screen_y);
	if (id == 0 || (id & TILE_PICK_ID) != 0) return nullptr;
	Vehicle *vehicle = Vehicle::GetIfValid(VehicleID{id - 1});
	if (vehicle == nullptr || vehicle->vehstatus.Any({VehState::Unclickable, VehState::Shadow}) || (vehicle->vehstatus.Test(VehState::Hidden) && !IsVehicleInTunnel(*vehicle))) return nullptr;
	return vehicle;
}

void VerifyWorldAtlas()
{
	Window *window = GetMainWindow();
	if (window == nullptr || window->viewport == nullptr) throw std::runtime_error("World atlas verification needs a loaded viewport");
	const Viewport &viewport = *window->viewport;
	const Camera camera = MakeCamera(viewport);
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
	std::filesystem::create_directories(directory);
	std::array<std::vector<uint8_t>,4> pixels;
	std::array<std::vector<uint32_t>,4> ids;
	for (unsigned phase = 0; phase < pixels.size(); ++phase) {
		if (phase == 1) Textures().Repack();
		if (phase >= 2) {
			Textures().Clear();
			if (phase == 3) {
				/* Force source charts across a floating-point exponent boundary;
				 * ordinary repacking can leave the problematic row magnitude intact. */
				auto &page = Textures().pages.emplace_back(); page.Reset();
				if (!page.allocator.Allocate(ATLAS_SIZE,ATLAS_SIZE/2)) throw std::runtime_error("World atlas probe cannot reserve its relocation rows");
			}
		}
		Scene scene;
		if (!CaptureScene(viewport,camera,scene) || !RenderScene(scene,camera,pixels[phase],&ids[phase])) throw std::runtime_error("World atlas verification failed to capture/render");
		if (const char *probe = std::getenv("OPENTT3D_WORLD_PIXEL")) {
			int x = 0, y = 0;
			if (std::sscanf(probe,"%d,%d",&x,&y) != 2 || x < viewport.left || y < viewport.top || x >= viewport.left+camera.width || y >= viewport.top+camera.height) throw std::runtime_error("World pixel probe must be an in-viewport screen X,Y");
			size_t at = static_cast<size_t>(camera.height-1-(y-viewport.top))*camera.width+x-viewport.left;
			uint32_t id = ids[phase][at];
			Debug(driver,1,"OpenTT3D: world pixel {},{} phase {} owner {} RGB {},{},{}",x,y,phase,id,pixels[phase][at*4],pixels[phase][at*4+1],pixels[phase][at*4+2]);
			if ((id&TILE_PICK_ID) != 0) {
				TileIndex tile{id&~TILE_PICK_ID};
				Debug(driver,1,"OpenTT3D: world pixel tile {},{} type {}",TileX(tile),TileY(tile),to_underlying(GetTileType(tile)));
				if (IsTileType(tile,MP_HOUSE)) Debug(driver,1,"OpenTT3D: world pixel house {} stage {}",GetHouseType(tile),GetHouseBuildingStage(tile));
			} else if (id != 0) {
				if (const auto *vehicle = Vehicle::GetIfValid(VehicleID{id-1})) Debug(driver,1,"OpenTT3D: world pixel vehicle {} engine {}",vehicle->index,vehicle->engine_type);
			}
			for (const auto &instance : scene.instances) if (id != 0 && instance.data.ObjectId() == id) {
				const auto &data = instance.data;
				Debug(driver,1,"OpenTT3D: world pixel candidate mesh {} vertices {} origin {},{},{} region {},{},{},{} page {} mode {}",
					reinterpret_cast<uintptr_t>(instance.mesh),instance.mesh->size(),data.origin_opacity[0],data.origin_opacity[1],data.origin_opacity[2],data.region.left,data.region.top,data.region.right,data.region.bottom,data.uv_transform[3],data.identity[3]);
				std::array<uint64_t,4> hashes{};
				hashes.fill(1469598103934665603ULL);
				for (const auto &vertex : *instance.mesh) {
					auto words = std::bit_cast<std::array<uint32_t,20>>(vertex);
					for (size_t i = 0; i < words.size(); ++i) { auto &hash = hashes[i < 3 ? 0 : i < 6 ? 1 : i >= 10 && i <= 12 ? 2 : 3]; hash = (hash^words[i])*1099511628211ULL; }
				}
				Debug(driver,1,"OpenTT3D: world pixel mesh hashes position {} normal {} UV {} other {}; scale {},{} centre {},{} UV transform {},{},{} mirror {},{},{} surface {} flags {}",
					hashes[0],hashes[1],hashes[2],hashes[3],data.scale_center[0],data.scale_center[1],data.scale_center[2],data.scale_center[3],data.uv_transform[0],data.uv_transform[1],data.uv_transform[2],data.mirror_layer_heading[0],data.mirror_layer_heading[1],data.mirror_layer_heading[2],data.identity[1],data.identity[2]);
			}
		}
		RecycleCapture(scene);
		std::ofstream image(directory/fmt::format("model-world-atlas-{}.pam",phase),std::ios::binary);
		image << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = camera.height-1; y >= 0; --y) image.write(reinterpret_cast<const char *>(pixels[phase].data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
	}
	for (unsigned phase = 1; phase < pixels.size(); ++phase) {
		size_t colours = 0, picking = 0, first = ids[0].size();
		for (size_t i = 0; i < ids[0].size(); ++i) {
			bool changed = !std::equal(pixels[0].begin()+i*4,pixels[0].begin()+i*4+4,pixels[phase].begin()+i*4);
			colours += changed; picking += ids[0][i] != ids[phase][i];
			if (first == ids[0].size() && (changed || ids[0][i] != ids[phase][i])) first = i;
		}
		if (first != ids[0].size()) {
			Debug(driver,1,"OpenTT3D: world atlas phase {} first difference at {},{} (screen {},{}), IDs {} -> {}, RGB {},{},{} -> {},{},{}",
				phase,first%camera.width,camera.height-1-first/camera.width,viewport.left+first%camera.width,viewport.top+camera.height-1-first/camera.width,
				ids[0][first],ids[phase][first],pixels[0][first*4],pixels[0][first*4+1],pixels[0][first*4+2],pixels[phase][first*4],pixels[phase][first*4+1],pixels[phase][first*4+2]);
			throw std::runtime_error(fmt::format("Whole-world atlas relocation phase {} changed {} colour pixels and {} picking IDs",phase,colours,picking));
		}
	}
	Debug(driver,1,"OpenTT3D: whole-world atlas relocation preserves {} exact RGBA/picking pixels across repack, clear and forced row relocation",ids[0].size());
}

void VerifyTilePicking()
{
	Viewport viewport{};
	viewport.width = 640; viewport.height = 480; viewport.zoom = ZoomLevel::Normal;
	struct Cleanup { const Viewport *viewport; ~Cleanup() { ForgetViewport(viewport); } } cleanup{&viewport};
	unsigned attempts = 0, checked = 0;
	for (uint32_t index = 0; index < Map::Size() && attempts < 32; ++index) {
		TileIndex tile{index};
		if (!IsTileType(tile,MP_HOUSE) || GetHouseBuildingStage(tile) != TOWN_HOUSE_COMPLETED) continue;
		++attempts;
		unsigned views = 0;
		for (unsigned turn = 0; turn < 4; ++turn) {
			Camera camera{{TileX(tile)*16.0f+8,TileY(tile)*16.0f+8,TerrainZ(GetTileMaxPixelZ(tile))+8.0f},6,viewport.width,viewport.height,turn+0.25f};
			camera.vertical_fov = VIEWPORT_VERTICAL_FOV;
			camera_positions[&viewport].snapshot = camera;
			Scene scene;
			if (!CaptureScene(viewport,camera,scene)) throw std::runtime_error("Tile picking verification: world capture failed");
			std::vector<uint8_t> pixels;
			std::vector<uint32_t> ids;
			if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("Tile picking verification: GPU readback failed");
			Scene untagged = scene;
			for (auto &instance : untagged.instances) if ((instance.data.ObjectId() & TILE_PICK_ID) != 0) instance.data.SetObjectId(0);
			for (auto &vertex : untagged.vertices) if ((vertex.object_id & TILE_PICK_ID) != 0) vertex.object_id = 0;
			std::vector<uint8_t> unchanged_colours;
			if (!RenderScene(untagged,camera,unchanged_colours) || pixels != unchanged_colours) throw std::runtime_error("Tile picking verification: ownership tags changed world colours/material mirroring");
			Frame frame{0,0,viewport.width,viewport.height,viewport.zoom,{}, {},frame_epoch,TextureGeneration(),false,camera};
			frame.picking.resize(ids.size());
			for (int y = 0; y < viewport.height; ++y) std::copy_n(ids.data()+static_cast<size_t>(viewport.height-1-y)*viewport.width,viewport.width,frame.picking.data()+static_cast<size_t>(y)*viewport.width);
			frames.insert_or_assign(&viewport,std::move(frame));
			unsigned samples = 0;
			Point witness{-1,-1};
			for (int y = 0; y < viewport.height && samples < 16; y += 3) for (int x = 0; x < viewport.width && samples < 16; x += 3) {
				if (frames.at(&viewport).picking[static_cast<size_t>(y)*viewport.width+x] != (TILE_PICK_ID | index)) continue;
				Point terrain = PickTerrain(viewport,x,y,false);
				if (terrain.x >= 0 && TileVirtXY(terrain.x,terrain.y) == tile) continue;
				/* These are exactly the roof/wall pixels that a terrain-only ray
				 * would assign to a different tile (or miss altogether). */
				Point selected = TranslateXYToTileCoord(viewport,x,y,false);
				if (selected.x < 0 || TileVirtXY(selected.x,selected.y) != tile || PickVehicle(viewport,x,y) != nullptr) throw std::runtime_error("Tile picking verification: a structure selected another tile or a vehicle");
				witness = {x,y}; ++samples;
			}
			if (samples == 0) { RecycleCapture(scene); break; }
			if (Vulkan::Active() || OpenGL::Active()) {
				if (!(Vulkan::Active() ? Vulkan::RenderViewport(&viewport,scene,camera) : OpenGL::RenderViewport(&viewport,scene,camera))) throw std::runtime_error("Tile picking verification: GPU-resident capture failed");
				auto &resident = frames.at(&viewport);
				resident.gpu_resident = true; resident.pick_epoch = UINT64_MAX;
				Point selected = TranslateXYToTileCoord(viewport,witness.x,witness.y,false);
				if (selected.x < 0 || TileVirtXY(selected.x,selected.y) != tile || PickVehicle(viewport,witness.x,witness.y) != nullptr) throw std::runtime_error("Tile picking verification: GPU-resident tile ownership differs");
			}
			RecycleCapture(scene);
			checked += samples; ++views;
		}
		if (views == 4) {
			Debug(driver,1,"OpenTT3D: {} roof/wall pixels select their owning tile across four rotations, with independent vehicle picking",checked);
			return;
		}
	}
	throw std::runtime_error("Tile picking verification requires a visible completed building fixture");
}

/** Exercise the same text-effect registry/projection path used by actual drawing,
 * including secondary viewports, message updates and reuse by legacy effects. */
static void VerifyTextEffectAnchors()
{
	int x = (Map::MaxX()/2)*TILE_SIZE+8, y = (Map::MaxY()/2)*TILE_SIZE+8;
	int z = GetSlopePixelZ(x,y)+6;
	Vec3 world{static_cast<float>(x),static_cast<float>(y),TerrainZ(z)};
	Viewport viewport{};
	struct Cleanup {
		Viewport &viewport;
		std::vector<TextEffectID> effects;
		~Cleanup() { for (auto id : effects) if (id != INVALID_TE_ID) RemoveTextEffect(id); ForgetViewport(&viewport); }
	} cleanup{viewport,{}};
	cleanup.effects.push_back(ShowFillingPercent(x,y,z,42,STR_PERCENT_NONE));
	cleanup.effects.push_back(AddTextEffectAtWorld(GetEncodedString(STR_INCOME_FLOAT_INCOME,100),x,y,z,74,TE_RISING));
	if (std::ranges::find(cleanup.effects,INVALID_TE_ID) != cleanup.effects.end()) throw std::runtime_error("Text effects require a loaded game");
	unsigned checks = 0;
	for (bool secondary : {false,true}) for (unsigned turn = 0; turn < 4; ++turn) for (unsigned pose = 0; pose < 3; ++pose) {
		viewport.width = secondary ? 320 : 640; viewport.height = secondary ? 180 : 480;
		viewport.virtual_left = secondary ? 7800 : -2400; viewport.virtual_top = secondary ? -4300 : 1500;
		viewport.zoom = static_cast<ZoomLevel>(pose+1);
		Camera camera{world+Vec3{7.0f*pose,-3.0f*pose,0},0.8f+pose*0.6f,viewport.width,viewport.height,turn+0.17f};
		camera.pitch = 15+pose*15;
		if (pose == 2) { camera.focus = camera.Eye(); camera.first_person = true; }
		camera_positions[&viewport].snapshot = camera;
		auto point = camera.Project(world);
		if (!point.visible) throw std::runtime_error("Text-effect reference anchor is behind the camera");
		for (TextEffectID id : cleanup.effects) {
			ViewportSign legacy = GetTextEffectSign(id), projected = GetTextEffectSign(id,&viewport);
			Point original = RemapCoords(x,y,z);
			int expected_x = viewport.virtual_left+ScaleByZoom(static_cast<int>(std::lround(point.x)),viewport.zoom)+legacy.center-original.x;
			int expected_y = viewport.virtual_top+ScaleByZoom(static_cast<int>(std::lround(point.y)),viewport.zoom)+legacy.top-original.y;
			if (projected.center != expected_x || projected.top != expected_y || projected.width_normal != legacy.width_normal) {
				throw std::runtime_error("Text effects lost their world anchor after camera/viewport movement");
			}
			++checks;
		}
		UpdateFillingPercent(cleanup.effects[0],73,STR_PERCENT_UP_DOWN);
	}
	RemoveTextEffect(cleanup.effects.back()); cleanup.effects.pop_back();
	auto id = AddTextEffect(GetEncodedString(STR_JUST_INT,123),51,93,74,TE_RISING);
	cleanup.effects.push_back(id);
	auto legacy = GetTextEffectSign(id), projected = GetTextEffectSign(id,&viewport);
	if (legacy.center != projected.center || legacy.top != projected.top) throw std::runtime_error("Reused legacy text effect retained a stale world anchor");
	Debug(driver,1,"OpenTT3D: {} loading/income text anchors follow orbit, dolly, Cab and secondary viewports; registry reuse passed",checks);
}

/** Integration check against the loaded terrain and actual window input paths. */
void VerifyViewportNavigation()
{
	Window *window = GetMainWindow();
	if (!IsEnabled() || window == nullptr || window->viewport == nullptr) throw std::runtime_error("Navigation verification requires a 3D world viewport");
	VerifyTextEffectAnchors();
	ViewportData &vp = *window->viewport;
	struct Restore {
		Window &window;
		ViewportData saved;
		float saved_rotation;
		CameraPosition saved_position;
		~Restore()
		{
			HandleMiddleOrbit(false, {}, {});
			*window.viewport = saved;
			rotation = saved_rotation;
			camera_positions[window.viewport.get()] = saved_position;
			frames.erase(window.viewport.get());
			DoZoomInOutWindow(ZOOM_NONE, &window);
			RebuildViewportOverlay(&window);
			window.SetDirty();
		}
	} restore{*window, vp, rotation, camera_positions[&vp]};
	const int center_x = vp.virtual_left + vp.virtual_width / 2;
	const int center_y = vp.virtual_top + vp.virtual_height / 2;
	unsigned checks = 0;
	for (unsigned turn = 0; turn < 4; ++turn) {
		rotation = turn;
		for (ZoomLevel zoom : {ZoomLevel::In2x, ZoomLevel::Normal, ZoomLevel::Out2x}) {
			for (int u : {1, 2}) for (int v : {1, 2}) {
				for (bool in : {false, true}) {
					vp = restore.saved;
					camera_positions[&vp] = restore.saved_position;
					vp.follow_vehicle = VehicleID::Invalid();
					vp.zoom = zoom;
					auto &position = camera_positions[&vp];
					position.zoom_current = position.zoom_target = to_underlying(zoom);
					position.zoom_anchor.reset();
					position.fixed_focus.reset();
					position.free_orbit = false;
					vp.virtual_width = ScaleByZoom(vp.width, zoom);
					vp.virtual_height = ScaleByZoom(vp.height, zoom);
					SetScrollPosition(vp, {center_x - vp.virtual_width / 2, center_y - vp.virtual_height / 2});
					Point cursor{vp.left + vp.width * u / 3, vp.top + vp.height * v / 3};
					Point hit = PickTerrain(vp, cursor.x, cursor.y, false);
					if (hit.x == -1) continue;
					float x = cursor.x - vp.left + 0.5f, y = cursor.y - vp.top + 0.5f;
					auto anchor = MakeCamera(vp).ScreenRay(x, y).AtZ(TerrainZ(GetSlopePixelZ(hit.x, hit.y)));
					if (!anchor.has_value()) throw std::runtime_error("Navigation verification: missing terrain anchor");
					ZoomAtCursor(*window, in, cursor);
					for (unsigned frame = 0; frame < 90; ++frame) UpdateCameraMotion(1.0f / 60);
					auto projected = MakeCamera(vp).Project(*anchor);
					float error = std::hypot(projected.x - x, projected.y - y);
					if (error > 1.0f) throw std::runtime_error(fmt::format("Navigation verification: zoom anchor moved {:.3f}px (rotation {}, zoom {}, in {})", error, turn, to_underlying(zoom), in));
					++checks;
					/* The input delta must move the same terrain-plane point to the cursor. */
					hit = PickTerrain(vp, cursor.x, cursor.y, false);
					if (hit.x == -1) continue;
					Point delta{-17, 11};
					anchor = MakeCamera(vp).ScreenRay(x + delta.x, y + delta.y).AtZ(TerrainZ(GetSlopePixelZ(hit.x, hit.y)));
					if (!anchor.has_value()) continue;
					ScrollAtCursor(*window, delta, cursor);
					projected = MakeCamera(vp).Project(*anchor);
					error = std::hypot(projected.x - x, projected.y - y);
					if (error > 1.0f) throw std::runtime_error(fmt::format("Navigation verification: drag anchor moved {:.3f}px (rotation {})", error, turn));
					++checks;
				}
			}
		}
	}
	if (checks < 16) throw std::runtime_error("Navigation verification: insufficient visible terrain");
	Debug(driver, 1, "OpenTT3D: {} terrain zoom/drag anchor checks passed across all rotations", checks);
	SetZoom(*window, MIN_CAMERA_ZOOM, true);
	if (CanZoom(vp, true) || std::abs(GetEffectiveZoom(vp)-MIN_CAMERA_ZOOM) > 0.01f) throw std::runtime_error("Navigation verification: extended close zoom is unavailable");
	Point orbit_point{vp.left + vp.width / 2, vp.top + vp.height * 3 / 4};
	if (FindWindowFromPt(orbit_point.x, orbit_point.y) == window) {
		float initial = rotation;
		Camera before_orbit = MakeCamera(vp);
		HandleMiddleOrbit(true, orbit_point, {});
		if (!orbit_gesture) throw std::runtime_error("Navigation verification: middle press did not pick an orbit pivot");
		Vec3 pivot = orbit_gesture->pivot;
		auto pixel = before_orbit.Project(pivot);
		HandleMiddleOrbit(true, orbit_point, {37, 19});
		float held = rotation;
		float held_pitch = MakeCamera(vp).pitch;
		auto after_orbit = MakeCamera(vp).Project(pivot);
		if (held_pitch == before_orbit.pitch || std::hypot(pixel.x - after_orbit.x, pixel.y - after_orbit.y) > 0.1f) throw std::runtime_error(fmt::format("Navigation verification: middle tilt moved the picked pivot: pixel {:.6f},{:.6f} expected {:.6f},{:.6f}, pivot {},{},{}; focus before {},{},{} after {},{},{}; pitch {} -> {}",after_orbit.x,after_orbit.y,pixel.x,pixel.y,pivot.x,pivot.y,pivot.z,before_orbit.focus.x,before_orbit.focus.y,before_orbit.focus.z,MakeCamera(vp).focus.x,MakeCamera(vp).focus.y,MakeCamera(vp).focus.z,before_orbit.pitch,held_pitch));
		HandleMiddleOrbit(false, orbit_point, {});
		HandleMiddleOrbit(false, orbit_point, {100, 100});
		UpdateViewportPosition(window, 30);
		auto released = MakeCamera(vp).Project(pivot);
		if (MakeCamera(vp).pitch != held_pitch || std::hypot(pixel.x - released.x, pixel.y - released.y) > 0.1f) throw std::runtime_error("Navigation verification: orbit pivot or tilt changed after release");
		if (held == initial || rotation != held || std::abs(held - std::round(held)) < 0.001f) throw std::runtime_error("Navigation verification: middle orbit did not retain continuous yaw");
		Viewport copy = vp;
		CopyViewportCamera(vp, copy);
		if (std::abs(MakeCamera(copy).pitch - held_pitch) > 0.001f) throw std::runtime_error("Navigation verification: screenshot lost orbit tilt");
		ForgetViewport(&copy);
		Point terrain = PickTerrain(vp, orbit_point.x, orbit_point.y, false);
		if (terrain.x >= 0) {
			Camera tilted = MakeCamera(vp);
			float x = orbit_point.x - vp.left + 0.5f, y = orbit_point.y - vp.top + 0.5f;
			auto anchor = tilted.ScreenRay(x, y).AtZ(TerrainZ(GetSlopePixelZ(terrain.x, terrain.y)));
			if (!anchor) throw std::runtime_error("Navigation verification: missing tilted zoom anchor");
			/* At street-level magnification the float world-point grid is a
			 * visible fraction of a pixel. Measure preservation of the actual
			 * picked point, as the orbit check above does, not a different ideal
			 * point that the world coordinate cannot represent. */
			auto picked_pixel = tilted.Project(*anchor);
			ZoomAtCursor(*window, false, orbit_point);
			for (unsigned frame = 0; frame < 90; ++frame) UpdateCameraMotion(1.0f / 60);
			auto projected = MakeCamera(vp).Project(*anchor);
			if (std::hypot(projected.x - picked_pixel.x, projected.y - picked_pixel.y) > 0.1f || MakeCamera(vp).pitch != held_pitch) throw std::runtime_error(fmt::format("Navigation verification: tilted zoom changed its anchor or pitch: pixel {:.4f},{:.4f} expected {:.4f},{:.4f}, anchor {},{},{}",projected.x,projected.y,picked_pixel.x,picked_pixel.y,anchor->x,anchor->y,anchor->z));
			Point delta{-13, 7};
			anchor = MakeCamera(vp).ScreenRay(x + delta.x, y + delta.y).AtZ(TerrainZ(GetSlopePixelZ(terrain.x, terrain.y)));
			if (anchor) {
				ScrollAtCursor(*window, delta, orbit_point);
				projected = MakeCamera(vp).Project(*anchor);
				if (std::hypot(projected.x - x, projected.y - y) > 1.0f) throw std::runtime_error("Navigation verification: tilted pan changed its anchor");
			}
		}
	}
	Debug(driver, 1, "OpenTT3D: extended zoom and persistent continuous orbit checks passed");
	Debug(driver, 1, "OpenTT3D: clicked-point yaw/tilt, release persistence and tilted screenshots passed");
	/* Reproduce the reported exhausted dolly range after an orbit lifts its
	 * mathematical focus. Rebasing must preserve the actual view, then allow
	 * the remaining descent rather than keeping the eye high above the map. */
	SetZoom(*window,MIN_CAMERA_ZOOM,true);
	PinFocus(vp,MakeCamera(vp).focus+Vec3{0,0,128},false);
	Camera raised = MakeCamera(vp);
	if (!CanZoom(vp,true)) throw std::runtime_error("Navigation verification: raised orbit focus exhausted the street-level zoom range");
	Camera rebased = MakeCamera(vp);
	Vec3 eye_error = raised.Eye()-rebased.Eye();
	if (Dot(eye_error,eye_error) > 0.0001f || raised.rotation != rebased.rotation || raised.pitch != rebased.pitch) throw std::runtime_error("Navigation verification: rebasing zoom changed the actual camera pose");
	SetZoom(*window,MIN_CAMERA_ZOOM,true);
	if (MakeCamera(vp).Eye().z-CameraGroundHeight(MakeCamera(vp).focus.x,MakeCamera(vp).focus.y) > 20) throw std::runtime_error("Navigation verification: zoom could not return to street level");
	for (float level : {MIN_CAMERA_ZOOM,-3.0f,0.0f,3.0f,5.0f}) {
		SetZoom(*window,level,true);
		Camera before_legacy_change = MakeCamera(vp);
		float dolly_before = GetEffectiveZoom(vp);
		ZoomLevel legacy = vp.zoom;
		vp.zoom = legacy == ZoomLevel::Normal ? ZoomLevel::Out2x : ZoomLevel::Normal;
		UpdateCameraMotion(1.0f/60);
		if (GetEffectiveZoom(vp) != dolly_before || MakeCamera(vp).vertical_fov != VIEWPORT_VERTICAL_FOV || before_legacy_change.vertical_fov != VIEWPORT_VERTICAL_FOV) throw std::runtime_error("Navigation verification: legacy/DPI zoom changed the 3D lens or dolly range");
		vp.zoom = legacy;
	}
	Debug(driver,1,"OpenTT3D: fixed FOV, legacy-zoom independence and street-level recovery after orbit passed");
	unsigned following_checks = 0;
	for (const Vehicle *vehicle : Vehicle::Iterate()) {
		if (vehicle->vehstatus.Test(VehState::Hidden)) continue;
		vp.follow_vehicle = vehicle->index;
		for (unsigned turn = 0; turn < 4; ++turn) {
			rotation = turn;
			auto projected = MakeCamera(vp).Project({static_cast<float>(vehicle->x_pos), static_cast<float>(vehicle->y_pos), RenderVehicleZ(*vehicle)});
			if (!projected.visible || std::abs(projected.x - vp.width * 0.5f) > 0.01f || std::abs(projected.y - vp.height * 0.5f) > 0.01f) {
				throw std::runtime_error("Navigation verification: followed vehicle is not centred");
			}
			Viewport copy = vp;
			CopyViewportCamera(vp, copy);
			auto copied = MakeCamera(copy).Project({static_cast<float>(vehicle->x_pos), static_cast<float>(vehicle->y_pos), RenderVehicleZ(*vehicle)});
			ForgetViewport(&copy);
			if (std::abs(projected.x - copied.x) > 0.01f || std::abs(projected.y - copied.y) > 0.01f) throw std::runtime_error("Navigation verification: screenshot lost the follow camera");
			++following_checks;
		}
		if (following_checks >= 64) break;
	}
	Debug(driver, 1, "OpenTT3D: {} live vehicle-follow and screenshot camera checks passed", following_checks);
	for (const Vehicle *vehicle : Vehicle::Iterate()) {
		if (!vehicle->IsPrimaryVehicle() || vehicle->vehstatus.Test(VehState::Hidden)) continue;
		camera_positions[&vp].cab.reset();
		if (!ToggleFirstPerson(vehicle->index)) throw std::runtime_error("Navigation verification: could not enter a vehicle cab");
		Camera cab = MakeCamera(vp);
		if (!cab.first_person || cab.hidden_object != vehicle->index.base() + 1) throw std::runtime_error("Navigation verification: invalid cab camera or visible camera vehicle");
		if (FindWindowFromPt(orbit_point.x, orbit_point.y) == window) {
			HandleMiddleOrbit(true, orbit_point, {});
			HandleMiddleOrbit(true, orbit_point, {23, -27});
			HandleMiddleOrbit(false, orbit_point, {});
			Camera looked = MakeCamera(vp);
			if (!looked.first_person || looked.pitch >= cab.pitch || looked.rotation == cab.rotation || Dot(looked.focus - cab.focus, looked.focus - cab.focus) > 0.0001f) throw std::runtime_error("Navigation verification: cab free-look must retain vehicle eye");
			ZoomAtCursor(*window, true, orbit_point);
			for (unsigned frame = 0; frame < 90; ++frame) UpdateCameraMotion(1.0f / 60);
			if (!MakeCamera(vp).first_person || MakeCamera(vp).pitch != looked.pitch || MakeCamera(vp).vertical_fov != looked.vertical_fov || CanZoom(vp,true) || CanZoom(vp,false)) throw std::runtime_error("Navigation verification: Cab must retain its fixed lens and disable zoom");
		}
		auto &motion = *camera_positions[&vp].cab;
		motion.heading -= 0.5f;
		float previous = motion.heading;
		UpdateCameraMotion(1.0f / 60);
		if (motion.heading <= previous || motion.heading >= previous + 0.5f) throw std::runtime_error("Navigation verification: cab heading snaps rather than interpolates");
		Viewport copy = vp;
		CopyViewportCamera(vp, copy);
		Camera snapshot = MakeCamera(copy);
		ForgetViewport(&copy);
		if (!snapshot.first_person || snapshot.rotation != MakeCamera(vp).rotation || snapshot.pitch != MakeCamera(vp).pitch) throw std::runtime_error("Navigation verification: cab screenshot lost its orientation");
		ToggleFirstPerson(vehicle->index);
		if (MakeCamera(vp).first_person) throw std::runtime_error("Navigation verification: could not leave the vehicle cab");
		Debug(driver, 1, "OpenTT3D: first-person mode, smooth heading and cab screenshot checks passed");
		break;
	}
	/* Test the real loaded-world capture/picker from beyond the former 4096-unit
	 * cutoff, aimed at the map centre. No simulation state or RNG is touched. */
	Vec3 target{Map::MaxX() * 8.0f, Map::MaxY() * 8.0f, 0};
	target.z = TerrainZ(GetSlopePixelZ(static_cast<int>(target.x), static_cast<int>(target.y)));
	Camera distant{target + Vec3{-8192, -8192, 512}, 1, vp.width, vp.height, 2};
	distant.first_person = true; distant.vertical_fov = 60;
	distant.pitch = std::atan2(512 * Camera::WORLD_Z_SCALE, std::hypot(8192.0f, 8192.0f)) * 180 / std::numbers::pi_v<float>;
	camera_positions[&vp].snapshot = distant;
	BeginCapture(distant);
	auto tile_bounds = CaptureTileBounds();
	FinishCapture();
	int tx = static_cast<int>(target.x / 16), ty = static_cast<int>(target.y / 16);
	if (tx < tile_bounds[0] || tx > tile_bounds[2] || ty < tile_bounds[1] || ty > tile_bounds[3]) throw std::runtime_error("Navigation verification: distant map centre was excluded from capture");
	Point hit = PickTerrain(vp, vp.left + vp.width / 2, vp.top + vp.height / 2, false);
	if (hit.x < 0) {
		Ray ray = distant.ScreenRay(vp.width / 2 + 0.5f, vp.height / 2 + 0.5f);
		double enter = 0, leave = std::numeric_limits<double>::infinity();
		bool intersects = ray.ClipBox({0, 0, 0}, {Map::MaxX() * 16.0f - 0.001f, Map::MaxY() * 16.0f - 0.001f, TerrainZ(_settings_game.construction.map_height_limit * TILE_HEIGHT + 2.0f * TILE_HEIGHT)}, enter, leave);
		throw std::runtime_error(fmt::format("Navigation verification: distant terrain picking failed: eye {},{},{} ray {},{},{} map {},{} target {},{},{} interval {} {} {}", ray.origin.x, ray.origin.y, ray.origin.z, ray.direction.x, ray.direction.y, ray.direction.z, Map::MaxX(), Map::MaxY(), target.x, target.y, target.z, intersects, enter, leave));
	}
	ViewportSign sign{};
	auto label = ProjectSign(vp, sign, static_cast<int>(target.x), static_cast<int>(target.y), static_cast<int>(target.z/TERRAIN_HEIGHT_SCALE));
	if (label.center == -INT_MAX / 4) throw std::runtime_error("Navigation verification: distant first-person label was clipped");
	Debug(driver, 1, "OpenTT3D: first-person terrain capture, picking and labels beyond 4096 world units passed");
}

} // namespace Renderer3D
