/* SPDX-License-Identifier: GPL-2.0-only */
/** @file viewport_3d.h Narrow integration surface for upstream presentation code. */

#ifndef RENDERER3D_VIEWPORT_3D_H
#define RENDERER3D_VIEWPORT_3D_H

#include "../gfx_type.h"
#include "../tile_type.h"
#include "../viewport_type.h"
#include "../vehicle_type.h"
#include <optional>

struct Vehicle;
struct Window;

namespace Renderer3D {

bool IsEnabled();
bool SetEnabled(bool enabled);
void RotateCamera(float quarter_turns);
float GetRotation();
float GetPitch(const Viewport &viewport);
void ResetCameraRotation();
bool ToggleFirstPerson(VehicleID vehicle);
bool IsFirstPerson(VehicleID vehicle);
void CancelFirstPerson(const Viewport &viewport);
void ReplaceCameraVehicle(VehicleID previous, VehicleID replacement);
bool HandleMiddleOrbit(bool pressed, Point cursor, Point delta);
void BeginFrame();
void BeginReadback();
void EndReadback();
void ForgetViewport(const Viewport *viewport);
void CopyViewportCamera(const Viewport &source, const Viewport &destination);
bool DrawViewport(const Viewport &viewport, const DrawPixelInfo &dpi);
Point PickTerrain(const Viewport &viewport, int screen_x, int screen_y, bool clamp_to_map);
Point PickMap(const Viewport &viewport, int screen_x, int screen_y, bool clamp_to_map);
Vehicle *PickVehicle(const Viewport &viewport, int screen_x, int screen_y);
Point UnrotateScroll(Point virtual_delta);
bool ZoomAtCursor(Window &window, bool in, Point cursor);
bool Zoom(Window &window, bool in, std::optional<Point> cursor = {});
bool SetZoom(Window &window, float level, bool instant, std::optional<Point> cursor = {});
bool CanZoom(const Viewport &viewport, bool in);
float GetEffectiveZoom(const Viewport &viewport);
bool ScrollAtCursor(Window &window, Point delta, Point cursor);
ViewportSign ProjectSign(const Viewport &viewport, const ViewportSign &sign, int x, int y, int z);
ViewportSign ProjectSign(const Viewport &viewport, const ViewportSign &sign, TileIndex tile);
bool FocusReferenceModel();
void VerifyViewportNavigation();
void VerifyTilePicking();
void VerifyWorldAtlas();

} // namespace Renderer3D

#endif
