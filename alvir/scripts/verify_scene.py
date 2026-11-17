"""Reopen the saved Blender artifact and check model/source agreement."""
import json
import math
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/scene.json').read_text())
scene=bpy.context.scene
assert scene.unit_settings.scale_length==1 and scene.unit_settings.system=='METRIC'
assert scene['Horizontal CRS']=='EPSG:32639'
assert scene.cycles.device=='CPU'
for b in D['buildings']:
    o=bpy.data.objects[b['id']+' · walls']
    assert o['height_evidence']==b['height_evidence']
    foundation=bpy.data.objects[b['id']+' · foundations']
    points=[foundation.matrix_world @ v.co for v in foundation.data.vertices]
    assert len(points)==2*len(b['polygon'])
    for actual,expected in zip(points[:len(b['polygon'])],b['polygon']):
        assert math.hypot(actual.x-expected[0],actual.y-expected[1])<.002,'Transformed footprint vertex mismatch'
    for axis in (0,1):
        assert abs(min(v[axis] for v in points)-min(p[axis] for p in b['polygon']))<.002
        assert abs(max(v[axis] for v in points)-max(p[axis] for p in b['polygon']))<.002
meshes={o.data.name:o.data for o in scene.objects if o.type=='MESH'}
assert all(math.isfinite(c) for m in meshes.values() for v in m.vertices for c in v.co)
external=[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file]
assert not external
core=bpy.data.objects['Alvir · DEM-derived terrain context'].data
context=bpy.data.objects['Regional relief · terrain only'].data
x0,y0,x1,y1=D['terrain']['bounds']
boundary=[v.co for v in core.vertices if min(abs(v.co.x-x0),abs(v.co.x-x1),abs(v.co.y-y0),abs(v.co.y-y1))<.001]
lookup={(round(v.co.x,3),round(v.co.y,3)):v.co.z for v in context.vertices}
for v in boundary:
    assert abs(lookup[(round(v.x,3),round(v.y,3))]-v.z)<.001,'Terrain border seam'
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
camera=bpy.data.objects['04 · Geographic plan']
for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
    p=world_to_camera_view(scene,camera,Vector((x,y,0)))
    assert p.z>0 and 0<=p.x<=1 and 0<=p.y<=1,'Plan crops study boundary'
report=dict(result='passed',saved_building_footprints_checked=len(D['buildings']),
            transformed_footprint_vertex_tolerance_m=.002,metric_scale=True,crs=scene['Horizontal CRS'],
            external_images=external,portable_cpu_default=True,shared_terrain_border_vertices=len(boundary),
            full_study_area_plan_framing=True,
            note='Checks agreement with source polygons; does not certify real-world survey accuracy.')
(ROOT/'output/integration-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
