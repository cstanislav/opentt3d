/* SPDX-License-Identifier: GPL-2.0-only */
/** @file cocoa_vulkan.mm Native Cocoa input/windowing with a Vulkan Metal surface. */
#define VK_USE_PLATFORM_METAL_EXT
#include "../../stdafx.h"
#define Rect OTTDRect
#define Point OTTDPoint
#import <Cocoa/Cocoa.h>
#import <QuartzCore/CAMetalLayer.h>
#undef Rect
#undef Point
#include "cocoa_vulkan.h"
#include "cocoa_wnd.h"
#include "../../renderer3d/vulkan_backend.h"
#include "../../blitter/factory.hpp"
#include "../../gfx_func.h"
#include "../../error_func.h"
#include "../../palette_func.h"
#include "../../debug.h"

@interface OpenTT3DVulkanView : NSView
- (instancetype)initWithFrame:(NSRect)frame driver:(VideoDriver_CocoaVulkan *)driver;
@end

@implementation OpenTT3DVulkanView {
	VideoDriver_CocoaVulkan *driver;
}
- (instancetype)initWithFrame:(NSRect)frame driver:(VideoDriver_CocoaVulkan *)value
{
	if ((self = [super initWithFrame:frame])) {
		driver = value;
		[self setWantsLayer:YES];
		CAMetalLayer *metal = [CAMetalLayer layer];
		metal.opaque = YES;
		metal.framebufferOnly = YES;
		[self setLayer:metal];
	}
	return self;
}
- (void)setFrameSize:(NSSize)size
{
	[super setFrameSize:size];
	if (driver != nullptr) driver->AllocateBackingStore();
}
- (void)viewDidChangeBackingProperties
{
	[super viewDidChangeBackingProperties];
	if (driver != nullptr) driver->AllocateBackingStore();
}
@end

static FVideoDriver_CocoaVulkan factory;

std::optional<std::string_view> VideoDriver_CocoaVulkan::Start(const StringList &parameters)
{
	auto failure = this->Initialize();
	if (failure) return failure;
	if (BlitterFactory::GetCurrentBlitter()->GetScreenDepth() != 32) { this->Stop(); return "Vulkan requires a 32bpp blitter"; }
	const char *extensions[] = {VK_KHR_SURFACE_EXTENSION_NAME, VK_EXT_METAL_SURFACE_EXTENSION_NAME};
	if (!Renderer3D::Vulkan::CreateInstance(extensions)) { this->Stop(); return Renderer3D::Vulkan::LastError(); }
	bool fullscreen = _fullscreen;
	if (!this->MakeWindow(_cur_resolution.width, _cur_resolution.height)) { this->Stop(); return "Could not create Vulkan window"; }
	VkMetalSurfaceCreateInfoEXT surface_info{.sType = VK_STRUCTURE_TYPE_METAL_SURFACE_CREATE_INFO_EXT};
	surface_info.pLayer = this->metal_layer;
	VkSurfaceKHR surface = VK_NULL_HANDLE;
	VkResult result = vkCreateMetalSurfaceEXT(Renderer3D::Vulkan::Instance(), &surface_info, nullptr, &surface);
	if (result != VK_SUCCESS) { this->Stop(); return "Could not create Vulkan Metal surface"; }
	if (!Renderer3D::Vulkan::SetSurface(surface)) { this->Stop(); return Renderer3D::Vulkan::LastError(); }
	this->driver_info = Renderer3D::Vulkan::Description();
	this->AllocateBackingStore(true);
	if (fullscreen) this->QueueOnMainThread([this] { this->ToggleFullscreen(true); });
	this->GameSizeChanged();
	this->UpdateVideoModes();
	MarkWholeScreenDirty();
	this->is_game_threaded = !GetDriverParamBool(parameters, "no_threads") && !GetDriverParamBool(parameters, "no_thread");
	return std::nullopt;
}

void VideoDriver_CocoaVulkan::Stop()
{
	Renderer3D::Vulkan::Destroy();
	_screen.dst_ptr = nullptr;
	this->VideoDriver_Cocoa::Stop();
	this->metal_layer = nil;
}

NSView *VideoDriver_CocoaVulkan::AllocateDrawView()
{
	NSView *view = [[OpenTT3DVulkanView alloc] initWithFrame:this->cocoaview.bounds driver:this];
	this->metal_layer = (CAMetalLayer *)view.layer;
	return view;
}

void VideoDriver_CocoaVulkan::AllocateBackingStore(bool force)
{
	if (this->setup || this->window == nil || this->cocoaview == nil || !Renderer3D::Vulkan::Active()) return;
	NSRect rect = [this->cocoaview getRealRect:this->cocoaview.bounds];
	this->metal_layer.contentsScale = [this->cocoaview getContentsScale];
	this->metal_layer.drawableSize = CGSizeMake(rect.size.width, rect.size.height);
	if (!Renderer3D::Vulkan::Resize(static_cast<int>(rect.size.width), static_cast<int>(rect.size.height))) FatalError("{}", Renderer3D::Vulkan::LastError());
	if (this->buffer_locked) _screen.dst_ptr = Renderer3D::Vulkan::VideoBuffer();
	this->dirty_rect = {};
	this->GameSizeChanged();
	if (force) MarkWholeScreenDirty();
}

void *VideoDriver_CocoaVulkan::GetVideoPointer() { return Renderer3D::Vulkan::VideoBuffer(); }
uint8_t *VideoDriver_CocoaVulkan::GetAnimBuffer() { return Renderer3D::Vulkan::AnimationBuffer(); }

void VideoDriver_CocoaVulkan::CheckPaletteAnim()
{
	Palette palette;
	if (CopyPalette(palette, false) && BlitterFactory::GetCurrentBlitter()->UsePaletteAnimation() == Blitter::PaletteAnimation::Blitter) BlitterFactory::GetCurrentBlitter()->PaletteAnimate(palette);
}

void VideoDriver_CocoaVulkan::Paint()
{
	if (!Renderer3D::Vulkan::Present(BlitterFactory::GetCurrentBlitter()->NeedsAnimationBuffer())) FatalError("{}", Renderer3D::Vulkan::LastError());
	this->dirty_rect = {};
}
