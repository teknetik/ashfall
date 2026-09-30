import sys
sys.path.insert(0, '/home/teknetik/code/ao2/art/pistol_mods_20260930/src')
import bpy, pm_common as C
C.reset(); hs = C.import_hands()
for h in hs:
    print('HM obj', h.name, [m.name for m in h.data.materials], list(h.data.color_attributes.keys()) if hasattr(h.data,'color_attributes') else '')
    for m in h.data.materials:
        b = m.node_tree.nodes.get('Principled BSDF')
        print('HM', m.name, [n.bl_idname for n in m.node_tree.nodes], b.inputs['Base Color'].is_linked if b else None, tuple(b.inputs['Base Color'].default_value) if b else None)
