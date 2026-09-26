/* SPDX-License-Identifier: GPL-2.0-only */
/** @file authored_geometry.cpp Compile explicit sculpting operations; map original pixel artwork. */

#include "../stdafx.h"
#include "authored_geometry.h"
#include "voxel_models.h"
#include "camera.hpp"
#include "gl_backend.hpp"
#include "material_chart.hpp"
#include "tree_geometry.hpp"
#include "../fileio_func.h"
#include "../3rdparty/nlohmann/json.hpp"
#include "../debug.h"
#include "../table/sprites.h"
#include "../table/tree_land.h"
#include "../engine_base.h"
#include "../vehicle_base.h"
#include "../newgrf_engine.h"
#include "../settings_type.h"
#include "../sprite.h"
#include "../spritecache.h"
#include <fstream>
#include <numbers>
#include <unordered_map>
#include <map>
#include <set>
#include <tuple>
#include <filesystem>
#include <memory>

namespace Renderer3D {
namespace {

using Json = nlohmann::json;

struct TreeBark {
	SpriteID sprite;
	TextureRegion crop;
	std::array<float,2> repeat;
	Rgb reference_colour;
};

struct TreeComponents {
	std::array<Scene,3> wood;
	std::array<std::array<Scene,3>,3> foliage; // Mature, withering, sparse; each has three LODs.
	std::array<TextureRegion,7> crops;
	std::array<float,7> growth{0.5f,0.66f,0.83f,1,1,1,1};
	std::array<float,2> foliage_repeat{3,4};
	bool retain_dead_foliage = false;
	bool foliage_charts = false;
	std::optional<TreeBark> bark;
};

struct AuthoredModel {
	std::vector<SpriteID> sprites;
	bool component_materials = false;
	Scene mesh;
	Scene dead;
	Scene site;
	std::array<Scene, 2> distant_mesh, distant_dead;
	std::optional<TreeComponents> tree;
	Vec3 low{1e9f, 1e9f, 1e9f}, high{-1e9f, -1e9f, -1e9f};
};

void Face(Scene &mesh, std::span<const Vec3> points, std::initializer_list<unsigned> face)
{
	std::vector<unsigned> indices(face);
	for (size_t i = 1; i + 1 < indices.size(); ++i) mesh.Triangle(points[indices[0]], points[indices[i]], points[indices[i + 1]], {});
}

void Box(Scene &mesh, float x, float y, float z, float w, float h, float d)
{
	const Vec3 p[] = {{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z},{x,y,z+d},{x+w,y,z+d},{x+w,y+h,z+d},{x,y+h,z+d}};
	Face(mesh,p,{3,2,1,0}); Face(mesh,p,{4,5,6,7}); Face(mesh,p,{0,1,5,4});
	Face(mesh,p,{1,2,6,5}); Face(mesh,p,{2,3,7,6}); Face(mesh,p,{3,0,4,7});
}

float Cross2(Vec3 a, Vec3 b, Vec3 c) { return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x); }

void Prism(Scene &mesh, const std::vector<Vec3> &polygon, float z, float height)
{
	std::vector<unsigned> remaining;
	for (unsigned i = 0; i < polygon.size(); ++i) remaining.push_back(i);
	while (remaining.size() >= 3) {
		bool found = false;
		for (size_t i = 0; i < remaining.size(); ++i) {
			unsigned ia = remaining[(i + remaining.size() - 1) % remaining.size()], ib = remaining[i], ic = remaining[(i+1) % remaining.size()];
			Vec3 a = polygon[ia], b = polygon[ib], c = polygon[ic];
			if (Cross2(a,b,c) <= 1e-6f) continue;
			bool contains = false;
			for (auto index : remaining) {
				if (index == ia || index == ib || index == ic) continue;
				Vec3 q = polygon[index];
				if (Cross2(a,b,q) > -1e-6f && Cross2(b,c,q) > -1e-6f && Cross2(c,a,q) > -1e-6f) { contains = true; break; }
			}
			if (contains) continue;
			a.z = b.z = c.z = z + height; mesh.Triangle(a,b,c,{});
			a.z = b.z = c.z = z; mesh.Triangle(c,b,a,{});
			remaining.erase(remaining.begin() + i); found = true; break;
		}
		if (!found) throw std::runtime_error("Invalid authored footprint polygon");
	}
	for (size_t i = 0; i < polygon.size(); ++i) {
		Vec3 a = polygon[i], b = polygon[(i+1)%polygon.size()]; a.z = b.z = z;
		Vec3 c = b, d = a; c.z = d.z = z + height;
		mesh.Quad(a,b,c,d,{});
	}
}

void Ellipsoid(Scene &mesh, float x, float y, float z, float rx, float ry, float height, bool dome, unsigned lod)
{
	const unsigned sides = lod == 0 ? 16 : lod == 1 ? 8 : 6, rings = lod == 0 ? 8 : 4;
	auto point = [&](unsigned ring, unsigned side) {
		float elevation = (dome ? 0.0f : -std::numbers::pi_v<float>/2) + ring * (dome ? std::numbers::pi_v<float>/2 : std::numbers::pi_v<float>) / rings;
		float angle = side * 2 * std::numbers::pi_v<float> / sides;
		return Vec3{x + rx*std::cos(elevation)*std::cos(angle), y + ry*std::cos(elevation)*std::sin(angle),
			z + (dome ? height*std::sin(elevation) : height*(std::sin(elevation)+1)/2)};
	};
	for (unsigned ring = 0; ring < rings; ++ring) for (unsigned side = 0; side < sides; ++side) {
		Vec3 a=point(ring,side), b=point(ring,(side+1)%sides), c=point(ring+1,(side+1)%sides), d=point(ring+1,side);
		if (dome || ring != 0) mesh.Triangle(a,b,c,{});
		if (ring != rings-1) mesh.Triangle(a,c,d,{});
	}
}

void BuildPart(Scene &mesh, const Json &part, unsigned lod = 0)
{
	std::string shape = part.at(0).get<std::string>();
	auto f = [&](size_t index) { return part.at(index).get<float>(); };
	if (shape == "sector") {
		std::vector<Vec3> profile;
		for (const auto &p : part.at(3)) profile.push_back({p.at(0),p.at(1),p.at(2)});
		TreeSector(mesh,{f(1),f(2),0},profile,f(4),f(5),part.at(6).get<unsigned>(),lod);
		return;
	}
	if (shape == "bough") {
		TreeBough(mesh,{f(1),f(2),f(3)},{f(4),f(5),f(6)},part.size() > 7 ? f(7) : 0,lod);
		return;
	}
	if (shape == "crown") {
		TreeCrown(mesh,{f(1),f(2),f(3)},{f(4),f(5),f(6)},part.size() > 7 ? f(7) : 0,lod);
		return;
	}
	if (shape == "branch") {
		std::vector<TreeBranchPoint> points;
		for (const auto &p : part.at(1)) points.push_back({{p.at(0),p.at(1),p.at(2)},p.at(3)});
		TreeBranch(mesh,points,lod);
		return;
	}
	if (shape == "material") {
		Scene component;
		for (const auto &child : part.at(2)) BuildPart(component,child,lod);
		const auto &material = part.at(1);
		if (material.contains("colour")) {
			const auto &colour = material.at("colour");
			for (auto &vertex : component.vertices) {
				vertex.colour = {colour.at(0),colour.at(1),colour.at(2)};
				vertex.texture = {-1,-1,-4}; // Explicit solid component within a textured assembly.
				if (material.value("lit",true)) vertex.surface = static_cast<SurfaceMode>(SURFACE_SHADED);
			}
		} else {
			MaterialChart chart;
			const char *names[] = {"end","side","top"};
			for (unsigned face = 0; face < 3; ++face) {
				const auto &crop = material.contains(names[face]) ? material.at(names[face]) : material.at("all");
				chart.faces[face] = {crop.at(0),crop.at(1),crop.at(2),crop.at(3)};
			}
			if (material.contains("repeat")) chart.repeat = material.at("repeat").get<std::array<float,2>>();
			chart.lit = material.value("lit",true);
			component.vertices = ApplyMaterialChart(component.vertices,chart);
		}
		mesh.vertices.insert(mesh.vertices.end(),component.vertices.begin(),component.vertices.end());
		return;
	}
	if (shape == "lathe") {
		Json sections = part.at(3);
		float vertical_repeat = part.size() > 5 ? part[5].value("vertical_repeat",0.0f) : 0;
		if (vertical_repeat > 0) {
			if (vertical_repeat < 0.25f) throw std::runtime_error("Lathe material repeat is too small");
			Json divided = Json::array({sections.front()});
			for (size_t ring = 1; ring < sections.size(); ++ring) {
				float low = sections[ring-1][0], high = sections[ring][0];
				for (float z = (std::floor(low/vertical_repeat)+1)*vertical_repeat; z < high-0.0001f; z += vertical_repeat) {
					float t = (z-low)/(high-low);
					divided.push_back({z,std::lerp(sections[ring-1][1].get<float>(),sections[ring][1].get<float>(),t),
						std::lerp(sections[ring-1][2].get<float>(),sections[ring][2].get<float>(),t)});
				}
				divided.push_back(sections[ring]);
			}
			sections = std::move(divided);
		}
		unsigned authored_sides = part.size() > 5 ? part[5].value("sides",24U) : 24;
		if (authored_sides < 3 || authored_sides > 128) throw std::runtime_error("Invalid authored lathe side count");
		unsigned sides = lod == 0 ? authored_sides : std::min(authored_sides,lod == 1 ? 12U : 8U);
		float angle_offset = (part.size() > 5 ? part[5].value("angle",0.0f) : 0.0f)*std::numbers::pi_v<float>/180;
		float thickness = f(4);
		auto material = [&](size_t first, bool interior, bool rim = false, float repeat_origin = 0) {
			for (size_t i = first; i < mesh.vertices.size(); ++i) {
				auto &vertex = mesh.vertices[i];
				Vec3 p = vertex.position;
				if (part.size() > 5) {
					/* Artist-selected source rectangles separate wall, rim and interior.
					 * Arc-length wrapping avoids stretching projected edge pixels. */
					const auto &crop = part[5].at(rim ? "rim" : interior ? "interior" : "wall");
					float phase = std::atan2(p.y - f(2), p.x - f(1)) / std::numbers::pi_v<float> + 0.25f;
					float u = std::abs(std::remainder(phase, 2.0f));
					float v = (p.z - sections.front()[0].get<float>()) / (sections.back()[0].get<float>() - sections.front()[0].get<float>());
					if (vertical_repeat > 0 && !rim) v = std::clamp((p.z-repeat_origin)/vertical_repeat,0.0f,1.0f);
					vertex.texture = {std::lerp(crop[0].get<float>(), crop[2].get<float>(), u), std::lerp(crop[3].get<float>(), crop[1].get<float>(), v), -3};
					if (part[5].value("lit",false)) vertex.surface = static_cast<SurfaceMode>(SURFACE_SHADED);
					continue;
				}
				float along = std::abs(p.x - f(1) + p.y - f(2)), side = p.y - f(2) - p.x + f(1);
				if (interior) { along *= 0.25f; side *= 0.35f; p.z = sections.back()[0].get<float>() - thickness; }
				/* Fold the rear half onto the reference-facing half continuously.
				 * Per-axis normal mirroring introduced a diagonal seam on lathed walls. */
				vertex.texture = {f(1) + (along - side) * 0.5f, f(2) + (along + side) * 0.5f, p.z};
			}
		};
		auto point = [&](size_t ring, unsigned side, bool inner) {
			float angle = angle_offset + side * 2 * std::numbers::pi_v<float> / sides;
			float inset = inner ? thickness : 0;
			return Vec3{f(1) + (sections[ring][1].get<float>() - inset) * std::cos(angle), f(2) + (sections[ring][2].get<float>() - inset) * std::sin(angle), sections[ring][0]};
		};
		for (unsigned side = 0; side < sides; ++side) {
			unsigned next = (side + 1) % sides;
			for (size_t ring = 0; ring + 1 < sections.size(); ++ring) {
				float repeat_origin = vertical_repeat > 0 ? std::floor((sections[ring][0].get<float>()+0.0001f)/vertical_repeat)*vertical_repeat : 0;
				size_t first = mesh.vertices.size();
				mesh.Quad(point(ring, side, false), point(ring, next, false), point(ring + 1, next, false), point(ring + 1, side, false), {});
				material(first, false, false, repeat_origin);
				first = mesh.vertices.size();
				mesh.Quad(point(ring, next, true), point(ring, side, true), point(ring + 1, side, true), point(ring + 1, next, true), {});
				material(first, true, false, repeat_origin);
			}
			size_t top = sections.size() - 1;
			size_t first = mesh.vertices.size();
			mesh.Quad(point(top, side, false), point(top, next, false), point(top, next, true), point(top, side, true), {});
			material(first, false, true);
		}
		return;
	}
	if (shape == "transform") {
		Scene local;
		for (const auto &child : part.at(4)) BuildPart(local, child, lod);
		Vec3 translation{part[1][0], part[1][1], part[1][2]}, rotation{part[2][0], part[2][1], part[2][2]}, scale{part[3][0], part[3][1], part[3][2]};
		auto rotate = [&](Vec3 p) {
			for (unsigned axis = 0; axis < 3; ++axis) {
				float angle = (axis == 0 ? rotation.x : axis == 1 ? rotation.y : rotation.z) * std::numbers::pi_v<float> / 180;
				float c = std::cos(angle), s = std::sin(angle);
				if (axis == 0) p = {p.x, p.y * c - p.z * s, p.y * s + p.z * c};
				if (axis == 1) p = {p.x * c + p.z * s, p.y, -p.x * s + p.z * c};
				if (axis == 2) p = {p.x * c - p.y * s, p.x * s + p.y * c, p.z};
			}
			return p;
		};
		for (Vertex vertex : local.vertices) {
			vertex.position = rotate({vertex.position.x * scale.x, vertex.position.y * scale.y, vertex.position.z * scale.z}) + translation;
			vertex.normal = Normalize(rotate({vertex.normal.x / scale.x, vertex.normal.y / scale.y, vertex.normal.z / scale.z}));
			if (vertex.texture.z >= 0) vertex.texture = rotate({vertex.texture.x * scale.x, vertex.texture.y * scale.y, vertex.texture.z * scale.z}) + translation;
			mesh.vertices.push_back(vertex);
		}
		return;
	}
	if (shape == "sweep") {
		const auto &sections = part.at(1);
		unsigned sides = lod == 0 ? 12 : 8;
		auto point = [&](size_t section, unsigned side) {
			float angle = side * 2 * std::numbers::pi_v<float> / sides;
			return Vec3{sections[section][0], sections[section][1].get<float>() * std::cos(angle), sections[section][2].get<float>() + sections[section][3].get<float>() * std::sin(angle)};
		};
		for (size_t section = 0; section + 1 < sections.size(); ++section) for (unsigned side = 0; side < sides; ++side) {
			unsigned next = (side + 1) % sides;
			mesh.Quad(point(section, side), point(section, next), point(section + 1, next), point(section + 1, side), {});
		}
		for (unsigned side = 0; side < sides; ++side) {
			unsigned next = (side + 1) % sides;
			mesh.Triangle({sections[0][0], 0, sections[0][2]}, point(0, next), point(0, side), {});
			size_t last = sections.size() - 1;
			mesh.Triangle({sections[last][0], 0, sections[last][2]}, point(last, side), point(last, next), {});
		}
		return;
	}
	if (shape == "box") { Box(mesh,f(1),f(2),f(3),f(4),f(5),f(6)); return; }
	if (shape == "prism") {
		std::vector<Vec3> polygon;
		for (const auto &p : part.at(3)) polygon.push_back({p.at(0).get<float>(),p.at(1).get<float>(),0});
		Prism(mesh,polygon,f(1),f(2)); return;
	}
	if (shape == "ellipsoid" || shape == "dome") { Ellipsoid(mesh,f(1),f(2),f(3),f(4),f(5),f(6),shape=="dome",lod); return; }
	if (shape == "round" || shape == "cone" || shape == "inverse_cone") {
		unsigned sides = static_cast<unsigned>(f(7));
		if (lod != 0) sides = std::min(sides, lod == 1 ? 8U : 6U);
		std::vector<Vec3> polygon;
		for (unsigned i=0;i<sides;++i) {
			float angle=i*2*std::numbers::pi_v<float>/sides;
			polygon.push_back({f(1)+f(4)*std::cos(angle),f(2)+f(5)*std::sin(angle),0});
		}
		if (shape=="round") { Prism(mesh,polygon,f(3),f(6)); return; }
		Vec3 tip{f(1),f(2),shape=="inverse_cone" ? f(3) : f(3)+f(6)};
		for (unsigned i=0;i<sides;++i) {
			Vec3 a=polygon[i], b=polygon[(i+1)%sides]; a.z=b.z=shape=="inverse_cone" ? f(3)+f(6) : f(3);
			if (shape=="inverse_cone") mesh.Triangle(b,a,tip,{}); else mesh.Triangle(a,b,tip,{});
		}
		return;
	}
	if (shape == "frond" || shape == "leaf" || shape == "palm_frond") {
		Vec3 root{f(1),f(2),f(3)}, tip{f(4),f(5),f(6)};
		if (shape == "palm_frond") TreePalmFrond(mesh,root,tip,f(7),lod);
		else TreeLeaf(mesh,root,tip,f(7),part.size() > 8 ? f(8) : 2.5f,part.size() > 9 ? f(9) : 0.18f,lod);
		return;
	}
	if (shape == "tube") {
		std::vector<Vec3> path;
		for (const auto &p : part.at(2)) path.push_back({p.at(0).get<float>(),p.at(1).get<float>(),p.at(2).get<float>()});
		for (size_t segment=0;segment+1<path.size();++segment) {
			Vec3 along=Normalize(path[segment+1]-path[segment]);
			Vec3 right=Normalize(std::abs(along.z)<0.9f ? Vec3{-along.y,along.x,0} : Vec3{1,0,0});
			Vec3 up=Normal({},right,along);
			unsigned sides = lod == 0 ? 10 : lod == 1 ? 6 : 4;
			for (unsigned i=0;i<sides;++i) {
				float a=i*2*std::numbers::pi_v<float>/sides, b=(i+1)*2*std::numbers::pi_v<float>/sides;
				Vec3 first=(right*std::cos(a)+up*std::sin(a))*f(1), next=(right*std::cos(b)+up*std::sin(b))*f(1);
				mesh.Quad(path[segment]+first,path[segment]+next,path[segment+1]+next,path[segment+1]+first,{});
			}
		}
		return;
	}
	float x=f(1),y=f(2),z=f(3),w=f(4),h=f(5),d=f(6);
	if (shape == "gable") {
		Vec3 p[]={{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z},{x+w/2,y,z+d},{x+w/2,y+h,z+d}};
		Face(mesh,p,{0,1,4}); Face(mesh,p,{2,3,5}); Face(mesh,p,{0,4,5,3}); Face(mesh,p,{1,2,5,4}); return;
	}
	if (shape == "hip") {
		float inset=std::min({f(7),w/2,h/2});
		Vec3 p[]={{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z},
			{x+inset,y+inset,z+d},{x+w-inset,y+inset,z+d},{x+w-inset,y+h-inset,z+d},{x+inset,y+h-inset,z+d}};
		Face(mesh,p,{0,1,5,4}); Face(mesh,p,{1,2,6,5}); Face(mesh,p,{2,3,7,6}); Face(mesh,p,{3,0,4,7});
		if (w > 2 * inset && h > 2 * inset) Face(mesh, p, {4, 5, 6, 7});
		return;
	}
	if (shape == "roofring") {
		float ridge=f(7), inside=f(8);
		Vec3 outer[]={{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z}};
		Vec3 middle[]={{x+ridge,y+ridge,z+d},{x+w-ridge,y+ridge,z+d},{x+w-ridge,y+h-ridge,z+d},{x+ridge,y+h-ridge,z+d}};
		Vec3 inner[]={{x+inside,y+inside,z},{x+w-inside,y+inside,z},{x+w-inside,y+h-inside,z},{x+inside,y+h-inside,z}};
		for (unsigned i=0;i<4;++i) {
			unsigned j=(i+1)%4;
			mesh.Quad(outer[i],outer[j],middle[j],middle[i],{});
			mesh.Quad(middle[i],middle[j],inner[j],inner[i],{});
		}
		return;
	}
	if (shape == "wedge") {
		Vec3 p[]={{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z},{x,y,z+d},{x+w,y,z+d}};
		Face(mesh,p,{0,1,5,4}); Face(mesh,p,{1,2,5}); Face(mesh,p,{0,4,3}); Face(mesh,p,{4,5,2,3}); return;
	}
	throw std::runtime_error("Unknown authored shape " + shape);
}

std::unordered_map<unsigned,AuthoredModel> LoadModels(const std::string &pack, bool trees=false)
{
		std::unordered_map<unsigned,AuthoredModel> result;
		std::string filename=FioFindFullPath(BASESET_DIR,pack);
		std::ifstream stream(filename);
		if (!stream) throw std::runtime_error("Missing authored asset pack " + pack);
		Json data=Json::parse(stream);
		if (data.at("format")!=2) throw std::runtime_error("Unsupported authored asset format");
		auto bark_material = [&](const Json &name) {
			const auto &material = data.at("bark_materials").at(name.get<std::string>());
			const auto &crop = material.at("crop"), &colour = material.at("reference_colour");
			return TreeBark{material.at("sprite"),{crop[0],crop[1],crop[2],crop[3]},
				material.at("repeat").get<std::array<float,2>>(),{colour[0],colour[1],colour[2]}};
		};
		auto wood_colour = [](const TreeComponents &tree, const Json &bark) {
			Rgb reference = tree.bark ? tree.bark->reference_colour : Rgb{};
			return Rgb{bark[0].get<float>()/reference.r,bark[1].get<float>()/reference.g,bark[2].get<float>()/reference.b};
		};
		std::map<std::string,TreeBark> bark_bindings;
		if (data.contains("bark_materials")) for (const auto &[name,material] : data.at("bark_materials").items()) {
			for (unsigned identifier : material.at("models")) {
				if (!bark_bindings.emplace(std::to_string(identifier),bark_material(name)).second) throw std::runtime_error("Duplicate tree bark binding");
			}
		}
		for (const auto &[key,value] : data.at("models").items()) {
			AuthoredModel model;
			model.sprites = value.value("sprites", std::vector<SpriteID>{});
			if (trees && value.contains("tree_materials")) {
				model.tree.emplace();
				auto &tree = *model.tree;
				const auto &materials = value.at("tree_materials"), &crop = materials.at("foliage_crop"), &bark = materials.at("wood_colour");
				tree.crops.fill({crop[0],crop[1],crop[2],crop[3]});
				if (materials.contains("foliage_crop_by_stage")) for (const auto &[stage,region] : materials.at("foliage_crop_by_stage").items()) {
					tree.crops.at(std::stoul(stage)) = {region[0],region[1],region[2],region[3]};
				}
				tree.growth = materials.value("growth",tree.growth);
				tree.retain_dead_foliage = materials.value("retain_dead_foliage",false);
				tree.foliage_charts = materials.value("foliage_charts",false);
				if (materials.contains("bark")) tree.bark = bark_material(materials.at("bark"));
				else if (auto binding = bark_bindings.find(key); binding != bark_bindings.end()) tree.bark = binding->second;
				auto repeat = materials.value("repeat",std::array<float,2>{3,4});
				tree.foliage_repeat = repeat;
				auto scale = materials.value("scale",std::array<float,2>{1,1});
				if (repeat[0] <= 0 || repeat[1] <= 0) throw std::runtime_error("Invalid foliage material repeat");
				if (scale[0] <= 0 || scale[1] <= 0) throw std::runtime_error("Invalid authored tree scale");
				for (const auto &group : value.at("parts")) {
					std::string role = group.at(0);
					if (role != "wood" && role != "foliage") throw std::runtime_error("A component tree needs explicit wood/foliage groups");
					for (const auto &part : group.at(1)) for (unsigned lod = 0; lod < 3; ++lod) {
						Scene component;
						BuildPart(component,part,lod);
						for (auto &v : component.vertices) {
							v.position = {v.position.x*scale[0],v.position.y*scale[0],v.position.z*scale[1]};
							v.normal = Normalize({v.normal.x/scale[0],v.normal.y/scale[0],v.normal.z/scale[1]});
						}
						if (role == "wood") {
							for (auto &v : component.vertices) {
								v.colour = wood_colour(tree,bark);
								if (tree.bark) {
									const auto &repeat = tree.bark->repeat;
									v.texture = v.texture.z == -5 ? Vec3{v.texture.x*scale[0]/repeat[0],-v.texture.y*scale[1]/repeat[1],-1} : Vec3{v.position.x/repeat[0],v.position.y/repeat[1],-1};
								} else v.texture = {-1,-1,-4};
							}
							auto &out = tree.wood[lod].vertices;
							out.insert(out.end(),component.vertices.begin(),component.vertices.end());
						} else {
							Vec3 low{1e9f,1e9f,1e9f}, high{-1e9f,-1e9f,-1e9f};
							for (const auto &v : component.vertices) {
								low = {std::min(low.x,v.position.x),std::min(low.y,v.position.y),std::min(low.z,v.position.z)};
								high = {std::max(high.x,v.position.x),std::max(high.y,v.position.y),std::max(high.z,v.position.z)};
							}
							Vec3 centre = (low+high)*0.5f;
							for (unsigned age = 0; age < 3; ++age) {
								float density = tree.foliage_charts || age == 0 ? 1 : age == 1 ? 0.96f : 0.90f;
								auto &out = tree.foliage[age][lod].vertices;
								for (size_t i = 0; i < component.vertices.size(); i += 3) {
									Vec3 n = component.vertices[i].normal;
									unsigned axis = std::abs(n.z/Camera::WORLD_Z_SCALE) > std::max(std::abs(n.x),std::abs(n.y)) ? 2 : std::abs(n.x) > std::abs(n.y) ? 0 : 1;
									for (size_t j = i; j < i+3; ++j) {
										Vertex v = component.vertices[j];
										Vec3 p = v.position;
										/* Local physical units avoid both polar pinching and the
										 * height-axis compression of projected sprite materials. */
										if (!tree.foliage_charts) v.texture = axis == 2 ? Vec3{p.x/repeat[0],-p.y/repeat[1],-1} :
											Vec3{(axis == 0 ? p.y : p.x)/repeat[0],-p.z*Camera::WORLD_Z_SCALE/repeat[1],-1};
										v.position = centre+(p-centre)*density;
										out.push_back(v);
									}
								}
							}
						}
					}
				}
				/* Low-detail envelopes have different extrema; every LOD must be inside
				 * the common culling box so switching detail cannot clip a branch. */
				for (unsigned lod = 0; lod < 3; ++lod) for (const Scene *part : {&tree.wood[lod],&tree.foliage[0][lod]}) for (const auto &v : part->vertices) {
					model.low = {std::min(model.low.x,v.position.x),std::min(model.low.y,v.position.y),std::min(model.low.z,v.position.z)};
					model.high = {std::max(model.high.x,v.position.x),std::max(model.high.y,v.position.y),std::max(model.high.z,v.position.z)};
				}
				result.emplace(static_cast<unsigned>(std::stoul(key)),std::move(model));
				continue;
			}
			for (const auto &part : value.at("parts")) {
				BuildPart(model.mesh, part);
				for (unsigned lod = 1; lod <= 2; ++lod) BuildPart(model.distant_mesh[lod - 1], part, lod);
			}
			for (const Vertex &v : model.mesh.vertices) {
				model.component_materials |= (static_cast<uint32_t>(v.surface) & SURFACE_SHADED) != 0 || v.texture.z == -4;
				model.low={std::min(model.low.x,v.position.x),std::min(model.low.y,v.position.y),std::min(model.low.z,v.position.z)};
				model.high={std::max(model.high.x,v.position.x),std::max(model.high.y,v.position.y),std::max(model.high.z,v.position.z)};
			}
			if (trees && std::stoul(key)<1947) {
				auto dead_part = [&](const Json &part) {
					BuildPart(model.dead, part);
					for (unsigned lod = 1; lod <= 2; ++lod) BuildPart(model.distant_dead[lod - 1], part, lod);
				};
				for (const auto &part : value.at("parts")) if (part[0]=="round" || part[0]=="tube") dead_part(part);
				/* Shared hand-authored branch rig, scaled to each authored crown. */
				float h=model.high.z, r=std::max(model.high.x-model.low.x,model.high.y-model.low.y)*0.35f;
				for (const auto &path : {std::array<Vec3,3>{{{0,0,h*0.35f},{r*0.6f,0,h*0.55f},{r,0,h*0.66f}}},
					std::array<Vec3,3>{{{0,0,h*0.48f},{-r*0.6f,0,h*0.67f},{-r,0,h*0.8f}}},
					std::array<Vec3,3>{{{0,0,h*0.6f},{0,r*0.5f,h*0.76f},{0,r,h*0.86f}}},
					std::array<Vec3,3>{{{0,0,h*0.4f},{0,-r*0.6f,h*0.58f},{0,-r,h*0.7f}}}}) {
					Json points=Json::array(); for (Vec3 p:path) points.push_back({p.x,p.y,p.z});
					dead_part(Json::array({"tube",0.22f,points}));
				}
			}
			if (!model.mesh.vertices.empty()) Box(model.site, model.low.x, model.low.y, 0, model.high.x - model.low.x, model.high.y - model.low.y, 0.6f);
			result.emplace(static_cast<unsigned>(std::stoul(key)),std::move(model));
		}
		for (const auto &[key,value] : data.at("aliases").items()) {
			AuthoredModel model = result.at(value.is_object() ? value.at("model").get<unsigned>() : value.get<unsigned>());
			if (value.is_object() && model.tree && value.contains("bark")) model.tree->bark = bark_material(value.at("bark"));
			else if (model.tree) if (auto binding = bark_bindings.find(key); binding != bark_bindings.end()) model.tree->bark = binding->second;
			if (value.is_object() && model.tree && value.contains("wood_colour")) {
				const auto &colour = value.at("wood_colour");
				for (auto &lod : model.tree->wood) for (auto &v : lod.vertices) v.colour = wood_colour(*model.tree,colour);
			}
			result.emplace(static_cast<unsigned>(std::stoul(key)),std::move(model));
		}
		Debug(driver,1,"OpenTT3D: loaded {} profiles from {}",result.size(),pack);
		return result;

}

const std::unordered_map<unsigned,AuthoredModel> &HouseModels()
{
	static const auto models=LoadModels("opentt3d-houses.json");
	return models;
}

const std::unordered_map<unsigned,AuthoredModel> &TreeModels()
{
	static const auto models=LoadModels("opentt3d-trees.json",true);
	return models;
}

const std::unordered_map<unsigned, AuthoredModel> &IndustryModels()
{
	static const auto models = LoadModels("opentt3d-industries.json");
	return models;
}

static constexpr unsigned VEHICLE_VIEWS[] = {5, 3, 1, 7};

Vec3 VehicleView(Vec3 p, unsigned direction)
{
	float angle = (5.0f - direction) * std::numbers::pi_v<float> / 4;
	float c = std::cos(angle), s = std::sin(angle);
	return {p.x * c - p.y * s, p.x * s + p.y * c, p.z};
}

struct VehicleStateModel {
	std::array<std::array<std::vector<Vertex>, 4>, 3> faces;
	std::array<std::array<float, 4>, 4> projection{};
	Vec3 low{1e9f, 1e9f, 1e9f}, high{-1e9f, -1e9f, -1e9f};
};

struct VehicleModel {
	std::string name;
	std::array<std::array<SpriteID, 8>, 2> sprites;
	std::shared_ptr<const std::array<VehicleStateModel, 2>> states;
};

const std::map<unsigned, VehicleModel> &VehicleModels()
{
	static const auto models = [] {
		std::ifstream stream(FioFindFullPath(BASESET_DIR, "opentt3d-vehicles.json"));
		if (!stream) throw std::runtime_error("Missing authored vehicle catalogue");
		Json data = Json::parse(stream);
		if (data.at("format") != 3) throw std::runtime_error("Unsupported vehicle asset format");
		std::map<unsigned, VehicleModel> result;
		std::map<std::string, std::shared_ptr<const std::array<VehicleStateModel, 2>>> assemblies;
		for (const auto &[id, value] : data.at("models").items()) {
			VehicleModel model;
			model.name = value.at("name");
			model.sprites[0] = value.at("sprites").get<std::array<SpriteID, 8>>();
			model.sprites[1] = value.at("loaded_sprites").get<std::array<SpriteID, 8>>();
			std::string assembly = value.at("assembly");
			if (auto shared = assemblies.find(assembly); shared != assemblies.end()) {
				model.states = shared->second;
				result.emplace(static_cast<unsigned>(std::stoul(id)), std::move(model));
				continue;
			}
			auto states = std::make_shared<std::array<VehicleStateModel, 2>>();
			for (unsigned loaded = 0; loaded < 2; ++loaded) {
				auto &state = (*states)[loaded];
				for (auto &bounds : state.projection) bounds = {1e9f, 1e9f, -1e9f, -1e9f};
				for (unsigned lod = 0; lod < 3; ++lod) {
					Scene geometry;
					for (const auto &part : value.at("parts")) BuildPart(geometry, part, lod);
					if (loaded != 0) for (const auto &part : value.at("loaded_parts")) BuildPart(geometry, part, lod);
					if (lod == 0) for (const Vertex &vertex : geometry.vertices) {
						Vec3 p = vertex.position;
						state.low = {std::min(state.low.x, p.x), std::min(state.low.y, p.y), std::min(state.low.z, p.z)};
						state.high = {std::max(state.high.x, p.x), std::max(state.high.y, p.y), std::max(state.high.z, p.z)};
						for (unsigned view = 0; view < 4; ++view) {
							Vec3 q = VehicleView(p, VEHICLE_VIEWS[view]);
							auto &bounds = state.projection[view];
							float u = 2 * (q.y - q.x), v = q.x + q.y - q.z;
							bounds = {std::min(bounds[0], u), std::min(bounds[1], v), std::max(bounds[2], u), std::max(bounds[3], v)};
						}
					}
					for (size_t first = 0; first < geometry.vertices.size(); first += 3) {
						unsigned selected = 0;
						float best = -1e9f;
						for (unsigned view = 0; view < 4; ++view) {
							float facing = Dot(VehicleView(geometry.vertices[first].normal, VEHICLE_VIEWS[view]), {1, 1, 2});
							if (facing > best + 0.0001f) { best = facing; selected = view; }
						}
						auto &face = state.faces[lod][selected];
						face.insert(face.end(), geometry.vertices.begin() + first, geometry.vertices.begin() + first + 3);
					}
				}
			}
			model.states = states;
			assemblies.emplace(assembly, states);
			result.emplace(static_cast<unsigned>(std::stoul(id)), std::move(model));
		}
		Debug(driver, 1, "OpenTT3D: loaded {} directional vehicle assemblies", result.size());
		return result;
	}();
	return models;
}

std::array<SpriteID, 8> EngineReferenceSprites(unsigned id, bool loaded)
{
	const Engine *engine = Engine::GetIfValid(EngineID{static_cast<uint16_t>(id)});
	if (engine == nullptr) return VehicleModels().at(id).sprites[loaded];
	unsigned image = 0;
	std::string kind;
	switch (engine->type) {
		case VEH_TRAIN: image = engine->VehInfo<RailVehicleInfo>().image_index; kind = "train"; break;
		case VEH_ROAD: image = engine->VehInfo<RoadVehicleInfo>().image_index; kind = "road"; break;
		case VEH_SHIP: image = engine->VehInfo<ShipVehicleInfo>().image_index; kind = "ship"; break;
		case VEH_AIRCRAFT: image = engine->VehInfo<AircraftVehicleInfo>().image_index; kind = "aircraft"; break;
		default: return {};
	}
	static const Json sets = [] {
		std::ifstream stream(FioFindFullPath(BASESET_DIR, "opentt3d-vehicles.json"));
		return Json::parse(stream).at("sprite_sets");
	}();
	if (sets.at(kind).contains(std::to_string(image))) return sets.at(kind).at(std::to_string(image)).at(loaded ? "loaded_sprites" : "sprites").get<std::array<SpriteID, 8>>();
	std::array<SpriteID, 8> result = VehicleModels().at(id).sprites[loaded];
	for (unsigned direction = 0; direction < 8; ++direction) {
		VehicleSpriteSeq sequence;
		GetCustomVehicleIcon(engine->index, static_cast<Direction>(direction), EIT_PURCHASE, &sequence);
		if (sequence.IsValid()) result[direction] = sequence.seq[0].sprite;
	}
	return result;
}

} // namespace

