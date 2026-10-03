/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "road_stop_capture.h"
#include "sprite_textures.hpp"
#include "../road_cmd.h"
#include "../station_map.h"
#include "../station_func.h"
#include "../viewport_func.h"
#include "../debug.h"
#include <map>

namespace Renderer3D {
void DrawRoadStop(Scene &scene, const Camera &camera, Vec3 origin, bool truck, unsigned layout, bool tram, PaletteID palette, bool transparent, bool invisible, float height_limit)
{
	if (scene.visibility && !scene.visibility->Intersects(origin,origin+Vec3{16,16,12})) return;
	bool detail = camera.PixelScaleAt(origin+Vec3{8,8,4}) >= 1.25f;
	using Key = std::tuple<bool,unsigned,bool,bool>;
	static std::map<Key,RoadStopAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{truck,layout,tram,detail});
	if (inserted) found->second = MakeRoadStopAssembly(truck,layout,tram,detail);
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		RoadStopMaterial material = static_cast<RoadStopMaterial>(part);
		bool ground = material == RoadStopMaterial::Road || material == RoadStopMaterial::Paving || material == RoadStopMaterial::Tram || material == RoadStopMaterial::Markings;
		if (invisible && !ground) continue;
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,transparent && !ground ? 0.38f : 1};
		if (!ground) data.scale_center[1] = std::clamp(height_limit/12,0.1f,1.0f);
		bool substrate = material == RoadStopMaterial::Road || material == RoadStopMaterial::Paving;
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | (substrate ? 0 : SURFACE_SHADED)),1,2};
		const auto &source = *GetStationTileLayout(truck ? StationType::Truck : StationType::Bus,layout);
		SpriteID image = substrate ? source.ground.sprite & SPRITE_MASK :
			material == RoadStopMaterial::Company ? SPR_BUS_STOP_DT_X_W : material == RoadStopMaterial::Masonry ? SPR_TRUCK_STOP_DT_X_W : 0;
		if (image != 0) {
			PaletteID material_palette = substrate ? GroundSpritePaletteTransform(source.ground.sprite,source.ground.pal,palette) : material == RoadStopMaterial::Company ? palette : PAL_NONE;
			const auto &texture = Textures().Get(image,material_palette,0,true);
			data.uv_transform[3] = static_cast<float>(texture.page);
			data.region = texture.Region();
			if (substrate) {
				Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
				data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			}
		}
		scene.instances.push_back({&mesh,data});
	}
}

bool FocusRoadStop()
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		if (!IsStationRoadStopTile(TileXY(x,y))) continue;
		ScrollMainWindowToTile(TileXY(x,y),true);
		Debug(driver,1,"OpenTT3D: focused live road stop at {},{}",x,y);
		return true;
	}
	return false;
}
} // namespace Renderer3D
