/* SPDX-License-Identifier: GPL-2.0-only */
/** @file tunnel_geometry.hpp Authored portals, excavated approaches and continuous tunnel sections.
 * References: OpenGFX2 High Def 0.8.1 tunnel/track sheets. Dimensions and topology
 * are explicit construction geometry, not derived from images. Local +X enters the hill. */
#ifndef RENDERER3D_TUNNEL_GEOMETRY_HPP
#define RENDERER3D_TUNNEL_GEOMETRY_HPP

#include "terrain_geometry.hpp"
#include <numbers>

namespace Renderer3D {

enum class TunnelKind : unsigned { Rail, ElectricRail, Monorail, Maglev, Road, Tram };
enum class TunnelMaterial : unsigned { Earth, Floor, Structure, Lining, Detail, Light, Wire, Count };
struct TunnelAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(TunnelMaterial::Count)> parts;
};

/** Clear the inward lining ribs and reach the low wire before the 7.5-unit arch
 * mouth, including the finite length of the collector's contact shoe. */
inline float TunnelContactWireHeight(float local_x)
{
	return std::lerp(10.0f,7.55f,std::clamp(local_x/6.5f,0.0f,1.0f));
}

inline float TunnelPairContactWireHeight(float local_x, float length)
{
	return TunnelContactWireHeight(std::min(local_x,length+16-local_x));
}

inline Vec3 TunnelPoint(unsigned direction, Vec3 point)
{
	switch (direction) {
		case 0: return {16-point.x,16-point.y,point.z}; // NE, into -X.
		case 1: return {16-point.y,point.x,point.z};    // SE, into +Y.
		case 2: return point;                        // SW, into +X.
		default: return {point.y,16-point.x,point.z}; // NW, into -Y.
	}
}

/** Lining cross-section is deliberately below one eight-unit terrain level. */
inline std::vector<Vec3> TunnelProfile(TunnelKind kind, float x)
{
	if (kind == TunnelKind::Road || kind == TunnelKind::Tram) {
		return {{x,2.5f,0},{x,2.5f,6.8f},{x,3.3f,7.6f},{x,12.7f,7.6f},{x,13.5f,6.8f},{x,13.5f,0}};
	}
	std::vector<Vec3> result{{x,3,0},{x,3,5.1f}};
	for (unsigned i = 1; i <= 16; ++i) {
		float angle = std::numbers::pi_v<float>*i/16;
		result.push_back({x,8-5*std::cos(angle),5.1f+2.6f*std::sin(angle)});
	}
	result.push_back({x,13,0});
	return result;
}

inline float TunnelRoofHeight(TunnelKind kind, float y)
{
	static const auto rail = TunnelProfile(TunnelKind::Rail,0), road = TunnelProfile(TunnelKind::Road,0);
	const auto &profile = kind == TunnelKind::Road || kind == TunnelKind::Tram ? road : rail;
	for (size_t i = 1; i+1 < profile.size(); ++i) {
		Vec3 a = profile[i], b = profile[i+1];
		if (b.y > a.y && y >= a.y && y <= b.y) return std::lerp(a.z,b.z,(y-a.y)/(b.y-a.y));
	}
	return -INFINITY;
}

inline bool VisibleThroughTunnelMouth(TunnelKind kind, float length, Vec3 eye, Vec3 target)
{
	if (eye.x < 8 || eye.x > length+8) return true;
	if (target.x >= 8 && target.x <= length+8) return false;
	float mouth = target.x < 8 ? 8 : length+8;
	Vec3 crossing = eye+(target-eye)*((mouth-eye.x)/(target.x-eye.x));
	const auto profile = TunnelProfile(kind,mouth);
	if (crossing.y <= profile.front().y || crossing.y >= profile.back().y || crossing.z < 0) return false;
	for (size_t i = 1; i+1 < profile.size(); ++i) {
		Vec3 a = profile[i], b = profile[i+1];
		if (b.y <= a.y || crossing.y < a.y || crossing.y > b.y) continue;
		return crossing.z < std::lerp(a.z,b.z,(crossing.y-a.y)/(b.y-a.y));
	}
	return false;
}

/** Conservative scenery visibility from inside an original opaque tunnel.
 * Keep the whole bore and two infinite cones through enlarged mouth rectangles.
 * Rectangle corners deliberately include space outside the faceted arch; a box
 * rejected by every region cannot contribute a visible scenery surface. */
