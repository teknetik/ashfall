"""Merge the Meshy-rigged worker droid and its six library/basic animations into one GLB with named actions.
Run: blender -b --python art/outer_berms_20260926/merge_worker_droid.py
Source: meshy/outer-berms-20260926/worker-droid (rigged.glb + anim-*.glb). Geometry, UVs, weights and
textures come unchanged from rigged.glb; only the armature actions are collected and renamed."""
import bpy, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'meshy/outer-berms-20260926/worker-droid')
OUT = os.path.join(ROOT, 'unity/AthenHill/Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb')
CLIPS = ['idle', 'walk', 'run', 'attack', 'hit', 'death']

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, 'rigged.glb'))
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
keep = set(bpy.context.scene.objects)
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
report = {}
for clip in CLIPS:
    before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, f'anim-{clip}.glb'))
    new = [a for a in bpy.data.actions if a not in before]
    act = max(new, key=lambda a: a.frame_range[1] - a.frame_range[0])
    act.name = clip; act.use_fake_user = True
    report[clip] = dict(frames=list(act.frame_range), source_actions=len(new))
    for a in new:
        if a is not act: bpy.data.actions.remove(a)
    for o in [o for o in bpy.context.scene.objects if o not in keep]:
        bpy.data.objects.remove(o, do_unlink=True)
for m in [m for m in bpy.data.meshes if m.users == 0]: bpy.data.meshes.remove(m)
for m in [m for m in bpy.data.materials if m.users == 0]: bpy.data.materials.remove(m)
for i in [i for i in bpy.data.images if i.users == 0]: bpy.data.images.remove(i)
arm.animation_data_create()
# 27 Sep 2026 fix: Blender 4.4+ slotted actions. Each imported action's slot belongs to its discarded import armature;
# the previous NLA_TRACKS export evaluated nothing and wrote every clip as the static rest pose. Export the named
# actions directly (ACTIONS mode) with the idle action and its slot assigned so the exporter binds them to this rig.
idle = bpy.data.actions['idle']
arm.animation_data.action = idle
arm.animation_data.action_slot = idle.slots[0]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_animations=True, export_animation_mode='ACTIONS',
                          export_skins=True, export_image_format='AUTO', export_yup=True)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
report['mesh'] = dict(objects=len(meshes), triangles=sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes),
                      bones=len(arm.data.bones), height=max((o.dimensions.z for o in meshes), default=0))
json.dump(report, open(os.path.join(ROOT, 'art/outer_berms_20260926/worker-droid-merge.json'), 'w'), indent=2)
print('MERGED', json.dumps(report))
