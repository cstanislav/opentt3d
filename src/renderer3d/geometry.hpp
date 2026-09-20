/* SPDX-License-Identifier: GPL-2.0-only */
/** @file geometry.hpp Presentation-only mesh types. No simulation dependencies. */

#ifndef RENDERER3D_GEOMETRY_HPP
#define RENDERER3D_GEOMETRY_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

namespace Renderer3D {

struct Vec3 {
	float x = 0, y = 0, z = 0;
	Vec3 operator+(Vec3 other) const { return {x + other.x, y + other.y, z + other.z}; }
	Vec3 operator-(Vec3 other) const { return {x - other.x, y - other.y, z - other.z}; }
	Vec3 operator*(float scale) const { return {x * scale, y * scale, z * scale}; }
};

struct Rgb {
	float r = 1, g = 1, b = 1;
};

/** Interleaved GPU vertex. Colours are authored OpenGFX-reference materials. */
struct Vertex {
	Vec3 position;
	Vec3 normal;
	Rgb colour;
	float company_colour = 0;
};

inline Vec3 Normal(Vec3 a, Vec3 b, Vec3 c)
{
	Vec3 u = b - a, v = c - a;
	Vec3 n{u.y * v.z - u.z * v.y, u.z * v.x - u.x * v.z, u.x * v.y - u.y * v.x};
	float length = std::sqrt(n.x * n.x + n.y * n.y + n.z * n.z);
	return length > 0 ? n * (1.0f / length) : Vec3{0, 0, 1};
}

struct Model {
	std::string_view name;
	std::span<const Vertex> vertices;
};

/** A frame owns its geometry, never pointers to mutable game objects. */
struct Scene {
	std::vector<Vertex> vertices;

	void Triangle(Vec3 a, Vec3 b, Vec3 c, Rgb colour)
	{
		Vec3 normal = Normal(a, b, c);
		for (Vec3 p : {a, b, c}) vertices.push_back({p, normal, colour, 0});
	}

	void Quad(Vec3 a, Vec3 b, Vec3 c, Vec3 d, Rgb colour)
	{
		Triangle(a, b, c, colour);
		Triangle(a, c, d, colour);
	}

	void AddModel(const Model &model, Vec3 origin, float heading = 0, Rgb company = {}, float scale = 1)
	{
		const float cs = std::cos(heading), sn = std::sin(heading);
		for (auto v : model.vertices) {
			Vec3 p = v.position * scale;
			v.position = origin + Vec3{p.x * cs - p.y * sn, p.x * sn + p.y * cs, p.z};
			Vec3 n = v.normal;
			v.normal = {n.x * cs - n.y * sn, n.x * sn + n.y * cs, n.z};
			if (v.company_colour != 0) {
				v.colour = {company.r * v.colour.r, company.g * v.colour.g, company.b * v.colour.b};
			}
			vertices.push_back(v);
		}
	}
};

} // namespace Renderer3D

#endif
