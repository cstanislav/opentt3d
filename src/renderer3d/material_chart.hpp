/* SPDX-License-Identifier: GPL-2.0-only */
/** @file material_chart.hpp Artist-selected component charts, clipped at repeat boundaries. */
#ifndef RENDERER3D_MATERIAL_CHART_HPP
#define RENDERER3D_MATERIAL_CHART_HPP

#include "geometry.hpp"

namespace Renderer3D {

/** X-facing ends, Y-facing sides and upward/downward surfaces. Coordinates are
 * normalized source-image rectangles, explicitly supplied by the model author. */
struct MaterialChart {
	std::array<TextureRegion,3> faces;
	std::array<float,2> repeat{}; ///< Model units per repetition; zero fits the component.
	bool lit = true;
};

inline std::vector<Vertex> ApplyMaterialChart(std::span<const Vertex> input, const MaterialChart &chart)
{
	std::vector<Vertex> result;
	if (input.empty()) return result;
	Vec3 low = input.front().position, high = low;
	for (const auto &v : input) {
		low = {std::min(low.x,v.position.x),std::min(low.y,v.position.y),std::min(low.z,v.position.z)};
		high = {std::max(high.x,v.position.x),std::max(high.y,v.position.y),std::max(high.z,v.position.z)};
	}
	struct Point { Vertex vertex; float s,t; };
	auto clip = [](const std::vector<Point> &polygon, bool horizontal, float edge, bool keep_above) {
		std::vector<Point> output;
		if (polygon.empty()) return output;
		auto distance = [&](const Point &p) { return ((horizontal ? p.s : p.t)-edge)*(keep_above ? 1 : -1); };
		Point previous = polygon.back();
		for (const auto &point : polygon) {
			float a = distance(previous), b = distance(point);
			if ((a >= 0) != (b >= 0)) {
				float fraction = a/(a-b);
				Point intersection = previous;
				intersection.vertex.position = previous.vertex.position+(point.vertex.position-previous.vertex.position)*fraction;
				intersection.s = std::lerp(previous.s,point.s,fraction);
				intersection.t = std::lerp(previous.t,point.t,fraction);
				output.push_back(intersection);
			}
			if (b >= 0) output.push_back(point);
			previous = point;
		}
		return output;
	};
	for (size_t first = 0; first < input.size(); first += 3) {
		Vec3 n = input[first].normal;
		unsigned face = std::abs(n.z) >= 0.45f ? 2 : std::abs(n.x) >= std::abs(n.y) ? 0 : 1;
		auto coordinate = [face](Vec3 p) { return face == 0 ? std::array<float,2>{p.y,p.z} : face == 1 ? std::array<float,2>{p.x,p.z} : std::array<float,2>{p.x,p.y}; };
		auto start = coordinate(low), end = coordinate(high);
		float step_s = chart.repeat[0] > 0 ? chart.repeat[0] : std::max(0.001f,end[0]-start[0]);
		float step_t = chart.repeat[1] > 0 ? chart.repeat[1] : std::max(0.001f,end[1]-start[1]);
		std::vector<Point> triangle;
		float min_s = 1e9f, max_s = -1e9f, min_t = 1e9f, max_t = -1e9f;
		for (size_t i = first; i < first+3; ++i) {
			auto uv = coordinate(input[i].position);
			float s = (uv[0]-start[0])/step_s, t = (uv[1]-start[1])/step_t;
			min_s = std::min(min_s,s); max_s = std::max(max_s,s);
			min_t = std::min(min_t,t); max_t = std::max(max_t,t);
			triangle.push_back({input[i],s,t});
		}
		const auto &crop = chart.faces[face];
		for (int s = static_cast<int>(std::floor(min_s)); s <= static_cast<int>(std::floor(max_s)); ++s) {
			for (int t = static_cast<int>(std::floor(min_t)); t <= static_cast<int>(std::floor(max_t)); ++t) {
				auto polygon = clip(clip(clip(clip(triangle,true,s,true),true,s+1,false),false,t,true),false,t+1,false);
				for (size_t i = 1; i+1 < polygon.size(); ++i) {
					Vec3 a = polygon[i].vertex.position-polygon[0].vertex.position, b = polygon[i+1].vertex.position-polygon[0].vertex.position;
					Vec3 cross{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};
					if (Dot(cross,cross) < 1e-12f) continue;
					for (size_t index : {size_t{0},i,i+1}) {
						Vertex vertex = polygon[index].vertex;
						vertex.texture = {std::lerp(crop.left,crop.right,std::clamp(polygon[index].s-s,0.0f,1.0f)),
							std::lerp(crop.bottom,crop.top,std::clamp(polygon[index].t-t,0.0f,1.0f)),-3};
						if (chart.lit) vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(vertex.surface) | SURFACE_SHADED);
						result.push_back(vertex);
					}
				}
			}
		}
	}
	return result;
}

} // namespace Renderer3D
#endif
