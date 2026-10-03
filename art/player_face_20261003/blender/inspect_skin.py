"""player_face_20261003: inspect the MPFB skin mesh in suit_m0.25.blend (parts, UV regions of head/neck/hands),
draw the UV layout, and export the skin-only mesh (+ eyes with UVs collapsed into an unused corner) for Meshy retexture.
Usage: blender.sh inspect_skin.py"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
from fitlib import *

PF = AO2 / 'art/player_face_20261003'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'mpfb' / 'suit_m0.25.blend'))
rec = {'parts': {}}
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    rec['parts'][o.name] = {'verts': len(o.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in o.data.polygons),
                           'uv': [l.name for l in o.data.uv_layers], 'mats': [s.material.name if s.material else None for s in o.material_slots],
                           'mods': [m.type for m in o.modifiers]}
human = bpy.data.objects['Human']
me = human.data; uv = me.uv_layers.active.data
gidx = {g.index: g.name for g in human.vertex_groups}
def region(v):
    best = max(v.groups, key=lambda g: g.weight, default=None)
    if not best: return 'none'
    n = gidx[best.group]
    if n in ('Head', 'neck', 'head_end', 'headfront') or 'eye' in n.lower() or 'jaw' in n.lower(): return 'head'
    if 'Hand' in n or any(n.startswith(f) for f in ('thumb', 'index', 'middle', 'ring', 'pinky')): return 'hand'
    return 'other:' + n
regs = {}
for p in me.polygons:
    r = region(me.vertices[p.vertices[0]])
    for li in p.loop_indices:
        u = uv[li].uv
        b = regs.setdefault(r, [9, 9, -9, -9, 0])
        b[0] = min(b[0], u.x); b[1] = min(b[1], u.y); b[2] = max(b[2], u.x); b[3] = max(b[3], u.y)
    regs[r][4] += 1
rec['uv_regions'] = {k: [round(x, 4) for x in v[:4]] + [v[4]] for k, v in regs.items()}
rec['groups'] = sorted(set(gidx.values()))[:80]
lo, hi = eval_bounds(human); rec['bounds'] = [list(lo), list(hi)]
print('REC', json.dumps(rec))
(PF / 'blender' / 'inspect_skin.json').write_text(json.dumps(rec, indent=2))

# UV layout as SVG (coloured by region), converted with magick outside Blender
cols={'head':'#d04040','hand':'#4060d0'}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><rect width="1024" height="1024" fill="white"/>']
for p in me.polygons:
    r=region(me.vertices[p.vertices[0]]); c=cols.get(r,'#40a040')
    pts=' '.join('%.1f,%.1f'%(uv[li].uv.x*1024,(1-uv[li].uv.y)*1024) for li in p.loop_indices)
    svg.append('<polygon points="%s" fill="%s" fill-opacity="0.5" stroke="black" stroke-width="0.3"/>'%(pts,c))
svg.append('</svg>')
(PF/'renders'/'uv_layout_human.svg').write_text('\n'.join(svg))
