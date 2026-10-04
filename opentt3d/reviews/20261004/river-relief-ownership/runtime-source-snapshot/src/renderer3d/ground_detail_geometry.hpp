/* SPDX-License-Identifier: GPL-2.0-only */
/** @file ground_detail_geometry.hpp Authored field growth, stacked hay and exposed rocks. */
#ifndef RENDERER3D_GROUND_DETAIL_GEOMETRY_HPP
#define RENDERER3D_GROUND_DETAIL_GEOMETRY_HPP

#include "terrain_geometry.hpp"
#include <numbers>

namespace Renderer3D {

enum class GroundDetailMaterial : unsigned { Soil, Crop, Hay, Bindings, Rock, Snow, Count };
struct GroundDetailAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(GroundDetailMaterial::Count)> parts;
};

inline void GroundDetailConform(std::vector<Vertex> &vertices, const TileSurface &surface)
{
	for (auto &v : vertices) v.position.z += surface.Height(v.position.x,v.position.y);
	for (size_t i = 0; i < vertices.size(); i += 3) {
		Vec3 n = Normal(vertices[i].position,vertices[i+1].position,vertices[i+2].position);
		for (size_t j = i; j < i+3; ++j) vertices[j].normal = n;
	}
}

/** Thin but closed leaf solids, never camera-facing vegetation cards. */
inline void CropLeaf(Scene &scene, Vec3 root, Vec3 tip, float width, Rgb colour)
{
	Vec3 side = Normalize(Vec3{root.y-tip.y,tip.x-root.x,0})*width;
	Vec3 middle = (root+tip)*0.5f, a = middle+side, b = middle-side;
	Vec3 underside = middle-Vec3{0,0,0.05f};
	scene.Triangle(root,b,tip,colour); scene.Triangle(root,tip,a,colour);
	scene.Triangle(root,underside,b,colour); scene.Triangle(root,a,underside,colour);
	scene.Triangle(tip,b,underside,colour); scene.Triangle(tip,underside,a,colour);
}

