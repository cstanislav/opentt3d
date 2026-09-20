/* SPDX-License-Identifier: GPL-2.0-only */
/** @file viewport_3d.h Narrow integration surface for upstream presentation code. */

#ifndef RENDERER3D_VIEWPORT_3D_H
#define RENDERER3D_VIEWPORT_3D_H

#include "../gfx_type.h"
#include "../tile_type.h"
#include "../viewport_type.h"

struct Vehicle;

namespace Renderer3D {

bool IsEnabled();
bool SetEnabled(bool enabled);
void RotateCamera(int quarter_turns);
unsigned GetRotation();
void BeginFrame();
bool DrawViewport(const Viewport &viewport, const DrawPixelInfo &dpi);
Point PickTerrain(const Viewport &viewport, int screen_x, int screen_y, bool clamp_to_map);
Vehicle *PickVehicle(const Viewport &viewport, int screen_x, int screen_y);
Point UnrotateScroll(Point virtual_delta);
ViewportSign ProjectSign(const Viewport &viewport, const ViewportSign &sign, int x, int y, int z);
ViewportSign ProjectSign(const Viewport &viewport, const ViewportSign &sign, TileIndex tile);
bool FocusReferenceModel();

} // namespace Renderer3D

#endif