static bool DrawRegisteredModel(Scene &scene, const AuthoredModel &model, unsigned stage, const SpriteTexture &texture, Vec3 origin, Vec3 sprite_origin, float opacity, float pixel_scale)
{
	if (model.mesh.vertices.empty() || texture.ink_width==0 || texture.ink_height==0) return true;
	const auto &vertices=stage==0 ? model.site.vertices : stage==6 && !model.dead.vertices.empty() ? model.dead.vertices : model.mesh.vertices;
	/* Register the authored mesh to the actual sprite's pixel framing. OpenGFX2
	 * often draws a smaller footprint than the historical sprite-sort bounding
	 * box. These are scale/origin adjustments; topology remains explicitly authored. */
	struct RegistrationKey {
		const AuthoredModel *model;
		unsigned stage;
		int width,height;
		bool operator==(const RegistrationKey &) const = default;
	};
	struct RegistrationHash {
		size_t operator()(const RegistrationKey &key) const {
			return std::hash<const AuthoredModel *>{}(key.model) ^ (static_cast<size_t>(key.stage)<<2) ^ (static_cast<size_t>(key.width)<<8) ^ (static_cast<size_t>(key.height)<<24);
		}
	};
	struct Registration {
		Vec3 low, high;
		float xy_scale, z_scale, top, bottom, center_u;
	};
	static std::unordered_map<RegistrationKey,Registration,RegistrationHash> registrations;
	RegistrationKey key{&model,stage,texture.ink_width,texture.ink_height};
	auto registration=registrations.find(key);
	if (registration==registrations.end()) {
		Vec3 low_bound{1e9f, 1e9f, 1e9f}, high_bound{-1e9f, -1e9f, -1e9f};
		float left = 1e9f, right = -1e9f;
		for (const Vertex &vertex : vertices) {
			Vec3 p = vertex.position;
			low_bound = {std::min(low_bound.x, p.x), std::min(low_bound.y, p.y), std::min(low_bound.z, p.z)};
			high_bound = {std::max(high_bound.x, p.x), std::max(high_bound.y, p.y), std::max(high_bound.z, p.z)};
			left = std::min(left, 2 * (p.y - p.x));
			right = std::max(right, 2 * (p.y - p.x));
		}
		if (right - left < 1e-6f) return false;
		/* A rounded crown does not reach the corners of its bounding box. Use
		 * the authored vertices' actual projected extent, and the selected state's
		 * bounds (especially for bare branches), rather than a mature-model box. */
		const float xy_scale = texture.ink_width / (static_cast<float>(ZOOM_BASE) * (right - left));
		Vec3 center = (low_bound + high_bound) * 0.5f;
		auto vertical_bounds = [&](float z_scale) {
			std::array<float, 2> range{1e9f, -1e9f};
			for (const Vertex &v : vertices) {
				float y = xy_scale * (v.position.x - center.x + v.position.y - center.y) - z_scale * v.position.z;
				range[0] = std::min(range[0], y);
				range[1] = std::max(range[1], y);
			}
			return range;
		};
		float low=0.001f, high=8;
		float target_height=texture.ink_height/static_cast<float>(ZOOM_BASE);
		for (int i=0;i<24;++i) {
			float mid=(low+high)/2;
			auto range=vertical_bounds(mid);
			if (range[1] - range[0] < target_height) low = mid; else high = mid;
		}
		float z_scale=(low+high)/2;
		auto range=vertical_bounds(z_scale);
		float center_u = ((left + right) * 0.5f - 2 * (center.y - center.x)) * xy_scale;
		registration = registrations.emplace(key, Registration{low_bound, high_bound, xy_scale, z_scale, range[0], range[1], center_u}).first;
	}
	const Registration &fit = registration->second;
	float xy_scale = fit.xy_scale, z_scale = fit.z_scale;
	float center_x = (fit.low.x + fit.high.x) * 0.5f, center_y = (fit.low.y + fit.high.y) * 0.5f;
	float sx = (texture.x_offset + texture.ink_left + texture.ink_width * 0.5f) / ZOOM_BASE - fit.center_u;
	float sy = (texture.y_offset + texture.ink_top + texture.ink_height * 0.5f) / ZOOM_BASE - (fit.top + fit.bottom) / 2 + origin.z - sprite_origin.z;
	origin.x=sprite_origin.x+sy/2-sx/4;
	origin.y=sprite_origin.y+sy/2+sx/4;
	Vec3 low = origin + Vec3{(fit.low.x - center_x) * xy_scale, (fit.low.y - center_y) * xy_scale, fit.low.z * z_scale};
	Vec3 high = origin + Vec3{(fit.high.x - center_x) * xy_scale, (fit.high.y - center_y) * xy_scale, fit.high.z * z_scale};
	if (scene.visibility.has_value() && !scene.visibility->Intersects(low - Vec3{1, 1, 1}, high + Vec3{1, 1, 1})) return true;
	Vec3 relative = origin - sprite_origin;
	Vec3 uv = texture.LocalUV(2 * (relative.y - relative.x) * ZOOM_BASE - texture.x_offset,
		(relative.x + relative.y - relative.z) * ZOOM_BASE - texture.y_offset);
	InstanceData instance;
	instance.origin_opacity = {origin.x, origin.y, origin.z, opacity};
	instance.scale_center = {xy_scale, z_scale, center_x, center_y};
	instance.mirror_layer_heading = {fit.low.x + fit.high.x, fit.low.y + fit.high.y, 0, 0};
	instance.uv_transform = {uv.x, uv.y, ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE), uv.z};
	instance.region = texture.Region();
	instance.identity[1] = static_cast<float>(texture.opaque_surface ? SurfaceMode::Opaque : SurfaceMode::Cutout);
	instance.identity[3] = 2;
	instance.SetSpriteLocalUVBias();
	/* Subpixel curve error needs fewer facets, not a replacement sprite plane.
	 * Keep the full-detail registration so LOD changes never move/resize objects. */
	float diameter = std::max(texture.ink_width, texture.ink_height) * pixel_scale / ZOOM_BASE;
	unsigned lod = diameter < 6 ? 2 : diameter < 12 ? 1 : 0;
	const auto *mesh = &vertices;
	if (lod != 0 && stage != 0) mesh = &(stage == 6 && !model.dead.vertices.empty() ? model.distant_dead[lod - 1] : model.distant_mesh[lod - 1]).vertices;
	scene.instances.push_back({mesh, instance});
	return true;
}

