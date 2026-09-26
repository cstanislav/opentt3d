/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_visibility.hpp Conservative, camera-local voxel primitive visibility. */
#ifndef RENDERER3D_VOXEL_VISIBILITY_HPP
#define RENDERER3D_VOXEL_VISIBILITY_HPP

#include "camera.hpp"
#include <bit>
#include <limits>
#include <map>
#include <memory>
#include <unordered_map>

namespace Renderer3D {

/** A candidate is retained unless its projected bounding box provably contains
 * no raster sample. Arithmetic uncertainty and a full hardware subpixel protect
 * rounded edges. Near-plane intersections always retain the original triangles. */
class VoxelPixelProjector {
	std::array<float,16> matrix;
	std::array<double,3> origin, scale, centre, focus;
	double width, height, near, subpixel;
public:
	struct ProjectedPoint { double x = 0, y = 0, ex = 0, ey = 0; bool uncertain = true; };
	VoxelPixelProjector(const Camera &camera, const InstanceData &data, unsigned precision) : matrix(camera.Matrix()),
		origin{data.origin_opacity[0],data.origin_opacity[1],data.origin_opacity[2]},
		scale{data.scale_center[0],data.scale_center[0],data.scale_center[1]},
		centre{data.scale_center[2],data.scale_center[3],0},
		focus{camera.focus.x,camera.focus.y,camera.focus.z}, width(camera.width), height(camera.height),
		near(camera.Near()), subpixel(std::ldexp(1.0,-static_cast<int>(precision))) {}

	ProjectedPoint Project(Vec3 point) const
	{
		constexpr double factor = 8*std::numeric_limits<float>::epsilon();
		std::array<double,3> p{point.x,point.y,point.z}, relative{}, uncertainty{}, clip{}, error{};
		for (unsigned axis = 0; axis < 3; ++axis) {
			double local = (p[axis]-centre[axis])*scale[axis], world = origin[axis]+local;
			relative[axis] = world-focus[axis];
			uncertainty[axis] = factor*(std::abs(origin[axis])+std::abs(local)+std::abs(world)+std::abs(focus[axis])+std::abs(centre[axis]*scale[axis]))+1e-10;
		}
		for (unsigned component = 0; component < 3; ++component) {
			unsigned row = component == 2 ? 3 : component;
			clip[component] = matrix[12+row];
			double magnitude = std::abs(clip[component]);
			for (unsigned axis = 0; axis < 3; ++axis) {
				double coefficient = matrix[axis*4+row], product = coefficient*relative[axis];
				clip[component] += product; magnitude += std::abs(product);
				error[component] += std::abs(coefficient)*uncertainty[axis];
			}
			error[component] += factor*magnitude+1e-10;
		}
		if (!std::isfinite(clip[0]+clip[1]+clip[2]) || clip[2]-error[2] <= near) return {};
		double x = clip[0]/clip[2], y = clip[1]/clip[2];
		double ex = (error[0]+std::abs(x)*error[2])/(clip[2]-error[2]), ey = (error[1]+std::abs(y)*error[2])/(clip[2]-error[2]);
		double sx = (x+1)*width*0.5, sy = (1-y)*height*0.5;
		return {sx,sy,ex*width*0.5+factor*(std::abs(sx)+width)+subpixel,ey*height*0.5+factor*(std::abs(sy)+height)+subpixel,false};
	}

