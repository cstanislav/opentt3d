/* SPDX-License-Identifier: GPL-2.0-only */
/** @file world_capture.cpp Value-only, palette-textured render commands. */

#include "../stdafx.h"
#include "world_capture.h"
#include "sprite_textures.hpp"
#include "authored_geometry.h"
#include "voxel_models.h"
#include "profiling.h"
#include "camera_motion.hpp"
#include "bridge_capture.h"
#include "terrain_geometry.hpp"
#include "tunnel_capture.h"
#include "rail_capture.h"
#include "station_capture.h"
#include "ground_detail_capture.h"
#include "rail_detail_capture.h"
#include "depot_capture.h"
#include "crossing_capture.h"
#include "road_stop_capture.h"
#include "../road.h"
#include "../road_cmd.h"
#include "../road_map.h"
#include "../water_map.h"
#include "../station_map.h"
#include "../station_func.h"
#include "../station_base.h"
#include "../airport.h"
#include "../newgrf_canal.h"
#include "../clear_map.h"
#include "../rail_map.h"
#include "../viewport_func.h"
#include "../rail.h"
#include <map>
#include <set>
#include <bitset>
#include "../tunnelbridge_map.h"
#include "../landscape.h"
#include "../tile_map.h"
#include "../tile_cmd.h"
#include "../vehicle_base.h"
#include "../engine_base.h"
#include "../train.h"
#include "../aircraft.h"
#include "../effectvehicle_base.h"
#include "../house.h"
#include "../industry_map.h"
#include "../tree_map.h"
#include "../town_map.h"
#include "../town.h"
#include "../palette_func.h"
#include "../debug.h"
#include "../settings_type.h"
#include "../openttd.h"
#include "../table/clear_land.h"
#include "../table/industry_land.h"
#include <numbers>

namespace Renderer3D {

static_assert(2*MAX_MAP_SIZE_BITS <= 24, "Tile picking payload must exactly represent every upstream map index");

struct CaptureState {
	Camera camera;
	std::map<TileIndex,std::vector<ContactWireSegment>> contact_wires;
	std::map<TileIndex,std::vector<RailSupportSurface>> rail_surfaces;
	Vec3 depth_direction;
	float distance = 0, focal_scale = 0, near_plane = 0;
	Scene scene;
	const TileInfo *tile = nullptr;
	const Vehicle *vehicle = nullptr;
	Vec3 parent_origin{};
	SpriteID parent_sprite = 0;
	SpriteBounds parent_bounds{};
	int parent_left = 0, parent_top = 0;
	bool parent_offsets_pending = false;
	PaletteID parent_palette = PAL_NONE;
	unsigned tile_layers = 0;
	bool have_parent = false;
	unsigned reference_billboards = 0;
	unsigned modelled_vehicles = 0;
	unsigned bridge_parts = 0;
	unsigned fence_parts = 0;
	unsigned foundation_parts = 0;
	size_t foundation_vertices = 0;
	size_t fence_vertices = 0, rail_vertices = 0;
	unsigned tunnel_sections = 0;
	unsigned rail_sections = 0;
	unsigned station_sections = 0;
	unsigned voxel_airport_sections = 0;
	unsigned voxel_dock_sections = 0;
	unsigned ground_detail_sections = 0;
	unsigned signal_parts = 0, catenary_parts = 0;
	unsigned depot_sections = 0;
	unsigned crossing_sections = 0;
	unsigned road_stop_sections = 0;
	unsigned crossing_states = 0;
	std::array<std::pair<uint32_t,bool>,64> crossing_observations{};
	unsigned crossing_observation_count = 0;
	std::set<TileIndex> captured_tunnel_ends;
	struct TunnelCut { TunnelKind kind; unsigned direction; int floor; };
	std::map<TileIndex,TunnelCut> tunnel_cuts;
	bool diagnostic = false;
	size_t parent_mesh_begin = 0, parent_mesh_end = 0;
	size_t parent_instance_begin = 0, parent_instance_end = 0;
	bool parent_culled = false;
	uint32_t parent_id = 0;
	std::map<TileIndex,unsigned> plastic_fountain_grounds;
	unsigned industry_next_child = 0;
	bool industry_children_visible = true;
};
static std::optional<CaptureState> capture;
static std::vector<Vertex> recycled_vertices;
static std::vector<MeshInstance> recycled_instances;
struct AirportAnimationCheck {
	uint32_t tile = UINT32_MAX;
	unsigned frames = 0, seen = 0;
	bool complete = false;
};
static std::map<unsigned,AirportAnimationCheck> airport_animation_checks;
struct IndustryAnimationCheck {
	uint32_t tile = UINT32_MAX;
	unsigned expected = 0, seen = 0;
	bool complete = false;
};
static std::map<unsigned,IndustryAnimationCheck> industry_animation_checks;
static bool check_plastic_fountain = false;
static TileIndex checked_plastic_tile = INVALID_TILE;
static uint32_t checked_plastic_industry = UINT32_MAX;
static unsigned checked_plastic_frames = 0;
static bool check_forest_cycle = false;
static unsigned checked_forest_base = 16;
static std::map<TileIndex,std::pair<IndustryID,unsigned>> forest_cycles;
static bool check_power_sparks = false;
static TileIndex checked_spark_tile = INVALID_TILE;
static unsigned checked_spark_frames = 0;
static bool check_toy_factory = false;
static TileIndex checked_toy_factory_tile = INVALID_TILE;
static uint32_t checked_toy_factory_industry = UINT32_MAX;
static uint64_t checked_toy_factory_frames = 0;
static bool check_bubble_generator = false;
static TileIndex checked_bubble_tile = INVALID_TILE;
static uint32_t checked_bubble_industry = UINT32_MAX;
static uint64_t checked_bubble_frames = 0;
static bool check_toffee_quarry = false;
static TileIndex checked_toffee_tile = INVALID_TILE;
static uint32_t checked_toffee_industry = UINT32_MAX;
static std::bitset<std::size(_industry_anim_offs_toffee)> checked_toffee_frames;
static bool check_sugar_mine = false;
static TileIndex checked_sugar_tile = INVALID_TILE;
static uint32_t checked_sugar_industry = UINT32_MAX;
static std::bitset<std::size(_draw_industry_spec1)> checked_sugar_frames;
static unsigned checked_cargo_engine = UINT_MAX;
static uint32_t checked_cargo_vehicle = UINT32_MAX;
static unsigned checked_cargo_capacity = 0, checked_cargo_states = 0;
static uint32_t checked_depot_vehicle = UINT32_MAX;
static TileIndex checked_depot_tile = INVALID_TILE;
static unsigned checked_depot_phase = 0;
static bool check_radio_beacons = false;
static TileIndex checked_radio_tile = INVALID_TILE;
static std::set<std::array<uint32_t,2>> radio_beacon_colours;
static bool check_buoy_beacon = false;
static TileIndex checked_buoy_tile = INVALID_TILE;
static std::set<std::array<uint32_t,2>> buoy_beacon_colours;
static std::set<std::array<uint32_t,5>> buoy_foam_colours;
struct VehiclePose {
	Vec3 position;
	float heading = 0;
	uint64_t frame = 0;
	EngineID engine;
};
static std::unordered_map<uint32_t, VehiclePose> vehicle_poses;
static uint64_t capture_frame = 0;
static float frame_seconds = 1.0f / 60;
static void CaptureOcean();
static bool CaptureTunnelPair(TileIndex entrance);

void BeginCaptureFrame(float seconds)
{
	BeginTunnelFrame();
	++capture_frame;
	frame_seconds = seconds;
	std::erase_if(vehicle_poses, [](const auto &entry) { return entry.second.frame + 120 < capture_frame; });
	if (checked_depot_vehicle != UINT32_MAX && checked_depot_phase == 1) {
		const Vehicle *vehicle = Vehicle::GetIfValid(VehicleID{checked_depot_vehicle});
		bool supported = vehicle != nullptr && vehicle->IsInDepot() &&
			((vehicle->type == VEH_ROAD && IsRoadDepotTile(vehicle->tile) && HasVoxelDepot(GetRoadTypeRoad(vehicle->tile) == INVALID_ROADTYPE ? 5 : 4,GetRoadDepotDirection(vehicle->tile))) ||
			 (vehicle->type == VEH_SHIP && IsShipDepotTile(vehicle->tile) && HasVoxelShipDepot(GetShipDepotAxis(vehicle->tile),to_underlying(GetShipDepotPart(vehicle->tile)))));
		if (supported) {
			checked_depot_tile = vehicle->tile;
			checked_depot_phase = 2;
			Debug(driver,1,"OpenTT3D: depot traversal vehicle {} entered original hidden/depot state at {},{}",checked_depot_vehicle,TileX(checked_depot_tile),TileY(checked_depot_tile));
		}
	}
}

float RenderVehicleZ(const Vehicle &vehicle)
{
	/* Aircraft preserve their altitude above the local landscape, including
	 * elevated heliports/oil-rig decks. Only the terrain datum is exaggerated. */
	if (vehicle.type == VEH_AIRCRAFT || vehicle.type == VEH_EFFECT) {
		int x = std::clamp(vehicle.x_pos,0,static_cast<int>(Map::MaxX()*TILE_SIZE-1));
		int y = std::clamp(vehicle.y_pos,0,static_cast<int>(Map::MaxY()*TILE_SIZE-1));
		float ground = GetSlopePixelZ(x,y);
		return vehicle.z_pos+TerrainZ(ground)-ground;
	}
	return TerrainZ(vehicle.z_pos);
}

static VehiclePose SmoothVehiclePose(const Vehicle &vehicle)
{
	Vec3 target{static_cast<float>(vehicle.x_pos), static_cast<float>(vehicle.y_pos), RenderVehicleZ(vehicle)};
	float heading = to_underlying(vehicle.direction) * 0.5f;
	auto [found, inserted] = vehicle_poses.try_emplace(vehicle.index.base(), VehiclePose{target, heading, capture_frame, vehicle.engine_type});
	auto &pose = found->second;
	if (!inserted && pose.frame != capture_frame) {
		Vec3 delta = target - pose.position;
		if (pose.frame + 1 < capture_frame || pose.engine != vehicle.engine_type || Dot(delta, delta) > 256 * 256) {
			pose = {target, heading, capture_frame, vehicle.engine_type};
		} else {
			pose.position = {SmoothValue(pose.position.x, target.x, 24, frame_seconds), SmoothValue(pose.position.y, target.y, 24, frame_seconds), SmoothValue(pose.position.z, target.z, 24, frame_seconds)};
			pose.heading = SmoothHeading(pose.heading, heading, 12, frame_seconds);
			pose.frame = capture_frame;
		}
	}
	return pose;
}

/** Child overlays belong to the same pickable object as their parent geometry. */
struct ObjectTag {
	size_t begin;
	uint32_t id;
	size_t instance_begin = capture->scene.instances.size();
	~ObjectTag()
	{
		for (size_t i = begin; i < capture->scene.vertices.size(); ++i) capture->scene.vertices[i].object_id = id;
		for (size_t i = instance_begin; i < capture->scene.instances.size(); ++i) capture->scene.instances[i].data.SetObjectId(id);
	}
};

bool IsCapturing() { return capture.has_value(); }

void BeginCapture(const Camera &camera, bool diagnostic, std::optional<bool> tunnel_scenery_cull)
{
	assert(!capture.has_value());
	capture.emplace();
	capture->diagnostic = diagnostic;
	capture->camera = camera;
	capture->depth_direction = camera.Unrotate(Camera::Physical(camera.Back()));
	capture->distance = camera.Distance()+Dot(camera.focus_offset,capture->depth_direction);
	capture->focal_scale = camera.FocalPixels() / Camera::ART_SCALE;
	capture->near_plane = camera.Near();
	capture->scene.vertices.swap(recycled_vertices);
	capture->scene.instances.swap(recycled_instances);
	capture->scene.visibility = camera.Frustum(16);
	capture->scene.detail = Scene::DetailView{camera.focus,capture->depth_direction,capture->distance,camera.FocalPixels(),camera.Near()};
	static const bool experimental_tunnel_scenery_cull = [] { const char *value = std::getenv("OPENTT3D_TUNNEL_SCENERY_CULL"); return value != nullptr && std::string_view(value) == "1"; }();
	if (tunnel_scenery_cull.value_or(experimental_tunnel_scenery_cull)) capture->scene.scenery_regions = CaptureTunnelSceneryRegions(camera);
	Textures().BeginScene();
	CaptureOcean();
	if (camera.tunnel_entrance < Map::Size()) CaptureTunnelPair(TileIndex{camera.tunnel_entrance});
}

Scene FinishCapture()
{
	assert(capture.has_value());
	Scene scene = std::move(capture->scene);
	static bool reported_road_stops = false;
	if (capture->road_stop_sections != 0 && (!reported_road_stops || capture->diagnostic)) {
		Debug(driver,1,"OpenTT3D: {} road stops rendered with volume shelters and loading bays",capture->road_stop_sections);
		if (!capture->diagnostic) reported_road_stops = true;
	}
	static std::map<uint32_t,bool> observed_crossings;
	static uint64_t crossing_generation = UINT64_MAX;
	static bool reported_crossing_transition = false;
	if (crossing_generation != TextureGeneration()) {
		crossing_generation = TextureGeneration();
		observed_crossings.clear();
		reported_crossing_transition = false;
	}
	if (!reported_crossing_transition && !capture->diagnostic && _game_mode == GM_NORMAL) {
		for (unsigned i = 0; i < capture->crossing_observation_count; ++i) {
			auto [tile,state] = capture->crossing_observations[i];
			auto previous = observed_crossings.find(tile);
			if (previous != observed_crossings.end() && previous->second != state) {
				Debug(driver,1,"OpenTT3D: live crossing {},{} changed from {} to {}",TileX(TileIndex{tile}),TileY(TileIndex{tile}),
					previous->second ? "barred" : "open",state ? "barred" : "open");
				reported_crossing_transition = true;
				break;
			}
			if (observed_crossings.size() >= 64 && previous == observed_crossings.end()) observed_crossings.erase(observed_crossings.begin());
			observed_crossings[tile] = state;
		}
	}
	static unsigned reported_crossing_states = 0;
	for (unsigned state = 0; state < 2; ++state) {
		if ((capture->crossing_states & (1U<<state)) != 0 && (reported_crossing_states & (1U<<state)) == 0 && !capture->diagnostic && _game_mode == GM_NORMAL) {
			Debug(driver,1,"OpenTT3D: live crossing {} state captured",state ? "barred" : "open");
			reported_crossing_states |= 1U<<state;
		}
	}
	static bool reported_crossings = false;
	if (capture->crossing_sections != 0 && (!reported_crossings || capture->diagnostic)) {
		Debug(driver,1,"OpenTT3D: {} crossings rendered with state-aware signals and clear roadways",capture->crossing_sections);
		if (!capture->diagnostic) reported_crossings = true;
	}
	static bool reported_depots = false;
	if (capture->depot_sections != 0 && (!reported_depots || capture->diagnostic)) {
		Debug(driver,1,"OpenTT3D: {} depots rendered with open bays and component materials",capture->depot_sections);
		if (!capture->diagnostic) reported_depots = true;
	}
	static bool reported = false;
	static bool reported_vehicles = false;
	static bool reported_bridges = false;
	static bool reported_fences = false;
	static bool reported_foundations = false;
	static bool reported_tunnels = false;
	static bool reported_rails = false;
	static bool reported_stations = false;
	static bool reported_ground_details = false;
	static bool reported_signals = false, reported_catenary = false;
	if (!capture->diagnostic && !reported_signals && capture->signal_parts != 0) {
		Debug(driver,1,"OpenTT3D: {} signals rendered with state-aware lamps and semaphore geometry",capture->signal_parts);
		reported_signals = true;
	}
	if (!capture->diagnostic && !reported_catenary && capture->catenary_parts != 0) {
		Debug(driver,1,"OpenTT3D: {} catenary parts rendered with contact wires, droppers and masts",capture->catenary_parts);
		reported_catenary = true;
	}
	if (!capture->diagnostic && !reported_ground_details && capture->ground_detail_sections != 0) {
		Debug(driver,1,"OpenTT3D: {} ground-detail tiles rendered with raised crops, hay, rocks or turf",capture->ground_detail_sections);
		reported_ground_details = true;
	}
	if (!capture->diagnostic && !reported_stations && capture->station_sections != 0) {
		Debug(driver,1,"OpenTT3D: {} station tiles rendered with platforms, buildings and paired halls",capture->station_sections);
		reported_stations = true;
	}
	static bool reported_voxel_airports = false;
	if (capture->voxel_airport_sections != 0 && (!reported_voxel_airports || capture->diagnostic)) {
		Debug(driver,1,"OpenTT3D: {} airport tiles rendered with authored voxel buildings",capture->voxel_airport_sections);
		reported_voxel_airports = true;
	}
	static bool reported_voxel_docks = false;
	if (capture->voxel_dock_sections != 0 && (!reported_voxel_docks || capture->diagnostic)) {
		Debug(driver,1,"OpenTT3D: {} dock sections rendered with climate-aware voxel geometry",capture->voxel_dock_sections);
		reported_voxel_docks = true;
	}
	if (!capture->diagnostic && !reported_rails && capture->rail_sections != 0) {
		Debug(driver,1,"OpenTT3D: {} rail sections rendered with volume rails, sleepers and guideways",capture->rail_sections);
		reported_rails = true;
	}
	if (!capture->diagnostic && !reported_tunnels && capture->tunnel_sections != 0) {
		Debug(driver,1,"OpenTT3D: {} tunnel sections rendered with open portals and continuous interiors",capture->tunnel_sections);
		reported_tunnels = true;
	}
	if (!capture->diagnostic && !reported_foundations && capture->foundation_parts != 0) {
		Debug(driver,1,"OpenTT3D: {} slope foundations rendered with complete retaining walls",capture->foundation_parts);
		reported_foundations = true;
	}
	if (!capture->diagnostic && !reported_fences && capture->fence_parts != 0) {
		Debug(driver,1,"OpenTT3D: {} fence sections rendered as terrain-following geometry",capture->fence_parts);
		reported_fences = true;
	}
	if (!capture->diagnostic && !reported_bridges && capture->bridge_parts != 0) {
		Debug(driver, 1, "OpenTT3D: {} bridge parts rendered with volumetric geometry", capture->bridge_parts);
		reported_bridges = true;
	}
	if (!capture->diagnostic && !reported_vehicles && capture->modelled_vehicles != 0) {
		Debug(driver, 1, "OpenTT3D: {} visible vehicle bodies rendered with directional authored geometry", capture->modelled_vehicles);
		reported_vehicles = true;
	}
	if (!capture->diagnostic && !reported && capture->reference_billboards != 0) {
		Debug(driver, 1, "OpenTT3D: {} unmodelled reference sprites in this view (release coverage is incomplete)", capture->reference_billboards);
		reported = true;
	}
	if (!capture->diagnostic && Profile::IsBenchmarking()) {
		static_assert(MP_OBJECT == static_cast<unsigned>(Profile::GeometryOwner::Object));
		Profile::GeometryCounts counts{};
		auto add = [&](uint32_t id, size_t vertices) {
			size_t owner = static_cast<size_t>(id == 0 ? Profile::GeometryOwner::Unowned : Profile::GeometryOwner::Vehicle);
			if ((id & TILE_PICK_ID) != 0) {
				TileIndex tile(id & ~TILE_PICK_ID);
				owner = tile.base() < Map::Size() ? static_cast<size_t>(GetTileType(tile)) : static_cast<size_t>(Profile::GeometryOwner::Unowned);
			}
			counts[owner] += vertices;
		};
		for (const auto &instance : scene.instances) add(instance.data.ObjectId(),instance.mesh->size());
		for (const auto &vertex : scene.vertices) add(vertex.object_id,1);
		Profile::AddCapturedGeometry(counts,capture->foundation_vertices,capture->fence_vertices,capture->rail_vertices);
	}
	capture.reset();
	return scene;
}

void RecycleCapture(Scene &scene)
{
	if (scene.vertices.capacity() > recycled_vertices.capacity()) scene.vertices.swap(recycled_vertices);
	if (scene.instances.capacity() > recycled_instances.capacity()) scene.instances.swap(recycled_instances);
	recycled_vertices.clear();
	recycled_instances.clear();
}

void CaptureTile(const TileInfo *tile)
{
	if (!capture) return;
	capture->tile = tile; capture->vehicle = nullptr;
	capture->tile_layers = 0; capture->have_parent = false;
}

void CaptureVehicle(const Vehicle *vehicle)
{
	if (!capture) return;
	capture->vehicle = vehicle; capture->tile = nullptr; capture->have_parent = false;
}

static float PixelScaleAt(Vec3 origin)
{
	float depth = capture->distance - Dot(origin - capture->camera.focus, capture->depth_direction);
	return capture->focal_scale / std::max(capture->near_plane, depth);
}

static unsigned TextureZoom(float scale)
{
	return scale >= 4 ? 0 : scale >= 2 ? 1 : scale >= 1 ? 2 : scale >= 0.5f ? 3 : scale >= 0.25f ? 4 : 5;
}

static unsigned TextureZoom(Vec3 origin) { return TextureZoom(PixelScaleAt(origin)); }

static bool CaptureTunnelPair(TileIndex entrance)
{
	if (capture->captured_tunnel_ends.contains(entrance)) return true;
	TunnelKind kind;
	if (!GetVanillaTunnelKind(entrance,kind)) return false;
	TileIndex other = GetOtherTunnelEnd(entrance);
	TunnelKind other_kind;
	if (!GetVanillaTunnelKind(other,other_kind) || kind != other_kind) return false;
	capture->captured_tunnel_ends.insert(entrance);
	capture->captured_tunnel_ends.insert(other);
	if (other < entrance) std::swap(entrance,other);
	unsigned direction = GetTunnelBridgeDirection(entrance);
	/* North-corner heights differ at opposite mouths; tunnel floors do not. */
	Vec3 origin{TileX(entrance)*16.0f,TileY(entrance)*16.0f,TerrainZ(GetTilePixelZ(entrance))};
	Vec3 finish{TileX(other)*16.0f,TileY(other)*16.0f,TerrainZ(GetTilePixelZ(other))};
	assert(origin.z == finish.z);
	unsigned length = static_cast<unsigned>((std::abs(finish.x-origin.x)+std::abs(finish.y-origin.y))/16);
	Vec3 step = (finish-origin)*(1.0f/length);
	bool reserved = kind <= TunnelKind::Maglev && _game_mode != GM_MENU && _settings_client.gui.show_track_reservation && HasTunnelBridgeReservation(entrance);
	for (unsigned segment = 0; segment <= length; ++segment) {
		Vec3 position = origin+step*segment;
		ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | TileVirtXY(static_cast<int>(position.x),static_cast<int>(position.y)).base()};
		size_t first = capture->scene.instances.size();
		bool portal = segment == 0 || segment == length;
		if (!portal) {
			Vec3 position = origin+step*segment;
			capture->tunnel_cuts.emplace(TileVirtXY(static_cast<int>(position.x),static_cast<int>(position.y)),CaptureState::TunnelCut{kind,direction,static_cast<int>(origin.z)});
		}
		TileIndex end = segment == length ? other : entrance;
		unsigned facing = segment == length ? to_underlying(ReverseDiagDir(static_cast<DiagDirection>(direction))) : direction;
		DrawTunnelSection(capture->scene,capture->camera,origin+step*segment,facing,kind,portal,HasTunnelBridgeSnowOrDesert(end),reserved);
		if (capture->scene.instances.size() != first) ++capture->tunnel_sections;
	}
	return true;
}

