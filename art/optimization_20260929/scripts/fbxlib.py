"""Minimal FBX 'surgery' helpers built on Blender's bundled binary FBX codec.

SUPERSEDED FOR DELIVERABLES (30 Sep 2026): files written by write_surgery() were rejected by
Unity's FBX SDK ("File is corrupted"). Root cause: _add_prop mapped FBX type 'C' (char/bool,
e.g. Model "Shading") to encode_bin.add_bool, which emits Blender's internal code 'B' - not a
valid FBX property type (see scripts/fbx_typecode_audit.py). The mapping is fixed below
('C' -> add_char), but the shipped FBX files are now written by Blender's official exporter
(reexport_blender.py); the read helpers remain in use for inspection and verification.

The optimized LODs are written by cloning the *source* FBX element tree
(header, GlobalSettings axes/units, Model transforms, Material names,
connections) and replacing only Geometry payloads. That guarantees that the
new files import in Unity with exactly the same node transform, unit scale and
material slot names as the source when given the same ModelImporter settings.

Runs under a normal CPython with numpy (no bpy needed).
"""
import array
import importlib
import sys
import types

import numpy as np

ADDON_DIR = "/usr/share/blender/5.2/scripts/addons_core/io_scene_fbx"

if "fbxcodec" not in sys.modules:
    pkg = types.ModuleType("fbxcodec")
    pkg.__path__ = [ADDON_DIR]
    sys.modules["fbxcodec"] = pkg
parse_fbx = importlib.import_module("fbxcodec.parse_fbx")
encode_bin = importlib.import_module("fbxcodec.encode_bin")


# --------------------------------------------------------------------------- read

def load(path):
    root, version = parse_fbx.parse(path)
    return root, version


def child(elem, key):
    for c in elem.elems:
        if c.id == key:
            return c
    return None


def children(elem, key):
    return [c for c in elem.elems if c.id == key]


def obj_name(elem):
    return elem.props[1].split(b"\x00\x01")[0].decode("utf-8", "replace")


def objects(root, kind):
    objs = child(root, b"Objects")
    return [o for o in objs.elems if o.id == kind]


def arr(a, dtype):
    return np.frombuffer(a, dtype=dtype) if isinstance(a, array.array) else np.asarray(a, dtype=dtype)


def read_geometry(geom):
    """Return a dict with numpy arrays for a Blender-style FBX mesh Geometry."""
    out = {"name": obj_name(geom)}
    out["cp"] = arr(child(geom, b"Vertices").props[0], np.float64).reshape(-1, 3)
    pvi = arr(child(geom, b"PolygonVertexIndex").props[0], np.int32)
    ends = pvi < 0
    out["corner_cp"] = np.where(ends, ~pvi, pvi).astype(np.int64)
    end_idx = np.nonzero(ends)[0]
    starts = np.concatenate([[0], end_idx[:-1] + 1])
    out["poly_start"] = starts
    out["poly_size"] = end_idx - starts + 1
    layers = {}
    for c in geom.elems:
        if not c.id.startswith(b"LayerElement"):
            continue
        rec = {"kind": c.id.decode(), "children": {}}
        for sub in c.elems:
            if len(sub.props) == 1 and isinstance(sub.props[0], array.array):
                rec["children"][sub.id.decode()] = sub.props[0]
            elif sub.props:
                v = sub.props[0]
                rec["children"][sub.id.decode()] = v.decode() if isinstance(v, bytes) else v
        layers.setdefault(c.id.decode(), []).append(rec)
    out["layers"] = layers
    return out