	bool TriangleVisible(const ProjectedPoint &a, const ProjectedPoint &b, const ProjectedPoint &c) const
	{
		if (a.uncertain || b.uncertain || c.uncertain) return true;
		auto edge = [](const ProjectedPoint &a, const ProjectedPoint &b, const ProjectedPoint &p) {
			double dx = b.x-a.x, dy = b.y-a.y, px = p.x-a.x, py = p.y-a.y;
			double edx = b.ex+a.ex, edy = b.ey+a.ey, epx = p.ex+a.ex, epy = p.ey+a.ey;
			double value = dx*py-dy*px;
			double error = std::abs(dx)*epy+std::abs(py)*edx+edx*epy+std::abs(dy)*epx+std::abs(px)*edy+edy*epx+1e-10;
			return std::array<double,2>{value,error};
		};
		/* Palette meshes use back-face culling. Front faces have negative area
		 * in the top-down framebuffer; uncertain subpixel winding is retained. */
		auto area = edge(a,b,c);
		if (area[0] > area[1]) return false;
		double min_x = std::min({a.x-a.ex,b.x-b.ex,c.x-c.ex}), max_x = std::max({a.x+a.ex,b.x+b.ex,c.x+c.ex});
		double min_y = std::min({a.y-a.ey,b.y-b.ey,c.y-c.ey}), max_y = std::max({a.y+a.ey,b.y+b.ey,c.y+c.ey});
		if (min_x > width-0.5 || max_x < 0.5 || min_y > height-0.5 || max_y < 0.5) return false;
		int left = static_cast<int>(std::ceil(std::max(0.5,min_x)-0.5)), right = static_cast<int>(std::floor(std::min(width-0.5,max_x)-0.5));
		int top = static_cast<int>(std::ceil(std::max(0.5,min_y)-0.5)), bottom = static_cast<int>(std::floor(std::min(height-0.5,max_y)-0.5));
		if (left > right || top > bottom) return false;
		if (static_cast<int64_t>(right-left+1)*(bottom-top+1) > 16) return true;
		for (int y = top; y <= bottom; ++y) for (int x = left; x <= right; ++x) {
			ProjectedPoint sample{x+0.5,y+0.5,0,0,false};
			auto e0 = edge(a,b,sample), e1 = edge(b,c,sample), e2 = edge(c,a,sample);
			if (e0[0] <= e0[1] && e1[0] <= e1[1] && e2[0] <= e2[1]) return true;
		}
		return false;
	}

