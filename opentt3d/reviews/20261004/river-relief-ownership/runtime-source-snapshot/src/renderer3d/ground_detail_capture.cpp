/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "ground_detail_capture.h"
#include "world_capture.h"
#include "sprite_textures.hpp"
#include "../clear_map.h"
#include "../viewport_func.h"
#include "../debug.h"
#include "../table/clear_land.h"
#include "../settings_type.h"
#include "../landscape.h"
#include <map>

namespace Renderer3D {

bool FocusGroundDetail(unsigned kind, unsigned variant)
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsTileType(tile,MP_CLEAR)) continue;
		if (kind == 4) {
			auto [slope,height] = GetTileSlopeZ(tile);
			unsigned layout = slope == SLOPE_FLAT ? GB(TileHash(x*TILE_SIZE,y*TILE_SIZE),0,3) : 0;
			if ((layout >= 5 ? layout-5 : layout) != variant) continue;
		}
		if (kind >= 3 ? !IsSnowTile(tile) && IsClearGround(tile,kind == 3 ? CLEAR_GRASS : CLEAR_ROUGH) && (kind != 3 || GetClearDensity(tile) == variant) : kind == 0 ? IsClearGround(tile,CLEAR_FIELDS) && !IsSnowTile(tile) && GetFieldType(tile) == variant :
			IsClearGround(tile,CLEAR_ROCKS) && (kind == 1 ? !IsSnowTile(tile) : IsSnowTile(tile) && GetClearDensity(tile) == variant)) {
			ScrollMainWindowToTile(tile,true);
			Debug(driver,1,"OpenTT3D: focused live ground detail {} variant {} at {},{}",kind,variant,x,y);
			return true;
		}
	}
	return false;
}

void DrawGroundDetails(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, bool rocks, unsigned variant, unsigned snow)
{
	if (scene.visibility && !scene.visibility->Intersects(origin-Vec3{0.1f,0.1f,0.1f},origin+Vec3{16.1f,16.1f,TerrainZ(GetSlopeMaxPixelZ(slope))+8})) return;
	float scale = camera.PixelScaleAt(origin+Vec3{8,8,2});
	unsigned lod = rocks || scale >= 5 ? 0 : scale >= 0.6f ? 1 : 2;
	using Key = std::tuple<bool,unsigned,Slope,unsigned,unsigned>;
	static std::map<Key,GroundDetailAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{rocks,variant,slope,snow,lod});
	if (inserted) found->second = rocks ? MakeRockAssembly(variant,snow,MakeTileSurface(slope)) : MakeFieldAssembly(variant,MakeTileSurface(slope),lod);
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,1};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,2};
		SpriteID image = part == static_cast<unsigned>(GroundDetailMaterial::Soil) ? SPR_FLAT_BARE_LAND :
			part == static_cast<unsigned>(GroundDetailMaterial::Crop) && variant >= 3 && variant <= 6 ? _clear_land_sprites_farmland[variant] :
			part == static_cast<unsigned>(GroundDetailMaterial::Hay) ? SPR_FARMLAND_HAYPACKS :
			part == static_cast<unsigned>(GroundDetailMaterial::Rock) ? (variant == 0 ? SPR_FLAT_ROCKY_LAND_1 : SPR_FLAT_ROCKY_LAND_2) : 0;
		if (image != 0) {
			const auto &texture = Textures().Get(image,PAL_NONE,0,true);
			Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
			data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			data.region = texture.Region();
		}
		scene.instances.push_back({&mesh,data});
	}
}

void DrawClearSurface(Scene &scene, const Camera &camera, Vec3 origin, Slope slope, bool rough, unsigned variant, unsigned fine_edges)
{
	if (scene.visibility && !scene.visibility->Intersects(origin,origin+Vec3{16,16,TerrainZ(GetSlopeMaxPixelZ(slope))+2})) return;
	unsigned climate = to_underlying(_settings_game.game_creation.landscape);
	float scale = camera.PixelScaleAt(origin+Vec3{8,8,1});
	unsigned lod = scale >= 5 ? 0 : scale >= 1.8f ? 1 : 2;
	using Key = std::tuple<bool,unsigned,unsigned,Slope,unsigned,unsigned>;
	static std::map<Key,ClearSurfaceAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{rough,variant,climate,slope,lod,fine_edges});
	if (inserted) found->second = MakeClearSurfaceAssembly(rough,variant,climate,MakeTileSurface(slope),lod,fine_edges);
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,1};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,0};
		SpriteID image = climate == 3 ? 0 : part == static_cast<unsigned>(ClearSurfaceMaterial::Ground) ? SPR_FLAT_BARE_LAND :
			part == static_cast<unsigned>(ClearSurfaceMaterial::Grass) ? SPR_FLAT_GRASS_TILE : SPR_FLAT_ROCKY_LAND_2;
		if (image != 0) {
			const auto &texture = Textures().Get(image,PAL_NONE,0,true);
			if (part == static_cast<unsigned>(ClearSurfaceMaterial::Ground)) {
				Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
				data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
				data.region = texture.Region();
				data.identity[3] = 1;
			} else {
				TextureRegion crop = part == static_cast<unsigned>(ClearSurfaceMaterial::Grass) ? TextureRegion{0.54f,0.44f,0.56f,0.46f} : TextureRegion{136/256.0f,52/124.0f,143/256.0f,55/124.0f};
				int left = static_cast<int>(std::floor(crop.left*texture.width)), top = static_cast<int>(std::floor(crop.top*texture.height));
				int right = static_cast<int>(std::ceil(crop.right*texture.width)), bottom = static_cast<int>(std::ceil(crop.bottom*texture.height));
				data.region = {(texture.x+left)/static_cast<float>(ATLAS_SIZE),(texture.y+top)/static_cast<float>(ATLAS_SIZE),
					(texture.x+right)/static_cast<float>(ATLAS_SIZE),(texture.y+bottom)/static_cast<float>(ATLAS_SIZE)};
				data.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::RepeatingChart) | SURFACE_SHADED);
				SetWorldTexelChart(data,texture,crop);
			}
		}
		scene.instances.push_back({&mesh,data});
	}
}

} // namespace Renderer3D
