/* SPDX-License-Identifier: GPL-2.0-only */
/** @file renderer3d_camera.cpp Projection agreement and rotation/picking invariants. */

#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "camera.hpp"
#include "texture_bounds.hpp"
#include "camera_motion.hpp"
#include "atlas_allocator.hpp"
#include "instance_batcher.hpp"
#include "indexed_mesh.hpp"
#include "material_chart.hpp"
#include "sprite_textures.hpp"
#include "bridge_geometry.hpp"
#include "terrain_geometry.hpp"
#include "world_capture.h"
#include "../blitter/32bpp_base.hpp"
#include "../landscape.h"
#include <map>
#include <set>
#include <cstring>

using namespace Renderer3D;
using Catch::Detail::Approx;

TEST_CASE("Indexed immutable meshes preserve every vertex attribute and triangle order", "[renderer3d]")
{
	Scene scene;
	scene.Quad({-1,-1,0},{1,-1,0},{1,1,0},{-1,1,0},{0.2f,0.5f,0.8f});
	auto indexed = IndexMesh(scene.vertices);
	REQUIRE(indexed.indices.size() == scene.vertices.size());
	CHECK(indexed.vertices.size() == 4);
	CHECK(indexed.ShortIndices() == std::vector<uint16_t>{0,1,2,0,2,3});
	for (size_t i = 0; i < scene.vertices.size(); ++i) CHECK(std::memcmp(&scene.vertices[i],&indexed.vertices[indexed.indices[i]],sizeof(Vertex)) == 0);
	/* A seam can differ in any attribute, not only position. Reconstruct the
	 * stream bit-for-bit after changing each 32-bit field independently. */
	for (size_t field = 0; field < sizeof(Vertex)/sizeof(uint32_t); ++field) {
		auto original = scene.vertices;
		auto words = std::bit_cast<std::array<uint32_t,20>>(original[3]);
		words[field] ^= 1;
		original[3] = std::bit_cast<Vertex>(words);
		auto result = IndexMesh(original);
		REQUIRE(result.indices.size() == original.size());
		CHECK(result.vertices.size() == 5);
		for (size_t i = 0; i < original.size(); ++i) CHECK(std::memcmp(&original[i],&result.vertices[result.indices[i]],sizeof(Vertex)) == 0);
	}
	CHECK(IndexMesh({}).indices.empty());
	std::vector<Vertex> unique(3);
	for (unsigned i = 0; i < unique.size(); ++i) unique[i].position.x = i;
	CHECK(IndexMesh(unique).indices.empty()); // Avoid an index buffer when it adds storage.
}

TEST_CASE("Mesh indices retain signed zero, NaN payloads and values beyond 16 bits", "[renderer3d]")
{
	std::vector<Vertex> bits(64);
	bits[3].position.x = -0.0f;
	bits[4].texture.x = std::bit_cast<float>(uint32_t{0x7fc01234});
	bits[5] = bits[4];
	bits[6].texture.x = std::bit_cast<float>(uint32_t{0x7fc01235});
	auto result = IndexMesh(bits);
	REQUIRE(result.indices.size() == bits.size());
	CHECK(result.indices[0] != result.indices[3]);
	CHECK(result.indices[4] == result.indices[5]);
	CHECK(result.indices[4] != result.indices[6]);
	for (size_t i = 0; i < bits.size(); ++i) CHECK(std::memcmp(&bits[i],&result.vertices[result.indices[i]],sizeof(Vertex)) == 0);
	std::vector<Vertex> large;
	large.reserve(68000*3);
	for (unsigned i = 0; i < 68000; ++i) {
		Vertex vertex{}; vertex.object_id = TILE_PICK_ID | i;
		for (unsigned copy = 0; copy < 3; ++copy) large.push_back(vertex);
	}
	auto wide = IndexMesh(large);
	REQUIRE(wide.indices.size() == large.size());
	CHECK(wide.vertices.size() == 68000);
	CHECK(wide.ShortIndices().empty());
	CHECK(wide.indices.back() == 67999);
	CHECK(wide.vertices[wide.indices.back()].object_id == (TILE_PICK_ID | 67999));
}

TEST_CASE("Fractional instance chart offsets stay independent of atlas placement", "[renderer3d]")
{
	SpriteTexture texture;
	texture.page = 3; texture.width = 8; texture.height = 6; texture.zoom = 5;
	const float source_u = 113.1893f, source_v = 166.7137f;
	Vec3 local = texture.LocalUV(source_u,source_v);
	InstanceData data;
	data.scale_center = {1.182858f,1.7343717f,6.575204f,8};
	data.uv_transform = {local.x,local.y,4.0f/(32*1024),local.z};
	data.identity[1] = static_cast<float>(SurfaceMode::Opaque); data.identity[3] = 2;
	data.SetSpriteLocalUVBias(); data.SetChildLayer(true); data.SetObjectId(TILE_PICK_ID|0xFFFFFFU);
	Vertex vertex{{3,7,12},{0,0,1},{},0,{1.234567f,2.345678f,0.456789f}};
	data.region = texture.Region();
	Vertex expected = ResolveInstanceVertex(vertex,data);
	bool cancellation_observed = false;
	for (int x : {1,29,95,311,711,883}) for (int y : {1,31,95,303,511,887}) {
		texture.x = x; texture.y = y;
		Vec3 absolute = texture.UV(source_u,source_v);
		cancellation_observed |= absolute.x-texture.Region().left != local.x || absolute.y-texture.Region().top != local.y;
		data.region = texture.Region();
		Vertex actual = ResolveInstanceVertex(vertex,data);
		CHECK(std::bit_cast<std::array<uint32_t,3>>(actual.texture) == std::bit_cast<std::array<uint32_t,3>>(expected.texture));
		CHECK((static_cast<uint32_t>(actual.surface)&SURFACE_SPRITE_LOCAL_UV) != 0);
		CHECK(actual.object_id == (TILE_PICK_ID|0xFFFFFFU));
		CHECK(data.ChildLayer());
	}
	CHECK(cancellation_observed); // The old absolute/add/subtract representation is observably lossy.
}

TEST_CASE("Palette raster culling never leaks onto shared sprite-overlay batches", "[renderer3d]")
{
	std::vector<Vertex> mesh(3);
	InstanceData palette, overlay;
	palette.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::Palette) | SURFACE_UNLIT);
	overlay.identity[1] = static_cast<float>(SurfaceMode::Cutout);
	std::array<MeshInstance,2> instances{{{&mesh,palette},{&mesh,overlay}}};
	InstanceBatcher batches;
	batches.Build(instances,false);
	REQUIRE(batches.batches.size() == 1);
	CHECK_FALSE(batches.PaletteOnly(batches.batches.front()));
	instances[1].data = palette;
	batches.Build(instances,false);
	CHECK(batches.PaletteOnly(batches.batches.front()));
	instances[1].data.origin_opacity[3] = 0.38f;
	batches.Build(instances,true);
	REQUIRE(batches.batches.size() == 2);
	for (const auto &batch : batches.batches) CHECK(batches.PaletteOnly(batch));
}

