#!/usr/bin/env python3
"""Compile checked-in Vulkan shaders to a portable embedded SPIR-V header."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="glslangValidator")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    lines = ["/* Generated from renderer3d/shaders; GPL-2.0-only. */", "#pragma once", "#include <cstdint>", "namespace Renderer3D::Vulkan::Shaders {"]
    with tempfile.TemporaryDirectory() as directory:
        for filename in ("vk_world.vert", "vk_world_packed.vert", "vk_world_packed_fast.vert", "vk_world_visible.vert", "vk_world_visible_fast.vert", "vk_world.frag", "vk_voxel.frag", "vk_voxel_slice.frag", "vk_composite.vert", "vk_composite.frag"):
            binary = Path(directory) / (filename + ".spv")
            packed = filename.startswith(("vk_world_packed", "vk_world_visible"))
            source = "vk_world.vert" if packed else filename
            defines = ["-DVOXEL_PACKED_VERTEX=1"] if packed else []
            if packed and "_fast." in filename:
                defines.append("-DVOXEL_PACKED_EXACT_PRODUCTS=1")
            if filename.startswith("vk_world_visible"):
                defines.append("-DVOXEL_VISIBLE_INSTANCE=1")
            subprocess.run([args.compiler, "-V", "--target-env", "vulkan1.1", "-Os", *defines, "-o", str(binary), str(root / "src/renderer3d/shaders" / source)], check=True)
            data = binary.read_bytes()
            values = struct.unpack("<" + "I" * (len(data) // 4), data)
            lines.append("inline constexpr uint32_t " + filename.replace(".", "_") + "[] = {")
            for start in range(0, len(values), 8):
                lines.append("    " + ", ".join(f"0x{value:08x}" for value in values[start:start + 8]) + ",")
            lines.append("};")
    lines.append("}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
