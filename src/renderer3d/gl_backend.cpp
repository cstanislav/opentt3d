/* SPDX-License-Identifier: GPL-2.0-only */
/** @file gl_backend.cpp Depth-tested mesh pass, isolated from upstream UI GL state. */

#include "../stdafx.h"
#include "gl_backend.hpp"
#include "../debug.h"

#ifdef WITH_OPENGL

#ifdef _WIN32
#include <windows.h>
#endif
#define GL_GLEXT_PROTOTYPES
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION
#include <OpenGL/gl3.h>
#else
#include <GL/gl.h>
#endif
#include "../3rdparty/opengl/glext.h"
#include "../video/opengl.h"

extern GetOGLProcAddressProc GetOGLProcAddress;

namespace Renderer3D {

#define R3D_GL_FUNCTIONS(X) \
	X(glGetIntegerv) X(glIsEnabled) X(glGetFloatv) X(glGetBooleanv) X(glGetError) \
	X(glGenFramebuffers) X(glBindFramebuffer) X(glDeleteFramebuffers) X(glCheckFramebufferStatus) \
	X(glGenRenderbuffers) X(glBindRenderbuffer) X(glRenderbufferStorage) X(glFramebufferRenderbuffer) X(glDeleteRenderbuffers) \
	X(glGenTextures) X(glDeleteTextures) X(glBindTexture) X(glTexImage2D) X(glTexParameteri) X(glFramebufferTexture2D) \
	X(glGenBuffers) X(glDeleteBuffers) X(glBindBuffer) X(glBufferData) \
	X(glGenVertexArrays) X(glDeleteVertexArrays) X(glBindVertexArray) \
	X(glCreateShader) X(glShaderSource) X(glCompileShader) X(glGetShaderiv) X(glGetShaderInfoLog) X(glDeleteShader) \
	X(glCreateProgram) X(glAttachShader) X(glBindAttribLocation) X(glLinkProgram) X(glGetProgramiv) X(glGetProgramInfoLog) X(glDeleteProgram) \
	X(glUseProgram) X(glGetUniformLocation) X(glUniform4f) X(glUniform2f) X(glUniform1f) \
	X(glEnableVertexAttribArray) X(glVertexAttribPointer) X(glViewport) X(glDisable) X(glEnable) \
	X(glClearColor) X(glClearDepth) X(glClear) X(glDepthFunc) X(glDepthMask) X(glColorMask) \
	X(glDrawArrays) X(glReadPixels) X(glPixelStorei) X(glActiveTexture)

#define DECLARE_GL(name) static decltype(&name) r_##name = nullptr;
R3D_GL_FUNCTIONS(DECLARE_GL)
#undef DECLARE_GL

static GLuint program = 0, framebuffer = 0, depth = 0, colour = 0, vertex_array = 0, vertex_buffer = 0;
static int buffer_width = 0, buffer_height = 0;
static bool functions_loaded = false, initialization_failed = false;

bool HasOpenGLBackend()
{
	return OpenGLBackend::Get() != nullptr && IsOpenGLVersionAtLeast(3, 2) && !initialization_failed;
}

static bool LoadFunctions()
{
	if (functions_loaded) return true;
#define LOAD_GL(name) \
	r_##name = reinterpret_cast<decltype(r_##name)>(GetOGLProcAddress(#name)); \
	if (r_##name == nullptr) { Debug(driver, 0, "OpenTT3D: missing OpenGL function " #name); return false; }
	R3D_GL_FUNCTIONS(LOAD_GL)
#undef LOAD_GL
	functions_loaded = true;
	return true;
}

/** The upstream driver keeps a mapped pixel-unpack buffer and several GL bindings. */
struct StateGuard {
	GLint draw_fbo, read_fbo, renderbuffer, vao, array_buffer, pack_buffer, unpack_buffer;
	GLint active_texture, texture, old_program, viewport[4], depth_func;
	GLint pack_alignment, pack_row_length, pack_skip_rows, pack_skip_pixels, unpack_alignment, unpack_row_length;
	GLfloat clear_colour[4], clear_depth;
	GLboolean depth_mask, colour_mask[4], depth_test, blend, cull, scissor, srgb;

	StateGuard()
	{
		r_glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw_fbo);
		r_glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read_fbo);
		r_glGetIntegerv(GL_RENDERBUFFER_BINDING, &renderbuffer);
		r_glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
		r_glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &array_buffer);
		r_glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &pack_buffer);
		r_glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING, &unpack_buffer);
		r_glGetIntegerv(GL_ACTIVE_TEXTURE, &active_texture);
		r_glActiveTexture(GL_TEXTURE0);
		r_glGetIntegerv(GL_TEXTURE_BINDING_2D, &texture);
		r_glGetIntegerv(GL_CURRENT_PROGRAM, &old_program);
		r_glGetIntegerv(GL_VIEWPORT, viewport);
		r_glGetIntegerv(GL_DEPTH_FUNC, &depth_func);
		r_glGetIntegerv(GL_PACK_ALIGNMENT, &pack_alignment);
		r_glGetIntegerv(GL_PACK_ROW_LENGTH, &pack_row_length);
		r_glGetIntegerv(GL_PACK_SKIP_ROWS, &pack_skip_rows);
		r_glGetIntegerv(GL_PACK_SKIP_PIXELS, &pack_skip_pixels);
		r_glGetIntegerv(GL_UNPACK_ALIGNMENT, &unpack_alignment);
		r_glGetIntegerv(GL_UNPACK_ROW_LENGTH, &unpack_row_length);
		r_glGetFloatv(GL_COLOR_CLEAR_VALUE, clear_colour);
		r_glGetFloatv(GL_DEPTH_CLEAR_VALUE, &clear_depth);
		r_glGetBooleanv(GL_DEPTH_WRITEMASK, &depth_mask);
		r_glGetBooleanv(GL_COLOR_WRITEMASK, colour_mask);
		depth_test = r_glIsEnabled(GL_DEPTH_TEST);
		blend = r_glIsEnabled(GL_BLEND);
		cull = r_glIsEnabled(GL_CULL_FACE);
		scissor = r_glIsEnabled(GL_SCISSOR_TEST);
		srgb = r_glIsEnabled(GL_FRAMEBUFFER_SRGB);
	}

	~StateGuard()
	{
		r_glBindFramebuffer(GL_DRAW_FRAMEBUFFER, draw_fbo);
		r_glBindFramebuffer(GL_READ_FRAMEBUFFER, read_fbo);
		r_glBindRenderbuffer(GL_RENDERBUFFER, renderbuffer);
		r_glBindVertexArray(vao);
		r_glBindBuffer(GL_ARRAY_BUFFER, array_buffer);
		r_glBindBuffer(GL_PIXEL_PACK_BUFFER, pack_buffer);
		r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER, unpack_buffer);
		r_glBindTexture(GL_TEXTURE_2D, texture);
		r_glActiveTexture(active_texture);
		r_glUseProgram(old_program);
		r_glViewport(viewport[0], viewport[1], viewport[2], viewport[3]);
		r_glDepthFunc(depth_func);
		r_glDepthMask(depth_mask);
		r_glColorMask(colour_mask[0], colour_mask[1], colour_mask[2], colour_mask[3]);
		r_glPixelStorei(GL_PACK_ALIGNMENT, pack_alignment);
		r_glPixelStorei(GL_PACK_ROW_LENGTH, pack_row_length);
		r_glPixelStorei(GL_PACK_SKIP_ROWS, pack_skip_rows);
		r_glPixelStorei(GL_PACK_SKIP_PIXELS, pack_skip_pixels);
		r_glPixelStorei(GL_UNPACK_ALIGNMENT, unpack_alignment);
		r_glPixelStorei(GL_UNPACK_ROW_LENGTH, unpack_row_length);
		r_glClearColor(clear_colour[0], clear_colour[1], clear_colour[2], clear_colour[3]);
		r_glClearDepth(clear_depth);
		Set(GL_DEPTH_TEST, depth_test); Set(GL_BLEND, blend); Set(GL_CULL_FACE, cull);
		Set(GL_SCISSOR_TEST, scissor); Set(GL_FRAMEBUFFER_SRGB, srgb);
	}

	static void Set(GLenum state, bool enabled) { if (enabled) r_glEnable(state); else r_glDisable(state); }
};

