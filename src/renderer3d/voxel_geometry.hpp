/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_geometry.hpp Authored cell volumes and palette-preserving surface meshing. */
#ifndef RENDERER3D_VOXEL_GEOMETRY_HPP
#define RENDERER3D_VOXEL_GEOMETRY_HPP

#include "geometry.hpp"
#include "voxel_volume.hpp"
#include "voxel_packed_mesh.hpp"
#include <limits>
#include <unordered_map>

namespace Renderer3D {

/** Native Classic grid: half a ground unit and one sprite-height unit. A tile
 * spans 32 cells and a terrain height level spans eight layers. */
inline constexpr Vec3 VOXEL_CELL_SIZE{0.5f,0.5f,1};

struct VoxelMaterial {
	std::array<uint8_t,6> colours{}; ///< -X,+X,-Y,+Y,-Z,+Z DOS palette indices.
};

struct VoxelMesh {
	std::vector<Vertex> vertices;
	size_t occupied = 0, exposed_faces = 0, quads = 0;
	Vec3 low{}, high{};
};

class VoxelGrid {
	friend class VoxelSource;
	std::array<int,3> size;
	std::vector<uint16_t> cells;
	std::vector<VoxelMaterial> materials;
	Vec3 origin, step;
	size_t Index(int x, int y, int z) const { return (static_cast<size_t>(z)*size[1]+y)*size[0]+x; }
public:
	VoxelGrid(std::array<int,3> size, std::vector<VoxelMaterial> materials, Vec3 origin = {}, Vec3 step = VOXEL_CELL_SIZE) :
		size(size), materials(std::move(materials)), origin(origin), step(step)
	{
		uint64_t count = 1;
		for (int extent : size) {
			if (extent <= 0 || extent > 1024) throw std::invalid_argument("Invalid voxel extent");
			count *= extent;
		}
		if (count > 16*1024*1024 || this->materials.size() > UINT16_MAX || this->materials.empty()) throw std::invalid_argument("Voxel model exceeds its cell/material budget");
		if (!(step.x > 0 && step.y > 0 && step.z > 0) || !std::isfinite(step.x+step.y+step.z+origin.x+origin.y+origin.z)) throw std::invalid_argument("Invalid voxel grid transform");
		cells.resize(static_cast<size_t>(count));
	}
	uint16_t Get(int x, int y, int z) const
	{
		return x < 0 || y < 0 || z < 0 || x >= size[0] || y >= size[1] || z >= size[2] ? 0 : cells[Index(x,y,z)];
	}

	/** Automatically aggregate authored cells. Any occupied cell retains its
	 * coarse block (thin posts cannot disappear); deterministic majority material
	 * retains original palette/remap indices. Clamp the mesh to the original
	 * occupied bounds, preserving ground contact and complete physical footprints. */
	VoxelMesh ReducedMesh(unsigned factor) const
	{
		if (factor == 1) return Mesh();
		if (factor < 2 || factor > 16 || (factor & (factor-1)) != 0) throw std::invalid_argument("Invalid automatic voxel LOD factor");
		std::array<int,3> extent;
		for (unsigned axis = 0; axis < 3; ++axis) extent[axis] = (size[axis]+factor-1)/factor;
		VoxelGrid reduced(extent,materials,origin,step*factor);
		Vec3 low{INFINITY,INFINITY,INFINITY}, high{-INFINITY,-INFINITY,-INFINITY};
		std::vector<unsigned> counts(materials.size()+1);
		std::vector<uint16_t> used;
		for (int z = 0; z < extent[2]; ++z) for (int y = 0; y < extent[1]; ++y) for (int x = 0; x < extent[0]; ++x) {
			for (int dz = z*factor; dz < std::min<int>((z+1)*factor,size[2]); ++dz)
			for (int dy = y*factor; dy < std::min<int>((y+1)*factor,size[1]); ++dy)
			for (int dx = x*factor; dx < std::min<int>((x+1)*factor,size[0]); ++dx) {
				uint16_t cell = Get(dx,dy,dz);
				if (cell == 0) continue;
				if (counts[cell]++ == 0) used.push_back(cell);
				low = {std::min(low.x,origin.x+dx*step.x),std::min(low.y,origin.y+dy*step.y),std::min(low.z,origin.z+dz*step.z)};
				high = {std::max(high.x,origin.x+(dx+1)*step.x),std::max(high.y,origin.y+(dy+1)*step.y),std::max(high.z,origin.z+(dz+1)*step.z)};
			}
			uint16_t selected = 0;
			for (uint16_t cell : used) if (selected == 0 || counts[cell] > counts[selected] || (counts[cell] == counts[selected] && cell < selected)) selected = cell;
			if (selected != 0) reduced.Fill({x,y,z},{x+1,y+1,z+1},selected);
			for (uint16_t cell : used) counts[cell] = 0;
			used.clear();
		}
		auto mesh = reduced.Mesh();
		if (mesh.occupied == 0) return mesh;
		for (auto &vertex : mesh.vertices) {
			vertex.position = {std::clamp(vertex.position.x,low.x,high.x),std::clamp(vertex.position.y,low.y,high.y),std::clamp(vertex.position.z,low.z,high.z)};
		}
		mesh.low = low; mesh.high = high;
		return mesh;
	}
	void Fill(std::array<int,3> low, std::array<int,3> high, uint16_t material)
	{
		if (material > materials.size()) throw std::invalid_argument("Unknown voxel material");
		for (unsigned axis = 0; axis < 3; ++axis) if (low[axis] < 0 || high[axis] > size[axis] || low[axis] >= high[axis]) throw std::invalid_argument("Voxel box is outside its authored grid");
		for (int z = low[2]; z < high[2]; ++z) for (int y = low[1]; y < high[1]; ++y) {
			std::fill(cells.begin()+Index(low[0],y,z),cells.begin()+Index(high[0]-1,y,z)+1,material);
		}
	}

