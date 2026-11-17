"""Render or benchmark the packed animation on a remote GPU machine.

Run inside Blender. CUDA/Cycles uses a separate frame cache and restores the
original model daylight; it must never be mixed with the Mac EEVEE frames.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import bpy

ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/'video'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--backend',choices=['CUDA','OPTIX','EEVEE','CPU'],default='CUDA')
    p.add_argument('--gpu-index',type=int,help='Index in the printed list of devices for this backend; omitted uses all.')
    p.add_argument('--samples',type=int,default=32,help='Cycles samples; EEVEE retains the prepared scene settings.')
    p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=2160)
    p.add_argument('--benchmark',action='store_true')
    p.add_argument('--width',type=int,default=3840)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not 1<=args.start<=args.end<=2160 or args.samples<1 or args.width<320 or args.width%2:p.error('Invalid render settings')
    original=json.loads((VIDEO/'walkthrough-manifest.json').read_text())
    scene_path=Path(bpy.data.filepath)
    assert hashlib.sha256(scene_path.read_bytes()).hexdigest()==original['animation_sha256'],'Wrong animation file'
    if bpy.app.version[:2]!=(4,5):
        raise RuntimeError('Use Blender 4.5 LTS to match the prepared animation; recommended patch version is 4.5.9.')
    s=bpy.context.scene;devices=[]
    profile='eevee' if args.backend=='EEVEE' else 'cycles'
    if profile=='cycles':
        s.render.engine='CYCLES';s.cycles.samples=args.samples;s.cycles.use_denoising=True
        s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.03
        # The EEVEE animation added direct/fill suns. Cycles uses the original
        # physically lit Nishita sky, matching the original model stills.
        for obj in s.objects:
            if obj.type=='LIGHT' and obj.name.startswith('Walkthrough ·'):obj.hide_render=True
        s.view_settings.exposure=-1.6
        if args.backend=='CPU':s.cycles.device='CPU';devices=['CPU benchmark only']
        else:
            prefs=bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type=args.backend;prefs.get_devices()
            available=[d for d in prefs.devices if d.type==args.backend]
            print('AVAILABLE_GPUS',[(i,d.name,d.id) for i,d in enumerate(available)],flush=True)
            if not available:raise RuntimeError(f'No {args.backend} GPUs detected. Check NVIDIA driver and Blender build.')
            if args.gpu_index is not None and not 0<=args.gpu_index<len(available):p.error('GPU index out of range')
            selected=available if args.gpu_index is None else [available[args.gpu_index]]
            for d in prefs.devices:d.use=d in selected
            devices=[d.name for d in selected];s.cycles.device='GPU'
    else:
        if args.gpu_index is not None:p.error('EEVEE GPU selection is controlled by the graphics/display backend, not CUDA indices.')
        s.render.engine='BLENDER_EEVEE_NEXT';devices=['Active graphics device; verify driver/display setup']
        s.eevee.taa_render_samples=8
        for obj in s.objects:
            if obj.type=='LIGHT' and obj.name.startswith('Walkthrough ·'):obj.hide_render=False
        s.view_settings.exposure=.15
    s.render.resolution_x=args.width;s.render.resolution_y=round(args.width*9/16);s.render.resolution_percentage=100
    s.render.fps=24;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=97
    s.render.image_settings.color_mode='RGB';s.render.use_stamp=False;s.render.use_persistent_data=True
    s.render.use_motion_blur=True;s.render.motion_blur_shutter=.25
    samples=s.cycles.samples if profile=='cycles' else s.eevee.taa_render_samples
    # Version/backend/device-independent profile separates appearance settings.
    identity=dict(animation_sha256=original['animation_sha256'],engine=profile,backend=args.backend,width=args.width,
                  height=s.render.resolution_y,samples=samples,blender=bpy.app.version_string,
                  worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    signature=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    folder=VIDEO/'remote-benchmarks'/f'{args.backend.lower()}-{args.width}-{samples}' if args.benchmark else VIDEO/f'frames-{profile}'
    folder.mkdir(parents=True,exist_ok=True)
    meta=folder/'profile.json'
    if meta.exists():
        previous=json.loads(meta.read_text())
        if previous['signature']!=signature:raise RuntimeError(f'{folder} has another rendering profile. Preserve or move it first.')
    else:
        temporary=meta.with_name(f'profile-{os.getpid()}.tmp')
        temporary.write_text(json.dumps(dict(signature=signature,**identity),indent=2)+'\n')
        temporary.replace(meta)
    print('RENDER_PROFILE',json.dumps(dict(**identity,devices=devices)),flush=True)
    if args.benchmark:
        results=[]
        for frame in [120,504,1032,1560,1992]:
            s.frame_set(frame);s.render.filepath=str(folder/f'{profile}-{frame:04}.jpg')
            started=time.perf_counter();bpy.ops.render.render(write_still=True)
            seconds=time.perf_counter()-started
            result=dict(frame=frame,seconds=round(seconds,3));results.append(result)
            print('BENCHMARK_FRAME',json.dumps(result),flush=True)
        report=dict(profile=identity,devices=devices,frames=results,
                    note='Still-frame timings include setup. Benchmark a short animation range before estimating a full render.')
        (folder/f'{profile}-benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
        return
    if args.width!=3840:raise RuntimeError('Production frames must be native 3840 × 2160. Use --benchmark for smaller tests.')
    for f in folder.glob('*.jpg'):
        with f.open('rb') as stream:
            if f.stat().st_size<4:complete=False
            else:stream.seek(-2,2);complete=stream.read()==b'\xff\xd9'
        if not complete:f.unlink()
    s.render.filepath=str(folder)+'/'
    s.render.use_overwrite=False;s.frame_start=args.start;s.frame_end=args.end
    started=time.perf_counter()
    def progress(scene):
        print('REMOTE_FRAME',scene.frame_current,'range',args.start,args.end,'elapsed',round(time.perf_counter()-started,2),flush=True)
    bpy.app.handlers.render_write.append(progress)
    bpy.ops.render.render(animation=True)
    report=dict(profile=identity,devices=devices,start=args.start,end=args.end,elapsed_seconds=time.perf_counter()-started)
    (folder/f'worker-{args.start:04}-{args.end:04}.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
