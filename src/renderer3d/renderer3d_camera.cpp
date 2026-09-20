/* SPDX-License-Identifier: GPL-2.0-only */
/** @file renderer3d_camera.cpp Projection agreement and rotation/picking invariants. */

#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "camera.hpp"
#include "../landscape.h"

using namespace Renderer3D;
using Catch::Detail::Approx;

TEST_CASE("OpenTT3D default camera agrees with upstream world projection", "[renderer3d]")
{
	Camera camera{{512, 256, 0}, static_cast<float>(ZOOM_BASE), 1280, 800, 0};
	Point center = RemapCoords(512, 256, 0);
	for (int x : {0, 64, 511, 1024, 8191}) {
		for (int y : {0, 128, 255, 512}) {
			for (int z : {0, 8, 16, 120, 255}) {
				auto actual = camera.Project({static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)});
				Point expected = RemapCoords(x, y, z);
				CHECK(actual.x == expected.x - center.x + 640);
				CHECK(actual.y == expected.y - center.y + 400);
			}
		}
	}
}

TEST_CASE("OpenTT3D projection unprojects at every rotation and zoom", "[renderer3d]")
{
	for (unsigned rotation = 0; rotation < 4; ++rotation) {
		for (float scale : {0.125f, 0.5f, 1.0f, 2.0f, 4.0f}) {
			Camera camera{{211.25f, 304.5f, 24}, scale, 1279, 799, rotation};
			for (Vec3 p : {Vec3{0, 0, 0}, Vec3{145, 192, 8}, Vec3{1024.5f, 4096.25f, 255}}) {
				auto screen = camera.Project(p);
				auto actual = camera.Unproject(screen.x, screen.y, p.z);
				CHECK(actual.x == Approx(p.x));
				CHECK(actual.y == Approx(p.y));
				CHECK(actual.z == Approx(p.z));
			}
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
