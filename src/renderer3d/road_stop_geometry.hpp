/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_ROAD_STOP_GEOMETRY_HPP
#define RENDERER3D_ROAD_STOP_GEOMETRY_HPP

#include "terrain_geometry.hpp"
#include "material_chart.hpp"
#include "tunnel_geometry.hpp"

namespace Renderer3D {
enum class RoadStopMaterial : unsigned { Road, Paving, Company, Masonry, Metal, Wood, Glass, Detail, Markings, Tram, Count };
struct RoadStopAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(RoadStopMaterial::Count)> parts;
};

inline Vec3 RoadStopPoint(unsigned layout, Vec3 p)
{
	if (layout < 4) return TunnelPoint(layout,p); // Canonical bay opens towards +X.
	return layout == 4 ? p : Vec3{p.y,p.x,p.z};
}

inline RoadStopAssembly MakeRoadStopAssembly(bool truck, unsigned layout, bool tram = false, bool detail = true)
{
	std::array<Scene,static_cast<unsigned>(RoadStopMaterial::Count)> parts;
	auto mesh = [&](RoadStopMaterial material) -> Scene & { return parts[static_cast<unsigned>(material)]; };
	auto box = [&](RoadStopMaterial material, Vec3 a, Vec3 b, Rgb colour = Rgb{}) { GeometryBox(mesh(material),a,b,colour); };
	auto beam = [&](RoadStopMaterial material, Vec3 a, Vec3 b, float radius, Rgb colour) { GeometryBeam(mesh(material),a,b,radius,colour); };
	const Rgb pale{0.85f,0.86f,0.82f}, wood{0.48f,0.34f,0.16f}, dark{0.15f,0.17f,0.18f};
	bool drive_through = layout >= 4;
	box(RoadStopMaterial::Road,{drive_through ? 0.0f : 3.0f,3,0.01f},{16,13,0.08f});
	for (float y : {0.0f,13.0f}) box(RoadStopMaterial::Paving,{0,y,0},{16,y+3,0.35f});
	if (!drive_through) box(RoadStopMaterial::Paving,{0,3,0},{3,13,0.35f});
	if (drive_through) {
		for (float x : {0.5f,6.5f,12.5f}) box(RoadStopMaterial::Markings,{x,7.83f,0.081f},{x+2.5f,8.17f,0.10f},pale);
	} else {
		for (float y : {5.5f,10.5f}) box(RoadStopMaterial::Markings,{4,y,0.081f},{13.7f,y+0.17f,0.10f},pale);
	}
	/* Components are authored at side Y=0. The transform places the same
	 * structural assembly at the far curb or along the back of a bay stop. */
	auto placed = [&](unsigned side, const auto &build) {
		std::array<size_t,static_cast<unsigned>(RoadStopMaterial::Count)> begin;
		for (size_t i = 0; i < parts.size(); ++i) begin[i] = parts[i].vertices.size();
		build();
		for (size_t i = 0; i < parts.size(); ++i) {
			for (size_t j = begin[i]; j < parts[i].vertices.size(); ++j) {
				auto &p = parts[i].vertices[j].position;
				if (side == 1) p.y = 16-p.y;
				if (side == 2) std::swap(p.x,p.y);
			}
			if (side != 0) for (size_t j = begin[i]; j < parts[i].vertices.size(); j += 3) std::swap(parts[i].vertices[j+1],parts[i].vertices[j+2]);
		}
	};
	auto sign = [&](float x) {
		beam(RoadStopMaterial::Metal,{x,1.5f,0.35f},{x,1.5f,11.5f},0.075f,pale);
		box(RoadStopMaterial::Metal,{x-0.75f,1.40f,9.7f},{x+0.75f,1.60f,11.2f},pale);
		box(RoadStopMaterial::Company,{x-0.64f,1.38f,9.86f},{x+0.64f,1.62f,11.04f});
		box(RoadStopMaterial::Detail,{x-0.30f,1.30f,4.2f},{x+0.30f,1.39f,6.5f},{0.72f,0.71f,0.60f});
	};
	auto canopy = [&](float a, float b) {
		for (float x : {a,b}) for (float y : {0.4f,2.5f}) beam(RoadStopMaterial::Metal,{x,y,0.35f},{x,y,y < 1 ? 9.1f : 10},0.085f,pale);
		auto roof_z = [](float y) { return 9.05f+(y-0.2f)*0.95f/2.6f; };
		for (unsigned panel = 0; panel < 4; ++panel) {
			float x0 = std::lerp(a,b,panel/4.0f), x1 = std::lerp(a,b,(panel+1)/4.0f);
			Vec3 p{x0,0.2f,roof_z(0.2f)}, q{x1,0.2f,roof_z(0.2f)}, r{x1,2.8f,roof_z(2.8f)}, s{x0,2.8f,roof_z(2.8f)}, thickness{0,0,-0.14f};
			mesh(RoadStopMaterial::Company).Quad(p,q,r,s,{});
			mesh(RoadStopMaterial::Company).Quad(s+thickness,r+thickness,q+thickness,p+thickness,{});
			for (auto edge : {std::pair{p,q},std::pair{q,r},std::pair{r,s},std::pair{s,p}}) beam(RoadStopMaterial::Metal,edge.first,edge.second,0.09f,pale);
		}
		for (float centre : {std::lerp(a,b,0.27f),std::lerp(a,b,0.73f)}) {
			float width = (b-a)*0.19f;
			for (float x : {centre-width+0.25f,centre+width-0.25f}) {
				for (float y : {1.05f,2.25f}) box(RoadStopMaterial::Wood,{x-0.06f,y-0.06f,0.35f},{x+0.06f,y+0.06f,1.6f},wood);
			}
			unsigned slats = detail ? 5 : 2;
			for (unsigned i = 0; i < slats; ++i) {
				float y = 1+i*1.4f/slats, z = 1.8f+i*1.6f/slats;
				box(RoadStopMaterial::Wood,{centre-width,y,1.5f},{centre+width,y+1.25f/slats,1.65f},wood);
				box(RoadStopMaterial::Wood,{centre-width,0.9f,z},{centre+width,1.05f,z+1.4f/slats},wood);
			}
		}
		sign(std::min(14.9f,b+0.8f));
	};
	auto fence = [&](float a, float b, bool company) {
		float height = company ? 2.1f : 4.3f;
		for (float x = a; x <= b; x += 2) box(RoadStopMaterial::Metal,{x-0.06f,0.75f,0.35f},{x+0.06f,0.9f,height},company ? pale : wood);
		beam(RoadStopMaterial::Metal,{a,0.82f,height},{b,0.82f,height},0.055f,company ? pale : wood);
		if (company) {
			for (float x = a+0.3f; x < b; x += 0.8f) box(RoadStopMaterial::Company,{x,0.76f,0.8f},{std::min(b,x+0.30f),0.88f,1.95f});
		} else {
			beam(RoadStopMaterial::Metal,{a,0.82f,0.8f},{b,0.82f,0.8f},0.04f,pale);
			if (detail) for (float x = a; x < b-0.5f; x += 0.6f) for (float z = 0.8f; z < height-0.6f; z += 0.7f) {
				beam(RoadStopMaterial::Metal,{x,0.82f,z},{std::min(b,x+0.6f),0.82f,z+0.7f},0.016f,pale);
				beam(RoadStopMaterial::Metal,{x,0.82f,z+0.7f},{std::min(b,x+0.6f),0.82f,z},0.016f,pale);
			}
		}
	};
	auto loading = [&](float a, float b) {
		box(RoadStopMaterial::Masonry,{a,0.2f,0.35f},{b,0.55f,8.8f});
		for (float x : {a,b-0.45f}) box(RoadStopMaterial::Masonry,{x,0.5f,0.35f},{x+0.45f,2.8f,8.8f});
		Vec3 p{a,0.1f,10}, q{b,0.1f,10}, r{b,2.9f,8.8f}, s{a,2.9f,8.8f};
		mesh(RoadStopMaterial::Masonry).Quad(p,q,r,s,{});
		mesh(RoadStopMaterial::Masonry).Quad(s-Vec3{0,0,0.16f},r-Vec3{0,0,0.16f},q-Vec3{0,0,0.16f},p-Vec3{0,0,0.16f},{});
		for (auto edge : {std::pair{p,q},std::pair{q,r},std::pair{r,s},std::pair{s,p}}) beam(RoadStopMaterial::Metal,edge.first,edge.second,0.07f,pale);
		for (unsigned i = 0; i < 4; ++i) {
			float x0 = std::lerp(a,b,(i+0.12f)/4), x1 = std::lerp(a,b,(i+0.88f)/4);
			mesh(RoadStopMaterial::Company).Quad({x0,0.55f,9.847f},{x1,0.55f,9.847f},{x1,2.45f,9.032f},{x0,2.45f,9.032f},{});
		}
	};
	auto office = [&](float a) {
		box(RoadStopMaterial::Masonry,{a,0.2f,0.35f},{a+4.4f,2.8f,7.6f});
		box(RoadStopMaterial::Metal,{a-0.15f,0.05f,7.6f},{a+4.55f,2.95f,7.85f},pale);
		box(RoadStopMaterial::Detail,{a+0.15f,0.35f,7.85f},{a+4.25f,2.65f,7.88f},dark);
		box(RoadStopMaterial::Company,{a+0.45f,2.80f,0.35f},{a+1.5f,2.87f,5.8f});
		box(RoadStopMaterial::Metal,{a+2.1f,2.80f,3},{a+3.85f,2.86f,5.8f},pale);
		box(RoadStopMaterial::Glass,{a+2.22f,2.86f,3.2f},{a+3.73f,2.89f,5.6f},{0.18f,0.31f,0.44f});
	};
	if (!truck) {
		placed(0,[&] { canopy(drive_through ? 2.0f : 3.3f,14.0f); });
		if (drive_through) placed(1,[&] { canopy(2,14); });
		else {
			placed(2,[&] { canopy(1.0f,14.0f); });
			placed(1,[&] { fence(3.3f,15,true); });
			box(RoadStopMaterial::Company,{14.45f,0.4f,0.35f},{15.05f,1.0f,2.25f});
			box(RoadStopMaterial::Metal,{14.40f,0.35f,2.25f},{15.10f,1.05f,2.38f},pale);
			box(RoadStopMaterial::Detail,{14.54f,0.49f,2.38f},{14.96f,0.91f,2.40f},dark);
		}
	} else if (drive_through) {
		placed(0,[&] { loading(0.6f,15.4f); });
		placed(1,[&] { office(0.4f); fence(5.1f,15.1f,false); sign(6.2f); });
	} else {
		placed(2,[&] { office(0.4f); loading(5.1f,15.4f); });
		placed(0,[&] { fence(3.3f,15.1f,false); sign(14.8f); });
		placed(1,[&] { fence(3.3f,15.1f,false); });
	}
	if (tram && drive_through) for (float y : {3.7f,6.3f,9.7f,12.3f}) box(RoadStopMaterial::Tram,{0,y-0.07f,0.08f},{16,y+0.07f,0.13f},{0.58f,0.61f,0.61f});
	RoadStopAssembly result;
	for (size_t part = 0; part < parts.size(); ++part) {
		auto &vertices = parts[part].vertices;
		/* Recompute after local side reflections, before choosing component charts. */
		for (size_t i = 0; i < vertices.size(); i += 3) {
			Vec3 normal = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
			for (size_t j = i; j < i+3; ++j) vertices[j].normal = normal;
		}
		RoadStopMaterial material = static_cast<RoadStopMaterial>(part);
		if (material == RoadStopMaterial::Road || material == RoadStopMaterial::Paving || material == RoadStopMaterial::Company || material == RoadStopMaterial::Masonry) {
			TextureRegion crop = material == RoadStopMaterial::Road ? TextureRegion{136.0f/256,72.0f/127,144.0f/256,76.0f/127} :
				material == RoadStopMaterial::Paving ? TextureRegion{112.0f/256,50.0f/127,144.0f/256,66.0f/127} :
				material == RoadStopMaterial::Company ? TextureRegion{43.4f/108,30.4f/87,43.6f/108,30.6f/87} : TextureRegion{26.0f/88,45.0f/81,34.0f/88,53.0f/81};
			float repeat = material == RoadStopMaterial::Road ? 0.5f : material == RoadStopMaterial::Paving ? 4 : 2;
			vertices = ApplyMaterialChart(vertices,{{crop,crop,crop},{repeat,repeat},true});
		}
		for (auto &vertex : vertices) vertex.position = RoadStopPoint(layout,vertex.position);
		for (size_t i = 0; i < vertices.size(); i += 3) {
			if (layout == 5) std::swap(vertices[i+1],vertices[i+2]);
			Vec3 normal = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
			for (size_t j = i; j < i+3; ++j) vertices[j].normal = normal;
		}
		result.parts[part] = std::move(vertices);
	}
	return result;
}
} // namespace Renderer3D
#endif