TEST_CASE("Foundation walls close every exposed side and the raised half-tile", "[renderer3d]")
{
	TileSurface bottom{{8,0,0,0},0};
	TileSurface levelled;
	auto mesh = MakeFoundationMesh(bottom,levelled,8);
	std::array<bool,4> sides{};
	double area = 0;
	for (size_t i = 0; i < mesh.size(); i += 3) {
		const Vec3 a = mesh[i].position, b = mesh[i+1].position, c = mesh[i+2].position;
		Vec3 u = b-a, v = c-a;
		Vec3 cross{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
		area += std::sqrt(Dot(cross,cross))/2;
		Vec3 normal = mesh[i].normal;
		if (normal.x < -0.9f) sides[0] = true;
		if (normal.x > 0.9f) sides[1] = true;
		if (normal.y < -0.9f) sides[2] = true;
		if (normal.y > 0.9f) sides[3] = true;
	}
	/* Cell feet embed below the terrain by less than one half-unit; exposed
	 * side coverage must contain the old analytic 384-unit wall envelope. */
	CHECK(area >= 384);
	CHECK(area <= 416);
	for (bool present : sides) CHECK(present);
	TileSurface half = bottom;
	half.raised_half = 0; half.upper_height = 8;
	mesh = MakeFoundationMesh(bottom,half,0);
	CHECK(std::any_of(mesh.begin(),mesh.end(),[](const Vertex &v) { return v.normal.x > 0.99f && v.position.x < 16; }));
	CHECK(std::any_of(mesh.begin(),mesh.end(),[](const Vertex &v) { return v.normal.y > 0.99f && v.position.y < 16; }));
	for (const auto &v : mesh) {
		CHECK(v.position.z >= 0);
		CHECK(v.position.z <= 8);
		CHECK(std::abs(v.normal.z) == 0); // Horizontal contacts are hidden by terrain.
		CHECK((static_cast<uint32_t>(v.surface)&15U) == static_cast<uint32_t>(SurfaceMode::Palette));
	}
}

TEST_CASE("Terrain surfaces and fence feet follow all vanilla slopes", "[renderer3d]")
{
	for (unsigned value = 0; value < 32; ++value) {
		if (value >= 15 && value != 23 && value != 27 && value != 29 && value != 30) continue;
		Slope slope = static_cast<Slope>(value);
		TileSurface surface = MakeTileSurface(slope);
		for (int x = 0; x < 16; x += 2) for (int y = 0; y < 16; y += 2) CHECK(surface.Height(x,y) == Approx(2*GetPartialPixelZ(x,y,slope)));
		for (unsigned style = 0; style < 7; ++style) for (unsigned lod = 0; lod < 3; ++lod) {
			auto mesh = MakeFenceMesh(style,{0,1,0},{16,1,0},surface,false,0,lod);
			REQUIRE_FALSE(mesh.empty());
			float xy = style == 6 ? (lod == 0 ? 0.125f : 0.25f) : style == 1 || style == 2 ? 0.25f : 0.5f;
			float dz = style == 1 || style == 2 || (style == 6 && lod == 0) ? 0.25f : 0.5f;
			bool finite = true, supported = true, voxel_faces = true;
			unsigned contacts = 0;
			for (const auto &v : mesh) {
				float relative = v.position.z-surface.Height(v.position.x,v.position.y);
				finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z+v.texture.x+v.texture.y);
				/* Feet embed by their cell quantization plus the terrain variation
				 * across one cell; voxel steps are never sheared into sloping quads. */
				supported &= relative >= -(dz+2*xy)-0.0001f && relative <= 5.5f+dz+2*xy;
				voxel_faces &= std::abs(v.normal.x)+std::abs(v.normal.y)+std::abs(v.normal.z) > 0.9999f &&
					std::abs(v.normal.x)+std::abs(v.normal.y)+std::abs(v.normal.z) < 1.0001f;
				voxel_faces &= (static_cast<uint32_t>(v.surface)&15U) == static_cast<uint32_t>(SurfaceMode::Palette);
				if (v.normal.z < -0.99f && relative <= 0.0001f) ++contacts;
			}
			INFO("fence=" << style << " slope=" << value << " lod=" << lod);
			CHECK(finite);
			CHECK(supported);
			CHECK(voxel_faces);
			CHECK(contacts >= 8);
		}
	}
}

TEST_CASE("Bridge ramps meet upstream vehicle slopes in all four directions", "[renderer3d]")
{
	const Slope slopes[] = {SLOPE_NE, SLOPE_SE, SLOPE_SW, SLOPE_NW};
	for (unsigned direction = 0; direction < 4; ++direction) {
		for (uint x : {0U, 4U, 8U, 12U}) for (uint y : {0U, 4U, 8U, 12U}) {
			CHECK(BridgeRampHeight(direction, x, y) == GetPartialPixelZ(x, y, slopes[direction]));
		}
		/* Surface overlays follow the same sheared deck and keep their small
		 * depth offset on both flat and sloped heads, without moving the texture. */
		for (bool sloped : {false, true}) {
			auto mesh = MakeBridgeMesh({0, 6, BridgeRole::Surface, direction % 2 != 0, direction, sloped});
			REQUIRE(mesh.size() == 6);
			for (const auto &v : mesh) {
				CHECK(v.position.z == Approx(0.025f + (sloped ? BridgeRampHeight(direction, v.position.x, v.position.y) - 8 : 0)));
				CHECK(v.normal.z > 0.8f);
			}
		}
	}
}

TEST_CASE("Bridge assemblies have finite outward faces under axis reflection", "[renderer3d]")
{
	for (unsigned type = 0; type <= 13; ++type) for (unsigned piece = 0; piece < 6; ++piece) {
		for (BridgeRole role : {BridgeRole::Deck, BridgeRole::Front, BridgeRole::Pillar, BridgeRole::Ramp}) {
			for (bool along_y : {false, true}) {
				auto mesh = MakeBridgeMesh({type, piece, role, along_y, along_y ? 1U : 2U, role == BridgeRole::Ramp});
				if (role == BridgeRole::Pillar && ((type >= 3 && type <= 5 && piece == 5) || (type >= 6 && type <= 8 && piece == 0) || (type >= 10 && type <= 12 && piece == 0))) {
					CHECK(mesh.empty());
					continue;
				}
				REQUIRE_FALSE(mesh.empty());
				bool finite = true, consistent = true;
				double volume = 0;
				for (size_t i = 0; i < mesh.size(); i += 3) {
					const auto &a = mesh[i], &b = mesh[i+1], &c = mesh[i+2];
					Vec3 cross{b.position.y*c.position.z-b.position.z*c.position.y,
						b.position.z*c.position.x-b.position.x*c.position.z,b.position.x*c.position.y-b.position.y*c.position.x};
					volume += Dot(a.position, cross) / 6;
					for (size_t j = i; j < i+3; ++j) {
						const auto &v = mesh[j];
						finite &= std::isfinite(v.position.x + v.position.y + v.position.z + v.normal.x + v.normal.y + v.normal.z);
						consistent &= Dot(v.normal, Normal(a.position,b.position,c.position)) > 0.999f;
					}
				}
				INFO("type=" << type << " piece=" << piece << " role=" << static_cast<unsigned>(role) << " axis=" << along_y);
				CHECK(finite);
				CHECK(consistent);
				CHECK(volume > 0);
			}
		}
	}
}

