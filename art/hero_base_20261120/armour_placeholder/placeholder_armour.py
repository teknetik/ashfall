"""Hero base: STAND-IN armour files (headless Blender 5.2). Usage: blender.sh placeholder_armour.py
The seven installed TS_*.glb pieces as they are (fitted to the PREVIOUS body, so they do not fit the hero), re-bound by
vertex-group name to the hero's armature and exported with it, so their skins have the hero's joints and bind poses.
They exist only so the installer chain (TutorialSetInstall.Attach refuses pieces whose bind poses differ from the
body's) can be exercised before the real re-fit in ../armour/out is ready. Never ship a build with these.
Out: armour_placeholder/out/TS_*.glb (no textures)."""
import bpy, json
from pathlib import Path
ROOT = Path('/home/teknetik/code/ao2'); H = ROOT / 'art/hero_base_20261120'; OUT = H / 'armour_placeholder/out'; OUT.mkdir(parents=True, exist_ok=True)
SRC = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Armour/TutorialSet'
KEPT = H / 'rollback/assets/Art/Armour/TutorialSet'          # once the hero files are installed the originals live here
PIECES = ['TS_Helmet', 'TS_FieldVest', 'TS_WardenCarrier', 'TS_ArmGuards', 'TS_Gloves', 'TS_LegArmour', 'TS_Boots']
rec = {}
for name in PIECES:
    bpy.ops.wm.open_mainfile(filepath=str(H / 'build/hero.blend'))
    rig = bpy.data.objects['Armature']; bones = {b.name for b in rig.data.bones}
    for o in list(bpy.data.objects):
        if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    src = KEPT / f'{name}.glb'
    if not src.exists(): src = SRC / f'{name}.glb'
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(src), bone_heuristic='BLENDER')
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for m in meshes:
        mw = m.matrix_world.copy(); m.parent = None; m.matrix_world = mw
        for md in list(m.modifiers):
            if md.type == 'ARMATURE': m.modifiers.remove(md)
        bpy.ops.object.select_all(action='DESELECT'); m.select_set(True); bpy.context.view_layer.objects.active = m
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        missing = [g.name for g in m.vertex_groups if g.name not in bones]
        m.parent = rig; md = m.modifiers.new('Armature', 'ARMATURE'); md.object = rig
        rec.setdefault(name, []).append({'mesh': m.name, 'tris': sum(len(p.vertices) - 2 for p in m.data.polygons), 'groups_not_on_the_hero_rig': missing})
    for o in new:
        if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    if rig.animation_data: rig.animation_data_clear()
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes: m.select_set(True)
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(OUT / f'{name}.glb'), use_selection=True, export_format='GLB', export_skins=True, export_animations=False,
                              export_morph=False, export_yup=True, export_image_format='NONE', export_tangents=True)
(OUT / 'placeholder.json').write_text(json.dumps(rec, indent=1)); print('PLACEHOLDER OK', json.dumps(rec))
