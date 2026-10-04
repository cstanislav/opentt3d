/* SPDX-License-Identifier: GPL-2.0-only */
/** @file voxel_visibility_worker.hpp Value-only background visibility preparation. */
#ifndef RENDERER3D_VOXEL_VISIBILITY_WORKER_HPP
#define RENDERER3D_VOXEL_VISIBILITY_WORKER_HPP

#include "voxel_visibility.hpp"
#include "voxel_packed_mesh.hpp"
#include "../thread.h"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <utility>

namespace Renderer3D {

class VoxelVisibilityWorker {
public:
	struct Result {
		std::vector<std::array<uint32_t,7>> transforms;
		std::vector<std::shared_ptr<const std::vector<uint64_t>>> geometry;
	};
private:
	struct Job {
		Camera camera;
		unsigned precision, worker;
		size_t scene_instances;
		uint64_t generation;
		const std::vector<Vertex> *mesh;
		std::shared_ptr<const void> source_lease;
		std::shared_ptr<const PackedVoxelMesh> packed;
		std::vector<InstanceData> instances;
		std::vector<std::array<uint32_t,7>> transforms;
	};
	std::mutex mutex;
	std::condition_variable changed;
	std::array<std::thread,2> threads;
	bool stopping = false, failed = false;
	std::optional<Camera> camera;
	unsigned precision = 0;
	std::atomic<uint64_t> generation{0};
	std::deque<const std::vector<Vertex> *> order;
	std::unordered_map<const std::vector<Vertex> *,std::shared_ptr<Job>> pending;
	std::unordered_map<const std::vector<Vertex> *,Result> completed;
	std::unordered_map<const std::vector<Vertex> *,std::shared_ptr<const Job>> active;
	std::unordered_map<const std::vector<Vertex> *,unsigned> owners;
	std::array<uint64_t,2> assigned_work{};
	std::array<uint64_t,2> cache_generation{};
	std::array<std::atomic<size_t>,2> cache_bytes{};
	unsigned worker_count = 1;
	std::string error;
	bool diagnostic = [] { const char *value = std::getenv("OPENTT3D_VOXEL_CULL_DEBUG"); return value != nullptr && std::string_view(value) == "1"; }();
	bool memory_diagnostic = [] { const char *value = std::getenv("OPENTT3D_MEMORY_DEBUG"); return value != nullptr && std::string_view(value) == "1"; }();

