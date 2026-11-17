"""Draw a shareable, source-labeled vector plan without proprietary imagery."""
import html
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/scene.json').read_text())
x0,y0,x1,y1=D['terrain']['bounds'];scale=1050/(x1-x0)


def pt(p):return (65+(p[0]-x0)*scale,160+(y1-p[1])*scale)


def points(ring):return ' '.join('%.2f,%.2f'%pt(p) for p in ring)


def main():
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1320" viewBox="0 0 1400 1320">',
       '<rect width="1400" height="1320" fill="#f3f0e6"/>',
       '<g font-family="Arial,sans-serif" fill="#243b31">',
       '<text x="65" y="66" font-size="36" font-weight="700">ALVIR / الویر</text>',
       '<text x="65" y="101" font-size="16">Village and agricultural valley · Markazi, Iran</text>',
       '<text x="65" y="128" font-size="13">35.3867° N, 50.0018° E · UTM 39N · Local metres</text>',
       '<rect x="65" y="160" width="1050" height="1046" fill="#ded6bc"/>']
    h=np.load(ROOT/'data/terrain.npy')
    for j in range(0,256,4):
        for i in range(0,256,4):
            z=float(h[j:j+4,i:i+4].mean());v=int(max(170,min(228,219-z*.10)))
            x,y=pt((x0+(x1-x0)*i/256,y0+(y1-y0)*(j+4)/256))
            s.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="16.6" height="16.6" fill="rgb({v},{v-7},{v-28})"/>')
    for field in D['fields']:
        s.append(f'<polygon points="{points(field["polygon"])}" fill="#a5b18a" fill-opacity=".8" stroke="#758862" stroke-width=".7"><title>Interpreted agricultural envelope; not cadastral</title></polygon>')
    for r in D['roads']:
        s.append(f'<polyline points="{points(r["points"])}" fill="none" stroke="#6a665b" stroke-width="{max(.8,r["width_m"]*scale):.2f}"><title>{html.escape(r["id"])}</title></polyline>')
    for b in D['buildings']:
        s.append(f'<polygon points="{points(b["polygon"])}" fill="#ab6843" stroke="#633f29" stroke-width=".25"><title>{b["id"]}: source footprint; height estimated</title></polygon>')
    if 'watercourse' in D:
        s.append(f'<polyline points="{points(D["watercourse"]["points"])}" fill="none" stroke="#4c7c86" stroke-width="1.7" stroke-dasharray="5 3"/>')
    x,y=pt(D['fort_location'])
    s.extend([f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="#643748" stroke-width="2"/>',
              f'<text x="{x-100}" y="{y-12}" font-size="12">Historic fort</text>',
              '<text x="1160" y="198" font-size="16" font-weight="700">EVIDENCE</text>',
              '<rect x="1160" y="223" width="14" height="14" fill="#ab6843"/>',
              '<text x="1184" y="235" font-size="12">474 source footprints</text>',
              '<path d="M1160 266h16" stroke="#6a665b" stroke-width="3"/>',
              '<text x="1184" y="270" font-size="12">48 mapped road ways</text>',
              '<rect x="1160" y="294" width="14" height="14" fill="#a5b18a"/>',
              '<text x="1184" y="306" font-size="12">Interpreted farm areas</text>',
              '<path d="M1160 337h16" stroke="#4c7c86" stroke-width="2" stroke-dasharray="4 2"/>',
              '<text x="1184" y="341" font-size="12">Interpreted channel</text>',
              '<text x="1160" y="393" font-size="12">Building heights, façades,</text>',
              '<text x="1160" y="412" font-size="12">parcel divisions and planting</text>',
              '<text x="1160" y="431" font-size="12">remain estimates.</text>',
              '<path d="M1230 560v-65m0 0l-9 17m9-17l9 17" fill="none" stroke="#243b31" stroke-width="2"/>',
              '<text x="1224" y="482" font-size="17" font-weight="700">N</text>',
              f'<path d="M65 1240h{500*scale:.2f}" stroke="#243b31" stroke-width="5"/>',
              '<text x="65" y="1262" font-size="12">0</text>',
              f'<text x="{65+500*scale:.2f}" y="1262" font-size="12" text-anchor="end">500 m</text>',
              '<text x="350" y="1243" font-size="12">Footprints: Microsoft · Roads: © OpenStreetMap contributors · Terrain: Mapzen / USGS</text>',
              '<text x="350" y="1263" font-size="12">Reference-based reconstruction. Not a survey, cadastral map, or verified current building inventory.</text>',
              '</g></svg>'])
    (ROOT/'output/geographic_plan.svg').write_text('\n'.join(s)+'\n')
    print('Wrote alvir/output/geographic_plan.svg')


if __name__=='__main__':main()
