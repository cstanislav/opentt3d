/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "bridge_capture.h"
#include "world_capture.h"
#include "sprite_textures.hpp"
#include "../bridge_map.h"
#include "../viewport_func.h"
#include "../debug.h"
#include <map>
#include <tuple>

namespace Renderer3D {

static const BridgeCaptureInfo *bridge_capture = nullptr;

BridgeCaptureScope::BridgeCaptureScope(BridgeCaptureInfo value) : previous(bridge_capture), info(value)
{
	if (IsCapturing()) bridge_capture = &info;
}

BridgeCaptureScope::BridgeCaptureScope(BridgeRole role) : previous(bridge_capture)
{
	if (IsCapturing() && previous != nullptr) { info = *previous; info.shape.role = role; bridge_capture = &info; }
}

BridgeCaptureScope::~BridgeCaptureScope() { bridge_capture = previous; }
const BridgeCaptureInfo *CurrentBridgeCapture() { return bridge_capture; }

bool DrawCapturedBridge(Scene &scene, const BridgeCaptureInfo &info, SpriteID image, PaletteID palette, Vec3 sprite_origin, unsigned zoom, bool transparent, const SubSprite *sub)
{
	if (info.custom || info.shape.role == BridgeRole::None || info.shape.type > 13 || !IsBaseGraphicsSprite(image)) return false;
	BridgeShape shape = info.shape;
	if (shape.role == BridgeRole::Pillar) {
		/* The sprite's top cap used to coincide with the road/rail surface.
		 * Stop it inside the slab, retaining overlap at the support joint. */
		shape.pillar_top = std::min(shape.pillar_top,BridgePillarCap(info.origin.z,sprite_origin.z));
		if (shape.pillar_top <= -5) return true;
	}
	if (shape.role == BridgeRole::Pillar && sub != nullptr) {
		/* These upstream crops select whole north/south columns. Applying their
		 * 2D alpha rectangle to the 3D surface would shave off its rear faces. */
		shape.pillar_mask = 0;
		for (unsigned column = 0; column < 2; ++column) {
			float u = (shape.along_y ? 28.0f : -28.0f) * column;
			if (u >= sub->left && u <= sub->right) shape.pillar_mask |= 1U << column;
		}
		if (shape.pillar_mask == 0) return true;
	}
	using Key = std::tuple<unsigned, unsigned, BridgeRole, bool, unsigned, bool, unsigned, float>;
	static std::map<Key, std::vector<Vertex>> meshes;
	auto [found, inserted] = meshes.try_emplace(Key{shape.type,shape.piece,shape.role,shape.along_y,shape.ramp_direction,shape.sloped,shape.pillar_mask,shape.pillar_top});
	if (inserted) found->second = MakeBridgeMesh(shape);
	if (found->second.empty()) return true;
	Vec3 origin = shape.role == BridgeRole::Pillar ? sprite_origin : info.origin;
	if (scene.visibility && !scene.visibility->Intersects(origin + Vec3{-1,-1,-9},origin + Vec3{17,17,32})) return true;
	bool opaque = shape.role != BridgeRole::Surface;
	SpriteTexture texture = Textures().Get(image,palette,zoom,opaque);
	Vec3 relative = origin - sprite_origin;
	Vec3 uv = texture.UV(2 * (relative.y-relative.x) * ZOOM_BASE - texture.x_offset,(relative.x+relative.y-relative.z) * ZOOM_BASE - texture.y_offset);
	InstanceData data;
	data.origin_opacity = {origin.x,origin.y,origin.z,transparent ? 0.38f : 1};
	data.uv_transform = {uv.x,uv.y,ZOOM_BASE / (static_cast<float>(1U << texture.zoom) * ATLAS_SIZE),uv.z};
	data.region = texture.Region();
	data.identity = {0,static_cast<float>(opaque ? SurfaceMode::Opaque : SurfaceMode::Cutout),1,1};
	if (sub != nullptr && shape.role != BridgeRole::Pillar) {
		Vec3 start = texture.UV(sub->left * ZOOM_BASE - texture.x_offset,sub->top * ZOOM_BASE - texture.y_offset);
		Vec3 end = texture.UV((sub->right + 1) * ZOOM_BASE - texture.x_offset,(sub->bottom + 1) * ZOOM_BASE - texture.y_offset);
		data.region = {std::max(data.region.left,start.x),std::max(data.region.top,start.y),std::min(data.region.right,end.x),std::min(data.region.bottom,end.y)};
		data.identity[1] = static_cast<float>(SurfaceMode::Cutout);
		if (data.region.left >= data.region.right || data.region.top >= data.region.bottom) return true;
	}
	scene.instances.push_back({&found->second,data});
	return true;
}

bool FocusReferenceBridge()
{
	if (Map::Size() == 0) return false;
	for (uint y = 1; y < Map::MaxY(); ++y) for (uint x = 1; x < Map::MaxX(); ++x) {
		TileIndex tile = TileXY(x,y);
		if (!IsBridgeTile(tile)) continue;
		TileIndex end = GetOtherBridgeEnd(tile);
		TileIndex middle = TileXY((x+TileX(end))/2,(y+TileY(end))/2);
		ScrollMainWindowToTile(middle,true);
		Debug(driver,1,"OpenTT3D: focused live bridge at {},{}",TileX(middle),TileY(middle));
		return true;
	}
	return false;
}

} // namespace Renderer3D
