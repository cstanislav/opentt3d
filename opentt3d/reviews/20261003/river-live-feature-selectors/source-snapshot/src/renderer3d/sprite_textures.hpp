/* SPDX-License-Identifier: GPL-2.0-only */
/** @file sprite_textures.hpp Bounded, palette-aware atlas of upstream-resolved sprites. */
#ifndef RENDERER3D_SPRITE_TEXTURES_HPP
#define RENDERER3D_SPRITE_TEXTURES_HPP

#include "../gfx_type.h"
#include "../zoom_type.h"
#include "geometry.hpp"
#include "atlas_allocator.hpp"
#include <unordered_map>
#include <atomic>
#include <stdexcept>

struct TileInfo;
struct SpriteBounds;

namespace Renderer3D {

static constexpr int ATLAS_SIZE = 1024;
static constexpr int ATLAS_PAGES = 24;

/** Distinct from malformed assets: the caller can reclaim stale packed sprites. */
class AtlasFull : public std::runtime_error {
public:
	AtlasFull() : std::runtime_error("Visible sprite textures exceed the atlas budget") {}
};

struct SpriteTexture {
	int page = -1, x = 0, y = 0, width = 0, height = 0;
	int source_width = 0, source_height = 0, x_offset = 0, y_offset = 0;
	unsigned zoom = 0;
	bool base_graphics = false;
	int ink_left = 0, ink_top = 0, ink_width = 0, ink_height = 0;
	bool opaque_surface = false;
	uint64_t last_used = 0;
	PaletteID palette = 0;
	TextureRegion Region() const
	{
		return {x/static_cast<float>(ATLAS_SIZE),y/static_cast<float>(ATLAS_SIZE),
			(x+width)/static_cast<float>(ATLAS_SIZE),(y+height)/static_cast<float>(ATLAS_SIZE)};
	}
	Vec3 UV(float source_x, float source_y) const
	{
		float scale = static_cast<float>(1U << zoom);
		return {(x + source_x / scale) / ATLAS_SIZE, (y + source_y / scale) / ATLAS_SIZE, static_cast<float>(page)};
	}
	Vec3 LocalUV(float source_x, float source_y) const
	{
		float scale = static_cast<float>(1U << zoom)*ATLAS_SIZE;
		return {source_x/scale,source_y/scale,static_cast<float>(page)};
	}
};

/** Match Classic terrain's approximately two native texels per physical world
 * unit. Use the native crop dimensions, never its current mip dimensions, so
 * texture-detail switches do not change the material's size in the world. */
inline void SetWorldTexelChart(InstanceData &data, const SpriteTexture &texture, TextureRegion crop,
	std::array<float,2> units_per_phase = {1,1}, float scale = 1)
{
	constexpr float texels_per_unit = 2;
	float width = static_cast<float>(texture.source_width)/ZOOM_BASE;
	float height = static_cast<float>(texture.source_height)/ZOOM_BASE;
	float pixels_x = std::max(1.0f,std::ceil(crop.right*width)-std::floor(crop.left*width));
	float pixels_y = std::max(1.0f,std::ceil(crop.bottom*height)-std::floor(crop.top*height));
	data.uv_transform[0] = texels_per_unit*units_per_phase[0]*scale/pixels_x;
	data.uv_transform[1] = texels_per_unit*units_per_phase[1]*scale/pixels_y;
	data.uv_transform[3] = static_cast<float>(texture.page);
	data.identity[3] = 4;
}

struct AtlasPage {
	std::vector<uint8_t> rgba, remap;
	AtlasAllocator allocator{ATLAS_SIZE};
	uint64_t last_used = 0;
	int dirty_left = ATLAS_SIZE, dirty_top = ATLAS_SIZE, dirty_right = 0, dirty_bottom = 0;
	void Reset();
	void ClearGutter(int x, int y, int width, int height);
	void Dirty(int x, int y, int width, int height);
};

enum class SpriteTextureLayer : uint8_t { Complete, CanalDikeGround };

/** Classic canal masonry uses neutral indices1..21; its independently painted
 * climate soil uses indices24+. Test source indices before palette recolouring. */
inline bool KeepCanalDikeGround(uint8_t index) { return index >= 24; }

/** The neutral-masonry/climate-soil partition was reviewed for this palette.
 * Other base sets, including RGB sprites without remap indices, stay intact. */
inline bool SupportsCanalDikeGround(std::string_view base_set) { return base_set == "OpenGFX2 Classic"; }
bool IsClassicCanalDikeSprite(SpriteID image);

class SpriteTextures {
	std::unordered_map<uint64_t, SpriteTexture> entries;
	SpriteTexture *recent_palette = nullptr; ///< Node-stable lookup only; cleared before atlas retirement.
	uint64_t epoch = 0;
	bool invalid = false;
	std::vector<AtlasPage> spare_pages; ///< Reuse the existing repack peak, at most 2 * ATLAS_PAGES total CPU pages.
	AtlasPage AcquirePage();
	std::pair<int, Point> Allocate(int width, int height);
public:
	std::vector<AtlasPage> pages;
	void BeginScene();
	void Invalidate() { invalid = true; }
	void Clear();
	void Repack();
	const SpriteTexture &Get(SpriteID image, PaletteID palette, unsigned zoom = 0, bool opaque_surface = false, SpriteTextureLayer layer = SpriteTextureLayer::Complete);
	const SpriteTexture &GetPalette(PaletteID palette = 0);
	void MarkAllDirty();
};

SpriteTextures &Textures();
void UsePaletteMaterial(InstanceData &data, PaletteID palette = 0);
void InvalidateTextures();
uint64_t TextureGeneration();
bool IsBaseGraphicsSprite(SpriteID image);
void ExportSpriteReference(SpriteID image, PaletteID palette, const std::string &filename, std::vector<uint8_t> *palette_indices = nullptr);
void ExportHouseReferences();
void ExportIndustryReferences();
void ExportBridgeReferences();
void ExportTerrainReferences();
/** Optional read-only export of sprites selected by real lock/river draw callbacks. */
bool WaterSourceTracingEnabled();
void ObserveWaterSource(const TileInfo &tile, SpriteID image, PaletteID palette, std::array<int,3> origin,
	const SpriteBounds *bounds, bool transparent, bool cropped, bool diagnostic);
struct RiverSourceSelector;
void RetainRiverSelector(const TileInfo &tile, const RiverSourceSelector &selector);
void ExportStationReferences();
void ExportRailDetailReferences();
void ExportInfrastructureReferences();
void ExportObjectReferences();
void ExportEffectReferences();
void ExportFenceGallery(unsigned style, unsigned slope, std::optional<unsigned> layout = {});
void VerifyFenceModels();
void ExportFoundationGallery(unsigned slope, unsigned foundation);
void VerifyFoundationModels();
SpriteID IndustryBodySprite(unsigned graphics);
void ExportHouseModelGallery(unsigned house, bool industry = false);
void VerifyGPUScene(bool vehicle_poses = true);
void VerifyInstanceOrdering();
void VerifyClipping();
void VerifyTextureMipCache();
void VerifyCanalDikeGroundTexture(SpriteID image);

} // namespace Renderer3D
#endif