bool CaptureTunnel(const TileInfo &tile)
{
	return capture.has_value() && CaptureTunnelPair(tile.tile);
}

TileSurface MakeTileSurface(Slope slope)
{
	TileSurface surface;
	const Corner names[] = {CORNER_N,CORNER_W,CORNER_S,CORNER_E};
	for (unsigned i = 0; i < 4; ++i) surface.corners[i] = TerrainZ(GetSlopePixelZInCorner(RemoveHalftileSlope(slope),names[i]));
	surface.centre = TerrainZ(GetPartialPixelZ(8,8,RemoveHalftileSlope(slope)));
	if (IsHalftileSlope(slope)) {
		surface.raised_half = std::find(std::begin(names),std::end(names),GetHalftileSlopeCorner(slope))-std::begin(names);
		surface.upper_height = TerrainZ(GetSlopeMaxPixelZ(slope));
	}
	return surface;
}

void CaptureRailTracks(const TileInfo &tile, RailType type, TrackBits tracks, TrackBits reserved)
{
	if (!capture || tracks == TRACK_BIT_NONE) return;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawRailTracks(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},tile.tileh,type,tracks,reserved);
	if (Profile::IsBenchmarking()) for (size_t i = first; i < capture->scene.instances.size(); ++i) capture->rail_vertices += capture->scene.instances[i].mesh->size();
	if (capture->scene.instances.size() != first) ++capture->rail_sections;
}

void CaptureRailSupport(Vec3 origin, Slope slope, RailType type, TrackBits tracks)
{
	if (!capture || tracks == TRACK_BIT_NONE || type > RAILTYPE_MAGLEV || origin.x < 0 || origin.y < 0 || origin.x >= Map::MaxX()*16 || origin.y >= Map::MaxY()*16) return;
	auto &surfaces = capture->rail_surfaces[TileVirtXY(static_cast<int>(origin.x),static_cast<int>(origin.y))];
	surfaces.push_back({origin,MakeTileSurface(slope),to_underlying(type),to_underlying(tracks)});
}

bool CaptureRailStation(const TileInfo &tile, unsigned layout, const DrawTileSprites &source, PaletteID palette)
{
	if (!capture || !IsRailStationTile(tile.tile) || GetCustomStationSpecIndex(tile.tile) != 0 || layout >= 8) return false;
	RailType type = GetRailType(tile.tile);
	if (type > RAILTYPE_MAGLEV || GetRailTypeInfo(type)->UsesOverlay()) return false;
	unsigned offset = GetRailTypeInfo(type)->GetRailtypeSpriteOffset();
	if (!IsBaseGraphicsSprite((source.ground.sprite & SPRITE_MASK)+offset) || !IsBaseGraphicsSprite(SPR_RAIL_PLATFORM_X_REAR) || !IsBaseGraphicsSprite(SPR_RAIL_PLATFORM_BUILDING_X)) return false;
	for (const auto &component : source.GetSequence()) if (!IsBaseGraphicsSprite((component.image.sprite & SPRITE_MASK)+offset)) return false;
	CaptureGround(SPR_FLAT_GRASS_TILE,PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	TrackBits track = AxisToTrackBits(GetRailStationAxis(tile.tile));
	bool reserved = _game_mode != GM_MENU && _settings_client.gui.show_track_reservation && HasStationReservation(tile.tile);
	CaptureRailTracks(tile,type,track,reserved ? track : TRACK_BIT_NONE);
	if (IsInvisibilitySet(TO_BUILDINGS)) return true;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawRailStation(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},type,layout,palette,IsTransparencySet(TO_BUILDINGS));
	if (capture->scene.instances.size() != first) ++capture->station_sections;
	return true;
}

void BeginVoxelAirportAnimationChecks(std::span<const unsigned> graphics)
{
	std::map<unsigned,AirportAnimationCheck> checks;
	for (unsigned graphic : graphics) {
		if (graphic >= 74) throw std::runtime_error("Not a vanilla airport animation");
		unsigned frames = GetAirportTileLayouts(graphic).size();
		if (frames < 2 || frames > 16) throw std::runtime_error("Airport tile has no supported source animation");
		for (unsigned frame = 0; frame < frames; ++frame) {
			if (!VoxelAirportState(graphic,frame)) throw std::runtime_error("Airport animation has an unbound active-climate voxel frame");
		}
		checks.emplace(graphic,AirportAnimationCheck{UINT32_MAX,frames,0,false});
	}
	airport_animation_checks = std::move(checks);
	Debug(driver,1,"OpenTT3D: observing {} live voxel airport animations without changing game state",airport_animation_checks.size());
}

void BeginVoxelRadioBeaconCheck()
{
	check_radio_beacons = true; checked_radio_tile = INVALID_TILE; radio_beacon_colours.clear();
	Debug(driver,1,"OpenTT3D: observing original radio beacon palette without changing animation state");
}

void BeginVoxelIndustryAnimationChecks(std::span<const unsigned> graphics)
{
	std::map<unsigned,IndustryAnimationCheck> checks;
	for (unsigned graphic : graphics) {
		if (graphic >= std::size(_industry_draw_tile_data)/4 || !GetIndustryTileSpec(graphic)->anim_state) throw std::runtime_error("Industry tile has no original table-frame animation");
		IndustryAnimationCheck check;
		for (unsigned frame = 0; frame < 4; ++frame) {
			auto state = VoxelIndustryState(graphic,_industry_draw_tile_data[graphic*4+frame].building.sprite);
			if (!state) throw std::runtime_error("Industry animation has an unbound or replaced source frame");
			/* Original tables may repeat their last sprite. Require each distinct
			 * source selection, rather than an unreachable duplicate table slot. */
			check.expected |= 1U<<*state;
		}
		if (std::popcount(check.expected) < 2) throw std::runtime_error("Industry animation has fewer than two distinct source frames");
		checks.emplace(graphic,check);
	}
	industry_animation_checks = std::move(checks);
	Debug(driver,1,"OpenTT3D: observing {} live voxel industry animations without changing game state",industry_animation_checks.size());
}

void BeginVoxelPlasticFountainCheck()
{
	for (unsigned graphics = GFX_PLASTIC_FOUNTAIN_ANIMATED_1; graphics <= GFX_PLASTIC_FOUNTAIN_ANIMATED_8; ++graphics) {
		for (unsigned stage = 0; stage < 4; ++stage) {
			const auto &source = _industry_draw_tile_data[graphics*4+stage];
			if (!VoxelIndustryState(graphics,source.ground.sprite,true) ||
				(stage == 3 && !VoxelIndustryState(graphics,source.building.sprite)) ||
				(stage < 3 && (source.building.sprite != 0 || HasVoxelAsset("industries",graphics,stage)))) {
				throw std::runtime_error("Plastic fountain needs all eight original ground/body poses and its empty construction bodies");
			}
		}
	}
	checked_plastic_tile = INVALID_TILE; checked_plastic_industry = UINT32_MAX; checked_plastic_frames = 0;
	check_plastic_fountain = true;
	Debug(driver,1,"OpenTT3D: observing all eight plastic-fountain ground/body pairs on one unchanged industry tile without changing game state");
}

static void ObserveVoxelPlasticFountain(TileIndex tile, unsigned graphics)
{
	if (!check_plastic_fountain || graphics < GFX_PLASTIC_FOUNTAIN_ANIMATED_1 || graphics > GFX_PLASTIC_FOUNTAIN_ANIMATED_8 || GetIndustryConstructionStage(tile) != 3) return;
	/* The body must share this actual capture with its original ground pose.
	 * A previous viewport/frame's floor cannot qualify a newly visible body. */
	auto ground = capture->plastic_fountain_grounds.find(tile);
	if (ground == capture->plastic_fountain_grounds.end() || ground->second != graphics) return;
	if (checked_plastic_tile == INVALID_TILE) checked_plastic_tile = tile;
	if (tile != checked_plastic_tile) return;
	uint32_t industry = GetIndustryIndex(tile).base();
	if (checked_plastic_industry != industry) { checked_plastic_industry = industry; checked_plastic_frames = 0; }
	unsigned phase = graphics-GFX_PLASTIC_FOUNTAIN_ANIMATED_1;
	if ((checked_plastic_frames & (1U<<phase)) == 0) {
		Debug(driver,1,"OpenTT3D: plastic fountain tile {},{} industry {} graphics {} paired ground/body pose {} captured",TileX(tile),TileY(tile),industry,graphics,phase);
		checked_plastic_frames |= 1U<<phase;
	}
	if (checked_plastic_frames == 0xFF) {
		Debug(driver,1,"OpenTT3D: voxel plastic-fountain verification passed: eight original ground/body poses on one unchanged tile {},{} industry {}",TileX(tile),TileY(tile),industry);
		check_plastic_fountain = false;
	}
}

struct IndustryPaletteCheck {
	TileIndex tile = INVALID_TILE;
	uint32_t industry = UINT32_MAX;
	unsigned first_colour = 232, colour_count = 7;
	unsigned materials = 0;
	std::set<std::array<uint32_t,7>> phases;
	bool ground = true;
	bool passed = false;
};
static std::map<unsigned,IndustryPaletteCheck> industry_palette_checks;

void BeginVoxelIndustryPaletteCheck(unsigned graphics)
{
	bool fire = graphics >= 52 && graphics <= 57;
	bool fizzy = graphics >= 157 && graphics <= 159;
	if (!fire && !fizzy) throw std::invalid_argument("Industry palette observation needs steel ground52..57 or fizzy-drink body157..159");
	const auto &source = _industry_draw_tile_data[graphics*4+3];
	if (!VoxelIndustryState(graphics,fire ? source.ground.sprite : source.building.sprite,fire)) throw std::invalid_argument("Industry palette observation needs the original completed voxel layer");
	IndustryPaletteCheck check;
	check.ground = fire;
	if (fizzy) { check.first_colour = 227; check.colour_count = 5; }
	industry_palette_checks[graphics] = check;
	Debug(driver,1,"OpenTT3D: observing original {} palette on voxel industry {} {} without changing game state",fire ? "molten-metal" : "fizzy-drink",fire ? "ground" : "body",graphics);
}

static void ObserveVoxelIndustryPalette(TileIndex tile, unsigned graphics, size_t first, bool ground)
{
	auto found = industry_palette_checks.find(graphics);
	if (found == industry_palette_checks.end() || found->second.passed || found->second.ground != ground || capture->diagnostic || GetIndustryConstructionStage(tile) != 3) return;
	auto &check = found->second;
	if (check.tile == INVALID_TILE) {
		unsigned emitted = 0;
		for (size_t i = first; i < capture->scene.instances.size(); ++i) emitted |= VoxelPaletteMask(*capture->scene.instances[i].mesh,check.first_colour,check.colour_count);
		if (std::popcount(emitted) < (check.ground ? 2 : check.colour_count)) return;
		check.tile = tile;
		check.industry = GetIndustryIndex(tile).base();
		check.materials = emitted;
	}
	if (tile != check.tile || GetIndustryIndex(tile).base() != check.industry) return;
	auto palette = SnapshotPalette();
	std::array<uint32_t,7> phase{};
	for (unsigned i = 0; i < check.colour_count; ++i) if (check.materials & (1U<<i)) {
		Colour colour = palette.palette[check.first_colour+i];
		phase[i] = (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b;
	}
	check.phases.insert(phase);
	if (check.phases.size() >= check.colour_count) {
		check.passed = true;
		Debug(driver,1,"OpenTT3D: voxel industry palette observation passed: graphics {} tile {},{}, {} original {} phases across {} emitted animated materials",graphics,TileX(tile),TileY(tile),check.phases.size(),check.ground ? "fire" : "fizzy-drink",std::popcount(check.materials));
	}
}

void BeginVoxelVehicleCargoCheck(unsigned engine)
{
	if (!VoxelVehicleState(engine,false) || !VoxelVehicleState(engine,true)) throw std::runtime_error("Cargo observation requires both original voxel vehicle bindings in the active climate");
	checked_cargo_engine = engine;
	checked_cargo_vehicle = UINT32_MAX;
	checked_cargo_capacity = checked_cargo_states = 0;
	Debug(driver,1,"OpenTT3D: observing actual empty/full cargo for voxel engine {} without changing vehicle state",engine);
}

void BeginVoxelForestCycleCheck(std::optional<unsigned> graphics)
{
	unsigned base = graphics.value_or(_settings_game.game_creation.landscape == LandscapeType::Toyland ? 129 : 16);
	if (base != 16 && base != 129 && base != 135) throw std::invalid_argument("Harvest cycle needs original timber16, cotton129 or battery135 graphics");
	for (unsigned graphic : {base,base+1}) for (unsigned stage = 0; stage < 4; ++stage) {
		const auto &source = _industry_draw_tile_data[graphic*4+stage];
		if (!VoxelIndustryState(graphic,source.building.sprite) || !VoxelIndustryState(graphic,source.ground.sprite,true)) {
			throw std::runtime_error("Forest production cycle requires every original body and independent ground binding");
		}
	}
	checked_forest_base = base;
	forest_cycles.clear(); check_forest_cycle = true;
	Debug(driver,1,"OpenTT3D: observing actual mature industry graphics {}, harvested {} and all regrowth states without changing industry state",checked_forest_base,checked_forest_base+1);
}

void BeginVoxelDepotTraversalCheck(unsigned vehicle)
{
	const Vehicle *target = Vehicle::GetIfValid(VehicleID{vehicle});
	if (target == nullptr || (target->type != VEH_ROAD && target->type != VEH_SHIP)) throw std::runtime_error("Depot traversal requires an actual road vehicle or ship");
	checked_depot_vehicle = vehicle;
	checked_depot_tile = INVALID_TILE;
	checked_depot_phase = 0;
	Debug(driver,1,"OpenTT3D: observing visible/depot/visible traversal for vehicle {} without changing its orders or state",vehicle);
}

bool CaptureVoxelAirport(const TileInfo &tile, unsigned graphics, const DrawTileSprites &source, PaletteID palette)
{
	if (!capture || !IsAirport(tile.tile) || GetAirportGfx(tile.tile) >= 74) return false;
	unsigned frame = GetAirportTileLayouts(graphics).size() == 1 ? 0 : GetAnimationFrame(tile.tile);
	if (!HasVoxelAirport(graphics,frame)) return false;
	SpriteID ground = source.ground.sprite;
	{
		ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
		if (DrawVoxelAirportGround(capture->scene,graphics,frame,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},GroundSpritePaletteTransform(ground,source.ground.pal,palette))) {
			unsigned climate = to_underlying(_settings_game.game_creation.landscape);
			static std::set<std::tuple<unsigned,unsigned,unsigned>> reported;
			if (!capture->diagnostic && reported.emplace(graphics,frame,climate).second) {
				Debug(driver,1,"OpenTT3D: live independent voxel airport ground {} captured at {},{}",graphics,TileX(tile.tile),TileY(tile.tile));
				Debug(driver,1,"OpenTT3D: airport voxel climate selection graphics {} frame {} layer ground climate {} binding {}",graphics,frame,climate,*VoxelAirportState(graphics,frame,true));
			}
			if (source.GetSequence().empty()) {
				++capture->voxel_airport_sections;
				static std::set<unsigned> reported_ground_only;
				if (!capture->diagnostic && reported_ground_only.insert(graphics).second) Debug(driver,1,"OpenTT3D: live voxel airport tile {} captured at {},{} (original ground-only ownership)",graphics,TileX(tile.tile),TileY(tile.tile));
			}
		} else {
			CaptureGround(ground,GroundSpritePaletteTransform(ground,source.ground.pal,palette),tile.x,tile.y,tile.z,tile,nullptr,0,0);
		}
	}
	if (IsInvisibilitySet(TO_BUILDINGS)) return true;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	auto state = VoxelAirportState(graphics,frame);
	if (state) DrawVoxelAsset(capture->scene,"airport_tiles",graphics,*state,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},palette,IsTransparencySet(TO_BUILDINGS) ? 0.38f : 1);
	if (capture->scene.instances.size() != first) {
		++capture->voxel_airport_sections;
		unsigned climate = to_underlying(_settings_game.game_creation.landscape);
		static std::set<std::tuple<unsigned,unsigned,unsigned>> reported;
		if (!capture->diagnostic && reported.emplace(graphics,frame,climate).second) {
			Debug(driver,1,"OpenTT3D: live voxel airport tile {} captured at {},{}",graphics,TileX(tile.tile),TileY(tile.tile));
			Debug(driver,1,"OpenTT3D: airport voxel climate selection graphics {} frame {} layer body climate {} binding {}",graphics,frame,climate,*state);
		}
		/* Optional read-only trace for full-resolution volume clearance audits.
		 * Nine significant digits round-trip each emitted float transform. */
		if (!capture->diagnostic) Debug(driver,5,"OpenTT3D: clearance airport frame {} tile {} graphics {} state {} origin {:.9g},{:.9g},{:.9g}",
			capture_frame,tile.tile.base(),graphics,*state,static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z));
		if (check_radio_beacons && graphics == 32 && !capture->diagnostic) {
			if (checked_radio_tile == INVALID_TILE) {
				unsigned materials = 0;
				for (size_t i = first; i < capture->scene.instances.size(); ++i) materials |= VoxelPaletteMask(*capture->scene.instances[i].mesh,239,2);
				if (materials == 3) {
					checked_radio_tile = tile.tile;
					Debug(driver,1,"OpenTT3D: radio beacon material pair emitted on tile {},{}",TileX(tile.tile),TileY(tile.tile));
				}
			}
			if (checked_radio_tile == tile.tile) {
				auto palette = SnapshotPalette();
				std::array<uint32_t,2> colours{};
				for (unsigned i = 0; i < colours.size(); ++i) {
					Colour colour = palette.palette[239+i];
					colours[i] = (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b;
				}
				if (radio_beacon_colours.insert(colours).second) Debug(driver,1,"OpenTT3D: radio beacon palette phase {}: {} / {}",radio_beacon_colours.size(),colours[0],colours[1]);
				if (radio_beacon_colours.size() >= 3) {
					Debug(driver,1,"OpenTT3D: voxel radio beacon observation passed: {} original paired palette phases on tile {},{}",radio_beacon_colours.size(),TileX(tile.tile),TileY(tile.tile));
					check_radio_beacons = false;
				}
			}
		}
		auto found = airport_animation_checks.find(graphics);
		if (found != airport_animation_checks.end() && !found->second.complete) {
			auto &check = found->second;
			if (check.tile == UINT32_MAX) check.tile = tile.tile.base();
			if (check.tile == tile.tile.base() && frame < check.frames) {
				check.seen |= 1U<<frame;
				if (check.seen == (1U<<check.frames)-1) {
					check.complete = true;
					Debug(driver,1,"OpenTT3D: airport {} animation verification passed: {} upstream frames captured at {},{}",graphics,check.frames,TileX(tile.tile),TileY(tile.tile));
				}
			}
		}
	}
	return true;
}

