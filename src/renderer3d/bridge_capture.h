/* SPDX-License-Identifier: GPL-2.0-only */
/** @file bridge_capture.h Scoped presentation metadata from upstream bridge drawing. */
#ifndef RENDERER3D_BRIDGE_CAPTURE_H
#define RENDERER3D_BRIDGE_CAPTURE_H
#include "bridge_geometry.hpp"
#include "../sprite.h"
#include "../rail_type.h"

namespace Renderer3D {

struct BridgeCaptureInfo {
	BridgeShape shape;
	Vec3 origin;
	bool custom = false;
	RailType rail = INVALID_RAILTYPE;
	bool reserved = false;
};

class BridgeCaptureScope {
	const BridgeCaptureInfo *previous = nullptr;
	BridgeCaptureInfo info;
public:
	explicit BridgeCaptureScope(BridgeCaptureInfo info);
	explicit BridgeCaptureScope(BridgeRole role);
	~BridgeCaptureScope();
	BridgeCaptureScope(const BridgeCaptureScope &) = delete;
	BridgeCaptureScope &operator=(const BridgeCaptureScope &) = delete;
};

const BridgeCaptureInfo *CurrentBridgeCapture();
bool DrawCapturedBridge(Scene &scene, const BridgeCaptureInfo &info, SpriteID image, PaletteID palette, Vec3 sprite_origin, unsigned zoom, bool transparent, const SubSprite *sub);
void ExportBridgeModelGallery(unsigned type);
void VerifyBridgeModels();
bool FocusReferenceBridge();

} // namespace Renderer3D
#endif
