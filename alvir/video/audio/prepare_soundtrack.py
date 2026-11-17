"""Create a faded background-music excerpt from the credited CC BY setar recording."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--duration', type=float, default=90)
p.add_argument('--start', type=float, default=32.9)
args = p.parse_args()
if args.duration <= 0 or args.start < 0:
    p.error('duration must be positive and start must be non-negative')
exe = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
source = ROOT / 'setar_alireza_farrokhzadi.mp3'
out = ROOT / 'alvir_setar_soundtrack.wav'
fade_out = max(0, args.duration - 3)
filters = (f'loudnorm=I=-20:TP=-2:LRA=9,afade=t=in:st=0:d=1.5,'
           f'afade=t=out:st={fade_out}:d=3')
subprocess.run([exe, '-hide_banner', '-y', '-ss', str(args.start), '-i', str(source),
                '-t', str(args.duration), '-vn', '-af', filters, '-ar', '48000',
                '-ac', '2', '-c:a', 'pcm_s16le', str(out)], check=True)
metadata = {
    'title': 'Setar,Alireza Farrokhzadi.mp3',
    'performer': 'Alireza Farrokhzadi',
    'publisher': 'sonsbcnintercultural',
    'source_url': 'https://freesound.org/people/sonsbcnintercultural/sounds/256120/',
    'download_url': 'https://cdn.freesound.org/previews/256/256120_4735604-hq.mp3',
    'license': 'Creative Commons Attribution 3.0 Unported (CC BY 3.0)',
    'license_url': 'https://creativecommons.org/licenses/by/3.0/',
    'source_date': '2014-11-29',
    'performance_date_as_stated_by_uploader': '2014-11-25',
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'excerpt_start_seconds': args.start,
    'excerpt_duration_seconds': args.duration,
    'changes': 'Excerpted, loudness normalized to -20 LUFS target, faded in/out, and resampled to 48 kHz stereo PCM.',
    'output': out.name,
    'output_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'credit': 'Music: Setar,Alireza Farrokhzadi.mp3 — Alireza Farrokhzadi / sonsbcnintercultural, Freesound 256120, CC BY 3.0. Excerpted, normalized and faded.',
    'rights_note': 'Retain creator, title, source and license credit with redistributed videos; no endorsement is implied.'
}
(ROOT / 'soundtrack.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+'\n')
print(json.dumps(metadata, indent=2, ensure_ascii=False))
