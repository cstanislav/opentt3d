/* SPDX-License-Identifier: GPL-2.0-only */
/** @file renderer3d_voxels.cpp Exposed-volume, palette and greedy-meshing invariants. */
#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "voxel_geometry.hpp"
#include "voxel_models.h"
#include "camera.hpp"
#include "voxel_visibility.hpp"
#include "voxel_visibility_worker.hpp"
#include <map>
#include <numbers>
#include <set>

using namespace Renderer3D;
using Catch::Detail::Approx;

TEST_CASE("Background voxel visibility cancels stale cameras and owns its complete value snapshot", "[renderer3d][voxel]")
{
	VoxelGrid grid({8,8,8},{{{72,73,74,75,76,77}}}); grid.Fill({1,1,1},{7,7,7},1);
	auto mesh = grid.Mesh(false);
	auto packed = grid.Pack(mesh,true);
	REQUIRE(packed != nullptr);
	std::vector<InstanceData> instances(80);
	for (unsigned i = 0; i < instances.size(); ++i) instances[i].origin_opacity = {static_cast<float>(i%10)*5,static_cast<float>(i/10)*5,0,1};
	Camera first{{20,20,4},0.12f,128,96,0.15f}, current = first;
	current.rotation = 1.25f;
	VoxelVisibilityWorker worker(GENERATE(1U,2U));
	worker.SetCamera(first,8); worker.Request(mesh.vertices,packed,instances,instances.size());
	worker.SetCamera(current,8); worker.Request(mesh.vertices,packed,instances,instances.size());
	const auto snapshot = instances;
	instances.front().origin_opacity[0] += 100;
	REQUIRE(worker.WaitIdle(std::chrono::seconds(10)));
	CHECK(worker.TakeError().empty());
	auto result = worker.Take(mesh.vertices);
	REQUIRE(result.has_value());
	REQUIRE(result->transforms.size() == snapshot.size());
	CHECK(result->transforms.front() == VoxelVisibilityTransform(snapshot.front()));
	CHECK_FALSE(result->transforms.front() == VoxelVisibilityTransform(instances.front()));
	VoxelVisibilityCache reference;
	reference.Begin(current,8,snapshot.size());
	auto lookup = MakePackedVoxelLookup(packed->vertices);
	std::vector<VisibleVoxelTriangle> expected;
	std::vector<VisibleVoxelTriangle> actual;
	REQUIRE(result->geometry.size() == snapshot.size());
	for (unsigned instance = 0; instance < snapshot.size(); ++instance) {
		for (uint64_t triangle : reference.PackedTriangles(mesh.vertices,snapshot[instance],lookup.indices,lookup.bits)) {
			uint64_t word = triangle | (static_cast<uint64_t>(instance)<<(lookup.bits*3));
			expected.push_back({static_cast<uint32_t>(word),static_cast<uint32_t>(word>>32)});
		}
		for (uint64_t triangle : *result->geometry[instance]) {
			uint64_t word = triangle | (static_cast<uint64_t>(instance)<<(lookup.bits*3));
			actual.push_back({static_cast<uint32_t>(word),static_cast<uint32_t>(word>>32)});
		}
	}
	CHECK(actual == expected);
	VoxelVisibilityCache adopted;
	adopted.Begin(current,8,snapshot.size());
	for (unsigned instance = 0; instance < snapshot.size(); ++instance) {
		adopted.AdoptPacked(mesh.vertices,result->transforms[instance],std::move(result->geometry[instance]));
		CHECK(adopted.HasPacked(mesh.vertices,snapshot[instance]));
		auto cached = adopted.PackedTriangles(mesh.vertices,snapshot[instance],lookup.indices,lookup.bits);
		auto original = reference.PackedTriangles(mesh.vertices,snapshot[instance],lookup.indices,lookup.bits);
		CHECK(std::equal(cached.begin(),cached.end(),original.begin(),original.end()));
	}
	CHECK_FALSE(adopted.HasPacked(mesh.vertices,instances.front()));
	CHECK_FALSE(worker.Take(mesh.vertices));
	worker.Cancel();
}

TEST_CASE("Parallel voxel preparation preserves the newest per-mesh snapshot and cancellation", "[renderer3d][voxel]")
{
	VoxelGrid grid({8,8,12},{{{72,73,74,75,76,77}}}); grid.Fill({1,1,1},{7,7,11},1);
	std::array<VoxelMesh,3> meshes{grid.Mesh(false),grid.Mesh(false),grid.Mesh(false)};
	auto packed = grid.Pack(meshes.front(),true);
	REQUIRE(packed != nullptr);
	std::vector<InstanceData> instances(96);
	for (unsigned i = 0; i < instances.size(); ++i) instances[i].origin_opacity = {static_cast<float>(i%12)*5,static_cast<float>(i/12)*5,0,1};
	Camera camera{{25,20,4},0.12f,128,96,0.15f};
	VoxelVisibilityWorker worker(2);
	worker.SetCamera(camera,8);
	for (auto &mesh : meshes) worker.Request(mesh.vertices,packed,instances,instances.size());
	worker.Cancel();
	camera.rotation = 2.25f;
	worker.SetCamera(camera,8);
	for (unsigned update = 0; update < 6; ++update) {
		instances.front().origin_opacity[0] = static_cast<float>(update)*3;
		for (auto &mesh : meshes) worker.Request(mesh.vertices,packed,instances,instances.size());
	}
	instances.front().origin_opacity[0] = 0;
	for (auto &mesh : meshes) worker.Request(mesh.vertices,packed,instances,instances.size());
	const auto snapshot = instances;
	instances.clear();
	REQUIRE(worker.WaitIdle(std::chrono::seconds(20)));
	CHECK(worker.TakeError().empty());
	auto lookup = MakePackedVoxelLookup(packed->vertices);
	VoxelVisibilityCache reference;
	reference.Begin(camera,8,snapshot.size());
	for (auto &mesh : meshes) {
		auto result = worker.Take(mesh.vertices);
		REQUIRE(result.has_value());
		REQUIRE(result->geometry.size() == snapshot.size());
		for (size_t i = 0; i < snapshot.size(); ++i) {
			CHECK(result->transforms[i] == VoxelVisibilityTransform(snapshot[i]));
			auto expected = reference.PackedTriangles(mesh.vertices,snapshot[i],lookup.indices,lookup.bits);
			CHECK(std::equal(result->geometry[i]->begin(),result->geometry[i]->end(),expected.begin(),expected.end()));
		}
	}
}

