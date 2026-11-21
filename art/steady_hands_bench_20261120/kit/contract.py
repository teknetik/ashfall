# kit/contract.py: CONTRACT.md section A in code. Custom properties on the objects are the source of truth; this file
# sets them, makes the helper empties, builds the node hierarchy and writes parts.json and stats.json from the scene.
#
#   CT.part(o, 'pistol', 'scale_l', 'Left grip scale', parent='frame', material='wood', mass='light',
#           held_by=['screw_grip_a', 'screw_grip_b'], steps=['s1.scales'])       -> node 'pistol_scale_l'
#   CT.fastener(o, 'pistol', 'screw_grip_a', 'Upper grip screw', bit='slot', turns=6, holds=['scale_l', 'scale_r'],
#               into='frame', shank_d=3 * MM, parent='frame', steps=[...])
#   CT.clear(o, offset=(0, -0.03, 0))        the pose where the part is just clear ('<node>__clear', world offset)
#   CT.clear_along(o, 0.02)                  the same along the part's own +Z (fasteners from am_parts)
#   CT.grab(o, point)   CT.tip(o, point, direction)   CT.mark(o, 'oil', point, normal)
#   CT.seat_pose(o, 'work', matrix, accepts=['pistol.frame'])   a place another family's part rests, as a full pose
#   CT.path(o, 'peel', points, normals)   CT.zone(o, 'dust', centre, half_size, rot)   CT.wipe(o, 'dust', zone='dust')
#   CT.sequence([...])                        the order parts come off / go on (check.py sweeps it)
#   CT.build_hierarchy('pistol')              parents nodes and empties; call once, after every part and rig exists
#   CT.validate('pistol') -> [problems]       CT.write('pistol', outdir, glb='pistol.glb', ...)
#
# Ids: a part id is '<family>.<part>'; inside a family the short form ('frame') is enough and is expanded.
# Poses are empties (CONTRACT.md): '<node>__clear' is a SIBLING of the node (same parent), every other helper is a
# CHILD of the node. For a part that rides a rig bone, '__clear' hangs on the part's logical parent, so it does not
# move with the parameter.
import bpy, json, math, re, time
from mathutils import Vector, Matrix
import geo as G

KINDS = ('part', 'fastener', 'tool', 'fixture', 'consumable')
MATERIALS = ('steel', 'alloy', 'wood', 'rubber', 'plastic', 'copper', 'glass', 'canvas', 'paper', 'ceramic')
MASSES = ('tiny', 'light', 'medium', 'heavy')
BITS = ('slot', 'cross', 'hex', 'socket', 'pin', 'hand', 'pliers')
HELPERS = ('clear', 'grab', 'tip', 'path', 'mark', 'zone')
MM = 0.001


def full_id(family, pid):
    return pid if '.' in pid else '%s.%s' % (family, pid)


def node_of(pid_full):
    return pid_full.replace('.', '_')


def _get(o):
    return json.loads(o['sh'])


def _put(o, d):
    o['sh'] = json.dumps(d)
    o['sh_id'] = d['id']


def parts(family=None):
    """Part objects of the scene (optionally of one family), by id."""
    out = {}
    for o in bpy.data.objects:
        if 'sh' in o and o.type == 'MESH':
            d = _get(o)
            if family is None or d['family'] == family:
                out[d['id']] = o
    return out


def part(o, family, pid, label, kind='part', parent=None, material='steel', mass='light', item=None, symmetry=1,
         tol_mm=5.0, tol_deg=20.0, held_by=(), steps=(), origin=None, flex=False, loose=False, fixed=False, touches=(), note=None):
    """Register a mesh object as a contract part. origin: world point for the node origin (default: left alone).
    flex: the part deforms when it comes off (wrap, wire twist, lead): the path sweep skips it. loose: a thing that
    lies on the bench and seats nowhere (test card, tool), so it needs no '__clear'. fixed: it is its own node but never
    comes off in this job (a barrel, a trigger on its pin), so it needs no '__clear' either. touches: ids it may be in contact
    with when seated, beyond its parent and held_by (the sweep reports any other contact)."""
    fid = full_id(family, pid)
    if origin is not None:
        G.set_origin(o, origin)
    o.name = node_of(fid); o.data.name = o.name
    d = {'family': family, 'id': fid, 'node': o.name, 'label': label, 'kind': kind,
         'parent': full_id(family, parent) if parent else None, 'item': item, 'material': material, 'mass': mass,
         'seat': {'symmetry': symmetry, 'tol_mm': tol_mm, 'tol_deg': tol_deg},
         'held_by': [full_id(family, h) for h in held_by], 'steps': list(steps), 'flex': bool(flex), 'loose': bool(loose), 'fixed': bool(fixed),
         'touches': [full_id(family, h) for h in touches]}
    if note:
        d['note'] = note
    _put(o, d)
    return o


