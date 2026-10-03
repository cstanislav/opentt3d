/* SPDX-License-Identifier: GPL-2.0-only */
/** @file renderer3d_transport.cpp Tunnel clearances and portal orientation invariants. */
#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "tunnel_geometry.hpp"
#include "rail_capture.h"
#include "station_geometry.hpp"
#include "ground_detail_geometry.hpp"
#include "rail_detail_geometry.hpp"
#include "depot_geometry.hpp"
#include "crossing_geometry.hpp"
#include "road_stop_geometry.hpp"
#include "bridge_geometry.hpp"
#include "world_capture.h"
#include "voxel_models.h"
#include "sprite_textures.hpp"
#include "../landscape.h"
#include "../rail.h"
#include "../slope_func.h"
#include "../track_func.h"
#include "../table/sprites.h"
#include <set>

using namespace Renderer3D;
using Catch::Detail::Approx;

TEST_CASE("Original objects retain source climate restrictions and all five four-tile HQ selectors", "[renderer3d][voxel]")
{
	for (unsigned type = 0; type < 4; ++type) {
		CHECK(OriginalObjectLayoutIdentifier(type,0,0) == type);
		CHECK_FALSE(OriginalObjectLayoutIdentifier(type,1,0));
		CHECK_FALSE(OriginalObjectLayoutIdentifier(type,0,1));
	}
	for (unsigned size = 0; size < 5; ++size) for (unsigned part = 0; part < 4; ++part) CHECK(OriginalObjectLayoutIdentifier(4,size,part) == 4+size*4+part);
	CHECK_FALSE(OriginalObjectLayoutIdentifier(4,5,0));
	CHECK_FALSE(OriginalObjectLayoutIdentifier(4,0,4));
	CHECK_FALSE(OriginalObjectLayoutIdentifier(5,0,0));
	for (unsigned type = 0; type < 5; ++type) for (unsigned climate = 0; climate < 4; ++climate) CHECK(OriginalObjectModelClimateSupported(type,climate) == (type == 0 ? climate < 3 : type == 1 ? climate < 2 : true));
	CHECK_FALSE(OriginalObjectModelClimateSupported(5,0));
	CHECK_FALSE(OriginalObjectModelClimateSupported(2,4));
}

static std::optional<float> TriangleHit(const Ray &ray, Vec3 a, Vec3 b, Vec3 c)
{
	auto cross = [](Vec3 u, Vec3 v) { return Vec3{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x}; };
	Vec3 edge = b-a, second = c-a, h = cross(ray.direction,second);
	float determinant = Dot(edge,h);
	if (std::abs(determinant) < 1e-7f) return std::nullopt;
	Vec3 s = ray.origin-a;
	float u = Dot(s,h)/determinant;
	if (u < 0 || u > 1) return std::nullopt;
	Vec3 q = cross(s,edge);
	float v = Dot(ray.direction,q)/determinant;
	if (v < 0 || u+v > 1) return std::nullopt;
	float distance = Dot(second,q)/determinant;
	return distance > 0.0001f ? std::optional<float>{distance} : std::nullopt;
}

static float FirstHit(const TunnelAssembly &assembly, const Ray &ray)
{
	float distance = std::numeric_limits<float>::infinity();
	for (const auto &part : assembly.parts) for (size_t i = 0; i < part.size(); i += 3) {
		if (auto hit = TriangleHit(ray,part[i].position,part[i+1].position,part[i+2].position)) distance = std::min(distance,*hit);
	}
	return distance;
}

TEST_CASE("Voxel fence families retain openings, heights and raised diagonal contact", "[renderer3d][voxel]")
{
	auto hit = [](const std::vector<Vertex> &mesh, Ray ray) {
		float nearest = INFINITY;
		for (size_t i = 0; i < mesh.size(); i += 3) if (auto distance = TriangleHit(ray,mesh[i].position,mesh[i+1].position,mesh[i+2].position)) nearest = std::min(nearest,*distance);
		return nearest;
	};
	auto white = MakeFenceMesh(2,{0,1,0},{16,1,0},{});
	CHECK(hit(white,{{0,1,8},{0,0,-1}}) == Approx(5));
	CHECK_FALSE(std::isfinite(hit(white,{{1,0,1.75f},{0,1,0}})));
	CHECK(std::isfinite(hit(white,{{1,0,1.125f},{0,1,0}})));
	auto gate = MakeFenceMesh(1,{0,1,0},{16,1,0},{},false,2);
	CHECK_FALSE(std::isfinite(hit(gate,{{8,0,2.1f},{0,1,0}})));
	CHECK(std::isfinite(hit(gate,{{8,0,1.125f},{0,1,0}})));
	auto chain = MakeFenceMesh(6,{0,1,0},{16,1,0},{});
	CHECK(hit(chain,{{0,1,8},{0,0,-1}}) == Approx(3));
	CHECK_FALSE(std::isfinite(hit(chain,{{2.25f,0,2},{0,1,0}})));
	CHECK(std::isfinite(hit(chain,{{2,0,2},{0,1,0}})));
	for (unsigned lod = 0; lod < 3; ++lod) for (Corner corner : {CORNER_W,CORNER_S,CORNER_E,CORNER_N}) {
		for (Slope terrain : {SLOPE_FLAT,HalftileSlope(SlopeWithOneCornerRaised(corner),corner),HalftileSlope(SteepSlope(corner),corner)}) {
			float base = TerrainZ(GetSlopePixelZInCorner(RemoveHalftileSlope(terrain),corner));
			bool along = corner == CORNER_W || corner == CORNER_E;
			Vec3 start{along ? 0.0f : 16.0f,0,base}, end{along ? 16.0f : 0.0f,16,base};
			auto diagonal = MakeFenceMesh(6,start,end,MakeTileSurface(terrain),true,0,lod);
			INFO("corner=" << to_underlying(corner) << " slope=" << to_underlying(terrain) << " lod=" << lod);
			CHECK(std::ranges::all_of(diagonal,[base](const Vertex &v) { return v.position.z >= base && v.position.z <= base+5; }));
			CHECK(std::ranges::any_of(diagonal,[base](const Vertex &v) { return v.normal.z < -0.99f && v.position.z == base; }));
			CHECK(hit(diagonal,{start+Vec3{0,0,8},{0,0,-1}}) == Approx(3));
			CHECK(hit(diagonal,{end+Vec3{0,0,8},{0,0,-1}}) == Approx(3));
		}
	}
}

TEST_CASE("Voxel foundations stay below playable surfaces and support every legal foundation", "[renderer3d][voxel]")
{
	std::set<std::pair<Slope,Foundation>> cases;
	for (unsigned value = 1; value < 32; ++value) {
		if (value >= 15 && value != 23 && value != 27 && value != 29 && value != 30) continue;
		Slope slope = static_cast<Slope>(value);
		cases.emplace(slope,FOUNDATION_LEVELED);
		for (unsigned tracks = 1; tracks <= TRACK_BIT_ALL; ++tracks) {
			Foundation foundation = GetRailFoundation(slope,static_cast<TrackBits>(tracks));
			if (foundation != FOUNDATION_NONE && foundation != FOUNDATION_INVALID && foundation != FOUNDATION_STEEP_BOTH) cases.emplace(slope,foundation);
		}
	}
	for (auto [slope,foundation] : cases) {
		Slope upper = slope;
		float rise = TerrainZ(ApplyPixelFoundationToSlope(foundation,upper));
		auto low = MakeTileSurface(slope), high = MakeTileSurface(upper);
		auto solid = MakeFoundationMesh(low,high,rise,0,true);
		INFO("slope=" << static_cast<unsigned>(slope) << " foundation=" << static_cast<unsigned>(foundation));
		REQUIRE_FALSE(solid.empty());
		bool finite = true, aligned = true;
		for (const auto &vertex : solid) {
			finite &= std::isfinite(vertex.position.x+vertex.position.y+vertex.position.z);
			float length = std::abs(vertex.normal.x)+std::abs(vertex.normal.y)+std::abs(vertex.normal.z);
			aligned &= std::abs(length-1) < 0.000001f;
			aligned &= (std::abs(vertex.normal.x) > 0.5f)+(std::abs(vertex.normal.y) > 0.5f)+(std::abs(vertex.normal.z) > 0.5f) == 1;
		}
		CHECK(finite); CHECK(aligned);
		unsigned supported = 0;
		for (float x : {0.125f,3.125f,7.125f,11.125f,15.125f}) for (float y : {0.125f,3.125f,7.125f,11.125f,15.125f}) {
			float terrain = low.Height(x,y), ceiling = rise+high.Height(x,y);
			float nearest = INFINITY;
			for (size_t i = 0; i < solid.size(); i += 3) if (solid[i].normal.z > 0.99f) {
				if (auto distance = TriangleHit({{x,y,40},{0,0,-1}},solid[i].position,solid[i+1].position,solid[i+2].position)) nearest = std::min(nearest,*distance);
			}
			if (std::isfinite(nearest)) CHECK(40-nearest <= ceiling+0.0001f);
			/* Skip the half-cell stair band immediately at an internal diagonal.
			 * Interior support must approach the original surface within a cell. */
			if (ceiling-terrain > 1 && std::abs(x-y) > 0.5f && std::abs(x+y-16) > 0.5f) {
				REQUIRE(std::isfinite(nearest));
				CHECK(ceiling-(40-nearest) <= 0.75f);
				++supported;
			}
		}
		CHECK(supported != 0);
		for (unsigned lod : {1U,2U}) {
			auto distant = MakeFoundationMesh(low,high,rise,lod,true);
			float max_z = -INFINITY;
			for (const auto &v : distant) max_z = std::max(max_z,v.position.z);
			CHECK(max_z <= rise+TerrainZ(GetSlopeMaxPixelZ(upper)));
		}
	}
	/* The two microstep faces of one diagonal wall stone must not alternate
	 * between unrelated light ramps, which produced vertical zebra striping. */
	const Corner corners[] = {CORNER_N,CORNER_W,CORNER_S,CORNER_E};
	for (unsigned turn = 0; turn < 4; ++turn) {
		Slope slope = SlopeWithOneCornerRaised(corners[turn]);
		auto mesh = MakeFoundationMesh(MakeTileSurface(slope),MakeTileSurface(HalftileSlope(slope,corners[turn])),0);
		auto colour = [&](Vec3 origin, Vec3 direction) {
			for (unsigned i = 0; i < turn; ++i) { origin = {16-origin.y,origin.x,origin.z}; direction = {-direction.y,direction.x,direction.z}; }
			float distance = INFINITY, palette = -1;
			for (size_t i = 0; i < mesh.size(); i += 3) if (auto hit = TriangleHit({origin,direction},mesh[i].position,mesh[i+1].position,mesh[i+2].position); hit && *hit < distance) {
				distance = *hit; palette = mesh[i].texture.x;
			}
			return palette;
		};
		for (float z : {1.125f,3.125f,5.125f,7.125f}) {
			float x = colour({8.25f,8.125f,z},{-1,0,0}), y = colour({7.125f,9.25f,z},{0,-1,0});
			REQUIRE(x >= 0);
			CHECK(x == y);
		}
	}
}

