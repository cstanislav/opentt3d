/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_models.cpp Read-only authored voxel catalogue and shared palette materials. */
#include "../stdafx.h"
#include "voxel_models.h"
#include "voxel_geometry.hpp"
#include "voxel_mesh_cache.hpp"
#include "authored_geometry.h"
#include "sprite_textures.hpp"
#include "gl_backend.hpp"
#include "depot_capture.h"
#include "station_capture.h"
#include "tunnel_geometry.hpp"
#include "../fileio_func.h"
#include "../debug.h"
#include "../core/bitmath_func.hpp"
#include "../palette_func.h"
#include "../spritecache.h"
#include "../station_map.h"
#include "../station_func.h"
#include "../town_map.h"
#include "../tree_map.h"
#include "../town.h"
#include "../house.h"
#include "../viewport_func.h"
#include "../vehicle_base.h"
#include "../aircraft.h"
#include "../settings_type.h"
#include "../industry.h"
#include "../industry_map.h"
#include "../industrytype.h"
#include "../table/sprites.h"
#include "../table/tree_land.h"
#include "../table/industry_land.h"
#include "../3rdparty/nlohmann/json.hpp"
#include <fstream>
#include <filesystem>
#include <map>
#include <memory>
#include <set>
#include <tuple>

namespace Renderer3D {
namespace {
using VoxelModel = VoxelCachedSurface;

uint64_t VoxelCPUCacheBudget()
{
	const char *value = std::getenv("OPENTT3D_CPU_VOXEL_CACHE_MIB");
	if (value == nullptr || *value == '\0') return 1024ULL*1024*1024;
	char *end = nullptr;
	unsigned long long mib = std::strtoull(value,&end,10);
	if (*value == '-' || *end != '\0' || mib > 1024*1024) throw std::runtime_error("Invalid CPU voxel cache budget");
	return mib == 0 ? UINT64_MAX : mib*1024*1024;
}
struct Catalogue {
	std::vector<VoxelMaterial> materials;
	std::map<std::string,VoxelModel,std::less<>> models;
	std::map<std::tuple<std::string,unsigned,unsigned>,std::string> bindings;
	std::array<const VoxelModel *,2009-1576+1> tree_models{};
	mutable VoxelMeshCache surfaces{VoxelCPUCacheBudget()};
};

const Catalogue &Models()
{
	static const Catalogue catalogue = [] {
		std::ifstream stream(FioFindFullPath(BASESET_DIR,"opentt3d-voxels.json"));
		if (!stream) throw std::runtime_error("Missing authored voxel catalogue");
		auto data = nlohmann::json::parse(stream);
		if (data.at("format") != 1 || data.at("cell_size").get<std::array<float,3>>() != std::array<float,3>{0.5f,0.5f,1}) throw std::runtime_error("Unsupported voxel format/grid");
		std::vector<VoxelMaterial> materials;
		for (const auto &entry : data.at("materials")) {
			VoxelMaterial material;
			if (entry.size() != 6) throw std::runtime_error("Voxel material needs six face colours");
			for (unsigned face = 0; face < 6; ++face) {
				unsigned colour = entry.at(face).get<unsigned>();
				if (colour == 0 || colour > 255) throw std::runtime_error("Invalid voxel palette index");
				material.colours[face] = colour;
			}
			materials.push_back(material);
		}
		Catalogue result;
		const char *unit_setting = std::getenv("OPENTT3D_VOXEL_TREE_UNIT_REFERENCE");
		const bool unit_reference = unit_setting != nullptr && std::string_view(unit_setting) == "1";
		if (unit_reference) Debug(driver,1,"OpenTT3D: unmerged tree cell reference enabled; volume substitution disabled");
		size_t occupied = 0, faces = 0, quads = 0, triangles = 0, source_bytes = 0, dense_bytes = 0;
		for (const auto &[name,entry] : data.at("models").items()) {
			if (name.empty() || name.size() > 96 || name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_") != std::string::npos) throw std::runtime_error("Invalid voxel model name");
			auto origin = entry.at("origin").get<std::array<float,3>>();
			auto size = entry.at("size").get<std::array<int,3>>();
			auto cell_size = entry.value("cell_size",std::array<float,3>{0.5f,0.5f,1});
			VoxelModel model;
			VoxelGrid grid(size,materials,Vec3{origin[0],origin[1],origin[2]},Vec3{cell_size[0],cell_size[1],cell_size[2]});
			for (const auto &run : entry.at("runs")) {
				auto values = run.get<std::array<int,5>>();
				if (values[4] < 1 || static_cast<size_t>(values[4]) > materials.size()) throw std::runtime_error("Invalid voxel run material");
				if (values[3] < 1 || values[3] > size[0] || values[0] < 0 || values[0] > size[0]-values[3] ||
					values[1] < 0 || values[1] >= size[1] || values[2] < 0 || values[2] >= size[2]) throw std::runtime_error("Voxel run is outside its grid");
				grid.Fill({values[0],values[1],values[2]},{values[0]+values[3],values[1]+1,values[2]+1},values[4]);
			}
			model.merged = !(unit_reference && name.starts_with("tree_"));
			model.surface = grid.Mesh(model.merged);
			model.source = std::make_unique<VoxelSource>(grid);
			source_bytes += model.source->StorageBytes();
			dense_bytes += static_cast<size_t>(size[0])*size[1]*size[2]*sizeof(uint16_t);
			if (model.surface.occupied != entry.at("occupied").get<size_t>()) throw std::runtime_error("Voxel run occupancy does not match its manifest");
			occupied += model.surface.occupied; faces += model.surface.exposed_faces; quads += model.surface.quads;
			triangles += model.surface.vertices.size()/3;
			auto [entry_model,inserted] = result.models.emplace(name,std::move(model));
			if (VoxelVolumesEnabled() && !unit_reference && name.starts_with("tree_")) VoxelVolumeRegistry().emplace(&entry_model->second.surface.vertices,grid.Volume());
			if (PackedVoxelMeshesEnabled()) if (auto packed = grid.Pack(entry_model->second.surface,name.starts_with("tree_"))) PackedVoxelMeshRegistry().emplace(&entry_model->second.surface.vertices,std::move(packed));
			result.surfaces.Register(entry_model->second);
		}
		result.materials = std::move(materials);
		for (const auto &[category,identifiers] : data.at("bindings").items()) for (const auto &[id,states] : identifiers.items()) for (const auto &[state,name] : states.items()) {
			std::string model = name.get<std::string>();
			if (!result.models.contains(model)) throw std::runtime_error("Voxel binding references a missing model");
			if (category == "vehicles" && (std::stoul(id) >= 256 || std::stoul(state) >= 8)) throw std::runtime_error("Invalid voxel vehicle engine/climate state");
			result.bindings.emplace(std::tuple{category,static_cast<unsigned>(std::stoul(id)),static_cast<unsigned>(std::stoul(state))},model);
			if (category == "trees") {
				unsigned base = std::stoul(id), stage = std::stoul(state);
				if (base >= 1576 && base <= 2003 && (base-1576)%7 == 0 && stage < 7) result.tree_models[base-1576+stage] = &result.models.at(model);
			}
		}
		Debug(driver,1,"OpenTT3D: loaded {} authored voxel models, {} occupied cells, {} exposed cell faces merged to {} conforming rectangles / {} triangles",result.models.size(),occupied,faces,quads,triangles);
		Debug(driver,1,"OpenTT3D: retained lossless voxel sources use {} bytes instead of {} dense cell bytes, with one shared palette",source_bytes,dense_bytes);
		Debug(driver,1,"OpenTT3D: CPU voxel surfaces retain {} bytes under a scene-pinned soft budget",result.surfaces.ResidentBytes());
		if (PackedVoxelMeshesEnabled()) Debug(driver,1,"OpenTT3D: {} voxel meshes support lossless packed vertex streams",PackedVoxelMeshRegistry().size());
		return result;
	}();
	return catalogue;
}

std::shared_ptr<const void> PinVoxelModel(const VoxelModel &model)
{
	const auto &catalogue = Models();
	return catalogue.surfaces.Pin(model,catalogue.materials);
}

void AddVoxelInstance(Scene &scene, const VoxelModel &model, const InstanceData &data)
{
	static const bool enabled = [] { const char *value = std::getenv("OPENTT3D_AUTO_LOD"); return value == nullptr || std::string_view(value) != "0"; }();
	const VoxelModel *selected = &model;
	if (enabled && scene.detail) {
		Vec3 origin{data.origin_opacity[0],data.origin_opacity[1],data.origin_opacity[2]};
		const auto &mesh = model.surface;
		float radius = std::max({std::abs(mesh.low.x),std::abs(mesh.low.y),std::abs(mesh.high.x),std::abs(mesh.high.y)})*1.42f;
		float pixels = scene.detail->PixelsPerUnit(origin+Vec3{-radius,-radius,mesh.low.z-radius},origin+Vec3{radius,radius,mesh.high.z+radius});
		/* No authored low-detail variants. A coarse cell is at most two screen
		 * pixels across, and nearby geometry always keeps the original surface. */
		unsigned level = pixels < 0.125f ? 4 : pixels < 0.25f ? 3 : pixels < 0.5f ? 2 : pixels < 1 ? 1 : 0;
		if (level != 0) {
			auto &lod = model.lods[level-1];
			if (!lod) {
				lod = std::make_unique<VoxelModel>();
				lod->lod_source = model.source.get(); lod->reduction = 1U<<level;
				lod->surface = model.source->Expand(Models().materials).ReducedMesh(lod->reduction);
				Models().surfaces.Register(*lod);
			}
			selected = lod.get();
		}
	}
	auto lease = PinVoxelModel(*selected);
	scene.instances.push_back({&selected->surface.vertices,data,std::move(lease)});
}

InstanceData Material(Vec3 origin, PaletteID palette, float opacity)
{
	InstanceData data;
	data.origin_opacity = {origin.x,origin.y,origin.z,opacity};
	UsePaletteMaterial(data,palette);
	return data;
}

/* Upstream multi-tile order is north, then +Y, then +X, then +X+Y. */
std::vector<Vec3> HouseReviewOffsets(unsigned house)
{
	const auto flags = HouseSpec::Get(house)->building_flags;
	if (flags.Test(BuildingFlag::Size2x2)) return {{},{0,16,0},{16,0,0},{16,16,0}};
	if (flags.Test(BuildingFlag::Size1x2)) return {{},{0,16,0}};
	if (flags.Test(BuildingFlag::Size2x1)) return {{},{16,0,0}};
	return {};
}
} // namespace

uint32_t VoxelPaletteMask(std::span<const Vertex> vertices, unsigned first, unsigned count)
{
	if (count == 0 || count > 32 || first >= 256 || count > 256-first) throw std::invalid_argument("Invalid voxel palette interval");
	uint32_t mask = 0;
	for (const auto &vertex : vertices) {
		if ((static_cast<uint32_t>(vertex.surface) & 15U) != static_cast<uint32_t>(SurfaceMode::Palette) || !(vertex.texture.x >= 0 && vertex.texture.x < 1)) continue;
		/* The mesher stores (index+0.5)/256, at the texel centre. Rounding
		 * this value upward would observe the neighbouring animation entry. */
		unsigned index = static_cast<unsigned>(vertex.texture.x*256);
		if (index >= first && index-first < count) mask |= 1U<<(index-first);
	}
	return mask;
}

bool HasVoxelAsset(std::string_view category, unsigned identifier, unsigned state)
{
	return Models().bindings.contains({std::string(category),identifier,state});
}

bool HasVoxelTree(SpriteID image)
{
	image &= SPRITE_MASK;
	if (image < 1576 || image > 2009) return false;
	unsigned stage = (image-1576)%7, base = image-stage;
	static const bool indexed = [] {
		const char *value = std::getenv("OPENTT3D_VOXEL_TREE_LOOKUP_CACHE");
		return value == nullptr || std::string_view(value) != "0";
	}();
	if (indexed) {
		/* The catalogue is immutable. Avoid string/tuple tree searches for every
		 * unbound tree in a wide viewport; preserve partial lifecycle bindings. */
		static const auto masks = [] {
			std::array<uint8_t,62> result{};
			for (const auto &[binding,name] : Models().bindings) {
				const auto &[category,sprite,age] = binding;
				if (category == "trees" && sprite >= 1576 && sprite <= 2003 && (sprite-1576)%7 == 0 && age < 7) result[(sprite-1576)/7] |= 1U<<age;
			}
			return result;
		}();
		unsigned family = (base-1576)/7;
		if ((masks[family] & (1U<<stage)) == 0) return false;
		static uint64_t generation = UINT64_MAX;
		static std::array<int8_t,62> provenance{};
		uint64_t current = TextureGeneration();
		if (generation != current) { generation = current; provenance.fill(0); }
		if (provenance[family] == 0) {
			bool original = true;
			for (unsigned age = 0; age < 7; ++age) original &= IsBaseGraphicsSprite(base+age);
			provenance[family] = original ? 1 : -1;
		}
		return provenance[family] > 0;
	}
	if (!HasVoxelAsset("trees",base,stage)) return false;
	/* A partially replaced lifecycle belongs to its supplied graphics family. */
	for (unsigned age = 0; age < 7; ++age) if (!IsBaseGraphicsSprite(base+age)) return false;
	return true;
}

bool UseVoxelTrees()
{
	static const bool voxel = [] { const char *value = std::getenv("OPENTT3D_TREE_STYLE"); return value != nullptr && std::string_view(value) == "voxel"; }();
	return voxel;
}

bool FocusVoxelTree(unsigned base, unsigned stage)
{
	if (base < 1576 || base > 2003 || (base-1576)%7 != 0 || stage >= 7 || !HasVoxelTree(base+stage)) return false;
	std::array<unsigned,7> counts{};
	TileIndex selected = INVALID_TILE;
	unsigned selected_slot = 0;
	std::tuple<unsigned,int,int> best{};
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsTileType(tile,MP_TREES)) continue;
		/* This is the original DrawTile_Trees layout selection, read-only. Older
		 * trees on a multi-tree tile are mature; only its last slot uses growth. */
		unsigned hash = CountBits(tile.base()+x*TILE_SIZE+y*TILE_SIZE);
		unsigned layout = (hash&3)+(GetTreeType(tile)<<2);
		if ((GetTreeGround(tile) == TREE_GROUND_SNOW_DESERT || GetTreeGround(tile) == TREE_GROUND_ROUGH_SNOW) &&
			GetTreeDensity(tile) >= 2 && layout >= (TREE_SUB_ARCTIC<<2) && layout < (TREE_RAINFOREST<<2)) layout += 164-(TREE_SUB_ARCTIC<<2);
		for (unsigned slot = 0; slot < GetTreeCount(tile); ++slot) {
			if (_tree_layout_sprite[layout][slot].sprite != base) continue;
			unsigned age = slot+1 == GetTreeCount(tile) ? to_underlying(GetTreeGrowth(tile)) : 3;
			++counts[age];
			if (age != stage) continue;
			/* Prefer a readable interior/single-tree example over the first row at
			 * the map edge. This affects only the review camera, never tree state. */
			unsigned margin = std::min({x,y,Map::MaxX()-x,Map::MaxY()-y,16U});
			int distance = std::abs(static_cast<int>(x)-static_cast<int>(Map::MaxX()/2))+std::abs(static_cast<int>(y)-static_cast<int>(Map::MaxY()/2));
			auto score = std::tuple{margin,-static_cast<int>(GetTreeCount(tile)),-distance};
			if (selected == INVALID_TILE || score > best) { selected = tile; selected_slot = slot; best = score; }
		}
	}
	if (selected != INVALID_TILE) {
		ScrollMainWindowToTile(selected,true);
		Debug(driver,1,"OpenTT3D: focused {} tree {} stage {} at {},{} (slot {})",UseVoxelTrees() ? "voxel" : "projected",base,stage,TileX(selected),TileY(selected),selected_slot);
		return true;
	}
	Debug(driver,1,"OpenTT3D: tree lookup {} stage {} found no match; actual stage counts {}/{}/{}/{}/{}/{}/{}",base,stage,counts[0],counts[1],counts[2],counts[3],counts[4],counts[5],counts[6]);
	return false;
}

std::optional<unsigned> VoxelHouseState(unsigned house, unsigned stage, unsigned variant)
{
	auto source = GetTownDrawTileData();
	if (stage > 3 || variant > 3 || house >= source.size()/16) return {};
	if ((house == 4 || house == 5) && !IsBaseGraphicsSprite(SPR_LIFT)) return {};
	unsigned state = variant*4+stage;
	if (HasVoxelAsset("houses",house,state)) return state;
	/* A generic stage binding may cover an identical source sprite, with its
	 * original palette still applied. Different geometry needs an explicit state. */
	if (source[house*16+state].building.sprite == source[house*16+stage].building.sprite && HasVoxelAsset("houses",house,stage)) return stage;
	return {};
}

