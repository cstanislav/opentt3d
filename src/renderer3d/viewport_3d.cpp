/* SPDX-License-Identifier: GPL-2.0-only */
/** @file viewport_3d.cpp Read-only scene adapter and upstream framebuffer composition. */

#include "../stdafx.h"
#include "viewport_3d.h"
#include "gl_backend.hpp"
#include "renderer3d_models.h"
#include "../blitter/factory.hpp"
#include "../clear_map.h"
#include "../company_base.h"
#include "../debug.h"
#include "../engine_base.h"
#include "../gfx_func.h"
#include "../house.h"
#include "../landscape.h"
#include "../palette_func.h"
#include "../rail_map.h"
#include "../road_map.h"
#include "../town_map.h"
#include "../transparency.h"
#include "../tree_map.h"
#include "../vehicle_base.h"
#include "../vehicle_func.h"
#include "../video/video_driver.hpp"
#include "../viewport_func.h"
#include "../water_map.h"
#include "../zoom_func.h"

#include <cstdlib>
#include <numbers>
#include <unordered_map>

namespace Renderer3D {

/** Development opt-in. Activation is intentionally separate from saved game settings. */
static bool requested = [] {
	const char *value = std::getenv("OPENTT3D_RENDERER");
	return value != nullptr && std::string_view(value) == "1";
}();
static unsigned rotation = 0;

struct Frame {
	int left, top, width, height;
	ZoomLevel zoom;
	std::vector<uint8_t> pixels;
};
static std::unordered_map<const Viewport *, Frame> frames;

bool IsEnabled()
{
	return requested && HasOpenGLBackend() && BlitterFactory::GetCurrentBlitter()->GetScreenDepth() == 32;
}

bool SetEnabled(bool enabled)
{
	if (enabled && (!HasOpenGLBackend() || BlitterFactory::GetCurrentBlitter()->GetScreenDepth() != 32)) return false;
	requested = enabled;
	rotation = 0;
	frames.clear();
	MarkWholeScreenDirty();
	return true;
}

unsigned GetRotation() { return rotation; }

void RotateCamera(int quarter_turns)
{
	rotation = (rotation + quarter_turns) & 3;
	frames.clear();
	MarkWholeScreenDirty();
}

void BeginFrame()
{
	/* Cache only within one draw tick, so closed/reallocated Viewports cannot alias old frames. */
	frames.clear();
	/* Upstream dirty rectangles are projected for the original camera. Until rotated
	 * invalidation is implemented, repaint the full presentation each draw tick. */
	if (IsEnabled()) MarkWholeScreenDirty();
}

static Camera MakeCamera(const Viewport &vp)
{
	const float sx = (vp.virtual_left + vp.virtual_width * 0.5f) / ZOOM_BASE;
	const float sy = (vp.virtual_top + vp.virtual_height * 0.5f) / ZOOM_BASE;
	Camera camera;
	camera.focus = {(sy - sx * 0.5f) * 0.5f, (sy + sx * 0.5f) * 0.5f, 0};
	/* Move the orbit pivot up the same viewing ray to the terrain. This preserves
	 * the default projection exactly and keeps the viewed place centred on rotation. */
	Point ground = InverseRemapCoords2(static_cast<int>(sx * ZOOM_BASE), static_cast<int>(sy * ZOOM_BASE), true);
	if (ground.x >= 0 && ground.y >= 0 && ground.x < static_cast<int>(Map::MaxX() * TILE_SIZE) && ground.y < static_cast<int>(Map::MaxY() * TILE_SIZE)) {
		float z = GetSlopePixelZ(ground.x, ground.y);
		camera.focus = camera.focus + Vec3{z * 0.5f, z * 0.5f, z};
	}
	camera.pixels_per_unit = static_cast<float>(ZOOM_BASE) / (1U << to_underlying(vp.zoom));
	camera.width = vp.width;
	camera.height = vp.height;
	camera.rotation = rotation;
	return camera;
}

Point UnrotateScroll(Point delta)
{
	if (!IsEnabled()) return delta;
	switch (rotation) {
		case 1: return {-2 * delta.y, delta.x / 2};
		case 2: return {-delta.x, -delta.y};
		case 3: return {2 * delta.y, -delta.x / 2};
		default: return delta;
	}
}

ViewportSign ProjectSign(const Viewport &vp, const ViewportSign &sign, int x, int y, int z)
{
	if (!IsEnabled() || rotation == 0) return sign;
	ViewportSign result = sign;
	Point original = RemapCoords(x, y, z);
	auto p = MakeCamera(vp).Project({static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)});
	result.center = vp.virtual_left + ScaleByZoom(static_cast<int>(std::lround(p.x)), vp.zoom) + sign.center - original.x;
	result.top = vp.virtual_top + ScaleByZoom(static_cast<int>(std::lround(p.y)), vp.zoom) + sign.top - original.y;
	return result;
}

