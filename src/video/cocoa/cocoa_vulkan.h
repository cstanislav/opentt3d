/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef VIDEO_COCOA_VULKAN_H
#define VIDEO_COCOA_VULKAN_H
#include "cocoa_v.h"
@class CAMetalLayer;

class VideoDriver_CocoaVulkan : public VideoDriver_Cocoa {
	CAMetalLayer *metal_layer = nil;
	std::string driver_info;
public:
	VideoDriver_CocoaVulkan() : VideoDriver_Cocoa(true) {}
	std::optional<std::string_view> Start(const StringList &parameters) override;
	void Stop() override;
	std::string_view GetName() const override { return "cocoa-vulkan"; }
	std::string_view GetInfoString() const override { return driver_info; }
	bool HasAnimBuffer() override { return true; }
	uint8_t *GetAnimBuffer() override;
	void AllocateBackingStore(bool force = false) override;
protected:
	void Paint() override;
	void CheckPaletteAnim() override;
	void *GetVideoPointer() override;
	void ReleaseVideoPointer() override {}
	NSView *AllocateDrawView() override;
};

class FVideoDriver_CocoaVulkan : public DriverFactoryBase {
public:
	FVideoDriver_CocoaVulkan() : DriverFactoryBase(Driver::DT_VIDEO, 10, "cocoa-vulkan", "OpenTT3D Vulkan/Metal video driver") {}
	std::unique_ptr<Driver> CreateInstance() const override { return std::make_unique<VideoDriver_CocoaVulkan>(); }
protected:
	bool UsesHardwareAcceleration() const override { return true; }
};
#endif