	std::shared_ptr<const PackedVoxelMesh> Pack(const VoxelMesh &mesh, bool pixel_cull = false) const { return PackVoxelMesh(mesh.vertices,size,origin,step,pixel_cull); }

	std::shared_ptr<const VoxelVolume> Volume() const
	{
		auto volume = std::make_shared<VoxelVolume>();
		auto &words = volume->words;
		uint32_t material_offset = VoxelVolume::HEADER_WORDS, cell_offset = material_offset+static_cast<uint32_t>(materials.size())*2;
		words.resize(cell_offset+(cells.size()+1)/2);
		for (unsigned axis = 0; axis < 3; ++axis) words[axis] = size[axis];
		words[3] = materials.size(); words[7] = cell_offset; words[11] = material_offset;
		words[21] = std::bit_cast<uint32_t>(1.0f); words[22] = 0;
		words[4] = std::bit_cast<uint32_t>(origin.x); words[5] = std::bit_cast<uint32_t>(origin.y); words[6] = std::bit_cast<uint32_t>(origin.z);
		words[8] = std::bit_cast<uint32_t>(step.x); words[9] = std::bit_cast<uint32_t>(step.y); words[10] = std::bit_cast<uint32_t>(step.z);
		for (size_t material = 0; material < materials.size(); ++material) for (unsigned face = 0; face < 6; ++face) words[material_offset+material*2+(face>>2)] |= static_cast<uint32_t>(materials[material].colours[face]) << (8*(face&3));
		std::array<int,3> low = size, high{};
		for (size_t i = 0; i < cells.size(); ++i) {
			words[cell_offset+(i>>1)] |= static_cast<uint32_t>(cells[i]) << (16*(i&1));
			if (cells[i] == 0) continue;
			int x = i%size[0], y = (i/size[0])%size[1], z = i/(static_cast<size_t>(size[0])*size[1]);
			low = {std::min(low[0],x),std::min(low[1],y),std::min(low[2],z)};
			high = {std::max(high[0],x+1),std::max(high[1],y+1),std::max(high[2],z+1)};
		}
		for (unsigned axis = 0; axis < 3; ++axis) { words[12+axis] = low[axis]; words[16+axis] = high[axis]; }
		if (low[0] >= high[0]) return volume;
		/* Surface acceleration retains the original packed cell array above. A
		 * second word per cell packs material, six exposed faces and a conservative
		 * Chebyshev distance to any exposed cell. It skips only empty surface work,
		 * never replaces authored occupancy or geometry with a coarser model. */
		uint32_t surface_offset = words.size();
		words[20] = surface_offset;
		words.resize(words.size()+cells.size());
		std::vector<uint8_t> distance(cells.size(),255);
		struct SliceBounds { int low_u = std::numeric_limits<int>::max(), low_v = std::numeric_limits<int>::max(), high_u = 0, high_v = 0; };
		std::array<std::vector<SliceBounds>,6> slices;
		for (unsigned face = 0; face < 6; ++face) slices[face].resize(size[face/2]);
		for (int z = 0; z < size[2]; ++z) for (int y = 0; y < size[1]; ++y) for (int x = 0; x < size[0]; ++x) {
			size_t index = Index(x,y,z);
			uint32_t faces = 0;
			if (cells[index] != 0) {
				faces = (Get(x-1,y,z) == 0) | ((Get(x+1,y,z) == 0)<<1) | ((Get(x,y-1,z) == 0)<<2) |
					((Get(x,y+1,z) == 0)<<3) | ((Get(x,y,z-1) == 0)<<4) | ((Get(x,y,z+1) == 0)<<5);
				if (faces != 0) distance[index] = 0;
			}
			words[surface_offset+index] = cells[index] | (faces<<16);
			std::array<int,3> cell{x,y,z};
			for (unsigned face = 0; face < 6; ++face) if ((faces&(1U<<face)) != 0) {
				unsigned axis = face/2, u = (axis+1)%3, v = (axis+2)%3;
				auto &slice = slices[face][cell[axis]];
				slice.low_u = std::min(slice.low_u,cell[u]); slice.high_u = std::max(slice.high_u,cell[u]+1);
				slice.low_v = std::min(slice.low_v,cell[v]); slice.high_v = std::max(slice.high_v,cell[v]+1);
			}
		}
		Scene planes;
		for (unsigned face = 0; face < 6; ++face) for (int layer = 0; layer < size[face/2]; ++layer) {
			const auto &slice = slices[face][layer];
			if (slice.low_u >= slice.high_u) continue;
			unsigned axis = face/2, u = (axis+1)%3, v = (axis+2)%3;
			auto point = [&](int du, int dv) {
				std::array<float,3> p{};
				p[axis] = layer+(face&1U); p[u] = du; p[v] = dv;
				return origin+Vec3{p[0]*step.x,p[1]*step.y,p[2]*step.z};
			};
			Vec3 a = point(slice.low_u-1,slice.low_v-1), b = point(slice.high_u+1,slice.low_v-1);
			Vec3 c = point(slice.high_u+1,slice.high_v+1), d = point(slice.low_u-1,slice.high_v+1);
			if ((face&1U) != 0) planes.Quad(a,b,c,d,{}); else planes.Quad(a,d,c,b,{});
		}
		volume->slices = std::move(planes.vertices);
		for (int direction : {1,-1}) {
			for (int z = direction > 0 ? 0 : size[2]-1; z >= 0 && z < size[2]; z += direction)
			for (int y = direction > 0 ? 0 : size[1]-1; y >= 0 && y < size[1]; y += direction)
			for (int x = direction > 0 ? 0 : size[0]-1; x >= 0 && x < size[0]; x += direction) {
				auto &value = distance[Index(x,y,z)];
				if (value == 0) continue;
				for (int dz = -1; dz <= 0; ++dz) for (int dy = -1; dy <= 1; ++dy) for (int dx = -1; dx <= 1; ++dx) {
					if (dz == 0 && (dy > 0 || (dy == 0 && dx >= 0))) continue;
					int nx = x+dx*direction, ny = y+dy*direction, nz = z+dz*direction;
					if (nx < 0 || ny < 0 || nz < 0 || nx >= size[0] || ny >= size[1] || nz >= size[2]) continue;
					value = std::min<unsigned>(value,static_cast<unsigned>(distance[Index(nx,ny,nz)])+1);
				}
			}
		}
		for (size_t i = 0; i < cells.size(); ++i) words[surface_offset+i] |= static_cast<uint32_t>(distance[i])<<24;
		/* Rasterized unit edges can cover a pixel just outside their analytic
		 * bounds after subpixel rounding. The proxy/traversal has a guard cell;
		 * the immutable occupied bounds and all actual cells remain unchanged. */
		Vec3 a = origin+Vec3{(low[0]-1)*step.x,(low[1]-1)*step.y,(low[2]-1)*step.z};
		Vec3 b = origin+Vec3{(high[0]+1)*step.x,(high[1]+1)*step.y,(high[2]+1)*step.z};
		Scene box;
		box.Quad({a.x,a.y,a.z},{a.x,a.y,b.z},{a.x,b.y,b.z},{a.x,b.y,a.z},{});
		box.Quad({b.x,a.y,a.z},{b.x,b.y,a.z},{b.x,b.y,b.z},{b.x,a.y,b.z},{});
		box.Quad({a.x,a.y,a.z},{b.x,a.y,a.z},{b.x,a.y,b.z},{a.x,a.y,b.z},{});
		box.Quad({a.x,b.y,a.z},{a.x,b.y,b.z},{b.x,b.y,b.z},{b.x,b.y,a.z},{});
		box.Quad({a.x,a.y,a.z},{a.x,b.y,a.z},{b.x,b.y,a.z},{b.x,a.y,a.z},{});
		box.Quad({a.x,a.y,b.z},{b.x,a.y,b.z},{b.x,b.y,b.z},{a.x,b.y,b.z},{});
		volume->bounds = std::move(box.vertices);
		return volume;
	}

