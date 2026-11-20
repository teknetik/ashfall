"""Review renders of the first-person view models from RifleHandsPass20261120 --steps dump (OBJ in camera space).
Grey-material Cycles renders: no game shading, only shape, contact and framing. Unity is left-handed (x right, y up,
z forward); Blender gets (x, z, y).
Usage: blender -b --factory-startup -P render_dump.py -- DUMP_DIR OUT_DIR [states...]
Each state renders 'fp' (the player's view) and 'fp_armour'; the rifle hip state also renders five orbit views."""
import bpy, json, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
dump, out = argv[0], argv[1]
states = argv[2:] or ['rifle_hip', 'rifle_ads', 'rifle_burst', 'rifle_walk', 'rifle_sprint', 'rifle_lowered', 'pistol_hip', 'pistol_ads']
os.makedirs(out, exist_ok=True)
cam_cfg = json.load(open(os.path.join(dump, 'camera.json')))

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.62, .55, .45, 1); bg.inputs[1].default_value = .6
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(140)); sc.collection.objects.link(sun)
    return sc

def mat(name, rgb, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m

def load(path, sc, armour):
    mats = {'arms': mat('skin', (.62, .40, .30), .55), 'armour': mat('armour', (.16, .17, .13), .7), 'weapon': mat('weapon', (.30, .30, .32), .45)}
    verts, faces, name, objs = [], [], None, []
    def flush():
        if name is None or not faces: return
        kind = name.split('_')[0]
        if kind == 'armour' and not armour: return
        used = sorted({i for f in faces for i in f}); remap = {v: k for k, v in enumerate(used)}
        me = bpy.data.meshes.new(name); me.from_pydata([verts[i] for i in used], [], [[remap[i] for i in f] for f in faces]); me.update()
        for p in me.polygons: p.use_smooth = True
        ob = bpy.data.objects.new(name, me); ob.data.materials.append(mats.get(kind, mats['weapon'])); sc.collection.objects.link(ob); objs.append(ob)
    for line in open(path):
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:4]); verts.append((x, z, y))
        elif line.startswith('f '):
            faces.append([int(t) - 1 for t in line.split()[1:4]])
        elif line.startswith('o '):
            flush(); name = line.split()[1]; faces = []
    flush()
    return objs

def camera(sc, pos, look, vfov):
    c = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(c); sc.camera = c
    c.data.sensor_fit = 'VERTICAL'; c.data.angle = math.radians(vfov); c.data.clip_start = .005
    c.location = Vector(pos); d = Vector(look) - Vector(pos)
    c.rotation_euler = d.to_track_quat('-Z', 'Z').to_euler()
    return c

def render(sc, path):
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print('wrote', path, flush=True)

for st in states:
    f = os.path.join(dump, st + '.obj')
    if not os.path.exists(f): print('missing', f); continue
    for armour in (False, True):
        sc = reset(); objs = load(f, sc, armour)
        camera(sc, (0, 0, 0), (0, 1, 0), cam_cfg['vfov'])
        render(sc, os.path.join(out, f"{st}_fp{'_armour' if armour else ''}.png"))
        if st == 'rifle_hip' and not armour:
            arms = [o for o in objs if o.name.startswith('arms')]
            # hands: the arm vertices furthest forward on each side
            vs = [o.matrix_world @ v.co for o in arms for v in o.data.vertices]
            fwd = sorted(vs, key=lambda v: -v.y)[:4000]
            right = [v for v in fwd if v.x > .05]; left = [v for v in fwd if v.x <= .05]
            def centre(l): return sum(l, Vector()) / max(1, len(l))
            # shooting hand: arm vertices near the pistol grip region (low, right); support: furthest forward
            rh = centre(sorted(vs, key=lambda v: (v - Vector((.1, .25, -.25))).length)[:800])
            lh = centre(sorted(vs, key=lambda v: -v.y)[:800])
            for name, pos, look in [
                ('orbit_shoot_right', rh + Vector((.32, -.02, .06)), rh),
                ('orbit_shoot_front', rh + Vector((.12, .30, .05)), rh),
                ('orbit_shoot_left', rh + Vector((-.30, .02, .08)), rh),
                ('orbit_support_left', lh + Vector((-.32, -.02, .05)), lh),
                ('orbit_support_under', lh + Vector((.04, -.06, -.30)), lh),
                ('orbit_support_right', lh + Vector((.32, .02, .04)), lh)]:
                for o in [x for x in sc.collection.objects if x.type == 'CAMERA']: bpy.data.objects.remove(o)
                camera(sc, pos, look, 40)
                render(sc, os.path.join(out, f"{st}_{name}.png"))
