/* SPDX-License-Identifier: GPL-2.0-only */
/** @file depot_geometry.hpp Authored open maintenance sheds, with component-only charts. */
#ifndef RENDERER3D_DEPOT_GEOMETRY_HPP
#define RENDERER3D_DEPOT_GEOMETRY_HPP

#include "rail_geometry.hpp"
#include "material_chart.hpp"
#include "tunnel_geometry.hpp"

namespace Renderer3D {

enum class DepotMaterial : unsigned { Masonry, Roof, Company, Glazing, Metal, Floor, Detail, TrackBed, Track, ReservedTrack, TrackSupport, Wire, Count };
struct DepotAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(DepotMaterial::Count)> parts;
};

/** Canonical +X is the door; these are actual upstream depot exit directions. */
inline Vec3 DepotPoint(unsigned direction, Vec3 point) { return TunnelPoint(direction,point); }

inline TextureRegion DepotChart(unsigned kind, DepotMaterial material)
{
	if (material == DepotMaterial::Company) return {63.4f/168,22.4f/93,63.6f/168,22.6f/93};
	if (material == DepotMaterial::Masonry) {
		if (kind <= 1) return {26.0f/204,108.0f/160,32.0f/204,114.0f/160};
		if (kind == 2) return {26.0f/200,104.0f/152,38.0f/200,112.0f/152};
		if (kind == 3) return {140.0f/200,94.0f/148,152.0f/200,106.0f/148};
		if (kind == 4) return {125.0f/240,162.0f/193,135.0f/240,172.0f/193};
		return {26.0f/240,158.0f/228,38.0f/240,170.0f/228};
	}
	if (kind <= 1) return {143.0f/204,71.0f/160,151.0f/204,79.0f/160};
	if (kind == 4) return {50.0f/240,74.0f/193,54.0f/240,78.0f/193};
	return {50.4f/240,118.4f/228,50.6f/240,118.6f/228};
}

