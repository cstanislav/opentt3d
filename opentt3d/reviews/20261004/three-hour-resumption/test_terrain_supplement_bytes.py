"""Fresh supplements retain complete raw source headers, partial alpha and hidden RGB."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image,PngImagePlugin

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('terrain_supplement',HERE/'supplement-bank-terrain-provenance.py')
supplement=importlib.util.module_from_spec(spec);spec.loader.exec_module(supplement)


class TerrainSupplementBytesTests(unittest.TestCase):
    def test_complete_png_reconstructs_raw_partial_alpha_and_hidden_rgb(self):
        header='P7\nWIDTH 2\nHEIGHT 1\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n'
        rgba=bytes((173,19,231,0,39,182,21,127))
        with tempfile.TemporaryDirectory(prefix='opentt3d-source-bytes-') as directory:
            raw=Path(directory)/'source.pam';raw.write_bytes(header.encode('ascii')+rgba)
            png=raw.with_suffix('.png');picture=Image.frombytes('RGBA',(2,1),rgba)
            metadata=PngImagePlugin.PngInfo();metadata.add_text('opentt3d_pam_header',header)
            picture.save(png,pnginfo=metadata)
            expected=hashlib.sha256(raw.read_bytes()).hexdigest()
            self.assertEqual(supplement.original_pam_digest(raw),expected)
            self.assertEqual(supplement.original_pam_digest(png),expected)

    def test_header_differences_are_not_normalized_away(self):
        header='P7\nWIDTH 1\nHEIGHT 1\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n'
        with tempfile.TemporaryDirectory(prefix='opentt3d-source-header-') as directory:
            picture=Image.frombytes('RGBA',(1,1),bytes((3,2,1,255)));paths=[]
            for index,value in enumerate((header,header.replace('WIDTH 1\n','WIDTH 1\r\n'))):
                path=Path(directory)/f'source-{index}.png';metadata=PngImagePlugin.PngInfo()
                metadata.add_text('opentt3d_pam_header',value);picture.save(path,pnginfo=metadata);paths.append(path)
            self.assertNotEqual(*(supplement.original_pam_digest(path) for path in paths))

    def test_display_only_png_without_original_header_is_not_source_evidence(self):
        with tempfile.TemporaryDirectory(prefix='opentt3d-no-source-header-') as directory:
            path=Path(directory)/'display.png';Image.new('RGBA',(1,1)).save(path)
            with self.assertRaises(KeyError):supplement.original_pam_digest(path)

    def test_query_equivalence_requires_original_callback_and_registration_fields(self):
        for field in ('base_set','base_graphics','feature','feature_flags','offset_callback','palette',
            'requested_offset','resolved_offset','slope','source_height','source_offset','source_size','tile','tile_xy','water_class'):
            self.assertIn(field,supplement.IDENTITY)
        self.assertNotIn('selected_sprite',supplement.IDENTITY)
        self.assertNotIn('texture_generation',supplement.IDENTITY)


if __name__=='__main__':unittest.main()