ViewportSign ProjectSign(const Viewport &vp, const ViewportSign &sign, TileIndex tile)
{
	if (!IsEnabled() || rotation == 0 || tile == INVALID_TILE) return sign;
	int x = TileX(tile) * TILE_SIZE, y = TileY(tile) * TILE_SIZE;
	return ProjectSign(vp, sign, x, y, GetSlopePixelZ(x, y));
}

bool FocusReferenceModel()
{
	if (Map::Size() == 0) return false;
	for (uint y = 0; y < Map::MaxY(); ++y) {
		for (uint x = 0; x < Map::MaxX(); ++x) {
			TileIndex tile = TileXY(x, y);
			if (IsTileType(tile, MP_HOUSE) && GetHouseBuildingStage(tile) == TOWN_HOUSE_COMPLETED &&
				(GetHouseType(tile) == 1 || GetHouseType(tile) == 2)) {
				Debug(driver, 1, "OpenTT3D: reference house {} at {},{}", GetHouseType(tile), x, y);
				ScrollMainWindowToTile(tile, true);
				return true;
			}
		}
	}
	return false;
}

static const Model &FindModel(std::string_view name)
{
	for (const auto &model : authored_models) if (model.name == name) return model;
	return authored_models[std::size(authored_models) - 1]; // Explicit development placeholder.
}

static Vec3 TilePoint(TileIndex tile, float dx, float dy, float offset = 0)
{
	auto [slope, z] = GetTilePixelSlope(tile);
	float height;
	if (dx == 0 && dy == 0) height = GetSlopePixelZInCorner(slope, CORNER_N);
	else if (dx == 16 && dy == 0) height = GetSlopePixelZInCorner(slope, CORNER_W);
	else if (dx == 16 && dy == 16) height = GetSlopePixelZInCorner(slope, CORNER_S);
	else if (dx == 0 && dy == 16) height = GetSlopePixelZInCorner(slope, CORNER_E);
	else height = GetPartialPixelZ(std::clamp(static_cast<int>(dx), 0, 15), std::clamp(static_cast<int>(dy), 0, 15), slope);
	return {TileX(tile) * 16.0f + dx, TileY(tile) * 16.0f + dy, z + height + offset};
}

static Rgb GroundColour(TileIndex tile)
{
	if (IsTileType(tile, MP_WATER)) return {0.13f, 0.36f, 0.59f};
	if (IsTileType(tile, MP_CLEAR)) {
		if (IsSnowTile(tile)) return {0.87f, 0.90f, 0.91f};
		switch (GetClearGround(tile)) {
			case CLEAR_DESERT: return {0.80f, 0.65f, 0.35f};
			case CLEAR_ROCKS: return {0.47f, 0.46f, 0.41f};
			case CLEAR_FIELDS: return {0.59f, 0.49f, 0.23f};
			default: break;
		}
		if (GetClearDensity(tile) == 0) return {0.43f, 0.33f, 0.20f};
	}
	if (IsTileType(tile, MP_HOUSE) || IsTileType(tile, MP_STATION)) return {0.57f, 0.57f, 0.51f};
	if (IsTileType(tile, MP_TREES) && GetTreeGround(tile) == TREE_GROUND_SNOW_DESERT) {
		return _settings_game.game_creation.landscape == LandscapeType::Tropic ? Rgb{0.80f, 0.65f, 0.35f} : Rgb{0.87f, 0.90f, 0.91f};
	}
	/* A presentation-only tile hash; never consume either upstream random stream. */
	const float variation = 0.94f + ((tile.base() * 2654435761U) >> 28) * 0.006f;
	return {0.38f * variation, 0.54f * variation, 0.20f * variation};
}

