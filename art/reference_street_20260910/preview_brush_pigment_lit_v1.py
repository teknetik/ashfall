"""STAGED: execute only through the exclusive live Blender MCP operator.

ACTION='AUTHOR' creates an isolated source scene/library. ACTION='RENDER' renders
one of VIEW='phrase'/'close'/'grazing', MODE='before'/'after'/'albedo'. Geometry,
placement and the full original scenes remain untouched; no Unity export.
"""
from pathlib import Path
import hashlib,json,math
import bpy
import numpy as np
from mathutils import Vector

R=Path('/home/teknetik/code/ao2');A=R/'art/reference_street_20260910'
O=A/'brush-pigment-lit-v1';C=json.loads((O/'installer-contract.json').read_text())
SCENE='Factory brush pigment Lit v1 source audition'
ACTION=globals().get('ACTION','AUTHOR');VIEW=globals().get('VIEW','phrase');MODE=globals().get('MODE','after')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/C['sourceMeshExport'])==C['sourceMeshSha256']
for row in C['packedMaps']:assert sha(O/row['file'])==row['sha256']
for row in C['sourceMapRecords']:assert sha(R/row['file'])==row['sha256']
assert sha(R/C['previewSubstrate']['file'])==C['previewSubstrate']['sha256']
original_scene=bpy.context.window.scene
geometry_proof=[]

def image_node(m,path,space,uv):
    im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name=space
    t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=im;t.extension='REPEAT';t.interpolation='Linear'
    m.node_tree.links.new(uv,t.inputs['Vector']);return t

def uvmap(m,scale):
    n=m.node_tree.nodes;l=m.node_tree.links;u=n.new('ShaderNodeUVMap');u.uv_map='UV0 retained'
    v=n.new('ShaderNodeVectorMath');v.operation='SCALE';v.inputs[3].default_value=scale;l.new(u.outputs[0],v.inputs[0]);return v.outputs[0]

