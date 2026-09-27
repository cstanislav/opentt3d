/* SPDX-License-Identifier: GPL-2.0-only */
/** @file world_capture.h Capture upstream visual decisions before 2D projection/culling. */
#ifndef RENDERER3D_WORLD_CAPTURE_H
#define RENDERER3D_WORLD_CAPTURE_H

#include "camera.hpp"
#include "../sprite.h"
#include "../tile_type.h"
#include "../slope_type.h"
#include "../viewport_type.h"
#include "../rail_type.h"
#include "../track_type.h"

struct Vehicle;
struct TileInfo;

namespace Renderer3D {
struct TileSurface;
TileSurface MakeTileSurface(Slope slope);
bool IsCapturing();
void BeginCaptureFrame(float seconds);
void BeginCapture(const Camera &camera, bool diagnostic = false, std::optional<bool> tunnel_scenery_cull = {});
Scene FinishCapture();
void RecycleCapture(Scene &scene);
void CaptureTile(const TileInfo *tile);
void CaptureVehicle(const Vehicle *vehicle);
float RenderVehicleZ(const Vehicle &vehicle);
bool CaptureFence(const TileInfo &tile, unsigned style, unsigned layout, SpriteID image, SpriteID material, PaletteID palette);
bool FocusReferenceFence(unsigned style);
bool CaptureFoundation(const TileInfo &tile, Foundation foundation);
bool FocusReferenceFoundation(std::string_view kind);
bool CaptureTunnel(const TileInfo &tile);
void CaptureRailTracks(const TileInfo &tile, RailType type, TrackBits tracks, TrackBits reserved);
void CaptureRailSupport(Vec3 origin, Slope slope, RailType type, TrackBits tracks);
bool CaptureRailStation(const TileInfo &tile, unsigned layout, const DrawTileSprites &source, PaletteID palette);
bool CaptureVoxelAirport(const TileInfo &tile, unsigned graphics, const DrawTileSprites &source, PaletteID palette);
void BeginVoxelAirportAnimationChecks(std::span<const unsigned> graphics);
void BeginVoxelIndustryAnimationChecks(std::span<const unsigned> graphics);
void BeginVoxelIndustryPaletteCheck(unsigned graphics);
void BeginVoxelForestCycleCheck();
void BeginVoxelPowerSparkCheck();
void BeginVoxelVehicleCargoCheck(unsigned engine);
void BeginVoxelHelicopterRotorCheck(unsigned engine);
void BeginVoxelAircraftContactCheck(unsigned engine);
void BeginVoxelTrainCollectorCheck(unsigned engine);
void BeginVoxelTrainSupportCheck(unsigned engine, bool corners = false);
void BeginVoxelDepotTraversalCheck(unsigned vehicle);
void BeginVoxelRadioBeaconCheck();
bool FocusVoxelBuoy();
void BeginVoxelBuoyBeaconCheck();
void BeginVoxelHouseLiftCheck();
void BeginVoxelWaterAnimationCheck(unsigned house);
void BeginVoxelStadiumPaletteCheck(unsigned house);
void BeginVoxelHousePaletteCheck(unsigned house);
void BeginVoxelDockPaletteCheck(unsigned graphics);
bool CaptureFarmland(const TileInfo &tile, unsigned stage, SpriteID image);
bool CaptureNaturalGround(const TileInfo &tile, bool rough, unsigned variant, SpriteID image);
bool CaptureRocks(const TileInfo &tile, unsigned variant, SpriteID image, unsigned snow = 0);
bool CaptureRailSignal(TileIndex tile, SpriteID image, int x, int y, int z, unsigned type, unsigned variant, unsigned state, unsigned direction);
bool CaptureRailWire(const TileInfo &tile, SpriteID image, Track track, const std::array<int,4> &heights, unsigned support_mask, unsigned half = 0);
bool CaptureRailPylon(const TileInfo &tile, SpriteID image, int x, int y, int elevation, int contact_x, int contact_y, bool on_bridge = false);
bool CaptureDepot(const TileInfo &tile, unsigned kind, unsigned direction, const DrawTileSprites &source, int relocation, SpriteID ground, PaletteID palette, bool reserved = false);
bool CaptureShipDepot(const TileInfo &tile, unsigned axis, unsigned part, PaletteID palette);
bool CaptureVoxelDock(const TileInfo &tile, unsigned graphics, const DrawTileSprites &source, PaletteID palette);
bool CaptureCrossing(const TileInfo &tile, SpriteID ground, PaletteID palette);
bool CaptureRoadStop(const TileInfo &tile, unsigned layout, const DrawTileSprites &source, PaletteID palette);
void CaptureGround(SpriteID image, PaletteID palette, int x, int y, int z, const TileInfo &tile, const SubSprite *sub, int offset_x, int offset_y, unsigned fine_edges = UINT_MAX);
void CaptureParent(SpriteID image, PaletteID palette, int x, int y, int z, const SpriteBounds &bounds, bool transparent, const SubSprite *sub);
void CaptureChild(SpriteID image, PaletteID palette, int x, int y, bool transparent, const SubSprite *sub, bool scale, bool relative);
std::array<int, 4> CaptureTileBounds();
bool CaptureVehicleVisible(const Vehicle *vehicle);
}

/** Implemented at the upstream viewport boundary, using the original tile/vehicle draw callbacks. */
void CollectViewport3D(const Viewport &viewport);

#endif
