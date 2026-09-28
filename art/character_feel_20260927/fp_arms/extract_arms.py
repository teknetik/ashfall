# Blender 5.2 headless: first-person arms from the player colonist (same mesh, skin and armature).
# Keeps faces whose vertices are mostly weighted to the forearms and hands (plus the lower third of the upper arms),
# deletes everything else, and exports a skinned GLB. Usage: blender -b -P extract_arms.py -- in.glb out.glb
import bpy, bmesh, sys
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
KEEP = {'RightForeArm', 'RightHand', 'LeftForeArm', 'LeftHand'}
PART = {'RightArm', 'LeftArm'}
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    names = {g.index: g.name for g in o.vertex_groups}
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    deform = bm.verts.layers.deform.verify()
    arm = {}
    for v in bm.verts:
        w = v[deform]; k = sum(x for i, x in w.items() if names.get(i) in KEEP); p = sum(x for i, x in w.items() if names.get(i) in PART)
        arm[v.index] = k + .6 * p * (1 if k > .02 else 0)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if sum(arm[v.index] for v in f.verts) / len(f.verts) < .5]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    print('arms faces kept', len(bm.faces), 'verts', len(bm.verts))
    bm.to_mesh(me); bm.free()
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=False, export_skins=True)
