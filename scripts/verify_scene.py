"""Read-only integration checks on a generated .blend; run with Blender -b FILE."""
import itertools
import json
import math
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
config=json.loads(scene['Configuration'])
spans=[o for o in scene.objects if 'span_number' in o]
assert len(spans)==33
assert {o['span_number'] for o in spans}==set(range(1,34))
assert scene.unit_settings.system=='METRIC' and scene.unit_settings.scale_length==1
assert scene.cycles.device=='CPU', 'Saved scene must use a portable default device'
assert bpy.data.objects['Flowing river · surface'].data.materials[0].node_tree.animation_data
external=[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file]
assert not external, f'Unexpected external image dependencies: {external}'
for key in ('PROJECT DATUM · local metre coordinates','Central pedestrian deck'):
    assert key in bpy.data.objects, key
# An unobstructed centerline must pass through the entire lower gallery.
bpy.context.view_layer.update()
hit,location,normal,index,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),Vector((-125,0,2.65)),Vector((1,0,0)),distance=260)
assert not hit, f'Lower gallery blocked by {obj.name} at {tuple(location)}'
for name in ('02 · Complete west elevation','06 · Architectural overview'):
    cam=bpy.data.objects[name]
    for point in itertools.product((-config['length']/2,config['length']/2),(-8,8),(0,13)):
        screen=world_to_camera_view(scene,cam,Vector(point))
        assert screen.z>0 and 0<=screen.x<=1 and 0<=screen.y<=1, (name,point,tuple(screen))
report={'reopened_blend':str(Path(bpy.data.filepath).name),'numbered_spans':33,
        'external_image_dependencies':external,'water_shader_animation':True,
        'full_bridge_camera_framing':['elevation','aerial'],
        'metric_scale':True,'portable_default_device':'CPU',
        'lower_gallery_clear_length_m':260,'result':'passed'}
(ROOT/'output/integration-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('INTEGRATION_CHECK',json.dumps(report))