static GLuint Compile(GLenum type, const char *source)
{
	GLuint shader = r_glCreateShader(type);
	r_glShaderSource(shader, 1, &source, nullptr);
	r_glCompileShader(shader);
	GLint success = 0;
	r_glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
	if (success) return shader;
	char log[2048]{};
	r_glGetShaderInfoLog(shader, sizeof(log), nullptr, log);
	Debug(driver, 0, "OpenTT3D shader: {}", log);
	r_glDeleteShader(shader);
	return 0;
}

static bool Initialize()
{
	if (program != 0) return true;
	const char *vertex_source = R"GLSL(#version 150
in vec3 position;
in vec3 normal;
in vec3 colour;
uniform vec4 camera;
uniform vec2 dimensions;
uniform vec2 rotation;
uniform float depth_range;
out vec3 lit_colour;
void main() {
    vec3 p = position - camera.xyz;
    p.xy = mat2(rotation.x, rotation.y, -rotation.y, rotation.x) * p.xy;
    vec2 pixel = vec2(2.0 * (p.y - p.x), p.x + p.y - p.z) * camera.w;
    gl_Position = vec4(pixel.x * 2.0 / dimensions.x, -pixel.y * 2.0 / dimensions.y,
        -(p.x + p.y + 2.0 * p.z) / depth_range, 1.0);
    float light = 0.66 + 0.34 * max(dot(normalize(normal), normalize(vec3(-0.45, -0.65, 1.0))), 0.0);
    lit_colour = colour * light;
}
)GLSL";
	const char *fragment_source = R"GLSL(#version 150