TEST_CASE("Voxel hedge corner caps agree where perpendicular volumes overlap", "[renderer3d][voxel]")
{
	const Vec3 corners[] = {{0,0,0},{16,0,0},{16,16,0},{0,16,0}};
	const unsigned edges[][2] = {{0,3},{3,2},{1,2},{0,1}};
	for (Slope slope : {SLOPE_FLAT,SLOPE_SW,SLOPE_NE}) {
		std::array<std::vector<Vertex>,4> fences;
		for (unsigned edge = 0; edge < 4; ++edge) fences[edge] = MakeFenceMesh(1,corners[edges[edge][0]],corners[edges[edge][1]],MakeTileSurface(slope));
		for (float x : {0.3125f,15.6875f}) for (float y : {0.3125f,15.6875f}) {
			std::vector<std::pair<float,float>> hits;
			float nearest = INFINITY;
			for (const auto &mesh : fences) for (size_t i = 0; i < mesh.size(); i += 3) {
				if (mesh[i].normal.z < 0.99f) continue;
				if (auto distance = TriangleHit({{x,y,32},{0,0,-1}},mesh[i].position,mesh[i+1].position,mesh[i+2].position)) {
					hits.emplace_back(*distance,mesh[i].texture.x);
					nearest = std::min(nearest,*distance);
				}
			}
			std::set<float> colours;
			unsigned surfaces = 0;
			for (auto [distance,colour] : hits) if (std::abs(distance-nearest) < 0.0001f) { colours.insert(colour); ++surfaces; }
			INFO("slope=" << static_cast<unsigned>(slope) << " corner=" << x << "," << y);
			REQUIRE(surfaces >= 2);
			CHECK(colours.size() == 1);
		}
	}
}

TEST_CASE("Tunnel entrances and lining leave actual Cab and vehicle clearances", "[renderer3d]")
{
	for (unsigned kind = 0; kind < 6; ++kind) for (bool portal : {false,true}) {
		INFO("kind=" << kind << " portal=" << portal);
		auto assembly = MakeTunnelAssembly(static_cast<TunnelKind>(kind),portal);
		for (float lane : (kind >= 4 ? std::vector<float>{5,11} : std::vector<float>{8})) {
			CHECK_FALSE(std::isfinite(FirstHit(assembly,{{-1,lane,6},{1,0,0}})));
		}
		float ceiling = FirstHit(assembly,{{12,8,6},{0,0,1}});
		CHECK(ceiling > (kind == 1 ? 0.9f : 1.5f)); // Electric contact wire is below the vault.
		CHECK(ceiling < 2.0f);
		CHECK(FirstHit(assembly,{{12,8,6},{0,0,-1}}) < 6.5f);
		if (portal) {
			/* The doubled bank is continuous above every bore, including the
			 * monorail hood, and both exposed retaining cheeks close its sides. */
			for (float y : {1.0f,8.0f,15.0f}) CHECK(FirstHit(assembly,{{12,y,24},{0,0,-1}}) == Approx(12));
			for (float direction : {-1.0f,1.0f}) CHECK(FirstHit(assembly,{{6,8,5},{0,direction,0}}) == Approx(5.8f));
		}
		bool finite = true;
		for (const auto &part : assembly.parts) for (const auto &vertex : part) {
			finite &= std::isfinite(vertex.position.x+vertex.position.y+vertex.position.z+vertex.normal.x+vertex.normal.y+vertex.normal.z);
		}
		REQUIRE(finite);
	}
}

TEST_CASE("Airport source climate guards preserve distinct Toyland terminal artwork", "[renderer3d][voxel]")
{
	for (unsigned graphics = 0; graphics < 74; ++graphics) {
		for (unsigned climate = 0; climate < 3; ++climate) CHECK(AirportModelClimateSupported(graphics,climate));
		bool replaced = (graphics >= 19 && graphics <= 28) || graphics == 43 || graphics == 47;
		CHECK(AirportModelClimateSupported(graphics,3) == !replaced);
		CHECK_FALSE(AirportModelClimateSupported(graphics,4));
	}
}

TEST_CASE("Airport climate bindings select only the active source and animation frame", "[renderer3d][voxel]")
{
	for (unsigned frame = 0; frame < 12; ++frame) {
		uint64_t shared = uint64_t{1}<<frame;
		for (unsigned climate = 0; climate < 4; ++climate) {
			unsigned state = climate*16+frame;
			uint64_t explicit_state = uint64_t{1}<<state;
			CHECK(SelectVoxelAirportState(shared|explicit_state,frame,climate,false) == state);
			CHECK(SelectVoxelAirportState(shared|explicit_state,frame,climate,true) == state);
			CHECK(SelectVoxelAirportState(shared,frame,climate,true) == frame);
			if (climate != 0) CHECK_FALSE(SelectVoxelAirportState(shared,frame,climate,false));
			for (unsigned other = 0; other < 4; ++other) if (other != climate) {
				CHECK_FALSE(SelectVoxelAirportState(explicit_state,frame,other,false));
			}
			CHECK_FALSE(SelectVoxelAirportState(explicit_state,(frame+1)%12,climate,true));
		}
	}
	CHECK_FALSE(SelectVoxelAirportState(UINT64_MAX,16,0,true));
	CHECK_FALSE(SelectVoxelAirportState(UINT64_MAX,0,4,true));
	CHECK_FALSE(AirportModelClimateSupported(74,0));
}

TEST_CASE("Tunnel directions connect paired portals without moving the track centre", "[renderer3d]")
{
	for (unsigned direction = 0; direction < 4; ++direction) {
		Vec3 a = TunnelPoint(direction,{0,8,0}), b = TunnelPoint(direction,{16,8,0});
		CHECK(Dot(b-a,b-a) == Approx(256));
		Vec3 exit = TunnelPoint((direction+2)%4,{8,8,0})+(b-a)*3;
		Vec3 expected = TunnelPoint(direction,{56,8,0});
		CHECK(exit == expected);
		CHECK(TunnelPoint(direction,{8,8,6}) == Vec3{8,8,6});
	}
}

TEST_CASE("Captured contact wires retain grade, diagonal and bridge elevations", "[renderer3d]")
{
	ContactWireSegment slope{{32,56,18},{48,56,26}};
	auto [contact,distance] = slope.Nearest({36,57,0});
	CHECK(contact == Vec3{36,56,20});
	CHECK(distance == Approx(1));
	CHECK(slope.Nearest({30,56,100}).first == slope.first);
	CHECK(slope.Nearest({50,56,100}).first == slope.last);
	ContactWireSegment chord{{64,72,42},{72,64,42}};
	CHECK(chord.Nearest({68,68,0}).first == Vec3{68,68,42});
	CHECK(chord.Nearest({68,68,0}).second == Approx(0));
	ContactWireSegment empty{{1,1,1},{1,1,2}};
	CHECK_THROWS(empty.Nearest({1,1,1}));
}

