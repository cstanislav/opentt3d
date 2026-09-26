/* SPDX-License-Identifier: GPL-2.0-only */
/** @file geometry.hpp Presentation-only mesh types. No simulation dependencies. */

#ifndef RENDERER3D_GEOMETRY_HPP
#define RENDERER3D_GEOMETRY_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <cstdint>
#include <span>
#include <optional>
#include <string_view>
#include <vector>

namespace Renderer3D {

struct Vec3 {
	float x = 0, y = 0, z = 0;
	bool operator==(const Vec3 &) const = default;
	Vec3 operator+(Vec3 other) const { return {x + other.x, y + other.y, z + other.z}; }
	Vec3 operator-(Vec3 other) const { return {x - other.x, y - other.y, z - other.z}; }
	Vec3 operator*(float scale) const { return {x * scale, y * scale, z * scale}; }
};

inline float Dot(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3 Normalize(Vec3 p) { return p * (1.0f / std::sqrt(Dot(p, p))); }

struct Ray {
	Vec3 origin, direction;
	Vec3 At(float distance) const { return origin + direction * distance; }
	std::optional<Vec3> AtZ(float z) const
	{
		if (std::abs(direction.z) < 1e-8f) return std::nullopt;
		float distance = (z - origin.z) / direction.z;
		if (distance < 0) return std::nullopt;
		return At(distance);
	}
	bool ClipBox(Vec3 low, Vec3 high, double &enter, double &leave) const
	{
		const double o[] = {origin.x, origin.y, origin.z}, d[] = {direction.x, direction.y, direction.z};
		const double a[] = {low.x, low.y, low.z}, b[] = {high.x, high.y, high.z};
		for (int axis = 0; axis < 3; ++axis) {
			if (std::abs(d[axis]) < 1e-8f) {
				if (o[axis] < a[axis] || o[axis] > b[axis]) return false;
			} else {
				double first = (a[axis] - o[axis]) / d[axis], last = (b[axis] - o[axis]) / d[axis];
				if (first > last) std::swap(first, last);
				enter = std::max(enter, first); leave = std::min(leave, last);
				if (enter > leave) return false;
			}
		}
		return true;
	}
};

struct Rgb {
	float r = 1, g = 1, b = 1;
};

struct TextureRegion {
	float left = 0, top = 0, right = 1, bottom = 1;
};

enum class SurfaceMode : uint32_t { Cutout, Opaque, RepeatingWater, Shadow, RepeatingChart, Palette };
/** Vertex-only flag: texture XY is relative to texture_region, preserving the
 * same precision as GPU instances without an atlas-add/subtract round trip. */
inline constexpr uint32_t SURFACE_SPRITE_LOCAL_UV = 16;
inline constexpr uint32_t SURFACE_SHADED = 32; ///< Apply geometric face lighting to a component-local material.
inline constexpr uint32_t SURFACE_UNLIT = 64; ///< Authored palette shading, preserving exact retro colours.
inline constexpr uint32_t TILE_PICK_ID = 0x80000000U; ///< Tile ownership is separate from vehicle IDs.

/** Interleaved GPU vertex. Colours are authored OpenGFX-reference materials. */
struct Vertex {
	Vec3 position;
	Vec3 normal;
	Rgb colour;
	float company_colour = 0;
	Vec3 texture{-1, -1, -1}; ///< Atlas UV/page; authored -3 is a normalized chart, -4 forces a solid component.
	float opacity = 1;
	TextureRegion texture_region{};
	uint32_t object_id = 0;
	SurfaceMode surface = SurfaceMode::Cutout;
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

/** Clip planes operate on positions relative to origin, matching the GPU matrix. */
struct ClipVolume {
	Vec3 origin;
	std::array<std::array<float, 4>, 6> planes;
	bool Intersects(Vec3 low, Vec3 high) const
	{
		for (const auto &plane : planes) {
			Vec3 positive{plane[0] >= 0 ? high.x : low.x, plane[1] >= 0 ? high.y : low.y, plane[2] >= 0 ? high.z : low.z};
			positive = positive - origin;
			if (plane[0] * positive.x + plane[1] * positive.y + plane[2] * positive.z + plane[3] < -0.001f) return false;
		}
		return true;
	}

	/** Intersect the (possibly infinite) frustum with a finite world box. Corner
	 * rays alone miss horizon/slab intersections, so consider all plane triples. */
	std::optional<std::array<Vec3, 2>> IntersectionBounds(Vec3 low, Vec3 high) const
	{
		using Plane = std::array<double, 4>;
		using Vector = std::array<double, 3>;
		std::vector<Plane> clip;
		for (auto plane : planes) {
			double length = std::sqrt(static_cast<double>(plane[0]) * plane[0] + static_cast<double>(plane[1]) * plane[1] + static_cast<double>(plane[2]) * plane[2]);
			if (length > 1e-12) clip.push_back({plane[0] / length, plane[1] / length, plane[2] / length, plane[3] / length});
		}
		Vec3 a = low - origin, b = high - origin;
		clip.insert(clip.end(), {{1, 0, 0, -a.x}, {-1, 0, 0, b.x}, {0, 1, 0, -a.y}, {0, -1, 0, b.y}, {0, 0, 1, -a.z}, {0, 0, -1, b.z}});
		auto cross = [](const Plane &p, const Plane &q) { return Vector{p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0]}; };
		std::optional<std::array<Vec3, 2>> bounds;
		for (size_t i = 0; i < clip.size(); ++i) for (size_t j = i + 1; j < clip.size(); ++j) for (size_t k = j + 1; k < clip.size(); ++k) {
			const auto &p = clip[i], &q = clip[j], &r = clip[k];
			auto qr = cross(q, r), rp = cross(r, p), pq = cross(p, q);
			double determinant = p[0] * qr[0] + p[1] * qr[1] + p[2] * qr[2];
			if (std::abs(determinant) < 1e-12) continue;
			Vector point{};
			for (unsigned axis = 0; axis < 3; ++axis) point[axis] = (-p[3] * qr[axis] - q[3] * rp[axis] - r[3] * pq[axis]) / determinant;
			if (std::any_of(clip.begin(), clip.end(), [&](const Plane &test) { return test[0] * point[0] + test[1] * point[1] + test[2] * point[2] + test[3] < -0.001; })) continue;
			Vec3 world{static_cast<float>(point[0] + origin.x), static_cast<float>(point[1] + origin.y), static_cast<float>(point[2] + origin.z)};
			if (!bounds) bounds = std::array<Vec3, 2>{world, world};
			auto &[first, last] = *bounds;
			first = {std::min(first.x, world.x), std::min(first.y, world.y), std::min(first.z, world.z)};
			last = {std::max(last.x, world.x), std::max(last.y, world.y), std::max(last.z, world.z)};
		}
		return bounds;
	}
};

/** Six vec4 records, shared by the GL texture-buffer and Vulkan storage-buffer paths.
 * Vehicle pick IDs are below 2^20 and therefore represented exactly as floats. */
struct alignas(16) InstanceData {
	std::array<float, 4> origin_opacity{0, 0, 0, 1};
	std::array<float, 4> scale_center{1, 1, 0, 0}; ///< XY scale, Z scale, authored centre X/Y.
	std::array<float, 4> mirror_layer_heading{}; ///< Mirror sums/canonical yaw X/Y, normal offset or longitudinal scale, yaw radians.
	std::array<float, 4> uv_transform{0, 0, 1, -1}; ///< Bias U/V, scale, atlas page.
	TextureRegion region;
	std::array<float, 4> identity{}; ///< ID payload, surface mode, flags (1 unmirrored / 2 tile ID / 4 child / 8 canonical yaw / 16 longitudinal scale / 32 sprite-local UV bias), UV mode (3 phase / 4 density-scaled phase).
	void SetSpriteLocalUVBias() { identity[2] = static_cast<float>(static_cast<uint32_t>(identity[2]) | 32U); }
	void SetLongitudinalScale(float scale)
	{
		if (!std::isfinite(scale) || scale <= 0) throw std::invalid_argument("Invalid longitudinal instance scale");
		mirror_layer_heading[2] = scale;
		identity[2] = static_cast<float>(static_cast<uint32_t>(identity[2]) | 16U);
	}
	InstanceData CanonicalGPURecord() const
	{
		InstanceData result = *this;
		/* Unmirrored palette instances do not use the image mirror coordinates.
		 * Reuse those two words for CPU-rounded trig values, rather than letting
		 * driver-specific sin/cos approximations move a shared coloured edge. */
		if ((static_cast<uint32_t>(identity[1]) & 15U) == static_cast<uint32_t>(SurfaceMode::Palette) && (static_cast<uint32_t>(identity[2]) & 1U) != 0 && mirror_layer_heading[3] != 0) {
			result.mirror_layer_heading[0] = std::cos(mirror_layer_heading[3]);
			result.mirror_layer_heading[1] = std::sin(mirror_layer_heading[3]);
			result.identity[2] = static_cast<float>(static_cast<uint32_t>(identity[2]) | 8U);
		}
		return result;
	}
	void SetChildLayer(bool child)
	{
		identity[2] = static_cast<float>((static_cast<uint32_t>(identity[2]) & ~4U) | (child ? 4U : 0U));
	}
	bool ChildLayer() const { return (static_cast<uint32_t>(identity[2]) & 4U) != 0; }
	void SetObjectId(uint32_t id)
	{
		/* Legal map indices fit in 24 mantissa bits; encode their namespace
		 * separately rather than rounding a tile-plus-vehicle numeric base. */
		if ((id & ~TILE_PICK_ID) > 0xFFFFFFU) throw std::out_of_range("Instance picking ID exceeds the exact map-index range");
		identity[0] = static_cast<float>(id & ~TILE_PICK_ID);
		identity[2] = static_cast<float>((static_cast<uint32_t>(identity[2]) & ~2U) | ((id & TILE_PICK_ID) != 0 ? 2U : 0U));
	}
	uint32_t ObjectId() const
	{
		return static_cast<uint32_t>(identity[0]) | ((static_cast<uint32_t>(identity[2]) & 2U) != 0 ? TILE_PICK_ID : 0U);
	}
};
static_assert(sizeof(InstanceData) == 96);

struct MeshInstance {
	const std::vector<Vertex> *mesh; ///< Immutable during rendering; persistent authored meshes have stable storage.
	InstanceData data;
};

/** CPU reference for instance validation and non-instanced tooling. */
inline Vertex ResolveInstanceVertex(Vertex vertex, const InstanceData &instance, bool sprite_local_uv = false)
{
	bool solid_component = vertex.texture.z == -4;
	float xy = instance.scale_center[0], z = instance.scale_center[1];
	float cx = instance.scale_center[2], cy = instance.scale_center[3];
	Vec3 local{(vertex.position.x - cx) * xy, (vertex.position.y - cy) * xy, vertex.position.z * z};
	Vec3 normal = Normalize({vertex.normal.x / xy, vertex.normal.y / xy, vertex.normal.z / z});
	bool longitudinal = (static_cast<uint32_t>(instance.identity[2]) & 16U) != 0;
	if (longitudinal) {
		local.x *= instance.mirror_layer_heading[2];
		normal = Normalize({normal.x/instance.mirror_layer_heading[2],normal.y,normal.z});
	}
	bool authored_sample = instance.identity[3] == 2 && vertex.texture.z >= 0;
	Vec3 sample = authored_sample ? vertex.texture : vertex.position;
	if (!authored_sample && (static_cast<uint32_t>(instance.identity[2]) & 1U) == 0 && Dot(normal, {1, 1, 2}) < -0.001f) {
		if (normal.x < -0.1f) sample.x = instance.mirror_layer_heading[0] - sample.x;
		if (normal.y < -0.1f) sample.y = instance.mirror_layer_heading[1] - sample.y;
	}
	sample = {(sample.x - cx) * xy, (sample.y - cy) * xy, sample.z * z};
	if (longitudinal) sample.x *= instance.mirror_layer_heading[2];
	bool canonical_yaw = (static_cast<uint32_t>(instance.identity[2]) & 8U) != 0;
	float cs = canonical_yaw ? instance.mirror_layer_heading[0] : std::cos(instance.mirror_layer_heading[3]);
	float sn = canonical_yaw ? instance.mirror_layer_heading[1] : std::sin(instance.mirror_layer_heading[3]);
	auto rotate = [&](Vec3 p) {
		/* Keep products at float precision before the matrix-vector sum. CPU-only
		 * FMA contraction otherwise selects a neighbouring voxel face at a
		 * subpixel boundary. Volatile is portable across reference compilers. */
		volatile float xx = p.x*cs, yy = p.y*sn, xy = p.x*sn, yx = p.y*cs;
		return Vec3{xx-yy,xy+yx,p.z};
	};
	local = rotate(local); normal = rotate(normal); sample = rotate(sample);
	vertex.position = Vec3{instance.origin_opacity[0], instance.origin_opacity[1], instance.origin_opacity[2]} + local + normal * (longitudinal ? 0 : instance.mirror_layer_heading[2]);
	vertex.normal = normal;
	bool local_bias = (static_cast<uint32_t>(instance.identity[2]) & 32U) != 0;
	/* Keep an already-local bias local in expanded reference/tooling vertices;
	 * adding and removing the atlas origin would lose its subtexel precision. */
	sprite_local_uv |= local_bias;
	if (instance.identity[1] == static_cast<float>(SurfaceMode::RepeatingWater)) sprite_local_uv = false;
	float bias_u = instance.uv_transform[0] - (sprite_local_uv && !local_bias ? instance.region.left : 0);
	float bias_v = instance.uv_transform[1] - (sprite_local_uv && !local_bias ? instance.region.top : 0);
	if (instance.identity[3] == 4) {
		vertex.texture = {vertex.texture.x*instance.uv_transform[0],vertex.texture.y*instance.uv_transform[1],instance.uv_transform[3]};
	} else if (instance.identity[3] == 3) {
		vertex.texture = {vertex.texture.x,vertex.texture.y,instance.uv_transform[3]};
	} else if (instance.identity[3] == 1) {
		vertex.texture = {bias_u + vertex.texture.x * instance.uv_transform[2],
			bias_v + vertex.texture.y * instance.uv_transform[2], instance.uv_transform[3]};
	} else if (instance.identity[3] == 2 && vertex.texture.z == -3) {
		vertex.texture = sprite_local_uv ? Vec3{vertex.texture.x * (instance.region.right - instance.region.left),
			vertex.texture.y * (instance.region.bottom - instance.region.top), instance.uv_transform[3]} : Vec3{std::lerp(instance.region.left, instance.region.right, vertex.texture.x),
			std::lerp(instance.region.top, instance.region.bottom, vertex.texture.y), instance.uv_transform[3]};
	} else {
		vertex.texture = {bias_u + 2 * (sample.y - sample.x) * instance.uv_transform[2],
			bias_v + (sample.x + sample.y - sample.z) * instance.uv_transform[2], instance.uv_transform[3]};
	}
	vertex.opacity = instance.origin_opacity[3];
	if (solid_component) vertex.texture.z = -1;
	vertex.texture_region = instance.region;
	vertex.object_id = instance.ObjectId();
	vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(instance.identity[1]) | (static_cast<uint32_t>(vertex.surface) & (SURFACE_SHADED | SURFACE_UNLIT)) | (sprite_local_uv ? SURFACE_SPRITE_LOCAL_UV : 0));
	return vertex;
}

/** A frame owns its geometry, never pointers to mutable game objects. */
struct Scene {
	std::vector<Vertex> vertices;
	std::vector<MeshInstance> instances;
	std::optional<ClipVolume> visibility;
	struct WaterMaterial { Vec3 uv_origin{}; float uv_scale = 0; } water;
	/** Authored instances have stable lifetime/address. Diagnostic references can
	 * instead use call-scoped GPU uploads, retaining the same instanced shader path. */
	bool persistent_meshes = true;

