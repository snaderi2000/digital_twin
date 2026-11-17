"""Prepare and render an actual animated camera tour using Blender EEVEE.

Original Cycles scene is left intact. A separate editable animation scene is saved.
Frames are restartable; use encode_video.py to make the MP4 after rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from flythrough_path import FPS, TOTAL_FRAMES, pose, shot_ranges


def prepare(width, samples):
    signature=hashlib.sha256((ROOT/'output/si_o_se_pol.blend').read_bytes()
        +(ROOT/'scripts/flythrough_path.py').read_bytes()
        +Path(__file__).read_bytes()+f'{width}:{samples}'.encode()).hexdigest()
    manifest_path=ROOT/'video/manifest.json'
    if any((ROOT/'video/frames').glob('*.png')):
        previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        if previous.get('render_signature')!=signature:
            raise RuntimeError('Existing video frames use different settings/source. Move or remove video/frames before rebuilding.')
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples=samples
    scene.eevee.use_raytracing=True
    scene.eevee.ray_tracing_options.resolution_scale='2'
    scene.render.resolution_x=width
    scene.render.resolution_y=round(width*9/16)
    scene.render.resolution_percentage=100
    scene.render.fps=FPS
    scene.frame_start=1; scene.frame_end=TOTAL_FRAMES
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=15
    scene.render.film_transparent=False
    scene.view_settings.exposure=.15
    scene.render.use_motion_blur=True
    scene.render.motion_blur_shutter=.2
    scene.render.use_persistent_data=True
    # Daytime tour: keep the sun and sky fill; omit the 66 night-time arch washers.
    for light in scene.objects:
        if light.type=='LIGHT' and light.name.startswith('Warm concealed arch wash'):
            light.hide_render=True
    collection=bpy.data.collections.new('15 | Fly-through cameras')
    scene.collection.children.link(collection)
    scene.timeline_markers.clear()
    checks=[]
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for index,(shot,first,last) in enumerate(shot_ranges()):
        data=bpy.data.cameras.new(f'Tour {index+1:02} · {shot["name"]}')
        cam=bpy.data.objects.new(data.name,data); collection.objects.link(cam)
        data.lens=shot['lens']; data.clip_start=.05; data.clip_end=2500
        cam.rotation_mode='QUATERNION'
        marker=scene.timeline_markers.new(shot['name'],frame=first); marker.camera=cam
        if first==1: scene.camera=cam
        previous=None
        for frame in range(first,last+1):
            position,target=pose(shot,(frame-first)/(last-first))
            cam.location=position
            cam.rotation_quaternion=(Vector(target)-cam.location).to_track_quat('-Z','Y')
            cam.keyframe_insert(data_path='location',frame=frame)
            cam.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            # Check the path and a 15 cm camera safety radius against actual geometry.
            point=Vector(position)
            if previous is not None and (point-previous).length>1e-8:
                direction=point-previous
                hit,*rest=scene.ray_cast(depsgraph,previous,direction.normalized(),distance=direction.length)
                if hit: raise RuntimeError(f'Camera path intersects geometry in {shot["name"]}, frame {frame}')
            for axis in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                hit,location,normal,face,obj,matrix=scene.ray_cast(depsgraph,point,Vector(axis),distance=.15)
                if hit: raise RuntimeError(f'Camera is too close to {obj.name}, frame {frame}')
            previous=point
        checks.append(dict(shot=shot['name'],first=first,last=last,path_collision_free=True))
    # EEVEE needs an explicit sun for the procedural sky's direct light.
    sun=bpy.data.lights.new('Tour · late afternoon sun','SUN')
    sun.energy=2.3; sun.color=(1,.84,.66); sun.angle=.045
    obj=bpy.data.objects.new(sun.name,sun); collection.objects.link(obj)
    import math
    direction=Vector((math.cos(math.radians(220))*math.cos(math.radians(17)),
                      math.sin(math.radians(220))*math.cos(math.radians(17)),math.sin(math.radians(17))))
    obj.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    # An animated reflection shader keeps the real-time water stable in motion.
    water=bpy.data.objects['Flowing river · surface'].data.materials[0]
    nodes,links=water.node_tree.nodes,water.node_tree.links
    shader=nodes.get('Principled BSDF')
    shader.inputs['Transmission Weight'].default_value=0
    shader.inputs['Metallic'].default_value=.35
    shader.inputs['Roughness'].default_value=.22
    for link in list(links):
        if link.to_node.type=='OUTPUT_MATERIAL' and link.to_socket.name=='Volume': links.remove(link)
    water.node_tree.animation_data_clear()
    flow=nodes.get('Flow · animated river current')
    flow.inputs['Location'].driver_add('default_value',1).driver.expression='-0.035*(frame-1)'
    scene['Video']=f'{TOTAL_FRAMES/FPS:g}-second camera fly-through, 24 fps; EEVEE lighting/water adaptation of the original model.'
    scene.frame_set(1)
    (ROOT/'video').mkdir(exist_ok=True)
    manifest=dict(fps=FPS,frames=TOTAL_FRAMES,duration_seconds=TOTAL_FRAMES/FPS,
                  width=scene.render.resolution_x,height=scene.render.resolution_y,
                  engine='EEVEE',samples=samples,shots=checks,
                  original_scene='output/si_o_se_pol.blend',
                  animation_scene='output/si_o_se_pol_flythrough.blend',render_signature=signature)
    (ROOT/'video/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/si_o_se_pol_flythrough.blend'),compress=True)
    manifest['animation_sha256']=hashlib.sha256((ROOT/'output/si_o_se_pol_flythrough.blend').read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    return scene


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--width',type=int,default=1920)
    p.add_argument('--samples',type=int,default=16)
    p.add_argument('--preview',action='store_true')
    p.add_argument('--start',type=int,default=1)
    p.add_argument('--end',type=int,default=TOTAL_FRAMES)
    p.add_argument('--prepared',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.width<320 or args.width%2: p.error('--width must be even and at least 320')
    if args.samples<1 or not 1<=args.start<=args.end<=TOTAL_FRAMES: p.error('Invalid sample count/frame range')
    scene=bpy.context.scene if args.prepared else prepare(args.width,args.samples)
    if args.prepared:
        manifest=json.loads((ROOT/'video/manifest.json').read_text())
        digest=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
        if digest!=manifest.get('animation_sha256'):
            raise RuntimeError('Animation scene differs from the frame manifest; prepare the tour again before resuming.')
        if manifest['frames']!=TOTAL_FRAMES:
            raise RuntimeError('Shot timing changed. Prepare the animation again before rendering.')
    frames=([round((first+last)/2) for shot,first,last in shot_ranges()] if args.preview else range(args.start,args.end+1))
    folder=ROOT/'video'/('previews' if args.preview else 'frames')
    folder.mkdir(parents=True,exist_ok=True)
    if not args.preview:
        # One animation render retains EEVEE's scene state between frames. Existing
        # complete frames can be resumed without starting the tour over.
        scene.render.filepath=str(folder)+'/'
        for path in folder.glob('*.png'):
            with path.open('rb') as f:
                complete=path.stat().st_size>=24
                if complete:
                    f.seek(-12,2); complete=b'IEND' in f.read()
            if not complete: path.unlink()
        scene.render.use_overwrite=False
        scene.frame_start=args.start; scene.frame_end=args.end
        def progress(scene):
            print(f'VIDEO_FRAME {scene.frame_current}/{TOTAL_FRAMES}',flush=True)
        bpy.app.handlers.render_write.append(progress)
        bpy.ops.render.render(animation=True)
        return
    for frame in frames:
        destination=folder/f'{frame:04}.png'
        if destination.exists() and not args.preview: continue
        scene.frame_set(frame)
        scene.render.filepath=str(destination)
        start=time.time()
        bpy.ops.render.render(write_still=True)
        print(f'VIDEO_FRAME {frame}/{TOTAL_FRAMES} {time.time()-start:.2f}s',flush=True)


if __name__=='__main__': main()
