"""Minimal glTF-binary reader for the basin chunks (numpy only). Positions/normals stay in glTF space (Y up,
right-handed); Unity (glTFast) space is (-x, y, z)."""
import json, struct
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    data = open(path, 'rb').read()
    magic, ver, length = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67
    off = 12; js = None; binc = None
    while off < length:
        clen, ctype = struct.unpack_from('<II', data, off); off += 8
        chunk = data[off:off + clen]; off += clen
        if ctype == 0x4E4F534A: js = json.loads(chunk)
        elif ctype == 0x004E4942: binc = chunk
    return js, binc


def accessor(js, binc, i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    dt = CT[a['componentType']]; n = NC[a['type']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0) or np.dtype(dt).itemsize * n
    count = a['count']
    raw = np.frombuffer(binc, dtype=np.uint8, count=stride * (count - 1) + np.dtype(dt).itemsize * n, offset=start)
    arr = np.lib.stride_tricks.as_strided(raw.view(dt) if stride % np.dtype(dt).itemsize == 0 and False else raw, shape=(count,), strides=(stride,))
    out = np.empty((count, n), dtype=dt)
    for k in range(count):
        out[k] = np.frombuffer(binc, dtype=dt, count=n, offset=start + k * stride)
    if a.get('normalized'):
        out = out.astype(np.float64) / np.iinfo(dt).max
    return out


def meshes(path):
    js, binc = read_glb(path)
    res = []
    for node in js['nodes']:
        if 'mesh' not in node: continue
        m = js['meshes'][node['mesh']]
        for p in m['primitives']:
            at = p['attributes']
            d = dict(node=node['name'], mesh=m['name'], material=p.get('material'),
                     attrs={k: js['accessors'][v] for k, v in at.items()})
            d['P'] = accessor(js, binc, at['POSITION']).astype(np.float64)
            if 'NORMAL' in at: d['N'] = accessor(js, binc, at['NORMAL']).astype(np.float64)
            if 'COLOR_0' in at: d['C'] = accessor(js, binc, at['COLOR_0'])
            if 'TEXCOORD_0' in at: d['UV'] = accessor(js, binc, at['TEXCOORD_0'])
            d['I'] = accessor(js, binc, p['indices']).reshape(-1, 3).astype(np.int64)
            d['T'] = node.get('translation'); d['R'] = node.get('rotation'); d['S'] = node.get('scale')
            res.append(d)
    return js, res