TEST_CASE("Electric collectors retain roof mounts while following both tunnel mouths", "[renderer3d][voxel]")
{
	for (float length : {16.0f,64.0f,256.0f}) {
		for (float x = -16; x <= length+32; x += 0.5f) {
			float height = TunnelPairContactWireHeight(x,length);
			CHECK(height == Approx(TunnelPairContactWireHeight(length+16-x,length)));
			if (x <= 0 || x >= length+16) CHECK(height == Approx(10));
			if (x >= 6.5f && x <= length+9.5f) CHECK(height == Approx(7.55));
			for (auto [mount,top] : {std::pair{6.5f,10.25f},std::pair{6.625f,9.375f}}) {
				InstanceData data;
				data.origin_opacity = {17,29,32,1};
				data.SetObjectId(513);
				FitVoxelCollectorToWire(data,mount,top,height);
				Vertex base{},contact{};
				base.position = {1,2,mount}; contact.position = {1,2,top};
				base.normal = contact.normal = {0,0,1};
				CHECK(ResolveInstanceVertex(base,data).position.z == Approx(32+mount));
				CHECK(ResolveInstanceVertex(contact,data).position.z == Approx(32+height));
				CHECK(data.ObjectId() == 513);
			}
		}
	}
	InstanceData invalid;
	CHECK_THROWS(FitVoxelCollectorToWire(invalid,6.5f,6.5f,10));
	CHECK_THROWS(FitVoxelCollectorToWire(invalid,6.5f,10.25f,6));
	CHECK_THROWS(FitVoxelCollectorToWire(invalid,6.5f,10.25f,INFINITY));
}

TEST_CASE("Underground labels are visible through mouths rather than through walls", "[renderer3d]")
{
	for (unsigned kind = 0; kind < 6; ++kind) {
		auto type = static_cast<TunnelKind>(kind);
		CHECK(VisibleThroughTunnelMouth(type,48,{20,8,6},{100,8,6}));
		CHECK(VisibleThroughTunnelMouth(type,48,{20,8,6},{-20,8,6}));
		CHECK_FALSE(VisibleThroughTunnelMouth(type,48,{20,8,6},{24,8,20}));
		CHECK_FALSE(VisibleThroughTunnelMouth(type,48,{20,8,6},{100,40,6}));
		CHECK_FALSE(VisibleThroughTunnelMouth(type,48,{20,8,6},{100,8,50}));
	}
}

TEST_CASE("Tunnel scenery regions conservatively retain both mouths and crossing bounds", "[renderer3d]")
{
	for (auto kind : {TunnelKind::Rail,TunnelKind::ElectricRail,TunnelKind::Monorail,TunnelKind::Maglev,TunnelKind::Road,TunnelKind::Tram}) {
		CHECK(TunnelSceneryRegions(kind,48,{7,8,4},{},2).empty());
		CHECK(TunnelSceneryRegions(kind,48,{20,8,20},{},2).empty());
		for (unsigned direction = 0; direction < 4; ++direction) for (Vec3 origin : {Vec3{},Vec3{500000,700000,96}}) {
			Vec3 eye{20,8,4};
			auto regions = TunnelSceneryRegions(kind,48,eye,origin,direction);
			REQUIRE(regions.size() == 3);
			auto retained = [&](Vec3 low, Vec3 high) {
				Vec3 a = origin+TunnelPoint(direction,low), b = origin+TunnelPoint(direction,high);
				Vec3 first{std::min(a.x,b.x),std::min(a.y,b.y),std::min(a.z,b.z)};
				Vec3 last{std::max(a.x,b.x),std::max(a.y,b.y),std::max(a.z,b.z)};
				return std::ranges::any_of(regions,[&](const ClipVolume &region) { return region.Intersects(first,last); });
			};
			CHECK(retained({18,7,2},{22,9,6}));
			CHECK_FALSE(retained({18,7,20},{22,9,24}));
			CHECK_FALSE(retained({18,40,2},{22,44,6}));
			CHECK(retained({80,-30,0},{100,40,12})); // A box can cross the cone without containing a mouth.
			CHECK(retained({1000000,8,4},{1000001,9,5})); // No draw-distance limit.
			for (float x : {-100.0f,-1.0f,60.0f,100.0f,500.0f}) for (float y = -20; y <= 40; y += 3) for (float z = -3; z <= 25; z += 2) {
				Vec3 point{x,y,z};
				if (VisibleThroughTunnelMouth(kind,48,eye,point)) CHECK(retained(point,point));
			}
		}
	}
}

TEST_CASE("Industry source-climate replacements retain independent ground and body ownership", "[renderer3d][voxel]")
{
	for (unsigned graphic : {16U,17U,33U,34U,35U,36U,37U,38U}) {
		CHECK(IndustryModelClimateSupported(graphic,0));
		for (unsigned climate : {1U,2U,3U}) CHECK_FALSE(IndustryModelClimateSupported(graphic,climate));
	}
	for (unsigned graphic : {32U,39U,60U,63U}) for (unsigned climate = 0; climate < 4; ++climate) CHECK(IndustryModelClimateSupported(graphic,climate));
	for (unsigned climate = 1; climate < 4; ++climate) {
		CHECK(IndustryModelClimateSupported(7,climate,false,2035));
		CHECK_FALSE(IndustryModelClimateSupported(7,climate,true,3924));
		CHECK(IndustryModelClimateSupported(29,climate,false,2174));
		CHECK_FALSE(IndustryModelClimateSupported(29,climate,true,2173));
		CHECK(IndustryModelClimateSupported(29,climate,true,2022) == (climate != 3));
		CHECK(IndustryModelClimateSupported(18,climate,true,1420));
	}
	for (unsigned climate = 0; climate < 4; ++climate) {
		for (unsigned graphic : {129U,130U}) {
			for (unsigned sprite = 2072; sprite <= 2076; ++sprite) CHECK(IndustryModelClimateSupported(graphic,climate,false,sprite) == (climate == 3));
			CHECK(IndustryModelClimateSupported(graphic,climate,true,2077) == (climate == 3));
		}
		for (unsigned graphic : {131U,132U,133U,134U,138U,139U,140U,141U}) {
			CHECK(IndustryModelClimateSupported(graphic,climate));
			CHECK(IndustryModelClimateSupported(graphic,climate,true,2022) == (climate == 3));
		}
		for (unsigned graphic : {135U,136U,137U}) {
			CHECK(IndustryModelClimateSupported(graphic,climate));
			CHECK(IndustryModelClimateSupported(graphic,climate,true,2077) == (climate == 3));
		}
		for (unsigned graphic : {26U,27U,28U}) CHECK(IndustryModelClimateSupported(graphic,climate) == (climate != 3));
		CHECK(IndustryModelClimateSupported(67,climate,false,2206) == (climate != 3));
		CHECK(IndustryModelClimateSupported(67,climate,false,2221)); // Unchanged construction remains independently bound.
		CHECK(IndustryModelClimateSupported(24,climate,false,2094));
		CHECK(IndustryModelClimateSupported(24,climate,true,4061) == (climate != 3));
		CHECK(IndustryModelClimateSupported(39,climate,true,2146));
		for (auto [graphic,sprite] : {std::pair{82U,2257U},std::pair{85U,2260U},std::pair{86U,2261U}}) {
			CHECK(IndustryModelClimateSupported(graphic,climate,true,sprite) == (climate != 3));
			CHECK(IndustryModelClimateSupported(graphic,climate,true,sprite-16)); // Dry construction remains independently bound.
		}
		CHECK(IndustryModelClimateSupported(75,climate,false,2250));
		CHECK(IndustryModelClimateSupported(75,climate,true,2022) == (climate != 3));
	}
}

TEST_CASE("Industry climate bindings prefer explicit artwork without leaking shared source states", "[renderer3d][voxel]")
{
	uint64_t shared = 15, arctic = shared<<16, toyland = shared<<48;
	for (unsigned stage = 0; stage < 4; ++stage) {
		CHECK(SelectVoxelIndustryState(shared|arctic,stage,0,true) == stage);
		CHECK(SelectVoxelIndustryState(shared|arctic,stage,1,false) == 16+stage);
		CHECK_FALSE(SelectVoxelIndustryState(shared,stage,1,false)); // No temperate forest in Arctic.
		CHECK_FALSE(SelectVoxelIndustryState(arctic,stage,0,true)); // No snow in temperate.
		CHECK(SelectVoxelIndustryState(shared,stage,2,true) == stage); // Proven shared source.
		CHECK_FALSE(SelectVoxelIndustryState(shared|arctic,stage,2,false));
		CHECK(SelectVoxelIndustryState(shared|toyland,stage,3,true) == 48+stage);
		CHECK(SelectVoxelIndustryState(shared,stage,3,true) == stage); // Original Toyland-only base.
		CHECK_FALSE(SelectVoxelIndustryState(shared,stage,0,false));
		uint64_t missing = (shared|arctic)&~(uint64_t{1}<<(16+stage));
		CHECK_FALSE(SelectVoxelIndustryState(missing,stage,1,false));
		CHECK(SelectVoxelIndustryState(missing,stage,1,true) == stage);
	}
	for (unsigned stage : {4U,15U,16U,19U,UINT_MAX}) CHECK_FALSE(SelectVoxelIndustryState(UINT64_MAX,stage,1,true));
	for (unsigned climate : {4U,16U,UINT_MAX}) CHECK_FALSE(SelectVoxelIndustryState(UINT64_MAX,0,climate,true));
}

