/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_STATION_CAPTURE_H
#define RENDERER3D_STATION_CAPTURE_H

#include "station_geometry.hpp"
#include "camera.hpp"
#include "../rail_type.h"
#include "../gfx_type.h"

namespace Renderer3D {
void DrawRailStation(Scene &scene, const Camera &camera, Vec3 origin, RailType type, unsigned layout, PaletteID palette, bool transparent);
void ExportStationGallery(unsigned type, unsigned layout);
void VerifyStationModels();
bool FocusReferenceStation();
unsigned VoxelDockState();
bool HasVoxelDock(unsigned graphics);
bool DrawVoxelDock(Scene &scene, Vec3 origin, unsigned graphics, PaletteID palette, bool transparent = false, bool invisible = false);
bool FocusVoxelDock(unsigned graphics);
Scene DockReviewScene(unsigned graphics, PaletteID palette, bool transparent = false, bool invisible = false);
Scene JoinedDockReviewScene(unsigned direction, PaletteID palette, bool transparent = false, bool invisible = false);
void VerifyDocks();
}
#endif
