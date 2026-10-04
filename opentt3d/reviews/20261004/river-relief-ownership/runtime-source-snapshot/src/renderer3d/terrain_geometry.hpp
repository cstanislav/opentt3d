/* SPDX-License-Identifier: GPL-2.0-only */
/** @file terrain_geometry.hpp Explicit small terrain structures and surface charts. */
#ifndef RENDERER3D_TERRAIN_GEOMETRY_HPP
#define RENDERER3D_TERRAIN_GEOMETRY_HPP

#include "geometry.hpp"
#include "voxel_geometry.hpp"

namespace Renderer3D {

/** Terrain borders use the same half-unit edge samples as voxel ground tiles.
 * Matching heights alone is insufficient: a long raster edge next to short
 * voxel edges can expose subpixel T-junction gaps at a low viewing angle. */
inline void GroundEdgeFan(Scene &mesh, std::span<const Vec3> boundary, Vec3 centre, Rgb colour = {}, unsigned fine_edges = 15, bool tile_boundary_only = false)
{
	for (size_t edge = 0; edge < boundary.size(); ++edge) {
		Vec3 a = boundary[edge], b = boundary[(edge+1)%boundary.size()];
		unsigned edge_mask = a.y == b.y && a.y == 0 ? 1U : a.x == b.x && a.x == 16 ? 2U : a.y == b.y && a.y == 16 ? 4U : a.x == b.x && a.x == 0 ? 8U : 0U;
		/* Ordinary terrain agrees on whole-tile edges. Only contacts with a
		 * voxel substrate require half-unit samples; do not subdivide a whole
		 * map merely because a handful of tiles contain those substrates. */
		float density = edge_mask == 0 || (fine_edges & edge_mask) != 0 ? 2.0f : 1.0f/16;
		unsigned steps = tile_boundary_only && edge_mask == 0 ? 1U : std::max(1U,static_cast<unsigned>(std::ceil(std::max(std::abs(b.x-a.x),std::abs(b.y-a.y))*density)));
		for (unsigned i = 0; i < steps; ++i) {
			Vec3 first = a+(b-a)*(static_cast<float>(i)/steps);
			Vec3 last = a+(b-a)*(static_cast<float>(i+1)/steps);
			mesh.Triangle(first,last,centre,colour);
		}
	}
}

/** Same four triangles as the terrain mesh, with a separate raised half-tile. */
struct TileSurface {
	std::array<float,4> corners{}; ///< N, W, S, E in world XY order.
	float centre = 0, upper_height = 0;
	int raised_half = -1;
	float EdgeHeight(unsigned edge, bool second) const
	{
		if (raised_half == static_cast<int>(edge) || raised_half == static_cast<int>((edge+1)%4)) return upper_height;
		return corners[(edge+second)%4];
	}
	float Height(float x, float y) const
	{
		if ((raised_half == 0 && x+y < 16) || (raised_half == 1 && x > y) ||
			(raised_half == 2 && x+y >= 16) || (raised_half == 3 && x <= y)) return upper_height;
		float dx = x-8, dy = y-8;
		unsigned edge = std::abs(dx) > std::abs(dy) ? (dx > 0 ? 1 : 3) : (dy > 0 ? 2 : 0);
		const Vec3 points[] = {{0,0,0},{16,0,0},{16,16,0},{0,16,0}};
		Vec3 a = points[edge], b = points[(edge+1)%4];
		float det = (a.y-b.y)*(8-b.x)+(b.x-a.x)*(8-b.y);
		float wc = ((a.y-b.y)*(x-b.x)+(b.x-a.x)*(y-b.y))/det;
		float wa = ((b.y-8)*(x-8)+(8-b.x)*(y-8))/det;
		return wa*corners[edge] + (1-wa-wc)*corners[(edge+1)%4] + wc*centre;
	}
};

inline void GeometryBeam(Scene &mesh, Vec3 a, Vec3 b, float radius, Rgb colour = {})
{
	Vec3 along = Normalize(b-a);
	Vec3 right = std::abs(along.z) < 0.9f ? Normalize(Vec3{-along.y,along.x,0}) : Vec3{1,0,0};
	Vec3 up = Normal({},along,right);
	Vec3 r = right*radius, u = up*radius;
	Vec3 p[] = {a-r-u,a+r-u,a+r+u,a-r+u,b-r-u,b+r-u,b+r+u,b-r+u};
	mesh.Quad(p[0],p[3],p[2],p[1],colour);
	mesh.Quad(p[4],p[5],p[6],p[7],colour);
	for (unsigned i = 0; i < 4; ++i) mesh.Quad(p[i],p[(i+1)%4],p[4+(i+1)%4],p[4+i],colour);
}

inline void GeometryBox(Scene &mesh, Vec3 low, Vec3 high, Rgb colour = {})
{
	Vec3 p[] = {{low.x,low.y,low.z},{high.x,low.y,low.z},{high.x,high.y,low.z},{low.x,high.y,low.z},
		{low.x,low.y,high.z},{high.x,low.y,high.z},{high.x,high.y,high.z},{low.x,high.y,high.z}};
	mesh.Quad(p[0],p[3],p[2],p[1],colour); mesh.Quad(p[4],p[5],p[6],p[7],colour);
	for (unsigned i = 0; i < 4; ++i) mesh.Quad(p[i],p[(i+1)%4],p[4+(i+1)%4],p[4+i],colour);
}

/** Styles: hedge, hedge/gate, white timber, two flowering hedges, stone and
 * railway chain link. Shapes and palette cells are authored independently of
 * sprite projection. Thin boards/wires use a finer grid than opaque hedge bodies. */
inline std::vector<Vertex> MakeFenceMesh(unsigned style, Vec3 start, Vec3 end, const TileSurface &surface, bool flat_height = false, unsigned component = 0, unsigned lod = 0)
{
	float length = std::hypot(end.x-start.x,end.y-start.y);
	if (style > 6 || component > 2 || lod > 2 || !std::isfinite(length) || length <= 0) throw std::invalid_argument("Invalid voxel fence layout");
	Vec3 along{(end.x-start.x)/length,(end.y-start.y)/length,0}, across{-along.y,along.x,0};
	bool hedge = style == 0 || style == 1 || style == 3 || style == 4;
	float xy = style == 6 ? (lod == 0 ? 0.125f : 0.25f) : style == 1 || style == 2 ? 0.25f : 0.5f;
	float dz = style == 1 || style == 2 || (style == 6 && lod == 0) ? 0.25f : 0.5f;
	float low_ground = flat_height ? start.z : std::min({surface.corners[0],surface.corners[1],surface.corners[2],surface.corners[3],surface.centre,surface.upper_height});
	float high_ground = flat_height ? start.z : std::max({surface.corners[0],surface.corners[1],surface.corners[2],surface.corners[3],surface.centre,surface.upper_height});
	Vec3 origin{std::floor((std::min(start.x,end.x)-1)/xy)*xy-xy*0.5f,
		std::floor((std::min(start.y,end.y)-1)/xy)*xy-xy*0.5f,std::floor((low_ground-1)/dz)*dz};
	std::array<int,3> size{static_cast<int>(std::ceil((std::max(start.x,end.x)+1-origin.x)/xy)),
		static_cast<int>(std::ceil((std::max(start.y,end.y)+1-origin.y)/xy)),static_cast<int>(std::ceil((high_ground+7-origin.z)/dz))};
	VoxelGrid grid(size,{
		{{88,80,81,88,104,90}}, // stems and deeply shaded foliage
		{{91,88,89,91,80,93}},{{92,89,90,92,80,94}},{{90,88,88,91,80,92}},{{93,90,91,93,80,95}},
		{{29,25,28,30,24,30}},{{125,112,124,126,112,126}}, // subtle cream/coral blossom
		{{7,4,5,9,2,11}},{{6,3,4,7,2,10}},{{9,5,6,10,3,13}},{{5,2,3,5,2,6}}, // stone courses
		{{12,10,12,15,10,15}},{{202,199,200,203,198,204}},{{19,16,17,20,16,21}} // boards, posts, wire
	},origin,{xy,xy,dz});
	/* Local authored variation, independent of map state and simulation RNG.
	 * A short repeated row table made foliage read as horizontal brick courses. */
	auto grain = [](unsigned column, unsigned row) {
		uint32_t value = column*0x9E3779B9U ^ row*0x85EBCA6BU ^ 0xA531U;
		value ^= value>>16; value *= 0x7FEB352DU; value ^= value>>15;
		return value;
	};
	static constexpr float crown[] = {5,4.5f,4.5f,5,4.5f,5,5,4.5f,5,4.5f,5,4.5f,4.5f,5,4.5f,5};
	float first_post = style == 1 ? length*3/8 : 0, last_post = style == 1 ? length*5/8 : length;
	unsigned posts = style == 1 ? 2 : style == 6 ? (lod < 2 ? 5 : 3) : lod == 0 ? 9 : lod == 1 ? 5 : 3;
	for (int y = 0; y < size[1]; ++y) for (int x = 0; x < size[0]; ++x) {
		Vec3 p = origin+Vec3{(x+0.5f)*xy,(y+0.5f)*xy,0};
		float s = Dot(p-start,along), cross = std::abs(Dot(p-start,across));
		if (s < -xy*0.49f || s > length+xy*0.49f || cross > 0.375f) continue;
		float low = INFINITY, high = -INFINITY;
		for (float dx : {-xy*0.5f,xy*0.5f}) for (float dy : {-xy*0.5f,xy*0.5f}) {
			float height = flat_height ? start.z : surface.Height(p.x+dx,p.y+dy);
			low = std::min(low,height); high = std::max(high,height);
		}
		auto fill = [&](float bottom, float top, unsigned material) {
			int a = static_cast<int>(std::floor((bottom-origin.z)/dz+0.00001f));
			int b = static_cast<int>(std::ceil((top-origin.z)/dz-0.00001f));
			if (a < b) grid.Fill({x,y,a},{x+1,y+1,b},material);
		};
		unsigned column = static_cast<unsigned>(std::max(0.0f,std::floor(s*2)));
		/* Perpendicular hedge volumes overlap at tile corners. Give their
		 * shared cap cells the same grain, independent of segment direction and
		 * mesh allocation/draw order, rather than two coplanar palette colours. */
		if (s < 1 || s > length-1) column = 0;
		bool gap = style == 1 && s > first_post && s < last_post;
		if ((hedge || style == 5) && !gap && s >= 0 && s < length) {
			float height = crown[std::min(15U,static_cast<unsigned>(std::max(0.0f,s)*16/length))];
			int bottom = static_cast<int>(std::floor((low-origin.z)/dz));
			int top = static_cast<int>(std::ceil((high+height-origin.z)/dz));
			for (int z = bottom; z < top; ++z) {
				float h = origin.z+(z+0.5f)*dz-high;
				if (hedge && cross > (h < 1 || h > height-0.5f ? 0.125f : 0.375f)) continue;
				unsigned row = static_cast<unsigned>(std::max(0.0f,std::floor(h*2)));
				unsigned material;
				if (hedge) {
					material = h < 1 ? 1 : 2+(lod == 0 ? grain(column,row)%4 : 0);
					if ((style == 3 || style == 4) && h > height-1 && grain(column,row)%11 == 0) material = style == 3 ? 6 : 7;
				} else {
					material = lod == 2 ? 8 : row%4 == 0 && (column+row/4)%5 != 0 ? 11 : 8+grain(column/2,row/2)%3;
				}
				grid.Fill({x,y,z},{x+1,y+1,z+1},material);
			}
		}
		if (style != 1 && style != 2 && style != 6) continue;
		float post_distance = INFINITY;
		for (unsigned post = 0; post < posts; ++post) post_distance = std::min(post_distance,std::abs(s-std::lerp(first_post,last_post,static_cast<float>(post)/(posts-1))));
		bool post = post_distance <= 0.126f && cross <= 0.126f;
		float post_height = style == 6 ? 5.0f : style == 1 ? 3.5f : 3.0f;
		if (post) fill(low,high+post_height,style == 6 ? 13 : 12);
		/* Diagonal slices need neighbouring lattice rows to share real faces. */
		float wire_half_width = xy*(std::abs(along.x*along.y) > 0.01f ? 0.72f : 0.49f);
		if (s < first_post || s > last_post || cross > wire_half_width) continue;
		for (float height : {1.0f,2.25f}) fill(low+height,high+height+dz,style == 6 ? 14 : 12);
		if (style == 6) fill(low+4.5f,high+4.5f+dz,14);
		if (style == 1) {
			float height = 1.0f+1.25f*(s-first_post)/(last_post-first_post);
			float rise = xy*0.625f/(last_post-first_post);
			fill(low+height-rise,high+height+rise+0.125f,12);
		}
		if (style == 6 && lod == 0) {
			for (int z = static_cast<int>(std::floor((low+0.5f-origin.z)/dz)); z < static_cast<int>(std::ceil((high+4.75f-origin.z)/dz)); ++z) {
				float h = origin.z+(z+0.5f)*dz-high;
				if (h < 0.5f || h > 4.75f) continue;
				if (std::abs(std::remainder(s+h*0.5f,1.0f)) < 0.126f || std::abs(std::remainder(s-h*0.5f,1.0f)) < 0.126f) grid.Fill({x,y,z},{x+1,y+1,z+1},14);
			}
		}
		if (style == 6 && post) fill(low,high+post_height,13);
	}
	if (style == 1 && component == 1) return grid.Mesh(true,1,7).vertices;
	if (style == 1 && component == 2) return grid.Mesh(true,12,12).vertices;
	return grid.Mesh().vertices;
}

/** Authored rubble supporting the unchanged upstream foundation surface. Cells
 * fit below the upper surface and embed into the lower terrain. Hidden ground
 * contacts are omitted from the draw mesh, not left coplanar with grass/road. */
inline std::vector<Vertex> MakeFoundationMesh(const TileSurface &bottom, const TileSurface &top, float top_base, unsigned lod = 0, bool contacts = false, bool greedy = true)
{
	if (lod > 2 || !std::isfinite(top_base) || top_base < 0 || top_base > TerrainZ(16)) throw std::invalid_argument("Invalid voxel foundation");
	float xy = lod == 0 ? 0.5f : lod == 1 ? 1 : 2;
	float dz = lod == 0 ? 0.25f : lod == 1 ? 0.5f : 1;
	int extent = static_cast<int>(16/xy);
	float maximum = top_base+std::max({top.corners[0],top.corners[1],top.corners[2],top.corners[3],top.centre,top.upper_height});
	int layers = std::max(2,static_cast<int>(std::ceil(maximum/dz))+2);
	std::vector<VoxelMaterial> materials{
		{{33,35,34,37,104,38}},{{104,33,104,34,104,35}},{{34,57,34,59,33,31}},
		{{3,5,4,9,2,11}},{{24,26,25,30,24,31}},{{1,2,1,4,1,5}},
		{{34,36,35,38,33,39}},{{4,7,5,11,3,12}},{{2,4,3,7,1,9}},
		{{25,28,26,31,24,31}},{{35,58,36,39,34,39}}
	};
	if (top.raised_half >= 0) {
		/* A diagonal retaining wall has one authored light direction. Giving
		 * alternating X/Y microsteps unrelated ramps made it look like stripes. */
		static constexpr uint8_t diagonal[][11] = {
			{36,34,58,7,28,3,37,9,5,29,59}, {35,33,57,6,27,2,36,8,4,28,58},
			{34,104,34,4,25,1,35,5,3,26,35}, {35,33,35,5,25,2,36,6,4,27,36}
		};
		static constexpr unsigned faces[][2] = {{1,3},{0,3},{0,2},{1,2}};
		for (unsigned index = 0; index < 11; ++index) {
			VoxelMaterial material = materials[index];
			for (unsigned face : faces[top.raised_half]) material.colours[face] = diagonal[top.raised_half][index];
			materials.push_back(material);
		}
	}
	unsigned occluder = static_cast<unsigned>(materials.size())+1;
	materials.push_back({{0,0,0,0,0,0}});
	VoxelGrid grid({extent,extent,layers},std::move(materials),{0,0,-dz},{xy,xy,dz});
	for (int y = 0; y < extent; ++y) for (int x = 0; x < extent; ++x) {
		float low = INFINITY, high = INFINITY, gap = 0;
		/* Sample inside the cell: a half-tile discontinuity on a shared corner
		 * must not assign the opposite side's height to an otherwise covered cell. */
		for (float dx : {0.0001f,xy-0.0001f}) for (float dy : {0.0001f,xy-0.0001f}) {
			float a = bottom.Height(x*xy+dx,y*xy+dy), b = top_base+top.Height(x*xy+dx,y*xy+dy);
			low = std::min(low,a); high = std::min(high,b); gap = std::max(gap,b-a);
		}
		int first = std::clamp(static_cast<int>(std::floor(low/dz+0.001f))+1,1,layers-1);
		int last = std::clamp(static_cast<int>(std::floor(high/dz+0.001f))+1,1,layers-1);
		/* The last material is an occupancy mask for soil and the ground
		 * contact above a support column. Doing this before meshing preserves
		 * identical hidden-face decisions for merged and unit-cell references. */
		if (!contacts) grid.Fill({x,y,0},{x+1,y+1,first},occluder);
		if (gap >= 0.0002f && last > first) {
			grid.Fill({x,y,first},{x+1,y+1,last},1);
			if (!contacts) grid.Fill({x,y,last},{x+1,y+1,last+1},occluder);
		}
	}
	/* Irregular stone clusters are explicitly procedural volumes, not a sampled
	 * sprite projection. The same 3D grain continues around every exposed corner. */
	auto hash = [](int x, int y, int z) {
		uint32_t value = static_cast<uint32_t>(x)*0x9E3779B9U ^ static_cast<uint32_t>(y)*0x85EBCA6BU ^ static_cast<uint32_t>(z)*0xC2B2AE35U ^ 0x7143U;
		value ^= value>>16; value *= 0x7FEB352DU; value ^= value>>15;
		return value;
	};
	static constexpr unsigned stone[] = {1,4,1,3,4,1,5,2,1,4,3,1,2,5,4,1};
	for (int z = 0; z < layers; ++z) for (int y = 0; y < extent; ++y) for (int x = 0; x < extent; ++x) {
		if (grid.Get(x,y,z) == 0 || grid.Get(x,y,z) == occluder) continue;
		if (grid.Get(x-1,y,z) && grid.Get(x+1,y,z) && grid.Get(x,y-1,z) && grid.Get(x,y+1,z)) continue;
		Vec3 p{(x+0.5f)*xy,(y+0.5f)*xy,(z-0.5f)*dz};
		/* Height units are compressed relative to XY in the original artwork.
		 * Taller source-space stones avoid stretched horizontal brick courses. */
		int cx = static_cast<int>(std::floor(p.x)), cy = static_cast<int>(std::floor(p.y)), cz = static_cast<int>(std::floor(p.z/2));
		float best = INFINITY, second = INFINITY;
		uint32_t chosen = 0;
		float centre_z = 0;
		if (lod < 2) for (int iz = cz-1; iz <= cz+1; ++iz) for (int iy = cy-1; iy <= cy+1; ++iy) for (int ix = cx-1; ix <= cx+1; ++ix) {
			uint32_t value = hash(ix,iy,iz);
			Vec3 centre{ix+0.25f+(value&7)/16.0f,iy+0.25f+((value>>3)&7)/16.0f,(iz+0.25f+((value>>6)&7)/16.0f)*2};
			Vec3 delta = p-centre; delta.z *= 0.5f;
			float distance = Dot(delta,delta);
			if (distance < best) { second = best; best = distance; chosen = value; centre_z = centre.z; }
			else second = std::min(second,distance);
		}
		unsigned material = stone[chosen%std::size(stone)];
		if (lod == 0) {
			if (p.z-centre_z > 0.35f) {
				const unsigned highlights[] = {0,7,1,11,8,10};
				material = highlights[material];
			} else if (p.z-centre_z < -0.5f) material = material == 4 ? 9 : material == 1 || material == 3 ? 2 : material;
			if (second-best < 0.045f) material = 6;
		}
		if (top.raised_half >= 0 && ((x > 0 && grid.Get(x-1,y,z) == 0) || (x+1 < extent && grid.Get(x+1,y,z) == 0) ||
			(y > 0 && grid.Get(x,y-1,z) == 0) || (y+1 < extent && grid.Get(x,y+1,z) == 0))) material += 11;
		grid.Fill({x,y,z},{x+1,y+1,z+1},material);
	}
	/* Coarser grids bound distant geometry cost. Keep their few cell quads:
	 * a long merged triangle can rasterize differently when a wall is subpixel. */
	return grid.Mesh(greedy && lod == 0,1,contacts ? UINT16_MAX : occluder-1).vertices;
}

} // namespace Renderer3D
#endif
