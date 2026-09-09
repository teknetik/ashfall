"""Continuous flared-cylinder coordinates; removes root/trunk domain seams."""
import bpy,json,math
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2'); OUT=ROOT/'art/phase1_20260908'
o=bpy.data.objects['Ward connected root flare']; me=o.data
uv=me.uv_layers.active
for face in me.polygons:
    coords=[]
    for li in face.loop_indices:
        p=o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
        radius=math.hypot(p.x,p.y)
        # Root grain flows out from the bole. A smooth radial ramp replaces
        # the former discontinuous projection switch; four full wrap tiles.
        r=max(0., radius-1.12)
        flare=r*r/(r+.8)
        coords.append([math.atan2(-p.y,p.x)*4/math.tau,(p.z+.95*flare)/2.2])
    anchor=coords[0][0]
    for li,value in zip(face.loop_indices,coords):
        value[0]+=round((anchor-value[0])/4)*4
        uv.data[li].uv=value
me.calc_loop_triangles()
positions,normals,tex,indices,unique=[],[],[],[],{}
def unity(v): return [round(v.x,6),round(v.z,6),round(-v.y,6)]
for triangle in me.loop_triangles:
    for li in triangle.loops:
        loop=me.loops[li]; p=unity(o.matrix_world@me.vertices[loop.vertex_index].co)
        n=unity(o.matrix_world.to_3x3()@me.corner_normals[li].vector)
        t=[round(float(v),6) for v in uv.data[li].uv]; key=tuple(p+n+t)
        if key not in unique:
            unique[key]=len(positions);positions.append(p);normals.append(n);tex.append(t)
        indices.append(unique[key])
(OUT/'tree-root-mesh.json').write_text(json.dumps(dict(name=o.name,positions=positions,normals=normals,uv=tex,indices=indices),separators=(',',':')))
r=json.loads((OUT/'tree-root-report.json').read_text());r.update(vertices=len(positions),uv='Continuous flared cylinder, four seamless circumference tiles, 2.2 metre vertical scale. Root side stretching remains a review consideration.')
(OUT/'tree-root-report.json').write_text(json.dumps(r,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree-root-repaired.blend'))
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.export_scene.fbx(filepath=str(OUT/'tree-root-repaired.fbx'),use_selection=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False)
print(json.dumps(r))
