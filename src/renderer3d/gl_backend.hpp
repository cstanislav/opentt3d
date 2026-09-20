/* SPDX-License-Identifier: GPL-2.0-only */
/** @file gl_backend.hpp Offscreen 3D rendering using the active upstream GL context. */

#ifndef RENDERER3D_GL_BACKEND_HPP
#define RENDERER3D_GL_BACKEND_HPP

#include "camera.hpp"

namespace Renderer3D {

bool HasOpenGLBackend();
/** RGBA pixels, bottom row first. Caller composites into the upstream framebuffer. */
bool RenderScene(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels);
/** Called with the video driver's context current, before that context is destroyed. */
void DestroyOpenGLResources();

} // namespace Renderer3D

#endif