bool DrawAuthoredHouse(Scene &scene, unsigned house, unsigned stage, const SpriteTexture &texture, Vec3 origin, Vec3 sprite_origin, float opacity, float pixel_scale, unsigned variant)
{
	if (auto state = VoxelHouseState(house,stage,variant); state && DrawVoxelAsset(scene,"houses",house,*state,origin,texture.palette,opacity)) return true;
	const auto &models=HouseModels();
	auto found=models.find(house);
	return found!=models.end() && DrawRegisteredModel(scene,found->second,stage,texture,origin,sprite_origin,opacity,pixel_scale);
}

bool TreeHasComponentMaterials(SpriteID image)
{
	image &= SPRITE_MASK;
	if (image < 1576 || image > 2009) return false;
	unsigned base = image-(image-1576)%7;
	const auto &models = TreeModels();
	auto found = models.find(base);
	return found != models.end() && found->second.tree.has_value();
}

static TextureRegion TreeMaterialRegion(const SpriteTexture &texture, const TextureRegion &crop)
{
	int left = std::clamp(static_cast<int>(std::floor(crop.left*texture.width)),0,texture.width-1);
	int top = std::clamp(static_cast<int>(std::floor(crop.top*texture.height)),0,texture.height-1);
	int right = std::clamp(static_cast<int>(std::ceil(crop.right*texture.width)),left+1,texture.width);
	int bottom = std::clamp(static_cast<int>(std::ceil(crop.bottom*texture.height)),top+1,texture.height);
	return {(texture.x+left)/static_cast<float>(ATLAS_SIZE),(texture.y+top)/static_cast<float>(ATLAS_SIZE),
		(texture.x+right)/static_cast<float>(ATLAS_SIZE),(texture.y+bottom)/static_cast<float>(ATLAS_SIZE)};
}

