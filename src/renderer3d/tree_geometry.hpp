/* SPDX-License-Identifier: GPL-2.0-only */
/** @file tree_geometry.hpp Authored, closed branch and foliage volumes in world coordinates. */

#ifndef RENDERER3D_TREE_GEOMETRY_HPP
#define RENDERER3D_TREE_GEOMETRY_HPP

#include "camera.hpp"

namespace Renderer3D {

struct TreeBranchPoint {
	Vec3 position;
	float radius;
};

/** Shared rings at bends prevent open seams between independently oriented tubes. */
inline void TreeBranch(Scene &mesh, std::span<const TreeBranchPoint> points, unsigned lod)
{
	if (points.size() < 2) throw std::runtime_error("Tree branch needs two control points");
	unsigned sides = lod == 0 ? 8 : lod == 1 ? 6 : 4;
	if (lod == 2 && std::ranges::all_of(points, [](const auto &p) { return p.radius < 0.18f; })) return;
	auto cross = [](Vec3 a, Vec3 b) { return Vec3{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; };
	std::vector<Vec3> directions, rings;
	std::vector<float> lengths{0};
	for (size_t i = 1; i < points.size(); ++i) {
		Vec3 delta = Camera::Physical(points[i].position-points[i-1].position);
		if (Dot(delta,delta) < 0.000001f) throw std::runtime_error("Tree branch has coincident control points");
		directions.push_back(Normalize(delta));
		lengths.push_back(lengths.back()+std::sqrt(Dot(delta,delta)));
	}
	Vec3 reference = std::abs(directions.front().z) < 0.9f ? Vec3{0,0,1} : Vec3{0,1,0};
	Vec3 previous_tangent = directions.front(), across = Normalize(cross(previous_tangent,reference));
	for (size_t i = 0; i < points.size(); ++i) {
		if (!(points[i].radius > 0)) throw std::runtime_error("Tree branch radius must be positive");
		Vec3 tangent = i == 0 ? directions.front() : i+1 == points.size() ? directions.back() : directions[i-1]+directions[i];
		if (Dot(tangent,tangent) < 0.000001f) throw std::runtime_error("Tree branch reverses at a control point");
		tangent = Normalize(tangent);
		/* Parallel-transport the ring instead of crossing every tangent with a
		 * fixed axis: a cactus arm may legitimately turn from horizontal to vertical. */
		Vec3 rotation = cross(previous_tangent,tangent);
		float cosine = std::clamp(Dot(previous_tangent,tangent),-1.0f,1.0f);
		if (cosine < -0.9999f) throw std::runtime_error("Tree branch reverses its ring frame");
		across = Normalize(across+cross(rotation,across)+cross(rotation,cross(rotation,across))*(1/(1+cosine)));
		previous_tangent = tangent;
		Vec3 up = cross(tangent,across);
		for (unsigned side = 0; side < sides; ++side) {
			float angle = 2*std::numbers::pi_v<float>*side/sides;
			rings.push_back(points[i].position+Camera::World((across*std::cos(angle)+up*std::sin(angle))*points[i].radius));
		}
	}
	for (size_t i = 1; i < points.size(); ++i) for (unsigned side = 0; side < sides; ++side) {
		unsigned next = (side+1)%sides;
		size_t first = mesh.vertices.size();
		mesh.Quad(rings[(i-1)*sides+side],rings[(i-1)*sides+next],rings[i*sides+next],rings[i*sides+side],{});
		/* Unwrapped physical arc/length coordinates preserve grain through bends.
		 * The duplicate seam endpoint uses 2*pi rather than wrapping back to zero. */
		auto uv = [&](size_t ring, unsigned angle) { return Vec3{2*std::numbers::pi_v<float>*points[ring].radius*angle/sides,lengths[ring],-5}; };
		const Vec3 charts[] = {uv(i-1,side),uv(i-1,side+1),uv(i,side+1),uv(i-1,side),uv(i,side+1),uv(i,side)};
		for (unsigned vertex = 0; vertex < 6; ++vertex) mesh.vertices[first+vertex].texture = charts[vertex];
		if (i == 1) mesh.Triangle(points.front().position,rings[next],rings[side],{});
		if (i+1 == points.size()) mesh.Triangle(points.back().position,rings[i*sides+side],rings[i*sides+next],{});
	}
}

/** Irregular broadleaf envelope. Seed is an authored shape parameter, never game RNG. */
inline void TreeCrown(Scene &mesh, Vec3 base, Vec3 size, float seed, unsigned lod)
{
	unsigned sides = lod == 0 ? 24 : lod == 1 ? 12 : 8, rings = lod == 0 ? 12 : lod == 1 ? 6 : 4;
	auto point = [&](unsigned ring, unsigned side) {
		if (ring == 0) return base;
		if (ring == rings) return base+Vec3{0,0,size.z};
		float t = (1-std::cos(std::numbers::pi_v<float>*ring/rings))*0.5f;
		float angle = 2*std::numbers::pi_v<float>*(side%sides)/sides;
		float envelope = std::sin(std::numbers::pi_v<float>*t);
		float lobe = envelope*(0.14f*std::sin(3*angle+seed)+0.075f*std::cos(7*angle+2*t+seed)+
			0.075f*std::sin(4*std::numbers::pi_v<float>*t+3*angle+seed));
		float radius = 2*std::sqrt(t*(1-t))*(1+lobe);
		return base+Vec3{size.x*radius*std::cos(angle),size.y*radius*std::sin(angle),
			size.z*(t+0.03f*std::sin(5*angle+seed)*envelope)};
	};
	for (unsigned ring = 0; ring < rings; ++ring) for (unsigned side = 0; side < sides; ++side) {
		Vec3 a = point(ring,side), b = point(ring,side+1), c = point(ring+1,side+1), d = point(ring+1,side);
		if (ring != 0) mesh.Triangle(a,b,c,{});
		if (ring+1 != rings) mesh.Triangle(a,c,d,{});
	}
}

/** Drooping conifer layer with a scalloped hem and a curved, tapered upper surface. */
inline void TreeBough(Scene &mesh, Vec3 base, Vec3 size, float seed, unsigned lod)
{
	unsigned sides = lod == 0 ? 24 : lod == 1 ? 12 : 8, rings = lod == 0 ? 6 : 3;
	auto point = [&](unsigned ring, unsigned side) {
		float t = static_cast<float>(ring)/rings, a = 2*std::numbers::pi_v<float>*(side%sides)/sides;
		float radius = (1-t)*(1+0.22f*std::sin(std::numbers::pi_v<float>*t))*(1+0.12f*std::sin(5*a+seed)+0.06f*std::cos(7*a+3*t+seed));
		return base+Vec3{size.x*radius*std::cos(a),size.y*radius*std::sin(a),size.z*(t+0.07f*std::sin(5*a+seed)*(1-t))};
	};
	for (unsigned ring = 0; ring < rings; ++ring) for (unsigned side = 0; side < sides; ++side) {
		Vec3 a = point(ring,side), b = point(ring,side+1), c = point(ring+1,side+1), d = point(ring+1,side);
		mesh.Triangle(a,b,c,{});
		if (ring+1 < rings) mesh.Triangle(a,c,d,{});
		if (ring == 0) mesh.Triangle(base,b,a,{});
	}
}

/** Folded, arched leaf blade with an underside and a raised midrib. */
inline void TreeLeaf(Scene &mesh, Vec3 root, Vec3 tip, float width, float arch, float thickness, unsigned lod)
{
	Vec3 delta = tip-root;
	if (delta.x*delta.x+delta.y*delta.y < 0.000001f || width <= 0 || thickness <= 0) throw std::runtime_error("Invalid authored leaf blade");
	Vec3 side = Normalize({-delta.y,delta.x,0});
	unsigned sections = lod == 0 ? 8 : lod == 1 ? 4 : 2;
	auto point = [&](unsigned section, unsigned corner) {
		if (section == 0) return root;
		if (section == sections) return tip;
		float t = static_cast<float>(section)/sections, envelope = std::sin(std::numbers::pi_v<float>*t);
		Vec3 centre = root+delta*t+Vec3{0,0,4*arch*t*(1-t)};
		const Vec3 offsets[] = {side*width,Vec3{0,0,thickness},side*(-width),Vec3{0,0,-thickness*0.35f}};
		return centre+offsets[corner%4]*envelope;
	};
	for (unsigned section = 0; section < sections; ++section) for (unsigned corner = 0; corner < 4; ++corner) {
		Vec3 a = point(section,corner), b = point(section,corner+1), c = point(section+1,corner+1), d = point(section+1,corner);
		if (section != 0) mesh.Triangle(a,b,c,{});
		if (section+1 != sections) mesh.Triangle(a,c,d,{});
	}
}

/** Real paired leaflets on a curved rachis; unresolved far detail stays a closed blade. */
inline void TreePalmFrond(Scene &mesh, Vec3 root, Vec3 tip, float width, unsigned lod)
{
	constexpr float arch = 2.5f;
	if (lod == 2) { TreeLeaf(mesh,root,tip,width,arch,0.10f,lod); return; }
	TreeLeaf(mesh,root,tip,0.10f,arch,0.08f,lod);
	Vec3 delta = tip-root, across = Normalize({-delta.y,delta.x,0});
	unsigned pairs = lod == 0 ? 10 : 4;
	for (unsigned pair = 0; pair < pairs; ++pair) for (float side : {-1.0f,1.0f}) {
		float t = 0.10f+0.82f*pair/pairs;
		Vec3 centre = root+delta*t+Vec3{0,0,4*arch*t*(1-t)};
		Vec3 end = centre+delta*0.14f+across*(side*width*std::sin(std::numbers::pi_v<float>*t))+Vec3{0,0,-1.2f};
		TreeLeaf(mesh,centre,end,lod == 0 ? 0.36f : 0.65f,0.25f,0.09f,2);
	}
}

/** Solid turned profile or a closed angular gore, used by Toyland's sculpted crowns. */
inline void TreeSector(Scene &mesh, Vec3 origin, std::span<const Vec3> profile, float begin, float end, unsigned sides, unsigned lod)
{
	if (profile.size() < 2 || sides < 2 || end <= begin || end-begin > 360.001f) throw std::runtime_error("Invalid tree sector");
	bool complete = end-begin > 359.999f;
	sides = std::max(complete ? 6U : 2U,lod == 0 ? sides : lod == 1 ? sides/2 : sides/3);
	auto pointed = [&](size_t ring) { return profile[ring].y == 0 && profile[ring].z == 0; };
	auto centre = [&](size_t ring) { return origin+Vec3{0,0,profile[ring].x}; };
	auto point = [&](size_t ring, unsigned side) {
		if (pointed(ring)) return centre(ring);
		if (complete && side == sides) side = 0;
		float a = (begin+(end-begin)*side/sides)*std::numbers::pi_v<float>/180;
		return centre(ring)+Vec3{profile[ring].y*std::cos(a),profile[ring].z*std::sin(a),0};
	};
	for (size_t ring = 0; ring+1 < profile.size(); ++ring) {
		if (profile[ring+1].x <= profile[ring].x) throw std::runtime_error("Tree sector profile heights must increase");
		for (unsigned side = 0; side < sides; ++side) {
			Vec3 a = point(ring,side), b = point(ring,side+1), c = point(ring+1,side+1), d = point(ring+1,side);
			if (!pointed(ring)) mesh.Triangle(a,b,c,{});
			if (!pointed(ring+1)) mesh.Triangle(a,c,d,{});
			if (ring == 0 && !pointed(ring)) mesh.Triangle(centre(ring),b,a,{});
			if (ring+2 == profile.size() && !pointed(ring+1)) mesh.Triangle(centre(ring+1),d,c,{});
		}
		if (!complete) {
			if (!pointed(ring)) {
				mesh.Triangle(centre(ring),point(ring,0),point(ring+1,0),{});
				mesh.Triangle(centre(ring),point(ring+1,sides),point(ring,sides),{});
			}
			if (!pointed(ring+1)) {
				mesh.Triangle(centre(ring),point(ring+1,0),centre(ring+1),{});
				mesh.Triangle(centre(ring),centre(ring+1),point(ring+1,sides),{});
			}
		}
	}
}

} // namespace Renderer3D
#endif