static const std::vector<Vertex> *ClippedGroundMesh(const std::vector<Vertex> *mesh, const TileInfo &tile, Vec3 tile_offset = {})
{
	if (auto cut = capture->tunnel_cuts.find(tile.tile); cut != capture->tunnel_cuts.end()) {
		using Key = std::tuple<const std::vector<Vertex> *,TunnelKind,unsigned,int,float,float,float>;
		static std::map<Key,std::vector<Vertex>> clipped;
		const auto &bore = cut->second;
		int floor = bore.floor-static_cast<int>(TerrainZ(tile.z));
		if (std::any_of(mesh->begin(),mesh->end(),[&](const Vertex &v) { return v.position.z+tile_offset.z < floor+7.75f; })) {
			auto [found,inserted] = clipped.try_emplace(Key{mesh,bore.kind,bore.direction,floor,tile_offset.x,tile_offset.y,tile_offset.z});
			if (inserted) found->second = CutTunnelTerrain(*mesh,bore.kind,bore.direction,static_cast<float>(floor),tile_offset);
			return &found->second;
		}
	}
	return mesh;
}

/** Both sides choose identical subdivisions, including an unbound/custom
 * industry or depot which falls back to its original ground material. */
static unsigned GroundFineEdges(TileIndex tile)
{
	auto fine = [](TileIndex candidate) {
		if (IsTileType(candidate,MP_INDUSTRY) || IsRoadDepotTile(candidate) || IsRailDepotTile(candidate) || IsDockTile(candidate)) return true;
		if (IsTileType(candidate,MP_HOUSE) && HasVoxelHouseGround(GetHouseType(candidate)) && VoxelHouseGroundState(GetHouseType(candidate),GetHouseBuildingStage(candidate),TileHash2Bit(TileX(candidate)*TILE_SIZE,TileY(candidate)*TILE_SIZE))) return true;
		/* The Toyland rough board has independent coloured patches. Its
		 * boundary vertices must also be shared by adjacent ordinary tiles. */
		if (_settings_game.game_creation.landscape != LandscapeType::Toyland) return false;
		return (IsTileType(candidate,MP_CLEAR) && IsClearGround(candidate,CLEAR_ROUGH)) ||
			(IsTileType(candidate,MP_TREES) && GetTreeGround(candidate) == TREE_GROUND_ROUGH);
	};
	if (fine(tile)) return 15;
	unsigned mask = 0;
	const int dx[] = {0,1,0,-1}, dy[] = {-1,0,1,0};
	for (unsigned edge = 0; edge < 4; ++edge) {
		int x = static_cast<int>(TileX(tile))+dx[edge], y = static_cast<int>(TileY(tile))+dy[edge];
		if (x >= 0 && y >= 0 && x < static_cast<int>(Map::SizeX()) && y < static_cast<int>(Map::SizeY()) && fine(TileXY(x,y))) mask |= 1U<<edge;
	}
	return mask;
}

bool CaptureNaturalGround(const TileInfo &tile, bool rough, unsigned variant, SpriteID image)
{
	if (!capture || (!IsTileType(tile.tile,MP_CLEAR) && !IsTileType(tile.tile,MP_TREES)) ||
		(!rough && (variant == 0 || _settings_game.game_creation.landscape == LandscapeType::Toyland)) ||
		variant >= (rough ? 5U : 4U) || !IsBaseGraphicsSprite(image) || !IsBaseGraphicsSprite(SPR_FLAT_BARE_LAND) ||
		!IsBaseGraphicsSprite(SPR_FLAT_GRASS_TILE) || !IsBaseGraphicsSprite(SPR_FLAT_ROCKY_LAND_2)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawClearSurface(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},tile.tileh,rough,variant,GroundFineEdges(tile.tile));
	for (size_t index = first; index < capture->scene.instances.size(); ++index) {
		auto &instance = capture->scene.instances[index];
		instance.mesh = ClippedGroundMesh(instance.mesh,tile);
	}
	++capture->tile_layers;
	if (capture->scene.instances.size() != first) ++capture->ground_detail_sections;
	return true;
}

bool CaptureFarmland(const TileInfo &tile, unsigned stage, SpriteID image)
{
	if (!capture || stage >= 9 || !IsBaseGraphicsSprite(image) || !IsBaseGraphicsSprite(SPR_FLAT_BARE_LAND) || (stage == 8 && !IsBaseGraphicsSprite(SPR_FARMLAND_HAYPACKS))) return false;
	CaptureGround(SPR_FLAT_BARE_LAND+SlopeToSpriteOffset(tile.tileh),PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawGroundDetails(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},tile.tileh,false,stage);
	if (capture->scene.instances.size() != first) ++capture->ground_detail_sections;
	return true;
}

bool CaptureRocks(const TileInfo &tile, unsigned variant, SpriteID image, unsigned snow)
{
	if (!capture || variant > 1 || snow > 4 || !IsBaseGraphicsSprite(image) || !IsBaseGraphicsSprite(variant == 0 ? SPR_FLAT_ROCKY_LAND_1 : SPR_FLAT_ROCKY_LAND_2)) return false;
	/* Snow ground has already been submitted by the original callback. The
	 * painted rock overlay is replaced, so it cannot remain under this model. */
	if (snow == 0) CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(tile.tileh),PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawGroundDetails(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},tile.tileh,true,variant,snow);
	if (capture->scene.instances.size() != first) ++capture->ground_detail_sections;
	return true;
}

bool CaptureRailSignal(TileIndex tile, SpriteID image, int x, int y, int z, unsigned type, unsigned variant, unsigned state, unsigned direction)
{
	if (!capture || type >= 6 || variant >= 2 || state >= 2 || direction >= 8 || !IsBaseGraphicsSprite(image)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.base()};
	float height = 16;
	if (IsBridgeAbove(tile)) height = std::max(2.0f,TerrainZ(GetBridgePixelHeight(GetNorthernBridgeEnd(tile))-z)-3);
	size_t first = capture->scene.instances.size();
	DrawRailSignal(capture->scene,capture->camera,{static_cast<float>(x),static_cast<float>(y),TerrainZ(z)},type,variant,state,direction,height);
	if (capture->scene.instances.size() != first) ++capture->signal_parts;
	return true;
}

bool CaptureDepot(const TileInfo &tile, unsigned kind, unsigned direction, const DrawTileSprites &source, int relocation, SpriteID ground, PaletteID palette, bool reserved)
{
	if (!capture || kind >= 6 || direction >= 4 || !IsBaseGraphicsSprite(ground)) return false;
	for (const auto &piece : source.GetSequence()) if (!IsBaseGraphicsSprite((piece.image.sprite & SPRITE_MASK)+relocation)) return false;
	SpriteID canonical = kind < 4 ? SPR_RAIL_DEPOT_NE+GetRailTypeInfo(static_cast<RailType>(kind))->GetRailtypeSpriteOffset() :
		kind == 4 ? SPR_ROAD_DEPOT+4 : SPR_TRAMWAY_DEPOT_NO_TRACK+4;
	if (!IsBaseGraphicsSprite(canonical) || !IsBaseGraphicsSprite(SPR_RAIL_PLATFORM_X_REAR)) return false;
	if (kind < 4) ground = IsSnowRailGround(tile.tile) ? SPR_FLAT_SNOW_DESERT_TILE : SPR_FLAT_GRASS_TILE;
	int original_offset = kind < 4 ? GetRailTypeInfo(static_cast<RailType>(kind))->GetRailtypeSpriteOffset() :
		kind == 5 ? SPR_TRAMWAY_DEPOT_NO_TRACK-SPR_ROAD_DEPOT : 0;
	bool original_family = relocation == original_offset;
	bool voxel = original_family && HasVoxelDepot(kind,direction);
	unsigned floor_state = 0;
	if (kind < 4) floor_state = IsSnowRailGround(tile.tile) ? (_settings_game.game_creation.landscape == LandscapeType::Tropic ? 2 : 1) :
		_settings_game.game_creation.landscape == LandscapeType::Toyland ? 3 : 0;
	if (voxel) ++capture->tile_layers;
	else CaptureGround(ground,PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawDepot(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},kind,direction,palette,
		IsTransparencySet(TO_BUILDINGS),IsInvisibilitySet(TO_BUILDINGS),reserved,original_family,floor_state);
	if (capture->scene.instances.size() != first) {
		++capture->depot_sections;
		if (voxel && !capture->diagnostic) {
			static std::set<std::pair<unsigned,unsigned>> reported;
			if (reported.emplace(kind,direction).second) {
				Debug(driver,1,"OpenTT3D: live voxel depot {} direction {} captured at {},{}",kind,direction,TileX(tile.tile),TileY(tile.tile));
				Debug(driver,1,"OpenTT3D: voxel depot {} direction {} selected climate state {}",kind,direction,VoxelDepotState(direction));
			}
			if (checked_depot_phase == 2 && checked_depot_tile == tile.tile) {
				const Vehicle *vehicle = Vehicle::GetIfValid(VehicleID{checked_depot_vehicle});
				if (vehicle != nullptr && vehicle->IsInDepot() && vehicle->tile == tile.tile) checked_depot_phase = 3;
			}
		}
	}
	return true;
}

bool CaptureShipDepot(const TileInfo &tile, unsigned axis, unsigned part, PaletteID palette)
{
	if (!capture || !HasVoxelShipDepot(axis,part)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	if (!DrawVoxelShipDepot(capture->scene,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},axis,part,palette,
		IsTransparencySet(TO_BUILDINGS),IsInvisibilitySet(TO_BUILDINGS))) return false;
	if (capture->scene.instances.size() != first) {
		++capture->depot_sections;
		if (!capture->diagnostic) {
			static std::set<std::pair<unsigned,unsigned>> reported;
			if (reported.emplace(axis,part).second) Debug(driver,1,"OpenTT3D: live voxel ship depot axis {} part {} captured at {},{}",axis,part,TileX(tile.tile),TileY(tile.tile));
			if (checked_depot_phase == 2 && checked_depot_tile == tile.tile) {
				const Vehicle *vehicle = Vehicle::GetIfValid(VehicleID{checked_depot_vehicle});
				if (vehicle != nullptr && vehicle->IsInDepot() && vehicle->tile == tile.tile) checked_depot_phase = 3;
			}
		}
	}
	return true;
}

static unsigned checked_dock_graphics = UINT_MAX;
static TileIndex checked_dock_tile = INVALID_TILE;
static std::set<std::array<uint32_t,3>> checked_dock_lamps;
static std::set<std::array<uint32_t,5>> checked_dock_foam;

void BeginVoxelDockPaletteCheck(unsigned graphics)
{
	if (graphics < 4 || graphics >= 6 || VoxelDockState() != 0 || !HasVoxelDock(graphics)) throw std::invalid_argument("Dock palette observation needs an original non-Toyland water part4 or5");
	checked_dock_graphics = graphics; checked_dock_tile = INVALID_TILE;
	checked_dock_lamps.clear(); checked_dock_foam.clear();
	Debug(driver,1,"OpenTT3D: observing original lamp and foam palette phases on voxel dock {}",graphics);
}

static void ObserveVoxelDockPalette(TileIndex tile, unsigned graphics, size_t first)
{
	if (graphics != checked_dock_graphics || capture->diagnostic) return;
	if (checked_dock_tile == INVALID_TILE) {
		unsigned emitted = 0;
		for (size_t i = first; i < capture->scene.instances.size(); ++i) emitted |= VoxelPaletteMask(*capture->scene.instances[i].mesh,241,14);
		if ((emitted&0x3E07U) != 0x3E07U) return;
		checked_dock_tile = tile;
	}
	if (tile != checked_dock_tile) return;
	auto palette = SnapshotPalette();
	auto rgb = [&](unsigned index) {
		Colour colour = palette.palette[index];
		return (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b;
	};
	std::array<uint32_t,3> lamps{};
	std::array<uint32_t,5> foam{};
	for (unsigned i = 0; i < lamps.size(); ++i) lamps[i] = rgb(241+i);
	for (unsigned i = 0; i < foam.size(); ++i) foam[i] = rgb(250+i);
	checked_dock_lamps.insert(lamps); checked_dock_foam.insert(foam);
	if (checked_dock_lamps.size() >= 4 && checked_dock_foam.size() >= 5) {
		Debug(driver,1,"OpenTT3D: voxel dock palette observation passed: graphics {} tile {},{}, {} original lamp phases and {} foam phases",graphics,TileX(tile),TileY(tile),checked_dock_lamps.size(),checked_dock_foam.size());
		checked_dock_graphics = UINT_MAX;
	}
}

bool CaptureVoxelDock(const TileInfo &tile, unsigned graphics, const DrawTileSprites &source, PaletteID palette)
{
	if (!capture || !IsDockTile(tile.tile) || graphics >= 6 || !HasVoxelDock(graphics)) return false;
	for (const auto &piece : source.GetSequence()) if (!IsBaseGraphicsSprite(piece.image.sprite&SPRITE_MASK)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	if (!DrawVoxelDock(capture->scene,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},graphics,palette,
		IsTransparencySet(TO_BUILDINGS),IsInvisibilitySet(TO_BUILDINGS))) return false;
	if (capture->scene.instances.size() != first) {
		++capture->voxel_dock_sections;
		ObserveVoxelDockPalette(tile.tile,graphics,first);
		if (!capture->diagnostic) {
			static std::set<unsigned> reported;
			if (reported.insert(graphics).second) Debug(driver,1,"OpenTT3D: live voxel dock {} climate state {} captured at {},{}",graphics,VoxelDockState(),TileX(tile.tile),TileY(tile.tile));
		}
	}
	return true;
}

bool CaptureCrossing(const TileInfo &tile, SpriteID ground, PaletteID palette)
{
	if (!capture || !IsBaseGraphicsSprite(ground)) return false;
	RailType type = GetRailType(tile.tile);
	RoadType road = GetRoadTypeRoad(tile.tile), tram = GetRoadTypeTram(tile.tile);
	if (type > RAILTYPE_MAGLEV || (road != INVALID_ROADTYPE && (road != ROADTYPE_ROAD || GetRoadTypeInfo(road)->UsesOverlay())) ||
		(tram != INVALID_ROADTYPE && (tram != ROADTYPE_TRAM || GetRoadTypeInfo(tram)->UsesOverlay()))) return false;
	const auto *rti = GetRailTypeInfo(type);
	if (rti->UsesOverlay() || !IsBaseGraphicsSprite(SPR_ROAD_X) || !IsBaseGraphicsSprite(SPR_FLAT_BARE_LAND)) return false;
	unsigned variant = (ground-rti->base_sprites.crossing)/4;
	SpriteID clean = variant >= 2 ? SPR_FLAT_SNOW_DESERT_TILE : variant == 1 ? GetRoadDepotDrawData(DIAGDIR_NE).ground.sprite :
		palette == PALETTE_TO_BARE_LAND ? SPR_FLAT_BARE_LAND : SPR_FLAT_GRASS_TILE;
	if (!IsBaseGraphicsSprite(clean)) return false;
	CaptureGround(clean,PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	DrawCrossing(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},to_underlying(type),
		GetCrossingRailAxis(tile.tile),IsCrossingBarred(tile.tile),tram != INVALID_ROADTYPE,
		_game_mode != GM_MENU && _settings_client.gui.show_track_reservation && HasCrossingReservation(tile.tile));
	if (capture->scene.instances.size() != first) {
		++capture->crossing_sections;
		capture->crossing_states |= 1U<<IsCrossingBarred(tile.tile);
		if (capture->crossing_observation_count < capture->crossing_observations.size()) {
			capture->crossing_observations[capture->crossing_observation_count++] = {tile.tile.base(),IsCrossingBarred(tile.tile)};
		}
	}
	return true;
}

bool CaptureRailWire(const TileInfo &tile, SpriteID image, Track track, const std::array<int,4> &heights, unsigned support_mask, unsigned half)
{
	if (!capture || track >= TRACK_END || half > 2 || !IsBaseGraphicsSprite(image)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	/* RailPath's geometric endpoints, in DiagDirection order NE,SE,SW,NW. */
	constexpr unsigned first_end[] = {0,3,0,2,2,0}, last_end[] = {2,1,3,1,3,1};
	unsigned a = first_end[track], b = last_end[track];
	unsigned supports = ((support_mask>>a)&1U) | (((support_mask>>b)&1U)<<1);
	size_t first = capture->scene.instances.size();
	DrawCatenaryWire(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(heights[a])},track,TerrainZ(heights[b]-heights[a]),supports,half,IsTransparencySet(TO_CATENARY));
	Vec3 begin = RailPath(track,half == 2 ? 0.5f : 0).point, end = RailPath(track,half == 1 ? 0.5f : 1).point;
	begin.z = TerrainZ(std::lerp(static_cast<float>(heights[a]),static_cast<float>(heights[b]),half == 2 ? 0.5f : 0))+10;
	end.z = TerrainZ(std::lerp(static_cast<float>(heights[a]),static_cast<float>(heights[b]),half == 1 ? 0.5f : 1))+10;
	Vec3 origin{static_cast<float>(tile.x),static_cast<float>(tile.y),0};
	capture->contact_wires[tile.tile].push_back({origin+begin,origin+end});
	if (capture->scene.instances.size() != first) ++capture->catenary_parts;
	return true;
}

bool CaptureRailPylon(const TileInfo &tile, SpriteID image, int x, int y, int elevation, int contact_x, int contact_y, bool on_bridge)
{
	if (!capture || !IsBaseGraphicsSprite(image)) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	int tx = static_cast<int>(tile.x), ty = static_cast<int>(tile.y);
	int floor = on_bridge ? elevation : GetSlopePixelZ(std::clamp(x,tx,tx+15),std::clamp(y,ty,ty+15),true);
	size_t first = capture->scene.instances.size();
	DrawCatenaryPylon(capture->scene,{static_cast<float>(x),static_cast<float>(y),TerrainZ(floor)},
		{static_cast<float>(contact_x),static_cast<float>(contact_y),TerrainZ(elevation)+10.0f},IsTransparencySet(TO_CATENARY));
	if (capture->scene.instances.size() != first) ++capture->catenary_parts;
	return true;
}

bool CaptureRoadStop(const TileInfo &tile, unsigned layout, const DrawTileSprites &source, PaletteID palette)
{
	if (!capture || layout >= 6 || !IsStationRoadStopTile(tile.tile)) return false;
	RoadType road = GetRoadTypeRoad(tile.tile), tram = GetRoadTypeTram(tile.tile);
	if (layout < 4 && tram != INVALID_ROADTYPE) return false;
	if ((road != INVALID_ROADTYPE && (road != ROADTYPE_ROAD || GetRoadTypeInfo(road)->UsesOverlay())) ||
		(tram != INVALID_ROADTYPE && (tram != ROADTYPE_TRAM || GetRoadTypeInfo(tram)->UsesOverlay()))) return false;
	for (const auto &part : source.GetSequence()) if (!IsBaseGraphicsSprite(part.image.sprite & SPRITE_MASK)) return false;
	bool truck = GetRoadStopType(tile.tile) == RoadStopType::Truck;
	SpriteID paving = GetRoadDepotDrawData(DIAGDIR_NE).ground.sprite;
	if (!IsBaseGraphicsSprite(source.ground.sprite & SPRITE_MASK) || !IsBaseGraphicsSprite(paving) ||
		!IsBaseGraphicsSprite(SPR_ROAD_X) || !IsBaseGraphicsSprite(SPR_BUS_STOP_DT_X_W) || (truck && !IsBaseGraphicsSprite(SPR_TRUCK_STOP_DT_X_W))) return false;
	CaptureGround(paving,PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0);
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	size_t first = capture->scene.instances.size();
	float height = IsBridgeAbove(tile.tile) ? std::max(1.0f,TerrainZ(GetBridgePixelHeight(GetNorthernBridgeEnd(tile.tile))-tile.z)-1) : 12;
	DrawRoadStop(capture->scene,capture->camera,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},truck,layout,tram != INVALID_ROADTYPE,palette,
		IsTransparencySet(TO_BUILDINGS),IsInvisibilitySet(TO_BUILDINGS),height);
	if (capture->scene.instances.size() != first) ++capture->road_stop_sections;
	return true;
}

