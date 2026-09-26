/* SPDX-License-Identifier: GPL-2.0-only */
/** @file rail_capture.cpp Presentation of upstream rail layouts and foundations. */
#include "../stdafx.h"
#include "rail_capture.h"
#include "world_capture.h"
#include "sprite_textures.hpp"
#include "../rail.h"
#include "../rail_map.h"
#include "../landscape.h"
#include "../water.h"
#include "../pbs.h"
#include "../settings_type.h"
#include "../viewport_func.h"
#include "../openttd.h"
#include <map>

namespace Renderer3D {

const RailAssembly &RailGeometry(RailType type, Track track, Slope slope, unsigned lod, TrackBits layout)
{
	/* Only guide-wall clearance depends on adjoining routes. Reuse the same
	 * immutable conventional/monorail sections across all junction layouts. */
	if (type != RAILTYPE_MAGLEV) layout = TRACK_BIT_NONE;
	/* Electrification is drawn separately; its running track is identical. */
	if (type == RAILTYPE_ELECTRIC) type = RAILTYPE_RAIL;
	using Key = std::tuple<RailType,Track,Slope,unsigned,TrackBits>;
	static std::map<Key,RailAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{type,track,slope,lod,layout});
	if (inserted) {
		found->second = MakeRailAssembly(to_underlying(type),to_underlying(track),MakeTileSurface(slope),lod,to_underlying(layout));
		for (const auto &mesh : found->second.parts) RegisterPackedVoxelMesh(mesh,true);
	}
	return found->second;
}

void DrawRailTracks(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, RailType type, TrackBits tracks, TrackBits reserved)
{
	if (scene.visibility && !scene.visibility->Intersects(origin,origin+Vec3{16,16,GetSlopeMaxPixelZ(slope)+1.0f})) return;
	float scale = camera.PixelScaleAt(origin+Vec3{8,8,0});
	unsigned lod = scale >= 1.25f ? 0 : scale >= 0.35f ? 1 : 2;
	for (Track track = TRACK_BEGIN; track < TRACK_END; ++track) {
		if ((tracks & TrackToTrackBits(track)) == TRACK_BIT_NONE) continue;
		const auto &geometry = RailGeometry(type,track,slope,lod,tracks);
		bool is_reserved = (reserved & TrackToTrackBits(track)) != TRACK_BIT_NONE;
		for (size_t part = 0; part < geometry.parts.size(); ++part) {
			if (part == static_cast<unsigned>(is_reserved ? RailMaterial::Rails : RailMaterial::ReservedRails)) continue;
			const auto &mesh = geometry.parts[part];
			if (mesh.empty()) continue;
			InstanceData data;
			data.origin_opacity = {origin.x,origin.y,origin.z,1};
			UsePaletteMaterial(data);
			scene.instances.push_back({&mesh,data});
		}
	}
}

/** Resolve provenance before replacing any source drawing. Partial Action-A
 * replacements and custom rail types retain the upstream reference path. */
static bool SupportedRailType(RailType type)
{
	if (type > RAILTYPE_MAGLEV) return false;
	const auto *rti = GetRailTypeInfo(type);
	if (rti->UsesOverlay()) return false;
	static uint64_t generation = UINT64_MAX;
	static std::array<int,4> supported{};
	if (generation != TextureGeneration()) { generation = TextureGeneration(); supported.fill(0); }
	int &value = supported[to_underlying(type)];
	if (value != 0) return value > 0;
	bool base = IsBaseGraphicsSprite(SPR_FLAT_GRASS_TILE) && IsBaseGraphicsSprite(SPR_FLAT_BARE_LAND) && IsBaseGraphicsSprite(SPR_FLAT_SNOW_DESERT_TILE);
	for (unsigned i = 0; i < 26; ++i) base &= IsBaseGraphicsSprite(rti->base_sprites.track_y+i);
	for (unsigned i = 0; i < 8; ++i) base &= IsBaseGraphicsSprite(rti->base_sprites.track_y+rti->snow_offset+i);
	for (SpriteID image : {rti->base_sprites.single_x,rti->base_sprites.single_y,rti->base_sprites.single_n,
		rti->base_sprites.single_s,rti->base_sprites.single_e,rti->base_sprites.single_w}) base &= IsBaseGraphicsSprite(image);
	value = base ? 1 : -1;
	return base;
}

bool CaptureRailTile(TileInfo &tile, TrackBits tracks)
{
	if (!IsCapturing()) return false;
	RailType type = GetRailType(tile.tile);
	if (!SupportedRailType(type)) return false;
	RailGroundType ground = GetRailGroundType(tile.tile);
	Foundation foundation = GetRailFoundation(tile.tileh,tracks);
	Corner upper = CORNER_INVALID;
	if (IsNonContinuousFoundation(foundation)) {
		upper = foundation == FOUNDATION_STEEP_BOTH ? GetHighestSlopeCorner(tile.tileh) : GetHalftileFoundationCorner(foundation);
		tracks &= ~CornerToTrackBits(upper);
		foundation = foundation == FOUNDATION_STEEP_BOTH ? FOUNDATION_STEEP_LOWER : FOUNDATION_NONE;
	}
	/* Apply exactly the same local TileInfo transformations as DrawTrackBits.
	 * No map field, reservation, vehicle or simulation state is modified. */
	DrawFoundation(&tile,foundation);
	auto draw_surface = [&](bool raised) {
		if (ground == RailGroundType::HalfTileWater && !raised) {
			if (tile.tileh == SLOPE_FLAT) DrawGroundSprite(SPR_FLAT_WATER_TILE,PAL_NONE);
			else DrawShoreTile(tile.tileh);
			return;
		}
		SpriteID image = ground == RailGroundType::Barren ? SPR_FLAT_BARE_LAND :
			ground == RailGroundType::SnowOrDesert || (raised && ground == RailGroundType::HalfTileSnow) ? SPR_FLAT_SNOW_DESERT_TILE : SPR_FLAT_GRASS_TILE;
		Slope chart = IsHalftileSlope(tile.tileh) ? SlopeWithThreeCornersRaised(OppositeCorner(GetHalftileSlopeCorner(tile.tileh))) : tile.tileh;
		DrawGroundSprite(image+SlopeToSpriteOffset(chart),PAL_NONE);
	};
	TrackBits reserved = _game_mode != GM_MENU && _settings_client.gui.show_track_reservation ? GetRailReservationTrackBits(tile.tile) : TRACK_BIT_NONE;
	draw_surface(false);
	CaptureRailTracks(tile,type,tracks,reserved);
	if (IsValidCorner(upper)) {
		DrawFoundation(&tile,HalftileFoundation(upper));
		draw_surface(true);
		CaptureRailTracks(tile,type,CornerToTrackBits(upper),reserved);
	}
	return true;
}

} // namespace Renderer3D
