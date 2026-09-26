/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_TUNNEL_CAPTURE_H
#define RENDERER3D_TUNNEL_CAPTURE_H

#include "camera.hpp"
#include "tunnel_geometry.hpp"
#include "../tile_type.h"

struct Vehicle;

namespace Renderer3D {
const TunnelAssembly &TunnelGeometry(TunnelKind kind, bool portal);
void DrawTunnelSection(Scene &scene, const Camera &camera, Vec3 tile_origin, unsigned direction, TunnelKind kind, bool portal, bool snow_desert, bool reserved = false);
bool GetVanillaTunnelKind(TileIndex entrance, TunnelKind &kind);
bool IsVehicleInTunnel(const Vehicle &vehicle);
void BeginTunnelFrame();
bool TunnelLabelVisible(const Camera &camera, Vec3 point);
void ExportTunnelGallery(unsigned kind, unsigned direction);
void VerifyTunnelModels();
void VerifyLiveTunnelCapture();
bool FocusReferenceTunnel();
} // namespace Renderer3D
#endif
