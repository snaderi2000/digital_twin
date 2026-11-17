"""Render the saved Alvir scene, keeping the .blend on a portable CPU default."""
import argparse
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[1]
CAMERAS={'aerial':'01 · Village and valley','village':'02 · Village fabric',
         'orchards':'03 · Orchard edge','plan':'04 · Geographic plan','detail':'05 · Inferred façade study'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--views',default='aerial')
    p.add_argument('--width',type=int,default=2560)
    p.add_argument('--samples',type=int,default=64)
    p.add_argument('--suffix',default='')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    names=list(CAMERAS) if args.views=='all' else args.views.split(',')
    if any(n not in CAMERAS for n in names):p.error('Unknown view')
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=args.samples
    scene.cycles.device='CPU';scene.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='METAL';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='METAL'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except Exception:pass
    scene.render.resolution_x=args.width;scene.render.resolution_y=round(args.width*9/16)
    records_path=ROOT/'output/renders.json'
    records=json.loads(records_path.read_text()) if records_path.exists() else {}
    for view in names:
        scene.camera=bpy.data.objects[CAMERAS[view]]
        scene.render.filepath=str(ROOT/'renders'/f'{view}{args.suffix}.png')
        bpy.ops.render.render(write_still=True)
        records[view+args.suffix]=dict(file=f'renders/{view}{args.suffix}.png',width=args.width,
                                    height=scene.render.resolution_y,samples=args.samples,engine='Cycles')
        records_path.write_text(json.dumps(records,indent=2)+'\n')
        print('ALVIR_RENDER_COMPLETE',view,flush=True)


if __name__=='__main__':main()
