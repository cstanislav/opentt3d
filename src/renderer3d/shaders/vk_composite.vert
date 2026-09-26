#version 450
// SPDX-License-Identifier: GPL-2.0-only
layout(push_constant) uniform Parameters { vec4 destination; vec4 source; uvec4 mode; } params;
layout(location=0) out vec2 uv;
void main()
{
    vec2 corner = vec2(gl_VertexIndex & 1, (gl_VertexIndex >> 1) & 1);
    gl_Position = vec4(params.destination.xy + corner * params.destination.zw, 0, 1);
    uv = params.source.xy + corner * params.source.zw;
}