inline GroundDetailAssembly MakeFieldAssembly(unsigned stage, const TileSurface &surface, unsigned lod = 0)
{
	std::array<Scene,static_cast<unsigned>(GroundDetailMaterial::Count)> meshes;
	auto &soil = meshes[static_cast<unsigned>(GroundDetailMaterial::Soil)];
	auto &crop = meshes[static_cast<unsigned>(GroundDetailMaterial::Crop)];
	auto &hay = meshes[static_cast<unsigned>(GroundDetailMaterial::Hay)];
	auto &bindings = meshes[static_cast<unsigned>(GroundDetailMaterial::Bindings)];
	/* Eight continuous plough ridges. The underlying material is clean earth,
	 * not the reference picture containing already-painted stalks or bales. */
	const Vec3 corners[] = {{0,0,0.025f},{16,0,0.025f},{16,16,0.025f},{0,16,0.025f}};
	for (unsigned i = 0; i < 4; ++i) soil.Triangle(corners[i],corners[(i+1)%4],{8,8,0.025f},{0.56f,0.53f,0.48f});
	bool planar = std::abs(surface.corners[0]+surface.corners[2]-surface.corners[1]-surface.corners[3]) < 0.001f &&
		std::abs(surface.centre-(surface.corners[0]+surface.corners[2])*0.5f) < 0.001f;
	float ridge_step = planar ? 16 : 1;
	for (unsigned row = 0; row < 8; ++row) {
		float y = row*2+1;
		for (float x = 0; x < 16; x += ridge_step) {
			soil.Quad({x,y-0.8f,0.03f},{x+ridge_step,y-0.8f,0.03f},{x+ridge_step,y,0.65f},{x,y,0.65f},{1,0.94f,0.87f});
			soil.Quad({x,y,0.65f},{x+ridge_step,y,0.65f},{x+ridge_step,y+0.8f,0.03f},{x,y+0.8f,0.03f},{1,0.94f,0.87f});
		}
	}
	for (auto &v : soil.vertices) v.texture = {v.position.x,v.position.y,0};
	const float heights[] = {0.16f,0.55f,0.95f,1.45f,1.90f,2.25f,2.65f,0.40f,0.12f};
	const Rgb colours[] = {{0.68f,0.50f,0.28f},{0.39f,0.53f,0.12f},{0.34f,0.52f,0.12f},
		{0.24f,0.49f,0.07f},{0.30f,0.54f,0.09f},{0.59f,0.64f,0.27f},{0.84f,0.79f,0.46f},
		{0.77f,0.66f,0.36f},{0.73f,0.58f,0.29f}};
	float height = heights[stage];
	if (stage >= 3 && stage <= 6 && lod < 2) {
		/* Mature references have a dense lower canopy, not isolated seedlings.
		 * Closed, irregular row crowns fill that volume below the detailed ears. */
		float stride = lod == 0 ? 1 : 4;
		for (unsigned row = 0; row < 8; ++row) for (float x = 0; x < 16; x += stride) {
			Vec3 ring[2][6];
			for (unsigned end = 0; end < 2; ++end) {
				float px = x+end*stride, y = row*2+1;
				float h = height*((lod == 0 ? 0.46f : 0.88f)+0.03f*((static_cast<unsigned>(px)+row*3)%4));
				if (lod != 0 && stage >= 5) h += 0.12f;
				float width = (stage == 4 ? 0.97f : 0.90f)-0.035f*((static_cast<unsigned>(px)+row)%3);
				ring[end][0] = {px,y-0.25f,0.65f}; ring[end][1] = {px,y+0.25f,0.65f};
				ring[end][2] = {px,y+width,0.65f+h*0.6f}; ring[end][3] = {px,y+width*0.85f,0.65f+h};
				ring[end][4] = {px,y-width*0.85f,0.65f+h}; ring[end][5] = {px,y-width,0.65f+h*0.6f};
			}
			for (unsigned edge = 0; edge < 6; ++edge) crop.Quad(ring[0][edge],ring[0][(edge+1)%6],ring[1][(edge+1)%6],ring[1][edge],colours[stage]);
			for (unsigned edge = 1; edge < 5; ++edge) {
				if (x == 0) crop.Triangle(ring[0][0],ring[0][edge+1],ring[0][edge],colours[stage]);
				if (x+stride == 16) crop.Triangle(ring[1][0],ring[1][edge],ring[1][edge+1],colours[stage]);
			}
		}
	}
	/* At middle distance the raised row crown carries the full growth height;
	 * individual subpixel stems/ears need not add thousands of hidden faces. */
	if ((lod < 2 || (stage >= 3 && stage <= 6)) && !(lod == 1 && stage >= 3 && stage <= 6)) {
		unsigned spacing = lod == 0 ? 1 : 4;
		for (unsigned row = 0; row < 8; ++row) for (unsigned stalk = 0; stalk < 16; stalk += spacing) {
			float x = stalk+0.5f, y = row*2+1;
			float h = height*(0.84f+0.04f*((row*3+stalk*5)%5));
			Rgb colour = colours[stage];
			if (lod == 2) {
				/* Small distant clusters still have closed volume and growth height. */
				if (stalk == 0) GeometryBox(crop,{0.05f,y-0.75f,0.65f},{15.95f,y+0.75f,0.65f+h*0.75f},colour);
				continue;
			}
			Vec3 root{x,y,0.65f}, tip{x+0.06f*((stalk%3)-1.0f),y,h+0.65f};
			GeometryBeam(crop,root,tip,stage >= 3 && stage <= 6 ? 0.035f : 0.025f,colour);
			if (stage >= 2 && stage <= 6) for (unsigned leaf = 0; leaf < (lod == 0 ? 3U : 2U); ++leaf) {
				float angle = (leaf*2.1f+(row+stalk)%4)*1.1f;
				Vec3 base = root+Vec3{0,0,h*(0.3f+0.17f*leaf)};
				CropLeaf(crop,base,base+Vec3{0.42f*std::cos(angle),0.42f*std::sin(angle),h*0.22f},0.075f,colour);
			}
			if (stage == 5 || stage == 6) GeometryBeam(crop,tip-Vec3{0,0,0.30f},tip+Vec3{0.06f,0,0.12f},0.075f,colours[6]);
		}
	}
	if (stage == 8) {
		for (Vec3 centre : {Vec3{4,4.5f,0},Vec3{11.5f,11,0}}) for (unsigned layer = 0; layer < 2; ++layer) {
			for (unsigned x = 0; x < 2; ++x) for (unsigned y = 0; y < 2; ++y) {
				Vec3 low = centre+Vec3{x*1.75f-1.72f,y*1.65f-1.62f,0.32f+layer*1.45f};
				Vec3 high = low+Vec3{1.68f,1.58f,1.38f};
				size_t first = hay.vertices.size();
				GeometryBox(hay,low,high,{});
				for (size_t i = first; i < hay.vertices.size(); ++i) {
					auto &v = hay.vertices[i];
					float u = std::abs(v.normal.x) > 0.5f ? (v.position.y-low.y)/1.58f : (v.position.x-low.x)/1.68f;
					float t = std::abs(v.normal.z) > 0.5f ? (v.position.y-low.y)/1.58f : (v.position.z-low.z)/1.38f;
					/* Selected straw-only top patch from field-8-0, 256x127. */
					v.texture = {(129+4*u)/256,(16+4*t)/127,-3};
				}
				if (lod < 2) for (float x_offset : {0.45f,1.23f}) {
					float bx = low.x+x_offset;
					GeometryBeam(bindings,{bx,low.y,high.z+0.025f},{bx,high.y,high.z+0.025f},0.018f,{0.46f,0.35f,0.16f});
					for (float by : {low.y-0.02f,high.y+0.02f}) GeometryBeam(bindings,{bx,by,low.z},{bx,by,high.z},0.018f,{0.46f,0.35f,0.16f});
				}
			}
		}
	}
	if (stage >= 3 && stage <= 6) {
		/* Foliage-only chart from the centre of each mature field reference.
		 * It breaks up the authored canopy solids without reintroducing the
		 * entire directional field picture or painting crops onto the ground. */
		for (size_t i = 0; i < crop.vertices.size(); ++i) {
			const Vec3 coordinates[] = {{0,0,0},{1,0,0},{0.5f,1,0}};
			Vec3 uv = coordinates[i%3];
			crop.vertices[i].texture = {(120+8*uv.x)/256,(56+8*uv.y)/127,-3};
			crop.vertices[i].colour = {};
		}
	}
	GroundDetailAssembly result;
	for (size_t i = 0; i < meshes.size(); ++i) {
		GroundDetailConform(meshes[i].vertices,surface);
		result.parts[i] = std::move(meshes[i].vertices);
	}
	return result;
}