bool DrawAuthoredTree(Scene &scene, SpriteID image, const SpriteTexture &texture, Vec3 origin, float opacity, float pixel_scale)
{
	image &= SPRITE_MASK;
	if (image<1576 || image>2009) return false;
	unsigned stage=(image-1576)%7, base=image-stage;
	if (UseVoxelTrees() && HasVoxelTree(image)) return DrawVoxelAsset(scene,"trees",base,stage,origin,texture.palette,opacity);
	const auto &models=TreeModels();
	auto found=models.find(base);
	if (found != models.end() && found->second.tree) {
		const auto &model = found->second;
		const auto &tree = *model.tree;
		float growth = tree.growth[stage];
		Vec3 low = origin+model.low*growth, high = origin+model.high*growth;
		if (scene.visibility && !scene.visibility->Intersects(low,high)) return true;
		float diameter = std::max({high.x-low.x,high.y-low.y,(high.z-low.z)*Camera::WORLD_Z_SCALE})*pixel_scale*Camera::ART_SCALE;
		/* At twelve pixels an eight-sided crown's radial error is under half a
		 * pixel. Keep fine foliage/ribs for views where they can resolve. */
		unsigned lod = diameter < 12 ? 2 : diameter < 32 ? 1 : 0;
		InstanceData data;
		data.origin_opacity = {origin.x,origin.y,origin.z,opacity};
		data.scale_center = {growth,growth,0,0};
		data.identity = {0,static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED),1,0};
		if (tree.bark) {
			const auto &bark = Textures().Get(tree.bark->sprite,PAL_NONE,0,true);
			if (bark.width <= 0 || bark.height <= 0) throw std::runtime_error("Missing authored bark material");
			data.region = TreeMaterialRegion(bark,tree.bark->crop);
			data.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::RepeatingChart) | SURFACE_SHADED);
			SetWorldTexelChart(data,bark,tree.bark->crop,tree.bark->repeat,growth);
		}
		if (!tree.wood[lod].vertices.empty()) scene.instances.push_back({&tree.wood[lod].vertices,data});
		if (stage != 6 || tree.retain_dead_foliage) {
			unsigned age = stage == 4 ? 1 : stage == 5 ? 2 : 0;
			if (texture.width <= 0 || texture.height <= 0) return true;
			data.region = tree.foliage_charts ? texture.Region() : TreeMaterialRegion(texture,tree.crops[stage]);
			data.uv_transform[3] = static_cast<float>(texture.page);
			data.identity[1] = static_cast<float>(static_cast<uint32_t>(tree.foliage_charts ? SurfaceMode::Opaque : SurfaceMode::RepeatingChart) | SURFACE_SHADED);
			data.identity[3] = tree.foliage_charts ? 2 : 3;
			if (!tree.foliage_charts) {
				float density = age == 0 ? 1 : age == 1 ? 0.96f : 0.90f;
				SetWorldTexelChart(data,texture,tree.crops[stage],tree.foliage_repeat,growth*density);
			}
			if (!tree.foliage[age][lod].vertices.empty()) scene.instances.push_back({&tree.foliage[age][lod].vertices,data});
		}
		return true;
	}
	return found!=models.end() && DrawRegisteredModel(scene,found->second,stage==6 ? 6 : 3,texture,origin,origin,opacity,pixel_scale);
}

