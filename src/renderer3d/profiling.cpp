/* SPDX-License-Identifier: GPL-2.0-only */
/** @file profiling.cpp Reproducible frame-time reports from the real draw loop. */
#include "../stdafx.h"
#include "profiling.h"
#include "vulkan_backend.h"
#include "viewport_3d.h"
#include "gl_backend.hpp"
#include "sprite_textures.hpp"
#include "../3rdparty/nlohmann/json.hpp"
#include "../debug.h"
#include "../fileio_func.h"
#include "../gfx_func.h"
#include "../settings_type.h"
#include "../screenshot.h"
#include "../video/video_driver.hpp"
#include "../window_func.h"
#include "../window_gui.h"
#include <filesystem>
#include <fstream>
#include <numeric>

namespace Renderer3D::Profile {

struct Sample {
	double interval = 0, work = 0;
	double deadline_lateness = 0;
	double gpu = 0;
	bool gpu_available = false;
	std::array<double, static_cast<size_t>(Section::Count)> sections{};
	size_t vertices = 0, passes = 0;
	size_t mesh_uploads = 0, mesh_upload_bytes = 0;
	GeometryCounts geometry_owners{};
	size_t foundation_vertices = 0;
	size_t fence_vertices = 0, rail_vertices = 0;
};
static Sample current;
static Clock::time_point previous{}, start{};
static std::vector<Sample> samples;
static unsigned requested = 0, warmup = 0;
static bool require_fullscreen = false, capture_on_complete = false;
static int measured_width = 0, measured_height = 0;

void BeginFrame(Clock::time_point deadline)
{
	auto now = Clock::now();
	current = {};
	current.deadline_lateness = std::max(0.0,std::chrono::duration<double,std::milli>(now-deadline).count());
	if (previous != Clock::time_point{}) current.interval = std::chrono::duration<double, std::milli>(now - previous).count();
	previous = start = now;
}

void AddTime(Section section, double milliseconds) { current.sections[static_cast<size_t>(section)] += milliseconds; }
void AddGeometry(size_t vertices) { current.vertices += vertices; ++current.passes; }
bool IsBenchmarking() { return requested != 0; }
void AddCapturedGeometry(const GeometryCounts &owners, size_t foundation_vertices, size_t fence_vertices, size_t rail_vertices)
{
	for (size_t i = 0; i < owners.size(); ++i) current.geometry_owners[i] += owners[i];
	current.foundation_vertices += foundation_vertices;
	current.fence_vertices += fence_vertices; current.rail_vertices += rail_vertices;
}
void AddMeshUpload(size_t bytes) { ++current.mesh_uploads; current.mesh_upload_bytes += bytes; }
void AddGPUTime(double milliseconds) { current.gpu = milliseconds; current.gpu_available = true; }

void StartBenchmark(unsigned frames, bool fullscreen, bool capture)
{
	requested = std::clamp(frames, 1U, MAX_BENCHMARK_FRAMES);
	warmup = 30;
	require_fullscreen = fullscreen;
	capture_on_complete = capture;
	measured_width = measured_height = 0;
	samples.clear();
	samples.reserve(requested);
	Debug(driver, 1, "OpenTT3D: benchmarking {} presented frames after 30 warm-up frames", requested);
}

void EndFrame()
{
	if (requested == 0) return;
	if (require_fullscreen && !_fullscreen) return;
	if (measured_width != _screen.width || measured_height != _screen.height) {
		measured_width = _screen.width;
		measured_height = _screen.height;
		warmup = 30;
		samples.clear();
	}
	if (warmup != 0) { --warmup; return; }
	current.work = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
	samples.push_back(current);
	if (samples.size() < requested) return;
	requested = 0;
	using Json = nlohmann::json;
	auto summary = [&](auto value) {
		std::vector<double> values;
		for (const auto &sample : samples) values.push_back(value(sample));
		std::sort(values.begin(), values.end());
		auto percentile = [&](double p) { return values[std::min(values.size() - 1, static_cast<size_t>(std::ceil(p * values.size()) - 1))]; };
		return Json{{"mean", std::accumulate(values.begin(), values.end(), 0.0) / values.size()},
			{"p50", percentile(0.50)}, {"p95", percentile(0.95)}, {"p99", percentile(0.99)}, {"max", values.back()}};
	};
	Json report{{"frames", samples.size()}, {"backend", BackendDescription()}, {"renderer_enabled", IsEnabled()},
		{"width", _screen.width}, {"height", _screen.height}, {"fullscreen", _fullscreen},
		{"requested_refresh_rate", _settings_client.gui.refresh_rate}, {"rotation", GetRotation()},
		{"frame_interval_ms", summary([](const Sample &s) { return s.interval; })},
		{"frame_deadline_lateness_ms", summary([](const Sample &s) { return s.deadline_lateness; })},
		{"frame_work_ms", summary([](const Sample &s) { return s.work; })},
		{"vertices", summary([](const Sample &s) { return static_cast<double>(s.vertices); })},
		{"passes", summary([](const Sample &s) { return static_cast<double>(s.passes); })},
		{"mesh_uploads", summary([](const Sample &s) { return static_cast<double>(s.mesh_uploads); })},
		{"mesh_upload_bytes", summary([](const Sample &s) { return static_cast<double>(s.mesh_upload_bytes); })},
		{"atlas_pages", Textures().pages.size()}};
	const char *names[] = {"capture_ms", "backend_including_readback_ms", "readback_ms", "composite_ms", "buffer_wait_ms", "game_lock_wait_ms", "window_draw_inclusive_ms", "present_ms",
		"texture_decode_ms", "atlas_repack_ms", "mesh_upload_ms", "swapchain_acquire_inclusive_ms", "presentation_upload_ms", "queue_submit_ms", "queue_present_ms", "mesh_index_ms", "palette_upload_ms", "ui_palette_upload_ms"};
	static_assert(std::size(names) == static_cast<size_t>(Section::Count));
	const char *owners[] = {"clear", "rail", "road", "house", "trees", "station", "water", "void", "industry", "tunnel_bridge", "object", "vehicle", "unowned"};
	static_assert(std::size(owners) == static_cast<size_t>(GeometryOwner::Count));
	for (size_t i = 0; i < std::size(owners); ++i) report["captured_vertices_by_owner"][owners[i]] = summary([i](const Sample &s) { return static_cast<double>(s.geometry_owners[i]); });
	report["captured_foundation_vertices"] = summary([](const Sample &s) { return static_cast<double>(s.foundation_vertices); });
	report["captured_fence_vertices"] = summary([](const Sample &s) { return static_cast<double>(s.fence_vertices); });
	report["captured_running_rail_vertices"] = summary([](const Sample &s) { return static_cast<double>(s.rail_vertices); });
	if (Vulkan::Active()) {
		auto stats = Vulkan::GetMeshCacheStats();
		report["mesh_cache"] = {{"pooled", stats.pooled}, {"meshes", stats.meshes}, {"buffers", stats.buffers}, {"used_bytes", stats.used_bytes}, {"capacity_bytes", stats.capacity_bytes},
			{"indexed_meshes",stats.indexed_meshes},{"source_vertices",stats.source_vertices},{"stored_vertices",stats.stored_vertices},{"index_bytes",stats.index_bytes}};
	}
	/* Vulkan queries are consumed after the frame fence, two frames later,
	 * without a profiling-only GPU wait. Warm-up excludes unavailable queries. */
	if (std::all_of(samples.begin(), samples.end(), [](const Sample &s) { return s.gpu_available; })) report["gpu_frame_ms"] = summary([](const Sample &s) { return s.gpu; });
	for (size_t i = 0; i < std::size(names); ++i) report[names[i]] = summary([i](const Sample &s) { return s.sections[i]; });
	if (const Window *window = GetMainWindow(); window != nullptr && window->viewport != nullptr) {
		report["legacy_zoom"] = to_underlying(window->viewport->zoom);
		report["effective_zoom"] = GetEffectiveZoom(*window->viewport);
		report["pitch_degrees"] = GetPitch(*window->viewport);
		report["draw_distance"] = "unlimited";
		report["first_person"] = IsFirstPerson(window->viewport->follow_vehicle);
		report["viewport"] = {{"left", window->viewport->virtual_left}, {"top", window->viewport->virtual_top},
			{"width", window->viewport->virtual_width}, {"height", window->viewport->virtual_height}};
	}
	double mean = report["frame_interval_ms"]["mean"].get<double>();
	report["measured_fps"] = mean > 0 ? 1000.0 / mean : 0;
	report["frames_over_16_67_ms"] = std::count_if(samples.begin(), samples.end(), [](const Sample &s) { return s.work > 1000.0 / 60; });
	report["intervals_over_20_ms"] = std::count_if(samples.begin(), samples.end(), [](const Sample &s) { return s.interval > 20; });
	report["slow_frames"] = Json::array();
	for (size_t index = 0; index < samples.size(); ++index) {
		const auto &sample = samples[index];
		if (sample.work <= 20 && sample.interval <= 20) continue;
		Json slow{{"index", index}, {"work_ms", sample.work}, {"interval_ms", sample.interval}, {"vertices", sample.vertices}, {"passes", sample.passes},
			{"deadline_lateness_ms", sample.deadline_lateness},
			{"mesh_uploads", sample.mesh_uploads}, {"mesh_upload_bytes", sample.mesh_upload_bytes}};
		for (size_t i = 0; i < std::size(names); ++i) slow[names[i]] = sample.sections[i];
		report["slow_frames"].push_back(std::move(slow));
	}
	std::filesystem::path path = std::filesystem::path(FioGetDirectory(SP_WORKING_DIR, BASE_DIR)) / "benchmark.json";
	std::ofstream output(path);
	output << report.dump(2) << '\n';
	if (!output) throw std::runtime_error("Could not write renderer benchmark");
	Debug(driver, 1, "OpenTT3D: benchmark {:.2f} fps, p95 work {:.2f}ms; {}", report["measured_fps"].get<double>(), report["frame_work_ms"]["p95"].get<double>(), path.string());
	if (capture_on_complete) {
		capture_on_complete = false;
		VideoDriver::GetInstance()->QueueOnMainThread([] { MakeScreenshot((Vulkan::Active() || OpenGL::Active()) ? SC_PRESENTED : SC_VIEWPORT, "smoke"); });
	}
}

} // namespace Renderer3D::Profile