def corner_attribute(geom_data, kind, key, index_key, width, layer=0):
    """Expand a layer element to one value per polygon corner."""
    rec = geom_data["layers"][kind][layer]["children"]
    mapping = rec["MappingInformationType"]
    ref = rec["ReferenceInformationType"]
    values = arr(rec[key], np.float64).reshape(-1, width)
    if ref in ("IndexToDirect", "Index") and index_key in rec:
        index = arr(rec[index_key], np.int32).astype(np.int64)
    else:
        index = None
    if mapping == "ByPolygonVertex":
        return values[index] if index is not None else values
    if mapping in ("ByVertice", "ByVertex"):
        per_cp = values[index] if index is not None else values
        return per_cp[geom_data["corner_cp"]]
    if mapping == "ByPolygon":
        per_poly = values[index] if index is not None else values
        return np.repeat(per_poly, geom_data["poly_size"], axis=0)
    if mapping == "AllSame":
        return np.repeat(values[:1], len(geom_data["corner_cp"]), axis=0)
    raise ValueError(f"unsupported mapping {mapping} for {kind}")


def triangulate(poly_start, poly_size):
    """Fan-triangulate polygons; returns (T,3) corner indices."""
    tri_counts = poly_size - 2
    total = int(tri_counts.sum())
    poly_of_tri = np.repeat(np.arange(len(poly_start)), tri_counts)
    first_tri = np.concatenate([[0], np.cumsum(tri_counts)[:-1]])
    k = np.arange(total) - first_tri[poly_of_tri]
    s = poly_start[poly_of_tri]
    return np.stack([s, s + k + 1, s + k + 2], axis=1), poly_of_tri


# -------------------------------------------------------------------------- write

def _add_prop(e, value, t):
    t = chr(t) if isinstance(t, int) else t
    if t == "Y":
        e.add_int16(value)
    elif t == "C":
        # FBX 'C' is a 1-byte char/bool; encode_bin.add_bool would write the non-FBX code 'B'
        e.add_char(value if isinstance(value, bytes) else (b"\x01" if value else b"\x00"))
    elif t == "I":
        e.add_int32(value)
    elif t == "L":
        e.add_int64(value)
    elif t == "F":
        e.add_float32(value)
    elif t == "D":
        e.add_float64(value)
    elif t == "S":
        e.add_string(value if isinstance(value, bytes) else value.encode())
    elif t == "R":
        e.add_bytes(value)
    elif t == "i":
        e.add_int32_array(value)
    elif t == "l":
        e.add_int64_array(value)
    elif t == "f":
        e.add_float32_array(value)
    elif t == "d":
        e.add_float64_array(value)
    elif t == "b":
        e.add_bool_array(value)
    elif t == "c":
        e.add_byte_array(value)
    else:
        raise ValueError(f"unknown FBX prop type {t!r}")


def to_writable(elem):
    e = encode_bin.FBXElem(elem.id)
    for value, t in zip(elem.props, elem.props_type):
        _add_prop(e, value, t)
    for c in elem.elems:
        e.elems.append(to_writable(c))
    return e


def new_elem(eid, *typed_props):
    e = encode_bin.FBXElem(eid)
    for t, v in typed_props:
        _add_prop(e, v, t)
    return e