TEST_CASE("Atlas packing retains nonoverlapping UV rectangles for mixed sprite sizes", "[renderer3d]")
{
	AtlasAllocator atlas(64);
	std::vector<AtlasAllocator::Area> placed;
	/* Mixed aspect ratios leave reusable holes instead of wasting whole rows. */
	for (auto size : {Point{40, 16}, Point{24, 48}, Point{40, 32}, Point{64, 16}}) {
		auto rect = atlas.Allocate(size.x, size.y);
		REQUIRE(rect.has_value());
		CHECK(rect->x >= 0);
		CHECK(rect->y >= 0);
		CHECK(rect->x + rect->width <= 64);
		CHECK(rect->y + rect->height <= 64);
		for (auto previous : placed) CHECK((rect->x >= previous.x + previous.width || previous.x >= rect->x + rect->width ||
			rect->y >= previous.y + previous.height || previous.y >= rect->y + rect->height));
		placed.push_back(*rect);
	}
	CHECK_FALSE(atlas.Allocate(1, 1).has_value()); // All 4096 pixels are occupied.
}

TEST_CASE("Reusable instance batches retain submission order and discard previous scenes", "[renderer3d]")
{
	std::vector<Vertex> first(3), second(6);
	std::vector<MeshInstance> instances;
	for (unsigned i = 0; i < 400; ++i) {
		InstanceData data;
		data.identity[0] = static_cast<float>(i+1);
		data.origin_opacity[3] = i%3 == 0 ? 0.38f : 1;
		instances.push_back({i%2 == 0 ? &first : &second,data});
	}
	InstanceBatcher staging;
	for (bool split : {false,true}) {
		staging.Build(instances,split);
		/* Reuse each mesh/layer lookup while moving the live instances. The
		 * cache must not reuse last frame's actual GPU records. */
		for (unsigned i = 0; i < instances.size(); ++i) instances[i].data.origin_opacity[0] = i+0.25f;
		staging.Build(instances,split);
		CHECK(staging.batches.size() == (split ? 4 : 2));
		std::set<unsigned> seen;
		for (const auto &batch : staging.batches) {
			REQUIRE(batch.source < instances.size());
			CHECK(instances[batch.source].mesh == batch.mesh);
			unsigned previous = 0;
			for (size_t i = batch.first; i < batch.first+batch.count; ++i) {
				const auto &data = staging.records[i];
				unsigned id = static_cast<unsigned>(data.identity[0]);
				CHECK(id > previous);
				CHECK(instances[id-1].mesh == batch.mesh);
				CHECK(data.origin_opacity[0] == instances[id-1].data.origin_opacity[0]);
				if (split) CHECK((data.origin_opacity[3] < 0.99f) == batch.transparent);
				seen.insert(id); previous = id;
			}
		}
		CHECK(seen.size() == instances.size());
		staging.Build(std::span<const MeshInstance>{instances}.first(1),split);
		REQUIRE(staging.batches.size() == 1);
		CHECK(staging.batches.front().count == 1);
		CHECK(staging.records.front().identity[0] == 1);
		for (unsigned frame = 0; frame < 240; ++frame) staging.Build({},split);
		CHECK(staging.batches.empty());
		CHECK(staging.records.front().identity[0] == 0);
	}
}

TEST_CASE("Instance staging preserves composite order through rehash and retirement", "[renderer3d]")
{
	std::vector<std::vector<Vertex>> meshes(1024);
	std::vector<MeshInstance> instances;
	std::map<const std::vector<Vertex> *,size_t> first_capture;
	for (unsigned i = 0; i < 2048; ++i) {
		InstanceData data;
		data.SetObjectId(i+1);
		data.origin_opacity[3] = i%3 == 0 ? 0.38f : 1;
		instances.push_back({&meshes[(i*37)%meshes.size()],data});
		first_capture.try_emplace(instances.back().mesh,i);
	}
	InstanceBatcher staging;
	for (unsigned pass = 0; pass < 2; ++pass) {
		staging.Build(instances,true);
		using Key = std::pair<size_t,bool>;
		std::optional<Key> previous;
		std::set<uint32_t> seen;
		bool correct = true;
		for (const auto &batch : staging.batches) {
			Key key{first_capture.at(batch.mesh),batch.transparent};
			CHECK(batch.source == first_capture.at(batch.mesh));
			correct &= !previous || std::less<Key>{}(*previous,key);
			previous = key;
			uint32_t last_id = 0;
			for (size_t index = batch.first; index < batch.first+batch.count; ++index) {
				const auto &data = staging.records[index];
				uint32_t id = data.ObjectId();
				REQUIRE(id > 0);
				REQUIRE(id <= instances.size());
				correct &= id > last_id && instances[id-1].mesh == batch.mesh && (data.origin_opacity[3] < 0.99f) == batch.transparent;
				seen.insert(id); last_id = id;
			}
		}
		CHECK(correct);
		CHECK(seen.size() == instances.size());
		for (unsigned frame = 0; frame < 240; ++frame) staging.Build({},true);
	}
}

TEST_CASE("Mesh allocation addresses do not decide coplanar draw precedence", "[renderer3d]")
{
	std::array<std::vector<Vertex>,2> meshes;
	InstanceData first, second;
	first.SetObjectId(TILE_PICK_ID|0xFFFFFFU);
	second.SetObjectId(731);
	InstanceBatcher staging;
	for (bool reverse_allocation : {false,true}) for (bool split : {false,true}) for (bool child : {false,true}) {
		first.SetChildLayer(child); second.SetChildLayer(child);
		std::array<MeshInstance,2> instances{{{&meshes[reverse_allocation ? 1 : 0],first},{&meshes[reverse_allocation ? 0 : 1],second}}};
		staging.Build(instances,split);
		REQUIRE(staging.batches.size() == 2);
		CHECK(staging.records[staging.batches.front().first].ObjectId() == first.ObjectId());
		CHECK(staging.records[staging.batches.back().first].ObjectId() == second.ObjectId());
	}
}

