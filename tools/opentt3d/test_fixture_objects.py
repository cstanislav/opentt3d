"""Ordinary object fixtures must not force source sizes or change commands/RNG."""
from pathlib import Path
import struct
import unittest

from fixture_objects import statue_ground_replacement

ROOT = Path(__file__).resolve().parents[2]


class OriginalObjectFixtureTests(unittest.TestCase):
    def test_partial_graphics_probe_replaces_only_the_original_concrete_ground_chart(self):
        data = statue_ground_replacement()
        offset = 0
        def pseudo():
            nonlocal offset
            size,kind = struct.unpack_from("<HB",data,offset)
            self.assertEqual(kind,255)
            payload = data[offset+3:offset+3+size]; offset += 3+size
            return payload
        self.assertEqual(pseudo(),struct.pack("<I",3))
        self.assertTrue(pseudo().startswith(b"\x08\x08O3OG"))
        self.assertEqual(pseudo(),b"\x0a\x01\x01"+struct.pack("<H",1420))
        size,kind,height,width,x,y = struct.unpack_from("<HBBHhh",data,offset)
        self.assertEqual((kind,height,width,x,y),(2,31,64,-32,0))
        offset += 10
        end = offset+size-8
        pixels = bytearray()
        while offset < end:
            count = data[offset]; offset += 1
            self.assertTrue(1 <= count <= 127)
            pixels.extend(data[offset:offset+count]); offset += count
        self.assertEqual(len(pixels),64*31)
        self.assertEqual(set(pixels),{0,73,199})
        self.assertEqual(data[offset:],b"\0\0")
        line = next(line for line in (ROOT/"src/table/sprites.h").read_text().splitlines() if line.startswith("static const SpriteID SPR_CONCRETE_GROUND "))
        self.assertEqual(int(line.split("=",1)[1].strip().rstrip(";")),1420)

    def test_hq_statue_fixture_uses_only_public_commands_and_keeps_source_state(self):
        script = (ROOT/"tools/opentt3d/fixtures/objects/main.nut").read_text()
        for required in ("AICompany.BuildCompanyHQ(tile)","AITown.PerformTownAction(town,AITown.TOWN_ACTION_BUILD_STATUE)",
                         "AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())","AITile.IsBuildableRectangle(tile,2,2)",
                         "AIObjectType.IsValidObjectType(3)","AIObjectType.BuildObject(3,0,tile)","AITile.IsSteepSlope(slope)",
                         "AITile.GetSlope(","OBJECT_FIXTURE_FAILED","OBJECT_FIXTURE_READY"):
            self.assertIn(required,script)
        for mutation in ("UpdateCompanyHQ","SetAnimationFrame","SetCompanyRating","SetTileType","Random(","TOWN_INVALID"):
            self.assertNotIn(mutation,script)
        runtime = (ROOT/"tools/opentt3d/fixture_objects.py").read_text()
        self.assertIn("public AIObjectType.BuildObject(3,0,tile)",runtime)
        self.assertNotIn("AITile.RaiseTile",script)
        self.assertNotIn("AITile.LowerTile",script)
        self.assertIn("save failed-fixture",runtime)
        self.assertIn("Use a new output directory",runtime)
        self.assertIn('"127.0.0.1"',runtime)
        self.assertIn('OPENTT3D_RENDERER="0"',runtime)


if __name__ == "__main__":
    unittest.main()
