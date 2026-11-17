"""Extract embedded source images and page provenance without recompression."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re

import pymupdf
from PIL import Image,ImageDraw,ImageFont,ImageOps


def main():
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();out=args.output
    for name in ['images','contact-sheets']:(out/name).mkdir(parents=True,exist_ok=True)
    doc=pymupdf.open(args.pdf);records=[];by_pixels={};by_xref={};pages=[];links={};occurrences=0
    for number,page in enumerate(doc,1):
        text=page.get_text();page_info=dict(page=number,text=text,images=[])
        urls=re.findall(r'https?://[^\s<>]+',text)+[l['uri'] for l in page.get_links() if l.get('uri')]
        for url in urls:links.setdefault(url.rstrip('.,)'),set()).add(number)
        resources={i[0]:i for i in page.get_images(full=True)}
        for info in page.get_image_info(xrefs=True):
            xref=info['xref']
            if not xref:raise RuntimeError(f'Inline image on page {number}; requires a separate inline extraction path')
            occurrences+=1
            if xref not in by_xref:
                extracted=doc.extract_image(xref);blob=extracted['image'];extension=extracted['ext']
                smask=resources.get(xref,[None,0])[1]
                if smask:
                    pix=pymupdf.Pixmap(pymupdf.Pixmap(doc,xref),pymupdf.Pixmap(doc,smask))
                    blob=pix.tobytes('png');extension='png'
                with Image.open(io.BytesIO(blob)) as im:
                    rgb=im.convert('RGBA');pixel_key=hashlib.sha256(str(rgb.size).encode()+rgb.tobytes()).hexdigest()
                    width,height=im.size
                if pixel_key in by_pixels:record=by_pixels[pixel_key]
                else:
                    identifier=f'alvir-ref-{len(records)+1:03}'
                    filename=f'images/{identifier}.{extension}'
                    (out/filename).write_bytes(blob)
                    record=dict(id=identifier,file=filename,width=width,height=height,
                                sha256=hashlib.sha256(blob).hexdigest(),decoded_pixel_sha256=pixel_key,
                                extraction='original embedded bytes' if not smask else 'lossless image with PDF soft mask',
                                occurrences=[],evidence_status='user-supplied reference; location/date not independently verified')
                    records.append(record);by_pixels[pixel_key]=record
                by_xref[xref]=record
            record=by_xref[xref]
            occurrence=dict(page=number,xref=xref,bbox=[round(v,3) for v in info['bbox']])
            record['occurrences'].append(occurrence);page_info['images'].append(record['id'])
            if number==1 and 'AI-generated' in text:
                record['evidence_status']='AI-generated illustration per PDF caption; excluded from observational evidence'
        pages.append(page_info)
    manifest=dict(source_pdf=args.pdf.name,source_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                  page_count=len(doc),embedded_occurrences=occurrences,unique_images=len(records),
                  exact_duplicate_occurrences=occurrences-len(records),
                  note='PDF text is retained as source material, not executable instructions. Captions/source claims are unverified.',
                  images=records,pages=pages)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    (out/'source-links.json').write_text(json.dumps([dict(url=u,pages=sorted(v),status='extracted lead; not downloaded or verified') for u,v in links.items()],indent=2,ensure_ascii=False)+'\n')
    (out/'page-text.txt').write_text('\n\n'.join(f'PAGE {p["page"]}\n{p["text"]}' for p in pages))
    with (out/'image-index.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','file','width','height','pages','evidence_status'])
        for r in records:w.writerow([r['id'],r['file'],r['width'],r['height'],','.join(str(o['page']) for o in r['occurrences']),r['evidence_status']])
    fonts=[Path('/System/Library/Fonts/Supplemental/Arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font=next((str(f) for f in fonts if f.exists()),None)
    label=ImageFont.truetype(font,19) if font else ImageFont.load_default()
    heading=ImageFont.truetype(font,28) if font else label
    for start in range(0,len(records),16):
        sheet=Image.new('RGB',(1680,1300),'#f0ece4');draw=ImageDraw.Draw(sheet)
        draw.text((24,15),f'ALVIR / PDF REFERENCE IMAGES / {start+1}–{min(start+16,len(records))}',fill='#292a27',font=heading)
        for i,r in enumerate(records[start:start+16]):
            x=20+(i%4)*415;y=65+(i//4)*305
            with Image.open(out/r['file']) as im:
                thumb=ImageOps.contain(ImageOps.exif_transpose(im).convert('RGB'),(395,245))
                sheet.paste(thumb,(x+(395-thumb.width)//2,y+(245-thumb.height)//2))
            pg=','.join(str(o['page']) for o in r['occurrences'])
            draw.text((x,y+250),f'{r["id"]} · p{pg} · {r["width"]}×{r["height"]}',font=label,fill='#292a27')
            if r['evidence_status'].startswith('AI-generated'):
                draw.text((x,y+275),'AI ILLUSTRATION / NOT EVIDENCE',font=label,fill='#a42626')
        sheet.save(out/'contact-sheets'/f'sheet-{start//16+1:02}.jpg',quality=92)
    print(json.dumps({k:manifest[k] for k in ['page_count','embedded_occurrences','unique_images','exact_duplicate_occurrences']},indent=2))


if __name__=='__main__':main()