	size_t VertexCount() const
	{
		size_t count = vertices.size();
		for (const auto &instance : instances) count += instance.mesh->size();
		return count;
	}

	std::vector<Vertex> ExpandedVertices(bool sprite_local_uv = false) const
	{
		std::vector<Vertex> result = vertices;
		result.reserve(VertexCount());
		for (bool child : {false,true}) for (const auto &instance : instances) if (instance.data.ChildLayer() == child) {
			for (const Vertex &vertex : *instance.mesh) result.push_back(ResolveInstanceVertex(vertex, instance.data, sprite_local_uv));
		}
		return result;
	}
	void TexturedTriangle(Vec3 a, Vec3 b, Vec3 c, Vec3 uv_a, Vec3 uv_b, Vec3 uv_c, float opacity = 1, TextureRegion region = {})
	{
		Vec3 normal = Normal(a, b, c);
		vertices.push_back({a, normal, {}, 0, uv_a, opacity, region});
		vertices.push_back({b, normal, {}, 0, uv_b, opacity, region});
		vertices.push_back({c, normal, {}, 0, uv_c, opacity, region});
	}

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

	/** Homogeneous sea strips extend to the horizon. A texture page of -2 marks
	 * a direction at infinity rather than a finite world position. */
	void Ocean(float max_x, float max_y, float page, TextureRegion region)
	{
		const Vec3 corners[] = {{0, 0, 0}, {max_x, 0, 0}, {max_x, max_y, 0}, {0, max_y, 0}};
		Vec3 center{max_x * 0.5f, max_y * 0.5f, 0};
		for (unsigned i = 0; i < 4; ++i) {
			unsigned j = (i + 1) % 4;
			const Vec3 points[] = {corners[i], corners[j], corners[j] - center, corners[i] - center};
			for (unsigned index : {0U, 1U, 2U, 0U, 2U, 3U}) {
				Vec3 p = points[index];
				vertices.push_back({p, {0, 0, 1}, {}, 0, {p.x / 16, p.y / 16, index < 2 ? page : -2}, 1, region, 0, SurfaceMode::RepeatingWater});
			}
		}
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
