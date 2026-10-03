"""Authored ownership planes preserve existing cells/paint and exact disjoint unions."""
import unittest

from compile_voxels import compile_catalogue


class VoxelOwnerPlaneTests(unittest.TestCase):
    def source(self,ops):
        return {"format":1,"materials":{"wall":[2,3,4,5,6,7]},"models":{
            "study":{"size":[8,8,8],"cell_size":[0.5,0.5,0.5],"origin":[0,0,-0.5],"ops":ops}},"bindings":{}}

    def cells(self,ops):
        catalogue = compile_catalogue(self.source(ops))
        return {(x+i,y,z):catalogue["materials"][material-1]
                for x,y,z,length,material in catalogue["models"]["study"]["runs"] for i in range(length)}

    def test_complementary_planes_have_no_holes_duplicates_or_repainted_faces(self):
        box = [["box","wall",0,0,0,8,8,8]]
        expected = self.cells(box); joined = {}
        for xside in ("less","greater_equal"):
            for yside in ("less","greater_equal"):
                actual = self.cells(box+[["clip_plane",[2,0,-1],8,xside],["clip_plane",[0,2,-1],8,yside]])
                self.assertFalse(joined.keys() & actual.keys())
                joined.update(actual)
        self.assertEqual(joined,expected)

    def test_registered_source_owner_keeps_upper_relief_across_a_physical_tile_edge(self):
        cells = self.cells([["box","wall",0,0,0,8,8,8],["clip_plane",[0,2,-1],8,"less"]])
        self.assertIn((2,3,0),cells)
        self.assertNotIn((2,4,0),cells)
        self.assertIn((2,4,2),cells,"Raised original owner keeps its own roof/wall instead of sending a vertical column to its neighbour")

    def test_component_offsets_translate_the_plane_with_the_authored_cells(self):
        source = self.source([["use","part",[2,3,1]]])
        source["components"] = {"part":[["box","wall",0,0,0,4,4,4],["clip_plane",[2,0,-1],4,"less"]]}
        compiled = compile_catalogue(source)
        actual = {(x+i,y,z) for x,y,z,length,material in compiled["models"]["study"]["runs"] for i in range(length)}
        expected = {(x+2,y+3,z+1) for x in range(4) for y in range(4) for z in range(4) if 2*x-z < 4}
        self.assertEqual(actual,expected)

    def test_invalid_planes_are_rejected_instead_of_rounded_or_ignored(self):
        for plane,threshold,side in (([0,0,0],4,"less"),([2.0,0,-1],4,"less"),([True,0,-1],4,"less"),
                                     ([2048,0,-1],4,"less"),([2,0,-1],False,"less"),([2,0,-1],4,"nearest")):
            with self.subTest(plane=plane,threshold=threshold,side=side),self.assertRaises(ValueError):
                self.cells([["box","wall",0,0,0,8,8,8],["clip_plane",plane,threshold,side]])


if __name__ == "__main__":
    unittest.main()