	/** Only occupied-to-empty boundaries are emitted. Greedy rectangles merge
	 * coplanar equal-colour faces without changing shape, palette or normals. */
	VoxelMesh Mesh(bool greedy = true, uint16_t first_material = 1, uint16_t last_material = UINT16_MAX, bool compact_boundary = true) const
	{
		VoxelMesh result;
		std::array<int,3> low = size, high{};
		for (int z = 0; z < size[2]; ++z) for (int y = 0; y < size[1]; ++y) for (int x = 0; x < size[0]; ++x) {
			uint16_t cell = cells[Index(x,y,z)];
			if (cell == 0 || cell < first_material || cell > last_material) continue;
			++result.occupied;
			low = {std::min(low[0],x),std::min(low[1],y),std::min(low[2],z)};
			high = {std::max(high[0],x+1),std::max(high[1],y+1),std::max(high[2],z+1)};
		}
		if (result.occupied == 0) return result;
		result.low = {INFINITY,INFINITY,INFINITY}; result.high = {-INFINITY,-INFINITY,-INFINITY};
		Scene mesh;
		struct Rectangle {
			unsigned axis, positive;
			std::array<int,3> corner;
			int width, height;
			uint16_t colour;
		};
		std::vector<Rectangle> rectangles;
		/* A complete surface can share exact rectangle-edge cuts. Independently
		 * requested material partitions retain the unit boundary topology, since
		 * their adjacent partition may be meshed in a later call. */
		bool compact_polygons = compact_boundary && greedy;
		bool shared_edges = compact_polygons && first_material == 1 && last_material >= materials.size();
		auto finish = [&](size_t first, uint16_t colour) {
			for (size_t i = first; i < mesh.vertices.size(); ++i) {
				auto &vertex = mesh.vertices[i];
				vertex.texture = {(colour-0.5f)/256,0.5f,-3};
				vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette) | SURFACE_UNLIT);
				Vec3 p = vertex.position;
				result.low = {std::min(result.low.x,p.x),std::min(result.low.y,p.y),std::min(result.low.z,p.z)};
				result.high = {std::max(result.high.x,p.x),std::max(result.high.y,p.y),std::max(result.high.z,p.z)};
			}
		};
		for (unsigned axis = 0; axis < 3; ++axis) for (unsigned positive = 0; positive < 2; ++positive) {
			unsigned u = (axis+1)%3, v = (axis+2)%3;
			/* Thin components occupy only a small part of their shared volume.
			 * Restrict the face scan, but still query neighbours in the full grid
			 * so material partitions never expose their internal interfaces. */
			int width = high[u]-low[u], height = high[v]-low[v];
			std::vector<uint16_t> mask(static_cast<size_t>(width)*height);
			std::vector<uint8_t> colour_edges(static_cast<size_t>(width)*height);
			for (int layer = low[axis]; layer < high[axis]; ++layer) {
				auto face_colour = [&](std::array<int,3> p) -> uint16_t {
					uint16_t cell = Get(p[0],p[1],p[2]);
					p[axis] += positive ? 1 : -1;
					return cell != 0 && Get(p[0],p[1],p[2]) == 0 ? 1U+materials[cell-1].colours[axis*2+positive] : 0;
				};
				for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
					std::array<int,3> p{}; p[axis] = layer; p[u] = x+low[u]; p[v] = y+low[v];
					uint16_t cell = Get(p[0],p[1],p[2]);
					uint16_t colour = face_colour(p);
					bool exposed = colour != 0 && cell >= first_material && cell <= last_material;
					uint8_t edges = 0;
					if (compact_polygons && exposed) for (unsigned tangent : {u,v}) for (int side : {-1,1}) {
						auto neighbour = p; neighbour[tangent] += side;
						uint16_t adjacent = face_colour(neighbour);
						if (adjacent != colour) edges |= 1U<<((tangent == u ? 0 : 2)+(side > 0));
					}
					/* Keep reference diagonals at colour AND occupied/empty edges.
					 * A projected collinear silhouette can round non-convexly too:
					 * an interior ear then covers a pixel outside its unit faces.
					 * Unit boundary vertices alone do not preserve that silhouette. */
					mask[static_cast<size_t>(y)*width+x] = exposed ? colour : 0;
					colour_edges[static_cast<size_t>(y)*width+x] = edges;
					result.exposed_faces += exposed;
				}
				for (int y = 0; y < height; ++y) for (int x = 0; x < width;) {
					uint16_t colour = mask[static_cast<size_t>(y)*width+x];
					if (colour == 0) { ++x; continue; }
					int w = 1, h = 1;
					if (greedy) {
						while (x+w < width && mask[static_cast<size_t>(y)*width+x+w] == colour) ++w;
						for (; y+h < height; ++h) {
							bool same = true;
							for (int dx = 0; dx < w; ++dx) same &= mask[static_cast<size_t>(y+h)*width+x+dx] == colour;
							if (!same) break;
						}
					}
					auto point = [&](float a, float b) {
						std::array<float,3> p{}; p[axis] = static_cast<float>(layer+positive); p[u] = a+low[u]; p[v] = b+low[v];
						return origin+Vec3{p[0]*step.x,p[1]*step.y,p[2]*step.z};
					};
					size_t first = mesh.vertices.size();
					/* Guard strips affect triangulation, not the logical greedy-quad
					 * count. Compact polygons defer triangulation until their edge cuts are
					 * known. The reference/contact fallback retains its original unit
					 * boundary fans and cell strips, including depth interpolation. */
					if (compact_polygons) {
						std::array<int,3> corner{};
						corner[axis] = layer+positive; corner[u] = x+low[u]; corner[v] = y+low[v];
						auto rectangle = [&](int dx, int dy, int rw, int rh) {
							auto cell = corner; cell[u] += dx; cell[v] += dy;
							rectangles.push_back({axis,positive,cell,rw,rh,colour});
						};
						/* Thin strips save no triangles by making long boundary ears.
						 * Their projected collinear vertices can round either side of a
						 * material edge; retain the exact unit-cell diagonals instead. */
						if (w == 1 || h == 1) {
							for (int dy = 0; dy < h; ++dy) for (int dx = 0; dx < w; ++dx) {
								rectangle(dx,dy,1,1);
							}
						} else {
							bool left = false, right = false, bottom = false, top = false;
							for (int dy = 0; dy < h; ++dy) {
								left |= (colour_edges[static_cast<size_t>(y+dy)*width+x]&1U) != 0;
								right |= (colour_edges[static_cast<size_t>(y+dy)*width+x+w-1]&2U) != 0;
							}
							for (int dx = 0; dx < w; ++dx) {
								bottom |= (colour_edges[static_cast<size_t>(y)*width+x+dx]&4U) != 0;
								top |= (colour_edges[static_cast<size_t>(y+h-1)*width+x+dx]&8U) != 0;
							}
							for (int dx = 0; dx < w; ++dx) {
								if (bottom) rectangle(dx,0,1,1);
								if (top) rectangle(dx,h-1,1,1);
							}
							for (int dy = bottom; dy < h-top; ++dy) {
								if (left) rectangle(0,dy,1,1);
								if (right) rectangle(w-1,dy,1,1);
							}
							if (w > left+right && h > bottom+top) rectangle(left,bottom,w-left-right,h-bottom-top);
						}
					} else if (w*h <= w+h) {
						for (int dy = 0; dy < h; ++dy) for (int dx = 0; dx < w; ++dx) {
							Vec3 a = point(x+dx,y+dy), b = point(x+dx+1,y+dy), c = point(x+dx+1,y+dy+1), d = point(x+dx,y+dy+1);
							if (positive) mesh.Quad(a,b,c,d,{}); else mesh.Quad(a,d,c,b,{});
						}
					} else {
						Vec3 centre = point(x+w*0.5f,y+h*0.5f);
						auto triangle = [&](Vec3 a, Vec3 b) { if (positive) mesh.Triangle(centre,a,b,{}); else mesh.Triangle(centre,b,a,{}); };
						for (int dx = 0; dx < w; ++dx) {
							triangle(point(x+dx,y),point(x+dx+1,y));
							triangle(point(x+dx+1,y+h),point(x+dx,y+h));
						}
						for (int dy = 0; dy < h; ++dy) {
							triangle(point(x+w,y+dy),point(x+w,y+dy+1));
							triangle(point(x,y+dy+1),point(x,y+dy));
						}
					}
					finish(first,colour);
					++result.quads;
					for (int dy = 0; dy < h; ++dy) std::fill_n(mask.begin()+static_cast<size_t>(y+dy)*width+x,w,0);
					x += w;
				}
			}
		}
		if (compact_polygons) {
			using CellPoint = std::array<int,3>;
			auto corners = [](const Rectangle &rect) {
				std::array<CellPoint,4> points{rect.corner,rect.corner,rect.corner,rect.corner};
				unsigned u = (rect.axis+1)%3, v = (rect.axis+2)%3;
				points[1][u] += rect.width; points[2][u] += rect.width;
				points[2][v] += rect.height; points[3][v] += rect.height;
				return points;
			};
			auto key = [](unsigned axis, const CellPoint &point) {
				/* Grid coordinates include the far edge at 1024, hence 11 bits. */
				return (axis<<22) | (static_cast<uint32_t>(point[(axis+1)%3])<<11) | static_cast<uint32_t>(point[(axis+2)%3]);
			};
			std::unordered_map<uint32_t,std::vector<int>> cuts;
			cuts.reserve(rectangles.size()*4);
			for (const auto &rect : rectangles) for (const auto &point : corners(rect)) {
				for (unsigned axis = 0; axis < 3; ++axis) cuts[key(axis,point)].push_back(point[axis]);
			}
			/* Keep unit vertices at actual colour/crease boundaries. GPU subpixel
			 * rounding makes a long projected edge differ from its cell segments
			 * even when the world points are mathematically collinear. Only the
			 * artificial cuts between coplanar equal-colour rectangles may simplify. */
			for (const auto &rect : rectangles) {
				auto points = corners(rect);
				auto face_colour = [&](CellPoint point) -> unsigned {
					uint16_t cell = Get(point[0],point[1],point[2]);
					point[rect.axis] += rect.positive ? 1 : -1;
					return cell != 0 && Get(point[0],point[1],point[2]) == 0 ? 1U+materials[cell-1].colours[rect.axis*2+rect.positive] : 0;
				};
				for (unsigned edge = 0; edge < 4; ++edge) {
					CellPoint a = points[edge], b = points[(edge+1)%4];
					unsigned axis = 0;
					while (a[axis] == b[axis]) ++axis;
					unsigned across = 3-axis-rect.axis;
					auto &line = cuts[key(axis,a)];
					for (int cell = std::min(a[axis],b[axis]); cell < std::max(a[axis],b[axis]); ++cell) {
						CellPoint p = a; p[axis] = cell; p[rect.axis] -= rect.positive; --p[across];
						unsigned before = face_colour(p);
						++p[across];
						if (!shared_edges || before != face_colour(p)) { line.push_back(cell); line.push_back(cell+1); }
					}
				}
			}
			for (auto &[line,points] : cuts) {
				std::sort(points.begin(),points.end());
				points.erase(std::unique(points.begin(),points.end()),points.end());
			}
			auto world = [&](const CellPoint &point) { return origin+Vec3{point[0]*step.x,point[1]*step.y,point[2]*step.z}; };
			std::vector<CellPoint> boundary;
			std::vector<size_t> remaining;
			for (const auto &rect : rectangles) {
				boundary.clear();
				auto points = corners(rect);
				for (unsigned edge = 0; edge < 4; ++edge) {
					CellPoint a = points[edge], b = points[(edge+1)%4];
					unsigned axis = 0;
					while (a[axis] == b[axis]) ++axis;
					const auto &line = cuts.at(key(axis,a));
					if (a[axis] < b[axis]) {
						auto end = std::lower_bound(line.begin(),line.end(),b[axis]);
						for (auto it = std::lower_bound(line.begin(),line.end(),a[axis]); it != end; ++it) {
							a[axis] = *it; boundary.push_back(a);
						}
					} else {
						auto end = std::upper_bound(line.begin(),line.end(),b[axis]);
						for (auto it = std::upper_bound(line.begin(),line.end(),a[axis]); it != end;) {
							a[axis] = *--it; boundary.push_back(a);
						}
					}
				}
				size_t first = mesh.vertices.size();
				if (boundary.size() == 4) {
					if (rect.positive) mesh.Quad(world(boundary[0]),world(boundary[1]),world(boundary[2]),world(boundary[3]),{});
					else mesh.Quad(world(boundary[0]),world(boundary[3]),world(boundary[2]),world(boundary[1]),{});
					finish(first,rect.colour);
					continue;
				}
				unsigned u = (rect.axis+1)%3, v = (rect.axis+2)%3;
				auto cross = [&](const CellPoint &a, const CellPoint &b, const CellPoint &c) {
					return (b[u]-a[u])*(c[v]-a[v])-(b[v]-a[v])*(c[u]-a[u]);
				};
				auto triangle = [&](const CellPoint &a, const CellPoint &b, const CellPoint &c) {
					if (rect.positive) mesh.Triangle(world(a),world(b),world(c),{});
					else mesh.Triangle(world(a),world(c),world(b),{});
				};
				remaining.clear();
				for (size_t i = 0; i < boundary.size(); ++i) remaining.push_back(i);
				/* Convex ear clipping preserves the collinear edge vertices without
				 * adding a centre/fan. A diagonal must not skip a remaining vertex:
				 * doing so would recreate a T-junction on the last straight edge. */
				while (remaining.size() > 3) {
					bool clipped = false;
					for (size_t i = 0; i < remaining.size(); ++i) {
						size_t ia = remaining[(i+remaining.size()-1)%remaining.size()], ib = remaining[i], ic = remaining[(i+1)%remaining.size()];
						const auto &a = boundary[ia], &b = boundary[ib], &c = boundary[ic];
						if (cross(a,b,c) <= 0) continue;
						bool skips = false;
						for (size_t index : remaining) if (index != ia && index != ib && index != ic) {
							const auto &p = boundary[index];
							if (cross(a,c,p) == 0 && (p[u]-a[u])*(p[u]-c[u])+(p[v]-a[v])*(p[v]-c[v]) <= 0) { skips = true; break; }
						}
						if (skips) continue;
						triangle(a,b,c);
						remaining.erase(remaining.begin()+i);
						clipped = true;
						break;
					}
					if (!clipped) throw std::logic_error("Could not triangulate a voxel boundary");
				}
				triangle(boundary[remaining[0]],boundary[remaining[1]],boundary[remaining[2]]);
				finish(first,rect.colour);
			}
		}
		result.vertices = std::move(mesh.vertices);
		/* Finished voxel surfaces are immutable, including the many generated
		 * slope/fence/rail variants. Do not retain geometric growth capacity in
		 * those long-lived caches after authoring the final triangle stream. */
		result.vertices.shrink_to_fit();
		return result;
	}
};

