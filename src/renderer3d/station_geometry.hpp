/* SPDX-License-Identifier: GPL-2.0-only */
/** @file station_geometry.hpp Authored vanilla station platforms, buildings and paired halls. */
#ifndef RENDERER3D_STATION_GEOMETRY_HPP
#define RENDERER3D_STATION_GEOMETRY_HPP

#include "terrain_geometry.hpp"
#include <numbers>

namespace Renderer3D {

enum class StationMaterial : unsigned { Platform, Brick, Roof, Metal, Company, Glass, Detail, Catenary, Count };
struct StationAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(StationMaterial::Count)> parts;
};

/** Source rectangles selected from station-0-0-1 and station-0-2-1.
 * They contain only pavement, brick, roof or sign paint, never other components. */
inline Vec3 StationMaterialUV(StationMaterial material, float u, float v)
{
	switch (material) {
		case StationMaterial::Platform: return {(120+8*u)/168,(12+8*v)/93,-3};
		case StationMaterial::Brick: return {(38+8*u)/168,(82+8*v)/122,-3};
		case StationMaterial::Roof: return {(110+8*u)/168,(17+8*v)/122,-3};
		case StationMaterial::Company: return {63.5f/168,22.5f/93,-3};
		default: return {-1,-1,-1};
	}
}

inline float StationRoofHeight(unsigned kind, float x, float y)
{
	float t = std::clamp(y/16,0.0f,1.0f);
	if (kind <= 1) return 16+8*std::sqrt(std::max(0.0f,1-(1-t)*(1-t)));
	if (kind == 2) return 24-8*std::sqrt(std::max(0.0f,1-(1-t)*(1-t)));
	return 16+8*(1-t)*(1-t)+2*std::sin(std::numbers::pi_v<float>*x/16)*t;
}

