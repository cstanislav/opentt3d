/* SPDX-License-Identifier: GPL-2.0-only */
/** @file reference_export.cpp Reproducible artwork references from the active base set. */

#include "../stdafx.h"
#include "sprite_textures.hpp"
#include "authored_geometry.h"
#include "voxel_models.h"
#include "bridge_capture.h"
#include "world_capture.h"
#include "tunnel_capture.h"
#include "rail_capture.h"
#include "station_capture.h"
#include "ground_detail_capture.h"
#include "rail_detail_capture.h"
#include "depot_capture.h"
#include "crossing_capture.h"
#include "road_stop_capture.h"
#include "material_chart.hpp"
#include "indexed_mesh.hpp"
#include "../tunnelbridge_map.h"
#include "vulkan_backend.h"
#include "gl_backend.hpp"
#include "../town.h"
#include "../sprite.h"
#include "../spritecache.h"
#include "../house.h"
#include "../strings_func.h"
#include "../fileio_func.h"
#include "../3rdparty/nlohmann/json.hpp"
#include "../debug.h"
#include "../table/tree_land.h"
#include "../table/sprites.h"
#include "../industry.h"
#include "../industrytype.h"
#include "../palette_func.h"
#include "../bridge.h"
#include "../table/industry_land.h"
#include "../table/clear_land.h"
#include "../landscape.h"
#include "../rail.h"
#include "../road.h"
#include "../road_cmd.h"
#include "../table/track_land.h"
#include "../water_map.h"
#include "../table/water_land.h"
#include "../table/airporttile_ids.h"
#include "../station_func.h"
#include "../station_map.h"
#include "../newgrf_canal.h"
#include "../vehicle_base.h"
#include <set>
#include <filesystem>
#include <fstream>

namespace Renderer3D {

void ExportHouseReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	auto data = GetTownDrawTileData();
	nlohmann::json manifest = nlohmann::json::array();
	std::map<std::pair<SpriteID,PaletteID>,std::vector<uint8_t>> grounds;
	for (size_t house = 0; house < data.size() / 16; ++house) {
		for (size_t variant = 0; variant < 4; ++variant) {
			for (size_t stage = 0; stage < 4; ++stage) {
				const auto &drawing = data[house * 16 + variant * 4 + stage];
				auto filename = fmt::format("house-{:03}-{}-{}.pam", house, variant, stage);
				std::vector<uint8_t> palette_indices;
				if (drawing.building.sprite != 0) ExportSpriteReference(drawing.building.sprite, drawing.building.pal, (directory / filename).string(),&palette_indices);
				manifest.push_back({{"house", house}, {"variant", variant}, {"stage", stage},
					{"name", GetString(HouseSpec::Get(house)->building_name)}, {"sprite", drawing.building.sprite},
					{"palette", drawing.building.pal}, {"palette_indices",palette_indices}, {"image", drawing.building.sprite != 0 ? filename : ""},
					{"origin", {drawing.origin.x, drawing.origin.y, drawing.origin.z}},
					{"extent", {drawing.extent.x, drawing.extent.y, drawing.extent.z}}, {"procedure",drawing.draw_proc}});
				if (drawing.building.sprite != 0) {
					const Sprite *sprite = GetSprite(drawing.building.sprite & SPRITE_MASK,SpriteType::Normal);
					manifest.back()["sprite_offset"] = {sprite->x_offs,sprite->y_offs};
					manifest.back()["sprite_size"] = {sprite->width,sprite->height};
				}
				SpriteID ground = drawing.ground.sprite&SPRITE_MASK;
				auto ground_name = fmt::format("house-ground-{}-{}.pam",ground,drawing.ground.pal);
				manifest.back()["ground_sprite"] = ground;
				manifest.back()["ground_palette"] = drawing.ground.pal;
				manifest.back()["ground_image"] = ground != 0 ? ground_name : "";
				if (ground != 0) {
					auto [entry,inserted] = grounds.try_emplace({ground,drawing.ground.pal});
					if (inserted) ExportSpriteReference(ground,drawing.ground.pal,(directory/ground_name).string(),&entry->second);
					manifest.back()["ground_palette_indices"] = entry->second;
					const Sprite *sprite = GetSprite(ground,SpriteType::Normal);
					manifest.back()["ground_sprite_offset"] = {sprite->x_offs,sprite->y_offs};
					manifest.back()["ground_sprite_size"] = {sprite->width,sprite->height};
				}
			}
		}
	}
	std::ofstream(directory / "houses.json") << manifest.dump(2) << '\n';
	ExportSpriteReference(SPR_LIFT,PAL_NONE,(directory/"house-lift.pam").string());
	const Sprite *lift = GetSprite(SPR_LIFT,SpriteType::Normal);
	std::ofstream(directory/"house-parts.json") << nlohmann::json{{"lift",{{"sprite",SPR_LIFT},{"image","house-lift.pam"},
		{"sprite_offset",{lift->x_offs,lift->y_offs}},{"sprite_size",{lift->width,lift->height}},
		{"screen_offset",{14,60}},{"positions",37}}}}.dump(2) << '\n';
	std::set<std::pair<SpriteID,PaletteID>> trees;
	for (const auto &row : _tree_layout_sprite) for (const auto &sprite : row) trees.emplace(sprite.sprite,sprite.pal);
	nlohmann::json tree_manifest=nlohmann::json::array();
	for (auto [base,palette] : trees) {
		for (unsigned stage=0;stage<7;++stage) {
			auto filename=fmt::format("tree-{}-{}-{}.pam",base,palette,stage);
			std::vector<uint8_t> palette_indices;
			ExportSpriteReference(base+stage,palette,(directory/filename).string(),&palette_indices);
			const Sprite *sprite = GetSprite(base+stage,SpriteType::Normal);
			tree_manifest.push_back({{"base",base},{"palette",palette},{"stage",stage},{"image",filename},
				{"palette_indices",palette_indices},{"sprite_offset",{sprite->x_offs,sprite->y_offs}},{"sprite_size",{sprite->width,sprite->height}}});
		}
	}
	std::ofstream(directory/"trees.json") << tree_manifest.dump(2) << '\n';
	Debug(driver, 1, "OpenTT3D: exported {} house-state references to {}", manifest.size(), directory.string());
}

void ExportHouseModelGallery(unsigned house, bool industry)
{
	auto data=GetTownDrawTileData();
	bool tree=!industry && house>=1576 && house<=2009;
	if (industry ? house >= std::size(_industry_draw_tile_data) / 4 : !tree && house>=data.size()/16) return;
	DrawBuildingsTileStruct drawing{};
	if (industry) drawing = _industry_draw_tile_data[house * 4 + 3];
	else if (tree) drawing.building={house,PAL_NONE}; else drawing=data[house*16+3];
	if (drawing.building.sprite==0) return;
	if (industry && !HasAuthoredIndustry(house, drawing.building.sprite)) throw std::runtime_error("Industry gallery has no authored model for this state");
	std::filesystem::path directory=std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned rotation=0;rotation<4;++rotation) {
		Textures().BeginScene();
		unsigned tree_stage = tree ? (house - 1576) % 7 : 0;
		SpriteTexture texture = Textures().Get(drawing.building.sprite, drawing.building.pal, 0, !tree || (tree_stage != 4 && tree_stage != 5 && !TreeHasComponentMaterials(house)));
		if (rotation==0) Debug(driver,1,"OpenTT3D: house {} reference offset {},{} dimensions {},{}",house,texture.x_offset,texture.y_offset,texture.source_width,texture.source_height);
		Scene scene;
		Vec3 sprite_origin{static_cast<float>(drawing.origin.x+drawing.offset.x),static_cast<float>(drawing.origin.y+drawing.offset.y),static_cast<float>(drawing.origin.z+drawing.offset.z)};
		if (industry) DrawAuthoredIndustry(scene, house, drawing.building.sprite, texture, {}, sprite_origin, 1);
		else if (tree) DrawAuthoredTree(scene,house,texture,{},1); else DrawAuthoredHouse(scene,house,3,texture,{},sprite_origin,1);
		auto expanded = scene.ExpandedVertices();
		float height=1;
		Vec3 low{1e9f,1e9f,1e9f},high{-1e9f,-1e9f,-1e9f};
		for (const Vertex &v:expanded) {
			low={std::min(low.x,v.position.x),std::min(low.y,v.position.y),std::min(low.z,v.position.z)};
			high={std::max(high.x,v.position.x),std::max(high.y,v.position.y),std::max(high.z,v.position.z)};
		}
		for (const Vertex &v : expanded) height=std::max(height,v.position.z);
		Camera camera{(low+high)*0.5f,std::min(5.0f,320.0f/(height+32)),640,640,static_cast<float>(rotation)};
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Gallery GPU rendering failed");
		std::ofstream file(directory/fmt::format("model-{}{:03}-{}.pam",industry ? "industry-" : "",house,rotation),std::ios::binary);
		file << "P7\nWIDTH 640\nHEIGHT 640\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y=639;y>=0;--y) file.write(reinterpret_cast<const char *>(pixels.data()+y*640*4),640*4);
	}
	Debug(driver,1,"OpenTT3D: exported four model-review views for {} {}",industry ? "industry" : "house",house);
}

void ExportIndustryReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	std::map<std::pair<SpriteID,PaletteID>,nlohmann::json> ground_references;
	for (size_t i = 0; i < std::size(_industry_draw_tile_data); ++i) {
		const auto &drawing = _industry_draw_tile_data[i];
		auto name = fmt::format("industry-{:03}-{}.pam", i / 4, i % 4);
		std::vector<uint8_t> palette_indices;
		if (drawing.building.sprite != 0) ExportSpriteReference(drawing.building.sprite,drawing.building.pal,(directory/name).string(),&palette_indices);
		manifest.push_back({{"graphics", i / 4}, {"stage", i % 4}, {"sprite", drawing.building.sprite}, {"palette", drawing.building.pal},
			{"state_kind",GetIndustryTileSpec(i/4)->anim_state ? "animation" : "construction"},
			{"image", drawing.building.sprite != 0 ? name : ""}, {"procedure", drawing.draw_proc},
			{"origin", {drawing.origin.x, drawing.origin.y, drawing.origin.z}}, {"extent", {drawing.extent.x, drawing.extent.y, drawing.extent.z}},
			{"palette_indices",palette_indices}});
		if (drawing.building.sprite != 0) {
			const Sprite *source = GetSprite(drawing.building.sprite&SPRITE_MASK,SpriteType::Normal);
			manifest.back()["sprite_offset"] = {source->x_offs,source->y_offs};
			manifest.back()["sprite_size"] = {source->width,source->height};
		}
		auto key = std::pair{drawing.ground.sprite,drawing.ground.pal};
		auto found = ground_references.find(key);
		if (found == ground_references.end()) {
			auto ground_name = fmt::format("industry-ground-{}-{}.pam",key.first&SPRITE_MASK,key.second);
			std::vector<uint8_t> indices;
			nlohmann::json ground{{"ground_sprite",key.first},{"ground_palette",key.second},{"ground_image",""}};
			if ((key.first&SPRITE_MASK) != 0) {
				ExportSpriteReference(key.first,key.second,(directory/ground_name).string(),&indices);
				const Sprite *source = GetSprite(key.first&SPRITE_MASK,SpriteType::Normal);
				ground["ground_image"] = ground_name;
				ground["ground_sprite_offset"] = {source->x_offs,source->y_offs};
				ground["ground_sprite_size"] = {source->width,source->height};
			}
			ground["ground_palette_indices"] = indices;
			found = ground_references.emplace(key,std::move(ground)).first;
		}
		manifest.back().update(found->second);
	}
	std::ofstream(directory / "industries.json") << manifest.dump(2) << '\n';
	nlohmann::json effects = nlohmann::json::array();
	const auto &parent = _industry_draw_tile_data[10*4+3];
	const Sprite *parent_sprite = GetSprite(parent.building.sprite&SPRITE_MASK,SpriteType::Normal);
	const std::array<int,2> parent_offset{parent_sprite->x_offs,parent_sprite->y_offs};
	for (unsigned frame = 1; frame <= std::size(_coal_plant_sparks); ++frame) {
		SpriteID image = SPR_IT_POWER_PLANT_TRANSFORMERS+frame;
		auto name = fmt::format("industry-effect-10-{}.pam",frame);
		std::vector<uint8_t> indices;
		ExportSpriteReference(image,PAL_NONE,(directory/name).string(),&indices);
		const Sprite *sprite = GetSprite(image,SpriteType::Normal);
		const auto &offset = _coal_plant_sparks[frame-1];
		effects.push_back({{"graphics",10},{"frame",frame},{"sprite",image},{"palette",PAL_NONE},
			{"image",name},{"palette_indices",indices},{"sprite_offset",{sprite->x_offs,sprite->y_offs}},
			{"sprite_size",{sprite->width,sprite->height}},{"child_offset",{offset.x,offset.y}},
			{"parent_sprite",parent.building.sprite},{"parent_image","industry-010-3.pam"},
			{"parent_origin",{parent.origin.x,parent.origin.y,parent.origin.z}},
			{"parent_sprite_offset",parent_offset}});
	}
	std::ofstream(directory / "industry-effects.json") << effects.dump(2) << '\n';
	Debug(driver, 1, "OpenTT3D: exported {} industry tile-state references", manifest.size());
	Debug(driver,1,"OpenTT3D: exported {} original power-station spark frames and parent-relative offsets",effects.size());
}

SpriteID IndustryBodySprite(unsigned graphics)
{
	return graphics < std::size(_industry_draw_tile_data) / 4 ? _industry_draw_tile_data[graphics * 4 + 3].building.sprite & SPRITE_MASK : 0;
}

void ExportBridgeReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	std::set<std::pair<SpriteID, PaletteID>> exported;
	for (unsigned type = 0; type < MAX_BRIDGES; ++type) for (BridgePieces piece = BRIDGE_PIECE_NORTH; piece < NUM_BRIDGE_PIECES; ++piece) {
		auto sprites = GetBridgeSpriteTable(type, piece);
		for (size_t slot = 0; slot < sprites.size(); ++slot) {
			auto sprite = sprites[slot];
			if ((sprite.sprite & SPRITE_MASK) == 0) continue;
			auto name = fmt::format("bridge-sprite-{}-{}.pam", sprite.sprite & SPRITE_MASK, sprite.pal);
			if (exported.emplace(sprite.sprite, sprite.pal).second) ExportSpriteReference(sprite.sprite, sprite.pal, (directory / name).string());
			const Sprite *source = GetSprite(sprite.sprite & SPRITE_MASK,SpriteType::Normal);
			manifest.push_back({{"type", type}, {"piece", to_underlying(piece)}, {"slot", slot}, {"sprite", sprite.sprite}, {"palette", sprite.pal}, {"image", name},
				{"offset", {source->x_offs,source->y_offs}}, {"size", {source->width,source->height}}});
		}
	}
	std::ofstream(directory / "bridges.json") << manifest.dump(2) << '\n';
	Debug(driver, 1, "OpenTT3D: exported {} bridge sprite bindings", manifest.size());
}

void ExportTerrainReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	auto image = [&](const char *category, unsigned style, unsigned variant, SpriteID sprite) {
		auto filename = fmt::format("{}-{}-{}.pam",category,style,variant);
		ExportSpriteReference(sprite,PAL_NONE,(directory/filename).string());
		const Sprite *source = GetSprite(sprite,SpriteType::Normal);
		manifest.push_back({{"category",category},{"style",style},{"variant",variant},{"sprite",sprite},{"image",filename},
			{"offset",{source->x_offs,source->y_offs}},{"size",{source->width,source->height}}});
	};
	for (unsigned style = 0; style < 6; ++style) for (unsigned variant = 0; variant < 6; ++variant) image("fence",style,variant,_clear_land_fence_sprites[style]+variant);
	for (unsigned variant = 0; variant < 8; ++variant) image("rail-fence",0,variant,SPR_TRACK_FENCE_FLAT_X+variant);
	for (unsigned slope = 1; slope < 15; ++slope) image("foundation",0,slope,SPR_FOUNDATION_BASE+slope);
	for (unsigned slot = 0; slot < NORMAL_FOUNDATION_SPRITE_COUNT; ++slot) image("foundation-extra",0,slot,SPR_SLOPES_BASE+slot);
	for (unsigned slot = 0; slot < 4*HALFTILE_BLOCK_SIZE; ++slot) image("foundation-half",0,slot,SPR_HALFTILE_FOUNDATION_BASE+slot);
	for (unsigned style = 0; style < 9; ++style) image("field",style,0,_clear_land_sprites_farmland[style]);
	image("rocks",0,0,SPR_FLAT_ROCKY_LAND_1);
	image("rocks",1,0,SPR_FLAT_ROCKY_LAND_2);
	for (unsigned density = 0; density < 4; ++density) {
		image("grass",density,0,SPR_FLAT_BARE_LAND+density*19);
		image("snow-desert",density,0,_clear_land_sprites_snow_desert[density]);
		image("snow-rocks",density,0,SPR_OVERLAY_ROCKS_BASE+(density+1)*19);
	}
	for (unsigned variant = 0; variant < 5; ++variant) image("rough",0,variant,_landscape_clear_sprites_rough[variant]);
	const SpriteID tunnels[] = {SPR_TUNNEL_ENTRY_REAR_RAIL,SPR_TUNNEL_ENTRY_REAR_MONO,SPR_TUNNEL_ENTRY_REAR_MAGLEV,SPR_TUNNEL_ENTRY_REAR_ROAD};
	for (unsigned style = 0; style < 4; ++style) for (unsigned variant = 0; variant < 8; ++variant) image("tunnel",style,variant,tunnels[style]+variant);
	image("road",0,0,SPR_ROAD_X);
	image("track",0,0,SPR_RAIL_TRACK_X);
	image("track",1,0,SPR_MONO_TRACK_X);
	image("track",2,0,SPR_MGLV_TRACK_X);
	std::ofstream(directory/"terrain-details.json") << manifest.dump(2) << '\n';
	Debug(driver,1,"OpenTT3D: exported {} terrain-detail references",manifest.size());
}

void ExportStationReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	for (RailType type : {RAILTYPE_RAIL,RAILTYPE_MONO,RAILTYPE_MAGLEV}) for (unsigned layout = 0; layout < 8; ++layout) {
		const auto *drawing = GetStationTileLayout(StationType::Rail,layout);
		unsigned part = 0;
		auto image = [&](SpriteID sprite) {
			sprite = (sprite & SPRITE_MASK)+GetRailTypeInfo(type)->GetRailtypeSpriteOffset();
			auto name = fmt::format("station-{}-{}-{}.pam",to_underlying(type),layout,part);
			ExportSpriteReference(sprite,PAL_NONE,(directory/name).string());
			const Sprite *source = GetSprite(sprite,SpriteType::Normal);
			manifest.push_back({{"railtype",to_underlying(type)},{"layout",layout},{"part",part++},{"sprite",sprite},{"image",name},
				{"offset",{source->x_offs,source->y_offs}},{"size",{source->width,source->height}}});
		};
		image(drawing->ground.sprite);
		for (const auto &component : drawing->GetSequence()) image(component.image.sprite);
	}
	std::ofstream(directory/"stations.json") << manifest.dump(2) << '\n';
	Debug(driver,1,"OpenTT3D: exported {} vanilla station component references",manifest.size());
}

void ExportRailDetailReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	auto image = [&](const char *category, unsigned style, unsigned variant, SpriteID sprite) {
		auto filename = fmt::format("{}-{}-{}.pam",category,style,variant);
		ExportSpriteReference(sprite,PAL_NONE,(directory/filename).string());
		manifest.push_back({{"category",category},{"style",style},{"variant",variant},{"sprite",sprite},{"image",filename}});
	};
	for (unsigned type = 0; type < 6; ++type) for (unsigned variant = 0; variant < 2; ++variant) {
		for (unsigned direction = 0; direction < 8; ++direction) for (unsigned state = 0; state < 2; ++state) {
			SpriteID base = type == 0 && variant == 0 ? SPR_ORIGINAL_SIGNALS_BASE : SPR_SIGNALS_BASE-16;
			image("signal",type*2+variant,direction*2+state,base+type*16+variant*64+direction*2+state+(type > 3 ? 64 : 0));
		}
	}
	for (unsigned pylon = 0; pylon < 8; ++pylon) image("pylon",0,pylon,SPR_PYLON_BASE+pylon);
	for (unsigned wire = 0; wire < 28; ++wire) image("wire",0,wire,SPR_WIRE_BASE+wire);
	std::ofstream(directory/"rail-details.json") << manifest.dump(2) << '\n';
	Debug(driver,1,"OpenTT3D: exported {} rail-detail references",manifest.size());
}

void ExportInfrastructureReferences()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json manifest = nlohmann::json::array();
	auto image = [&](const char *category, unsigned style, unsigned variant, SpriteID sprite) {
		auto filename = fmt::format("{}-{}-{}.pam",category,style,variant);
		std::vector<uint8_t> palette_indices;
		ExportSpriteReference(sprite,PAL_NONE,(directory/filename).string(),&palette_indices);
		const Sprite *source = GetSprite(sprite,SpriteType::Normal);
		manifest.push_back({{"category",category},{"style",style},{"variant",variant},{"sprite",sprite},{"image",filename},
			{"size",{source->width,source->height}},{"offset",{source->x_offs,source->y_offs}},{"palette_indices",palette_indices}});
	};
	for (unsigned kind = 0; kind < 6; ++kind) for (unsigned direction = 0; direction < 4; ++direction) {
		const DrawTileSprites &source = kind < 4 ? _depot_gfx_table[direction] : GetRoadDepotDrawData(static_cast<DiagDirection>(direction));
		int relocation = kind < 4 ? GetRailTypeInfo(static_cast<RailType>(kind))->GetRailtypeSpriteOffset() :
			kind == 5 ? SPR_TRAMWAY_DEPOT_NO_TRACK-SPR_ROAD_DEPOT : 0;
		SpriteID ground = source.ground.sprite & SPRITE_MASK;
		if (kind < 4 && ground != SPR_FLAT_GRASS_TILE) ground += relocation;
		image("depot",kind,direction*3,ground);
		manifest.back()["direction"] = direction;
		manifest.back()["part"] = 0;
		manifest.back()["origin"] = {0,0,0};
		unsigned part = 1;
		for (const auto &piece : source.GetSequence()) {
			image("depot",kind,direction*3+part,(piece.image.sprite & SPRITE_MASK)+relocation);
			manifest.back()["direction"] = direction;
			manifest.back()["part"] = part++;
			manifest.back()["origin"] = {piece.origin.x,piece.origin.y,piece.origin.z};
			manifest.back()["extent"] = {piece.extent.x,piece.extent.y,piece.extent.z};
		}
	}
	for (unsigned kind = 0; kind < 4; ++kind) for (unsigned variant = 0; variant < 12; ++variant) {
		image("crossing",kind,variant,GetRailTypeInfo(static_cast<RailType>(kind))->base_sprites.crossing+variant);
	}
	for (unsigned axis = 0; axis < 2; ++axis) for (unsigned half = 0; half < 2; ++half) {
		const auto &source = _shipdepot_display_data[axis][half];
		image("ship-depot",axis,half*4,source.ground.sprite&SPRITE_MASK);
		manifest.back()["direction"] = axis*2+half;
		manifest.back()["depot_part"] = half;
		manifest.back()["part"] = 0;
		manifest.back()["origin"] = {0,0,0};
		unsigned part = 1;
		for (const auto &piece : source.GetSequence()) {
			image("ship-depot",axis,half*4+part,piece.image.sprite&SPRITE_MASK);
			manifest.back()["direction"] = axis*2+half;
			manifest.back()["depot_part"] = half;
			manifest.back()["part"] = part++;
			manifest.back()["origin"] = {piece.origin.x,piece.origin.y,piece.origin.z};
			manifest.back()["extent"] = {piece.extent.x,piece.extent.y,piece.extent.z};
		}
	}
	for (unsigned layout = 0; layout < 6; ++layout) {
		const auto &source = *GetStationTileLayout(StationType::Dock,layout);
		image("dock",layout,0,source.ground.sprite&SPRITE_MASK);
		manifest.back()["direction"] = layout;
		manifest.back()["part"] = 0;
		manifest.back()["origin"] = {0,0,0};
		unsigned part = 1;
		for (const auto &piece : source.GetSequence()) {
			image("dock",layout,part,piece.image.sprite&SPRITE_MASK);
			manifest.back()["direction"] = layout;
			manifest.back()["part"] = part++;
			manifest.back()["origin"] = {piece.origin.x,piece.origin.y,piece.origin.z};
			manifest.back()["extent"] = {piece.extent.x,piece.extent.y,piece.extent.z};
		}
	}
	for (const auto &piece : GetStationTileLayout(StationType::Buoy,0)->GetSequence()) {
		SpriteID resolved = piece.image.sprite&SPRITE_MASK;
		TileIndex actual = INVALID_TILE;
		for (uint y = 1; y < Map::MaxY() && actual == INVALID_TILE; ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
			TileIndex tile = TileXY(x,y);
			if (!IsBuoyTile(tile)) continue;
			actual = tile;
			if (SpriteID replacement = GetCanalSprite(CF_BUOY,tile); replacement != 0) resolved = replacement;
			break;
		}
		image("buoy",0,0,resolved);
		manifest.back()["actual_tile"] = actual == INVALID_TILE ? -1 : static_cast<int>(actual.base());
		manifest.back()["origin"] = {piece.origin.x,piece.origin.y,piece.origin.z};
		manifest.back()["extent"] = {piece.extent.x,piece.extent.y,piece.extent.z};
	}
	for (unsigned kind = 0; kind < 2; ++kind) for (unsigned layout = 0; layout < 6; ++layout) {
		const auto *source = GetStationTileLayout(kind == 0 ? StationType::Bus : StationType::Truck,layout);
		image("roadstop",kind,layout*4,source->ground.sprite & SPRITE_MASK);
		unsigned part = 1;
		for (const auto &piece : source->GetSequence()) image("roadstop",kind,layout*4+part++,piece.image.sprite & SPRITE_MASK);
	}
	for (unsigned kind = 0; kind < 4; ++kind) {
		const auto &sprites = GetRailTypeInfo(static_cast<RailType>(kind))->base_sprites;
		const SpriteID routes[] = {sprites.single_x,sprites.single_y,sprites.single_n,sprites.single_s,sprites.single_w,sprites.single_e};
		for (unsigned track = 0; track < std::size(routes); ++track) image("rail",kind,track,routes[track]);
		for (unsigned track = 0; track < 26; ++track) image("rail-ground",kind,track,sprites.track_y+track);
	}
	for (unsigned gfx = 0; gfx <= APT_GRASS_FENCE_NE_FLAG_2; ++gfx) {
		auto frames = GetAirportTileLayouts(gfx);
		for (unsigned frame = 0; frame < frames.size(); ++frame) {
			const auto &source = *frames[frame];
			if ((source.ground.sprite & SPRITE_MASK) != 0) {
				image("airport",gfx,frame*32,source.ground.sprite & SPRITE_MASK);
				manifest.back()["frame"] = frame;
			}
			unsigned part = 1;
			for (const auto &piece : source.GetSequence()) {
				if ((piece.image.sprite & SPRITE_MASK) == 0) continue;
				image("airport",gfx,frame*32+part++,piece.image.sprite & SPRITE_MASK);
				manifest.back()["frame"] = frame;
				manifest.back()["origin"] = {piece.origin.x,piece.origin.y,piece.origin.z};
				manifest.back()["extent"] = {piece.extent.x,piece.extent.y,piece.extent.z};
			}
		}
	}
	std::ofstream(directory/"infrastructure.json") << manifest.dump(2) << '\n';
	Debug(driver,1,"OpenTT3D: exported {} depot, ship-depot, crossing, road-stop, railway and airport references",manifest.size());
}

static Scene TunnelReviewScene(TunnelKind kind, unsigned direction, const Camera &camera)
{
	Textures().BeginScene();
	Scene scene;
	Vec3 step = TunnelPoint(direction,{16,8,0})-TunnelPoint(direction,{0,8,0});
	for (unsigned section = 0; section < 4; ++section) {
		DrawTunnelSection(scene,camera,step*section,section == 3 ? (direction+2)%4 : direction,kind,section == 0 || section == 3,false);
	}
	for (auto &instance : scene.instances) instance.data.SetObjectId(149);
	return scene;
}

static void WriteReviewImage(const std::filesystem::path &path, const Camera &camera, const std::vector<uint8_t> &pixels)
{
	std::ofstream file(path,std::ios::binary);
	if (!file) throw std::runtime_error("Cannot write review image");
	file << fmt::format("P7\nWIDTH {}\nHEIGHT {}\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n",camera.width,camera.height);
	for (int y = camera.height-1; y >= 0; --y) file.write(reinterpret_cast<const char *>(pixels.data()+y*camera.width*4),camera.width*4);
}

static Scene SignalReviewScene(unsigned type, unsigned variant, unsigned state, unsigned direction, const Camera &camera)
{
	Scene scene;
	DrawRailSignal(scene,camera,{},type,variant,state,direction);
	for (auto &instance : scene.instances) instance.data.SetObjectId(173);
	return scene;
}

static Scene DepotReviewScene(unsigned kind, unsigned direction, const Camera &camera, bool transparent = false, PaletteID palette = PALETTE_TO_BLUE)
{
	Textures().BeginScene();
	Scene scene;
	DrawDepot(scene,camera,{},kind,direction,palette,transparent);
	for (auto &instance : scene.instances) instance.data.SetObjectId(181);
	return scene;
}

void ExportDepotGallery(unsigned kind, unsigned direction)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,10},7,640,640,turn+0.25f};
		Scene scene = DepotReviewScene(kind,direction,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Depot gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-depot-{}-{}.pam",kind,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported depot {} direction {} model gallery",kind,direction);
}

Scene ShipDepotReviewScene(unsigned axis, PaletteID palette, bool transparent, bool invisible)
{
	if (axis >= 2) throw std::runtime_error("Invalid ship-depot axis");
	Textures().BeginScene();
	Scene scene;
	static const auto water = [] {
		Scene tile; tile.Quad({0,0,0},{16,0,0},{16,16,0},{0,16,0},{});
		return tile.vertices;
	}();
	const auto &texture = Textures().Get(SPR_FLAT_WATER_TILE,PAL_NONE,0,true);
	Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
	for (unsigned part = 0; part < 2; ++part) {
		Vec3 origin = axis == 0 ? Vec3{16.0f*part,0,0} : Vec3{0,16.0f*part,0};
		InstanceData floor;
		floor.origin_opacity = {origin.x,origin.y,0,1};
		floor.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
		floor.region = texture.Region();
		floor.identity = {0,static_cast<float>(SurfaceMode::Opaque),1,0};
		floor.SetObjectId(TILE_PICK_ID|static_cast<uint32_t>(0x123450+part));
		scene.instances.push_back({&water,floor});
		size_t first = scene.instances.size();
		if (!DrawVoxelShipDepot(scene,origin,axis,part,palette,transparent,invisible)) throw std::runtime_error("Missing original voxel ship-depot binding");
		for (size_t i = first; i < scene.instances.size(); ++i) scene.instances[i].data.SetObjectId(floor.ObjectId());
	}
	return scene;
}

/** Apply the original recolour table independently of palette strips/atlas UVs. */
static Scene PaletteReferenceScene(const Scene &actual, PaletteID palette)
{
	Scene oracle;
	const auto colours = SnapshotPalette();
	const uint8_t *mapping = GetNonSprite(palette,SpriteType::Recolour)+1;
	for (const auto &instance : actual.instances) {
		if ((static_cast<unsigned>(instance.mesh->front().surface)&15U) != static_cast<unsigned>(SurfaceMode::Palette)) {
			oracle.instances.push_back(instance);
			continue;
		}
		Scene single; single.instances.push_back(instance);
		auto expanded = single.ExpandedVertices(true);
		for (size_t i = 0; i < expanded.size(); ++i) {
			unsigned index = static_cast<unsigned>((*instance.mesh)[i].texture.x*256);
			Colour colour = colours.palette[mapping[index]];
			expanded[i].colour = {colour.r/255.0f,colour.g/255.0f,colour.b/255.0f};
			if (mapping[index] == 0) expanded[i].opacity = 0;
			expanded[i].texture = {0,0,-1};
			expanded[i].surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT);
		}
		oracle.vertices.insert(oracle.vertices.end(),expanded.begin(),expanded.end());
	}
	return oracle;
}

