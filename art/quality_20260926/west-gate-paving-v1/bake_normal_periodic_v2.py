"""Live Blender MCP: bake tangent normals from the metre-scaled authored height.

Uses a separate6m plane/scene; retains the original default scene. Save the whole
file as a copy. Do not use libraries.write after the recorded native save crash.
"""
from pathlib import Path
import hashlib
import json
import time
import bpy
import numpy as np

OUT=Path('/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1/periodic-v2')
N=1254
EXTENT=6.0
HEIGHT_SCALE=.016
normal_path=OUT/'Normal-OpenGL.png'
blend_path=OUT/'Paving-authoring.blend'
if normal_path.exists() or blend_path.exists():
    raise RuntimeError('Preserve existing bake; use a new version for changes.')
original_scene=bpy.context.scene
original_objects=[(o.name,o.as_pointer()) for o in original_scene.objects]
source_scene=bpy.data.scenes.get('Ward Paving V2 source maps')
if source_scene is None:
    raise RuntimeError('Run the authored source-map recipe first.')
source_scene.name='Ward Paving V2 physical-height source'
try:
    source_scene.render.engine='CYCLES'
except TypeError as error:
    raise RuntimeError('Installed Blender does not support the requested Cycles bake: '+str(error))
source_scene.cycles.device='CPU'
source_scene.cycles.samples=1
source_scene.render.threads_mode='FIXED'
source_scene.render.threads=4
source_scene.view_settings.view_transform='Raw'
source_scene.view_settings.look='None'
source_scene.view_settings.exposure=0
source_scene.view_settings.gamma=1

mesh=bpy.data.meshes.new('WardPavingV1_6metre_plane')
mesh.from_pydata([(-3,-3,0),(3,-3,0),(3,3,0),(-3,3,0)],[],[(0,1,2,3)])
mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for loop,xy in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):
    loop.uv=xy
plane=bpy.data.objects.new('WardPavingV1 height-to-normal bake surface 6m',mesh)
source_scene.collection.objects.link(plane)
material=bpy.data.materials.new('WardPavingV1 physical-height source material')
material.use_nodes=True
nodes=material.node_tree.nodes
nodes.clear()
links=material.node_tree.links
output=nodes.new('ShaderNodeOutputMaterial')
principled=nodes.new('ShaderNodeBsdfPrincipled')
links.new(principled.outputs['BSDF'],output.inputs['Surface'])

def file_texture(name,file,color_data):
    image=bpy.data.images.load(str(OUT/file),check_existing=False)
    image.name=name
    image.colorspace_settings.name='Non-Color' if color_data else 'sRGB'
    image.pack()
    node=nodes.new('ShaderNodeTexImage')
    node.image=image
    return node

albedo=file_texture('WardPavingV1 preserved source albedo','Albedo-preserved.png',False)
roughness=file_texture('WardPavingV1 authored roughness','Roughness.png',True)
height=file_texture('WardPavingV1 normalized physical height','Height-normalized.png',True)
links.new(albedo.outputs['Color'],principled.inputs['Base Color'])
links.new(roughness.outputs['Color'],principled.inputs['Roughness'])
principled.inputs['Metallic'].default_value=0
bump=nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value=1
bump.inputs['Distance'].default_value=HEIGHT_SCALE
links.new(height.outputs['Color'],bump.inputs['Height'])
links.new(bump.outputs['Normal'],principled.inputs['Normal'])
plane.data.materials.append(material)

normal=bpy.data.images.new('WardPavingV1 Cycles tangent normal',width=N,height=N,alpha=False,float_buffer=True)
normal.colorspace_settings.name='Non-Color'
target=nodes.new('ShaderNodeTexImage')
target.image=normal
for node in nodes:
    node.select=False
target.select=True
nodes.active=target

bake_start=time.monotonic()
try:
    bpy.context.window.scene=source_scene
    for ob in source_scene.objects:
        ob.select_set(False)
    plane.select_set(True)
    source_scene.view_layers[0].objects.active=plane
    bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',
                       normal_g='POS_Y',normal_b='POS_Z',use_selected_to_active=False,
                       use_clear=True,margin=0,margin_type='EXTEND')
    source_scene.render.image_settings.file_format='PNG'
    source_scene.render.image_settings.color_mode='RGB'
    source_scene.render.image_settings.color_depth='16'
    normal.save_render(str(normal_path),scene=source_scene)
    normal.pack()
    values=np.empty(N*N*4,np.float32)
    normal.pixels.foreach_get(values)
    rgb=values.reshape(N,N,4)[:,:,:3]
    n=rgb*2-1
    n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-8)
    angles=np.degrees(np.arccos(np.clip(n[:,:,2],-1,1)))
    # The whole-file copy contains both the recovered default scene and the
    # complete plane/material/bake target with packed authoring maps.
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path),copy=True,check_existing=False)
    report=dict(status='Cycles normal bake complete; Unity audition pending',
                sourceScene=source_scene.name,engine=source_scene.render.engine,device=source_scene.cycles.device,
                samples=source_scene.cycles.samples,threads=source_scene.render.threads,
                resolution=[N,N],planeMetres=[EXTENT,EXTENT],
                heightEncoding='height_metres = normalized*.016 - .008',
                bumpDistanceMetres=HEIGHT_SCALE,bumpStrength=1,
                bakeType='NORMAL',normalSpace='TANGENT',swizzle=['POS_X','POS_Y','POS_Z'],
                bakeMarginPixels=0,imageDepth=16,saveViewTransform='Raw',
                normalAnglePercentilesDegrees=np.percentile(angles,[0,50,90,95,99,100]).tolist(),
                elapsedSeconds=time.monotonic()-bake_start,
                normalSha256=hashlib.sha256(normal_path.read_bytes()).hexdigest(),
                blendSha256=hashlib.sha256(blend_path.read_bytes()).hexdigest(),
                blendBytes=blend_path.stat().st_size,
                originalObjectsUnchanged=original_objects==[(o.name,o.as_pointer()) for o in original_scene.objects])
    (OUT/'normal-bake.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
finally:
    bpy.context.window.scene=original_scene
