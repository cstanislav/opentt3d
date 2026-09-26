/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "rail_detail_capture.h"
#include "../rail_map.h"
#include "../rail.h"
#include "../elrail_func.h"
#include "../viewport_func.h"
#include "../debug.h"
#include <map>

namespace Renderer3D {

static void AddRailDetail(Scene &scene, const std::vector<Vertex> &mesh, Vec3 origin, bool transparent, float heading = 0, float height_scale = 1)
{
	InstanceData data;
	data.origin_opacity = {origin.x,origin.y,origin.z,transparent ? 0.38f : 1};
	data.scale_center[1] = height_scale;
	data.mirror_layer_heading[3] = heading;
	data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,0};
	scene.instances.push_back({&mesh,data});
}

void DrawRailSignal(Scene &scene, const Camera &camera, Vec3 origin, unsigned type, unsigned variant, unsigned state, unsigned direction, float height_limit)
{
	if (scene.visibility && !scene.visibility->Intersects(origin-Vec3{3,3,0},origin+Vec3{3,3,17})) return;
	bool detail = camera.PixelScaleAt(origin) >= 0.8f;
	using Key = std::tuple<unsigned,unsigned,unsigned,bool>;
	static std::map<Key,std::vector<Vertex>> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{type,variant,state,detail});
	if (inserted) found->second = MakeSignalMesh(type,variant != 0,state != 0,detail);
	AddRailDetail(scene,found->second,origin,false,SignalHeading(direction),std::min(1.0f,std::max(2.0f,height_limit)/16));
}

void DrawCatenaryWire(Scene &scene, const Camera &camera, Vec3 origin, unsigned track, int grade, unsigned supports, unsigned half, bool transparent)
{
	if (scene.visibility && !scene.visibility->Intersects(origin+Vec3{-0.1f,-0.1f,std::min(0,grade)+9.0f},origin+Vec3{16.1f,16.1f,std::max(0,grade)+12.5f})) return;
	bool detail = camera.PixelScaleAt(origin+Vec3{8,8,10}) >= 0.7f;
	using Key = std::tuple<unsigned,int,unsigned,unsigned,bool>;
	static std::map<Key,std::vector<Vertex>> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{track,grade,supports,half,detail});
	if (inserted) found->second = MakeCatenaryWire(track,grade,supports,half,detail);
	AddRailDetail(scene,found->second,origin,transparent);
}

void DrawCatenaryPylon(Scene &scene, Vec3 origin, Vec3 contact, bool transparent)
{
	Vec3 delta = contact-origin;
	if (scene.visibility && !scene.visibility->Intersects(origin+Vec3{std::min(-0.3f,delta.x-0.2f),std::min(-0.3f,delta.y-0.2f),0},origin+Vec3{std::max(0.3f,delta.x+0.2f),std::max(0.3f,delta.y+0.2f),delta.z+2.3f})) return;
	using Key = std::tuple<int,int,int>;
	static std::map<Key,std::vector<Vertex>> meshes;
	auto [found,inserted] = meshes.try_emplace(Key{static_cast<int>(std::lround(delta.x)),static_cast<int>(std::lround(delta.y)),static_cast<int>(std::lround(delta.z))});
	if (inserted) found->second = MakeCatenaryPylon(delta);
	AddRailDetail(scene,found->second,origin,transparent);
}

bool FocusRailDetail(bool catenary)
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsTileType(tile,MP_RAILWAY) || !IsPlainRail(tile)) continue;
		if (catenary ? HasRailCatenaryDrawn(GetRailType(tile)) : HasSignals(tile)) {
			ScrollMainWindowToTile(tile,true);
			Debug(driver,1,"OpenTT3D: focused live {} at {},{}",catenary ? "catenary" : "signal",x,y);
			return true;
		}
	}
	return false;
}

} // namespace Renderer3D