TEST_CASE("Opacity-boundary mesh groups retain their unpartitioned painter order", "[renderer3d]")
{
	std::vector<Vertex> boundary_mesh(3), ordinary_mesh(3);
	for (float boundary : {0.99f,std::nextafter(0.99f,0.0f),std::nextafter(0.99f,1.0f)}) {
		const float opacity[] = {0.38f,1.0f,boundary,1.0f,0.38f,0.62f};
		std::vector<MeshInstance> instances;
		for (unsigned i = 0; i < std::size(opacity); ++i) {
			InstanceData data;
			data.SetObjectId(i+1); data.origin_opacity[3] = opacity[i];
			instances.push_back({i == 1 || i == 4 ? &ordinary_mesh : &boundary_mesh,data});
		}
		InstanceBatcher staging;
		staging.Build(instances,true);
		REQUIRE(staging.batches.size() == 3);
		for (const auto &batch : staging.batches) {
			if (batch.mesh == &boundary_mesh) {
				CHECK(batch.both_passes);
				REQUIRE(batch.count == 4);
				const uint32_t expected[] = {1,3,4,6};
				for (unsigned i = 0; i < 4; ++i) CHECK(staging.records[batch.first+i].ObjectId() == expected[i]);
			} else {
				CHECK_FALSE(batch.both_passes);
				CHECK(batch.count == 1);
			}
		}
		instances[2].data.origin_opacity[3] = 0.75f;
		staging.Build(instances,true);
		CHECK(staging.batches.size() == 4);
		for (const auto &batch : staging.batches) CHECK_FALSE(batch.both_passes);
	}
}

TEST_CASE("Instance rotations preserve separately rounded products at voxel face boundaries", "[renderer3d]")
{
	bool fused_difference = false;
	for (unsigned pose = 0; pose < 16; ++pose) for (int x = -20; x <= 20; ++x) for (int y = -5; y <= 5; ++y) {
		InstanceData data;
		data.mirror_layer_heading[3] = pose*std::numbers::pi_v<float>/8+0.07f;
		float cs = std::cos(data.mirror_layer_heading[3]), sn = std::sin(data.mirror_layer_heading[3]);
		Vertex vertex{{x*0.25f,y*0.25f,2},{0,0,1},{},0};
		volatile float xx = vertex.position.x*cs, yy = vertex.position.y*sn;
		volatile float xy = vertex.position.x*sn, yx = vertex.position.y*cs;
		Vec3 expected{xx-yy,xy+yx,2};
		auto actual = ResolveInstanceVertex(vertex,data);
		CHECK(actual.position == expected);
		fused_difference |= std::fma(vertex.position.x,cs,-yy) != expected.x;
	}
	/* The test includes real contraction-sensitive inputs, not just cardinal
	 * rotations where both arithmetic paths happen to give the same result. */
	CHECK(fused_difference);
}

TEST_CASE("Canonical palette yaw staging retains reference vertices and complete instance metadata", "[renderer3d]")
{
	for (float heading : {0.0f,0.07f,2*std::numbers::pi_v<float>/8+0.07f,10*std::numbers::pi_v<float>/8+0.07f,-1.25f}) {
		InstanceData source;
		source.origin_opacity = {13,17,6,0.38f};
		source.scale_center = {0.75f,1.25f,2,-3};
		source.mirror_layer_heading = {17,23,0,heading};
		source.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT),1,2};
		source.SetObjectId(TILE_PICK_ID|0xFFFFFFU);
		source.SetChildLayer(true);
		source.SetLongitudinalScale(0.75f);
		const InstanceData unchanged = source;
		auto packed = source.CanonicalGPURecord();
		CHECK(std::memcmp(&source,&unchanged,sizeof(source)) == 0);
		CHECK(packed.ObjectId() == source.ObjectId());
		CHECK(packed.ChildLayer());
		CHECK(packed.origin_opacity == source.origin_opacity);
		CHECK(packed.scale_center == source.scale_center);
		CHECK(packed.uv_transform == source.uv_transform);
		CHECK(packed.mirror_layer_heading[2] == 0.75f);
		CHECK(((static_cast<uint32_t>(packed.identity[2])&8U) != 0) == (heading != 0));
		for (int x = -20; x <= 20; ++x) for (int y = -6; y <= 6; ++y) {
			Vertex vertex{{x*0.25f-0.125f,y*0.25f,7.5f},{0,1,0},{204.5f/256,0.5f,-3},0};
			auto expected = ResolveInstanceVertex(vertex,source,true);
			auto actual = ResolveInstanceVertex(vertex,packed,true);
			CHECK(std::memcmp(&actual,&expected,sizeof(Vertex)) == 0);
		}
		for (bool mirrored : {false,true}) {
			InstanceData projected = source;
			if (mirrored) projected.identity[2] = 0;
			else projected.identity[1] = static_cast<float>(SurfaceMode::Opaque);
			auto copy = projected.CanonicalGPURecord();
			CHECK(std::memcmp(&copy,&projected,sizeof(copy)) == 0);
		}
	}
}

TEST_CASE("Ordered child batches follow parents without changing picking flags or mesh reuse", "[renderer3d]")
{
	std::array<std::vector<Vertex>,2> meshes;
	for (auto &mesh : meshes) { mesh.resize(3); for (auto &vertex : mesh) vertex.normal = {0,0,1}; }
	InstanceData parent, child;
	parent.identity[2] = 1;
	parent.SetObjectId(TILE_PICK_ID|0xFFFFFFU);
	child = parent; child.SetChildLayer(true); child.SetObjectId(27);
	CHECK_FALSE(parent.ChildLayer());
	CHECK(child.ChildLayer());
	CHECK(child.ObjectId() == 27);
	CHECK((static_cast<uint32_t>(child.identity[2])&1U) != 0);
	child.SetObjectId(TILE_PICK_ID|81);
	CHECK(child.ChildLayer());
	CHECK(child.ObjectId() == (TILE_PICK_ID|81));
	InstanceBatcher staging;
	for (bool same_mesh : {false,true}) for (bool split : {false,true}) {
		Scene scene;
		/* Deliberately submit the child first and allocate its mesh before the
		 * parent. Neither pointer order nor input order may override the layer. */
		scene.instances = {{&meshes[0],child},{&meshes[same_mesh ? 0 : 1],parent}};
		for (unsigned pass = 0; pass < 2; ++pass) {
			staging.Build(scene.instances,split);
			REQUIRE(staging.batches.size() == 2);
			CHECK_FALSE(staging.records[staging.batches[0].first].ChildLayer());
			CHECK(staging.records[staging.batches[1].first].ChildLayer());
			CHECK(staging.batches[0].mesh == &meshes[same_mesh ? 0 : 1]);
			auto expanded = scene.ExpandedVertices();
			REQUIRE(expanded.size() == 6);
			CHECK(expanded.front().object_id == parent.ObjectId());
			CHECK(expanded.back().object_id == child.ObjectId());
			for (unsigned frame = 0; frame < 240; ++frame) staging.Build({},split);
		}
	}
	child.SetChildLayer(false);
	CHECK_FALSE(child.ChildLayer());
	CHECK(child.ObjectId() == (TILE_PICK_ID|81));
}

