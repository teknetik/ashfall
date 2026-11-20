"""Before/after contact sheets from CharacterArmsPass20261120 --steps dump (OBJ per actor, pose and version, in the
actor's frame: feet at the origin, facing Unity +Z). Grey Cycles renders (CPU): shape only, no game shading.
Unity is left-handed (x right, y up, z forward); Blender gets (x, z, y).
One image per actor and view: columns = poses, top row = before (cool grey), bottom row = after (warm grey).
Usage: blender -b --factory-startup -P render_sheets.py -- DUMP_DIR OUT_DIR [actor_regex] [views=front,threequarter,side,back]"""
import bpy, json, math, os, re, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
dump, out = argv[0], argv[1]
only = re.compile(argv[2]) if len(argv) > 2 and argv[2] else None
views = (argv[3] if len(argv) > 3 else 'front,threequarter').split(',')
os.makedirs(out, exist_ok=True)
index = json.load(open(os.path.join(dump, 'index.json')))
actors = []
for e in index:
    if e['actor'] not in actors and (not only or only.search(e['actor'])):
        actors.append(e['actor'])
YAW = {'front': 0, 'threequarter': 35, 'side': 90, 'back': 180, 'backthreequarter': 145}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 8
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.85, .85, .85, 1); bg.inputs[1].default_value = .55
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(20)); sc.collection.objects.link(sun)
    return sc


def mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = .6
    return m


def load(path, sc, m_body, m_prop, offset, yaw):
    verts, faces, name, objs = [], [], None, []
    rot = math.radians(yaw)
    c, s = math.cos(rot), math.sin(rot)

    def flush():
        if name is None or not faces:
            return
        used = sorted({i for f in faces for i in f}); remap = {v: k for k, v in enumerate(used)}
        me = bpy.data.meshes.new(name); me.from_pydata([verts[i] for i in used], [], [[remap[i] for i in f] for f in faces]); me.update()
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(name, me); ob.data.materials.append(m_prop if name.startswith('prop') else m_body)
        ob.location = offset; sc.collection.objects.link(ob); objs.append(ob)
    for line in open(path):
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:4])
            bx, by = x, z
            verts.append((bx * c - by * s, bx * s + by * c, y))
        elif line.startswith('f '):
            faces.append([int(t) - 1 for t in line.split()[1:4]])
        elif line.startswith('o '):
            flush(); name = line.split()[1]; faces = []
    flush()
    return objs


for actor in actors:
    entries = [e for e in index if e['actor'] == actor]
    poses = []
    for e in entries:
        if e['pose'] not in poses:
            poses.append(e['pose'])
    for view in views:
        sc = reset()
        mb, ma, mp = mat('before', (.55, .58, .62)), mat('after', (.72, .62, .52)), mat('prop', (.25, .25, .27))
        col = 1.15
        for i, pose in enumerate(poses):
            for row, version in enumerate(('before', 'after')):
                f = os.path.join(dump, f"{actor}__{pose}__{version}.obj")
                if os.path.exists(f):
                    load(f, sc, mb if version == 'before' else ma, mp, (i * col, 0, (1 - row) * 2.25), YAW[view])
        w = max(1, len(poses)) * col
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = 'ORTHO'
        h = 4.6
        cam.data.ortho_scale = max(w, h * w / w)
        # camera in front (Blender +Y is the actors' forward), looking back at them
        cam.location = Vector(((len(poses) - 1) * col / 2, 12, 2.15))
        cam.rotation_euler = (math.radians(90), 0, math.radians(180))
        px = 260
        sc.render.resolution_x = int(w * px); sc.render.resolution_y = int(h * px)
        cam.data.sensor_fit = 'HORIZONTAL' if w >= h else 'VERTICAL'
        cam.data.ortho_scale = max(w, h)
        sc.render.filepath = os.path.join(out, f"{actor}__{view}.png")
        bpy.ops.render.render(write_still=True)
        print('wrote', sc.render.filepath, 'poses', poses, flush=True)
