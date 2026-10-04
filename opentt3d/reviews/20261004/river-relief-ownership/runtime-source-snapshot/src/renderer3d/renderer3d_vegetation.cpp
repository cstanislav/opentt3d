/* SPDX-License-Identifier: GPL-2.0-only */
/** @file renderer3d_vegetation.cpp Closed vegetation volumes and authored branch junctions. */
#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "tree_geometry.hpp"
#include "clear_surface_geometry.hpp"
#include "world_capture.h"
#include "../slope_func.h"
#include <map>

using namespace Renderer3D;

/** Every geometric edge must occur twice, with opposite directions. */
static void CheckClosedTreeMesh(const Scene &mesh)
{
	using Point = std::array<int64_t,3>;
	std::map<std::pair<Point,Point>,std::pair<unsigned,int>> edges;
	auto point = [](Vec3 p) { return Point{std::llround(p.x*100000),std::llround(p.y*100000),std::llround(p.z*100000)}; };
	auto cross = [](Vec3 a, Vec3 b) { return Vec3{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; };
	REQUIRE_FALSE(mesh.vertices.empty());
	bool valid = true;
	double volume = 0;
	for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
		Vec3 a = mesh.vertices[i].position, b = mesh.vertices[i+1].position, c = mesh.vertices[i+2].position;
		Vec3 area = cross(b-a,c-a);
		valid &= std::isfinite(Dot(area,area)) && Dot(area,area) > 1e-12f;
		volume += Dot(a,cross(b,c))/6.0;
		for (unsigned edge = 0; edge < 3; ++edge) {
			Point p = point(mesh.vertices[i+edge].position), q = point(mesh.vertices[i+(edge+1)%3].position);
			int direction = p < q ? 1 : -1;
			if (q < p) std::swap(p,q);
			auto &count = edges[{p,q}];
			++count.first; count.second += direction;
		}
	}
	CHECK(valid);
	CHECK(volume > 0);
	CHECK(std::ranges::all_of(edges, [](const auto &edge) { return edge.second.first == 2 && edge.second.second == 0; }));
}

TEST_CASE("Tapered branches remain closed across bends and detail transitions", "[renderer3d]")
{
	const TreeBranchPoint branch[] = {{{0,0,0},0.7f},{{0.4f,-0.2f,9},0.45f},{{-0.6f,0.8f,19},0.2f},{{1.2f,0.4f,30},0.03f}};
	const TreeBranchPoint root[] = {{{0,0,2},0.3f},{{1,0.4f,0.6f},0.15f},{{2,0.7f,-0.2f},0.025f}};
	const TreeBranchPoint arm[] = {{{0,0,8},0.6f},{{2,0,8},0.5f},{{3,0,10},0.4f},{{3,0,16},0.3f}};
	for (unsigned lod = 0; lod < 3; ++lod) for (auto points : {std::span<const TreeBranchPoint>{branch},std::span<const TreeBranchPoint>{root},std::span<const TreeBranchPoint>{arm}}) {
		Scene mesh;
		TreeBranch(mesh,points,lod);
		CheckClosedTreeMesh(mesh);
	}
}

TEST_CASE("Tree crowns and drooping boughs keep closed finite volumes at every LOD", "[renderer3d]")
{
	for (bool bough : {false,true}) for (float seed : {0.4f,1.2f,2.7f,4.3f,5.6f}) {
		size_t previous = SIZE_MAX;
		for (unsigned lod = 0; lod < 3; ++lod) {
			Scene mesh;
			if (bough) TreeBough(mesh,{1,-2,7},{4,3,12},seed,lod);
			else TreeCrown(mesh,{1,-2,7},{4,3,12},seed,lod);
			CheckClosedTreeMesh(mesh);
			CHECK(mesh.vertices.size() < previous);
			previous = mesh.vertices.size();
		}
	}
}

TEST_CASE("Invalid branch controls cannot enter immutable mesh caches", "[renderer3d]")
{
	Scene mesh;
	const TreeBranchPoint coincident[] = {{{0,0,0},0.5f},{{0,0,0},0.2f}};
	const TreeBranchPoint reversed[] = {{{0,0,0},0.5f},{{0,0,10},0.3f},{{0,0,0},0.1f}};
	const TreeBranchPoint radius[] = {{{0,0,0},0.5f},{{0,0,10},0}};
	CHECK_THROWS_AS(TreeBranch(mesh,coincident,0),std::runtime_error);
	CHECK_THROWS_AS(TreeBranch(mesh,reversed,0),std::runtime_error);
	CHECK_THROWS_AS(TreeBranch(mesh,radius,0),std::runtime_error);
	CHECK(mesh.vertices.empty());
}

TEST_CASE("Palm leaflets and succulent blades have closed raised surfaces", "[renderer3d]")
{
	for (unsigned lod = 0; lod < 3; ++lod) for (Vec3 tip : {Vec3{7,2,24},Vec3{-3,6,0},Vec3{1,-5,10}}) {
		Scene leaf;
		TreeLeaf(leaf,{0,0,5},tip,1.2f,2.5f,0.25f,lod);
		CheckClosedTreeMesh(leaf);
	}
	Scene near_scene, far_scene;
	TreePalmFrond(near_scene,{0,0,32},{8,1,26},2,0);
	TreePalmFrond(far_scene,{0,0,32},{8,1,26},2,2);
	CHECK(near_scene.vertices.size() > far_scene.vertices.size());
	CheckClosedTreeMesh(near_scene);
	CheckClosedTreeMesh(far_scene);
}

