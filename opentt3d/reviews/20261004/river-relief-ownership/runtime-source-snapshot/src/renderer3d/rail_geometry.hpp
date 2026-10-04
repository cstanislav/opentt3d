/* SPDX-License-Identifier: GPL-2.0-only */
/** @file rail_geometry.hpp Authored rail sections, sleepers and guideways.
 * The six routes follow OpenTTD track endpoints. No topology is extracted from
 * artwork; terrain charts and raised components are deliberately independent. */
#ifndef RENDERER3D_RAIL_GEOMETRY_HPP
#define RENDERER3D_RAIL_GEOMETRY_HPP

#include "terrain_geometry.hpp"
#include "voxel_geometry.hpp"
#include <limits>
#include <numbers>

namespace Renderer3D {

enum class RailMaterial : unsigned { Ballast, Supports, Rails, ReservedRails, Fasteners, Count };
struct RailAssembly {
	std::array<std::vector<Vertex>,static_cast<unsigned>(RailMaterial::Count)> parts;
};

struct RailPathFrame { Vec3 point, across; };

/** X, Y, upper, lower, left, right, in the upstream Track order. Diagonal
 * half-tile routes are straight chords, just like the simulation and artwork. */
inline RailPathFrame RailPath(unsigned track, float t)
{
	if (track == 0) return {{16*t,8,0},{0,1,0}};
	if (track == 1) return {{8,16*t,0},{-1,0,0}};
	constexpr float diagonal = std::numbers::sqrt2_v<float>/2;
	RailPathFrame frame{{8*t,8*(1-t),0},{diagonal,diagonal,0}};
	bool mirror_x = track == 3 || track == 4, mirror_y = track == 3 || track == 5;
	if (mirror_x) { frame.point.x = 16-frame.point.x; frame.across.x = -frame.across.x; }
	if (mirror_y) { frame.point.y = 16-frame.point.y; frame.across.y = -frame.across.y; }
	if (mirror_x != mirror_y) frame.across = frame.across*-1;
	return frame;
}

/** A closed cross-section swept between adjacent tile ports. Profile X is the
 * cross-track distance, Z is height; caps are present for isolated end pieces. */
inline void RailSweep(Scene &mesh, unsigned track, std::span<const Vec3> profile, unsigned steps, Rgb colour, float offset = 0, float begin = 0, float end = 1)
{
	auto ring = [&](float t, const Vec3 &p) {
		auto frame = RailPath(track,t);
		Vec3 point = frame.point+frame.across*(offset+p.x)+Vec3{0,0,p.z};
		/* Miter the ends at the actual tile edges. Clamping perpendicular end
		 * rings bent the outer rails and pinched the gauge at every tile join. */
		if (track >= 2) {
			Vec3 along{frame.across.y,-frame.across.x,0};
			if (t == 0) point = point+along*((frame.point.x-point.x)/along.x);
			if (t == 1) point = point+along*((frame.point.y-point.y)/along.y);
		}
		return point;
	};
	for (unsigned section = 0; section < steps; ++section) {
		float a = std::lerp(begin,end,static_cast<float>(section)/steps), b = std::lerp(begin,end,static_cast<float>(section+1)/steps);
		for (size_t i = 0; i < profile.size(); ++i) {
			size_t j = (i+1)%profile.size();
			mesh.Quad(ring(a,profile[i]),ring(a,profile[j]),ring(b,profile[j]),ring(b,profile[i]),colour);
		}
	}
	for (size_t i = 1; i+1 < profile.size(); ++i) {
		mesh.Triangle(ring(begin,profile[0]),ring(begin,profile[i+1]),ring(begin,profile[i]),colour);
		mesh.Triangle(ring(end,profile[0]),ring(end,profile[i]),ring(end,profile[i+1]),colour);
	}
}

inline float RailPathDistance(Vec3 point, unsigned track)
{
	float distance = std::numeric_limits<float>::infinity();
	unsigned count = 1;
	Vec3 a = RailPath(track,0).point;
	for (unsigned i = 1; i <= count; ++i) {
		Vec3 b = RailPath(track,static_cast<float>(i)/count).point, direction = b-a;
		float t = std::clamp(Dot(point-a,direction)/Dot(direction,direction),0.0f,1.0f);
		Vec3 delta = point-(a+direction*t);
		distance = std::min(distance,Dot(delta,delta));
		a = b;
	}
	return std::sqrt(distance);
}

struct RailSupportContact { float smooth, stepped; };

/** Read-only support metadata for the exact quarter-cell running surface. */
struct RailSupportSurface {
	Vec3 origin;
	TileSurface surface;
	unsigned kind = 0, tracks = 0;
	std::optional<RailSupportContact> Contact(Vec3 point) const
	{
		Vec3 local = point-origin;
		if (local.x < 0 || local.y < 0 || local.x >= 16 || local.y >= 16) return {};
		float nearest = INFINITY;
		for (unsigned track = 0; track < 6; ++track) if ((tracks & (1U<<track)) != 0) nearest = std::min(nearest,RailPathDistance({local.x,local.y,0},track));
		if (nearest > 1.75f) return {};
		float x = std::floor(local.x*4)*0.25f, y = std::floor(local.y*4)*0.25f, highest = -INFINITY;
		/* A point on a step edge touches both closed cell volumes. In a
		 * descending section the previous cell, not floor(point), is higher. */
		float left = x > 0 && local.x == x ? x-0.25f : x, back = y > 0 && local.y == y ? y-0.25f : y;
		for (float px : {left,x+0.25f}) for (float py : {back,y+0.25f}) highest = std::max(highest,surface.Height(px,py));
		/* Preserve the authored half-unit running datum. Monorail underframes
		 * straddle their raised central beam; maglev keeps a quarter-unit gap
		 * over the slab rather than riding atop its outside guide walls. */
		return RailSupportContact{origin.z+surface.Height(local.x,local.y)+0.5f,origin.z+std::ceil(highest*8)*0.125f+0.5f};
	}
};

/** Keep guide walls outside every route's running clearance. Overlaying whole
 * single-track channels would put a solid wall across a crossing or turnout. */
inline std::vector<std::array<float,2>> RailGuideRanges(unsigned track, float side, unsigned layout)
{
	auto visible = [&](float t) {
		auto frame = RailPath(track,t);
		Vec3 p = frame.point+frame.across*side;
		for (unsigned other = 0; other < 6; ++other) if (other != track && (layout & (1U<<other)) && RailPathDistance(p,other) < 3.4f) return false;
		return true;
	};
	std::vector<std::array<float,2>> ranges;
	float start = 0;
	bool previous = visible(0);
	for (unsigned i = 1; i <= 128; ++i) {
		float end = i/128.0f;
		bool current = visible(end);
		if (current != previous) {
			float lo = (i-1)/128.0f, hi = end;
			for (unsigned j = 0; j < 12; ++j) {
				float mid = (lo+hi)*0.5f;
				if (visible(mid) == previous) lo = mid; else hi = mid;
			}
			float boundary = (lo+hi)*0.5f;
			if (previous) ranges.push_back({start,boundary}); else start = boundary;
		}
		previous = current;
	}
	if (previous) ranges.push_back({start,1});
	return ranges;
}

inline RailAssembly MakeRailAssembly(unsigned kind, unsigned track, const TileSurface &surface, unsigned lod = 0, unsigned layout = 0)
{
	if (kind > 3 || track > 5) throw std::invalid_argument("Invalid voxel rail kind/route");
	/* Rail relief uses a transport subgrid: quarter ground units and eighth
	 * height units. It retains thin running surfaces without turning a rail
	 * into a one-height-level wall. All surfaces remain axis-aligned voxels. */
	constexpr float xy = 0.25f, dz = 0.125f;
	/* At subpixel scale, flat straight sections are constant along their run.
	 * Keep the exact cross-section/gauge and height grid, but avoid subdividing
	 * that identical length into quarter-unit cells. Diagonals, grades and
	 * maglev junction clearances retain the original fine lattice. */
	bool flat = surface.raised_half < 0 && surface.centre == 0 && std::ranges::all_of(surface.corners,[](float z) { return z == 0; });
	bool coarse_run = lod == 2 && track < 2 && flat && (kind != 3 || (layout & ~(1U<<track)) == 0);
	float dx = coarse_run && track == 0 ? 1.0f : xy, dy = coarse_run && track == 1 ? 1.0f : xy;
	int columns = static_cast<int>(16/dx), rows = static_cast<int>(16/dy);
	float maximum = std::max({surface.corners[0],surface.corners[1],surface.corners[2],surface.corners[3],surface.centre,surface.upper_height});
	VoxelMaterial steel = kind <= 1 ? VoxelMaterial{{4,6,5,7,3,9}} :
		kind == 2 ? VoxelMaterial{{6,8,7,9,5,10}} : VoxelMaterial{{7,8,7,9,5,12}};
	std::vector<VoxelMaterial> materials{
		{{104,105,104,106,104,106}},{{105,106,105,107,104,107}},{{106,107,106,108,104,108}},{{105,106,105,107,104,33}},
		{{70,71,70,71,70,71}},{{6,7,6,8,5,9}},{{6,7,6,8,5,9}},
		steel,{{3,4,3,5,3,6}}
	};
	if (kind == 3) {
		for (unsigned i = 0; i < 4; ++i) materials[i] = {{4,5,4,6,3,static_cast<uint8_t>(5+i%2)}};
		materials[4] = {{7,8,7,9,5,11}}; // Raised-panel edge highlights.
		materials[5] = {{4,5,4,6,3,6}}; // Slab joints.
		materials[6] = {{6,7,6,8,5,8}};
	}
	VoxelGrid grid({columns,rows,static_cast<int>(std::ceil(maximum/dz))+9},std::move(materials),{},{dx,dy,dz});
	/* Authored low-contrast grit at the same half-unit spacing as building
	 * palette cells. A diagonal arithmetic ramp looked like large chequerboard
	 * slabs in the Cab; these source browns leave sleepers and steel distinct. */
	static constexpr unsigned grit[8][8] = {
		{0,1,2,1,1,0,3,1},{2,1,0,3,1,2,1,0},{1,3,1,0,2,1,0,1},{0,1,2,1,3,0,1,2},
		{1,2,0,1,1,3,2,1},{3,1,1,2,0,1,0,3},{1,0,3,1,2,1,1,0},{2,1,0,2,1,0,3,1}
	};
	auto frame = RailPath(track,0);
	Vec3 along{frame.across.y,-frame.across.x,0};
	float width = kind == 3 ? 4.25f : 3;
	auto running = [&](unsigned route, Vec3 p) {
		auto f = RailPath(route,0);
		float d = std::abs(Dot(p-f.point,f.across));
		/* Two diagonal lattice rows give face-connected steps rather than a
		 * string of cubes touching only at corners. Their mean gauge is 2.65. */
		return kind <= 1 ? std::abs(d-1.25f) <= (route < 2 ? 0.126f : 0.18f) : kind == 2 ? d <= 0.60f : std::abs(d-3.625f) <= 0.126f;
	};
	for (int y = 0; y < rows; ++y) for (int x = 0; x < columns; ++x) {
		Vec3 p{(x+0.5f)*dx,(y+0.5f)*dy,0};
		float distance = std::abs(Dot(p-frame.point,frame.across));
		if (distance > width) continue;
		float low = INFINITY, high = -INFINITY;
		for (float ox : {0.0f,dx}) for (float oy : {0.0f,dy}) {
			float height = surface.Height(x*dx+ox,y*dy+oy);
			low = std::min(low,height); high = std::max(high,height);
		}
		int bottom = std::max(0,static_cast<int>(std::floor(low/dz))), base = static_cast<int>(std::ceil(high/dz));
		auto fill = [&](int a, int b, unsigned material) { grid.Fill({x,y,a},{x+1,y+1,b},material); };
		unsigned grain = lod == 0 ? grit[(y/2)%8][(x/2)%8] : 1;
		fill(bottom,base+1,1+grain);
		float position = Dot(p-frame.point,along);
		float pitch = kind == 2 ? 2.75f : 2.0f;
		bool tie = std::abs(std::remainder(position-pitch*0.5f,pitch)) < (kind == 2 ? 0.40f : 0.25f);
		if (kind == 3 && distance <= 3.75f) {
			/* Panel joints use one tile-space grid through junctions. Per-route
			 * joint colours would fight at coincident crossing slab surfaces. */
			bool edge = std::abs(distance-3.125f) <= 0.126f;
			if (edge) for (unsigned other = 0; other < 6; ++other) {
				if (other == track || !(layout & (1U<<other))) continue;
				auto route = RailPath(other,0);
				/* Slabs use a straight band clipped by the tile, including the
				 * complete port width beyond a diagonal centreline's endpoint. */
				if (std::abs(Dot(p-route.point,route.across)) <= 3.75f) edge = false;
			}
			bool joint = x%16 == 0 || y%16 == 0;
			fill(base+1,base+2,edge ? 5 : lod < 2 && joint ? 6 : 7);
		}
		else if (lod < 2 && tie && distance <= (kind == 2 ? 1.5f : 2.125f)) fill(base+1,base+2,kind == 2 ? 6 : 5);
		bool rail = running(track,p);
		if (rail && kind == 3) for (unsigned other = 0; other < 6; ++other) {
			if (other != track && (layout & (1U<<other)) && RailPathDistance(p,other) < 3.4f+xy) rail = false;
		}
		if (rail) fill(base+2,base+(kind <= 1 ? 4 : 8),8);
		else if (kind <= 1 && lod == 0 && tie && std::abs(distance-1.625f) < 0.126f) fill(base+1,base+3,9);
	}
	RailAssembly result;
	result.parts[static_cast<unsigned>(RailMaterial::Ballast)] = grid.Mesh(true,1,4).vertices;
	result.parts[static_cast<unsigned>(RailMaterial::Supports)] = grid.Mesh(true,5,7).vertices;
	result.parts[static_cast<unsigned>(RailMaterial::Rails)] = grid.Mesh(true,8,8).vertices;
	result.parts[static_cast<unsigned>(RailMaterial::Fasteners)] = grid.Mesh(true,9,9).vertices;
	auto &reserved = result.parts[static_cast<unsigned>(RailMaterial::ReservedRails)];
	reserved = result.parts[static_cast<unsigned>(RailMaterial::Rails)];
	for (auto &v : reserved) {
		unsigned index = static_cast<unsigned>(v.texture.x*256);
		v.texture.x = (std::max(1U,index/2)+0.5f)/256;
	}
	return result;
}

/** Clip an authored railway component along its canonical X axis. Depots and
 * crossings retain the shared profiles without track extending through walls. */
inline std::vector<Vertex> ClipRailSection(std::span<const Vertex> mesh, float low, float high)
{
	std::vector<Vertex> result;
	for (size_t first = 0; first < mesh.size(); first += 3) {
		std::vector<Vertex> polygon{mesh[first],mesh[first+1],mesh[first+2]};
		for (bool upper : {false,true}) {
			std::vector<Vertex> clipped;
			if (polygon.empty()) break;
			Vertex previous = polygon.back();
			for (const auto &point : polygon) {
				float a = upper ? high-previous.position.x : previous.position.x-low;
				float b = upper ? high-point.position.x : point.position.x-low;
				if ((a >= 0) != (b >= 0)) {
					float t = a/(a-b);
					Vertex edge = previous;
					edge.position = previous.position+(point.position-previous.position)*t;
					edge.texture = previous.texture+(point.texture-previous.texture)*t;
					edge.colour = {std::lerp(previous.colour.r,point.colour.r,t),std::lerp(previous.colour.g,point.colour.g,t),std::lerp(previous.colour.b,point.colour.b,t)};
					clipped.push_back(edge);
				}
				if (b >= 0) clipped.push_back(point);
				previous = point;
			}
			polygon = std::move(clipped);
		}
		for (size_t i = 1; i+1 < polygon.size(); ++i) {
			Vec3 a = polygon[i].position-polygon[0].position, b = polygon[i+1].position-polygon[0].position;
			Vec3 cross{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};
			if (Dot(cross,cross) < 1e-12f) continue;
			for (size_t index : {size_t{0},i,i+1}) result.push_back(polygon[index]);
		}
	}
	return result;
}

} // namespace Renderer3D
#endif
