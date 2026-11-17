#!/usr/bin/env python3
"""Portable project commands; only the Python standard library is required."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def blender():
    candidates=[os.environ.get('BLENDER'),shutil.which('blender'),
                ROOT/'.tools/Blender.app/Contents/MacOS/Blender',
                '/Applications/Blender.app/Contents/MacOS/Blender',
                r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe']
    for path in candidates:
        if path and Path(path).is_file(): return str(path)
    raise SystemExit('Blender 4.5 LTS is required. Install it from blender.org, or set BLENDER to its executable path.')

def main():
    p=argparse.ArgumentParser(description='Si-o-se-pol Blender reconstruction')
    p.add_argument('command',choices=['build','render','open','test','sheet','verify','video','encode-video','open-video','extend-video'])
    p.add_argument('--quality',choices=['preview','standard','final'],default='standard')
    p.add_argument('--views',default='hero',help='hero,elevation,detail,deck,gallery,aerial or all')
    p.add_argument('--threads',type=int,default=8)
    p.add_argument('--width',type=int,default=1920,help='Video width in pixels')
    p.add_argument('--samples',type=int,default=16,help='EEVEE samples per video frame')
    args=p.parse_args()
    if args.threads<1: p.error('--threads must be positive')
    if args.command=='test':
        return subprocess.call([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT)
    if args.command=='sheet':
        return subprocess.call([sys.executable,'scripts/draw_sheet.py'],cwd=ROOT)
    if args.command=='encode-video':
        return subprocess.call([sys.executable,'scripts/encode_video.py'],cwd=ROOT)
    if args.command=='extend-video':
        return subprocess.call([sys.executable,'scripts/extend_video.py'],cwd=ROOT)
    exe=blender(); scene=ROOT/'output'/('si_o_se_pol_flythrough.blend' if args.command=='open-video' else 'si_o_se_pol.blend')
    if args.command in ('open','open-video'):
        if not scene.exists():
            p.error('Generate the animation first: python3 manage.py video' if args.command=='open-video'
                    else 'Build the scene first: python3 manage.py build')
        subprocess.Popen([exe,str(scene)],cwd=ROOT)
        return 0
    cmd=[exe,'--background','--threads',str(args.threads),'--python-exit-code','1']
    if args.command=='build':
        cmd+=['--python',str(ROOT/'scripts/build_scene.py'),'--','--quality',args.quality]
    elif args.command=='verify':
        if not scene.exists(): p.error('Build the scene first: python3 manage.py build')
        cmd+=[str(scene),'--python',str(ROOT/'scripts/verify_scene.py')]
    elif args.command=='video':
        if not scene.exists(): p.error('Build the scene first: python3 manage.py build')
        cmd+=[str(scene),'--python',str(ROOT/'scripts/render_video.py'),'--',
              '--width',str(args.width),'--samples',str(args.samples)]
    else:
        if not scene.exists(): p.error('Build the scene first: python3 manage.py build')
        cmd+=[str(scene),'--python',str(ROOT/'scripts/render_scene.py'),'--','--quality',args.quality,'--views',args.views]
    return subprocess.call(cmd,cwd=ROOT)

if __name__=='__main__': sys.exit(main())