static const std::vector<uint16_t> &HouseGroundMasks()
{
	static const auto masks = [] {
		std::vector<uint16_t> result(GetTownDrawTileData().size()/16);
		for (const auto &[binding,name] : Models().bindings) {
			const auto &[category,id,state] = binding;
			if (category == "house_ground" && id < result.size() && state < 16) result[id] |= 1U<<state;
		}
		return result;
	}();
	return masks;
}

bool HasVoxelHouseGround(unsigned house)
{
	const auto &masks = HouseGroundMasks();
	return house < masks.size() && masks[house] != 0;
}

std::optional<unsigned> VoxelHouseGroundState(unsigned house, unsigned stage, unsigned variant)
{
	/* Avoid source-table access and tile variant hashes for the many unbound
	 * houses visited while choosing compatible neighbouring terrain edges. */
	if (!HasVoxelHouseGround(house) || stage > 3 || variant > 3) return {};
	auto source = GetTownDrawTileData();
	const auto &masks = HouseGroundMasks();
	unsigned state = variant*4+stage;
	if ((source[house*16+state].ground.sprite&SPRITE_MASK) == 0) return {};
	if ((masks[house] & (1U<<state)) == 0) {
		if (source[house*16+state].ground.sprite != source[house*16+stage].ground.sprite || (masks[house] & (1U<<stage)) == 0) return {};
		state = stage;
	}
	static uint64_t generation = UINT64_MAX;
	static std::vector<int8_t> provenance(masks.size());
	if (generation != TextureGeneration()) { generation = TextureGeneration(); std::fill(provenance.begin(),provenance.end(),0); }
	if (provenance[house] == 0) {
		bool original = true;
		for (unsigned slot = 0; slot < 16; ++slot) {
			const auto &entry = source[house*16+slot];
			for (SpriteID image : {entry.ground.sprite,entry.building.sprite}) if ((image&SPRITE_MASK) != 0) original &= IsBaseGraphicsSprite(image&SPRITE_MASK);
		}
		provenance[house] = original ? 1 : -1;
	}
	return provenance[house] > 0 ? std::optional<unsigned>{state} : std::nullopt;
}

bool DrawVoxelHouseGround(Scene &scene, unsigned house, unsigned stage, unsigned variant, SpriteID image, Vec3 origin, PaletteID palette)
{
	auto state = VoxelHouseGroundState(house,stage,variant);
	if (!state || (GetTownDrawTileData()[house*16+variant*4+stage].ground.sprite&SPRITE_MASK) != (image&SPRITE_MASK)) return false;
	return DrawVoxelAsset(scene,"house_ground",house,*state,origin,palette,1);
}

static bool HasVoxelToyFactoryChildren()
{
	for (SpriteID image : {SPR_IT_TOY_FACTORY_STAMP_HOLDER,SPR_IT_TOY_FACTORY_STAMP,SPR_IT_TOY_FACTORY_CLAY,SPR_IT_TOY_FACTORY_ROBOT}) {
		if (!IsBaseGraphicsSprite(image) || !HasVoxelAsset("infrastructure",image,0)) return false;
	}
	return true;
}

std::array<VoxelIndustryChild,4> VoxelToyFactoryChildren(unsigned frame)
{
	if (frame >= std::size(_industry_anim_offs_toys)) throw std::invalid_argument("Invalid original toy-factory frame");
	const auto &source = _industry_anim_offs_toys[frame];
	std::array<VoxelIndustryChild,4> children{};
	/* The source's (-2,+1) screen steps move the conveyor along +X. The
	 * press's (0,+dy) steps move only -Z, not along an inverse-screen diagonal. */
	if (source.image_1 != 0xFF) children[0] = {SPR_IT_TOY_FACTORY_CLAY,source.x,96+source.image_1,{static_cast<float>(source.image_1),0,0}};
	if (source.image_2 != 0xFF) children[1] = {SPR_IT_TOY_FACTORY_ROBOT,16-source.image_2*2,100+source.image_2,{static_cast<float>(source.image_2),0,0}};
	children[2] = {SPR_IT_TOY_FACTORY_STAMP,7,source.image_3,{0,0,-static_cast<float>(source.image_3)}};
	children[3] = {SPR_IT_TOY_FACTORY_STAMP_HOLDER,0,42,{}};
	return children;
}

std::optional<unsigned> VoxelIndustryState(unsigned graphics, SpriteID image, bool ground)
{
	if (graphics >= std::size(_industry_draw_tile_data)/4) return {};
	image &= SPRITE_MASK;
	if (!IndustryModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape),ground,image)) return {};
	if (image == 0) return {};
	std::string_view category = ground ? "industry_ground" : "industries";
	bool bound = false;
	for (unsigned stage = 0; stage < 4; ++stage) bound |= HasVoxelAsset(category,graphics,stage);
	if (!bound) return {};
	/* Keep custom replacements and special drawing procedures on their supplied
	 * path. A shared original stage sprite may resolve to a shared volume. */
	unsigned first = graphics <= 1 ? 0 : graphics, last = graphics <= 1 ? 1 : graphics;
	if (graphics == 47 || graphics == 48) { first = 47; last = 48; } // Copper hoist construction and its three original wheel poses.
	if (graphics >= GFX_OILRIG_1 && graphics <= GFX_OILRIG_5) {
		/* These source cuts share physical deck/building components. A partial
		 * replacement must retain the supplied art across the complete rig. */
		first = GFX_OILRIG_1; last = GFX_OILRIG_5;
	} else if (graphics >= GFX_OILWELL_NOT_ANIMATED && graphics <= GFX_OILWELL_ANIMATED_3) {
		first = GFX_OILWELL_NOT_ANIMATED; last = GFX_OILWELL_ANIMATED_3;
	} else if (graphics == 33 || graphics == 34) {
		first = 33; last = 34; // The two source cuts form one connected farmhouse.
	} else if (graphics == 58 || graphics == 59) {
		first = 58; last = 59; // One bank's roof, colonnade and arch cross this seam.
	} else if (graphics >= 72 && graphics <= 88) {
		/* Gold's troughs cross body/ground ownership,74 owns part of75's roof,
		 * and86/87 share a workshop. Keep partial custom replacements together. */
		first = 72; last = 88;
	} else if (ground && graphics >= 100 && graphics <= 115) {
		/* The iron-ore works is entirely ground-owned. Its hall and small-works
		 * roofs cross source cuts; a partial replacement must keep the supplied
		 * layout rather than mixing it with neighbouring voxel walls/roofs. */
		first = 100; last = 115;
	} else if (!ground && graphics >= 132 && graphics <= 134) {
		/* Gift wrapping and the peppermint roof cross all three projected body
		 * cuts. Keep partial custom body replacements together; soil is separate. */
		first = 132; last = 134;
	} else if (!ground && graphics >= 139 && graphics <= 141) {
		/* Castle walls and flags cross these three projected source cuts. Keep
		 * partial body replacements together while preserving independent soil. */
		first = 139; last = 141;
	} else if (graphics >= GFX_PLASTIC_FOUNTAIN_ANIMATED_1 && graphics <= GFX_PLASTIC_FOUNTAIN_ANIMATED_8) {
		/* The original animation changes graphics IDs. Keep each independently
		 * owned layer on one source path throughout all eight liquid poses. */
		first = GFX_PLASTIC_FOUNTAIN_ANIMATED_1; last = GFX_PLASTIC_FOUNTAIN_ANIMATED_8;
	} else if (!ground && graphics >= 157 && graphics <= 159) {
		/* Glass chambers and circulation tubing cross all three source cuts.
		 * A partial custom replacement retains the connected supplied apparatus. */
		first = 157; last = 159;
	} else if (!ground && graphics >= 142 && graphics <= 146) {
		/* Construction swaps the blue tower's owner, and the fixed holder owns
		 * wall cuts across the press. Keep every connected body on one source path. */
		first = 142; last = 146;
	}
	bool toy_factory = graphics >= 142 && graphics <= 146 && (ground || HasVoxelToyFactoryChildren());
	bool power_sparks = graphics == 10 && HasVoxelAsset("industries",10,3) && IsBaseGraphicsSprite(SPR_IT_POWER_PLANT_TRANSFORMERS);
	if (power_sparks) for (unsigned frame = 1; frame <= std::size(_coal_plant_sparks); ++frame) {
		SpriteID spark = SPR_IT_POWER_PLANT_TRANSFORMERS+frame;
		power_sparks &= IsBaseGraphicsSprite(spark) && HasVoxelAsset("infrastructure",spark,0);
	}
	for (unsigned family = first; family <= last; ++family) for (unsigned stage = 0; stage < 4; ++stage) {
		const auto &source = _industry_draw_tile_data[family*4+stage];
		SpriteID sprite = (ground ? source.ground.sprite : source.building.sprite)&SPRITE_MASK;
		if ((source.draw_proc != 0 && !(power_sparks && source.draw_proc == 5) && !(toy_factory && source.draw_proc == 4)) || (sprite != 0 && !IsBaseGraphicsSprite(sprite))) return {};
		if (first == 72 && last == 88) {
			SpriteID other = (ground ? source.building.sprite : source.ground.sprite)&SPRITE_MASK;
			if (other != 0 && !IsBaseGraphicsSprite(other)) return {};
		}
	}
	for (unsigned stage = 0; stage < 4; ++stage) if (HasVoxelAsset(category,graphics,stage)) {
		const auto &source = _industry_draw_tile_data[graphics*4+stage];
		if (((ground ? source.ground.sprite : source.building.sprite)&SPRITE_MASK) == image) return stage;
	}
	return {};
}

bool DrawVoxelIndustryGround(Scene &scene, unsigned graphics, SpriteID image, Vec3 origin, PaletteID palette)
{
	auto state = VoxelIndustryState(graphics,image,true);
	return state && DrawVoxelAsset(scene,"industry_ground",graphics,*state,origin,palette,1);
}

bool DrawVoxelIndustrySpark(Scene &scene, SpriteID image, Vec3 origin, PaletteID palette, float opacity)
{
	image &= SPRITE_MASK;
	if (image <= SPR_IT_POWER_PLANT_TRANSFORMERS || image > SPR_IT_POWER_PLANT_TRANSFORMERS+std::size(_coal_plant_sparks) ||
		!VoxelIndustryState(10,SPR_IT_POWER_PLANT_TRANSFORMERS)) return false;
	size_t before = scene.instances.size();
	if (!DrawVoxelAsset(scene,"infrastructure",image,0,origin,palette,opacity)) return false;
	for (size_t i = before; i < scene.instances.size(); ++i) scene.instances[i].data.SetChildLayer(true);
	return true;
}

bool DrawVoxelToyFactoryChild(Scene &scene, SpriteID image, unsigned frame, Vec3 origin, PaletteID palette, float opacity)
{
	image &= SPRITE_MASK;
	if (!VoxelIndustryState(143,_industry_draw_tile_data[143*4+3].building.sprite)) return false;
	for (const auto &child : VoxelToyFactoryChildren(frame)) if (child.image != 0 && child.image == image) {
		size_t before = scene.instances.size();
		if (!DrawVoxelAsset(scene,"infrastructure",image,0,origin+child.offset,palette,opacity)) return false;
		for (size_t i = before; i < scene.instances.size(); ++i) scene.instances[i].data.SetChildLayer(true);
		return true;
	}
	return false;
}

bool DrawVoxelHelicopterRotor(Scene &scene, SpriteID image, Vec3 origin, PaletteID palette)
{
	image &= SPRITE_MASK;
	if (image < SPR_ROTOR_STOPPED || image > SPR_ROTOR_MOVING_3) return false;
	/* The original rotor uses four fixed world-space poses, independently of
	 * aircraft heading. A partially replaced animation keeps its supplied art. */
	for (unsigned state = 0; state < 4; ++state) {
		if (!IsBaseGraphicsSprite(SPR_ROTOR_STOPPED+state) || !HasVoxelAsset("infrastructure",SPR_ROTOR_STOPPED,state)) return false;
	}
	return DrawVoxelAsset(scene,"infrastructure",SPR_ROTOR_STOPPED,image-SPR_ROTOR_STOPPED,origin,palette);
}

bool FocusVoxelIndustry(unsigned graphics, unsigned stage, bool ground)
{
	if (graphics >= std::size(_industry_draw_tile_data)/4 || stage >= 4) return false;
	std::array<unsigned,4> counts{};
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		bool oilrig = graphics == GFX_OILRIG_1 && ground && IsTileType(tile,MP_STATION) && IsOilRig(tile);
		if (!oilrig && (!IsTileType(tile,MP_INDUSTRY) || GetIndustryGfx(tile) != graphics)) continue;
		unsigned actual = oilrig ? 3 : GetIndustryConstructionStage(tile);
		++counts[actual];
		const auto &source = _industry_draw_tile_data[graphics*4+actual];
		if (actual != stage || !VoxelIndustryState(graphics,ground ? source.ground.sprite : source.building.sprite,ground)) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel industry{} {} construction stage {} at {},{}",ground ? " ground" : "",graphics,stage,x,y);
		return true;
	}
	Debug(driver,1,"OpenTT3D: industry lookup {} stage {} found no voxel match; actual stage counts {}/{}/{}/{}",graphics,stage,counts[0],counts[1],counts[2],counts[3]);
	return false;
}

bool FocusVoxelAirport(unsigned graphics)
{
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsTileType(tile,MP_STATION) || !IsAirport(tile) || !HasVoxelAirport(GetAirportGfx(tile),0)) continue;
		if (graphics != UINT_MAX && GetAirportGfx(tile) != graphics) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel airport tile {} at {},{}",GetAirportGfx(tile),x,y);
		return true;
	}
	return false;
}

/** Original airports have at most12 frames. Ground states reserve16 per climate;
 * an absent override retains an explicitly shared original base-ground binding. */
static unsigned VoxelAirportGroundState(unsigned graphics, unsigned frame)
{
	unsigned state = 16*to_underlying(_settings_game.game_creation.landscape)+frame;
	return HasVoxelAsset("airport_ground",graphics,state) ? state : frame;
}

bool HasVoxelAirport(unsigned graphics, unsigned frame)
{
	static uint64_t generation = UINT64_MAX;
	static std::array<int,74> supported{};
	if (graphics >= supported.size() || !AirportModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape))) return false;
	auto layouts = GetAirportTileLayouts(graphics);
	if (frame >= layouts.size()) return false;
	/* Several original airport buildings belong entirely to the ground sprite.
	 * Empty body sequences need a ground binding, never a fabricated body. */
	if (layouts[frame]->GetSequence().empty() ? !HasVoxelAsset("airport_ground",graphics,VoxelAirportGroundState(graphics,frame)) : !HasVoxelAsset("airport_tiles",graphics,frame)) return false;
	if (generation != TextureGeneration()) { generation = TextureGeneration(); supported.fill(0); }
	int &value = supported[graphics];
	if (value == 0) {
		bool base = true;
		/* A partial source replacement keeps the supplied ground/body/animation
		 * together, including airports whose ground has a separate voxel owner. */
		for (const auto *source : layouts) {
			base &= IsBaseGraphicsSprite(source->ground.sprite & SPRITE_MASK);
			for (const auto &component : source->GetSequence()) base &= IsBaseGraphicsSprite(component.image.sprite & SPRITE_MASK);
		}
		value = base ? 1 : -1;
	}
	return value > 0;
}

bool DrawVoxelAirportGround(Scene &scene, unsigned graphics, unsigned frame, Vec3 origin, PaletteID palette)
{
	return HasVoxelAirport(graphics,frame) && DrawVoxelAsset(scene,"airport_ground",graphics,VoxelAirportGroundState(graphics,frame),origin,palette);
}

bool FocusVoxelHouseStage(unsigned stage, unsigned house, unsigned variant)
{
	if (stage > TOWN_HOUSE_COMPLETED) return false;
	std::array<unsigned,4> counts{};
	auto source = GetTownDrawTileData();
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsTileType(tile,MP_HOUSE) || (house != UINT_MAX && GetHouseType(tile) != house)) continue;
		unsigned actual_variant = TileHash2Bit(x*TILE_SIZE,y*TILE_SIZE);
		if (variant != UINT_MAX && actual_variant != variant) continue;
		++counts[GetHouseBuildingStage(tile)];
		if (GetHouseBuildingStage(tile) != stage) continue;
		bool body = VoxelHouseState(GetHouseType(tile),stage,actual_variant).has_value();
		unsigned index = GetHouseType(tile)*16+actual_variant*4+stage;
		bool ground_only = !body && index < source.size() && source[index].building.sprite == 0 && VoxelHouseGroundState(GetHouseType(tile),stage,actual_variant);
		if (!body && !ground_only) continue;
		ScrollMainWindowToTile(tile,true);
		Debug(driver,1,"OpenTT3D: focused voxel house {} construction stage {} at {},{} (variant {}, {} binding)",GetHouseType(tile),stage,x,y,actual_variant,ground_only ? "ground-only" : "body");
		return true;
	}
	Debug(driver,1,"OpenTT3D: house-stage lookup house {} variant {} stage {} found no voxel match; actual stage counts {}/{}/{}/{}",house,variant,stage,counts[0],counts[1],counts[2],counts[3]);
	return false;
}

