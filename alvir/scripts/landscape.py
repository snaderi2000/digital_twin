"""Create explicitly inferred field subdivisions and vegetation within observed envelopes."""
import json
import math
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import Polygon, LineString, Point, box
from shapely.affinity import rotate
from shapely.ops import unary_union, nearest_points

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/scene.json').read_text())
R=random.Random(4738287)
xmin,ymin,xmax,ymax=D['terrain']['bounds']
SIZE=4096


def px(p):return ((p[0]-xmin)/(xmax-xmin)*(SIZE-1),(ymax-p[1])/(ymax-ymin)*(SIZE-1))


def main():
    image=Image.new('RGB',(SIZE,SIZE),(154,137,104));draw=ImageDraw.Draw(image)
    building_polys=[Polygon(b['polygon']) for b in D['buildings']]
    structures=unary_union(building_polys).buffer(3)
    road_area=unary_union([LineString(r['points']).buffer(r['width_m']/2+1.5) for r in D['roads']])
    exclusion=unary_union([structures,road_area])
    parcels=[];trees=[];walls=[]
    for envelope in D['fields']:
        area=Polygon(envelope['polygon']).difference(exclusion)
        bx,by,tx,ty=area.bounds
        angle=R.uniform(-32,32)
        center=area.centroid.coords[0]
        y=by-150
        while y<ty+150:
            h=R.uniform(45,100);x=bx-150
            while x<tx+150:
                w=R.uniform(32,85)
                cell=rotate(box(x,y,x+w,y+h),angle,origin=center).intersection(area)
                for poly in ([cell] if cell.geom_type=='Polygon' else getattr(cell,'geoms',[])):
                    if poly.geom_type!='Polygon' or poly.area<150:continue
                    inner=poly.buffer(-1.3)
                    if inner.geom_type!='Polygon' or inner.is_empty:continue
                    orchard=envelope['orchard'] and R.random()<.72
                    palette=[(104,116,65),(118,126,74),(143,141,94),(156,144,100),(124,136,80),(167,151,108)]
                    color=R.choice(palette) if not orchard else R.choice([(115,111,71),(128,121,79),(137,130,85)])
                    points=list(inner.exterior.coords)
                    draw.polygon([px(p) for p in points],fill=color)
                    parcels.append(dict(polygon=points,orchard=orchard,evidence='inferred_subdivision',angle=angle))
                    # Very thin tilled rows are generated from geometry, not image pixels.
                    rowmask=Image.new('L',(SIZE,SIZE));md=ImageDraw.Draw(rowmask)
                    md.polygon([px(p) for p in points],fill=255)
                    stripes=Image.new('RGB',(SIZE,SIZE),color);sd=ImageDraw.Draw(stripes)
                    left,top,right,bottom=rowmask.getbbox()
                    for yy in range(top,bottom,5 if orchard else 3):
                        sd.line([(left,yy),(right,yy+int((right-left)*.15))],fill=tuple(int(c*.90) for c in color),width=1)
                    image.paste(stripes,(0,0),rowmask)
                    draw=ImageDraw.Draw(image)
                    if orchard:
                        ax,ay,cx,cy=inner.bounds
                        for xx in np.arange(ax+4,cx,11):
                            for yy in np.arange(ay+4,cy,11):
                                p=Point(xx+R.uniform(-1,1),yy+R.uniform(-1,1))
                                if inner.contains(p) and R.random()<.80:
                                    trees.append([p.x,p.y,R.uniform(4.5,7.7),R.randrange(8),R.uniform(0,math.tau)])
                    if orchard and R.random()<.35:
                        walls.append(points)
                x+=w
            y+=h
    for residential in D['residential']:
        draw.polygon([px(p) for p in residential],fill=(155,145,122))
    for road in D['roads']:
        width=max(2,round(road['width_m']/(xmax-xmin)*SIZE))
        color=(139,132,116) if road['kind'] in ('residential','tertiary','unclassified') else (164,147,113)
        draw.line([px(p) for p in road['points']],fill=color,width=width,joint='curve')
    # Break up flat colors without changing the geographic feature placement.
    arr=np.asarray(image).astype(np.float32)
    noise=np.random.default_rng(4738287).normal(0,1.5,(SIZE,SIZE,1))
    Image.fromarray(np.clip(arr+noise,0,255).astype('uint8')).save(ROOT/'data/ground_palette.png')
    courtyards=[]
    for building,poly in zip(D['buildings'],building_polys):
        if poly.area<40 or poly.area>900:continue
        enclosure=poly.buffer(R.uniform(3,6),join_style=2)
        p,q=nearest_points(poly,road_area)
        access=LineString([p,q]).buffer(2)
        boundary=enclosure.boundary.difference(exclusion).difference(access)
        lines=[boundary] if boundary.geom_type=='LineString' else getattr(boundary,'geoms',[])
        for line in lines:
            if line.geom_type=='LineString' and line.length>2:courtyards.append(list(line.coords))
        garden=enclosure.difference(exclusion)
        if garden.area>20 and R.random()<.48:
            p=garden.representative_point()
            trees.append([p.x,p.y,R.uniform(4,7),R.randrange(8),R.uniform(0,math.tau)])
    result=dict(parcels=parcels,trees=trees,walls=walls,courtyards=courtyards,
                evidence='Envelope placement interpreted from imagery; all individual parcels, trees and garden walls inferred.')
    (ROOT/'data/landscape.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(parcels=len(parcels),trees=len(trees),garden_wall_loops=len(walls))))


if __name__=='__main__':main()