def fastener(o, family, pid, label, bit, turns, holds, into=None, shank_d=None, **kw):
    """Register a fastener. holds: ids it clamps (the first is the one its head sits on); into: the id it threads or
    presses into; shank_d: shank diameter for the hole check (metres)."""
    kw.setdefault('kind', 'fastener'); kw.setdefault('mass', 'tiny'); kw.setdefault('symmetry', 0)
    kw.setdefault('tol_mm', 3.0); kw.setdefault('tol_deg', 25.0)
    part(o, family, pid, label, **kw)
    d = _get(o)
    d['fastener'] = {'bit': bit, 'turns': turns, 'holds': [full_id(family, h) for h in holds],
                     'into': full_id(family, into) if into else None, 'shank_mm': round(shank_d / MM, 3) if shank_d else None}
    _put(o, d)
    return o


def tool(o, family, pid, label, verbs, tags, **kw):
    kw.setdefault('kind', 'tool'); kw.setdefault('loose', True)
    part(o, family, pid, label, **kw)
    d = _get(o)
    d['tool'] = {'verbs': list(verbs), 'tip': o.name + '__tip', 'tags': list(tags)}
    _put(o, d)
    return o


def update(o, **kw):
    """Change fields of a registered part (for example steps=[...] or held_by=[...])."""
    d = _get(o)
    d.update(kw)
    _put(o, d)
    return o


# ---------------------------------------------------------------------- helper empties
def _empty(name, M, kind='PLAIN_AXES', size=0.004):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_type = kind; e.empty_display_size = size
    e.matrix_world = M
    e['sh_helper'] = name.split('__', 1)[1].split('_')[0]
    e['sh_of'] = name.split('__', 1)[0]
    return e


def _zframe(point, normal, tangent=None):
    z = Vector(normal).normalized()
    t = Vector(tangent) if tangent is not None else (Vector((1, 0, 0)) if abs(z.x) < 0.9 else Vector((0, 1, 0)))
    x = t - z * z.dot(t)
    if x.length < 1e-9:
        x = z.orthogonal()
    x.normalize()
    M = Matrix((x, z.cross(x), z)).transposed().to_4x4()
    M.translation = Vector(point)
    return M


def clear(o, offset=None, matrix=None, rot=None):
    """'<node>__clear': the pose where the part is just clear of what it seats on. offset: world vector from the rest
    pose; rot: extra world rotation (3x3 or 4x4) applied about the part's origin; matrix: the whole world pose."""
    bpy.context.view_layer.update()
    if matrix is None:
        M = o.matrix_world.copy()
        if rot is not None:
            R = Matrix(rot).to_3x3().to_4x4()
            t = M.translation.copy()
            M = Matrix.Translation(t) @ R @ Matrix.Translation(-t) @ M
        if offset is not None:
            M.translation = M.translation + Vector(offset)
    else:
        M = Matrix(matrix)
    return _empty(o.name + '__clear', M, 'ARROWS')