bool DrawVoxelAsset(Scene &scene, std::string_view category, unsigned identifier, unsigned state, Vec3 origin, PaletteID palette, float opacity)
{
	const auto &models = Models();
	const VoxelModel *resolved = nullptr;
	if (category == "trees" && identifier >= 1576 && identifier <= 2003 && (identifier-1576)%7 == 0 && state < 7) {
		resolved = models.tree_models[identifier-1576+state];
	} else {
		auto found = models.bindings.find({std::string(category),identifier,state});
		if (found != models.bindings.end()) resolved = &models.models.at(found->second);
	}
	if (resolved == nullptr) return false;
	const auto &model = resolved->surface;
	if (scene.visibility && !scene.visibility->Intersects(origin+model.low,origin+model.high)) return true;
	if (category == "trees" && !scene.scenery_regions.empty() && std::ranges::none_of(scene.scenery_regions,
		[&](const ClipVolume &region) { return region.Intersects(origin+model.low,origin+model.high); })) return true;
	AddVoxelInstance(scene,*resolved,Material(origin,palette,opacity));
	return true;
}

std::optional<unsigned> VoxelVehicleState(unsigned engine, bool loaded, unsigned climate)
{
	static const auto masks = [] {
		std::array<unsigned,256> result{};
		for (const auto &[binding,name] : Models().bindings) {
			const auto &[category,engine,state] = binding;
			if (category == "vehicles") result.at(engine) |= 1U<<state;
		}
		for (unsigned mask : result) for (unsigned climate = 0; climate < 4; ++climate) {
			unsigned pair = (mask>>(climate*2))&3U;
			if (pair != 0 && pair != 3) throw std::runtime_error("Voxel vehicle climate needs both original cargo states");
		}
		return result;
	}();
	if (engine >= masks.size()) return {};
	if (climate == UINT_MAX) climate = to_underlying(_settings_game.game_creation.landscape);
	return SelectVoxelVehicleState(masks[engine],loaded,climate);
}

std::optional<VoxelTrainSupport> VoxelTrainSupportBounds(unsigned engine, bool loaded, float heading)
{
	if (engine >= 116) return {};
	auto state = VoxelVehicleState(engine,loaded);
	if (!state) return {};
	const auto &model = Models().models.at(Models().bindings.at({"vehicles",engine,*state}));
	static std::map<const VoxelMesh *,std::vector<float>> contacts;
	auto [found,inserted] = contacts.try_emplace(&model.surface);
	if (inserted) {
		auto lease = PinVoxelModel(model);
		for (const auto &vertex : model.surface.vertices) if (vertex.position.z == model.surface.low.z) found->second.push_back(vertex.position.x);
		std::ranges::sort(found->second);
		found->second.erase(std::unique(found->second.begin(),found->second.end()),found->second.end());
	}
	float scale = OriginalTrainVoxelScale(heading,model.surface.high.x-model.surface.low.x);
	return VoxelTrainSupport{found->second.front()*scale,found->second.back()*scale,model.surface.low.z,scale,found->second};
}

bool DrawVoxelVehicle(Scene &scene, unsigned engine, bool loaded, Vec3 origin, float heading, PaletteID palette, float opacity, unsigned climate, float grade)
{
	auto state = VoxelVehicleState(engine,loaded,climate);
	if (!state) return false;
	const auto &models = Models();
	auto binding = models.bindings.find({"vehicles",engine,*state});
	if (binding == models.bindings.end()) return false;
	const auto &mesh = models.models.at(binding->second).surface;
	float radius = std::max({std::abs(mesh.low.x),std::abs(mesh.low.y),std::abs(mesh.high.x),std::abs(mesh.high.y)})*1.42f;
	float pitch_margin = grade == 0 ? 0 : radius*std::abs(grade)+1;
	if (scene.visibility && !scene.visibility->Intersects(origin+Vec3{-radius,-radius,mesh.low.z-pitch_margin},origin+Vec3{radius,radius,mesh.high.z+pitch_margin})) return true;
	auto data = Material(origin,palette,opacity);
	data.mirror_layer_heading[3] = heading;
	if (engine < 116) data.SetLongitudinalScale(OriginalTrainVoxelScale(heading,mesh.high.x-mesh.low.x));
	if (engine < 116 && grade != 0) data.SetPitch(grade,Camera::WORLD_Z_SCALE,mesh.low.z);
	AddVoxelInstance(scene,models.models.at(binding->second),data);
	return true;
}

static Vec3 CollectorContactCentre(const VoxelMesh &mesh)
{
	/* A single-arm frame is asymmetric: its overall bounds are not the wire
	 * contact shoe. Cache the top surface's XY centre in immutable model space. */
	static std::map<const VoxelMesh *,Vec3> contacts;
	auto [contact,inserted] = contacts.try_emplace(&mesh);
	if (inserted) {
		Vec3 low{INFINITY,INFINITY,mesh.high.z},high{-INFINITY,-INFINITY,mesh.high.z};
		for (const auto &vertex : mesh.vertices) if (vertex.position.z == mesh.high.z) {
			low.x = std::min(low.x,vertex.position.x); low.y = std::min(low.y,vertex.position.y);
			high.x = std::max(high.x,vertex.position.x); high.y = std::max(high.y,vertex.position.y);
		}
		contact->second = (low+high)*0.5f;
	}
	return contact->second;
}

static void SetCollectorPose(InstanceData &data, const VoxelMesh &body, const VoxelMesh &mesh, float heading, float grade, float height)
{
	data.mirror_layer_heading[3] = heading;
	float length_scale = OriginalTrainVoxelScale(heading,body.high.x-body.low.x);
	data.SetLongitudinalScale(length_scale);
	data.SetPitch(grade,Camera::WORLD_Z_SCALE,body.low.z);
	try {
		FitVoxelCollectorToWire(data,mesh.low.z,mesh.high.z,height,CollectorContactCentre(mesh).x*length_scale);
	} catch (const std::invalid_argument &error) {
		throw std::invalid_argument(fmt::format("{}: mount {} top {} contact {} contact_x {} heading {} grade {} body_base {}",error.what(),mesh.low.z,mesh.high.z,height,CollectorContactCentre(mesh).x*length_scale,heading,grade,body.low.z));
	}
}

std::optional<Vec3> VoxelTrainCollectorMount(unsigned engine, unsigned part, float heading, float grade, float contact_height)
{
	const auto &models = Models();
	auto binding = models.bindings.find({"vehicle_collectors",engine,part});
	auto state = VoxelVehicleState(engine,false);
	if (binding == models.bindings.end() || !state) return {};
	const auto &body = models.models.at(models.bindings.at({"vehicles",engine,*state})).surface;
	const auto &mesh = models.models.at(binding->second).surface;
	auto lease = PinVoxelModel(models.models.at(binding->second));
	InstanceData data;
	SetCollectorPose(data,body,mesh,heading,grade,contact_height);
	Vertex contact{}; contact.position = CollectorContactCentre(mesh); contact.normal = {0,0,1};
	return ResolveInstanceVertex(contact,data).position;
}

unsigned DrawVoxelTrainCollectors(Scene &scene, unsigned engine, Vec3 origin, float heading, PaletteID palette, std::array<float,2> contact_heights, float grade)
{
	const auto &models = Models();
	auto state = VoxelVehicleState(engine,false);
	if (!state || engine >= 116) return 0;
	const auto &body = models.models.at(models.bindings.at({"vehicles",engine,*state})).surface;
	unsigned drawn = 0;
	for (unsigned part = 0; part < 2; ++part) {
		auto binding = models.bindings.find({"vehicle_collectors",engine,part});
		if (binding == models.bindings.end()) continue;
		const auto &mesh = models.models.at(binding->second).surface;
		float radius = std::max({std::abs(body.low.x),std::abs(body.high.x),std::abs(mesh.low.y),std::abs(mesh.high.y)})*1.42f;
		float margin = radius*std::abs(grade)+1;
		if (scene.visibility && !scene.visibility->Intersects(origin+Vec3{-radius,-radius,mesh.low.z-margin},origin+Vec3{radius,radius,contact_heights[part]+margin})) continue;
		auto lease = PinVoxelModel(models.models.at(binding->second));
		auto data = Material(origin,palette,1);
		SetCollectorPose(data,body,mesh,heading,grade,contact_heights[part]);
		scene.instances.push_back({&mesh.vertices,data,std::move(lease)});
		++drawn;
	}
	return drawn;
}

bool FocusVoxelVehicle(unsigned engine)
{
	for (const Vehicle *vehicle : Vehicle::Iterate()) {
		/* Attached wagons and rear engine parts have their own original artwork
		 * and picking IDs even though only the front engine is primary. */
		if ((!vehicle->IsPrimaryVehicle() && vehicle->type != VEH_TRAIN) || vehicle->engine_type.base() != engine ||
			vehicle->vehstatus.Any({VehState::Hidden,VehState::Shadow, VehState::Unclickable})) continue;
		bool loaded = vehicle->cargo_cap != 0 && vehicle->cargo.StoredCount() >= vehicle->cargo_cap/2U;
		auto state = VoxelVehicleState(engine,loaded);
		if (!state) continue;
		ScrollMainWindowTo(vehicle->x_pos,vehicle->y_pos,vehicle->z_pos,true);
		Debug(driver,1,"OpenTT3D: focused voxel vehicle engine {} vehicle {} at {},{},{}, load {}/{}",engine,vehicle->index.base(),vehicle->x_pos,vehicle->y_pos,vehicle->z_pos,vehicle->cargo.StoredCount(),vehicle->cargo_cap);
		Debug(driver,1,"OpenTT3D: focused voxel vehicle engine {} climate {} binding state {}",engine,to_underlying(_settings_game.game_creation.landscape),*state);
		return true;
	}
	return false;
}

bool DrawVoxelHouseLift(Scene &scene, Vec3 origin, unsigned position, PaletteID palette, float opacity)
{
	if (position > 63) return false;
	/* The original 4x13-pixel cabin occupies the facade bay at screen (-15,9)
	 * before its upstream vertical offset. Its pose is never simulated here. */
	return DrawVoxelAsset(scene,"infrastructure",SPR_LIFT,0,origin+Vec3{14.5f,8,3.5f+position},palette,opacity);
}