TEST_CASE("Shared visibility results survive cache eviction without copying or mutation", "[renderer3d][voxel]")
{
	VoxelGrid grid({8,8,8},{{{72,73,74,75,76,77}}}); grid.Fill({1,1,1},{7,7,7},1);
	auto mesh = grid.Mesh(false);
	auto packed = grid.Pack(mesh,true);
	REQUIRE(packed != nullptr);
	auto lookup = MakePackedVoxelLookup(packed->vertices);
	Camera camera{{4,4,4},0.12f,128,96,0.15f};
	InstanceData instance;
	VoxelVisibilityCache producer, consumer;
	producer.Begin(camera,4,1); consumer.Begin(camera,4,1);
	auto shared = producer.SharedPackedTriangles(mesh.vertices,instance,lookup.indices,lookup.bits);
	REQUIRE_FALSE(shared->empty());
	const auto original = *shared;
	consumer.AdoptPacked(mesh.vertices,VoxelVisibilityTransform(instance),shared);
	CHECK(consumer.PackedTriangles(mesh.vertices,instance,lookup.indices,lookup.bits).data() == shared->data());
	CHECK(producer.SharedPackedTriangles(mesh.vertices,instance,lookup.indices,lookup.bits) == shared);
	/* The unpacked diagnostic path may be rebuilt, but must not append to or
	 * mutate a packed result already being read on another thread. */
	const auto triangles = producer.Triangles(mesh.vertices,instance);
	CHECK(triangles.size() == shared->size());
	camera.rotation += 1;
	producer.Begin(camera,4,1);
	CHECK_FALSE(producer.HasPacked(mesh.vertices,instance));
	CHECK(*shared == original);
	CHECK(consumer.PackedTriangles(mesh.vertices,instance,lookup.indices,lookup.bits).data() == shared->data());
	consumer.Begin(camera,4,1);
	CHECK(shared.use_count() == 1);
	CHECK(*shared == original);
}

TEST_CASE("Idle visibility workers release cancelled camera results without another request", "[renderer3d][voxel]")
{
	VoxelGrid grid({8,8,8},{{{72,73,74,75,76,77}}}); grid.Fill({1,1,1},{7,7,7},1);
	auto mesh = grid.Mesh(false);
	auto packed = grid.Pack(mesh,true);
	REQUIRE(packed != nullptr);
	Camera camera{{4,4,4},0.12f,128,96,0.15f};
	std::array<InstanceData,1> instances;
	VoxelVisibilityWorker worker(GENERATE(1U,2U));
	for (unsigned cycle = 0; cycle < 4; ++cycle) {
		worker.SetCamera(camera,4);
		worker.Request(mesh.vertices,packed,instances,instances.size());
		REQUIRE(worker.WaitIdle(std::chrono::seconds(10)));
		auto result = worker.Take(mesh.vertices);
		REQUIRE(result.has_value());
		REQUIRE(result->geometry.size() == 1);
		std::weak_ptr<const std::vector<uint64_t>> retained = result->geometry.front();
		result.reset();
		CHECK_FALSE(retained.expired());
		worker.Cancel();
		REQUIRE(worker.WaitIdle(std::chrono::seconds(10)));
		CHECK(retained.expired());
		CHECK_FALSE(worker.Take(mesh.vertices));
		camera.rotation += 0.25f;
	}
}