static TileIndex foundation_review_tile = INVALID_TILE;

bool CaptureFoundation(const TileInfo &tile, Foundation foundation)
{
	if (!capture) return false;
	static uint64_t generation = UINT64_MAX;
	static bool supported = false;
	if (generation != TextureGeneration()) {
		generation = TextureGeneration(); supported = true;
		for (unsigned slope = 1; slope < 15; ++slope) supported &= IsBaseGraphicsSprite(SPR_FOUNDATION_BASE+slope);
		for (unsigned slot = 0; slot < NORMAL_FOUNDATION_SPRITE_COUNT; ++slot) supported &= IsBaseGraphicsSprite(SPR_SLOPES_BASE+slot);
		for (unsigned slot = 0; slot < 4*HALFTILE_BLOCK_SIZE; ++slot) supported &= IsBaseGraphicsSprite(SPR_HALFTILE_FOUNDATION_BASE+slot);
	}
	if (!supported) return false;
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	Vec3 origin{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)};
	if (capture->scene.visibility && !capture->scene.visibility->Intersects(origin,origin+Vec3{16,16,TerrainZ(24)})) return true;
	float scale = PixelScaleAt(origin+Vec3{8,8,4});
	unsigned lod = scale >= 1.25f ? 0 : scale >= 0.35f ? 1 : 2;
	using Key = std::tuple<Slope,Foundation,unsigned>;
	static std::map<Key,std::vector<Vertex>> meshes;
	auto [mesh,inserted] = meshes.try_emplace(Key{tile.tileh,foundation,lod});
	if (inserted) {
		Slope upper = tile.tileh;
		float rise = TerrainZ(ApplyPixelFoundationToSlope(foundation,upper));
		mesh->second = MakeFoundationMesh(MakeTileSurface(tile.tileh),MakeTileSurface(upper),rise,lod);
	}
	if (mesh->second.empty()) return true;
	InstanceData data;
	data.origin_opacity = {origin.x,origin.y,origin.z,1};
	UsePaletteMaterial(data);
	capture->scene.instances.push_back({&mesh->second,data});
	++capture->foundation_parts;
	capture->foundation_vertices += mesh->second.size();
	if (!capture->diagnostic && tile.tile == foundation_review_tile) {
		Debug(driver,1,"OpenTT3D: live voxel foundation {} slope {} captured at {},{}",to_underlying(foundation),to_underlying(tile.tileh),TileX(tile.tile),TileY(tile.tile));
		foundation_review_tile = INVALID_TILE;
	}
	return true;
}

bool FocusReferenceFoundation(std::string_view kind)
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		TileType type = GetTileType(tile);
		if ((kind == "house" || kind == "voxel-house") && type != MP_HOUSE) continue;
		if (kind == "voxel-house" && !VoxelHouseState(GetHouseType(tile),GetHouseBuildingStage(tile),TileHash2Bit(x*TILE_SIZE,y*TILE_SIZE))) continue;
		if (kind == "rail" && type != MP_RAILWAY) continue;
		if (kind == "road" && type != MP_ROAD) continue;
		if (kind == "station" && type != MP_STATION) continue;
		if (kind == "industry" && type != MP_INDUSTRY) continue;
		Slope slope = GetTileSlope(tile);
		if (slope == SLOPE_FLAT) continue;
		auto proc = _tile_type_procs[type]->get_foundation_proc;
		Foundation foundation = proc ? proc(tile,slope) : FOUNDATION_NONE;
		if (!IsFoundation(foundation) || foundation == FOUNDATION_INVALID) continue;
		foundation_review_tile = tile;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused live {} foundation {} slope {} at {},{}",kind,to_underlying(foundation),to_underlying(slope),x,y);
		return true;
	}
	return false;
}

static void CaptureFenceMesh(const TileInfo &tile, unsigned style, unsigned layout, PaletteID palette)
{
	ObjectTag tag{capture->scene.vertices.size(),TILE_PICK_ID | tile.tile.base()};
	Vec3 origin{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)};
	if (capture->scene.visibility && !capture->scene.visibility->Intersects(origin-Vec3{1,1,1},origin+Vec3{17,17,TerrainZ(24)})) return;
	float scale = PixelScaleAt(origin+Vec3{8,8,3});
	unsigned lod = scale >= 1.25f ? 0 : scale >= 0.35f ? 1 : 2;
	/* Sloped RFO slots select different source sprites, but their 3D placement
	 * is the same edge. The slope is already a separate geometry key. */
	if (style == 6 && layout%8 >= 4) layout = (layout < 8 ? 0 : 8)+(layout&1);
	using Key = std::tuple<unsigned,unsigned,Slope,unsigned>;
	static std::map<Key,std::vector<Vertex>> meshes;
	auto [mesh,inserted] = meshes.try_emplace(Key{style,layout,tile.tileh,lod});
	if (inserted) {
		TileSurface surface = MakeTileSurface(tile.tileh);
		Vec3 start, end;
		bool flat = false;
		if (style == 6) {
			/* RFO order from the upstream rail drawing callback, including the
			 * internal diagonal fence of a raised half-tile. */
			if (layout == 2 || layout == 10 || layout == 3 || layout == 11) {
				flat = true;
				unsigned corner = layout == 2 ? 1 : layout == 10 ? 3 : layout == 3 ? 0 : 2;
				float z = surface.corners[corner];
				start = layout == 2 || layout == 10 ? Vec3{0,0,z} : Vec3{16,0,z};
				end = layout == 2 || layout == 10 ? Vec3{16,16,z} : Vec3{0,16,z};
			} else if (layout % 2 == 0) {
				float y = layout < 8 ? 1 : 15;
				start = {0,y,0}; end = {16,y,0};
			} else {
				float x = layout < 8 ? 1 : 15;
				start = {x,0,0}; end = {x,16,0};
			}
		} else {
			const Vec3 corners[] = {{0,0,0},{16,0,0},{16,16,0},{0,16,0}};
			const unsigned edges[][2] = {{0,3},{3,2},{1,2},{0,1}}; // NE, SE, SW, NW.
			start = corners[edges[layout][0]]; end = corners[edges[layout][1]];
		}
		mesh->second = MakeFenceMesh(style,start,end,surface,flat,0,lod);
		RegisterPackedVoxelMesh(mesh->second,true);
	}
	InstanceData data;
	data.origin_opacity = {origin.x,origin.y,origin.z,1};
	UsePaletteMaterial(data,palette);
	capture->scene.instances.push_back({&mesh->second,data});
}

bool CaptureFence(const TileInfo &tile, unsigned style, unsigned layout, SpriteID image, SpriteID material, PaletteID palette)
{
	if (!capture || style > 6 || layout >= (style == 6 ? 16U : 4U) || material == 0 || !IsBaseGraphicsSprite(image) || !IsBaseGraphicsSprite(material)) return false;
	if (style == 1 && (!IsBaseGraphicsSprite(SPR_HEDGE_BUSHES) || !IsBaseGraphicsSprite(SPR_HEDGE_FENCE))) return false;
	size_t begin = capture->scene.instances.size();
	/* Face-local palette cells keep white gate paint off hedge end-caps without
	 * the old texture-chart partitions or a second full-volume mesh build. */
	CaptureFenceMesh(tile,style,layout,palette);
	if (capture->scene.instances.size() > begin) {
		++capture->fence_parts;
		if (Profile::IsBenchmarking()) for (size_t i = begin; i < capture->scene.instances.size(); ++i) capture->fence_vertices += capture->scene.instances[i].mesh->size();
		static std::array<bool,7> reported{};
		if (!reported[style] && capture->tile != nullptr && capture->tile->tile == tile.tile) {
			reported[style] = true;
			Debug(driver,1,"OpenTT3D: live voxel fence style {} captured at {},{}",style,TileX(tile.tile),TileY(tile.tile));
		}
	}
	return true;
}

bool FocusReferenceFence(unsigned style)
{
	if (style > 6) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		bool found = false;
		if (style < 6 && IsTileType(tile,MP_CLEAR) && IsClearGround(tile,CLEAR_FIELDS)) {
			for (DiagDirection side : {DIAGDIR_NE,DIAGDIR_SE,DIAGDIR_SW,DIAGDIR_NW}) found |= GetFence(tile,side) == style+1;
		} else if (style == 6 && IsTileType(tile,MP_RAILWAY) && IsPlainRail(tile)) {
			switch (GetRailGroundType(tile)) {
				case RailGroundType::FenceNW: case RailGroundType::FenceSE: case RailGroundType::FenceSENW:
				case RailGroundType::FenceNE: case RailGroundType::FenceSW: case RailGroundType::FenceNESW:
				case RailGroundType::FenceVert1: case RailGroundType::FenceVert2:
				case RailGroundType::FenceHoriz1: case RailGroundType::FenceHoriz2: found = true; break;
				default: break;
			}
		}
		if (!found) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused live fence style {} at {},{}",style,x,y);
		return true;
	}
	return false;
}

/** Homogeneous repeat-textured strips cover the exterior through the horizon. */
static void CaptureOcean()
{
	if (_settings_game.construction.freeform_edges || Map::Size() == 0) return;
	const Camera &camera = capture->camera;
	SpriteTexture texture = Textures().Get(SPR_FLAT_WATER_TILE, PAL_NONE, TextureZoom({camera.focus.x, camera.focus.y, 0}), true);
	capture->scene.water = {texture.UV(-texture.x_offset, -texture.y_offset), ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE)};
	capture->scene.Ocean(Map::MaxX() * 16.0f, Map::MaxY() * 16.0f, texture.page, texture.Region());
}

static Vec3 SpriteUV(const SpriteTexture &texture, Vec3 p, Vec3 origin, int extra_x = 0, int extra_y = 0)
{
	Vec3 relative = p - origin;
	return texture.UV(2 * (relative.y - relative.x) * ZOOM_BASE - texture.x_offset - extra_x,
		(relative.x + relative.y - relative.z) * ZOOM_BASE - texture.y_offset - extra_y);
}

/** Every upstream slope has an immutable local mesh, shared by terrain layers. */
static const std::vector<Vertex> &GroundGeometry(Slope tileh, bool flat_material, unsigned fine_edges)
{
	static std::array<std::vector<Vertex>, 512*16> meshes;
	auto &vertices = meshes[(to_underlying(tileh)*2+flat_material)*16+fine_edges];
	if (!vertices.empty()) return vertices;
	Scene mesh;
	Slope slope = RemoveHalftileSlope(tileh);
	Vec3 corner[] = {{0, 0, 0}, {16, 0, 0}, {16, 16, 0}, {0, 16, 0}};
	const Corner names[] = {CORNER_N, CORNER_W, CORNER_S, CORNER_E};
	for (unsigned i = 0; i < 4; ++i) corner[i].z += TerrainZ(GetSlopePixelZInCorner(slope, names[i]));
	if (tileh == SLOPE_FLAT) {
		if (fine_edges == 0) mesh.Quad(corner[0],corner[1],corner[2],corner[3],{});
		else GroundEdgeFan(mesh,corner,{8,8,0},{},fine_edges);
	} else if (IsHalftileSlope(tileh)) {
		Corner raised = GetHalftileSlopeCorner(tileh);
		unsigned top = raised == CORNER_N ? 0 : raised == CORNER_W ? 1 : raised == CORNER_S ? 2 : 3;
		unsigned left = (top + 1) % 4, right = (top + 3) % 4;
		float cx = (corner[top].x + corner[left].x + corner[right].x) / 3;
		float cy = (corner[top].y + corner[left].y + corner[right].y) / 3;
		float height = TerrainZ(GetPartialPixelZ(static_cast<int>(cx), static_cast<int>(cy), tileh));
		Vec3 a = corner[top], b = corner[left], c = corner[right];
		a.z = b.z = c.z = height;
		const Vec3 boundary[] = {a,b,c};
		GroundEdgeFan(mesh,boundary,(a+b+c)*(1.0f/3),{},fine_edges);
		/* The lower half was already submitted before DrawFoundation. Drawing
		 * it again here would paint the upper material over water/track below. */
	} else {
		Vec3 center{8, 8, TerrainZ(GetPartialPixelZ(8, 8, tileh))};
		GroundEdgeFan(mesh,corner,center,{},fine_edges);
	}
	vertices = std::move(mesh.vertices);
	for (auto &vertex : vertices) vertex.texture = {vertex.position.x,vertex.position.y,flat_material ? 0 : vertex.position.z/TERRAIN_HEIGHT_SCALE};
	return vertices;
}

/** Natural terrain uses a flat material chart, not the camera-compressed image
 * of a slope. Raised details/transport overlays are handled separately. */
static std::optional<SpriteID> FlatTerrainMaterial(SpriteID image, Slope slope)
{
	if (!IsBaseGraphicsSprite(image)) return std::nullopt;
	SpriteID sprite = image & SPRITE_MASK;
	Slope chart_slope = IsHalftileSlope(slope) ? SlopeWithThreeCornersRaised(OppositeCorner(GetHalftileSlopeCorner(slope))) : slope;
	unsigned offset = SlopeToSpriteOffset(chart_slope);
	auto matches = [&](SpriteID base) { return base != 0 && sprite == base+offset && IsBaseGraphicsSprite(base); };
	for (unsigned density = 0; density < 4; ++density) {
		SpriteID base = SPR_FLAT_BARE_LAND+density*19;
		if (matches(base)) return base;
		base = _clear_land_sprites_snow_desert[density];
		if (matches(base)) return base;
	}
	for (unsigned field = 0; field < 9; ++field) if (matches(_clear_land_sprites_farmland[field])) return _clear_land_sprites_farmland[field];
	for (SpriteID base : {SPR_FLAT_ROUGH_LAND,SPR_FLAT_ROCKY_LAND_1,SPR_FLAT_ROCKY_LAND_2}) if (matches(base)) return base;
	if (slope == SLOPE_FLAT) for (SpriteID base : _landscape_clear_sprites_rough) if (matches(base)) return base;
	return std::nullopt;
}

