/* SPDX-License-Identifier: GPL-2.0-only */
/** @file sprite_textures.cpp Decode actual Classic base-set images via upstream loaders. */

#include "../stdafx.h"
#include "sprite_textures.hpp"
#include "texture_bounds.hpp"
#include "profiling.h"
#include "../base_media_graphics.h"
#include "../spritecache.h"
#include "../palette_func.h"
#include "../table/sprites.h"
#include "../debug.h"
#include <fstream>

namespace Renderer3D {

SpriteTextures &Textures() { static SpriteTextures textures; return textures; }
static std::atomic<uint64_t> generation{0};
void InvalidateTextures() { Textures().Invalidate(); ++generation; }
uint64_t TextureGeneration() { return generation.load(); }

static bool MaterialLookupCacheEnabled()
{
	static const bool enabled = [] { const char *value = std::getenv("OPENTT3D_MATERIAL_LOOKUP_CACHE"); return value == nullptr || std::string_view(value) != "0"; }();
	return enabled;
}

bool IsBaseGraphicsSprite(SpriteID image)
{
	image &= SPRITE_MASK;
	/* Provenance is per source file, not per tree on every draw tick. Reloads
	 * invalidate both tables before any SpriteFile address may be reused. The
	 * bounded original-ID table also retains custom replacements as negative
	 * entries; dynamic NewGRF IDs still resolve their actual source file. */
	static std::unordered_map<const SpriteFile *, bool> sources;
	static std::array<int8_t,SPR_NEWGRFS_BASE> original_ids{};
	static uint64_t source_generation = UINT64_MAX;
	uint64_t current = TextureGeneration();
	if (source_generation != current) { sources.clear(); original_ids.fill(0); source_generation = current; }
	if (MaterialLookupCacheEnabled() && image < original_ids.size() && original_ids[image] != 0) return original_ids[image] > 0;
	const SpriteFile *file = GetOriginFile(image);
	if (file == nullptr) return false; // Missing sprites may be installed later; do not cache absence.
	bool base_graphics;
	if (auto found = sources.find(file); found != sources.end()) base_graphics = found->second;
	else {
		base_graphics = file->GetSimplifiedFilename() == "openttd" || file->GetSimplifiedFilename() == "orig_extra";
		if (!base_graphics) {
			if (const GraphicsSet *set = BaseGraphics::GetUsedSet(); set != nullptr) {
				for (const MD5File &base : set->files) if (base.filename == file->GetFilename()) { base_graphics = true; break; }
			}
		}
		sources.emplace(file, base_graphics);
	}
	if (image < original_ids.size()) original_ids[image] = base_graphics ? 1 : -1;
	return base_graphics;
}

class TextureDecoder final : public SpriteEncoder {
public:
	using Family = std::array<std::unique_ptr<TextureDecoder>,to_underlying(ZoomLevel::Max)+1>;
	std::vector<SpriteLoader::CommonPixel> pixels;
	int width = 0, height = 0, source_width = 0, source_height = 0, x_offset = 0, y_offset = 0;
	int ink_left=0,ink_top=0,ink_width=0,ink_height=0;
	unsigned zoom;
	Family *family;
	explicit TextureDecoder(unsigned zoom, Family *family = nullptr) : zoom(zoom), family(family) {}
	bool Is32BppSupported() override { return true; }
	Sprite *Encode(SpriteType, const SpriteLoader::SpriteCollection &collection, SpriteAllocator &) override
	{
		const auto &root = collection.Root();
		source_width = root.width; source_height = root.height;
		x_offset = root.x_offs; y_offset = root.y_offs;
		auto bounds = FindInkBounds(root.width, root.height, [&](int x, int y) { return root.data[static_cast<size_t>(y) * root.width + x].a; });
		ink_left = bounds.left; ink_top = bounds.top; ink_width = bounds.width; ink_height = bounds.height;
		if (family != nullptr) {
			/* The upstream loader has already resolved every native/fallback mip.
			 * Retain those exact pixels instead of decoding the same sprite again
			 * when a moving camera crosses the next texture-detail boundary. */
			for (unsigned requested = 0; requested < family->size(); ++requested) {
				unsigned selected = requested;
				while (selected < to_underlying(ZoomLevel::Max) &&
					(collection[static_cast<ZoomLevel>(selected)].width+2 > ATLAS_SIZE || collection[static_cast<ZoomLevel>(selected)].height+2 > ATLAS_SIZE)) ++selected;
				const auto &sprite = collection[static_cast<ZoomLevel>(selected)];
				auto level = std::make_unique<TextureDecoder>(selected);
				level->source_width = source_width; level->source_height = source_height;
				level->x_offset = x_offset; level->y_offset = y_offset;
				level->ink_left = ink_left; level->ink_top = ink_top; level->ink_width = ink_width; level->ink_height = ink_height;
				level->width = sprite.width; level->height = sprite.height;
				level->pixels.assign(sprite.data,sprite.data+static_cast<size_t>(sprite.width)*sprite.height);
				(*family)[requested] = std::move(level);
			}
			return nullptr;
		}
		while (zoom < to_underlying(ZoomLevel::Max) &&
			(collection[static_cast<ZoomLevel>(zoom)].width + 2 > ATLAS_SIZE || collection[static_cast<ZoomLevel>(zoom)].height + 2 > ATLAS_SIZE)) ++zoom;
		const auto &sprite = collection[static_cast<ZoomLevel>(zoom)];
		width = sprite.width; height = sprite.height;
		pixels.assign(sprite.data, sprite.data + static_cast<size_t>(width) * height);
		return nullptr; // The custom encoder owns its value-only output.
	}
};

void AtlasPage::Dirty(int x, int y, int width, int height)
{
	dirty_left = std::min(dirty_left, x); dirty_top = std::min(dirty_top, y);
	dirty_right = std::max(dirty_right, x + width); dirty_bottom = std::max(dirty_bottom, y + height);
}

void AtlasPage::Reset()
{
	allocator = AtlasAllocator{ATLAS_SIZE};
	last_used = 0;
	dirty_left = dirty_top = ATLAS_SIZE;
	dirty_right = dirty_bottom = 0;
	/* resize initializes a new buffer once, but leaves pooled storage intact.
	 * Every allocated rectangle and gutter is overwritten before GPU upload. */
	rgba.resize(static_cast<size_t>(ATLAS_SIZE) * ATLAS_SIZE * 4);
	remap.resize(static_cast<size_t>(ATLAS_SIZE) * ATLAS_SIZE * 2);
}

void AtlasPage::ClearGutter(int x, int y, int width, int height)
{
	for (int row : {y-1,y+height}) {
		size_t start = static_cast<size_t>(row) * ATLAS_SIZE + x - 1;
		std::fill_n(rgba.data()+start*4,(width+2)*4,0);
		std::fill_n(remap.data()+start*2,(width+2)*2,0);
	}
	for (int row = y; row < y+height; ++row) for (int column : {x-1,x+width}) {
		size_t pixel = static_cast<size_t>(row) * ATLAS_SIZE + column;
		std::fill_n(rgba.data()+pixel*4,4,0);
		std::fill_n(remap.data()+pixel*2,2,0);
	}
}

AtlasPage SpriteTextures::AcquirePage()
{
	AtlasPage page;
	if (!spare_pages.empty()) { page = std::move(spare_pages.back()); spare_pages.pop_back(); }
	page.Reset();
	return page;
}

void SpriteTextures::Clear()
{
	recent_palette = nullptr;
	entries.clear();
	pages.clear();
	spare_pages.clear();
	invalid = false;
}

void SpriteTextures::Repack()
{
	Profile::Scope timer(Profile::Section::AtlasRepack);
	/* Move existing texels instead of synchronously decoding/dilating all the
	 * HighDef sprites again when a moving camera fragments the atlas. */
	std::vector<std::pair<uint64_t, SpriteTexture>> retained(entries.begin(), entries.end());
	/* Retain the current capture and recent secondary viewports, not every
	 * resolution/palette ever visited by a moving camera. */
	std::erase_if(retained, [&](const auto &entry) { return entry.second.last_used + 4 < epoch; });
	std::sort(retained.begin(), retained.end(), [](const auto &a, const auto &b) {
		if (a.second.height != b.second.height) return a.second.height > b.second.height;
		return a.second.width > b.second.width;
	});
	auto old_pages = std::move(pages);
	pages.clear();
	recent_palette = nullptr;
	entries.clear();
	/* Repacking is a bulk operation: sorted shelves are linear in the number of
	 * sprites. Repeated general-purpose rectangle pruning made this a 50ms stall. */
	struct Shelf { int x = 0, y = 0, height = 0; std::vector<AtlasAllocator::Area> free; };
	std::vector<Shelf> shelves;
	for (auto [key, texture] : retained) {
		int width = texture.width + 2, height = texture.height + 2;
		size_t index = 0;
		for (; index < shelves.size(); ++index) {
			const auto &shelf = shelves[index];
			if ((shelf.x + width <= ATLAS_SIZE && height <= shelf.height) || shelf.y + shelf.height + height <= ATLAS_SIZE) break;
		}
		if (index == shelves.size()) {
			if (pages.size() == ATLAS_PAGES) continue; // A subsequent capture reloads evicted source pixels from the bounded cache.
			shelves.emplace_back();
			pages.push_back(AcquirePage());
		}
		auto &shelf = shelves[index];
		if (shelf.x + width > ATLAS_SIZE || height > shelf.height) {
			if (shelf.x < ATLAS_SIZE && shelf.height > 0) shelf.free.push_back({shelf.x, shelf.y, ATLAS_SIZE - shelf.x, shelf.height});
			shelf.y += shelf.height; shelf.x = 0; shelf.height = height;
		}
		Point location{shelf.x + 1, shelf.y + 1};
		if (height < shelf.height) shelf.free.push_back({shelf.x, shelf.y + height, width, shelf.height - height});
		shelf.x += width;
		const auto &source = old_pages[texture.page];
		auto &destination = pages[index];
		for (int y = -1; y <= texture.height; ++y) {
			size_t from = static_cast<size_t>(texture.y + y) * ATLAS_SIZE + texture.x - 1;
			size_t to = static_cast<size_t>(location.y + y) * ATLAS_SIZE + location.x - 1;
			std::copy_n(source.rgba.data() + from * 4, (texture.width+2) * 4, destination.rgba.data() + to * 4);
			std::copy_n(source.remap.data() + from * 2, (texture.width+2) * 2, destination.remap.data() + to * 2);
		}
		texture.page = index; texture.x = location.x; texture.y = location.y;
		destination.Dirty(location.x - 1, location.y - 1, texture.width + 2, texture.height + 2);
		entries.emplace(key, texture);
	}
	for (size_t i = 0; i < pages.size(); ++i) {
		auto &shelf = shelves[i];
		if (shelf.x < ATLAS_SIZE) shelf.free.push_back({shelf.x, shelf.y, ATLAS_SIZE - shelf.x, shelf.height});
		if (shelf.y + shelf.height < ATLAS_SIZE) shelf.free.push_back({0, shelf.y + shelf.height, ATLAS_SIZE, ATLAS_SIZE - shelf.y - shelf.height});
		std::erase_if(shelf.free, [](const auto &area) { return area.width < 3 || area.height < 3; });
		pages[i].allocator.ResetFreeAreas(std::move(shelf.free));
	}
	for (const auto &[key, texture] : entries) pages[texture.page].last_used = std::max(pages[texture.page].last_used, texture.last_used);
	/* Repacking already needs source and destination pages simultaneously.
	 * Retain that bounded high-water storage rather than allocating, zeroing
	 * and freeing tens of MiB during every moving-camera compaction. */
	for (auto &page : old_pages) spare_pages.push_back(std::move(page));
	assert(pages.size() + spare_pages.size() <= 2 * ATLAS_PAGES);
}

void SpriteTextures::BeginScene()
{
	if (invalid) Clear();
	++epoch;
}

void SpriteTextures::MarkAllDirty()
{
	for (auto &page : pages) page.Dirty(0, 0, ATLAS_SIZE, ATLAS_SIZE);
}

std::pair<int, Point> SpriteTextures::Allocate(int width, int height)
{
	if (width + 2 > ATLAS_SIZE || height + 2 > ATLAS_SIZE) throw std::runtime_error("Sprite exceeds texture atlas page");
	int best_page = -1, best_score = std::numeric_limits<int>::max();
	for (size_t i = 0; i < pages.size(); ++i) {
		int score = pages[i].allocator.Score(width + 2, height + 2);
		if (score < best_score) { best_score = score; best_page = static_cast<int>(i); }
	}
	if (best_page >= 0) {
		auto &page = pages[best_page];
		auto rect = page.allocator.Allocate(width + 2, height + 2);
		assert(rect.has_value());
		page.last_used = epoch;
		return {best_page, {rect->x + 1, rect->y + 1}};
	}
	int index;
	if (pages.size() < ATLAS_PAGES) {
		index = static_cast<int>(pages.size());
		pages.push_back(AcquirePage());
	} else {
		auto oldest = std::min_element(pages.begin(), pages.end(), [](const auto &a, const auto &b) { return a.last_used < b.last_used; });
		if (oldest->last_used == epoch) throw AtlasFull();
		index = static_cast<int>(oldest - pages.begin());
		if (recent_palette != nullptr && recent_palette->page == index) recent_palette = nullptr;
		std::erase_if(entries, [=](const auto &entry) { return entry.second.page == index; });
		oldest->Reset();
	}
	auto &page = pages[index];
	auto rect = page.allocator.Allocate(width + 2, height + 2);
	assert(rect.has_value());
	page.last_used = epoch;
	/* Only allocated rectangles are sampled. Get/Repack marks each rectangle,
	 * including its zeroed gutter, instead of uploading unused page capacity. */
	return {index, {1, 1}};
}

static void PadOpaqueTexture(TextureDecoder &decoder)
{
	/* Extend existing texels into transparent padding for opaque 3D surfaces.
	 * This is texture edge dilation, not image-derived geometry or invented detail. */
	std::vector<int> nearest(decoder.pixels.size(),-1), queue;
	queue.reserve(nearest.size());
	auto alpha = [&](int x, int y) { return decoder.pixels[static_cast<size_t>(y) * decoder.width + x].a; };
	for (size_t i = 0; i < nearest.size(); ++i) {
		if (decoder.pixels[i].a == 0 || IsIsolatedEdgeTexel(decoder.width, decoder.height, i % decoder.width, i / decoder.width, alpha)) continue;
		nearest[i] = static_cast<int>(i);
		queue.push_back(static_cast<int>(i));
	}
	/* A genuinely tiny sprite may consist entirely of isolated pixels. */
	if (queue.empty()) for (size_t i = 0; i < nearest.size(); ++i) {
		if (decoder.pixels[i].a == 0) continue;
		nearest[i] = static_cast<int>(i);
		queue.push_back(static_cast<int>(i));
	}
	for (size_t head=0;head<queue.size();++head) {
		int i=queue[head], x=i%decoder.width, y=i/decoder.width;
		auto visit=[&](int next) { if (nearest[next]<0) { nearest[next]=nearest[i]; queue.push_back(next); } };
		if (x > 0) visit(i - 1);
		if (x + 1 < decoder.width) visit(i + 1);
		if (y > 0) visit(i - decoder.width);
		if (y + 1 < decoder.height) visit(i + decoder.width);
	}
	for (size_t i=0;i<nearest.size();++i) if (nearest[i]>=0) {
		if (decoder.pixels[i].a==0) decoder.pixels[i]=decoder.pixels[nearest[i]];
		decoder.pixels[i].a=255;
	}
}

/** Bounded exact-source mip cache. Palette variants share source pixels. */
static const TextureDecoder &DecodedTexture(SpriteID image, unsigned zoom, bool opaque_surface)
{
	struct Entry { std::unique_ptr<TextureDecoder> decoder; uint64_t used; };
	static std::unordered_map<uint64_t,Entry> decoded;
	static uint64_t cache_generation = UINT64_MAX, clock = 0;
	static size_t bytes = 0;
	constexpr size_t budget = 96*1024*1024;
	uint64_t current = TextureGeneration();
	if (cache_generation != current) { decoded.clear(); bytes = 0; cache_generation = current; }
	auto key_for = [&](unsigned level) { return image | (static_cast<uint64_t>(level)<<56) | (static_cast<uint64_t>(opaque_surface)<<63); };
	uint64_t key = key_for(zoom);
	++clock;
	if (auto found = decoded.find(key); found != decoded.end()) {
		found->second.used = clock;
		return *found->second.decoder;
	}
	Profile::Scope timer(Profile::Section::TextureDecode);
	auto start = Profile::Clock::now();
	TextureDecoder::Family family;
	TextureDecoder collector(zoom,&family);
	UniquePtrSpriteAllocator allocator;
	GetRawSprite(image,SpriteType::Normal,&allocator,&collector);
	auto raw_done = Profile::Clock::now();
	auto insert = [&](unsigned level) {
		uint64_t level_key = key_for(level);
		if (auto found = decoded.find(level_key); found != decoded.end()) { found->second.used = clock; return; }
		auto data = std::move(family[level]);
		if (data == nullptr) throw std::runtime_error("Upstream sprite has no resolved mip family");
		if (opaque_surface) PadOpaqueTexture(*data);
		size_t size = data->pixels.capacity()*sizeof(SpriteLoader::CommonPixel)+sizeof(Entry)+sizeof(TextureDecoder);
		while (!decoded.empty() && bytes+size > budget) {
			auto oldest = std::min_element(decoded.begin(),decoded.end(),[](const auto &a, const auto &b) { return a.second.used < b.second.used; });
			bytes -= oldest->second.decoder->pixels.capacity()*sizeof(SpriteLoader::CommonPixel)+sizeof(Entry)+sizeof(TextureDecoder);
			decoded.erase(oldest);
		}
		bytes += size;
		decoded.emplace(level_key,Entry{std::move(data),clock});
	};
	/* Insert the requested level last so eviction cannot invalidate the return. */
	for (unsigned level = 0; level < family.size(); ++level) if (level != zoom) insert(level);
	insert(zoom);
	double raw_ms = std::chrono::duration<double,std::milli>(raw_done-start).count();
	double prepare_ms = std::chrono::duration<double,std::milli>(Profile::Clock::now()-raw_done).count();
	if (raw_ms+prepare_ms > 1) Debug(driver,2,"OpenTT3D: source texture {} mip family request {} decode {:.3f} ms, preparation {:.3f} ms",image,zoom,raw_ms,prepare_ms);
	return *decoded.at(key).decoder;
}

void VerifyTextureMipCache()
{
	unsigned levels = 0;
	for (SpriteID image : {SPR_FLAT_GRASS_TILE,SPR_FLAT_ROCKY_LAND_2,SpriteID{1545},SpriteID{1412},SpriteID{1600}}) {
		for (bool opaque : {false,true}) for (unsigned zoom = 0; zoom <= to_underlying(ZoomLevel::Max); ++zoom) {
			TextureDecoder direct(zoom);
			UniquePtrSpriteAllocator allocator;
			GetRawSprite(image,SpriteType::Normal,&allocator,&direct);
			if (opaque) PadOpaqueTexture(direct);
			const auto &cached = DecodedTexture(image,zoom,opaque);
			if (cached.width != direct.width || cached.height != direct.height || cached.zoom != direct.zoom ||
				cached.source_width != direct.source_width || cached.source_height != direct.source_height ||
				cached.x_offset != direct.x_offset || cached.y_offset != direct.y_offset ||
				cached.ink_left != direct.ink_left || cached.ink_top != direct.ink_top || cached.ink_width != direct.ink_width || cached.ink_height != direct.ink_height ||
				cached.pixels.size() != direct.pixels.size()) throw std::runtime_error("Cached mip metadata differs from upstream decoding");
			for (size_t i = 0; i < direct.pixels.size(); ++i) {
				const auto &a = direct.pixels[i], &b = cached.pixels[i];
				if (a.r != b.r || a.g != b.g || a.b != b.b || a.a != b.a || a.m != b.m) throw std::runtime_error("Cached mip pixels differ from upstream decoding/padding");
			}
			++levels;
		}
		if (Textures().Get(image,PAL_NONE,0).zoom < to_underlying(ZoomLevel::Normal)) throw std::runtime_error("World material used an upscaled source instead of the native pixel grid");
	}
	Debug(driver,1,"OpenTT3D: {} cached mip/padding variants match direct upstream pixels and framing",levels);
	Debug(driver,1,"OpenTT3D: model materials use {} at native resolution or coarser",BaseGraphics::GetUsedSet()->name);
	/* A normal source chart can evict the last palette's page. Its new map node
	 * may reuse the same allocation address and the same palette ID, but it must
	 * never be returned as a 256-colour strip by the direct palette lookup. */
	SpriteTextures eviction;
	eviction.BeginScene();
	const auto &initial = eviction.GetPalette(PAL_NONE);
	if (initial.width != 256 || initial.height != 1) throw std::runtime_error("Palette eviction probe has no original strip");
	eviction.pages.resize(ATLAS_PAGES);
	for (auto &page : eviction.pages) { page.allocator.ResetFreeAreas({}); page.last_used = 1; }
	eviction.BeginScene();
	eviction.Get(SPR_FLAT_GRASS_TILE,PAL_NONE,to_underlying(ZoomLevel::Normal),true);
	const auto &restored = eviction.GetPalette(PAL_NONE);
	if (restored.width != 256 || restored.height != 1 || restored.palette != PAL_NONE) throw std::runtime_error("Palette cache retained an evicted source-chart node");
	Debug(driver,1,"OpenTT3D: palette lookup survives atlas-page eviction and source-node reuse");
}

const SpriteTexture &SpriteTextures::Get(SpriteID image, PaletteID palette, unsigned zoom, bool opaque_surface)
{
	image &= SPRITE_MASK;
	palette &= PALETTE_MASK;
	/* Classic's native pixel grid is normal zoom. Upscaled loader levels contain
	 * duplicated texels, waste atlas space and must not imply extra model detail. */
	zoom = std::clamp(zoom, static_cast<unsigned>(to_underlying(ZoomLevel::Normal)), static_cast<unsigned>(to_underlying(ZoomLevel::Max)));
	uint64_t key = image | (static_cast<uint64_t>(palette) << 24) | (static_cast<uint64_t>(zoom) << 56) | (static_cast<uint64_t>(opaque_surface) << 63);
	if (auto found = entries.find(key); found != entries.end()) {
		found->second.last_used = epoch;
		pages[found->second.page].last_used = epoch;
		return found->second;
	}
	const TextureDecoder &decoder = DecodedTexture(image, zoom, opaque_surface);
	auto [page_index, location] = Allocate(decoder.width, decoder.height);
	auto &page = pages[page_index];
	const uint8_t *mapping = palette != PAL_NONE && palette != PALETTE_TO_TRANSPARENT ? GetNonSprite(palette, SpriteType::Recolour) + 1 : nullptr;
	for (int y = 0; y < decoder.height; ++y) {
		for (int x = 0; x < decoder.width; ++x) {
			auto pixel = decoder.pixels[static_cast<size_t>(y) * decoder.width + x];
			uint8_t index = pixel.m != 0 && mapping != nullptr ? mapping[pixel.m] : pixel.m;
			if (pixel.m != 0 && index == 0) pixel.a = 0;
			size_t target = static_cast<size_t>(location.y + y) * ATLAS_SIZE + location.x + x;
			page.rgba[target * 4] = pixel.r; page.rgba[target * 4 + 1] = pixel.g;
			page.rgba[target * 4 + 2] = pixel.b; page.rgba[target * 4 + 3] = pixel.a;
			page.remap[target * 2] = index;
			uint8_t brightness = std::max({pixel.r, pixel.g, pixel.b});
			page.remap[target * 2 + 1] = brightness == 0 ? DEFAULT_BRIGHTNESS : brightness;
		}
	}
	page.ClearGutter(location.x,location.y,decoder.width,decoder.height);
	page.Dirty(location.x - 1, location.y - 1, decoder.width + 2, decoder.height + 2);
	SpriteTexture texture{page_index, location.x, location.y, decoder.width, decoder.height,
		decoder.source_width, decoder.source_height, decoder.x_offset, decoder.y_offset, decoder.zoom, IsBaseGraphicsSprite(image)};
	texture.ink_left=decoder.ink_left;texture.ink_top=decoder.ink_top;texture.ink_width=decoder.ink_width;texture.ink_height=decoder.ink_height;
	texture.opaque_surface = opaque_surface;
	texture.palette = palette;
	texture.last_used = epoch;
	return entries.emplace(key, texture).first->second;
}

/** Palette-only voxel materials retain original recolouring and animation.
 * Level six is reserved for palette strips; source-sprite mip keys use 0..5. */
const SpriteTexture &SpriteTextures::GetPalette(PaletteID palette)
{
	palette &= PALETTE_MASK;
	if (MaterialLookupCacheEnabled() && recent_palette != nullptr && recent_palette->palette == palette) {
		recent_palette->last_used = epoch;
		pages[recent_palette->page].last_used = epoch;
		return *recent_palette;
	}
	uint64_t key = (uint64_t{6}<<56) | (static_cast<uint64_t>(palette)<<24);
	if (auto found = entries.find(key); found != entries.end()) {
		found->second.last_used = epoch;
		pages[found->second.page].last_used = epoch;
		recent_palette = &found->second;
		return found->second;
	}
	auto [page_index, location] = Allocate(256,1);
	auto &page = pages[page_index];
	const uint8_t *mapping = palette != PAL_NONE && palette != PALETTE_TO_TRANSPARENT ? GetNonSprite(palette,SpriteType::Recolour)+1 : nullptr;
	for (unsigned index = 0; index < 256; ++index) {
		size_t pixel = static_cast<size_t>(location.y)*ATLAS_SIZE+location.x+index;
		unsigned mapped = mapping == nullptr ? index : mapping[index];
		page.rgba[pixel*4] = page.rgba[pixel*4+1] = page.rgba[pixel*4+2] = 0;
		page.rgba[pixel*4+3] = mapped == 0 ? 0 : 255;
		page.remap[pixel*2] = mapped;
		page.remap[pixel*2+1] = DEFAULT_BRIGHTNESS;
	}
	page.ClearGutter(location.x,location.y,256,1);
	page.Dirty(location.x-1,location.y-1,258,3);
	SpriteTexture texture{page_index,location.x,location.y,256,1,256*ZOOM_BASE,ZOOM_BASE,0,0,to_underlying(ZoomLevel::Normal),true};
	texture.palette = palette; texture.last_used = epoch; texture.opaque_surface = true;
	recent_palette = &entries.emplace(key,texture).first->second;
	return *recent_palette;
}

void ExportSpriteReference(SpriteID image, PaletteID palette, const std::string &filename, std::vector<uint8_t> *palette_indices)
{
	TextureDecoder decoder(to_underlying(ZoomLevel::Normal));
	UniquePtrSpriteAllocator allocator;
	GetRawSprite(image & SPRITE_MASK, SpriteType::Normal, &allocator, &decoder);
	const uint8_t *mapping = palette != PAL_NONE ? GetNonSprite(palette & PALETTE_MASK, SpriteType::Recolour) + 1 : nullptr;
	std::array<bool,256> used_indices{};
	/* Portable PAM preserves alpha and can be inspected/converted by the Docker art tools. */
	std::ofstream file(filename, std::ios::binary);
	if (!file) throw std::runtime_error("Cannot create sprite reference " + filename);
	file << "P7\nWIDTH " << decoder.width << "\nHEIGHT " << decoder.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
	for (const auto &pixel : decoder.pixels) {
		Colour c(pixel.r, pixel.g, pixel.b, pixel.a);
		if (pixel.m != 0) {
			uint8_t index = mapping != nullptr ? mapping[pixel.m] : pixel.m;
			if (pixel.a != 0 && index != 0) used_indices[index] = true;
			c = AdjustBrightness(_cur_palette.palette[index], GetColourBrightness(c));
			c.a = index == 0 ? 0 : pixel.a;
		}
		const uint8_t channels[] = {c.r, c.g, c.b, c.a};
		file.write(reinterpret_cast<const char *>(channels), 4);
	}
	if (palette_indices != nullptr) {
		palette_indices->clear();
		for (unsigned index = 1; index < used_indices.size(); ++index) if (used_indices[index]) palette_indices->push_back(index);
	}
}

void UsePaletteMaterial(InstanceData &data, PaletteID palette)
{
	const auto &strip = Textures().GetPalette(palette);
	data.region = strip.Region();
	data.uv_transform = {0,0,1,static_cast<float>(strip.page)};
	data.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::Palette) | SURFACE_UNLIT);
	data.identity[2] = static_cast<float>(static_cast<uint32_t>(data.identity[2]) | 1U);
	data.identity[3] = 2;
}

} // namespace Renderer3D
