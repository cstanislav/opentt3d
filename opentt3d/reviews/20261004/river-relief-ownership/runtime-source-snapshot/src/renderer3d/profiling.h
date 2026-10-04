/* SPDX-License-Identifier: GPL-2.0-only */
/** @file profiling.h Measured presentation costs; never simulation timing. */
#ifndef RENDERER3D_PROFILING_H
#define RENDERER3D_PROFILING_H

#include <chrono>
#include <cstddef>
#include <array>

namespace Renderer3D::Profile {

/** Ten minutes at 60 Hz accommodates original industry regrowth and service cycles. */
inline constexpr unsigned MAX_BENCHMARK_FRAMES = 36000;

enum class Section {
	Capture, Backend, Readback, Composite, BufferWait, GameWait, WindowDraw, Present,
	TextureDecode, AtlasRepack, MeshUpload, SwapchainAcquire, PresentationUpload, QueueSubmit, QueuePresent, MeshIndex, PaletteUpload, UIPaletteUpload, Count
};
using Clock = std::chrono::steady_clock;
/** Presentation ownership only; counts include each captured instance. */
enum class GeometryOwner { Clear, Rail, Road, House, Trees, Station, Water, Void, Industry, TunnelBridge, Object, Vehicle, Unowned, Count };
using GeometryCounts = std::array<size_t,static_cast<size_t>(GeometryOwner::Count)>;

void BeginFrame(Clock::time_point deadline);
void EndFrame();
void StartBenchmark(unsigned frames, bool fullscreen = false, bool capture = false);
void AddTime(Section section, double milliseconds);
void AddGeometry(size_t vertices);
bool IsBenchmarking();
void AddCapturedGeometry(const GeometryCounts &owners, size_t foundation_vertices, size_t fence_vertices, size_t rail_vertices);
void AddMeshUpload(size_t bytes);
void AddGPUTime(double milliseconds);

class Scope {
	Section section;
	Clock::time_point start = Clock::now();
public:
	explicit Scope(Section section) : section(section) {}
	~Scope() { AddTime(section, std::chrono::duration<double, std::milli>(Clock::now() - start).count()); }
	Scope(const Scope &) = delete;
	Scope &operator=(const Scope &) = delete;
};

} // namespace Renderer3D::Profile
#endif
