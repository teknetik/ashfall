# Compact field utility belt: woven band, bound edges, two shaped canvas pouches, brass catches.
# Geometry only; no new item/stat. Attached to the existing pelvis rig with blend into lower spine.
new=[]
from mathutils.bvhtree import BVHTree
body_surface=BVHTree.FromPolygons([v.co.copy() for v in char.data.vertices],[list(p.vertices) for p in char.data.polygons])
def material(name,color,rough,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;return m
canvas=material('PlayerFieldWebbing',(.115,.102,.074),.9)
# Original woven canvas tile (no external source texture).
import numpy as np
n=256;yy,xx=np.mgrid[:n,:n];warp=.96+.06*np.sin(xx*math.pi/4);weft=.96+.06*np.sin(yy*math.pi/4);over=((xx//8+yy//8)%2)==0
weave=np.where(over,warp,weft);grain=np.random.default_rng(51005).uniform(.96,1.04,(n,n));px=np.ones((n,n,4),dtype=np.float32)
for k,c in enumerate([.38,.35,.29]):px[:,:,k]=c*weave*grain
im=bpy.data.images.new('Field canvas weave',width=n,height=n,alpha=False);im.pixels.foreach_set(px.ravel());im.filepath_raw=str(OUT/'field_canvas.png');im.file_format='PNG';im.save()
nt=canvas.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
hardware=material('PlayerBeltHardware',(.16,.125,.065),.48,.65)
def mesh_obj(name,vs,fs,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
 group=o.vertex_groups.new(name='Hips');group.add(list(range(len(vs))),1,'REPLACE')
 ca=me.color_attributes.new('Col','FLOAT_COLOR','POINT')
 for d in ca.data:d.color=(1,1,1,1)
 me.color_attributes.active_color=ca
 uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  axis=max(range(3),key=lambda k:abs(poly.normal[k]));axes=[k for k in range(3) if k!=axis]
  for li in poly.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]*70,co[axes[1]]*70)
 new.append(o);return o
# Slightly irregular cloth band, with actual 4mm thickness and stitched raised edging.
def band(name,z,width,rx,ry,mat):
 vs=[];fs=[];steps=80
 for radius in [0,-.004]:
  for level in [-.5,.5]:
   for i in range(steps):
    t=2*math.pi*i/steps; ripple=.001*math.sin(9*t)
    height=z+width*level+ripple;direction=Vector((math.sin(t),math.cos(t),0));origin=Vector((0,-.028,height));hit=body_surface.ray_cast(origin,direction,.26)[0]
    distance=(hit-origin).length if hit else .16
    point=origin+direction*(distance+.008+radius);vs.append(tuple(point))
 for a,b in [(0,1),(1,3),(3,2),(2,0)]:
  for i in range(steps):j=(i+1)%steps;fs.append((a*steps+i,a*steps+j,b*steps+j,b*steps+i))
 return mesh_obj(name,vs,fs,mat)
band('Field belt',1.055,.043,.187,.143,canvas)
band('Belt upper binding',1.075,.004,.189,.145,canvas);band('Belt lower binding',1.035,.004,.189,.145,canvas)
def rounded_box(name,center,size,mat,bevel=.008):
 # Bevelled boxes start from authored vertices, avoiding operator-dependent primitive context.
 cx,cy,cz=center;sx,sy,sz=[v/2 for v in size]
 vs=[(cx+x*sx,cy+y*sy,cz+z*sz) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 fs=[(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5),(0,2,6,4),(1,5,7,3)]
 o=mesh_obj(name,vs,fs,mat);bpy.context.view_layer.objects.active=o;o.select_set(True)
 mod=o.modifiers.new('Soft sewn edges','BEVEL');mod.width=bevel;mod.segments=3
 bpy.ops.object.modifier_apply(modifier=mod.name);o.select_set(False)
 for p in o.data.polygons:p.use_smooth=True
 return o
rounded_box('Buckle',(.0,-.177,1.055),(.045,.012,.035),hardware,.004)
rounded_box('Buckle inset',(.0,-.185,1.055),(.027,.006,.018),canvas,.002)
# Pouches sit at the front quarters clear of hand swing, vest hem and the thigh holster.
for x,y,z,w in [(.105,-.153,1.002,.065),(-.105,-.153,1.009,.066)]:
 rounded_box('Canvas utility pocket',(x,y,z),(w,.045,.086),canvas,.012)
 rounded_box('Pocket folded flap',(x,y-.024,z+.028),(w+.004,.009,.032),canvas,.006)
 for dx in [-w/2+.004,w/2-.004]:
  rounded_box('Pocket side seam',(x+dx,y-.024,z-.008),(.002,.002,.048),canvas,.0007)
 rounded_box('Pocket catch',(x,y-.031,z+.02),(.013,.005,.017),hardware,.002)
# Join into the body skin, preserving its material ordering and rest rig. Only ~2k extra triangles.
bpy.ops.object.select_all(action='DESELECT');char.select_set(True)
for o in new:o.select_set(True)
bpy.context.view_layer.objects.active=char;bpy.ops.object.join()
report['field_belt']={'parts':len(new),'body_triangles':sum(len(p.vertices)-2 for p in char.data.polygons),'materials':[m.name for m in char.data.materials]}