TEST_CASE("Conservative voxel pixel bounds retain projected triangle sample coverage", "[renderer3d][voxel]")
{
	VoxelGrid grid({24,24,40},{{{72,73,74,75,76,77}}},{-6,-6,0},{0.5f,0.5f,0.5f});
	grid.Fill({2,3,0},{22,21,30},1); grid.Fill({7,8,30},{17,16,40},1);
	auto mesh = grid.Mesh(false);
	VoxelVisibilityCache cache;
	size_t culled = 0;
	for (Vec3 origin : {Vec3{},Vec3{500000,700000,100}}) for (float scale : {0.03f,0.12f,0.3f}) for (float turn : {0.15f,1.25f,2.65f}) {
		InstanceData data; data.origin_opacity = {origin.x,origin.y,origin.z,1};
		Camera camera{origin+Vec3{0,0,10},scale,120,90,turn}; camera.vertical_fov = 40;
		cache.Begin(camera,8,1);
		auto triangles = cache.Triangles(mesh.vertices,data);
		CHECK(std::is_sorted(triangles.begin(),triangles.end()));
		CHECK(cache.Triangles(mesh.vertices,data).size() == triangles.size());
		std::vector<bool> kept(mesh.vertices.size()/3);
		for (auto index : triangles) { REQUIRE(index%3 == 0); kept[index/3] = true; }
		for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
			if (kept[i/3]) continue;
			++culled;
			ScreenPoint a = camera.Project(origin+mesh.vertices[i].position), b = camera.Project(origin+mesh.vertices[i+1].position), c = camera.Project(origin+mesh.vertices[i+2].position);
			REQUIRE(a.visible); REQUIRE(b.visible); REQUIRE(c.visible);
			auto edge = [](ScreenPoint p, ScreenPoint q, double x, double y) { return (static_cast<double>(q.x)-p.x)*(y-p.y)-(static_cast<double>(q.y)-p.y)*(x-p.x); };
			/* This stream, like the native palette pipeline, culls back faces. */
			if (edge(a,b,c.x,c.y) >= -1e-12) continue;
			int low_x = std::max(0,static_cast<int>(std::ceil(std::min({a.x,b.x,c.x})-0.503)));
			int high_x = std::min(camera.width-1,static_cast<int>(std::floor(std::max({a.x,b.x,c.x})-0.497)));
			int low_y = std::max(0,static_cast<int>(std::ceil(std::min({a.y,b.y,c.y})-0.503)));
			int high_y = std::min(camera.height-1,static_cast<int>(std::floor(std::max({a.y,b.y,c.y})-0.497)));
			for (int y = low_y; y <= high_y; ++y) for (int x = low_x; x <= high_x; ++x) for (double dx : {-0.5/256,0.0,0.5/256}) for (double dy : {-0.5/256,0.0,0.5/256}) {
				double e0 = edge(a,b,x+0.5+dx,y+0.5+dy), e1 = edge(b,c,x+0.5+dx,y+0.5+dy), e2 = edge(c,a,x+0.5+dx,y+0.5+dy);
				CHECK_FALSE(((e0 >= 0 && e1 >= 0 && e2 >= 0) || (e0 <= 0 && e1 <= 0 && e2 <= 0)));
			}
		}
	}
	CHECK(culled > mesh.vertices.size()/3);
	Camera inside{{0,0,5},1,120,90}; inside.first_person = true;
	InstanceData identity;
	CHECK(VoxelPixelProjector(inside,identity,8).Visible({-6,-6,0},{6,6,20}));
}

TEST_CASE("Indexed visible voxel streams preserve corners, instance identity and chunk resets", "[renderer3d][voxel]")
{
	const std::array<uint32_t,6> source{17,41,73,17,73,89};
	auto lookup = MakePackedVoxelLookup(source);
	IndexedVoxelVisibility stream(lookup);
	auto triangle = [&](size_t first) {
		return static_cast<uint64_t>(lookup.indices[first]) |
			(static_cast<uint64_t>(lookup.indices[first+1])<<lookup.bits) |
			(static_cast<uint64_t>(lookup.indices[first+2])<<(lookup.bits*2));
	};
	for (uint32_t instance : {7U,8U}) {
		stream.BeginInstance(instance);
		stream.Add(triangle(0)); stream.Add(triangle(3));
	}
	REQUIRE(stream.vertices.size() == 8);
	REQUIRE(stream.indices.size() == 12);
	for (size_t i = 0; i < stream.indices.size(); ++i) {
		const auto &vertex = stream.vertices.at(stream.indices[i]);
		CHECK(vertex[0] == source[i%source.size()]);
		CHECK(vertex[1] == 7+i/source.size());
	}
	stream.Clear(); stream.Add(triangle(3));
	REQUIRE(stream.vertices.size() == 3);
	REQUIRE(stream.indices.size() == 3);
	for (size_t i = 0; i < 3; ++i) {
		CHECK(stream.vertices.at(stream.indices[i])[0] == source[3+i]);
		CHECK(stream.vertices.at(stream.indices[i])[1] == 8);
	}
}

TEST_CASE("Packed voxel meshes retain every vertex bit, primitive order and signed normals", "[renderer3d][voxel]")
{
	VoxelGrid grid({48,48,100},{{{1,2,3,4,5,6}},{{255,250,251,252,253,254}}},{-6,-6,-0.5f},{0.25f,0.25f,0.5f});
	grid.Fill({10,10,0},{38,38,80},1);
	grid.Fill({18,18,20},{30,30,100},2);
	grid.Fill({20,20,10},{28,28,75},0);
	for (bool greedy : {false,true}) {
		auto mesh = grid.Mesh(greedy);
		for (auto &vertex : mesh.vertices) vertex.company_colour = -0.0f;
		mesh.vertices[0].normal.y = -0.0f;
		mesh.vertices[1].normal.x = std::nextafter(-1.0f,0.0f);
		auto packed = grid.Pack(mesh);
		REQUIRE(packed != nullptr);
		auto automatic = AutoPackVoxelMesh(mesh.vertices,true);
		REQUIRE(automatic != nullptr);
		for (size_t i = 0; i < mesh.vertices.size(); ++i) CHECK(std::bit_cast<std::array<uint32_t,20>>(automatic->Decode(automatic->vertices[i])) == std::bit_cast<std::array<uint32_t,20>>(mesh.vertices[i]));
		CHECK(packed->format[7] == 1);
		REQUIRE(packed->vertices.size() == mesh.vertices.size());
		for (size_t i = 0; i < mesh.vertices.size(); ++i) CHECK(std::bit_cast<std::array<uint32_t,20>>(packed->Decode(packed->vertices[i])) == std::bit_cast<std::array<uint32_t,20>>(mesh.vertices[i]));
		auto indexed = IndexPackedVoxelMesh(packed->vertices);
		if (!indexed.indices.empty()) {
			REQUIRE(indexed.indices.size() == packed->vertices.size());
			for (size_t i = 0; i < indexed.indices.size(); ++i) CHECK(indexed.vertices[indexed.indices[i]] == packed->vertices[i]);
		}
		auto lookup = MakePackedVoxelLookup(packed->vertices);
		REQUIRE(lookup.bits*3 <= 63);
		for (size_t first = 0; first < lookup.indices.size(); first += 3) {
			uint64_t triangle = static_cast<uint64_t>(lookup.indices[first]) | (static_cast<uint64_t>(lookup.indices[first+1])<<lookup.bits) |
				(static_cast<uint64_t>(lookup.indices[first+2])<<(lookup.bits*2));
			uint64_t instance = std::min<uint64_t>(37,(uint64_t{1}<<(64-lookup.bits*3))-1);
			triangle |= instance<<(lookup.bits*3);
			CHECK((triangle>>(lookup.bits*3)) == instance);
			for (unsigned corner = 0; corner < 3; ++corner) CHECK(lookup.vertices[(triangle>>(lookup.bits*corner))&((1U<<lookup.bits)-1)] == packed->vertices[first+corner]);
		}
	}
}

