"""Validate native frames and encode the titled 4K walkthrough with licensed setar."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/'video'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--frames',type=Path,default=VIDEO/'frames')
    parser.add_argument('--output',type=Path,default=VIDEO/'alvir_walkthrough_90s_4k.mp4')
    args=parser.parse_args()
    ffmpeg,ffprobe=shutil.which('ffmpeg'),shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise SystemExit('FFmpeg and ffprobe are required.')
    m=json.loads((VIDEO/'walkthrough-manifest.json').read_text())
    profile_file=args.frames/'profile.json'
    if profile_file.exists():
        profile=json.loads(profile_file.read_text())
        assert profile['animation_sha256']==m['animation_sha256'],'Frames use another animation'
        assert (profile['width'],profile['height'])==(m['width'],m['height'])
        m['engine']=profile['engine'];m['samples']=profile['samples']
    music=json.loads((VIDEO/'audio/soundtrack.json').read_text())
    audio=VIDEO/'audio'/music['output']
    assert hashlib.sha256(audio.read_bytes()).hexdigest()==music['output_sha256']
    from PIL import Image
    for frame in range(1,m['frames']+1):
        path=args.frames/f'{frame:04}.jpg'
        with Image.open(path) as im:
            assert im.size==(m['width'],m['height']),str(path)
            im.verify()
        with path.open('rb') as f:
            f.seek(-2,2);assert f.read()==b'\xff\xd9',str(path)
    font=next((p for p in [Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
              Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.exists()),None)
    if font is None:raise SystemExit('Install Arial or DejaVu Sans for titles.')
    def escape(value):return str(value).replace('\\','/').replace(':',r'\:').replace("'",r"\'")
    font=escape(font);scale=m['width']/1920
    def text_file(name,text):
        path=VIDEO/(name+'.txt');path.write_text(text+'\n');return escape(path)
    def title(name,text,size,y,start,end):
        path=text_file(name,text)
        return (f"drawtext=fontfile='{font}':textfile='{path}':fontsize={round(size*scale)}:"
                f"fontcolor=white:x={round(64*scale)}:y=h-{round(y*scale)}:line_spacing={round(8*scale)}:"
                f"shadowcolor=black@0.8:shadowx=2:shadowy=2:enable='between(t,{start},{end})'")
    filters=[title('title','ALVIR',54,170,.7,7.5),
             title('subtitle','A WALK THROUGH THE VILLAGE  /  IRAN',21,120,.7,7.5),
             title('evidence','Digital reconstruction · building heights and façades estimated',15,38,0,90)]
    for i,shot in enumerate(m['shots'][1:-1],1):
        start=(shot['first']-1)/m['fps']
        filters.append(title(f'chapter-{i}',shot['name'].upper(),24,94,start+.5,start+4.5))
    music_credit=('Setar improvisation — Alireza Farrokhzadi / sonsbcnintercultural\n'
                  'freesound.org/s/256120/ · CC BY 3.0 · creativecommons.org/licenses/by/3.0/\n'
                  'Music excerpted, normalized and faded')
    data_credit=('Microsoft building footprints · © OpenStreetMap contributors · Mapzen / USGS terrain\n'
                 'Sentinel-2 cloudless — s2maps.eu by EOX IT Services GmbH · CC BY 4.0\n'
                 'Contains modified Copernicus Sentinel data 2016 & 2017')
    filters+=["drawbox=x=0:y=ih*0.61:w=iw:h=ih*0.39:color=black@0.45:t=fill:enable='gte(t,78)'",
              title('music-credit',music_credit,17,300,78,90),
              title('data-credit',data_credit,15,178,78,90),
              'fade=t=in:st=0:d=0.8','fade=t=out:st=88.8:d=1.2',
              'scale=out_color_matrix=bt709:out_range=tv','format=yuv420p']
    metadata=[';FFMETADATA1','title=Alvir | A walk through the village',
              'comment=Native 4K Blender reconstruction. Building heights, facades and planting estimated.',
              'artist=Digital Twin project',
              'copyright=Music: Alireza Farrokhzadi / sonsbcnintercultural, Freesound 256120, CC BY 3.0. See credits.txt.']
    for shot in m['shots']:
        metadata+=['[CHAPTER]','TIMEBASE=1/1000',f'START={round((shot["first"]-1)/m["fps"]*1000)}',
                   f'END={round(shot["last"]/m["fps"]*1000)}',f'title={shot["name"]}']
    meta=VIDEO/'chapters.ffmetadata';meta.write_text('\n'.join(metadata)+'\n')
    credits=music_credit+'\nSource: '+music['source_url']+'\nLicense: '+music['license_url']+'\n\n'+data_credit
    credits+='\n\nSee ../README.md for complete model sources, modifications, and evidence limitations.\n'
    (VIDEO/'credits.txt').write_text(credits)
    out=args.output.resolve();temp=out.with_name(out.stem+'.encoding.mp4')
    cmd=[ffmpeg,'-y','-nostdin','-hide_banner','-loglevel','warning','-xerror',
         '-framerate',str(m['fps']),'-start_number','1','-i',str(args.frames/'%04d.jpg'),
         '-i',str(audio),'-i',str(meta),'-map','0:v:0','-map','1:a:0','-map_metadata','2','-map_chapters','2',
         '-vf',','.join(filters),'-frames:v',str(m['frames']),'-t','90',
         '-c:v','libx264','-preset','medium','-crf','18','-threads','8','-pix_fmt','yuv420p',
         '-r',str(m['fps']),'-g',str(m['fps']*2),'-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
         '-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(temp)]
    subprocess.run(cmd,check=True)
    info=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_format','-show_streams','-show_chapters','-of','json',str(temp)],text=True))
    v=next(s for s in info['streams'] if s['codec_type']=='video')
    a=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'])==(m['width'],m['height']) and int(v['nb_frames'])==m['frames']
    assert v['codec_name']=='h264' and a['codec_name']=='aac' and a['channels']==2
    assert abs(float(info['format']['duration'])-90)<.1
    assert abs(float(a['duration'])-90)<.1
    assert len(info['chapters'])==len(m['shots'])
    # Decode the entire deliverable once to catch damaged/truncated packets.
    subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(temp),'-map','0:v:0','-map','0:a:0','-f','null','-'],check=True)
    temp.replace(out)
    report=dict(result='passed',file=out.name,width=v['width'],height=v['height'],
                frames=int(v['nb_frames']),fps=v['avg_frame_rate'],duration_seconds=90,
                video_codec=v['codec_name'],audio_codec=a['codec_name'],audio_channels=a['channels'],
                full_decode=True,native_resolution=True,engine=m['engine'],samples=m['samples'],size_bytes=out.stat().st_size,
                sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    (VIDEO/'video-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
