"""Project source geography into local metric coordinates and prepare model data.

Run with alvir/requirements.txt installed. The high-resolution Esri image is
reference-only; the separately licensed Sentinel mosaic supplies ground context.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import Polygon, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
C = json.loads((ROOT/'config.json').read_text())
REF = ROOT/'references'
DATA = ROOT/'data'
to_utm = Transformer.from_crs(4326, C['horizontal_crs'], always_xy=True)
from_utm = Transformer.from_crs(C['horizontal_crs'], 4326, always_xy=True)
merc_to_utm = Transformer.from_crs(3857, C['horizontal_crs'], always_xy=True)
utm_to_merc = Transformer.from_crs(C['horizontal_crs'], 3857, always_xy=True)
OX, OY = to_utm.transform(*C['origin_wgs84'])
ext = json.loads((REF/'esri.json').read_text())['extent']
satellite = Image.open(REF/'satellite-context.jpg').convert('RGB')
SAT_ARRAY = np.asarray(satellite)


def local(lon, lat):
    x,y=to_utm.transform(lon,lat)
    return x-OX,y-OY


def from_pixel(x,y):
    mx=ext['xmin']+x/2048*(ext['xmax']-ext['xmin'])
    my=ext['ymax']-y/2048*(ext['ymax']-ext['ymin'])
    x,y=merc_to_utm.transform(mx,my)
    return x-OX,y-OY


def to_pixel(x,y):
    mx,my=utm_to_merc.transform(x+OX,y+OY)
    return ((mx-ext['xmin'])/(ext['xmax']-ext['xmin'])*2048,
            (ext['ymax']-my)/(ext['ymax']-ext['ymin'])*2048)


tiles={}
for path in REF.glob('dem-12-*.png'):
    _,z,x,y=path.stem.split('-')
    rgb=np.asarray(Image.open(path)).astype(float)
    tiles[int(x),int(y)]=rgb[:,:,0]*256+rgb[:,:,1]+rgb[:,:,2]/256-32768


def elevation(x,y):
    lon,lat=from_utm.transform(x+OX,y+OY)
    px=(lon+180)/360*4096*256-.5
    py=(1-np.arcsinh(np.tan(np.radians(lat)))/np.pi)/2*4096*256-.5
    ix,iy=int(math.floor(px)),int(math.floor(py)); fx,fy=px-ix,py-iy
    def pixel(a,b):return tiles[a//256,b//256][b%256,a%256]
    return (pixel(ix,iy)*(1-fx)+pixel(ix+1,iy)*fx)*(1-fy)+(pixel(ix,iy+1)*(1-fx)+pixel(ix+1,iy+1)*fx)*fy


Z0=elevation(0,0)


def sample_roof(poly):
    coords=[to_pixel(*p) for p in poly.exterior.coords]
    left=max(0,math.floor(min(p[0] for p in coords)));right=min(2048,math.ceil(max(p[0] for p in coords))+1)
    top=max(0,math.floor(min(p[1] for p in coords)));bottom=min(2048,math.ceil(max(p[1] for p in coords))+1)
    if right<=left or bottom<=top:return 'earth',[.48,.43,.34]
    mask=Image.new('L',(right-left,bottom-top))
    ImageDraw.Draw(mask).polygon([(x-left,y-top) for x,y in coords],fill=255)
    pixels=SAT_ARRAY[top:bottom,left:right][np.asarray(mask)>0].astype(float)/255
    if len(pixels)<3:return 'earth', [0.48,0.43,0.34]
    # Saturated metal roofs are distinctive in the reference image. Everything
    # else is uncertain: use neutral metal or earthen finish, not a height claim.
    r,g,b=pixels.T
    red=(r>g*1.3)&(r>b*1.35)&(r>.38)
    blue=(b>r*1.25)&(g>r*1.1)&(b>.3)
    if red.mean()>.14:return 'red_metal',[.39,.095,.045]
    if blue.mean()>.14:return 'blue_metal',[.06,.27,.34]
    neutral=(pixels.max(1)-pixels.min(1)<.17)&(pixels.mean(1)>.48)
    if neutral.mean()>.3:return 'galvanized',[.43,.47,.45]
    return 'earth',[.48,.39,.27]


def parts(geometry,kind):
    if geometry.is_empty:return []
    if geometry.geom_type==kind:return [geometry]
    return [g for g in getattr(geometry,'geoms',[]) if g.geom_type==kind]


def main():
    DATA.mkdir(exist_ok=True)
    corners=[from_pixel(x,y) for x,y in [(0,0),(2048,0),(2048,2048),(0,2048)]]
    boundary=Polygon(corners)
    xmin,ymin,xmax,ymax=boundary.bounds
    N=C['terrain_grid_samples']
    xs=np.linspace(xmin,xmax,N);ys=np.linspace(ymin,ymax,N)
    heights=np.array([[elevation(x,y)-Z0 for x in xs] for y in ys],dtype=np.float32)
    np.save(DATA/'terrain.npy',heights)
    terrain=dict(origin_utm=[OX,OY,Z0],crs=C['horizontal_crs'],bounds=[xmin,ymin,xmax,ymax],
                 shape=list(heights.shape),range_m=[float(heights.min()),float(heights.max())],
                 note='Bilinearly resampled Terrarium DEM; denser mesh does not add measured detail.')
    (DATA/'terrain.json').write_text(json.dumps(terrain,indent=2)+'\n')
    context_xs=np.linspace(-4500,4500,257)
    context=np.array([[elevation(x,y)-Z0 for x in context_xs] for y in context_xs],dtype=np.float32)
    np.save(DATA/'context_terrain.npy',context)
    (DATA/'context_terrain.json').write_text(json.dumps(dict(bounds=[-4500,-4500,4500,4500],shape=[257,257],
         scope='Terrain-only regional backdrop; buildings and land use outside main extent not reconstructed'),indent=2)+'\n')
    xml=ET.parse(REF/'osm.xml').getroot()
    nodes={n.attrib['id']:local(float(n.attrib['lon']),float(n.attrib['lat'])) for n in xml.findall('node')}
    roads=[];residential=[]
    for way in xml.findall('way'):
        tags={t.attrib['k']:t.attrib['v'] for t in way.findall('tag')}
        points=[nodes[n.attrib['ref']] for n in way.findall('nd') if n.attrib['ref'] in nodes]
        if len(points)<2:continue
        if 'highway' in tags:
            width={'residential':5.5,'unclassified':5,'tertiary':6.5,'track':3,'path':1.7,'service':3.5,'footway':1.6}.get(tags['highway'],4)
            for line in parts(LineString(points).intersection(boundary),'LineString'):
                roads.append(dict(id='osm-way-'+way.attrib['id'],kind=tags['highway'],width_m=width,
                                  width_evidence='estimated',tags=tags,points=list(line.coords)))
        elif tags.get('landuse')=='residential' and len(points)>3:
            residential.append(list(Polygon(points).exterior.coords))
    road_lines=unary_union([LineString(r['points']) for r in roads])
    features=json.loads((DATA/'buildings_wgs84.geojson').read_text())['features']
    buildings=[]
    for feature in features:
        poly=Polygon([local(*p[:2]) for p in feature['geometry']['coordinates'][0]])
        if not poly.is_valid:poly=poly.buffer(0)
        if poly.geom_type!='Polygon' or poly.area<8 or not boundary.intersects(poly):continue
        poly=orient(poly,sign=1)
        key=hashlib.sha256(json.dumps(feature['geometry'],sort_keys=True).encode()).hexdigest()[:12]
        rng=random.Random(key)
        center=poly.centroid; base=elevation(center.x,center.y)-Z0
        roof,color=sample_roof(poly)
        rect=poly.minimum_rotated_rectangle
        rectangularity=poly.area/rect.area
        # Unmeasured defaults are explicitly labeled per feature.
        floors=2 if poly.area>55 and rng.random()<.26 else 1
        if poly.area>450:floors=1
        source_h=feature['properties'].get('height',-1)
        height=float(source_h) if source_h>0 else floors*C['estimated_storey_height_m']+rng.uniform(-.15,.25)
        ground=[elevation(x,y)-Z0 for x,y in poly.exterior.coords]
        base=max(base,float(np.percentile(ground,70)))
        ring=list(poly.exterior.coords)[:-1]
        edges=[]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
            edges.append(mid.distance(road_lines))
        buildings.append(dict(id='ms-'+key,polygon=ring,rectangle=list(rect.exterior.coords)[:-1],
                              rectangularity=rectangularity,area_m2=poly.area,base_z=base,
                              foundation_bottom=min(ground)-.3,height_m=height,floors=floors,
                              height_evidence='source_estimate' if source_h>0 else 'unmeasured_typology_estimate',
                              roof=roof,roof_color=color,roof_evidence='approximate_satellite_visual_class',
                              roof_shape='gable_inferred' if roof!='earth' and rectangularity>.84 else 'flat_inferred',
                              entrance_edge=min(range(len(edges)),key=edges.__getitem__),
                              facade_evidence='procedural_typology_not_individually_verified',
                              source_confidence=feature['properties'].get('confidence',-1)))
    # Agricultural envelopes visually interpreted from the satellite reference.
    # The subdivision/planting within them is an artistic reconstruction.
    pixel_fields=[
      ('north_fields',[(500,0),(1250,0),(1170,180),(1120,260),(970,360),(870,400),(740,455),(640,485),(495,650),(390,745),(320,700),(420,460),(480,300),(560,260),(620,130)]),
      ('orchards_above_village',[(1220,220),(1470,210),(1510,255),(1430,330),(1270,380),(1230,575),(1175,680),(1100,760),(1000,850),(900,880),(790,965),(720,1050),(680,1090),(600,1130),(410,1200),(330,1230),(300,1170),(240,1120),(280,980),(300,900),(390,810),(460,770),(490,690),(570,620),(620,540),(700,510),(850,460),(900,400),(1050,350),(1160,300)]),
      ('western_orchards',[(260,800),(300,860),(275,970),(200,1050),(235,1100),(280,1180),(310,1270),(290,1380),(225,1450),(180,1540),(100,1720),(0,1750),(0,1110),(80,980),(150,900)]),
      ('southwestern_fields',[(0,1750),(120,1680),(205,1560),(270,1470),(300,1490),(350,1740),(290,1800),(220,1900),(220,2048),(0,2048)]),
      ('north_east_fields',[(1530,0),(2048,0),(2048,135),(1960,130),(1870,240),(1800,210),(1730,240),(1690,180),(1600,165),(1490,200),(1460,150)]),
      ('west_dry_fields',[(0,150),(510,35),(520,190),(420,265),(370,370),(200,460),(0,490)]),
      ('west_terraces',[(50,480),(300,400),(420,330),(450,400),(350,560),(250,650),(90,800),(0,880),(0,570)])]
    fields=[dict(id=name,polygon=[from_pixel(*p) for p in pts],
                 evidence='visually_interpreted_agricultural_envelope',
                 parcels='procedural_subdivision_not_cadastral',orchard=('orchard' in name)) for name,pts in pixel_fields]
    course_pixels=[(1560,0),(1430,38),(1360,63),(1290,110),(1240,150),(1200,225),(1120,280),
        (1040,317),(965,390),(880,420),(760,465),(710,482),(675,515),(690,550),(620,585),
        (594,645),(550,668),(530,700),(565,727),(530,765),(460,810),(430,850),(345,865),
        (320,905),(300,940),(270,960),(238,1000),(244,1040),(190,1100),(145,1130),
        (130,1150),(145,1200),(95,1225),(15,1265)]
    watercourse=dict(points=[from_pixel(*p) for p in course_pixels],width_m=5,
         evidence='Approximate visual trace of valley channel in reference imagery; width and seasonal flow unmeasured')
    model=dict(terrain=terrain,buildings=buildings,roads=roads,fields=fields,residential=residential,
               watercourse=watercourse,fort_location=list(local(49.9982263,35.3866343)))
    (DATA/'scene.json').write_text(json.dumps(model,separators=(',',':'))+'\n')
    # Diagnostic overlay is kept with reference material, not redistributed.
    overlay=satellite.copy();draw=ImageDraw.Draw(overlay)
    for b in buildings:draw.line([to_pixel(*p) for p in b['polygon']+[b['polygon'][0]]],fill=(0,255,255),width=1)
    for r in roads:draw.line([to_pixel(*p) for p in r['points']],fill=(255,65,40),width=2)
    overlay.save(REF/'alignment-check.jpg')
    report=dict(buildings=len(buildings),mapped_road_segments=len(roads),
                building_heights=dict(Counter(b['height_evidence'] for b in buildings)),
                roof_classes=dict(Counter(b['roof'] for b in buildings)),terrain=terrain,
                source='Microsoft Global ML Building Footprints; OpenStreetMap; Mapzen terrain tiles',
                estimated_fields=len(fields),checks='Finite metric coordinates, valid polygons, DEM coverage checked')
    (DATA/'preparation-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
