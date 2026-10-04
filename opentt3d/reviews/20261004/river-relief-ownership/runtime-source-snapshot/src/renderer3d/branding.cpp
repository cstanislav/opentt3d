/* SPDX-License-Identifier: GPL-2.0-only */
/** @file branding.cpp Authored pixel-letter wordmark, painted by the original UI blitter. */
#include "../stdafx.h"
#include "branding.h"
#include "../gfx_func.h"
#include "../palette_func.h"
#include "../zoom_func.h"

namespace Renderer3D {

void DrawTitleLogo(int width)
{
	/* O P E N T T 3 D. Each row is an explicitly drawn five-pixel glyph. */
	static constexpr uint8_t glyphs[][7] = {
		{14, 17, 17, 17, 17, 17, 14}, {30, 17, 17, 30, 16, 16, 16},
		{31, 16, 16, 30, 16, 16, 31}, {17, 25, 25, 21, 19, 19, 17},
		{31, 4, 4, 4, 4, 4, 4}, {31, 4, 4, 4, 4, 4, 4},
		{30, 1, 1, 14, 1, 1, 30}, {30, 17, 17, 17, 17, 17, 30},
	};
	int pixel = std::max(1, std::min(ScaleGUITrad(7), (width - ScaleGUITrad(32)) / 50));
	int depth = std::max(1, pixel / 2), x = (width - 47 * pixel - depth) / 2, y = ScaleGUITrad(36);
	for (int layer = depth; layer >= 0; --layer) {
		for (unsigned letter = 0; letter < std::size(glyphs); ++letter) {
			for (unsigned row = 0; row < 7; ++row) for (unsigned column = 0; column < 5; ++column) {
				if ((glyphs[letter][row] & (1U << (4 - column))) == 0) continue;
				PixelColour colour = layer != 0 ? GetColourGradient(COLOUR_DARK_BLUE, SHADE_DARK) :
					GetColourGradient(letter >= 6 ? COLOUR_YELLOW : COLOUR_LIGHT_BLUE, row < 3 ? SHADE_LIGHTEST : SHADE_LIGHTER);
				int left = x + (letter * 6 + column) * pixel + layer, top = y + row * pixel + layer;
				GfxFillRect(left, top, left + pixel - 1, top + pixel - 1, colour);
			}
		}
	}
}

} // namespace Renderer3D
