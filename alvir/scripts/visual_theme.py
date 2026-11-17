"""Apply an explicitly interpretive photo-informed material pass in Blender.

Preserves geometry, assignments, coordinates and cameras. CLI writes a separate
study file, leaving the original render handoff and its frame cache untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT=Path(__file__).resolve().parents[1]


def surface(mat,settings):
    mat.use_nodes=True;n,l=mat.node_tree.nodes,mat.node_tree.links;n.clear()
    output=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled')
    l.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Roughness'].default_value=settings['roughness']
    p.inputs['Metallic'].default_value=settings.get('metallic',0)
    color=settings['color'];mat.diffuse_color=(*color,1)
    geo=n.new('ShaderNodeNewGeometry');position=geo.outputs['Position']
    if 'grain_axis' in settings:
        axis=n.new('ShaderNodeVectorMath');axis.operation='MULTIPLY';axis.inputs[1].default_value=settings['grain_axis']
        l.new(position,axis.inputs[0]);position=axis.outputs['Vector']
    broad=n.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=2.3;broad.inputs['Detail'].default_value=3
    l.new(position,broad.inputs['Vector'])
    palette=n.new('ShaderNodeValToRGB');palette.name='Photo-informed tonal variation'
    palette.color_ramp.elements[0].position=.15;palette.color_ramp.elements[1].position=.85
    palette.color_ramp.elements[0].color=(*(v*.62 for v in color),1)
    palette.color_ramp.elements[1].color=(*(min(.95,v*1.2) for v in color),1)
    l.new(broad.outputs['Fac'],palette.inputs[0]);base=palette.outputs['Color']
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=65;fine.inputs['Detail'].default_value=2
    l.new(position,fine.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.5;bump.inputs['Distance'].default_value=settings['grain']
    l.new(fine.outputs['Fac'],bump.inputs['Height']);normal=bump.outputs['Normal']
    if settings.get('cracks'):
        warp=n.new('ShaderNodeVectorMath');warp.operation='SCALE';warp.inputs['Scale'].default_value=.24
        l.new(broad.outputs['Color'],warp.inputs[0])
        add=n.new('ShaderNodeVectorMath');add.operation='ADD';l.new(position,add.inputs[0]);l.new(warp.outputs['Vector'],add.inputs[1])
        cells=n.new('ShaderNodeTexVoronoi');cells.feature='DISTANCE_TO_EDGE';cells.inputs['Scale'].default_value=3.5
        l.new(add.outputs['Vector'],cells.inputs['Vector'])
        cracks=n.new('ShaderNodeValToRGB');cracks.name='Interpretive fine clay fissures'
        cracks.color_ramp.elements[0].position=.001;cracks.color_ramp.elements[1].position=.009
        cracks.color_ramp.elements[0].color=(.65,.65,.65,1);cracks.color_ramp.elements[1].color=(1,1,1,1)
        l.new(cells.outputs['Distance'],cracks.inputs[0])
        weather=n.new('ShaderNodeValToRGB');weather.name='Patchy fissure coverage'
        weather.color_ramp.elements[0].position=.46;weather.color_ramp.elements[1].position=.68
        l.new(broad.outputs['Fac'],weather.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY'
        l.new(weather.outputs['Color'],mix.inputs[0])
        l.new(base,mix.inputs[1]);l.new(cracks.outputs['Color'],mix.inputs[2]);base=mix.outputs[0]
        height=n.new('ShaderNodeMixRGB');height.inputs[1].default_value=(1,1,1,1)
        l.new(weather.outputs['Color'],height.inputs[0]);l.new(cracks.outputs['Color'],height.inputs[2])
        fissure=n.new('ShaderNodeBump');fissure.inputs['Distance'].default_value=.006;fissure.inputs['Strength'].default_value=.45
        l.new(height.outputs[0],fissure.inputs['Height']);l.new(normal,fissure.inputs['Normal']);normal=fissure.outputs['Normal']
    l.new(base,p.inputs['Base Color']);l.new(normal,p.inputs['Normal'])
    mat['reference_ids']=', '.join(f'alvir-ref-{i:03}' for i in settings.get('refs',[]))
    mat['evidence']='Photo-informed material interpretation; not a registered photo texture or measured surface.'


def apply_theme(scene):
    path=ROOT/'data/visual-theme.json';theme=json.loads(path.read_text());changed=[];unused=[]
    if not bpy.data.materials.get('Rammed earth · weathered clay'):
        raise RuntimeError('This is not the expected Alvir scene.')
    for name,settings in theme['surfaces'].items():
        mat=bpy.data.materials.get(name)
        if mat is None:
            unused.append(name);continue  # Blender drops unused material datablocks when saving.
        surface(mat,settings);changed.append(name)
    brick=bpy.data.materials.get('Exposed ochre brick')
    if brick:
        for node in brick.node_tree.nodes:
            if node.type=='TEX_BRICK':
                for key,color in zip(['Color1','Color2'],theme['brick_colors']):node.inputs[key].default_value=(*color,1)
                node.inputs['Mortar'].default_value=(.22,.185,.135,1)
        brick['reference_ids']='alvir-ref-068, alvir-ref-073, alvir-ref-074';changed.append(brick.name)
    for i in range(5):
        mat=bpy.data.materials.get('Orchard foliage '+str(i))
        if mat:
            color=[v+i*s for v,s in zip(theme['foliage_base'],theme['foliage_step'])]
            surface(mat,dict(color=color,roughness=.78,grain=.001,refs=theme['foliage_refs']))
            mat.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.08
            changed.append(mat.name)
    scene['Visual theme']=theme['name'];scene['Visual theme scope']=theme['scope']
    scene['Visual theme SHA256']=hashlib.sha256(path.read_bytes()).hexdigest()
    scene['Theme materials absent or unused']=json.dumps(unused)
    note=bpy.data.texts.get('READ ME · photo-informed theme') or bpy.data.texts.new('READ ME · photo-informed theme')
    note.clear();note.write(json.dumps(theme,indent=2,ensure_ascii=False))
    return changed


def geometry_fingerprint(scene):
    digest=hashlib.sha256()
    for obj in sorted(scene.objects,key=lambda o:o.name):
        digest.update(obj.name.encode());digest.update(repr(tuple(v for row in obj.matrix_world for v in row)).encode())
        if obj.type=='MESH':
            digest.update(str(len(obj.data.vertices)).encode())
            # Shared meshes need hashing only once; object transforms above remain distinct.
    meshes={o.data.name:o.data for o in scene.objects if o.type=='MESH'}
    for name,mesh in sorted(meshes.items()):
        digest.update(name.encode())
        import array
        coords=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',coords)
        digest.update(coords.tobytes())
    return digest.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'output/alvir_reference_theme.blend')
    p.add_argument('--previews',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    scene=bpy.context.scene;before=geometry_fingerprint(scene);changed=apply_theme(scene)
    after=geometry_fingerprint(scene);assert before==after,'Theme unexpectedly changed geometry'
    for obj in scene.objects:
        if obj.type=='LIGHT' and obj.name.startswith('Walkthrough ·'):obj.hide_render=True
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.view_settings.exposure=-1.6
    assert not [i for i in bpy.data.images if i.source=='FILE' and not i.packed_file]
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()),compress=True)
    report=dict(result='passed',materials_changed=changed,geometry_unchanged=True,geometry_sha256=after,
                all_textures_packed=True,theme_sha256=scene['Visual theme SHA256'],
                output=str(args.output),output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                note='Material study only; no photographic registration or geometry accuracy improvement claimed.')
    (ROOT/'output/visual-theme-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('THEME_APPLIED',json.dumps(report),flush=True)
    if args.previews:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type='METAL';prefs.get_devices()
            for d in prefs.devices:d.use=d.type=='METAL'
            if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
        except Exception:pass
        scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.render.use_stamp=True;scene.render.use_stamp_note=True
        scene.render.use_stamp_labels=False
        scene.render.stamp_note_text='Alvir reference material study | Geometry inferred | Microsoft / OSM / Mapzen / USGS | Sentinel-2 cloudless, EOX, Copernicus 2016 & 2017'
        scene.render.use_motion_blur=False
        for frame,name in [(1032,'theme-street'),(1560,'theme-garden')]:
            scene.frame_set(frame);scene.render.filepath=str(ROOT/'renders'/f'{name}.png')
            bpy.ops.render.render(write_still=True)


if __name__=='__main__':main()
