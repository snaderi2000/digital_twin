"""Split the 2160-frame Cycles job across selected visible Blender CUDA devices."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',default=shutil.which('blender'))
    p.add_argument('--gpus',default='0',help='Comma-separated indices from remote_render.py AVAILABLE_GPUS output.')
    p.add_argument('--samples',type=int,default=32)
    p.add_argument('--threads',type=int,default=4)
    args=p.parse_args()
    if not args.blender:p.error('Pass --blender /path/to/blender')
    try:gpus=[int(x) for x in args.gpus.split(',')]
    except ValueError:p.error('--gpus must contain integer indices')
    if not gpus or min(gpus)<0 or len(set(gpus))!=len(gpus) or len(gpus)>2160:p.error('Invalid or duplicate GPU indices')
    if args.samples<1 or args.threads<1:p.error('Samples and threads must be positive')
    logs=ROOT/'video/worker-logs';logs.mkdir(parents=True,exist_ok=True)
    workers=[]
    try:
        for i,gpu in enumerate(gpus):
            first=2160*i//len(gpus)+1;last=2160*(i+1)//len(gpus)
            command=[args.blender,'-b','-t',str(args.threads),'--python-exit-code','1',
                     str(ROOT/'output/alvir_walkthrough.blend'),'--python',str(ROOT/'scripts/remote_render.py'),'--',
                     '--backend','CUDA','--gpu-index',str(gpu),'--samples',str(args.samples),
                     '--start',str(first),'--end',str(last)]
            log=(logs/f'gpu-{gpu}-{first:04}-{last:04}.log').open('w')
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            workers.append((gpu,process,log))
            print(f'GPU index {gpu}: frames {first}–{last}; PID {process.pid}',flush=True)
        failed=[]
        for gpu,process,log in workers:
            code=process.wait();log.close()
            if code:failed.append((gpu,code))
        if failed:raise RuntimeError(f'Workers failed: {failed}. Inspect video/worker-logs; complete frames remain resumable.')
        print('All selected frame ranges finished. Encode video/frames-cycles with encode_walkthrough.py.')
    except KeyboardInterrupt:
        for gpu,process,log in workers:
            if process.poll() is None:process.terminate()
        for gpu,process,log in workers:process.wait();log.close()
        return 130
    return 0


if __name__=='__main__':sys.exit(main())