TEST_CASE("Packed voxel meshes refuse nonrepresentable attributes and oversized layouts", "[renderer3d][voxel]")
{
	VoxelGrid grid({8,8,8},{{{72,73,74,75,76,77}}});
	grid.Fill({1,1,1},{7,7,7},1);
	auto mesh = grid.Mesh();
	REQUIRE(grid.Pack(mesh) != nullptr);
	for (unsigned change = 0; change < 6; ++change) {
		auto vertices = mesh.vertices;
		switch (change) {
			case 0: vertices[0].position.x += 0.125f; break;
			case 1: vertices[0].opacity = 0.5f; break;
			case 2: vertices[0].object_id = 7; break;
			case 3: vertices[0].texture_region.right = 0.25f; break;
			case 4: vertices[0].texture.x = 0.123f; break;
			case 5: vertices[0].position.z = INFINITY; break;
		}
		CHECK_FALSE(PackVoxelMesh(vertices,{8,8,8},{},VOXEL_CELL_SIZE));
	}
	CHECK_FALSE(PackVoxelMesh(mesh.vertices,{1024,1024,1024},{},VOXEL_CELL_SIZE));
	VoxelGrid fractional({8,8,8},{{{72,73,74,75,76,77}}},{},{0.3f,0.25f,0.5f});
	fractional.Fill({1,1,1},{7,7,7},1);
	auto inexact = fractional.Pack(fractional.Mesh());
	REQUIRE(inexact != nullptr);
	CHECK(inexact->format[7] == 0);
}

TEST_CASE("Packed voxel volumes retain every cell, face colour and physical bound", "[renderer3d][voxel]")
{
	std::vector<VoxelMaterial> colours{{{1,2,3,4,5,6}},{{250,251,252,253,254,255}}};
	VoxelGrid grid({3,5,7},colours,{0.125f,-0.375f,0.5f},{0.5f,0.25f,0.75f});
	grid.Fill({1,1,1},{3,4,6},1);
	grid.Fill({2,3,5},{3,5,7},2);
	auto volume = grid.Volume();
	CHECK(volume->Size() == std::array<int,3>{3,5,7});
	CHECK(volume->Origin() == Vec3{0.125f,-0.375f,0.5f});
	CHECK(volume->Step() == Vec3{0.5f,0.25f,0.75f});
	for (int z = -1; z <= 7; ++z) for (int y = -1; y <= 5; ++y) for (int x = -1; x <= 3; ++x) CHECK(volume->Get(x,y,z) == grid.Get(x,y,z));
	for (unsigned material = 1; material <= 2; ++material) for (unsigned face = 0; face < 6; ++face) CHECK(volume->Colour(material,face) == colours[material-1].colours[face]);
	CHECK_THROWS_AS(volume->Colour(0,0),std::out_of_range);
	CHECK_THROWS_AS(volume->Colour(2,6),std::out_of_range);
	REQUIRE(volume->bounds.size() == 36);
	auto mesh = grid.Mesh();
	Vec3 step = volume->Step();
	for (auto &vertex : volume->bounds) {
		CHECK((vertex.position.x == mesh.low.x-step.x || vertex.position.x == mesh.high.x+step.x));
		CHECK((vertex.position.y == mesh.low.y-step.y || vertex.position.y == mesh.high.y+step.y));
		CHECK((vertex.position.z == mesh.low.z-step.z || vertex.position.z == mesh.high.z+step.z));
	}
	CHECK((volume->words[volume->words[7]+(3*5*7)/2] >> 16) == 0); // Odd packed cell has no stray upper material.
}