inline std::vector<ClipVolume> TunnelSceneryRegions(TunnelKind kind, float length, Vec3 local_eye, Vec3 origin, unsigned direction)
{
	const auto profile = TunnelProfile(kind,0);
	if (length < 16 || local_eye.x <= 8.5f || local_eye.x >= length+7.5f ||
		local_eye.y <= profile.front().y+0.25f || local_eye.y >= profile.back().y-0.25f ||
		local_eye.z <= 0.25f || local_eye.z >= TunnelRoofHeight(kind,local_eye.y)-0.25f) return {};
	float roof = 0;
	for (Vec3 point : profile) roof = std::max(roof,point.z);
	float left = profile.front().y-0.5f, right = profile.back().y+0.5f, bottom = -0.5f, top = roof+0.5f;
	Vec3 zero = TunnelPoint(direction,{});
	auto world = [&](std::array<std::array<float,4>,6> planes) {
		ClipVolume result{origin+zero,planes};
		for (auto &plane : result.planes) {
			Vec3 normal = TunnelPoint(direction,{plane[0],plane[1],plane[2]})-zero;
			plane[0] = normal.x; plane[1] = normal.y; plane[2] = normal.z;
		}
		return result;
	};
	std::vector<ClipVolume> regions;
	regions.push_back(world({{{1,0,0,-7.5f},{-1,0,0,length+8.5f},{0,1,0,-left},{0,-1,0,right},{0,0,1,-bottom},{0,0,-1,top}}}));
	for (float mouth : {8.0f,length+8.0f}) {
		float sign = mouth < local_eye.x ? -1 : 1, distance = std::abs(mouth-local_eye.x);
		auto through_eye = [&](Vec3 normal) { return std::array<float,4>{normal.x,normal.y,normal.z,-Dot(normal,local_eye)}; };
		regions.push_back(world({{{sign,0,0,-sign*mouth+0.5f},
			through_eye({-sign*(left-local_eye.y),distance,0}),
			through_eye({sign*(right-local_eye.y),-distance,0}),
			through_eye({-sign*(bottom-local_eye.z),0,distance}),
			through_eye({sign*(top-local_eye.z),0,-distance}),{0,0,0,1}}}));
	}
	return regions;
}

/** Subtract one convex bore segment from terrain or rooted scenery triangles. Some legal slopes dip
 * below the vault beside the centreline; merely drawing a tube under them
 * leaves strips of grass crossing the interior. Material charts interpolate
 * with the clipped geometry, and the actual map heights are never modified. */
inline std::vector<Vertex> CutTunnelTerrain(std::span<const Vertex> input, TunnelKind kind, unsigned direction, float floor, Vec3 tile_offset = {})
{
	std::vector<Vertex> result;
	auto profile = TunnelProfile(kind,0);
	auto local = [&](Vec3 point) { point = TunnelPoint((4-direction)%4,point+tile_offset); point.z -= floor; return point; };
	/* Tree roots and body-owned foundations can extend below the terrain and
	 * across tile edges. Their local origin need not be the tile origin. Bound
	 * excavation along X so an overhanging component outside this segment stays. */
	std::vector<std::array<float,4>> planes{{1,0,0,0},{-1,0,0,16},{0,1,0,-profile.front().y},{0,-1,0,profile.back().y},{0,0,1,0.4f}};
	for (size_t i = 1; i+1 < profile.size(); ++i) {
		Vec3 a = profile[i], b = profile[i+1];
		float dy = b.y-a.y, dz = b.z-a.z;
		if (dy <= 0) continue;
		planes.push_back({0,dz,-dy,dy*(a.z+0.03f)-dz*a.y});
	}
	auto interpolate = [](Vertex a, const Vertex &b, float t) {
		a.position = a.position+(b.position-a.position)*t;
		a.normal = a.normal+(b.normal-a.normal)*t;
		a.texture = a.texture+(b.texture-a.texture)*t;
		return a;
	};
	for (size_t triangle = 0; triangle < input.size(); triangle += 3) {
		std::vector<Vertex> inside{input[triangle],input[triangle+1],input[triangle+2]};
		for (const auto &plane : planes) {
			if (inside.empty()) break;
			auto distance = [&](const Vertex &v) { Vec3 p = local(v.position); return plane[0]*p.x+plane[1]*p.y+plane[2]*p.z+plane[3]; };
			std::vector<Vertex> retained, clipped;
			Vertex previous = inside.back();
			for (const Vertex &current : inside) {
				float a = distance(previous), b = distance(current);
				if ((a >= 0) != (b >= 0)) {
					Vertex cut = interpolate(previous,current,a/(a-b));
					retained.push_back(cut); clipped.push_back(cut);
				}
				(b >= 0 ? clipped : retained).push_back(current);
				previous = current;
			}
			for (size_t i = 1; i+1 < retained.size(); ++i) {
				result.push_back(retained[0]); result.push_back(retained[i]); result.push_back(retained[i+1]);
			}
			inside = std::move(clipped);
		}
	}
	return result;
}

