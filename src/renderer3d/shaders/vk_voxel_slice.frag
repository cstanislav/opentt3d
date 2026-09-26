#version 450
#extension GL_GOOGLE_include_directive : require
// SPDX-License-Identifier: GPL-2.0-only
#include "vk_voxel_shared.glsl"
// Axis-fixed planes at original cell boundaries, with full-cell exposed masks.
layout(location=9) flat in uint volume_face;
layout(location=10) flat in float volume_plane;

void main()
{
    Instance instance = instances.items[volume_instance];
    ivec3 size = ivec3(volume.words[0],volume.words[1],volume.words[2]);
    vec3 origin = uintBitsToFloat(uvec3(volume.words[4],volume.words[5],volume.words[6]));
    vec3 step_size = uintBitsToFloat(uvec3(volume.words[8],volume.words[9],volume.words[10]));
    vec3 point = (volume_position-origin)/step_size;
    int axis = int(volume_face >> 1), u = (axis+1)%3, v = (axis+2)%3;
    ivec3 cell = ivec3(floor(point));
    cell[axis] = int(round((volume_plane-origin[axis])/step_size[axis]))-int(volume_face&1u);
    vec3 margin = (abs(dFdx(point))+abs(dFdy(point)))/exp2(params.water.w)+0.002;
    vec2 fraction = fract(vec2(point[u],point[v]));
    vec2 boundary = min(fraction,vec2(1)-fraction);
    uint index;
    if (any(lessThanEqual(boundary,vec2(margin[u],margin[v])))) {
        float depth;
        if (!raster_cell_neighbourhood(cell,volume_face,size,origin,step_size,point,max(margin[u],margin[v]),instance,index,depth)) discard;
    } else {
        uint surface = surface_word(cell,size);
        if ((surface & (1u << (16u+volume_face))) == 0u) discard;
        index = face_colour(surface&65535u,volume_face);
    }
    vec4 colour = palette_colour(index,instance.uv_transform.w);
    if (colour.a < 0.01) discard;
    output_colour = colour;
    output_id = pick_id;
}