TEST_CASE("Voxel surface skipping bounds agree with independent exhaustive cell distances", "[renderer3d][voxel]")
{
	for (unsigned pattern = 0; pattern < 3; ++pattern) {
		VoxelGrid grid({13,11,9},{{{72,73,74,75,76,77}}});
		if (pattern == 0) grid.Fill({4,3,2},{9,8,7},1);
		else if (pattern == 1) { grid.Fill({1,8,1},{3,10,3},1); grid.Fill({10,1,6},{12,3,8},1); }
		else { grid.Fill({0,0,0},{13,11,9},1); grid.Fill({2,2,2},{11,9,7},0); }
		auto volume = grid.Volume();
		std::vector<std::array<int,3>> surface;
		std::set<std::pair<unsigned,int>> expected_planes, actual_planes;
		for (int z = 0; z < 9; ++z) for (int y = 0; y < 11; ++y) for (int x = 0; x < 13; ++x) {
			unsigned mask = 0, material = grid.Get(x,y,z);
			if (material != 0) {
				const int offsets[6][3] = {{-1,0,0},{1,0,0},{0,-1,0},{0,1,0},{0,0,-1},{0,0,1}};
				for (unsigned face = 0; face < 6; ++face) if (grid.Get(x+offsets[face][0],y+offsets[face][1],z+offsets[face][2]) == 0) mask |= 1U<<face;
			}
			uint32_t word = volume->words[volume->words[20]+(z*11+y)*13+x];
			REQUIRE((word&65535U) == material); REQUIRE(((word>>16)&63U) == mask);
			if (mask != 0) surface.push_back({x,y,z});
			for (unsigned face = 0; face < 6; ++face) if ((mask&(1U<<face)) != 0) expected_planes.emplace(face,std::array<int,3>{x,y,z}[face/2]);
		}
		REQUIRE(volume->slices.size()%6 == 0);
		for (size_t i = 0; i < volume->slices.size(); i += 6) {
			const auto &vertex = volume->slices[i];
			unsigned face = vertex.normal.x != 0 ? (vertex.normal.x > 0 ? 1 : 0) : vertex.normal.y != 0 ? (vertex.normal.y > 0 ? 3 : 2) : (vertex.normal.z > 0 ? 5 : 4);
			unsigned axis = face/2;
			float plane = std::array<float,3>{vertex.position.x,vertex.position.y,vertex.position.z}[axis];
			int layer = static_cast<int>(std::round(plane/(axis == 2 ? 1 : 0.5f)))-(face&1U);
			CHECK(actual_planes.emplace(face,layer).second);
			for (unsigned corner = 0; corner < 6; ++corner) {
				const auto &p = volume->slices[i+corner];
				CHECK(p.normal == vertex.normal);
				CHECK(std::array<float,3>{p.position.x,p.position.y,p.position.z}[axis] == plane);
			}
		}
		CHECK(actual_planes == expected_planes);
		REQUIRE_FALSE(surface.empty());
		for (int z = 0; z < 9; ++z) for (int y = 0; y < 11; ++y) for (int x = 0; x < 13; ++x) {
			unsigned expected = 255;
			for (auto point : surface) expected = std::min<unsigned>(expected,std::max({std::abs(point[0]-x),std::abs(point[1]-y),std::abs(point[2]-z)}));
			CHECK((volume->words[volume->words[20]+(z*11+y)*13+x]>>24) == expected);
		}
	}
}

TEST_CASE("Voxel rays preserve all six faces, openings and inside-volume backface rules", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,4,4},{{{72,73,74,75,76,77}}},{0.25f,-0.5f,2});
	grid.Fill({1,1,1},{3,3,3},1);
	auto volume = grid.Volume();
	const Vec3 centre{1.25f,0.5f,4};
	const Vec3 directions[] = {{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
	for (unsigned face = 0; face < 6; ++face) {
		auto hit = volume->Trace(centre-directions[face]*4,directions[face]);
		REQUIRE(hit.has_value());
		CHECK(hit->face == face);
		CHECK(hit->colour == 72+face);
		CHECK(hit->distance == Approx(face < 4 ? 3.5 : 3));
		CHECK_FALSE(volume->Trace(centre,directions[face]));
	}
	CHECK_FALSE(volume->Trace({8,8,8},{1,0,0}));
	CHECK_THROWS_AS(volume->Trace({},{}),std::invalid_argument);
	VoxelGrid split({6,2,2},{{{72,73,74,75,76,77}},{{80,81,82,83,84,85}}},{},{1,1,1});
	split.Fill({0,0,0},{2,2,2},1); split.Fill({3,0,0},{6,2,2},2);
	auto hit = split.Volume()->Trace({1,0.5f,0.5f},{1,0,0});
	REQUIRE(hit.has_value());
	CHECK(hit->distance == Approx(2)); CHECK(hit->colour == 80);
}

TEST_CASE("Voxel front proxies retain mesh fallback when the eye or near plane intersects their bounds", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,4,4},{{{72,73,74,75,76,77}}},{},{1,1,1});
	grid.Fill({0,0,0},{4,4,4},1);
	auto volume = grid.Volume();
	for (Vec3 origin : {Vec3{},Vec3{500000,700000,320}}) for (float xy : {0.5f,1.0f,2.0f}) {
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,1};
		data.scale_center = {xy,1,0,0};
		Camera camera{origin,1,256,256};
		CHECK(VolumeOutsideNearPlane(*volume,data,camera.Frustum()));
		camera.first_person = true;
		for (float rotation : {0.0f,0.7f,1.4f,2.2f,3.1f}) {
			camera.rotation = rotation;
			camera.SetFocusRelative(origin,{2*xy,2*xy,2});
			CHECK_FALSE(VolumeOutsideNearPlane(*volume,data,camera.Frustum()));
			camera.SetFocusRelative(origin,Vec3{2*xy,2*xy,2}+camera.Unrotate(Camera::World(camera.Back()*30)));
			CHECK(VolumeOutsideNearPlane(*volume,data,camera.Frustum()));
		}
	}
}