void CaptureGround(SpriteID image, PaletteID palette, int x, int y, int z, const TileInfo &tile, const SubSprite *, int offset_x, int offset_y, unsigned fine_edges)
{
	if (!capture || tile.tile == INVALID_TILE || !IsValidTile(tile.tile)) return;
	Vec3 origin{static_cast<float>(x), static_cast<float>(y), TerrainZ(z)};
	if (tile.tileh == SLOPE_FLAT && offset_x == 0 && offset_y == 0) {
		size_t first = capture->scene.instances.size();
		bool industry = IsTileType(tile.tile,MP_INDUSTRY);
		bool oilrig = IsTileType(tile.tile,MP_STATION) && IsOilRig(tile.tile);
		bool house = IsTileType(tile.tile,MP_HOUSE) && HasVoxelHouseGround(GetHouseType(tile.tile));
		unsigned graphics = industry ? GetIndustryGfx(tile.tile) : oilrig ? GFX_OILRIG_1 : house ? GetHouseType(tile.tile) : 0;
		unsigned variant = house ? TileHash2Bit(tile.x,tile.y) : 0;
		bool voxel = industry || oilrig ? DrawVoxelIndustryGround(capture->scene,graphics,image,origin,palette) :
			house && DrawVoxelHouseGround(capture->scene,graphics,GetHouseBuildingStage(tile.tile),variant,image,origin,palette);
		if (voxel) {
			++capture->tile_layers;
			for (size_t i = first; i < capture->scene.instances.size(); ++i) {
				/* Preserve the existing underground-Cab clipping of terrain above
				 * a bore, even though this layer now has explicit palette volume. */
				capture->scene.instances[i].mesh = ClippedGroundMesh(capture->scene.instances[i].mesh,tile);
				capture->scene.instances[i].data.SetObjectId(TILE_PICK_ID|tile.tile.base());
			}
			capture->scene.instances.erase(std::remove_if(capture->scene.instances.begin()+first,capture->scene.instances.end(),
				[](const auto &instance) { return instance.mesh->empty(); }),capture->scene.instances.end());
			if (capture->scene.instances.size() > first && !capture->diagnostic) {
				unsigned stage = industry ? GetIndustryConstructionStage(tile.tile) : oilrig ? 3 : GetHouseBuildingStage(tile.tile);
				if (industry && !industry_palette_checks.empty()) ObserveVoxelIndustryPalette(tile.tile,graphics,first,true);
				if (industry && check_plastic_fountain && stage == 3 && graphics >= GFX_PLASTIC_FOUNTAIN_ANIMATED_1 && graphics <= GFX_PLASTIC_FOUNTAIN_ANIMATED_8) capture->plastic_fountain_grounds[tile.tile] = graphics;
				unsigned climate = to_underlying(_settings_game.game_creation.landscape);
				static std::set<std::tuple<bool,unsigned,unsigned,unsigned,unsigned>> reported;
				if (reported.emplace(house,graphics,stage,variant,climate).second) {
					Debug(driver,1,"OpenTT3D: live voxel {} ground {} construction stage {} captured at {},{}",house ? "house" : "industry",graphics,stage,TileX(tile.tile),TileY(tile.tile));
					if (house) Debug(driver,1,"OpenTT3D: live voxel house ground {} construction stage {} variant {} captured",graphics,stage,variant);
					else if (auto state = VoxelIndustryState(graphics,image,true)) Debug(driver,1,"OpenTT3D: industry voxel climate selection graphics {} stage {} layer ground climate {} binding {}",graphics,stage,climate,*state);
				}
			}
			return;
		}
	}
	bool opaque = capture->tile_layers == 0;
	auto flat_material = FlatTerrainMaterial(image,tile.tileh);
	/* The first layer must meet adjacent terrain/voxel floors at the original
	 * map height. Only subsequent overlays need a small depth-order offset. */
	float layer = (capture->tile_layers++) * 0.015f;
	if (!capture->scene.visibility->Intersects({tile.x - 1.0f, tile.y - 1.0f, TerrainZ(tile.z) - 1.0f}, {tile.x + 17.0f, tile.y + 17.0f, TerrainZ(tile.z + 32) + 1})) return;
	SpriteTexture texture = Textures().Get(flat_material.value_or(image), palette, TextureZoom(origin), opaque);
	Vec3 root{static_cast<float>(tile.x), static_cast<float>(tile.y), TerrainZ(tile.z)};
	Vec3 material_root = root;
	if (flat_material) material_root.z = origin.z;
	else material_root.z = origin.z+(root.z-origin.z)/TERRAIN_HEIGHT_SCALE;
	Vec3 uv = SpriteUV(texture, material_root, origin, offset_x, offset_y);
	InstanceData instance;
	instance.origin_opacity = {root.x, root.y, root.z + layer, 1};
	instance.uv_transform = {uv.x, uv.y, ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE), uv.z};
	instance.region = texture.Region();
	instance.identity[1] = static_cast<float>(static_cast<uint32_t>(texture.opaque_surface ? SurfaceMode::Opaque : SurfaceMode::Cutout) | (flat_material ? SURFACE_SHADED : 0));
	instance.identity[2] = 1; // Terrain UVs are never mirrored onto rear faces.
	instance.identity[3] = 2; // Preserve source UV heights while doubling terrain geometry.
	instance.SetObjectId(TILE_PICK_ID | tile.tile.base());
	if (fine_edges == UINT_MAX) fine_edges = GroundFineEdges(tile.tile);
	if (fine_edges >= 16) throw std::runtime_error("Invalid ground boundary mask");
	const auto *mesh = ClippedGroundMesh(&GroundGeometry(tile.tileh,flat_material.has_value(),fine_edges),tile);
	if (!mesh->empty()) capture->scene.instances.push_back({mesh, instance});
}

/** Temporary reference display for artwork review. Counted as missing geometry,
 * never accepted by the completed-vanilla release coverage gate. */
static void ReferenceSprite(const SpriteTexture &texture, Vec3 origin, float opacity)
{
	float left = texture.x_offset / static_cast<float>(ZOOM_BASE), top = texture.y_offset / static_cast<float>(ZOOM_BASE);
	float right = left + texture.source_width / static_cast<float>(ZOOM_BASE), bottom = top + texture.source_height / static_cast<float>(ZOOM_BASE);
	auto point = [&](float u, float v) { return origin + Vec3{bottom / 2 - u / 4, bottom / 2 + u / 4, bottom - v}; };
	Vec3 a = point(left, top), b = point(right, top), c = point(right, bottom), d = point(left, bottom);
	Vec3 uv_a = texture.UV(0, 0), uv_b = texture.UV(texture.source_width, 0);
	Vec3 uv_c = texture.UV(texture.source_width, texture.source_height), uv_d = texture.UV(0, texture.source_height);
	capture->scene.TexturedTriangle(a, b, c, uv_a, uv_b, uv_c, opacity, texture.Region());
	capture->scene.TexturedTriangle(a, c, d, uv_a, uv_c, uv_d, opacity, texture.Region());
	++capture->reference_billboards;
}

/** Rotor/shadow artwork lies in a horizontal plane; smoke faces the camera. */
static void PlanarVehicleMaterial(const SpriteTexture &texture, Vec3 origin, bool shadow, bool face_camera)
{
	float left = texture.x_offset / static_cast<float>(ZOOM_BASE), top = texture.y_offset / static_cast<float>(ZOOM_BASE);
	float right = left + texture.source_width / static_cast<float>(ZOOM_BASE), bottom = top + texture.source_height / static_cast<float>(ZOOM_BASE);
	const Camera &camera = capture->camera;
	Vec3 horizontal = camera.Unrotate(Camera::Right()) * (1 / Camera::ART_SCALE);
	Vec3 vertical = camera.Unrotate(Camera::World(camera.Up())) * (-1 / Camera::ART_SCALE);
	auto point = [&](float u, float v) {
		return face_camera ? origin + horizontal * u + vertical * v : origin + Vec3{v * 0.5f - u * 0.25f, v * 0.5f + u * 0.25f, shadow ? 0.04f : 0};
	};
	size_t begin = capture->scene.vertices.size();
	float opacity = shadow ? 0.32f : face_camera ? 0.98f : 1;
	capture->scene.TexturedTriangle(point(left, top), point(right, top), point(right, bottom), texture.UV(0, 0), texture.UV(texture.source_width, 0), texture.UV(texture.source_width, texture.source_height), opacity, texture.Region());
	capture->scene.TexturedTriangle(point(left, top), point(right, bottom), point(left, bottom), texture.UV(0, 0), texture.UV(texture.source_width, texture.source_height), texture.UV(0, texture.source_height), opacity, texture.Region());
	if (shadow) for (size_t i = begin; i < capture->scene.vertices.size(); ++i) capture->scene.vertices[i].surface = SurfaceMode::Shadow;
}

static unsigned checked_water_house = UINT_MAX;
static TileIndex checked_water_tile = INVALID_TILE;
static unsigned checked_water_materials = 0;
static std::set<std::array<uint32_t,10>> checked_water_colours;

void BeginVoxelWaterAnimationCheck(unsigned house)
{
	checked_water_house = house; checked_water_tile = INVALID_TILE;
	checked_water_materials = 0; checked_water_colours.clear();
	Debug(driver,1,"OpenTT3D: observing original animated water palette on voxel house {}",house);
}

static void ObserveVoxelWater(TileIndex tile, unsigned house)
{
	if (checked_water_house != house || capture->diagnostic || capture->parent_culled) return;
	if (checked_water_tile == INVALID_TILE) {
		checked_water_materials = 0;
		for (size_t i = capture->parent_instance_begin; i < capture->parent_instance_end; ++i) {
			checked_water_materials |= VoxelPaletteMask(*capture->scene.instances[i].mesh,245,10);
		}
		if (std::popcount(checked_water_materials) < 2) return;
		checked_water_tile = tile;
	}
	if (tile != checked_water_tile) return;
	auto palette = SnapshotPalette();
	std::array<uint32_t,10> colours{};
	for (unsigned i = 0; i < colours.size(); ++i) if ((checked_water_materials & (1U<<i)) != 0) {
		Colour colour = palette.palette[245+i];
		colours[i] = (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b;
	}
	checked_water_colours.insert(colours);
	if (checked_water_colours.size() >= 5) {
		Debug(driver,1,"OpenTT3D: voxel water palette observation passed: house {} tile {},{}, {} original colour phases across {} emitted animated materials",house,TileX(tile),TileY(tile),checked_water_colours.size(),std::popcount(checked_water_materials));
		checked_water_house = UINT_MAX;
	}
}

static unsigned checked_house_palette = UINT_MAX;
static TileIndex checked_house_palette_tile = INVALID_TILE;
static std::set<std::array<uint32_t,5>> checked_house_crowd_phases;
static std::set<std::array<uint32_t,4>> checked_house_light_phases;

void BeginVoxelHousePaletteCheck(unsigned house)
{
	if (house != 20 && house != 31 && house != 32 && house != 39 && house != 104 && house != 105) throw std::invalid_argument("House palette observation needs original stadium20/32, theatre31, cinema39 or Toyland shop104/105");
	checked_house_palette = house; checked_house_palette_tile = INVALID_TILE;
	checked_house_crowd_phases.clear(); checked_house_light_phases.clear();
	Debug(driver,1,"OpenTT3D: observing original animated palette on voxel house {}",house);
}

void BeginVoxelStadiumPaletteCheck(unsigned house)
{
	if (house != 20 && house != 32) throw std::invalid_argument("Stadium palette observation needs original house20 or32");
	BeginVoxelHousePaletteCheck(house);
}

static void ObserveVoxelHousePalette(TileIndex tile, unsigned house)
{
	if (house != checked_house_palette || capture->diagnostic || capture->parent_culled) return;
	bool crowd_required = house == 20 || house == 32, lights_required = house != 20;
	unsigned light_first = house == 104 ? 239 : house == 105 ? 242 : 241;
	unsigned light_count = house == 104 ? 2 : house == 105 ? 3 : 4;
	unsigned light_phases = house == 104 ? 2 : 4;
	if (checked_house_palette_tile == INVALID_TILE) {
		unsigned emitted = 0;
		for (size_t i = capture->parent_instance_begin; i < capture->parent_instance_end; ++i) emitted |= VoxelPaletteMask(*capture->scene.instances[i].mesh,227,18);
		unsigned required = (crowd_required ? 0x1FU : 0) | (lights_required ? ((1U<<light_count)-1)<<(light_first-227) : 0);
		if ((emitted&required) != required) return;
		checked_house_palette_tile = tile;
	}
	if (tile != checked_house_palette_tile) return;
	auto palette = SnapshotPalette();
	auto rgb = [&](unsigned index) {
		Colour colour = palette.palette[index];
		return (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b;
	};
	if (crowd_required) {
		std::array<uint32_t,5> crowd{};
		for (unsigned i = 0; i < crowd.size(); ++i) crowd[i] = rgb(227+i);
		checked_house_crowd_phases.insert(crowd);
	}
	if (lights_required) {
		std::array<uint32_t,4> score{};
		for (unsigned i = 0; i < light_count; ++i) score[i] = rgb(light_first+i);
		checked_house_light_phases.insert(score);
	}
	if ((!crowd_required || checked_house_crowd_phases.size() >= 5) && (!lights_required || checked_house_light_phases.size() >= light_phases)) {
		if (!crowd_required) {
			Debug(driver,1,"OpenTT3D: voxel house palette observation passed: house {} tile {},{}, {} original light phases across palette entries {}..{}",house,TileX(tile),TileY(tile),checked_house_light_phases.size(),light_first,light_first+light_count-1);
		} else {
			Debug(driver,1,"OpenTT3D: voxel stadium palette observation passed: house {} tile {},{}, {} original crowd phases and {} scoreboard phases",house,TileX(tile),TileY(tile),checked_house_crowd_phases.size(),checked_house_light_phases.size());
		}
		checked_house_palette = UINT_MAX;
	}
}

bool FocusVoxelBuoy()
{
	unsigned state = _settings_game.game_creation.landscape == LandscapeType::Toyland ? 1 : 0;
	if (!HasVoxelAsset("infrastructure",SPR_IMG_BUOY,state)) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsBuoyTile(tile)) continue;
		SpriteID sprite = GetCanalSprite(CF_BUOY,tile);
		if (sprite == 0 || !IsBaseGraphicsSprite(sprite)) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel buoy at {},{}",x,y);
		return true;
	}
	return false;
}

void BeginVoxelBuoyBeaconCheck()
{
	check_buoy_beacon = true; checked_buoy_tile = INVALID_TILE; buoy_beacon_colours.clear(); buoy_foam_colours.clear();
	Debug(driver,1,"OpenTT3D: observing original239/240 beacons and250..254 foam on an actually captured voxel buoy");
}

static unsigned checked_rotor_engine = UINT_MAX;
static uint32_t checked_rotor_vehicle = UINT32_MAX;
static unsigned checked_rotor_states = 0;
static bool checked_rotor_restarted = false;
static unsigned checked_aircraft_contact = UINT_MAX;
static unsigned checked_collector_engine = UINT_MAX;
static uint32_t checked_collector_vehicle = UINT32_MAX;
static unsigned checked_collector_states = 0;
static unsigned checked_support_engine = UINT_MAX, checked_support_states = 0;
static uint32_t checked_support_vehicle = UINT32_MAX;
static unsigned checked_support_corners = 0;
static bool check_support_corners = false;

static std::optional<RailSupportContact> CapturedRailSupport(Vec3 point)
{
	if (point.x < 0 || point.y < 0 || point.x >= Map::MaxX()*16 || point.y >= Map::MaxY()*16) return {};
	auto tile = capture->rail_surfaces.find(TileVirtXY(static_cast<int>(point.x),static_cast<int>(point.y)));
	if (tile == capture->rail_surfaces.end()) return {};
	std::optional<RailSupportContact> result;
	float nearest = 4;
	for (const auto &surface : tile->second) if (auto contact = surface.Contact(point)) {
		float distance = std::abs(contact->smooth-point.z);
		/* A track below an overpass or above a tunnel cannot attract the train
		 * to the wrong deck. Source-replaced tracks contribute no metadata. */
		if (distance < nearest) { nearest = distance; result = contact; }
	}
	return result;
}

static float FitTrainToCapturedRail(unsigned engine, bool loaded, Vec3 &position, float heading)
{
	auto support = VoxelTrainSupportBounds(engine,loaded,heading);
	if (!support || support->front-support->rear < 0.5f) return 0;
	Vec3 along{std::cos(heading),std::sin(heading),0};
	float grade = 0, height = position.z+support->height;
	for (unsigned iteration = 0; iteration < 4; ++iteration) {
		float cosine = 1/std::sqrt(1+grade*grade*Camera::WORLD_Z_SCALE*Camera::WORLD_Z_SCALE);
		Vec3 rear = position+along*(support->rear*cosine), front = position+along*(support->front*cosine);
		rear.z = height+support->rear*cosine*grade; front.z = height+support->front*cosine*grade;
		auto a = CapturedRailSupport(rear), b = CapturedRailSupport(front);
		if (!a || !b) return 0;
		grade = (b->smooth-a->smooth)/((support->front-support->rear)*cosine);
		if (std::abs(grade) > TerrainZ(0.5f)+0.001f) return 0;
		height = std::max(a->stepped-support->rear*cosine*grade,b->stepped-support->front*cosine*grade);
		/* At a grade transition a rigid underframe can span a crest. Keep its
		 * intermediate wheelsets above the same stepped running surface. */
		for (float contact_x : support->contact_x) {
			float x = contact_x*support->length_scale*cosine;
			Vec3 point = position+along*x; point.z = height+x*grade;
			if (auto contact = CapturedRailSupport(point)) height = std::max(height,contact->stepped-x*grade);
		}
	}
	position.z = height-support->height;
	return grade;
}

void BeginVoxelTrainSupportCheck(unsigned engine, bool corners)
{
	if (engine >= 116 || !VoxelVehicleState(engine,false)) throw std::invalid_argument("Train support observation requires an original voxel train");
	checked_support_engine = engine; checked_support_vehicle = UINT32_MAX; checked_support_states = 0;
	checked_support_corners = 0; check_support_corners = corners;
}

static void CheckTrainSupport(const Vehicle &vehicle, const MeshInstance &instance, float heading, float grade, bool loaded)
{
	if (capture->diagnostic || checked_support_engine != vehicle.engine_type.base()) return;
	if (checked_support_vehicle == UINT32_MAX) checked_support_vehicle = vehicle.index.base();
	if (checked_support_vehicle != vehicle.index.base()) return;
	auto support = VoxelTrainSupportBounds(vehicle.engine_type.base(),loaded,heading);
	if (!support) return;
	unsigned samples = 0;
	float minimum = INFINITY, maximum = -INFINITY;
	for (const auto &vertex : *instance.mesh) if (vertex.position.z == support->height) {
		Vec3 point = ResolveInstanceVertex(vertex,instance.data).position;
		if (auto contact = CapturedRailSupport(point)) {
			float gap = point.z-contact->stepped;
			minimum = std::min(minimum,gap); maximum = std::max(maximum,gap); ++samples;
		}
	}
	if (samples == 0) return;
	if (minimum < -0.126f || ((std::abs(grade) < 0.0001f || std::abs(grade) >= TerrainZ(0.5f)-0.001f) && maximum > 0.251f)) {
		throw std::runtime_error(fmt::format("Train support engine {} vehicle {} at {},{},{} grade {} has wheel gaps {}..{}",checked_support_engine,checked_support_vehicle,vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,grade,minimum,maximum));
	}
	unsigned state = grade > TerrainZ(0.5f)-0.01f ? 4U : grade < -TerrainZ(0.5f)+0.01f ? 8U : 0U;
	if (std::abs(grade) < 0.0001f && IsValidTile(vehicle.tile)) {
		state |= IsRailStationTile(vehicle.tile) ? 1U : IsTileType(vehicle.tile,MP_RAILWAY) ? 2U :
			IsBridgeTile(vehicle.tile) ? 16U : IsTunnelTile(vehicle.tile) ? 32U : 0U;
	}
	if ((checked_support_states | state) != checked_support_states) Debug(driver,1,"OpenTT3D: train support engine {} vehicle {} at {},{},{} grade {} gap {}..{} states {}",checked_support_engine,checked_support_vehicle,vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,grade,minimum,maximum,state);
	checked_support_states |= state;
	if (IsValidTile(vehicle.tile) && IsPlainRailTile(vehicle.tile)) {
		unsigned corners = Train::From(&vehicle)->track & GetTrackBits(vehicle.tile) & (TRACK_BIT_UPPER | TRACK_BIT_LOWER | TRACK_BIT_LEFT | TRACK_BIT_RIGHT);
		if ((checked_support_corners | corners) != checked_support_corners) {
			Debug(driver,1,"OpenTT3D: train corner support engine {} vehicle {} at {},{} tracks {} heading {} gap {}..{} samples {}",checked_support_engine,checked_support_vehicle,vehicle.x_pos,vehicle.y_pos,corners,heading,minimum,maximum,samples);
		}
		checked_support_corners |= corners;
	}
	if (checked_support_states == 63 && (!check_support_corners || checked_support_corners == (TRACK_BIT_UPPER | TRACK_BIT_LOWER | TRACK_BIT_LEFT | TRACK_BIT_RIGHT))) {
		Debug(driver,1,"OpenTT3D: voxel train support observation passed: engine {} vehicle {}, station/flat/ascending/descending/bridge/tunnel support and original vehicle state",checked_support_engine,checked_support_vehicle);
		if (check_support_corners) Debug(driver,1,"OpenTT3D: voxel train corner observation passed: engine {} vehicle {}, all four original corner tracks with actual smoothed headings and captured support",checked_support_engine,checked_support_vehicle);
		checked_support_engine = UINT_MAX;
	}
}

static std::optional<float> CapturedContactWireHeight(Vec3 point)
{
	int x = static_cast<int>(std::floor(point.x/16)), y = static_cast<int>(std::floor(point.y/16));
	float nearest = INFINITY;
	std::optional<float> height;
	for (int ty = y-1; ty <= y+1; ++ty) for (int tx = x-1; tx <= x+1; ++tx) {
		if (tx < 0 || ty < 0 || tx >= static_cast<int>(Map::MaxX()) || ty >= static_cast<int>(Map::MaxY())) continue;
		auto found = capture->contact_wires.find(TileXY(tx,ty));
		if (found == capture->contact_wires.end()) continue;
		for (const auto &wire : found->second) {
			auto [contact,distance] = wire.Nearest(point);
			/* A collector shoe spans the running route; a nearby crossing route
			 * or the wire on an overpass must not pull it onto a different deck. */
			if (distance > 1.5f*1.5f || std::abs(contact.z-point.z) >= 4) continue;
			float score = distance+(contact.z-point.z)*(contact.z-point.z)*0.01f;
			if (score >= nearest) continue;
			nearest = score; height = contact.z;
		}
	}
	return height;
}

