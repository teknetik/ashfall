import bpy,bmesh,json,math,random,ast
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/building_weathering_20260909';rng=random.Random(909115)
scene=bpy.data.scenes['Ward Field Supply and Finery weathering v3-base'];bpy.context.window.scene=scene
rows=json.loads((O/'unity-source.json').read_text());byname={r['name']:r for r in rows};refs={o['source_path']:o for o in scene.objects if 'source_path'in o}
changed={k:o for k,o in refs.items()if not o.get('reference_only',True)};additions=[o for o in scene.objects if o.type=='MESH'and not o.get('reference_only',True)and 'source_path'not in o]
M={m['unity_key']:m for m in bpy.data.materials if 'unity_key'in m}
for node in ast.parse((O/'author_weathering_v3.py').read_text()).body:
 if isinstance(node,ast.FunctionDef)and node.name in ['B','U','mesh','prism','outline','damage','export']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'retained weathering authoring helper','exec'))
for ob in list(additions):
 if ob.get('material_key')=='Graffiti':additions.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)
for ob in additions:
 key=ob.get('material_key')
 if key in ['Karaveen','Paper','Warden','CrackDust','DryBlood']:
  bm=bmesh.new();bm.from_mesh(ob.data)
  expected=B((0,1,0)if 'threshold fleck'in ob.name else(-1,0,0))
  if sum(f.normal.dot(expected)*f.calc_area()for f in bm.faces)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
  bm.to_mesh(ob.data);bm.free()

# Larger elongated failures along construction edges supplement small local chips.
damage('field_supply Front masonry segment 3 2',(17.87,4.67,-8.83),2.0,.31)
damage('North wall core',(19.35,6.70,-14.2),2.6,.36,(0,0,1),(1,0,0))
damage('Roof parapet end 16.84',(16.715,7.25,-15.3),1.25,.30)

m=bpy.data.materials.new('Wear GraffitiSolid');m.use_nodes=True;m['unity_key']='GraffitiSolid';m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.63,.55,.39,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95;M['GraffitiSolid']=m
font=bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',check_existing=True)
slats=[r for r in rows if 'Rolled shutter slat'in r['name']]
for line,text,y0 in [('upper','THE FACTORIES',2.22),('lower','NEVER SLEEP.',1.71)]:
 chars=[];cursor=0
 for char in text:
  if char==' ':cursor+=.30;continue
  curve=bpy.data.curves.new('Painted '+char,'FONT');curve.body=char;curve.font=font;curve.size=1;curve.resolution_u=4;curve.extrude=0
  ob=bpy.data.objects.new('Brush letter '+char,curve);scene.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.convert(target='MESH');ob=bpy.context.object
  width=max(v.co.x for v in ob.data.vertices)-min(v.co.x for v in ob.data.vertices);chars.append((ob,cursor));cursor+=width+.085
 scale=2.55/cursor
 for ob,offset in chars:
  jitter=rng.uniform(-.016,.016);angle=rng.uniform(-.028,.028)
  for v in ob.data.vertices:
   x=v.co.x;y=v.co.y
   v.co=B((17.936,y0+(x*math.sin(angle)+y*math.cos(angle))*.40+jitter,-7.72-(offset+x*math.cos(angle)-y*math.sin(angle))*scale))
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
  for row in slats:
   a=row['bounds']['min'][1]+.001;b=row['bounds']['max'][1]-.001
   if a>y0+.45 or b<y0-.04:continue
   copy=bm.copy()
   for level,sign in [(a,1),(b,-1)]:
    bmesh.ops.bisect_plane(copy,geom=list(copy.verts)+list(copy.edges)+list(copy.faces),dist=.000001,plane_co=(0,0,level),plane_no=(0,0,sign),clear_inner=True)
   if not copy.faces:copy.free();continue
   bmesh.ops.recalc_face_normals(copy,faces=list(copy.faces))
   for f in copy.faces:
    if f.normal.x>0:f.normal_flip()
   me=bpy.data.meshes.new('Hand painted lettering');copy.to_mesh(me);copy.free();new=bpy.data.objects.new('Factory '+line+' '+str(len(additions)),me);scene.collection.objects.link(new);me.materials.append(m);new['material_key']='GraffitiSolid';new['family']='field_supply';new['reference_only']=False;additions.append(new)
   uv=me.uv_layers.new(name='UV0 paint metres')
   for l in me.loops:uv.data[l.index].uv=(me.vertices[l.vertex_index].co.y,me.vertices[l.vertex_index].co.z)
  bm.free();bpy.data.objects.remove(ob,do_unlink=True)

out=[export(ob,path)for path,ob in changed.items()]+[export(ob)for ob in additions]
for p in out:
 if p['material']=='GraffitiSolid':p['castsShadow']=False
(O/'weathering-meshes-v3.json').write_text(json.dumps(out,separators=(',',':')))
(O/'manifest-v3.json').write_text(json.dumps(dict(blender=bpy.app.version_string,replacements=len(changed),additions=len(additions),triangles=sum(len(p['indices'])//3 for p in out),source='weathering-v3.blend',supersedes='v1 authoring candidate; original source retained',notes=['Corrected outward paper normals','Replaced illegible mask with two authored lettering lines clipped to shutter slats','Added elongated render failures at roof and wall joints']),indent=2))
# Mirror the source review composition to account for Unity's camera handedness.
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');flip=nt.nodes.new('CompositorNodeFlip');flip.axis='X';comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],flip.inputs['Image']);nt.links.new(flip.outputs['Image'],comp.inputs['Image'])
cam=scene.camera;cam.location=B((4,7,-4));cam.rotation_euler=(B((18.5,3.6,-13))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=46
bpy.ops.wm.save_as_mainfile(filepath=str(O/'weathering-v3.blend'));scene.render.filepath=str(O/'source-review-v3.png')
print('Weathering v3 saved: '+str(len(out))+' parts')
