"""Generate a dimensioned SVG reference sheet from the model's parameter file."""
import html
import json
from pathlib import Path
from geometry import layout, pointed_arch

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/bridge.json').read_text())
PITCH,CENTERS=layout(C)
PARTS=[]

def text(x,y,value,size=14,color='#33414b',weight=400):
    PARTS.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{html.escape(value)}</text>')

def line(x1,y1,x2,y2,color='#a8b1b2',width=1,dash=''):
    PARTS.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="{width}" fill="none" stroke-dasharray="{dash}"/>')

def rect(x,y,w,h,fill='#e3ceb0',stroke='#856b4b'):
    PARTS.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width=".8"/>')

def arch(cx,baseline,scale,width,spring,rise,base,fill='#faf8f3'):
    points=[(cx-width/2*scale,baseline-base*scale)]
    points += [(cx+x*scale,baseline-(spring+z)*scale) for x,z in pointed_arch(width/2,rise,24)]
    points += [(cx+width/2*scale,baseline-base*scale)]
    data='M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in points)+' Z'
    PARTS.append(f'<path d="{data}" fill="{fill}" stroke="#856b4b" stroke-width=".75"/>')

def dimension(x1,x2,y,label):
    line(x1,y,x2,y,'#577d83')
    for x in (x1,x2): line(x,y-6,x,y+6,'#577d83')
    text((x1+x2)/2-len(label)*3.5,y-10,label,13,'#577d83')

def main():
    PARTS.clear()
    PARTS.append('<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1150" viewBox="0 0 1800 1150">')
    PARTS.append('<rect width="1800" height="1150" fill="#faf8f3"/><g font-family="Helvetica,Arial,sans-serif">')
    text(76,65,'ISFAHAN  /  ARCHITECTURAL RECONSTRUCTION',13,'#8a6745',600)
    text(76,125,'Si-o-se-pol',50,'#243b42',500)
    text(78,159,'The Bridge of Thirty-three Arches · present-day character · flowing river',18)
    text(1525,68,'MODEL STUDY  /  01',14,'#8a6745',600)
    text(1525,94,'LOCAL UNITS: METRES',12)
    line(76,191,1724,191,'#243b42')
    text(76,231,'01  /  RIVER ELEVATION',14,'#243b42',600)
    text(1095,231,'Schematic elevation of the generated geometry; not a measured survey',13)
    scale=1640/C['length']; base=354; origin=900
    rect(origin-C['length']/2*scale,base-C['roof_height']*scale,C['length']*scale,C['roof_height']*scale)
    for x in CENTERS:
        arch(origin+x*scale,base,scale,C['lower_opening'],C['lower_spring'],C['lower_rise'],0)
    for j in range(99):
        if j in (48,49,50): continue
        x=(j-49)*PITCH/3
        arch(origin+x*scale,base,scale,C['upper_opening'],C['upper_spring'],C['upper_rise'],C['deck_height']+.23)
    rect(origin-PITCH/2*scale,base-12.85*scale,PITCH*scale,(12.85-C['deck_height'])*scale)
    arch(origin,base,scale,3.4,9.55,2.75,C['deck_height']+.23)
    line(80,base-C['water_level']*scale,1720,base-C['water_level']*scale,'#77a3a7',1.4)
    line(80,base-C['deck_height']*scale,1720,base-C['deck_height']*scale,'#856b4b',1)
    dimension(80,1720,391,'297.76 m · selected published overall length')
    text(80,424,'33 river openings · repeated nominal clear span 5.60 m · regularized bay layout',14)
    text(80,479,'02  /  DECK PLAN',14,'#243b42',600)
    y=515; h=C['width']*scale
    rect(80,y,1640,h,'#e9e5dc')
    for side in (-1,1):
        yy=y+h/2+side*5.75*scale-1.25*scale
        rect(80,yy,1640,2.5*scale,'#e3ceb0')
        for x in CENTERS:
            line(origin+x*scale,yy,origin+x*scale,yy+2.5*scale,'#ac9473',.6)
    line(80,y+h/2,1720,y+h/2,'#a8b1b2',.7,'7 5')
    text(635,y+h/2+5,'OPEN CENTRAL PEDESTRIAN PROMENADE',13,'#657174')
    text(80,624,'Nominal body width 13.80 m · raised side galleries · central pavilion projects beyond the main facade',14)
    line(76,664,1724,664)
    text(80,707,'03  /  TYPICAL RIVER BAY',14,'#243b42',600)
    ds=29; db=990; dx=300
    rect(dx-PITCH/2*ds,db-6.43*ds,PITCH*ds,6.43*ds)
    arch(dx,db,ds,C['lower_opening'],C['lower_spring'],C['lower_rise'],0)
    line(dx-PITCH/2*ds,db-C['water_level']*ds,dx+PITCH/2*ds,db-C['water_level']*ds,'#77a3a7',2)
    dimension(dx-C['lower_opening']/2*ds,dx+C['lower_opening']/2*ds,1020,'5.60 m')
    text(80,1059,'Two-centre pointed profile; individual spans are idealized.',13)
    text(650,707,'REFERENCE-BASED PARAMETERS',14,'#243b42',600)
    notes=[('33','river spans, consistent across published references'),
           ('297.76 m','selected overall length; sources also report about 295 m'),
           ('13.80 m','nominal body width from the Cardiff reference'),
           ('6.65 m','modeled deck datum; estimated from proportions'),
           ('12.05 m','modeled main roof datum; estimated'),
           ('0.70 m','art-directed water level, not a current observation')]
    for i,(value,note) in enumerate(notes):
        text(650,756+i*44,value,20,'#8a6745',500)
        text(805,756+i*44,note,15)
    line(76,1090,1724,1090,'#243b42')
    text(80,1121,'Generated from config/bridge.json · See docs/accuracy.md for sources, assumptions and survey requirements.',13)
    text(1530,1121,'VISUAL MODEL  /  V1',13,'#8a6745')
    PARTS.append('</g></svg>')
    (ROOT/'docs/model_sheet.svg').write_text('\n'.join(PARTS)+'\n')

if __name__=='__main__': main()