inline StationAssembly MakeStationAssembly(unsigned kind, unsigned layout)
{
	std::array<Scene,static_cast<unsigned>(StationMaterial::Count)> parts;
	auto mesh = [&](StationMaterial part) -> Scene & { return parts[static_cast<unsigned>(part)]; };
	auto panel = [&](StationMaterial part, Vec3 a, Vec3 b, Vec3 c, Vec3 d, Rgb colour = Rgb{}) {
		auto &surface = mesh(part);
		bool tiled = part == StationMaterial::Platform || part == StationMaterial::Brick || part == StationMaterial::Roof;
		unsigned nx = tiled ? std::max(1U,static_cast<unsigned>(std::ceil(std::sqrt(std::max(Dot(b-a,b-a),Dot(c-d,c-d)))/2))) : 1;
		unsigned ny = tiled ? std::max(1U,static_cast<unsigned>(std::ceil(std::sqrt(std::max(Dot(d-a,d-a),Dot(c-b,c-b)))/2))) : 1;
		auto point = [&](float x, float y) { return (a+(b-a)*x)*(1-y)+(d+(c-d)*x)*y; };
		for (unsigned x = 0; x < nx; ++x) for (unsigned y = 0; y < ny; ++y) {
			float x0 = static_cast<float>(x)/nx, x1 = static_cast<float>(x+1)/nx;
			float y0 = static_cast<float>(y)/ny, y1 = static_cast<float>(y+1)/ny;
			size_t first = surface.vertices.size();
			surface.Quad(point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1),colour);
			const Vec3 uv[] = {StationMaterialUV(part,0,0),StationMaterialUV(part,1,0),StationMaterialUV(part,1,1),
				StationMaterialUV(part,0,0),StationMaterialUV(part,1,1),StationMaterialUV(part,0,1)};
			for (size_t i = 0; i < 6; ++i) surface.vertices[first+i].texture = uv[i];
		}
	};
	auto box = [&](StationMaterial part, Vec3 low, Vec3 high, Rgb colour = Rgb{}) {
		Vec3 p[] = {{low.x,low.y,low.z},{high.x,low.y,low.z},{high.x,high.y,low.z},{low.x,high.y,low.z},
			{low.x,low.y,high.z},{high.x,low.y,high.z},{high.x,high.y,high.z},{low.x,high.y,high.z}};
		const unsigned faces[][4] = {{0,3,2,1},{4,5,6,7},{0,1,5,4},{1,2,6,5},{2,3,7,6},{3,0,4,7}};
		for (auto &face : faces) {
			Vec3 a = p[face[0]], along = p[face[1]]-a, up = p[face[3]]-a;
			unsigned nx = std::max(1U,static_cast<unsigned>(std::ceil(std::sqrt(Dot(along,along))/2)));
			unsigned ny = std::max(1U,static_cast<unsigned>(std::ceil(std::sqrt(Dot(up,up))/2)));
			for (unsigned x = 0; x < nx; ++x) for (unsigned y = 0; y < ny; ++y) {
				Vec3 q = a+along*(static_cast<float>(x)/nx)+up*(static_cast<float>(y)/ny);
				panel(part,q,q+along*(1.0f/nx),q+along*(1.0f/nx)+up*(1.0f/ny),q+up*(1.0f/ny),colour);
			}
		}
	};
	auto solid = [&](StationMaterial part, Vec3 low, Vec3 high, Rgb colour) { GeometryBox(mesh(part),low,high,colour); };
	const Rgb pale{0.79f,0.80f,0.76f}, iron{0.61f,0.65f,0.67f}, gold{0.60f,0.49f,0.27f};
	const unsigned shape = layout/2;
	float platform_width = kind == 3 ? 4 : 5;
	for (bool front : {false,true}) {
		float y = front ? 16-platform_width : 0;
		box(StationMaterial::Platform,{0,y,0},{16,y+platform_width,2});
		float edge = front ? y : y+platform_width-0.20f;
		solid(StationMaterial::Detail,{0,edge,2},{16,edge+0.20f,2.04f},pale);
		for (float x = 4; x < 16; x += 4) solid(StationMaterial::Detail,{x-0.025f,y,2},{x+0.025f,y+platform_width,2.025f},{0.47f,0.48f,0.47f});
		if (!(shape == 1 && !front)) {
			for (float x : {6.0f,10.0f}) GeometryBeam(mesh(StationMaterial::Metal),{x,y+1.4f,2},{x,y+1.4f,5.7f},0.075f,pale);
			box(StationMaterial::Company,{5.8f,y+1.3f,4.6f},{10.2f,y+1.5f,5.7f});
			/* Benches and legs are separate volume components, not platform paint. */
			solid(StationMaterial::Detail,{1.0f,y+2.1f,3.1f},{4.0f,y+2.8f,3.3f},{0.33f,0.22f,0.13f});
			for (float x : {1.3f,3.7f}) solid(StationMaterial::Metal,{x,y+2.2f,2},{x+0.12f,y+2.7f,3.1f},iron);
		}
	}
	auto pitched_roof = [&](float x0, float x1, float y0, float y1, float eave, float ridge) {
		float middle = (y0+y1)*0.5f;
		panel(StationMaterial::Roof,{x0,y0,eave},{x1,y0,eave},{x1,middle,ridge},{x0,middle,ridge});
		panel(StationMaterial::Roof,{x0,middle,ridge},{x1,middle,ridge},{x1,y1,eave},{x0,y1,eave});
		GeometryBeam(mesh(StationMaterial::Detail),{x0,y0,eave},{x1,y0,eave},0.06f,pale);
		GeometryBeam(mesh(StationMaterial::Detail),{x0,y1,eave},{x1,y1,eave},0.06f,pale);
		mesh(StationMaterial::Detail).Triangle({x0,y1,eave},{x0,middle,ridge},{x0,y0,eave},{0.40f,0.29f,0.21f});
		mesh(StationMaterial::Detail).Triangle({x1,y0,eave},{x1,middle,ridge},{x1,y1,eave},{0.40f,0.29f,0.21f});
	};
	if (shape == 1) {
		if (kind <= 1) {
			for (auto wing : {std::array<float,3>{0.6f,5.2f,8.5f},{5.2f,10.8f,11.5f},{10.8f,15.4f,8.5f}}) {
				box(StationMaterial::Brick,{wing[0],0.3f,2},{wing[1],3.8f,wing[2]});
				pitched_roof(wing[0]-0.2f,wing[1]+0.2f,0.1f,4,wing[2],wing[2]+2.1f);
			}
			/* Clock gable, face and hands are independent authored parts. */
			Vec3 ga{6.3f,3.83f,11.4f}, gb{9.7f,3.83f,11.4f}, gc{8,3.83f,14}, back{0,-1.8f,0};
			mesh(StationMaterial::Detail).Triangle(ga,gb,gc,{0.57f,0.24f,0.14f});
			mesh(StationMaterial::Detail).Triangle(ga+back,gc+back,gb+back,{0.57f,0.24f,0.14f});
			panel(StationMaterial::Roof,ga,gc,gc+back,ga+back);
			panel(StationMaterial::Roof,gc,gb,gb+back,gc+back);
			solid(StationMaterial::Detail,{7.4f,3.86f,11.5f},{8.6f,3.91f,12.7f},pale);
			GeometryBeam(mesh(StationMaterial::Detail),{8,3.94f,12.1f},{8,3.94f,12.57f},0.035f,{0.1f,0.1f,0.1f});
			GeometryBeam(mesh(StationMaterial::Detail),{8,3.94f,12.1f},{8.32f,3.94f,12.1f},0.035f,{0.1f,0.1f,0.1f});
		} else if (kind == 2) {
			solid(StationMaterial::Detail,{0.8f,0.3f,2},{15.2f,3.7f,10},gold);
			pitched_roof(0.5f,15.5f,0,4,10,11.6f);
		} else {
			for (float x : {0.8f,7.7f,14.6f}) solid(StationMaterial::Detail,{x,0.5f,2},{x+0.6f,1.1f,10},gold);
			for (unsigned section = 0; section < 8; ++section) {
				float a = std::numbers::pi_v<float>*section/8, b = std::numbers::pi_v<float>*(section+1)/8;
				Vec3 p{0.5f,2-2*std::cos(a),10+2*std::sin(a)}, q{0.5f,2-2*std::cos(b),10+2*std::sin(b)};
				panel(StationMaterial::Glass,p,p+Vec3{15,0,0},q+Vec3{15,0,0},q,{0.30f,0.56f,0.75f});
				for (float x = 0.5f; x <= 15.5f; x += 2.5f) GeometryBeam(mesh(StationMaterial::Metal),p+Vec3{x-0.5f,0,0},q+Vec3{x-0.5f,0,0},0.08f,iron);
			}
		}
		if (kind < 3) {
			for (float x : {2.0f,12.0f}) for (float y : {0.25f,3.82f}) {
				solid(StationMaterial::Metal,{x,y,4.2f},{x+1.8f,y+0.05f,7.2f},pale);
				solid(StationMaterial::Detail,{x+0.12f,y-0.025f,4.35f},{x+1.68f,y+0.075f,7.05f},{0.16f,0.30f,0.45f});
			}
			solid(StationMaterial::Detail,{7.1f,3.81f,2},{8.9f,3.87f,6.8f},{0.20f,0.13f,0.09f});
			box(StationMaterial::Company,{3,3.8f,7.7f},{13,5.3f,8});
			for (float x : {3.2f,12.8f}) GeometryBeam(mesh(StationMaterial::Metal),{x,5.1f,2},{x,5.1f,7.7f},0.08f,pale);
		}
	} else if (shape >= 2) {
		const float outer_height = StationRoofHeight(kind,0,0);
		for (float x : {0.5f,5.5f,10.5f,15.5f}) {
			if (kind <= 1) box(StationMaterial::Brick,{x-0.4f,0.2f,2},{x+0.4f,0.9f,outer_height});
			else solid(StationMaterial::Detail,{x-0.3f,0.2f,2},{x+0.3f,0.8f,outer_height},gold);
		}
		if (kind <= 1) box(StationMaterial::Brick,{0,0.2f,outer_height-2},{16,0.9f,outer_height});
		else solid(StationMaterial::Detail,{0,0.2f,outer_height-0.7f},{16,0.8f,outer_height},gold);
		if (kind <= 1) for (float centre : {3.0f,8.0f,13.0f}) for (unsigned segment = 0; segment < 8; ++segment) {
			float a = std::numbers::pi_v<float>*segment/8, b = std::numbers::pi_v<float>*(segment+1)/8;
			Vec3 p{centre+2.1f*std::cos(a),0.2f,8+3.5f*std::sin(a)};
			Vec3 q{centre+2.1f*std::cos(b),0.2f,8+3.5f*std::sin(b)};
			Vec3 r{q.x,0.2f,outer_height-2}, s{p.x,0.2f,outer_height-2}, thickness{0,0.7f,0};
			panel(StationMaterial::Brick,p,s,r,q);
			panel(StationMaterial::Brick,p+thickness,q+thickness,r+thickness,s+thickness);
			panel(StationMaterial::Brick,p,q,q+thickness,p+thickness);
		}
		/* A and B are mirrored half-halls. Their seam heights agree over the
		 * adjoining platforms, following the original paired tile layout. */
		for (unsigned row = 0; row < 12; ++row) {
			float a = 16*(1-std::cos(std::numbers::pi_v<float>*row/24));
			float b = 16*(1-std::cos(std::numbers::pi_v<float>*(row+1)/24));
			for (float x = 0; x < 16; x += 4) {
				Vec3 p{x,a,StationRoofHeight(kind,x,a)}, q{x+4,a,StationRoofHeight(kind,x+4,a)};
				Vec3 r{x+4,b,StationRoofHeight(kind,x+4,b)}, s{x,b,StationRoofHeight(kind,x,b)};
				panel(StationMaterial::Glass,p,q,r,s,kind <= 1 ? Rgb{0.30f,0.60f,0.79f} : Rgb{0.90f,0.89f,0.52f});
				GeometryBeam(mesh(StationMaterial::Metal),p,s,0.07f,iron);
				if (x == 12) GeometryBeam(mesh(StationMaterial::Metal),q,r,0.07f,iron);
				if (row%3 == 0) GeometryBeam(mesh(StationMaterial::Metal),p,q,0.055f,iron);
			}
		}
		/* Upstream retains wires but omits outdoor pylons under the hall.
		 * Real roof hangers support those same contact wires in close-up views. */
		if (kind == 1) for (float x : {4.0f,12.0f}) {
			float roof = StationRoofHeight(kind,x,8);
			GeometryBeam(mesh(StationMaterial::Catenary),{x,8,10},{x,8,roof},0.033f,iron);
			for (float z = roof-2.2f; z < roof-1; z += 0.4f) {
				solid(StationMaterial::Catenary,{x-0.13f,7.87f,z},{x+0.13f,8.13f,z+0.17f},{0.49f,0.12f,0.095f});
			}
		}
	}
	StationAssembly result;
	for (size_t part = 0; part < parts.size(); ++part) {
		auto &vertices = parts[part].vertices;
		bool mirror = shape == 3, transpose = layout%2 != 0;
		for (auto &v : vertices) {
			if (mirror) v.position.y = 16-v.position.y;
			if (transpose) std::swap(v.position.x,v.position.y);
		}
		for (size_t i = 0; i < vertices.size(); i += 3) {
			if (mirror != transpose) std::swap(vertices[i+1],vertices[i+2]);
			Vec3 n = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
			for (size_t j = i; j < i+3; ++j) vertices[j].normal = n;
		}
		result.parts[part] = std::move(vertices);
	}
	return result;
}

} // namespace Renderer3D
#endif
