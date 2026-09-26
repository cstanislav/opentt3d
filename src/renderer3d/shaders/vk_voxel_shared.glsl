// SPDX-License-Identifier: GPL-2.0-only
// Shared full-cell material and exact unit-face raster queries.
layout(location=3) flat in vec4 uv_region;
layout(location=5) flat in uint pick_id;
layout(location=6) flat in uint volume_instance;
layout(location=7) in vec3 volume_position;
layout(location=8) flat in vec3 volume_eye;
layout(set=0, binding=0) uniform sampler2DArray colour_atlas;
layout(set=0, binding=1) uniform sampler2DArray remap_atlas;
layout(set=0, binding=2) uniform sampler2D palette;
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
layout(std430, set=0, binding=4) readonly buffer Volume { uint words[]; } volume;
layout(push_constant) uniform Parameters {
    mat4 view_projection;
    vec4 camera;
    vec4 water;
    uvec4 mode;
} params;
layout(location=0) out vec4 output_colour;
layout(location=1) out uint output_id;

uint surface_word(ivec3 cell, ivec3 size)
{
    if (any(lessThan(cell, ivec3(0))) || any(greaterThanEqual(cell, size))) return 0u;
    uint index = uint((cell.z * size.y + cell.y) * size.x + cell.x);
    return volume.words[volume.words[20] + index];
}

uint face_colour(uint material, uint face)
{
    uint packed = volume.words[volume.words[11] + 2u * (material - 1u) + (face >> 2)];
    return (packed >> (8u * (face & 3u))) & 255u;
}

vec4 palette_colour(uint index, float page)
{
    ivec2 texel = ivec2(uv_region.xy * 1024 + 0.5) + ivec2(int(index), 0);
    ivec3 address = ivec3(texel, int(page + 0.5));
    vec4 colour = texelFetch(colour_atlas, address, 0);
    vec2 remap = floor(texelFetch(remap_atlas, address, 0).rg * 255 + 0.5);
    if (remap.x > 0) {
        vec3 rgb = floor(texelFetch(palette, ivec2(int(remap.x), 0), 0).rgb * 255 + 0.5);
        rgb = floor(rgb * remap.y / 128);
        vec3 excess = max(rgb - 255, vec3(0));
        float overbright = floor((excess.r + excess.g + excess.b) / 2);
        colour.rgb = min(rgb + floor(overbright * max(vec3(255) - rgb, vec3(0)) / 256), vec3(255)) / 255;
    }
    return colour;
}

// Explicit FMA keeps one IEEE rounding without Metal's non-inlined
// NoContraction add/multiply wrappers. Immutable one/zero words prevent the
// shader optimizer from folding these back into those expensive wrappers.
vec3 rounded_add(vec3 a, vec3 b) { precise vec3 result = fma(a,vec3(uintBitsToFloat(volume.words[21])),b); return result; }
vec3 rounded_subtract(vec3 a, vec3 b) { precise vec3 result = fma(a,vec3(uintBitsToFloat(volume.words[21])),-b); return result; }
vec3 rounded_multiply(vec3 a, vec3 b)
{
    vec3 zero = uintBitsToFloat(((floatBitsToUint(a)^floatBitsToUint(b)) & uvec3(0x80000000u)) | uvec3(volume.words[22]));
    precise vec3 result = fma(a,b,zero);
    return result;
}
vec2 rounded_add(vec2 a, vec2 b) { precise vec2 result = fma(a,vec2(uintBitsToFloat(volume.words[21])),b); return result; }
vec2 rounded_multiply(vec2 a, vec2 b)
{
    vec2 zero = uintBitsToFloat(((floatBitsToUint(a)^floatBitsToUint(b)) & uvec2(0x80000000u)) | uvec2(volume.words[22]));
    precise vec2 result = fma(a,b,zero);
    return result;
}

vec4 reference_clip(vec3 point, uint face, Instance instance)
{
    vec3 scale = vec3(instance.scale_center.x,instance.scale_center.x,instance.scale_center.y);
    vec3 local = rounded_multiply(rounded_subtract(point,vec3(instance.scale_center.zw,0)),scale);
    // Eligibility guarantees zero normal offset and yaw. Isolate each rounding
    // barrier rather than propagating NoContraction through unrelated arithmetic.
    vec3 world = rounded_add(instance.origin_opacity.xyz,local);
    // The reference vertex path rounds its reconstructed position before the
    // matrix multiply. Do not fuse cell construction/camera subtraction into it:
    // a single ULP can change which side of a subpixel boundary owns a pixel.
    vec3 relative = rounded_subtract(world,params.camera.xyz);
    return params.view_projection * vec4(relative,1);
}

