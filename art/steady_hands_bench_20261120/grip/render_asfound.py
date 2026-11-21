# The exported grip.glb with the family's as-found texture set swapped in (tex/grip__dirty_*.png): the core fresh
# from the mould and the uncured seams, as the bench shows them before anything is wiped. review/[warm_]asfound_*.png
#   SH/blender.sh grip/render_asfound.py -- [--samples 36] [--warm]
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import bpy
from mathutils import Vector
import kitload
RV = kitload.load('review'); ME = kitload.load('measure')

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
samples = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 36
warm = '--warm' in argv
tag = 'warm_asfound_' if warm else 'asfound_'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'export', 'grip.glb'))
pj = json.load(open(os.path.join(HERE, 'export', 'parts.json')))
nodes = {p['node'] for p in pj['parts']}
objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name in nodes]
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name not in nodes:
        o.hide_render = True
swapped = set()
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            nm = n.image.name.lower()
            for kind in ('color', 'normal', 'orm'):
                if kind in nm:
                    im = bpy.data.images.load(os.path.join(HERE, 'export', 'tex', 'grip__dirty_%s.png' % kind), check_existing=True)
                    im.colorspace_settings.name = 'sRGB' if kind == 'color' else 'Non-Color'
                    n.image = im; swapped.add(kind)
                    break           # 'normal' contains 'orm': without this the normal map node got the ORM image (black renders)
print('ASFOUND swapped', sorted(swapped))
RV.WARM = warm
RV.studio(samples=samples)
lo, hi = ME.bounds(objs)
c = Vector((lo + hi) / 2); size = float(max(hi - lo))
RV.ground(float(lo[2]) - 0.0002)
out = os.path.join(HERE, 'review')
paths = []
for name, yaw, down in (('left', -100, 20), ('right', 80, 20), ('back', 15, 14)):
    cam = RV.close_cam(c, dist=0.3, down=down, yaw=yaw, name='cam_' + name, fit=size * 0.66)
    paths.append(RV.render(os.path.join(out, tag + name + '.png'), cam, res=(1200, 1200), samples=samples))
RV.contact_sheet(paths, os.path.join(out, tag + 'sheet.jpg'), cols=3, labels=['as found: ' + os.path.basename(p)[len(tag):-4] for p in paths], width=900)
print('ASFOUND RENDERS', len(paths))
