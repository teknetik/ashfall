import bpy, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import mbk
from mbk import RG
bpy.ops.wm.open_mainfile(filepath=os.path.join(mbk.PROG, 'fixtures/export/fixtures.blend'))
arm = bpy.data.objects['fixtures_vise_rig']
print('ARM parent', arm.parent.name if arm.parent else None, 'bones', [b.name for b in arm.data.bones], 'props', {k: arm[k] for k in arm.keys() if k not in ('anymachine',)})
for v in (0.0, 0.5, 1.0):
    RG.set_params(arm, {'vise_jaw': v})
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ('fixtures_vise', 'fixtures_vise_slide', 'fixtures_vise_plate_m', 'fixtures_vise_pad_m', 'fixtures_vise_screw'):
        o = bpy.data.objects[n].evaluated_get(dg)
        print(v, n, [round(x, 4) for x in o.matrix_world.translation], 'scale', [round(x, 3) for x in o.matrix_world.to_scale()], 'hide', o.hide_render, 'pb', [round(x,4) for x in arm.pose.bones['vise_jaw'].location])