in vec3 lit_colour;
out vec4 output_colour;
void main() { output_colour = vec4(lit_colour, 1.0); }
)GLSL";
	GLuint vertex = Compile(GL_VERTEX_SHADER, vertex_source);
	GLuint fragment = Compile(GL_FRAGMENT_SHADER, fragment_source);
	if (!vertex || !fragment) {
		r_glDeleteShader(vertex); r_glDeleteShader(fragment);
		return false;
	}
	program = r_glCreateProgram();
	r_glAttachShader(program, vertex); r_glAttachShader(program, fragment);
	r_glBindAttribLocation(program, 0, "position");
	r_glBindAttribLocation(program, 1, "normal");
	r_glBindAttribLocation(program, 2, "colour");
	r_glLinkProgram(program);
	r_glDeleteShader(vertex); r_glDeleteShader(fragment);
	GLint success = 0;
	r_glGetProgramiv(program, GL_LINK_STATUS, &success);
	if (!success) {
		char log[2048]{};
		r_glGetProgramInfoLog(program, sizeof(log), nullptr, log);
		Debug(driver, 0, "OpenTT3D program: {}", log);
		r_glDeleteProgram(program); program = 0;
		return false;
	}
	r_glGenFramebuffers(1, &framebuffer);
	r_glGenRenderbuffers(1, &depth);
	r_glGenTextures(1, &colour);
	r_glGenVertexArrays(1, &vertex_array);
	r_glGenBuffers(1, &vertex_buffer);
	Debug(driver, 1, "OpenTT3D: depth-tested mesh renderer initialized");
	return true;
}