TEST_CASE("Toy-factory source children preserve physical press and conveyor motion", "[renderer3d][voxel]")
{
	unsigned clay = 0, robots = 0, stamp = 0, holder = 0;
	std::set<int> stamp_positions;
	for (unsigned frame = 0; frame < 50; ++frame) {
		auto children = VoxelToyFactoryChildren(frame);
		for (unsigned slot = 0; slot < children.size(); ++slot) {
			const auto &child = children[slot];
			if (child.image == 0) continue;
			float sx = 2*(child.offset.y-child.offset.x), sy = child.offset.x+child.offset.y-child.offset.z;
			if (slot == 0 || slot == 1) {
				CHECK(child.image == (slot == 0 ? 4719 : 4720));
				CHECK(sx == child.x-(slot == 0 ? 50 : 16));
				CHECK(sy == child.y-(slot == 0 ? 96 : 100));
				CHECK(child.offset.y == 0); CHECK(child.offset.z == 0);
				(slot == 0 ? clay : robots)++;
			} else if (slot == 2) {
				CHECK(child.image == 4718); CHECK(child.x == 7);
				CHECK(child.offset.x == 0); CHECK(child.offset.y == 0);
				CHECK(sy == child.y); CHECK(child.offset.z >= -29);
				stamp_positions.insert(child.y); ++stamp;
			} else {
				CHECK(child.image == 4717); CHECK(child.x == 0); CHECK(child.y == 42);
				CHECK(Dot(child.offset,child.offset) == 0); ++holder;
			}
		}
	}
	CHECK(clay == 29); CHECK(robots == 19); CHECK(stamp == 50); CHECK(holder == 50);
	CHECK(stamp_positions == std::set<int>{0,1,2,4,6,8,11,14,17,20,24,29});
	for (unsigned frame : {0U,49U}) {
		auto children = VoxelToyFactoryChildren(frame);
		CHECK(children[0].image == 0); CHECK(children[1].image == 0);
	}
	CHECK_THROWS_AS(VoxelToyFactoryChildren(50),std::invalid_argument);
}

TEST_CASE("Bubble-generator children preserve construction absence and axial plunger travel", "[renderer3d][voxel]")
{
	std::set<int> heights;
	for (unsigned stage = 0; stage < 4; ++stage) for (unsigned frame = 0; frame < 40; ++frame) {
		auto children = VoxelBubbleGeneratorChildren(stage,frame);
		CHECK(children[0].image == (stage == 3 ? 4747 : 0));
		CHECK(children[1].image == (stage != 0 ? 4746 : 0));
		CHECK(Dot(children[1].offset,children[1].offset) == 0);
		if (stage != 0) { CHECK(children[1].x == 3); CHECK(children[1].y == 67); }
		if (stage != 3) continue;
		const auto &plunger = children[0];
		CHECK(plunger.x == 5); CHECK(plunger.y >= 68); CHECK(plunger.y <= 86);
		CHECK(plunger.offset.x == 0); CHECK(plunger.offset.y == 0);
		CHECK(-plunger.offset.z == plunger.y-68);
		heights.insert(plunger.y);
	}
	CHECK(heights.size() == 19);
	CHECK(VoxelBubbleGeneratorChildren(3,0)[0].offset.z == 0);
	CHECK(VoxelBubbleGeneratorChildren(3,39)[0].offset.z == 0);
	for (unsigned frame = 8; frame <= 21; ++frame) CHECK(VoxelBubbleGeneratorChildren(3,frame)[0].offset.z == -18);
	for (unsigned stage = 0; stage < 3; ++stage) {
		auto children = VoxelBubbleGeneratorChildren(stage,255);
		CHECK(children[0].image == 0);
		CHECK(children[1].image == (stage == 0 ? 0 : 4746));
	}
	CHECK_THROWS_AS(VoxelBubbleGeneratorChildren(4,0),std::invalid_argument);
	CHECK_THROWS_AS(VoxelBubbleGeneratorChildren(3,40),std::invalid_argument);
}

TEST_CASE("Sugar-mine crossbar motion preserves source fill states and genuine child absences", "[renderer3d][voxel]")
{
	std::array<unsigned,15> appearances{};
	std::array<unsigned,4> child_counts{};
	std::set<int> positions;
	for (unsigned frame = 0; frame < 96; ++frame) {
		auto children = VoxelSugarMineChildren(3,frame);
		const auto &sieve = children[0];
		REQUIRE(sieve.image >= 4775); REQUIRE(sieve.image <= 4779);
		CHECK(sieve.y == 0); CHECK(sieve.offset.z == 0);
		CHECK(sieve.offset.x+sieve.offset.y == 0);
		CHECK(2*(sieve.offset.y-sieve.offset.x) == sieve.x-8);
		positions.insert(sieve.x);
		unsigned visible = 0;
		for (const auto &child : children) if (child.image != 0) {
			REQUIRE(child.image >= 4775); REQUIRE(child.image <= 4789);
			++appearances[child.image-4775]; ++visible;
		}
		++child_counts[visible];
		if (children[1].image != 0) {
			CHECK(children[1].image >= 4784); CHECK(children[1].image <= 4789);
			CHECK(children[1].x == 8); CHECK(children[1].y == 41);
		}
		if (children[2].image != 0) {
			CHECK(children[2].image >= 4780); CHECK(children[2].image <= 4783);
		}
	}
	CHECK(positions == std::set<int>{4,6,8,10,12});
	CHECK(appearances == std::array<unsigned,15>{15,16,16,16,33,12,11,11,51,11,11,11,11,11,11});
	CHECK(child_counts == std::array<unsigned,4>{0,1,39,56});
	CHECK(VoxelSugarMineChildren(3,0)[0].image == 4779);
	CHECK(VoxelSugarMineChildren(3,95)[2].x == 10);
	CHECK(VoxelSugarMineChildren(3,95)[2].y == 66);
	for (unsigned stage = 0; stage < 3; ++stage) for (const auto &child : VoxelSugarMineChildren(stage,255)) CHECK(child.image == 0);
	for (unsigned climate = 0; climate < 4; ++climate) for (unsigned graphics = 171; graphics <= 174; ++graphics) {
		CHECK(IndustryModelClimateSupported(graphics,climate,false,4773));
		CHECK(IndustryModelClimateSupported(graphics,climate,true,3981) == (climate == 3));
	}
	CHECK_THROWS_AS(VoxelSugarMineChildren(4,0),std::invalid_argument);
	CHECK_THROWS_AS(VoxelSugarMineChildren(3,96),std::invalid_argument);
}

TEST_CASE("Toffee cutter follows its inclined shaft and never treats sound markers as absence", "[renderer3d][voxel]")
{
	std::set<int> positions;
	for (unsigned frame = 0; frame < 70; ++frame) {
		auto children = VoxelToffeeQuarryChildren(3,frame);
		const auto &shovel = children[0], &redraw = children[1];
		CHECK(shovel.image == 4767); CHECK(redraw.image == 4766);
		CHECK(redraw.x == 6); CHECK(redraw.y == 14); CHECK(Dot(redraw.offset,redraw.offset) == 0);
		CHECK(shovel.x >= 12); CHECK(shovel.x <= 22); CHECK(shovel.x+shovel.y == 46);
		CHECK(shovel.offset.y == 0); CHECK(shovel.offset.z == -shovel.offset.x);
		CHECK(2*(shovel.offset.y-shovel.offset.x) == shovel.x-22);
		CHECK(shovel.offset.x+shovel.offset.y-shovel.offset.z == shovel.y-24);
		if (frame%14 == 0) CHECK(Dot(shovel.offset,shovel.offset) == 0);
		positions.insert(shovel.x);
	}
	CHECK(positions.size() == 11);
	for (unsigned stage = 0; stage < 3; ++stage) {
		auto children = VoxelToffeeQuarryChildren(stage,255);
		CHECK(children[0].image == 4767); CHECK(children[1].image == 4766);
		CHECK(children[0].x == 22); CHECK(children[0].y == 24);
		CHECK(Dot(children[0].offset,children[0].offset) == 0);
	}
	for (unsigned climate = 0; climate < 4; ++climate) for (unsigned graphics = 164; graphics <= 166; ++graphics) {
		CHECK(IndustryModelClimateSupported(graphics,climate,false,4763));
		CHECK(IndustryModelClimateSupported(graphics,climate,true,3981) == (climate == 3));
	}
	CHECK_THROWS_AS(VoxelToffeeQuarryChildren(4,0),std::invalid_argument);
	CHECK_THROWS_AS(VoxelToffeeQuarryChildren(3,70),std::invalid_argument);
}

