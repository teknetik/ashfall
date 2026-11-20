#!/usr/bin/env python3
"""Meshy's remeshed characters ship near-flat vertex normals (median angle between a vertex normal and its triangle's
normal ~6 deg, the three normals of a triangle ~7.6 deg apart; positions split ~3x), which renders as visible facets
on faces in Unity. This rewrites the NORMAL accessor in place with smooth normals: angle-weighted face normals averaged
over every vertex sharing a position (UV/normal seams welded), keeping hard edges sharper than CREASE degrees.
Everything else in the file (UVs, skin, textures, animation) is byte-identical.
Usage: smooth_normals.py in.glb out.glb [crease_deg=60]"""
import json, struct, sys
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
crease = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
b = bytearray(open(src, 'rb').read())
jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
bl = struct.unpack('<I', b[o:o + 4])[0]; base = o + 8


def view(i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
    off = base + v.get('byteOffset', 0) + a.get('byteOffset', 0)
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16}[a['componentType']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    assert v.get('byteStride', n * np.dtype(dt).itemsize) == n * np.dtype(dt).itemsize
    return off, dt, n, a['count']


done = set()
for mesh in j['meshes']:
    for prim in mesh['primitives']:
        ni = prim['attributes']['NORMAL']
        if ni in done: continue
        done.add(ni)
        po, pdt, _, pc = view(prim['attributes']['POSITION']); P = np.frombuffer(bytes(b[po:po + pc * 12]), np.float32).reshape(-1, 3).astype(np.float64)
        io, idt, _, ic = view(prim['indices']); I = np.frombuffer(bytes(b[io:io + ic * np.dtype(idt).itemsize]), idt).reshape(-1, 3).astype(np.int64)
        no, _, _, nc = view(ni); N0 = np.frombuffer(bytes(b[no:no + nc * 12]), np.float32).reshape(-1, 3)
        # angle-weighted face normals per corner
        e = [P[I[:, (k + 1) % 3]] - P[I[:, k]] for k in range(3)]
        fn = np.cross(e[0], -e[2]); fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-20
        ang = []
        for k in range(3):
            a = e[k]; c = -e[(k + 2) % 3]
            cos = (a * c).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(c, axis=1) + 1e-20)
            ang.append(np.arccos(np.clip(cos, -1, 1)))
        # position groups
        _, grp = np.unique(P.round(6), axis=0, return_inverse=True); grp = grp.ravel()
        G = grp.max() + 1
        # pass 1: plain smooth normal per position group
        acc = np.zeros((G, 3))
        for k in range(3): np.add.at(acc, grp[I[:, k]], fn * ang[k][:, None])
        gn = acc / (np.linalg.norm(acc, axis=1, keepdims=True) + 1e-20)
        # pass 2: per vertex, only faces within the crease angle of that vertex's own incident faces
        own = np.zeros((len(P), 3))
        for k in range(3): np.add.at(own, I[:, k], fn * ang[k][:, None])
        own /= np.linalg.norm(own, axis=1, keepdims=True) + 1e-20
        cosc = np.cos(np.radians(crease))
        out = np.zeros((len(P), 3))
        # each corner contributes its face normal to every vertex of its position group whose own normal is close
        order = np.argsort(grp); gs = grp[order]
        starts = np.searchsorted(gs, np.arange(G)); ends = np.searchsorted(gs, np.arange(G), side='right')
        corner_v = I.ravel(); corner_f = np.repeat(np.arange(len(I)), 3); corner_a = np.stack(ang, 1).ravel()
        # faces per group
        cg = grp[corner_v]; co = np.argsort(cg); cgs = cg[co]
        cs = np.searchsorted(cgs, np.arange(G)); ce = np.searchsorted(cgs, np.arange(G), side='right')
        for g in range(G):
            verts = order[starts[g]:ends[g]]
            corners = co[cs[g]:ce[g]]
            f = fn[corner_f[corners]] * corner_a[corners][:, None]
            fu = fn[corner_f[corners]]
            for v in verts:
                m = (fu @ own[v]) > cosc
                s = f[m].sum(0) if m.any() else own[v]
                out[v] = s
        out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-20
        bad = ~np.isfinite(out).all(1) | (np.linalg.norm(out, axis=1) < .5); out[bad] = N0[bad]
        before = np.degrees(np.arccos(np.clip((N0[I[:, 0]] * fn).sum(1), -1, 1)))
        after = np.degrees(np.arccos(np.clip((out[I[:, 0]] * fn).sum(1), -1, 1)))
        b[no:no + nc * 12] = out.astype(np.float32).tobytes()
        print(f'normals {nc}: groups {G}, crease {crease}, vertex-vs-face angle median {np.median(before):.2f} -> {np.median(after):.2f} deg, '
              f'triangle normal spread {np.median(np.degrees(np.arccos(np.clip((N0[I[:,0]]*N0[I[:,1]]).sum(1),-1,1)))):.2f} -> '
              f'{np.median(np.degrees(np.arccos(np.clip((out[I[:,0]]*out[I[:,1]]).sum(1),-1,1)))):.2f}')
open(dst, 'wb').write(b)
