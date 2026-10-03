"""player_face_20261003: alpha-clipped shell layers for the scalp hair, beard and moustache.
The hair is painted into the Meshy skin texture (like the NPCs); the shells give it volume and a broken silhouette.
Shells are copies of the skin faces under the painted hair (tex/hair_mask.png), offset along the normal and combed
(beard down, scalp hair back), sharing the skin's UVs and vertex groups (so they skin with the head), on one material
'PlayerHairShell' (tex/hair_shell.png, glTF MASK). Each layer carries a vertex-colour alpha (1.0 inner -> 0.55 outer)
that glTF multiplies into the texture alpha, so outer layers are sparser and the strands taper.
build_shells(human, rig) -> shell object (not joined)."""
import bpy, bmesh, numpy as np
from pathlib import Path
from mathutils import Vector

PF = Path('/home/teknetik/code/ao2/art/player_face_20261003')
LAYERS = 4
HAIR_H = 0.008      # scalp hair thickness (m) at full mask
BEARD_H = 0.010     # beard / moustache
COMB = {'hair': 0.9, 'beard': 0.7}   # comb shear per metre of height


def load_mask():
    im = bpy.data.images.load(str(PF / 'tex' / 'hair_mask.png')); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[..., 0], w, h


def shell_material():
    m = bpy.data.materials.get('PlayerHairShell')
    if m: return m
    m = bpy.data.materials.new('PlayerHairShell'); m.use_nodes = True; nt = m.node_tree; bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(PF / 'tex' / 'hair_shell.png'), check_existing=True)
    # The vertex-colour alpha is NOT wired in the node tree: Blender's glTF exporter then exports the named 'Col'
    # attribute (export_vertex_color='NAME') with its alpha for every material, and glTF multiplies COLOR_0 into the
    # base colour. Wiring it here takes the exporter's "alpha-only vertex colour" path, which drops the alpha.
    nt.links.new(t.outputs['Color'], bs.inputs['Base Color'])
    rnd = nt.nodes.new('ShaderNodeMath'); rnd.operation = 'ROUND'      # Blender's glTF exporter reads Round as alphaMode MASK 0.5
    nt.links.new(t.outputs['Alpha'], rnd.inputs[0]); nt.links.new(rnd.outputs[0], bs.inputs['Alpha'])
    bs.inputs['Roughness'].default_value = 0.55
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    m.use_backface_culling = False
    return m


def build_shells(human, rig, eye_z=None):
    mask, W, H = load_mask()
    me = human.data; uvl = me.uv_layers.active.data
    def sample(uv):
        x = min(W - 1, max(0, int(uv.x * W))); y = min(H - 1, max(0, int(uv.y * H)))
        return float(mask[y, x])
    # per-vertex mask (max over its loops) and per-face selection
    vmask = np.zeros(len(me.vertices), np.float32)
    for p in me.polygons:
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index; vmask[vi] = max(vmask[vi], sample(uvl[li].uv))
    # no shells round the eyes (the mask catches brow and lash shadows): skip faces within 3.6 cm of an eyeball centre
    eyes = [o for o in bpy.data.objects if o.type == 'MESH' and 'high-poly' in o.name]
    centres = []
    if eyes:
        ev = [eyes[0].matrix_world @ v.co for v in eyes[0].data.vertices]
        for side in (1, -1):
            pts = [p for p in ev if p.x * side > 0]
            if pts: centres.append(sum(pts, Vector()) / len(pts))
    hw = human.matrix_world
    def near_eye(p): return any((hw @ me.vertices[v].co - c).length < 0.036 for v in p.vertices for c in centres)
    sel = [p.index for p in me.polygons if max(vmask[v] for v in p.vertices) > 0.2 and not near_eye(p)]
    if eye_z is None:
        eye_z = (rig.matrix_world @ rig.data.bones['Head'].head_local).z + 0.07
    src = human.copy(); src.data = human.data.copy(); src.name = 'HairShellSrc'; bpy.context.collection.objects.link(src)
    for mod in list(src.modifiers):
        if mod.type != 'ARMATURE': src.modifiers.remove(mod)
    bm = bmesh.new(); bm.from_mesh(src.data); bm.faces.ensure_lookup_table()
    keep = set(sel)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(src.data); bm.free(); src.data.update()
    # original vertex index map: the bmesh delete keeps order, so rebuild the mask by nearest position in the source
    from mathutils.kdtree import KDTree
    kd = KDTree(len(me.vertices))
    for v in me.vertices: kd.insert(v.co, v.index)
    kd.balance()
    sm = src.data; mw = src.matrix_world
    base_co = [v.co.copy() for v in sm.vertices]; nrm = [v.normal.copy() for v in sm.vertices]
    msk = [vmask[kd.find(v.co)[1]] for v in sm.vertices]
    parts = []
    for k in range(1, LAYERS + 1):
        o = src.copy(); o.data = src.data.copy(); o.name = f'HairShell{k}'; bpy.context.collection.objects.link(o)
        f = k / LAYERS
        for i, v in enumerate(o.data.vertices):
            w = mw @ base_co[i]; n = nrm[i]
            beard = w.z < eye_z - 0.035
            h = (BEARD_H if beard else HAIR_H) * f * (0.35 + 0.65 * min(1.0, msk[i] * 1.4))
            comb = Vector((0, 0, -1)) if beard else Vector((0, 0.8, -0.35)).normalized()
            comb = (comb - n * comb.dot(n)).normalized() if (comb - n * comb.dot(n)).length > 1e-4 else Vector()
            v.co = base_co[i] + n * h + comb * h * COMB['beard' if beard else 'hair']
        ca = o.data.color_attributes.get('Col') or o.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        a = 1.0 - 0.45 * (k - 1) / max(1, LAYERS - 1)
        # outer layers fade out towards the edge of the painted hair, so the silhouette tapers instead of fuzzing
        for i, d in enumerate(ca.data):
            edge = 1.0 if k == 1 else min(1.0, max(0.0, (msk[i] - 0.25) / 0.45))
            d.color = (1, 1, 1, a * (0.25 + 0.75 * edge) if k > 1 else a)
        parts.append(o)
    bpy.data.objects.remove(src)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    sh = bpy.context.view_layer.objects.active; sh.name = 'HairShells'; sh.data.name = 'HairShells'
    sh.data.materials.clear(); sh.data.materials.append(shell_material())
    return sh, {'faces_per_layer': len(sel), 'layers': LAYERS, 'tris': sum(len(p.vertices) - 2 for p in sh.data.polygons)}
