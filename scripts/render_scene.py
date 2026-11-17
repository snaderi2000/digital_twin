"""Render the saved scene without rebuilding geometry. Run inside Blender."""
import argparse
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[1]
CAMERAS={
    'hero':'01 · River panorama',
    'elevation':'02 · Complete west elevation',
    'detail':'03 · Masonry and cutwater',
    'deck':'04 · Upper promenade',
    'gallery':'05 · Lower longitudinal gallery',
    'aerial':'06 · Architectural overview',
}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--views',default='hero')
    p.add_argument('--quality',choices=['preview','standard','final'],default='standard')
    p.add_argument('--frame',type=int,default=1)
    p.add_argument('--suffix',default='')
    p.add_argument('--samples',type=int,help='Optional maximum sample override')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    names=list(CAMERAS) if args.views=='all' else args.views.split(',')
    for name in names:
        if name not in CAMERAS: p.error(f'Unknown view: {name}. Choices: {", ".join(CAMERAS)}')
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    # Device preferences are not stored in .blend files; initialize them per process.
    scene.cycles.device='CPU'
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='METAL'; prefs.get_devices()
        for device in prefs.devices:
            device.use=device.type=='METAL'
        if any(d.use for d in prefs.devices): scene.cycles.device='GPU'
    except Exception:
        pass
    scene.cycles.samples={'preview':32,'standard':96,'final':256}[args.quality]
    if args.samples is not None:
        if args.samples<1: p.error('--samples must be positive')
        scene.cycles.samples=args.samples
    scene.cycles.adaptive_threshold=.025 if args.quality=='preview' else .012
    scene.render.resolution_x={'preview':1440,'standard':2560,'final':3840}[args.quality]
    scene.render.resolution_y=round(scene.render.resolution_x*9/16)
    scene.frame_set(args.frame)
    for name in names:
        scene.camera=bpy.data.objects[CAMERAS[name]]
        scene.render.filepath=str(ROOT/'renders'/f'{name}{args.suffix}.png')
        bpy.ops.render.render(write_still=True)
        manifest=ROOT/'output/renders.json'
        records=json.loads(manifest.read_text()) if manifest.exists() else {}
        records[name+args.suffix]={'file':f'renders/{name}{args.suffix}.png',
            'camera':scene.camera.name,'width':scene.render.resolution_x,
            'height':scene.render.resolution_y,'max_samples':scene.cycles.samples,
            'frame':args.frame,'engine':'Cycles','blender':bpy.app.version_string}
        manifest.write_text(json.dumps(records,indent=2)+'\n')
        print('RENDER_COMPLETE',name,flush=True)

if __name__=='__main__': main()
