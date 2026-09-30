"""Dump the transform-relevant structure of binary FBX files as JSON.

Run: blender -b --factory-startup --python fbx_inspect.py -- out.json a.fbx [b.fbx ...]

Reports GlobalSettings (axes, unit scale), each Model's Lcl/Pre/Post transforms,
each Geometry's raw vertex bounds, polygon/triangle counts, UV layer names and
material names, plus the Model->Geometry/Material connections. Uses Blender's
bundled low-level parser only (no import into a scene), so the numbers are
exactly what is stored in the file.
"""
import json
import sys
import array

from io_scene_fbx import parse_fbx


def props70(elem):
    out = {}
    for child in elem.elems:
        if child.id != b"Properties70":
            continue
        for p in child.elems:
            name = p.props[0].decode("utf-8", "replace")
            vals = []
            for v in p.props[4:]:
                vals.append(v.decode("utf-8", "replace") if isinstance(v, bytes) else v)
            out[name] = vals
    return out


def find(elem, key):
    for child in elem.elems:
        if child.id == key:
            return child
    return None


def name_of(elem):
    raw = elem.props[1]
    return raw.split(b"\x00\x01")[0].decode("utf-8", "replace")


def inspect(path):
    root, version = parse_fbx.parse(path)
    result = {"path": path, "version": version}
    gs = find(root, b"GlobalSettings")
    result["globalSettings"] = props70(gs) if gs else None
    objects = find(root, b"Objects")
    by_id = {}
    models, geoms, mats = [], [], []
    for obj in objects.elems:
        uid = obj.props[0]
        if obj.id == b"Model":
            p = props70(obj)
            rec = {"id": uid, "name": name_of(obj), "type": obj.props[2].decode(),
                   "props": {k: v for k, v in p.items() if k in (
                       "Lcl Translation", "Lcl Rotation", "Lcl Scaling", "PreRotation",
                       "PostRotation", "RotationOrder", "RotationOffset", "RotationPivot",
                       "ScalingOffset", "ScalingPivot", "GeometricTranslation",
                       "GeometricRotation", "GeometricScaling", "InheritType")}}
            models.append(rec)
            by_id[uid] = rec
        elif obj.id == b"Geometry":
            verts = find(obj, b"Vertices")
            pvi = find(obj, b"PolygonVertexIndex")
            rec = {"id": uid, "name": name_of(obj)}
            if verts is not None:
                v = verts.props[0]
                n = len(v) // 3
                xs, ys, zs = v[0::3], v[1::3], v[2::3]
                rec["vertices"] = n
                rec["rawBoundsMin"] = [min(xs), min(ys), min(zs)]
                rec["rawBoundsMax"] = [max(xs), max(ys), max(zs)]
            if pvi is not None:
                idx = pvi.props[0]
                polys = 0
                tris = 0
                count = 0
                for i in idx:
                    count += 1
                    if i < 0:
                        polys += 1
                        tris += count - 2
                        count = 0
                rec["polygons"] = polys
                rec["triangles"] = tris
            uvs = []
            for child in obj.elems:
                if child.id == b"LayerElementUV":
                    nm = find(child, b"Name")
                    uvs.append(nm.props[0].decode() if nm else "")
            rec["uvLayers"] = uvs
            normals = [c for c in obj.elems if c.id == b"LayerElementNormal"]
            rec["normalLayers"] = len(normals)
            if normals:
                m = find(normals[0], b"MappingInformationType")
                rec["normalMapping"] = m.props[0].decode() if m else None
            smoothing = [c for c in obj.elems if c.id == b"LayerElementSmoothing"]
            rec["smoothingLayers"] = len(smoothing)
            geoms.append(rec)
            by_id[uid] = rec
        elif obj.id == b"Material":
            rec = {"id": uid, "name": name_of(obj)}
            mats.append(rec)
            by_id[uid] = rec
    conns = find(root, b"Connections")
    links = []
    for c in conns.elems:
        if c.props[0] == b"OO":
            a, b = c.props[1], c.props[2]
            if a in by_id and (b in by_id or b == 0):
                links.append([by_id[a]["name"], by_id[b]["name"] if b in by_id else "<root>"])
    result["models"] = models
    result["geometries"] = geoms
    result["materials"] = mats
    result["connections"] = links
    return result


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[0]
    results = [inspect(p) for p in argv[1:]]
    with open(out, "w") as fh:
        json.dump(results, fh, indent=1, default=str)
    print("wrote", out)


main()
