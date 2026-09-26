/* SPDX-License-Identifier: GPL-2.0-only */
/** @file clear_surface_geometry.hpp Authored turf, rough-ground hummocks and small stones. */
#ifndef RENDERER3D_CLEAR_SURFACE_GEOMETRY_HPP
#define RENDERER3D_CLEAR_SURFACE_GEOMETRY_HPP

#include "ground_detail_geometry.hpp"
#include "camera.hpp"

namespace Renderer3D {

enum class ClearSurfaceMaterial : unsigned { Ground, Grass, Stone, Accent, Count };
struct ClearSurfaceAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(ClearSurfaceMaterial::Count)> parts;
};

inline void ClearSurfaceMound(Scene &mesh, Vec3 centre, float rx, float ry, float height, Rgb colour, unsigned sides = 6)
{
	for (unsigned side = 0; side < sides; ++side) {
		float a = 2*std::numbers::pi_v<float>*side/sides, b = 2*std::numbers::pi_v<float>*(side+1)/sides;
		Vec3 p = centre+Vec3{rx*std::cos(a),ry*std::sin(a),0}, q = centre+Vec3{rx*std::cos(b),ry*std::sin(b),0};
		mesh.Triangle(p,q,centre+Vec3{0.12f*rx,-0.08f*ry,height},colour);
		mesh.Triangle(centre,q,p,colour);
	}
}