void BeginVoxelTrainCollectorCheck(unsigned engine)
{
	if (!VoxelTrainCollectorMount(engine,0,0)) throw std::invalid_argument("Collector observation needs an original bound electric locomotive");
	checked_collector_engine = engine; checked_collector_vehicle = UINT32_MAX; checked_collector_states = 0;
}

void BeginVoxelAircraftContactCheck(unsigned engine)
{
	if (engine < 215 || engine > 255 || !VoxelVehicleState(engine,false)) throw std::invalid_argument("Aircraft contact observation needs a bound aircraft in its proper climate");
	checked_aircraft_contact = engine;
}

/** Diagnostic only: every authored skid/wheel corner must land on an actual
 * captured horizontal deck triangle, including joins between industry owners. */
static unsigned CheckElevatedAircraftContacts(float height)
{
	std::set<std::pair<float,float>> contacts;
	for (size_t i = capture->parent_instance_begin; i < capture->parent_instance_end; ++i) {
		const auto &instance = capture->scene.instances[i];
		for (const auto &vertex : *instance.mesh) {
			Vec3 point = ResolveInstanceVertex(vertex,instance.data).position;
			if (std::abs(point.z-height) < 0.001f) contacts.emplace(point.x,point.y);
		}
	}
	unsigned count = contacts.size();
	for (size_t i = 0; i < capture->parent_instance_begin && !contacts.empty(); ++i) {
		const auto &instance = capture->scene.instances[i];
		if ((instance.data.ObjectId()&TILE_PICK_ID) == 0) continue;
		for (size_t v = 0; v < instance.mesh->size() && !contacts.empty(); v += 3) {
			Vec3 a = ResolveInstanceVertex((*instance.mesh)[v],instance.data).position;
			Vec3 b = ResolveInstanceVertex((*instance.mesh)[v+1],instance.data).position;
			Vec3 c = ResolveInstanceVertex((*instance.mesh)[v+2],instance.data).position;
			if (std::abs(a.z-height) >= 0.001f || std::abs(b.z-height) >= 0.001f || std::abs(c.z-height) >= 0.001f) continue;
			auto cross = [](Vec3 a,Vec3 b,Vec3 p) { return (b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x); };
			float area = cross(a,b,c);
			if (area <= 0.000001f) continue;
			std::erase_if(contacts,[&](const auto &point) {
				Vec3 p{point.first,point.second,height};
				return cross(a,b,p) >= -0.0001f && cross(b,c,p) >= -0.0001f && cross(c,a,p) >= -0.0001f;
			});
		}
	}
	if (count == 0 || !contacts.empty()) throw std::runtime_error(fmt::format("Elevated aircraft support has {} of {} corners outside the captured deck",contacts.size(),count));
	return count;
}

void BeginVoxelHelicopterRotorCheck(unsigned engine)
{
	if (engine < 253 || engine > 255 || !VoxelVehicleState(engine,false)) throw std::invalid_argument("Rotor observation needs an original voxel helicopter in its proper climate");
	checked_rotor_engine = engine; checked_rotor_vehicle = UINT32_MAX; checked_rotor_states = 0;
	checked_rotor_restarted = false;
	Debug(driver,1,"OpenTT3D: observing original stopped/moving rotor states on voxel helicopter {}",engine);
}