TEST_CASE("Tunnel excavation removes intersecting terrain while retaining the shoulders and charts", "[renderer3d]")
{
	Scene terrain;
	terrain.Quad({0,0,6},{16,0,6},{16,16,6},{0,16,6},{});
	for (auto &vertex : terrain.vertices) vertex.texture = {vertex.position.x,vertex.position.y,0};
	for (unsigned direction = 0; direction < 4; ++direction) {
		TunnelAssembly clipped;
		clipped.parts[0] = CutTunnelTerrain(terrain.vertices,TunnelKind::Rail,direction,0);
		CHECK_FALSE(std::isfinite(FirstHit(clipped,{{8,8,5},{0,0,1}})));
		Vec3 shoulder = TunnelPoint(direction,{8,1,5});
		CHECK(FirstHit(clipped,{shoulder,{0,0,1}}) == Approx(1));
		for (const auto &vertex : clipped.parts[0]) {
			CHECK(vertex.texture.x == Approx(vertex.position.x));
			CHECK(vertex.texture.y == Approx(vertex.position.y));
		}
	}
}

TEST_CASE("Voxel ground excavation keeps palette indices and clears the complete soil slab", "[renderer3d][voxel]")
{
	VoxelGrid grid({32,32,2},{{{112,112,112,112,112,112}},{{2,2,2,2,2,2}}},{0,0,5.5f},{0.5f,0.5f,0.25f});
	grid.Fill({0,0,0},{32,32,2},1);
	grid.Fill({4,0,0},{8,32,2},2);
	auto terrain = grid.Mesh();
	for (TunnelKind kind : {TunnelKind::Rail,TunnelKind::Road}) for (unsigned direction = 0; direction < 4; ++direction) {
		TunnelAssembly clipped;
		clipped.parts[0] = CutTunnelTerrain(terrain.vertices,kind,direction,0);
		CHECK_FALSE(std::isfinite(FirstHit(clipped,{{8,8,5},{0,0,1}})));
		Vec3 shoulder = TunnelPoint(direction,{8,1,5});
		CHECK(FirstHit(clipped,{shoulder,{0,0,1}}) == Approx(0.5f));
		for (const auto &vertex : clipped.parts[0]) {
			CHECK(static_cast<uint32_t>(vertex.surface) == (static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT));
			CHECK((vertex.texture.x == (112.5f/256) || vertex.texture.x == (2.5f/256)));
			CHECK(vertex.opacity == 1);
		}
	}
}

TEST_CASE("Tunnel excavation respects translated roots and the ends of its segment", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,4,10},{{{105,105,105,105,105,105}}},{-1,-1,-0.75f},{0.5f,0.5f,0.5f});
	grid.Fill({0,0,0},{4,4,10},1);
	auto root = grid.Mesh();
	for (unsigned direction = 0; direction < 4; ++direction) {
		Vec3 anchor = TunnelPoint(direction,{8,8,8});
		TunnelAssembly clipped;
		clipped.parts[0] = CutTunnelTerrain(root.vertices,TunnelKind::Rail,direction,0,anchor);
		float removed_low = 7.25f-anchor.z, kept_high = 12.25f-anchor.z;
		/* The underground side is removed; the above-ground top remains. */
		CHECK_FALSE(std::isfinite(FirstHit(clipped,{{-2,0,removed_low+0.1f},{1,0,0}})));
		CHECK(FirstHit(clipped,{{0,0,kept_high+1},{0,0,-1}}) == Approx(1));
		for (const auto &vertex : clipped.parts[0]) {
			CHECK(vertex.position.z+anchor.z >= 7.6f);
			CHECK(vertex.texture.x == 105.5f/256);
		}
		/* A root beyond this underground section must be kept in its original
		 * local coordinates, even if its cross-section enters the infinite bore. */
		Vec3 outside = TunnelPoint(direction,{-3,8,8});
		auto retained = CutTunnelTerrain(root.vertices,TunnelKind::Rail,direction,0,outside);
		REQUIRE(retained.size() == root.vertices.size());
		for (size_t i = 0; i < retained.size(); ++i) CHECK(retained[i].position == root.vertices[i].position);
	}
}

TEST_CASE("Raised source-owner grounds keep above-vault relief through independent LOD tunnel cuts", "[renderer3d][voxel]")
{
	/* The same tunnel subtraction used by ClippedGroundMesh must not flatten a
	 * raised original ground owner. Stress a near-vault diagnostic slab as well
	 * as the ordinary doubled-height separation; no actual map is modified. */
	std::array<VoxelGrid,4> owners{
		VoxelGrid({64,64,24},{{{72,73,74,75,76,77}}},{0,0,-0.5f},{0.5f,0.5f,0.5f}),
		VoxelGrid({64,64,24},{{{72,73,74,75,76,77}}},{-16,0,-0.5f},{0.5f,0.5f,0.5f}),
		VoxelGrid({64,64,24},{{{72,73,74,75,76,77}}},{0,-16,-0.5f},{0.5f,0.5f,0.5f}),
		VoxelGrid({64,64,24},{{{72,73,74,75,76,77}}},{-16,-16,-0.5f},{0.5f,0.5f,0.5f})};
	for (int z = 0; z < 24; ++z) for (int y = 0; y < 64; ++y) for (int x = 0; x < 64; ++x) {
		if (z != 0 && !(x >= 8 && x < 56 && y >= 8 && y < 56)) continue;
		unsigned owner = (2*x-z >= 64) | ((2*y-z >= 64)<<1);
		owners[owner].Fill({x,y,z},{x+1,y+1,z+1},1);
	}
	for (unsigned part = 0; part < owners.size(); ++part) for (unsigned factor : {1U,2U,4U,8U,16U}) {
		CAPTURE(part,factor);
		auto mesh = owners[part].ReducedMesh(factor,true);
		for (TunnelKind kind : {TunnelKind::Rail,TunnelKind::Road}) for (unsigned direction = 0; direction < 4; ++direction) {
			CAPTURE(kind,direction);
			/* A legal full doubled terrain level above the bore is untouched. */
			CHECK_FALSE(GroundIntersectsTunnelVault(mesh.vertices,-16));
			auto retained = CutTunnelTerrain(mesh.vertices,kind,direction,-16);
			REQUIRE(retained.size() == mesh.vertices.size());
			CHECK(std::memcmp(retained.data(),mesh.vertices.data(),retained.size()*sizeof(Vertex)) == 0);
			CHECK(GroundIntersectsTunnelVault(mesh.vertices,0));
			TunnelAssembly clipped; clipped.parts[0] = CutTunnelTerrain(mesh.vertices,kind,direction,0);
			Vec3 top = TunnelPoint(direction,{8,8,12.5f});
			TunnelAssembly uncut; uncut.parts[0] = mesh.vertices;
			CHECK(FirstHit(uncut,{top,{0,0,-1}}) == Approx(1));
			CHECK(FirstHit(clipped,{top,{0,0,-1}}) == Approx(1));
			Vec3 bore = TunnelPoint(direction,{8,8,-0.25f});
			CHECK(FirstHit(clipped,{bore,{0,0,1}}) > 7.75f);
			CHECK(std::ranges::all_of(clipped.parts[0],[](const Vertex &vertex) {
				return vertex.texture.x >= 72.5f/256 && vertex.texture.x <= 77.5f/256 && vertex.opacity == 1;
			}));
			/* Every upper source triangle survives as the same three vertex words
			 * in source order, including its normal, paint and surface identity. */
			size_t cursor = 0;
			for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
				if (GroundIntersectsTunnelVault(std::span(mesh.vertices).subspan(i,3),0)) continue;
				while (cursor < clipped.parts[0].size() && std::memcmp(&mesh.vertices[i],&clipped.parts[0][cursor],3*sizeof(Vertex)) != 0) cursor += 3;
				REQUIRE(cursor < clipped.parts[0].size());
				cursor += 3;
			}
		}
	}
}

TEST_CASE("Rail routes join the upstream edge ports with continuous gauge", "[renderer3d]")
{
	static_assert(TRACK_X == 0 && TRACK_Y == 1 && TRACK_UPPER == 2 && TRACK_LOWER == 3 && TRACK_LEFT == 4 && TRACK_RIGHT == 5);
	const Vec3 ports[][2] = {{{0,8,0},{16,8,0}},{{8,0,0},{8,16,0}},{{0,8,0},{8,0,0}},
		{{16,8,0},{8,16,0}},{{16,8,0},{8,0,0}},{{0,8,0},{8,16,0}}};
	for (unsigned track = 0; track < 6; ++track) {
		for (unsigned end = 0; end < 2; ++end) {
			auto frame = RailPath(track,static_cast<float>(end));
			CHECK(frame.point == ports[track][end]);
			CHECK(Dot(ports[track][1]-ports[track][0],frame.across) == Approx(0).margin(0.00001f));
		}
		for (unsigned step = 0; step <= 16; ++step) {
			auto frame = RailPath(track,step/16.0f);
			CHECK(Dot(frame.across,frame.across) == Approx(1));
			Vec3 a = frame.point-frame.across*1.3f, b = frame.point+frame.across*1.3f;
			CHECK(Dot(b-a,b-a) == Approx(2.6f*2.6f));
			if (track >= 2) {
				float x = track == 3 || track == 4 ? 16-frame.point.x : frame.point.x;
				float y = track == 3 || track == 5 ? 16-frame.point.y : frame.point.y;
				CHECK(x+y == Approx(8));
			}
		}
	}
}

