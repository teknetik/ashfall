"""Derive a reviewed near mesh from detailed textured Meshy source in Blender.
The source FBX is never modified; UVs and all full texture maps are retained.
"""
import bpy,json,shutil,random,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('/home/teknetik/code/ao2');F=globals().get('RUNTIME_FAMILY','trash-v2');TARGET=int(globals().get('RUNTIME_TRIANGLES',180000))
SRC=R/'meshy/ground-detail-20260910'/F;O=R/'meshy/ground-detail-20260910'/(F+'-runtime')
assert not (O/'model.fbx').exists(),'Preserve previous runtime derivative';O.mkdir(exist_ok=True)
S=bpy.data.scenes.new(F+' reviewed near authoring');bpy.context.window.scene=S
before=set(S.objects);bpy.ops.import_scene.fbx(filepath=str(SRC/'model.fbx'))
obs=[o for o in S.objects if o not in before and o.type=='MESH'];records=[]
for ob in obs:
 ob.data.calc_loop_triangles();count=len(ob.data.loop_triangles);ratio=min(1,TARGET/count)
 # Deterministic surface samples are retained only for geometric error reporting.
 rng=random.Random(910215);samples=[ob.data.vertices[rng.randrange(len(ob.data.vertices))].co.copy() for _ in range(8000)]
 bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Near source silhouette reduction; original retained','DECIMATE');mod.decimate_type='COLLAPSE';mod.ratio=ratio;mod.use_collapse_triangulate=True
 bpy.ops.object.modifier_apply(modifier=mod.name);ob.data.calc_loop_triangles()
 tree=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(t.vertices) for t in ob.data.loop_triangles],all_triangles=True)
 errors=sorted(tree.find_nearest(p)[3] for p in samples)
 records.append(dict(sourceTriangles=count,nearTriangles=len(ob.data.loop_triangles),ratio=ratio,uvLayers=len(ob.data.uv_layers),sourceToNearVertexDistanceSourceUnits=dict(samples=len(errors),p50=errors[len(errors)//2],p95=errors[int(len(errors)*.95)],max=errors[-1]),sourceNormalPolicy='Original smooth surface and UVs retained through Blender modifier; Mikk tangents recomputed on Unity import'))
for ob in bpy.context.selected_objects:ob.select_set(False)
for ob in obs:ob.select_set(True)
bpy.context.view_layer.objects.active=obs[0]
bpy.ops.export_scene.fbx(filepath=str(O/'model.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,path_mode='AUTO')
shutil.copytree(SRC/'model_textures',O/'model_textures')
bpy.data.libraries.write(str(O/'near-source.blend'),{S},fake_user=True)
(O/'runtime-manifest.json').write_text(json.dumps(dict(source=str(SRC.relative_to(R)),sourceRetained=True,method='Blender collapse on textured detailed source, not Meshy reduced v1',records=records,fullMapsRetained=True,visualAcceptance=False,requires='Matched source versus near renders and native player-height moving review'),indent=2))
print(json.dumps(records))