TEST_CASE("Repeating component charts preserve surface area and stay inside their selected material", "[renderer3d]")
{
	Scene original;
	original.Quad({0,0,2},{11,0,2},{11,7,5},{0,7,5},{});
	MaterialChart chart{{TextureRegion{0.2f,0.3f,0.4f,0.5f},TextureRegion{0.2f,0.3f,0.4f,0.5f},TextureRegion{0.2f,0.3f,0.4f,0.5f}},{3,2},true};
	auto result = ApplyMaterialChart(original.vertices,chart);
	auto area = [](std::span<const Vertex> vertices) {
		double sum = 0;
		for (size_t i = 0; i < vertices.size(); i += 3) {
			Vec3 a = vertices[i+1].position-vertices[i].position, b = vertices[i+2].position-vertices[i].position;
			Vec3 cross{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};
			sum += std::sqrt(Dot(cross,cross))*0.5;
		}
		return sum;
	};
	REQUIRE(result.size() > original.vertices.size());
	CHECK(area(result) == Approx(area(original.vertices)).epsilon(1e-6));
	for (const auto &v : result) {
		CHECK(v.texture.x >= 0.2f); CHECK(v.texture.x <= 0.4f);
		CHECK(v.texture.y >= 0.3f); CHECK(v.texture.y <= 0.5f);
		CHECK(v.position.z == Approx(2+3*v.position.y/7));
		CHECK((static_cast<uint32_t>(v.surface) & SURFACE_SHADED) != 0);
	}
	InstanceData instance;
	instance.uv_transform[3] = 2;
	instance.identity[3] = 2;
	Vertex solid{}; solid.texture = {-1,-1,-4}; solid.surface = static_cast<SurfaceMode>(SURFACE_SHADED);
	auto expanded = ResolveInstanceVertex(solid,instance);
	CHECK(expanded.texture.z == -1);
	CHECK((static_cast<uint32_t>(expanded.surface) & SURFACE_SHADED) != 0);
}

TEST_CASE("Repeating chart phases remain independent of instance placement and atlas position", "[renderer3d]")
{
	Vertex vertex{};
	vertex.position = {3,4,5}; vertex.normal = {0,0,1}; vertex.texture = {-1.25f,3.75f,-1};
	InstanceData data;
	data.origin_opacity = {500,700,20,1}; data.scale_center = {0.6f,1.2f,1,2};
	data.region = {0.25f,0.5f,0.3125f,0.625f}; data.uv_transform[3] = 7;
	data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::RepeatingChart) | SURFACE_SHADED),1,3};
	data.SetObjectId(TILE_PICK_ID | 1234);
	for (bool local : {false,true}) {
		auto result = ResolveInstanceVertex(vertex,data,local);
		CHECK(result.texture.x == vertex.texture.x); CHECK(result.texture.y == vertex.texture.y);
		CHECK(result.texture.z == 7); CHECK(result.texture_region.left == data.region.left);
		CHECK(result.object_id == (TILE_PICK_ID | 1234));
		CHECK((static_cast<uint32_t>(result.surface) & 15U) == static_cast<uint32_t>(SurfaceMode::RepeatingChart));
	}
}

TEST_CASE("Classic material pixels keep their world scale through growth and texture LOD", "[renderer3d]")
{
	TextureRegion crop{0.25f,0.25f,0.75f,0.75f};
	for (unsigned zoom : {2U,3U,4U}) for (float growth : {0.5f,0.83f,1.0f}) {
		SpriteTexture texture;
		texture.source_width = 256; texture.source_height = 128;
		texture.width = 256>>zoom; texture.height = 128>>zoom; texture.zoom = zoom;
		texture.page = 3; texture.x = 173; texture.y = 251;
		InstanceData data;
		data.origin_opacity = {100,200,30,1}; data.scale_center = {growth,growth,0,0};
		SetWorldTexelChart(data,texture,crop,{3,7},growth);
		Vertex a{}, b{};
		a.normal = b.normal = {0,0,1}; a.texture = {0,0,-1};
		b.position = {0.5f/growth,0,0.5f/(growth*Camera::WORLD_Z_SCALE)};
		b.texture = {b.position.x/3,-b.position.z*Camera::WORLD_Z_SCALE/7,-1};
		auto first = ResolveInstanceVertex(a,data), last = ResolveInstanceVertex(b,data);
		CHECK(last.position.x-first.position.x == Approx(0.5f));
		CHECK((last.position.z-first.position.z)*Camera::WORLD_Z_SCALE == Approx(0.5f).margin(0.00001f));
		/* A half world unit spans one native pixel on either chart axis, even
		 * on a smaller growth model or when a coarser source mip is selected. */
		CHECK((last.texture.x-first.texture.x)*32 == Approx(1));
		CHECK((last.texture.y-first.texture.y)*16 == Approx(-1));
		CHECK(last.texture.z == 3);
	}
}

TEST_CASE("Tile picking IDs preserve every map-index bit and the existing material flags", "[renderer3d]")
{
	for (uint32_t tile : {0U,1U,1048575U,8388607U,8388608U,16777214U,16777215U}) for (unsigned mirror : {0U,1U}) {
		InstanceData data;
		data.identity[2] = static_cast<float>(mirror);
		data.mirror_layer_heading = {16,16,0,0};
		data.uv_transform = {0,0,0.01f,1};
		Vertex v{{1,3,5},{-1,0,0},{},0};
		auto before = ResolveInstanceVertex(v,data);
		data.SetObjectId(TILE_PICK_ID | tile);
		auto after = ResolveInstanceVertex(v,data);
		CHECK(data.ObjectId() == (TILE_PICK_ID | tile));
		CHECK(after.object_id == (TILE_PICK_ID | tile));
		CHECK(after.texture == before.texture);
		CHECK(after.position == before.position);
		data.SetObjectId(71);
		CHECK(data.ObjectId() == 71);
		CHECK(data.identity[2] == static_cast<float>(mirror));
	}
}

TEST_CASE("UI blending preserves coverage over GPU viewports and opaque legacy pixels", "[renderer3d]")
{
	Colour transparent(0, 0, 0, 0);
	Colour red = Blitter_32bppBase::ComposeColourRGBA(255, 0, 0, 128, transparent);
	CHECK(red.r == 128);
	CHECK(red.a == 128);
	Colour green = Blitter_32bppBase::ComposeColourRGBA(0, 255, 0, 128, red);
	CHECK(green.r == 64);
	CHECK(green.g == 128);
	CHECK(green.a == 192);
	Colour opaque = Blitter_32bppBase::ComposeColourRGBA(255, 0, 0, 128, Colour(0, 0, 255));
	/* Upstream's unsigned /256 arithmetic rounds both channels down. */
	CHECK(opaque.r == 127);
	CHECK(opaque.b == 127);
	CHECK(opaque.a == 255);
	Colour shadow = Blitter_32bppBase::MakeTransparent(transparent, 3, 4);
	CHECK(shadow.r == 0);
	CHECK(shadow.a == 64);
}

TEST_CASE("World AABB culling agrees with projected point visibility", "[renderer3d]")
{
	for (float turn : {0.0f, 0.47f, 1.0f, 2.8f}) {
		Camera camera{{1024, 1024, 20}, 2, 1280, 800, turn};
		auto clip = camera.Frustum();
		for (int x = -600; x <= 600; x += 100) for (int y = -600; y <= 600; y += 100) {
			Vec3 point = camera.focus + Vec3{static_cast<float>(x), static_cast<float>(y), 7};
			auto pixel = camera.Project(point);
			bool expected = pixel.visible && pixel.x >= 0 && pixel.y >= 0 && pixel.x <= camera.width && pixel.y <= camera.height;
			CHECK(clip.Intersects(point, point) == expected);
		}
		CHECK(clip.Intersects(camera.focus - Vec3{1, 1, 1}, camera.focus + Vec3{1, 1, 1}));
	}
}

