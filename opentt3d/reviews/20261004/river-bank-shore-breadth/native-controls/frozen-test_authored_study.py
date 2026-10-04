"""Thin manually authored shore structure does not approve source fidelity or states."""
from collections import defaultdict,Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('shore_approved_compiler',HERE.parent/'river-relief-ownership/approved-compiler-snapshot.py')
compiler=importlib.util.module_from_spec(spec);spec.loader.exec_module(compiler)


class ShoreBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((HERE/'authored-source.json').read_text())
        cls.sources=json.loads((HERE/'actual-source-index.json').read_text())
        cls.compiled=compiler.compile_catalogue(cls.source)

    def test_twenty_separate_original_shore_observations_keep_public_queries_and_complete_bytes(self):
        self.assertEqual(len(self.sources),20);self.assertEqual(len(self.compiled['models']),20)
        self.assertEqual(Counter(row['climate_name'] for row in self.sources),{'temperate':6,'arctic':4,'tropic':4,'toyland':6})
        self.assertEqual(self.compiled['bindings'],{})
        for row in self.sources:
            with self.subTest(climate=row['climate_name'],offset=row['requested_offset']):
                self.assertEqual(row['source_height'],0);self.assertTrue(row['public_terrain_type_query_performed'])
                self.assertTrue(row['source_wave_fringe_preserved']);self.assertFalse(row['native_source_pixels_resized'])
                self.assertFalse(row['quality_approved']);self.assertFalse(row['runtime_bound'])
                self.assertEqual(hashlib.sha256((ROOT/row['source_pam']).read_bytes()).hexdigest(),row['source_pam_sha256'])

    def test_each_solid_thin_column_keeps_the_original_undoubled_slope_and_clear_water_centre(self):
        for row in self.sources:
            name=f"river_bank_shore_study_{row['climate_name']}_offset{row['requested_offset']:02d}";model=self.compiled['models'][name]
            self.assertEqual(model['size'],[64,64,36]);self.assertEqual(model['cell_size'],[0.25]*3);self.assertEqual(model['origin'],[0,0,0])
            columns=defaultdict(set)
            for x,y,z,length,material in model['runs']:
                for dx in range(length):columns[x+dx,y].add(z)
            self.assertTrue(columns);self.assertNotIn((32,32),columns)
            for (x,y),zs in columns.items():
                self.assertLessEqual(len(zs),4);self.assertEqual(zs,set(range(min(zs),max(zs)+1)))
                t=x if row['slope'] in (3,12) else y
                rise=t//2 if row['slope'] in (3,6) else 32-t//2
                self.assertLessEqual(abs(min(zs)-rise),1)

    def test_grain_only_repaints_existing_cells_and_never_reclassifies_wave_water(self):
        clean=json.loads(json.dumps(self.source))
        for model in clean['models'].values():model['ops']=[op for op in model['ops'] if op[0]!='scatter_paint']
        plain=compiler.compile_catalogue(clean)
        cells=lambda model:{(x+dx,y,z) for x,y,z,length,material in model['runs'] for dx in range(length)}
        for name,model in self.compiled['models'].items():self.assertEqual(cells(model),cells(plain['models'][name]))
        used={material for model in self.compiled['models'].values() for x,y,z,length,material in model['runs']}
        self.assertFalse({value for material in used for value in self.compiled['materials'][material-1]}&set(range(245,255)))

    def test_no_image_sampling_or_simulation_rng_is_an_authoring_operation(self):
        source=(HERE/'author-models.py').read_text()
        for token in ('getpixel(', 'getdata(', 'Image.open(', 'read_pam(', 'random.', 'numpy.', 'alpha_trace'):
            self.assertNotIn(token,source)
        self.assertEqual({op[0] for model in self.source['models'].values() for op in model['ops']},{'prism','scatter_paint'})


if __name__=='__main__':unittest.main()
