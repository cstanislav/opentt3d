#version 450
// SPDX-License-Identifier: GPL-2.0-only
layout(location=0) in vec3 lit_colour;
layout(location=1) in vec3 uv_page;
layout(location=2) in float alpha;
layout(location=3) flat in vec4 uv_region;
layout(location=4) flat in uint material_surface;
layout(location=5) flat in uint pick_id;
layout(set=0, binding=0) uniform sampler2DArray colour_atlas;
layout(set=0, binding=1) uniform sampler2DArray remap_atlas;
layout(set=0, binding=2) uniform sampler2D palette;
layout(push_constant) uniform Parameters {
    mat4 view_projection;
    vec4 camera;
    vec4 water;
    uvec4 mode;
} params;
layout(location=0) out vec4 output_colour;
layout(location=1) out uint output_id;

void main()
{
    uint surface = material_surface & 15u;
    if (surface == 5u && !gl_FrontFacing) discard;
    if ((alpha < 0.99) != (params.mode.y != 0u)) discard;
    vec4 colour = vec4(lit_colour, alpha);
    if (uv_page.z >= 0) {
        vec3 uv = uv_page;
        if (surface == 2u) {
            vec2 cell = fract(uv.xy / max(uv.z, 1e-20)) * 16;
            uv.z = params.water.z;
            uv.xy = params.water.xy - uv_region.xy + vec2(2 * (cell.y - cell.x), cell.x + cell.y) * params.water.w;
        }
        vec2 extent = (uv_region.zw - uv_region.xy) * 1024;
        vec2 local = surface == 4u ? fract(uv.xy) * extent : uv.xy * 1024;
        if (surface == 5u) local = vec2(float((material_surface >> 8) & 255u) + 0.5, 0.5);
        if (surface == 0u && (local.x < 0 || local.y < 0 || local.x >= extent.x || local.y >= extent.y)) discard;
        // Atlas relocation leaves sprite-local interpolation and texel selection unchanged.
        ivec2 texel = clamp(ivec2(floor(local + 0.0001)), ivec2(0), ivec2(extent + 0.5) - 1) + ivec2(uv_region.xy * 1024 + 0.5);
        ivec3 address = ivec3(texel, int(uv.z + 0.5));
        colour = texelFetch(colour_atlas, address, 0);
        vec2 remap = floor(texelFetch(remap_atlas, address, 0).rg * 255 + 0.5);
        if (remap.x > 0) {
            vec3 rgb = floor(texelFetch(palette, ivec2(int(remap.x), 0), 0).rgb * 255 + 0.5);
            rgb = floor(rgb * remap.y / 128);
            vec3 excess = max(rgb - 255, vec3(0));
            float overbright = floor((excess.r + excess.g + excess.b) / 2);
            colour.rgb = min(rgb + floor(overbright * max(vec3(255) - rgb, vec3(0)) / 256), vec3(255)) / 255;
        }
        if ((material_surface & 32u) != 0u) colour.rgb *= lit_colour;
        colour.a *= alpha;
    }
    if (colour.a < 0.01) discard;
    if (surface == 3u) colour.rgb = vec3(0);
    output_colour = colour;
    output_id = pick_id;
}