def build_geometry_elem(template, name, cp, corner_cp, poly_size, normals=None,
                        uv=None, uv_name="UVMap", extra_corner_layers=None):
    """Clone a Geometry element from a parsed template, replacing its mesh data.

    cp: (V,3) control points; corner_cp: (C,) cp index per corner; poly_size: (P,)
    normals: (C,3) per-corner normals written ByPolygonVertex/Direct.
    uv: (C,2) per-corner UVs written ByPolygonVertex/IndexToDirect (deduplicated).
    extra_corner_layers: {LayerElementTangent: (C,3), ...} optional.
    The template's non-mesh children (Properties70, GeometryVersion, material
    layer, Layer table) are preserved; Edges/Smoothing layers are dropped because
    they would no longer match the new topology.
    """
    uid = template.props[0]
    g = encode_bin.FBXElem(b"Geometry")
    g.add_int64(uid)
    g.add_string(name.encode() + b"\x00\x01Geometry")
    g.add_string(b"Mesh")

    ends = np.cumsum(poly_size) - 1
    pvi = corner_cp.astype(np.int32).copy()
    pvi[ends] = ~pvi[ends]

    kept_layer_kinds = set()
    for c in template.elems:
        cid = c.id
        if cid == b"Vertices":
            g.elems.append(new_elem(b"Vertices", ("d", np.ascontiguousarray(cp, np.float64).ravel())))
        elif cid == b"PolygonVertexIndex":
            g.elems.append(new_elem(b"PolygonVertexIndex", ("i", pvi)))
        elif cid in (b"Edges",):
            continue
        elif cid == b"LayerElementNormal":
            if normals is None:
                continue
            kept_layer_kinds.add(b"LayerElementNormal")
            n = encode_bin.FBXElem(b"LayerElementNormal")
            n.add_int32(0)
            n.elems.append(new_elem(b"Version", ("I", 101)))
            n.elems.append(new_elem(b"Name", ("S", b"")))
            n.elems.append(new_elem(b"MappingInformationType", ("S", b"ByPolygonVertex")))
            n.elems.append(new_elem(b"ReferenceInformationType", ("S", b"Direct")))
            n.elems.append(new_elem(b"Normals", ("d", np.ascontiguousarray(normals, np.float64).ravel())))
            g.elems.append(n)
        elif cid == b"LayerElementUV":
            if uv is None:
                continue
            kept_layer_kinds.add(b"LayerElementUV")
            uvq = np.round(np.asarray(uv, np.float64), 7)
            uniq, inverse = np.unique(uvq, axis=0, return_inverse=True)
            u = encode_bin.FBXElem(b"LayerElementUV")
            u.add_int32(0)
            u.elems.append(new_elem(b"Version", ("I", 101)))
            u.elems.append(new_elem(b"Name", ("S", uv_name.encode())))
            u.elems.append(new_elem(b"MappingInformationType", ("S", b"ByPolygonVertex")))
            u.elems.append(new_elem(b"ReferenceInformationType", ("S", b"IndexToDirect")))
            u.elems.append(new_elem(b"UV", ("d", np.ascontiguousarray(uniq, np.float64).ravel())))
            u.elems.append(new_elem(b"UVIndex", ("i", inverse.ravel().astype(np.int32))))
            g.elems.append(u)
        elif cid in (b"LayerElementTangent", b"LayerElementBinormal"):
            key = cid.decode()
            if not extra_corner_layers or key not in extra_corner_layers:
                continue
            kept_layer_kinds.add(cid)
            data_key = b"Tangents" if cid == b"LayerElementTangent" else b"Binormals"
            t = encode_bin.FBXElem(cid)
            t.add_int32(0)
            t.elems.append(new_elem(b"Version", ("I", 101)))
            t.elems.append(new_elem(b"Name", ("S", uv_name.encode())))
            t.elems.append(new_elem(b"MappingInformationType", ("S", b"ByPolygonVertex")))
            t.elems.append(new_elem(b"ReferenceInformationType", ("S", b"Direct")))
            t.elems.append(new_elem(data_key, ("d", np.ascontiguousarray(extra_corner_layers[key], np.float64).ravel())))
            g.elems.append(t)
        elif cid == b"LayerElementColor":
            if not extra_corner_layers or "LayerElementColor" not in extra_corner_layers:
                continue
            kept_layer_kinds.add(cid)
            col = np.round(np.asarray(extra_corner_layers["LayerElementColor"], np.float64), 6)
            uniq, inverse = np.unique(col, axis=0, return_inverse=True)
            name_elem = child(c, b"Name")
            k = encode_bin.FBXElem(cid)
            k.add_int32(0)
            k.elems.append(new_elem(b"Version", ("I", 101)))
            k.elems.append(new_elem(b"Name", ("S", name_elem.props[0] if name_elem else b"Col")))
            k.elems.append(new_elem(b"MappingInformationType", ("S", b"ByPolygonVertex")))
            k.elems.append(new_elem(b"ReferenceInformationType", ("S", b"IndexToDirect")))
            k.elems.append(new_elem(b"Colors", ("d", np.ascontiguousarray(uniq, np.float64).ravel())))
            k.elems.append(new_elem(b"ColorIndex", ("i", inverse.ravel().astype(np.int32))))
            g.elems.append(k)
        elif cid in (b"LayerElementSmoothing", b"LayerElementEdgeCrease", b"LayerElementVisibility"):
            continue
        elif cid == b"LayerElementMaterial":
            kept_layer_kinds.add(cid)
            g.elems.append(to_writable(c))
        elif cid == b"Layer":
            layer = encode_bin.FBXElem(b"Layer")
            for value, t in zip(c.props, c.props_type):
                _add_prop(layer, value, t)
            for sub in c.elems:
                if sub.id == b"LayerElement":
                    kind = child(sub, b"Type").props[0]
                    if kind not in kept_layer_kinds:
                        continue
                layer.elems.append(to_writable(sub))
            g.elems.append(layer)
        else:
            g.elems.append(to_writable(c))
    return g