float edge(vec2 a, vec2 b, vec2 point)
{
    vec2 products = rounded_multiply(b-a,point.yx-a.yx);
    return products.x-products.y;
}

bool inclusive_edge(vec2 a, vec2 b)
{
    vec2 d = b-a;
    return d.y < 0 || (d.y == 0 && d.x > 0);
}

vec2 projected_xy(vec4 clip)
{
    // Shader division may use a less accurate reciprocal than fixed-function
    // viewport setup. Correct its residual before rounding to the same subpixel
    // grid: even a one-ULP quotient error can replace a visible leaf edge.
    float reciprocal = 1 / clip.w;
    vec2 numerator = vec2(clip.x,-clip.y);
    precise float residual = fma(-reciprocal,clip.w,uintBitsToFloat(volume.words[21]));
    precise float corrected = fma(residual,reciprocal,reciprocal);
    return rounded_multiply(numerator,vec2(corrected));
}

vec2 screen_point(vec4 clip, vec2 dimensions)
{
    vec2 half_size = dimensions*0.5;
    return rounded_add(rounded_multiply(projected_xy(clip),half_size),half_size);
}

float triangle_depth(vec4 ca, vec4 cb, vec4 cc)
{
    if (min(ca.w,min(cb.w,cc.w)) <= params.camera.w) return -1;
    vec2 dimensions = vec2(params.mode.w & 65535u,params.mode.w >> 16);
    float subpixel = exp2(params.water.w);
    vec2 sa = screen_point(ca,dimensions), sb = screen_point(cb,dimensions), sc = screen_point(cc,dimensions);
    // Subpixel is a power of two; its multiplication is exact before the bias.
    vec2 a = floor(fma(sa,vec2(subpixel),vec2(0.5))), b = floor(fma(sb,vec2(subpixel),vec2(0.5))), c = floor(fma(sc,vec2(subpixel),vec2(0.5)));
    float area = edge(a,b,c);
    if (area == 0) return -1;
    if (area < 0) { vec2 p = b; b = c; c = p; vec4 clip = cb; cb = cc; cc = clip; area = -area; }
    vec2 pixel = gl_FragCoord.xy * subpixel;
    float e0 = edge(b,c,pixel), e1 = edge(c,a,pixel), e2 = edge(a,b,pixel);
    if (e0 < 0 || e1 < 0 || e2 < 0 || (e0 == 0 && !inclusive_edge(b,c)) ||
            (e1 == 0 && !inclusive_edge(c,a)) || (e2 == 0 && !inclusive_edge(a,b))) return -1;
    return params.camera.w * ((e0 / ca.w + e1 / cb.w + e2 / cc.w) / area);
}

// Resolve the same discrete face ownership as unit-cell rasterization near a
// projected cell edge. This does not alter cells or admit a colour tolerance.
bool raster_cell_neighbourhood(ivec3 hit_cell, uint face, ivec3 size, vec3 origin, vec3 step_size,
        vec3 ray_point, float margin, Instance instance, out uint index, out float depth)
{
    depth = -1;
    index = 0u;
    int axis = int(face >> 1), positive = int(face & 1u);
    int u = (axis+1)%3, v = (axis+2)%3;
    for (int y = -1; y <= 1; ++y) for (int x = -1; x <= 1; ++x) {
        ivec3 cell = hit_cell;
        cell[u] += x; cell[v] += y;
        vec2 within = vec2(ray_point[u]-float(cell[u]),ray_point[v]-float(cell[v]));
        if (any(lessThan(within,vec2(-margin))) || any(greaterThan(within,vec2(1+margin)))) continue;
        uint surface = surface_word(cell,size);
        if ((surface & (1u << (16u+face))) == 0u) continue;
        uint material = surface & 65535u;
        vec3 a = vec3(cell); a[axis] += float(positive);
        vec3 b = a, c = a, d = a;
        b[u] += 1; c[u] += 1; c[v] += 1; d[v] += 1;
        vec4 ca = reference_clip(origin+a*step_size,face,instance);
        vec4 cb = reference_clip(origin+b*step_size,face,instance);
        vec4 cc = reference_clip(origin+c*step_size,face,instance);
        vec4 cd = reference_clip(origin+d*step_size,face,instance);
        float candidate = max(triangle_depth(ca,cb,cc),triangle_depth(ca,cc,cd));
        if (candidate >= 0 && candidate >= depth) { depth = candidate; index = face_colour(material,face); }
    }
    return depth >= 0;
}