TEST_CASE("Toyland turned crowns and individual gores are closed volumes", "[renderer3d]")
{
	const std::vector<Vec3> profiles[] = {{{4,0,0},{28,7,7}},{{20,8,8},{25,0,0}},{{9,6,5},{12,5,4},{15,0,0}},{{6,4,4},{23,4,4}}};
	for (const auto &profile : profiles) for (unsigned lod = 0; lod < 3; ++lod) for (float arc : {45.0f,360.0f}) {
		Scene mesh;
		TreeSector(mesh,{1,-2,0},profile,15,15+arc,24,lod);
		CheckClosedTreeMesh(mesh);
	}
}

TEST_CASE("Turf blades, pebbles and rough-ground volumes follow every legal terrain slope", "[renderer3d]")
{
	for (unsigned climate = 0; climate < 4; ++climate) for (bool rough : {false,true}) for (unsigned variant = 0; variant < (rough ? 5U : 4U); ++variant) {
		for (unsigned slope = 0; slope < 32; ++slope) {
			if (slope >= 15 && slope != 23 && slope != 27 && slope != 29 && slope != 30) continue;
			auto surface = MakeTileSurface(static_cast<Slope>(slope));
			for (unsigned lod = 0; lod < 3; ++lod) {
				auto assembly = MakeClearSurfaceAssembly(rough,variant,climate,surface,lod);
				bool finite = true, supported = true, contained = true;
				for (const auto &part : assembly.parts) for (const auto &v : part) {
					finite &= std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z);
					supported &= v.position.z >= surface.Height(v.position.x,v.position.y)-0.0001f;
					contained &= v.position.x >= 0 && v.position.y >= 0 && v.position.x <= 16 && v.position.y <= 16;
				}
				CHECK(finite); CHECK(supported); CHECK(contained);
				CHECK_FALSE(assembly.parts[static_cast<unsigned>(ClearSurfaceMaterial::Ground)].empty());
				if (climate != 3 && (rough || variant != 0) && lod < 2) CHECK_FALSE(assembly.parts[static_cast<unsigned>(ClearSurfaceMaterial::Grass)].empty());
				if (climate == 3 && rough) CHECK_FALSE(assembly.parts[static_cast<unsigned>(ClearSurfaceMaterial::Accent)].empty());
			}
		}
	}
}

TEST_CASE("Natural ground borders preserve map height and voxel-compatible edge samples", "[renderer3d]")
{
	for (unsigned climate = 0; climate < 4; ++climate) for (unsigned slope = 0; slope < 32; ++slope) {
		if (slope >= 15 && slope != 23 && slope != 27 && slope != 29 && slope != 30) continue;
		auto surface = MakeTileSurface(static_cast<Slope>(slope));
		auto mesh = MakeClearSurfaceAssembly(false,3,climate,surface,0);
		const auto &ground = mesh.parts[static_cast<unsigned>(ClearSurfaceMaterial::Ground)];
		for (unsigned edge = 0; edge < 4; ++edge) for (unsigned step = 0; step <= 32; ++step) {
			float p = step*0.5f;
			Vec3 point = edge == 0 ? Vec3{p,0,0} : edge == 1 ? Vec3{16,p,0} : edge == 2 ? Vec3{p,16,0} : Vec3{0,p,0};
			point.z = surface.Height(point.x,point.y);
			REQUIRE(std::ranges::any_of(ground,[&](const Vertex &vertex) { return vertex.position == point; }));
		}
	}
	for (unsigned climate = 0; climate < 4; ++climate) {
		auto coarse = MakeClearSurfaceAssembly(false,3,climate,{},0,0);
		auto contact = MakeClearSurfaceAssembly(false,3,climate,{},0,1);
		auto fine = MakeClearSurfaceAssembly(false,3,climate,{},0,15);
		const auto index = static_cast<unsigned>(ClearSurfaceMaterial::Ground);
		CHECK(coarse.parts[index].size() < contact.parts[index].size());
		CHECK(contact.parts[index].size() < fine.parts[index].size());
		for (unsigned sample = 0; sample <= 32; ++sample) {
			Vec3 p{sample*0.5f,0,0};
			CHECK(std::ranges::any_of(contact.parts[index],[&](const Vertex &vertex) { return vertex.position == p; }));
		}
	}
}

TEST_CASE("Middle-distance crop rows preserve growth height without unresolved stems", "[renderer3d]")
{
	for (unsigned stage = 3; stage <= 6; ++stage) {
		auto close = MakeFieldAssembly(stage,MakeTileSurface(SLOPE_FLAT),0);
		auto middle = MakeFieldAssembly(stage,MakeTileSurface(SLOPE_FLAT),1);
		const auto &full = close.parts[static_cast<unsigned>(GroundDetailMaterial::Crop)];
		const auto &coarse = middle.parts[static_cast<unsigned>(GroundDetailMaterial::Crop)];
		auto height = [](const auto &vertices) {
			float top = 0;
			for (const auto &v : vertices) top = std::max(top,v.position.z);
			return top;
		};
		CHECK(coarse.size()*5 < full.size());
		CHECK(std::abs(height(full)-height(coarse)) < 0.25f);
	}
}
