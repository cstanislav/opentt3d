/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_GROUND_DETAIL_CAPTURE_H
#define RENDERER3D_GROUND_DETAIL_CAPTURE_H

#include "ground_detail_geometry.hpp"
#include "clear_surface_geometry.hpp"
#include "camera.hpp"
#include "../slope_type.h"

namespace Renderer3D {
void DrawGroundDetails(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, bool rocks, unsigned variant, unsigned snow = 0);
void DrawClearSurface(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, bool rough, unsigned variant, unsigned fine_edges = 15);
void ExportGroundDetailGallery(unsigned kind, unsigned variant, unsigned slope);
void VerifyGroundDetails();
void VerifyGroundContinuity();
bool FocusGroundDetail(unsigned kind, unsigned variant);
}
#endif
