"""Native-resolution, restartable 90-second camera walk through the Alvir model."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/'video'
FPS=24
TOTAL=90*FPS
D=json.loads((ROOT/'data/scene.json').read_text())
H=np.load(ROOT/'data/terrain.npy')
X0,Y0,X1,Y1=D['terrain']['bounds']


def ground(x,y):
    u=np.clip((x-X0)/(X1-X0)*(H.shape[1]-1),0,H.shape[1]-1.000001)
    v=np.clip((y-Y0)/(Y1-Y0)*(H.shape[0]-1),0,H.shape[0]-1.000001)
    a,b=int(u),int(v);fx,fy=u-a,v-b
    return float((H[b,a]*(1-fx)+H[b,a+1]*fx)*(1-fy)+(H[b+1,a]*(1-fx)+H[b+1,a+1]*fx)*fy)


def shots():
    routes=json.loads((VIDEO/'walk-routes.json').read_text())['routes']
    result=[dict(name='Alvir and its valley',seconds=10,lens=43,kind='aerial',
                 start=(750,-1000,650),end=(610,-840,540),target=(-100,180,20))]
    for route in routes:
        result.append(dict(name=route['name'],seconds=22,lens=27,kind='walk',route=route))
    result.append(dict(name='Orchards and the village',seconds=14,lens=43,kind='aerial',
                       start=(-560,-310,230),end=(-700,-470,340),target=(-80,150,15)))
    first=1
    for s in result:
        s['first']=first;s['last']=first+s['seconds']*FPS-1;first=s['last']+1
    assert first==TOTAL+1
    return result


def pose(shot,t):
    # Small eased shoulders; nearly constant walking speed through the shot.
    e=.07
    if t<e:u=t*t/(2*e)
    elif t>1-e:u=1-e-(1-t)**2/(2*e)
    else:u=t-e/2
    u/=1-e
    if shot['kind']=='aerial':
        return Vector(shot['start']).lerp(Vector(shot['end']),u),Vector(shot['target'])
    r=shot['route'];a,b=map(Vector,r['points_xy']);p=a.lerp(b,u)
    direction=(b-a).normalized()
    # Look along the street with a level horizon. No artificial head bob.
    q=p+direction*10
    eye=Vector((p.x,p.y,ground(*p)+r['eye_above_dem_m']))
    target=Vector((q.x,q.y,eye.z+.18))
    return eye,target


def sun(collection,name,energy,color,azimuth,elevation,shadows=True):
    light=bpy.data.lights.new(name,'SUN');light.energy=energy;light.color=color
    light.angle=.06;light.use_shadow=shadows
    o=bpy.data.objects.new(name,light);collection.objects.link(o)
    a,e=math.radians(azimuth),math.radians(elevation)
    direction=Vector((math.cos(a)*math.cos(e),math.sin(a)*math.cos(e),math.sin(e)))
    o.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()


def prepare(width,samples):
    signature=hashlib.sha256((ROOT/'output/alvir_village.blend').read_bytes()+
        Path(__file__).read_bytes()+(VIDEO/'walk-routes.json').read_bytes()+
        (ROOT/'data/terrain.npy').read_bytes()+(ROOT/'data/scene.json').read_bytes()+
        (ROOT/'data/visual-theme.json').read_bytes()+(ROOT/'scripts/visual_theme.py').read_bytes()+
        f'{width}:{samples}'.encode()).hexdigest()
    manifest_file=VIDEO/'walkthrough-manifest.json'
    if any((VIDEO/'frames').glob('*.jpg')):
        old=json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
        if old.get('render_signature')!=signature:
            raise RuntimeError('Frame cache belongs to different settings; preserve or move it before preparing again.')
    s=bpy.context.scene
    sys.path.insert(0,str(ROOT/'scripts'))
    from visual_theme import apply_theme
    apply_theme(s)
    s.render.engine='BLENDER_EEVEE_NEXT'
    s.eevee.taa_render_samples=samples;s.eevee.use_raytracing=False
    s.render.resolution_x=width;s.render.resolution_y=round(width*9/16);s.render.resolution_percentage=100
    s.render.fps=FPS;s.frame_start=1;s.frame_end=TOTAL
    s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=97
    s.render.image_settings.color_mode='RGB';s.render.use_stamp=False
    s.render.use_motion_blur=True;s.render.motion_blur_shutter=.25
    s.render.use_persistent_data=True;s.view_settings.exposure=.15
    collection=bpy.data.collections.new('12 | Walkthrough cameras and daylight')
    s.collection.children.link(collection)
    sun(collection,'Walkthrough · afternoon sun',3.0,(1,.90,.78),230,34)
    sun(collection,'Walkthrough · diffuse sky fill',.65,(.72,.83,1),40,70,False)
    s.timeline_markers.clear()
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    checks=[]
    for number,shot in enumerate(shots(),1):
        print('CHECKING_ROUTE',shot['name'],flush=True)
        previous=None;poses=[]
        # Check a static dependency graph before changing any camera transforms.
        bpy.context.view_layer.update()
        for frame in range(shot['first'],shot['last']+1):
            point,target=pose(shot,(frame-shot['first'])/(shot['last']-shot['first']))
            if previous is not None:
                direction=point-previous
                if direction.length>1e-7:
                    hit,*_=s.ray_cast(depsgraph,previous,direction.normalized(),distance=direction.length)
                    if hit:raise RuntimeError(f'Camera path intersection: {shot["name"]}, frame {frame}')
            for axis in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
                hit,loc,normal,face,obj,matrix=s.ray_cast(depsgraph,point,Vector(axis),distance=.35)
                if hit:raise RuntimeError(f'Camera clearance <35cm: {obj.name}, {shot["name"]}, frame {frame}')
            poses.append((frame,point,target));previous=point
        print('ROUTE_CLEAR',shot['name'],flush=True)
        data=bpy.data.cameras.new(f'Walk {number:02} · '+shot['name']);data.lens=shot['lens']
        data.clip_start=.06;data.clip_end=15000
        cam=bpy.data.objects.new(data.name,data);collection.objects.link(cam);cam.rotation_mode='QUATERNION'
        marker=s.timeline_markers.new(shot['name'],frame=shot['first']);marker.camera=cam
        if number==1:s.camera=cam
        previous_q=None
        for frame,point,target in poses:
            cam.location=point;q=(target-point).to_track_quat('-Z','Y')
            if previous_q is not None and q.dot(previous_q)<0:q.negate()
            cam.rotation_quaternion=q
            cam.keyframe_insert(data_path='location',frame=frame)
            cam.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            previous_q=q.copy()
        checks.append(dict(name=shot['name'],kind=shot['kind'],first=shot['first'],last=shot['last'],
                           path_collision_free=True,camera_clearance_m=.35))
    s.frame_set(1)
    s['Walkthrough']='90 seconds, native 4K/24fps. 66 seconds pedestrian camera, 24 seconds aerial orientation.'
    s['Walkthrough evidence']='Original mapped footprint model; architecture, planting and heights remain estimated.'
    VIDEO.mkdir(exist_ok=True)
    out=ROOT/'output/alvir_walkthrough.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    manifest=dict(width=width,height=s.render.resolution_y,fps=FPS,frames=TOTAL,duration_seconds=90,
                  samples=samples,engine='EEVEE',frame_format='JPEG quality 97',
                  original_scene='output/alvir_village.blend',animation_scene='output/alvir_walkthrough.blend',
                  render_signature=signature,animation_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),shots=checks)
    manifest_file.write_text(json.dumps(manifest,indent=2)+'\n')
    print('WALKTHROUGH_PREPARED',json.dumps(manifest),flush=True)
    return s


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--width',type=int,default=3840);p.add_argument('--samples',type=int,default=8)
    p.add_argument('--preview',action='store_true');p.add_argument('--prepared',action='store_true')
    p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=TOTAL)
    p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.width%2 or args.width<320 or args.samples<1 or not 1<=args.start<=args.end<=TOTAL:p.error('Invalid render settings')
    s=bpy.context.scene if args.prepared else prepare(args.width,args.samples)
    if args.prepared:
        m=json.loads((VIDEO/'walkthrough-manifest.json').read_text())
        assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==m['animation_sha256']
    if args.prepare_only:return
    folder=VIDEO/('previews' if args.preview else 'frames');folder.mkdir(exist_ok=True)
    if args.preview:
        for shot in shots():
            frame=(shot['first']+shot['last'])//2;s.frame_set(frame)
            s.render.filepath=str(folder/f'shot-{frame:04}.jpg')
            bpy.ops.render.render(write_still=True)
        return
    # Keep EEVEE scene state alive across frames, and resume complete cached frames.
    for f in folder.glob('*.jpg'):
        with f.open('rb') as stream:
            if f.stat().st_size<4:complete=False
            else:stream.seek(-2,2);complete=stream.read()==b'\xff\xd9'
        if not complete:f.unlink()
    s.render.filepath=str(folder)+'/'
    s.render.use_overwrite=False;s.frame_start=args.start;s.frame_end=args.end
    def progress(scene):print(f'WALK_FRAME {scene.frame_current}/{TOTAL}',flush=True)
    bpy.app.handlers.render_write.append(progress)
    bpy.ops.render.render(animation=True)


if __name__=='__main__':main()
