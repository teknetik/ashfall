"""Minimal glTF-binary writer for terrain meshes (numpy only). Input is in Unity space; glTFast imports glTF (x, y, z)
as Unity (-x, y, z), so X (positions and normals) is negated here and the winding is made counter-clockwise seen from
the normal side in glTF space. One node + mesh per object, one shared material named 'Terrain' (Unity overrides it)."""
import json, struct
import numpy as np


def _pad(b, fill=b'\x00'):
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, objects, generator='ao2 berms expanse'):
    """objects: list of dict(name, P (n,3) Unity, N (n,3) Unity, C (n,4) float or None, UV (n,2) or None, I (m,3) int)."""
    bin_parts = []; offset = 0
    accessors = []; views = []; meshes = []; nodes = []

    def add_view(arr, target):
        nonlocal offset
        data = arr.tobytes()
        views.append(dict(buffer=0, byteOffset=offset, byteLength=len(data), **({'target': target} if target else {})))
        bin_parts.append(_pad(data)); offset += len(_pad(data))
        return len(views) - 1

    for ob in objects:
        P = np.asarray(ob['P'], np.float32).copy(); P[:, 0] *= -1
        N = np.asarray(ob['N'], np.float32).copy(); N[:, 0] *= -1
        I = np.asarray(ob['I'], np.int64).copy()
        # counter-clockwise around the vertex normal (glTF space)
        a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
        fn = np.cross(b - a, c - a); vn = N[I[:, 0]] + N[I[:, 1]] + N[I[:, 2]]
        flip = (fn * vn).sum(1) < 0
        I[flip] = I[flip][:, [0, 2, 1]]
        attrs = {}
        v = add_view(P, 34962)
        accessors.append(dict(bufferView=v, componentType=5126, count=len(P), type='VEC3', min=P.min(0).tolist(), max=P.max(0).tolist()))
        attrs['POSITION'] = len(accessors) - 1
        v = add_view(N, 34962); accessors.append(dict(bufferView=v, componentType=5126, count=len(N), type='VEC3')); attrs['NORMAL'] = len(accessors) - 1
        if ob.get('UV') is not None:
            UV = np.asarray(ob['UV'], np.float32).copy()
            v = add_view(UV, 34962); accessors.append(dict(bufferView=v, componentType=5126, count=len(UV), type='VEC2')); attrs['TEXCOORD_0'] = len(accessors) - 1
        if ob.get('C') is not None:
            C = np.asarray(ob['C'], np.float32)
            v = add_view(C, 34962); accessors.append(dict(bufferView=v, componentType=5126, count=len(C), type='VEC4')); attrs['COLOR_0'] = len(accessors) - 1
        if len(P) < 65536:
            idx = I.astype(np.uint16).ravel(); ct = 5123
        else:
            idx = I.astype(np.uint32).ravel(); ct = 5125
        v = add_view(idx, 34963); accessors.append(dict(bufferView=v, componentType=ct, count=int(idx.size), type='SCALAR'))
        meshes.append(dict(name=ob['name'], primitives=[dict(attributes=attrs, indices=len(accessors) - 1, material=0, mode=4)]))
        nodes.append(dict(name=ob['name'], mesh=len(meshes) - 1))
    gl = dict(asset=dict(version='2.0', generator=generator), scene=0, scenes=[dict(nodes=list(range(len(nodes))))],
              nodes=nodes, meshes=meshes, accessors=accessors, bufferViews=views,
              buffers=[dict(byteLength=offset)],
              materials=[dict(name='Terrain', pbrMetallicRoughness=dict(baseColorFactor=[0.6, 0.5, 0.4, 1], metallicFactor=0, roughnessFactor=1))])
    js = _pad(json.dumps(gl, separators=(',', ':')).encode(), b' ')
    binb = b''.join(bin_parts)
    total = 12 + 8 + len(js) + 8 + len(binb)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(binb), 0x004E4942)); f.write(binb)
    return total