TEST_CASE("Voxel rail heads follow straight bands and match adjoining diagonal tiles", "[renderer3d]")
{
	for (unsigned type = 0; type < 4; ++type) for (unsigned track = 2; track < 6; ++track) for (unsigned lod = 0; lod < 3; ++lod) {
		auto assembly = MakeRailAssembly(type,track,{},lod);
		auto frame = RailPath(track,0);
		const auto &rails = assembly.parts[static_cast<unsigned>(RailMaterial::Rails)];
		bool straight = true;
		for (const auto &vertex : rails) {
			float distance = std::abs(Dot(vertex.position-frame.point,frame.across));
			/* Bounds include the projected half-cell width of the transport
			 * lattice, not the formerly smooth swept rail profile. */
			straight &= type <= 1 ? distance >= 0.9999f && distance <= 1.6001f :
				type == 2 ? distance <= 0.7501f : distance >= 3.2499f && distance <= 4.0001f;
			CHECK(vertex.position.x*8 == Approx(std::round(vertex.position.x*8))); // Boundary-fan centres may use half a cell.
			CHECK(vertex.position.y*8 == Approx(std::round(vertex.position.y*8)));
			CHECK((static_cast<unsigned>(vertex.surface)&15U) == static_cast<unsigned>(SurfaceMode::Palette));
		}
		INFO("type=" << type << " track=" << track << " lod=" << lod);
		CHECK(straight);
	}
	/* A voxel diagonal stair changes row at the tile edge just as inside a tile.
	 * Neighbouring steps must share positive-area faces, not just a corner. */
	for (unsigned type = 0; type < 4; ++type) {
		auto upper = MakeRailAssembly(type,2,{}), lower = MakeRailAssembly(type,3,{});
		auto on_cap = [&](const auto &vertices, Ray ray) {
			for (size_t i = 0; i < vertices.size(); i += 3) {
				auto hit = TriangleHit(ray,vertices[i].position,vertices[i+1].position,vertices[i+2].position);
				if (hit && std::abs(*hit-0.25f) < 0.0001f) return true;
			}
			return false;
		};
		unsigned shared = 0;
		for (unsigned x = 0; x < 64; ++x) {
			float height = type <= 1 ? 0.375f : 0.625f;
			bool a = on_cap(upper.parts[static_cast<unsigned>(RailMaterial::Rails)],{{(x+0.5f)*0.25f,-0.25f,height},{0,1,0}});
			bool b = on_cap(lower.parts[static_cast<unsigned>(RailMaterial::Rails)],{{(x+0.5f)*0.25f,16.25f,height},{0,-1,0}});
			shared += a && b;
		}
		CHECK(shared >= 2);
	}
	/* Distant flat straight runs may use fewer longitudinal cells, but their
	 * running-head height, gauge and complete cross-section stay identical. */
	for (unsigned type = 0; type < 4; ++type) for (unsigned track = 0; track < 2; ++track) {
		auto medium = MakeRailAssembly(type,track,{},1), distant = MakeRailAssembly(type,track,{},2);
		const auto &a = medium.parts[static_cast<unsigned>(RailMaterial::Rails)], &b = distant.parts[static_cast<unsigned>(RailMaterial::Rails)];
		CHECK(b.size()*2 < a.size());
		auto hit = [](const std::vector<Vertex> &mesh, Ray ray) {
			float nearest = INFINITY;
			for (size_t i = 0; i < mesh.size(); i += 3) if (auto distance = TriangleHit(ray,mesh[i].position,mesh[i+1].position,mesh[i+2].position)) nearest = std::min(nearest,*distance);
			return nearest;
		};
		for (float t : {0.03125f,0.28125f,0.53125f,0.78125f,0.96875f}) for (int step = -40; step <= 40; ++step) {
			auto frame = RailPath(track,t);
			Ray ray{frame.point+frame.across*(step/8.0f)+Vec3{0,0,4},{0,0,-1}};
			float near_hit = hit(a,ray), far_hit = hit(b,ray);
			CHECK(std::isfinite(near_hit) == std::isfinite(far_hit));
			if (std::isfinite(near_hit)) CHECK(near_hit == Approx(far_hit).margin(0.000001f));
		}
	}
}

TEST_CASE("Low bridge decks clear Cab paths and contain their pillar caps", "[renderer3d]")
{
	for (unsigned type = 0; type <= 13; ++type) for (bool along_y : {false,true}) {
		TunnelAssembly bridge;
		for (BridgeRole role : {BridgeRole::Deck,BridgeRole::Front}) {
			auto mesh = MakeBridgeMesh({type,0,role,along_y});
			for (auto &v : mesh) v.position.z += 8;
			bridge.parts[0].insert(bridge.parts[0].end(),mesh.begin(),mesh.end());
		}
		for (float height : {6.0f,7.0f}) {
			Ray path = along_y ? Ray{{-1,8,height},{1,0,0}} : Ray{{8,-1,height},{0,1,0}};
			CHECK_FALSE(std::isfinite(FirstHit(bridge,path)));
		}
		CHECK(FirstHit(bridge,{{8,8,6},{0,0,1}}) == Approx(2-BRIDGE_DECK_THICKNESS));
		for (float segment_z : {5.0f,-3.0f,-11.0f}) {
			BridgeShape shape{type,4,BridgeRole::Pillar,along_y};
			shape.pillar_top = BridgePillarCap(8,segment_z);
			for (const auto &v : MakeBridgeMesh(shape)) CHECK(v.position.z+segment_z <= 8-BRIDGE_DECK_THICKNESS*0.5f+0.0001f);
		}
	}
}

TEST_CASE("Rail assemblies sit on legal gameplay foundations at every detail level", "[renderer3d]")
{
	std::set<std::pair<Slope,Track>> surfaces;
	for (unsigned value = 0; value < 32; ++value) {
		if (value >= 15 && value != 23 && value != 27 && value != 29 && value != 30) continue;
		for (unsigned bits = 1; bits <= TRACK_BIT_ALL; ++bits) {
			Slope slope = static_cast<Slope>(value);
			TrackBits tracks = static_cast<TrackBits>(bits);
			Foundation foundation = GetRailFoundation(slope,tracks);
			if (foundation == FOUNDATION_INVALID) continue;
			Corner upper = CORNER_INVALID;
			if (IsNonContinuousFoundation(foundation)) {
				upper = foundation == FOUNDATION_STEEP_BOTH ? GetHighestSlopeCorner(slope) : GetHalftileFoundationCorner(foundation);
				tracks &= ~CornerToTrackBits(upper);
				foundation = foundation == FOUNDATION_STEEP_BOTH ? FOUNDATION_STEEP_LOWER : FOUNDATION_NONE;
			}
			ApplyPixelFoundationToSlope(foundation,slope);
			for (Track track = TRACK_BEGIN; track < TRACK_END; ++track) if ((tracks & TrackToTrackBits(track)) != TRACK_BIT_NONE) surfaces.emplace(slope,track);
			if (IsValidCorner(upper)) {
				ApplyPixelFoundationToSlope(HalftileFoundation(upper),slope);
				surfaces.emplace(slope,FindFirstTrack(CornerToTrackBits(upper)));
			}
		}
	}
	for (auto [slope,track] : surfaces) for (unsigned type = 0; type < 4; ++type) for (unsigned lod = 0; lod < 3; ++lod) {
		INFO("slope=" << to_underlying(slope) << " track=" << to_underlying(track) << " type=" << type << " lod=" << lod);
		auto surface = MakeTileSurface(slope);
		auto assembly = MakeRailAssembly(type,to_underlying(track),surface,lod);
		bool finite = true, supported = true, contained = true;
		for (const auto &part : assembly.parts) for (const auto &v : part) {
			finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z);
			/* The base layer embeds by at most one vertical cell plus the
			 * terrain change across a ground cell; there are no floating feet. */
			supported &= v.position.z >= surface.Height(v.position.x,v.position.y)-0.3751f;
			supported &= v.position.z <= surface.Height(v.position.x,v.position.y)+(type < 2 ? 0.5f : 1.0f)+0.3751f;
			contained &= v.position.x >= 0 && v.position.x <= 16 && v.position.y >= 0 && v.position.y <= 16;
		}
		CHECK(finite); CHECK(supported); CHECK(contained);
		const auto &rails = assembly.parts[static_cast<unsigned>(RailMaterial::Rails)];
		REQUIRE_FALSE(rails.empty());
		if (type < 2 && track < TRACK_UPPER) for (float distance : {4.0f,8.0f,12.0f}) for (float side : {-1.3f,1.3f}) {
			auto frame = RailPath(to_underlying(track),distance/16);
			Vec3 p = frame.point+frame.across*side;
			float ground = surface.Height(p.x,p.y), hit = 100;
			for (size_t i = 0; i < rails.size(); i += 3) if (auto ray = TriangleHit({{p.x,p.y,ground+2},{0,0,-1}},rails[i].position,rails[i+1].position,rails[i+2].position)) hit = std::min(hit,*ray);
			CHECK(hit <= 1.5001f);
			CHECK(hit >= 1.1249f);
			RailSupportSurface support{{},surface,type,static_cast<unsigned>(TrackToTrackBits(track))};
			auto contact = support.Contact(p);
			REQUIRE(contact.has_value());
			CHECK(contact->stepped == Approx(ground+2-hit).margin(0.0001f));
			CHECK(contact->stepped >= contact->smooth-0.0001f);
			CHECK(contact->stepped-contact->smooth <= 0.3751f);
		}
	}
}