void VerifyShipDepots()
{
	unsigned views = 0;
	for (unsigned axis = 0; axis < 2; ++axis) for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
		Vec3 high = axis == 0 ? Vec3{32,16,24} : Vec3{16,32,24};
		Camera camera{high*0.5f,2,256,256,turn+0.25f};
		if (street) camera = StreetReviewCamera({},high,256,256,turn+0.25f);
		for (unsigned company = 0; company < 16; ++company) {
			PaletteID palette = PALETTE_RECOLOUR_START+company;
			Scene actual = ShipDepotReviewScene(axis,palette);
			Scene oracle = PaletteReferenceScene(actual,palette);
			std::vector<uint8_t> pixels, reference;
			std::vector<uint32_t> ids, reference_ids;
			if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(oracle,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Joined ship depot differs from CPU geometry/original company palette");
			for (unsigned part = 0; part < 2; ++part) if (std::count(ids.begin(),ids.end(),TILE_PICK_ID|static_cast<uint32_t>(0x123450+part)) < 8) throw std::runtime_error("Joined ship depot lost one tile's ownership");
			if (company == 0) {
				Scene floor = actual;
				std::erase_if(floor.instances,[](const MeshInstance &instance) { return (static_cast<unsigned>(instance.mesh->front().surface)&15U) == static_cast<unsigned>(SurfaceMode::Palette); });
				Scene invisible = ShipDepotReviewScene(axis,palette,true,true);
				if (invisible.instances.size() != 2 || !RenderScene(floor,camera,pixels,&ids) || !RenderScene(invisible,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Invisible ship depot changed the independent opaque water or tile ownership");
				Scene transparent = ShipDepotReviewScene(axis,palette,true);
				if (!RenderScene(transparent,camera,reference,&reference_ids) || ids != reference_ids) throw std::runtime_error("Transparent ship depot intercepts water picking");
			}
			++views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} joined voxel ship-depot views preserve both axes, original company palettes, CPU geometry and opaque water ownership under transparent/invisible bodies",views);
}

void VerifyDepots()
{
	unsigned views = 0, voxel_palette_views = 0;
	for (unsigned kind = 0; kind < 6; ++kind) for (unsigned direction = 0; direction < 4; ++direction) for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,9},2.5f,256,256,turn+0.25f};
		Scene scene = DepotReviewScene(kind,direction,camera);
		std::vector<uint8_t> pixels, reference;
		std::vector<uint32_t> ids, reference_ids;
		if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),181) < 64) throw std::runtime_error("Depot direction geometry is missing");
		Scene recoloured = DepotReviewScene(kind,direction,camera,false,PALETTE_TO_RED);
		if (!RenderScene(recoloured,camera,reference,&reference_ids) || ids != reference_ids || pixels == reference) throw std::runtime_error("Depot company colours must change without moving the building");
		if (HasVoxelDepot(kind,direction)) {
			Scene invisible, floor;
			DrawDepot(invisible,camera,{},kind,direction,PALETTE_TO_RED,true,true);
			if (scene.instances.size() < 2 || invisible.instances.size()+1 != scene.instances.size() || invisible.instances[0].mesh != scene.instances[0].mesh || invisible.instances[0].data.origin_opacity[3] != 1) throw std::runtime_error("Invisible voxel depot did not retain its original opaque floor and running infrastructure");
			for (size_t i = 0; i < scene.instances.size(); ++i) if (i != 1) floor.instances.push_back(scene.instances[i]);
			for (size_t i = 0; i < invisible.instances.size(); ++i) {
				if (invisible.instances[i].mesh != floor.instances[i].mesh) throw std::runtime_error("Voxel depot invisibility changed track/wire selection");
				invisible.instances[i].data.SetObjectId(181);
			}
			if (!RenderScene(invisible,camera,pixels,&ids) || !RenderScene(floor,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Voxel depot invisibility changed floor/track colours or tile ownership");
			if (turn == 0) for (unsigned company = 0; company < 16; ++company) {
				PaletteID palette = PALETTE_RECOLOUR_START+company;
				Scene actual = DepotReviewScene(kind,direction,camera,false,palette), oracle;
				const auto colours = SnapshotPalette();
				const uint8_t *mapping = GetNonSprite(palette,SpriteType::Recolour)+1;
				for (const auto &instance : actual.instances) {
					Scene single; single.instances.push_back(instance);
					auto expanded = single.ExpandedVertices(true);
					for (size_t i = 0; i < expanded.size(); ++i) {
						unsigned index = static_cast<unsigned>((*instance.mesh)[i].texture.x*256);
						Colour colour = colours.palette[mapping[index]];
						expanded[i].colour = {colour.r/255.0f,colour.g/255.0f,colour.b/255.0f};
						if (mapping[index] == 0) expanded[i].opacity = 0;
						expanded[i].texture = {0,0,-1};
						expanded[i].surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT);
					}
					oracle.vertices.insert(oracle.vertices.end(),expanded.begin(),expanded.end());
				}
				if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(oracle,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Voxel depot differs from the original company recolour table");
				++voxel_palette_views;
			}
		}
		Scene transparent = DepotReviewScene(kind,direction,camera,true);
		std::erase_if(transparent.instances,[](const MeshInstance &instance) { return instance.data.origin_opacity[3] > 0.99f; });
		if (!RenderScene(transparent,camera,reference,&reference_ids) || std::any_of(reference_ids.begin(),reference_ids.end(),[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent depot walls intercept picking");
		if (turn == 0) for (const auto &instance : scene.instances) {
			Scene isolated, expanded;
			isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
			if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Depot component charts differ between CPU and GPU instances");
		}
		++views;
	}
	Debug(driver,1,"OpenTT3D: {} depot direction views, component materials, company colours and transparent walls passed",views);
	Debug(driver,1,"OpenTT3D: {} voxel depot views match all sixteen original company tables; invisible floors retain exact colour and tile ownership",voxel_palette_views);
	VerifyShipDepots();
}

static void AddDockReviewTile(Scene &scene, unsigned graphics, Vec3 origin, uint32_t id, PaletteID palette, bool transparent, bool invisible)
{
	static const auto ground = [] {
		std::array<std::vector<Vertex>,6> meshes;
		const Slope slopes[] = {SLOPE_SW,SLOPE_NW,SLOPE_NE,SLOPE_SE,SLOPE_FLAT,SLOPE_FLAT};
		for (unsigned layout = 0; layout < meshes.size(); ++layout) {
			auto surface = MakeTileSurface(slopes[layout]);
			Scene tile;
			const Vec3 corners[] = {{0,0,surface.corners[0]},{16,0,surface.corners[1]},{16,16,surface.corners[2]},{0,16,surface.corners[3]}};
			GroundEdgeFan(tile,corners,{8,8,surface.centre});
			for (auto &vertex : tile.vertices) vertex.texture = {vertex.position.x,vertex.position.y,vertex.position.z/TERRAIN_HEIGHT_SCALE};
			meshes[layout] = std::move(tile.vertices);
		}
		return meshes;
	}();
	const auto &source = *GetStationTileLayout(StationType::Dock,graphics);
	const auto &texture = Textures().Get(source.ground.sprite&SPRITE_MASK,PAL_NONE,0,true);
	Vec3 uv = texture.UV(-texture.x_offset,-texture.y_offset);
	InstanceData floor;
	floor.origin_opacity = {origin.x,origin.y,origin.z,1};
	floor.uv_transform = {uv.x,uv.y,ZOOM_BASE/(static_cast<float>(1U<<texture.zoom)*ATLAS_SIZE),uv.z};
	floor.region = texture.Region();
	floor.identity = {0,static_cast<float>(SurfaceMode::Opaque),1,2};
	floor.SetObjectId(id);
	scene.instances.push_back({&ground[graphics],floor});
	size_t first = scene.instances.size();
	if (!DrawVoxelDock(scene,origin,graphics,palette,transparent,invisible)) throw std::runtime_error("Missing original voxel dock binding");
	for (size_t i = first; i < scene.instances.size(); ++i) scene.instances[i].data.SetObjectId(id);
}

Scene DockReviewScene(unsigned graphics, PaletteID palette, bool transparent, bool invisible)
{
	if (graphics >= 6) throw std::runtime_error("Invalid dock graphics");
	Textures().BeginScene();
	Scene scene;
	AddDockReviewTile(scene,graphics,{},TILE_PICK_ID|0x654320,palette,transparent,invisible);
	return scene;
}

Scene JoinedDockReviewScene(unsigned direction, PaletteID palette, bool transparent, bool invisible)
{
	if (direction >= 4) throw std::runtime_error("Invalid dock direction");
	Textures().BeginScene();
	Scene scene;
	const Vec3 offsets[] = {{-16,0,0},{0,16,0},{16,0,0},{0,-16,0}};
	AddDockReviewTile(scene,direction,{},TILE_PICK_ID|0x654320,palette,transparent,invisible);
	AddDockReviewTile(scene,4+direction%2,offsets[direction],TILE_PICK_ID|0x654321,palette,transparent,invisible);
	return scene;
}

void VerifyDocks()
{
	unsigned views = 0;
	const Vec3 offsets[] = {{-16,0,0},{0,16,0},{16,0,0},{0,-16,0}};
	for (unsigned direction = 0; direction < 4; ++direction) for (unsigned turn = 0; turn < 4; ++turn) for (bool street : {false,true}) {
		Vec3 low{std::min(0.0f,offsets[direction].x),std::min(0.0f,offsets[direction].y),0};
		Vec3 high{16+std::max(0.0f,offsets[direction].x),16+std::max(0.0f,offsets[direction].y),TerrainZ(8)+6};
		Camera camera{(low+high)*0.5f,2,256,256,turn+0.15f};
		if (street) camera = StreetReviewCamera(low,high,256,256,turn+0.15f);
		for (unsigned company = 0; company < 16; ++company) {
			PaletteID palette = PALETTE_RECOLOUR_START+company;
			Scene actual = JoinedDockReviewScene(direction,palette);
			Scene oracle = PaletteReferenceScene(actual,palette);
			std::vector<uint8_t> pixels,reference;
			std::vector<uint32_t> ids,reference_ids;
			if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(oracle,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Joined dock differs from original palettes or CPU geometry");
			if (company == 0) {
				Scene floor = actual;
				std::erase_if(floor.instances,[](const MeshInstance &instance) { return (static_cast<unsigned>(instance.mesh->front().surface)&15U) == static_cast<unsigned>(SurfaceMode::Palette); });
				Scene invisible = JoinedDockReviewScene(direction,palette,true,true);
				if (invisible.instances.size() != 2 || !RenderScene(floor,camera,pixels,&ids) || !RenderScene(invisible,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Invisible dock changed the independent shore/water ground or tile IDs");
				Scene transparent = JoinedDockReviewScene(direction,palette,true);
				if (!RenderScene(transparent,camera,reference,&reference_ids) || ids != reference_ids) throw std::runtime_error("Transparent dock intercepts shore/water picking");
			}
			++views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} joined voxel dock views preserve original climate/company palettes, CPU geometry, sloped shore/water and transparent ownership",views);
}

static Scene CrossingReviewScene(unsigned kind, unsigned axis, bool barred, bool tram, const Camera &camera)
{
	Textures().BeginScene();
	Scene scene;
	DrawCrossing(scene,camera,{},kind,axis,barred,tram);
	for (auto &instance : scene.instances) instance.data.SetObjectId(191);
	return scene;
}

void ExportCrossingGallery(unsigned kind, unsigned axis, bool barred)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,2},8,640,640,turn+0.25f};
		Scene scene = CrossingReviewScene(kind,axis,barred,false,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Crossing gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-crossing-{}-{}.pam",kind,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported crossing {} axis {} barred {} model gallery",kind,axis,barred);
}

void VerifyCrossings()
{
	unsigned views = 0;
	for (unsigned kind = 0; kind < 4; ++kind) for (unsigned axis = 0; axis < 2; ++axis) for (bool barred : {false,true}) for (bool tram : {false,true}) for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,2},3,256,256,turn+0.25f};
		Scene scene = CrossingReviewScene(kind,axis,barred,tram,camera);
		std::vector<uint8_t> pixels, reference;
		std::vector<uint32_t> ids, reference_ids;
		if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),191) < 64) throw std::runtime_error("Crossing layout geometry missing");
		/* Test lamp pixels in isolation: red cargo/ballast must not be mistaken
		 * for a warning lamp. Only the signal equipment extends above four units. */
		Scene lamps;
		for (const auto &instance : scene.instances) {
			float top = 0;
			for (const auto &vertex : *instance.mesh) top = std::max(top,vertex.position.z);
			if (top > 4) lamps.instances.push_back(instance);
		}
		if (!RenderScene(lamps,camera,pixels,&ids)) throw std::runtime_error("Crossing lamp rendering failed");
		unsigned red = 0;
		for (size_t i = 0; i < ids.size(); ++i) red += ids[i] == 191 && pixels[i*4] > 150 && pixels[i*4+1] < 70;
		if ((red != 0) != barred) throw std::runtime_error("Crossing lamps disagree with the upstream barred state");
		if (turn == 0) for (const auto &instance : scene.instances) {
			Scene isolated, expanded;
			isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
			if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Crossing component differs between CPU and GPU instances");
		}
		++views;
	}
	Debug(driver,1,"OpenTT3D: {} crossing layout/state views, warning lamps and component materials passed",views);
}

static Scene RoadStopReviewScene(bool truck, unsigned layout, bool tram, const Camera &camera, PaletteID palette = PALETTE_TO_BLUE, bool transparent = false)
{
	Textures().BeginScene();
	Scene scene;
	DrawRoadStop(scene,camera,{},truck,layout,tram,palette,transparent);
	for (auto &instance : scene.instances) instance.data.SetObjectId(197);
	return scene;
}

void ExportRoadStopGallery(bool truck, unsigned layout)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,4},7,640,640,turn+0.25f};
		Scene scene = RoadStopReviewScene(truck,layout,false,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Road-stop gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-roadstop-{}-{}.pam",truck ? 1 : 0,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported road stop {} layout {} model gallery",truck ? 1 : 0,layout);
}

void VerifyRoadStops()
{
	unsigned views = 0;
	for (bool truck : {false,true}) for (unsigned layout = 0; layout < 6; ++layout) for (bool tram : {false,true}) {
		if (tram && layout < 4) continue;
		for (unsigned turn = 0; turn < 4; ++turn) {
			Camera camera{{8,8,4},2.5f,256,256,turn+0.25f};
			Scene scene = RoadStopReviewScene(truck,layout,tram,camera);
			std::vector<uint8_t> pixels, reference;
			std::vector<uint32_t> ids, reference_ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),197) < 64) throw std::runtime_error("Road-stop layout geometry missing");
			Scene recoloured = RoadStopReviewScene(truck,layout,tram,camera,PALETTE_TO_RED);
			if (!RenderScene(recoloured,camera,reference,&reference_ids) || ids != reference_ids || pixels == reference) throw std::runtime_error("Road-stop company colours disagree with the original palette");
			Scene transparent = RoadStopReviewScene(truck,layout,tram,camera,PALETTE_TO_BLUE,true);
			std::erase_if(transparent.instances,[](const MeshInstance &instance) { return instance.data.origin_opacity[3] > 0.99f; });
			if (!RenderScene(transparent,camera,reference,&reference_ids) || std::any_of(reference_ids.begin(),reference_ids.end(),[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent road-stop shelter intercepts picking");
			if (turn == 0) for (const auto &instance : scene.instances) {
				Scene isolated, expanded;
				isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
				if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Road-stop component material differs between CPU and GPU instances");
			}
			++views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} road-stop layout/tram views, company materials and transparent shelters passed",views);
}

static Scene CatenaryReviewScene(unsigned track, int grade, unsigned supports, const Camera &camera, bool transparent = false)
{
	Scene scene;
	DrawCatenaryWire(scene,camera,{},track,grade,supports,0,transparent);
	for (unsigned end = 0; end < 2; ++end) if (supports & (1U<<end)) {
		auto frame = RailPath(track,static_cast<float>(end));
		Vec3 point = frame.point+Vec3{0,0,static_cast<float>(end ? grade : 0)};
		DrawCatenaryPylon(scene,point+frame.across*(end ? 4.0f : -4.0f),point+Vec3{0,0,10},transparent);
	}
	for (auto &instance : scene.instances) instance.data.SetObjectId(179);
	return scene;
}

void ExportSignalGallery(unsigned type, unsigned variant, unsigned state)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{0,0,7},24,640,640,turn+0.25f};
		Scene scene = SignalReviewScene(type,variant,state,0,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Signal gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-signal-{}-{}.pam",type,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported signal {} variant {} state {} model gallery",type,variant,state);
}

void ExportCatenaryGallery(unsigned track, int grade)
{
	grade = static_cast<int>(TerrainZ(grade));
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{RailPath(track,0.5f).point+Vec3{0,0,grade*0.5f+6},7,640,640,turn+0.25f};
		Scene scene = CatenaryReviewScene(track,grade,3,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Catenary gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-catenary-{}-{}.pam",track,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported catenary track {} grade {} model gallery",track,grade);
}

void VerifyRailDetails()
{
	unsigned signals = 0, wires = 0;
	for (unsigned type = 0; type < 6; ++type) for (unsigned variant = 0; variant < 2; ++variant) for (unsigned state = 0; state < 2; ++state) {
		for (unsigned direction = 0; direction < 8; ++direction) {
			Camera camera{{0,0,7},5,256,256,0.25f};
			Scene scene = SignalReviewScene(type,variant,state,direction,camera);
			std::vector<uint8_t> pixels, reference;
			std::vector<uint32_t> ids, reference_ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),173) < 16) throw std::runtime_error("Signal state/direction geometry missing");
			Scene expanded; expanded.vertices = scene.ExpandedVertices(true);
			if (!RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Signal instance colour/position differs from CPU reference");
			++signals;
		}
	}
	for (unsigned state = 0; state < 2; ++state) {
		Camera camera{{0,0,10.7f},14,256,256,0.5f}; // Front of the +X-facing signal.
		Scene scene = SignalReviewScene(0,0,state,0,camera);
		std::vector<uint8_t> pixels;
		std::vector<uint32_t> ids;
		if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("Signal aspect rendering failed");
		unsigned red = 0, green = 0;
		for (size_t i = 0; i < ids.size(); ++i) if (ids[i] == 173) {
			red += pixels[i*4] > 160 && pixels[i*4+1] < 70;
			green += pixels[i*4+1] > 160 && pixels[i*4] < 70;
		}
		if (state == 0 ? red == 0 || green != 0 : green == 0 || red != 0) throw std::runtime_error("Signal aspect does not match its upstream red/green state");
	}
	/* The auxiliary presignal lamp is red at danger and green at clear;
	 * path signals instead extinguish their lower red lamp when cleared. */
	for (unsigned type = 1; type < 6; ++type) for (unsigned state = 0; state < 2; ++state) {
		Camera camera{{0,0,10.5f},32,256,256,0.5f};
		Scene scene = SignalReviewScene(type,0,state,0,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Auxiliary signal lamp rendering failed");
		auto point = camera.Project({0.56f,0,9.5f});
		int x = static_cast<int>(point.x), y = camera.height-1-static_cast<int>(point.y);
		if (x < 0 || x >= camera.width || y < 0 || y >= camera.height) throw std::runtime_error("Auxiliary signal lamp outside review frame");
		size_t pixel = (static_cast<size_t>(y)*camera.width+x)*4;
		bool red = pixels[pixel] > 160 && pixels[pixel+1] < 70;
		bool green = pixels[pixel+1] > 160 && pixels[pixel] < 70;
		if (state == 0 ? !red : type < 4 ? !green : red || green) throw std::runtime_error("Auxiliary signal lamp disagrees with its base-set aspect");
	}
	for (unsigned track = 0; track < 6; ++track) for (int grade : {-16,0,16}) for (unsigned supports = 1; supports <= 3; ++supports) {
		for (unsigned turn = 0; turn < 4; ++turn) {
			Camera camera{RailPath(track,0.5f).point+Vec3{0,0,grade*0.5f+6},3,256,256,turn+0.25f};
			Scene scene = CatenaryReviewScene(track,grade,supports,camera);
			std::vector<uint8_t> pixels;
			std::vector<uint32_t> ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),179) < 8) throw std::runtime_error("Catenary slope/direction geometry missing");
			Scene transparent = CatenaryReviewScene(track,grade,supports,camera,true);
			if (!RenderScene(transparent,camera,pixels,&ids) || std::any_of(ids.begin(),ids.end(),[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent catenary intercepts picking");
			++wires;
		}
	}
	Debug(driver,1,"OpenTT3D: {} signal states/directions and {} catenary views passed, with correct aspects and transparent picking",signals,wires);
}

static Scene GroundDetailReviewScene(unsigned kind, unsigned variant, Slope slope, const Camera &camera, bool ground)
{
	Textures().BeginScene();
	Scene scene;
	if (kind >= 3) DrawClearSurface(scene,camera,{},slope,kind == 4,variant);
	else DrawGroundDetails(scene,camera,{},slope,kind != 0,kind == 2 ? 0 : variant,kind == 2 ? variant+1 : 0);
	for (auto &instance : scene.instances) instance.data.SetObjectId(163);
	if (ground && kind < 3) {
		TileInfo tile{}; tile.tile = TileXY(1,1); tile.tileh = slope;
		SpriteID image = kind == 0 ? SPR_FLAT_BARE_LAND : kind == 1 ? SPR_FLAT_GRASS_TILE : SPR_FLAT_SNOW_DESERT_TILE;
		BeginCapture(camera,true);
		try { CaptureGround(image+SlopeToSpriteOffset(slope),PAL_NONE,0,0,0,tile,nullptr,0,0); }
		catch (...) { FinishCapture(); throw; }
		Scene base = FinishCapture();
		scene.instances.insert(scene.instances.begin(),base.instances.begin(),base.instances.end());
	}
	return scene;
}