TEST_CASE("Instanced geometry keeps immutable meshes and value-only material records", "[renderer3d]")
{
	std::vector<Vertex> mesh{{{2, 3, 4}, {0, 0, 1}, {}, 0}};
	InstanceData data;
	data.origin_opacity = {10, 20, 30, 0.4f};
	data.scale_center = {2, 3, 1, 1};
	data.uv_transform = {0.1f, 0.2f, 0.01f, 5};
	data.identity = {1048575, static_cast<float>(SurfaceMode::Opaque), 0, 0};
	Scene scene;
	scene.instances.push_back({&mesh, data});
	CHECK(scene.vertices.empty());
	CHECK(scene.VertexCount() == 1);
	auto expanded = scene.ExpandedVertices();
	REQUIRE(expanded.size() == 1);
	CHECK(expanded[0].position.x == 12);
	CHECK(expanded[0].position.y == 24);
	CHECK(expanded[0].position.z == 42);
	CHECK(expanded[0].texture.x == Approx(0.14f));
	CHECK(expanded[0].texture.y == Approx(0.14f));
	CHECK(expanded[0].object_id == 1048575);
	CHECK(expanded[0].surface == SurfaceMode::Opaque);
	CHECK(mesh[0].position.x == 2);
	CHECK(mesh[0].texture.z == -1);
	Vertex authored = mesh[0];
	authored.texture = {12, 19, 0};
	data.identity[3] = 1;
	data.mirror_layer_heading[3] = 1.2f;
	auto explicit_uv = ResolveInstanceVertex(authored, data);
	CHECK(explicit_uv.texture.x == Approx(0.22f));
	CHECK(explicit_uv.texture.y == Approx(0.39f));
	CHECK(explicit_uv.texture.z == 5);
	data.identity[3] = 2;
	data.mirror_layer_heading[3] = 0;
	authored.texture = {1, 2, 3};
	auto sample_position = ResolveInstanceVertex(authored, data);
	CHECK(sample_position.position.x == 12); // Geometry stays at its authored position.
	CHECK(sample_position.texture.x == Approx(0.14f));
	CHECK(sample_position.texture.y == Approx(0.13f));
	authored.texture = {0.3f, 0.7f, -3};
	data.region = {0.1f, 0.2f, 0.2f, 0.4f};
	auto crop = ResolveInstanceVertex(authored, data);
	CHECK(crop.texture.x == Approx(0.13f));
	CHECK(crop.texture.y == Approx(0.34f));
	auto local_crop = ResolveInstanceVertex(authored, data, true);
	CHECK(local_crop.texture.x == Approx(0.03f));
	CHECK(local_crop.texture.y == Approx(0.14f));
	CHECK((static_cast<uint32_t>(local_crop.surface) & SURFACE_SPRITE_LOCAL_UV) != 0);
	CHECK(local_crop.position == crop.position);
}

TEST_CASE("Detached edge pixels do not stretch texture registration", "[renderer3d]")
{
	/* Reproduce the isolated corner mark above the HighDef birch canopy. */
	std::array<uint8_t, 120 * 300> alpha{};
	alpha[0] = 255;
	for (int y = 95; y < 295; ++y) for (int x = 40; x < 118; ++x) alpha[y * 120 + x] = 255;
	auto sample = [&](int x, int y) { return alpha[y * 120 + x]; };
	auto bounds = FindInkBounds(120, 300, sample);
	CHECK(bounds.left == 40);
	CHECK(bounds.top == 95);
	CHECK(bounds.width == 78);
	CHECK(bounds.height == 200);
	CHECK(IsIsolatedEdgeTexel(120, 300, 0, 0, sample));
	CHECK(alpha[0] == 255); // Registration never edits original texture pixels.
	alpha.fill(0);
	alpha[0] = 255;
	bounds = FindInkBounds(120, 300, sample);
	CHECK(bounds.width == 1);
	CHECK(bounds.height == 1);
	alpha[121] = 255; // Diagonally connected artwork touching the corner is retained.
	bounds = FindInkBounds(120, 300, sample);
	CHECK(bounds.width == 2);
	CHECK(bounds.height == 2);
	CHECK_FALSE(IsIsolatedEdgeTexel(120, 300, 0, 0, sample));
}

TEST_CASE("Perspective preserves the original focal-plane art proportions", "[renderer3d]")
{
	Camera camera{{512, 256, 0}, static_cast<float>(ZOOM_BASE), 1280, 800, 0};
	Point center = RemapCoords(512, 256, 0);
	for (int dx : {-64, 0, 64}) {
		for (int dy : {-64, 0, 64}) {
			int x = 512 + dx, y = 256 + dy, z = -3 * (dx + dy);
			auto actual = camera.Project({static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)});
			Point expected = RemapCoords(x, y, z);
			CHECK(actual.x == Approx(expected.x - center.x + 640));
			CHECK(actual.y == Approx(expected.y - center.y + 400));
		}
	}
}

TEST_CASE("Perspective screen rays hit the projected point at every rotation and zoom", "[renderer3d]")
{
	for (float rotation : {0.0f, 0.37f, 1.0f, 2.0f, 3.0f, 3.8f}) {
		for (float scale : {0.125f, 0.5f, 1.0f, 2.0f, 4.0f}) {
			Camera camera{{211.25f, 304.5f, 24}, scale, 1279, 799, rotation};
			for (Vec3 p : {Vec3{200, 288, 0}, Vec3{211, 300, 8}, Vec3{224.5f, 312.25f, 25}}) {
				auto screen = camera.Project(p);
				REQUIRE(screen.visible);
				auto actual = camera.ScreenRay(screen.x, screen.y).AtZ(p.z);
				REQUIRE(actual.has_value());
				CHECK(actual->x == Approx(p.x).margin(0.01));
				CHECK(actual->y == Approx(p.y).margin(0.01));
				CHECK(actual->z == Approx(p.z).margin(0.01));
			}
		}
	}
}

TEST_CASE("Perspective makes nearer objects larger and clips behind the camera", "[renderer3d]")
{
	Camera camera{{0, 0, 0}, 1, 1280, 800, 0};
	Vec3 toward = (camera.Eye() - camera.focus) * 0.25f;
	Vec3 right{-5, 5, 0};
	float near_width = camera.Project(toward + right).x - camera.Project(toward - right).x;
	float far_width = camera.Project(toward * -1 + right).x - camera.Project(toward * -1 - right).x;
	CHECK(near_width / far_width == Approx(5.0f / 3.0f));
	CHECK_FALSE(camera.Project(camera.Eye() * 2).visible);
}