static void Ground(Scene &scene, TileIndex tile)
{
	Rgb colour = GroundColour(tile);
	Vec3 a = TilePoint(tile, 0, 0), b = TilePoint(tile, 16, 0);
	Vec3 c = TilePoint(tile, 16, 16), d = TilePoint(tile, 0, 16), center = TilePoint(tile, 8, 8);
	scene.Triangle(a, b, center, colour); scene.Triangle(b, c, center, colour);
	scene.Triangle(c, d, center, colour); scene.Triangle(d, a, center, colour);
}

static void SurfaceRect(Scene &scene, TileIndex tile, float x, float y, float X, float Y, Rgb colour, float offset)
{
	scene.Quad(TilePoint(tile, x, y, offset), TilePoint(tile, X, y, offset),
		TilePoint(tile, X, Y, offset), TilePoint(tile, x, Y, offset), colour);
}

static void Roads(Scene &scene, TileIndex tile)
{
	if (!IsNormalRoad(tile) && !IsLevelCrossing(tile)) return;
	RoadBits bits = IsNormalRoad(tile) ? GetAllRoadBits(tile) : GetCrossingRoadBits(tile);
	Rgb asphalt{0.27f, 0.28f, 0.26f}, kerb{0.65f, 0.65f, 0.58f}, markings{0.84f, 0.82f, 0.67f};
	SurfaceRect(scene, tile, 3, 3, 13, 13, kerb, 0.16f);
	SurfaceRect(scene, tile, 4, 4, 12, 12, asphalt, 0.24f);
	if (bits & ROAD_NE) { SurfaceRect(scene, tile, 0, 3, 8, 13, kerb, 0.16f); SurfaceRect(scene, tile, 0, 4, 8, 12, asphalt, 0.24f); }
	if (bits & ROAD_SW) { SurfaceRect(scene, tile, 8, 3, 16, 13, kerb, 0.16f); SurfaceRect(scene, tile, 8, 4, 16, 12, asphalt, 0.24f); }
	if (bits & ROAD_NW) { SurfaceRect(scene, tile, 3, 0, 13, 8, kerb, 0.16f); SurfaceRect(scene, tile, 4, 0, 12, 8, asphalt, 0.24f); }
	if (bits & ROAD_SE) { SurfaceRect(scene, tile, 3, 8, 13, 16, kerb, 0.16f); SurfaceRect(scene, tile, 4, 8, 12, 16, asphalt, 0.24f); }
	if (bits == ROAD_X) for (int x : {1, 6, 11}) SurfaceRect(scene, tile, x, 7.7f, x + 3, 8.3f, markings, 0.32f);
	if (bits == ROAD_Y) for (int y : {1, 6, 11}) SurfaceRect(scene, tile, 7.7f, y, 8.3f, y + 3, markings, 0.32f);
}

static void TrackStrip(Scene &scene, TileIndex tile, Vec3 a, Vec3 b, float half_width, Rgb colour, float z)
{
	Vec3 delta = b - a;
	float length = std::sqrt(delta.x * delta.x + delta.y * delta.y);
	Vec3 normal{-delta.y / length * half_width, delta.x / length * half_width, 0};
	a = a + normal; b = b + normal;
	Vec3 c = b - normal * 2, d = a - normal * 2;
	scene.Quad(TilePoint(tile, a.x, a.y, z), TilePoint(tile, b.x, b.y, z),
		TilePoint(tile, c.x, c.y, z), TilePoint(tile, d.x, d.y, z), colour);
}