void ExportGroundDetailGallery(unsigned kind, unsigned variant, unsigned slope)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,TerrainZ(GetSlopeMaxPixelZ(static_cast<Slope>(slope)))*0.5f+1},7,640,640,turn+0.25f};
		Scene scene = GroundDetailReviewScene(kind,variant,static_cast<Slope>(slope),camera,true);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Ground-detail gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-ground-detail-{}-{}-{}.pam",kind,variant,turn),camera,pixels);
	}
	if (kind >= 3) {
		Camera camera{{24,24,TerrainZ(GetSlopeMaxPixelZ(static_cast<Slope>(slope)))*0.5f+4},1,960,640,0};
		camera.first_person = true; camera.pitch = 4; camera.vertical_fov = 40;
		Scene scene = GroundDetailReviewScene(kind,variant,static_cast<Slope>(slope),camera,true);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Ground-detail close-view rendering failed");
		WriteReviewImage(directory/fmt::format("model-ground-detail-{}-{}-cab.pam",kind,variant),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported ground detail {} variant {} slope {} model gallery",kind,variant,slope);
}

void VerifyGroundContinuity()
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
	std::filesystem::create_directories(directory);
	TileIndex sample = INVALID_TILE;
	for (uint i = 0; i < Map::Size(); ++i) {
		TileIndex tile{i};
		if (IsValidTile(tile) && !IsTileType(tile,MP_INDUSTRY)) { sample = tile; break; }
	}
	if (sample == INVALID_TILE) throw std::runtime_error("Ground continuity probe needs a valid reference tile");
	unsigned views = 0;
	for (unsigned layout = 0; layout < 3; ++layout) for (Vec3 source_origin : {Vec3{},Vec3{4096,8192,96}}) for (unsigned turn = 0; turn < 4; ++turn) {
		Vec3 origin{source_origin.x,source_origin.y,TerrainZ(source_origin.z)};
		/* Two independent ramp directions meet the level voxel floors at their
		 * original edge. No voxel floor is flattened onto a sloping map tile. */
		auto height = [layout](float x, float y) { return layout == 0 ? 0.0f : TerrainZ(std::max(0.0f,(layout == 1 ? x : y)-64)*0.5f); };
		auto kind_at = [layout](int x, int y) {
			unsigned kind = (x+y)%3;
			return kind == 2 && layout != 0 && (layout == 1 ? x : y) >= 4 ? 0U : kind;
		};
		Camera camera{{},1,768,512,static_cast<float>(turn)};
		camera.first_person = true; camera.pitch = 3; camera.vertical_fov = 40;
		camera.focus = origin+Vec3{64,64,6}+camera.Unrotate({40,40,0});
		camera.focus.z += height(camera.focus.x-origin.x,camera.focus.y-origin.y);
		Textures().BeginScene();
		Scene actual, reference;
		for (unsigned y = 0; y < 8; ++y) for (unsigned x = 0; x < 8; ++x) {
			Vec3 position = origin+Vec3{x*16.0f,y*16.0f,0};
			position.z += height(x*16.0f,y*16.0f);
			Slope slope = layout == 1 && x >= 4 ? SLOPE_SW : layout == 2 && y >= 4 ? SLOPE_SE : SLOPE_FLAT;
			unsigned kind = kind_at(x,y);
			unsigned fine_edges = 0;
			const int dx[] = {0,1,0,-1}, dy[] = {-1,0,1,0};
			for (unsigned edge = 0; edge < 4; ++edge) {
				int nx = static_cast<int>(x)+dx[edge], ny = static_cast<int>(y)+dy[edge];
				if (nx >= 0 && ny >= 0 && nx < 8 && ny < 8 && (kind_at(nx,ny) == 2 || (_settings_game.game_creation.landscape == LandscapeType::Toyland && kind_at(nx,ny) == 1))) fine_edges |= 1U<<edge;
			}
			if (_settings_game.game_creation.landscape == LandscapeType::Toyland && kind == 1) fine_edges = 15;
			if (kind == 0) {
				TileInfo tile{}; tile.tile = sample; tile.tileh = slope;
				tile.x = static_cast<int>(position.x); tile.y = static_cast<int>(position.y); tile.z = static_cast<int>(position.z/TERRAIN_HEIGHT_SCALE);
				BeginCapture(camera,true);
				try { CaptureGround(SPR_FLAT_BARE_LAND+SlopeToSpriteOffset(slope),PAL_NONE,tile.x,tile.y,tile.z,tile,nullptr,0,0,fine_edges); }
				catch (...) { FinishCapture(); throw; }
				Scene ground = FinishCapture();
				actual.instances.insert(actual.instances.end(),ground.instances.begin(),ground.instances.end());
			} else if (kind == 1) {
				bool rough = _settings_game.game_creation.landscape == LandscapeType::Toyland;
				Scene ground; DrawClearSurface(ground,camera,position,slope,rough,rough ? 0 : 3,fine_edges);
				if (ground.instances.empty()) throw std::runtime_error("Ground continuity probe has no natural substrate");
				actual.instances.push_back(ground.instances.front());
			} else if (!DrawVoxelAsset(actual,"depot_floors",4,0,position)) {
				throw std::runtime_error("Ground continuity probe has no voxel floor");
			}
		}
		for (auto &instance : actual.instances) instance.data.SetObjectId(TILE_PICK_ID|83);
		if (layout == 0) {
			reference.Quad(origin,origin+Vec3{128,0,0},origin+Vec3{128,128,0},origin+Vec3{0,128,0},{0.2f,0.25f,0.3f});
		} else {
			auto point = [&](float along, float across, float z) { return origin+(layout == 1 ? Vec3{along,across,z} : Vec3{across,along,z}); };
			reference.Quad(point(0,0,0),point(64,0,0),point(64,128,0),point(0,128,0),{0.2f,0.25f,0.3f});
			reference.Quad(point(64,0,0),point(128,0,TerrainZ(32)),point(128,128,TerrainZ(32)),point(64,128,0),{0.2f,0.25f,0.3f});
		}
		for (auto &vertex : reference.vertices) vertex.object_id = TILE_PICK_ID|83;
		std::vector<uint8_t> pixels, expected;
		std::vector<uint32_t> ids, expected_ids;
		if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids)) throw std::runtime_error("Ground continuity probe failed to render");
		if (std::count(expected_ids.begin(),expected_ids.end(),TILE_PICK_ID|83) < 1024) throw std::runtime_error("Ground continuity reference has insufficient terrain coverage");
		unsigned holes = 0;
		Vec3 first{};
		for (int y = 2; y < camera.height-2; ++y) for (int x = 2; x < camera.width-2; ++x) {
			size_t i = static_cast<size_t>(y)*camera.width+x;
			if (expected_ids[i] == 0 || expected_ids[i-2] == 0 || expected_ids[i+2] == 0 || expected_ids[i-2*camera.width] == 0 || expected_ids[i+2*camera.width] == 0 || ids[i] != 0) continue;
			if (holes++ == 0) first = camera.ScreenRay(x+0.5f,camera.height-y-0.5f).AtZ(origin.z).value_or(Vec3{});
		}
		WriteReviewImage(directory/fmt::format("model-ground-continuity-{}.pam",views),camera,pixels);
		if (holes != 0) throw std::runtime_error(fmt::format("Ground continuity view {} exposes {} sky pixels inside the terrain footprint; first ray at base height {},{},{}",views,holes,first.x,first.y,first.z));
		++views;
	}
	Debug(driver,1,"OpenTT3D: ground continuity verification passed: {} low-angle mixed-surface views retain complete terrain coverage",views);
}

void VerifyGroundDetails()
{
	unsigned views = 0;
	for (unsigned kind = 0; kind < 5; ++kind) for (unsigned variant = 0; variant < (kind == 0 ? 9U : kind == 1 ? 2U : kind == 4 ? 5U : 4U); ++variant) {
		for (unsigned slope = 0; slope < 32; ++slope) {
			if (slope >= 15 && slope != 23 && slope != 27 && slope != 29 && slope != 30) continue;
			for (unsigned turn = 0; turn < 4; ++turn) {
				Camera camera{{8,8,TerrainZ(GetSlopeMaxPixelZ(static_cast<Slope>(slope)))*0.5f+1},2,256,256,turn+0.25f};
				Scene scene = GroundDetailReviewScene(kind,variant,static_cast<Slope>(slope),camera,false);
				std::vector<uint8_t> pixels, comparison;
				std::vector<uint32_t> ids, comparison_ids;
				if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),163) < 32) throw std::runtime_error(fmt::format("Ground detail {} variant {} slope {} turn {} is missing",kind,variant,slope,turn));
				if (slope == 0 && ((kind == 0 && (variant == 8 || variant == 4)) || kind == 1 || kind >= 3)) for (const auto &instance : scene.instances) {
					Scene isolated, expanded;
					isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
					if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,comparison,&comparison_ids) || pixels != comparison || ids != comparison_ids) throw std::runtime_error("Ground detail instancing differs from CPU component material reference");
				}
				++views;
			}
		}
	}
	Debug(driver,1,"OpenTT3D: {} raised ground-detail views and component materials passed",views);
}

static Scene StationReviewScene(RailType type, unsigned layout, const Camera &camera, bool transparent = false, PaletteID palette = PALETTE_TO_BLUE)
{
	Textures().BeginScene();
	Scene scene;
	DrawRailStation(scene,camera,{},type,layout,palette,transparent);
	for (auto &instance : scene.instances) instance.data.SetObjectId(157);
	return scene;
}

void ExportStationGallery(unsigned type, unsigned layout)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	Vec3 step{};
	if (layout >= 4) {
		float offset = layout < 6 ? 16 : -16;
		step = layout%2 == 0 ? Vec3{0,offset,0} : Vec3{offset,0,0};
	}
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{Vec3{8,8,layout >= 4 ? 12.0f : 6.0f}+step*0.5f,4,640,640,turn+0.25f};
		Scene scene = StationReviewScene(static_cast<RailType>(type),layout,camera);
		TrackBits tracks = layout%2 == 0 ? TRACK_BIT_X : TRACK_BIT_Y;
		DrawRailTracks(scene,camera,{},SLOPE_FLAT,static_cast<RailType>(type),tracks,TRACK_BIT_NONE);
		if (layout >= 4) {
			DrawRailStation(scene,camera,step,static_cast<RailType>(type),layout^2,PALETTE_TO_BLUE,false);
			DrawRailTracks(scene,camera,step,SLOPE_FLAT,static_cast<RailType>(type),tracks,TRACK_BIT_NONE);
		}
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Station gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-station-{}-{}-{}.pam",type,layout,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported station {} layout {} model gallery",type,layout);
}

void VerifyStationModels()
{
	unsigned views = 0;
	for (unsigned type = 0; type < 4; ++type) for (unsigned layout = 0; layout < 8; ++layout) for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,8},2,256,256,turn+0.25f};
		std::vector<uint8_t> pixels, comparison;
		std::vector<uint32_t> ids, comparison_ids;
		Scene scene = StationReviewScene(static_cast<RailType>(type),layout,camera);
		if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),157) < 64) throw std::runtime_error(fmt::format("Station {} layout {} turn {} is missing",type,layout,turn));
		Scene transparent = StationReviewScene(static_cast<RailType>(type),layout,camera,true);
		if (!RenderScene(transparent,camera,comparison,&comparison_ids) || std::any_of(comparison_ids.begin(),comparison_ids.end(),[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent station intercepts picking");
		if (type == 0 && layout == 2) {
			Scene recoloured = StationReviewScene(RAILTYPE_RAIL,layout,camera,false,PALETTE_TO_RED);
			if (!RenderScene(recoloured,camera,comparison,&comparison_ids) || comparison_ids != ids || comparison == pixels) throw std::runtime_error("Station company paint must change without moving the structure");
			for (const auto &instance : scene.instances) {
				Scene isolated, expanded;
				isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
				if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,comparison,&comparison_ids) || pixels != comparison || ids != comparison_ids) throw std::runtime_error("Station instancing differs from CPU component material reference");
			}
		}
		++views;
	}
	Debug(driver,1,"OpenTT3D: {} station layout views, company materials and transparent picking passed",views);
	VerifyDocks();
}

static Scene RailReviewScene(RailType type, TrackBits tracks, Slope slope, const Camera &camera, bool terrain, TrackBits reserved = TRACK_BIT_NONE)
{
	Foundation foundation = GetRailFoundation(slope,tracks);
	if (foundation == FOUNDATION_INVALID) throw std::runtime_error("Invalid track/slope review combination");
	TileInfo tile{};
	tile.tile = TileXY(1,1); tile.tileh = slope;
	Corner upper = CORNER_INVALID;
	if (IsNonContinuousFoundation(foundation)) {
		upper = foundation == FOUNDATION_STEEP_BOTH ? GetHighestSlopeCorner(slope) : GetHalftileFoundationCorner(foundation);
		tracks &= ~CornerToTrackBits(upper);
		foundation = foundation == FOUNDATION_STEEP_BOTH ? FOUNDATION_STEEP_LOWER : FOUNDATION_NONE;
	}
	Scene rails;
	BeginCapture(camera,true);
	try {
		auto ground = [&] {
			Slope chart = IsHalftileSlope(tile.tileh) ? SlopeWithThreeCornersRaised(OppositeCorner(GetHalftileSlopeCorner(tile.tileh))) : tile.tileh;
			if (terrain) CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(chart),PAL_NONE,0,0,tile.z,tile,nullptr,0,0);
		};
		DrawFoundation(&tile,foundation);
		ground();
		DrawRailTracks(rails,camera,{0,0,TerrainZ(tile.z)},tile.tileh,type,tracks,reserved);
		if (IsValidCorner(upper)) {
			DrawFoundation(&tile,HalftileFoundation(upper));
			ground();
			DrawRailTracks(rails,camera,{0,0,TerrainZ(tile.z)},tile.tileh,type,CornerToTrackBits(upper),reserved);
		}
	} catch (...) { FinishCapture(); throw; }
	Scene ground = FinishCapture();
	for (auto &instance : rails.instances) instance.data.SetObjectId(151);
	if (terrain) rails.instances.insert(rails.instances.begin(),ground.instances.begin(),ground.instances.end());
	return rails;
}

void ExportRailGallery(unsigned type, unsigned tracks, unsigned slope)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{{8,8,TerrainZ(GetSlopeMaxPixelZ(static_cast<Slope>(slope)))*0.5f},6,640,640,turn+0.25f};
		Scene scene = RailReviewScene(static_cast<RailType>(type),static_cast<TrackBits>(tracks),static_cast<Slope>(slope),camera,true);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Rail gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-rail-{}-{}.pam",type,turn),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported rail {} tracks {} slope {} model gallery",type,tracks,slope);
}

void VerifyRailModels()
{
	unsigned views = 0;
	for (unsigned type = 0; type < 4; ++type) for (unsigned slope = 0; slope < 32; ++slope) {
		if (slope >= 15 && slope != 23 && slope != 27 && slope != 29 && slope != 30) continue;
		for (unsigned tracks = 1; tracks <= TRACK_BIT_ALL; ++tracks) {
			if (GetRailFoundation(static_cast<Slope>(slope),static_cast<TrackBits>(tracks)) == FOUNDATION_INVALID) continue;
			for (float scale : {2.0f,0.2f}) for (unsigned turn = 0; turn < 4; ++turn) {
				if (scale != 2 && (slope != 0 || (tracks != TRACK_BIT_X && tracks != TRACK_BIT_Y))) continue;
				Camera camera{{8,8,TerrainZ(GetSlopeMaxPixelZ(static_cast<Slope>(slope)))*0.5f},scale,192,192,turn+0.25f};
				Scene scene = RailReviewScene(static_cast<RailType>(type),static_cast<TrackBits>(tracks),static_cast<Slope>(slope),camera,false);
				std::vector<uint8_t> pixels;
				std::vector<uint32_t> ids;
				if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),151) < (scale == 2 ? 16 : 2)) throw std::runtime_error(fmt::format("Rail type {} tracks {} slope {} view {} scale {} missing geometry",type,tracks,slope,turn,scale));
				if (scale != 2) {
					Scene expanded; expanded.vertices = scene.ExpandedVertices(true);
					std::vector<uint8_t> reference; std::vector<uint32_t> reference_ids;
					if (!RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Distant rail instance colour/picking mismatch");
				}
				++views;
			}
		}
	}
	Camera camera{{8,8,0},3,256,256,0.25f};
	Scene ordinary = RailReviewScene(RAILTYPE_RAIL,TRACK_BIT_X,SLOPE_FLAT,camera,false);
	Scene reserved = RailReviewScene(RAILTYPE_RAIL,TRACK_BIT_X,SLOPE_FLAT,camera,false,TRACK_BIT_X);
	std::vector<uint8_t> pixels, dark;
	std::vector<uint32_t> ids, dark_ids;
	if (!RenderScene(ordinary,camera,pixels,&ids) || !RenderScene(reserved,camera,dark,&dark_ids) || ids != dark_ids || pixels == dark) throw std::runtime_error("Rail reservations must change material without changing geometry or picking");
	/* Check material charts per component; coincident rails at a junction can
	 * legitimately choose either matching face when batches are reordered. */
	for (const auto &instance : ordinary.instances) {
		Scene isolated, expanded;
		isolated.instances = {instance}; expanded.vertices = isolated.ExpandedVertices(true);
		if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,dark,&dark_ids) || ids != dark_ids || pixels != dark) throw std::runtime_error("Rail instancing differs from CPU material/geometry reference");
	}
	Debug(driver,1,"OpenTT3D: {} rail layout/slope views, reservation materials and instancing passed",views);
}

void ExportTunnelGallery(unsigned kind, unsigned direction)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{TunnelPoint(direction,{32,8,4}),3,640,640,turn+0.25f};
		Scene scene = TunnelReviewScene(static_cast<TunnelKind>(kind),direction,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Tunnel gallery rendering failed");
		WriteReviewImage(directory/fmt::format("model-tunnel-{}-{}.pam",kind,turn),camera,pixels);
	}
	for (int position : {2,20,50}) {
		Camera camera{TunnelPoint(direction,{static_cast<float>(position),8,6}),1,960,540,direction+0.5f};
		camera.first_person = true; camera.vertical_fov = 40; camera.pitch = 0;
		Scene scene = TunnelReviewScene(static_cast<TunnelKind>(kind),direction,camera);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Tunnel interior rendering failed");
		WriteReviewImage(directory/fmt::format("tunnel-cab-{}-{}.pam",kind,position),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported tunnel {} direction {} exterior and Cab galleries",kind,direction);
}

void VerifyTunnelModels()
{
	unsigned views = 0;
	for (unsigned kind = 0; kind < 6; ++kind) for (unsigned direction = 0; direction < 4; ++direction) {
		for (unsigned view = 0; view < 6; ++view) {
			Camera camera{TunnelPoint(direction,{32,8,4}),1,256,256,view+0.25f};
			if (view >= 4) {
				camera.focus = TunnelPoint(direction,{view == 4 ? 20.0f : 50.0f,8,6});
				camera.rotation = direction+0.5f; camera.first_person = true; camera.vertical_fov = 40; camera.pitch = 0;
			}
			Scene scene = TunnelReviewScene(static_cast<TunnelKind>(kind),direction,camera);
			std::vector<uint8_t> pixels;
			std::vector<uint32_t> ids;
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),149) < 64) throw std::runtime_error(fmt::format("Tunnel {} direction {} view {} is missing geometry",kind,direction,view));
			++views;
		}
	}
	Debug(driver,1,"OpenTT3D: {} tunnel exterior/interior views passed GPU visibility and picking",views);
}

