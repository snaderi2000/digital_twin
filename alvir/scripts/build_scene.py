"""Build the georeferenced Alvir scene inside Blender 4.5 LTS.

Mapped geometry and inferred detail remain separate, with evidence on each object.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'scripts'))
import build_scene as common
from geometry import MeshBuffer

D=json.loads((ROOT/'data/scene.json').read_text())
L=json.loads((ROOT/'data/landscape.json').read_text())
C=json.loads((ROOT/'config.json').read_text())
H=np.load(ROOT/'data/terrain.npy')
X0,Y0,X1,Y1=D['terrain']['bounds']
R=random.Random(C['seed'])
M={}


def ground(x,y):
    u=max(0,min(H.shape[1]-1.000001,(x-X0)/(X1-X0)*(H.shape[1]-1)))
    v=max(0,min(H.shape[0]-1.000001,(y-Y0)/(Y1-Y0)*(H.shape[0]-1)))
    a,b=int(u),int(v);fx,fy=u-a,v-b
    return float((H[b,a]*(1-fx)+H[b,a+1]*fx)*(1-fy)+(H[b+1,a]*(1-fx)+H[b+1,a+1]*fx)*fy)


def obj(name,buf,mats,group,bevel=0):return common.mesh_object(name,buf,mats,group,bevel)


def surface(name,color,rough=.85,grain=.015):
    m,p=common.material(name,color,rough)
    nodes,links=m.node_tree.nodes,m.node_tree.links
    geo=nodes.new('ShaderNodeNewGeometry');noise=nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=28;noise.inputs['Detail'].default_value=4
    links.new(geo.outputs['Position'],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(*(v*.62 for v in color),1)
    ramp.color_ramp.elements[1].color=(*(min(1,v*1.14) for v in color),1)
    links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],p.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=grain;bump.inputs['Strength'].default_value=.45
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],p.inputs['Normal'])
    return m


def materials():
    M['earth']=surface('Rammed earth · weathered clay',(.48,.37,.235),grain=.055)
    M['plaster']=surface('Warm lime render',(.65,.60,.48),grain=.012)
    M['white']=surface('Modern pale plaster',(.74,.73,.67),grain=.008)
    M['brick']=common.masonry('Exposed ochre brick',(.48,.31,.18),(.62,.45,.28),.24,.07,.006,False)
    M['stone']=common.masonry('Rough stone footing',(.30,.29,.24),(.45,.43,.35),.48,.25,.018,False)
    M['wood']=surface('Weathered wooden gates',(.18,.125,.07),grain=.025)
    M['frame']=surface('Painted grey steel frames',(.16,.19,.18),.48,.002)
    M['blue_door']=surface('Faded turquoise painted doors',(.075,.25,.27),.65,.004)
    M['glass']=common.material('Dark reflected glazing',(.055,.085,.10),.22)[0]
    M['bark']=surface('Walnut and orchard bark',(.21,.16,.105),grain=.045)
    M['asphalt']=surface('Worn village road surface',(.22,.215,.185),grain=.018)
    M['track']=surface('Compacted earth lane',(.43,.35,.235),grain=.03)
    M['metal']={}
    for key,color in [('galvanized',(.46,.49,.48)),('blue_metal',(.045,.25,.33)),('red_metal',(.42,.10,.045))]:
        m=surface('Corrugated roof · '+key,color,.52,.005)
        m.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.5
        M['metal'][key]=m
    M['leaves']=[surface('Orchard foliage '+str(i),(.08+i*.014,.15+i*.020,.035+i*.007),.7,.001) for i in range(5)]
    for m in M['leaves']:
        m.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.08
    terrain=surface('Terrain · rock and soil',(.32,.255,.16),grain=.09)
    M['backdrop']=terrain
    nn,ll=terrain.node_tree.nodes,terrain.node_tree.links
    background_image=nn.new('ShaderNodeTexImage')
    background_image.image=bpy.data.images.load(str(ROOT/'data/context_texture.jpg'));background_image.image.pack()
    background_uv=nn.new('ShaderNodeTexCoord');ll.new(background_uv.outputs['UV'],background_image.inputs['Vector'])
    ll.new(background_image.outputs['Color'],nn.get('Principled BSDF').inputs['Base Color'])
    M['terrain']=terrain.copy();M['terrain'].name='Village ground · vector-derived land palette'
    n,l=M['terrain'].node_tree.nodes,M['terrain'].node_tree.links
    image=n.new('ShaderNodeTexImage');image.image=bpy.data.images.load(str(ROOT/'data/ground_texture.png'));image.image.pack()
    uv=n.new('ShaderNodeTexCoord');l.new(uv.outputs['UV'],image.inputs['Vector'])
    geo=n.new('ShaderNodeNewGeometry')
    broad=n.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=.023;broad.inputs['Detail'].default_value=5
    l.new(geo.outputs['Position'],broad.inputs['Vector'])
    tint=n.new('ShaderNodeValToRGB')
    tint.color_ramp.elements[0].color=(.40,.34,.26,1);tint.color_ramp.elements[1].color=(1,.98,.88,1)
    l.new(broad.outputs['Fac'],tint.inputs[0])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.7
    l.new(image.outputs['Color'],mix.inputs[1]);l.new(tint.outputs[0],mix.inputs[2])
    l.new(mix.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
    erosion=n.new('ShaderNodeTexNoise');erosion.inputs['Scale'].default_value=.18;erosion.inputs['Detail'].default_value=5
    l.new(geo.outputs['Position'],erosion.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.35;bump.inputs['Strength'].default_value=.5
    l.new(erosion.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],n.get('Principled BSDF').inputs['Normal'])
    # Identical world-space shading at the detailed/context boundary.
    M['backdrop']=M['terrain'].copy();M['backdrop'].name='Regional terrain · matched boundary shading'
    for node in M['backdrop'].node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image and node.image.name.startswith('ground_texture'):
            node.image=bpy.data.images.get('context_texture.jpg')


def terrain_mesh(name,array,bounds,mat,group,omit_core=False):
    xmin,ymin,xmax,ymax=bounds;ny,nx=array.shape
    buf=MeshBuffer()
    xs=np.linspace(xmin,xmax,nx);ys=np.linspace(ymin,ymax,ny)
    if omit_core:
        # Share every border sample with the detailed grid: no overlapping
        # surfaces or T-junction gaps where the two DEM meshes meet.
        xs=np.unique(np.concatenate([xs,np.linspace(X0,X1,H.shape[1])]))
        ys=np.unique(np.concatenate([ys,np.linspace(Y0,Y1,H.shape[0])]))
        def height(x,y):
            if (abs(x-X0)<1e-6 or abs(x-X1)<1e-6) and Y0<=y<=Y1:return ground(x,y)
            if (abs(y-Y0)<1e-6 or abs(y-Y1)<1e-6) and X0<=x<=X1:return ground(x,y)
            u=np.clip((x-xmin)/(xmax-xmin)*(array.shape[1]-1),0,array.shape[1]-1.000001)
            v=np.clip((y-ymin)/(ymax-ymin)*(array.shape[0]-1),0,array.shape[0]-1.000001)
            a,b=int(u),int(v);fx,fy=u-a,v-b
            return float((array[b,a]*(1-fx)+array[b,a+1]*fx)*(1-fy)+(array[b+1,a]*(1-fx)+array[b+1,a+1]*fx)*fy)
        buf.vertices=[(float(x),float(y),height(x,y)) for y in ys for x in xs]
        nx,ny=len(xs),len(ys)
    else:
        buf.vertices=[(float(x),float(y),float(array[j,i])) for j,y in enumerate(ys) for i,x in enumerate(xs)]
    for j in range(ny-1):
        for i in range(nx-1):
            k=j*nx+i;x,y,z=buf.vertices[k]
            if omit_core and X0<=(x+xs[i+1])/2<=X1 and Y0<=(y+ys[j+1])/2<=Y1:continue
            buf.faces.append((k,k+1,k+nx+1,k+nx));buf.materials.append(0)
    o=obj(name,buf,[mat],group)
    uv=o.data.uv_layers.active
    for poly in o.data.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            v=o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=((v.x-xmin)/(xmax-xmin),(v.y-ymin)/(ymax-ymin))
    o['source']='Mapzen Terrarium / USGS global elevation sources';o['vertical_exaggeration']=1.0
    return o


def prism_z(buf,ring,z0,z1,material=0):
    n=len(ring)
    verts=[(x,y,z0) for x,y in ring]+[(x,y,z1) for x,y in ring]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    buf.poly(verts,faces,material)


def beam(buf,a,b,width,height,material=0):
    a,b=Vector(a),Vector(b);d=b-a
    if d.length<.001:return
    if math.hypot(d.x,d.y)<1e-8:
        side=Vector((width/2,0,0));up=Vector((0,height/2,0))
    else:
        side=Vector((-d.y,d.x,0)).normalized()*width/2
        up=Vector((0,0,height/2))
    buf.poly([tuple(p) for p in (a-side-up,b-side-up,b+side-up,a+side-up,a-side+up,b-side+up,b+side+up,a+side+up)],
             [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)


def wall_face(buf,points,material=0):buf.poly(points,[(0,1,2,3)],material)


def building(b):
    rng=random.Random(b['id']);ring=b['polygon'];z=b['base_z'];h=b['height_m']
    walls=MeshBuffer();details=MeshBuffer();foot=MeshBuffer()
    prism_z(foot,ring,b['foundation_bottom'],z+.35)
    obj(b['id']+' · foundations',foot,[M['stone']],'03 | Buildings · foundations')
    mat=rng.choices(['earth','plaster','white','brick'],[.35,.29,.18,.18])[0]
    for edge,(a,bb) in enumerate(zip(ring,ring[1:]+ring[:1])):
        ax,ay=a;bx,by=bb;length=math.hypot(bx-ax,by-ay)
        if length<.05:continue
        ux,uy=(bx-ax)/length,(by-ay)/length
        nx,ny=uy,-ux
        def point(t,v,depth=0):return (ax+ux*t+nx*depth,ay+uy*t+ny*depth,z+v)
        openings=[]
        if edge==b['entrance_edge'] and length>3:
            dw=1.45 if b['area_m2']<120 else 2.3
            openings.append((length*.5-dw/2,length*.5+dw/2,.12,2.3,'door'))
        if length>4:
            count=max(1,int(length/4))
            for floor in range(b['floors']):
                for j in range(count):
                    center=(j+.5)*length/count
                    op=(center-.55,center+.55,floor*3.1+1.15,floor*3.1+2.4,'window')
                    if op[3]>h-.2:continue
                    if any(op[0]<d[1]+.35 and op[1]>d[0]-.35 and op[2]<d[3] and op[3]>d[2] for d in openings):continue
                    openings.append(op)
        # Wall faces are partitioned around actual recessed openings.
        us=sorted(set([0,length]+[o[i] for o in openings for i in (0,1)]))
        vs=sorted(set([.3,h]+[o[i] for o in openings for i in (2,3)]))
        for u0,u1 in zip(us,us[1:]):
            for v0,v1 in zip(vs,vs[1:]):
                midu,midv=(u0+u1)/2,(v0+v1)/2
                if any(l<midu<r and lo<midv<hi for l,r,lo,hi,t in openings):continue
                wall_face(walls,[point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)])
        for left,right,lo,hi,kind in openings:
            corners=[point(left,lo),point(right,lo),point(right,hi),point(left,hi)]
            inset=[point(left,lo,-.16),point(right,lo,-.16),point(right,hi,-.16),point(left,hi,-.16)]
            for i in range(4):wall_face(walls,[corners[i],corners[(i+1)%4],inset[(i+1)%4],inset[i]])
            index=(2 if rng.random()<.5 else 3) if kind=='door' else 0
            wall_face(details,inset,index)
            for v in [lo,hi]:beam(details,point(left,v,.025),point(right,v,.025),.10,.085,1)
            for u in [left,right,(left+right)/2]:beam(details,point(u,lo,.02),point(u,hi,.02),.07,.06,1)
            if kind=='window':beam(details,point(left,(lo+hi)/2,.02),point(right,(lo+hi)/2,.02),.055,.05,1)
            else:
                for u in np.arange(left+.1,right,.16):beam(details,point(u,lo,-.12),point(u,hi,-.12),.018,.02,1)
        # Coping makes the building silhouette legible at grazing light.
        beam(walls,point(0,h+.06),point(length,h+.06),.24,.16)
    o=obj(b['id']+' · walls',walls,[M[mat]],'04 | Buildings · façades',.025)
    for key in ['id','height_m','height_evidence','roof_evidence','facade_evidence']:o[key]=b[key]
    o['source']='Microsoft Global ML Building Footprints';o['footprint_area_m2']=b['area_m2']
    obj(b['id']+' · recessed windows and doors',details,[M['glass'],M['frame'],M['wood'],M['blue_door']],'05 | Buildings · inferred details')
    roof=MeshBuffer()
    if b['roof_shape']=='gable_inferred':
        rect=b['rectangle'];a,bb,c,d=[Vector((p[0],p[1],z+h+.12)) for p in rect]
        if (bb-a).length<(c-bb).length:a,bb,c,d=bb,c,d,a
        u=(bb-a).normalized();v=(d-a).normalized()
        a-=u*.22+v*.22;bb+=u*.22-v*.22;c+=u*.22+v*.22;d-=u*.22-v*.22
        rise=min(2.4,(d-a).length*.22)
        p=(a+d)/2+Vector((0,0,rise));q=(bb+c)/2+Vector((0,0,rise))
        roof.poly([tuple(v) for v in [a,bb,c,d,p,q]],[(0,1,5,4),(4,5,2,3),(0,4,3),(1,2,5)])
        roofmat=M['metal'][b['roof']]
        length=(bb-a).length
        for t in np.arange(0,length,.55):
            s=t/length
            beam(roof,a.lerp(bb,s),p.lerp(q,s),.025,.028)
            beam(roof,p.lerp(q,s),d.lerp(c,s),.025,.028)
        beam(roof,p,q,.13,.075)
    else:
        prism_z(roof,ring,z+h-.12,z+h+.1)
        roofmat=M['earth'] if b['roof']=='earth' else M['metal'][b['roof']]
        for a,bb in zip(ring,ring[1:]+ring[:1]):beam(roof,(*a,z+h+.25),(*bb,z+h+.25),.2,.3)
    obj(b['id']+' · roof',roof,[roofmat],'06 | Buildings · roofs')['shape_evidence']=b['roof_shape']
    # Rooftop service details are representative, not observed equipment inventories.
    if b['roof_shape']=='flat_inferred' and b['area_m2']>70:
        cx=sum(p[0] for p in ring)/len(ring);cy=sum(p[1] for p in ring)/len(ring)
        buf=MeshBuffer();buf.box((cx,cy,z+h+.45),(.65,.65,.7))
        obj(b['id']+' · vent',buf,[M['plaster']],'05 | Buildings · inferred details')


def roads():
    for road in D['roads']:
        buf=MeshBuffer();width=road['width_m']
        for a,b in zip(road['points'],road['points'][1:]):
            a,b=Vector(a),Vector(b);delta=b-a;length=delta.length
            if length<.01:continue
            side=Vector((-delta.y,delta.x)).normalized()*width/2
            n=max(1,math.ceil(length/4))
            for i in range(n):
                p=a.lerp(b,i/n);q=a.lerp(b,(i+1)/n)
                corners=[p-side,q-side,q+side,p+side]
                wall_face(buf,[(v.x,v.y,ground(v.x,v.y)+.10) for v in corners])
        mat=M['track'] if road['kind'] in ('track','path','footway') else M['asphalt']
        o=obj(road['id'],buf,[mat],'02 | Mapped roads')
        o['source']='OpenStreetMap contributors';o['width_evidence']='estimated';o['osm_tags']=json.dumps(road['tags'],ensure_ascii=False)


def tree_mesh(index):
    rng=random.Random(index+100);buf=MeshBuffer()
    # All trees share eight detailed meshes. Coordinates normalize to height 1.
    def branch(a,b,r0,r1):
        a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,1,0))).normalized();v=d.cross(u)
        vertices=[tuple(p+radius*(u*math.cos(k*math.tau/7)+v*math.sin(k*math.tau/7))) for p,radius in [(a,r0),(b,r1)] for k in range(7)]
        faces=[tuple(reversed(range(7))),tuple(range(7,14))]+[(k,(k+1)%7,(k+1)%7+7,k+7) for k in range(7)]
        buf.poly(vertices,faces,0)
    branch((0,0,0),(.01,0,.65),.025,.009)
    for k in range(9):
        angle=rng.random()*math.tau
        center=Vector((math.cos(angle)*.21,math.sin(angle)*.21,rng.uniform(.60,.82)))
        branch((0,0,.37),center,.013,.004)
        for leaf in range(180):
            theta=rng.random()*math.tau;u=rng.uniform(-1,1);radius=rng.random()**(1/3)*.25
            s=math.sqrt(1-u*u)
            pos=center+Vector((radius*s*math.cos(theta),radius*s*math.sin(theta),radius*u*.9))
            a=Vector((rng.uniform(.012,.028),rng.uniform(-.02,.02),rng.uniform(-.015,.015)))
            b=Vector((rng.uniform(-.012,.012),rng.uniform(.014,.024),rng.uniform(-.016,.016)))
            buf.poly([tuple(v) for v in [pos-a-b,pos+a-b,pos+a+b,pos-a+b]],[(0,1,2,3)],rng.randint(1,5))
    o=obj('Orchard tree prototype '+str(index),buf,[M['bark']]+M['leaves'],'00 | Internal tree prototypes')
    mesh=o.data;bpy.data.objects.remove(o,do_unlink=True)
    return mesh


def landscape():
    meshes=[tree_mesh(i) for i in range(8)]
    group=common.collection('08 | Inferred orchard planting')
    for i,(x,y,height,variant,angle) in enumerate(L['trees']):
        o=bpy.data.objects.new('Orchard tree · %05d'%i,meshes[variant]);group.objects.link(o)
        o.location=(x,y,ground(x,y));o.scale=(height,height,height);o.rotation_euler.z=angle
    if 'watercourse' in D:
        channel=MeshBuffer();bank_tree=0
        for a,b in zip(D['watercourse']['points'],D['watercourse']['points'][1:]):
            a,b=Vector(a),Vector(b);delta=b-a;length=delta.length
            normal=Vector((-delta.y,delta.x)).normalized()
            n=max(1,math.ceil(length/5))
            for i in range(n):
                p=a.lerp(b,i/n);q=a.lerp(b,(i+1)/n)
                corners=[p-normal*2.5,q-normal*2.5,q+normal*2.5,p+normal*2.5]
                wall_face(channel,[(v.x,v.y,ground(v.x,v.y)+.12) for v in corners])
                if i%3==0:
                    for sign in [-1,1]:
                        v=p+normal*sign*R.uniform(4.5,7)
                        o=bpy.data.objects.new('Valley tree · %04d'%bank_tree,meshes[bank_tree%8]);group.objects.link(o)
                        h=R.uniform(7,11);o.location=(v.x,v.y,ground(v.x,v.y));o.scale=(h*.75,h*.75,h)
                        bank_tree+=1
        obj('Valley channel · approximate visual trace',channel,[M['stone']],'10 | Interpreted valley channel')['evidence']=D['watercourse']['evidence']
    buf=MeshBuffer()
    for loop in L['walls']+L.get('courtyards',[]):
        for a,b in zip(loop,loop[1:]):
            a,b=Vector(a),Vector(b);length=(b-a).length;n=max(1,math.ceil(length/3))
            for i in range(n):
                p=a.lerp(b,i/n);q=a.lerp(b,(i+1)/n)
                h=1.25+R.uniform(-.10,.10)
                beam(buf,(p.x,p.y,ground(*p)+h/2),(q.x,q.y,ground(*q)+h/2),.38,h)
    obj('Garden enclosures · inferred from local wall typology',buf,[M['earth']],'09 | Inferred garden walls',.07)


def fort():
    # OSM node 9679160382; outline approximated from the visible ruined enclosure.
    # No invented intact towers or reconstructed historic superstructure.
    cx,cy=D.get('fort_location',[-324.4,-4.0])
    # A ruin at the mapped point is indicative; plan and wall heights are uncertain.
    buf=MeshBuffer();rng=random.Random(9679160382)
    for i in range(48):
        a=i*math.tau/48;b=(i+1)*math.tau/48
        if i in (5,6,20,21,22,35):continue
        p=(cx+18*math.cos(a),cy+16*math.sin(a));q=(cx+18*math.cos(b),cy+16*math.sin(b))
        h=rng.uniform(.65,2.0)
        beam(buf,(*p,ground(*p)+h/2),(*q,ground(*q)+h/2),1.1,h)
    o=obj('Alvir historic fort · indicative ruined enclosure',buf,[M['earth']],'07 | Mapped historic fort',.12)
    o['source']='OSM node 9679160382';o['location_evidence']='mapped point';o['geometry_evidence']='unmeasured indicative ruin, not verified historic reconstruction'


def setup():
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.cycles.adaptive_threshold=.025;scene.cycles.max_bounces=6
    scene.render.resolution_x=2560;scene.render.resolution_y=1440;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    for prop in scene.render.bl_rna.properties:
        if prop.identifier.startswith('use_stamp') and prop.type=='BOOLEAN':setattr(scene.render,prop.identifier,False)
    scene.render.use_stamp=True;scene.render.use_stamp_note=True;scene.render.use_stamp_labels=False
    scene.render.stamp_font_size=12
    scene.render.stamp_note_text='Microsoft footprints | © OpenStreetMap contributors | Mapzen / USGS terrain | Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 & 2017)'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-1.6
    world=bpy.data.worlds.new('Alvir · clear summer afternoon');world.use_nodes=True;scene.world=world
    n,l=world.node_tree.nodes,world.node_tree.links
    sky=n.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(34);sky.sun_rotation=math.radians(230)
    sky.altitude=1800;sky.air_density=.9;sky.dust_density=.65;sky.sun_size=math.radians(.7)
    l.new(sky.outputs[0],n.get('Background').inputs['Color']);n.get('Background').inputs['Strength'].default_value=.22
    scene['Project']='Alvir village · geospatial visual reconstruction'
    scene['Horizontal CRS']=C['horizontal_crs'];scene['UTM origin metres']=D['terrain']['origin_utm'][:2]
    scene['Elevation origin metres']=D['terrain']['origin_utm'][2]
    scene['Axes']='X easting, Y northing, Z up; scale 1 metre; no vertical exaggeration'
    scene['Evidence']='Mapped footprints/roads and DEM. Heights, facade details and planting inferred. Not a measured digital twin.'
    scene['Season']=C['season']
    scene['Imagery attribution']='Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 & 2017), CC BY 4.0. Historical landscape context.'
    cameras=[('01 · Village and valley',(950,-1250,1000),(-170,260,5),47),
             ('02 · Village fabric',(420,-540,330),(-60,50,6),52),
             ('03 · Orchard edge',(-430,-310,135),(-120,120,8),45),
             ('04 · Geographic plan',(0,0,3200),(0,0,0),45)]
    for name,position,target,lens in cameras:
        cam=common.camera(name,position,target,lens);cam.data.clip_end=20000
        if name.startswith('04'):
            cam.data.type='ORTHO'
            cam.location.x=(X0+X1)/2;cam.location.y=(Y0+Y1)/2
            cam.data.ortho_scale=max(X1-X0,(Y1-Y0)*16/9)*1.03
    # An exterior detail view demonstrates the inferred façade treatment.
    candidate=min((b for b in D['buildings'] if b['area_m2']>70 and b['roof_shape']=='gable_inferred'),
                  key=lambda b:sum((sum(p[i] for p in b['polygon'])/len(b['polygon'])-v)**2 for i,v in enumerate((350,-120))))
    ring=candidate['polygon'];edge=candidate['entrance_edge'];a=Vector(ring[edge]);bb=Vector(ring[(edge+1)%len(ring)])
    mid=(a+bb)/2;normal=Vector(((bb-a).y,-(bb-a).x)).normalized();eye=mid+normal*22
    cam=common.camera('05 · Inferred façade study',(eye.x,eye.y,candidate['base_z']+9),
                      (mid.x,mid.y,candidate['base_z']+candidate['height_m']*.5),38)
    cam.data.clip_end=20000
    cam['evidence']='Typology illustration only; not a photograph-matched façade.'
    scene.camera=bpy.data.objects['01 · Village and valley']
    scene.cycles.device='CPU'
    return scene


def main():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    materials()
    terrain_mesh('Alvir · DEM-derived terrain context',H,D['terrain']['bounds'],M['terrain'],'01 | Georeferenced terrain')
    terrain_mesh('Regional relief · terrain only',np.load(ROOT/'data/context_terrain.npy'),[-4500,-4500,4500,4500],M['backdrop'],'01 | Georeferenced terrain',True)
    roads()
    for i,b in enumerate(D['buildings']):
        building(b)
        if i%100==0:print('BUILDINGS',i,len(D['buildings']),flush=True)
    landscape();fort();scene=setup()
    if (ROOT/'data/visual-theme.json').exists():
        sys.path.insert(0,str(ROOT/'scripts'))
        from visual_theme import apply_theme
        apply_theme(scene)
    notes=bpy.data.texts.new('READ ME · evidence and coordinates')
    notes.write('ALVIR VILLAGE\nMapped building footprints and roads with true-scale terrain.\n'+scene['Evidence']+'\n'+json.dumps(D['terrain'],indent=2))
    bpy.context.view_layer.update()
    assert len([o for o in scene.objects if o.get('source')=='Microsoft Global ML Building Footprints'])==len(D['buildings'])
    assert all(math.isfinite(v) for o in scene.objects if o.type=='MESH' for vertex in o.data.vertices for v in vertex.co)
    report=dict(buildings=len(D['buildings']),roads=len(D['roads']),instanced_trees=len(L['trees']),
                objects=len(scene.objects),unique_meshes=len(bpy.data.meshes),
                unique_vertices=sum(len(m.vertices) for m in bpy.data.meshes),
                crs=C['horizontal_crs'],origin=D['terrain']['origin_utm'],units='metres',
                external_images=[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file],
                validation='passed',limitations='All building heights and facade layouts are estimates; parcels and individual trees inferred.')
    assert not report['external_images']
    (ROOT/'output').mkdir(exist_ok=True)
    (ROOT/'output/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/alvir_village.blend'),compress=True)
    print('ALVIR_BUILD_COMPLETE',json.dumps(report),flush=True)


if __name__=='__main__':main()
