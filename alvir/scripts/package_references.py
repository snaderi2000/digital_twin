"""Create reproducible reference and server bundles from a Git LFS checkout."""
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def digest(data):return hashlib.sha256(data).hexdigest()


def archive(path,members):
    with zipfile.ZipFile(path,'w') as z:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name);info.external_attr=0o100644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=5)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,data in members.items():assert digest(z.read(name))==digest(data)


def main():
    refs=ROOT/'references/user-pdf';m=json.loads((refs/'manifest.json').read_text())
    assert digest((refs/'source.pdf').read_bytes())==m['source_sha256']
    for item in m['images']:
        p=refs/item['file'];assert digest(p.read_bytes())==item['sha256']
        with Image.open(p) as im:
            assert im.size==(item['width'],item['height']);im.verify()
    reference_files={str(p.relative_to(refs)):p.read_bytes() for p in refs.rglob('*') if p.is_file() and not p.name.startswith('.')}
    photos=ROOT/'output/alvir_reference_images.zip'
    archive(photos,{'alvir-reference-images/'+name:data for name,data in reference_files.items()})
    include=['output/alvir_walkthrough.blend','output/visual-theme-check.json',
             'data/scene.json','data/terrain.npy','data/CDLA-Permissive-2.0.txt','data/MICROSOFT-DATA-LICENSE.txt',
             'data/source-manifest.json','data/sentinel_context.json','data/visual-theme.json',
             'README.md','reference-requirements.txt','video/walkthrough-manifest.json','video/walk-routes.json','video/credits.txt',
             'scripts/remote_render.py','scripts/run_remote_workers.py','scripts/render_walkthrough.py',
             'scripts/encode_walkthrough.py','scripts/visual_theme.py','scripts/extract_reference_pdf.py','scripts/create_reference_board.py',
             'renders/theme-street.png','renders/theme-garden.png']
    bundle={'alvir/'+name:(ROOT/name).read_bytes() for name in include}
    for p in (ROOT/'video/audio').iterdir():
        if p.is_file() and p.suffix in ['.wav','.mp3','.json','.txt','.py']:
            bundle['alvir/'+str(p.relative_to(ROOT))]=p.read_bytes()
    for name,data in reference_files.items():bundle['alvir/references/user-pdf/'+name]=data
    bundle['V100_HANDOFF.txt']=(ROOT/'video/V100_HANDOFF.txt').read_bytes()
    manifest=json.loads(bundle['alvir/video/walkthrough-manifest.json'])
    assert digest(bundle['alvir/output/alvir_walkthrough.blend'])==manifest['animation_sha256']
    checks={name:dict(bytes=len(data),sha256=digest(data)) for name,data in bundle.items()}
    bundle['BUNDLE_MANIFEST.json']=(json.dumps(checks,indent=2)+'\n').encode()
    server=ROOT/'video/alvir_v100_reference_theme_bundle.zip';archive(server,bundle)
    report=dict(result='passed',unique_images=len(m['images']),embedded_occurrences=m['embedded_occurrences'],
                source_pdf_hash_verified=True,original_image_hashes_verified=True,themed_server_scene_matches_manifest=True,
                artifacts=[dict(file=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in [photos,server]])
    (ROOT/'output/reference-library-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