void VerifyLiveTunnelCapture()
{
	TileIndex entrance = INVALID_TILE;
	TunnelKind kind = TunnelKind::Rail;
	for (uint y = 1; y < Map::MaxY() && entrance == INVALID_TILE; ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (GetVanillaTunnelKind(tile,kind)) { entrance = tile; break; }
	}
	if (entrance == INVALID_TILE) throw std::runtime_error("Live tunnel check requires a map with a supported tunnel");
	TileIndex other = GetOtherTunnelEnd(entrance);
	unsigned direction = GetTunnelBridgeDirection(entrance);
	Vec3 origin{TileX(entrance)*16.0f,TileY(entrance)*16.0f,TerrainZ(GetTilePixelZ(entrance))};
	float length = (std::abs(static_cast<int>(TileX(other))-static_cast<int>(TileX(entrance)))+std::abs(static_cast<int>(TileY(other))-static_cast<int>(TileY(entrance))))*16.0f;
	Debug(driver,1,"OpenTT3D: live tunnel review {},{} to {},{}, floor {}, direction {}",TileX(entrance),TileY(entrance),TileX(other),TileY(other),origin.z,direction);
	struct VehicleState { const Vehicle *vehicle; int x,y,z; Direction direction; VehStates flags; };
	std::vector<VehicleState> vehicles;
	for (const Vehicle *vehicle : Vehicle::Iterate()) vehicles.push_back({vehicle,vehicle->x_pos,vehicle->y_pos,vehicle->z_pos,vehicle->direction,vehicle->vehstatus});
	std::set<const std::vector<Vertex> *> tunnel_meshes, lining_meshes;
	for (bool portal : {false,true}) {
		const auto &assembly = TunnelGeometry(kind,portal);
		for (const auto &part : assembly.parts) tunnel_meshes.insert(&part);
		/* Portal overhangs can legitimately be occluded by outside foliage.
		 * Require the underground bore itself to be clear of terrain/scenery. */
		if (!portal) lining_meshes.insert(&assembly.parts[static_cast<unsigned>(TunnelMaterial::Lining)]);
	}
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	constexpr uint32_t tunnel_id = 0xE00000; // Beyond the vehicle-ID range, exactly representable as float.
	unsigned checked_pixels = 0, view = 0;
	for (float position : {12.0f,(length+16)*0.5f,length-4}) {
		Camera camera{origin+TunnelPoint(direction,{position,8,6}),1,640,360,direction+0.5f};
		camera.first_person = true; camera.vertical_fov = 40; camera.pitch = 0; camera.tunnel_entrance = entrance.base();
		Scene isolated;
		for (unsigned attempt = 0; ; ++attempt) {
			try { BeginCapture(camera,true); isolated = FinishCapture(); break; }
			catch (const AtlasFull &) { if (IsCapturing()) FinishCapture(); if (attempt != 0) throw; Textures().Repack(); }
		}
		for (auto &instance : isolated.instances) instance.data.SetObjectId(lining_meshes.contains(instance.mesh) ? tunnel_id : 0);
		std::vector<uint8_t> reference_pixels;
		std::vector<uint32_t> reference_ids;
		if (!RenderScene(isolated,camera,reference_pixels,&reference_ids)) throw std::runtime_error("Tunnel-hint rendering failed");
		Scene world;
		for (unsigned attempt = 0; ; ++attempt) {
			try { BeginCapture(camera,true); CollectViewport3D(Viewport{}); world = FinishCapture(); break; }
			catch (const AtlasFull &) { if (IsCapturing()) FinishCapture(); if (attempt != 0) throw; Textures().Repack(); }
			catch (...) { if (IsCapturing()) FinishCapture(); throw; }
		}
		for (size_t i = 0; i < world.instances.size(); ++i) {
			auto &instance = world.instances[i];
			if (tunnel_meshes.contains(instance.mesh)) instance.data.SetObjectId(tunnel_id);
			else if (instance.data.ObjectId() == 0 || (instance.data.ObjectId() & TILE_PICK_ID) != 0) instance.data.SetObjectId(0x100000+i);
		}
		std::vector<uint8_t> pixels;
		std::vector<uint32_t> ids;
		if (!RenderScene(world,camera,pixels,&ids)) throw std::runtime_error("Live tunnel rendering failed");
		unsigned lining = 0, covered = 0;
		std::map<size_t,unsigned> overlaps;
		for (size_t i = 0; i < ids.size(); ++i) if (reference_ids[i] == tunnel_id) {
			++lining;
			if (ids[i] == 0 || (ids[i] >= 0x100000 && ids[i] != tunnel_id)) {
				++covered;
				if (ids[i] >= 0x100000 && ids[i]-0x100000 < world.instances.size()) ++overlaps[ids[i]-0x100000];
			}
		}
		WriteReviewImage(directory/fmt::format("live-tunnel-cab-{}.pam",view++),camera,pixels);
		if (lining < 64 || covered != 0) {
			for (auto [index,count] : overlaps) {
				const auto &instance = world.instances[index];
				Debug(driver,1,"OpenTT3D: tunnel overlap {} pixels, mesh {} vertices at {},{},{}",count,instance.mesh->size(),instance.data.origin_opacity[0],instance.data.origin_opacity[1],instance.data.origin_opacity[2]);
				for (size_t pixel = 0; pixel < ids.size(); ++pixel) if (reference_ids[pixel] == tunnel_id && ids[pixel] == 0x100000+index) {
					Ray ray = camera.ScreenRay(pixel%camera.width+0.5f,camera.height-1-pixel/camera.width+0.5f);
					Debug(driver,1,"OpenTT3D: overlap ray from {},{},{} direction {},{},{}",ray.origin.x,ray.origin.y,ray.origin.z,ray.direction.x,ray.direction.y,ray.direction.z);
					auto hit_mesh = [&](const MeshInstance &item) {
						float first = std::numeric_limits<float>::infinity();
						auto cross = [](Vec3 a,Vec3 b) { return Vec3{a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; };
						for (size_t t = 0; t < item.mesh->size(); t += 3) {
							Vec3 a = ResolveInstanceVertex((*item.mesh)[t],item.data).position;
							Vec3 b = ResolveInstanceVertex((*item.mesh)[t+1],item.data).position-a;
							Vec3 c = ResolveInstanceVertex((*item.mesh)[t+2],item.data).position-a;
							Vec3 h = cross(ray.direction,c), s = ray.origin-a;
							float det = Dot(b,h);
							if (std::abs(det) < 1e-8f) continue;
							float u = Dot(s,h)/det;
							Vec3 q = cross(s,b);
							float v = Dot(ray.direction,q)/det, distance = Dot(c,q)/det;
							if (u >= 0 && v >= 0 && u+v <= 1 && distance > 0) first = std::min(first,distance);
						}
						return first;
					};
					float bore_hit = std::numeric_limits<float>::infinity();
					for (const auto &item : isolated.instances) if (lining_meshes.contains(item.mesh)) bore_hit = std::min(bore_hit,hit_mesh(item));
					Debug(driver,1,"OpenTT3D: overlap CPU distances terrain {}, lining {}",hit_mesh(instance),bore_hit);
					break;
				}
			}
			throw std::runtime_error(fmt::format("Live tunnel view {}: {} lining pixels, {} covered by terrain/scenery",view,lining,covered));
		}
		checked_pixels += lining;
	}
	unsigned culling_views = 0;
	size_t omitted_vertices = 0;
	for (float position : {7.0f,12.0f,(length+16)*0.5f,length-4,length+9}) for (unsigned turn = 0; turn < 4; ++turn) {
		Camera camera{origin+TunnelPoint(direction,{position,8,6}),1,640,360,direction+0.5f+turn};
		camera.first_person = true; camera.vertical_fov = 40; camera.pitch = turn%2 == 0 ? 0 : 12; camera.tunnel_entrance = entrance.base();
		auto world = [&](bool culled) {
			for (unsigned attempt = 0; ; ++attempt) {
				try { BeginCapture(camera,true,culled); CollectViewport3D(Viewport{}); return FinishCapture(); }
				catch (const AtlasFull &) { if (IsCapturing()) FinishCapture(); if (attempt != 0) throw; Textures().Repack(); }
				catch (...) { if (IsCapturing()) FinishCapture(); throw; }
			}
		};
		Scene reference = world(false), actual = world(true);
		std::vector<uint8_t> expected, pixels;
		std::vector<uint32_t> expected_ids, ids;
		if (!RenderScene(reference,camera,expected,&expected_ids) || !RenderScene(actual,camera,pixels,&ids)) throw std::runtime_error("Tunnel scenery culling comparison did not render");
		if (pixels != expected || ids != expected_ids) {
			WriteReviewImage(directory/fmt::format("tunnel-scenery-failed-{}-full.pam",culling_views),camera,expected);
			WriteReviewImage(directory/fmt::format("tunnel-scenery-failed-{}-culled.pam",culling_views),camera,pixels);
			throw std::runtime_error("Tunnel scenery culling changed exact world colour or picking");
		}
		if (actual.VertexCount() > reference.VertexCount()) throw std::runtime_error("Tunnel scenery culling added geometry");
		omitted_vertices += reference.VertexCount()-actual.VertexCount();
		++culling_views;
	}
	Debug(driver,1,"OpenTT3D: {} live tunnel scenery culling views preserve exact RGBA and picking across both mouths, four headings and tilted Cab; {} hidden submitted vertices omitted",culling_views,omitted_vertices);
	for (const auto &state : vehicles) if (state.vehicle->x_pos != state.x || state.vehicle->y_pos != state.y || state.vehicle->z_pos != state.z || state.vehicle->direction != state.direction || state.vehicle->vehstatus != state.flags) throw std::runtime_error("Tunnel rendering changed vehicle gameplay state");
	Debug(driver,1,"OpenTT3D: live tunnel hint, {} unobstructed lining pixels and unchanged vehicle state passed",checked_pixels);
}

static Scene FenceReviewScene(unsigned style, Slope slope, const Camera &camera, bool show_ground = false, std::optional<unsigned> layout = {})
{
	TileInfo tile{};
	tile.tile = TileXY(1,1);
	tile.tileh = slope;
	BeginCapture(camera,true);
	try {
		if (show_ground) {
			if (IsHalftileSlope(slope)) {
				TileInfo lower = tile;
				lower.tileh = RemoveHalftileSlope(slope);
				CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(lower.tileh),PAL_NONE,0,0,0,lower,nullptr,0,0);
				CaptureFoundation(lower,HalftileFoundation(GetHalftileSlopeCorner(slope)));
			}
			Slope chart = IsHalftileSlope(slope) ? SlopeWithThreeCornersRaised(OppositeCorner(GetHalftileSlopeCorner(slope))) : slope;
			CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(chart),PAL_NONE,0,0,0,tile,nullptr,0,0);
		}
		SpriteID material = style == 6 ? SPR_TRACK_FENCE_FLAT_X : _clear_land_fence_sprites[style];
		if (layout) {
			CaptureFence(tile,style,*layout,material,material,PAL_NONE);
		} else if (style == 6) {
			for (unsigned layout : {0U,1U,8U,9U}) CaptureFence(tile,style,layout,material,material,PAL_NONE);
		} else {
			for (unsigned edge = 0; edge < 4; ++edge) CaptureFence(tile,style,edge,material,material,PAL_NONE);
		}
	} catch (...) {
		FinishCapture();
		throw;
	}
	Scene scene = FinishCapture();
	scene.vertices.clear(); // A diagnostic assembly does not include the world's exterior ocean.
	for (auto &instance : scene.instances) {
		if (!instance.mesh->empty() && (static_cast<uint32_t>(instance.mesh->front().surface)&15U) == static_cast<uint32_t>(SurfaceMode::Palette)) instance.data.SetObjectId(131);
	}
	return scene;
}

static Camera FenceReviewCamera(Slope slope, unsigned turn, float scale = 6, int size = 640)
{
	Camera camera{{8,8,6},scale,size,size,turn+0.25f};
	if (turn >= 4) {
		camera.first_person = true; camera.rotation = turn-4+1.5f; camera.pitch = 4; camera.vertical_fov = 40;
		Vec3 back = camera.Unrotate({Camera::INV_SQRT2,Camera::INV_SQRT2,0});
		camera.focus = Vec3{8,8,0}+back*36;
		camera.focus.z = MakeTileSurface(slope).Height(std::clamp(camera.focus.x,0.0f,16.0f),std::clamp(camera.focus.y,0.0f,16.0f))+6;
	}
	return camera;
}

void ExportFenceGallery(unsigned style, unsigned slope, std::optional<unsigned> layout)
{
	Slope terrain = static_cast<Slope>(slope), lower = RemoveHalftileSlope(terrain);
	bool valid = lower < 15 || lower == SLOPE_STEEP_W || lower == SLOPE_STEEP_S || lower == SLOPE_STEEP_E || lower == SLOPE_STEEP_N;
	if (slope >= 32) valid &= IsHalftileSlope(terrain) && HasSlopeHighestCorner(lower) && GetHalftileSlopeCorner(terrain) == GetHighestSlopeCorner(lower) && style == 6 && layout.has_value();
	if (style > 6 || slope > 255 || !valid || (layout && (style != 6 || *layout > 15))) throw std::runtime_error("Invalid fence gallery style, slope or layout");
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned turn = 0; turn < 8; ++turn) {
		Camera camera = FenceReviewCamera(static_cast<Slope>(slope),turn);
		Scene scene = FenceReviewScene(style,static_cast<Slope>(slope),camera,true,layout);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Fence gallery rendering failed");
		std::string name = layout ? fmt::format("model-fence-{}-layout-{}-{}.pam",style,*layout,turn) : fmt::format("model-fence-{}-{}.pam",style,turn);
		std::ofstream file(directory/name,std::ios::binary);
		file << "P7\nWIDTH 640\nHEIGHT 640\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = 639; y >= 0; --y) file.write(reinterpret_cast<const char *>(pixels.data()+y*640*4),640*4);
	}
	Debug(driver,1,"OpenTT3D: exported fence {} slope {} model gallery{}",style,slope,layout ? fmt::format(" layout {}",*layout) : "");
}