TEST_CASE("Pinhole projection uses square pixels and limits tall-building lean", "[renderer3d]")
{
	Camera camera{{1024, 1024, 24}, 1, 1280, 800, 0};
	auto center = camera.Project(camera.focus);
	auto right = camera.Project(camera.focus + Camera::World(Camera::Right()) * 10);
	auto up = camera.Project(camera.focus + Camera::World(camera.Up()) * 10);
	CHECK(right.x - center.x == Approx(center.y - up.y).margin(0.001));
	Vec3 base = camera.focus + Camera::Right() * 80;
	auto bottom = camera.Project(base), top = camera.Project(base + Vec3{0, 0, 64});
	CHECK(std::abs((top.x - center.x) / (bottom.x - center.x) - 1) < 0.04f);
}

TEST_CASE("First-person projection and rays share the calibrated lens", "[renderer3d]")
{
	Camera camera{{1000, 1000, 24}, 1, 1280, 800, 0.73f};
	camera.first_person = true;
	camera.pitch = 2;
	camera.vertical_fov = 60;
	Ray ray = camera.ScreenRay(640, 400);
	auto target = camera.Project(ray.At(100));
	CHECK(target.visible);
	CHECK(target.x == Approx(640).margin(0.01));
	CHECK(target.y == Approx(400).margin(0.01));
	CHECK(ray.origin.x == camera.focus.x);
	CHECK(ray.origin.y == camera.focus.y);
	CHECK(ray.origin.z == camera.focus.z);
	auto matrix = camera.Matrix();
	Vec3 p = ray.At(100) - camera.focus;
	std::array<float, 4> v{p.x, p.y, p.z, 1}, clip{};
	for (int r = 0; r < 4; ++r) for (int c = 0; c < 4; ++c) clip[r] += matrix[c * 4 + r] * v[c];
	CHECK(clip[0] / clip[3] == Approx(0).margin(0.0001));
	CHECK(clip[1] / clip[3] == Approx(0).margin(0.0001));
	CHECK(camera.PixelScaleAt(ray.At(100)) > 0);
}

TEST_CASE("Clicked-point orbit retains the picked pixel and physical eye radius at every tilt", "[renderer3d]")
{
	for (float yaw : {0.0f, 0.71f, 2.5f}) for (float pitch : {5.0f, 30.0f, 80.0f}) {
		Camera original{{1024, 2048, 48}, 2, 1279, 799, yaw};
		original.pitch = pitch;
		for (auto pixel : {Point{127, 231}, Point{891, 611}}) {
			Vec3 pivot = original.ScreenRay(pixel.x, pixel.y).At(original.Distance() * 0.8f);
			float radius = Dot(Camera::Physical(original.Eye() - pivot), Camera::Physical(original.Eye() - pivot));
			for (float tilt : {-120.0f, -15.0f, 21.0f, 120.0f}) {
				Camera moved = original.Orbited(pivot, 0.61f, tilt);
				auto projected = moved.Project(pivot);
				CHECK(projected.visible);
				CHECK(projected.x == Approx(pixel.x).margin(0.02));
				CHECK(projected.y == Approx(pixel.y).margin(0.02));
				Vec3 eye = Camera::Physical(moved.Eye() - pivot);
				CHECK(Dot(eye, eye) == Approx(radius).epsilon(0.0001));
				CHECK(moved.pitch >= 3);
				CHECK(moved.pitch <= 89);
				auto cropped = moved.Cropped(70, 81, 301, 277).Project(pivot);
				CHECK(cropped.x == Approx(pixel.x - 70).margin(0.02));
				CHECK(cropped.y == Approx(pixel.y - 81).margin(0.02));
			}
		}
	}
}

TEST_CASE("Street-level orbit retains subpixel anchors at large world coordinates", "[renderer3d]")
{
	for (Vec3 origin : {Vec3{4761.8735f,171.68036f,0},Vec3{32768,32768,128},Vec3{131000,64000,80}}) {
		Camera original{origin,256,2560,1600,3};
		original.vertical_fov = 40;
		Vec3 pivot = original.ScreenRay(1280.5f,1200.5f).At(original.Distance()*0.8f);
		auto expected = original.Project(pivot);
		for (float yaw : {0.044471f,0.61f,2.3f}) for (float tilt : {-20.0f,1.461538f,47.0f}) {
			Camera moved = original.Orbited(pivot,yaw,tilt);
			auto actual = moved.Project(pivot);
			CHECK(actual.x == Approx(expected.x).margin(0.02));
			CHECK(actual.y == Approx(expected.y).margin(0.02));
			CHECK(actual.depth == Approx(expected.depth).margin(0.0001));
			auto matrix = moved.Matrix();
			Vec3 relative = pivot-moved.focus;
			std::array<float,4> point{relative.x,relative.y,relative.z,1}, clip{};
			for (int row = 0; row < 4; ++row) for (int column = 0; column < 4; ++column) clip[row] += matrix[column*4+row]*point[column];
			CHECK((clip[0]/clip[3]+1)*1280 == Approx(expected.x).margin(0.02));
			CHECK((1-clip[1]/clip[3])*800 == Approx(expected.y).margin(0.02));
			CHECK(moved.Frustum().Intersects(pivot-Vec3{0.01f,0.01f,0.01f},pivot+Vec3{0.01f,0.01f,0.01f}));
			Vec3 residual;
			auto anchored = moved.FocusForAnchor(pivot,expected.x+13.125f,expected.y-7.75f,&residual);
			REQUIRE(anchored.has_value());
			moved.focus = *anchored; moved.focus_offset = residual;
			auto shifted = moved.Project(pivot);
			CHECK(shifted.x == Approx(expected.x+13.125f).margin(0.02));
			CHECK(shifted.y == Approx(expected.y-7.75f).margin(0.02));
		}
	}
}

TEST_CASE("First-person frusta include distant terrain and full-map bounds across the horizon", "[renderer3d]")
{
	for (float yaw : {0.0f, 0.71f, 2.0f, 3.5f}) for (float pitch : {-15.0f, 0.0f, 2.0f, 75.0f}) {
		Camera camera{{65536, 65536, 128}, 1, 1280, 800, yaw};
		camera.first_person = true; camera.vertical_fov = 60; camera.pitch = pitch;
		auto clip = camera.Frustum();
		auto bounds = clip.IntersectionBounds({0, 0, 0}, {131072, 131072, 2048});
		REQUIRE(bounds.has_value());
		for (float depth : {100.0f, 4096.0f, 8192.0f, 65536.0f, 1000000.0f}) {
			Vec3 point = camera.ScreenRay(640, 400).At(depth);
			CHECK(camera.Project(point).visible);
			CHECK(clip.Intersects(point - Vec3{1, 1, 1}, point + Vec3{1, 1, 1}));
		}
		for (int y = 0; y <= 131072; y += 16384) for (int x = 0; x <= 131072; x += 16384) for (int z : {0, 1024, 2048}) {
			Vec3 point{static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)};
			auto projected = camera.Project(point);
			if (!projected.visible || projected.x < 0 || projected.x > camera.width || projected.y < 0 || projected.y > camera.height) continue;
			CHECK(point.x >= (*bounds)[0].x - 0.1f);
			CHECK(point.x <= (*bounds)[1].x + 0.1f);
			CHECK(point.y >= (*bounds)[0].y - 0.1f);
			CHECK(point.y <= (*bounds)[1].y + 0.1f);
		}
		Vec3 behind = camera.Eye() + camera.Unrotate(Camera::World(camera.Back())) * 10;
		CHECK_FALSE(clip.Intersects(behind, behind));
	}
}

