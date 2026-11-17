"""Reproject licensed historical Sentinel imagery into the model's metric frame."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
T=json.loads((ROOT/'data/terrain.json').read_text())
S=json.loads((ROOT/'data/sentinel_context.json').read_text())


def sample(bounds,size=2048):
    source=np.asarray(Image.open(ROOT/'data/sentinel_context.jpg')).astype(np.float32)
    xmin,ymin,xmax,ymax=bounds;ox,oy,_=T['origin_utm']
    xs,ys=np.meshgrid(np.linspace(xmin,xmax,size)+ox,np.linspace(ymax,ymin,size)+oy)
    mx,my=Transformer.from_crs(T['crs'],3857,always_xy=True).transform(xs,ys)
    a,b,c,d=S['extent_3857']
    u=np.clip((mx-a)/(c-a)*(source.shape[1]-1),0,source.shape[1]-1.001)
    v=np.clip((d-my)/(d-b)*(source.shape[0]-1),0,source.shape[0]-1.001)
    ix=u.astype(int);iy=v.astype(int);fx=(u-ix).astype(np.float32)[...,None];fy=(v-iy).astype(np.float32)[...,None]
    arr=(source[iy,ix]*(1-fx)+source[iy,ix+1]*fx)*(1-fy)+(source[iy+1,ix]*(1-fx)+source[iy+1,ix+1]*fx)*fy
    # Moderate the mosaic's warm color enhancement; retain geographic texture.
    grey=arr.mean(axis=2,keepdims=True)
    return .72*arr+.28*grey


def main():
    context=sample([-4500,-4500,4500,4500])
    Image.fromarray(np.clip(context,0,255).astype('uint8')).save(ROOT/'data/context_texture.jpg',quality=95)
    ground=sample(T['bounds'])
    palette=np.asarray(Image.open(ROOT/'data/ground_palette.png').resize((2048,2048),Image.Resampling.LANCZOS)).astype(np.float32)
    edge=np.minimum(np.arange(2048),np.arange(2048)[::-1])
    weight=np.minimum(edge[:,None],edge[None,:])/120
    weight=np.clip(weight,0,1)[...,None]*.22
    ground=ground*(1-weight)+palette*weight
    Image.fromarray(np.clip(ground,0,255).astype('uint8')).save(ROOT/'data/ground_texture.png')
    print('Prepared georeferenced Sentinel-based terrain textures; imagery attribution retained in data/sentinel_context.json')


if __name__=='__main__':main()
