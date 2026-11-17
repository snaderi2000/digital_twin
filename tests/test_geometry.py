import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry import MeshBuffer, layout, pointed_arch


class GeometryTests(unittest.TestCase):
    def test_arch_endpoints_symmetry_and_monotonicity(self):
        p = pointed_arch(2.8, 3.65, 32)
        for actual, expected in zip(p[0], (-2.8,0)):
            self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(p[32][0],0)
        self.assertAlmostEqual(p[32][1],3.65)
        self.assertTrue(all(p[i+1][0] > p[i][0] for i in range(64)))
        for left,right in zip(p,reversed(p)):
            self.assertAlmostEqual(left[0],-right[0])
            self.assertAlmostEqual(left[1],right[1])

    def test_layout_and_clearances(self):
        c=json.loads((ROOT/'config/bridge.json').read_text())
        pitch, centers=layout(c)
        self.assertEqual(len(centers),33)
        self.assertAlmostEqual(centers[0]-pitch/2,-c['length']/2+c['end_margin'])
        self.assertAlmostEqual(centers[-1]+pitch/2,c['length']/2-c['end_margin'])
        self.assertGreater(pitch-c['lower_opening'],0)
        self.assertGreater(c['deck_height'],c['lower_spring']+c['lower_rise'])
        self.assertGreater(c['roof_height'],c['upper_spring']+c['upper_rise'])
        self.assertGreater(pitch/3,c['upper_opening'])

    def test_mesh_finite_indices_and_closed_components(self):
        b=MeshBuffer()
        b.arch_wall(0,0,8.7,5.6,0,2.05,3.65,6.4,13.8)
        b.arch_ring(0,-7,5.6,2.05,3.65,.25,.08)
        edges={}
        for f in b.faces:
            for a,v in zip(f,f[1:]+f[:1]):
                self.assertLess(v,len(b.vertices))
                key=tuple(sorted((a,v)))
                edges[key]=edges.get(key,0)+1
        self.assertTrue(all(v==2 for v in edges.values()))
        self.assertTrue(all(math.isfinite(v) for p in b.vertices for v in p))

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError): pointed_arch(0,3)
        with self.assertRaises(ValueError):
            layout(dict(river_spans=1,length=10,end_margin=1,lower_opening=9))

    def test_crossed_vault_preserves_longitudinal_headroom(self):
        b=MeshBuffer()
        b.crossed_vault(0,5.6,13.8,2.05,3.65,6.43)
        centerline=[p for p in b.vertices if abs(p[1])<1e-8]
        self.assertTrue(centerline)
        self.assertTrue(all(p[2]>=4.3-1e-8 for p in centerline))
        # Every edge belongs to two faces, including the groin and end boundaries.
        incidence={}
        for f in b.faces:
            for a,v in zip(f,f[1:]+f[:1]):
                key=tuple(sorted((a,v)))
                incidence[key]=incidence.get(key,0)+1
        self.assertTrue(all(v==2 for v in incidence.values()))


if __name__=='__main__': unittest.main()