	void Run(unsigned worker)
	{
		VoxelVisibilityCache cache;
		std::unordered_map<const PackedVoxelMesh *,PackedVoxelLookup> lookups;
		for (;;) {
			std::shared_ptr<const Job> job;
			{
				std::unique_lock lock(mutex);
				auto available = [&] { return std::find_if(order.begin(),order.end(),[&](const auto *mesh) { return pending.at(mesh)->worker == worker && !active.contains(mesh); }); };
				changed.wait(lock,[&] { return stopping || failed || cache_generation[worker] != generation.load() || available() != order.end(); });
				if (stopping || failed) return;
				if (cache_generation[worker] != generation.load()) {
					uint64_t current = generation.load();
					lock.unlock();
					/* Cancellation must release old camera results even if no future
					 * job arrives (for example after zooming in or entering Cab). */
					cache.Clear();
					if (memory_diagnostic) cache_bytes[worker].store(cache.MemoryBytes(),std::memory_order_relaxed);
					lock.lock(); cache_generation[worker] = current;
					changed.notify_all();
					continue;
				}
				auto next = available();
				auto mesh = *next; order.erase(next);
				job = std::move(pending.at(mesh)); pending.erase(mesh); active.emplace(mesh,job);
			}
			try {
				if (diagnostic) Debug(driver,1,"OpenTT3D: visibility worker starts generation {} mesh {} instances {}",job->generation,reinterpret_cast<uintptr_t>(job->mesh),job->instances.size());
				auto [entry,inserted] = lookups.try_emplace(job->packed.get());
				if (inserted) entry->second = MakePackedVoxelLookup(job->packed->vertices);
				const auto &lookup = entry->second;
				if (lookup.bits > 21 || job->instances.size() > (uint64_t{1}<<(64-lookup.bits*3))) throw std::invalid_argument("Voxel visibility job cannot encode its references");
				Result result;
				result.transforms = job->transforms;
				cache.Begin(job->camera,job->precision,job->scene_instances);
				result.geometry.reserve(job->instances.size());
				size_t count = 0;
				for (const auto &instance : job->instances) {
					if (generation.load(std::memory_order_relaxed) != job->generation) break;
					auto triangles = cache.SharedPackedTriangles(*job->mesh,instance,lookup.indices,lookup.bits);
					count += triangles->size(); result.geometry.push_back(std::move(triangles));
				}
				if (memory_diagnostic) {
					size_t bytes = cache.MemoryBytes();
					for (const auto &[mesh,lookup] : lookups) bytes += (lookup.vertices.capacity()+lookup.indices.capacity())*sizeof(uint32_t);
					cache_bytes[worker].store(bytes,std::memory_order_relaxed);
				}
				if (generation.load(std::memory_order_relaxed) == job->generation) {
					std::lock_guard lock(mutex);
					if (generation.load(std::memory_order_relaxed) == job->generation) {
						if (diagnostic) Debug(driver,1,"OpenTT3D: visibility worker completes generation {} mesh {} triangles {}",job->generation,reinterpret_cast<uintptr_t>(job->mesh),count);
						completed.insert_or_assign(job->mesh,std::move(result));
					}
				}
			} catch (const std::exception &exception) {
				std::lock_guard lock(mutex);
				error = exception.what(); failed = true; ++generation; order.clear(); pending.clear(); completed.clear();
			}
			{
				std::lock_guard lock(mutex);
				active.erase(job->mesh);
			}
			changed.notify_all();
		}
	}

public:
	static unsigned Concurrency()
	{
		static const unsigned count = [] { const char *value = std::getenv("OPENTT3D_VOXEL_CULL_WORKERS"); return value != nullptr && std::string_view(value) == "2" ? 2U : 1U; }();
		return count;
	}
	explicit VoxelVisibilityWorker(unsigned concurrency = Concurrency())
	{
		unsigned started = 0;
		for (unsigned i = 0; i < std::clamp(concurrency,1U,2U); ++i) {
			if (!StartNewThread(&threads[i],"voxel-visibility",[this,i] { Run(i); })) break;
			++started;
		}
		std::lock_guard lock(mutex);
		worker_count = started; failed = started == 0;
	}
	~VoxelVisibilityWorker()
	{
		{
			std::lock_guard lock(mutex);
			stopping = true; ++generation; order.clear(); pending.clear(); completed.clear();
		}
		changed.notify_all();
		for (auto &thread : threads) if (thread.joinable()) thread.join();
	}
	VoxelVisibilityWorker(const VoxelVisibilityWorker &) = delete;
	VoxelVisibilityWorker &operator=(const VoxelVisibilityWorker &) = delete;

	void SetCamera(const Camera &current, unsigned subpixel_precision)
	{
		std::lock_guard lock(mutex);
		if (camera && *camera == current && precision == subpixel_precision) return;
		camera = current; precision = subpixel_precision; ++generation;
		if (diagnostic) Debug(driver,1,"OpenTT3D: visibility worker camera generation {} focus {},{},{} scale {} rotation {} size {}x{}",generation.load(),current.focus.x,current.focus.y,current.focus.z,current.pixels_per_unit,current.rotation,current.width,current.height);
		order.clear(); pending.clear(); completed.clear();
		owners.clear(); assigned_work.fill(0);
		changed.notify_all();
	}
	void Cancel()
	{
		std::lock_guard lock(mutex);
		if (!camera) return;
		camera.reset(); ++generation; order.clear(); pending.clear(); completed.clear();
		owners.clear(); assigned_work.fill(0);
		if (diagnostic) Debug(driver,1,"OpenTT3D: visibility worker cancels generation {}",generation.load());
		changed.notify_all();
	}

