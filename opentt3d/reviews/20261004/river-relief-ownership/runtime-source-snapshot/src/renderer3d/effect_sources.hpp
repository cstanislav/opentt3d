/* SPDX-License-Identifier: GPL-2.0-only */
/** @file effect_sources.hpp Read-only original effect artwork, independent of simulation ticks. */
#ifndef RENDERER3D_EFFECT_SOURCES_HPP
#define RENDERER3D_EFFECT_SOURCES_HPP

#include "../table/sprites.h"

namespace Renderer3D {
struct EffectSourceFamily { const char *name; SpriteID first, last; };
inline constexpr EffectSourceFamily EFFECT_SOURCE_FAMILIES[] = {
	{"chimney",SPR_CHIMNEY_SMOKE_0,SPR_CHIMNEY_SMOKE_7},
	{"steam",SPR_STEAM_SMOKE_0,SPR_STEAM_SMOKE_4},
	{"diesel",SPR_DIESEL_SMOKE_0,SPR_DIESEL_SMOKE_5},
	{"electric-spark",SPR_ELECTRIC_SPARK_0,SPR_ELECTRIC_SPARK_5},
	{"smoke",SPR_SMOKE_0,SPR_SMOKE_4},
	{"explosion-large",SPR_EXPLOSION_LARGE_0,SPR_EXPLOSION_LARGE_F},
	{"breakdown",SPR_BREAKDOWN_SMOKE_0,SPR_BREAKDOWN_SMOKE_3},
	{"explosion-small",SPR_EXPLOSION_SMALL_0,SPR_EXPLOSION_SMALL_B},
	{"bulldozer",SPR_BULLDOZER_NE,SPR_BULLDOZER_NW},
	{"bubble",SPR_BUBBLE_0,SPR_BUBBLE_ABSORB_4},
};

constexpr bool IsPresentableEffectSource(SpriteID image)
{
	/* The original BubbleTick replaces this threshold before viewport update. */
	if (image == SPR_BUBBLE_GENERATE_3) return false;
	for (const auto &family : EFFECT_SOURCE_FAMILIES) if (image >= family.first && image <= family.last) return true;
	return false;
}
} // namespace Renderer3D
#endif
