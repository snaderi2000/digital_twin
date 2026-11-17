"""Acquire public sources for Alvir. Prepared data is shipped for offline builds."""
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references'
INDEX='https://bfppub.blob.core.windows.net/%24web/2026-08-13/dataset-links.csv'
OSM='https://api.openstreetmap.org/api/0.6/map?bbox=49.986,35.374,50.018,35.399'
IMAGERY='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?'+urllib.parse.urlencode(
    dict(bbox='49.986,35.374,50.018,35.399',bboxSR=4326,imageSR=3857,size='2048,2048',format='jpg',f='json'))


def main():
    REF.mkdir(exist_ok=True);(ROOT/'data').mkdir(exist_ok=True)
    records=[]
    def get(name,url,license_note):
        path=REF/name
        cached=path.exists()
        if not cached:
            request=urllib.request.Request(url,headers={'User-Agent':'AlvirReconstruction/0.1 (geographic modeling study)'})
            data=urllib.request.urlopen(request,timeout=120).read()
            path.write_bytes(data)
        records.append(dict(file=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            license=license_note,cache_reused=cached))
        print(name,'cached' if cached else 'downloaded',flush=True)
        return path
    index=get('building-index.csv',INDEX,'Microsoft CDLA Permissive 2.0')
    row=next(r for r in csv.DictReader(index.open()) if r['Location']=='Iran' and r['QuadKey']=='123002131')
    buildings=get('buildings.geojsonl.gz',row['Url'],'Microsoft CDLA Permissive 2.0')
    get('osm.xml',OSM,'OpenStreetMap contributors; ODbL 1.0')
    for x in (2616,2617):
        for y in (1616,1617):
            get(f'dem-12-{x}-{y}.png',f'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/12/{x}/{y}.png',
                'Mapzen Terrain Tiles; USGS SRTM/GMTED2010 attribution; see source documentation')
    meta=get('esri.json',IMAGERY,'Esri World Imagery; reference use only; image not distributed in model')
    href=json.loads(meta.read_text()).get('href')
    if not href:raise RuntimeError('Imagery export did not return a usable image URL')
    get('satellite-context.jpg',href,'Reference only. This Esri raster is not embedded in the model or renders.')
    sentinel_meta=ROOT/'data/sentinel_context.json'
    if sentinel_meta.exists():
        sm=json.loads(sentinel_meta.read_text())
        target=ROOT/'data/sentinel_context.jpg'
        if not target.exists():
            request=urllib.request.Request(sm['url'],headers={'User-Agent':'AlvirReconstruction/0.1'})
            target.write_bytes(urllib.request.urlopen(request,timeout=120).read())
        records.append(dict(file='data/sentinel_context.jpg',url=sm['url'],
                       sha256=hashlib.sha256(target.read_bytes()).hexdigest(),license=sm['license'],attribution=sm['attribution']))
    selected=[]
    with gzip.open(buildings,'rt') as handle:
        for line in handle:
            feature=json.loads(line);x,y=feature['geometry']['coordinates'][0][0][:2]
            if 49.986<x<50.018 and 35.374<y<35.399:selected.append(feature)
    (ROOT/'data/buildings_wgs84.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=selected),separators=(',',':'))+'\n')
    report=dict(manifest_generated_utc=datetime.now(timezone.utc).isoformat(),sources=records,
                note='Cached sources preserve acquisition snapshots. Remove a specific reference file to fetch it again; this can change the model.')
    (ROOT/'data/source-manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
