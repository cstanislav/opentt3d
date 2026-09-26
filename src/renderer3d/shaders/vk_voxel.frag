#version 450
#extension GL_GOOGLE_include_directive : require
// SPDX-License-Identifier: GPL-2.0-only
#include "vk_voxel_shared.glsl"
layout(depth_less) out float gl_FragDepth;

void main()
{
    // The guarded front proxy is always closer than its actual cell surfaces,
    // permitting conservative early depth rejection. Near-plane/inside views
    // use the original mesh path rather than an artificial clipped cap.
    if (!gl_FrontFacing) discard;
    Instance instance = instances.items[volume_instance];
    ivec3 size = ivec3(volume.words[0], volume.words[1], volume.words[2]);
    vec3 origin = uintBitsToFloat(uvec3(volume.words[4], volume.words[5], volume.words[6]));
    vec3 step_size = uintBitsToFloat(uvec3(volume.words[8], volume.words[9], volume.words[10]));
    vec3 low = vec3(volume.words[12], volume.words[13], volume.words[14]) - 1;
    vec3 high = vec3(volume.words[16], volume.words[17], volume.words[18]) + 1;
    // Anchor the traversal at the interpolated box surface rather than adding a
    // nearly-unit t to a distant eye; cell precision then stays local to the box.
    vec3 anchor = (volume_position - origin) / step_size;
    vec3 eye = (volume_eye - origin) / step_size;
    vec3 ray = normalize(anchor - eye);
    // Bound the grid-space displacement of a subpixel-rounded raster edge. A
    // full-subpixel guard plus local floating-point slack keeps neighbouring
    // candidates; faces farther away cannot cover this pixel.
    float pixel_radius = (length(anchor-eye)+length(high-low)) * (length(dFdx(ray))+length(dFdy(ray))) / exp2(params.water.w) + 0.002;
    vec3 plane_margin = vec3(pixel_radius) / max(abs(ray),vec3(1e-20));
    float enter = -1e30, leave = 1e30;
    uint face = 0u;
    for (int axis = 0; axis < 3; ++axis) {
        if (abs(ray[axis]) < 1e-20) {
            if (anchor[axis] < low[axis] || anchor[axis] > high[axis]) discard;
        } else {
            float a = (low[axis] - anchor[axis]) / ray[axis];
            float b = (high[axis] - anchor[axis]) / ray[axis];
            float near_side = min(a,b), far_side = max(a,b);
            if (near_side >= enter) { enter = near_side; face = uint(axis * 2 + (ray[axis] < 0 ? 1 : 0)); }
            leave = min(leave,far_side);
        }
    }
    vec3 world_ray = ray * step_size * vec3(instance.scale_center.x, instance.scale_center.x, instance.scale_center.y);
    float depth_rate = (params.view_projection * vec4(world_ray,0)).w;
    vec3 depth_gradient = vec3(params.view_projection[0].w,params.view_projection[1].w,params.view_projection[2].w) *
        step_size * vec3(instance.scale_center.x,instance.scale_center.x,instance.scale_center.y);
    float depth_slack = min(3 * dot(abs(depth_gradient),vec3(1)),
        2 * length(depth_gradient) * max(plane_margin.x,max(plane_margin.y,plane_margin.z)) + 0.002);
    float anchor_depth = reference_clip(volume_position,0u,instance).w;
    if (depth_rate <= 0) discard;
    float minimum = -length(anchor - eye) + params.camera.w / depth_rate;
    float time = max(enter,minimum);
    if (!(time < leave)) discard;
    ivec3 direction = ivec3(sign(ray));
    ivec3 cell = ivec3(floor(anchor + ray * time + ray * 0.0001));
    vec3 next_time, delta;
    for (int axis = 0; axis < 3; ++axis) {
        if (direction[axis] == 0) { next_time[axis] = 1e30; delta[axis] = 1e30; }
        else {
            float boundary = float(cell[axis] + (direction[axis] > 0 ? 1 : 0));
            next_time[axis] = (boundary - anchor[axis]) / ray[axis];
            delta[axis] = abs(1 / ray[axis]);
        }
    }
    float best_depth = -1;
    uint best_index = 0u;
    int limit = size.x + size.y + size.z + 9;
    for (int visited = 0; visited < limit && time < leave; ++visited) {
        // All future candidates lie within two grid cells of their increasing
        // ray parameter. The smaller of that box bound and the conservative
        // subpixel cone bounds their nearest possible clip depth.
        if (best_depth >= 0 && anchor_depth + depth_rate*time - depth_slack > params.camera.w / best_depth) break;
        uint clearance = surface_word(cell,size) >> 24;
        if (clearance > 3u) {
            // No surface cell lies within this Chebyshev neighbourhood. Keep
            // three cells around the destination for the complete raster guard.
            time += (float(clearance)-3) / max(abs(ray.x),max(abs(ray.y),abs(ray.z)));
            if (time >= leave) break;
            cell = ivec3(floor(anchor+ray*time+ray*0.0001));
            for (int axis = 0; axis < 3; ++axis) if (direction[axis] != 0) {
                float boundary = float(cell[axis]+(direction[axis] > 0 ? 1 : 0));
                next_time[axis] = (boundary-anchor[axis]) / ray[axis];
            }
        } else {
            uint index;
            float depth;
            if (raster_cell_neighbourhood(cell,face,size,origin,step_size,anchor+ray*time,plane_margin[int(face >> 1)],instance,index,depth) && depth > best_depth &&
                    palette_colour(index,instance.uv_transform.w).a >= 0.01) {
                best_depth = depth; best_index = index;
            }
        }
        int axis = next_time.x < next_time.y ? 0 : 1;
        if (next_time.z <= next_time[axis]) axis = 2;
        time = next_time[axis]; next_time[axis] += delta[axis];
        cell[axis] += direction[axis]; face = uint(axis * 2 + (direction[axis] < 0 ? 1 : 0));
    }
    if (best_depth < 0) discard;
    gl_FragDepth = best_depth;
    output_colour = palette_colour(best_index,instance.uv_transform.w);
    output_id = pick_id;
}