bool RenderScene(const Scene &scene, const Camera &camera, std::vector<uint8_t> &pixels)
{
	if (!HasOpenGLBackend() || camera.width <= 0 || camera.height <= 0) return false;
	if (!LoadFunctions()) { initialization_failed = true; return false; }
	/* Cocoa's backing context can have a pending error from presenting before its
	 * first drawable exists. Attribute only errors from this pass to this pass. */
	for (GLenum error = r_glGetError(); error != GL_NO_ERROR; error = r_glGetError()) {
		Debug(driver, 2, "OpenTT3D: pre-existing OpenGL error before mesh pass ({})", error);
	}
	StateGuard state;
	if (!Initialize()) { initialization_failed = true; return false; }
	GLint maximum = 0;
	r_glGetIntegerv(GL_MAX_TEXTURE_SIZE, &maximum);
	if (camera.width > maximum || camera.height > maximum) return false;
	r_glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0);
	r_glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
	r_glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
	if (camera.width != buffer_width || camera.height != buffer_height) {
		r_glBindTexture(GL_TEXTURE_2D, colour);
		r_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		r_glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		r_glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, camera.width, camera.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
		r_glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, colour, 0);
		r_glBindRenderbuffer(GL_RENDERBUFFER, depth);
		r_glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, camera.width, camera.height);
		r_glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth);
		if (r_glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) return false;
		buffer_width = camera.width; buffer_height = camera.height;
	}
	r_glViewport(0, 0, camera.width, camera.height);
	r_glDisable(GL_BLEND); r_glDisable(GL_CULL_FACE); r_glDisable(GL_SCISSOR_TEST); r_glDisable(GL_FRAMEBUFFER_SRGB);
	r_glEnable(GL_DEPTH_TEST); r_glDepthFunc(GL_LEQUAL); r_glDepthMask(GL_TRUE);
	r_glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	r_glClearColor(0, 0, 0, 1); r_glClearDepth(1);
	r_glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	r_glUseProgram(program);
	r_glUniform4f(r_glGetUniformLocation(program, "camera"), camera.focus.x, camera.focus.y, camera.focus.z, camera.pixels_per_unit);
	r_glUniform2f(r_glGetUniformLocation(program, "dimensions"), camera.width, camera.height);
	static constexpr float rotations[4][2] = {{1, 0}, {0, 1}, {-1, 0}, {0, -1}};
	r_glUniform2f(r_glGetUniformLocation(program, "rotation"), rotations[camera.rotation & 3][0], rotations[camera.rotation & 3][1]);
	r_glUniform1f(r_glGetUniformLocation(program, "depth_range"), 262144.0f);
	r_glBindVertexArray(vertex_array);
	r_glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer);
	r_glBufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(scene.vertices.size() * sizeof(Vertex)), scene.vertices.data(), GL_STREAM_DRAW);
	for (GLuint attribute = 0; attribute < 3; ++attribute) r_glEnableVertexAttribArray(attribute);
	r_glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, position)));
	r_glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, normal)));
	r_glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void *>(offsetof(Vertex, colour)));
	r_glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(scene.vertices.size()));
	pixels.resize(static_cast<size_t>(camera.width) * camera.height * 4);
	r_glPixelStorei(GL_PACK_ALIGNMENT, 1); r_glPixelStorei(GL_PACK_ROW_LENGTH, 0);
	r_glPixelStorei(GL_PACK_SKIP_ROWS, 0); r_glPixelStorei(GL_PACK_SKIP_PIXELS, 0);
	r_glReadPixels(0, 0, camera.width, camera.height, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
	GLenum error = r_glGetError();
	if (error != GL_NO_ERROR) {
		Debug(driver, 0, "OpenTT3D: OpenGL rendering failed ({})", error);
		return false;
	}
	return true;
}

void DestroyOpenGLResources()
{
	if (functions_loaded) {
		r_glDeleteProgram(program); r_glDeleteFramebuffers(1, &framebuffer);
		r_glDeleteRenderbuffers(1, &depth); r_glDeleteTextures(1, &colour);
		r_glDeleteVertexArrays(1, &vertex_array); r_glDeleteBuffers(1, &vertex_buffer);
	}
	program = framebuffer = depth = colour = vertex_array = vertex_buffer = 0;
	buffer_width = buffer_height = 0;
	functions_loaded = initialization_failed = false;
}

} // namespace Renderer3D

#else
namespace Renderer3D {
bool HasOpenGLBackend() { return false; }
bool RenderScene(const Scene &, const Camera &, std::vector<uint8_t> &) { return false; }
void DestroyOpenGLResources() {}
}
#endif
