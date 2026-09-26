/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_VOXEL_MODELS_H
#define RENDERER3D_VOXEL_MODELS_H
#include "geometry.hpp"
#include "../gfx_type.h"

namespace Renderer3D {
bool HasVoxelAsset(std::string_view category, unsigned identifier, unsigned state);
bool HasVoxelTree(SpriteID image);
std::optional<unsigned> VoxelHouseState(unsigned house, unsigned stage, unsigned variant);
bool HasVoxelHouseGround(unsigned house);
std::optional<unsigned> VoxelHouseGroundState(unsigned house, unsigned stage, unsigned variant);
bool DrawVoxelHouseGround(Scene &scene, unsigned house, unsigned stage, unsigned variant, SpriteID image, Vec3 origin, PaletteID palette);
std::optional<unsigned> VoxelIndustryState(unsigned graphics, SpriteID image, bool ground = false);
bool DrawVoxelIndustryGround(Scene &scene, unsigned graphics, SpriteID image, Vec3 origin, PaletteID palette);
bool DrawVoxelIndustrySpark(Scene &scene, SpriteID image, Vec3 origin, PaletteID palette = 0, float opacity = 1);
uint32_t VoxelPaletteMask(std::span<const Vertex> vertices, unsigned first, unsigned count);
bool DrawVoxelAsset(Scene &scene, std::string_view category, unsigned identifier, unsigned state,
	Vec3 origin, PaletteID palette = 0, float opacity = 1);
bool DrawVoxelHouseLift(Scene &scene, Vec3 origin, unsigned position, PaletteID palette = 0, float opacity = 1);
/** States0/1 are the shared cargo pair; optional climate*2+cargo pairs override it. */
inline std::optional<unsigned> SelectVoxelVehicleState(unsigned states, bool loaded, unsigned climate)
{
	if (climate >= 4) return {};
	unsigned cargo = loaded ? 1 : 0, state = climate*2+cargo;
	if ((states & (1U<<state)) != 0) return state;
	return (states & (1U<<cargo)) != 0 ? std::optional<unsigned>{cargo} : std::nullopt;
}
std::optional<unsigned> VoxelVehicleState(unsigned engine, bool loaded, unsigned climate = UINT_MAX);
/** Original train spacing uses eight map steps, rather than Euclidean arc length.
 * Preserve the authored diagonal proportions and leave three quarter-cells for
 * the couplers on an axial track. No simulation positions or lengths are changed. */
inline float OriginalTrainVoxelScale(float heading, float authored_length)
{
	if (!std::isfinite(heading) || !std::isfinite(authored_length) || authored_length <= 0) throw std::invalid_argument("Invalid original train voxel dimensions");
	return 7.25f/(std::max(std::abs(std::cos(heading)),std::abs(std::sin(heading)))*authored_length);
}
bool DrawVoxelVehicle(Scene &scene, unsigned engine, bool loaded, Vec3 origin, float heading, PaletteID palette, float opacity = 1, unsigned climate = UINT_MAX);
void VerifyVoxelModels();
void VerifyVoxelMeshes(std::string_view prefix = {});
void VerifyVoxelVehicleModels(unsigned only_engine = UINT_MAX);
void VerifyVoxelTreeModels();
void VerifyVoxelIndustryModels();
void ExportVoxelReviews(std::string_view prefix = {});
bool FocusVoxelAirport(unsigned graphics = UINT_MAX);
bool FocusVoxelHouseStage(unsigned stage, unsigned house = UINT_MAX, unsigned variant = UINT_MAX);
bool FocusVoxelTree(unsigned base, unsigned stage);
bool FocusVoxelVehicle(unsigned engine);
bool FocusVoxelIndustry(unsigned graphics, unsigned stage, bool ground = false);
}
#endif
