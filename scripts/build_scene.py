"""Build an editable, self-contained Si-o-se-pol reconstruction in Blender 4.5 LTS.

blender -b -t 8 --python scripts/build_scene.py -- --render hero --quality preview
All surfaces are native geometry or procedural shaders. No external assets required.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from geometry import MeshBuffer, layout, pointed_arch

C = json.loads((ROOT / 'config/bridge.json').read_text())
RNG = random.Random(C['seed'])
COLLECTIONS = {}
MATERIALS = {}


def collection(name):
    if name not in COLLECTIONS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLLECTIONS[name] = c
    return COLLECTIONS[name]


def mesh_object(name, buffer, materials, group, bevel=0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(buffer.vertices, [], buffer.faces)
    mesh.update()
    # Face-projected UVs in metres; brick scale is independent of object dimensions.
    uv = mesh.uv_layers.new(name='Masonry · metres')
    for p in mesh.polygons:
        p.material_index = buffer.materials[p.index] % len(materials)
        n = p.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            v = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = ((v.y,v.z) if axis==0 else (v.x,v.z) if axis==1 else (v.x,v.y))
    for m in materials:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    collection(group).objects.link(obj)
    if bevel:
        mod = obj.modifiers.new('Soft, weathered arris', 'BEVEL')
        mod.width, mod.segments = bevel, 2
        mod.limit_method = 'ANGLE'
    return obj


def box(name, center, size, mat, group, bevel=0):
    b = MeshBuffer()
    b.box(center,size)
    return mesh_object(name,b,[mat],group,bevel)


def material(name, color, roughness=.8):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    MATERIALS[name]=m
    return m,p


def masonry(name, color1, color2, width=.26, height=.065, mortar=.004, weather=True):
    m,p=material(name,color1)
    n,l=m.node_tree.nodes,m.node_tree.links
    uv=n.new('ShaderNodeTexCoord')
    brick=n.new('ShaderNodeTexBrick')
    brick.inputs['Color1'].default_value=(*color1,1)
    brick.inputs['Color2'].default_value=(*color2,1)
    brick.inputs['Mortar'].default_value=(.29,.25,.18,1)
    brick.inputs['Scale'].default_value=1
    brick.inputs['Mortar Size'].default_value=mortar
    brick.inputs['Mortar Smooth'].default_value=.001
    brick.inputs['Brick Width'].default_value=width
    brick.inputs['Row Height'].default_value=height
    brick.offset=.5
    brick.offset_frequency=2
    # Slightly irregular edges avoid a mechanically perfect brick grid at close range.
    warp=n.new('ShaderNodeTexNoise'); warp.inputs['Scale'].default_value=23
    warp.inputs['Detail'].default_value=3
    l.new(uv.outputs['UV'],warp.inputs['Vector'])
    offset=n.new('ShaderNodeVectorMath'); offset.operation='SUBTRACT'
    offset.inputs[1].default_value=(.5,.5,.5)
    l.new(warp.outputs['Color'],offset.inputs[0])
    amplitude=n.new('ShaderNodeVectorMath'); amplitude.operation='SCALE'
    amplitude.inputs['Scale'].default_value=.012
    l.new(offset.outputs[0],amplitude.inputs[0])
    distorted=n.new('ShaderNodeVectorMath'); distorted.operation='ADD'
    l.new(uv.outputs['UV'],distorted.inputs[0]); l.new(amplitude.outputs[0],distorted.inputs[1])
    l.new(distorted.outputs[0],brick.inputs['Vector'])
    geo=n.new('ShaderNodeNewGeometry')
    noise=n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=1.1
    noise.inputs['Detail'].default_value=4
    noise.inputs['Roughness'].default_value=.75
    l.new(geo.outputs['Position'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.18
    ramp.color_ramp.elements[0].color=(.28,.25,.19,1)
    ramp.color_ramp.elements[1].position=.85
    ramp.color_ramp.elements[1].color=(1,.95,.83,1)
    l.new(noise.outputs['Fac'],ramp.inputs[0])
    mix=n.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=.65
    l.new(brick.outputs['Color'],mix.inputs[1]); l.new(ramp.outputs[0],mix.inputs[2])
    color=mix.outputs[0]
    if weather:
        streak_scale=n.new('ShaderNodeVectorMath'); streak_scale.operation='MULTIPLY'
        streak_scale.inputs[1].default_value=(3,3,.16)
        l.new(geo.outputs['Position'],streak_scale.inputs[0])
        streaks=n.new('ShaderNodeTexNoise'); streaks.inputs['Scale'].default_value=2
        streaks.inputs['Detail'].default_value=3
        l.new(streak_scale.outputs[0],streaks.inputs['Vector'])
        dirt=n.new('ShaderNodeValToRGB')
        dirt.color_ramp.elements[0].position=.25; dirt.color_ramp.elements[0].color=(.20,.19,.15,1)
        dirt.color_ramp.elements[1].position=.62; dirt.color_ramp.elements[1].color=(1,1,1,1)
        l.new(streaks.outputs['Fac'],dirt.inputs[0])
        weather_mix=n.new('ShaderNodeMixRGB'); weather_mix.blend_type='MULTIPLY'
        weather_mix.inputs[0].default_value=.36
        l.new(color,weather_mix.inputs[1]); l.new(dirt.outputs[0],weather_mix.inputs[2])
        color=weather_mix.outputs[0]
        sep=n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Position'],sep.inputs[0])
        wet=n.new('ShaderNodeMapRange')
        wet.inputs['From Min'].default_value=.6
        wet.inputs['From Max'].default_value=2.6
        wet.inputs['To Min'].default_value=.28
        wet.inputs['To Max'].default_value=1
        l.new(sep.outputs['Z'],wet.inputs['Value'])
        wetmix=n.new('ShaderNodeMixRGB'); wetmix.blend_type='MULTIPLY'; wetmix.inputs[0].default_value=1
        l.new(color,wetmix.inputs[1]); l.new(wet.outputs['Result'],wetmix.inputs[2])
        color=wetmix.outputs[0]
    l.new(color,p.inputs['Base Color'])
    fine=n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=125
    fine.inputs['Detail'].default_value=3
    l.new(geo.outputs['Position'],fine.inputs['Vector'])
    grain=n.new('ShaderNodeBump'); grain.inputs['Strength'].default_value=.28; grain.inputs['Distance'].default_value=.012
    l.new(fine.outputs['Fac'],grain.inputs['Height'])
    bump=n.new('ShaderNodeBump'); bump.invert=True
    bump.inputs['Strength'].default_value=.7; bump.inputs['Distance'].default_value=.012
    l.new(brick.outputs['Fac'],bump.inputs['Height']); l.new(grain.outputs[0],bump.inputs['Normal'])
    l.new(bump.outputs[0],p.inputs['Normal'])
    return m


def setup_materials():
    MATERIALS['brick']=masonry('01 · Ochre fired brick / lime joints',(.49,.30,.145),(.70,.49,.265))
    MATERIALS['stone']=masonry('02 · River limestone / damp courses',(.39,.39,.33),(.58,.54,.43),.88,.39,.009)
    MATERIALS['paving']=masonry('03 · Worn grey promenade paving',(.24,.25,.24),(.32,.32,.30),.8,.52,.006,False)
    MATERIALS['coping']=masonry('04 · Terracotta coping',(.51,.33,.19),(.65,.47,.28),.29,.12,.004,False)
    MATERIALS['earth']=masonry('05 · Riverbank aggregate',(.18,.16,.11),(.30,.26,.18),1.2,.9,.001,False)
    MATERIALS['grass']=material('06 · Muted riverbank planting',(.10,.13,.055))[0]
    MATERIALS['bark']=material('07 · Plane tree bark',(.16,.12,.075))[0]
    MATERIALS['metal']=material('08 · Aged dark bronze',(.045,.038,.025),.48)[0]
    MATERIALS['leaves']=[material(f'Plane foliage {i}',(.07+i*.018,.11+i*.022,.035+i*.008))[0] for i in range(5)]
    MATERIALS['voussoirs']=[]
    for i in range(9):
        f=.80+i*.045
        m,p=material(f'Radial brick · tone {i+1:02}',(.55*f,.36*f,.19*f))
        n,l=m.node_tree.nodes,m.node_tree.links
        tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=90; tex.inputs['Detail'].default_value=3
        g=n.new('ShaderNodeNewGeometry'); l.new(g.outputs['Position'],tex.inputs['Vector'])
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.35; bump.inputs['Distance'].default_value=.014
        l.new(tex.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs[0],p.inputs['Normal'])
        MATERIALS['voussoirs'].append(m)


def rotated_buffer(b, angle, translation=(0,0,0)):
    co,si=math.cos(angle),math.sin(angle)
    tx,ty,tz=translation
    b.vertices=[(x*co-y*si+tx,x*si+y*co+ty,z+tz) for x,y,z in b.vertices]
    return b


def bridge():
    brick,stone,coping=MATERIALS['brick'],MATERIALS['stone'],MATERIALS['coping']
    pitch,centers=layout(C)
    w,L,deck=C['width'],C['length'],C['deck_height']
    # 33 river openings: the vaults are genuinely open through the full bridge width.
    for i,x in enumerate(centers):
        b=MeshBuffer()
        b.crossed_vault(x,C['lower_opening'],w,C['lower_spring'],C['lower_rise'],deck-.22)
        o=mesh_object(f'River span {i+1:02} · pointed barrel vault',b,[brick],'01 | River vaults')
        o['span_number']=i+1
        o['clear_span_m']=C['lower_opening']
        b=MeshBuffer()
        for side in (-1,1):
            b.arch_ring(x,side*(w/2+.035),C['lower_opening'],C['lower_spring'],C['lower_rise'],.28,.12,40,9,.045)
        mesh_object(f'River span {i+1:02} · radial arch bricks',b,MATERIALS['voussoirs'],'04 | Radial brickwork',.004)
    # Pier cores have a longitudinal passage, rather than obstructing the lower gallery.
    pier_width=pitch-C['lower_opening']
    for i in range(34):
        x=centers[0]-pitch/2+i*pitch
        b=MeshBuffer()
        b.arch_wall(0,0,w,2.05,0,2.75,1.55,deck-.22,pier_width,24)
        mesh_object(f'Pier {i+1:02} · transverse passage',rotated_buffer(b,math.pi/2,(x,0,0)),[brick],'02 | Piers and cutwaters',.018)
        # Dressed stone blocks flank the lower gallery opening.
        b=MeshBuffer()
        for side in (-1,1):
            b.box((x,side*(w/4+.55),.68),(pier_width+.035,w/2-1.1,1.36))
            # Triangular upstream / downstream cutwaters with sloping brick caps.
            y=side*w/2
            a=pier_width/2
            verts=[(x-a,y,0),(x+a,y,0),(x,y+side*1.55,0),
                   (x-a,y,1.40),(x+a,y,1.40),(x,y+side*1.55,1.40)]
            faces=[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
            if side<0: faces=[tuple(reversed(f)) for f in faces]
            b.poly(verts,faces)
        mesh_object(f'Pier {i+1:02} · limestone plinth',b,[stone],'02 | Piers and cutwaters',.018)
        b=MeshBuffer()
        for side in (-1,1):
            y=side*w/2; a=pier_width/2
            verts=[(x-a,y,1.4),(x+a,y,1.4),(x,y+side*1.55,1.4),
                   (x-a*.78,y,3.75),(x+a*.78,y,3.75)]
            faces=[(0,2,1),(0,1,4,3),(0,3,2),(1,2,4),(2,3,4)]
            if side<0: faces=[tuple(reversed(f)) for f in faces]
            b.poly(verts,faces)
        mesh_object(f'Pier {i+1:02} · weathered cutwater shoulder',b,[brick],'02 | Piers and cutwaters',.012)
    box('Lower longitudinal footway',(0,0,1.12),(L-10,1.9,.20),stone,'03 | Promenades',.025)
    box('Central pedestrian deck',(0,0,deck-.12),(L,9.3,.24),MATERIALS['paving'],'03 | Promenades',.02)
    for side in (-1,1):
        # Continuous raised edge platforms, cornices, and benches.
        box('Raised side promenade',(0,side*5.65,deck+.02),(L,2.5,.42),stone,'03 | Promenades',.018)
        box('Seating ledge along central promenade',(0,side*4.51,deck+.20),(L,.44,.36),stone,'03 | Promenades',.025)
        box('String course above river arches',(0,side*(w/2+.045),deck-.28),(L,.25,.25),coping,'05 | Cornices and parapets',.015)
        upitch=pitch/3
        for j in range(99):
            if j in (48,49,50): continue
            x=(j-49)*upitch
            # Exterior arcade and its courtyard-facing arch frame.
            for face,y in [('river',side*(w/2-.23)),('deck',side*4.83)]:
                b=MeshBuffer()
                b.arch_wall(x,y,upitch,C['upper_opening'],deck+.23,C['upper_spring'],C['upper_rise'],C['roof_height'],.46,24)
                mesh_object(f'{side:+} upper {j+1:03} · {face} arch',b,[brick],'06 | Upper arcades')
                b=MeshBuffer()
                b.arch_ring(x,y+side*(.24 if face=='river' else -.24),C['upper_opening'],C['upper_spring'],C['upper_rise'],.115,.07,24,9,.055)
                mesh_object(f'{side:+} upper {j+1:03} · {face} voussoirs',b,MATERIALS['voussoirs'],'04 | Radial brickwork',.003)
            # Deep inner niche wall with the smaller pedestrian access opening seen from deck.
            b=MeshBuffer()
            b.arch_wall(x,side*5.10,C['upper_opening'],.92,deck+.23,deck+1.88,.36,C['roof_height'],.18,12)
            mesh_object(f'{side:+} upper {j+1:03} · niche and low portal',b,[brick],'07 | Gallery interiors')
            # Shallow vault above each bay; real curved underside across the gallery width.
            b=MeshBuffer()
            b.arch_wall(x,side*5.75,C['upper_opening'],C['upper_opening'],deck+.23,C['upper_spring'],C['upper_rise'],C['roof_height'],1.85,24)
            mesh_object(f'{side:+} upper {j+1:03} · gallery vault',b,[brick],'07 | Gallery interiors')
            # Fine recessed rectangular surrounds and a thin brick capping course.
            b=MeshBuffer()
            for edge in (-1,1):
                b.box((x+edge*(upitch/2-.12),side*(w/2+.018),9.28),(.07,.065,5.36))
            b.box((x,side*(w/2+.018),11.90),(upitch-.2,.065,.075))
            mesh_object(f'{side:+} upper {j+1:03} · panel moulding',b,[coping],'05 | Cornices and parapets',.006)
        # Central projecting pavilion; wider and taller than the surrounding arcade.
        for face,y in [('river',side*(w/2+.34)),('deck',side*4.83)]:
            b=MeshBuffer()
            b.arch_wall(0,y,pitch,3.4,deck+.23,9.55,2.75,12.85,.68,32)
            mesh_object(f'{side:+} central pavilion · {face}',b,[brick],'08 | Central pavilions',.012)
            b=MeshBuffer(); b.arch_ring(0,y+side*.35,3.4,9.55,2.75,.18,.09,36,9)
            mesh_object(f'{side:+} central pavilion · arch ring {face}',b,MATERIALS['voussoirs'],'04 | Radial brickwork',.004)
        box('Pavilion balcony base',(0,side*6.05,deck+.1),(pitch,3.3,.46),stone,'08 | Central pavilions',.02)
        box('Pavilion roof',(0,side*6.05,12.81),(pitch+.2,3.35,.25),coping,'08 | Central pavilions',.012)
        # Narrow blind niches in the central pavilion side piers.
        b=MeshBuffer()
        for x in (-3.1,3.1):
            b.arch_ring(x,side*(w/2+.70),.72,9.5,1.55,.085,.065,24,9)
            for edge in (-1,1): b.box((x+edge*.40,side*(w/2+.70),8.28),(.08,.065,2.44))
        mesh_object('Central pavilion ornamental niches',b,MATERIALS['voussoirs'],'08 | Central pavilions',.003)
        # Roof slabs only cover the side galleries; the broad central deck remains open.
        box('Arcade roof',(0,side*5.75,12.10),(L,2.52,.20),brick,'05 | Cornices and parapets',.01)
        box('Roof edge coping',(0,side*(w/2-.12),12.23),(L,.40,.20),coping,'05 | Cornices and parapets',.012)
        box('Inner roof edge',(0,side*4.70,12.20),(L,.35,.20),coping,'05 | Cornices and parapets',.012)
    # End abutments continue the pedestrian deck into the riverside approaches.
    for side in (-1,1):
        x=side*(L/2-2.5)
        box('Solid end abutment',(x,0,3.10),(5,w,6.2),brick,'09 | Abutments',.04)
        for edge in (-1,1):
            b=MeshBuffer()
            b.arch_wall(x,edge*5.75,5,2.18,deck+.23,9.35,2.25,12.05,2.5,24)
            mesh_object('Terminal arcade bay',b,[brick],'09 | Abutments',.012)


def water_material():
    m,p=material('Zayandeh Rud · animated flowing water',(.045,.095,.085),.23)
    p.inputs['Metallic'].default_value=0
    p.inputs['IOR'].default_value=1.333
    p.inputs['Transmission Weight'].default_value=.68
    n,l=m.node_tree.nodes,m.node_tree.links
    tex=n.new('ShaderNodeTexCoord')
    mapping=n.new('ShaderNodeMapping'); mapping.name='Flow · animated river current'
    l.new(tex.outputs['Object'],mapping.inputs[0])
    mapping.inputs['Scale'].default_value=(.45,1.8,1)
    for frame,y in [(1,0),(241,-9)]:
        mapping.inputs['Location'].default_value=(0,y,0)
        mapping.inputs['Location'].keyframe_insert(data_path='default_value',frame=frame)
    noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=2.7; noise.inputs['Detail'].default_value=3
    l.new(mapping.outputs[0],noise.inputs[0])
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.65; bump.inputs['Distance'].default_value=.11
    l.new(noise.outputs['Fac'],bump.inputs['Height'])
    fine=n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=19; fine.inputs['Detail'].default_value=2
    l.new(mapping.outputs[0],fine.inputs[0])
    b2=n.new('ShaderNodeBump'); b2.inputs['Strength'].default_value=.20; b2.inputs['Distance'].default_value=.014
    l.new(fine.outputs['Fac'],b2.inputs['Height']); l.new(bump.outputs[0],b2.inputs['Normal']); l.new(b2.outputs[0],p.inputs['Normal'])
    absorb=n.new('ShaderNodeVolumeAbsorption'); absorb.inputs['Color'].default_value=(.29,.44,.34,1); absorb.inputs['Density'].default_value=.13
    l.new(absorb.outputs[0],n.get('Material Output').inputs['Volume'])
    return m


def tree(name,x,y,height):
    # Geometry-only branching plane trees. Each crown uses a linked leaf-cluster mesh.
    bark=MATERIALS['bark']
    trunk=MeshBuffer(); trunk.box((x,y,3.8+height*.36),(.31,.34,height*.72))
    mesh_object(name+' · trunk',trunk,[bark],'12 | Riverside trees',.10)
    verts,faces=[],[]
    for k in range(7):
        a=RNG.random()*math.tau
        center=Vector((x+math.cos(a)*height*.20,y+math.sin(a)*height*.20,3.8+height*(.60+RNG.random()*.20)))
        start=Vector((x,y,3.8+height*.40))
        direction=center-start
        bpy.ops.mesh.primitive_cone_add(vertices=7,radius1=.14,radius2=.05,depth=direction.length,location=(start+center)/2)
        obj=bpy.context.object; obj.name=name+' · branch'; obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        for c in list(obj.users_collection): c.objects.unlink(obj)
        collection('12 | Riverside trees').objects.link(obj); obj.data.materials.append(bark)
        # Dense leaf cards distributed inside crown ellipsoids, with no spherical shells.
        for j in range(260):
            theta=RNG.random()*math.tau; u=RNG.uniform(-1,1); r=RNG.random()**(1/3)*height*.24
            radial=math.sqrt(1-u*u)
            p=center+Vector((r*radial*math.cos(theta),r*radial*math.sin(theta),r*u*.85))
            a1=Vector((RNG.uniform(.08,.18),RNG.uniform(-.12,.12),RNG.uniform(-.08,.08)))
            a2=Vector((RNG.uniform(-.06,.06),RNG.uniform(.06,.14),RNG.uniform(-.10,.10)))
            off=len(verts)
            verts += [tuple(p-a1-a2),tuple(p+a1-a2),tuple(p+a1+a2),tuple(p-a1+a2)]
            faces.append((off,off+1,off+2,off+3))
    b=MeshBuffer(); b.poly(verts,faces)
    b.materials=[RNG.randrange(5) for _ in b.faces]
    mesh_object(name+' · leaves',b,MATERIALS['leaves'],'12 | Riverside trees')


def environment():
    L=C['length']
    box('Riverbed',(0,0,-1.35),(L+800,1600,1.1),MATERIALS['earth'],'10 | River')
    # Fine surface mesh carries subtle long waves; shader adds the smaller ripples.
    b=MeshBuffer(); nx,ny=240,180
    vertices=[]
    for j in range(ny+1):
        y=-550+j*1100/ny
        for i in range(nx+1):
            x=-L/2-5+i*(L+10)/nx
            z=C['water_level']+.018*math.sin(y*1.3+x*.27)+.009*math.sin(x*2.1-y*.8)
            vertices.append((x,y,z))
    faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; faces.append((a,a+1,a+nx+2,a+nx+1))
    b.poly(vertices,faces)
    o=mesh_object('Flowing river · surface',b,[water_material()],'10 | River')
    for p in o.data.polygons: p.use_smooth=True
    for side in (-1,1):
        x=side*(L/2+48)
        box('Riverbank terrain',(x,0,1.1),(92,1100,4.0),MATERIALS['earth'],'11 | Riverbanks')
        box('Riverbank promenade',(side*(L/2+7),0,3.23),(14,750,.24),MATERIALS['paving'],'11 | Riverbanks',.04)
        box('Riverside retaining wall',(side*(L/2+.1),0,1.4),(1.4,850,3.6),MATERIALS['stone'],'11 | Riverbanks',.04)
        box('Riverside lawn',(side*(L/2+38),0,3.18),(45,850,.10),MATERIALS['grass'],'11 | Riverbanks')
        # Walkable ramps from bank grade up to the bridge deck.
        b=MeshBuffer()
        x0=side*L/2; x1=side*(L/2+31)
        verts=[(x0,-4.4,3.3),(x1,-4.4,3.3),(x1,4.4,3.3),(x0,4.4,3.3),
               (x0,-4.4,6.65),(x1,-4.4,3.45),(x1,4.4,3.45),(x0,4.4,6.65)]
        faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        if side<0: faces=[tuple(reversed(f)) for f in faces]
        b.poly(verts,faces)
        mesh_object('Approach ramp · inferred site geometry',b,[MATERIALS['paving']],'11 | Riverbanks',.025)
        for j in range(22):
            y=(j-10.5)*17+RNG.uniform(-2,2)
            if abs(y)<13: continue
            tree(f'Plane tree {side:+}/{j:02}',side*(L/2+22+RNG.uniform(0,22)),y,RNG.uniform(7,11))
        # Simple modern lights on riverbanks, not invented towers on the monument.
        b=MeshBuffer()
        for y in range(-180,181,24):
            b.box((side*(L/2+6),y,5.0),(.09,.09,3.6))
            b.box((side*(L/2+6),y,6.78),(.58,.30,.10))
        mesh_object('Riverside lamp posts',b,[MATERIALS['metal']],'11 | Riverbanks',.02)


def camera(name,position,target,lens=45):
    data=bpy.data.cameras.new(name); obj=bpy.data.objects.new(name,data)
    collection('14 | Cameras').objects.link(obj)
    obj.location=position; obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens; data.clip_end=2500; data.clip_start=.08
    return obj


def lighting():
    scene=bpy.context.scene
    world=bpy.data.worlds.new('Isfahan · late afternoon sky'); world.use_nodes=True; scene.world=world
    n,l=world.node_tree.nodes,world.node_tree.links
    sky=n.new('ShaderNodeTexSky'); sky.sky_type='NISHITA'
    sky.sun_elevation=math.radians(17); sky.sun_rotation=math.radians(220)
    sky.altitude=1570; sky.air_density=1.1; sky.dust_density=.8
    sky.sun_disc=True; sky.sun_size=math.radians(.8)
    l.new(sky.outputs['Color'],n.get('Background').inputs['Color'])
    n.get('Background').inputs['Strength'].default_value=.08
    # Independent area fill improves visibility beneath the brick arcades.
    data=bpy.data.lights.new('Soft western sky fill','AREA'); data.energy=14000; data.shape='DISK'; data.size=100
    obj=bpy.data.objects.new(data.name,data); collection('13 | Lighting').objects.link(obj)
    obj.location=(0,-35,65)
    # Architectural fixtures for optional dusk lighting; daylight renders keep them subtle.
    pitch,centers=layout(C)
    for x in centers:
        for side in (-1,1):
            d=bpy.data.lights.new('Warm concealed arch wash','AREA')
            d.energy=45; d.color=(1,.59,.24); d.shape='DISK'; d.size=1.5
            o=bpy.data.objects.new(d.name,d); collection('13 | Lighting').objects.link(o)
            o.location=(x,side*5.9,2.4); o.rotation_euler=(math.pi,0,0)


def setup_scene(quality):
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES'
    scene.cycles.samples={'preview':32,'standard':96,'final':256}[quality]
    scene.cycles.use_denoising=True
    scene.cycles.adaptive_threshold=.025 if quality=='preview' else .012
    scene.cycles.max_bounces=8
    scene.cycles.transmission_bounces=6
    scene.cycles.transparent_max_bounces=8
    scene.render.resolution_x={'preview':1440,'standard':2560,'final':3840}[quality]
    scene.render.resolution_y=round(scene.render.resolution_x*.5625)
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.35
    scene.render.fps=24; scene.frame_end=240
    scene['Project']='Si-o-se-pol | present-day visual reconstruction'
    scene['Fidelity']='Reference-based parametric model, not a measured survey or live instrumented twin.'
    scene['Coordinates']='Local metres: X bridge axis, Y river flow, Z up. Not georeferenced.'
    scene['Water']='Art-directed flowing river; animation of surface shading, not a hydraulic simulation.'
    scene['Configuration']=json.dumps(C)
    # Metal support varies by host; CPU is the portable default.
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='METAL'; prefs.get_devices()
        found=False
        for d in prefs.devices:
            d.use=d.type=='METAL'; found=found or d.use
        if found: scene.cycles.device='GPU'
    except Exception:
        scene.cycles.device='CPU'
    return scene


def validate_scene():
    spans=[o for o in bpy.data.objects if 'span_number' in o]
    assert sorted(o['span_number'] for o in spans)==list(range(1,34)), 'Missing/duplicate river spans'
    assert len([o for o in bpy.data.objects if o.type=='CAMERA'])>=5
    for o in bpy.data.objects:
        if o.type=='MESH':
            assert all(math.isfinite(c) for v in o.data.vertices for c in v.co),o.name
            assert o.data.uv_layers, o.name+' lacks UVs'
    assert bpy.context.scene.unit_settings.scale_length==1
    report={
        'river_spans':len(spans),'length_m':C['length'],'nominal_width_m':C['width'],
        'objects':len(bpy.data.objects),
        'mesh_vertices':sum(len(o.data.vertices) for o in bpy.data.objects if o.type=='MESH'),
        'mesh_faces':sum(len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'),
        'cameras':[o.name for o in bpy.data.objects if o.type=='CAMERA'],
        'blender':bpy.app.version_string,'render_device':bpy.context.scene.cycles.device,
        'saved_scene_default_device':'CPU',
        'checks':'33 numbered spans; finite mesh vertices; UVs; metric units; cameras',
        'accuracy':'Not survey certified. See docs/accuracy.md.'}
    (ROOT/'output/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SCENE_VALIDATION',json.dumps(report),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--quality',choices=['preview','standard','final'],default='standard')
    parser.add_argument('--render',default='',help='Comma separated: hero,elevation,detail,deck,gallery,aerial')
    parser.add_argument('--output',default=str(ROOT/'output/si_o_se_pol.blend'))
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    t=time.time()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if not c.objects: bpy.data.collections.remove(c)
    setup_materials(); print('Materials ready',flush=True)
    bridge(); print('Bridge geometry ready',flush=True)
    environment(); print('Environment ready',flush=True)
    lighting()
    cameras={
        'hero':camera('01 · River panorama',(-102,-92,10),(-26,0,5.7),44),
        'elevation':camera('02 · Complete west elevation',(0,-430,15),(0,0,5),46),
        'detail':camera('03 · Masonry and cutwater',(-33,-43,8),(-13,0,6.2),48),
        'deck':camera('04 · Upper promenade',(-119,-1.8,8.3),(-65,0,8.6),28),
        'gallery':camera('05 · Lower longitudinal gallery',(-125,0,2.65),(-65,0,2.65),25),
        'aerial':camera('06 · Architectural overview',(-230,-300,220),(0,0,3),45)
    }
    scene=setup_scene(args.quality); scene.camera=cameras['hero']
    scene.frame_set(1)
    # A named datum holds project metadata without changing the model origin.
    datum=bpy.data.objects.new('PROJECT DATUM · local metre coordinates',None)
    collection('00 | Project metadata').objects.link(datum)
    datum['latitude_reference_only']=C['reference_latitude']; datum['longitude_reference_only']=C['reference_longitude']
    for name in ('README.md','docs/accuracy.md'):
        path=ROOT/name
        if path.exists(): bpy.data.texts.load(str(path))
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.clip_end=2500
                area.spaces.active.shading.color_type='MATERIAL'
                area.spaces.active.shading.show_cavity=True
                area.spaces.active.region_3d.view_perspective='CAMERA'
    bpy.ops.object.select_all(action='DESELECT')
    validate_scene()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    # Compute-device preferences live outside .blend files. Keep the delivered file
    # portable, while this process may still use an available GPU for its renders.
    render_device=scene.cycles.device
    scene.cycles.device='CPU'
    bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    scene.cycles.device=render_device
    print(f'BUILD_COMPLETE {time.time()-t:.1f}s {out}',flush=True)
    for name in filter(None,args.render.split(',')):
        if name not in cameras: raise ValueError(f'Unknown camera {name}')
        scene.camera=cameras[name]
        scene.render.filepath=str(ROOT/'renders'/f'{name}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDER_COMPLETE',name,flush=True)


if __name__=='__main__': main()