static void Tracks(Scene &scene, TileIndex tile)
{
	if (!IsPlainRailTile(tile)) return;
	/* Authored centre lines for the six vanilla track pieces, in tile-local units. */
	static constexpr Vec3 endpoints[6][2] = {
		{{0, 8, 0}, {16, 8, 0}}, {{8, 0, 0}, {8, 16, 0}},
		{{0, 8, 0}, {8, 0, 0}}, {{8, 16, 0}, {16, 8, 0}},
		{{0, 8, 0}, {8, 16, 0}}, {{8, 0, 0}, {16, 8, 0}},
	};
	for (unsigned track = 0; track < 6; ++track) {
		if (!HasBit(GetTrackBits(tile), track)) continue;
		Vec3 a = endpoints[track][0], b = endpoints[track][1], delta = b - a;
		float length = std::sqrt(delta.x * delta.x + delta.y * delta.y);
		Vec3 normal{-delta.y / length, delta.x / length, 0};
		TrackStrip(scene, tile, a, b, 2.3f, {0.47f, 0.44f, 0.36f}, 0.20f);
		for (float t = 0.1f; t < 1; t += 0.18f) {
			Vec3 p = a + delta * t;
			TrackStrip(scene, tile, p - normal * 1.9f, p + normal * 1.9f, 0.26f, {0.31f, 0.24f, 0.17f}, 0.29f);
		}
		TrackStrip(scene, tile, a + normal * 1.05f, b + normal * 1.05f, 0.13f, {0.74f, 0.76f, 0.74f}, 0.40f);
		TrackStrip(scene, tile, a - normal * 1.05f, b - normal * 1.05f, 0.13f, {0.74f, 0.76f, 0.74f}, 0.40f);
	}
}

static void TileObjects(Scene &scene, TileIndex tile)
{
	Vec3 origin{TileX(tile) * 16.0f, TileY(tile) * 16.0f, static_cast<float>(GetTileMaxPixelZ(tile))};
	switch (GetTileType(tile)) {
		case MP_HOUSE: {
			if (IsInvisibilitySet(TO_HOUSES)) return;
			const auto house = GetHouseType(tile);
			std::string_view model = "development_placeholder";
			if (HouseSpec::Get(house)->grf_prop.grffile == nullptr && GetHouseBuildingStage(tile) == TOWN_HOUSE_COMPLETED) {
				if (house == 1) model = "temperate_flats";
				if (house == 2) model = "temperate_brick_house";
			}
			scene.AddModel(FindModel(model), origin);
			break;
		}
		case MP_TREES: {
			if (IsInvisibilitySet(TO_TREES)) return;
			/* Temporary reference-tree scene population; species/state coverage is
			 * explicitly incomplete in the asset inventory. */
			static constexpr float offsets[4][2] = {{4, 4}, {11, 10}, {3, 12}, {12, 3}};
			for (uint i = 0; i < GetTreeCount(tile); ++i) {
				float scale = i == GetTreeCount(tile) - 1 && to_underlying(GetTreeGrowth(tile)) < 3 ? 0.45f : 1.0f;
				scene.AddModel(FindModel("temperate_conifer_03"), TilePoint(tile, offsets[i][0], offsets[i][1]), 0, {}, scale);
			}
			break;
		}
		case MP_ROAD:
			Roads(scene, tile);
			if (IsRoadDepot(tile)) scene.AddModel(FindModel("development_placeholder"), origin);
			break;
		case MP_RAILWAY:
			Tracks(scene, tile);
			if (IsRailDepot(tile)) scene.AddModel(FindModel("development_placeholder"), origin);
			break;
		case MP_STATION: case MP_INDUSTRY: case MP_OBJECT: case MP_TUNNELBRIDGE:
			scene.AddModel(FindModel("development_placeholder"), origin);
			break;
		default: break;
	}
}