TEST_CASE("Voxel ray traversal agrees with independent exposed-triangle intersections", "[renderer3d][voxel]")
{
	VoxelGrid grid({9,7,11},{{{72,73,74,75,76,77}},{{80,81,82,83,84,85}}},{-2,-1,-0.75f},{0.5f,0.25f,0.75f});
	for (int z = 0; z < 11; ++z) for (int y = 0; y < 7; ++y) for (int x = 0; x < 9; ++x) {
		if ((x*x+3*y+7*z)%5 < 3) grid.Fill({x,y,z},{x+1,y+1,z+1},1+(x+y+z)%2);
	}
	auto volume = grid.Volume();
	auto mesh = grid.Mesh(false);
	for (unsigned ray = 0; ray < 180; ++ray) {
		float angle = ray*0.137f;
		Vec3 origin{8*std::cos(angle),8*std::sin(angle),-3+static_cast<float>(ray%29)*0.537f};
		Vec3 target{-1.31f+(ray%17)*0.173f,-0.67f+(ray%13)*0.109f,0.13f+(ray%19)*0.317f};
		Vec3 direction = Normalize(target-origin);
		double closest = INFINITY;
		unsigned colour = 0;
		for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
			const auto &a = mesh.vertices[i];
			if (Dot(a.normal,direction) >= 0) continue;
			Vec3 e1 = mesh.vertices[i+1].position-a.position, e2 = mesh.vertices[i+2].position-a.position;
			Vec3 p{direction.y*e2.z-direction.z*e2.y,direction.z*e2.x-direction.x*e2.z,direction.x*e2.y-direction.y*e2.x};
			double determinant = Dot(e1,p);
			if (std::abs(determinant) < 1e-12) continue;
			Vec3 t = origin-a.position;
			double u = Dot(t,p)/determinant;
			if (u < 0 || u > 1) continue;
			Vec3 q{t.y*e1.z-t.z*e1.y,t.z*e1.x-t.x*e1.z,t.x*e1.y-t.y*e1.x};
			double v = Dot(direction,q)/determinant;
			if (v < 0 || u+v > 1) continue;
			double distance = Dot(e2,q)/determinant;
			if (distance >= 0 && distance < closest) { closest = distance; colour = static_cast<unsigned>(a.texture.x*256); }
		}
		auto hit = volume->Trace(origin,direction);
		REQUIRE(hit.has_value() == std::isfinite(closest));
		if (hit) { CHECK(hit->distance == Approx(closest).margin(0.00002)); CHECK(hit->colour == colour); }
	}
}

TEST_CASE("Voxel vehicle climate overrides preserve shared cargo pairs without cross-climate leakage", "[renderer3d][voxel]")
{
	for (unsigned climate = 0; climate < 4; ++climate) for (bool loaded : {false,true}) {
		CHECK(SelectVoxelVehicleState(0x03,loaded,climate) == (loaded ? 1U : 0U));
		CHECK_FALSE(SelectVoxelVehicleState(0,loaded,climate));
	}
	/* Food vans have different Arctic/tropical rear panels under the same
	 * original engine and sprite IDs, with no shared temperate/Toyland body. */
	CHECK_FALSE(SelectVoxelVehicleState(0x3C,false,0));
	CHECK_FALSE(SelectVoxelVehicleState(0x3C,true,3));
	CHECK(SelectVoxelVehicleState(0x3C,false,1) == 2);
	CHECK(SelectVoxelVehicleState(0x3C,true,1) == 3);
	CHECK(SelectVoxelVehicleState(0x3C,false,2) == 4);
	CHECK(SelectVoxelVehicleState(0x3C,true,2) == 5);
	CHECK(SelectVoxelVehicleState(0x33,false,1) == 0);
	CHECK(SelectVoxelVehicleState(0x33,true,2) == 5);
	CHECK(SelectVoxelVehicleState(0x33,true,3) == 1);
	CHECK(SelectVoxelVehicleState(0xC3,false,3) == 6);
	CHECK(SelectVoxelVehicleState(0xC3,true,3) == 7);
	CHECK_FALSE(SelectVoxelVehicleState(0xFF,false,4));
	CHECK_FALSE(SelectVoxelVehicleState(0xFF,true,UINT_MAX));
}

TEST_CASE("Original train voxel bodies retain source proportions without overlapping map-step couplings", "[renderer3d][voxel]")
{
	for (float length : {10.0f,10.25f}) for (unsigned pose = 0; pose < 360; ++pose) {
		float heading = pose*std::numbers::pi_v<float>/180;
		float step = std::max(std::abs(std::cos(heading)),std::abs(std::sin(heading)));
		float span = length*OriginalTrainVoxelScale(heading,length);
		CHECK(span*step == Approx(7.25f).margin(0.00001f));
		CHECK(8.0f/step-span >= 0.749f);
	}
	CHECK(OriginalTrainVoxelScale(0,10) == Approx(0.725f));
	CHECK(OriginalTrainVoxelScale(std::numbers::pi_v<float>/4,10.25f) == Approx(1.0002974f));
	CHECK_THROWS_AS(OriginalTrainVoxelScale(0,0),std::invalid_argument);
	CHECK_THROWS_AS(OriginalTrainVoxelScale(std::numeric_limits<float>::infinity(),10),std::invalid_argument);
}

static std::pair<double,double> VoxelAreaVolume(const VoxelMesh &mesh)
{
	double area = 0, volume = 0;
	for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
		Vec3 a = mesh.vertices[i].position, b = mesh.vertices[i+1].position, c = mesh.vertices[i+2].position;
		Vec3 u = b-a, v = c-a;
		Vec3 cross{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
		area += std::sqrt(Dot(cross,cross))/2;
		Vec3 bc{b.y*c.z-b.z*c.y,b.z*c.x-b.x*c.z,b.x*c.y-b.y*c.x};
		volume += Dot(a,bc)/6;
	}
	return {area,volume};
}

TEST_CASE("Voxel meshes merge colour-compatible faces and eliminate internal boundaries", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,3,2},{{{72,73,74,75,76,77}},{{80,81,82,83,84,85}}},{2,4,8});
	grid.Fill({0,0,0},{4,3,2},1);
	auto merged = grid.Mesh(), cells = grid.Mesh(false);
	CHECK(merged.occupied == 24);
	CHECK(merged.exposed_faces == 52);
	CHECK(merged.quads == 6);
	CHECK(merged.vertices.size() < cells.vertices.size());
	CHECK(cells.quads == 52);
	CHECK(merged.low == Vec3{2,4,8});
	CHECK(merged.high == Vec3{4,5.5f,10});
	auto [area,volume] = VoxelAreaVolume(merged);
	CHECK(area == Approx(20));
	CHECK(volume == Approx(6));
	CHECK(VoxelAreaVolume(cells).first == Approx(area));
	grid.Fill({2,0,0},{4,3,2},2);
	merged = grid.Mesh();
	CHECK(merged.exposed_faces == 52); // Different colours do not expose internal walls.
	CHECK(merged.quads == 10);
	CHECK(VoxelAreaVolume(merged).second == Approx(6));
}