	void Request(const std::vector<Vertex> &mesh, std::shared_ptr<const PackedVoxelMesh> packed,
			std::span<const InstanceData> instances, size_t scene_instances, std::shared_ptr<const void> source_lease = {})
	{
		std::lock_guard lock(mutex);
		if (failed || !camera) return;
		auto matches = [&](const Job &job) {
			if (job.generation != generation.load(std::memory_order_relaxed) || job.transforms.size() != instances.size()) return false;
			for (size_t i = 0; i < instances.size(); ++i) if (job.transforms[i] != VoxelVisibilityTransform(instances[i])) return false;
			return true;
		};
		/* Keep at most one active job per mesh. A newer pending snapshot must
		 * never finish first and then be overwritten by an older active result. */
		auto running = active.find(&mesh);
		if (running != active.end() && matches(*running->second)) {
			/* A->B->A edits can return to the active snapshot. Discard B rather
			 * than letting that superseded pending result replace A afterwards. */
			if (pending.erase(&mesh) != 0) std::erase(order,&mesh);
			return;
		}
		auto found = pending.find(&mesh);
		if (found != pending.end() && matches(*found->second)) return;
		auto job = std::make_shared<Job>();
		/* Stable mesh affinity preserves each worker's per-transform cache
		 * across live tree edits instead of recomputing a forest on another worker. */
		unsigned least_loaded = static_cast<unsigned>(std::min_element(assigned_work.begin(),assigned_work.begin()+worker_count)-assigned_work.begin());
		auto [owner,inserted] = owners.try_emplace(&mesh,least_loaded);
		/* Round-robin mesh counts can put every dense mature tree family on
		 * one worker. Balance their original vertex/instance work instead. */
		if (inserted) assigned_work[owner->second] += static_cast<uint64_t>(packed->vertices.size())*instances.size();
		job->worker = owner->second;
		job->camera = *camera; job->precision = precision; job->scene_instances = scene_instances;
		job->generation = generation.load(std::memory_order_relaxed); job->mesh = &mesh; job->packed = std::move(packed);
		job->source_lease = std::move(source_lease);
		job->instances.assign(instances.begin(),instances.end());
		job->transforms.reserve(instances.size());
		for (const auto &instance : instances) job->transforms.push_back(VoxelVisibilityTransform(instance));
		if (found == pending.end()) order.push_back(&mesh);
		pending.insert_or_assign(&mesh,std::move(job));
		changed.notify_all();
	}

	std::optional<Result> Take(const std::vector<Vertex> &mesh)
	{
		std::lock_guard lock(mutex);
		auto found = completed.find(&mesh);
		if (found == completed.end()) return {};
		Result result = std::move(found->second); completed.erase(found);
		return result;
	}
	std::string TakeError()
	{
		std::lock_guard lock(mutex);
		return std::exchange(error,{});
	}
	size_t MemoryBytes()
	{
		std::lock_guard lock(mutex);
		size_t bytes = 0;
		for (const auto &cache : cache_bytes) bytes += cache.load(std::memory_order_relaxed);
		for (const auto &[mesh,result] : completed) {
			bytes += result.transforms.capacity()*sizeof(result.transforms.front())+result.geometry.capacity()*sizeof(result.geometry.front());
			/* Triangle storage is shared with the worker cache already counted above. */
		}
		auto snapshots = [&](const auto &jobs) {
			for (const auto &[mesh,job] : jobs) bytes += sizeof(Job)+job->instances.capacity()*sizeof(InstanceData)+job->transforms.capacity()*sizeof(job->transforms.front());
		};
		snapshots(active); snapshots(pending);
		return bytes;
	}
	/** Diagnostic synchronization; interactive rendering never waits here. */
	bool WaitIdle(std::chrono::milliseconds timeout)
	{
		std::unique_lock lock(mutex);
		return changed.wait_for(lock,timeout,[&] {
			return failed || (order.empty() && active.empty() && std::all_of(cache_generation.begin(),cache_generation.begin()+worker_count,[&](uint64_t value) { return value == generation.load(); }));
		});
	}
};

} // namespace Renderer3D
#endif