void VerifyTreeModels()
{
	VerifyVoxelTreeModels();
	unsigned views = 0, families = 0, voxel_families = 0;
	std::map<unsigned,std::set<PaletteID>> palettes;
	for (const auto &row : _tree_layout_sprite) for (const auto &sprite : row) palettes[sprite.sprite].insert(sprite.pal);
	for (const auto &[base,model] : TreeModels()) {
		if (!model.tree) continue;
		bool all_voxel = UseVoxelTrees();
		for (unsigned stage = 0; stage < 7; ++stage) all_voxel &= HasVoxelTree(base+stage);
		if (all_voxel) { ++voxel_families; continue; }
		++families;
		float extent = std::max({model.high.x-model.low.x,model.high.y-model.low.y,(model.high.z-model.low.z)*Camera::WORLD_Z_SCALE});
		palettes[base].insert(PAL_NONE);
		std::vector<uint8_t> default_palette_pixels;
		std::vector<uint32_t> default_palette_ids;
		for (PaletteID palette : palettes[base]) for (unsigned lod = 0; lod < 3; ++lod) for (unsigned stage = 0; stage < 7; ++stage) for (unsigned turn = 0; turn < 4; ++turn) {
			if (palette != PAL_NONE && (lod != 0 || stage != 3)) continue;
			Textures().BeginScene();
			const auto &texture = Textures().Get(base+stage,palette,lod*2,false);
			Scene scene;
			float pixel_scale = (lod == 0 ? 48.0f : lod == 1 ? 20.0f : 6.0f)/(extent*model.tree->growth[stage]*Camera::ART_SCALE);
			if (!DrawAuthoredTree(scene,base+stage,texture,{},1,pixel_scale) || scene.instances.empty()) throw std::runtime_error("Component tree has no state geometry");
			unsigned components = stage == 6 && !model.tree->retain_dead_foliage ? 1 : 2;
			if (scene.instances.size() != components || scene.instances.front().mesh != &model.tree->wood[lod].vertices) throw std::runtime_error("Tree lifecycle or LOD selected the wrong component meshes");
			for (auto &instance : scene.instances) instance.data.SetObjectId(base);
			float height = model.high.z*model.tree->growth[stage];
			Camera camera{{0,0,height*0.5f},std::min(6.0f,75.0f/std::max(1.0f,height)),256,256,turn+0.25f};
			std::vector<uint8_t> pixels, reference;
			std::vector<uint32_t> ids, reference_ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),base) < 8) throw std::runtime_error(fmt::format("Tree {} stage {} turn {} is not visible",base,stage,turn));
			if (lod == 0 && stage == 3 && turn == 0) {
				if (palette == PAL_NONE) { default_palette_pixels = pixels; default_palette_ids = ids; }
				else if (pixels == default_palette_pixels || ids != default_palette_ids) throw std::runtime_error(fmt::format("Tree {} palette {} did not recolour independently of its geometry",base,palette));
			}
			for (const auto &instance : scene.instances) {
				Scene isolated, expanded;
				isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
				for (const auto &v : expanded.vertices) {
					if (!std::isfinite(v.position.x+v.position.y+v.position.z+v.normal.x+v.normal.y+v.normal.z+v.texture.x+v.texture.y)) throw std::runtime_error("Tree contains non-finite geometry/materials");
					Vec3 p = v.position, low = model.low*model.tree->growth[stage], high = model.high*model.tree->growth[stage];
					if (p.x < low.x-0.0001f || p.y < low.y-0.0001f || p.z < low.z-0.0001f || p.x > high.x+0.0001f || p.y > high.y+0.0001f || p.z > high.z+0.0001f) throw std::runtime_error("Tree LOD exceeds its culling bounds");
				}
				if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,reference,&reference_ids)) throw std::runtime_error("Tree component rendering failed");
				if (std::count(ids.begin(),ids.end(),base) < 4) throw std::runtime_error(fmt::format("Tree {} stage {} LOD {} has an invisible {} material crop",base,stage,lod,instance.mesh == &model.tree->wood[lod].vertices ? "bark" : "foliage"));
				if (pixels != reference || ids != reference_ids) {
					unsigned colours = 0, picks = 0, delta = 0;
					for (size_t i = 0; i < ids.size(); ++i) {
						bool changed = false;
						for (unsigned channel = 0; channel < 4; ++channel) {
							unsigned d = static_cast<unsigned>(std::abs(static_cast<int>(pixels[i*4+channel])-reference[i*4+channel]));
							delta = std::max(delta,d); changed |= d != 0;
						}
						colours += changed; picks += ids[i] != reference_ids[i];
					}
					/* CPU/GPU normal normalization can straddle one RGBA8 rounding
					 * boundary. Geometry/alpha coverage and all picking IDs stay exact. */
					if (delta > 1 || picks != 0) throw std::runtime_error(fmt::format("Tree {} stage {} LOD {} turn {} component {} differs between CPU and GPU: {} colour pixels, {} IDs, max channel delta {}",base,stage,lod,turn,instance.data.identity[3],colours,picks,delta));
				}
			}
			for (auto &instance : scene.instances) instance.data.origin_opacity[3] = 0.38f;
			if (!RenderScene(scene,camera,reference,&reference_ids) || std::ranges::any_of(reference_ids, [](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent tree intercepts picking");
			++views;
		}
	}
	if (families == 0 && voxel_families == 0) throw std::runtime_error("No tree profiles loaded");
	Debug(driver,1,"OpenTT3D: {} component tree families and {} lifecycle/LOD views passed materials (one RGBA8 rounding level), culling bounds and exact picking",families,views);
	Debug(driver,1,"OpenTT3D: {} complete voxel tree families verified separately with exact palette/cell geometry",voxel_families);
}

