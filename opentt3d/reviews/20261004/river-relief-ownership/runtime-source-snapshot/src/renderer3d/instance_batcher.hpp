/* SPDX-License-Identifier: GPL-2.0-only */
/** @file instance_batcher.hpp Reusable CPU staging for immutable mesh instances. */
#ifndef RENDERER3D_INSTANCE_BATCHER_HPP
#define RENDERER3D_INSTANCE_BATCHER_HPP

#include "geometry.hpp"
#include <unordered_map>

namespace Renderer3D {

/** Count/prefix/scatter avoids per-mesh record vectors and repeated allocation
 * and copying of the entire instance stream. Ordering within each batch and the
 * first-captured mesh order within each explicit draw layer are retained.
 * Child layers follow their opaque parents independently of mesh allocation order. */
class InstanceBatcher {
	struct Bucket {
		std::array<size_t,2> count{}, write{};
		size_t source = 0;
		uint64_t epoch = 0;
		bool boundary = false;
	};
	using Buckets = std::unordered_map<const std::vector<Vertex> *,Bucket>;
	std::array<Buckets,2> buckets;
	std::array<std::vector<Buckets::value_type *>,2> active;
	struct Owner { Buckets::value_type *entry = nullptr; bool child = false; };
	std::vector<Owner> owners;
	uint64_t epoch = 0;
public:
	struct Batch { const std::vector<Vertex> *mesh; size_t first, count; bool transparent, both_passes; size_t source; };
	std::vector<Batch> batches;
	std::vector<InstanceData> records;

	/** Palette fragments already reject rear faces in the shader. Apply that
	 * same test in rasterization only when every record uses palette surfaces;
	 * a sprite overlay can share the mesh with its voxel parent. */
	bool PaletteOnly(const Batch &batch) const
	{
		for (size_t i = batch.first; i < batch.first+batch.count; ++i) {
			if ((static_cast<uint32_t>(records[i].identity[1])&15U) != static_cast<uint32_t>(SurfaceMode::Palette)) return false;
		}
		return true;
	}

	void Build(std::span<const MeshInstance> instances, bool split_transparency)
	{
		++epoch;
		owners.resize(instances.size());
		batches.clear();
		for (auto &layer : active) layer.clear();
		for (size_t i = 0; i < instances.size(); ++i) {
			const auto &instance = instances[i];
			bool child = instance.data.ChildLayer();
			auto &owner = owners[i];
			/* Most captured positions retain their mesh/layer between frames. Cache
			 * only the lookup, never instance values or first-capture draw order.
			 * Nodes survive rehash; every retained owner was used last frame and
			 * cannot meet the long-unused retirement condition below. */
			if (owner.entry == nullptr || owner.child != child || owner.entry->first != instance.mesh) {
				auto [entry,inserted] = buckets[child].try_emplace(instance.mesh);
				owner = {&*entry,child};
			}
			auto &bucket = owner.entry->second;
			if (bucket.epoch != epoch) { bucket.epoch = epoch; bucket.count = {}; bucket.boundary = false; bucket.source = i; active[child].push_back(owner.entry); }
			float opacity = instance.data.origin_opacity[3];
			++bucket.count[split_transparency && opacity < 0.99f];
			/* Interpolation can move an otherwise constant alpha across 0.99. Keep
			 * the entire mesh's original order in that narrow neighbourhood; the
			 * unchanged fragment test still decides coverage in both passes. */
			bucket.boundary |= split_transparency && std::abs(opacity-0.99f) <= 0.00001f;
		}
		/* Resolve each owner once; node references survive rehash. First capture
		 * decides mesh order, not allocation addresses, so coplanar colour and
		 * picking remain reproducible across launches. Children follow parents. */
		size_t offset = 0;
		for (const auto &layer : active) for (auto *entry : layer) {
			auto &[mesh,bucket] = *entry;
			if (!split_transparency || bucket.boundary) {
				size_t count = bucket.count[0]+bucket.count[1];
				bucket.write[0] = offset;
				batches.push_back({mesh,offset,count,false,true,bucket.source});
				offset += count;
			} else for (unsigned pass = 0; pass < 2; ++pass) {
				bucket.write[pass] = offset;
				if (bucket.count[pass] != 0) batches.push_back({mesh,offset,bucket.count[pass],pass != 0,false,bucket.source});
				offset += bucket.count[pass];
			}
		}
		records.resize(std::max<size_t>(1,offset));
		if (instances.empty()) records[0] = InstanceData{}; // Valid descriptor for dynamic-only scenes.
		for (size_t i = 0; i < instances.size(); ++i) {
			auto &bucket = owners[i].entry->second;
			unsigned pass = split_transparency && !bucket.boundary && instances[i].data.origin_opacity[3] < 0.99f;
			records[bucket.write[pass]++] = instances[i].data.CanonicalGPURecord();
		}
		/* Retain stream capacity, but retire keys for long-unused models/LODs. */
		if (epoch%120 == 0) for (auto &layer : buckets) std::erase_if(layer,[&](const auto &entry) { return entry.second.epoch+120 <= epoch; });
	}
};

} // namespace Renderer3D
#endif
