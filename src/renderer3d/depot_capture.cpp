/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "depot_capture.h"
#include "sprite_textures.hpp"
#include "voxel_models.h"
#include "../rail.h"
#include "../elrail_func.h"
#include "../rail_map.h"
#include "../road_map.h"
#include "../road_cmd.h"
#include "../transparency.h"
#include "../viewport_func.h"
#include "../debug.h"
#include "../settings_type.h"
#include "../table/track_land.h"
#include "../water_map.h"
#include "../table/water_land.h"
#include <map>

namespace Renderer3D {

bool HasVoxelShipDepot(unsigned axis, unsigned part)
{
	if (axis >= 2 || part >= 2) return false;
	/* The six structural sprites are identical across original climates. Water
	 * is deliberately separate: upstream retains its water-class/custom selection. */
	for (unsigned a = 0; a < 2; ++a) for (unsigned p = 0; p < 2; ++p) {
		if (!HasVoxelAsset("ship_depots",a,p)) return false;
		for (const auto &piece : _shipdepot_display_data[a][p].GetSequence()) {
			if (!IsBaseGraphicsSprite(piece.image.sprite&SPRITE_MASK)) return false;
		}
	}
	return true;
}

bool DrawVoxelShipDepot(Scene &scene, Vec3 origin, unsigned axis, unsigned part, PaletteID palette, bool transparent, bool invisible)
{
	if (!HasVoxelShipDepot(axis,part)) return false;
	return invisible || DrawVoxelAsset(scene,"ship_depots",axis,part,origin,palette,transparent ? 0.38f : 1);
}

bool FocusShipDepot(unsigned axis)
{
	if (axis >= 2) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsShipDepotTile(tile) || GetShipDepotAxis(tile) != axis || GetShipDepotPart(tile) != DepotPart::North || !HasVoxelShipDepot(axis,0)) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel ship depot axis {} at {},{}",axis,x,y);
		return true;
	}
	return false;
}

unsigned VoxelDepotState(unsigned direction)
{
	return direction+(_settings_game.game_creation.landscape == LandscapeType::Toyland ? 4 : 0);
}

bool HasVoxelDepot(unsigned kind, unsigned direction)
{
	if (kind > 4 || direction >= 4 || !HasVoxelAsset("depots",kind,VoxelDepotState(direction)) || !HasVoxelAsset("depot_floors",kind,0)) return false;
	if (kind < 4) for (unsigned state = 1; state < 4; ++state) if (!HasVoxelAsset("depot_floors",kind,state)) return false;
	if (kind == 1 && !HasVoxelAsset("depot_wires",kind,direction)) return false;
	for (unsigned view = 0; view < 4; ++view) {
		const auto &source = kind < 4 ? _depot_gfx_table[view] : GetRoadDepotDrawData(static_cast<DiagDirection>(view));
		unsigned offset = kind < 4 ? GetRailTypeInfo(static_cast<RailType>(kind))->GetRailtypeSpriteOffset() : 0;
		SpriteID ground = source.ground.sprite&SPRITE_MASK;
		if (kind < 4 && ground != SPR_FLAT_GRASS_TILE) ground += offset;
		if (!IsBaseGraphicsSprite(ground)) return false;
		for (const auto &piece : source.GetSequence()) if (!IsBaseGraphicsSprite((piece.image.sprite&SPRITE_MASK)+offset)) return false;
	}
	return true;
}

