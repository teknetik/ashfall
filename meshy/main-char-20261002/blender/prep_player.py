# Blender 5.2 headless (run via ~/.local/state/ward-programme/blender.sh). Game-ready player from Carl's main_char_OK.glb:
#   hi   595k-triangle source (kept untouched; only read)
#   lo   decimated LOD0 (~60k tris, source UVs kept) with a 4k tangent-space normal baked from hi (geometry + hi's own
#        normal texture), base colour and metallic/roughness textures carried over at source size (2048)
#   lo1  LOD1 (~15k tris) from lo, same textures (record only; installed only if cheap)
#   rig  lo with 1k textures for the Meshy rigging upload (Meshy needs a textured GLB, face toward +Z)
# Outputs in meshy/main-char-20261002/blender/: player_lod0.glb, player_lod1.glb, player_rig_input.glb,
# player_normal_4k.png, previews/*.png, prep.json, player_prep.blend.
import bpy, json, sys, time, math
from pathlib import Path
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = Path(argv[0]); OUT = Path(argv[1]); OUT.mkdir(parents=True, exist_ok=True); (OUT / 'previews').mkdir(exist_ok=True)
TARGET_TRIS = int(argv[2]) if len(argv) > 2 else 60000
LOD1_TRIS = int(argv[3]) if len(argv) > 3 else 15000
RIG_FACING_ROT_Z = float(argv[4]) if len(argv) > 4 else 0.0   # degrees about Z applied to the rig-input copy (0 = as delivered)
rec = {'source': str(SRC), 'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'target_tris': TARGET_TRIS}
t0 = time.time()
def log(*a): print('[prep]', *a, flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
hi = [o for o in bpy.data.objects if o.type == 'MESH'][0]
hi.name = 'hi'
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def bounds(o):
    xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]; zs = [v.co.z for v in o.data.vertices]
    return {'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]}
rec['hi'] = {'tris': tris(hi), 'verts': len(hi.data.vertices), 'bounds_blender_xyz': bounds(hi), 'uv_layers': [u.name for u in hi.data.uv_layers]}
rec['images'] = {im.name: list(im.size) for im in bpy.data.images}
log('hi', rec['hi'])

# Facing heuristic: the nose is the most forward point of the head band; Blender -Y is glTF +Z (the Meshy/glTF forward).
b = rec['hi']['bounds_blender_xyz']; top = b['max'][2]; h = top - b['min'][2]
head = [v.co for v in hi.data.vertices if v.co.z > top - .10 * h]
ymin = min(v.y for v in head); ymax = max(v.y for v in head); yc = sum(v.y for v in head) / len(head)
rec['facing'] = {'head_y_centre': yc, 'head_y_min': ymin, 'head_y_max': ymax, 'guess': 'faces -Y (glTF +Z) ' if (yc - ymin) > (ymax - yc) else 'faces +Y (glTF -Z)'}
log('facing', rec['facing'])

# ---- LOD0: decimate (collapse keeps UVs) ----
bpy.ops.object.select_all(action='DESELECT'); hi.select_set(True); bpy.context.view_layer.objects.active = hi
bpy.ops.object.duplicate(); lo = bpy.context.view_layer.objects.active; lo.name = 'lo'
lo.data = lo.data.copy(); lo.data.name = 'lo'
m = lo.modifiers.new('dec', 'DECIMATE'); m.ratio = TARGET_TRIS / rec['hi']['tris']; m.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=m.name)
# (no normal recalculation: decimation keeps the source face orientation; recalculating flipped the overlapping beard shell, 2 Oct 16:10)
bpy.ops.object.shade_smooth()
rec['lo'] = {'tris': tris(lo), 'verts': len(lo.data.vertices), 'decimate_ratio': m.ratio, 'seconds': round(time.time() - t0, 1)}
log('lo', rec['lo'])

# ---- materials: lo gets a copy of hi's material with the baked normal ----
hi_mat = hi.data.materials[0]
lo_mat = hi_mat.copy(); lo_mat.name = 'PlayerLOD0'; lo.data.materials.clear(); lo.data.materials.append(lo_mat)
nodes = lo_mat.node_tree.nodes
normal_tex = next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_node.type == 'NORMAL_MAP' for l in n.outputs[0].links))
base_tex = next(n for n in nodes if n.type == 'TEX_IMAGE' and any(l.to_socket.name == 'Base Color' for l in n.outputs[0].links))
mr_tex = next(n for n in nodes if n.type == 'TEX_IMAGE' and n not in (normal_tex, base_tex))
rec['source_textures'] = {'base': [base_tex.image.name, list(base_tex.image.size)], 'metallic_roughness': [mr_tex.image.name, list(mr_tex.image.size)], 'normal': [normal_tex.image.name, list(normal_tex.image.size)]}
N = 4096
baked = bpy.data.images.new('player_normal_4k', N, N, alpha=False, float_buffer=False)
baked.colorspace_settings.name = 'Non-Color'
bake_node = nodes.new('ShaderNodeTexImage'); bake_node.image = baked; bake_node.name = 'BAKE_TARGET'
nodes.active = bake_node
# ---- bake: hi (selected) -> lo (active), tangent-space normal, Cycles CPU, 1 sample ----
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
sc.cycles.use_denoising = False
bk = sc.render.bake; bk.use_selected_to_active = True; bk.cage_extrusion = 0.004; bk.max_ray_distance = 0.012   # a few mm: the 10 % decimation deviates < 2 mm; longer rays hit the shells under the collar/beard
bk.normal_space = 'TANGENT'; bk.margin = 16; bk.use_clear = True
bpy.ops.object.select_all(action='DESELECT'); hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
tb = time.time(); bpy.ops.object.bake(type='NORMAL'); rec['bake'] = {'size': N, 'seconds': round(time.time() - tb, 1), 'cage_extrusion': bk.cage_extrusion, 'max_ray_distance': bk.max_ray_distance}
log('bake', rec['bake'])
baked.filepath_raw = str(OUT / 'player_normal_4k.png'); baked.file_format = 'PNG'; baked.save()
# use the baked map in lo's material; drop the bake target node
normal_tex.image = baked; nodes.remove(bake_node)
hi.hide_render = True; hi.hide_set(True)

