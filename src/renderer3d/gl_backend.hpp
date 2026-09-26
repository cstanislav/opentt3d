/* SPDX-License-Identifier: GPL-2.0-only */
/** @file gl_backend.hpp GPU-resident viewports, UI composition and explicit GL readbacks. */

#ifndef RENDERER3D_GL_BACKEND_HPP
#define RENDERER3D_GL_BACKEND_HPP

#include "camera.hpp"
#include "../gfx_type.h"
#include <functional>
#include <string>

namespace Renderer3D {

bool HasOpenGLBackend();
bool HasRenderBackend();
int MaximumFramebufferSize();
std::string BackendDescription();
/** Diagnostic ownership check; transient references must never enter this cache. */
size_t PersistentMeshCount();
/** RGBA pixels, bottom row first. Caller composites into the upstream framebuffer. */
bool RenderScene(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels, std::vector<uint32_t> *picking = nullptr);
/** Called with the video driver's context current, before that context is destroyed. */
void DestroyOpenGLResources();

/** Interactive GL targets stay in the driver's rendering context. Only the completed
 * presentation texture crosses to Cocoa's shared layer context. */
namespace OpenGL {
using PresentationCapture = std::function<void(int, int, std::vector<Colour>)>;
bool Active();
/** Bound queued GPU work to two complete frames before mapping the next UI buffer. */
bool WaitForFrame();
unsigned FrameSlot();
void BeginFrame();
bool RenderViewport(const void *key, const Scene &scene, const Camera &camera);
void ComposeViewport(const void *key, int source_x, int source_y, int width, int height, int destination_x, int destination_y);
uint32_t ReadObjectId(const void *key, int x, int y);
void ForgetViewport(const void *key);
/** Called after uploading the original UI/animation planes. draw_ui uses the original
 * driver's shaders, with vertically flipped output to retain its top-down texture convention. */
bool PreparePresentation(int width, int height, const std::function<void()> &draw_ui);
uint32_t PresentationTexture();
void FinishPresentation();
bool CapturePresentation(PresentationCapture callback);
void VerifyPresentation();
}

} // namespace Renderer3D

#endif