/** Lossless retained authoring cells. Dense grids are needed only while meshing
 * or building a diagnostic reference, never for ordinary mesh rendering. The
 * palette is supplied from the catalogue so every model shares that ownership. */
class VoxelSource {
	struct Run { uint32_t first; uint16_t length, material; };
	static_assert(sizeof(Run) == 8);
	std::array<int,3> size;
	Vec3 origin, step;
	std::vector<Run> runs;
public:
	explicit VoxelSource(const VoxelGrid &grid) : size(grid.size), origin(grid.origin), step(grid.step)
	{
		for (size_t first = 0; first < grid.cells.size();) {
			uint16_t material = grid.cells[first];
			if (material == 0) { ++first; continue; }
			size_t end = first+1;
			while (end < grid.cells.size() && end-first < UINT16_MAX && grid.cells[end] == material) ++end;
			runs.push_back({static_cast<uint32_t>(first),static_cast<uint16_t>(end-first),material});
			first = end;
		}
		runs.shrink_to_fit();
	}
	VoxelGrid Expand(const std::vector<VoxelMaterial> &materials) const
	{
		VoxelGrid grid(size,materials,origin,step);
		for (const auto &run : runs) {
			if (run.material > materials.size()) throw std::invalid_argument("Missing retained voxel source material");
			std::fill_n(grid.cells.begin()+run.first,run.length,run.material);
		}
		return grid;
	}
	size_t StorageBytes() const { return runs.capacity()*sizeof(Run); }
};

} // namespace Renderer3D
#endif