TEST_CASE("Coplanar voxel colour borders retain cell diagonals while interiors still merge", "[renderer3d][voxel]")
{
	VoxelGrid grid({32,8,1},{{{74,74,74,74,74,74}},{{204,204,204,204,204,204}}});
	grid.Fill({0,0,0},{32,8,1},1);
	grid.Fill({0,0,0},{32,1,1},2);
	auto merged = grid.Mesh(), reference = grid.Mesh(false);
	CHECK(merged.quads == 10);
	CHECK(merged.exposed_faces == reference.exposed_faces);
	CHECK(merged.vertices.size() < reference.vertices.size());
	unsigned protected_triangles = 0;
	bool merged_interior = false;
	for (size_t i = 0; i < merged.vertices.size(); i += 3) {
		if (merged.vertices[i].normal.z < 0.9f) continue;
		Vec3 a = merged.vertices[i].position, b = merged.vertices[i+1].position, c = merged.vertices[i+2].position;
		float xmin = std::min({a.x,b.x,c.x}), xmax = std::max({a.x,b.x,c.x});
		float ymin = std::min({a.y,b.y,c.y}), ymax = std::max({a.y,b.y,c.y});
		if (ymin < 1) {
			CHECK(xmax-xmin <= 0.5f);
			CHECK(ymax-ymin <= 0.5f);
			++protected_triangles;
		} else {
			merged_interior |= xmax-xmin > 0.5f || ymax-ymin > 0.5f;
		}
	}
	CHECK(protected_triangles == 128);
	CHECK(merged_interior);
	CHECK(VoxelAreaVolume(merged).first == Approx(VoxelAreaVolume(reference).first));
	CHECK(VoxelAreaVolume(merged).second == Approx(VoxelAreaVolume(reference).second));
}

TEST_CASE("Voxel cavities and thin parts keep exact volume, face normals and palette cells", "[renderer3d][voxel]")
{
	VoxelGrid grid({5,5,5},{{{1,2,3,4,5,6}}});
	grid.Fill({0,0,0},{5,5,5},1);
	grid.Fill({1,1,1},{4,4,4},0);
	auto mesh = grid.Mesh();
	CHECK(mesh.occupied == 98);
	CHECK(mesh.quads == 12);
	CHECK(VoxelAreaVolume(mesh).second == Approx(98*0.25));
	for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
		const auto &a = mesh.vertices[i], &b = mesh.vertices[i+1], &c = mesh.vertices[i+2];
		CHECK(Dot(a.normal,Normal(a.position,b.position,c.position)) == Approx(1));
		CHECK(std::abs(a.normal.x)+std::abs(a.normal.y)+std::abs(a.normal.z) == Approx(1));
		CHECK(a.texture == b.texture);
		CHECK(a.texture == c.texture);
		unsigned palette = static_cast<unsigned>(a.texture.x*256);
		CHECK(palette >= 1); CHECK(palette <= 6);
		CHECK((static_cast<uint32_t>(a.surface) & SURFACE_UNLIT) != 0);
	}
	grid.Fill({0,0,0},{5,5,5},0);
	grid.Fill({2,0,2},{3,5,3},1);
	mesh = grid.Mesh();
	CHECK(mesh.occupied == 5);
	CHECK(mesh.quads == 6);
	CHECK(VoxelAreaVolume(mesh).second == Approx(1.25));
}

TEST_CASE("Voxel animation observers select actual palette texels without shifting neighbours", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,1,1},{{{239,239,239,239,239,239}},{{240,240,240,240,240,240}},{{245,245,245,245,245,245}},{{254,254,254,254,254,254}}});
	for (int x = 0; x < 4; ++x) grid.Fill({x,0,0},{x+1,1,1},x+1);
	for (bool greedy : {false,true}) {
		auto mesh = grid.Mesh(greedy);
		CHECK(VoxelPaletteMask(mesh.vertices,239,2) == 3);
		CHECK(VoxelPaletteMask(mesh.vertices,245,10) == 513);
		CHECK(VoxelPaletteMask(mesh.vertices,238,3) == 6);
		CHECK(VoxelPaletteMask(mesh.vertices,255,1) == 0);
		for (auto &vertex : mesh.vertices) vertex.surface = SurfaceMode::Opaque;
		CHECK(VoxelPaletteMask(mesh.vertices,239,2) == 0);
	}
	CHECK_THROWS_AS(VoxelPaletteMask({},245,32),std::invalid_argument);
}

TEST_CASE("Voxel material partitions keep their shared occupied boundaries hidden", "[renderer3d][voxel]")
{
	VoxelGrid grid({4,4,2},{{{7,7,7,7,7,7}},{{12,12,12,12,12,12}}});
	grid.Fill({0,0,0},{4,4,1},1);
	grid.Fill({1,0,1},{3,4,2},2);
	auto all = grid.Mesh(), base = grid.Mesh(true,1,1), rail = grid.Mesh(true,2,2);
	CHECK(base.occupied == 16);
	CHECK(rail.occupied == 8);
	CHECK(base.exposed_faces+rail.exposed_faces == all.exposed_faces);
	CHECK(VoxelAreaVolume(base).first+VoxelAreaVolume(rail).first == Approx(VoxelAreaVolume(all).first));
	CHECK(grid.Mesh(true,3,4).vertices.empty());
}

