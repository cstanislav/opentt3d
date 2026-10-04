/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_RAIL_CAPTURE_H
#define RENDERER3D_RAIL_CAPTURE_H

#include "rail_geometry.hpp"
#include "camera.hpp"
#include "../rail_type.h"
#include "../track_type.h"
#include "../slope_type.h"

struct TileInfo;

namespace Renderer3D {
bool CaptureRailTile(TileInfo &tile, TrackBits tracks);
bool SupportedRailType(RailType type);
void DrawRailTracks(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, RailType type, TrackBits tracks, TrackBits reserved);
const RailAssembly &RailGeometry(RailType type, Track track, Slope slope, unsigned lod = 0, TrackBits layout = TRACK_BIT_NONE);
void ExportRailGallery(unsigned type, unsigned tracks, unsigned slope);
void VerifyRailModels();
}
#endif