inline DepotAssembly MakeDepotAssembly(unsigned kind, unsigned direction, unsigned lod = 0)
{
	std::array<Scene,static_cast<unsigned>(DepotMaterial::Count)> parts;
	auto mesh = [&](DepotMaterial part) -> Scene & { return parts[static_cast<unsigned>(part)]; };
	auto box = [&](DepotMaterial part, Vec3 low, Vec3 high, Rgb colour = Rgb{}) { GeometryBox(mesh(part),low,high,colour); };
	auto beam = [&](DepotMaterial part, Vec3 a, Vec3 b, float radius, Rgb colour) { GeometryBeam(mesh(part),a,b,radius,colour); };
	auto roof = [&](DepotMaterial part, Vec3 a, Vec3 b, Vec3 c, Vec3 d) {
		Vec3 thickness{0,0,-0.22f};
		mesh(part).Quad(a,b,c,d,{});
		mesh(part).Quad(d+thickness,c+thickness,b+thickness,a+thickness,{});
		for (auto edge : {std::pair{a,b},std::pair{b,c},std::pair{c,d},std::pair{d,a}}) {
			mesh(part).Quad(edge.first,edge.first+thickness,edge.second+thickness,edge.second,{});
		}
	};
	const Rgb iron{0.57f,0.60f,0.60f}, dark{0.10f,0.12f,0.13f}, cream{0.72f,0.65f,0.48f};
	const bool rail = kind < 4;
	float rear = rail ? 2 : 0.5f, front = rail ? 14 : 15.5f, left = rail ? 2 : 0.5f, right = 16-left;
	float eave = kind <= 1 ? 14 : kind < 4 ? 13 : 11;
	box(DepotMaterial::Floor,{rear,left,0.015f},{front,right,0.055f},{0.39f,0.40f,0.39f});
	box(DepotMaterial::Masonry,{rear,left,0},{rear+0.6f,right,eave});
	for (float y : {left,right-0.6f}) box(DepotMaterial::Masonry,{rear,y,0},{front,y+0.6f,eave});
	box(DepotMaterial::Masonry,{front-0.6f,left,0},{front,3.2f,eave});
	box(DepotMaterial::Masonry,{front-0.6f,12.8f,0},{front,right,eave});
	box(DepotMaterial::Masonry,{front-0.6f,3.2f,eave-1},{front,12.8f,eave});
	/* All bays have modeled inside walls, rafters and a genuinely open doorway. */
	for (float x : {rear+1,(rear+front)/2,front-0.5f}) {
		beam(DepotMaterial::Metal,{x,left+0.8f,eave-0.4f},{x,right-0.8f,eave-0.4f},0.08f,iron);
	}
	if (kind <= 1) {
		roof(DepotMaterial::Roof,{rear-0.3f,left-0.3f,eave},{front+0.3f,left-0.3f,eave},{front+0.3f,8,21},{rear-0.3f,8,21});
		roof(DepotMaterial::Roof,{rear-0.3f,8,21},{front+0.3f,8,21},{front+0.3f,right+0.3f,eave},{rear-0.3f,right+0.3f,eave});
		for (float x : {rear,front}) {
			Vec3 a{x,left,eave}, b{x,right,eave}, c{x,8,21}, depth{x == rear ? 0.6f : -0.6f,0,0};
			if (x == rear) std::swap(a,b);
			mesh(DepotMaterial::Masonry).Triangle(a,b,c,{});
			mesh(DepotMaterial::Masonry).Triangle(c+depth,b+depth,a+depth,{});
			for (auto edge : {std::pair{a,b},std::pair{b,c},std::pair{c,a}}) {
				mesh(DepotMaterial::Masonry).Quad(edge.first,edge.first+depth,edge.second+depth,edge.second,{});
			}
			/* Circular gable ventilation grille, independently modeled. */
			for (unsigned i = 0; i < 12; ++i) {
				float a = 2*std::numbers::pi_v<float>*i/12, b = 2*std::numbers::pi_v<float>*(i+1)/12;
				float face = x == rear ? x-0.02f : x+0.02f;
				mesh(DepotMaterial::Detail).Triangle({face,8,17.2f},{face,8+0.55f*std::cos(a),17.2f+1.0f*std::sin(a)},
					{face,8+0.55f*std::cos(b),17.2f+1.0f*std::sin(b)},dark);
			}
		}
		for (float y : {left-0.3f,right+0.3f}) box(DepotMaterial::Company,{rear-0.3f,y-0.06f,eave-0.45f},{front+0.3f,y+0.06f,eave});
		box(DepotMaterial::Masonry,{rear,6.8f,19.5f},{front,9.2f,22});
		roof(DepotMaterial::Roof,{rear-0.2f,6.6f,22},{front+0.2f,6.6f,22},{front+0.2f,8,23},{rear-0.2f,8,23});
		roof(DepotMaterial::Roof,{rear-0.2f,8,23},{front+0.2f,8,23},{front+0.2f,9.4f,22},{rear-0.2f,9.4f,22});
		for (float y : {6.6f,9.4f}) box(DepotMaterial::Company,{rear-0.2f,y-0.05f,21.6f},{front+0.2f,y+0.05f,22});
		for (float x : {2.5f,6.0f,10.0f,13.5f}) for (float y : {left-0.16f,right-0.16f}) {
			box(DepotMaterial::Masonry,{x-0.18f,y,0},{x+0.18f,y+0.32f,eave});
		}
		box(DepotMaterial::Detail,{rear-0.045f,7,0},{rear-0.015f,9,7},{0.25f,0.16f,0.09f});
		for (float y : {7.0f,9.0f}) beam(DepotMaterial::Metal,{rear-0.065f,y,0},{rear-0.065f,y,7},0.035f,cream);
		for (float y : {4.0f,11.0f}) {
			box(DepotMaterial::Detail,{rear-0.04f,y,8.5f},{rear-0.02f,y+1,9.5f},dark);
			if (lod == 0) for (float z = 8.7f; z < 9.5f; z += 0.25f) beam(DepotMaterial::Metal,{rear-0.065f,y,z},{rear-0.065f,y+1,z},0.025f,iron);
		}
		for (float x : {4.0f,8.0f,12.0f}) for (bool near : {false,true}) {
			float y = near ? right+0.01f : left-0.01f;
			box(DepotMaterial::Detail,{x-1.05f,y-0.035f,3.5f},{x+1.05f,y+0.035f,8.8f},cream);
			box(DepotMaterial::Glazing,{x-0.88f,y-0.06f,3.8f},{x+0.88f,y+0.06f,8.8f},{0.17f,0.14f,0.075f});
			for (unsigned i = 0; i < 8; ++i) {
				float a = std::numbers::pi_v<float>*i/8, b = std::numbers::pi_v<float>*(i+1)/8;
				Vec3 p{x+0.88f*std::cos(a),y,8.8f+2.0f*std::sin(a)}, q{x+0.88f*std::cos(b),y,8.8f+2.0f*std::sin(b)};
				mesh(DepotMaterial::Glazing).Triangle({x,y,8.8f},p,q,{0.17f,0.14f,0.075f});
				beam(DepotMaterial::Detail,p,q,0.065f,cream);
			}
			if (lod == 0) for (float z : {4.8f,6.5f}) beam(DepotMaterial::Detail,{x-0.85f,y+(near ? 0.07f : -0.07f),z},{x+0.85f,y+(near ? 0.07f : -0.07f),z},0.035f,cream);
		}
	} else if (kind == 3) {
		/* Shallow glass pyramid and perimeter mullions match the fallback maglev shed. */
		Vec3 centre{8,8,19};
		const Vec3 corners[] = {{rear,left,eave},{front,left,eave},{front,right,eave},{rear,right,eave}};
		for (unsigned i = 0; i < 4; ++i) {
			mesh(DepotMaterial::Company).Triangle(corners[i],corners[(i+1)%4],centre,{});
			Vec3 depth{0,0,-0.22f};
			mesh(DepotMaterial::Company).Triangle(centre+depth,corners[(i+1)%4]+depth,corners[i]+depth,{});
			beam(DepotMaterial::Metal,corners[i],corners[(i+1)%4],0.15f,iron);
			beam(DepotMaterial::Metal,corners[i],centre,0.075f,iron);
			beam(DepotMaterial::Metal,(corners[i]+corners[(i+1)%4])*0.5f,centre,0.045f,iron);
		}
		for (float x = rear; x <= front; x += 2) for (float y : {left,right}) beam(DepotMaterial::Metal,{x,y,eave-1},{x,y,eave+1},0.12f,iron);
	} else {
		/* Independent folded roof bays, never a painted zig-zag on a flat lid. */
		unsigned bays = kind == 2 ? 3 : 5;
		DepotMaterial covering = kind == 2 ? DepotMaterial::Company : DepotMaterial::Roof;
		for (unsigned i = 0; i < bays; ++i) {
			float a = std::lerp(rear,front,static_cast<float>(i)/bays), b = std::lerp(rear,front,static_cast<float>(i+1)/bays), middle = std::lerp(a,b,0.45f);
			roof(covering,{a,left,eave},{middle,left,eave+3},{middle,right,eave+3},{a,right,eave});
			roof(covering,{middle,left,eave+3},{b,left,eave},{b,right,eave},{middle,right,eave+3});
			beam(DepotMaterial::Metal,{middle,left,eave+3},{middle,right,eave+3},0.065f,iron);
			beam(DepotMaterial::Metal,{a,left,eave},{a,right,eave},0.045f,iron);
			for (float y : {left,right}) {
				mesh(DepotMaterial::Metal).Triangle({a,y,eave},{b,y,eave},{middle,y,eave+3},iron);
				mesh(DepotMaterial::Metal).Triangle({middle,y,eave+3},{b,y,eave},{a,y,eave},iron);
				beam(DepotMaterial::Metal,{a,y,eave},{middle,y,eave+3},0.06f,iron);
				beam(DepotMaterial::Metal,{middle,y,eave+3},{b,y,eave},0.06f,iron);
			}
		}
	}
	if (kind >= 2) {
		for (float y : {left-0.02f,right+0.02f}) for (float x = rear+0.6f; x < front; x += kind < 4 ? 3.5f : 1.0f) {
			box(DepotMaterial::Company,{x,y-0.05f,kind < 4 ? 3.0f : eave-1.8f},{std::min(front-0.1f,x+0.45f),y+0.05f,eave-0.1f});
		}
		if (kind < 4) for (float y : {left+0.4f,right-0.4f}) for (unsigned i = 0; i < 12; ++i) {
			box(DepotMaterial::Detail,{front,y-0.2f,static_cast<float>(i)},{front+0.06f,y+0.2f,i+1.0f},i%2 ? Rgb{0.88f,0.69f,0.08f} : dark);
		}
	}
	if (kind == 1) {
		beam(DepotMaterial::Wire,{8,8,10},{8,8,20.7f},0.035f,iron);
		for (float z : {17.0f,17.4f,17.8f}) box(DepotMaterial::Wire,{7.87f,7.87f,z},{8.13f,8.13f,z+0.17f},{0.49f,0.12f,0.095f});
	}
	if (kind == 5) {
		for (float y : {5.5f,10.5f}) {
			box(DepotMaterial::Metal,{7.7f,y-0.25f,13},{8.3f,y+0.25f,21},iron);
			for (float z = 16; z < 20; z += 0.65f) box(DepotMaterial::Company,{7.55f,y-0.4f,z},{8.45f,y+0.4f,z+0.3f});
		}
		beam(DepotMaterial::Metal,{8,4.7f,21},{8,8,23},0.13f,iron);
		beam(DepotMaterial::Metal,{8,8,23},{8,11.3f,21},0.13f,iron);
		box(DepotMaterial::Detail,{7.5f,7.5f,18},{8.5f,8.5f,21},{0.60f,0.49f,0.28f});
		for (float y : {5.0f,11.0f}) beam(DepotMaterial::Wire,{rear+0.7f,y,9.5f},{16,y,9.5f},0.035f,iron);
		for (float y : {3.7f,6.3f,9.7f,12.3f}) box(DepotMaterial::TrackSupport,{rear+0.8f,y-0.07f,0.055f},{16,y+0.07f,0.10f},iron);
	}
	if (rail) {
		auto tracks = MakeRailAssembly(kind,0,{},lod);
		for (size_t part = 0; part < tracks.parts.size(); ++part) {
			DepotMaterial target = part == static_cast<unsigned>(RailMaterial::Ballast) ? DepotMaterial::TrackBed :
				part == static_cast<unsigned>(RailMaterial::Rails) ? DepotMaterial::Track :
				part == static_cast<unsigned>(RailMaterial::ReservedRails) ? DepotMaterial::ReservedTrack : DepotMaterial::TrackSupport;
			auto clipped = ClipRailSection(tracks.parts[part],2.7f,16);
			auto &out = mesh(target).vertices;
			out.insert(out.end(),clipped.begin(),clipped.end());
		}
		for (float y : {6.7f,9.3f}) beam(DepotMaterial::Metal,{3.1f,y,0.2f},{3.1f,y,1.3f},0.13f,dark);
		box(DepotMaterial::Detail,{3,6.2f,1},{3.4f,9.8f,1.5f},{0.40f,0.19f,0.11f});
	}
	DepotAssembly result;
	for (size_t part = 0; part < parts.size(); ++part) {
		auto &vertices = parts[part].vertices;
		DepotMaterial material = static_cast<DepotMaterial>(part);
		if (material == DepotMaterial::Masonry || material == DepotMaterial::Roof || material == DepotMaterial::Company) {
			TextureRegion crop = DepotChart(kind,material);
			vertices = ApplyMaterialChart(vertices,{{crop,crop,crop},{2,2},true});
		}
		for (auto &vertex : vertices) vertex.position = DepotPoint(direction,vertex.position);
		for (size_t i = 0; i < vertices.size(); i += 3) {
			Vec3 normal = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
			for (size_t j = i; j < i+3; ++j) vertices[j].normal = normal;
		}
		result.parts[part] = std::move(vertices);
	}
	return result;
}

} // namespace Renderer3D
#endif