void CaptureParent(SpriteID image, PaletteID palette, int x, int y, int z, const SpriteBounds &bounds, bool transparent, const SubSprite *sub)
{
	if (!capture) return;
	uint32_t id = capture->tile != nullptr && IsValidTile(capture->tile->tile) ? TILE_PICK_ID | capture->tile->tile.base() : 0;
	if (capture->vehicle != nullptr && !capture->vehicle->vehstatus.Any({VehState::Unclickable,VehState::Shadow})) id = capture->vehicle->index.base()+1;
	ObjectTag tag{capture->scene.vertices.size(),id};
	capture->parent_id = tag.id;
	Vec3 source_origin{static_cast<float>(x + bounds.origin.x + bounds.offset.x),
		static_cast<float>(y + bounds.origin.y + bounds.offset.y), static_cast<float>(z + bounds.origin.z + bounds.offset.z)};
	/* Upstream sprite callbacks can place a child above the tile/vehicle datum.
	 * Raise the supporting datum, preserving smoke, roofs and rotor offsets. */
	Vec3 origin = source_origin;
	if (capture->vehicle != nullptr) origin.z += RenderVehicleZ(*capture->vehicle)-capture->vehicle->z_pos;
	else if (capture->tile != nullptr) origin.z += TerrainZ(capture->tile->z)-capture->tile->z;
	else origin.z += TerrainZ(z)-z;
	if (capture->tile != nullptr && IsTileType(capture->tile->tile,MP_TREES) &&
		(image&SPRITE_MASK) >= 1576 && (image&SPRITE_MASK) <= 2009 && IsBaseGraphicsSprite(image)) {
		/* The original combined sprite uses the tile's middle height for every
		 * tree. A real 3D trunk must instead meet the slope at its own XY root. */
		const auto &tile = *capture->tile;
		origin.z = TerrainZ(tile.z)+MakeTileSurface(tile.tileh).Height(origin.x-tile.x,origin.y-tile.y);
	}
	capture->parent_origin = origin; capture->parent_bounds = bounds; capture->have_parent = true;
	capture->parent_sprite = image&SPRITE_MASK;
	capture->parent_mesh_begin = capture->parent_mesh_end = capture->scene.vertices.size();
	capture->parent_instance_begin = capture->parent_instance_end = capture->scene.instances.size();
	capture->parent_culled = false;
	capture->industry_next_child = 0;
	capture->industry_children_visible = true;
	capture->parent_left = capture->parent_top = 0;
	capture->parent_offsets_pending = false;
	if ((image & SPRITE_MASK) == SPR_EMPTY_BOUNDING_BOX) return;
	if (capture->tile != nullptr && IsBuoyTile(capture->tile->tile) && (image&SPRITE_MASK) == GetCanalSprite(CF_BUOY,capture->tile->tile) && sub == nullptr && IsBaseGraphicsSprite(image) && HasVoxelAsset("infrastructure",SPR_IMG_BUOY,_settings_game.game_creation.landscape == LandscapeType::Toyland ? 1 : 0)) {
		const TileInfo &tile = *capture->tile;
		unsigned state = _settings_game.game_creation.landscape == LandscapeType::Toyland ? 1 : 0;
		DrawVoxelAsset(capture->scene,"infrastructure",SPR_IMG_BUOY,state,{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)},palette,transparent ? 0.38f : 1);
		capture->parent_instance_end = capture->scene.instances.size();
		capture->parent_culled = capture->parent_instance_begin == capture->parent_instance_end;
		if (capture->parent_culled) return;
		if (!capture->diagnostic) {
			static bool reported = false;
			if (!reported) { Debug(driver,1,"OpenTT3D: live voxel buoy captured at {},{} with original water ground",TileX(tile.tile),TileY(tile.tile)); reported = true; }
			if (check_buoy_beacon && (VoxelPaletteMask(*capture->scene.instances.back().mesh,239,16)&0xF803U) == 0xF803U) {
				if (checked_buoy_tile == INVALID_TILE) checked_buoy_tile = tile.tile;
				if (checked_buoy_tile == tile.tile) {
					auto colours = SnapshotPalette();
					auto rgb = [&](unsigned index) { Colour colour = colours.palette[index]; return (static_cast<uint32_t>(colour.r)<<16)|(static_cast<uint32_t>(colour.g)<<8)|colour.b; };
					buoy_beacon_colours.insert({rgb(239),rgb(240)});
					buoy_foam_colours.insert({rgb(250),rgb(251),rgb(252),rgb(253),rgb(254)});
					if (buoy_beacon_colours.size() >= 2 && buoy_foam_colours.size() >= 5) {
						Debug(driver,1,"OpenTT3D: voxel buoy beacon observation passed: tile {},{}, {} original beacon phases and {} foam phases",TileX(tile.tile),TileY(tile.tile),buoy_beacon_colours.size(),buoy_foam_colours.size());
						check_buoy_beacon = false;
					}
				}
			}
		}
		return;
	}
	if (const auto *bridge = CurrentBridgeCapture(); bridge != nullptr && DrawCapturedBridge(capture->scene,*bridge,image,palette,source_origin,TextureZoom(origin),transparent,sub)) {
		if ((bridge->shape.role == BridgeRole::Ramp || bridge->shape.role == BridgeRole::Deck) && !bridge->custom && bridge->rail != INVALID_RAILTYPE && SupportedRailType(bridge->rail)) {
			Vec3 floor = bridge->origin;
			floor.z = TerrainZ(floor.z);
			Slope slope = SLOPE_FLAT;
			if (bridge->shape.sloped) { floor.z -= TerrainZ(TILE_HEIGHT); slope = InclinedSlope(static_cast<DiagDirection>(bridge->shape.ramp_direction)); }
			TrackBits tracks = bridge->shape.along_y ? TRACK_BIT_Y : TRACK_BIT_X;
			size_t first = capture->scene.instances.size();
			DrawRailTracks(capture->scene,capture->camera,floor,slope,bridge->rail,tracks,bridge->reserved ? tracks : TRACK_BIT_NONE);
			for (size_t i = first; i < capture->scene.instances.size(); ++i) if (transparent) capture->scene.instances[i].data.origin_opacity[3] = 0.38f;
		}
		capture->parent_instance_end = capture->scene.instances.size();
		capture->parent_culled = capture->parent_instance_begin == capture->parent_instance_end;
		if (capture->parent_culled) return;
		++capture->bridge_parts;
		SpriteTexture texture = Textures().Get(image,palette,TextureZoom(origin),bridge->shape.role != BridgeRole::Surface);
		capture->parent_left = texture.x_offset; capture->parent_top = texture.y_offset;
		return;
	}
	if (capture->vehicle != nullptr) {
		const Vehicle &vehicle = *capture->vehicle;
		bool shadow = vehicle.vehstatus.Test(VehState::Shadow);
		bool rotor = vehicle.type == VEH_AIRCRAFT && vehicle.subtype == AIR_ROTOR;
		if (rotor && sub == nullptr && !transparent && VoxelVehicleState(vehicle.engine_type.base(),false)) {
			const Vehicle &body = *vehicle.First();
			bool original = body.type == VEH_AIRCRAFT && body.subtype == AIR_HELICOPTER;
			for (unsigned direction = 0; direction < 8 && original; ++direction) {
				VehicleSpriteSeq sequence;
				body.GetImage(static_cast<Direction>(direction),EIT_ON_MAP,&sequence);
				original = sequence.count == 1 && IsBaseGraphicsSprite(sequence.seq[0].sprite);
			}
			/* Share the body's current smoothed transform so the independent rotor
			 * cannot trail its cabin on turns, landings or capture-order changes. */
			Vec3 rotor_origin = SmoothVehiclePose(body).position+Vec3{0,0,ROTOR_Z_OFFSET-1};
			if (original && DrawVoxelHelicopterRotor(capture->scene,image,rotor_origin,palette)) {
				capture->parent_instance_end = capture->scene.instances.size();
				capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin;
				if (!capture->diagnostic && !capture->parent_culled && checked_rotor_engine == body.engine_type.base()) {
					if (checked_rotor_vehicle == UINT32_MAX) checked_rotor_vehicle = body.index.base();
					if (checked_rotor_vehicle == body.index.base()) {
						if (vehicle.x_pos != body.x_pos || vehicle.y_pos != body.y_pos || vehicle.z_pos-body.z_pos != ROTOR_Z_OFFSET || tag.id != 0) {
							throw std::runtime_error("Voxel rotor observation: original attachment or unclickable ownership changed");
						}
						unsigned state = (image&SPRITE_MASK)-SPR_ROTOR_STOPPED;
						if ((checked_rotor_states & (1U<<state)) == 0) Debug(driver,1,"OpenTT3D: voxel helicopter rotor engine {} vehicle {} captured original state {} at {},{},{}",checked_rotor_engine,checked_rotor_vehicle,state,body.x_pos,body.y_pos,body.z_pos);
						if (state != 0 && (checked_rotor_states & 1U) != 0) checked_rotor_restarted = true;
						checked_rotor_states |= 1U<<state;
						if (checked_rotor_states == 15 && checked_rotor_restarted) {
							Debug(driver,1,"OpenTT3D: voxel helicopter rotor observation passed: engine {} vehicle {}, all four original states and stopped-to-running transition, body-relative motion and unclickable ownership",checked_rotor_engine,checked_rotor_vehicle);
							checked_rotor_engine = UINT_MAX;
						}
					}
				}
				return;
			}
		}
		if (vehicle.type == VEH_EFFECT && sub == nullptr && DrawVoxelEffect(capture->scene,image,origin,palette,transparent ? 0.38f : 1)) {
			capture->parent_instance_end = capture->scene.instances.size();
			capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin;
			if (!capture->diagnostic && !capture->parent_culled) {
				const auto &effect = *EffectVehicle::From(&vehicle);
				Debug(driver,5,"OpenTT3D: voxel effect frame {} vehicle {} type {} sprite {} climate {} animation {},{} progress {} raw {},{},{} origin {:.9g},{:.9g},{:.9g} opacity {:.9g} pick {}",
					capture_frame,vehicle.index.base(),vehicle.subtype,image&SPRITE_MASK,to_underlying(_settings_game.game_creation.landscape),effect.animation_state,effect.animation_substate,vehicle.progress,
					vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,origin.x,origin.y,origin.z,transparent ? 0.38f : 1,tag.id);
			}
			return;
		}
		if (shadow || rotor || vehicle.type == VEH_EFFECT) {
			SpriteTexture texture = Textures().Get(image, palette, TextureZoom(origin));
			PlanarVehicleMaterial(texture, origin, shadow, vehicle.type == VEH_EFFECT);
			capture->parent_mesh_end = capture->scene.vertices.size();
			return;
		}
		if (vehicle.type <= VEH_AIRCRAFT && vehicle.engine_type.base() < 256 && IsBaseGraphicsSprite(image)) {
			VehiclePose pose = SmoothVehiclePose(vehicle);
			float heading = (5.0f - pose.heading * 2) * std::numbers::pi_v<float> / 4;
			bool reversed = false;
			if (vehicle.type == VEH_TRAIN) {
				const Train &train = *Train::From(&vehicle);
				bool rear = train.IsRearDualheaded();
				reversed = rear != train.flags.Test(VehicleRailFlag::Flipped);
				if (reversed) heading += std::numbers::pi_v<float>;
			}
			Vec3 position = pose.position;
			bool loaded = vehicle.cargo_cap != 0 && vehicle.cargo.StoredCount() >= vehicle.cargo_cap / 2U;
			/* Original airport motion places the aircraft anchor one height unit
			 * above its landing surface. Authored wheels/skids have a zero-height
			 * contact plane, so remove that sprite-anchor offset from both parts. */
			if (vehicle.type == VEH_AIRCRAFT && VoxelVehicleState(vehicle.engine_type.base(),loaded)) position.z -= 1;
			std::array<SpriteID, 8> references{};
			bool supported = true;
			for (unsigned direction = 0; direction < 8; ++direction) {
				VehicleSpriteSeq sequence;
				vehicle.GetImage(static_cast<Direction>((direction + (reversed ? 4 : 0)) % 8), EIT_ON_MAP, &sequence);
				if (sequence.count != 1 || !IsBaseGraphicsSprite(sequence.seq[0].sprite)) { supported = false; break; }
				references[direction] = sequence.seq[0].sprite;
			}
			float grade = supported && vehicle.type == VEH_TRAIN ? FitTrainToCapturedRail(vehicle.engine_type.base(),loaded,position,heading) : 0;
			if (supported && DrawAuthoredVehicle(capture->scene, vehicle.engine_type.base(), loaded, position, heading, palette, TextureZoom(position), 1, &references, grade)) {
				if (vehicle.type == VEH_TRAIN && capture->scene.instances.size() > capture->parent_instance_begin) CheckTrainSupport(vehicle,capture->scene.instances[capture->parent_instance_begin],heading,grade,loaded);
				if (vehicle.type == VEH_TRAIN && VoxelTrainCollectorMount(vehicle.engine_type.base(),0,heading)) {
					std::array<float,2> contacts{10,10};
					unsigned observed_states = 0;
					for (unsigned part = 0; part < contacts.size(); ++part) for (unsigned iteration = 0; iteration < 3; ++iteration) {
						std::optional<Vec3> mount;
						try {
							mount = VoxelTrainCollectorMount(vehicle.engine_type.base(),part,heading,grade,contacts[part]);
						} catch (const std::invalid_argument &error) {
							throw std::invalid_argument(fmt::format("{}; engine {} vehicle {} part {} iteration {} original {},{},{} rendered {},{},{} frame_seconds {}",error.what(),vehicle.engine_type.base(),vehicle.index.base(),part,iteration,vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,position.x,position.y,position.z,frame_seconds));
						}
						if (!mount) continue;
						if (auto height = TrainTunnelContactHeight(vehicle,position+*mount)) {
							contacts[part] = *height-position.z;
							observed_states |= contacts[part] > 9.99f ? 1U : contacts[part] < 7.56f ? 4U : 2U;
						} else if (auto height = CapturedContactWireHeight(position+*mount)) {
							contacts[part] = *height-position.z;
							observed_states |= 1U;
						}
					}
					size_t first = capture->scene.instances.size();
					unsigned drawn = DrawVoxelTrainCollectors(capture->scene,vehicle.engine_type.base(),position,heading,palette,contacts,grade);
					if (drawn != 0 && !capture->diagnostic && checked_collector_engine == vehicle.engine_type.base()) {
						if (checked_collector_vehicle == UINT32_MAX) checked_collector_vehicle = vehicle.index.base();
						if (checked_collector_vehicle == vehicle.index.base()) {
							for (size_t i = first; i < capture->scene.instances.size(); ++i) {
								const auto &instance = capture->scene.instances[i];
								float top = -INFINITY;
								for (const auto &vertex : *instance.mesh) top = std::max(top,vertex.position.z);
								Vec3 low{INFINITY,INFINITY,top},high{-INFINITY,-INFINITY,top};
								for (const auto &vertex : *instance.mesh) if (vertex.position.z == top) {
									low.x = std::min(low.x,vertex.position.x); low.y = std::min(low.y,vertex.position.y);
									high.x = std::max(high.x,vertex.position.x); high.y = std::max(high.y,vertex.position.y);
								}
								Vertex shoe{}; shoe.position = (low+high)*0.5f; shoe.normal = {0,0,1};
								float contact = ResolveInstanceVertex(shoe,instance.data).position.z;
								bool matched = std::ranges::any_of(contacts,[&](float height) { return std::abs(contact-position.z-height) < 0.0001f; });
								if (!matched || tag.id != vehicle.index.base()+1) throw std::runtime_error("Voxel collector lost wire contact or vehicle ownership");
							}
							if ((checked_collector_states | observed_states) != checked_collector_states) Debug(driver,1,"OpenTT3D: voxel train collector engine {} vehicle {} observed contact heights {},{} states {}",checked_collector_engine,checked_collector_vehicle,contacts[0],contacts[1],observed_states);
							checked_collector_states |= observed_states;
							if (checked_collector_states == 7) {
								Debug(driver,1,"OpenTT3D: voxel train collector observation passed: engine {} vehicle {}, surface/portal/tunnel wire contact and original ownership",checked_collector_engine,checked_collector_vehicle);
								checked_collector_engine = UINT_MAX;
							}
						}
					}
				}
				capture->parent_instance_end = capture->scene.instances.size();
				capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin;
				if (!capture->parent_culled) ++capture->modelled_vehicles;
				if (!capture->parent_culled && !capture->diagnostic && vehicle.index.base() == checked_depot_vehicle && !vehicle.IsInDepot()) {
					if (checked_depot_phase == 0) checked_depot_phase = 1;
					else if (checked_depot_phase == 3) {
						Debug(driver,1,"OpenTT3D: voxel depot traversal verification passed: vehicle {}, depot {},{}, original visible/inside/visible states and actual geometry captured",checked_depot_vehicle,TileX(checked_depot_tile),TileY(checked_depot_tile));
						checked_depot_vehicle = UINT32_MAX;
					}
				}
				if (auto state = VoxelVehicleState(vehicle.engine_type.base(),loaded); !capture->parent_culled && !capture->diagnostic && state) {
					/* Read the original stopped breakdown emitter alongside its effect.
					 * This never assigns reliability, countdowns, effects or RNG state. */
					if (vehicle.type == VEH_TRAIN && vehicle.breakdown_ctr == 1) Debug(driver,5,"OpenTT3D: breakdown train frame {} vehicle {} engine {} delay {} raw {},{},{} origin {:.9g},{:.9g},{:.9g}",
						capture_frame,vehicle.index.base(),vehicle.engine_type.base(),vehicle.breakdown_delay,vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,position.x,position.y,position.z);
					/* Record the emitted smoothed pose, not just the simulation's axial
					 * waypoint. This never advances aircraft state or animation. */
					if (vehicle.type == VEH_AIRCRAFT) Debug(driver,5,"OpenTT3D: clearance aircraft frame {} vehicle {} engine {} state {} raw {},{},{} direction {} pose {:.9g},{:.9g},{:.9g},{:.9g}",
						capture_frame,vehicle.index.base(),vehicle.engine_type.base(),*state,vehicle.x_pos,vehicle.y_pos,vehicle.z_pos,to_underlying(vehicle.direction),position.x,position.y,position.z,heading);
					if (checked_aircraft_contact == vehicle.engine_type.base() && vehicle.cur_speed == 0 && IsValidTile(vehicle.tile)) {
						const auto *airport = Station::GetIfValid(Aircraft::From(&vehicle)->targetairport);
						bool oilrig = airport != nullptr && airport->airport.type == AT_OILRIG;
						bool on_airport = oilrig || (IsTileType(vehicle.tile,MP_STATION) && IsAirport(vehicle.tile));
						int source_ground = GetSlopePixelZ(vehicle.x_pos,vehicle.y_pos), deck = airport == nullptr ? 0 : airport->airport.GetFTA()->delta_z;
						float ground = TerrainZ(source_ground)+deck;
						if (on_airport && vehicle.z_pos == source_ground+deck+1 && std::abs(position.z-ground) < 0.001f) {
							float lowest = INFINITY;
							for (size_t i = capture->parent_instance_begin; i < capture->parent_instance_end; ++i) {
								const auto &instance = capture->scene.instances[i];
								for (const auto &vertex : *instance.mesh) lowest = std::min(lowest,vertex.position.z+instance.data.origin_opacity[2]);
							}
							if (std::abs(lowest-ground) >= 0.001f) throw std::runtime_error("Authored aircraft wheels/skids do not meet the actual airport surface");
							if (oilrig) Debug(driver,1,"OpenTT3D: oil-rig helicopter deck contact passed: {} actual support corners on captured industry surfaces at height {}",CheckElevatedAircraftContacts(ground),ground);
							if (airport != nullptr && airport->airport.type == AT_HELIPORT && HasVoxelAirport(44,0)) Debug(driver,1,"OpenTT3D: heliport helicopter deck contact passed: {} actual support corners on captured airport surfaces at height {}",CheckElevatedAircraftContacts(ground),ground);
							Debug(driver,1,"OpenTT3D: voxel aircraft ground contact passed: engine {} vehicle {}, authored support plane {} matches actual airport surface",checked_aircraft_contact,vehicle.index.base(),lowest);
							checked_aircraft_contact = UINT_MAX;
						}
					}
					static std::set<std::pair<unsigned,bool>> reported;
					if (reported.emplace(vehicle.engine_type.base(),loaded).second) {
						Debug(driver,1,"OpenTT3D: live voxel vehicle engine {} cargo {} captured as vehicle {}",vehicle.engine_type.base(),loaded ? 1 : 0,vehicle.index.base());
						Debug(driver,1,"OpenTT3D: live voxel vehicle engine {} climate {} binding state {}",vehicle.engine_type.base(),to_underlying(_settings_game.game_creation.landscape),*state);
					}
					if (checked_cargo_engine == vehicle.engine_type.base() && vehicle.cargo_cap != 0) {
						if (checked_cargo_vehicle == UINT32_MAX) checked_cargo_vehicle = vehicle.index.base();
						if (checked_cargo_vehicle == vehicle.index.base()) {
							if (checked_cargo_capacity != vehicle.cargo_cap) {
								checked_cargo_capacity = vehicle.cargo_cap;
								checked_cargo_states = 0;
							}
							unsigned amount = vehicle.cargo.StoredCount();
							unsigned state = amount == 0 && !loaded ? 1U : amount == vehicle.cargo_cap && loaded ? 2U : 0U;
							if (state != 0 && (checked_cargo_states & state) == 0) Debug(driver,1,"OpenTT3D: voxel cargo engine {} vehicle {} observed {}/{} with binding {}",checked_cargo_engine,checked_cargo_vehicle,amount,vehicle.cargo_cap,loaded ? 1 : 0);
							checked_cargo_states |= state;
							if (checked_cargo_states == 3) {
								Debug(driver,1,"OpenTT3D: voxel vehicle cargo verification passed: engine {}, vehicle {}, actual empty 0/{} and full {}/{} bindings",checked_cargo_engine,checked_cargo_vehicle,checked_cargo_capacity,checked_cargo_capacity,checked_cargo_capacity);
								checked_cargo_engine = UINT_MAX;
							}
						}
					}
				}
				return;
			}
		}
	}
	bool house_body=false;
	if (capture->tile!=nullptr && IsTileType(capture->tile->tile,MP_HOUSE)) {
		unsigned house=GetHouseType(capture->tile->tile);
		unsigned index=house*16+TileHash2Bit(capture->tile->x,capture->tile->y)*4+GetHouseBuildingStage(capture->tile->tile);
		auto drawing=GetTownDrawTileData();
		house_body=index<drawing.size() && (drawing[index].building.sprite & SPRITE_MASK)==(image & SPRITE_MASK) && IsBaseGraphicsSprite(image);
	}
	bool tree=(image&SPRITE_MASK)>=1576 && (image&SPRITE_MASK)<=2009 && IsBaseGraphicsSprite(image);
	unsigned tree_stage = tree ? ((image & SPRITE_MASK) - 1576) % 7 : 0;
	if (tree && UseVoxelTrees() && capture->tile != nullptr && IsTileType(capture->tile->tile,MP_TREES) && HasVoxelTree(image)) {
		unsigned base = (image&SPRITE_MASK)-tree_stage;
		DrawVoxelAsset(capture->scene,"trees",base,tree_stage,origin,palette&PALETTE_MASK,transparent ? 0.38f : 1);
		const auto &tile = *capture->tile;
		Vec3 tile_offset = origin-Vec3{static_cast<float>(tile.x),static_cast<float>(tile.y),TerrainZ(tile.z)};
		for (size_t i = capture->parent_instance_begin; i < capture->scene.instances.size(); ++i) {
			/* Preserve the rooted surface silhouette while keeping underground
			 * bark out of the original tunnel's clear interior. */
			capture->scene.instances[i].mesh = ClippedGroundMesh(capture->scene.instances[i].mesh,tile,tile_offset);
		}
		capture->scene.instances.erase(std::remove_if(capture->scene.instances.begin()+capture->parent_instance_begin,capture->scene.instances.end(),
			[](const auto &instance) { return instance.mesh->empty(); }),capture->scene.instances.end());
		capture->parent_instance_end = capture->scene.instances.size();
		capture->parent_culled = capture->parent_instance_begin == capture->parent_instance_end;
		/* The voxel's original palette is independent of the source RGBA chart.
		 * Resolve sprite framing only if a later relative child actually needs it. */
		capture->parent_offsets_pending = true; capture->parent_palette = palette;
		if (!capture->parent_culled && !capture->diagnostic && capture->tile != nullptr) {
			static std::array<bool,2009-1576+1> reported{};
			unsigned index = (image&SPRITE_MASK)-1576;
			if (!reported[index]) {
				reported[index] = true;
				Debug(driver,1,"OpenTT3D: live voxel tree {} stage {} captured at {},{}",base,tree_stage,TileX(capture->tile->tile),TileY(capture->tile->tile));
			}
		}
		return;
	}
	/* Dying leaves are deliberately absent in the source. Opaque dilation would
	 * paint those gaps back in and turn sparse trees into solid coloured shells. */
	bool fading_tree = tree && (tree_stage == 4 || tree_stage == 5);
	bool opaque_house = house_body && GetHouseBuildingStage(capture->tile->tile) == TOWN_HOUSE_COMPLETED;
	bool industry = capture->tile != nullptr && IsTileType(capture->tile->tile, MP_INDUSTRY) && IsBaseGraphicsSprite(image) && HasAuthoredIndustry(GetIndustryGfx(capture->tile->tile), image);
	float pixel_scale = PixelScaleAt(origin);
	SpriteTexture texture = Textures().Get(image, palette, TextureZoom(pixel_scale), opaque_house || industry || (tree && !fading_tree && !TreeHasComponentMaterials(image)));
	capture->parent_left = texture.x_offset; capture->parent_top = texture.y_offset;
	if (industry) {
		Vec3 root{static_cast<float>(capture->tile->x), static_cast<float>(capture->tile->y), TerrainZ(capture->tile->z)};
		if (DrawAuthoredIndustry(capture->scene, GetIndustryGfx(capture->tile->tile), image, texture, root, origin, transparent ? 0.38f : 1, pixel_scale)) {
			capture->parent_culled = capture->scene.instances.size() == capture->parent_instance_begin;
			if (auto state = VoxelIndustryState(GetIndustryGfx(capture->tile->tile),image); !capture->parent_culled && !capture->diagnostic && state) {
				unsigned graphics = GetIndustryGfx(capture->tile->tile), stage = GetIndustryConstructionStage(capture->tile->tile);
				unsigned climate = to_underlying(_settings_game.game_creation.landscape);
				static std::set<std::tuple<unsigned,unsigned,unsigned>> reported;
				if (reported.emplace(graphics,stage,climate).second) {
					Debug(driver,1,"OpenTT3D: live voxel industry {} construction stage {} captured at {},{}",graphics,stage,TileX(capture->tile->tile),TileY(capture->tile->tile));
					Debug(driver,1,"OpenTT3D: industry voxel climate selection graphics {} stage {} layer body climate {} binding {}",graphics,stage,climate,*state);
				}
				ObserveVoxelPlasticFountain(capture->tile->tile,graphics);
				if (!industry_palette_checks.empty()) ObserveVoxelIndustryPalette(capture->tile->tile,graphics,capture->parent_instance_begin,false);
				if (check_forest_cycle && (graphics == checked_forest_base || graphics == checked_forest_base+1)) {
					TileIndex tile = capture->tile->tile;
					IndustryID industry = GetIndustryIndex(tile);
					auto found = forest_cycles.find(tile);
					if (found != forest_cycles.end() && found->second.first != industry) {
						forest_cycles.erase(found); found = forest_cycles.end();
					}
					if (found == forest_cycles.end() && graphics == checked_forest_base && stage == 3 && forest_cycles.size() < 128) {
						found = forest_cycles.emplace(tile,std::pair{industry,0U}).first;
					}
					if (found != forest_cycles.end()) {
						unsigned &phase = found->second.second;
						/* Dispatch changes16/129/135 to completed17/130/136; the next
						 * original tile loop restores the growing type and construction. */
						if ((phase == 0 && graphics == checked_forest_base+1 && stage == 3) ||
							(phase >= 1 && phase <= 4 && graphics == checked_forest_base && stage == phase-1)) {
							++phase;
							Debug(driver,1,"OpenTT3D: forest cycle tile {},{} industry {} phase {} graphics {} stage {} captured",TileX(tile),TileY(tile),industry.base(),phase,graphics,stage);
							if (phase == 5) {
								Debug(driver,1,"OpenTT3D: voxel forest cycle verification passed: one unchanged industry tile {},{} captured mature/{}/seedling/young/half-grown/mature",TileX(tile),TileY(tile),checked_forest_base == 135 ? "bare-sockets" : checked_forest_base == 129 ? "bare-sticks" : "logs");
								check_forest_cycle = false; forest_cycles.clear();
							}
						}
					}
				}
				auto found = industry_animation_checks.find(graphics);
				if (found != industry_animation_checks.end() && !found->second.complete) {
					auto &check = found->second;
					TileIndex tile = capture->tile->tile;
					if (check.tile == UINT32_MAX) check.tile = tile.base();
					if (check.tile == tile.base() && (check.expected & (1U<<*state)) != 0) {
						if ((check.seen & (1U<<*state)) == 0) Debug(driver,1,"OpenTT3D: industry {} animation source {} state {} captured at {},{}",graphics,image&SPRITE_MASK,*state,TileX(tile),TileY(tile));
						check.seen |= 1U<<*state;
						if (check.seen == check.expected) {
							check.complete = true;
							Debug(driver,1,"OpenTT3D: industry {} animation verification passed: {} original sprite frames captured at {},{}",graphics,std::popcount(check.seen),TileX(tile),TileY(tile));
						}
					}
				}
			}
			capture->parent_instance_end = capture->scene.instances.size();
			capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin;
			return;
		}
	}
	if (house_body) {
		Vec3 root{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
		unsigned variant = TileHash2Bit(capture->tile->x,capture->tile->y);
		if (DrawAuthoredHouse(capture->scene,GetHouseType(capture->tile->tile),GetHouseBuildingStage(capture->tile->tile),texture,root,origin,transparent ? 0.38f : 1.0f,pixel_scale,variant)) {
			capture->parent_mesh_end = capture->scene.vertices.size();
			capture->parent_instance_end = capture->scene.instances.size();
			capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin;
			static std::set<std::tuple<unsigned,unsigned,unsigned>> reported;
			unsigned house = GetHouseType(capture->tile->tile), stage = GetHouseBuildingStage(capture->tile->tile);
			if (checked_water_house == house && VoxelHouseState(house,stage,variant)) ObserveVoxelWater(capture->tile->tile,house);
			if (checked_house_palette == house && VoxelHouseState(house,stage,variant)) ObserveVoxelHousePalette(capture->tile->tile,house);
			if (!capture->parent_culled && !reported.contains({house,stage,variant}) && VoxelHouseState(house,stage,variant)) {
				reported.emplace(house,stage,variant);
				Debug(driver,1,"OpenTT3D: live voxel house {} construction stage {} captured at {},{}",house,stage,TileX(capture->tile->tile),TileY(capture->tile->tile));
				Debug(driver,1,"OpenTT3D: live voxel house {} construction stage {} variant {} captured",house,stage,variant);
			}
			return;
		}
	}
	if (tree && DrawAuthoredTree(capture->scene,image,texture,origin,transparent ? 0.38f : 1.0f,pixel_scale)) {
		capture->parent_mesh_end=capture->scene.vertices.size();
		capture->parent_instance_end = capture->scene.instances.size();
		capture->parent_culled = capture->parent_instance_end == capture->parent_instance_begin && capture->parent_mesh_end == capture->parent_mesh_begin;
		if (!capture->parent_culled && !capture->diagnostic && capture->tile != nullptr && !UseVoxelTrees()) {
			static std::set<std::pair<unsigned,unsigned>> reported;
			unsigned base = (image&SPRITE_MASK)-tree_stage;
			if (reported.emplace(base,tree_stage).second) Debug(driver,1,"OpenTT3D: live projected tree {} stage {} captured at {},{}",base,tree_stage,TileX(capture->tile->tile),TileY(capture->tile->tile));
		}
		return;
	}
	ReferenceSprite(texture, origin, transparent ? 0.38f : 1.0f);
}

static bool check_house_lift = false;
static TileIndex checked_lift_tile = INVALID_TILE;
static uint64_t checked_lift_positions = 0;

void BeginVoxelHouseLiftCheck()
{
	check_house_lift = true; checked_lift_tile = INVALID_TILE; checked_lift_positions = 0;
	Debug(driver,1,"OpenTT3D: observing actual voxel office lift travel");
}

void BeginVoxelPowerSparkCheck()
{
	if (!VoxelIndustryState(10,SPR_IT_POWER_PLANT_TRANSFORMERS)) throw std::runtime_error("Power-station spark family is not fully voxel-bound to its original sprites");
	check_power_sparks = true; checked_spark_tile = INVALID_TILE; checked_spark_frames = 0;
	Debug(driver,1,"OpenTT3D: observing all six actual power-station spark child frames");
}

void BeginVoxelToyFactoryCheck()
{
	if (!VoxelIndustryState(143,_industry_draw_tile_data[143*4+3].building.sprite)) throw std::runtime_error("Toy factory needs its original completed body and all four voxel children");
	check_toy_factory = true; checked_toy_factory_tile = INVALID_TILE;
	checked_toy_factory_industry = UINT32_MAX; checked_toy_factory_frames = 0;
	Debug(driver,1,"OpenTT3D: observing all 50 actual toy-factory frames and ordered child absences");
}

void BeginVoxelBubbleGeneratorCheck()
{
	if (!VoxelIndustryState(162,_industry_draw_tile_data[162*4+3].building.sprite)) throw std::runtime_error("Bubble generator needs its original body and both voxel children");
	check_bubble_generator = true; checked_bubble_tile = INVALID_TILE;
	checked_bubble_industry = UINT32_MAX; checked_bubble_frames = 0;
	Debug(driver,1,"OpenTT3D: observing all 40 actual bubble-generator frames with ordered plunger and cylinder");
}

void BeginVoxelToffeeQuarryCheck()
{
	if (!VoxelIndustryState(165,_industry_draw_tile_data[165*4+3].building.sprite)) throw std::runtime_error("Toffee quarry needs its original body, voxel shovel and shared parent redraw");
	check_toffee_quarry = true; checked_toffee_tile = INVALID_TILE;
	checked_toffee_industry = UINT32_MAX; checked_toffee_frames.reset();
	Debug(driver,1,"OpenTT3D: observing all 70 actual toffee-quarry frames with ordered shovel and shared parent redraw");
}

void BeginVoxelSugarMineCheck()
{
	if (!VoxelIndustryState(174,_industry_draw_tile_data[174*4+3].building.sprite)) throw std::runtime_error("Sugar mine needs its original connected posts and all 15 voxel children");
	check_sugar_mine = true; checked_sugar_tile = INVALID_TILE;
	checked_sugar_industry = UINT32_MAX; checked_sugar_frames.reset();
	Debug(driver,1,"OpenTT3D: observing all 96 actual sugar-mine frames with ordered sieve, cloud, pile and original absences");
}