void ExportVoxelReviews(std::string_view prefix)
{
	if (std::ranges::none_of(Models().models,[&](const auto &entry) { return entry.first.starts_with(prefix); })) throw std::runtime_error("No voxel models match the review prefix");
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
	std::filesystem::create_directories(directory);
		auto capture = [&](const Scene &scene, const Camera &camera, const std::string &name, bool object_alpha = false) {
		std::vector<uint8_t> pixels;
		std::vector<uint32_t> ids;
		if (!RenderScene(scene,camera,pixels,object_alpha ? &ids : nullptr)) throw std::runtime_error("Voxel review capture failed");
		if (object_alpha) for (size_t i = 0; i < ids.size(); ++i) if (ids[i] == 0) pixels[i*4+3] = 0;
		std::ofstream output(directory/(name+".pam"),std::ios::binary);
		output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(pixels.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
		if (!output) throw std::runtime_error("Could not write voxel review capture");
	};
	/* Even an unbound authoring study needs a fixed source-scale registration.
	 * Keep its actual model origin, rather than centring the visible silhouette. */
	auto native_model = [&](Scene scene, const std::string &name) {
		for (auto &instance : scene.instances) instance.data.SetObjectId(1);
		Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
		int left = 8192, top = 8192, right = 8192, bottom = 8192;
		for (const auto &instance : scene.instances) for (const auto &vertex : *instance.mesh) {
			auto point = camera.Project(ResolveInstanceVertex(vertex,instance.data).position);
			if (!point.visible) throw std::runtime_error("Native voxel study is outside the fixed-lens camera");
			left = std::min(left,static_cast<int>(std::floor(point.x))-4); top = std::min(top,static_cast<int>(std::floor(point.y))-4);
			right = std::max(right,static_cast<int>(std::ceil(point.x))+4); bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
		}
		capture(scene,camera.Cropped(left,top,right-left,bottom-top),name,true);
		std::ofstream registration(directory/(name+".json"));
		registration << nlohmann::json{{"model_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}}}.dump(2) << '\n';
		if (!registration) throw std::runtime_error("Could not write native voxel study registration");
	};
	for (const auto &[name,model] : Models().models) for (unsigned view = 0; view < 8; ++view) {
		if (!name.starts_with(prefix)) continue;
		Textures().BeginScene();
		Scene scene;
		AddVoxelInstance(scene,model,Material({},PAL_NONE,1));
		Vec3 centre = (model.surface.low+model.surface.high)*0.5f;
		Camera camera{centre,3,640,640,static_cast<float>(view)};
		if (view >= 4) camera = StreetReviewCamera(model.surface.low,model.surface.high,640,640,view-4+1.5f);
		capture(scene,camera,fmt::format("model-voxel-{}-{}",name,view));
		if (view == 0) native_model(scene,fmt::format("model-voxel-{}-native",name));
	}
	static const VoxelMesh ground = [] {
		VoxelGrid grid({112,112,1},{{{4,4,4,4,4,4}},{{7,7,7,7,7,7}}},{-8,-8,-1});
		grid.Fill({0,0,0},{112,112,1},1);
		grid.Fill({0,12,0},{112,16,1},2); grid.Fill({12,0,0},{16,112,1},2);
		/* Keep the reference substrate's depth interpolation at exact building
		 * contacts. The volume models above use compact shared boundaries. */
		return grid.Mesh(true,1,UINT16_MAX,false);
	}();
	auto context = [&](std::string_view label, std::span<const VoxelModel *const> group, std::span<const Vec3> placements = {}, std::span<const float> headings = {}, std::span<const bool> children = {}) {
		if (group.empty()) return;
		if ((!placements.empty() && placements.size() != group.size()) || (!headings.empty() && headings.size() != group.size()) || (!children.empty() && children.size() != group.size())) throw std::runtime_error("Invalid voxel review placements");
		bool has_ground = std::ranges::any_of(Models().bindings,[&](const auto &entry) {
			return (std::get<0>(entry.first) == "industry_ground" || std::get<0>(entry.first) == "house_ground" || std::get<0>(entry.first) == "airport_ground" || std::get<0>(entry.first) == "depot_floors") && std::ranges::find(group,&Models().models.at(entry.second)) != group.end();
		});
		auto place = [&](unsigned slot) { return placements.empty() ? Vec3{static_cast<float>(slot%2)*16,static_cast<float>(slot/2)*16,0} : placements[slot]; };
		Vec3 low{INFINITY,INFINITY,INFINITY}, high{-INFINITY,-INFINITY,-INFINITY};
		for (unsigned slot = 0; slot < group.size(); ++slot) {
			Vec3 origin = place(slot);
			Vec3 a = origin+group[slot]->surface.low, b = origin+group[slot]->surface.high;
			if (!headings.empty()) {
				float cs = std::cos(headings[slot]), sn = std::sin(headings[slot]);
				a.x = a.y = INFINITY; b.x = b.y = -INFINITY;
				for (float x : {group[slot]->surface.low.x,group[slot]->surface.high.x}) for (float y : {group[slot]->surface.low.y,group[slot]->surface.high.y}) {
					Vec3 p = origin+Vec3{x*cs-y*sn,x*sn+y*cs,0};
					a.x = std::min(a.x,p.x); a.y = std::min(a.y,p.y);
					b.x = std::max(b.x,p.x); b.y = std::max(b.y,p.y);
				}
			}
			low = {std::min(low.x,a.x),std::min(low.y,a.y),std::min(low.z,a.z)};
			high = {std::max(high.x,b.x),std::max(high.y,b.y),std::max(high.z,b.z)};
		}
		for (unsigned view = 0; view < 8; ++view) {
			Textures().BeginScene();
			Scene scene;
			scene.instances.push_back({&ground.vertices,Material({0,0,has_ground ? -0.25f : 0},PAL_NONE,1)});
			for (unsigned slot = 0; slot < group.size(); ++slot) {
				Vec3 origin = place(slot);
				AddVoxelInstance(scene,*group[slot],Material(origin,PAL_NONE,1));
				if (!headings.empty()) scene.instances.back().data.mirror_layer_heading[3] = headings[slot];
				if (!children.empty()) scene.instances.back().data.SetChildLayer(children[slot]);
			}
			Camera camera{(low+high)*0.5f,2.5f,800,600,view+0.2f};
			if (view >= 4) {
				camera = StreetReviewCamera(low,high,800,600,view-4+1.5f);
			} else {
				/* Fit the entire group rather than cropping the taller member when
				 * it is nearest the lens after an orbit. Keep the review lens fixed. */
				for (unsigned attempt = 0; attempt < 30; ++attempt) {
					bool fits = true;
					for (float x : {low.x,high.x}) for (float y : {low.y,high.y}) for (float z : {low.z,high.z}) {
						auto point = camera.Project({x,y,z});
						fits &= point.visible && point.x >= 24 && point.x < camera.width-24 && point.y >= 24 && point.y < camera.height-24;
					}
					if (fits) break;
					camera.pixels_per_unit *= 0.9f;
				}
			}
			capture(scene,camera,fmt::format("model-voxel-{}-{}",label,view));
		}
	};
	std::vector<const VoxelModel *> mixed;
	for (const auto &[name,model] : Models().models) if (name.starts_with(prefix) && mixed.size() < 4) mixed.push_back(&model);
	context("context",mixed);
	/* Every bound volume appears in a category context, including later pages.
	 * Growing the catalogue must not silently drop the fifth and later models. */
	std::map<std::string,std::vector<const VoxelModel *>> groups;
	for (const auto &[binding,name] : Models().bindings) {
		if (!name.starts_with(prefix)) continue;
		auto &group = groups[std::get<0>(binding)];
		const auto *model = &Models().models.at(name);
		if (std::find(group.begin(),group.end(),model) == group.end()) group.push_back(model);
	}
	for (const auto &[category,group] : groups) for (size_t first = 0; first < group.size(); first += 4) {
		std::vector<const VoxelModel *> page(group.begin()+first,group.begin()+std::min(first+4,group.size()));
		for (const auto *neighbour : group) {
			if (page.size() == 4) break;
			if (std::find(page.begin(),page.end(),neighbour) == page.end()) page.push_back(neighbour);
		}
		context(fmt::format("context-{}-{}",category,first/4),page);
	}
	for (unsigned house = 0; house < GetTownDrawTileData().size()/16; ++house) {
		auto offsets = HouseReviewOffsets(house);
		bool multiple_tiles = !offsets.empty();
		if (!multiple_tiles && !HouseSpec::Get(house)->building_flags.Test(BuildingFlag::Size1x1)) continue;
		if (!multiple_tiles) offsets.push_back({});
		for (unsigned stage = 0; stage < 4; ++stage) {
			std::vector<const VoxelModel *> group;
			std::vector<Vec3> placements;
			bool selected = false;
			unsigned parts = 0;
			for (unsigned part = 0; part < offsets.size(); ++part) {
				auto body = VoxelHouseState(house+part,stage,0), floor = VoxelHouseGroundState(house+part,stage,0);
				const auto &source = GetTownDrawTileData()[(house+part)*16+stage];
				if ((!body && !floor) || (!body && source.building.sprite != 0)) break;
				for (bool ground : {true,false}) if (auto state = ground ? floor : body) {
					const auto &name = Models().bindings.at({ground ? "house_ground" : "houses",house+part,*state});
					selected |= name.starts_with(prefix);
					group.push_back(&Models().models.at(name));
					placements.push_back(offsets[part]);
				}
				++parts;
			}
			if (!selected || parts != offsets.size()) continue;
			if (multiple_tiles) {
				context(fmt::format("context-house-{}-stage-{}",house,stage),group,placements);
				/* Fully voxel-bound grounds permit a source-scale complete block,
				 * including the original ground-only first construction stage. */
				Scene native;
				bool complete_ground = true;
				for (unsigned part = 0; part < offsets.size(); ++part) {
					const auto &source = GetTownDrawTileData()[(house+part)*16+stage];
					complete_ground &= DrawVoxelHouseGround(native,house+part,stage,0,source.ground.sprite,offsets[part],source.ground.pal);
					if (auto body = VoxelHouseState(house+part,stage,0)) DrawVoxelAsset(native,"houses",house+part,*body,offsets[part],source.building.pal);
				}
				if (complete_ground) {
					for (auto &instance : native.instances) instance.data.SetObjectId(1);
					Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
					/* Joined towers can be taller than the original stadium/hotel crop.
					 * Expand around their geometry at unchanged source scale and keep
					 * the shared tile anchor, just as for single-house native reviews. */
					int left = 8192-96, top = 8192-64, right = 8192+96, bottom = 8192+80;
					for (const auto &instance : native.instances) for (const auto &vertex : *instance.mesh) {
						auto point = camera.Project(ResolveInstanceVertex(vertex,instance.data).position);
						if (!point.visible) throw std::runtime_error("Native joined house review is outside the fixed-lens camera");
						left = std::min(left,static_cast<int>(std::floor(point.x))-4);
						top = std::min(top,static_cast<int>(std::floor(point.y))-4);
						right = std::max(right,static_cast<int>(std::ceil(point.x))+4);
						bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
					}
					std::string name = fmt::format("model-voxel-house-block-{}-{}-native",house,stage);
					capture(native,camera.Cropped(left,top,right-left,bottom-top),name,true);
					std::ofstream registration(directory/(name+".json"));
					registration << nlohmann::json{{"tile_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}}}.dump(2) << '\n';
					if (!registration) throw std::runtime_error("Could not write native joined-house registration");
				}
			}
			if (stage == 3) {
				auto neighbour_offsets = placements;
				float column = 16;
				for (Vec3 offset : offsets) column = std::max(column,offset.x+16);
				unsigned added = 0;
				for (unsigned neighbour = 0; neighbour < GetTownDrawTileData().size()/16 && added < 2; ++neighbour) {
					if (neighbour == house || !HouseSpec::Get(neighbour)->building_flags.Test(BuildingFlag::Size1x1)) continue;
					auto state = VoxelHouseState(neighbour,3,0);
					if (!state) continue;
					if (auto floor = VoxelHouseGroundState(neighbour,3,0)) {
						group.push_back(&Models().models.at(Models().bindings.at({"house_ground",neighbour,*floor})));
						neighbour_offsets.push_back({column,static_cast<float>(added)*16,0});
					}
					group.push_back(&Models().models.at(Models().bindings.at({"houses",neighbour,*state})));
					neighbour_offsets.push_back({column,static_cast<float>(added++)*16,0});
				}
				context(fmt::format("context-house-{}-neighbours",house),group,neighbour_offsets);
			}
		}
	}
	/* Place industry members at their actual layout offsets. A gallery page of
	 * unrelated adjacent parts cannot establish their in-game spacing/clearance. */
	for (IndustryType type = 0; type < NUM_INDUSTRYTYPES; ++type) {
		const auto &layouts = GetIndustrySpec(type)->layouts;
		for (unsigned layout = 0; layout < layouts.size(); ++layout) {
			/* Select the whole family before looking at construction slots. A
			 * ground-only first state may use a shared soil model with a different
			 * prefix, but it is still part of the requested original layout. */
			bool selected = false;
			for (const auto &part : layouts[layout]) for (unsigned stage = 0; stage < 4; ++stage) for (const char *category : {"industry_ground","industries"}) {
				if (part.gfx >= std::size(_industry_draw_tile_data)/4) continue;
				bool ground = std::string_view(category) == "industry_ground";
				const auto &source = _industry_draw_tile_data[part.gfx*4+stage];
				if (!IndustryModelClimateSupported(part.gfx,to_underlying(_settings_game.game_creation.landscape),ground,(ground ? source.ground.sprite : source.building.sprite)&SPRITE_MASK)) continue;
				auto binding = Models().bindings.find({category,part.gfx,stage});
				selected |= binding != Models().bindings.end() && binding->second.starts_with(prefix);
			}
			if (!selected) continue;
			for (unsigned stage = 0; stage < 4; ++stage) {
				std::vector<const VoxelModel *> group;
				std::vector<Vec3> placements;
				for (const auto &part : layouts[layout]) for (const char *category : {"industry_ground","industries"}) {
					if (part.gfx >= std::size(_industry_draw_tile_data)/4) continue;
					bool ground = std::string_view(category) == "industry_ground";
					const auto &source = _industry_draw_tile_data[part.gfx*4+stage];
					if (!IndustryModelClimateSupported(part.gfx,to_underlying(_settings_game.game_creation.landscape),ground,(ground ? source.ground.sprite : source.building.sprite)&SPRITE_MASK)) continue;
					auto binding = Models().bindings.find({category,part.gfx,stage});
					if (binding == Models().bindings.end()) continue;
					group.push_back(&Models().models.at(binding->second));
					placements.push_back({static_cast<float>(part.ti.x*TILE_SIZE),static_cast<float>(part.ti.y*TILE_SIZE),0});
					if (!ground && part.gfx == 143 && stage == 3 && VoxelIndustryState(143,source.building.sprite)) {
						Vec3 origin = placements.back();
						for (const auto &child : VoxelToyFactoryChildren(0)) if (child.image != 0) {
							group.push_back(&Models().models.at(Models().bindings.at({"infrastructure",child.image,0})));
							placements.push_back(origin+child.offset);
						}
					}
				}
				if (group.empty()) continue;
				context(fmt::format("context-industry-{}-layout-{}-stage-{}",type,layout,stage),group,placements);
				Scene joined;
				nlohmann::json tiles = nlohmann::json::array();
				bool complete = true;
				for (const auto &part : layouts[layout]) {
					if (part.gfx >= std::size(_industry_draw_tile_data)/4) continue;
					const auto &source = _industry_draw_tile_data[part.gfx*4+stage];
					Vec3 origin{static_cast<float>(part.ti.x*TILE_SIZE),static_cast<float>(part.ti.y*TILE_SIZE),0};
					complete &= DrawVoxelIndustryGround(joined,part.gfx,source.ground.sprite,origin,source.ground.pal);
					if ((source.building.sprite&SPRITE_MASK) != 0 && !DrawVoxelAsset(joined,"industries",part.gfx,stage,origin,source.building.pal)) {
						/* A nonzero source number can still resolve to genuine absence
						 * (toy-shop141 construction0). Only actual empty base artwork
						 * may complete this review without an authored body. */
						const auto &texture = Textures().Get(source.building.sprite,source.building.pal);
						complete &= texture.base_graphics && texture.ink_width == 0 && texture.ink_height == 0;
					}
					if (part.gfx == 143 && stage == 3) {
						for (const auto &child : VoxelToyFactoryChildren(0)) if (child.image != 0) complete &= DrawVoxelToyFactoryChild(joined,child.image,0,origin,source.building.pal);
					}
					tiles.push_back({{"graphics",part.gfx},{"origin",{origin.x,origin.y,origin.z}}});
					if (part.gfx == 143 && stage == 3) tiles.back()["procedural_frame"] = 0;
				}
				if (!complete) continue;
				for (auto &instance : joined.instances) instance.data.SetObjectId(1);
				Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
				int left = 8192, top = 8192, right = 8192, bottom = 8192;
				for (const auto &instance : joined.instances) for (const auto &vertex : *instance.mesh) {
					auto point = camera.Project(ResolveInstanceVertex(vertex,instance.data).position);
					if (!point.visible) throw std::runtime_error("Native joined industry review is outside the fixed-lens camera");
					left = std::min(left,static_cast<int>(std::floor(point.x))-4); top = std::min(top,static_cast<int>(std::floor(point.y))-4);
					right = std::max(right,static_cast<int>(std::ceil(point.x))+4); bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
				}
				std::string name = fmt::format("model-voxel-industry-layout-{}-{}-{}-native",type,layout,stage);
				capture(joined,camera.Cropped(left,top,right-left,bottom-top),name,true);
				std::ofstream registration(directory/(name+".json"));
				registration << nlohmann::json{{"tile_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}},{"tiles",tiles}}.dump(2) << '\n';
				if (!registration) throw std::runtime_error("Could not write native joined-industry registration");
			}
		}
	}
	/* Retain all original factory child combinations, including sentinel absences.
	 * These are read-only diagnostic scenes, never animation on an actual tile. */
	if (auto state = VoxelIndustryState(143,_industry_draw_tile_data[143*4+3].building.sprite)) {
		const auto &name = Models().bindings.at({"industries",143,*state});
		if (name.starts_with(prefix)) {
			nlohmann::json frames = nlohmann::json::array();
			for (unsigned frame = 0; frame < std::size(_industry_anim_offs_toys); ++frame) {
				Textures().BeginScene();
				Scene scene;
				DrawVoxelAsset(scene,"industries",143,*state,{},PAL_NONE);
				nlohmann::json children = nlohmann::json::array();
				std::vector<const VoxelModel *> group{&Models().models.at(name)};
				std::vector<Vec3> placements{{}};
				for (const auto &child : VoxelToyFactoryChildren(frame)) if (child.image != 0) {
					if (!DrawVoxelToyFactoryChild(scene,child.image,frame,{},PAL_NONE)) throw std::runtime_error("Incomplete toy-factory diagnostic children");
					children.push_back({{"sprite",child.image},{"child_offset",{child.x,child.y}},{"world_offset",{child.offset.x,child.offset.y,child.offset.z}}});
					group.push_back(&Models().models.at(Models().bindings.at({"infrastructure",child.image,0})));
					placements.push_back(child.offset);
				}
				std::string label = fmt::format("model-voxel-industry-procedural-143-{}-native",frame);
				native_model(scene,label);
				frames.push_back({{"graphics",143},{"stage",3},{"frame",frame},{"image",label+".pam"},{"children",children}});
				if (frame == 0 || frame == 19 || frame == 30 || frame == 41) context(fmt::format("context-industry-procedural-143-{}",frame),group,placements);
			}
			std::ofstream manifest(directory/"voxel-industry-procedural-143.json"); manifest << frames.dump(2) << '\n';
			if (!manifest) throw std::runtime_error("Could not write toy-factory diagnostic manifest");
		}
	}
	std::set<unsigned> selected_houses;
	for (const auto &[binding,name] : Models().bindings) if ((std::get<0>(binding) == "houses" || std::get<0>(binding) == "house_ground") && name.starts_with(prefix)) selected_houses.insert(std::get<1>(binding));
	for (unsigned base : selected_houses) for (unsigned slot = 0; slot < 16; ++slot) {
		const auto &source = GetTownDrawTileData()[base*16+slot];
		auto state = VoxelHouseState(base,slot%4,slot/4);
		/* Original empty civic/park bodies still have a real ground layer.
		 * Export it explicitly, but never fabricate an absent nonempty model. */
		if (!state && source.building.sprite != 0) continue;
		Textures().BeginScene();
		Scene house;
		if (DrawVoxelHouseGround(house,base,slot%4,slot/4,source.ground.sprite,{},source.ground.pal)) {
			for (auto &instance : house.instances) instance.data.SetObjectId(1);
		} else if (source.ground.sprite != 0) {
			const auto &texture = Textures().Get(source.ground.sprite,source.ground.pal,0,true);
			static const auto tile = [] {
				Scene scene; scene.Quad({0,0,0},{16,0,0},{16,16,0},{0,16,0},{});
				return scene.vertices;
			}();
			InstanceData ground;
			Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
			ground.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
			ground.region = texture.Region();
			ground.identity = {0,static_cast<float>(SurfaceMode::Opaque),1,0};
			ground.SetObjectId(1);
			house.instances.push_back({&tile,ground});
		}
		if (state) {
			const auto &name = Models().bindings.at({"houses",base,*state});
			auto material = Material({},source.building.pal,1); material.SetObjectId(1);
			AddVoxelInstance(house,Models().models.at(name),material);
		}
		Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
		/* Keep native scale and tile registration while fitting tall masts/cores.
		 * A fixed -96 crop silently truncated the 2000-era suspended office. */
		int left = 8192-64, top = 8192-96, right = 8192+64, bottom = 8192+48;
		for (const auto &instance : house.instances) for (const auto &vertex : *instance.mesh) {
			auto point = camera.Project(ResolveInstanceVertex(vertex,instance.data).position);
			if (!point.visible) throw std::runtime_error("Native house review is outside the fixed-lens camera");
			left = std::min(left,static_cast<int>(std::floor(point.x))-4);
			top = std::min(top,static_cast<int>(std::floor(point.y))-4);
			right = std::max(right,static_cast<int>(std::ceil(point.x))+4);
			bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
		}
		std::string name = fmt::format("model-voxel-house-{}-{}-native-{}",base,slot/4,slot%4);
		capture(house,camera.Cropped(left,top,right-left,bottom-top),name,true);
		std::ofstream registration(directory/(name+".json"));
		registration << nlohmann::json{{"tile_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}}}.dump(2) << '\n';
		if (!registration) throw std::runtime_error("Could not write native house registration");
	}
	/* A family's construction floor can share a differently named soil model.
	 * Export all native ground/body states of each selected industry definition
	 * so the registered source sheet retains its complete ownership history. */
	std::set<unsigned> industry_native_families;
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,base,stage] = binding;
		if ((category == "industries" || category == "industry_ground") && name.starts_with(prefix)) industry_native_families.insert(base);
	}
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,base,stage] = binding;
		unsigned airport_frame = stage%16;
		if (category == "airport_ground" && stage != VoxelAirportGroundState(base,airport_frame)) continue;
		if ((category == "airport_tiles" || (category == "airport_ground" && !HasVoxelAsset("airport_tiles",base,airport_frame))) && HasVoxelAirport(base,airport_frame)) {
			auto floor = Models().bindings.find({"airport_ground",base,VoxelAirportGroundState(base,airport_frame)});
			if (!name.starts_with(prefix) && (floor == Models().bindings.end() || !floor->second.starts_with(prefix))) continue;
			Textures().BeginScene();
			Scene airport;
			std::vector<const VoxelModel *> group;
			if (category == "airport_tiles") group.push_back(&Models().models.at(name));
			if (DrawVoxelAirportGround(airport,base,airport_frame,{},PAL_NONE)) group.push_back(&Models().models.at(floor->second));
			DrawVoxelAsset(airport,"airport_tiles",base,airport_frame,{},PALETTE_TO_BLUE);
			for (auto &instance : airport.instances) instance.data.SetObjectId(1);
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			int left = 8192-64, top = 8192-80, right = 8192+64, bottom = 8192+48;
			for (const auto &instance : airport.instances) for (const auto &vertex : *instance.mesh) {
				auto point = camera.Project(ResolveInstanceVertex(vertex,instance.data).position);
				if (!point.visible) throw std::runtime_error("Native airport review is outside the fixed-lens camera");
				left = std::min(left,static_cast<int>(std::floor(point.x))-4);
				top = std::min(top,static_cast<int>(std::floor(point.y))-4);
				right = std::max(right,static_cast<int>(std::ceil(point.x))+4);
				bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
			}
			std::string label = fmt::format("model-voxel-airport-{}-{}-native",base,airport_frame);
			capture(airport,camera.Cropped(left,top,right-left,bottom-top),label,true);
			std::ofstream registration(directory/(label+".json"));
			registration << nlohmann::json{{"tile_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}}}.dump(2) << '\n';
			if (!registration) throw std::runtime_error("Could not write native airport registration");
			std::vector<Vec3> placements(group.size());
			context(fmt::format("context-airport-{}-{}",base,airport_frame),group,placements);
		}
		if (category == "docks" && stage == VoxelDockState() && name.starts_with(prefix) && HasVoxelDock(base)) {
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			capture(DockReviewScene(base,PAL_NONE),camera.Cropped(8192-64,8192-80,128,128),fmt::format("model-voxel-dock-native-{}",base),true);
			if (base < 4) {
				Scene joined = JoinedDockReviewScene(base,PAL_NONE);
				capture(joined,camera.Cropped(8192-96,8192-80,192,144),fmt::format("model-voxel-dock-joined-native-{}",base),true);
				const Vec3 offsets[] = {{-16,0,0},{0,16,0},{16,0,0},{0,-16,0}};
				Vec3 low{std::min(0.0f,offsets[base].x),std::min(0.0f,offsets[base].y),0};
				Vec3 high{16+std::max(0.0f,offsets[base].x),16+std::max(0.0f,offsets[base].y),14};
				for (unsigned view = 0; view < 8; ++view) {
					Camera context_camera{(low+high)*0.5f,2.5f,800,600,view+0.2f};
					if (view >= 4) context_camera = StreetReviewCamera(low,high,800,600,view-4+1.5f);
					capture(joined,context_camera,fmt::format("model-voxel-context-dock-{}-{}",base,view));
				}
			}
		}
		if (category == "ship_depots" && stage == 0 && HasVoxelShipDepot(base,0) &&
			(name.starts_with(prefix) || Models().bindings.at({"ship_depots",base,1}).starts_with(prefix))) {
			Scene depot = ShipDepotReviewScene(base,PAL_NONE);
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			capture(depot,camera.Cropped(8192-96,8192-80,192,144),fmt::format("model-voxel-ship-depot-native-{}",base),true);
			std::vector<const VoxelModel *> group{&Models().models.at(name),&Models().models.at(Models().bindings.at({"ship_depots",base,1}))};
			std::vector<Vec3> placements{{},base == 0 ? Vec3{16,0,0} : Vec3{0,16,0}};
			context(fmt::format("context-ship-depot-{}",base),group,placements);
			if (HasVoxelAsset("vehicles",208,0)) {
				group.push_back(&Models().models.at(Models().bindings.at({"vehicles",208,0})));
				placements.push_back(base == 0 ? Vec3{24,8,0} : Vec3{8,24,0});
				std::vector<float> headings{0,0,base == 0 ? 0 : std::numbers::pi_v<float>*0.5f};
				context(fmt::format("context-ship-depot-{}-clearance",base),group,placements,headings);
			}
		}
		if (category == "depots" && name.starts_with(prefix) && VoxelDepotState(stage%4) == stage && HasVoxelDepot(base,stage%4)) {
			unsigned direction = stage%4;
			Textures().BeginScene();
			Scene depot;
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			DrawDepot(depot,camera,{},base,direction,PALETTE_TO_BLUE);
			for (auto &instance : depot.instances) instance.data.SetObjectId(1);
			capture(depot,camera.Cropped(8192-64,8192-80,128,128),fmt::format("model-voxel-depot-{}-native-{}",base,direction),true);
			std::vector<const VoxelModel *> group{&Models().models.at(name),&Models().models.at(Models().bindings.at({"depot_floors",base,base == 5 ? direction : 0}))};
			std::vector<Vec3> placements{{},{}};
			std::vector<float> headings{0,0};
			if (base == 4 && HasVoxelAsset("vehicles",123,1)) {
				group.push_back(&Models().models.at(Models().bindings.at({"vehicles",123,1})));
				placements.push_back(DepotPoint(direction,{22,8,0}));
				Vec3 exit = DepotPoint(direction,{16,8,0})-DepotPoint(direction,{8,8,0});
				headings.push_back(std::atan2(-exit.y,-exit.x));
			}
			if (base < 2 && HasVoxelAsset("vehicles",23,0)) {
				group.push_back(&Models().models.at(Models().bindings.at({"vehicles",23,0})));
				placements.push_back(DepotPoint(direction,{22,8,0}));
				Vec3 exit = DepotPoint(direction,{16,8,0})-DepotPoint(direction,{8,8,0});
				headings.push_back(std::atan2(-exit.y,-exit.x));
			}
			context(fmt::format("context-depot-{}-direction-{}",base,direction),group,placements,headings);
		}
		if ((category == "industries" || category == "industry_ground") && industry_native_families.contains(base)) {
			bool ground_layer = category == "industry_ground";
			const auto &source = _industry_draw_tile_data[base*4+stage];
			if (!IndustryModelClimateSupported(base,to_underlying(_settings_game.game_creation.landscape),ground_layer,(ground_layer ? source.ground.sprite : source.building.sprite)&SPRITE_MASK)) continue;
			Textures().BeginScene();
			Scene industry;
			/* Some original body sprites own a complete ground substrate. Keep the
			 * diagnostic plane below that geometry instead of clipping its top. */
			float z = std::min(ground_layer ? -0.25f : 0.0f,Models().models.at(name).surface.low.z-0.25f);
			industry.Quad({-16,-16,z},{48,-16,z},{48,48,z},{-16,48,z},{0,0,0});
			auto material = Material({},ground_layer ? source.ground.pal : source.building.pal,1);
			material.SetObjectId(1);
			AddVoxelInstance(industry,Models().models.at(name),material);
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			int left = 8192-64, top = 8192-80, right = 8192+64, bottom = 8192+48;
			/* Tall flare stacks and joined rig parts must retain their full source-
			 * scale silhouette. The former fixed crop silently cut their tops. */
			for (const auto &vertex : *industry.instances.front().mesh) {
				auto point = camera.Project(ResolveInstanceVertex(vertex,material).position);
				if (!point.visible) throw std::runtime_error("Native industry review is outside the fixed-lens camera");
				left = std::min(left,static_cast<int>(std::floor(point.x))-4);
				top = std::min(top,static_cast<int>(std::floor(point.y))-4);
				right = std::max(right,static_cast<int>(std::ceil(point.x))+4);
				bottom = std::max(bottom,static_cast<int>(std::ceil(point.y))+4);
			}
			std::string export_name = fmt::format("model-voxel-industry{}-{}-native-{}",ground_layer ? "-ground" : "",base,stage);
			capture(industry,camera.Cropped(left,top,right-left,bottom-top),export_name,true);
			std::ofstream registration(directory/(export_name+".json"));
			registration << nlohmann::json{{"tile_origin",{8192-left,8192-top}},{"image_size",{right-left,bottom-top}}}.dump(2) << '\n';
			if (!registration) throw std::runtime_error("Could not write native industry registration");
		}
		if (category == "vehicles" && name.starts_with(prefix) && VoxelVehicleState(base,(stage&1U) != 0) == stage) {
			if (base >= 23 && base <= 26 && stage == 0) for (unsigned lowered = 0; lowered < 3; ++lowered) for (unsigned view = 0; view < 8; ++view) {
				Scene train;
				DrawVoxelVehicle(train,base,false,{},0,PALETTE_RECOLOUR_START,1);
				std::array<float,2> heights = lowered == 0 ? std::array{10.0f,10.0f} : lowered == 1 ? std::array{7.55f,7.55f} : std::array{8.8f,7.55f};
				DrawVoxelTrainCollectors(train,base,{},0,PALETTE_RECOLOUR_START,heights);
				Camera camera{{0,0,5},3,640,640,static_cast<float>(view)};
				if (view >= 4) camera = StreetReviewCamera({-8,-2,0},{8,2,11},640,640,view-4+1.5f);
				capture(train,camera,fmt::format("model-voxel-train-{}-collector-{}-{}",base,lowered,view));
			}
			for (unsigned direction = 0; direction < 8; ++direction) {
				Textures().BeginScene();
				Scene vehicle;
				auto material = Material({},PALETTE_RECOLOUR_START,1);
				material.mirror_layer_heading[3] = (5.0f-direction)*std::numbers::pi_v<float>/4;
				const auto &mesh = Models().models.at(name).surface;
				if (base < 116) material.SetLongitudinalScale(OriginalTrainVoxelScale(material.mirror_layer_heading[3],mesh.high.x-mesh.low.x));
				material.SetObjectId(1);
				AddVoxelInstance(vehicle,Models().models.at(name),material);
				DrawVoxelTrainCollectors(vehicle,base,{},material.mirror_layer_heading[3],PALETTE_RECOLOUR_START);
				for (auto &instance : vehicle.instances) instance.data.SetObjectId(1);
				Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
				capture(vehicle,camera.Cropped(8192-48,8192-72,96,96),fmt::format("model-voxel-vehicle-{}-{}-native-{}",base,stage&1U,direction),true);
				if (base >= 253 && base <= 255 && (stage&1U) == 0) for (unsigned rotor = 0; rotor < 4; ++rotor) {
					Scene joined = vehicle;
					if (!DrawVoxelHelicopterRotor(joined,SPR_ROTOR_STOPPED+rotor,{0,0,ROTOR_Z_OFFSET})) continue;
					/* Diagnostic silhouette owns both parts; live rotors keep their
					 * original unclickable ID, checked separately during capture. */
					joined.instances.back().data.SetObjectId(1);
					capture(joined,camera.Cropped(8192-48,8192-72,96,96),fmt::format("model-voxel-helicopter-{}-rotor-{}-native-{}",base,rotor,direction),true);
					if (direction < 4) {
						const auto &rotor_mesh = Models().models.at(Models().bindings.at({"infrastructure",SPR_ROTOR_STOPPED,rotor})).surface;
						Vec3 low{std::min(mesh.low.x,rotor_mesh.low.x),std::min(mesh.low.y,rotor_mesh.low.y),mesh.low.z};
						Vec3 high{std::max(mesh.high.x,rotor_mesh.high.x),std::max(mesh.high.y,rotor_mesh.high.y),std::max(mesh.high.z,rotor_mesh.high.z+ROTOR_Z_OFFSET)};
						joined.instances.front().data.mirror_layer_heading[3] = 0;
						capture(joined,StreetReviewCamera(low,high,640,480,direction),fmt::format("model-voxel-helicopter-{}-rotor-{}-street-{}",base,rotor,direction));
					}
				}
			}
		}
		if (category != "trees" || !name.starts_with(prefix)) continue;
		/* Keep the fixed lens while using a distant virtual canvas, then crop its
		 * centre. One art pixel per world height unit makes source-scale silhouette
		 * review possible without allocating the large virtual framebuffer. */
		Textures().BeginScene();
		Scene native;
		/* Black ground hides embedded root cells exactly as the world terrain does. */
		native.Quad({-16,-16,0},{16,-16,0},{16,16,0},{-16,16,0},{0,0,0});
		AddVoxelInstance(native,Models().models.at(name),Material({},PAL_NONE,1));
		native.instances.back().data.SetObjectId(1);
		Camera native_camera{{},1,16384,16384,0};
		native_camera.vertical_fov = 40;
		capture(native,native_camera.Cropped(8192-48,8192-80,96,96),fmt::format("model-voxel-tree-{}-native-{}",base,stage),true);
		if (stage != 3) continue;
		std::vector<const VoxelModel *> group{&Models().models.at(name)};
		std::vector<Vec3> placements{{8,8,0}};
		for (unsigned house : {6U,13U}) if (auto state = VoxelHouseState(house,3,0)) {
			group.push_back(&Models().models.at(Models().bindings.at({"houses",house,*state})));
			placements.push_back({24,static_cast<float>(placements.size()-1)*16,0});
		}
		context(fmt::format("context-tree-{}-neighbours",base),group,placements);
	}
	if (auto binding = Models().bindings.find({"infrastructure",SPR_IMG_BUOY,0}); binding != Models().bindings.end() && binding->second.starts_with(prefix)) {
		Textures().BeginScene();
		Scene buoy;
		DrawVoxelAsset(buoy,"infrastructure",SPR_IMG_BUOY,_settings_game.game_creation.landscape == LandscapeType::Toyland ? 1 : 0,{});
		for (auto &instance : buoy.instances) instance.data.SetObjectId(1);
		Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
		capture(buoy,camera.Cropped(8192-32,8192-32,64,80),"model-voxel-buoy-native",true);
	}
	if (VoxelIndustryState(10,SPR_IT_POWER_PLANT_TRANSFORMERS)) {
		const auto &parent_name = Models().bindings.at({"industries",10,3});
		for (unsigned frame = 1; frame <= std::size(_coal_plant_sparks); ++frame) {
			const auto &spark_name = Models().bindings.at({"infrastructure",SPR_IT_POWER_PLANT_TRANSFORMERS+frame,0});
			if (!parent_name.starts_with(prefix) && !spark_name.starts_with(prefix)) continue;
			Textures().BeginScene();
			Scene combined;
			DrawVoxelAsset(combined,"industries",10,3,{});
			DrawVoxelIndustrySpark(combined,SPR_IT_POWER_PLANT_TRANSFORMERS+frame,{});
			for (auto &instance : combined.instances) instance.data.SetObjectId(1);
			Camera camera{{},1,16384,16384,0}; camera.vertical_fov = 40;
			capture(combined,camera.Cropped(8192-64,8192-80,128,128),fmt::format("model-voxel-power-spark-native-{}",frame),true);
			std::vector<const VoxelModel *> group{&Models().models.at(parent_name),&Models().models.at(spark_name)};
			context(fmt::format("context-power-spark-{}",frame),group,std::vector<Vec3>(2),{},std::array<bool,2>{false,true});
		}
	}
	Debug(driver,1,"OpenTT3D: exported voxel turntables, street-level views and neighbouring-building context (prefix '{}')",prefix);
}

void VerifyVoxelTreeModels()
{
	std::map<unsigned,std::set<PaletteID>> palettes;
	for (const auto &row : _tree_layout_sprite) for (const auto &sprite : row) palettes[sprite.sprite].insert(sprite.pal);
	unsigned views = 0;
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,base,stage] = binding;
		if (category != "trees") continue;
		if (stage >= 7 || !HasVoxelTree(base+stage)) throw std::runtime_error("Voxel tree binding does not match its original lifecycle family");
		const auto &mesh = Models().models.at(name).surface;
		palettes[base].insert(PAL_NONE);
		for (PaletteID palette : palettes[base]) for (float scale : {0.1f,0.7f,4.0f}) for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
			Textures().BeginScene();
			const auto &texture = Textures().Get(base+stage,palette,0,false);
			Scene scene, reference;
			if (!DrawVoxelAsset(scene,"trees",base,stage,{},texture.palette) || scene.instances.size() != 1 || scene.instances.front().mesh != &mesh.vertices) throw std::runtime_error("Tree did not select its exact voxel lifecycle binding");
			scene.instances.front().data.SetObjectId(TILE_PICK_ID|73);
			reference.vertices = scene.ExpandedVertices(true);
			Camera camera{(mesh.low+mesh.high)*0.5f,2,256,256,turn+0.15f};
			if (street) camera = StreetReviewCamera(mesh.low,mesh.high,256,256,turn+0.15f);
			std::vector<uint8_t> pixels, expected;
			std::vector<uint32_t> ids, expected_ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),TILE_PICK_ID|73) < 8 || !RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error(fmt::format("Voxel tree {} palette {} scale {} turn {} street {} failed review rendering",name,palette,scale,turn,street));
			if (pixels != expected || ids != expected_ids) {
				unsigned colours = 0, picks = 0;
				for (size_t i = 0; i < ids.size(); ++i) {
					bool different = !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,expected.begin()+i*4);
					colours += different;
					picks += ids[i] != expected_ids[i];
					if (different && colours <= 16) if (const auto *volume = FindVoxelVolume(&mesh.vertices); volume != nullptr) {
						unsigned px = i%camera.width, py = camera.height-1-i/camera.width;
						auto ray = camera.ScreenRay(px+0.5f,py+0.5f);
						if (auto hit = volume->Trace(ray.origin,ray.direction)) Debug(driver,1,"OpenTT3D: tree ray diagnostic pixel {},{} cell {},{},{} face {} colour {} distance {}",px,py,hit->cell[0],hit->cell[1],hit->cell[2],hit->face,hit->colour,hit->distance);
					}
				}
				std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
				std::filesystem::create_directories(directory);
				const auto cell_mesh = Models().models.at(name).source->Expand(Models().materials).Mesh(false);
				Scene cells = scene;
				cells.persistent_meshes = false;
				cells.instances.front().mesh = &cell_mesh.vertices;
				std::vector<uint8_t> cell_pixels;
				std::vector<uint32_t> cell_ids;
				if (RenderScene(cells,camera,cell_pixels,&cell_ids)) {
					unsigned cell_colours = 0, cell_picks = 0, mesh_colours = 0, mesh_picks = 0;
					for (size_t i = 0; i < ids.size(); ++i) {
						cell_colours += !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,cell_pixels.begin()+i*4);
						mesh_colours += !std::equal(expected.begin()+i*4,expected.begin()+i*4+4,cell_pixels.begin()+i*4);
						cell_picks += ids[i] != cell_ids[i]; mesh_picks += expected_ids[i] != cell_ids[i];
					}
					Debug(driver,1,"OpenTT3D: voxel tree cell diagnostic: GPU/cells {} colours {} IDs, CPU/cells {} colours {} IDs",cell_colours,cell_picks,mesh_colours,mesh_picks);
				}
				for (bool cpu : {false,true}) {
					const auto &image = cpu ? expected : pixels;
					std::ofstream output(directory/fmt::format("model-voxel-tree-mismatch-{}-{}-{}-{}-{}-{}.pam",name,palette,scale,turn,street,cpu ? "cpu" : "gpu"),std::ios::binary);
					output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
					for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(image.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
				}
				throw std::runtime_error(fmt::format("Voxel tree {} palette {} scale {} turn {} street {} differs from CPU geometry: {} colour pixels, {} IDs",name,palette,scale,turn,street,colours,picks));
			}
			scene.instances.front().data.origin_opacity[3] = 0.38f;
			if (!RenderScene(scene,camera,pixels,&ids) || std::ranges::any_of(ids,[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent voxel tree intercepted picking");
			++views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} voxel tree lifecycle/palette/scale views preserve exact bindings, CPU geometry and transparent tile picking",views);
	/* Far, non-power-of-two framebuffers exercise pixel visibility rather than
	 * only the close review matrices. A separate copy retains the exact original
	 * triangle stream and cannot take any registered optimized-mesh path. */
	unsigned distant_views = 0;
	size_t distant_pixels = 0;
	for (const auto &[name,model] : Models().models) {
		if (!name.starts_with("tree_")) continue;
		auto lease = PinVoxelModel(model);
		const auto original_mesh = model.surface.vertices;
		for (Vec3 origin : {Vec3{},Vec3{500000,700000,100}}) for (float scale : {0.03f,0.12f,0.3f}) for (float turn : {0.15f,1.25f,2.65f,3.1f}) for (bool child_layer : {false,true}) {
			Textures().BeginScene();
			Scene actual, reference;
			reference.persistent_meshes = false;
			for (unsigned instance = 0; instance < 3; ++instance) {
				auto data = Material(origin+(instance == 1 ? Vec3{3,1,0} : Vec3{}),instance == 2 ? PALETTE_TO_STRUCT_BROWN : PAL_NONE,1);
				data.SetObjectId(TILE_PICK_ID|static_cast<uint32_t>(1001+instance));
				data.SetChildLayer(child_layer && instance == 0);
				AddVoxelInstance(actual,model,data);
				reference.instances.push_back({&original_mesh,data});
			}
			Camera camera{origin+(model.surface.low+model.surface.high)*0.5f,scale,240,180,turn}; camera.vertical_fov = 40;
			std::vector<uint8_t> pixels, expected;
			std::vector<uint32_t> ids, expected_ids;
			if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error("Distant voxel tree comparison failed to render");
			if (pixels != expected || ids != expected_ids) throw std::runtime_error(fmt::format("Distant voxel tree {} origin {} scale {} turn {} child {} changed original triangle colour or instance ownership",name,origin.x,scale,turn,child_layer));
			distant_pixels += std::count_if(ids.begin(),ids.end(),[](uint32_t id) { return id != 0; });
			++distant_views;
		}
	}
	if (distant_pixels < 100) throw std::runtime_error("Distant voxel tree comparisons have insufficient pixel coverage");
	Debug(driver,1,"OpenTT3D: {} distant voxel tree views retain exact original triangles, coincident parent/child instance order and picking at ordinary/large origins ({} visible pixels)",distant_views,distant_pixels);
	/* More than four visibility pages, then insert/remove/reorder across their
	 * boundaries without moving the camera. An unregistered original mesh keeps
	 * this independent of page reuse, indexing and background preparation. */
	const auto &model = Models().models.at("tree_lime_03");
	auto lease = PinVoxelModel(model);
	const auto original_mesh = model.surface.vertices;
	Scene edited;
	for (unsigned i = 0; i < 1025; ++i) {
		auto data = Material({(i%32)*12.0f,(i/32)*12.0f,0},i%3 == 0 ? PALETTE_TO_STRUCT_BROWN : PAL_NONE,1);
		data.SetObjectId(TILE_PICK_ID|(1001+i));
		AddVoxelInstance(edited,model,data);
	}
	Camera edit_camera{{192,192,20},0.12f,320,240,0.35f}; edit_camera.vertical_fov = 40;
	for (unsigned change = 0; change < 5; ++change) {
		Textures().BeginScene();
		if (change == 1) {
			auto extra = edited.instances.front(); extra.data.origin_opacity[2] += 1; extra.data.SetObjectId(TILE_PICK_ID|2500);
			edited.instances.insert(edited.instances.begin()+3,extra);
		}
		if (change == 2) edited.instances.erase(edited.instances.begin()+257);
		if (change == 3) std::swap(edited.instances[2],edited.instances[900]);
		if (change == 4) { UsePaletteMaterial(edited.instances[600].data,PALETTE_TO_STRUCT_BROWN); edited.instances[600].data.SetObjectId(TILE_PICK_ID|3000); }
		Scene reference = edited;
		reference.persistent_meshes = false;
		for (auto &instance : reference.instances) instance.mesh = &original_mesh;
		std::vector<uint8_t> pixels, expected;
		std::vector<uint32_t> ids, expected_ids;
		if (!RenderScene(edited,edit_camera,pixels,&ids) || !RenderScene(reference,edit_camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) {
			throw std::runtime_error(fmt::format("Edited voxel visibility stream {} changed original colour, ordering or picking",change));
		}
		if (std::count_if(ids.begin(),ids.end(),[](uint32_t id) { return id != 0; }) < 100) throw std::runtime_error("Edited voxel visibility stream has insufficient coverage");
	}
	Debug(driver,1,"OpenTT3D: 5 edited voxel visibility streams preserve 1025-instance insertion, removal, ordering and live palette/picking records");
}

void VerifyVoxelIndustryModels()
{
	unsigned views = 0, ground_views = 0, climate_fallbacks = 0;
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,graphics,stage] = binding;
		bool ground = category == "industry_ground";
		if (category != "industries" && !ground) continue;
		if (graphics >= std::size(_industry_draw_tile_data)/4 || stage >= 4) throw std::runtime_error("Invalid voxel industry binding");
		const auto &source = _industry_draw_tile_data[graphics*4+stage];
		const auto &mesh = Models().models.at(name).surface;
		SpriteID image = ground ? source.ground.sprite : source.building.sprite;
		PaletteID palette = ground ? source.ground.pal : source.building.pal;
		if (!IndustryModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape),ground,image&SPRITE_MASK)) {
			Scene fallback;
			if (VoxelIndustryState(graphics,image,ground) || (ground ? DrawVoxelIndustryGround(fallback,graphics,image,{},palette) : HasAuthoredIndustry(graphics,image))) throw std::runtime_error("Unauthored climate selected a different climate's industry body/ground");
			++climate_fallbacks;
			continue;
		}
		if (!VoxelIndustryState(graphics,image,ground)) throw std::runtime_error("Industry state binding does not match its original sprite");
		Textures().BeginScene();
		const auto &texture = Textures().Get(image,palette,0,false);
		for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
			Scene scene, reference;
			bool drawn = ground ? DrawVoxelIndustryGround(scene,graphics,image,{},palette) : DrawAuthoredIndustry(scene,graphics,image,texture,{}, {},1);
			if (!drawn || scene.instances.size() != 1 || scene.instances.front().mesh != &mesh.vertices) throw std::runtime_error("Industry did not select its explicit voxel state/layer");
			scene.instances.front().data.SetObjectId(TILE_PICK_ID|79);
			reference.vertices = scene.ExpandedVertices(true);
			Camera camera{(mesh.low+mesh.high)*0.5f,2,256,256,turn+0.15f};
			if (street) camera = StreetReviewCamera(mesh.low,mesh.high,256,256,turn+0.15f);
			std::vector<uint8_t> pixels, expected;
			std::vector<uint32_t> ids, expected_ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),TILE_PICK_ID|79) < 8 || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Voxel industry construction colour or tile ownership differs from CPU geometry");
			scene.instances.front().data.origin_opacity[3] = 0.38f;
			if (!RenderScene(scene,camera,pixels,&ids) || std::ranges::any_of(ids,[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent voxel industry intercepted picking");
			++views;
			if (ground) ++ground_views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} voxel industry construction/animation views preserve source selection, exact CPU geometry and transparent tile picking",views);
	Debug(driver,1,"OpenTT3D: {} of these views verify explicit voxel industry ground/stockpile layers",ground_views);
	Debug(driver,1,"OpenTT3D: {} industry layer bindings retain their supplied source because the active climate has no matching authored volume",climate_fallbacks);
	if (VoxelIndustryState(10,SPR_IT_POWER_PLANT_TRANSFORMERS)) {
		unsigned spark_views = 0;
		const auto &parent = Models().models.at(Models().bindings.at({"industries",10,3})).surface;
		for (unsigned frame = 1; frame <= std::size(_coal_plant_sparks); ++frame) {
			const auto &spark = Models().models.at(Models().bindings.at({"infrastructure",SPR_IT_POWER_PLANT_TRANSFORMERS+frame,0})).surface;
			Vec3 low{std::min(parent.low.x,spark.low.x),std::min(parent.low.y,spark.low.y),std::min(parent.low.z,spark.low.z)};
			Vec3 high{std::max(parent.high.x,spark.high.x),std::max(parent.high.y,spark.high.y),std::max(parent.high.z,spark.high.z)};
			for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
				Textures().BeginScene();
				Scene actual, reference, isolated;
				DrawVoxelAsset(actual,"industries",10,3,{});
				if (!DrawVoxelIndustrySpark(actual,SPR_IT_POWER_PLANT_TRANSFORMERS+frame,{}) || actual.instances.size() != 2 || actual.instances.back().mesh != &spark.vertices) throw std::runtime_error("Power-station child did not select its exact spark mesh");
				for (auto &instance : actual.instances) instance.data.SetObjectId(TILE_PICK_ID|81);
				isolated.instances = {actual.instances.back()};
				reference.vertices = actual.ExpandedVertices(true);
				Camera camera{(low+high)*0.5f,2,256,256,turn+0.15f};
				if (street) camera = StreetReviewCamera(low,high,256,256,turn+0.15f);
				std::vector<uint8_t> pixels, expected;
				std::vector<uint32_t> ids, expected_ids;
				if (!RenderScene(isolated,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),TILE_PICK_ID|81) < 4) throw std::runtime_error("Power-station arc disappeared at a review angle");
				if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error("Power-station parent/spark comparison failed to render");
				if (pixels != expected || ids != expected_ids) {
					unsigned colours = 0, picks = 0;
					for (size_t i = 0; i < ids.size(); ++i) {
						colours += !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,expected.begin()+i*4);
						picks += ids[i] != expected_ids[i];
					}
					std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
					std::filesystem::create_directories(directory);
					for (bool cpu : {false,true}) {
						const auto &image = cpu ? expected : pixels;
						std::ofstream output(directory/fmt::format("model-power-spark-mismatch-{}-{}-{}-{}.pam",frame,turn,street,cpu ? "cpu" : "gpu"),std::ios::binary);
						output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
						for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(image.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
					}
					throw std::runtime_error(fmt::format("Power-station spark frame {} turn {} street {} differs from CPU instances: {} colour pixels, {} IDs",frame,turn,street,colours,picks));
				}
				for (auto &instance : actual.instances) instance.data.origin_opacity[3] = 0.38f;
				if (!RenderScene(actual,camera,pixels,&ids) || std::ranges::any_of(ids,[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent power-station spark intercepted picking");
				++spark_views;
			}
		}
		Debug(driver,1,"OpenTT3D: {} voxel power-station spark poses preserve exact child geometry, parent ownership and transparent picking",spark_views);
	}
}

void VerifyVoxelMeshes(std::string_view prefix)
{
	std::vector<uint8_t> pixels, expected;
	std::vector<uint32_t> ids, expected_ids;
	/* A copied scene pins CPU storage even after its original is destroyed.
	 * Once all pins are gone, retire and restore at the same GPU cache key. */
	const auto &catalogue = Models();
	auto cold = std::ranges::find_if(catalogue.models,[&](const auto &entry) {
		return entry.second.surface.occupied != 0 && !catalogue.surfaces.IsPinned(entry.second);
	});
	if (cold == catalogue.models.end()) throw std::runtime_error("No unused voxel source for CPU residency verification");
	const auto &retained = cold->second;
	for (unsigned view = 0; view < 4; ++view) {
		Textures().BeginScene();
		Scene scene;
		auto data = Material({},PALETTE_RECOLOUR_START,view&1U ? 0.38f : 1); data.SetObjectId(217);
		AddVoxelInstance(scene,retained,data);
		Camera camera = StreetReviewCamera(retained.surface.low,retained.surface.high,256,256,view+0.17f);
		if (!RenderScene(scene,camera,expected,&expected_ids)) throw std::runtime_error("CPU voxel residency reference did not render");
		auto copy = scene; scene = {};
		size_t vertices = copy.VertexCount();
		catalogue.surfaces.Trim(0);
		if (vertices == 0 || copy.VertexCount() != vertices) throw std::runtime_error("CPU voxel retirement invalidated a copied scene");
		copy = {};
		catalogue.surfaces.Trim(0);
		if (retained.surface.vertices.capacity() != 0) throw std::runtime_error("Unused CPU voxel storage was not released");
		AddVoxelInstance(scene,retained,data);
		if (scene.VertexCount() != vertices || !RenderScene(scene,camera,pixels,&ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Restored CPU voxel geometry changed exact colour, transparency or picking");
	}
	Debug(driver,1,"OpenTT3D: 4 CPU voxel retirement/rebuild views preserve scene pins, stable GPU keys, exact colour, transparency and picking");
	unsigned views = 0;
	unsigned bindings = 0;
	unsigned ground_bindings = 0;
	auto houses = GetTownDrawTileData();
	for (unsigned house = 0; house < houses.size()/16; ++house) for (unsigned variant = 0; variant < 4; ++variant) for (unsigned stage = 0; stage < 4; ++stage) {
		unsigned state = variant*4+stage;
		auto binding = Models().bindings.find({"houses",house,state});
		if (binding == Models().bindings.end() && houses[house*16+state].building.sprite == houses[house*16+stage].building.sprite) binding = Models().bindings.find({"houses",house,stage});
		if (binding == Models().bindings.end() || !binding->second.starts_with(prefix)) continue;
		SpriteTexture texture;
		texture.palette = houses[house*16+state].building.pal;
		Scene actual, reference;
		const auto &model = Models().models.at(binding->second).surface;
		if (!DrawAuthoredHouse(actual,house,stage,texture,{},{},1,4,variant) || actual.instances.size() != 1 || actual.instances[0].mesh != &model.vertices) throw std::runtime_error("House source variant selected the wrong voxel geometry");
		reference.instances.push_back({&model.vertices,Material({},texture.palette,1)});
		Camera camera{(model.low+model.high)*0.5f,1.4f,256,256,0.15f};
		if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("House variant lost its original source palette");
		++bindings;
	}
	Debug(driver,1,"OpenTT3D: {} house variant/construction bindings select their explicit geometry and original palettes",bindings);
	for (unsigned house = 0; house < houses.size()/16; ++house) for (unsigned variant = 0; variant < 4; ++variant) for (unsigned stage = 0; stage < 4; ++stage) {
		auto state = VoxelHouseGroundState(house,stage,variant);
		if (!state) continue;
		const auto &name = Models().bindings.at({"house_ground",house,*state});
		if (!name.starts_with(prefix)) continue;
		const auto &source = houses[house*16+variant*4+stage];
		const auto &model = Models().models.at(name).surface;
		Scene actual, reference;
		if (!DrawVoxelHouseGround(actual,house,stage,variant,source.ground.sprite,{},source.ground.pal) || actual.instances.size() != 1 || actual.instances[0].mesh != &model.vertices) throw std::runtime_error("House ground selected the wrong original state mesh");
		actual.instances[0].data.SetObjectId(TILE_PICK_ID|43);
		auto data = Material({},source.ground.pal,1); data.SetObjectId(TILE_PICK_ID|43);
		reference.instances.push_back({&model.vertices,data});
		Camera camera{(model.low+model.high)*0.5f,2,256,256,0.15f};
		if (!RenderScene(actual,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),TILE_PICK_ID|43) < 16 || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Opaque house ground lost its original palette or picking IDs");
		if (source.building.sprite == 0 && VoxelHouseState(house,stage,variant)) throw std::runtime_error("An original empty house body was replaced with geometry");
		if (auto body = VoxelHouseState(house,stage,variant)) {
			DrawVoxelAsset(actual,"houses",house,*body,{},source.building.pal,0.38f);
			actual.instances.back().data.SetObjectId(TILE_PICK_ID|44);
			if (!RenderScene(actual,camera,pixels,&ids) || ids != expected_ids) throw std::runtime_error("Transparent house stands intercepted the opaque ground's picking");
		}
		++ground_bindings;
	}
	Debug(driver,1,"OpenTT3D: {} voxel house-ground bindings preserve source palettes, empty body stages and opaque floor ownership",ground_bindings);
	static const VoxelMesh orientation = [] { VoxelGrid grid({4,4,4},{{{1,2,3,4,5,6}}}); grid.Fill({0,0,0},{4,4,4},1); return grid.Mesh(); }();
	for (unsigned turn = 0; turn < 4; ++turn) {
		Scene scene;
		auto data = Material({},PAL_NONE,1); data.SetObjectId(211);
		scene.instances.push_back({&orientation.vertices,data});
		Camera camera{{1,1,2},8,128,128,turn+0.3f};
		if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("Voxel winding reference failed");
		Vec3 eye = camera.Eye();
		auto palette = SnapshotPalette();
		std::array<unsigned,3> front{eye.x > 1 ? 2U : 1U,eye.y > 1 ? 4U : 3U,6U};
		unsigned visible = 0;
		for (size_t i = 0; i < ids.size(); ++i) if (ids[i] == 211) {
			bool matches = std::ranges::any_of(front,[&](unsigned index) { Colour c = palette.palette[index]; return pixels[i*4] == c.r && pixels[i*4+1] == c.g && pixels[i*4+2] == c.b; });
			if (!matches) throw std::runtime_error("Voxel winding exposed a rear-facing palette surface");
			++visible;
		}
		if (visible < 16) throw std::runtime_error("Voxel winding culled every visible surface");
	}
	for (const auto &[name,model] : Models().models) {
		if (!name.starts_with(prefix)) continue;
		auto lease = PinVoxelModel(model);
		const auto naive = model.source->Expand(Models().materials).Mesh(false);
		for (PaletteID palette : {PAL_NONE,PALETTE_TO_STRUCT_WHITE,PALETTE_TO_STRUCT_BROWN}) for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
			Textures().BeginScene();
			Scene merged, reference, expanded;
			reference.persistent_meshes = false;
			auto data = Material({},palette,1); data.SetObjectId(213);
			AddVoxelInstance(merged,model,data);
			reference.instances.push_back({&naive.vertices,data});
			expanded.vertices = merged.ExpandedVertices(true);
			Vec3 centre = (model.surface.low+model.surface.high)*0.5f;
			Vec3 extent = model.surface.high-model.surface.low;
			float longest = std::max({extent.x,extent.y,extent.z*Camera::WORLD_Z_SCALE});
			/* Small standalone fittings need an isolated close view rather than
			 * a subpixel orbit probe. Keep the lens and exact coverage threshold. */
			float scale = longest < 4 ? std::clamp(24.0f/std::max(0.125f,longest),1.4f,8.0f) : 1.4f;
			Camera camera{centre,scale,256,256,turn+0.15f};
			if (street) camera = StreetReviewCamera(model.surface.low,model.surface.high,256,256,turn+0.15f);
			if (!RenderScene(merged,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),213) < 16) throw std::runtime_error(fmt::format("Voxel {} palette {} turn {} street {} has insufficient review coverage",name,palette,turn,street));
			if (!RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error("Voxel unmerged reference failed");
			if (pixels != expected || ids != expected_ids) {
				size_t colours = 0, picks = 0;
				for (size_t i = 0; i < ids.size(); ++i) {
					picks += ids[i] != expected_ids[i];
					bool different = !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,expected.begin()+i*4);
					colours += different;
					if (different && colours <= 16) if (const auto *volume = FindVoxelVolume(&model.surface.vertices); volume != nullptr) {
						unsigned px = i%camera.width, py = camera.height-1-i/camera.width;
						auto ray = camera.ScreenRay(px+0.5f,py+0.5f);
						if (auto hit = volume->Trace(ray.origin,ray.direction)) Debug(driver,1,"OpenTT3D: voxel ray diagnostic pixel {},{} cell {},{},{} face {} colour {} distance {}",px,py,hit->cell[0],hit->cell[1],hit->cell[2],hit->face,hit->colour,hit->distance);
						else Debug(driver,1,"OpenTT3D: voxel ray diagnostic pixel {},{} misses the physical cells",px,py);
					}
				}
				std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
				std::filesystem::create_directories(directory);
				for (bool cells : {false,true}) {
					const auto &image = cells ? expected : pixels;
					std::ofstream output(directory/fmt::format("model-voxel-mismatch-{}-{}-{}-{}-{}.pam",name,palette,turn,street,cells ? "cells" : "merged"),std::ios::binary);
					output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
					for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(image.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
				}
				throw std::runtime_error(fmt::format("Voxel {} palette {} turn {} street {} greedy/reference mismatch: {} colour pixels, {} IDs",name,palette,turn,street,colours,picks));
			}
			if (!RenderScene(expanded,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Voxel instance material differs from CPU expansion");
			merged.instances[0].data.origin_opacity[3] = 0.38f;
			if (!RenderScene(merged,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),213) != 0) throw std::runtime_error("Transparent voxel model intercepted picking");
			++views;
		}
	}
	if (views == 0) throw std::runtime_error(fmt::format("No voxel models match verification prefix '{}'",prefix));
	/* A palette voxel must preserve the actual 8-bit colour, without projected
	 * sprite paint or an extra continuous lighting gradient. */
	static const VoxelMesh swatch = [] { VoxelGrid grid({4,4,4},{{{74,74,74,74,74,74}}}); grid.Fill({0,0,0},{4,4,4},1); return grid.Mesh(); }();
	for (unsigned relocation = 0; relocation < 3; ++relocation) {
		if (relocation != 0) Textures().Repack();
		Scene scene;
		auto data = Material({},PAL_NONE,1); data.SetObjectId(219);
		scene.instances.push_back({&swatch.vertices,data});
		Camera camera{{1,1,2},8,128,128,0.3f};
		if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("Voxel palette reference failed");
		Colour colour = SnapshotPalette().palette[74];
		unsigned coloured = 0;
		for (size_t i = 0; i < ids.size(); ++i) if (ids[i] == 219) {
			if (pixels[i*4] != colour.r || pixels[i*4+1] != colour.g || pixels[i*4+2] != colour.b) throw std::runtime_error("Voxel palette colour changed through lighting or atlas relocation");
			++coloured;
		}
		if (coloured < 16) throw std::runtime_error("Voxel palette reference has no visible surface");
	}
	Debug(driver,1,"OpenTT3D: {} authored voxel views match unmerged geometry, CPU instances, palette recolouring and transparent picking; exact palette relocation passed",views);
	unsigned joined_views = 0;
	for (unsigned house = 0; house < houses.size()/16; ++house) {
		auto offsets = HouseReviewOffsets(house);
		if (offsets.empty()) continue;
		for (unsigned stage = 0; stage < 4; ++stage) {
			std::map<std::string,VoxelMesh> individual_faces;
			Scene joined, reference;
			reference.persistent_meshes = false;
			bool selected = false;
			unsigned parts = 0;
			Vec3 low{INFINITY,INFINITY,INFINITY}, high{-INFINITY,-INFINITY,-INFINITY};
			for (unsigned part = 0; part < offsets.size(); ++part) {
				auto body = VoxelHouseState(house+part,stage,0), floor = VoxelHouseGroundState(house+part,stage,0);
				const auto &source = houses[(house+part)*16+stage];
				if ((!body && !floor) || (!body && source.building.sprite != 0)) break;
				for (bool ground : {true,false}) if (auto state = ground ? floor : body) {
					const auto &name = Models().bindings.at({ground ? "house_ground" : "houses",house+part,*state});
					selected |= name.starts_with(prefix);
					const auto &model = Models().models.at(name);
					const auto &mesh = model.surface;
					/* Include every adjoining layer even outside the selected prefix. */
					auto [naive,inserted] = individual_faces.try_emplace(name);
					if (inserted) naive->second = model.source->Expand(Models().materials).Mesh(false);
					auto data = Material(offsets[part],ground ? source.ground.pal : source.building.pal,1);
					data.SetObjectId(TILE_PICK_ID | (31+part));
					AddVoxelInstance(joined,model,data);
					reference.instances.push_back({&naive->second.vertices,data});
					Vec3 a = offsets[part]+mesh.low, b = offsets[part]+mesh.high;
					low = {std::min(low.x,a.x),std::min(low.y,a.y),std::min(low.z,a.z)};
					high = {std::max(high.x,b.x),std::max(high.y,b.y),std::max(high.z,b.z)};
				}
				++parts;
			}
			if (!selected || parts != offsets.size()) continue;
			for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
				Camera camera{(low+high)*0.5f,2,320,320,turn+0.15f};
				if (street) camera = StreetReviewCamera(low,high,320,320,turn+0.15f);
				if (!RenderScene(joined,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error("Joined voxel house comparison could not render");
				if (pixels != expected || ids != expected_ids) {
					auto directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
					std::filesystem::create_directories(directory);
					for (bool cells : {false,true}) {
						std::ofstream output(directory/fmt::format("model-joined-house-mismatch-{}-{}-{}-{}-{}.pam",house,stage,turn,street,cells ? "cells" : "merged"),std::ios::binary);
						output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
						const auto &image = cells ? expected : pixels;
						for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(image.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
					}
					size_t mismatch = 0;
					while (mismatch < ids.size() && std::equal(pixels.begin()+mismatch*4,pixels.begin()+mismatch*4+4,expected.begin()+mismatch*4) && ids[mismatch] == expected_ids[mismatch]) ++mismatch;
					throw std::runtime_error(fmt::format("Joined voxel house {} stage {} turn {} street {} changed colour or tile ownership at pixel {},{} (IDs {} / {})",house,stage,turn,street,mismatch%camera.width,camera.height-1-mismatch/camera.width,ids[mismatch],expected_ids[mismatch]));
				}
				Scene expanded;
				expanded.vertices = joined.ExpandedVertices(true);
				if (!RenderScene(expanded,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Joined voxel house lost per-tile ownership in CPU expansion");
				++joined_views;
			}
		}
	}
	Debug(driver,1,"OpenTT3D: {} joined multi-tile house views preserve exact cell references and independent tile picking",joined_views);
	unsigned airport_views = 0, airport_climate_fallbacks = 0;
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,graphics,state] = binding;
		if ((category != "airport_tiles" && category != "airport_ground") || !name.starts_with(prefix)) continue;
		unsigned frame = state%16;
		if (category == "airport_ground" && state != VoxelAirportGroundState(graphics,frame)) continue;
		if (AirportModelClimateSupported(graphics,to_underlying(_settings_game.game_creation.landscape))) continue;
		Scene fallback;
		if (HasVoxelAirport(graphics,frame) || DrawVoxelAirportGround(fallback,graphics,frame,{},PAL_NONE) || !fallback.instances.empty()) throw std::runtime_error("Unauthored airport climate selected a different climate's ground/body");
		++airport_climate_fallbacks;
	}
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,graphics,state] = binding;
		unsigned frame = state%16;
		if (category != "airport_ground" || state != VoxelAirportGroundState(graphics,frame) || !HasVoxelAirport(graphics,frame)) continue;
		auto body_binding = Models().bindings.find({"airport_tiles",graphics,frame});
		bool has_body = body_binding != Models().bindings.end();
		if (!name.starts_with(prefix) && (!has_body || !body_binding->second.starts_with(prefix))) continue;
		const auto &floor = Models().models.at(name).surface;
		const auto &body = has_body ? Models().models.at(body_binding->second).surface : floor;
		if (has_body == GetAirportTileLayouts(graphics)[frame]->GetSequence().empty()) throw std::runtime_error("Airport body ownership disagrees with the original empty sequence");
		Vec3 low{std::min(body.low.x,floor.low.x),std::min(body.low.y,floor.low.y),std::min(body.low.z,floor.low.z)};
		Vec3 high{std::max(body.high.x,floor.high.x),std::max(body.high.y,floor.high.y),std::max(body.high.z,floor.high.z)};
		for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) for (unsigned visibility = 0; visibility < 3; ++visibility) {
			Textures().BeginScene();
			Scene actual, reference;
			if (!DrawVoxelAirportGround(actual,graphics,frame,{},PAL_NONE) || actual.instances.size() != 1 || actual.instances.front().mesh != &floor.vertices) throw std::runtime_error("Airport lost its independent original ground binding");
			actual.instances.front().data.SetObjectId(TILE_PICK_ID|81);
			if (visibility != 2 && has_body) {
				if (!DrawVoxelAsset(actual,"airport_tiles",graphics,frame,{},PALETTE_TO_BLUE,visibility == 1 ? 0.38f : 1)) throw std::runtime_error("Airport lost its original body binding");
				actual.instances.back().data.SetObjectId(TILE_PICK_ID|82);
			}
			reference.vertices = actual.ExpandedVertices(true);
			Camera camera{(low+high)*0.5f,2,256,256,turn+0.15f};
			if (street) camera = StreetReviewCamera(low,high,256,256,turn+0.15f);
			if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Airport ground/body visibility changed exact CPU colour or ownership");
			if (std::count(ids.begin(),ids.end(),TILE_PICK_ID|81) < 8 || (visibility != 0 && std::ranges::find(ids,TILE_PICK_ID|82) != ids.end())) throw std::runtime_error("Airport transparency hid its opaque ground or intercepted picking");
			++airport_views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} voxel airport ground/body views preserve independent opaque ground, exact CPU colour and visible/transparent/hidden picking",airport_views);
	Debug(driver,1,"OpenTT3D: {} airport layer bindings retain their supplied source because the active climate has no matching authored volume",airport_climate_fallbacks);
	Debug(driver,1,"OpenTT3D: voxel mesh selection '{}' passed exact geometry, palettes and picking",prefix);
}

void VerifyVoxelModels(bool vehicle_poses)
{
	VerifyVoxelMeshes();
	std::vector<uint8_t> pixels, expected;
	std::vector<uint32_t> ids, expected_ids;
	if (vehicle_poses) VerifyVoxelVehicleModels();
	else Debug(driver,1,"OpenTT3D: scene-only voxel verification delegates complete vehicle pose matrices to explicit engine shards");
	unsigned lift_views = 0;
	for (unsigned position = 0; position <= 36; ++position) {
		size_t visible = 0;
		for (unsigned turn = 0; turn < 4; ++turn) {
			Scene actual, reference;
			DrawVoxelAsset(actual,"houses",4,3,{});
			size_t first = actual.instances.size();
			if (!DrawVoxelHouseLift(actual,{},position) || actual.instances.size() != first+1) throw std::runtime_error("Missing voxel office lift");
			auto &lift = actual.instances.back();
			if (lift.data.origin_opacity[2] != 3.5f+position) throw std::runtime_error("Voxel lift changed the upstream height step");
			lift.data.SetObjectId(227);
			reference.vertices = actual.ExpandedVertices(true);
			Camera camera{{8,8,26},3,256,256,turn+0.15f};
			if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Voxel lift/body instance agreement failed");
			visible += std::count(ids.begin(),ids.end(),227);
			++lift_views;
		}
		if (visible < 8) throw std::runtime_error("Voxel lift is buried in the office facade");
	}
	Debug(driver,1,"OpenTT3D: {} office lift poses preserve all 37 upstream positions, facade clearance and exact instance/picking agreement",lift_views);
	VerifyVoxelTreeModels();
	VerifyVoxelIndustryModels();
}

void VerifyVoxelVehicleModels(unsigned only_engine)
{
	std::vector<uint8_t> pixels, expected;
	std::vector<uint32_t> ids, expected_ids;
	unsigned vehicle_views = 0, bindings_checked = 0;
	std::array<PaletteID,17> vehicle_palettes{};
	for (unsigned company = 0; company < 16; ++company) vehicle_palettes[company] = PALETTE_RECOLOUR_START+company;
	vehicle_palettes.back() = PALETTE_CRASH;
	const auto original_palette = SnapshotPalette();
	for (const auto &[binding,name] : Models().bindings) {
		const auto &[category,engine,state] = binding;
		if (category != "vehicles" || (only_engine != UINT_MAX && engine != only_engine)) continue;
		bool loaded = (state&1U) != 0;
		unsigned climate = state/2;
		if (state >= 8 || VoxelVehicleState(engine,loaded,climate) != state) throw std::runtime_error("Vehicle climate/cargo binding cannot be selected");
		auto lease = PinVoxelModel(Models().models.at(name));
		const auto &mesh = Models().models.at(name).surface;
		if (engine < 116) for (const auto &vertex : mesh.vertices) {
			/* Use the actual faceted lining and inward ribs, not its bounding box
			 * or a smooth ellipse that admits clipping at facet boundaries. */
			float roof = TunnelRoofHeight(TunnelKind::Rail,8+vertex.position.y)-0.08f;
			if (vertex.position.z > roof) throw std::runtime_error(fmt::format("Train {} binding {} body {} exceeds the original tunnel loading gauge",engine,state,name));
		}
		++bindings_checked;
		for (PaletteID palette : vehicle_palettes) for (unsigned pose = 0; pose < 16; ++pose) for (bool street : {false,true}) {
			float heading = pose*std::numbers::pi_v<float>/8+0.07f;
			Scene actual, reference, expanded;
			/* Exercise the normal capture path for the active family. Other declared
			 * climates use an explicit read-only selection, never game-setting writes. */
			bool drawn = VoxelVehicleState(engine,loaded) == state ? DrawAuthoredVehicle(actual,engine,loaded,{},heading,palette,1) :
				DrawVoxelVehicle(actual,engine,loaded,{},heading,palette,1,climate);
			if (!drawn || actual.instances.size() != 1 || actual.instances[0].mesh != &mesh.vertices) throw std::runtime_error("Vehicle did not select its explicit climate/cargo voxel binding");
			auto material = Material({},palette,1); material.mirror_layer_heading[3] = heading;
			if (engine < 116) material.SetLongitudinalScale(OriginalTrainVoxelScale(heading,mesh.high.x-mesh.low.x));
			material.SetObjectId(engine+1);
			actual.instances[0].data.SetObjectId(engine+1);
			reference.instances.push_back({&mesh.vertices,material});
			expanded.vertices = actual.ExpandedVertices(true);
			/* Independent colour oracle: apply the original recolour table directly
			 * to authored face indices, bypassing palette strips and atlas sampling. */
			Scene source_colours;
			source_colours.vertices = reference.ExpandedVertices(true);
			const uint8_t *mapping = GetNonSprite(palette,SpriteType::Recolour)+1;
			for (size_t i = 0; i < mesh.vertices.size(); ++i) {
				unsigned index = static_cast<unsigned>(mesh.vertices[i].texture.x*256);
				unsigned mapped = mapping[index];
				Colour colour = original_palette.palette[mapped];
				auto &vertex = source_colours.vertices[i];
				vertex.colour = {colour.r/255.0f,colour.g/255.0f,colour.b/255.0f};
				vertex.texture = {0,0,-1};
				vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT);
				vertex.opacity = mapped == 0 ? 0 : 1;
			}
			Camera camera{(mesh.low+mesh.high)*0.5f,2,256,256,0.17f};
			if (street) camera = StreetReviewCamera(mesh.low,mesh.high,256,256,0.17f);
			if (!RenderScene(actual,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),engine+1) < 16 || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Voxel vehicle pose lost source livery or object ownership");
			if (!RenderScene(expanded,camera,expected,&expected_ids)) throw std::runtime_error("Voxel vehicle CPU instance reference failed to render");
			if (pixels != expected || ids != expected_ids) {
				unsigned colours = 0, picks = 0;
				for (size_t i = 0; i < ids.size(); ++i) {
					colours += !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,expected.begin()+i*4);
					picks += ids[i] != expected_ids[i];
				}
				std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
				std::filesystem::create_directories(directory);
				for (bool cpu : {false,true}) {
					const auto &image = cpu ? expected : pixels;
					std::ofstream output(directory/fmt::format("model-vehicle-mismatch-{}-{}-{}-{}-{}-{}.pam",engine,state,palette,pose,street,cpu ? "cpu" : "gpu"),std::ios::binary);
					output << "P7\nWIDTH " << camera.width << "\nHEIGHT " << camera.height << "\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
					for (int y = camera.height-1; y >= 0; --y) output.write(reinterpret_cast<const char *>(image.data()+static_cast<size_t>(y)*camera.width*4),camera.width*4);
				}
				throw std::runtime_error(fmt::format("Voxel vehicle {} model {} binding {} palette {} pose {} street {} differs from CPU instance reference: {} colour pixels, {} IDs",engine,name,state,palette,pose,street,colours,picks));
			}
			if (!RenderScene(source_colours,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Voxel vehicle differs from the original company/crash palette table");
			actual.instances[0].data.origin_opacity[3] = 0.38f;
			if (!RenderScene(actual,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),engine+1) != 0) throw std::runtime_error("Transparent voxel vehicle intercepted picking");
			++vehicle_views;
		}
		if (engine < 116) {
			unsigned pitched_views = 0;
			auto unit_mesh = Models().models.at(name).source->Expand(Models().materials).Mesh(false);
			for (float grade : {-TerrainZ(0.5f),-TerrainZ(0.25f),TerrainZ(0.25f),TerrainZ(0.5f)}) for (unsigned pose = 0; pose < 8; ++pose) for (bool street : {false,true}) for (PaletteID palette : {PAL_NONE,PALETTE_RECOLOUR_START,PALETTE_CRASH}) {
				Scene actual, reference, cells;
				float heading = pose*std::numbers::pi_v<float>/4+0.07f;
				DrawVoxelVehicle(actual,engine,loaded,{},heading,palette,1,climate,grade);
				auto &instance = actual.instances.front().data;
				instance.SetObjectId(engine+1);
				reference.vertices = actual.ExpandedVertices(true);
				cells.persistent_meshes = false;
				cells.instances.push_back({&unit_mesh.vertices,instance});
				Camera camera{{0,0,4},2,256,256,0.17f};
				if (street) camera = StreetReviewCamera({-9,-3,-3},{9,3,11},256,256,0.17f);
				if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error(fmt::format("Pitched train {} binding {} grade {} pose {} street {} differs from exact CPU geometry",engine,state,grade,pose,street));
				if (!RenderScene(cells,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error(fmt::format("Pitched train {} binding {} grade {} pose {} street {} differs from unit-cell geometry",engine,state,grade,pose,street));
				if (std::count(ids.begin(),ids.end(),engine+1) < 16) throw std::runtime_error("Pitched train disappeared or lost picking ownership");
				++pitched_views;
			}
			Debug(driver,1,"OpenTT3D: train engine {} binding {} passed {} pitched support-plane poses with exact colour and picking",engine,state,pitched_views);
		}
		if (engine >= 23 && engine <= 26 && !loaded) {
			unsigned collector_views = 0, parts = engine <= 24 ? 2 : 1;
			for (auto heights : {std::array{10.0f,10.0f},std::array{8.8f,8.8f},std::array{7.55f,7.55f},std::array{10.0f,7.55f},std::array{7.55f,10.0f}}) {
				for (unsigned pose = 0; pose < 16; ++pose) for (bool street : {false,true}) for (PaletteID palette : vehicle_palettes) {
					Scene actual, reference;
					float heading = pose*std::numbers::pi_v<float>/8+0.07f;
					DrawVoxelVehicle(actual,engine,false,{},heading,palette,1,climate);
					if (DrawVoxelTrainCollectors(actual,engine,{},heading,palette,heights) != parts || actual.instances.size() != parts+1) throw std::runtime_error("Electric train lost an independent roof collector");
					for (unsigned part = 0; part < parts; ++part) {
						const auto &instance = actual.instances[part+1];
						const auto &frame = Models().models.at(Models().bindings.at({"vehicle_collectors",engine,part})).surface;
						float low = INFINITY,high = -INFINITY;
						for (const auto &vertex : *instance.mesh) {
							float z = ResolveInstanceVertex(vertex,instance.data).position.z;
							low = std::min(low,z); high = std::max(high,z);
							if (heights[part] == 7.55f && z > TunnelRoofHeight(TunnelKind::ElectricRail,8+vertex.position.y)-0.08f) throw std::runtime_error("Lowered collector intersects the actual tunnel lining ribs");
						}
						if (std::abs(low-frame.low.z) > 0.00001f || std::abs(high-heights[part]) > 0.00001f) throw std::runtime_error("Collector moved its roof mounting or missed its own wire height");
					}
					for (auto &instance : actual.instances) instance.data.SetObjectId(engine+1);
					reference.vertices = actual.ExpandedVertices(true);
					Camera camera{{0,0,5},2,256,256,0.17f}; camera.vertical_fov = 40;
					if (street) camera = StreetReviewCamera({-8,-2,0},{8,2,11},256,256,0.17f);
					if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error(fmt::format("Electric train {} collector pose {} heights {},{} street {} differs from CPU instances",engine,pose,heights[0],heights[1],street));
					if (std::count(ids.begin(),ids.end(),engine+1) < 16 || std::ranges::any_of(ids,[&](uint32_t id) { return id != 0 && id != engine+1; })) throw std::runtime_error("Electric collector lost its original vehicle's picking ownership");
					for (auto &instance : actual.instances) instance.data.origin_opacity[3] = 0.38f;
					if (!RenderScene(actual,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),engine+1) != 0) throw std::runtime_error("Transparent electric collector intercepted picking");
					++collector_views;
				}
			}
			Debug(driver,1,"OpenTT3D: voxel train engine {} passed {} joined collector poses with fixed roof mounts, independent wire heights, company/crash palettes and original picking ownership",engine,collector_views);
			unsigned pitched_collectors = 0;
			for (float grade : {-TerrainZ(0.5f),TerrainZ(0.5f)}) for (unsigned pose = 0; pose < 8; ++pose) for (bool street : {false,true}) {
				Scene actual, reference;
				float heading = pose*std::numbers::pi_v<float>/4+0.07f;
				DrawVoxelVehicle(actual,engine,false,{},heading,PALETTE_RECOLOUR_START,1,climate,grade);
				std::array<float,2> heights{9,11};
				if (DrawVoxelTrainCollectors(actual,engine,{},heading,PALETTE_RECOLOUR_START,heights,grade) != parts) throw std::runtime_error("Pitched electric train lost its collectors");
				for (unsigned part = 0; part < parts; ++part) {
					const auto &frame = Models().models.at(Models().bindings.at({"vehicle_collectors",engine,part})).surface;
					const auto &instance = actual.instances[part+1];
					for (const auto &vertex : frame.vertices) if (vertex.position.z == frame.low.z) {
						Vec3 a = ResolveInstanceVertex(vertex,actual.instances[0].data).position, b = ResolveInstanceVertex(vertex,instance.data).position;
						if (Dot(a-b,a-b) > 1e-8f) throw std::runtime_error("Pitched collector detached from its original roof mount");
					}
					Vertex shoe{}; shoe.position = CollectorContactCentre(frame); shoe.normal = {0,0,1};
					if (std::abs(ResolveInstanceVertex(shoe,instance.data).position.z-heights[part]) > 0.00001f) throw std::runtime_error("Pitched collector missed its independent wire contact");
				}
				for (auto &instance : actual.instances) instance.data.SetObjectId(engine+1);
				reference.vertices = actual.ExpandedVertices(true);
				Camera camera{{0,0,5},2,256,256,0.17f};
				if (street) camera = StreetReviewCamera({-9,-3,-3},{9,3,13},256,256,0.17f);
				if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("Pitched collector and body differ from exact CPU placement");
				++pitched_collectors;
			}
			Debug(driver,1,"OpenTT3D: train engine {} passed {} pitched collector poses with attached mounts and independent wire contacts",engine,pitched_collectors);
		}
		if (engine >= 253 && engine <= 255 && !loaded) {
			unsigned rotor_views = 0;
			Scene invalid;
			if (DrawVoxelHelicopterRotor(invalid,SPR_ROTOR_STOPPED-1,{}) || DrawVoxelHelicopterRotor(invalid,SPR_ROTOR_MOVING_3+1,{}) || !invalid.instances.empty()) throw std::runtime_error("Unrelated sprite selected helicopter rotor geometry");
			for (unsigned rotor = 0; rotor < 4; ++rotor) for (unsigned pose = 0; pose < 8; ++pose) for (bool street : {false,true}) for (PaletteID palette : {PALETTE_RECOLOUR_START,PALETTE_CRASH}) {
				Scene actual, reference, isolated;
				float heading = pose*std::numbers::pi_v<float>/4+0.07f;
				DrawVoxelVehicle(actual,engine,false,{},heading,palette,1,climate);
				actual.instances.front().data.SetObjectId(engine+1);
				const auto &rotor_mesh = Models().models.at(Models().bindings.at({"infrastructure",SPR_ROTOR_STOPPED,rotor})).surface;
				if (!DrawVoxelHelicopterRotor(actual,SPR_ROTOR_STOPPED+rotor,{0,0,ROTOR_Z_OFFSET},palette) || actual.instances.size() != 2 || actual.instances.back().mesh != &rotor_mesh.vertices || actual.instances.back().data.mirror_layer_heading[3] != 0) throw std::runtime_error("Helicopter rotor lost independent source-state selection or fixed world-space orientation");
				reference.vertices = actual.ExpandedVertices(true);
				isolated.instances = {actual.instances.back()};
				isolated.instances.front().data.SetObjectId(engine+1);
				Camera camera{{0,0,3},3,256,256,pose*0.5f+0.17f};
				camera.vertical_fov = 40;
				if (street) camera = StreetReviewCamera({-9,-9,0},{9,9,6},256,256,pose*0.5f+0.17f);
				if (!RenderScene(isolated,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),engine+1) < 4) throw std::runtime_error("Voxel helicopter rotor disappeared from an all-angle review");
				if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error(fmt::format("Voxel helicopter {} rotor {} pose {} street {} differs from independent CPU placement",engine,rotor,pose,street));
				if (std::count(ids.begin(),ids.end(),engine+1) < 8 || std::ranges::any_of(ids,[&](uint32_t id) { return id != 0 && id != engine+1; })) throw std::runtime_error("Voxel helicopter rotor changed unclickable ownership");
				++rotor_views;
			}
			Debug(driver,1,"OpenTT3D: voxel helicopter engine {} passed {} joined rotor poses with original attachment, fixed-world animation, company/crash palettes and unclickable ownership",engine,rotor_views);
		}
	}
	if ((only_engine != UINT_MAX && bindings_checked == 0) || bindings_checked%2 != 0 || vehicle_views != bindings_checked*544) throw std::runtime_error("Requested voxel vehicles do not have complete climate/cargo pose matrices");
	Debug(driver,1,"OpenTT3D: {} voxel vehicle poses preserve all 16 company palettes and the original crash recolour, cargo bindings, continuous heading and exact source-colour/instance/picking agreement",vehicle_views);
	Debug(driver,1,"OpenTT3D: {} declared vehicle climate/cargo bindings passed without changing game climate",bindings_checked);
	if (only_engine != UINT_MAX) Debug(driver,1,"OpenTT3D: voxel vehicle engine {} pose matrix passed",only_engine);
}
} // namespace Renderer3D
