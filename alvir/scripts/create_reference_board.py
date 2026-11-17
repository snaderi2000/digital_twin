"""Build a portable, vector-layout reference board from the extracted PDF images."""
import json
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references/user-pdf'


def main():
    manifest=json.loads((REF/'manifest.json').read_text())
    images={int(i['id'][-3:]):i for i in manifest['images']}
    doc=pymupdf.open();page=doc.new_page(width=1191,height=842)
    page.draw_rect(page.rect,color=None,fill=(.95,.935,.90))
    page.insert_text((25,33),'ALVIR / PHOTOGRAPHIC MATERIAL REFERENCES',fontsize=23,color=(.16,.17,.14))
    page.insert_text((25,52),'A material study from the supplied PDF. Image locations and capture dates are not established.',fontsize=11)
    selected=[(67,'Earthen walls / faded green gates'),(68,'Old and new construction together'),
              (69,'Weathered timber / eroded clay'),(73,'Leafy shade / brick and adobe'),
              (74,'Timber roof ends / cracked render'),(75,'Gate, tree and repaired wall'),
              (47,'Paved streets also belong here'),(65,'Mature canopy / dry ground')]
    for i,(key,label) in enumerate(selected):
        x=25+(i%4)*290;y=73+(i//4)*352
        r=images[key];page.insert_image(pymupdf.Rect(x,y,x+274,y+292),filename=str(REF/r['file']),keep_proportion=True)
        fit=page.insert_textbox(pymupdf.Rect(x,y+296,x+275,y+345),f'{r["id"]} | PDF p{r["occurrences"][0]["page"]}\n{label}',fontsize=11)
        assert fit>=0,'Reference-board label does not fit'
    page.insert_text((25,814),'Use these for material character; none is registered to a particular modeled building. The AI cover is excluded.',fontsize=10)
    page=doc.new_page(width=1191,height=842);page.draw_rect(page.rect,color=None,fill=(.95,.935,.90))
    page.insert_text((25,35),'ALVIR / WHAT THE MODEL SHOULD TAKE FROM THESE PHOTOS',fontsize=22)
    palette=[('Sandy clay',(.34,.235,.145)),('Warm plaster',(.52,.455,.35)),('Faded green paint',(.18,.255,.185)),
             ('Weathered timber',(.18,.135,.085)),('Leafy shade',(.067,.133,.033)),('Worn asphalt',(.20,.205,.19))]
    def srgb(v):return 12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
    for i,(label,rgb) in enumerate(palette):
        x=25+i*192;page.draw_rect(pymupdf.Rect(x,62,x+174,122),color=None,fill=tuple(srgb(c) for c in rgb))
        page.insert_text((x,142),label,fontsize=12)
    page.insert_text((25,165),'Artist-selected shader palette, not calibrated color measurements.',fontsize=10)
    for i,(key,label) in enumerate([(63,'Dry hill and scattered vegetation'),(23,'Green cereal fields: another seasonal appearance'),(48,'Contemporary asphalt and mixed buildings')]):
        x=25+i*385;r=images[key]
        page.insert_image(pymupdf.Rect(x,191,x+365,441),filename=str(REF/r['file']),keep_proportion=True)
        page.insert_textbox(pymupdf.Rect(x,449,x+365,480),f'alvir-ref-{key:03} | {label}',fontsize=11)
    left=('APPLIED IN THE MATERIAL STUDY\n\n'
          'Warm, mottled earthen render with fine procedural fissures.\n'
          'Subdued sage-green paint, weathered wood and darker ironwork.\n'
          'Less saturated metal roofs and deeper foliage tones.\n'
          'Pale modern plaster and brick retained alongside older materials.\n\n'
          'Geometry, footprint positions, cameras, road types and material assignments are preserved. '
          'Photographs are not projected onto arbitrary buildings.')
    right=('EVIDENCE LIMITS / NEXT GEOMETRY PASS\n\n'
           '001: AI cover; excluded from evidence.\n'
           '002: regional aerial caption; not a verified Alvir layout.\n'
           '003: embedded photo differs from the page 5 description.\n'
           '040: intact tower caption is not geolocated.\n\n'
           'Match specific houses, mosque, trees and lanes to the map before changing their geometry. '
           'Do not combine all seasons into one uniformly green landscape. '
           'Dates sent are not capture dates. The 100 Instagram URLs are leads, not downloaded images.')
    page.insert_textbox(pymupdf.Rect(25,510,570,790),left,fontsize=15,lineheight=1.3)
    page.insert_textbox(pymupdf.Rect(615,510,1165,800),right,fontsize=14,lineheight=1.25)
    out=REF/'alvir-theme-board.pdf';doc.save(out,garbage=4,deflate=True)
    # A single PDF contact catalogue is convenient for reviewing all 75 originals.
    contact=pymupdf.open()
    for image in sorted((REF/'contact-sheets').glob('*.jpg')):
        p=contact.new_page(width=840,height=650);p.insert_image(p.rect,filename=str(image))
    contact.save(REF/'all-images-contact-sheet.pdf',garbage=4,deflate=True)
    print('Wrote theme board and five-page contact catalogue.')


if __name__=='__main__':main()
