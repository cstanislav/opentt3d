/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "tunnel_capture.h"
#include "sprite_textures.hpp"
#include "rail_capture.h"
#include "../tunnelbridge_map.h"
#include "../road.h"
#include "../rail.h"
#include "../elrail_func.h"
#include "../train.h"
#include "../roadveh.h"
#include "../viewport_func.h"
#include "../debug.h"
#include "../landscape.h"
#include <map>

namespace Renderer3D {

struct TunnelSight {
	Vec3 origin;
	float length;
	unsigned direction;
	TunnelKind kind;
};
static std::map<TileIndex,TunnelSight> sight_cache;

void BeginTunnelFrame() { sight_cache.clear(); }

bool TunnelLabelVisible(const Camera &camera, Vec3 point)
{
	if (!camera.first_person || camera.tunnel_entrance >= Map::Size()) return true;
	TileIndex entrance{camera.tunnel_entrance};
	auto found = sight_cache.find(entrance);
	if (found == sight_cache.end()) {
		TunnelKind kind;
		if (!GetVanillaTunnelKind(entrance,kind)) return true;
		TileIndex other = GetOtherTunnelEnd(entrance);
		Vec3 origin{TileX(entrance)*16.0f,TileY(entrance)*16.0f,static_cast<float>(GetTilePixelZ(entrance))};
		float length = (std::abs(static_cast<int>(TileX(other))-static_cast<int>(TileX(entrance)))+std::abs(static_cast<int>(TileY(other))-static_cast<int>(TileY(entrance))))*16.0f;
		found = sight_cache.emplace(entrance,TunnelSight{origin,length,to_underlying(GetTunnelBridgeDirection(entrance)),kind}).first;
	}
	const auto &tunnel = found->second;
	unsigned inverse = (4-tunnel.direction)%4;
	return VisibleThroughTunnelMouth(tunnel.kind,tunnel.length,TunnelPoint(inverse,camera.Eye()-tunnel.origin),TunnelPoint(inverse,point-tunnel.origin));
}

std::vector<ClipVolume> CaptureTunnelSceneryRegions(const Camera &camera)
{
	if (!camera.first_person || camera.tunnel_entrance >= Map::Size()) return {};
	TileIndex entrance{camera.tunnel_entrance};
	TunnelKind kind, other_kind;
	if (!GetVanillaTunnelKind(entrance,kind)) return {};
	TileIndex other = GetOtherTunnelEnd(entrance);
	if (!GetVanillaTunnelKind(other,other_kind) || kind != other_kind) return {};
	Vec3 origin{TileX(entrance)*16.0f,TileY(entrance)*16.0f,static_cast<float>(GetTilePixelZ(entrance))};
	float length = (std::abs(static_cast<int>(TileX(other))-static_cast<int>(TileX(entrance)))+std::abs(static_cast<int>(TileY(other))-static_cast<int>(TileY(entrance))))*16.0f;
	unsigned direction = to_underlying(GetTunnelBridgeDirection(entrance));
	return TunnelSceneryRegions(kind,length,TunnelPoint((4-direction)%4,camera.Eye()-origin),origin,direction);
}

bool GetVanillaTunnelKind(TileIndex entrance, TunnelKind &kind)
{
	if (!IsValidTile(entrance) || !IsTunnelTile(entrance)) return false;
	SpriteID portal;
	if (GetTunnelBridgeTransportType(entrance) == TRANSPORT_RAIL) {
		RailType rail = GetRailType(entrance);
		if (rail > RAILTYPE_MAGLEV || GetRailTypeInfo(rail)->UsesOverlay()) return false;
		kind = static_cast<TunnelKind>(to_underlying(rail));
		portal = GetRailTypeInfo(rail)->base_sprites.tunnel;
	} else {
		RoadType road = GetRoadTypeRoad(entrance), tram = GetRoadTypeTram(entrance);
		if ((road != INVALID_ROADTYPE && GetRoadTypeInfo(road)->UsesOverlay()) || (tram != INVALID_ROADTYPE && GetRoadTypeInfo(tram)->UsesOverlay())) return false;
		kind = tram == INVALID_ROADTYPE ? TunnelKind::Road : TunnelKind::Tram;
		portal = SPR_TUNNEL_ENTRY_REAR_ROAD;
	}
	portal += GetTunnelBridgeDirection(entrance)*2 + (HasTunnelBridgeSnowOrDesert(entrance) ? 32 : 0);
	return IsBaseGraphicsSprite(portal) && IsBaseGraphicsSprite(portal+1);
}

bool IsVehicleInTunnel(const Vehicle &vehicle)
{
	if (vehicle.tile == INVALID_TILE || !IsValidTile(vehicle.tile) || !IsTunnelTile(vehicle.tile)) return false;
	return (vehicle.type == VEH_TRAIN && Train::From(&vehicle)->track == TRACK_BIT_WORMHOLE) ||
		(vehicle.type == VEH_ROAD && RoadVehicle::From(&vehicle)->state == RVSB_WORMHOLE);
}

std::optional<float> TrainTunnelContactHeight(const Vehicle &vehicle, Vec3 point)
{
	if (vehicle.type != VEH_TRAIN) return {};
	TileIndex under = INVALID_TILE;
	if (point.x >= 0 && point.y >= 0 && point.x < Map::MaxX()*16 && point.y < Map::MaxY()*16) under = TileVirtXY(static_cast<int>(point.x),static_cast<int>(point.y));
	/* A wormhole vehicle keeps the entrance tile. At a mouth the two roof
	 * collectors can occupy different tiles, so also examine the sampled tile. */
	for (TileIndex entrance : {vehicle.tile,under}) {
		TunnelKind kind;
		if (!GetVanillaTunnelKind(entrance,kind) || kind != TunnelKind::ElectricRail) continue;
		TileIndex other = GetOtherTunnelEnd(entrance);
		float floor = GetTilePixelZ(entrance);
		if (std::abs(vehicle.z_pos-floor) > 1) continue;
		Vec3 origin{TileX(entrance)*16.0f,TileY(entrance)*16.0f,floor};
		Vec3 local = TunnelPoint((4-to_underlying(GetTunnelBridgeDirection(entrance)))%4,point-origin);
		if (local.y < 3 || local.y > 13) continue;
		float length = (std::abs(static_cast<int>(TileX(other))-static_cast<int>(TileX(entrance)))+std::abs(static_cast<int>(TileY(other))-static_cast<int>(TileY(entrance))))*16.0f;
		return floor+TunnelPairContactWireHeight(local.x,length);
	}
	return {};
}

const TunnelAssembly &TunnelGeometry(TunnelKind kind, bool portal)
{
	static std::map<std::pair<TunnelKind,bool>,TunnelAssembly> meshes;
	auto [found,inserted] = meshes.try_emplace(std::pair{kind,portal});
	if (inserted) found->second = MakeTunnelAssembly(kind,portal);
	return found->second;
}

void DrawTunnelSection(Scene &scene, const Camera &camera, Vec3 origin, unsigned direction, TunnelKind kind, bool portal, bool snow_desert, bool reserved)
{
	if (scene.visibility && !scene.visibility->Intersects(origin-Vec3{0,0,1},origin+Vec3{16,16,11})) return;
	const auto &assembly = TunnelGeometry(kind,portal);
	bool road = kind == TunnelKind::Road || kind == TunnelKind::Tram;
	for (size_t part = 0; part < assembly.parts.size(); ++part) {
		const auto &mesh = assembly.parts[part];
		if (mesh.empty()) continue;
		bool wire = part == static_cast<unsigned>(TunnelMaterial::Wire);
		if (wire && (IsInvisibilitySet(TO_CATENARY) || (kind == TunnelKind::ElectricRail && !HasRailCatenaryDrawn(RAILTYPE_ELECTRIC)))) continue;
		if (part == static_cast<unsigned>(TunnelMaterial::Detail) && camera.PixelScaleAt(origin+Vec3{8,8,4}) < 0.35f) continue;
		InstanceData data;
		data.origin_opacity = {origin.x+8,origin.y+8,origin.z,wire && IsTransparencySet(TO_CATENARY) ? 0.38f : 1};
		data.scale_center = {1,1,8,8};
		data.mirror_layer_heading[3] = (2-static_cast<int>(direction))*std::numbers::pi_v<float>/2;
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,1};
		if (part <= static_cast<unsigned>(TunnelMaterial::Floor)) {
			SpriteID image = part == static_cast<unsigned>(TunnelMaterial::Earth) ? (snow_desert ? SPR_FLAT_SNOW_DESERT_TILE : SPR_FLAT_GRASS_TILE) : (road ? SPR_ROAD_X : SPR_FLAT_BARE_LAND);
			SpriteTexture texture = Textures().Get(image,PAL_NONE,0,true);
			Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
			data.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			data.region = texture.Region();
			if (road && part == static_cast<unsigned>(TunnelMaterial::Floor)) data.identity[3] = 2;
		}
		scene.instances.push_back({&mesh,data});
	}
	if (kind <= TunnelKind::Maglev) {
		TrackBits track = direction%2 == 0 ? TRACK_BIT_X : TRACK_BIT_Y;
		DrawRailTracks(scene,camera,origin,SLOPE_FLAT,static_cast<RailType>(kind),track,reserved ? track : TRACK_BIT_NONE);
	}
}

bool FocusReferenceTunnel()
{
	if (Map::Size() == 0) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		TunnelKind kind;
		if (!GetVanillaTunnelKind(tile,kind)) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused live tunnel at {},{}",x,y);
		return true;
	}
	return false;
}

} // namespace Renderer3D