void VerifyFenceModels()
{
	unsigned views = 0;
	auto verify = [&](unsigned style, Slope slope, const Camera &camera, std::optional<unsigned> layout = {}) {
		Scene scene = FenceReviewScene(style,slope,camera,false,layout);
		std::vector<uint8_t> pixels;
		std::vector<uint32_t> ids;
		if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),131) < (camera.pixels_per_unit >= 2 ? 16 : 2)) throw std::runtime_error(fmt::format("Fence {} slope {} layout {} turn {} failed GPU visibility",style,to_underlying(slope),layout.value_or(16),camera.rotation));
		for (const auto &instance : scene.instances) {
			if (instance.mesh->empty() || (static_cast<uint32_t>(instance.mesh->front().surface)&15U) != static_cast<uint32_t>(SurfaceMode::Palette)) throw std::runtime_error("Fence retained a non-voxel material surface");
		}
		if (style == 1) {
			/* Check the single palette volume against the former hedge/gate
			 * partitions without unrelated equal-depth perimeter intersections. */
			const Vec3 corners[] = {{0,0,0},{16,0,0},{16,16,0},{0,16,0}};
			const unsigned edges[][2] = {{0,3},{3,2},{1,2},{0,1}};
			float scale = camera.PixelScaleAt({8,8,3});
			unsigned lod = scale >= 1.25f ? 0 : scale >= 0.35f ? 1 : 2;
			if (scene.instances.size() != 4) throw std::runtime_error("Gate fence retained redundant instance partitions");
			Scene all_partitions;
			for (unsigned edge = 0; edge < 4; ++edge) {
				Scene one, partitions;
				one.instances.push_back(scene.instances[edge]);
				for (unsigned component : {1U,2U}) for (const auto &vertex : MakeFenceMesh(1,corners[edges[edge][0]],corners[edges[edge][1]],MakeTileSurface(slope),false,component,lod)) {
					partitions.vertices.push_back(ResolveInstanceVertex(vertex,scene.instances[edge].data));
				}
				std::vector<uint8_t> a,b; std::vector<uint32_t> ai,bi;
				if (!RenderScene(one,camera,a,&ai) || !RenderScene(partitions,camera,b,&bi) || a != b || ai != bi) throw std::runtime_error(fmt::format("Unified gate differs from partitioned reference: slope {} edge {} turn {} lod {}",to_underlying(slope),edge,camera.rotation,lod));
				all_partitions.vertices.insert(all_partitions.vertices.end(),partitions.vertices.begin(),partitions.vertices.end());
			}
			std::vector<uint8_t> reference; std::vector<uint32_t> reference_ids;
			if (!RenderScene(all_partitions,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error(fmt::format("Gate perimeter differs from partitioned reference: slope {} turn {} lod {}",to_underlying(slope),camera.rotation,lod));
			if (slope == SLOPE_FLAT && camera.width == 192 && camera.rotation == 0.25f) {
				size_t vertices = 0;
				for (const auto &instance : scene.instances) vertices += instance.mesh->size();
				Debug(driver,1,"OpenTT3D: flat gate perimeter LOD {}: {} unified vertices / {} partitioned reference vertices; 4 instead of 8 instances",lod,vertices,all_partitions.vertices.size());
			}
		}
		if (layout && (*layout == 2 || *layout == 3 || *layout == 10 || *layout == 11)) {
			Corner corner = *layout == 2 ? CORNER_W : *layout == 3 ? CORNER_N : *layout == 10 ? CORNER_E : CORNER_S;
			float base = TerrainZ(GetSlopePixelZInCorner(RemoveHalftileSlope(slope),corner));
			for (const auto &instance : scene.instances) {
				float low = INFINITY, high = -INFINITY;
				for (const auto &vertex : *instance.mesh) { low = std::min(low,vertex.position.z); high = std::max(high,vertex.position.z); }
				if (low != base || high != base+5) throw std::runtime_error("Diagonal railway fence lost its upstream corner height");
			}
		}
		Scene expanded;
		/* Perimeter edges retain their captured order at equal-depth corners,
		 * independently of the allocation order of the cached meshes. */
		expanded.vertices = scene.ExpandedVertices(true);
		std::vector<uint8_t> reference;
		std::vector<uint32_t> reference_ids;
		if (!RenderScene(expanded,camera,reference,&reference_ids)) throw std::runtime_error("Voxel fence CPU expansion rendering failed");
		if (pixels != reference || ids != reference_ids) {
			size_t colours = 0, picks = 0;
			for (size_t pixel = 0; pixel < ids.size(); ++pixel) {
				colours += !std::equal(pixels.begin()+pixel*4,pixels.begin()+pixel*4+4,reference.begin()+pixel*4);
				picks += ids[pixel] != reference_ids[pixel];
			}
			unsigned isolated_mismatches = 0;
			for (const auto &instance : scene.instances) {
				Scene one, cpu; one.instances = {instance}; cpu.vertices = one.ExpandedVertices(true);
				std::vector<uint8_t> a,b; std::vector<uint32_t> ai,bi;
				if (!RenderScene(one,camera,a,&ai) || !RenderScene(cpu,camera,b,&bi) || a != b || ai != bi) ++isolated_mismatches;
			}
			throw std::runtime_error(fmt::format("Voxel fence {} slope {} layout {} turn {} scale {} differs: {} colour pixels, {} IDs, {} isolated instance mismatches",style,to_underlying(slope),layout.value_or(16),camera.rotation,camera.pixels_per_unit,colours,picks,isolated_mismatches));
		}
		for (auto &instance : scene.instances) instance.data.origin_opacity[3] = 0.38f;
		if (!RenderScene(scene,camera,reference,&reference_ids) || std::ranges::any_of(reference_ids,[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent voxel fence intercepted picking");
		++views;
	};
	for (unsigned style = 0; style < 7; ++style) for (unsigned slope = 0; slope < 32; ++slope) {
		if (slope >= 15 && slope != 23 && slope != 27 && slope != 29 && slope != 30) continue;
		for (float scale : {2.0f,0.75f,0.2f}) for (unsigned turn = 0; turn < 4; ++turn) {
			if (slope != 0 && scale != 2) continue;
			Camera camera{{8,8,6},scale,192,192,turn+0.25f};
			verify(style,static_cast<Slope>(slope),camera);
		}
	}
	/* Every upstream RFO slot, plus all four raised/steep half-tile and
	 * three-corner boundary cases. The old perimeter-only gallery missed these. */
	const Slope layout_slopes[] = {SLOPE_FLAT,SLOPE_FLAT,SLOPE_FLAT,SLOPE_FLAT,SLOPE_SW,SLOPE_SE,SLOPE_NE,SLOPE_NW,
		SLOPE_FLAT,SLOPE_FLAT,SLOPE_FLAT,SLOPE_FLAT,SLOPE_SW,SLOPE_SE,SLOPE_NE,SLOPE_NW};
	std::vector<std::pair<Slope,unsigned>> cases;
	for (unsigned layout = 0; layout < std::size(layout_slopes); ++layout) cases.emplace_back(layout_slopes[layout],layout);
	const unsigned diagonal_layouts[] = {2,11,10,3}; // Corner order W,S,E,N.
	for (Corner corner : {CORNER_W,CORNER_S,CORNER_E,CORNER_N}) {
		for (Slope slope : {HalftileSlope(SlopeWithOneCornerRaised(corner),corner),HalftileSlope(SteepSlope(corner),corner),SlopeWithThreeCornersRaised(OppositeCorner(corner))}) cases.emplace_back(slope,diagonal_layouts[corner]);
	}
	for (auto [slope,layout] : cases) for (unsigned turn = 0; turn < 8; ++turn) verify(6,slope,FenceReviewCamera(slope,turn,2,192),layout);
	for (Slope slope : {SLOPE_FLAT,SLOPE_SW}) for (unsigned turn = 0; turn < 8; ++turn) verify(1,slope,FenceReviewCamera(slope,turn));
	Debug(driver,1,"OpenTT3D: {} terrain-following fence views passed GPU visibility and picking; voxel palette/instances and transparent picking passed",views);
	Debug(driver,1,"OpenTT3D: all 16 railway fence layouts and 12 raised diagonal cases passed orbit/street and exact corner-height checks");
	Debug(driver,1,"OpenTT3D: unified gate meshes exactly match partitioned references in isolation and joined perimeters, including full-size orbit/street galleries");
}

static std::set<std::pair<Slope,Foundation>> FoundationCases()
{
	std::set<std::pair<Slope,Foundation>> result;
	for (unsigned value = 1; value < 32; ++value) {
		if (value >= 15 && value != 23 && value != 27 && value != 29 && value != 30) continue;
		Slope slope = static_cast<Slope>(value);
		result.emplace(slope,FOUNDATION_LEVELED);
		for (unsigned bits = 1; bits <= TRACK_BIT_ALL; ++bits) {
			Foundation foundation = GetRailFoundation(slope,static_cast<TrackBits>(bits));
			if (foundation != FOUNDATION_NONE && foundation != FOUNDATION_INVALID) result.emplace(slope,foundation);
		}
	}
	return result;
}

static Scene FoundationReviewScene(Slope slope, Foundation foundation, const Camera &camera, bool show_ground, bool house = false)
{
	TileInfo tile{};
	tile.tile = TileXY(1,1);
	tile.tileh = slope;
	BeginCapture(camera,true);
	try {
		if (show_ground) CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(slope),PAL_NONE,0,0,0,tile,nullptr,0,0);
		if (foundation == FOUNDATION_STEEP_BOTH) {
			Corner highest = GetHighestSlopeCorner(slope);
			DrawFoundation(&tile,FOUNDATION_STEEP_LOWER);
			DrawFoundation(&tile,HalftileFoundation(highest));
		} else DrawFoundation(&tile,foundation);
		if (show_ground) {
			Slope chart = IsHalftileSlope(tile.tileh) ? SlopeWithThreeCornersRaised(OppositeCorner(GetHalftileSlopeCorner(tile.tileh))) : tile.tileh;
			CaptureGround(SPR_FLAT_GRASS_TILE+SlopeToSpriteOffset(chart),PAL_NONE,0,0,tile.z,tile,nullptr,0,0);
		}
	} catch (...) {
		FinishCapture();
		throw;
	}
	Scene scene = FinishCapture();
	scene.vertices.clear();
	if (show_ground && scene.instances.size() < 3) throw std::runtime_error("Foundation review did not capture its ground and retaining walls");
	size_t end = scene.instances.size()-(show_ground ? 1 : 0);
	for (size_t i = show_ground ? 1 : 0; i < end; ++i) scene.instances[i].data.SetObjectId(137);
	if (house) DrawVoxelAsset(scene,"houses",2,3,{0,0,TerrainZ(tile.z)});
	return scene;
}

static Camera FoundationReviewCamera(unsigned view, float scale, int size, bool context = false)
{
	Camera camera{{8,8,context ? 16.0f : 8.0f},scale,size,size,view+0.25f};
	if (view >= 4) {
		camera.first_person = true; camera.rotation = view-4+1.5f; camera.pitch = context ? -8 : 0; camera.vertical_fov = 40;
		camera.focus = Vec3{8,8,6}+camera.Unrotate({Camera::INV_SQRT2,Camera::INV_SQRT2,0})*(context ? 60 : 36);
	}
	return camera;
}

void ExportFoundationGallery(unsigned slope, unsigned foundation)
{
	if (!FoundationCases().contains({static_cast<Slope>(slope),static_cast<Foundation>(foundation)})) throw std::runtime_error("Invalid foundation/slope review combination");
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	nlohmann::json cases = nlohmann::json::array();
	for (auto [s,f] : FoundationCases()) cases.push_back({{"slope",to_underlying(s)},{"foundation",to_underlying(f)}});
	std::ofstream(directory/"foundation-cases.json") << cases.dump(2) << '\n';
	unsigned tracks = 0;
	if (foundation != FOUNDATION_LEVELED) for (unsigned bits = 1; bits <= TRACK_BIT_ALL; ++bits) {
		if (GetRailFoundation(static_cast<Slope>(slope),static_cast<TrackBits>(bits)) == foundation) { tracks = bits; break; }
	}
	for (unsigned turn = 0; turn < 8; ++turn) for (bool context : {false,true}) {
		Camera camera = FoundationReviewCamera(turn,context ? 3 : 6,640,context);
		Scene scene = context && tracks != 0 ? RailReviewScene(RAILTYPE_RAIL,static_cast<TrackBits>(tracks),static_cast<Slope>(slope),camera,true) :
			FoundationReviewScene(static_cast<Slope>(slope),static_cast<Foundation>(foundation),camera,true,context && foundation == FOUNDATION_LEVELED);
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Foundation gallery rendering failed");
		std::ofstream file(directory/fmt::format("model-foundation-{}-slope-{}-{}{}.pam",foundation,slope,context ? "context-" : "",turn),std::ios::binary);
		file << "P7\nWIDTH 640\nHEIGHT 640\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = 639; y >= 0; --y) file.write(reinterpret_cast<const char *>(pixels.data()+y*640*4),640*4);
	}
	Debug(driver,1,"OpenTT3D: exported foundation {} slope {} model gallery",foundation,slope);
}

void VerifyFoundationModels()
{
	unsigned views = 0;
	for (auto [slope,foundation] : FoundationCases()) {
		size_t visible_pixels = 0;
		for (float scale : {3.0f,0.6f,0.15f}) for (unsigned turn = 0; turn < (scale == 3 ? 8U : 4U); ++turn) {
			Camera camera = FoundationReviewCamera(turn,scale,256);
			Scene scene = FoundationReviewScene(slope,foundation,camera,false);
			std::vector<uint8_t> pixels, reference;
			std::vector<uint32_t> ids, reference_ids;
			if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("Voxel foundation rendering failed");
			size_t visible = std::count(ids.begin(),ids.end(),137);
			visible_pixels += visible;
			float front_area = 0;
			for (const auto &instance : scene.instances) {
				if (instance.mesh->empty() || (static_cast<uint32_t>(instance.mesh->front().surface)&15U) != static_cast<uint32_t>(SurfaceMode::Palette)) throw std::runtime_error("Foundation retained a non-voxel material");
				for (size_t i = 0; i < instance.mesh->size(); i += 3) {
					Vertex a = ResolveInstanceVertex((*instance.mesh)[i],instance.data), b = ResolveInstanceVertex((*instance.mesh)[i+1],instance.data), c = ResolveInstanceVertex((*instance.mesh)[i+2],instance.data);
					if (Dot(a.normal,camera.Eye()-a.position) <= 0) continue;
					auto pa = camera.Project(a.position), pb = camera.Project(b.position), pc = camera.Project(c.position);
					if (pa.visible && pb.visible && pc.visible) front_area += std::abs((pb.x-pa.x)*(pc.y-pa.y)-(pc.x-pa.x)*(pb.y-pa.y))*0.5f;
				}
			}
			if (scale == 3 && front_area > 8 && visible == 0) throw std::runtime_error(fmt::format("Foundation {} slope {} turn {} lost an exposed outward wall",to_underlying(foundation),to_underlying(slope),turn));
			Scene expanded;
			expanded.vertices = scene.ExpandedVertices(true);
			if (!RenderScene(expanded,camera,reference,&reference_ids) || pixels != reference || ids != reference_ids) throw std::runtime_error("Voxel foundation CPU instance colour/picking mismatch");
			if (turn == 0) {
				Scene cells;
				Slope current = slope;
				float base = 0;
				size_t part = 0;
				auto append = [&](Foundation f) {
					Slope upper = current;
					float rise = TerrainZ(ApplyPixelFoundationToSlope(f,upper));
					float detail = camera.PixelScaleAt({8,8,base+4});
					unsigned lod = detail >= 1.25f ? 0 : detail >= 0.35f ? 1 : 2;
					auto unit = MakeFoundationMesh(MakeTileSurface(current),MakeTileSurface(upper),rise,lod,false,false);
					if (!unit.empty()) {
						if (part >= scene.instances.size()) throw std::runtime_error("Foundation reference part is missing");
						for (const auto &v : unit) cells.vertices.push_back(ResolveInstanceVertex(v,scene.instances[part].data));
						++part;
					}
					current = upper; base += rise;
				};
				if (foundation == FOUNDATION_STEEP_BOTH) { append(FOUNDATION_STEEP_LOWER); append(HalftileFoundation(GetHighestSlopeCorner(slope))); }
				else append(foundation);
				if (!RenderScene(cells,camera,reference,&reference_ids)) throw std::runtime_error("Foundation unit-cell reference rendering failed");
				if (pixels != reference || ids != reference_ids) {
					size_t colours = 0, picks = 0;
					for (size_t pixel = 0; pixel < ids.size(); ++pixel) {
						colours += !std::equal(pixels.begin()+pixel*4,pixels.begin()+pixel*4+4,reference.begin()+pixel*4);
						picks += ids[pixel] != reference_ids[pixel];
					}
					auto directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR))/"renderer3d-reference";
					std::filesystem::create_directories(directory);
					WriteReviewImage(directory/"foundation-mismatch-merged.pam",camera,pixels);
					WriteReviewImage(directory/"foundation-mismatch-cells.pam",camera,reference);
					throw std::runtime_error(fmt::format("Foundation {} slope {} scale {} differs from unit-cell geometry: {} colour pixels, {} IDs",to_underlying(foundation),to_underlying(slope),scale,colours,picks));
				}
			}
			for (auto &instance : scene.instances) instance.data.origin_opacity[3] = 0.38f;
			if (!RenderScene(scene,camera,reference,&reference_ids) || std::ranges::any_of(reference_ids,[](uint32_t id) { return id != 0; })) throw std::runtime_error("Transparent foundation intercepted picking");
			++views;
		}
		if (visible_pixels < 8) throw std::runtime_error("Foundation has no visible retaining-wall volume");
	}
	Debug(driver,1,"OpenTT3D: {} foundation views passed GPU visibility and picking; voxel palettes, CPU instances, unit-cell geometry and transparency passed",views);
}

/** Review geometry uses the same table slots/origins as DrawBridgeMiddle.
 * It deliberately has no map mutation or bridge-building commands. */
static Scene BridgeReviewScene(unsigned type, unsigned transport, bool along_y, bool sloped)
{
	Scene scene;
	const BridgePieces pieces[] = {BRIDGE_PIECE_NORTH, BRIDGE_PIECE_INNER_NORTH, BRIDGE_PIECE_MIDDLE_EVEN, BRIDGE_PIECE_INNER_SOUTH, BRIDGE_PIECE_SOUTH};
	auto point = [&](float x, float y, float z) { return along_y ? Vec3{y,x,z} : Vec3{x,y,z}; };
	for (unsigned tile = 0; tile < std::size(pieces); ++tile) {
		unsigned piece = to_underlying(pieces[tile]);
		auto sprites = GetBridgeSpriteTable(type, pieces[tile]).subspan(transport * 8 + (along_y ? 4 : 0), 3);
		BridgeCaptureInfo info{{type,piece,BridgeRole::Deck,along_y,0,false},point(tile*16,0,24),false};
		DrawCapturedBridge(scene,info,sprites[0].sprite,sprites[0].pal,info.origin+Vec3{0,0,-3},0,false,nullptr);
		info.shape.role = BridgeRole::Front;
		if ((sprites[1].sprite & SPRITE_MASK) != 0) DrawCapturedBridge(scene,info,sprites[1].sprite,sprites[1].pal,info.origin+point(0,12,-3),0,false,nullptr);
		if ((sprites[2].sprite & SPRITE_MASK) == 0) continue;
		info.shape.role = BridgeRole::Pillar;
		for (float y : {3.0f,12.0f}) for (int z = 21; z >= 0; z -= 8) {
			DrawCapturedBridge(scene,info,sprites[2].sprite,sprites[2].pal,point(tile*16,y,z),0,false,nullptr);
		}
	}
	for (unsigned end = 0; end < 2; ++end) {
		unsigned direction = along_y ? (end == 0 ? 1 : 3) : (end == 0 ? 2 : 0);
		const unsigned offsets[] = {2,1,0,3};
		auto sprite = GetBridgeSpriteTable(type,BRIDGE_PIECE_HEAD)[transport*8 + offsets[direction] + (sloped ? 4 : 0)];
		BridgeCaptureInfo info{{type,BRIDGE_PIECE_HEAD,BridgeRole::Ramp,along_y,direction,sloped},point(end == 0 ? -16 : 80,0,24),false};
		DrawCapturedBridge(scene,info,sprite.sprite,sprite.pal,info.origin+Vec3{0,0,-8},0,false,nullptr);
	}
	return scene;
}

void ExportBridgeModelGallery(unsigned type)
{
	std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
	std::filesystem::create_directories(directory);
	for (unsigned rotation = 0; rotation < 4; ++rotation) {
		Textures().BeginScene();
		Scene scene = BridgeReviewScene(type,0,false,true);
		Camera camera{{40,8,TerrainZ(24)},2,640,640,rotation + 0.2f};
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Bridge gallery GPU rendering failed");
		std::ofstream file(directory / fmt::format("model-bridge-{:02}-{}.pam",type,rotation),std::ios::binary);
		file << "P7\nWIDTH 640\nHEIGHT 640\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n";
		for (int y = 639; y >= 0; --y) file.write(reinterpret_cast<const char *>(pixels.data()+y*640*4),640*4);
	}
	for (bool overhead : {false,true}) {
		Textures().BeginScene();
		Scene scene = BridgeReviewScene(type,3,false,false);
		Camera camera{{40,8,TerrainZ(24)},2,640,480,0.2f};
		camera.pitch = 90;
		if (!overhead) {
			camera.first_person = true; camera.focus = {40,-4,TerrainZ(16)+6}; camera.rotation = 1.5f; camera.pitch = 0; camera.vertical_fov = 40;
			scene.Quad({32,-32,TerrainZ(16)},{48,-32,TerrainZ(16)},{48,48,TerrainZ(16)},{32,48,TerrainZ(16)},{0.18f,0.19f,0.18f});
		}
		std::vector<uint8_t> pixels;
		if (!RenderScene(scene,camera,pixels)) throw std::runtime_error("Bridge overhead/underpass gallery failed");
		WriteReviewImage(directory/fmt::format("model-bridge-{:02}-{}.pam",type,overhead ? "top" : "underpass"),camera,pixels);
	}
	Debug(driver,1,"OpenTT3D: exported bridge {} model gallery",type);
}

