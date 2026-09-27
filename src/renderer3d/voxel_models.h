/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_VOXEL_MODELS_H
#define RENDERER3D_VOXEL_MODELS_H
#include "geometry.hpp"
#include "../gfx_type.h"

namespace Renderer3D {
bool HasVoxelAsset(std::string_view category, unsigned identifier, unsigned state);
bool HasVoxelAirport(unsigned graphics, unsigned frame);
/** The Toyland set supplies different terminal/hangar paint under the same IDs. */
inline bool AirportModelClimateSupported(unsigned graphics, unsigned climate)
{
	return climate < 4 && (climate != 3 || !((graphics >= 19 && graphics <= 28) || graphics == 43 || graphics == 47));
}
bool DrawVoxelAirportGround(Scene &scene, unsigned graphics, unsigned frame, Vec3 origin, PaletteID palette);
bool HasVoxelTree(SpriteID image);
bool UseVoxelTrees();
std::optional<unsigned> VoxelHouseState(unsigned house, unsigned stage, unsigned variant);
bool HasVoxelHouseGround(unsigned house);
std::optional<unsigned> VoxelHouseGroundState(unsigned house, unsigned stage, unsigned variant);
bool DrawVoxelHouseGround(Scene &scene, unsigned house, unsigned stage, unsigned variant, SpriteID image, Vec3 origin, PaletteID palette);
/** Known source-climate restrictions apply to both voxel and legacy profiles.
 * Forest16/17 and farm33..38 currently model temperate artwork only. Industry
 * ground3924 and oil-well ground2173 also have independently painted climate
 * replacements despite retaining the same source numbers. Toyland additionally
 * replaces bare soil2022, forest2077, rig4061, gold pools2257/2260/2261,
 * rig bodies26..28 and paper2206. Cotton-candy129/130 uses its distinct Toyland
 * replacements of2072..2077, never the other climates' forest artwork. Sweet
 * factory131..134 models Toyland2022 soil; battery135/136 and cola137 share cotton's2077 ground.
 * Toy-shop138..141 shares the factory's2022 soil. These bodies are unchanged across climates.
 * Body ownership is
 * independent, so an unsupported ground need not hide an unchanged body. */
inline bool IndustryModelClimateSupported(unsigned graphics, unsigned climate, bool ground = false, SpriteID sprite = 0)
{
	if (climate >= 4) return false;
	if (graphics == 129 || graphics == 130) return climate == 3;
	if (ground && ((graphics >= 131 && graphics <= 134) || (graphics >= 138 && graphics <= 141)) && sprite == 2022) return climate == 3;
	if (ground && graphics >= 135 && graphics <= 137 && sprite == 2077) return climate == 3;
	if (climate == 0) return true;
	if (graphics == 16 || graphics == 17 || (graphics >= 33 && graphics <= 38)) return false;
	if (ground) return sprite != 3924 && sprite != 2173 && (climate != 3 || (sprite != 2022 && sprite != 2077 && sprite != 4061 && sprite != 2257 && sprite != 2260 && sprite != 2261));
	return climate != 3 || !((graphics >= 26 && graphics <= 28) || (graphics == 67 && sprite == 2206));
}
std::optional<unsigned> VoxelIndustryState(unsigned graphics, SpriteID image, bool ground = false);
bool DrawVoxelIndustryGround(Scene &scene, unsigned graphics, SpriteID image, Vec3 origin, PaletteID palette);
bool DrawVoxelIndustrySpark(Scene &scene, SpriteID image, Vec3 origin, PaletteID palette = 0, float opacity = 1);
bool DrawVoxelHelicopterRotor(Scene &scene, SpriteID image, Vec3 origin, PaletteID palette = 0);
std::optional<Vec3> VoxelTrainCollectorMount(unsigned engine, unsigned part, float heading, float grade = 0, float contact_height = 10);
unsigned DrawVoxelTrainCollectors(Scene &scene, unsigned engine, Vec3 origin, float heading, PaletteID palette,
	std::array<float,2> contact_heights = {10,10}, float grade = 0);
/** Keep a collector's fixed roof mounting while moving only its upper frame. */
inline void FitVoxelCollectorToWire(InstanceData &data, float mount, float top, float contact, float contact_x = 0)
{
	float level = data.pitch[3]+(contact-data.pitch[3]-contact_x*data.pitch[1])/data.pitch[0];
	if (!std::isfinite(mount) || !std::isfinite(top) || !std::isfinite(level) || top <= mount || level <= mount) throw std::invalid_argument("Invalid voxel collector contact");
	float scale = (level-mount)/(top-mount);
	data.scale_center[1] = scale;
	Vec3 offset = PitchInstanceVector({0,0,mount*(1-scale)},data.pitch);
	data.origin_opacity[0] += offset.x*std::cos(data.mirror_layer_heading[3]);
	data.origin_opacity[1] += offset.x*std::sin(data.mirror_layer_heading[3]);
	data.origin_opacity[2] += offset.z;
}
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
struct VoxelTrainSupport { float rear, front, height, length_scale; std::span<const float> contact_x; };
std::optional<VoxelTrainSupport> VoxelTrainSupportBounds(unsigned engine, bool loaded, float heading);
bool DrawVoxelVehicle(Scene &scene, unsigned engine, bool loaded, Vec3 origin, float heading, PaletteID palette, float opacity = 1, unsigned climate = UINT_MAX, float grade = 0);
void VerifyVoxelModels(bool vehicle_poses = true);
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