TEST_CASE("Bridge rail supports match the ramp deck in all four world orientations", "[renderer3d]")
{
	for (unsigned direction = 0; direction < 4; ++direction) {
		auto surface = MakeTileSurface(InclinedSlope(static_cast<DiagDirection>(direction)));
		RailSupportSurface support{{128,256,16},surface,0,1U<<(direction%2)};
		for (float distance : {0.125f,3.125f,8.125f,15.125f}) {
			Vec3 p = direction%2 == 0 ? Vec3{distance,8,0} : Vec3{8,distance,0};
			auto contact = support.Contact(p+support.origin);
			REQUIRE(contact.has_value());
			CHECK(contact->smooth == Approx(16.5f+TerrainZ(BridgeRampHeight(direction,p.x,p.y))));
			CHECK(contact->stepped >= contact->smooth);
			CHECK(contact->stepped-contact->smooth <= 0.1251f);
		}
		CHECK_FALSE(support.Contact(support.origin+Vec3{1,1,0}));
		CHECK_FALSE(support.Contact(support.origin+Vec3{-1,8,0}));
		CHECK_FALSE(support.Contact(support.origin+Vec3{16,8,0}));
	}
}

TEST_CASE("Maglev junction guide walls leave every running route open", "[renderer3d]")
{
	for (unsigned layout : {3U,5U,9U,17U,33U,12U,48U,63U}) for (unsigned lod : {0U,2U}) {
		TunnelAssembly walls;
		for (unsigned track = 0; track < 6; ++track) if (layout & (1U<<track)) {
			auto geometry = MakeRailAssembly(3,track,{},lod,layout);
			const auto &rails = geometry.parts[static_cast<unsigned>(RailMaterial::Rails)];
			walls.parts[0].insert(walls.parts[0].end(),rails.begin(),rails.end());
		}
		for (unsigned track = 0; track < 6; ++track) if (layout & (1U<<track)) {
			for (unsigned sample = 1; sample < 16; ++sample) for (float side : {-2.0f,0.0f,2.0f}) {
				auto frame = RailPath(track,sample/16.0f);
				Vec3 p = frame.point+frame.across*side+Vec3{0,0,2};
				INFO("layout=" << layout << " track=" << track << " sample=" << sample << " side=" << side << " lod=" << lod);
				CHECK_FALSE(std::isfinite(FirstHit(walls,{p,{0,0,-1}})));
			}
		}
	}
}

TEST_CASE("Maglev junction slabs agree on colours at shared tile-port surfaces", "[renderer3d][voxel]")
{
	const std::pair<unsigned,Vec3> cases[] = {
		{5,{2.125f,11.125f,2}},{9,{13.875f,4.875f,2}},
		{6,{11.125f,2.125f,2}},{10,{4.875f,13.875f,2}}
	};
	for (auto [layout,point] : cases) for (unsigned lod : {0U,1U,2U}) {
		std::set<unsigned> colours;
		unsigned routes = 0;
		for (unsigned track = 0; track < 6; ++track) if (layout & (1U<<track)) {
			auto assembly = MakeRailAssembly(3,track,{},lod,layout);
			const auto &slab = assembly.parts[static_cast<unsigned>(RailMaterial::Supports)];
			bool visible = false;
			for (size_t i = 0; i < slab.size(); i += 3) {
				if (slab[i].normal.z != 1) continue;
				if (auto hit = TriangleHit({point,{0,0,-1}},slab[i].position,slab[i+1].position,slab[i+2].position); hit && std::abs(*hit-1.75f) < 0.0001f) {
					colours.insert(static_cast<unsigned>(slab[i].texture.x*256));
					visible = true;
				}
			}
			routes += visible;
		}
		INFO("layout=" << layout << " lod=" << lod);
		CHECK(routes == 2);
		CHECK(colours.size() == 1);
	}
}

TEST_CASE("Station platforms and mirrored halls retain train and Cab clearance", "[renderer3d]")
{
	for (unsigned type = 0; type < 4; ++type) for (unsigned layout = 0; layout < 8; ++layout) {
		INFO("type=" << type << " layout=" << layout);
		auto assembly = MakeStationAssembly(type,layout);
		TunnelAssembly test;
		for (const auto &part : assembly.parts) test.parts[0].insert(test.parts[0].end(),part.begin(),part.end());
		for (float side : {6.0f,8.0f,10.0f}) {
			Ray forward = layout%2 == 0 ? Ray{{-1,side,6},{1,0,0}} : Ray{{side,-1,6},{0,1,0}};
			CHECK_FALSE(std::isfinite(FirstHit(test,forward)));
		}
		if (layout < 2) {
			Ray down = layout%2 == 0 ? Ray{{12,2,4},{0,0,-1}} : Ray{{2,12,4},{0,0,-1}};
			CHECK(FirstHit(test,down) == Approx(2).margin(0.03f));
		}
		bool finite = true, normals = true;
		for (const auto &part : assembly.parts) for (size_t i = 0; i < part.size(); i += 3) {
			Vec3 n = Normal(part[i].position,part[i+1].position,part[i+2].position);
			for (size_t j = i; j < i+3; ++j) {
				const auto &v = part[j];
				finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.texture.x+v.texture.y);
				normals &= Dot(v.normal,n) > 0.999f;
			}
		}
		CHECK(finite); CHECK(normals);
	}
}

TEST_CASE("Raised crop and rock details remain supported by all terrain slopes", "[renderer3d]")
{
	for (unsigned value = 0; value < 32; ++value) {
		if (value >= 15 && value != 23 && value != 27 && value != 29 && value != 30) continue;
		auto surface = MakeTileSurface(static_cast<Slope>(value));
		for (unsigned variant = 0; variant < 15; ++variant) for (unsigned lod = 0; lod < (variant < 9 ? 3U : 1U); ++lod) {
			INFO("slope=" << value << " variant=" << variant << " lod=" << lod);
			auto mesh = variant < 9 ? MakeFieldAssembly(variant,surface,lod) : MakeRockAssembly(variant == 10 ? 1 : 0,variant >= 11 ? variant-10 : 0,surface);
			bool finite = true, supported = true, contained = true;
			for (const auto &part : mesh.parts) for (const auto &vertex : part) {
				Vec3 p = vertex.position;
				finite &= std::isfinite(p.x+p.y+p.z+vertex.normal.x+vertex.normal.y+vertex.normal.z);
				supported &= p.z >= surface.Height(p.x,p.y)-0.001f;
				contained &= p.x >= 0 && p.x <= 16 && p.y >= 0 && p.y <= 16;
			}
			CHECK(finite); CHECK(supported); CHECK(contained);
		}
	}
	/* The reference's two hay stacks must have real three-unit tops, rather
	 * than merely adding rows of straw over the old flat painted image. */
	auto field = MakeFieldAssembly(8,{});
	TunnelAssembly hay;
	hay.parts[0] = field.parts[static_cast<unsigned>(GroundDetailMaterial::Hay)];
	CHECK(FirstHit(hay,{{3.1f,3.4f,10},{0,0,-1}}) == Approx(6.85f));
	CHECK(FirstHit(hay,{{10.6f,9.9f,10},{0,0,-1}}) == Approx(6.85f));
	CHECK_FALSE(std::isfinite(FirstHit(hay,{{8,8,10},{0,0,-1}})));
}

TEST_CASE("Catenary joins retain contact height and long-span messenger continuity", "[renderer3d]")
{
	CHECK(CatenaryRise(1,1) == Approx(CatenaryRise(0,2)));
	CHECK(CatenaryRise(0,1) == Approx(CatenaryRise(1,2)));
	for (unsigned track = 0; track < 6; ++track) for (int grade : {-8,0,8}) for (unsigned supports = 1; supports <= 3; ++supports) {
		TunnelAssembly wire;
		wire.parts[0] = MakeCatenaryWire(track,grade,supports);
		for (float t : {0.25f,0.5f,0.75f}) {
			Vec3 p = RailPath(track,t).point+Vec3{0,0,grade*t+8};
			float hit = FirstHit(wire,{p,{0,0,1}});
			INFO("track=" << track << " grade=" << grade << " supports=" << supports << " t=" << t);
			CHECK(hit > 1.9f); CHECK(hit < 2.1f);
		}
		bool finite = true;
		for (const auto &v : wire.parts[0]) finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z);
		CHECK(finite);
	}
}