inline ClearSurfaceAssembly MakeClearSurfaceAssembly(bool rough, unsigned variant, unsigned climate, const TileSurface &surface, unsigned lod, unsigned fine_edges = 15)
{
	std::array<Scene,static_cast<unsigned>(ClearSurfaceMaterial::Count)> meshes;
	auto &ground = meshes[static_cast<unsigned>(ClearSurfaceMaterial::Ground)];
	auto &grass = meshes[static_cast<unsigned>(ClearSurfaceMaterial::Grass)];
	auto &stone = meshes[static_cast<unsigned>(ClearSurfaceMaterial::Stone)];
	auto &accent = meshes[static_cast<unsigned>(ClearSurfaceMaterial::Accent)];
	unsigned density = rough ? 3 : variant;
	const Rgb turf[][4] = {
		{{0.36f,0.20f,0.07f},{0.30f,0.28f,0.12f},{0.26f,0.35f,0.12f},{0.24f,0.40f,0.13f}},
		{{0.36f,0.20f,0.07f},{0.36f,0.30f,0.14f},{0.41f,0.38f,0.17f},{0.45f,0.43f,0.21f}},
		{{0.36f,0.20f,0.07f},{0.34f,0.30f,0.19f},{0.37f,0.45f,0.27f},{0.39f,0.52f,0.29f}},
	};
	if (climate == 3) {
		/* Toyland's rough reference is a red/white board with raised plastic pips.
		 * The board is authored separately so the pips are not painted beneath it. */
		for (unsigned y = 0; y < 4; ++y) for (unsigned x = 0; x < 4; ++x) {
			bool light = (x+y)%2 != 0;
			Rgb colour = rough ? (light ? Rgb{0.84f,0.83f,0.80f} : Rgb{0.68f,0.025f,0.012f}) :
				(density == 0 || (density < 3 && (x*3+y)%4 >= density) ? (light ? Rgb{0.56f,0.57f,0.55f} : Rgb{0.39f,0.41f,0.39f}) :
				(light ? Rgb{0.32f,0.49f,0.015f} : Rgb{0.17f,0.35f,0.01f}));
			Vec3 corners[] = {{x*4.0f,y*4.0f,0},{x*4.0f+4,y*4.0f,0},{x*4.0f+4,y*4.0f+4,0},{x*4.0f,y*4.0f+4,0}};
			/* Interior checker edges already match their adjacent patch. Only
			 * the outer tile perimeter must conform to neighbouring voxel cells. */
			GroundEdgeFan(ground,corners,{x*4.0f+2,y*4.0f+2,0},colour,fine_edges,true);
		}
	} else {
		Rgb colour = turf[climate][density];
		/* Tone one complete bare-earth tile. Repeating a tiny patch here made
		 * each tile an obvious 8x8 grid and changed its native pixel density. */
		colour = {colour.r/0.36f,colour.g/0.20f,colour.b/0.07f};
		/* A replacement substrate is the actual terrain, not a raised decal.
		 * Adjacent roads, bare tiles and voxel floors share these exact edges. */
		const Vec3 corners[] = {{0,0,0},{16,0,0},{16,16,0},{0,16,0}};
		GroundEdgeFan(ground,corners,{8,8,0},colour,fine_edges);
		if (rough) {
			constexpr Vec3 bumps[] = {{3.1f,3.4f,0.7f},{9.4f,2.8f,0.5f},{12.1f,7.7f,0.8f},{5.7f,8.9f,0.6f},{3.5f,13.2f,0.5f},{11.4f,12.8f,0.7f}};
			for (unsigned index = 0; index < std::size(bumps); ++index) {
				Vec3 p = bumps[index];
				if (variant == 1) p = {16-p.y,p.x,p.z};
				if (variant == 2) p.x = 16-p.x;
				if (variant == 3) p.y = 16-p.y;
				if (variant == 4) std::swap(p.x,p.y);
				ClearSurfaceMound(ground,{p.x,p.y,0},1.7f,1.45f,p.z*1.8f,{colour.r*0.90f,colour.g*0.90f,colour.b*0.90f},lod == 2 ? 4 : 8);
			}
		}
		for (auto &v : ground.vertices) v.texture = {2*(v.position.y-v.position.x),v.position.x+v.position.y,0};
	}
	constexpr Vec3 tufts[] = {{1.2f,2.1f,0},{4.6f,1.3f,0},{8.1f,2.7f,0},{12.7f,1.8f,0},{14.5f,4.7f,0},
		{2.8f,5.3f,0},{6.5f,4.1f,0},{10.2f,5.8f,0},{1.4f,8.9f,0},{4.5f,8.1f,0},{8.2f,7.4f,0},{12.8f,8.6f,0},
		{3.0f,12.7f,0},{6.2f,11.2f,0},{9.7f,10.5f,0},{14.4f,12.1f,0},{5.1f,14.6f,0},{10.8f,14.2f,0}};
	if (climate != 3 && density != 0 && lod < 2) for (unsigned index = 0; index < std::size(tufts); ++index) {
		if (!rough && index%3 >= density) continue;
		Vec3 root = tufts[(index+variant*3)%std::size(tufts)]+Vec3{0,0,0.07f};
		float height = (rough ? 1.45f : 0.30f+0.22f*density)*(0.85f+0.08f*(index%4));
		for (unsigned leaf = 0; leaf < (lod == 0 ? 4U : 2U); ++leaf) {
			float angle = index*2.3f+leaf*2.1f;
			CropLeaf(grass,root,root+Vec3{0.34f*std::cos(angle),0.34f*std::sin(angle),height},0.055f,{});
		}
	}
	for (auto &v : grass.vertices) v.texture = {v.position.x,-v.position.z*Camera::WORLD_Z_SCALE,-1};
	constexpr Vec3 pebbles[] = {{2.6f,3.5f,0.22f},{6.7f,2.1f,0.3f},{12.2f,3.3f,0.24f},{4.4f,7.3f,0.32f},
		{9.6f,6.4f,0.22f},{13.5f,10.1f,0.26f},{3.5f,12.1f,0.25f},{9.1f,13.4f,0.3f}};
	if ((climate == 1 || climate == 2) && density == 3 && !rough && lod < 2) for (Vec3 p : pebbles) {
		ClearSurfaceMound(stone,{p.x,p.y,0},p.z*1.6f,p.z,p.z,{},lod == 0 ? 6 : 4);
	}
	for (auto &v : stone.vertices) v.texture = {v.position.x,-v.position.z*Camera::WORLD_Z_SCALE,-1};
	if (climate == 3 && rough) for (unsigned index = 0; index < 6; ++index) {
		Vec3 p = tufts[(index*3+variant)%std::size(tufts)];
		Rgb colour = ((static_cast<unsigned>(p.x)/4+static_cast<unsigned>(p.y)/4)%2 == 0) ? Rgb{0.88f,0.87f,0.84f} : Rgb{0.72f,0.025f,0.015f};
		GeometryBox(accent,p+Vec3{-0.42f,-0.42f,0.04f},p+Vec3{0.42f,0.42f,0.55f},colour);
	}
	ClearSurfaceAssembly result;
	for (size_t material = 0; material < meshes.size(); ++material) {
		GroundDetailConform(meshes[material].vertices,surface);
		result.parts[material] = std::move(meshes[material].vertices);
	}
	return result;
}

} // namespace Renderer3D
#endif
