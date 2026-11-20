"""Fix round: where do the plate shard and hem shards come from? Rest pose, CPU Cycles.
Rows: decimated export (out/), undecimated fit (work/vest_fit.obj), raw Meshy source fitted the same (via obj)."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
from mathutils import Matrix
out = HERE + '/renders/diag/'
def rest(arm):
    ad = arm.animation_data
    if ad:
        ad.action = None
        for t in ad.nla_tracks: t.mute = True
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
for tag in ('dec', 'fit'):
    reset()
    arm, body, P = load(('vest',) if tag == 'dec' else (), piece_paths={'vest': HERE + '/out/TS_FieldVest.glb'})
    rest(arm)
    if tag == 'fit':
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=HERE + '/work/vest_fit.obj', forward_axis='Y', up_axis='Z')
        o = next(x for x in bpy.data.objects if x not in before)
        src = import_glb(AO2 + '/meshy/tutorial-set-20261002/chest/model.glb')
        m = next(x for x in src if x.type == 'MESH').data.materials[0]
        for x in src: bpy.data.objects.remove(x)
        o.data.materials.clear(); o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
    cam = setup(res=(900, 900), light='backsun')
    h = arm.matrix_world @ arm.data.bones['Head'].head_local
    render(out + f'hem_{tag}_back.png', cam, h + Vector((0.05, 0.75, -0.55)), h + Vector((0, 0, -0.55)), 40)
    render(out + f'hem_{tag}_right.png', cam, h + Vector((-0.45, 0.55, -0.6)), h + Vector((-0.12, 0.0, -0.6)), 40)
