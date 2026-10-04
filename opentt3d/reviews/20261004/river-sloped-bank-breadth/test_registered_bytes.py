"""Regressions against cropping, hidden-RGB loss, opacity changes and recentering."""
import importlib.util
from pathlib import Path
import unittest
from PIL import Image

spec = importlib.util.spec_from_file_location("raw_registered_bytes",Path(__file__).with_name("registered-bytes.py"))
raw = importlib.util.module_from_spec(spec); spec.loader.exec_module(raw)


class RegisteredBytesTests(unittest.TestCase):
    def test_all_transparent_source_rgb_and_full_extent_survive(self):
        original = Image.frombytes("RGBA",(2,2),bytes([11,22,33,0, 1,2,3,0, 44,55,66,0, 77,88,99,0]))
        (a,b),bounds = raw.pair(raw.registered(original,[-7,2]),raw.registered(Image.new("RGBA",(1,1)),[2,-1]))
        self.assertEqual(bounds,(-7,-1,3,4))
        self.assertEqual(a.tobytes()[3*a.width*4:3*a.width*4+8],original.tobytes()[:8])
        self.assertEqual(a.tobytes()[4*a.width*4:4*a.width*4+8],original.tobytes()[8:])
        self.assertEqual(a.getpixel((9,0)),(0,0,0,0))
        self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_partial_alpha_is_not_blended_rounded_or_renormalized(self):
        pixels = bytes([1,2,253,1, 99,37,241,127, 151,177,19,254])
        picture = Image.frombytes("RGBA",(3,1),pixels)
        (a,b),bounds = raw.pair(raw.registered(picture,[0,0]),raw.registered(picture,[0,0]))
        self.assertEqual(bounds,(0,0,3,1))
        self.assertEqual(a.tobytes(),pixels)
        self.assertEqual(a.tobytes(),b.tobytes())

    def test_native_anchor_and_transparent_border_not_recentred(self):
        picture = Image.new("RGBA",(5,3)); picture.putpixel((2,1),(19,29,39,255))
        model = raw.native(picture,{"image_size":[5,3],"model_origin":[11,-4]})
        self.assertEqual(model[1],(-11,4,-6,7))
        self.assertEqual(model[0].tobytes(),picture.tobytes())

    def test_dimension_mode_and_noninteger_anchor_mismatch_are_rejected(self):
        with self.assertRaises(ValueError): raw.native(Image.new("RGBA",(1,1)),{"image_size":[2,1],"model_origin":[0,0]})
        with self.assertRaises(ValueError): raw.registered(Image.new("RGB",(1,1)),[0,0])
        with self.assertRaises(ValueError): raw.registered(Image.new("RGBA",(1,1)),[0.0,0])


if __name__ == "__main__": unittest.main()