void DrawDepot(Scene &scene, const Camera &camera, Vec3 origin, unsigned kind, unsigned direction, PaletteID palette, bool transparent, bool invisible, bool reserved, bool original_family, unsigned floor_state)
{
	bool voxel = original_family && HasVoxelDepot(kind,direction);
	if (voxel) {
		if (floor_state == UINT_MAX) floor_state = kind < 4 && _settings_game.game_creation.landscape == LandscapeType::Toyland ? 3 : 0;
		if (!DrawVoxelAsset(scene,"depot_floors",kind,floor_state,origin,PAL_NONE,1)) throw std::runtime_error("Missing voxel depot ground state");
		if (!invisible) DrawVoxelAsset(scene,"depots",kind,VoxelDepotState(direction),origin,palette,transparent ? 0.38f : 1);
		if (kind == 1 && !IsInvisibilitySet(TO_CATENARY) && HasRailCatenaryDrawn(RAILTYPE_ELECTRIC)) {
			DrawVoxelAsset(scene,"depot_wires",kind,direction,origin,PAL_NONE,IsTransparencySet(TO_CATENARY) ? 0.38f : 1);
		}
		if (kind == 4) return;
	}
	if (scene.visibility && !scene.visibility->Intersects(origin,origin+Vec3{16,16,24})) return;
	unsigned lod = camera.PixelScaleAt(origin+Vec3{8,8,8}) >= 1 ? 0 : 1;
	using Key = std::tuple<unsigned,unsigned,unsigned>;
	static std::map<Key,DepotAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{kind,direction,lod});
	if (inserted) found->second = MakeDepotAssembly(kind,direction,lod);
	SpriteID source = kind < 4 ? SPR_RAIL_DEPOT_NE+GetRailTypeInfo(static_cast<RailType>(kind))->GetRailtypeSpriteOffset() :
		kind == 4 ? SPR_ROAD_DEPOT+4 : SPR_TRAMWAY_DEPOT_NO_TRACK+4;
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		DepotMaterial material = static_cast<DepotMaterial>(part);
		bool track = material == DepotMaterial::TrackBed || material == DepotMaterial::Track || material == DepotMaterial::ReservedTrack || material == DepotMaterial::TrackSupport;
		bool wire = material == DepotMaterial::Wire;
		/* The voxel body/floor/wire replace these parts. Existing running-rail
		 * assemblies remain the shared voxel path, including reservations. */
		if (voxel && !track) continue;
		if ((invisible && !track && material != DepotMaterial::Floor && !wire) || material == (reserved ? DepotMaterial::Track : DepotMaterial::ReservedTrack)) continue;
		if (wire && (IsInvisibilitySet(TO_CATENARY) || (kind == 1 && !HasRailCatenaryDrawn(RAILTYPE_ELECTRIC)))) continue;
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,(!track && material != DepotMaterial::Floor && transparent) || (wire && IsTransparencySet(TO_CATENARY)) ? 0.38f : 1};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,2};
		if ((static_cast<unsigned>(mesh.front().surface)&15U) == static_cast<unsigned>(SurfaceMode::Palette)) {
			UsePaletteMaterial(data);
		} else if (material == DepotMaterial::Masonry || material == DepotMaterial::Roof || material == DepotMaterial::Company) {
			const auto &texture = Textures().Get(material == DepotMaterial::Company ? SPR_RAIL_PLATFORM_X_REAR : source,material == DepotMaterial::Company ? palette : PAL_NONE,0,true);
			data.uv_transform[3] = static_cast<float>(texture.page);
			data.region = texture.Region();
		} else if (material == DepotMaterial::TrackBed) {
			const auto &texture = Textures().Get(SPR_FLAT_BARE_LAND,PAL_NONE,0,true);
			Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
			data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			data.region = texture.Region();
		}
		scene.instances.push_back({&mesh,data});
	}
}

bool FocusDepot(unsigned voxel_kind, unsigned voxel_direction)
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (IsRailDepotTile(tile) || IsRoadDepotTile(tile)) {
			unsigned kind = IsRailDepotTile(tile) ? static_cast<unsigned>(GetRailType(tile)) : GetRoadTypeRoad(tile) == INVALID_ROADTYPE ? 5 : 4;
			unsigned direction = IsRailDepotTile(tile) ? static_cast<unsigned>(GetRailDepotDirection(tile)) : static_cast<unsigned>(GetRoadDepotDirection(tile));
			if (voxel_kind != UINT_MAX && (kind != voxel_kind || !HasVoxelDepot(kind,direction))) continue;
			if (voxel_direction != UINT_MAX && direction != voxel_direction) continue;
			ScrollMainWindowToTile(tile,true);
			Debug(driver,1,"OpenTT3D: focused live depot at {},{}",x,y);
			if (voxel_kind != UINT_MAX) Debug(driver,1,"OpenTT3D: focused voxel depot {} direction {} at {},{}",kind,direction,x,y);
			return true;
		}
	}
	return false;
}
} // namespace Renderer3D
