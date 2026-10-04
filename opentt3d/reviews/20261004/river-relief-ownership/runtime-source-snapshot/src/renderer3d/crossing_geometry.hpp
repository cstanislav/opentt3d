/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_CROSSING_GEOMETRY_HPP
#define RENDERER3D_CROSSING_GEOMETRY_HPP

#include "rail_detail_geometry.hpp"
#include "material_chart.hpp"

namespace Renderer3D {
enum class CrossingMaterial : unsigned { Road, Markings, Equipment, Gates, TrackBed, Track, ReservedTrack, TrackSupport, Count };
struct CrossingAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(CrossingMaterial::Count)> parts;
};

/** Canonical railway X crosses road Y. All control state comes from the map. */
inline CrossingAssembly MakeCrossingAssembly(unsigned kind, bool transpose, bool barred, bool tram, unsigned lod = 0)
{
	std::array<Scene,static_cast<unsigned>(CrossingMaterial::Count)> parts;
	auto mesh = [&](CrossingMaterial part) -> Scene & { return parts[static_cast<unsigned>(part)]; };
	GeometryBox(mesh(CrossingMaterial::Road),{3,0,0.01f},{13,16,0.10f},{});
	for (float y : {0.0f,13.5f}) GeometryBox(mesh(CrossingMaterial::Markings),{7.83f,y,0.101f},{8.17f,y+2.5f,0.12f},{0.92f,0.92f,0.86f});
	for (float y : {3.0f,12.8f}) GeometryBox(mesh(CrossingMaterial::Markings),{3.3f,y,0.10f},{12.7f,y+0.15f,0.12f},{0.76f,0.77f,0.73f});
	const Rgb metal{0.55f,0.57f,0.56f}, dark{0.08f,0.09f,0.09f};
	for (float x : {2.0f,14.0f}) for (float y : {3.0f,13.0f}) {
		auto &equipment = mesh(CrossingMaterial::Equipment);
		GeometryBox(equipment,{x-0.3f,y-0.3f,0},{x+0.3f,y+0.3f,0.35f},{0.50f,0.51f,0.48f});
		GeometryBox(equipment,{x-0.075f,y-0.075f,0.3f},{x+0.075f,y+0.075f,5.1f},metal);
		Scene head;
		GeometryBox(head,{-0.22f,-0.95f,4.1f},{0.30f,0.95f,5.8f},dark);
		for (float lamp : {-0.46f,0.46f}) SignalLens(head,lamp,4.9f,barred ? Rgb{1.15f,0.025f,0.015f} : Rgb{0.09f,0.01f,0.008f});
		for (auto &v : head.vertices) {
			Vec3 p = v.position;
			v.position = y < 8 ? Vec3{x+p.y,y-p.x,p.z} : Vec3{x-p.y,y+p.x,p.z};
		}
		equipment.vertices.insert(equipment.vertices.end(),head.vertices.begin(),head.vertices.end());
	}
	if (kind == 3 && barred) for (float y : {4.4f,11.6f}) {
		for (unsigned stripe = 0; stripe < 10; ++stripe) {
			GeometryBox(mesh(CrossingMaterial::Gates),{3.0f+stripe,y-0.18f,0.2f},{4.0f+stripe,y+0.18f,0.78f},
				stripe%2 ? Rgb{0.92f,0.73f,0.05f} : dark);
		}
	}
	if (tram) for (float x : {3.7f,6.3f,9.7f,12.3f}) GeometryBox(mesh(CrossingMaterial::Markings),{x-0.07f,0,0.10f},{x+0.07f,16,0.15f},metal);
	auto tracks = MakeRailAssembly(kind,0,{},lod);
	for (size_t part = 0; part < tracks.parts.size(); ++part) {
		CrossingMaterial target = part == static_cast<unsigned>(RailMaterial::Ballast) ? CrossingMaterial::TrackBed :
			part == static_cast<unsigned>(RailMaterial::Rails) ? CrossingMaterial::Track :
			part == static_cast<unsigned>(RailMaterial::ReservedRails) ? CrossingMaterial::ReservedTrack : CrossingMaterial::TrackSupport;
		auto &out = mesh(target).vertices;
		bool running = target == CrossingMaterial::Track || target == CrossingMaterial::ReservedTrack;
		/* Asphalt replaces the bed/ties through the roadway; maglev side walls
		 * must leave a real gap for cars until the original barred state closes it. */
		if (!running || kind == 3) {
			for (auto range : {std::pair{0.0f,3.0f},std::pair{13.0f,16.0f}}) {
				auto clipped = ClipRailSection(tracks.parts[part],range.first,range.second);
				out.insert(out.end(),clipped.begin(),clipped.end());
			}
		} else {
			/* Embed the running surface flush with the crossing deck. In
			 * particular, a full-height monorail beam cannot block the car lanes. */
			float head = kind == 2 ? 1.0f : 0.5f;
			for (auto range : {std::pair{0.0f,2.0f},std::pair{2.0f,3.0f},std::pair{3.0f,13.0f},std::pair{13.0f,14.0f},std::pair{14.0f,16.0f}}) {
				auto clipped = ClipRailSection(tracks.parts[part],range.first,range.second);
				for (auto &vertex : clipped) {
					float blend = std::clamp(std::min(vertex.position.x-2,14-vertex.position.x),0.0f,1.0f);
					vertex.position.z *= std::lerp(1.0f,0.12f/head,blend);
				}
				out.insert(out.end(),clipped.begin(),clipped.end());
			}
		}
	}
	CrossingAssembly result;
	for (size_t part = 0; part < parts.size(); ++part) {
		auto &vertices = parts[part].vertices;
		if (part == static_cast<unsigned>(CrossingMaterial::Road)) {
			TextureRegion asphalt{136.0f/256,72.0f/127,144.0f/256,76.0f/127};
			vertices = ApplyMaterialChart(vertices,{{asphalt,asphalt,asphalt},{0.5f,0.5f},true});
		}
		if (transpose) for (auto &vertex : vertices) std::swap(vertex.position.x,vertex.position.y);
		for (size_t i = 0; i < vertices.size(); i += 3) {
			if (transpose) std::swap(vertices[i+1],vertices[i+2]);
			Vec3 normal = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
			for (size_t j = i; j < i+3; ++j) vertices[j].normal = normal;
		}
		result.parts[part] = std::move(vertices);
	}
	return result;
}
} // namespace Renderer3D
#endif