inline TunnelAssembly MakeTunnelAssembly(TunnelKind kind, bool portal)
{
	std::array<Scene,static_cast<unsigned>(TunnelMaterial::Count)> meshes;
	auto &earth = meshes[static_cast<unsigned>(TunnelMaterial::Earth)];
	auto &floor = meshes[static_cast<unsigned>(TunnelMaterial::Floor)];
	auto &structure = meshes[static_cast<unsigned>(TunnelMaterial::Structure)];
	auto &lining = meshes[static_cast<unsigned>(TunnelMaterial::Lining)];
	auto &detail = meshes[static_cast<unsigned>(TunnelMaterial::Detail)];
	auto &lights = meshes[static_cast<unsigned>(TunnelMaterial::Light)];
	auto &wire = meshes[static_cast<unsigned>(TunnelMaterial::Wire)];
	const bool road = kind == TunnelKind::Road || kind == TunnelKind::Tram;
	const bool electric = kind == TunnelKind::ElectricRail || kind == TunnelKind::Tram;
	const bool hood = kind == TunnelKind::Monorail;
	const float begin = portal ? 8 : 0;
	const Rgb stone = kind == TunnelKind::Rail || kind == TunnelKind::ElectricRail ? Rgb{0.55f,0.56f,0.57f} : Rgb{0.62f,0.49f,0.29f};
	const Rgb steel{0.60f,0.63f,0.65f}, concrete{0.54f,0.54f,0.50f};
	if (road) {
		/* Artist-selected unmarked asphalt patch in road-0-0 (256x127).
		 * Repeat small surface charts; neither lawns nor painted highlights
		 * from the outdoor road illustration belong inside the bore. */
		for (float x = 0; x < 16; x += 2) for (float y = 2.2f; y < 13.8f; y += 2) {
			size_t first = floor.vertices.size();
			floor.Quad({x,y,0.01f},{x+2,y,0.01f},{x+2,std::min(y+2,13.8f),0.01f},{x,std::min(y+2,13.8f),0.01f},{});
			for (size_t i = first; i < floor.vertices.size(); ++i) {
				auto &v = floor.vertices[i];
				v.texture = {(136+8*(v.position.x-x))/256,(72+4*(v.position.y-y))/127,-3};
			}
		}
		for (float x = 1; x < 16; x += 4) structure.Quad({x,7.88f,0.025f},{x+2,7.88f,0.025f},{x+2,8.12f,0.025f},{x,8.12f,0.025f},{0.86f,0.86f,0.83f});
	} else floor.Quad({0,2.2f,-0.32f},{16,2.2f,-0.32f},{16,13.8f,-0.32f},{0,13.8f,-0.32f},{});
	for (float y : {2.2f,13.1f}) GeometryBox(structure,{0,y,-0.15f},{16,y+0.7f,0.22f},concrete);
	auto tram_rails = [&](float left, float right) {
		for (float y : {left,right}) {
			GeometryBox(structure,{0,y-0.17f,-0.1f},{16,y+0.17f,-0.04f},steel);
			GeometryBox(structure,{0,y-0.07f,-0.04f},{16,y+0.07f,0.08f},steel);
		}
	};
	if (kind == TunnelKind::Tram) { tram_rails(4.3f,5.7f); tram_rails(10.3f,11.7f); }
	/* Railway systems are instanced from the same section meshes as adjoining
	 * surface tracks, so gauge, head heights and guideways cannot jump at a mouth. */
	auto profile = TunnelProfile(kind,begin), last = TunnelProfile(kind,16);
	for (size_t i = 0; i+1 < profile.size(); ++i) {
		lining.Quad(profile[i],last[i],last[i+1],profile[i+1],{0.23f,0.25f,0.25f});
	}
	/* Individual brick courses and mortar gaps are real shallow relief. */
	const float side = road ? 2.5f : 3;
	for (unsigned row = 0; row < 4; ++row) for (float x = begin; x < 16; x += 2) {
		float z = 0.15f+row*1.18f;
		float tone = 0.27f+0.018f*((static_cast<unsigned>(x/2)+row)%3);
		for (bool right : {false,true}) {
			float y = right ? 16-side-0.065f : side;
			GeometryBox(detail,{x+0.045f,y,z},{x+1.955f,y+0.065f,z+1.08f},{tone,tone,tone*0.97f});
		}
	}
	for (float x = begin; x < 16; x += 8) {
		auto rib = TunnelProfile(kind,x+0.1f);
		for (size_t i = 0; i+1 < rib.size(); ++i) GeometryBeam(detail,rib[i],rib[i+1],0.08f,{0.38f,0.38f,0.36f});
		for (float y : {side+0.18f,16-side-0.38f}) GeometryBox(lights,{x+3,y,4.7f},{x+3.5f,y+0.2f,5.1f},{1.15f,1.03f,0.73f});
	}
	if (electric) {
		for (float y : (road ? std::vector<float>{5,11} : std::vector<float>{8})) {
			float end = road ? 8 : 6.5f, height = road ? 7.0f : TunnelContactWireHeight(end);
			if (portal) {
				GeometryBeam(wire,{0,y,10},{end,y,height},0.035f,{0.31f,0.29f,0.24f});
				GeometryBeam(wire,{end,y,height},{16,y,height},0.035f,{0.31f,0.29f,0.24f});
			} else GeometryBeam(wire,{0,y,height},{16,y,height},0.035f,{0.31f,0.29f,0.24f});
		}
	}
	if (portal) {
		for (bool right : {false,true}) {
			float a = right ? 13.8f : 0, b = right ? 16 : 2.2f;
			earth.Quad({0,a,0},{16,a,8},{16,b,8},{0,b,0},{});
			float y = right ? 13.8f : 2.2f;
			structure.Triangle({0,y,0},{8,y,0},{8,y,4},stone);
		}
		if (road) {
			for (float y : {1.8f,13.5f}) GeometryBox(structure,{7.5f,y,0},{9,y+0.7f,7.6f},stone);
			GeometryBox(structure,{7.5f,1.8f,7.6f},{16,14.2f,8.25f},stone);
			GeometryBox(detail,{7.35f,1.65f,8.0f},{8.1f,14.35f,8.45f},{0.71f,0.57f,0.35f});
		} else {
			/* Extruded voussoirs close both sides of the stone arch. */
			for (float y : {2.25f,13.0f}) GeometryBox(structure,{7.5f,y,0},{8.7f,y+0.75f,5.1f},stone);
			for (unsigned i = 0; i < 16; ++i) {
				float a = std::numbers::pi_v<float>*i/16, b = std::numbers::pi_v<float>*(i+1)/16;
				Vec3 p[] = {{7.5f,8-5*std::cos(a),5.1f+2.6f*std::sin(a)},{7.5f,8-5*std::cos(b),5.1f+2.6f*std::sin(b)},
					{7.5f,8-5.75f*std::cos(b),5.1f+3.4f*std::sin(b)},{7.5f,8-5.75f*std::cos(a),5.1f+3.4f*std::sin(a)}};
				Rgb colour{stone.r+(i%2)*0.035f,stone.g+(i%2)*0.035f,stone.b+(i%2)*0.035f};
				structure.Quad(p[0],p[1],p[2],p[3],colour);
				structure.Quad(p[3]+Vec3{1.2f,0,0},p[2]+Vec3{1.2f,0,0},p[1]+Vec3{1.2f,0,0},p[0]+Vec3{1.2f,0,0},colour);
				for (unsigned j = 0; j < 4; ++j) structure.Quad(p[j],p[j]+Vec3{1.2f,0,0},p[(j+1)%4]+Vec3{1.2f,0,0},p[(j+1)%4],colour);
				if (hood) {
					structure.Quad(p[3]+Vec3{1.2f,0,0},p[2]+Vec3{1.2f,0,0},Vec3{16,p[2].y,p[2].z},Vec3{16,p[3].y,p[3].z},colour);
				} else {
					structure.Quad(p[3],p[2],{7.5f,p[2].y,8.6f},{7.5f,p[3].y,8.6f},stone);
				}
			}
		}
		if (!hood) earth.Quad({8.7f,2.2f,8.6f},{16,2.2f,8},{16,13.8f,8},{8.7f,13.8f,8.6f},{});
	}
	for (auto index : {TunnelMaterial::Earth,TunnelMaterial::Floor}) for (auto &vertex : meshes[static_cast<unsigned>(index)].vertices) {
		if (vertex.texture.z != -3) vertex.texture = {2*(vertex.position.y-vertex.position.x),vertex.position.x+vertex.position.y,0};
	}
	TunnelAssembly result;
	for (size_t i = 0; i < result.parts.size(); ++i) result.parts[i] = std::move(meshes[i].vertices);
	return result;
}

} // namespace Renderer3D
#endif
