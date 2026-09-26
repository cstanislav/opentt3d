/* SPDX-License-Identifier: GPL-2.0-only */
/** @file bridge_geometry.hpp Authored bridge assemblies in fixed tile coordinates.
 * References: OpenGFX2 Classic 0.8.1 and authored bridge-family references.
 * Mesh topology is explicit construction geometry, never derived from images. */
#ifndef RENDERER3D_BRIDGE_GEOMETRY_HPP
#define RENDERER3D_BRIDGE_GEOMETRY_HPP

#include "geometry.hpp"
#include <numbers>

namespace Renderer3D {

enum class BridgeRole { None, Deck, Front, Ramp, Pillar, Surface };
inline constexpr float BRIDGE_DECK_THICKNESS = 0.5f;

inline float BridgePillarCap(float deck_z, float segment_z)
{
	return std::min(3.0f,deck_z-BRIDGE_DECK_THICKNESS*0.5f-segment_z);
}

struct BridgeShape {
	unsigned type = 0, piece = 0;
	BridgeRole role = BridgeRole::None;
	bool along_y = false;
	unsigned ramp_direction = 0; ///< NE, SE, SW, NW as in the upstream drawing table.
	bool sloped = false;
	unsigned pillar_mask = 3; ///< Physical north/south columns selected by upstream half-sprite cropping.
	float pillar_top = 3; ///< Local cap; the highest segment is buried inside the deck.
};

/** Bridge heights are gameplay world coordinates, not sprite bounding-box Z. */
inline float BridgeRampHeight(unsigned direction, float x, float y)
{
	switch (direction) {
		case 0: return (16 - x) * 0.5f;
		case 1: return y * 0.5f;
		case 2: return x * 0.5f;
		default: return (16 - y) * 0.5f;
	}
}

inline std::vector<Vertex> MakeBridgeMesh(const BridgeShape &shape)
{
	Scene mesh;
	auto box = [&](float x, float y, float z, float w, float h, float d, bool deck = false) {
		size_t first = mesh.vertices.size();
		Vec3 p[] = {{x,y,z},{x+w,y,z},{x+w,y+h,z},{x,y+h,z},{x,y,z+d},{x+w,y,z+d},{x+w,y+h,z+d},{x,y+h,z+d}};
		mesh.Quad(p[0],p[3],p[2],p[1],{}); mesh.Quad(p[4],p[5],p[6],p[7],{});
		mesh.Quad(p[0],p[1],p[5],p[4],{}); mesh.Quad(p[1],p[2],p[6],p[5],{});
		mesh.Quad(p[2],p[3],p[7],p[6],{}); mesh.Quad(p[3],p[0],p[4],p[7],{});
		if (deck) for (size_t i = first; i < mesh.vertices.size(); ++i) {
			auto &v = mesh.vertices[i];
			/* Use a clean edge-material sample underneath. Stretching a one-pixel
			 * strip over the slab painted enormous false braces above the Cab. */
			if (v.normal.z < 0) v.texture = {8,y,0};
			else if (v.normal.z == 0) v.texture = {v.position.x,v.position.y,0};
		}
	};
	auto beam = [&](Vec3 a, Vec3 b, float radius) {
		Vec3 along = Normalize(b - a);
		Vec3 right = Normalize(std::abs(along.z) < 0.9f ? Vec3{-along.y, along.x, 0} : Vec3{1, 0, 0});
		Vec3 up = Normal({}, along, right);
		Vec3 r = right * radius, u = up * radius;
		Vec3 p[] = {a-r-u,a+r-u,a+r+u,a-r+u,b-r-u,b+r-u,b+r+u,b-r+u};
		mesh.Quad(p[0],p[3],p[2],p[1],{}); mesh.Quad(p[4],p[5],p[6],p[7],{});
		for (unsigned i = 0; i < 4; ++i) mesh.Quad(p[i],p[(i+1)%4],p[4+(i+1)%4],p[4+i],{});
	};
	auto cylinder = [&](float x, float y, float z, float radius, float height) {
		constexpr unsigned sides = 12;
		for (unsigned i = 0; i < sides; ++i) {
			float a = i * 2 * std::numbers::pi_v<float> / sides, b = (i+1) * 2 * std::numbers::pi_v<float> / sides;
			Vec3 p{x+radius*std::cos(a),y+radius*std::sin(a),z}, q{x+radius*std::cos(b),y+radius*std::sin(b),z};
			mesh.Quad(p,q,q+Vec3{0,0,height},p+Vec3{0,0,height},{});
			mesh.Triangle({x,y,z+height},p+Vec3{0,0,height},q+Vec3{0,0,height},{});
			mesh.Triangle({x,y,z},q,p,{});
		}
	};
	const bool wooden = shape.type == 0, suspension = shape.type >= 3 && shape.type <= 5;
	const bool cantilever = shape.type >= 6 && shape.type <= 8, tubular = shape.type >= 10 && shape.type <= 12;
	const bool aqueduct = shape.type == 13;
	if (shape.role == BridgeRole::Pillar) {
		/* The upstream pillar callback supplies each eight-unit segment and its
		 * half-sprite clipping. Never add supports where its obstruction rules omit them. */
		for (float x : {1.0f, 15.0f}) {
			if ((shape.pillar_mask & (x < 8 ? 1U : 2U)) == 0) continue;
			if (suspension && (shape.piece == 5 || (shape.piece == 2 && x > 8) || (shape.piece == 3 && x < 8))) continue;
			if ((cantilever || tubular) && (shape.piece == 0 || (shape.piece == 1 && (cantilever ? x > 8 : x < 8)))) continue;
			bool anchor = suspension && ((shape.piece == 0 && x < 8) || (shape.piece == 1 && x > 8));
			if (shape.pillar_top <= -5) continue;
			if (wooden || (suspension && !anchor) || cantilever) cylinder(x, 1, -5, wooden ? 0.7f : 0.9f, shape.pillar_top+5);
			else box(x-0.8f,0.2f,-5,1.6f,1.6f,shape.pillar_top+5);
		}
	} else {
		const bool ramp = shape.role == BridgeRole::Ramp;
		if (shape.role == BridgeRole::Surface) {
			mesh.Quad({0,1,0.025f},{16,1,0.025f},{16,15,0.025f},{0,15,0.025f},{});
		} else if (shape.role == BridgeRole::Deck || ramp) {
			box(0,1,-BRIDGE_DECK_THICKNESS,16,14,BRIDGE_DECK_THICKNESS,true);
		}
		auto railing = [&](float y, bool front) {
			float low = 0.4f, rail_height = ramp ? 1.2f : wooden || shape.type == 9 ? 10 : 3;
			beam({0,y,low},{16,y,low},wooden ? 0.3f : 0.18f);
			if (aqueduct) { box(0,y-0.5f,-BRIDGE_DECK_THICKNESS,16,1,2.5f+BRIDGE_DECK_THICKNESS); return; }
			if (ramp || (!wooden && !suspension && !cantilever && !tubular && shape.type != 2)) {
				beam({0,y,rail_height},{16,y,rail_height},0.16f);
				for (int x = 0; x < 16; x += 2) beam({static_cast<float>(x),y,low},{static_cast<float>(x),y,rail_height},0.08f);
				return;
			}
			if (wooden) {
				beam({0,y,10},{16,y,10},0.3f);
				for (int x = 0; x <= 16; x += 4) beam({static_cast<float>(x),y,0},{static_cast<float>(x),y,10},0.24f);
				for (int x = 0; x < 16; x += 8) {
					beam({static_cast<float>(x),y,0},{x+4.0f,y,5},0.18f);
					beam({x+4.0f,y,5},{x+8.0f,y,0},0.18f);
				}
				if (front) for (int x = 0; x < 16; x += 4) beam({static_cast<float>(x),1,10},{static_cast<float>(x),15,10},0.25f);
				return;
			}
			if (shape.type == 2 || cantilever) {
				auto top = [&](float x) {
					float t = (x - 8) / 8;
					if (shape.type == 2) return 2 + 15 * std::sqrt(std::max(0.0f, 1 - t * t));
					if (shape.piece == 0) return 12 + 3 * (1 - std::abs(x-8)/8);
					if (shape.piece == 1) return 16 - x * 0.5f;
					return 16.0f;
				};
				for (int x = 0; x < 16; x += 2) beam({static_cast<float>(x),y,top(x)},{x+2.0f,y,top(x+2)},0.22f);
				for (int x = 0; x <= 16; x += 2) beam({static_cast<float>(x),y,low},{static_cast<float>(x),y,top(x)},0.12f);
				if (cantilever) for (int x = 0; x < 16; x += 4) {
					beam({static_cast<float>(x),y,low},{x+2.0f,y,top(x+2)},0.15f);
					beam({x+2.0f,y,top(x+2)},{x+4.0f,y,low},0.15f);
				}
				if (cantilever && front) for (int x = 0; x <= 16; x += 4) beam({static_cast<float>(x),1,top(x)},{static_cast<float>(x),15,top(x)},0.18f);
				return;
			}
			if (suspension) {
				beam({0,y,3},{16,y,3},0.18f);
				if (shape.piece == 5) return;
				auto cable = [&](float x) {
					float t = x / 16;
					if (shape.piece == 4) return 24 - 8 * 4 * t * (1-t);
					if (shape.piece == 0 || shape.piece == 3) return 4 + 20 * t * t;
					return 4 + 20 * (1-t) * (1-t);
				};
				for (int x = 0; x < 16; x += 2) beam({static_cast<float>(x),y,cable(x)},{x+2.0f,y,cable(x+2)},0.2f);
				for (int x = 0; x <= 16; x += 2) beam({static_cast<float>(x),y,low},{static_cast<float>(x),y,cable(x)},0.07f);
				for (float x : {0.0f, 16.0f}) if (cable(x) > 20) cylinder(x,y,-2,0.55f,27);
				return;
			}
			if (tubular) {
				beam({0,y,3},{16,y,3},0.16f);
				beam({0,y,12},{16,y,12},0.22f);
				for (int x = 0; x <= 16; x += 4) beam({static_cast<float>(x),y,0},{static_cast<float>(x),y,12},0.2f);
				for (int x = 0; x < 16; x += 2) { beam({static_cast<float>(x),y,4},{x+2.0f,y,12},0.035f); beam({static_cast<float>(x),y,12},{x+2.0f,y,4},0.035f); }
				if (front) for (int x = 0; x <= 16; x += 4) {
					if (shape.piece == 0 && x != 16) continue;
					if (shape.piece == 1 && x != 0) continue;
					for (unsigned side = 0; side < 12; ++side) {
						float a = side * std::numbers::pi_v<float> / 12, b = (side+1) * std::numbers::pi_v<float> / 12;
						beam({static_cast<float>(x),8+7*std::cos(a),12+8*std::sin(a)},{static_cast<float>(x),8+7*std::cos(b),12+8*std::sin(b)},0.18f);
					}
				}
			}
		};
		if (shape.role == BridgeRole::Deck || ramp) railing(1, false);
		if (shape.role == BridgeRole::Front || ramp || (aqueduct && shape.role == BridgeRole::Deck)) railing(15, true);
	}
	for (auto &vertex : mesh.vertices) {
		Vec3 sample = vertex.texture.z >= 0 ? vertex.texture : vertex.position;
		if (shape.along_y) { std::swap(vertex.position.x,vertex.position.y); std::swap(sample.x,sample.y); }
		if (shape.sloped && shape.role != BridgeRole::Pillar && shape.role != BridgeRole::None) {
			vertex.position.z += BridgeRampHeight(shape.ramp_direction,vertex.position.x,vertex.position.y) - 8;
			sample.z += BridgeRampHeight(shape.ramp_direction,sample.x,sample.y) - 8;
		}
		vertex.texture = {2 * (sample.y-sample.x),sample.x+sample.y-sample.z,0};
	}
	/* Axis swaps and the ramp shear require normals from transformed faces. */
	for (size_t i = 0; i < mesh.vertices.size(); i += 3) {
		if (shape.along_y) std::swap(mesh.vertices[i+1], mesh.vertices[i+2]);
		Vec3 normal = Normal(mesh.vertices[i].position,mesh.vertices[i+1].position,mesh.vertices[i+2].position);
		for (size_t j = i; j < i + 3; ++j) mesh.vertices[j].normal = normal;
	}
	return mesh.vertices;
}

} // namespace Renderer3D
#endif