TEST_CASE("Long-distance picking enters the map before stepping its first cell", "[renderer3d]")
{
	for (float distance : {8192.0f, 65536.0f, 1000000.0f}) {
		Ray ray{{-distance, -distance - 1, 500}, Normalize({1, 1, -0.0001f})};
		double enter = 0, leave = std::numeric_limits<double>::infinity();
		REQUIRE(ray.ClipBox({0, 0, 0}, {16384, 16384, 2048}, enter, leave));
		CHECK(static_cast<double>(ray.origin.y) + ray.direction.y * (enter + 0.0001) > 0);
		CHECK(static_cast<double>(ray.origin.y) + ray.direction.y * (enter - 0.0001) < 0);
		CHECK(leave > enter);
	}
}

TEST_CASE("Camera interpolation is frame-rate independent and crosses yaw wrap smoothly", "[renderer3d]")
{
	float slow = 2, fast = 2;
	for (unsigned frame = 0; frame < 30; ++frame) slow = SmoothValue(slow, -3, 16, 1.0f / 30);
	for (unsigned frame = 0; frame < 144; ++frame) fast = SmoothValue(fast, -3, 16, 1.0f / 144);
	CHECK(slow == Approx(fast).margin(0.0001));
	float heading = SmoothHeading(3.95f, 0.05f, 12, 1.0f / 60);
	CHECK(heading > 3.95f);
	CHECK(heading < 4.05f);
	CHECK(SmoothValue(2, -3, 16, 0) == 2);
}

TEST_CASE("Perspective GPU matrix and CPU projection agree", "[renderer3d]")
{
	for (float rotation : {0.0f, 0.37f, 1.0f, 2.0f, 3.0f, 3.8f}) {
		Camera camera{{100, 200, 24}, 2, 1600, 900, rotation};
		auto m = camera.Matrix();
		for (Vec3 p : {Vec3{80, 180, 0}, Vec3{130, 220, 64}}) {
			Vec3 relative = p - camera.focus;
			std::array<float, 4> v{relative.x, relative.y, relative.z, 1}, clip{};
			for (int r = 0; r < 4; ++r) for (int c = 0; c < 4; ++c) clip[r] += m[c * 4 + r] * v[c];
			auto screen = camera.Project(p);
			CHECK((clip[0] / clip[3] + 1) * 800 == Approx(screen.x));
			CHECK((1 - clip[1] / clip[3]) * 450 == Approx(screen.y));
			CHECK(clip[3] == Approx(screen.depth));
		}
	}
}

TEST_CASE("OpenTT3D scene instances preserve authored models", "[renderer3d]")
{
	const Vertex vertices[] = {{{2, 0, 1}, {1, 0, 0}, {0.5f, 0.75f, 1}, 1}};
	Scene scene;
	scene.AddModel({"test", vertices}, {10, 20, 30}, 0, {0.2f, 0.4f, 0.6f}, 2);
	REQUIRE(scene.vertices.size() == 1);
	CHECK(scene.vertices[0].position.x == 14);
	CHECK(scene.vertices[0].position.y == 20);
	CHECK(scene.vertices[0].position.z == 32);
	CHECK(scene.vertices[0].colour.r == Approx(0.1f));
	CHECK(scene.vertices[0].colour.g == Approx(0.3f));
	CHECK(scene.vertices[0].colour.b == Approx(0.6f));
	CHECK(vertices[0].position.x == 2);
	CHECK(vertices[0].colour.g == 0.75f);
}

TEST_CASE("Tiled perspective rendering preserves full-image rays and projection", "[renderer3d]")
{
	for (float rotation : {0.0f, 0.37f, 1.0f, 2.0f, 3.0f, 3.8f}) {
		Camera full{{100, 200, 32}, 1, 32000, 16000, rotation};
		Camera tile = full.Cropped(15200, 7800, 1600, 200);
		Vec3 point{145, 170, 48};
		auto a = full.Project(point), b = tile.Project(point);
		CHECK(b.x == Approx(a.x - tile.crop_x));
		CHECK(b.y == Approx(a.y - tile.crop_y));
		auto r1 = full.ScreenRay(15600, 7850), r2 = tile.ScreenRay(400, 50);
		CHECK(r1.direction.x == Approx(r2.direction.x));
		CHECK(r1.direction.y == Approx(r2.direction.y));
		CHECK(r1.direction.z == Approx(r2.direction.z));
		auto m = tile.Matrix();
		Vec3 p = point - tile.focus;
		std::array<float, 4> v{p.x, p.y, p.z, 1}, clip{};
		for (int r = 0; r < 4; ++r) for (int c = 0; c < 4; ++c) clip[r] += m[c * 4 + r] * v[c];
		CHECK((clip[0] / clip[3] + 1) * 800 == Approx(b.x).margin(0.01));
		CHECK((1 - clip[1] / clip[3]) * 100 == Approx(b.y).margin(0.01));
		auto nested = tile.Cropped(200, 50, 300, 100).Project(point);
		CHECK(nested.x == Approx(b.x - 200));
		CHECK(nested.y == Approx(b.y - 50));
	}
}

TEST_CASE("Perspective zoom and drag preserve their world-space anchor", "[renderer3d]")
{
	for (float rotation : {0.0f, 0.37f, 1.0f, 2.0f, 3.0f, 3.8f}) {
		for (float scale : {0.125f, 1.0f, 2.0f}) {
			Camera camera{{1024, 1024, 32}, scale, 1280, 800, rotation};
			for (Vec3 anchor : {Vec3{1000, 1050, 0}, Vec3{1024, 1024, 32}, Vec3{1030, 1000, 64}}) {
				auto screen = camera.Project(anchor);
				for (float zoom : {0.5f, 2.0f}) {
					Camera changed = camera;
					changed.pixels_per_unit *= zoom;
					auto focus = changed.FocusForAnchor(anchor, screen.x, screen.y);
					REQUIRE(focus.has_value());
					changed.focus = *focus;
					auto after = changed.Project(anchor);
					CHECK(after.x == Approx(screen.x).margin(0.01));
					CHECK(after.y == Approx(screen.y).margin(0.01));
				}
				Camera dragged = camera;
				auto focus = dragged.FocusForAnchor(anchor, screen.x + 53, screen.y - 27);
				REQUIRE(focus.has_value());
				dragged.focus = *focus;
				auto after = dragged.Project(anchor);
				CHECK(after.x == Approx(screen.x + 53).margin(0.01));
				CHECK(after.y == Approx(screen.y - 27).margin(0.01));
			}
		}
	}
}