bool HasAuthoredIndustry(unsigned graphics, SpriteID sprite)
{
	if (!IndustryModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape))) return false;
	if (VoxelIndustryState(graphics,sprite)) return true;
	auto found = IndustryModels().find(graphics);
	if (found == IndustryModels().end()) return false;
	if (found->second.sprites.empty()) return (sprite & SPRITE_MASK) != 0 && (sprite & SPRITE_MASK) == IndustryBodySprite(graphics);
	return std::ranges::find(found->second.sprites, sprite & SPRITE_MASK) != found->second.sprites.end();
}

bool DrawAuthoredIndustry(Scene &scene, unsigned graphics, SpriteID sprite, const SpriteTexture &texture, Vec3 origin, Vec3 sprite_origin, float opacity, float pixel_scale)
{
	if (auto state = VoxelIndustryState(graphics,sprite)) return DrawVoxelAsset(scene,"industries",graphics,*state,origin,texture.palette,opacity);
	return HasAuthoredIndustry(graphics, sprite) && DrawRegisteredModel(scene, IndustryModels().at(graphics), 3, texture, origin, sprite_origin, opacity, pixel_scale);
}

bool DrawAuthoredVehicle(Scene &scene, unsigned engine, bool loaded, Vec3 origin, float heading, PaletteID palette, unsigned texture_zoom, float opacity, const std::array<SpriteID, 8> *resolved, float grade)
{
	if (VoxelVehicleState(engine,loaded)) {
		auto references = resolved != nullptr ? *resolved : EngineReferenceSprites(engine,loaded);
		if (std::ranges::all_of(references,[](SpriteID sprite) { return IsBaseGraphicsSprite(sprite); }) && DrawVoxelVehicle(scene,engine,loaded,origin,heading,palette,opacity,UINT_MAX,grade)) return true;
	}
	const auto &models = VehicleModels();
	auto found = models.find(engine);
	if (found == models.end()) return false;
	const auto &model = found->second;
	const auto &state = (*model.states)[loaded];
	auto references = resolved != nullptr ? *resolved : EngineReferenceSprites(engine, loaded);
	float radius = std::max({std::abs(state.low.x), std::abs(state.high.x), std::abs(state.low.y), std::abs(state.high.y)}) * 1.42f;
	if (scene.visibility && !scene.visibility->Intersects(origin + Vec3{-radius, -radius, state.low.z}, origin + Vec3{radius, radius, state.high.z})) return true;
	unsigned lod = texture_zoom >= 4 ? 2 : texture_zoom >= 2 ? 1 : 0;
	/* Baked source-pixel UVs are stable across atlas relocation and texture LOD.
	 * Keeping separate reference views per face gives the rear actual rear artwork. */
	using Key = std::tuple<const VehicleStateModel *, unsigned, unsigned, int, int, int, int>;
	static std::map<Key, std::vector<Vertex>> prepared;
	for (unsigned view = 0; view < 4; ++view) {
		if (state.faces[lod][view].empty()) continue;
		SpriteTexture texture = Textures().Get(references[VEHICLE_VIEWS[view]], palette, texture_zoom, true);
		Key key{&state, lod, view, texture.ink_left, texture.ink_top, texture.ink_width, texture.ink_height};
		auto [mesh, inserted] = prepared.try_emplace(key);
		if (inserted) {
			mesh->second = state.faces[lod][view];
			auto bounds = state.projection[view];
			float xy_scale = texture.ink_width / (ZOOM_BASE * (bounds[2] - bounds[0]));
			auto vertical = [&](float z_scale) {
				std::array<float, 2> range{1e9f, -1e9f};
				for (const auto &face : state.faces[0]) for (const Vertex &vertex : face) {
					Vec3 p = VehicleView(vertex.position, VEHICLE_VIEWS[view]);
					float y = (p.x + p.y) * xy_scale - p.z * z_scale;
					range[0] = std::min(range[0], y); range[1] = std::max(range[1], y);
				}
				return range;
			};
			float lo = 0.001f, hi = 8;
			for (unsigned i = 0; i < 20; ++i) {
				float mid = (lo + hi) * 0.5f;
				auto range = vertical(mid);
				if (range[1] - range[0] < texture.ink_height / static_cast<float>(ZOOM_BASE)) lo = mid; else hi = mid;
			}
			float z_scale = (lo + hi) * 0.5f;
			auto range = vertical(z_scale);
			for (Vertex &vertex : mesh->second) {
				Vec3 p = VehicleView(vertex.position, VEHICLE_VIEWS[view]);
				float u = (2 * (p.y - p.x) - bounds[0]) * xy_scale;
				float v = (p.x + p.y) * xy_scale - p.z * z_scale - range[0];
				vertex.texture = {texture.ink_left / static_cast<float>(ZOOM_BASE) + u,
					texture.ink_top / static_cast<float>(ZOOM_BASE) + v, 0};
			}
		}
		Vec3 uv = texture.UV(0, 0);
		InstanceData instance;
		instance.origin_opacity = {origin.x, origin.y, origin.z, opacity};
		instance.mirror_layer_heading[3] = heading;
		instance.uv_transform = {uv.x, uv.y, ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE), uv.z};
		instance.region = texture.Region();
		instance.identity = {0, static_cast<float>(SurfaceMode::Opaque), 1, 1};
		scene.instances.push_back({&mesh->second, instance});
	}
	return true;
}

void ExportVehicleReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	Json manifest = Json::array();
	std::map<SpriteID,std::vector<uint8_t>> exported;
	for (const auto &[id, model] : VehicleModels()) {
		const Engine *engine = Engine::GetIfValid(EngineID{static_cast<uint16_t>(id)});
		if (engine == nullptr || !engine->info.climates.Test(_settings_game.game_creation.landscape)) continue;
		for (unsigned state = 0; state < 2; ++state) {
			auto sprites = EngineReferenceSprites(id, state != 0);
			for (unsigned direction = 0; direction < 8; ++direction) {
				SpriteID sprite = sprites[direction];
				auto name = fmt::format("vehicle-sprite-{}.pam", sprite);
				auto [entry,inserted] = exported.try_emplace(sprite);
				if (inserted) ExportSpriteReference(sprite,PALETTE_RECOLOUR_START,(directory/name).string(),&entry->second);
				const Sprite *source = GetSprite(sprite,SpriteType::Normal);
				manifest.push_back({{"engine", id}, {"name", model.name}, {"climate", to_underlying(_settings_game.game_creation.landscape)},
					{"loaded", state != 0}, {"direction", direction}, {"sprite", sprite}, {"image", name},
					{"palette_indices",entry->second},{"sprite_offset",{source->x_offs,source->y_offs}},{"sprite_size",{source->width,source->height}}});
			}
		}
	}
	std::ofstream(directory / "vehicles.json") << manifest.dump(2) << '\n';
	Json rotors = Json::array();
	for (SpriteID sprite = SPR_ROTOR_STOPPED; sprite <= SPR_ROTOR_MOVING_3; ++sprite) {
		auto name = fmt::format("aircraft-rotor-{}.pam",sprite);
		std::vector<uint8_t> indices;
		ExportSpriteReference(sprite,PAL_NONE,(directory/name).string(),&indices);
		const Sprite *source = GetSprite(sprite,SpriteType::Normal);
		rotors.push_back({{"sprite",sprite},{"state",sprite-SPR_ROTOR_STOPPED},
			{"climate",to_underlying(_settings_game.game_creation.landscape)},
			{"image",name},{"palette_indices",indices},{"sprite_offset",{source->x_offs,source->y_offs}},
			{"sprite_size",{source->width,source->height}}});
	}
	std::ofstream(directory / "aircraft-rotors.json") << rotors.dump(2) << '\n';
	Debug(driver, 1, "OpenTT3D: exported {} vehicle directional/state references", manifest.size());
}

