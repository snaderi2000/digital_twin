"""Encode the rendered camera animation as a broadly compatible H.264 MP4."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--font',type=Path)
    p.add_argument('--manifest',type=Path,default=ROOT/'video/manifest.json')
    p.add_argument('--input-video',type=Path,help='Use an assembled video instead of the original PNG sequence')
    p.add_argument('--output',type=Path,default=ROOT/'video/si_o_se_pol_flythrough.mp4')
    args=p.parse_args()
    ffmpeg,ffprobe=shutil.which('ffmpeg'),shutil.which('ffprobe')
    if not ffmpeg or not ffprobe: p.error('FFmpeg and ffprobe must be installed and on PATH')
    manifest=json.loads(args.manifest.read_text())
    width,height=manifest['width'],manifest['height']
    fps,count=manifest['fps'],manifest['frames']
    for frame in ([] if args.input_video else range(1,count+1)):
        path=ROOT/'video/frames'/f'{frame:04}.png'
        if not path.exists(): p.error(f'Missing frame: {path.name}')
        with path.open('rb') as f:
            header=f.read(24); f.seek(-12,2); ending=f.read()
        if header[:8]!=b'\x89PNG\r\n\x1a\n' or b'IEND' not in ending:
            p.error(f'Incomplete PNG: {path.name}')
        if struct.unpack('>II',header[16:24])!=(width,height):
            p.error(f'Wrong dimensions: {path.name}')
    fonts=[args.font,Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
           Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('C:/Windows/Fonts/arial.ttf')]
    font=next((f for f in fonts if f and f.exists()),None)
    if font is None: p.error('Pass --font with a TrueType font for the video titles')
    # Filter quoting is independent of shell quoting: subprocess always receives an argv list.
    font_path=str(font).replace('\\','/').replace(':','\\:').replace("'",r"\'")
    duration=count/fps
    scale=width/1920
    def caption(label,size,y,first,last):
        return (f"drawtext=fontfile='{font_path}':text='{label}':fontsize={round(size*scale)}:"
                f"fontcolor=white:x={round(64*scale)}:y=h-{round(y*scale)}:"
                f"shadowcolor=black@0.65:shadowx=2:shadowy=2:"
                f"enable='between(t,{first},{last})'")
    filters=[caption('SI-O-SE-POL',48,140,.5,4.2),caption('ISFAHAN  /  AN ARCHITECTURAL JOURNEY',20,96,.5,4.2)]
    for shot in manifest['shots'][1:]:
        start=(shot['first']-1)/fps
        filters.append(caption(shot['shot'].upper(),24,80,start+.35,start+2.8))
    filters += ['fade=t=in:st=0:d=0.6',f'fade=t=out:st={duration-.8}:d=0.8',
                'scale=out_color_matrix=bt709:out_range=tv','format=yuv420p']
    metadata=[';FFMETADATA1','title=Si-o-se-pol | Architectural fly-through',
              'comment=Rendered from a reference-based Blender reconstruction.']
    for shot in manifest['shots']:
        metadata += ['[CHAPTER]','TIMEBASE=1/1000',
                     f'START={round((shot["first"]-1)/fps*1000)}',
                     f'END={round(shot["last"]/fps*1000)}',f'title={shot["shot"]}']
    output=args.output.resolve()
    meta=(output.with_suffix('.chapters.ffmetadata') if args.input_video else ROOT/'video/chapters.ffmetadata')
    meta.write_text('\n'.join(metadata)+'\n')
    temporary=output.with_name(output.stem+'.encoding.mp4')
    source=(['-i',str(args.input_video)] if args.input_video else
            ['-framerate',str(fps),'-start_number','1','-i',str(ROOT/'video/frames/%04d.png')])
    cmd=[ffmpeg,'-y','-nostdin','-xerror','-hide_banner','-loglevel','warning',*source,
         '-i',str(meta),'-map','0:v:0','-map_metadata','1','-map_chapters','1',
         '-vf',','.join(filters),'-frames:v',str(count),'-c:v','libx264','-preset','medium','-crf','18',
         '-threads','8','-pix_fmt','yuv420p','-r',str(fps),'-g',str(fps*2),
         '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
         '-movflags','+faststart','-an',str(temporary)]
    subprocess.run(cmd,check=True)
    info=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(temporary)],text=True))
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    assert video['codec_name']=='h264'
    assert (video['width'],video['height'])==(width,height)
    assert int(video['nb_frames'])==count
    assert abs(float(info['format']['duration'])-duration)<.1
    temporary.replace(output)
    report={'file':str(output.relative_to(ROOT)),'codec':video['codec_name'],'pixel_format':video['pix_fmt'],
            'width':width,'height':height,'fps':fps,'frames':count,'duration_seconds':duration,
            'size_bytes':output.stat().st_size,'validation':'passed'}
    report_path=output.with_suffix('.validation.json') if args.input_video else ROOT/'video/video-check.json'
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
