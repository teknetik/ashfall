import sys, os
sys.path.insert(0, '/home/teknetik/code/ao2/art/pistol_mods_20260930/src')
import bpy
import pm_common as C, pm_mats as PM, mods_barrel as MB, mods_cell as MC, mods_grip as MG
C.reset(); C.import_pistol(); C.import_hands(); M = PM.library()
for fn in (MG.build_stabilised, MG.build_gyro, MB.build_bored_alloy, MB.build_lattice_focused, MC.build_capacitor, MC.build_overclocked):
    o, _ = fn(M)
    used = {}
    for p in o.data.polygons:
        used[p.material_index] = used.get(p.material_index, 0) + 1
    print('DIAG', o.name, [(i, s.material.name if s.material else None, used.get(i, 0)) for i, s in enumerate(o.material_slots)])
