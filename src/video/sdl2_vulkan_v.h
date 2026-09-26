/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef VIDEO_SDL2_VULKAN_H
#define VIDEO_SDL2_VULKAN_H
#include "sdl2_v.h"

class VideoDriver_SDL_Vulkan : public VideoDriver_SDL_Base {
public:
	VideoDriver_SDL_Vulkan() : VideoDriver_SDL_Base(true) {}
	std::optional<std::string_view> Start(const StringList &parameters) override;
	void Stop() override;
	std::string_view GetName() const override { return "sdl-vulkan"; }
	bool HasAnimBuffer() override { return true; }
	uint8_t *GetAnimBuffer() override;
protected:
	bool CreateMainWindow(uint width, uint height, uint flags) override;
	bool AllocateBackingStore(int width, int height, bool force) override;
	void *GetVideoPointer() override;
	void ReleaseVideoPointer() override {}
	void Paint() override;
};

class FVideoDriver_SDL_Vulkan : public DriverFactoryBase {
public:
	FVideoDriver_SDL_Vulkan() : DriverFactoryBase(Driver::DT_VIDEO, 11, "sdl-vulkan", "OpenTT3D SDL Vulkan video driver") {}
	std::unique_ptr<Driver> CreateInstance() const override { return std::make_unique<VideoDriver_SDL_Vulkan>(); }
protected:
	bool UsesHardwareAcceleration() const override { return true; }
};
#endif
