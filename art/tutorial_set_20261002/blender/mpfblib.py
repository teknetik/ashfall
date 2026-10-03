"""MPFB2 body helpers for the tutorial-set player (2 Oct 2026). Needs the MPFB extension (run with blender_mpfb.sh)."""
import bpy, importlib, math
from mathutils import Vector
from fitlib import *
HS = importlib.import_module('bl_ext.user_default.mpfb.services.humanservice').HumanService

# MPFB game_engine bone -> the game's Meshy skeleton names (see PROGRESS.md). Fingers keep MPFB names.
RENAME = {'pelvis': 'Hips', 'spine_01': 'Spine02', 'spine_02': 'Spine01', 'spine_03': 'Spine', 'neck_01': 'neck',
          'head': 'Head', 'clavicle_l': 'LeftShoulder', 'upperarm_l': 'LeftArm', 'lowerarm_l': 'LeftForeArm',
          'hand_l': 'LeftHand', 'clavicle_r': 'RightShoulder', 'upperarm_r': 'RightArm', 'lowerarm_r': 'RightForeArm',
          'hand_r': 'RightHand', 'thigh_l': 'LeftUpLeg', 'calf_l': 'LeftLeg', 'foot_l': 'LeftFoot', 'ball_l': 'LeftToeBase',
          'thigh_r': 'RightUpLeg', 'calf_r': 'RightLeg', 'foot_r': 'RightFoot', 'ball_r': 'RightToeBase'}

MACRO = {"gender": 1.0, "age": 0.5, "muscle": 1.0, "weight": 0.7, "proportions": 0.85, "height": 0.86, "cupsize": 0.5,
         "firmness": 0.5, "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}}

def new_human(macro=MACRO):
    bpy.ops.wm.read_homefile(use_empty=True)
    return HS.create_human(macro_detail_dict=macro, scale=0.1)

def add_rig(basemesh):
    return HS.add_builtin_rig(basemesh, 'game_engine')

def rename_rig(rig, meshes):
    """Renames bones and the matching vertex groups, drops Root, adds head_end/headfront leaf bones like the Meshy rig."""
    for o in meshes:
        for g in o.vertex_groups:
            if g.name in RENAME: g.name = RENAME[g.name]
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    for old, new in RENAME.items():
        if old in eb: eb[old].name = new
    if 'Root' in eb:
        eb['Hips'].parent = None; eb.remove(eb['Root'])
    head = eb['Head']
    top = Vector((head.head.x, head.head.y, head.head.z + (head.tail - head.head).length * 1.6))
    he = eb.new('head_end'); he.head = head.tail.copy(); he.tail = head.tail + (head.tail - head.head) * 0.3; he.parent = head
    hf = eb.new('headfront'); hf.head = Vector((head.head.x, head.head.y - 0.10, head.head.z)); hf.tail = hf.head + Vector((0, -0.04, 0)); hf.parent = head
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.data.name = 'Armature'

def bake_mesh(o):
    """Applies shape keys and every modifier except the Armature (keeps skinning)."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.data.shape_keys:
        bpy.ops.object.shape_key_add(from_mix=True)
        keep = o.data.shape_keys.key_blocks[-1].name
        for kb in list(o.data.shape_keys.key_blocks):
            if kb.name != keep: o.shape_key_remove(kb)
        o.shape_key_remove(o.data.shape_keys.key_blocks[0])
    for m in list(o.modifiers):
        if m.type == 'MASK': o.modifiers.remove(m); continue
        if m.type != 'ARMATURE':
            try: bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError: o.modifiers.remove(m)

def strip_helpers(basemesh):
    """Deletes MPFB helper geometry (everything outside the 'body' vertex group) and the helper/joint groups."""
    import bmesh
    me = basemesh.data; gi = basemesh.vertex_groups['body'].index
    keep = {v.index for v in me.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    for g in list(basemesh.vertex_groups):
        if g.name.startswith(('helper-', 'joint-')) or g.name in ('HelperGeometry', 'JointCubes', 'Left', 'Mid', 'Right', 'body'):
            basemesh.vertex_groups.remove(g)

def scale_to(rig, meshes, height):
    lo, hi = eval_bounds(meshes[0]); s = height / (hi.z - lo.z)
    for o in [rig] + meshes:
        if o.parent == rig: continue
        o.scale = [v * s for v in o.scale]
    for o in [rig] + meshes:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return s
