/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_CROSSING_CAPTURE_H
#define RENDERER3D_CROSSING_CAPTURE_H
#include "crossing_geometry.hpp"
#include "camera.hpp"

namespace Renderer3D {
void DrawCrossing(Scene &scene, const Camera &camera, Vec3 origin, unsigned kind, unsigned axis, bool barred, bool tram, bool reserved = false);
bool FocusCrossing();
void ExportCrossingGallery(unsigned kind, unsigned axis, bool barred);
void VerifyCrossings();
}
#endif