inline GroundDetailAssembly MakeRockAssembly(unsigned variant, unsigned snow, const TileSurface &surface)
{
	Scene rocks, caps;
	struct Stone { float x,y,rx,ry,height; };
	constexpr Stone layout[] = {{3.0f,2.0f,2.0f,1.5f,1.3f},{7.2f,2.0f,1.8f,1.5f,1.5f},{12.2f,3.0f,2.6f,1.8f,1.8f},
		{3.0f,6.5f,2.3f,2.4f,1.7f},{8.5f,6.5f,2.5f,2.1f,1.8f},{13.7f,7.5f,1.6f,1.8f,1.6f},
		{4.0f,11.2f,2.8f,2.0f,1.4f},{9.6f,11.8f,2.1f,2.5f,1.8f},{13.5f,13.4f,1.7f,1.7f,1.6f}};
	for (unsigned index = 0; index < std::size(layout); ++index) {
		const auto &stone = layout[index];
		Vec3 ring[6], top[6];
		Vec3 centre{stone.x,stone.y,stone.height+0.35f};
		for (unsigned side = 0; side < 6; ++side) {
			float angle = (side+(index%3)*0.15f)*std::numbers::pi_v<float>/3;
			float rough = 0.82f+0.045f*((side+index)%4);
			ring[side] = {stone.x+stone.rx*rough*std::cos(angle),stone.y+stone.ry*rough*std::sin(angle),0.02f};
			top[side] = {stone.x+(ring[side].x-stone.x)*0.78f,stone.y+(ring[side].y-stone.y)*0.78f,stone.height*(0.82f+0.05f*((side+index)%3))};
		}
		for (unsigned side = 0; side < 6; ++side) {
			unsigned next = (side+1)%6;
			rocks.Quad(ring[side],ring[next],top[next],top[side],{});
			rocks.Triangle(top[side],top[next],centre,{});
			if (snow != 0 && (snow == 4 || (side+index)%4 < snow)) {
				Vec3 lift{0,0,0.025f};
				caps.Triangle(top[side]+lift,top[next]+lift,centre+lift,{0.94f,0.96f,0.98f});
			}
		}
	}
	for (auto &v : rocks.vertices) {
		/* Separate authored stone charts preserve the actual lower-resolution
		 * second-rock-set artwork, without painting its grass gaps onto rocks. */
		float u = v.position.x-std::floor(v.position.x), t = v.position.z/2.2f;
		v.texture = variant == 0 ? Vec3{(133+8*u)/256,(52+8*t)/124,-3} : Vec3{(136+7*u)/256,(52+3*std::clamp(t,0.0f,1.0f))/124,-3};
	}
	GroundDetailConform(rocks.vertices,surface);
	GroundDetailConform(caps.vertices,surface);
	GroundDetailAssembly result;
	result.parts[static_cast<unsigned>(GroundDetailMaterial::Rock)] = std::move(rocks.vertices);
	result.parts[static_cast<unsigned>(GroundDetailMaterial::Snow)] = std::move(caps.vertices);
	return result;
}

} // namespace Renderer3D
#endif