void VerifyBridgeModels()
{
	unsigned views = 0;
	std::vector<uint8_t> pixels;
	std::vector<uint32_t> ids;
	for (unsigned type = 0; type < MAX_BRIDGES; ++type) for (unsigned transport = 0; transport < 4; ++transport) for (bool along_y : {false,true}) for (bool sloped : {false,true}) {
		Textures().BeginScene();
		Scene scene = BridgeReviewScene(type,transport,along_y,sloped);
		if (scene.instances.empty()) throw std::runtime_error("Bridge has no authored assembly");
		for (auto &instance : scene.instances) instance.data.SetObjectId(103);
		for (unsigned turn = 0; turn < 4; ++turn) {
			Camera camera{along_y ? Vec3{8,40,TerrainZ(24)} : Vec3{40,8,TerrainZ(24)},0.8f,256,256,turn + 0.2f};
			if (!RenderScene(scene,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),103) < 32) throw std::runtime_error(fmt::format("Bridge {} transport {} axis {} view {} failed visibility/picking",type,transport,along_y,turn));
			if (type == 0 && transport == 0 && sloped) {
				/* Opaque batching may choose either colour at coincident component
				 * joins. Compare material transforms per component, where the expected
				 * colour is unambiguous, in addition to the assembly ID check above. */
				for (size_t part = 0; part < scene.instances.size(); ++part) {
					Scene isolated, expanded;
					isolated.instances = {scene.instances[part]};
					expanded.vertices = isolated.ExpandedVertices(true);
					std::vector<uint8_t> reference_pixels;
					std::vector<uint32_t> reference_ids;
					if (!RenderScene(isolated,camera,pixels,&ids) || !RenderScene(expanded,camera,reference_pixels,&reference_ids) || pixels != reference_pixels || ids != reference_ids) {
						unsigned colours = 0, picks = 0;
						for (size_t i = 0; i < ids.size() && i < reference_ids.size(); ++i) {
							if (ids[i] != reference_ids[i]) ++picks;
							if (!std::equal(pixels.data()+i*4,pixels.data()+i*4+4,reference_pixels.data()+i*4)) ++colours;
						}
						throw std::runtime_error(fmt::format("Bridge part {} axis {} view {} differs from expanded geometry: {} colour pixels, {} IDs",part,along_y,turn,colours,picks));
					}
				}
			}
			++views;
		}
		Scene overhead = scene;
		for (auto &instance : overhead.instances) if (instance.data.origin_opacity[2] < TerrainZ(24)) {
			instance.data.SetObjectId(104);
			for (const auto &v : *instance.mesh) if (v.position.z+instance.data.origin_opacity[2] > TerrainZ(24)-BRIDGE_DECK_THICKNESS*0.5f+0.0001f) {
				throw std::runtime_error("Bridge pillar cap reaches the running surface");
			}
		}
		Camera top{along_y ? Vec3{8,40,TerrainZ(24)} : Vec3{40,8,TerrainZ(24)},0.8f,256,256,0.2f};
		top.pitch = 90;
		if (!RenderScene(overhead,top,pixels,&ids) || std::count(ids.begin(),ids.end(),104) != 0) throw std::runtime_error("Bridge pillars are visible through the deck from above");
	}
	/* Half-pillars are upstream sprite crops. From a turned camera their ID
	 * footprints must still partition the full column, with no stray post. */
	Textures().BeginScene();
	for (bool along_y : {false,true}) {
		auto sprite = GetBridgeSpriteTable(0,BRIDGE_PIECE_NORTH)[along_y ? 6 : 2];
		BridgeCaptureInfo info{{0,0,BridgeRole::Pillar,along_y,0,false},{},false};
		const SubSprite halves_x[] = {{-14,-1000,1000,1000},{-1000,-1000,-15,1000}};
		const SubSprite halves_y[] = {{-1000,-1000,15,1000},{16,-1000,1000,1000}};
		Scene full, halves;
		DrawCapturedBridge(full,info,sprite.sprite,sprite.pal,{},0,false,nullptr);
		for (const auto &sub : along_y ? halves_y : halves_x) DrawCapturedBridge(halves,info,sprite.sprite,sprite.pal,{},0,false,&sub);
		for (Scene *scene : {&full,&halves}) for (auto &instance : scene->instances) instance.data.SetObjectId(107);
		for (unsigned turn = 0; turn < 4; ++turn) {
			Camera camera{along_y ? Vec3{1,8,0} : Vec3{8,1,0},3,192,192,turn + 0.37f};
			std::vector<uint8_t> reference_pixels;
			std::vector<uint32_t> reference_ids;
			if (!RenderScene(full,camera,reference_pixels,&reference_ids) || !RenderScene(halves,camera,pixels,&ids) || ids != reference_ids) throw std::runtime_error("Bridge half-pillar clipping changed column coverage");
		}
		for (auto &instance : full.instances) instance.data.origin_opacity[3] = 0.38f;
		Camera camera{along_y ? Vec3{1,8,0} : Vec3{8,1,0},3,192,192,0.37f};
		if (!RenderScene(full,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),107) != 0) throw std::runtime_error("Transparent bridge intercepted picking");
	}
	Debug(driver,1,"OpenTT3D: {} bridge assembly views, half-pillar clipping and transparent picking passed",views);
	Debug(driver,1,"OpenTT3D: bridge pillar caps remain below the deck with zero overhead picking pixels");
}

/** Exercise nonzero shared-buffer offsets, page growth and a mesh larger than
 * the regular pool page. Degenerate prefix triangles leave a small visible
 * independent reference while forcing real GPU uploads of each requested size. */