def export(obj, path, image_format='AUTO'):
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_animations=False, export_skins=False,
                              export_apply=True, export_image_format=image_format, export_jpeg_quality=92, export_yup=True)
    return path.stat().st_size
rec['lod0_glb_bytes'] = export(lo, OUT / 'player_lod0.glb')
log('lod0 exported')

# ---- LOD1 ----
bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
bpy.ops.object.duplicate(); lo1 = bpy.context.view_layer.objects.active; lo1.name = 'lo1'; lo1.data = lo1.data.copy(); lo1.data.name = 'lo1'
m1 = lo1.modifiers.new('dec', 'DECIMATE'); m1.ratio = LOD1_TRIS / rec['lo']['tris']; m1.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=m1.name); bpy.ops.object.shade_smooth()
rec['lo1'] = {'tris': tris(lo1), 'verts': len(lo1.data.vertices)}
rec['lod1_glb_bytes'] = export(lo1, OUT / 'player_lod1.glb')
lo1.hide_set(True); lo1.hide_render = True
log('lod1', rec['lo1'])

# ---- rig input: lo with 1k textures, facing +Z (glTF) ----
bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
bpy.ops.object.duplicate(); rig = bpy.context.view_layer.objects.active; rig.name = 'rig_input'; rig.data = rig.data.copy()
rig.rotation_euler = (0, 0, math.radians(RIG_FACING_ROT_Z))
rig_mat = lo_mat.copy(); rig_mat.name = 'PlayerRigInput'; rig.data.materials.clear(); rig.data.materials.append(rig_mat)
for n in rig_mat.node_tree.nodes:
    if n.type == 'TEX_IMAGE' and n.image:
        small = n.image.copy(); small.name = n.image.name + '_1k'; small.scale(1024, 1024); n.image = small
rec['rig_input_glb_bytes'] = export(rig, OUT / 'player_rig_input.glb', image_format='JPEG')
rig.hide_set(True); rig.hide_render = True
log('rig input exported', rec['rig_input_glb_bytes'])

# ---- previews: Workbench hi vs Eevee lo with the baked normal, 4 angles ----
def render(obj, name, engine):
    for o in bpy.data.objects: o.hide_render = (o != obj and o.type == 'MESH')
    sc.render.engine = engine; sc.render.resolution_x = 600; sc.render.resolution_y = 900; sc.render.image_settings.file_format = 'PNG'
    if engine == 'BLENDER_WORKBENCH':
        sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); 
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.lens = 50
    sun = bpy.data.objects.get('sun') or bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    if sun.name not in sc.collection.objects: sc.collection.objects.link(sun)
    sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    c = [(b['min'][i] + b['max'][i]) / 2 for i in range(3)]; d = 4.2
    for label, ang in (('front', 0), ('left', 90), ('back', 180), ('right', 270)):
        a = math.radians(ang); cam.location = (c[0] - d * math.sin(a), c[1] - d * math.cos(a), c[2] + .1)
        cam.rotation_euler = (math.radians(88), 0, -a)
        sc.render.filepath = str(OUT / 'previews' / f'{name}_{label}.png'); bpy.ops.render.render(write_still=True)
    # face close-up from the front
    cam.data.lens = 85; cam.location = (c[0], c[1] - 1.6, top - .10 * h); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.render.filepath = str(OUT / 'previews' / f'{name}_face.png'); bpy.ops.render.render(write_still=True)
hi.hide_set(False); render(hi, 'hi', 'BLENDER_WORKBENCH'); hi.hide_set(True)
try: sc.eevee.taa_render_samples = 16
except Exception: pass
EEVEE = next(e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE') if e in [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
render(lo, 'lo', EEVEE)
rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); rec['total_seconds'] = round(time.time() - t0, 1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'player_prep.blend'))
(OUT / 'prep.json').write_text(json.dumps(rec, indent=2)); log('DONE', rec['total_seconds'], 's')
