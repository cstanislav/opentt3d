/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_RAIL_DETAIL_CAPTURE_H
#define RENDERER3D_RAIL_DETAIL_CAPTURE_H

#include "rail_detail_geometry.hpp"
#include "camera.hpp"

namespace Renderer3D {
void DrawRailSignal(Scene &scene, const Camera &camera, Vec3 origin, unsigned type, unsigned variant, unsigned state, unsigned direction, float height_limit = 16);
void DrawCatenaryWire(Scene &scene, const Camera &camera, Vec3 origin, unsigned track, int grade, unsigned supports, unsigned half, bool transparent);
void DrawCatenaryPylon(Scene &scene, Vec3 origin, Vec3 contact, bool transparent);
void ExportSignalGallery(unsigned type, unsigned variant, unsigned state);
void ExportCatenaryGallery(unsigned track, int grade);
void VerifyRailDetails();
bool FocusRailDetail(bool catenary);
}
#endif