static void VerifyMeshStorage()
{
	static const std::array<std::vector<Vertex>,5> meshes = [] {
		std::array<std::vector<Vertex>,5> result;
		const size_t bytes[] = {1024,2*1024*1024-200,2*1024*1024+520,20*1024*1024+920,2700};
		for (size_t i = 0; i < result.size(); ++i) {
			Scene face;
			face.Quad({-3,-3,0},{3,-3,0},{3,3,0},{-3,3,0},{0.2f+0.15f*i,0.9f-0.1f*i,0.3f+0.1f*i});
			result[i].assign((bytes[i]/(3*sizeof(Vertex))+1)*3,face.vertices.front());
			/* One exact vertex per degenerate triangle: the largest indexed
			 * payload still exceeds a pool page and needs indices above 65535. */
			for (size_t vertex = 0; vertex < result[i].size(); ++vertex) result[i][vertex].company_colour = static_cast<float>(vertex/3);
			result[i].insert(result[i].end(),face.vertices.begin(),face.vertices.end());
		}
		return result;
	}();
	Scene instanced;
	for (size_t i = 0; i < meshes.size(); ++i) {
		InstanceData record;
		record.origin_opacity = {(static_cast<float>(i)-2)*10,0,static_cast<float>(i%2)*2,i == 4 ? 0.38f : 1};
		record.SetObjectId(i == 2 ? TILE_PICK_ID | 0xFFFFFFU : 300+i);
		instanced.instances.push_back({&meshes[i],record});
	}
	Scene reference;
	reference.vertices = instanced.ExpandedVertices();
	std::vector<uint8_t> pixels, reference_pixels;
	std::vector<uint32_t> ids, reference_ids;
	Vulkan::MeshCacheStats uploaded;
	for (unsigned view = 0; view < 4; ++view) {
		Camera camera{{0,0,0},2,256,256,view*0.5f};
		if (!RenderScene(reference,camera,reference_pixels,&reference_ids) || !RenderScene(instanced,camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) {
			throw std::runtime_error("GPU verification: shared-buffer offsets or large mesh uploads changed colour/picking");
		}
		for (unsigned i = 0; i < 4; ++i) {
			uint32_t id = i == 2 ? TILE_PICK_ID | 0xFFFFFFU : 300+i;
			if (std::count(ids.begin(),ids.end(),id) == 0) throw std::runtime_error("GPU verification: pooled mesh disappeared");
		}
		if (std::count(ids.begin(),ids.end(),304) != 0) throw std::runtime_error("GPU verification: pooled transparent mesh intercepted picking");
		if (Vulkan::Active()) {
			auto usage = Vulkan::GetMeshCacheStats();
			if (view == 0) uploaded = usage;
			else if (usage != uploaded) throw std::runtime_error("GPU verification: cached mesh reuse grew the persistent pool");
		}
	}
	if (Vulkan::Active()) {
		if (uploaded.buffers < 2 || (uploaded.pooled ? uploaded.buffers >= uploaded.meshes : uploaded.buffers != uploaded.meshes) || uploaded.used_bytes > uploaded.capacity_bytes) {
			throw std::runtime_error("GPU verification: persistent mesh pool did not share/grow its storage");
		}
		if (IndexImmutableMeshes() && (uploaded.indexed_meshes == 0 || uploaded.stored_vertices >= uploaded.source_vertices || uploaded.index_bytes == 0)) throw std::runtime_error("GPU verification: immutable meshes did not retain indexed vertex reuse");
		Debug(driver,1,"OpenTT3D: Vulkan {} mesh storage holds {} meshes in {} buffers ({} / {} bytes)",uploaded.pooled ? "pooled" : "unpooled",uploaded.meshes,uploaded.buffers,uploaded.used_bytes,uploaded.capacity_bytes);
	}
	Debug(driver,1,"OpenTT3D: GPU multi-mesh storage, large uploads and reuse preserve colour and picking");
	/* Reuse the same vector objects for changed payloads. A pointer-keyed cache
	 * would silently draw the first payload and retain every temporary reference. */
	size_t persistent_count = PersistentMeshCount();
	auto usage = Vulkan::GetMeshCacheStats();
	std::array<std::vector<Vertex>,5> temporary;
	for (unsigned change = 0; change < 8; ++change) {
		temporary = meshes;
		/* Strictly increasing CPU-expanded uploads used to leave every smaller
		 * oversized frame-arena page resident, even after synchronous readback. */
		Vertex padding = temporary[0].front();
		temporary[0].insert(temporary[0].begin(),((change+1)*2*1024*1024/(3*sizeof(Vertex)))*3,padding);
		Scene transient = instanced;
		transient.persistent_meshes = false;
		for (size_t i = 0; i < temporary.size(); ++i) {
			for (auto &vertex : temporary[i]) {
				vertex.position.z += change*0.75f;
				vertex.colour.r = 0.05f+change*0.1f;
			}
			transient.instances[i].mesh = &temporary[i];
		}
		Scene expected;
		expected.vertices = transient.ExpandedVertices();
		Camera camera{{0,0,0},2,256,256,change*0.5f};
		if (!RenderScene(expected,camera,reference_pixels,&reference_ids) || !RenderScene(transient,camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) {
			throw std::runtime_error("GPU verification: transient mesh address reuse changed geometry, colour or picking");
		}
		if (PersistentMeshCount() != persistent_count || Vulkan::GetMeshCacheStats() != usage) throw std::runtime_error("GPU verification: transient mesh references grew persistent storage");
		if (Vulkan::Active()) {
			auto arena = Vulkan::GetReadbackArenaStats();
			if (arena.capacity_bytes > arena.largest_bytes+Vulkan::READBACK_ARENA_SCRATCH_BYTES) throw std::runtime_error("GPU verification: completed Vulkan uploads retained historical oversized arena pages");
		}
	}
	Debug(driver,1,"OpenTT3D: 8 transient mesh payloads preserve exact instancing and address reuse without persistent cache growth");
	if (Vulkan::Active()) {
		auto arena = Vulkan::GetReadbackArenaStats();
		Debug(driver,1,"OpenTT3D: increasing Vulkan readback uploads retain {} bytes in {} pages, largest {} bytes, with exact colour and picking",arena.capacity_bytes,arena.buffers,arena.largest_bytes);
	}
	/* Force cold-page retirement between exact multi-mesh captures. This covers
	 * nonzero shared-page offsets, both index widths and transparent ownership
	 * after reuploading the same immutable CPU identities. */
	for (unsigned view = 0; view < 4; ++view) {
		Camera camera{{0,0,0},2,256,256,view*0.5f};
		if (!RenderScene(reference,camera,reference_pixels,&reference_ids)) throw std::runtime_error("GPU verification: residency reference failed");
		size_t before = PersistentMeshCount();
		TrimMeshCache(0);
		if (PersistentMeshCount() >= before) throw std::runtime_error("GPU verification: completed cold mesh storage did not retire");
		if (!RenderScene(instanced,camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: retired mesh reupload changed exact colour or picking");
	}
	Debug(driver,1,"OpenTT3D: 4 cold mesh retirement/reupload views preserve exact geometry, colour, transparency and picking");
}

/** One shared mesh, interleaved opaque/transparent records, overlapping colours and
 * values on both sides of the shader's opacity boundary. Compare with the original
 * unpartitioned vertex stream so a batch split cannot silently change painter order. */
static void VerifyInstanceOpacityPartitions()
{
	static const std::vector<Vertex> mesh = [] {
		Scene face;
		face.Quad({-4,-4,0},{4,-4,0},{4,4,0},{-4,4,0},{1,1,1});
		for (auto &vertex : face.vertices) {
			vertex.texture = {204.5f/256,0.5f,-3};
			vertex.surface = static_cast<SurfaceMode>(static_cast<uint32_t>(SurfaceMode::Palette)|SURFACE_UNLIT);
		}
		return face.vertices;
	}();
	constexpr float opacities[] = {0.38f,1.0f,0.989f,0.99f,0.62f,0.0f,1.0f};
	Scene instanced, expanded;
	for (unsigned i = 0; i < std::size(opacities); ++i) {
		InstanceData record;
		record.origin_opacity = {(static_cast<int>(i)-3)*1.5f,static_cast<float>(i%2),6.0f+i*0.125f,opacities[i]};
		UsePaletteMaterial(record,PALETTE_RECOLOUR_START+i*2);
		record.SetObjectId(400+i);
		instanced.instances.push_back({&mesh,record});
	}
	expanded.vertices = instanced.ExpandedVertices(true);
	for (unsigned view = 0; view < 4; ++view) {
		Camera camera{{0,0,6},8,256,256,view*0.5f+0.15f};
		std::vector<uint8_t> pixels, reference;
		std::vector<uint32_t> ids, reference_ids;
		if (!RenderScene(instanced,camera,pixels,&ids) || !RenderScene(expanded,camera,reference,&reference_ids)) throw std::runtime_error("GPU verification: opacity batch probe render failed");
		if (pixels != reference || ids != reference_ids) {
			size_t colour_changes = 0, id_changes = 0;
			for (size_t i = 0; i < ids.size(); ++i) {
				colour_changes += std::memcmp(pixels.data()+i*4,reference.data()+i*4,4) != 0;
				id_changes += ids[i] != reference_ids[i];
			}
			throw std::runtime_error(fmt::format("GPU verification: opacity batch partition changed colour, painter order or picking (view {}, {} colour pixels, {} IDs)",view,colour_changes,id_changes));
		}
		if (std::ranges::none_of(ids,[](uint32_t id) { return id >= 400 && id <= 406; })) throw std::runtime_error("GPU verification: opacity partition probe is not visible");
		for (unsigned i = 0; i < std::size(opacities); ++i) if (opacities[i] < 0.99f && std::count(ids.begin(),ids.end(),400+i) != 0) throw std::runtime_error("GPU verification: a partitioned transparent instance intercepted picking");
	}
	Debug(driver,1,"OpenTT3D: mixed-opacity shared-mesh batches preserve exact unpartitioned colour order and picking across the 0.99 boundary");
}

static void VerifyOrderedChildInstances()
{
	static const std::array<std::vector<Vertex>,2> meshes = [] {
		std::array<std::vector<Vertex>,2> result;
		for (unsigned i = 0; i < result.size(); ++i) {
			Scene face;
			face.Quad({-4,-4,0},{4,-4,0},{4,4,0},{-4,4,0},i == 0 ? Rgb{0.1f,0.7f,1} : Rgb{0.8f,0.2f,0.1f});
			result[i] = std::move(face.vertices);
		}
		return result;
	}();
	unsigned views = 0;
	for (bool same_mesh : {false,true}) for (bool child_first : {false,true}) for (unsigned state = 0; state < 3; ++state) for (float turn : {0.15f,1.4f}) {
		InstanceData parent, child;
		parent.SetObjectId(TILE_PICK_ID|0xFFFFFFU);
		child.SetChildLayer(true); child.SetObjectId(827);
		if (state == 1) child.origin_opacity[2] = -1;
		if (state == 2) child.origin_opacity[3] = 0.38f;
		Scene actual, reference;
		actual.instances = {{&meshes[same_mesh ? 0 : 1],parent},{&meshes[0],child}};
		if (child_first) std::reverse(actual.instances.begin(),actual.instances.end());
		reference.vertices = actual.ExpandedVertices();
		Camera camera{{},8,256,256,turn};
		std::vector<uint8_t> pixels, expected;
		std::vector<uint32_t> ids, expected_ids;
		if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("GPU verification: ordered child batches changed exact colour or picking");
		uint32_t winner = state == 0 ? 827 : TILE_PICK_ID|0xFFFFFFU;
		if (ids[128*256+128] != winner) throw std::runtime_error("GPU verification: a child lost its coincident order, bypassed depth, or intercepted transparent picking");
		++views;
	}
	Debug(driver,1,"OpenTT3D: {} ordered child-layer views preserve coincident priority, ordinary depth, opacity and complete picking IDs",views);
}

/** Heap layout must not choose which of two coincident surfaces owns a pixel.
 * The two immutable pairs have opposite allocation order but identical art. */
static void VerifyMeshAllocationOrder()
{
	static const std::array<std::vector<Vertex>,4> meshes = [] {
		std::array<std::vector<Vertex>,4> result;
		for (unsigned i = 0; i < result.size(); ++i) {
			Scene face;
			face.Quad({-4,-4,0},{4,-4,0},{4,4,0},{-4,4,0},i == 0 || i == 3 ? Rgb{0.8f,0.2f,0.1f} : Rgb{0.1f,0.7f,1});
			result[i] = std::move(face.vertices);
		}
		return result;
	}();
	unsigned views = 0;
	for (bool reverse_allocation : {false,true}) for (bool reverse_submission : {false,true}) for (bool child : {false,true}) for (float opacity : {1.0f,0.38f}) for (float turn : {0.15f,1.4f}) {
		InstanceData first, second;
		first.SetObjectId(TILE_PICK_ID|0xFFFFFFU); second.SetObjectId(731);
		first.SetChildLayer(child); second.SetChildLayer(child);
		first.origin_opacity[3] = opacity; second.origin_opacity[3] = opacity;
		Scene actual, reference;
		actual.instances = {{&meshes[reverse_allocation ? 3 : 0],first},{&meshes[reverse_allocation ? 2 : 1],second}};
		if (reverse_submission) std::reverse(actual.instances.begin(),actual.instances.end());
		reference.vertices = actual.ExpandedVertices();
		Camera camera{{},8,256,256,turn};
		std::vector<uint8_t> pixels, expected;
		std::vector<uint32_t> ids, expected_ids;
		if (!RenderScene(actual,camera,pixels,&ids) || !RenderScene(reference,camera,expected,&expected_ids) || pixels != expected || ids != expected_ids) throw std::runtime_error("GPU verification: mesh allocation order changed coplanar colour or picking");
		uint32_t winner = opacity == 1 ? actual.instances.back().data.ObjectId() : 0;
		if (ids[128*256+128] != winner) throw std::runtime_error("GPU verification: stable mesh order lost coplanar ownership or transparent click-through");
		++views;
	}
	Debug(driver,1,"OpenTT3D: {} allocation-order views preserve coplanar colour, opacity and picking independently of mesh addresses",views);
}

void VerifyInstanceOrdering()
{
	VerifyTextureMipCache();
	VerifyOrderedChildInstances();
	VerifyMeshAllocationOrder();
	VerifyInstanceOpacityPartitions();
	VerifyMeshStorage();
	OpenGL::VerifyPresentation();
}

void VerifyGPUScene(bool vehicle_poses)
{
	VerifyTextureMipCache();
	VerifyOrderedChildInstances();
	VerifyMeshAllocationOrder();
	VerifyVoxelModels(vehicle_poses);
	Textures().BeginScene();
	Scene scene;
	scene.Quad({-20,-20,0},{20,-20,0},{20,20,0},{-20,20,0},{1,0,0});
	for (auto &v:scene.vertices) v.object_id=17;
	size_t first=scene.vertices.size();
	scene.Quad({-20,-20,4},{20,-20,4},{20,20,4},{-20,20,4},{0,1,0});
	for (size_t i=first;i<scene.vertices.size();++i) scene.vertices[i].object_id=29;
	Camera camera{{0,0,0},2,256,256,0};
	std::vector<uint8_t> pixels;
	std::vector<uint32_t> ids;
	if (!RenderScene(scene,camera,pixels,&ids)) throw std::runtime_error("GPU verification: mesh pass failed");
	size_t center=128*256+128;
	if (ids[center]!=29 || pixels[center*4+1]<=pixels[center*4]) throw std::runtime_error("GPU verification: depth and picking disagree");
	/* Compare uneven crops against the full frame, including seam pixels. */
	std::vector<uint8_t> cropped_pixels;
	std::vector<uint32_t> cropped_ids;
	for (int top = 0; top < camera.height; top += 59) {
		for (int left = 0; left < camera.width; left += 73) {
			Camera tile = camera.Cropped(left, top, std::min(73, camera.width - left), std::min(59, camera.height - top));
			if (!RenderScene(scene, tile, cropped_pixels, &cropped_ids)) throw std::runtime_error("GPU verification: cropped rendering failed");
			for (int y = 0; y < tile.height; ++y) {
				for (int x = 0; x < tile.width; ++x) {
					size_t original = static_cast<size_t>(camera.height - 1 - top - y) * camera.width + left + x;
					size_t cropped = static_cast<size_t>(tile.height - 1 - y) * tile.width + x;
					if (ids[original] != cropped_ids[cropped] || !std::equal(pixels.data() + original * 4, pixels.data() + original * 4 + 4, cropped_pixels.data() + cropped * 4)) {
						throw std::runtime_error("GPU verification: tiled colour or picking seam");
					}
				}
			}
		}
	}
	Debug(driver, 1, "OpenTT3D: tiled GPU rendering matches the full framebuffer");
	const uint8_t opaque_green = pixels[center * 4 + 1];
	first=scene.vertices.size();
	scene.Quad({-20,-20,8},{20,-20,8},{20,20,8},{-20,20,8},{0,0,1});
	for (size_t i=first;i<scene.vertices.size();++i) { scene.vertices[i].object_id=43; scene.vertices[i].opacity=0.4f; }
	if (!RenderScene(scene,camera,pixels,&ids) || ids[center]!=29) throw std::runtime_error("GPU verification: transparent geometry intercepts picking");
	if (pixels[center * 4 + 2] == 0 || pixels[center * 4 + 1] == 0 || pixels[center * 4 + 1] >= opaque_green) {
		throw std::runtime_error("GPU verification: translucent colour was not blended");
	}
	Debug(driver,1,"OpenTT3D: GPU depth, object picking and transparency verification passed");
	static const std::vector<Vertex> mesh = [] {
		Scene geometry;
		geometry.Quad({-9, -9, 0}, {9, -9, 0}, {9, 9, 0}, {-9, 9, 0}, {0.8f, 0.6f, 0.2f});
		return geometry.vertices;
	}();
	Scene instanced;
	InstanceData first_instance;
	first_instance.origin_opacity = {-6, 0, 0, 1};
	first_instance.identity[0] = 71;
	instanced.instances.push_back({&mesh, first_instance});
	InstanceData second_instance = first_instance;
	second_instance.origin_opacity = {6, 0, 4, 1};
	second_instance.scale_center = {0.75f, 1.5f, 1, -1};
	second_instance.mirror_layer_heading[3] = 0.25f;
	second_instance.identity[0] = 83;
	instanced.instances.push_back({&mesh, second_instance});
	Scene expanded;
	expanded.vertices = instanced.ExpandedVertices();
	std::vector<uint8_t> reference_pixels;
	std::vector<uint32_t> reference_ids;
	if (!RenderScene(expanded, camera, reference_pixels, &reference_ids) || !RenderScene(instanced, camera, pixels, &ids)) throw std::runtime_error("GPU verification: instance rendering failed");
	if (pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: instance transform or picking differs from CPU reference");
	Debug(driver, 1, "OpenTT3D: GPU model instances match expanded geometry and object IDs");
	for (Vec3 origin : {Vec3{4761.8735f,171.68036f,0},Vec3{131000,64000,80}}) for (unsigned turn = 0; turn < 4; ++turn) {
		Scene world, local;
		world.Quad(origin+Vec3{-0.125f,-0.125f,0},origin+Vec3{0.125f,-0.125f,0},origin+Vec3{0.125f,0.125f,0},origin+Vec3{-0.125f,0.125f,0},{0.25f,0.75f,0.5f});
		for (auto &vertex : world.vertices) vertex.object_id = TILE_PICK_ID | 613;
		local = world;
		for (auto &vertex : local.vertices) vertex.position = vertex.position-origin;
		Camera large{origin,256,256,256,static_cast<float>(turn)};
		large.vertical_fov = 40;
		large.focus_offset = {1.0f/2048,-1.0f/4096,1.0f/1024};
		Camera small = large;
		small.focus = large.focus_offset; small.focus_offset = {};
		if (!RenderScene(world,large,pixels,&ids) || !RenderScene(local,small,reference_pixels,&reference_ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: subpixel camera focus differs from local-coordinate reference");
		auto point = large.Project(origin);
		size_t pixel = static_cast<size_t>(255-static_cast<int>(point.y))*256+static_cast<int>(point.x);
		if (ids[pixel] != (TILE_PICK_ID | 613)) throw std::runtime_error("GPU verification: subpixel camera projection lost its picked surface");
	}
	Debug(driver,1,"OpenTT3D: 8 large-world subpixel-focus GPU views match local-coordinate colour and picking exactly");
	VerifyMeshStorage();
	VerifyInstanceOpacityPartitions();
	for (uint32_t tile : {0U,8388608U,16777214U,16777215U}) {
		Scene owned;
		InstanceData record;
		record.SetObjectId(TILE_PICK_ID | tile);
		owned.instances.push_back({&mesh,record});
		if (!RenderScene(owned,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),TILE_PICK_ID | tile) == 0) throw std::runtime_error("GPU verification: tile ID namespace lost map-index bits");
		owned.instances[0].data.SetObjectId(71);
		if (!RenderScene(owned,camera,pixels,&ids) || std::count(ids.begin(),ids.end(),71) == 0 || std::any_of(ids.begin(),ids.end(),[](uint32_t id) { return (id & TILE_PICK_ID) != 0; })) throw std::runtime_error("GPU verification: tile/vehicle instance namespaces leaked");
	}
	Debug(driver,1,"OpenTT3D: full 24-bit map indices and independent vehicle picking IDs passed");
	/* Force a material to move in the atlas, preserving its actual source pixels. */
	Textures().Get(1576, PAL_NONE, 0, true);
	Textures().BeginScene();
	static const std::vector<Vertex> terrain = [] {
		Scene geometry;
		geometry.Quad({0, 0, 0}, {16, 0, 0}, {16, 16, 0}, {0, 16, 0}, {});
		return geometry.vertices;
	}();
	Scene textured;
	auto material_instance = [&] {
		SpriteTexture texture = Textures().Get(SPR_FLAT_WATER_TILE, PAL_NONE, 0, true);
		Vec3 uv = texture.UV(-texture.x_offset, -texture.y_offset);
		InstanceData record;
		record.uv_transform = {uv.x, uv.y, ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE), uv.z};
		record.region = texture.Region();
		record.identity = {97, static_cast<float>(SurfaceMode::Opaque), 1, 0};
		textured.instances = {{&terrain, record}};
	};
	Camera texture_camera{{8, 8, 0}, 2, 256, 256, 0.35f};
	material_instance();
	if (!RenderScene(textured, texture_camera, reference_pixels, &reference_ids)) throw std::runtime_error("GPU verification: terrain instance failed");
	for (unsigned cycle = 0; cycle < 3; ++cycle) {
		Textures().Repack();
		material_instance();
		if (!RenderScene(textured, texture_camera, pixels, &ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: atlas repacking changed pixels or IDs");
	}
	Debug(driver, 1, "OpenTT3D: atlas relocation preserves textured terrain pixels and picking");
	static const std::vector<Vertex> explicit_mesh = [] {
		auto vertices = terrain;
		for (auto &vertex : vertices) vertex.texture = {2 * (vertex.position.y - vertex.position.x), vertex.position.x + vertex.position.y, 0};
		return vertices;
	}();
	textured.instances[0].mesh = &explicit_mesh;
	textured.instances[0].data.identity[3] = 1;
	textured.instances[0].data.mirror_layer_heading[3] = 0.43f;
	expanded.vertices = textured.ExpandedVertices();
	if (!RenderScene(expanded, texture_camera, reference_pixels, &reference_ids) || !RenderScene(textured, texture_camera, pixels, &ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: explicit vehicle UVs differ from expanded geometry");
	textured.instances[0].data.identity[3] = 2;
	expanded.vertices = textured.ExpandedVertices();
	if (!RenderScene(expanded, texture_camera, reference_pixels, &reference_ids) || !RenderScene(textured, texture_camera, pixels, &ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: authored sample coordinates differ from expanded geometry");
	static const std::vector<Vertex> normalized_mesh = [] {
		auto vertices = terrain;
		for (auto &vertex : vertices) vertex.texture = {vertex.position.x / 16, vertex.position.y / 16, -3};
		return vertices;
	}();
	textured.instances[0].mesh = &normalized_mesh;
	expanded.vertices = textured.ExpandedVertices();
	if (!RenderScene(expanded, texture_camera, reference_pixels, &reference_ids) || !RenderScene(textured, texture_camera, pixels, &ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: authored material crops differ from expanded geometry");
	static const std::vector<Vertex> shaded_mesh = [] {
		auto vertices = normalized_mesh;
		for (auto &vertex : vertices) vertex.normal = Normalize({0.5f,0.25f,0.83f});
		return vertices;
	}();
	textured.instances[0].mesh = &shaded_mesh;
	textured.instances[0].data.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::Opaque) | SURFACE_SHADED);
	expanded.vertices = textured.ExpandedVertices(true);
	if (!RenderScene(expanded,texture_camera,reference_pixels,&reference_ids) || !RenderScene(textured,texture_camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: shaded component materials differ from expanded geometry");
	static const std::vector<Vertex> repeating_mesh = [] {
		auto vertices = terrain;
		for (auto &vertex : vertices) vertex.texture = {vertex.position.x/4,-vertex.position.y/4,-1};
		return vertices;
	}();
	InstanceData full_chart = textured.instances[0].data;
	float width = (full_chart.region.right-full_chart.region.left)*ATLAS_SIZE, height = (full_chart.region.bottom-full_chart.region.top)*ATLAS_SIZE;
	float left = std::floor(width*0.45f), top = std::floor(height*0.45f);
	textured.instances[0].mesh = &repeating_mesh;
	textured.instances[0].data.identity[1] = static_cast<float>(static_cast<uint32_t>(SurfaceMode::RepeatingChart) | SURFACE_SHADED);
	textured.instances[0].data.identity[3] = 3;
	auto &crop = textured.instances[0].data.region;
	crop.left += left/ATLAS_SIZE; crop.top += top/ATLAS_SIZE;
	crop.right = crop.left+8.0f/ATLAS_SIZE; crop.bottom = crop.top+8.0f/ATLAS_SIZE;
	expanded.vertices = textured.ExpandedVertices(true);
	if (!RenderScene(expanded,texture_camera,reference_pixels,&reference_ids) || !RenderScene(textured,texture_camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) throw std::runtime_error("GPU verification: fragment-repeated material chart differs from expanded geometry");
	{
		Scene density = textured, density_reference;
		density.instances[0].data.identity[3] = 4;
		density.instances[0].data.uv_transform[0] = 0.5f;
		density.instances[0].data.uv_transform[1] = 2;
		density_reference.vertices = density.ExpandedVertices(true);
		if (!RenderScene(density_reference,texture_camera,reference_pixels,&reference_ids) || !RenderScene(density,texture_camera,pixels,&ids) || pixels != reference_pixels || ids != reference_ids) {
			throw std::runtime_error("GPU verification: world-texel density differs between CPU and GPU materials");
		}
	}
	/* The independent tiled reference binds the same cropped texture region.
	 * This retains crop-edge clamping and sprite-local interpolation precision. */
	TextureRegion selected{};
	auto tiled_vertices = ApplyMaterialChart(terrain,{{selected,selected,selected},{4,4},true});
	full_chart.region = crop;
	Scene tiled_reference;
	tiled_reference.instances = {{&tiled_vertices,full_chart}};
	/* Compare UV interpretation on identical triangles. Subdividing a large
	 * projected quad changes hardware subpixel rasterization/interpolation. */
	auto repeated_tiles = tiled_vertices;
	for (auto &vertex : repeated_tiles) vertex.texture = {vertex.position.x/4,-vertex.position.y/4,-1};
	Scene repeated_reference;
	repeated_reference.instances = {{&repeated_tiles,textured.instances[0].data}};
	/* Put reference texel boundaries between screen pixel centres. Different
	 * hardware interpolation of UVs offset by an integer period must not turn
	 * an exact nearest-neighbour tie into a false material mismatch. */
	Camera repeat_camera = texture_camera;
	repeat_camera.first_person = true; repeat_camera.pitch = 90; repeat_camera.rotation = 0.5f;
	repeat_camera.focus = {8,8,repeat_camera.FocalPixels()/(8*Camera::WORLD_Z_SCALE)};
	repeated_reference.instances[0].data.mirror_layer_heading[3] = 0;
	tiled_reference.instances[0].data.mirror_layer_heading[3] = 0;
	if (!RenderScene(repeated_reference,repeat_camera,pixels,&ids)) throw std::runtime_error("GPU verification: repeated reference failed to render");
	if (!RenderScene(tiled_reference,repeat_camera,reference_pixels,&reference_ids)) throw std::runtime_error("GPU verification: explicit repeated chart failed to render");
	if (pixels != reference_pixels || ids != reference_ids) {
		std::filesystem::path directory = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR,BASE_DIR)) / "renderer3d-reference";
		std::filesystem::create_directories(directory);
		WriteReviewImage(directory/"repeat-phase.pam",repeat_camera,pixels);
		WriteReviewImage(directory/"repeat-tiled.pam",repeat_camera,reference_pixels);
		size_t colour_differences = 0, id_differences = 0;
		for (size_t i = 0; i < ids.size(); ++i) {
			id_differences += ids[i] != reference_ids[i];
			colour_differences += !std::equal(pixels.begin()+i*4,pixels.begin()+i*4+4,reference_pixels.begin()+i*4);
		}
		throw std::runtime_error(fmt::format("GPU verification: fragment repeat differs from explicitly tiled component geometry ({} colour, {} ID pixels)",colour_differences,id_differences));
	}
	Debug(driver,1,"OpenTT3D: fragment-repeated component material charts preserve CPU/GPU colour and picking");
	Scene shadow_scene = scene;
	for (size_t i = first; i < shadow_scene.vertices.size(); ++i) shadow_scene.vertices[i].surface = SurfaceMode::Shadow;
	if (!RenderScene(shadow_scene, camera, pixels, &ids) || ids[center] != 29 || pixels[center * 4 + 2] != 0 || pixels[center * 4 + 1] >= opaque_green) throw std::runtime_error("GPU verification: vehicle shadow colour or click-through failed");
	Debug(driver, 1, "OpenTT3D: explicit vehicle UVs and non-pickable shadow materials passed");
	Camera far_camera{{0, 0, 24}, 1, 256, 256, 0};
	far_camera.first_person = true; far_camera.pitch = 0; far_camera.vertical_fov = 60;
	for (float distance : {8192.0f, 131072.0f, 1000000.0f}) {
		Scene far_scene;
		Vec3 right = far_camera.Unrotate(Camera::World(Camera::Right())) * (distance * 0.1f);
		Vec3 up = far_camera.Unrotate(Camera::World(far_camera.Up())) * (distance * 0.1f);
		for (unsigned layer = 0; layer < 2; ++layer) {
			Vec3 center_point = far_camera.ScreenRay(128, 128).At(distance + layer * 4);
			size_t begin = far_scene.vertices.size();
			far_scene.Quad(center_point - right - up, center_point + right - up, center_point + right + up, center_point - right + up, layer == 0 ? Rgb{0, 1, 0} : Rgb{1, 0, 0});
			for (size_t i = begin; i < far_scene.vertices.size(); ++i) far_scene.vertices[i].object_id = 101 + layer;
		}
		if (!RenderScene(far_scene, far_camera, pixels, &ids) || ids[center] != 101 || pixels[center * 4 + 1] <= pixels[center * 4]) throw std::runtime_error(fmt::format("GPU verification: distant geometry/depth/picking failed at {} world units", distance));
	}
	Textures().BeginScene();
	SpriteTexture ocean_texture = Textures().Get(SPR_FLAT_WATER_TILE, PAL_NONE, 0, true);
	Scene ocean;
	ocean.water = {ocean_texture.UV(-ocean_texture.x_offset, -ocean_texture.y_offset), ZOOM_BASE / (static_cast<float>(1U << ocean_texture.zoom) * ATLAS_SIZE)};
	ocean.Ocean(1, 1, ocean_texture.page, ocean_texture.Region());
	far_camera.focus = {0.5f, 0.5f, 32};
	for (unsigned yaw = 0; yaw < 4; ++yaw) {
		far_camera.rotation = yaw;
		if (!RenderScene(ocean, far_camera, pixels, &ids)) throw std::runtime_error("GPU verification: horizon ocean failed");
		size_t sky = (255 - 80) * 256 + 128, sea = (255 - 128) * 256 + 128;
		if (std::equal(pixels.data() + sky * 4, pixels.data() + sky * 4 + 3, pixels.data() + sea * 4)) throw std::runtime_error("GPU verification: ocean stops before the horizon");
	}
	Debug(driver, 1, "OpenTT3D: unlimited-distance GPU colour/depth/picking and infinite horizon ocean passed");
	if (Vulkan::Active() || OpenGL::Active()) {
		auto render = Vulkan::Active() ? Vulkan::RenderViewport : OpenGL::RenderViewport;
		auto pick = Vulkan::Active() ? Vulkan::ReadObjectId : OpenGL::ReadObjectId;
		auto forget = Vulkan::Active() ? Vulkan::ForgetViewport : OpenGL::ForgetViewport;
		static const int viewport_key = 0;
		for (auto size : {Point{256, 256}, Point{319, 197}, Point{96, 128}}) {
			camera.width = size.x; camera.height = size.y;
			if (!render(&viewport_key,scene,camera) || pick(&viewport_key,size.x/2,size.y/2) != 29) {
				throw std::runtime_error("GPU verification: resident viewport resize/picking failed");
			}
		}
		forget(&viewport_key);
		if (pick(&viewport_key,0,0) != 0) throw std::runtime_error("GPU verification: deleted viewport retained pick IDs");
		Debug(driver, 1, "OpenTT3D: GPU-resident viewport resize, single-pixel picking and retirement passed");
	}
	OpenGL::VerifyPresentation();
}

} // namespace Renderer3D
