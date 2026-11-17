"""Checks on the source-to-model mapping, independent of Blender rendering."""
import json
from pathlib import Path
import unittest

import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/scene.json').read_text())


class DataTests(unittest.TestCase):
    def test_projection_and_origin(self):
        transformer=Transformer.from_crs(4326,D['terrain']['crs'],always_xy=True)
        e,n=transformer.transform(50.0018,35.3867)
        self.assertAlmostEqual(e,D['terrain']['origin_utm'][0],places=5)
        self.assertAlmostEqual(n,D['terrain']['origin_utm'][1],places=5)
        self.assertTrue(1700<D['terrain']['origin_utm'][2]<1900)

    def test_building_footprints_preserved(self):
        source=json.loads((ROOT/'data/buildings_wgs84.geojson').read_text())['features']
        self.assertEqual(len(source),len(D['buildings']))
        self.assertEqual(len({b['id'] for b in D['buildings']}),len(source))
        self.assertTrue(all(Polygon(b['polygon']).is_valid for b in D['buildings']))
        self.assertTrue(all(b['height_evidence']=='unmeasured_typology_estimate' for b in D['buildings']))
        self.assertTrue(all(b['foundation_bottom']<b['base_z'] for b in D['buildings']))

    def test_terrain_not_flat_or_nonfinite(self):
        h=np.load(ROOT/'data/terrain.npy')
        self.assertEqual(list(h.shape),D['terrain']['shape'])
        self.assertTrue(np.isfinite(h).all())
        self.assertGreater(float(np.ptp(h)),300)
        self.assertLess(float(np.ptp(h)),500)

    def test_roads_have_source_identifiers(self):
        self.assertGreater(len(D['roads']),40)
        for road in D['roads']:
            self.assertTrue(road['id'].startswith('osm-way-'))
            self.assertGreaterEqual(len(road['points']),2)
            self.assertGreater(road['width_m'],0)
            self.assertEqual(road['width_evidence'],'estimated')


if __name__=='__main__':unittest.main()