TEST_CASE("Signal faces and semaphore swing follow the upstream direction convention", "[renderer3d]")
{
	const Vec3 faces[] = {{1,0,0},{-1,0,0},{0,-1,0},{0,1,0},{0.7071068f,-0.7071068f,0},
		{-0.7071068f,0.7071068f,0},{0.7071068f,0.7071068f,0},{-0.7071068f,-0.7071068f,0}};
	for (unsigned direction = 0; direction < 8; ++direction) {
		float heading = SignalHeading(direction);
		CHECK(Dot({std::cos(heading),std::sin(heading),0},faces[direction]) == Approx(1));
	}
	float red_top = 0, green_top = 0;
	for (bool green : {false,true}) {
		auto mesh = MakeSignalMesh(0,true,green);
		bool finite = true;
		for (const auto &v : mesh) {
			finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z);
			(green ? green_top : red_top) = std::max(green ? green_top : red_top,v.position.z);
		}
		CHECK(finite);
	}
	CHECK(green_top > red_top+2);
	CHECK(green_top < 16);
}

TEST_CASE("Depot doors retain vehicle clearance and tracks stop inside the back wall", "[renderer3d]")
{
	for (unsigned kind = 0; kind < 6; ++kind) for (unsigned direction = 0; direction < 4; ++direction) for (unsigned lod = 0; lod < 2; ++lod) {
		auto depot = MakeDepotAssembly(kind,direction,lod);
		TunnelAssembly whole;
		bool finite = true, bounded = true;
		for (size_t part = 0; part < depot.parts.size(); ++part) {
			if (part == static_cast<unsigned>(DepotMaterial::ReservedTrack)) continue;
			for (const auto &v : depot.parts[part]) {
				Vec3 p = v.position;
				finite &= std::isfinite(p.x+p.y+p.z+v.normal.x+v.normal.y+v.normal.z);
				bounded &= p.x >= -0.01f && p.x <= 16.01f && p.y >= -0.01f && p.y <= 16.01f && p.z >= -0.01f && p.z <= 24;
			}
			whole.parts[0].insert(whole.parts[0].end(),depot.parts[part].begin(),depot.parts[part].end());
		}
		INFO("kind=" << kind << " direction=" << direction << " lod=" << lod);
		CHECK(finite); CHECK(bounded);
		auto ray = [&](Vec3 a, Vec3 b) { return Ray{DepotPoint(direction,a),DepotPoint(direction,b)-DepotPoint(direction,a)}; };
		float bay = FirstHit(whole,ray({18,8,5},{17,8,5}));
		CHECK(bay > 13); CHECK(bay < 18);
		CHECK(FirstHit(whole,ray({18,2.6f,5},{17,2.6f,5})) < 5);
		if (kind < 4) {
			CHECK_FALSE(std::isfinite(FirstHit(whole,ray({0.5f,8,4},{0.5f,8,3}))));
			float y = kind < 2 ? 6.7f : kind == 2 ? 8.0f : 4.4f;
			float head = kind < 2 ? 0.5f : 1.0f;
			CHECK(FirstHit(whole,ray({15,y,4},{15,y,3})) == Approx(4-head).margin(0.001f));
		}
	}
}

TEST_CASE("Crossing equipment clears both road lanes and maglev gates obey the barred state", "[renderer3d]")
{
	for (unsigned kind = 0; kind < 4; ++kind) for (bool transpose : {false,true}) for (bool barred : {false,true}) for (bool tram : {false,true}) {
		auto crossing = MakeCrossingAssembly(kind,transpose,barred,tram);
		TunnelAssembly whole;
		bool finite = true;
		for (const auto &part : crossing.parts) for (const auto &vertex : part) {
			finite &= std::isfinite(vertex.position.x+vertex.position.y+vertex.position.z+vertex.normal.x+vertex.normal.y+vertex.normal.z);
			whole.parts[0].push_back(vertex);
		}
		CHECK(finite);
		for (float lane : {5.0f,11.0f}) {
			Ray ray = transpose ? Ray{{1,lane,0.5f},{1,0,0}} : Ray{{lane,1,0.5f},{0,1,0}};
			float hit = FirstHit(whole,ray);
			INFO("kind=" << kind << " transpose=" << transpose << " barred=" << barred << " tram=" << tram << " lane=" << lane);
			if (kind == 3 && barred) CHECK(hit < 4);
			else CHECK_FALSE(std::isfinite(hit));
		}
	}
}

TEST_CASE("Road-stop shelters have real roofs and leave both vehicle lanes open", "[renderer3d]")
{
	for (bool truck : {false,true}) for (unsigned layout = 0; layout < 6; ++layout) for (bool detail : {false,true}) for (bool tram : {false,true}) {
		if (tram && layout < 4) continue;
		auto stop = MakeRoadStopAssembly(truck,layout,tram,detail);
		TunnelAssembly whole;
		bool finite = true, contained = true;
		for (const auto &part : stop.parts) for (const auto &v : part) {
			Vec3 p = v.position;
			finite &= std::isfinite(p.x+p.y+p.z+v.normal.x+v.normal.y+v.normal.z);
			contained &= p.x >= -0.01f && p.y >= -0.01f && p.x <= 16.01f && p.y <= 16.01f && p.z >= -0.01f && p.z < 12;
			whole.parts[0].push_back(v);
		}
		INFO("truck=" << truck << " layout=" << layout << " detail=" << detail << " tram=" << tram);
		CHECK(finite); CHECK(contained);
		auto ray = [&](Vec3 a, Vec3 b) { return Ray{RoadStopPoint(layout,a),RoadStopPoint(layout,b)-RoadStopPoint(layout,a)}; };
		for (float lane : {5.0f,11.0f}) {
			float hit = FirstHit(whole,ray({18,lane,2},{17,lane,2}));
			if (layout >= 4) CHECK_FALSE(std::isfinite(hit));
			else CHECK(hit > 14.8f);
		}
		Vec3 roof = truck && layout < 4 ? Vec3{1.5f,9,14} : Vec3{8,1.5f,14};
		CHECK(FirstHit(whole,ray(roof,roof-Vec3{0,0,1})) < 6);
	}
}

TEST_CASE("Road-stop ground samples the adjoining full tile without microtexture repetition", "[renderer3d]")
{
	for (bool truck : {false,true}) for (unsigned layout = 0; layout < 6; ++layout) for (bool detail : {false,true}) {
		auto stop = MakeRoadStopAssembly(truck,layout,false,detail);
		CHECK(stop.parts[static_cast<unsigned>(RoadStopMaterial::Markings)].empty());
		for (RoadStopMaterial material : {RoadStopMaterial::Road,RoadStopMaterial::Paving}) {
			const auto &mesh = stop.parts[static_cast<unsigned>(material)];
			REQUIRE_FALSE(mesh.empty());
			for (const auto &vertex : mesh) {
				CHECK(vertex.texture.x == vertex.position.x);
				CHECK(vertex.texture.y == vertex.position.y);
				CHECK(vertex.texture.z == 0);
				CHECK((static_cast<uint32_t>(vertex.surface)&SURFACE_SHADED) == 0);
			}
			/* A curb needs only its physical faces, not thousands of clipped
			 * triangles from repeating an eight-source-pixel road crop. */
			CHECK(mesh.size() <= 3*36);
		}
	}
}

TEST_CASE("Canal dikes preserve original runtime selection for static and resolved base-set IDs", "[renderer3d]")
{
	for (SpriteID base : {SPR_CANAL_DIKES_BASE,SpriteID{9808}}) {
		for (unsigned variant = 0; variant < 12; ++variant) {
			CHECK(SelectCanalDikeVariant(base+variant,base,true,true) == variant);
			CHECK_FALSE(SelectCanalDikeVariant(base+variant,base,false,true));
			CHECK_FALSE(SelectCanalDikeVariant(base+variant,base,true,false));
		}
		CHECK_FALSE(SelectCanalDikeVariant(base-1,base,true,true));
		CHECK_FALSE(SelectCanalDikeVariant(base+12,base,true,true));
	}
}

TEST_CASE("Canal soil masks preserve climate paint without a second flat masonry wall", "[renderer3d]")
{
	CHECK(SupportsCanalDikeGround("OpenGFX2 Classic"));
	for (std::string_view name : {"OpenGFX2 High Def","OpenGFX","original_windows","custom",""}) CHECK_FALSE(SupportsCanalDikeGround(name));
	for (unsigned index = 0; index < 256; ++index) {
		CHECK(KeepCanalDikeGround(index) == (index >= 24));
	}
}
