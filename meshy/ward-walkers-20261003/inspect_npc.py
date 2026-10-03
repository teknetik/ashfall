"""Ward NPC inspection (headless Blender 5.2, Cycles CPU). Usage: blender.sh inspect_npc.py -- <npc folder> [model|rigged]
Renders the Meshy model at rest (front / three-quarter / side / back full body, face close-up) and, for the rigged
model, the middle frame of each idle/talk clip in the folder; writes inspect.json (triangles, bones, height, textures,
metallic stats, the holster/back measurements used by WardNpcInstall) and a contact sheet via ImageMagick later."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
HERE = Path(args[0]); WHICH = args[1] if len(args) > 1 else 'rigged'
OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
report = {'source': WHICH}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 20; s.cycles.use_denoising = True
    s.render.film_transparent = False
    s.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .58, .62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .7
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); s.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA')); s.collection.objects.link(fill)
    fill.data.energy = 220; fill.data.size = 3; fill.location = (3, -3, 2); fill.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    g = bpy.context.object; m = bpy.data.materials.new('ground'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.35, .3, .25, 1); g.data.materials.append(m)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); s.collection.objects.link(cam); s.camera = cam
    return s


def load(glb):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    mesh = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    # rigged_fixed.glb carries LOD0 (char1) and LOD1 (char1_lod1): render one (--lod1 picks the smaller)
    meshes = [o for o in new if o.type == 'MESH']
    if len(meshes) > 1 and 'fixed' in str(glb):
        keep = min(meshes, key=lambda o: len(o.data.vertices)) if '--lod1' in args else mesh
        drop = [o for o in meshes if o is not keep]
        new = [o for o in new if o not in drop]
        for o in drop: bpy.data.objects.remove(o, do_unlink=True)
        mesh = keep
    return arm, mesh, new


def world_verts(mesh):
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    mw = np.array(ev.matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
    ev.to_mesh_clear(); return co


def shoot(name, target, dist, yaw_deg, height, lens=50, res=(640, 960)):
    s = bpy.context.scene; cam = s.camera; cam.data.lens = lens
    s.render.resolution_x, s.render.resolution_y = res
    yaw = math.radians(yaw_deg)  # 0 = front (glTF import faces -Y)
    cam.location = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, height - target[2]))
    d = Vector(target) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    s.render.filepath = str(OUT / f'{WHICH}_{name}.png'); bpy.ops.render.render(write_still=True)


s = reset()
arm, mesh, objs = load(HERE / ('model.glb' if WHICH == 'model' else 'rigged.glb' if WHICH == 'rigged' else WHICH + '.glb'))
for o in objs:
    if o.type == 'MESH' and o != mesh: o.hide_render = True   # e.g. the LOD1 node of rigged_lod.glb
if arm:
    for o in s.objects:
        if o.animation_data: o.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix()
bpy.context.view_layer.update()
co = world_verts(mesh)
lo, hi = co.min(0), co.max(0); H = float(hi[2] - lo[2])
report['triangles'] = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
report['vertices'] = len(mesh.data.vertices)
report['bounds'] = [lo.round(4).tolist(), hi.round(4).tolist()]; report['height'] = round(H, 4)
report['materials'] = [m.name for m in mesh.data.materials]
imgs = []
for img in bpy.data.images:
    if img.size[0] == 0: continue
    e = {'name': img.name, 'size': list(img.size), 'colorspace': img.colorspace_settings.name}
    imgs.append(e)
report['images'] = imgs
if arm:
    report['bones'] = [b.name for b in arm.data.bones]
    report['bone_heads'] = {b.name: [round(x, 4) for x in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}
cx, cy = float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2)
mid = (cx, cy, lo[2] + H * .5)
for name, yaw in (('front', 0), ('quarter', 35), ('side', 90), ('back', 180)):
    shoot(name, mid, H * 1.55, yaw, lo[2] + H * .55, lens=50)
headz = lo[2] + H * .93
shoot('face', (cx, cy, headz), .9, 0, headz, lens=85, res=(640, 640))
shoot('face_q', (cx, cy, headz), .9, 40, headz, lens=85, res=(640, 640))
shoot('hips', (cx, cy, lo[2] + H * .5), 1.5, 25, lo[2] + H * .55, lens=60, res=(640, 640))
if arm and WHICH in ('rigged', 'rigged_fixed') and '--clips' in args:
    clips = sorted(p for p in HERE.glob('*.glb') if p.stem.split('_')[0] in ('idle', 'talk', 'walk', 'carry', 'basic'))
    report['clips'] = {}
    for clip in clips:
        a2, m2, new = load(clip)
        act = next((o.animation_data.action for o in new if o.animation_data and o.animation_data.action), None)
        if not act: report['clips'][clip.stem] = 'no action'; continue
        f0, f1 = act.frame_range
        if '--faceclip' in args:
            # skinning check of THIS file's mesh (e.g. LOD0): drive the base armature with the clip's action
            arm.animation_data_create(); arm.animation_data.action = act
            for o in new: o.hide_render = True
            s.frame_set(int((f0 + f1) / 2)); bpy.context.view_layer.update()
            c2 = world_verts(mesh)
            hb = arm.matrix_world @ arm.pose.bones['Head'].head; hz = float(hb.z) + .07
            shoot(f'{clip.stem}_mid_face', (float(hb.x), float(hb.y), hz), .9, 0, hz, lens=85, res=(640, 640))
            shoot(f'{clip.stem}_mid_face_q', (float(hb.x), float(hb.y), hz), .9, 35, hz, lens=85, res=(640, 640))
            arm.animation_data.action = None
        else:
            for o in objs:
                if o.type == 'MESH': o.hide_render = True
            for f, tag in ((f0, 'start'), ((f0 + f1) / 2, 'mid')):
                s.frame_set(int(f)); bpy.context.view_layer.update()
                c2 = world_verts(m2)
                if tag == 'mid':
                    shoot(f'{clip.stem}_mid', mid, H * 1.55, 30, lo[2] + H * .55)
        report['clips'][clip.stem] = {'frames': [f0, f1], 'mid_low_z': round(float(c2[:, 2].min()), 4), 'mid_height': round(float(c2[:, 2].max() - c2[:, 2].min()), 4)}
        for o in new: bpy.data.objects.remove(o, do_unlink=True)
        for o in objs:
            if o.type == 'MESH': o.hide_render = False
(HERE / f'inspect_{WHICH}.json').write_text(json.dumps(report, indent=1))
print('INSPECT OK', json.dumps({k: report[k] for k in ('triangles', 'height')}))
