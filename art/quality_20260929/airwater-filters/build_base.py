"""Review base for the Air + Water filter fittings (29 Sep 2026, task t_bd3d9fe3).

    sh bl.sh /home/teknetik/code/ao2/art/relay_airwater_surfaces_20260909/relay-airwater-surfaces-v2.blend --python build_base.py

Reads the 9 Sep surface-pass source (relay-airwater-surfaces-v2.blend, never saved over), keeps the 383 `air_water` objects, and
re-expresses them in the building A-space used by the other 29 Sep packages (+X screen-right from the avenue, +Y up, +Z to the avenue,
origin = building pivot, Y=0 = porch top) then rotated to Blender Z-up like Part.finalise():  newB = (xA, -zA, yA).
The v2 blend is a mirror image of the real building (Unity left-handed -> Blender by a proper rotation), so the bake is a reflection:
xA = 9 - By, yA = Bz - 0.5, zA = Bx + 20.6 (verified by canister centres 0.9/1.7/2.5 right of the door).  Faces are flipped to keep the
outside facing out.  Writes airwater-review-base.blend (old geometry only, collection 'Air + Water rev04 + surface pass (old)').
"""
import bpy, bmesh, math
from mathutils import Matrix, Vector
OUT = '/home/teknetik/code/ao2/art/quality_20260929/airwater-filters/airwater-review-base.blend'
# newB = (9 - By, -(Bx + 20.6), Bz - 0.5)
R = Matrix(((0, -1, 0, 9), (-1, 0, 0, -20.6), (0, 0, 1, -0.5), (0, 0, 0, 1)))
assert R.determinant() < 0
keep = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('air_water')]
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
col = bpy.data.collections.new('Air + Water rev04 + surface pass (old)')
bpy.context.scene.collection.children.link(col)
for c in list(bpy.data.collections):
    pass
for o in keep:
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    me = o.data
    if me.users > 1:
        me = me.copy(); o.data = me
    me.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    me.transform(R)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(45))
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me); bm.free()
    try:
        me.customdata_custom_splitnormals_clear()
    except Exception as ex:
        pass
    o['old_rev04'] = True
bpy.context.scene.name = 'Air + Water filters review'
for cam in [o for o in bpy.data.objects if o.type in ('CAMERA', 'LIGHT')]:
    bpy.data.objects.remove(cam, do_unlink=True)
bpy.ops.file.make_paths_absolute()
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('BASE SAVED', len(keep))
