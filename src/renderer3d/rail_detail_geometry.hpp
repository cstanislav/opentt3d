/* SPDX-License-Identifier: GPL-2.0-only */
/** @file rail_detail_geometry.hpp Authored signal mechanisms and overhead line equipment. */
#ifndef RENDERER3D_RAIL_DETAIL_GEOMETRY_HPP
#define RENDERER3D_RAIL_DETAIL_GEOMETRY_HPP

#include "rail_geometry.hpp"
#include "camera.hpp"

namespace Renderer3D {

/** Sprite offsets are not Direction order. These faces follow the upstream
 * trackdir/signal-bit table (not the inconsistent historical sprite labels). */
inline float SignalHeading(unsigned sprite_direction)
{
	constexpr unsigned faces[] = {5,1,7,3,6,2,4,0};
	return (5-static_cast<int>(faces[sprite_direction]))*std::numbers::pi_v<float>/4;
}

inline void SignalLens(Scene &scene, float y, float z, Rgb colour, float radius = 0.21f)
{
	const Rgb hood{0.09f,0.10f,0.10f};
	for (unsigned segment = 0; segment < 12; ++segment) {
		float a = 2*std::numbers::pi_v<float>*segment/12, b = 2*std::numbers::pi_v<float>*(segment+1)/12;
		Vec3 p{0.56f,y+radius*std::cos(a),z+radius*std::sin(a)/Camera::WORLD_Z_SCALE};
		Vec3 q{0.56f,y+radius*std::cos(b),z+radius*std::sin(b)/Camera::WORLD_Z_SCALE};
		scene.Triangle({0.56f,y,z},p,q,colour);
		scene.Quad({0.30f,p.y,p.z},{0.30f,q.y,q.z},q,p,hood);
	}
}

/** Rounded die-cast housing, with a real back and side wall rather than a card. */
inline void SignalHousing(Scene &scene, float bottom, float top, Rgb colour)
{
	std::array<Vec3,14> outline;
	for (unsigned cap = 0; cap < 2; ++cap) for (unsigned i = 0; i <= 6; ++i) {
		float angle = std::numbers::pi_v<float>*(cap+i/6.0f);
		float centre = cap == 0 ? top-0.4f/Camera::WORLD_Z_SCALE : bottom+0.4f/Camera::WORLD_Z_SCALE;
		outline[cap*7+i] = {0.3f,0.4f*std::cos(angle),centre+0.4f*std::sin(angle)/Camera::WORLD_Z_SCALE};
	}
	for (unsigned i = 0; i < outline.size(); ++i) {
		Vec3 a = outline[i], b = outline[(i+1)%outline.size()], back{-0.45f,0,0};
		scene.Triangle({0.3f,0,(bottom+top)/2},a,b,colour);
		scene.Triangle({-0.15f,0,(bottom+top)/2},b+back,a+back,colour);
		scene.Quad(a,a+back,b+back,b,colour);
	}
}

inline std::vector<Vertex> MakeSignalMesh(unsigned type, bool semaphore, bool green, bool detail = true)
{
	Scene scene;
	const Rgb metal{0.60f,0.62f,0.61f}, dark{0.07f,0.08f,0.08f};
	GeometryBox(scene,{-0.28f,-0.28f,0},{0.28f,0.28f,0.40f},{0.52f,0.53f,0.50f});
	if (semaphore && detail) {
		for (float x : {-0.15f,0.15f}) for (float y : {-0.15f,0.15f}) GeometryBeam(scene,{x,y,0.3f},{x,y,12.6f},0.04f,metal);
		for (float z = 0.6f; z < 12; z += 1.2f) {
			for (float x : {-0.15f,0.15f}) GeometryBeam(scene,{x,-0.15f,z},{x,0.15f,z+1.0f},0.022f,metal);
			for (float y : {-0.15f,0.15f}) GeometryBeam(scene,{-0.15f,y,z},{0.15f,y,z+1.0f},0.022f,metal);
		}
	} else GeometryBox(scene,{-0.10f,-0.10f,0.3f},{0.10f,0.10f,semaphore ? 12.6f : 9.2f},metal);
	if (semaphore) {
		GeometryBox(scene,{-0.10f,-0.35f,9.1f},{0.30f,0.35f,10.5f},dark);
		SignalLens(scene,0,9.8f,green ? Rgb{0.04f,1.15f,0.03f} : Rgb{1.15f,0.025f,0.015f},0.21f);
		size_t first = scene.vertices.size();
		GeometryBox(scene,{0.10f,-0.35f,10.72f},{0.37f,2.55f,11.28f},metal);
		GeometryBox(scene,{0.37f,-0.35f,10.72f},{0.43f,2.55f,11.28f},{0.92f,0.05f,0.025f});
		GeometryBox(scene,{0.43f,-0.25f,10.95f},{0.45f,2.48f,11.06f},{0.93f,0.92f,0.84f});
		for (unsigned i = 0; i < 12; ++i) {
			float a = 2*std::numbers::pi_v<float>*i/12, b = 2*std::numbers::pi_v<float>*(i+1)/12;
			Vec3 p{0.47f,2.36f+0.19f*std::cos(a),11+0.19f*std::sin(a)/Camera::WORLD_Z_SCALE};
			Vec3 q{0.47f,2.36f+0.19f*std::cos(b),11+0.19f*std::sin(b)/Camera::WORLD_Z_SCALE};
			scene.Triangle({0.47f,2.36f,11},p,q,{0.94f,0.91f,0.81f});
			scene.Quad(p,q,q+Vec3{-0.12f,0,0},p+Vec3{-0.12f,0,0},{0.92f,0.05f,0.025f});
			scene.Triangle({0.35f,2.36f,11},q+Vec3{-0.12f,0,0},p+Vec3{-0.12f,0,0},metal);
		}
		if (green) for (size_t i = first; i < scene.vertices.size(); ++i) {
			/* A 45-degree physical swing, accounting for OpenTTD's height units. */
			Vec3 &p = scene.vertices[i].position;
			float y = p.y, z = (p.z-11)*Camera::WORLD_Z_SCALE;
			p.y = (y-z)*0.707106781186548f;
			p.z = 11+(y+z)*0.707106781186548f/Camera::WORLD_Z_SCALE;
		}
	} else {
		SignalHousing(scene,type == 0 ? 9.3f : 8.8f,12.5f,dark);
		if (type == 0) {
			SignalLens(scene,0,11.45f,green ? Rgb{0.04f,1.15f,0.03f} : Rgb{0.01f,0.055f,0.01f});
			SignalLens(scene,0,10.15f,green ? Rgb{0.065f,0.005f,0.005f} : Rgb{1.15f,0.025f,0.015f});
		} else {
			SignalLens(scene,0,11.8f,green ? Rgb{0.04f,1.15f,0.03f} : Rgb{0.01f,0.055f,0.01f});
			SignalLens(scene,0,10.65f,green ? Rgb{0.065f,0.005f,0.005f} : Rgb{1.15f,0.025f,0.015f});
			SignalLens(scene,0,9.5f,type >= 4 ? (green ? Rgb{0.065f,0.005f,0.005f} : Rgb{1.15f,0.025f,0.015f}) :
				(green ? Rgb{0.04f,1.15f,0.03f} : Rgb{1.15f,0.025f,0.015f}));
		}
		if (type >= 4) GeometryBeam(scene,{-0.18f,-0.35f,9.4f},{-0.18f,0.35f,11.6f},0.07f,{0.61f,0.62f,0.60f});
	}
	if (semaphore && type >= 4) GeometryBox(scene,{0.3f,-0.16f,8.45f},{0.34f,0.16f,8.95f},{1.0f,0.86f,0.04f});
	if (type >= 1 && type <= 3) {
		bool horizontal = type == 1;
		float half = horizontal ? 0.65f : 0.19f, height = horizontal ? 0.65f : 2.2f;
		float inset = horizontal ? 0.10f : 0.06f;
		GeometryBox(scene,{-0.12f,-half,6.5f},{0.18f,half,6.5f+height},dark);
		GeometryBox(scene,{0.18f,inset-half,6.6f},{0.20f,half-inset,6.4f+height},type == 2 ? Rgb{0.92f,0.92f,0.88f} : Rgb{1.0f,0.86f,0.04f});
	} else if (type == 5) {
		GeometryBox(scene,{-0.13f,-0.65f,6.5f},{0.18f,0.65f,7.2f},{0.95f,0.94f,0.90f});
		GeometryBox(scene,{0.18f,-0.53f,6.61f},{0.21f,0.53f,7.09f},{0.92f,0.03f,0.025f});
	}
	for (size_t i = 0; i < scene.vertices.size(); i += 3) {
		Vec3 normal = Normal(scene.vertices[i].position,scene.vertices[i+1].position,scene.vertices[i+2].position);
		for (size_t j = i; j < i+3; ++j) scene.vertices[j].normal = normal;
	}
	return scene.vertices;
}

inline float CatenaryRise(float t, unsigned supports)
{
	float phase = supports == 1 ? t*0.5f : supports == 2 ? 0.5f+t*0.5f : t;
	return 2.0f-0.9f*4*phase*(1-phase);
}

inline std::vector<Vertex> MakeCatenaryWire(unsigned track, float grade, unsigned supports, unsigned half = 0, bool detail = true)
{
	Scene scene;
	float begin = half == 2 ? 0.5f : 0, end = half == 1 ? 0.5f : 1;
	auto point = [&](float t, bool messenger) {
		Vec3 p = RailPath(track,t).point;
		p.z = grade*t+10+(messenger ? CatenaryRise(t,supports) : 0);
		return p;
	};
	unsigned steps = detail ? 12 : 4;
	for (unsigned i = 0; i < steps; ++i) {
		float a = std::lerp(begin,end,static_cast<float>(i)/steps), b = std::lerp(begin,end,static_cast<float>(i+1)/steps);
		GeometryBeam(scene,point(a,false),point(b,false),0.035f,{0.62f,0.63f,0.60f});
		GeometryBeam(scene,point(a,true),point(b,true),0.026f,{0.52f,0.54f,0.51f});
		if (detail && i%3 == 0) GeometryBeam(scene,point(a,false),point(a,true),0.022f,{0.52f,0.54f,0.51f});
	}
	return scene.vertices;
}

inline std::vector<Vertex> MakeCatenaryPylon(Vec3 contact)
{
	Scene scene;
	const Rgb metal{0.58f,0.61f,0.59f};
	GeometryBox(scene,{-0.22f,-0.22f,0},{0.22f,0.22f,0.45f},{0.53f,0.54f,0.51f});
	GeometryBox(scene,{-0.075f,-0.075f,0.4f},{0.075f,0.075f,contact.z+2.2f},metal);
	GeometryBeam(scene,{0,0,contact.z+2},{contact.x,contact.y,contact.z+2},0.055f,metal);
	GeometryBeam(scene,{0,0,contact.z-2.5f},{contact.x,contact.y,contact.z+0.2f},0.05f,metal);
	GeometryBeam(scene,contact,contact+Vec3{0,0,2},0.033f,metal);
	for (float z : {0.45f,0.8f,1.15f}) GeometryBox(scene,contact+Vec3{-0.12f,-0.12f,z},contact+Vec3{0.12f,0.12f,z+0.17f},{0.49f,0.12f,0.095f});
	return scene.vertices;
}

} // namespace Renderer3D
#endif