void ExportVehicleModelGallery(unsigned engine, bool loaded)
{
	const Engine *definition = Engine::GetIfValid(EngineID{static_cast<uint16_t>(engine)});
	if (definition == nullptr || !definition->info.climates.Test(_settings_game.game_creation.landscape)) {
		Debug(driver, 0, "OpenTT3D: vehicle gallery requires a world in the engine's climate");
		return;
	}
	const auto &model = VehicleModels().at(engine);
	const auto &state = (*model.states)[loaded];
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned rotation = 0; rotation < 4; ++rotation) {
		Textures().BeginScene();
		Scene scene;
		DrawAuthoredVehicle(scene, engine, loaded, {}, 0, PALETTE_RECOLOUR_START, 0);
		Camera camera{(state.low + state.high) * 0.5f, std::min(8.0f, 160.0f / (state.high.x - state.low.x + state.high.y - state.low.y)), 640, 640, static_cast<float>(rotation)};
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene, camera, pixels)) throw std::runtime_error("Vehicle gallery GPU rendering failed");
		std::ofstream file(directory / fmt::format("model-vehicle-{:03}-{}.pam", engine, rotation), std::ios::binary);
		file << "P7\nWIDTH 640\nHEIGHT 640\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = 639; y >= 0; --y) file.write(reinterpret_cast<const char *>(pixels.data() + y * 640 * 4), 640 * 4);
	}
	Debug(driver, 1, "OpenTT3D: exported vehicle {} model gallery", engine);
}

void VerifyVehicleModels()
{
	unsigned poses = 0;
	std::vector<uint8_t> pixels;
	std::vector<uint32_t> ids;
	for (const auto &[engine, model] : VehicleModels()) {
		const Engine *definition = Engine::GetIfValid(EngineID{static_cast<uint16_t>(engine)});
		if (definition == nullptr || !definition->info.climates.Test(_settings_game.game_creation.landscape)) continue;
		for (unsigned loaded = 0; loaded < 2; ++loaded) {
			const auto &state = (*model.states)[loaded];
			for (const auto &lod : state.faces) for (const auto &face : lod) for (const Vertex &vertex : face) {
				if (!std::isfinite(vertex.position.x + vertex.position.y + vertex.position.z + vertex.normal.x + vertex.normal.y + vertex.normal.z)) throw std::runtime_error("Vehicle geometry contains a non-finite vertex");
			}
			float size = std::max({state.high.x - state.low.x, state.high.y - state.low.y, state.high.z - state.low.z, 1.0f});
			for (unsigned direction = 0; direction < 8; ++direction) {
				Textures().BeginScene();
				Scene scene;
				float angle = (5.0f - direction) * std::numbers::pi_v<float> / 4;
				if (!DrawAuthoredVehicle(scene, engine, loaded != 0, {}, angle, PALETTE_RECOLOUR_START, 1) || scene.instances.empty()) throw std::runtime_error("Vehicle definition has no volume geometry");
				for (auto &instance : scene.instances) instance.data.SetObjectId(engine + 1);
				Camera camera{{0, 0, (state.low.z + state.high.z) * 0.5f}, 28.0f / size, 128, 128, 0.37f};
				if (!RenderScene(scene, camera, pixels, &ids) || std::count(ids.begin(), ids.end(), engine + 1) < 8) throw std::runtime_error(fmt::format("Vehicle {} state {} direction {} failed visibility/picking", engine, loaded, direction));
				++poses;
			}
		}
	}
	Debug(driver, 1, "OpenTT3D: {} vehicle direction/cargo poses passed GPU visibility and picking", poses);
}

void VerifyIndustryModels()
{
	VerifyVoxelIndustryModels();
	unsigned views = 0;
	for (const auto &[graphics, model] : IndustryModels()) {
		if (!IndustryModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape))) continue;
		SpriteID image = IndustryBodySprite(graphics);
		if (!HasAuthoredIndustry(graphics, image)) throw std::runtime_error(fmt::format("Industry {} is not bound to its completed reference", graphics));
		Textures().BeginScene();
		SpriteTexture texture = Textures().Get(image, PAL_NONE, 0, true);
		Scene scene;
		if (!DrawAuthoredIndustry(scene, graphics, image, texture, {}, {}, 1) || scene.instances.empty()) throw std::runtime_error("Industry model has no geometry");
		for (auto &instance : scene.instances) instance.data.SetObjectId(graphics + 1);
		Vec3 low{1e9f, 1e9f, 1e9f}, high{-1e9f, -1e9f, -1e9f};
		for (const Vertex &vertex : scene.ExpandedVertices()) {
			Vec3 p = vertex.position;
			if (!std::isfinite(p.x + p.y + p.z + vertex.texture.x + vertex.texture.y)) throw std::runtime_error("Industry has non-finite geometry/material coordinates");
			low = {std::min(low.x, p.x), std::min(low.y, p.y), std::min(low.z, p.z)};
			high = {std::max(high.x, p.x), std::max(high.y, p.y), std::max(high.z, p.z)};
		}
		for (unsigned turn = 0; turn < 4; ++turn) {
			float extent = std::max({high.x - low.x, high.y - low.y, high.z - low.z, 1.0f});
			Camera camera{(low + high) * 0.5f, 48.0f / extent, 256, 256, static_cast<float>(turn)};
			std::vector<uint8_t> pixels;
			std::vector<uint32_t> ids;
			if (!RenderScene(scene, camera, pixels, &ids) || std::count(ids.begin(), ids.end(), graphics + 1) < 8) throw std::runtime_error(fmt::format("Industry {} failed view {} visibility", graphics, turn));
			if (model.component_materials) {
				Scene expanded;
				expanded.vertices = scene.ExpandedVertices(true);
				std::vector<uint8_t> reference;
				std::vector<uint32_t> reference_ids;
				if (!RenderScene(expanded,camera,reference,&reference_ids) || reference != pixels || reference_ids != ids) throw std::runtime_error("Industry component charts/solid materials differ from CPU instance reference");
			}
			++views;
		}
	}
	Debug(driver, 1, "OpenTT3D: {} authored industry views passed GPU visibility and material checks", views);
}

} // namespace Renderer3D
