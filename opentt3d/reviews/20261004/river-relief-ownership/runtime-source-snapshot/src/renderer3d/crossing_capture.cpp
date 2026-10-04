/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "crossing_capture.h"
#include "sprite_textures.hpp"
#include "../road_map.h"
#include "../viewport_func.h"
#include "../debug.h"
#include <map>

namespace Renderer3D {
void DrawCrossing(Scene &scene, const Camera &camera, Vec3 origin, unsigned kind, unsigned axis, bool barred, bool tram, bool reserved)
{
	if (scene.visibility && !scene.visibility->Intersects(origin,origin+Vec3{16,16,6})) return;
	unsigned lod = camera.PixelScaleAt(origin+Vec3{8,8,0}) >= 1.25f ? 0 : 1;
	using Key = std::tuple<unsigned,unsigned,bool,bool,unsigned>;
	static std::map<Key,CrossingAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{kind,axis,barred,tram,lod});
	if (inserted) found->second = MakeCrossingAssembly(kind,axis != 0,barred,tram,lod);
	for (size_t part = 0; part < found->second.parts.size(); ++part) {
		CrossingMaterial material = static_cast<CrossingMaterial>(part);
		if (material == (reserved ? CrossingMaterial::Track : CrossingMaterial::ReservedTrack)) continue;
		const auto &mesh = found->second.parts[part];
		if (mesh.empty()) continue;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,1};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,2};
		if ((static_cast<unsigned>(mesh.front().surface)&15U) == static_cast<unsigned>(SurfaceMode::Palette)) {
			UsePaletteMaterial(data);
		} else if (material == CrossingMaterial::Road) {
			const auto &texture = Textures().Get(SPR_ROAD_X,PAL_NONE,0,true);
			data.uv_transform[3] = static_cast<float>(texture.page);
			data.region = texture.Region();
		} else if (material == CrossingMaterial::TrackBed) {
			const auto &texture = Textures().Get(SPR_FLAT_BARE_LAND,PAL_NONE,0,true);
			Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
			data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			data.region = texture.Region();
		}
		scene.instances.push_back({&mesh,data});
	}
}

bool FocusCrossing()
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		if (!IsLevelCrossingTile(TileXY(x,y))) continue;
		ScrollMainWindowToTile(TileXY(x,y),true);
		Debug(driver,1,"OpenTT3D: focused live crossing at {},{}",x,y);
		return true;
	}
	return false;
}
} // namespace Renderer3D
