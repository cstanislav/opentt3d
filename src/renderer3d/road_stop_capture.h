/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_ROAD_STOP_CAPTURE_H
#define RENDERER3D_ROAD_STOP_CAPTURE_H
#include "road_stop_geometry.hpp"
#include "camera.hpp"
#include "../gfx_type.h"
namespace Renderer3D {
void DrawRoadStop(Scene &scene, const Camera &camera, Vec3 origin, bool truck, unsigned layout, bool tram, PaletteID palette, bool transparent = false, bool invisible = false, float height_limit = 12);
bool FocusRoadStop();
void ExportRoadStopGallery(bool truck, unsigned layout);
void VerifyRoadStops();
}
#endif