def pigment():
    m=bpy.data.materials.new('Brush pigment v1 exact packed channels');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n['Principled BSDF'];out=n['Material Output'];uv=uvmap(m,2)
    color=image_node(m,O/'BaseRGBA.png','sRGB',uv);packed=image_node(m,O/'MetalSmooth.png','Non-Color',uv)
    l.new(color.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Metallic'].default_value=0
    complement=n.new('ShaderNodeMath');complement.operation='SUBTRACT';complement.inputs[0].default_value=1;l.new(packed.outputs['Alpha'],complement.inputs[1]);l.new(complement.outputs[0],bs.inputs['Roughness'])
    cutoff=n.new('ShaderNodeMath');cutoff.operation='GREATER_THAN';cutoff.inputs[1].default_value=C['cutoff'];l.new(color.outputs['Alpha'],cutoff.inputs[0])
    transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.name='Pigment alpha-clipped PBR';l.new(cutoff.outputs[0],mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(bs.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
    emission=n.new('ShaderNodeEmission');l.new(color.outputs['Color'],emission.inputs['Color']);emix=n.new('ShaderNodeMixShader');emix.name='Pigment alpha-clipped albedo';l.new(cutoff.outputs[0],emix.inputs[0]);l.new(transparent.outputs[0],emix.inputs[1]);l.new(emission.outputs[0],emix.inputs[2])
    return m

def shutter_material():
    m=bpy.data.materials.new('Brush audition current shutter context');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n['Principled BSDF'];uv=uvmap(m,1);folder=R/C['previewSubstrate']['materialFolder']
    maps={k:image_node(m,folder/(k+'.png'),'sRGB' if k=='BaseColor' else 'Non-Color',uv)for k in ('BaseColor','Normal','Roughness','Metallic')}
    l.new(maps['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
    for ch in ('Roughness','Metallic'):
        sep=n.new('ShaderNodeSeparateColor');l.new(maps[ch].outputs['Color'],sep.inputs[0]);l.new(sep.outputs[0],bs.inputs[ch])
    norm=n.new('ShaderNodeNormalMap');norm.uv_map='UV0 retained';l.new(maps['Normal'].outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],bs.inputs['Normal'])
    em=n.new('ShaderNodeEmission');em.name='Context albedo';l.new(maps['BaseColor'].outputs['Color'],em.inputs['Color']);return m

def meshpart(scene,p,m,letter=False):
    pos=np.asarray(p['positions']);converted=pos[:,[0,2,1]].copy();converted[:,1]*=-1
    faces=np.asarray(p['indices']).reshape(-1,3);mesh=bpy.data.meshes.new(p.get('name',p.get('path'))+' exact source');mesh.from_pydata(converted.tolist(),[],faces.tolist());mesh.update()
    normals=np.asarray(p['normals'])[:,[0,2,1]].copy();normals[:,1]*=-1
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set_from_vertices(normals.tolist());mesh.update()
    uv=mesh.uv_layers.new(name='UV0 retained');original=np.asarray(p['uv'],dtype=np.float32);uv.data.foreach_set('uv',original[faces.ravel()].ravel())
    check=np.empty((len(mesh.loops),2),np.float32);uv.data.foreach_get('uv',check.ravel());assert np.array_equal(check,original[faces.ravel()])
    back=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',back.ravel());assert np.max(abs(back-converted))<.000002
    tris=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',tris);assert np.array_equal(tris,faces.ravel())
    corner=np.empty((len(mesh.loops),3),np.float32);mesh.corner_normals.foreach_get('vector',corner.ravel());expected=normals[faces.ravel()];expected/=np.linalg.norm(expected,axis=1,keepdims=True)
    mindot=float(np.min(np.sum(corner*expected,axis=1)));normalerror=float(np.max(abs(corner-expected)));assert mindot>.99999 and normalerror<.003
    geometry_proof.append({'source':p.get('sourcePath',p.get('path')),'positionsMaxErrorM':float(np.max(abs(back-converted))),'indicesAndUVExactlyEqual':True,'normalMinDot':mindot,'normalMaxComponentError':normalerror})
    obj=bpy.data.objects.new(p.get('name',p.get('path')),mesh);scene.collection.objects.link(obj);mesh.materials.append(m)
    obj['originalSourcePath']=p.get('sourcePath',p.get('path'));obj['previewOnlyDoNotExport']=True
    if letter:obj.visible_shadow=False;obj['phrase']=p['text'];obj['brushTarget']=True
    return obj

try:
    if ACTION=='AUTHOR':
        assert SCENE not in bpy.data.scenes and not (O/'preview-source.blend').exists()
        S=bpy.data.scenes.new(SCENE);bpy.context.window.scene=S;S.unit_settings.system='METRIC';S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=False;S.render.threads_mode='FIXED';S.render.threads=8
        S.view_settings.view_transform='Standard';S.view_settings.look='None';S.view_settings.exposure=0;S.view_settings.gamma=1
        S.world=bpy.data.worlds.new(SCENE+' neutral world');S.world.use_nodes=True;S.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1);S.world.node_tree.nodes['Background'].inputs[1].default_value=.4
        before=bpy.data.materials.new('Factory brush retained plain paint baseline');before.use_nodes=True;bs=before.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.73,.66,.53,1);bs.inputs['Roughness'].default_value=.92;bs.inputs['Metallic'].default_value=0
        after=pigment();substrate=shutter_material()
        parts=json.loads((R/C['sourceMeshExport']).read_text());letters=[meshpart(S,p,after,True)for p in parts]
        rows=[p for p in json.loads((R/C['previewSubstrate']['file']).read_text())if p['family']=='ShutterSteel'];assert len(rows)==20
        for p in rows:meshpart(S,p,substrate)
        cam=bpy.data.objects.new('Brush audition camera',bpy.data.cameras.new('Brush audition camera'));S.collection.objects.link(cam);S.camera=cam;cam.data.type='ORTHO'
        ld=bpy.data.lights.new('Brush audition soft light','AREA');ld.energy=550;ld.shape='DISK';ld.size=3;lo=bpy.data.objects.new(ld.name,ld);S.collection.objects.link(lo)
        S['beforeMaterial']=before.name;S['afterMaterial']=after.name;S['substrateMaterial']=substrate.name;S['lightObject']=lo.name
        bpy.data.libraries.write(str(O/'preview-source.blend'),{S,before},fake_user=True,path_remap='RELATIVE')
        substratefiles=[R/C['previewSubstrate']['materialFolder']/(k+'.png')for k in ('BaseColor','Normal','Roughness','Metallic')]
        (O/'preview-authoring.json').write_text(json.dumps({'scene':SCENE,'geometrySourceSha256':C['sourceMeshSha256'],'exactTwoLetterMeshes':True,'positionsIndicesUVNormalsPreserved':True,'geometryProof':geometry_proof,'sourceLetterOffsetInFrontOfSlatM':.008999,'geometryOrPlacementChange':False,'noPaintBumpNormalDisplacement':True,'existingLetterShadowCastingOff':True,'substrateHashes':{str(p.relative_to(R)):sha(p)for p in substratefiles},'sourceAccepted':False,'nativeAccepted':False},indent=2)+'\n')
        print(json.dumps({'scene':SCENE,'library':str(O/'preview-source.blend'),'status':'Ready for matched before/after views'}))
    elif ACTION=='RENDER':
        assert VIEW in ('phrase','close','grazing') and MODE in ('before','after','albedo')
        S=bpy.data.scenes.get(SCENE);assert S,'Run AUTHOR or load its saved library first';bpy.context.window.scene=S
        path=O/'previews'/(VIEW+'-'+MODE+'.png');path.parent.mkdir(exist_ok=True);assert not path.exists(),'Keep previous evidence.'
        target=Vector((17.94,9.015,2.18));span=3.18;delta=Vector((-5,0,.10))
        if VIEW=='close':target=Vector((17.94,8.98,2.46));span=1.45
        if VIEW=='grazing':target=Vector((17.94,9.015,2.18));span=2.5;delta=Vector((-2.2,-3.6,.2))
        S.camera.location=target+delta;S.camera.rotation_euler=(target-S.camera.location).to_track_quat('-Z','Y').to_euler();S.camera.data.ortho_scale=span
        light=bpy.data.objects[S['lightObject']];light.location=target+Vector((-3,-3,3));light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
        after=bpy.data.materials[S['afterMaterial']];before=bpy.data.materials[S['beforeMaterial']];n=after.node_tree.nodes;after.node_tree.links.new(n['Pigment alpha-clipped albedo' if MODE=='albedo' else 'Pigment alpha-clipped PBR'].outputs[0],n['Material Output'].inputs['Surface'])
        for obj in S.objects:
            if obj.get('brushTarget'):obj.data.materials[0]=before if MODE=='before' else after
        sub=bpy.data.materials[S['substrateMaterial']];n=sub.node_tree.nodes;sub.node_tree.links.new(n['Context albedo' if MODE=='albedo' else 'Principled BSDF'].outputs[0],n['Material Output'].inputs['Surface'])
        S.render.resolution_x=1920;S.render.resolution_y=1080;S.render.resolution_percentage=100;S.render.image_settings.file_format='PNG';S.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        path.with_suffix('.json').write_text(json.dumps({'view':VIEW,'mode':MODE,'camera':list(S.camera.location),'target':list(target),'orthoHorizontalSpanM':span,'cutoff':C['cutoff'],'sha256':sha(path),'sourceOnly':True,'nativeAccepted':False},indent=2)+'\n')
        print(json.dumps({'render':str(path),'sourceOnly':True}))
    else:raise ValueError(ACTION)
finally:
    bpy.context.window.scene=original_scene