TEST_CASE("Shared voxel edge cuts keep coloured steps free of raster T-junctions", "[renderer3d][voxel]")
{
	VoxelGrid grid({12,10,8},{{{7,7,7,7,7,7}},{{12,12,12,12,12,12}}});
	grid.Fill({0,0,0},{12,10,4},1);
	grid.Fill({2,1,4},{10,9,6},1);
	grid.Fill({4,2,6},{8,8,8},2);
	grid.Fill({6,0,0},{9,10,4},2);
	auto mesh = grid.Mesh();
	std::set<std::array<float,3>> points;
	for (const auto &vertex : mesh.vertices) points.insert({vertex.position.x,vertex.position.y,vertex.position.z});
	for (size_t first = 0; first < mesh.vertices.size(); first += 3) for (unsigned edge = 0; edge < 3; ++edge) {
		Vec3 a = mesh.vertices[first+edge].position, b = mesh.vertices[first+(edge+1)%3].position;
		Vec3 along = b-a;
		bool split = false;
		for (const auto &point : points) {
			Vec3 offset = Vec3{point[0],point[1],point[2]}-a;
			float t = Dot(offset,along)/Dot(along,along);
			Vec3 distance = offset-along*t;
			split |= t > 0.00001f && t < 0.99999f && Dot(distance,distance) < 1e-10f;
		}
		CHECK_FALSE(split);
	}
	CHECK(VoxelAreaVolume(mesh).first == Approx(VoxelAreaVolume(grid.Mesh(false)).first));
	CHECK(VoxelAreaVolume(mesh).second == Approx(mesh.occupied*0.25));
}

TEST_CASE("Voxel input bounds prevent malformed grids and silent clipped authoring", "[renderer3d][voxel]")
{
	std::vector<VoxelMaterial> materials{{{1,1,1,1,1,1}}};
	CHECK_THROWS(VoxelGrid({0,3,3},materials));
	CHECK_THROWS(VoxelGrid({1024,1024,1024},materials));
	CHECK_THROWS(VoxelGrid({2,2,2},materials,{}, {1,0,1}));
	VoxelGrid grid({3,3,3},materials);
	CHECK_THROWS(grid.Fill({-1,0,0},{1,1,1},1));
	CHECK_THROWS(grid.Fill({0,0,0},{4,1,1},1));
	CHECK_THROWS(grid.Fill({0,0,0},{1,1,1},2));
	CHECK(grid.Mesh().vertices.empty());
}

TEST_CASE("Greedy voxel rectangles cover exactly the authored exterior material cells", "[renderer3d][voxel]")
{
	std::vector<VoxelMaterial> materials{{{1,2,3,4,5,6}},{{7,8,9,10,11,12}}};
	VoxelGrid grid({9,7,11},materials);
	for (int z = 0; z < 11; ++z) for (int y = 0; y < 7; ++y) for (int x = 0; x < 9; ++x) {
		if ((x*7+y*3+z*5)%11 < 8) grid.Fill({x,y,z},{x+1,y+1,z+1},1+(x+y)%2);
	}
	using Key = std::array<int,5>; // Axis, sign, grid plane, u, v.
	std::map<Key,unsigned> expected, actual;
	for (int z = 0; z < 11; ++z) for (int y = 0; y < 7; ++y) for (int x = 0; x < 9; ++x) {
		unsigned material = grid.Get(x,y,z);
		if (material == 0) continue;
		for (unsigned axis = 0; axis < 3; ++axis) for (unsigned positive = 0; positive < 2; ++positive) {
			std::array<int,3> p{x,y,z}, next = p; next[axis] += positive ? 1 : -1;
			if (grid.Get(next[0],next[1],next[2]) == 0) expected[{static_cast<int>(axis),static_cast<int>(positive),p[axis]+static_cast<int>(positive),p[(axis+1)%3],p[(axis+2)%3]}] = materials[material-1].colours[axis*2+positive];
		}
	}
	auto mesh = grid.Mesh();
	for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
		Vec3 n = mesh.vertices[i].normal;
		unsigned axis = n.x != 0 ? 0 : n.y != 0 ? 1 : 2, u = (axis+1)%3, v = (axis+2)%3;
		bool positive = n.x+n.y+n.z > 0;
		std::array<float,3> low{100,100,100}, high{-100,-100,-100};
		std::array<std::array<float,3>,3> triangle;
		for (size_t j = i; j < i+3; ++j) {
			Vec3 p = mesh.vertices[j].position;
			std::array<float,3> cell{p.x*2,p.y*2,p.z};
			triangle[j-i] = cell;
			for (unsigned d = 0; d < 3; ++d) { low[d] = std::min(low[d],cell[d]); high[d] = std::max(high[d],cell[d]); }
		}
		unsigned colour = static_cast<unsigned>(mesh.vertices[i].texture.x*256);
		for (int a = static_cast<int>(std::floor(low[u])); a < high[u]; ++a) for (int b = static_cast<int>(std::floor(low[v])); b < high[v]; ++b) {
			auto side = [&](unsigned first, unsigned second) {
				const auto &p = triangle[first], &q = triangle[second];
				return (q[u]-p[u])*(b+0.5f-p[v])-(q[v]-p[v])*(a+0.5f-p[u]);
			};
			float ab = side(0,1), bc = side(1,2), ca = side(2,0);
			if (!((ab >= -0.00001f && bc >= -0.00001f && ca >= -0.00001f) || (ab <= 0.00001f && bc <= 0.00001f && ca <= 0.00001f))) continue;
			auto [found,inserted] = actual.emplace(Key{static_cast<int>(axis),positive,static_cast<int>(std::lround(low[axis])),a,b},colour);
			CHECK(found->second == colour);
		}
	}
	CHECK(actual == expected);
	CHECK(VoxelAreaVolume(mesh).second == Approx(mesh.occupied*0.25));
}
