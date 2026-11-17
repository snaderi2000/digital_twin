#!/usr/bin/env python3
"""Commands for the Alvir model; use a geospatial Python environment for prepare."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from manage import blender


def main():
    p=argparse.ArgumentParser(description='Alvir geospatial reconstruction')
    p.add_argument('command',choices=['fetch','prepare','build','render','open','verify','test','map','video','encode-video','open-video'])
    p.add_argument('--views',default='all')
    p.add_argument('--width',type=int)
    p.add_argument('--samples',type=int)
    p.add_argument('--preview',action='store_true')
    p.add_argument('--prepared',action='store_true')
    p.add_argument('--start',type=int,default=1)
    p.add_argument('--end',type=int,default=2160)
    args=p.parse_args()
    args.width=args.width or (3840 if args.command=='video' else 2560)
    args.samples=args.samples or (8 if args.command=='video' else 64)
    if args.command=='encode-video':
        return subprocess.call([sys.executable,str(ROOT/'scripts/encode_walkthrough.py')])
    if args.command in ('fetch','prepare','test','map'):
        scripts={'fetch':['fetch_data.py'],'prepare':['prepare_data.py','landscape.py','terrain_texture.py'],
                 'test':['test_data.py'],'map':['draw_map.py']}[args.command]
        for script in scripts:
            subprocess.run([sys.executable,str(ROOT/'scripts'/script)],check=True)
        return 0
    exe=blender();scene=ROOT/'output/alvir_village.blend'
    if args.command=='open-video' or (args.command=='video' and args.prepared):scene=ROOT/'output/alvir_walkthrough.blend'
    if args.command in ('open','open-video'):
        subprocess.Popen([exe,str(scene)]);return 0
    cmd=[exe,'--background','--threads','8','--python-exit-code','1']
    if args.command=='build':cmd+=['--python',str(ROOT/'scripts/build_scene.py')]
    elif args.command=='verify':cmd+=[str(scene),'--python',str(ROOT/'scripts/verify_scene.py')]
    elif args.command=='video':
        cmd+=[str(scene),'--python',str(ROOT/'scripts/render_walkthrough.py'),'--',
              '--width',str(args.width),'--samples',str(args.samples),'--start',str(args.start),'--end',str(args.end)]
        if args.preview:cmd+=['--preview']
        if args.prepared:cmd+=['--prepared']
    else:cmd+=[str(scene),'--python',str(ROOT/'scripts/render_scene.py'),'--','--views',args.views,'--width',str(args.width),'--samples',str(args.samples)]
    return subprocess.call(cmd)


if __name__=='__main__':sys.exit(main())