def write_surgery(src_root, version, out_path, replacements, model_renames=None,
                  drop_kinds=(b"Texture", b"Video")):
    """Write a copy of src_root replacing Geometry elements.

    replacements: {geometry_uid: writable Geometry FBXElem}
    model_renames: {old model name: new model name}
    drop_kinds: object kinds removed together with their connections. Textures and
    embedded Video payloads are dropped by default (the runtime material is assigned
    in Unity; the Material node and its slot name are kept).
    """
    model_renames = model_renames or {}
    objs = child(src_root, b"Objects")
    removed = {o.props[0] for o in objs.elems if o.id in drop_kinds}
    kind_counts = {}
    for o in objs.elems:
        if o.id not in drop_kinds:
            kind_counts[o.id] = kind_counts.get(o.id, 0) + 1
    root_w = encode_bin.FBXElem(b"")
    for top in src_root.elems:
        if top.id == b"Objects":
            ow = encode_bin.FBXElem(b"Objects")
            for o in top.elems:
                uid = o.props[0] if o.props else None
                if uid in removed:
                    continue
                if o.id == b"Geometry" and uid in replacements:
                    ow.elems.append(replacements[uid])
                elif o.id == b"Model" and obj_name(o) in model_renames:
                    mw = to_writable(o)
                    mw.props.clear()
                    mw.props_type.clear()
                    mw.add_int64(uid)
                    mw.add_string(model_renames[obj_name(o)].encode() + b"\x00\x01Model")
                    mw.add_string(o.props[2])
                    ow.elems.append(mw)
                else:
                    ow.elems.append(to_writable(o))
            root_w.elems.append(ow)
        elif top.id == b"Connections":
            cw = encode_bin.FBXElem(b"Connections")
            for c in top.elems:
                if c.props[1] in removed or c.props[2] in removed:
                    continue
                cw.elems.append(to_writable(c))
            root_w.elems.append(cw)
        elif top.id == b"Definitions":
            dw = encode_bin.FBXElem(b"Definitions")
            total = 0
            for d in top.elems:
                if d.id == b"ObjectType":
                    kind = d.props[0]
                    if kind in drop_kinds:
                        continue
                    tw = to_writable(d)
                    if kind != b"GlobalSettings":
                        for sub in tw.elems:
                            if sub.id == b"Count":
                                sub.props.clear()
                                sub.props_type.clear()
                                sub.add_int32(kind_counts.get(kind, 0))
                        total += kind_counts.get(kind, 0)
                    else:
                        total += 1
                    dw.elems.append(tw)
                else:
                    dw.elems.append(to_writable(d))
            for sub in dw.elems:
                if sub.id == b"Count":
                    sub.props.clear()
                    sub.props_type.clear()
                    sub.add_int32(total)
            root_w.elems.append(dw)
        else:
            root_w.elems.append(to_writable(top))
    encode_bin.write(out_path, root_w, version)