static void Vehicles(Scene &scene, const Camera &camera)
{
	for (const Vehicle *v : Vehicle::Iterate()) {
		if (v->vehstatus.Any({VehState::Hidden, VehState::Shadow}) || !IsCompanyBuildableVehicleType(v)) continue;
		Vec3 origin{static_cast<float>(v->x_pos), static_cast<float>(v->y_pos), static_cast<float>(v->z_pos)};
		auto p = camera.Project(origin);
		if (p.x < -160 || p.y < -160 || p.x > camera.width + 160 || p.y > camera.height + 160) continue;
		const Engine *engine = Engine::GetIfValid(v->engine_type);
		std::string_view model = "development_placeholder";
		if (engine != nullptr && engine->grf_prop.grffile == nullptr && v->type == VEH_TRAIN && v->engine_type.base() == 0) model = "kirby_paul_tank";
		Rgb company{0.26f, 0.42f, 0.8f};
		if (const Company *owner = Company::GetIfValid(v->owner); owner != nullptr) {
			Colour c = _cur_palette.palette[GetColourGradient(owner->colour, SHADE_NORMAL).p];
			company = {c.r / 255.0f, c.g / 255.0f, c.b / 255.0f};
		}
		float heading = (5.0f - to_underlying(v->direction)) * std::numbers::pi_v<float> / 4.0f;
		if (model == "development_placeholder") origin = origin - Vec3{3, 3, 0};
		scene.AddModel(FindModel(model), origin, heading, company, model == "development_placeholder" ? 0.4f : 1.0f);
	}
}

static Scene BuildScene(const Camera &camera)
{
	Scene scene;
	float min_x = static_cast<float>(Map::MaxX()), min_y = static_cast<float>(Map::MaxY()), max_x = 0, max_y = 0;
	const float maximum_z = _settings_game.construction.map_height_limit * TILE_HEIGHT + 128.0f;
	for (Vec3 p : camera.FrustumCorners(0, maximum_z, 128)) {
		min_x = std::min(min_x, p.x / 16); min_y = std::min(min_y, p.y / 16);
		max_x = std::max(max_x, p.x / 16); max_y = std::max(max_y, p.y / 16);
	}
	const int left = std::clamp(static_cast<int>(std::floor(min_x)), 0, static_cast<int>(Map::MaxX()));
	const int top = std::clamp(static_cast<int>(std::floor(min_y)), 0, static_cast<int>(Map::MaxY()));
	const int right = std::clamp(static_cast<int>(std::ceil(max_x)), 0, static_cast<int>(Map::MaxX()));
	const int bottom = std::clamp(static_cast<int>(std::ceil(max_y)), 0, static_cast<int>(Map::MaxY()));
	for (int y = top; y <= bottom; ++y) {
		for (int x = left; x <= right; ++x) {
			TileIndex tile = TileXY(x, y);
			if (!IsValidTile(tile)) continue;
			auto p = camera.Project(TilePoint(tile, 8, 8));
			const float margin = 128 * camera.pixels_per_unit;
			if (p.x < -margin || p.x > camera.width + margin || p.y < -margin || p.y > camera.height + margin) continue;
			Ground(scene, tile);
			TileObjects(scene, tile);
		}
	}
	Vehicles(scene, camera);
	return scene;
}