void CaptureChild(SpriteID image, PaletteID palette, int x, int y, bool transparent, const SubSprite *, bool scale, bool relative)
{
	if (!capture || !capture->have_parent) return;
	bool power_spark = capture->parent_sprite == SPR_IT_POWER_PLANT_TRANSFORMERS && capture->tile != nullptr &&
		IsTileType(capture->tile->tile,MP_INDUSTRY) && GetIndustryGfx(capture->tile->tile) == 10 &&
		(image&SPRITE_MASK) > SPR_IT_POWER_PLANT_TRANSFORMERS && (image&SPRITE_MASK) <= SPR_IT_POWER_PLANT_TRANSFORMERS+6 &&
		VoxelIndustryState(10,SPR_IT_POWER_PLANT_TRANSFORMERS).has_value();
	bool toy_factory = capture->tile != nullptr && IsTileType(capture->tile->tile,MP_INDUSTRY) &&
		GetIndustryGfx(capture->tile->tile) == 143 && IsIndustryCompleted(capture->tile->tile) &&
		capture->parent_sprite == (_industry_draw_tile_data[143*4+3].building.sprite&SPRITE_MASK) &&
		VoxelIndustryState(143,capture->parent_sprite).has_value();
	bool bubble_generator = capture->tile != nullptr && IsTileType(capture->tile->tile,MP_INDUSTRY) &&
		GetIndustryGfx(capture->tile->tile) == 162 &&
		capture->parent_sprite == (_industry_draw_tile_data[162*4+GetIndustryConstructionStage(capture->tile->tile)].building.sprite&SPRITE_MASK) &&
		VoxelIndustryState(162,capture->parent_sprite).has_value();
	bool toffee_quarry = capture->tile != nullptr && IsTileType(capture->tile->tile,MP_INDUSTRY) &&
		GetIndustryGfx(capture->tile->tile) == 165 &&
		capture->parent_sprite == (_industry_draw_tile_data[165*4+GetIndustryConstructionStage(capture->tile->tile)].building.sprite&SPRITE_MASK) &&
		VoxelIndustryState(165,capture->parent_sprite).has_value();
	bool sugar_mine = capture->tile != nullptr && IsTileType(capture->tile->tile,MP_INDUSTRY) &&
		GetIndustryGfx(capture->tile->tile) == 174 && IsIndustryCompleted(capture->tile->tile) &&
		capture->parent_sprite == (_industry_draw_tile_data[174*4+3].building.sprite&SPRITE_MASK) &&
		VoxelIndustryState(174,capture->parent_sprite).has_value();
	/* A rising arc has its own bounds above the gantry. Keep its independent
	 * frustum check even when the solid parent has just left the viewport. */
	if (capture->parent_culled && !power_spark && !toy_factory && !bubble_generator && !toffee_quarry && !sugar_mine) return;
	ObjectTag tag{capture->scene.vertices.size(), capture->parent_id};
	if (toy_factory) {
		TileIndex tile = capture->tile->tile;
		unsigned frame = GetAnimationFrame(tile);
		auto children = VoxelToyFactoryChildren(frame);
		auto &next = capture->industry_next_child;
		while (next < children.size() && children[next].image == 0) ++next;
		if (next >= children.size() || !scale || !relative || children[next].image != (image&SPRITE_MASK) || children[next].x != x || children[next].y != y) {
			throw std::runtime_error("Toy-factory child lost its original order, absence or screen offset");
		}
		Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
		size_t before = capture->scene.instances.size();
		if (!DrawVoxelToyFactoryChild(capture->scene,image,frame,origin,palette,transparent ? 0.38f : 1)) throw std::runtime_error("Missing original toy-factory voxel child");
		if (frame != GetAnimationFrame(tile)) throw std::runtime_error("Toy-factory rendering changed its original animation");
		capture->industry_children_visible &= capture->scene.instances.size() != before;
		if (++next == children.size() && capture->industry_children_visible && !capture->parent_culled && !capture->diagnostic && check_toy_factory) {
			uint32_t industry = GetIndustryIndex(tile).base();
			if (checked_toy_factory_tile == INVALID_TILE) { checked_toy_factory_tile = tile; checked_toy_factory_industry = industry; }
			if (checked_toy_factory_tile == tile && checked_toy_factory_industry == industry) {
				if ((checked_toy_factory_frames & (uint64_t{1}<<frame)) == 0) {
					Debug(driver,1,"OpenTT3D: toy-factory frame {} captured at {},{} industry {}, clay {} robot {} stamp {} holder {}",frame,TileX(tile),TileY(tile),industry,children[0].image,children[1].image,children[2].image,children[3].image);
				}
				checked_toy_factory_frames |= uint64_t{1}<<frame;
				if (std::popcount(checked_toy_factory_frames) == std::size(_industry_anim_offs_toys)) {
					Debug(driver,1,"OpenTT3D: voxel toy-factory verification passed: 50 original ordered child frames and absences on tile {},{} industry {}",TileX(tile),TileY(tile),industry);
					check_toy_factory = false;
				}
			}
		}
		return;
	}
	if (bubble_generator) {
		TileIndex tile = capture->tile->tile;
		unsigned stage = GetIndustryConstructionStage(tile), frame = GetAnimationFrame(tile);
		auto children = VoxelBubbleGeneratorChildren(stage,frame);
		auto &next = capture->industry_next_child;
		while (next < children.size() && children[next].image == 0) ++next;
		if (next >= children.size() || !scale || !relative || children[next].image != (image&SPRITE_MASK) || children[next].x != x || children[next].y != y) {
			throw std::runtime_error("Bubble-generator child lost its original construction, order or screen offset");
		}
		Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
		size_t before = capture->scene.instances.size();
		if (!DrawVoxelBubbleGeneratorChild(capture->scene,image,stage,frame,origin,palette,transparent ? 0.38f : 1)) throw std::runtime_error("Missing original bubble-generator voxel child");
		if (frame != GetAnimationFrame(tile) || stage != GetIndustryConstructionStage(tile)) throw std::runtime_error("Bubble-generator rendering changed its original state");
		capture->industry_children_visible &= capture->scene.instances.size() != before;
		if (++next == children.size() && capture->industry_children_visible && !capture->parent_culled && !capture->diagnostic) {
			static unsigned reported_stages = 0;
			if ((reported_stages & (1U<<stage)) == 0) {
				reported_stages |= 1U<<stage;
				Debug(driver,1,"OpenTT3D: live voxel bubble-generator stage {} children plunger {} cylinder {} captured at {},{}",stage,children[0].image,children[1].image,TileX(tile),TileY(tile));
			}
			if (stage == 3 && check_bubble_generator) {
				uint32_t industry = GetIndustryIndex(tile).base();
				if (checked_bubble_tile == INVALID_TILE) { checked_bubble_tile = tile; checked_bubble_industry = industry; }
				if (checked_bubble_tile == tile && checked_bubble_industry == industry) {
					if ((checked_bubble_frames & (uint64_t{1}<<frame)) == 0) Debug(driver,1,"OpenTT3D: bubble-generator frame {} captured at {},{} industry {}, plunger {} cylinder {}",frame,TileX(tile),TileY(tile),industry,children[0].image,children[1].image);
					checked_bubble_frames |= uint64_t{1}<<frame;
					if (std::popcount(checked_bubble_frames) == std::size(_industry_anim_offs_bubbles)) {
						Debug(driver,1,"OpenTT3D: voxel bubble-generator verification passed: 40 original ordered child frames on tile {},{} industry {}",TileX(tile),TileY(tile),industry);
						check_bubble_generator = false;
					}
				}
			}
		}
		return;
	}
	if (toffee_quarry) {
		TileIndex tile = capture->tile->tile;
		unsigned stage = GetIndustryConstructionStage(tile), frame = GetAnimationFrame(tile);
		auto children = VoxelToffeeQuarryChildren(stage,frame);
		auto &next = capture->industry_next_child;
		if (next >= children.size() || !scale || !relative || children[next].image != (image&SPRITE_MASK) || children[next].x != x || children[next].y != y) {
			throw std::runtime_error("Toffee-quarry child lost its original construction, order or screen offset");
		}
		if (next == 0) {
			Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
			size_t before = capture->scene.instances.size();
			if (!DrawVoxelToffeeShovel(capture->scene,stage,frame,origin,palette,transparent ? 0.38f : 1)) throw std::runtime_error("Missing original toffee-quarry voxel shovel");
			capture->industry_children_visible &= capture->scene.instances.size() != before;
		} else {
			/*4766 exactly redraws4764. Its shared volume was already selected by
			 * this parent capture; duplicating it would create coincident surfaces. */
			capture->industry_children_visible &= !capture->parent_culled && capture->parent_instance_end > capture->parent_instance_begin;
		}
		if (frame != GetAnimationFrame(tile) || stage != GetIndustryConstructionStage(tile)) throw std::runtime_error("Toffee-quarry rendering changed its original state");
		if (++next == children.size() && capture->industry_children_visible && !capture->parent_culled && !capture->diagnostic) {
			static unsigned reported_stages = 0;
			if ((reported_stages & (1U<<stage)) == 0) {
				reported_stages |= 1U<<stage;
				Debug(driver,1,"OpenTT3D: live voxel toffee-quarry stage {} children shovel {} shared-parent {} captured at {},{}",stage,children[0].image,children[1].image,TileX(tile),TileY(tile));
			}
			if (stage == 3 && check_toffee_quarry) {
				uint32_t industry = GetIndustryIndex(tile).base();
				if (checked_toffee_tile == INVALID_TILE) { checked_toffee_tile = tile; checked_toffee_industry = industry; }
				if (checked_toffee_tile == tile && checked_toffee_industry == industry) {
					if (!checked_toffee_frames[frame]) Debug(driver,1,"OpenTT3D: toffee-quarry frame {} captured at {},{} industry {}, shovel {} shared-parent {}",frame,TileX(tile),TileY(tile),industry,children[0].image,children[1].image);
					checked_toffee_frames.set(frame);
					if (checked_toffee_frames.all()) {
						Debug(driver,1,"OpenTT3D: voxel toffee-quarry verification passed: 70 original ordered child frames with shared parent on tile {},{} industry {}",TileX(tile),TileY(tile),industry);
						check_toffee_quarry = false;
					}
				}
			}
		}
		return;
	}
	if (sugar_mine) {
		TileIndex tile = capture->tile->tile;
		unsigned stage = GetIndustryConstructionStage(tile), frame = GetAnimationFrame(tile);
		auto children = VoxelSugarMineChildren(stage,frame);
		auto &next = capture->industry_next_child;
		while (next < children.size() && children[next].image == 0) ++next;
		if (next >= children.size() || !scale || !relative || children[next].image != (image&SPRITE_MASK) || children[next].x != x || children[next].y != y) {
			throw std::runtime_error("Sugar-mine child lost its original construction, order, absence or screen offset");
		}
		Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
		size_t before = capture->scene.instances.size();
		if (!DrawVoxelSugarMineChild(capture->scene,image,stage,frame,origin,palette,transparent ? 0.38f : 1)) throw std::runtime_error("Missing original sugar-mine voxel child");
		if (frame != GetAnimationFrame(tile) || stage != GetIndustryConstructionStage(tile)) throw std::runtime_error("Sugar-mine rendering changed its original state");
		capture->industry_children_visible &= capture->scene.instances.size() != before;
		/* Some frames end after the sieve/cloud. Trailing absent children must
		 * finish this capture, while a hidden required child cannot pass it. */
		++next;
		while (next < children.size() && children[next].image == 0) ++next;
		if (next == children.size() && capture->industry_children_visible && !capture->parent_culled && !capture->diagnostic && check_sugar_mine) {
			uint32_t industry = GetIndustryIndex(tile).base();
			if (checked_sugar_tile == INVALID_TILE) { checked_sugar_tile = tile; checked_sugar_industry = industry; }
			if (checked_sugar_tile == tile && checked_sugar_industry == industry) {
				if (!checked_sugar_frames[frame]) Debug(driver,1,"OpenTT3D: sugar-mine frame {} captured at {},{} industry {}, sieve {} cloud {} pile {}",frame,TileX(tile),TileY(tile),industry,children[0].image,children[1].image,children[2].image);
				checked_sugar_frames.set(frame);
				if (checked_sugar_frames.all()) {
					Debug(driver,1,"OpenTT3D: voxel sugar-mine verification passed: 96 original ordered child frames and absences on tile {},{} industry {}",TileX(tile),TileY(tile),industry);
					check_sugar_mine = false;
				}
			}
		}
		return;
	}
	if (power_spark) {
		unsigned frame = (image&SPRITE_MASK)-SPR_IT_POWER_PLANT_TRANSFORMERS;
		const auto &offset = _coal_plant_sparks[frame-1];
		TileIndex tile = capture->tile->tile;
		unsigned animation = GetAnimationFrame(tile);
		if (!scale || !relative || x != offset.x || y != offset.y || frame != animation) throw std::runtime_error("Power-station spark lost its original child frame/offset");
		Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
		size_t before = capture->scene.instances.size();
		if (!DrawVoxelIndustrySpark(capture->scene,image,origin,palette,transparent ? 0.38f : 1)) throw std::runtime_error("Missing bound power-station spark");
		if (animation != GetAnimationFrame(tile)) throw std::runtime_error("Spark rendering changed the original animation state");
		if (capture->scene.instances.size() != before && !capture->diagnostic) {
			static unsigned reported = 0;
			if ((reported & (1U<<frame)) == 0) {
				reported |= 1U<<frame;
				Debug(driver,1,"OpenTT3D: live voxel power-station spark frame {} captured at {},{}",frame,TileX(tile),TileY(tile));
			}
			if (check_power_sparks) {
				if (checked_spark_tile == INVALID_TILE) checked_spark_tile = tile;
				if (checked_spark_tile == tile) checked_spark_frames |= 1U<<(frame-1);
				if (checked_spark_frames == 0x3f) {
					Debug(driver,1,"OpenTT3D: voxel power-station spark verification passed: six original child frames captured at {},{}",TileX(tile),TileY(tile));
					check_power_sparks = false;
				}
			}
		}
		return;
	}
	if ((image & SPRITE_MASK) == SPR_LIFT && IsBaseGraphicsSprite(image) && capture->tile != nullptr && IsTileType(capture->tile->tile,MP_HOUSE)) {
		TileIndex tile = capture->tile->tile;
		unsigned house = GetHouseType(tile), variant = TileHash2Bit(capture->tile->x,capture->tile->y);
		if ((house == 4 || house == 5) && VoxelHouseState(house,GetHouseBuildingStage(tile),variant)) {
			unsigned position = GetLiftPosition(tile);
			bool destination = LiftHasDestination(tile);
			Vec3 origin{static_cast<float>(capture->tile->x),static_cast<float>(capture->tile->y),TerrainZ(capture->tile->z)};
			size_t before = capture->scene.instances.size();
			if (DrawVoxelHouseLift(capture->scene,origin,position,palette,transparent ? 0.38f : 1)) {
				if (position != GetLiftPosition(tile) || destination != LiftHasDestination(tile)) throw std::runtime_error("Lift rendering changed gameplay state");
				if (capture->scene.instances.size() == before) return;
				static bool reported = false;
				if (!reported && !capture->diagnostic) { reported = true; Debug(driver,1,"OpenTT3D: live office lift captured as an independent voxel cabin"); }
				if (check_house_lift && !capture->diagnostic) {
					if (checked_lift_tile == INVALID_TILE && destination) checked_lift_tile = tile;
					if (checked_lift_tile == tile) {
						checked_lift_positions |= uint64_t{1}<<position;
						if (std::popcount(checked_lift_positions) >= 8) {
							Debug(driver,1,"OpenTT3D: voxel house lift animation verification passed: {} actual positions on tile {},{}",std::popcount(checked_lift_positions),TileX(tile),TileY(tile));
							check_house_lift = false;
						}
					}
				}
				return;
			}
		}
	}
	if (relative && capture->parent_offsets_pending) {
		unsigned stage = (capture->parent_sprite-1576)%7;
		bool opaque = stage != 4 && stage != 5 && !TreeHasComponentMaterials(capture->parent_sprite);
		const auto &parent = Textures().Get(capture->parent_sprite,capture->parent_palette,TextureZoom(capture->parent_origin),opaque);
		capture->parent_left = parent.x_offset; capture->parent_top = parent.y_offset;
		capture->parent_offsets_pending = false;
	}
	float sx = static_cast<float>(x * (scale ? ZOOM_BASE : 1) + (relative ? capture->parent_left : 0)) / ZOOM_BASE;
	float sy = static_cast<float>(y * (scale ? ZOOM_BASE : 1) + (relative ? capture->parent_top : 0)) / ZOOM_BASE;
	Vec3 origin = capture->parent_origin + Vec3{sy / 3 - sx / 4, sy / 3 + sx / 4, -sy / 3};
	SpriteTexture texture = Textures().Get(image, palette, TextureZoom(origin));
	if (capture->parent_instance_end > capture->parent_instance_begin) {
		for (size_t i = capture->parent_instance_begin; i < capture->parent_instance_end; ++i) {
			MeshInstance instance = capture->scene.instances[i];
			Vec3 relative{instance.data.origin_opacity[0] - origin.x, instance.data.origin_opacity[1] - origin.y, instance.data.origin_opacity[2] - origin.z};
			Vec3 uv = texture.UV(2 * (relative.y - relative.x) * ZOOM_BASE - texture.x_offset,
				(relative.x + relative.y - relative.z) * ZOOM_BASE - texture.y_offset);
			instance.data.uv_transform = {uv.x, uv.y, ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE), uv.z};
			instance.data.region = texture.Region();
			instance.data.origin_opacity[3] = transparent ? 0.38f : 1.0f;
			instance.data.mirror_layer_heading[2] = 0.01f;
			instance.data.identity[1] = static_cast<float>(SurfaceMode::Cutout);
			instance.data.identity[2] = 1;
			capture->scene.instances.push_back(instance);
		}
		return;
	}
	if (capture->parent_mesh_end > capture->parent_mesh_begin) {
		for (size_t i=capture->parent_mesh_begin;i<capture->parent_mesh_end;++i) {
			Vertex vertex=capture->scene.vertices[i];
			vertex.texture=SpriteUV(texture,vertex.position,origin);
			vertex.texture_region=texture.Region();
			vertex.surface = SurfaceMode::Cutout;
			vertex.position=vertex.position+vertex.normal*0.01f;
			vertex.opacity=transparent ? 0.38f : 1.0f;
			capture->scene.vertices.push_back(vertex);
		}
		return;
	}
	ReferenceSprite(texture, origin, transparent ? 0.38f : 1.0f);
}

std::array<int, 4> CaptureTileBounds()
{
	assert(capture.has_value());
	float maximum_z = TerrainZ(_settings_game.construction.map_height_limit * TILE_HEIGHT) + 160.0f;
	constexpr float overhang = 128;
	auto bounds = capture->camera.Frustum(64).IntersectionBounds({-overhang, -overhang, -16},
		{Map::MaxX() * 16.0f + overhang, Map::MaxY() * 16.0f + overhang, maximum_z});
	if (!bounds) return {0, 0, -1, -1};
	const auto &[low, high] = *bounds;
	return {std::clamp(static_cast<int>(std::floor((low.x - overhang) / 16)), 0, static_cast<int>(Map::MaxX())),
		std::clamp(static_cast<int>(std::floor((low.y - overhang) / 16)), 0, static_cast<int>(Map::MaxY())),
		std::clamp(static_cast<int>(std::ceil((high.x + overhang) / 16)), 0, static_cast<int>(Map::MaxX())),
		std::clamp(static_cast<int>(std::ceil((high.y + overhang) / 16)), 0, static_cast<int>(Map::MaxY()))};
}

bool CaptureVehicleVisible(const Vehicle *vehicle)
{
	if (vehicle->vehstatus.Test(VehState::Hidden) && !IsVehicleInTunnel(*vehicle)) return false;
	if (capture->camera.hidden_object == vehicle->index.base() + 1) return false;
	if (vehicle->type == VEH_AIRCRAFT && vehicle->subtype == AIR_ROTOR && capture->camera.hidden_object == vehicle->First()->index.base() + 1) return false;
	Vec3 position{static_cast<float>(vehicle->x_pos), static_cast<float>(vehicle->y_pos), RenderVehicleZ(*vehicle)};
	return capture->scene.visibility->Intersects(position - Vec3{128, 128, 16}, position + Vec3{128, 128, 128});
}

} // namespace Renderer3D
