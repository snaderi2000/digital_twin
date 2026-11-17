"""Create a one-minute cut from the original, untitled Blender render frames.

Motion interpolation runs separately for each shot, never across an edit.
The original 24-second video and Blender animation are preserved.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'video/extended-cache'
OUTPUT = ROOT / 'video/si_o_se_pol_flythrough_60s.mp4'


def main():
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise SystemExit('FFmpeg and ffprobe are required.')
    source = json.loads((ROOT / 'video/manifest.json').read_text())
    fps = source['fps']
    target_count = 60 * fps
    CACHE.mkdir(exist_ok=True)
    signature = hashlib.sha256(Path(__file__).read_bytes() +
                               json.dumps(source, sort_keys=True).encode()).hexdigest()
    stamp = CACHE / 'signature.txt'
    if stamp.exists() and stamp.read_text() != signature:
        raise SystemExit('Extended-cut settings changed. Move video/extended-cache before rebuilding.')
    stamp.write_text(signature)

    def probe(path, count=None):
        info = json.loads(subprocess.check_output(
            [ffprobe, '-v', 'error', '-select_streams', 'v:0', '-show_streams', '-of', 'json', str(path)],
            text=True))['streams'][0]
        if ((count is not None and int(info['nb_frames']) != count) or info['width'] != source['width'] or
                info['height'] != source['height'] or info['avg_frame_rate'] != f'{fps}/1'):
            raise RuntimeError(f'Unexpected segment timing or dimensions: {path}')
        return int(info['nb_frames'])

    def finish_segment(temporary, destination, count):
        actual = probe(temporary)
        if not 0 <= count - actual <= 6:
            raise RuntimeError(f'Unexpected interpolation frame loss: {temporary}: {actual}/{count}')
        if actual < count:
            # Minterpolate drops its final lookahead frames. Hold the already
            # eased endpoint briefly so every chapter has its exact duration.
            padded = temporary.with_suffix('.padded.mp4')
            subprocess.run([ffmpeg, '-y', '-nostdin', '-v', 'error', '-xerror', '-i', str(temporary),
                            '-vf', 'tpad=stop_mode=clone:stop_duration=0.5', '-frames:v', str(count),
                            '-c:v', 'libx264', '-crf', '0', '-preset', 'fast', '-threads', '2',
                            '-pix_fmt', 'yuv420p', '-an', str(padded)], check=True)
            probe(padded, count)
            padded.replace(temporary)
        probe(temporary, count)
        temporary.replace(destination)

    shots = []
    for index, shot in enumerate(source['shots']):
        first = round((shot['first'] - 1) * target_count / source['frames']) + 1
        last = round(shot['last'] * target_count / source['frames'])
        shots.append(dict(shot=shot['shot'], first=first, last=last,
                          source_first=shot['first'], source_last=shot['last']))

    def process(item):
        index, shot = item
        count = shot['last'] - shot['first'] + 1
        original_count = shot['source_last'] - shot['source_first'] + 1
        for number in range(shot['source_first'], shot['source_last'] + 1):
            path = ROOT / 'video/frames' / f'{number:04}.png'
            with path.open('rb') as handle:
                handle.seek(-12, 2)
                if b'IEND' not in handle.read():
                    raise RuntimeError(f'Incomplete source frame: {path}')
        destination = CACHE / f'shot-{index:02}.mp4'
        if destination.exists():
            probe(destination, count)
            print(f'Reusing {shot["shot"]}', flush=True)
            return destination
        temporary = destination.with_suffix('.encoding.mp4')
        if temporary.exists():
            try:
                actual = probe(temporary)
            except (subprocess.CalledProcessError, ValueError, KeyError, RuntimeError):
                actual = -1
            if 0 <= count - actual <= 6:
                finish_segment(temporary, destination, count)
                print(f'Finished {shot["shot"]}', flush=True)
                return destination
        # One second of endpoint padding provides the interpolator with future
        # reference frames; -frames:v trims the output to exact chapter length.
        filters = (f'trim=end_frame={original_count},setpts={(count-1)/(original_count-1)}*(PTS-STARTPTS),'
                   'format=yuv420p,tpad=stop_mode=clone:stop_duration=1,'
                   f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bilat:vsbmc=1')
        print(f'Processing {shot["shot"]}: {count/fps:g} seconds', flush=True)
        with (CACHE / f'shot-{index:02}.log').open('w') as log:
            subprocess.run([ffmpeg, '-y', '-nostdin', '-xerror', '-hide_banner', '-loglevel', 'warning',
                            '-framerate', str(fps), '-start_number', str(shot['source_first']),
                            '-i', str(ROOT / 'video/frames/%04d.png'), '-vf', filters,
                            '-frames:v', str(count), '-c:v', 'libx264', '-crf', '0', '-preset', 'fast',
                            '-threads', '2', '-pix_fmt', 'yuv420p', '-an', str(temporary)],
                           stdout=log, stderr=log, check=True)
        finish_segment(temporary, destination, count)
        print(f'Finished {shot["shot"]}', flush=True)
        return destination

    with ThreadPoolExecutor(max_workers=3) as pool:
        segments = list(pool.map(process, enumerate(shots)))
    concat = CACHE / 'shots.ffconcat'
    concat.write_text('ffconcat version 1.0\n' + ''.join(f"file '{path.name}'\n" for path in segments))
    assembled = CACHE / 'assembled.mp4'
    subprocess.run([ffmpeg, '-y', '-nostdin', '-v', 'error', '-f', 'concat', '-safe', '0',
                    '-i', str(concat), '-c', 'copy', str(assembled)], check=True)
    probe(assembled, target_count)
    manifest = dict(fps=fps, frames=target_count, duration_seconds=60,
                    width=source['width'], height=source['height'], shots=shots,
                    method='Per-shot motion-compensated retiming of original Blender PNG frames',
                    source_manifest='video/manifest.json', source_render_signature=source['render_signature'])
    manifest_path = ROOT / 'video/manifest_60s.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run([sys.executable, str(ROOT / 'scripts/encode_video.py'),
                    '--manifest', str(manifest_path), '--input-video', str(assembled),
                    '--output', str(OUTPUT)], check=True)
    # Decode every frame to catch file corruption after final encoding.
    subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-i', str(OUTPUT),
                    '-f', 'null', '-'], check=True)
    print(f'Finished and verified: {OUTPUT}', flush=True)


if __name__ == '__main__':
    main()
