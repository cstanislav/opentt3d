/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef RENDERER3D_AUTHORED_GEOMETRY_H
#define RENDERER3D_AUTHORED_GEOMETRY_H

#include "geometry.hpp"
#include "sprite_textures.hpp"

namespace Renderer3D {
bool DrawAuthoredHouse(Scene &scene, unsigned house, unsigned stage, const SpriteTexture &texture, Vec3 origin, Vec3 sprite_origin, float opacity, float pixel_scale = 4, unsigned variant = 0);
bool DrawAuthoredTree(Scene &scene, SpriteID image, const SpriteTexture &texture, Vec3 origin, float opacity, float pixel_scale = 4);
bool TreeHasComponentMaterials(SpriteID image);
void VerifyTreeModels();
bool HasAuthoredIndustry(unsigned graphics, SpriteID sprite);
bool DrawAuthoredIndustry(Scene &scene, unsigned graphics, SpriteID sprite, const SpriteTexture &texture, Vec3 origin, Vec3 sprite_origin, float opacity, float pixel_scale = 4);
bool DrawAuthoredVehicle(Scene &scene, unsigned engine, bool loaded, Vec3 origin, float heading, PaletteID palette, unsigned texture_zoom, float opacity = 1, const std::array<SpriteID, 8> *resolved = nullptr);
void ExportVehicleReferences();
void ExportVehicleModelGallery(unsigned engine, bool loaded);
void VerifyVehicleModels();
void VerifyIndustryModels();
}
#endif
