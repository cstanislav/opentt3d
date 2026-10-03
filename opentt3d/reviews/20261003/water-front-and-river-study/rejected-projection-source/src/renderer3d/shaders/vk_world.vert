#version 450
// SPDX-License-Identifier: GPL-2.0-only
#ifdef VOXEL_PACKED_VERTEX
#ifdef VOXEL_VISIBLE_INSTANCE
layout(std430, set=0, binding=5) readonly buffer VisibleTriangles { uvec2 items[]; } visible_triangles;
layout(std430, set=0, binding=6) readonly buffer VisibleVertices { uint bits; uint values[]; } visible_vertices;
uint triangle_field(uvec2 words, uint shift)
{
    if (shift >= 32u) return words.y >> (shift-32u);
    if (shift == 0u) return words.x;
    return (words.x >> shift) | (words.y << (32u-shift));
}
#else
layout(location=0) in uint packed_vertex;
#endif
layout(std430, set=0, binding=4) readonly buffer PackedVertexFormat {
    vec4 origin;
    vec4 cell_step;
    uvec4 bits;
    vec4 colour_opacity;
    vec4 texture_region;
    uvec4 surface_info;
    vec4 normals[];
} vertex_format;
#else
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec3 vertex_colour;
layout(location=3) in vec3 texture_coord;
layout(location=4) in float opacity;
layout(location=5) in vec4 texture_region;
layout(location=6) in uint surface_mode;
layout(location=7) in uint object_id;
#endif

layout(push_constant) uniform Parameters {
    mat4 view_projection;
    vec4 camera;
    vec4 water;
    uvec4 mode;
} params;

struct Instance {
    vec4 origin_opacity;
    vec4 scale_center;
    vec4 mirror_layer_heading;
    vec4 uv_transform;
    vec4 region;
    vec4 identity;
    vec4 pitch;
};
layout(std430, set=0, binding=3) readonly buffer Instances { Instance items[]; } instances;
layout(location=0) out vec3 lit_colour;
layout(location=1) out vec3 uv_page;
layout(location=2) out float alpha;
layout(location=3) flat out vec4 uv_region;
layout(location=4) flat out uint material_surface;
layout(location=5) flat out uint pick_id;
layout(location=6) flat out uint volume_instance;
layout(location=7) out vec3 volume_position;
layout(location=8) flat out vec3 volume_eye;
layout(location=9) flat out uint volume_face;
layout(location=10) flat out float volume_plane;

vec2 canonical_rotate(vec2 value, float cs, float sn)
{
    precise vec2 products = value * cs;
    precise vec2 cross_products = value.yx * sn;
    precise vec2 result = vec2(products.x - cross_products.x, cross_products.y + products.y);
    return result;
}

vec2 canonical_pitch(vec2 value, vec3 pitch)
{
    precise vec2 products = value * pitch.x;
    precise vec2 cross_products = value.yx * pitch.zy;
    precise vec2 result = vec2(products.x - cross_products.x, cross_products.y + products.y);
    return result;
}

vec4 canonical_project(mat4 projection, vec4 point)
{
    // Match the column-major CPU order, without driver-dependent fused dots.
    precise vec4 x = projection[0] * point.x;
    precise vec4 y = projection[1] * point.y;
    precise vec4 z = projection[2] * point.z;
    precise vec4 w = projection[3] * point.w;
    precise vec4 xy = x + y;
    precise vec4 xyz = xy + z;
    precise vec4 result = xyz + w;
    return result;
}

