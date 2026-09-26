/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_DEPOT_CAPTURE_H
#define RENDERER3D_DEPOT_CAPTURE_H

#include "depot_geometry.hpp"
#include "camera.hpp"
#include "../gfx_type.h"

namespace Renderer3D {
bool HasVoxelDepot(unsigned kind, unsigned direction);
unsigned VoxelDepotState(unsigned direction);
void DrawDepot(Scene &scene, const Camera &camera, Vec3 origin, unsigned kind, unsigned direction, PaletteID palette, bool transparent = false, bool invisible = false, bool reserved = false, bool original_family = true, unsigned floor_state = UINT_MAX);
bool FocusDepot(unsigned voxel_kind = UINT_MAX, unsigned voxel_direction = UINT_MAX);
void ExportDepotGallery(unsigned kind, unsigned direction);
void VerifyDepots();
bool HasVoxelShipDepot(unsigned axis, unsigned part);
bool DrawVoxelShipDepot(Scene &scene, Vec3 origin, unsigned axis, unsigned part, PaletteID palette, bool transparent = false, bool invisible = false);
bool FocusShipDepot(unsigned axis);
Scene ShipDepotReviewScene(unsigned axis, PaletteID palette, bool transparent = false, bool invisible = false);
void VerifyShipDepots();
}
#endif