	bool Visible(Vec3 low, Vec3 high) const
	{
		constexpr double error_factor = 8*std::numeric_limits<float>::epsilon();
		std::array<double,3> a{low.x,low.y,low.z}, b{high.x,high.y,high.z};
		std::array<double,3> relative{}, extent{}, uncertainty{};
		for (unsigned axis = 0; axis < 3; ++axis) {
			double point = (a[axis]+b[axis])*0.5;
			extent[axis] = (b[axis]-a[axis])*0.5*scale[axis];
			double local = (point-centre[axis])*scale[axis], world = origin[axis]+local;
			relative[axis] = world-focus[axis];
			uncertainty[axis] = error_factor*(std::abs(origin[axis])+std::abs(local)+std::abs(world)+std::abs(focus[axis])+std::abs(centre[axis]*scale[axis])+2*extent[axis])+1e-10;
		}
		std::array<double,3> clip{}, error{};
		for (unsigned component = 0; component < 3; ++component) {
			unsigned row = component == 2 ? 3 : component;
			clip[component] = matrix[12+row];
			double magnitude = std::abs(clip[component]);
			for (unsigned axis = 0; axis < 3; ++axis) {
				double coefficient = matrix[axis*4+row], product = coefficient*relative[axis];
				clip[component] += product; magnitude += std::abs(product)+std::abs(coefficient)*extent[axis];
				error[component] += std::abs(coefficient)*uncertainty[axis];
			}
			error[component] += error_factor*magnitude+1e-10;
		}
		double denominator = clip[2]-error[2];
		for (unsigned axis = 0; axis < 3; ++axis) denominator -= std::abs(matrix[axis*4+3])*extent[axis];
		if (!std::isfinite(clip[0]+clip[1]+clip[2]) || denominator <= near) return true;
		double x = clip[0]/clip[2], y = clip[1]/clip[2];
		double ex = error[0]+std::abs(x)*error[2], ey = error[1]+std::abs(y)*error[2];
		/* For a box displacement d, projected deviation from its centre is
		 * ((rowXY - centreNDC*rowW).d)/(centreW + rowW.d). Bound numerator
		 * and its positive denominator separately, retaining their correlation. */
		for (unsigned axis = 0; axis < 3; ++axis) {
			ex += std::abs(matrix[axis*4]-x*matrix[axis*4+3])*extent[axis];
			ey += std::abs(matrix[axis*4+1]-y*matrix[axis*4+3])*extent[axis];
		}
		double sx = (x+1)*width*0.5, sy = (1-y)*height*0.5;
		ex = ex/denominator*width*0.5+error_factor*(std::abs(sx)+width)+subpixel;
		ey = ey/denominator*height*0.5+error_factor*(std::abs(sy)+height)+subpixel;
		double min_x = sx-ex, max_x = sx+ex, min_y = sy-ey, max_y = sy+ey;
		return std::ceil(std::max(0.5,min_x)-0.5) <= std::floor(std::min(width-0.5,max_x)-0.5) &&
			std::ceil(std::max(0.5,min_y)-0.5) <= std::floor(std::min(height-0.5,max_y)-0.5);
	}
};

struct VisibleVoxelTriangle { uint32_t low, high; bool operator==(const VisibleVoxelTriangle &) const = default; };

inline std::array<uint32_t,7> VoxelVisibilityTransform(const InstanceData &data)
{
	std::array<uint32_t,7> result;
	for (unsigned i = 0; i < 3; ++i) result[i] = std::bit_cast<uint32_t>(data.origin_opacity[i]);
	for (unsigned i = 0; i < 4; ++i) result[3+i] = std::bit_cast<uint32_t>(data.scale_center[i]);
	return result;
}

class VoxelVisibilityCache {
	struct Key {
		const std::vector<Vertex> *mesh;
		std::array<uint32_t,7> transform;
		bool operator==(const Key &) const = default;
	};
	struct Hash {
		size_t operator()(const Key &key) const {
			size_t value = reinterpret_cast<uintptr_t>(key.mesh);
			for (auto word : key.transform) value = (value^(value>>27)^word)*0x9e3779b1U;
			return value;
		}
	};
	struct Bounds { Vec3 low{INFINITY,INFINITY,INFINITY}, high{-INFINITY,-INFINITY,-INFINITY}; };
	struct Geometry {
		std::vector<Bounds> blocks;
		std::vector<Vec3> positions;
		std::vector<uint32_t> indices;
		std::vector<VoxelPixelProjector::ProjectedPoint> projected;
		std::vector<uint64_t> projected_at;
		uint64_t projection = 0;
	};
	struct Visibility { uint64_t used = 0; std::vector<uint32_t> triangles; std::shared_ptr<const std::vector<uint64_t>> packed; bool triangles_ready = false; };
	std::optional<Camera> camera;
	unsigned precision = 0;
	uint64_t generation = 0;
	std::unordered_map<const std::vector<Vertex> *,Geometry> geometry;
	std::unordered_map<Key,Visibility,Hash> visibility;
	static constexpr size_t BLOCK_VERTICES = 64*3;
	static Key MakeKey(const std::vector<Vertex> &mesh, const InstanceData &data) {
		return {&mesh,VoxelVisibilityTransform(data)};
	}
	static void Extend(Bounds &bounds, Vec3 point) {
		bounds.low = {std::min(bounds.low.x,point.x),std::min(bounds.low.y,point.y),std::min(bounds.low.z,point.z)};
		bounds.high = {std::max(bounds.high.x,point.x),std::max(bounds.high.y,point.y),std::max(bounds.high.z,point.z)};
	}
public:
	/** Drop camera/transform results while retaining immutable mesh topology. */
	void Clear() { visibility.clear(); camera.reset(); }

	size_t MemoryBytes() const
	{
		size_t bytes = 0;
		for (const auto &[key,entry] : visibility) bytes += sizeof(key)+sizeof(entry)+entry.triangles.capacity()*sizeof(uint32_t)+(entry.packed ? entry.packed->capacity()*sizeof(uint64_t) : 0);
		for (const auto &[mesh,entry] : geometry) bytes += sizeof(entry)+entry.blocks.capacity()*sizeof(Bounds)+entry.positions.capacity()*sizeof(Vec3)+
			entry.indices.capacity()*sizeof(uint32_t)+entry.projected.capacity()*sizeof(VoxelPixelProjector::ProjectedPoint)+entry.projected_at.capacity()*sizeof(uint64_t);
		return bytes;
	}

	bool Begin(const Camera &current, unsigned subpixel_precision, size_t instances)
	{
		bool changed = !camera || *camera != current || precision != subpixel_precision;
		if (changed) { visibility.clear(); camera = current; precision = subpixel_precision; }
		if (visibility.size() > std::max<size_t>(256,instances*2)) std::erase_if(visibility,[&](const auto &entry) { return entry.second.used != generation; });
		++generation;
		return changed;
	}

