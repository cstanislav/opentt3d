/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "station_capture.h"
#include "sprite_textures.hpp"
#include "voxel_models.h"
#include "../station_map.h"
#include "../station_func.h"
#include "../settings_type.h"
#include "../rail.h"
#include "../elrail_func.h"
#include "../transparency.h"
#include "../viewport_func.h"
#include "../debug.h"
#include <map>

namespace Renderer3D {

unsigned VoxelDockState()
{
	return _settings_game.game_creation.landscape == LandscapeType::Toyland ? 1 : 0;
}

bool HasVoxelDock(unsigned graphics)
{
	if (graphics >= 6) return false;
	for (unsigned layout = 0; layout < 6; ++layout) {
		if (!HasVoxelAsset("docks",layout,0) || !HasVoxelAsset("docks",layout,1)) return false;
		for (const auto &piece : GetStationTileLayout(StationType::Dock,layout)->GetSequence()) {
			if (!IsBaseGraphicsSprite(piece.image.sprite&SPRITE_MASK)) return false;
		}
	}
	return true;
}

bool DrawVoxelDock(Scene &scene, Vec3 origin, unsigned graphics, PaletteID palette, bool transparent, bool invisible)
{
	if (!HasVoxelDock(graphics)) return false;
	return invisible || DrawVoxelAsset(scene,"docks",graphics,VoxelDockState(),origin,palette,transparent ? 0.38f : 1);
}

bool FocusVoxelDock(unsigned graphics)
{
	if (!HasVoxelDock(graphics)) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsDockTile(tile) || GetStationGfx(tile) != graphics) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel dock {} at {},{}",graphics,x,y);
		return true;
	}
	return false;
}

void DrawRailStation(Scene &scene, const Camera &, Vec3 origin, RailType type, unsigned layout, PaletteID palette, bool transparent)
{
	if (scene.visibility && !scene.visibility->Intersects(origin-Vec3{1,1,0},origin+Vec3{17,17,28})) return;
	using Key = std::pair<RailType,unsigned>;
	static std::map<Key,StationAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{type,layout});
	if (inserted) found->second = MakeStationAssembly(to_underlying(type),layout);
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		bool catenary = part == static_cast<unsigned>(StationMaterial::Catenary);
		if (catenary && (IsInvisibilitySet(TO_CATENARY) || !HasRailCatenaryDrawn(type))) continue;
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		bool glass = part == static_cast<unsigned>(StationMaterial::Glass);
		data.origin_opacity = {origin.x,origin.y,origin.z,transparent || (catenary && IsTransparencySet(TO_CATENARY)) ? 0.38f : glass ? 0.36f : 1};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,2};
		SpriteID material = 0;
		/* Canonical component-only charts work in both axes and with every rail
		 * system. Live company paint still comes through the upstream palette. */
		if (part == static_cast<unsigned>(StationMaterial::Platform) || part == static_cast<unsigned>(StationMaterial::Company)) material = SPR_RAIL_PLATFORM_X_REAR;
		if (part == static_cast<unsigned>(StationMaterial::Brick) || part == static_cast<unsigned>(StationMaterial::Roof)) material = SPR_RAIL_PLATFORM_BUILDING_X;
		if (material != 0) {
			const auto &texture = Textures().Get(material,part == static_cast<unsigned>(StationMaterial::Company) ? palette : PAL_NONE,0,true);
			data.uv_transform[3] = static_cast<float>(texture.page);
			data.region = texture.Region();
		}
		scene.instances.push_back({&mesh,data});
	}
}

bool FocusReferenceStation()
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (IsRailStationTile(tile) && GetCustomStationSpecIndex(tile) == 0 && GetStationGfx(tile) >= 2 && GetRailType(tile) <= RAILTYPE_MAGLEV) {
			ScrollMainWindowToTile(tile,true);
			Debug(driver,1,"OpenTT3D: focused live station at {},{}",x,y);
			return true;
		}
	}
	return false;
}

} // namespace Renderer3D
