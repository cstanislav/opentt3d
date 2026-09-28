import unittest

from bulldozer_motion import audit, SOURCE


class BulldozerMotionTests(unittest.TestCase):
    def test_reverse_movement_preserves_the_original_displayed_direction(self):
        # Original state3 reverses along X but keeps sprite1418 (SW).
        # Sixteen/seventeen completed movement steps wrap progress at128/136.
        first = 'voxel effect frame 50 vehicle 4 type 8 sprite 1418 climate 0 animation 3,1 progress 128 raw 62,76,8 origin 62,76,16 opacity 1 pick 0'
        second = 'voxel effect frame 66 vehicle 4 type 8 sprite 1418 climate 0 animation 3,2 progress 136 raw 61,76,8 origin 61,76,16 opacity 1 pick 0'
        source = SOURCE.read_text()
        result = audit(first+'\n'+second,source)
        self.assertEqual(result['lifecycles'][0]['anchor'],(60,80,8))
        self.assertEqual(result['lifecycles'][0]['steps'],[16,17])
        self.assertEqual(result['complete_presented_lifecycles'],0)
        with self.assertRaisesRegex(ValueError,'sprite or progress'):
            audit(first.replace('sprite 1418','sprite 1416'),source)
        with self.assertRaisesRegex(ValueError,'displacement'):
            audit(first+'\n'+second.replace('61,76','63,76'),source)

    def test_effects_preserve_their_unclickable_terrain_relative_placement(self):
        line = 'voxel effect frame 1 vehicle 4 type 8 sprite 1416 climate 3 animation 0,0 progress 0 raw 60,80,8 origin 60,80,16 opacity 1 pick 0'
        source = SOURCE.read_text()
        for invalid in (line.replace('pick 0','pick 5'),line.replace('origin 60,80,16','origin 60,80,8'),line.replace('opacity 1','opacity 0.38')):
            with self.assertRaisesRegex(ValueError,'unclickable ownership'):
                audit(invalid,source)


if __name__ == '__main__':
    unittest.main()