bool DrawViewport(const Viewport &vp, const DrawPixelInfo &dpi)
{
	if (!IsEnabled() || Map::Size() == 0) return false;
	auto it = frames.find(&vp);
	if (it == frames.end() || it->second.left != vp.virtual_left || it->second.top != vp.virtual_top ||
		it->second.width != vp.width || it->second.height != vp.height || it->second.zoom != vp.zoom) {
		Frame frame{vp.virtual_left, vp.virtual_top, vp.width, vp.height, vp.zoom, {}};
		Camera camera = MakeCamera(vp);
		Scene scene = BuildScene(camera);
		if (!RenderScene(scene, camera, frame.pixels)) {
			requested = false;
			rotation = 0;
			MarkWholeScreenDirty();
			return false;
		}
		it = frames.insert_or_assign(&vp, std::move(frame)).first;
	}
	const auto &pixels = it->second.pixels;
	int left = UnScaleByZoom(dpi.left - (vp.virtual_left & ScaleByZoom(-1, vp.zoom)), vp.zoom);
	int top = UnScaleByZoom(dpi.top - (vp.virtual_top & ScaleByZoom(-1, vp.zoom)), vp.zoom);
	int width = UnScaleByZoom(dpi.width, vp.zoom), height = UnScaleByZoom(dpi.height, vp.zoom);
	/* Composite only this clipped draw region. Upstream paints windows and labels later. */
	for (int y = 0; y < height; ++y) {
		if (top + y < 0 || top + y >= vp.height) continue;
		auto *destination = static_cast<Colour *>(dpi.dst_ptr) + y * dpi.pitch;
		for (int x = 0; x < width; ++x) {
			if (left + x < 0 || left + x >= vp.width) continue;
			size_t offset = (static_cast<size_t>(vp.height - 1 - top - y) * vp.width + left + x) * 4;
			destination[x] = Colour(pixels[offset], pixels[offset + 1], pixels[offset + 2]);
		}
	}
	/* 40bpp's palette-animation plane must not reinterpret new RGB viewport pixels. */
	if (!_screen_disable_anim && BlitterFactory::GetCurrentBlitter()->NeedsAnimationBuffer()) {
		if (auto *animation = VideoDriver::GetInstance()->GetAnimBuffer(); animation != nullptr) {
			ptrdiff_t offset = static_cast<Colour *>(dpi.dst_ptr) - static_cast<Colour *>(_screen.dst_ptr);
			for (int y = 0; y < height; ++y) std::fill_n(animation + offset + y * dpi.pitch, width, uint8_t{0});
		}
	}
	return true;
}

Point PickTerrain(const Viewport &vp, int screen_x, int screen_y, bool clamp_to_map)
{
	if (screen_x < vp.left || screen_y < vp.top || screen_x >= vp.left + vp.width || screen_y >= vp.top + vp.height) return {-1, -1};
	Camera camera = MakeCamera(vp);
	float maximum_z = _settings_game.construction.map_height_limit * TILE_HEIGHT + TILE_HEIGHT;
	/* Walk the orthographic ray from its highest possible terrain intersection.
	 * Height queries are the upstream slope/foundation queries, not render geometry. */
	for (float z = maximum_z; z >= 0; z -= 0.5f) {
		Vec3 p = camera.Unproject(screen_x - vp.left + 0.5f, screen_y - vp.top + 0.5f, z);
		int x = static_cast<int>(std::floor(p.x)), y = static_cast<int>(std::floor(p.y));
		if (x < 0 || y < 0 || x >= static_cast<int>(Map::MaxX() * TILE_SIZE) || y >= static_cast<int>(Map::MaxY() * TILE_SIZE)) continue;
		if (!IsValidTile(TileVirtXY(x, y))) continue;
		if (z <= GetSlopePixelZ(x, y)) return {x, y};
	}
	if (!clamp_to_map) return {-1, -1};
	Vec3 p = camera.Unproject(screen_x - vp.left, screen_y - vp.top, 0);
	const int minimum = _settings_game.construction.freeform_edges ? TILE_SIZE : 0;
	return {std::clamp(static_cast<int>(p.x), minimum, static_cast<int>(Map::MaxX() * TILE_SIZE - 1)),
		std::clamp(static_cast<int>(p.y), minimum, static_cast<int>(Map::MaxY() * TILE_SIZE - 1))};
}

Vehicle *PickVehicle(const Viewport &vp, int screen_x, int screen_y)
{
	Camera camera = MakeCamera(vp);
	Vehicle *best = nullptr;
	float distance = 24.0f * camera.pixels_per_unit;
	for (Vehicle *v : Vehicle::Iterate()) {
		if (v->vehstatus.Any({VehState::Hidden, VehState::Unclickable, VehState::Shadow})) continue;
		auto p = camera.Project({static_cast<float>(v->x_pos), static_cast<float>(v->y_pos), static_cast<float>(v->z_pos + 3)});
		float d = std::hypot(p.x - (screen_x - vp.left), p.y - (screen_y - vp.top));
		if (d < distance) { best = v; distance = d; }
	}
	return best;
}

} // namespace Renderer3D