	std::span<const uint32_t> Triangles(const std::vector<Vertex> &mesh, const InstanceData &data)
	{
		Key key = MakeKey(mesh,data);
		auto [entry,inserted] = visibility.try_emplace(key);
		auto &result = entry->second;
		result.used = generation;
		if (!inserted && result.triangles_ready) return result.triangles;
		auto [geometry_entry,new_geometry] = geometry.try_emplace(&mesh);
		auto &shape = geometry_entry->second;
		auto &blocks = shape.blocks;
		if (new_geometry) {
			blocks.resize((mesh.size()+BLOCK_VERTICES-1)/BLOCK_VERTICES);
			std::map<std::array<uint32_t,3>,uint32_t> positions;
			shape.indices.reserve(mesh.size());
			for (size_t i = 0; i < mesh.size(); ++i) {
				Extend(blocks[i/BLOCK_VERTICES],mesh[i].position);
				auto [entry,inserted] = positions.try_emplace(std::bit_cast<std::array<uint32_t,3>>(mesh[i].position),static_cast<uint32_t>(shape.positions.size()));
				if (inserted) shape.positions.push_back(mesh[i].position);
				shape.indices.push_back(entry->second);
			}
			shape.projected.resize(shape.positions.size()); shape.projected_at.resize(shape.positions.size());
		}
		VoxelPixelProjector project(*camera,data,precision);
		++shape.projection;
		auto point = [&](size_t index) -> const VoxelPixelProjector::ProjectedPoint & {
			uint32_t vertex = shape.indices[index];
			if (shape.projected_at[vertex] != shape.projection) {
				shape.projected[vertex] = project.Project(shape.positions[vertex]);
				shape.projected_at[vertex] = shape.projection;
			}
			return shape.projected[vertex];
		};
		for (size_t block = 0; block < blocks.size(); ++block) {
			if (!project.Visible(blocks[block].low,blocks[block].high)) continue;
			for (size_t first = block*BLOCK_VERTICES; first+2 < std::min(mesh.size(),(block+1)*BLOCK_VERTICES); first += 3) {
				if (project.TriangleVisible(point(first),point(first+1),point(first+2))) result.triangles.push_back(static_cast<uint32_t>(first));
			}
		}
		result.triangles_ready = true;
		return result.triangles;
	}

	bool HasPacked(const std::vector<Vertex> &mesh, const InstanceData &data) const
	{
		auto entry = visibility.find(MakeKey(mesh,data));
		return entry != visibility.end() && entry->second.packed != nullptr;
	}
	void Forget(const std::vector<Vertex> &mesh, const InstanceData &data) { visibility.erase(MakeKey(mesh,data)); }

	void AdoptPacked(const std::vector<Vertex> &mesh, const std::array<uint32_t,7> &transform, std::shared_ptr<const std::vector<uint64_t>> triangles)
	{
		auto &entry = visibility[{&mesh,transform}];
		entry.used = generation; entry.packed = std::move(triangles);
	}

	std::shared_ptr<const std::vector<uint64_t>> SharedPackedTriangles(const std::vector<Vertex> &mesh, const InstanceData &data, std::span<const uint32_t> indices, unsigned bits)
	{
		auto found = visibility.find(MakeKey(mesh,data));
		if (found != visibility.end() && found->second.packed) { found->second.used = generation; return found->second.packed; }
		auto triangles = Triangles(mesh,data);
		auto &entry = visibility.at(MakeKey(mesh,data));
		auto packed = std::make_shared<std::vector<uint64_t>>();
		packed->reserve(triangles.size());
		for (uint32_t first : triangles) packed->push_back(static_cast<uint64_t>(indices[first]) |
			(static_cast<uint64_t>(indices[first+1])<<bits) | (static_cast<uint64_t>(indices[first+2])<<(bits*2)));
		entry.packed = std::move(packed);
		/* Workers and render caches share the immutable result. Do not retain
		 * another original-index stream after it has been encoded losslessly. */
		std::vector<uint32_t>{}.swap(entry.triangles); entry.triangles_ready = false;
		return entry.packed;
	}
	std::span<const uint64_t> PackedTriangles(const std::vector<Vertex> &mesh, const InstanceData &data, std::span<const uint32_t> indices, unsigned bits)
	{
		return *SharedPackedTriangles(mesh,data,indices,bits);
	}
};

} // namespace Renderer3D
#endif
