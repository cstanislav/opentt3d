/* SPDX-License-Identifier: GPL-2.0-only */
#include "../stdafx.h"
#include "sdl2_vulkan_v.h"
#include "../renderer3d/vulkan_backend.h"
#include "../blitter/factory.hpp"
#include "../gfx_func.h"
#include "../error_func.h"
#include "../window_func.h"
#include <SDL.h>
#include <SDL_vulkan.h>

static FVideoDriver_SDL_Vulkan factory;

bool VideoDriver_SDL_Vulkan::CreateMainWindow(uint width, uint height, uint flags)
{
	return VideoDriver_SDL_Base::CreateMainWindow(width, height, flags | SDL_WINDOW_VULKAN);
}

std::optional<std::string_view> VideoDriver_SDL_Vulkan::Start(const StringList &parameters)
{
	if (BlitterFactory::GetCurrentBlitter()->GetScreenDepth() != 32) return "Vulkan requires a 32bpp blitter";
	auto failure = VideoDriver_SDL_Base::Start(parameters);
	if (failure) return failure;
	unsigned count = 0;
	if (!SDL_Vulkan_GetInstanceExtensions(this->sdl_window, &count, nullptr)) { this->Stop(); return "Could not query SDL Vulkan extensions"; }
	std::vector<const char *> extensions(count);
	if (!SDL_Vulkan_GetInstanceExtensions(this->sdl_window, &count, extensions.data()) || !Renderer3D::Vulkan::CreateInstance(extensions)) { this->Stop(); return "Could not create SDL Vulkan instance"; }
	VkSurfaceKHR surface = VK_NULL_HANDLE;
	if (!SDL_Vulkan_CreateSurface(this->sdl_window, Renderer3D::Vulkan::Instance(), &surface)) { this->Stop(); return "Could not create SDL Vulkan surface"; }
	if (!Renderer3D::Vulkan::SetSurface(surface)) { this->Stop(); return Renderer3D::Vulkan::LastError(); }
	this->driver_info = Renderer3D::Vulkan::Description();
	int width, height;
	SDL_Vulkan_GetDrawableSize(this->sdl_window, &width, &height);
	this->ClientSizeChanged(width, height, true);
	if (_screen.dst_ptr == nullptr) { this->Stop(); return "Could not allocate Vulkan UI buffer"; }
	return std::nullopt;
}

void VideoDriver_SDL_Vulkan::Stop()
{
	Renderer3D::Vulkan::Destroy();
	_screen.dst_ptr = nullptr;
	VideoDriver_SDL_Base::Stop();
}

bool VideoDriver_SDL_Vulkan::AllocateBackingStore(int width, int height, bool)
{
	if (!Renderer3D::Vulkan::Active()) return false;
	bool result = Renderer3D::Vulkan::Resize(width, height);
	_screen.dst_ptr = Renderer3D::Vulkan::VideoBuffer();
	this->dirty_rect = {};
	return result;
}

void *VideoDriver_SDL_Vulkan::GetVideoPointer() { return Renderer3D::Vulkan::VideoBuffer(); }
uint8_t *VideoDriver_SDL_Vulkan::GetAnimBuffer() { return Renderer3D::Vulkan::AnimationBuffer(); }

void VideoDriver_SDL_Vulkan::Paint()
{
	Blitter *blitter = BlitterFactory::GetCurrentBlitter();
	if (this->local_palette.count_dirty != 0 && blitter->UsePaletteAnimation() == Blitter::PaletteAnimation::Blitter) blitter->PaletteAnimate(this->local_palette);
	this->local_palette.count_dirty = 0;
	if (!Renderer3D::Vulkan::Present(blitter->NeedsAnimationBuffer())) FatalError("{}", Renderer3D::Vulkan::LastError());
	this->dirty_rect = {};
}