void main()
{
#ifdef VOXEL_PACKED_VERTEX
#ifdef VOXEL_VISIBLE_INSTANCE
    uvec2 triangle = visible_triangles.items[uint(gl_VertexIndex)/3u];
    uint bits = visible_vertices.bits;
    uint vertex_index = triangle_field(triangle,(uint(gl_VertexIndex)%3u)*bits) & ((1u<<bits)-1u);
    uint packed_vertex = visible_vertices.values[vertex_index];
    uint visible_instance = uint(gl_InstanceIndex)+triangle_field(triangle,bits*3u);
#endif
    uint bx = vertex_format.bits.x, by = vertex_format.bits.y, bz = vertex_format.bits.z;
    uvec3 cell = uvec3(packed_vertex & ((1u<<bx)-1u), (packed_vertex>>bx) & ((1u<<by)-1u), (packed_vertex>>(bx+by)) & ((1u<<bz)-1u));
#ifdef VOXEL_PACKED_EXACT_PRODUCTS
    // The encoder proves every coordinate product is exactly representable.
    // Fusing the origin addition is therefore bit-identical to CPU decoding.
    precise vec3 position = fma(vec3(cell),vertex_format.cell_step.xyz,vertex_format.origin.xyz);
#else
    precise vec3 scaled_cell = vec3(cell)*vertex_format.cell_step.xyz;
    precise vec3 position = scaled_cell+vertex_format.origin.xyz;
#endif
    uint normal_index = (packed_vertex>>(bx+by+bz)) & ((1u<<vertex_format.bits.w)-1u);
    vec3 normal = vertex_format.normals[normal_index].xyz;
    uint palette_index = packed_vertex>>(bx+by+bz+vertex_format.bits.w);
#ifdef VOXEL_VISIBLE_INSTANCE
    // The CPU validates this complete invariant template before selecting the
    // visible-primitive pipeline. All geometric arithmetic remains unchanged.
    vec3 texture_coord = vec3((float(palette_index)+0.5)/256,0.5,-3);
    vec3 vertex_colour = vec3(1);
    float opacity = 1;
    vec4 texture_region = vec4(0,0,1,1);
    uint surface_mode = 69u, object_id = 0u;
#else
    vec3 texture_coord = vec3((float(palette_index)+0.5)/256,uintBitsToFloat(vertex_format.surface_info.z),uintBitsToFloat(vertex_format.surface_info.w));
    vec3 vertex_colour = vertex_format.colour_opacity.xyz;
    float opacity = vertex_format.colour_opacity.w;
    vec4 texture_region = vertex_format.texture_region;
    uint surface_mode = vertex_format.surface_info.x, object_id = vertex_format.surface_info.y;
#endif
#endif
    vec3 p = position;
    vec3 n = normal;
    uv_page = texture_coord;
    material_surface = surface_mode & ~16u;
    if (uv_page.z >= 0 && (material_surface & 15u) != 2u && (material_surface & 15u) != 4u && (surface_mode & 16u) == 0u) uv_page.xy -= texture_region.xy;
    alpha = opacity;
    uv_region = texture_region;
    pick_id = object_id;
#ifdef VOXEL_VISIBLE_INSTANCE
    volume_instance = visible_instance;
#else
    volume_instance = uint(gl_InstanceIndex);
#endif
    volume_position = position;
    volume_eye = vec3(0);
    volume_face = normal.x != 0 ? (normal.x > 0 ? 1u : 0u) : normal.y != 0 ? (normal.y > 0 ? 3u : 2u) : (normal.z > 0 ? 5u : 4u);
    volume_plane = position[int(volume_face >> 1)];
    if (params.mode.x != 0u) {
#ifdef VOXEL_VISIBLE_INSTANCE
        Instance instance = instances.items[visible_instance];
#else
        Instance instance = instances.items[gl_InstanceIndex];
#endif
        vec4 scale = instance.scale_center;
        vec4 mirror = instance.mirror_layer_heading;
        if (params.mode.z != 0u) {
            vec3 eye_delta = (params.camera.xyz - instance.origin_opacity.xyz) + params.water.xyz;
            volume_eye = vec3(eye_delta.xy / scale.x + scale.zw, eye_delta.z / scale.y);
        }
        vec3 local = vec3((position.xy - scale.zw) * scale.x, position.z * scale.y);
        n = normalize(normal / vec3(scale.x, scale.x, scale.y));
        bool longitudinal = (uint(instance.identity.z) & 16u) != 0u;
        if (longitudinal) {
            local.x *= mirror.z;
            n = normalize(n / vec3(mirror.z, 1, 1));
        }
        bool authored_sample = instance.identity.w > 1.5 && texture_coord.z >= 0;
        vec3 sample_position = authored_sample ? texture_coord : position;
        if (!authored_sample && (uint(instance.identity.z) & 1u) == 0u && dot(n, vec3(1, 1, 2)) < -0.001) {
            if (n.x < -0.1) sample_position.x = mirror.x - sample_position.x;
            if (n.y < -0.1) sample_position.y = mirror.y - sample_position.y;
        }
        sample_position = vec3((sample_position.xy - scale.zw) * scale.x, sample_position.z * scale.y);
        if (longitudinal) sample_position.x *= mirror.z;
        if (instance.pitch.y != 0) {
            vec4 pitch = instance.pitch;
            local.xz = canonical_pitch(local.xz - vec2(0, pitch.w), pitch.xyz) + vec2(0, pitch.w);
            sample_position.xz = canonical_pitch(sample_position.xz - vec2(0, pitch.w), pitch.xyz) + vec2(0, pitch.w);
            n.xz = canonical_pitch(n.xz, pitch.xzy);
            n = normalize(n);
        }
        if (mirror.w != 0) {
            bool canonical_yaw = (uint(instance.identity.z) & 8u) != 0u;
            float cs = canonical_yaw ? mirror.x : cos(mirror.w);
            float sn = canonical_yaw ? mirror.y : sin(mirror.w);
            mat2 yaw = mat2(cs, sn, -sn, cs);
            if (canonical_yaw) {
                local.xy = canonical_rotate(local.xy, cs, sn);
                n.xy = canonical_rotate(n.xy, cs, sn);
                sample_position.xy = canonical_rotate(sample_position.xy, cs, sn);
            } else {
                local.xy = yaw * local.xy;
                n.xy = yaw * n.xy;
                sample_position.xy = yaw * sample_position.xy;
            }
        }
        p = instance.origin_opacity.xyz + local + n * (longitudinal ? 0 : mirror.z);
        bool local_bias = (uint(instance.identity.z) & 32u) != 0u;
        vec2 bias = instance.uv_transform.xy - (local_bias || uint(instance.identity.y + 0.5) == 2u ? vec2(0) : instance.region.xy);
        uv_page = vec3(bias + vec2(2 * (sample_position.y - sample_position.x), sample_position.x + sample_position.y - sample_position.z) * instance.uv_transform.z, instance.uv_transform.w);
        if (instance.identity.w > 0.5 && instance.identity.w < 1.5) uv_page = vec3(bias + texture_coord.xy * instance.uv_transform.z, instance.uv_transform.w);
        if (instance.identity.w > 1.5 && texture_coord.z < -2.5) uv_page = vec3(texture_coord.xy * (instance.region.zw - instance.region.xy), instance.uv_transform.w);
        if (instance.identity.w > 2.5) uv_page = vec3(texture_coord.xy, instance.uv_transform.w);
        if (instance.identity.w > 3.5) uv_page.xy *= instance.uv_transform.xy;
        alpha = instance.origin_opacity.w;
        uv_region = instance.region;
        if (texture_coord.z < -3.5) uv_page.z = -1;
        material_surface = uint(instance.identity.y + 0.5) | (surface_mode & 96u);
        pick_id = uint(instance.identity.x) | ((uint(instance.identity.z) & 2u) != 0u ? 0x80000000u : 0u);
    }
    gl_Position = canonical_project(params.view_projection, vec4(p - params.camera.xyz, 1));
    float finite_point = 1;
    if ((material_surface & 15u) == 2u) {
        finite_point = texture_coord.z < -1.5 ? 0 : 1;
        gl_Position = canonical_project(params.view_projection, vec4(p - params.camera.xyz * finite_point, finite_point));
        uv_page = vec3(texture_coord.xy, finite_point);
    }
    gl_Position.y = -gl_Position.y;
    gl_Position.z = params.camera.w * finite_point; // Infinite-far reversed Z, without cancellation.
    vec3 lighting_normal = (material_surface & 32u) != 0u ? vec3(n.xy, n.z / 0.408248290463863) : n;
    float light = 0.66 + 0.34 * max(dot(normalize(lighting_normal), normalize(vec3(-0.45, -0.65, 1))), 0);
    if ((material_surface & 32u) != 0u) light /= 0.66 + 0.34 * normalize(vec3(-0.45, -0.65, 1)).z;
    if ((material_surface & 64u) != 0u) light = 1;
    // Palette indices are discrete face data, never perspective interpolants.
    if ((material_surface & 15u) == 5u) material_surface |= uint(floor(uv_page.x * 1024 + 0.0001)) << 8;
    lit_colour = vertex_colour * light;
}
