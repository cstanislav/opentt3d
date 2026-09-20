"""Check mesh topology, model sources, and portable glTF output."""

import base64
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

from compile_models import box, compile_pack, loft, write_gltf

ROOT = Path(__file__).resolve().parents[2]


class MeshTests(unittest.TestCase):
    def test_closed_box_has_outward_normals(self):
        vertices = box({"shape": "box", "min": [-1, -2, -3], "max": [1, 2, 3]}, [1, 1, 1], False)
        self.assertEqual(len(vertices), 36)
        for v in vertices:
            self.assertGreater(sum(v[i] * v[i + 3] for i in range(3)), 0)

    def test_loft_orientation_on_each_axis(self):
        for axis in ("x", "y", "z"):
            vertices = loft({"shape": "loft", "axis": axis, "segments": 8,
                             "rings": [[-2, 0, 0, 1, 1], [2, 0, 0, 1, 1]]}, [1, 1, 1], False)
            for v in vertices:
                self.assertGreater(sum(v[i] * v[i + 3] for i in range(3)), 0)

    def test_authored_pack_has_valid_normals_and_triangles(self):
        for name, vertices in compile_pack(ROOT / "assets/3d/models.json").items():
            self.assertEqual(len(vertices) % 3, 0, name)
            for v in vertices:
                self.assertTrue(all(math.isfinite(x) for x in v), name)
                self.assertAlmostEqual(sum(x * x for x in v[3:6]), 1, places=5, msg=name)
            for i in range(0, len(vertices), 3):
                a, b, c = (v[:3] for v in vertices[i:i + 3])
                self.assertNotEqual(a, b, name)
                self.assertNotEqual(b, c, name)
                self.assertNotEqual(a, c, name)

    def test_gltf_preserves_source_geometry_with_y_up_conversion(self):
        models = compile_pack(ROOT / "assets/3d/models.json")
        with tempfile.TemporaryDirectory() as directory:
            write_gltf(models, Path(directory))
            for name, vertices in models.items():
                doc = json.loads((Path(directory) / f"{name}.gltf").read_text())
                data = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])
                self.assertEqual(len(data), len(vertices) * 36)
                self.assertEqual(doc["accessors"][0]["count"], len(vertices))
                for i, vertex in enumerate(vertices):
                    position = struct.unpack_from("<3f", data, i * 36)
                    for actual, expected in zip(position, (vertex[0], vertex[2], -vertex[1])):
                        self.assertAlmostEqual(actual, expected, places=5)


if __name__ == "__main__":
    unittest.main()