def clear_along(o, dist):
    """'<node>__clear' at `dist` along the part's own +Z (a screw fully backed out, a pin driven out)."""
    bpy.context.view_layer.update()
    z = (o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    return clear(o, offset=z * dist)


def grab(o, point):
    return _empty(o.name + '__grab', Matrix.Translation(Vector(point)), 'SPHERE', 0.003)


def tip(o, point, direction):
    """'<node>__tip': the working point of a tool; its +Z points out of the tool along the working direction."""
    return _empty(o.name + '__tip', _zframe(point, direction), 'SINGLE_ARROW', 0.01)


def mark(o, mid, point, normal=None):
    M = _zframe(point, normal) if normal is not None else Matrix.Translation(Vector(point))
    return _empty('%s__mark_%s' % (o.name, mid), M, 'SPHERE', 0.0015)


def pose_mark(owner, mid, matrix, accepts=()):
    """'<node>__mark_<id>': a mark that is a FULL pose (SEAM.md section 2): a node placed on it takes this empty's
    world transform. matrix: 4x4 world pose. accepts: the part ids it is for. Its entry in parts.json carries
    "pose": true and "accepts". Use it in pairs for a part of another family that seats on `owner`:
    pose_mark(o, 'seat_x', M) and pose_mark(o, 'clear_x', M_clear); check.py sweeps the foreign part between the two
    (sequence event fields 'seat' and 'clear'). A plain mark() stays a point with a normal."""
    e = _empty('%s__mark_%s' % (owner.name, mid), Matrix(matrix), 'ARROWS', 0.012)
    e['sh_pose'] = 1
    e['sh_accepts'] = json.dumps(list(accepts))
    return e


def seat_pose(owner, sid, matrix, accepts=()):
    """'<node>__mark_seat_<id>': pose_mark() with the 'seat_' prefix (kept for the families that already call it)."""
    return pose_mark(owner, 'seat_' + sid, matrix, accepts)


def path(o, pid, points, normals=None):
    """'<node>__path_<id>_<nn>': 8 to 40 ordered empties on the surface along a line to follow. +Z is the surface
    normal when normals are given, +X runs along the path."""
    pts = [Vector(p) for p in points]
    if not 8 <= len(pts) <= 40:
        raise ValueError('path %s on %s has %d points; the contract wants 8 to 40 (use geo.resample)' % (pid, o.name, len(pts)))
    out = []
    for i, p in enumerate(pts):
        tg = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        n = Vector(normals[i]) if normals is not None else Vector((0, 0, 1))
        out.append(_empty('%s__path_%s_%02d' % (o.name, pid, i), _zframe(p, n, tg), 'PLAIN_AXES', 0.002))
    return out


def zone(o, zid, centre, half_size, rot=None):
    """'<node>__zone_<id>': a box to wipe. The empty's local cube -1..1 is the box (its scale holds the half sizes)."""
    R = Matrix(rot).to_3x3() if rot is not None else Matrix.Identity(3)
    if R.determinant() < 0:          # a mirrored frame exports as a negative scale (Unity read -120 x -120 x -4 mm):
        R.col[2] = -R.col[2]         # the box is the same with one axis turned round
    M = Matrix.Translation(Vector(centre)) @ R.to_4x4() @ Matrix.Diagonal((*[abs(x) for x in half_size], 1.0))
    return _empty('%s__zone_%s' % (o.name, zid), M, 'CUBE', 1.0)


def wipe(o, wid, zone=None, label=None):
    """Declare that this part has an as-found surface that is cleaned (bake.py writes the second texture set)."""
    d = _get(o)
    d.setdefault('wipes', []).append({'id': wid, 'zone': '%s__zone_%s' % (o.name, zone) if zone else None, 'label': label})
    _put(o, d)
    return o


def sequence(events):
    """The order in which parts come off and go on, for the assembly path sweep. events: list of dicts
    {'op': 'remove' | 'insert', 'part': id, 'step': 's1.scales', 'group': name or None, 'params': {param: value}}.
    Events that share a group may be done in any order (each is swept against all the others in the group).
    Optional fields (kit/check.py, 20 Nov 18:30):
      'seat', 'clear'  names of two pose marks: the part (usually of another family) is swept between them instead of
                       between its own rest pose and its '__clear' empty, stays at 'seat' afterwards, and from then on
                       rides the part that owns the seat mark.
      'unit': True     on an insert: what rides the part comes with it (its children that are loaded, or exactly what
                       left with it if it was removed earlier in the sequence).
      'among': [...]   family names: only parts of these families are in the way (a thing fitted on the bench, away
                       from the machine it will later go on).
      'expect': [...]  ids it may touch when seated, beyond what the part declares."""
    sc = bpy.context.scene
    fam = sc.get('sh_family', '')
    ev = []
    for e in events:
        e = dict(e)
        e['part'] = full_id(fam, e['part'])
        ev.append(e)
    sc['sh_sequence'] = json.dumps(ev)
    return ev


def begin(family, unit_scale_m=1.0):
    sc = bpy.context.scene
    sc['sh_family'] = family
    sc['sh_unit_scale'] = unit_scale_m
    sc['sh_params'] = '[]'
    sc['sh_sequence'] = '[]'
    sc['sh_absent'] = '[]'


def absent(ids):
    """Parts that are in the GLB at their seated pose but are NOT there in the as-found state (they are fitted during
    the job): the sweep starts without them."""
    sc = bpy.context.scene
    sc['sh_absent'] = json.dumps([full_id(sc['sh_family'], i) for i in ids])


# ---------------------------------------------------------------------- hierarchy
def helpers_of(o):
    pre = o.name + '__'
    return [e for e in bpy.data.objects if e.type == 'EMPTY' and e.name.startswith(pre)]


def _parent_keep(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.parent_type = 'OBJECT'
    child.matrix_parent_inverse = parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    child.matrix_world = mw


def build_hierarchy(family):
    """Parent every part to its contract parent and every helper empty to its place. Parts already parented to a rig
    bone keep that parent."""
    P = parts(family)
    for fid, o in P.items():
        d = _get(o)
        par = P.get(d['parent']) if d['parent'] else None
        if o.parent is None and par is not None:
            _parent_keep(o, par)
        for e in helpers_of(o):
            if e.name.endswith('__clear'):
                tgt = par if (o.parent_type == 'BONE' or o.parent is par) else o.parent
                _parent_keep(e, tgt)
            else:
                _parent_keep(e, o)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------- reading the scene back
def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def entry(o):
    """The parts.json entry of one part object."""
    d = _get(o)
    hs = {e.name: e for e in helpers_of(o)}
    dims = [round(x / MM, 1) for x in o.dimensions]
    e = {'id': d['id'], 'node': d['node'], 'label': d['label'], 'kind': d['kind'], 'parent': d['parent'], 'item': d['item'],
         'material': d['material'], 'mass': d['mass'], 'tris': tris(o), 'size_mm': dims}
    seat = dict(d['seat'])
    if o.name + '__clear' in hs:
        seat = {'clear': o.name + '__clear', **seat}
    e['seat'] = seat
    e['held_by'] = d['held_by']
    if d.get('fastener'):
        e['fastener'] = d['fastener']
    if d.get('tool'):
        e['tool'] = d['tool']
    e['steps'] = d['steps']
    if o.name + '__grab' in hs:
        e['grab'] = o.name + '__grab'
    pp = {}
    for n in sorted(hs):
        m = re.match(re.escape(o.name) + r'__path_(.+)_(\d\d)$', n)
        if m:
            pp.setdefault(m.group(1), []).append(n)
    if pp:
        e['paths'] = [{'id': k, 'nodes': v} for k, v in pp.items()]
    mk = [n for n in sorted(hs) if n.startswith(o.name + '__mark_')]
    if mk:
        e['marks'] = []
        for n in mk:
            m = {'id': n.split('__mark_', 1)[1], 'node': n}
            if hs[n].get('sh_pose'):
                m['pose'] = True
                m['accepts'] = json.loads(hs[n].get('sh_accepts', '[]'))
            e['marks'].append(m)
    zn = [n for n in sorted(hs) if n.startswith(o.name + '__zone_')]
    if zn:
        e['zones'] = [{'id': n.split('__zone_', 1)[1], 'node': n} for n in zn]
    if d.get('wipes'):
        e['wipes'] = d['wipes']
    for k in ('flex', 'loose', 'fixed'):
        if d.get(k):
            e[k] = True
    if d.get('rides'):
        e['rides'] = d['rides']
    if d.get('note'):
        e['note'] = d['note']
    return e


def validate(family, budget=None):
    """Problems with the contract in the open scene, as strings (empty = good)."""
    bad = []
    P = parts(family)
    if not P:
        return ['no parts registered for family %s' % family]
    absent_ids = set(json.loads(bpy.context.scene.get('sh_absent', '[]')))
    for fid, o in P.items():
        d = _get(o)
        if not re.match(r'^%s_[a-z0-9_]+$' % re.escape(family), o.name) or '__' in o.name:
            bad.append('%s: node name must be <family>_<part> in lower snake case' % o.name)
        if d['kind'] not in KINDS: bad.append('%s: kind %s' % (fid, d['kind']))
        if d['material'] not in MATERIALS: bad.append('%s: material %s' % (fid, d['material']))
        if d['mass'] not in MASSES: bad.append('%s: mass %s' % (fid, d['mass']))
        if d['parent'] and d['parent'].split('.')[0] == family and d['parent'] not in P:
            bad.append('%s: parent %s does not exist' % (fid, d['parent']))
        for h in d['held_by']:
            if h.split('.')[0] == family and h not in P:
                bad.append('%s: held_by %s does not exist' % (fid, h))
        has_clear = bpy.data.objects.get(o.name + '__clear') is not None
        if d['parent'] and not d['loose'] and not d.get('fixed') and not has_clear:
            bad.append('%s: seats on %s but has no __clear empty' % (fid, d['parent']))
        if d['kind'] == 'tool' and bpy.data.objects.get(o.name + '__tip') is None:
            bad.append('%s: tool without a __tip empty' % fid)
        if d['kind'] == 'fastener':
            f = d.get('fastener')
            if not f:
                bad.append('%s: fastener without a fastener block' % fid)
            else:
                if f['bit'] not in BITS: bad.append('%s: bit %s' % (fid, f['bit']))
                for h in f['holds']:
                    if h.split('.')[0] == family and h not in P:
                        bad.append('%s: holds %s which does not exist' % (fid, h))
        if abs(o.matrix_world.to_scale().x - 1) > 1e-5 or abs(o.matrix_world.to_scale().y - 1) > 1e-5 or abs(o.matrix_world.to_scale().z - 1) > 1e-5:
            bad.append('%s: node scale is not 1' % fid)
        for w in d.get('wipes', []):
            if w.get('zone') and bpy.data.objects.get(w['zone']) is None:
                bad.append('%s: wipe %s names a missing zone' % (fid, w['id']))
        e = entry(o)
        for p in e.get('paths', []):
            if not 8 <= len(p['nodes']) <= 40:
                bad.append('%s: path %s has %d empties (8 to 40)' % (fid, p['id'], len(p['nodes'])))
    total = sum(tris(o) for o in P.values())
    if budget and total > budget:
        bad.append('family %s has %d triangles, over its budget of %d' % (family, total, budget))
    for e in json.loads(bpy.context.scene.get('sh_sequence', '[]')):
        if e['part'].split('.')[0] == family and e['part'] not in P:
            bad.append('sequence names %s which does not exist' % e['part'])
    return bad


def collect(family):
    P = parts(family)
    order = sorted(P.values(), key=lambda o: (_get(o)['parent'] or '', o.name))
    # parents before children
    out, seen = [], set()

    def walk(pid):
        for o in order:
            d = _get(o)
            if d['parent'] == pid and d['id'] not in seen:
                seen.add(d['id']); out.append(entry(o)); walk(d['id'])
    walk(None)
    for o in order:          # parts whose parent is in another family
        if _get(o)['id'] not in seen:
            out.append(entry(o))
    return out


def write(family, outdir, glb=None, extra=None, stats_extra=None, budget=None):
    """Write parts.json and stats.json for the family in the open scene. Returns (parts dict, stats dict)."""
    import os, numpy as np
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    pl = collect(family)
    pj = {'family': family, 'glb': glb or family + '.glb', 'blender': '.'.join(str(x) for x in bpy.app.version),
          'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'unit_scale_m': sc.get('sh_unit_scale', 1.0),
          'parts': pl, 'params': json.loads(sc.get('sh_params', '[]')),
          'sequence': json.loads(sc.get('sh_sequence', '[]')), 'absent_at_start': json.loads(sc.get('sh_absent', '[]'))}
    if extra:
        pj.update(extra)
    P = parts(family)
    per = {}
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for fid, o in sorted(P.items()):
        co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices]) if o.data.vertices else np.zeros((1, 3))
        per[fid] = {'node': o.name, 'tris': tris(o), 'verts': len(o.data.vertices),
                    'min': [round(float(x), 5) for x in co.min(0)], 'max': [round(float(x), 5) for x in co.max(0)]}
        lo = np.minimum(lo, co.min(0)); hi = np.maximum(hi, co.max(0))
    st = {'family': family, 'tris_total': sum(p['tris'] for p in per.values()), 'budget': budget, 'nodes': len(per),
          'bounds_m': {'min': [round(float(x), 5) for x in lo], 'max': [round(float(x), 5) for x in hi]},
          'helpers': len([e for e in bpy.data.objects if e.type == 'EMPTY' and e.get('sh_helper')]),
          'parts': per}
    if stats_extra:
        st.update(stats_extra)
    os.makedirs(outdir, exist_ok=True)
    json.dump(pj, open(os.path.join(outdir, 'parts.json'), 'w'), indent=1)
    json.dump(st, open(os.path.join(outdir, 'stats.json'), 'w'), indent=1)
    return pj, st
