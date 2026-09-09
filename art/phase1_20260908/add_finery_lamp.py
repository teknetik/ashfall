import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/phase1_20260908'
assert Path(bpy.data.filepath).name=='finery-frontage.blend'
parts=[]
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,6),round(p.z,6),round(-p.y,6)]
for name,c,size,material in [('Lamp bracket',(16.65,3.31,-18),(.24,.18,.3),'Iron'),('Lamp weather hood',(16.36,3.30,-18),(.56,.09,.6),'Iron'),('Lamp housing',(16.43,3.19,-18),(.33,.17,.43),'Brass'),('Lamp diffuser',(16.40,3.085,-18),(.29,.042,.38),'LampEmission')]:
 assert not bpy.data.objects.get(name)
 m=bpy.data.materials.get(material) or bpy.data.materials.new(material)
 bpy.ops.mesh.primitive_cube_add(size=1,location=B(c));o=bpy.context.view_layer.objects.active;o.name=name;o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=o.modifiers.new('Folded casing edges','BEVEL');mod.width=.012;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name);o.data.materials.append(m)
 me=o.data;me.calc_loop_triangles();vs,ns,uv,ii=[],[],[],[]
 for tri in me.loop_triangles:
  for li in tri.loops:
   vs.append(U(o.matrix_world@me.vertices[me.loops[li].vertex_index].co));ns.append(U(o.matrix_world.to_3x3()@me.corner_normals[li].vector));uv.append([0.,0.]);ii.append(len(ii))
 parts.append(dict(name=name,group='Entrance light',positions=vs,normals=ns,uv=uv,indices=ii,material=material))
(O/'finery-lamp-mesh.json').write_text(json.dumps(parts,separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'finery-frontage.blend'))
print('Four authored lamp parts saved')
