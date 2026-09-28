import math
import unittest

from aircraft_clearance import box_overlap, parse_trace


class AircraftClearanceTests(unittest.TestCase):
    def test_face_edge_and_corner_contacts_are_not_intersections(self):
        for low,high in (((1,-1,-1),(2,1,1)),((1,1,-1),(2,2,1)),((1,1,1),(2,2,2))):
            self.assertEqual(box_overlap((0,0,0),(1,1,1),1,0,low,high),0)
        self.assertGreater(box_overlap((0,0,0),(1,1,1),1,0,(0.9,-1,-1),(2,1,1)),0)

    def test_rotated_thin_wing_rejects_an_aabb_only_corner_hit(self):
        diagonal = math.sqrt(0.5)
        self.assertEqual(box_overlap((0,0,0),(2,0.1,0.5),diagonal,diagonal,(1,-1.4,-0.2),(1.4,-1,0.2)),0)
        self.assertGreater(box_overlap((0,0,0),(2,0.1,0.5),diagonal,diagonal,(1,1,-0.2),(1.4,1.4,0.2)),0)
        self.assertEqual(box_overlap((0,0,0),(2,0.1,0.5),diagonal,diagonal,(1,1,0.5),(1.4,1.4,0.7)),0)

    def test_original_axial_pose_and_large_world_translation_agree(self):
        for angle in (0,math.pi/2,math.pi,-math.pi/2):
            cosine,sine = math.cos(angle),math.sin(angle)
            low,high = (-0.1,-0.1,0.2),(0.1,0.1,0.4)
            ordinary = box_overlap((0,0,0),(2,0.3,0.5),cosine,sine,low,high)
            shift = (32768,-16384,512)
            translated = box_overlap(shift,(2,0.3,0.5),cosine,sine,tuple(a+b for a,b in zip(low,shift)),tuple(a+b for a,b in zip(high,shift)))
            self.assertGreater(ordinary,0)
            self.assertAlmostEqual(ordinary,translated)

    def test_multiple_viewports_deduplicate_only_identical_frame_transforms(self):
        airport = 'clearance airport frame 4 tile 8 graphics 19 state 48 origin 16,32,8'
        aircraft = 'clearance aircraft frame 4 vehicle 2 engine 251 state 6 raw 38,8,9 direction 5 pose 37.75,8,8,0.25'
        planes,bodies = parse_trace('\n'.join((airport,aircraft,airport,aircraft)))
        self.assertEqual(len(planes[4]),1)
        self.assertEqual(len(bodies[4]),1)
        with self.assertRaisesRegex(ValueError,'inconsistent aircraft'):
            parse_trace('\n'.join((airport,aircraft,aircraft.replace('37.75','38'))))


if __name__ == '__main__':
    unittest.main()
