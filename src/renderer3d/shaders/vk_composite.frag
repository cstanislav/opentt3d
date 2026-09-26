#version 450
// SPDX-License-Identifier: GPL-2.0-only
layout(set=0, binding=0) uniform sampler2D image;
layout(set=0, binding=1) uniform sampler2D animation;
layout(set=0, binding=2) uniform sampler2D palette;
layout(push_constant) uniform Parameters { vec4 destination; vec4 source; uvec4 mode; } params;
layout(location=0) in vec2 uv;
layout(location=0) out vec4 colour;
void main()
{
    colour = texture(image, uv);
    if (params.mode.x != 0u) {
        int index = int(floor(texture(animation, uv).r * 255 + 0.5));
        if (index > 0) {
            vec3 rgb = texelFetch(palette, ivec2(index, 0), 0).rgb;
            float brightness = max(max(colour.r, colour.g), colour.b);
            vec3 adjusted = rgb * (brightness > 0 ? brightness / 0.5 : 1);
            vec3 excess = clamp(adjusted - 1, 0, 1);
            float overbright = (excess.r + excess.g + excess.b) / 2;
            colour.rgb = clamp(adjusted + overbright * (1 - adjusted), 0, 1);
        }
    }
}
