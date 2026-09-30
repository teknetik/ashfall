"""Shared numpy / meshoptimizer helpers for the 29 Sep 2026 LOD pass."""
import json
import time

import ctypes

import numpy as np
import meshoptimizer as mo


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def pack_keys(*cols):
    """Pack several non-negative int columns into one uint64 key (bit widths from the data)."""
    key = np.zeros(len(cols[0]), np.uint64)
    total = 0
    for c in cols:
        c = np.asarray(c, np.int64)
        bits = max(1, int(c.max(initial=0)).bit_length())
        total += bits
        assert total <= 64, "keys too large to pack"
        key = (key << np.uint64(bits)) | c.astype(np.uint64)
    return key


def render_vertices(corner_keys):
    """Unique render vertices from per-corner keys. Returns (unique_first_corner, corner_to_rv)."""
    uniq, first, inverse = np.unique(corner_keys, return_index=True, return_inverse=True)
    return first, inverse.ravel()


_lib = mo._loader.lib
_P_UINT = ctypes.POINTER(ctypes.c_uint)
_P_FLOAT = ctypes.POINTER(ctypes.c_float)
_P_UBYTE = ctypes.POINTER(ctypes.c_ubyte)
_lib.meshopt_simplifyWithAttributes.argtypes = [
    _P_UINT, _P_UINT, ctypes.c_size_t, _P_FLOAT, ctypes.c_size_t, ctypes.c_size_t,
    _P_FLOAT, ctypes.c_size_t, _P_FLOAT, ctypes.c_size_t, _P_UBYTE, ctypes.c_size_t,
    ctypes.c_float, ctypes.c_uint, _P_FLOAT]
_lib.meshopt_simplifyWithAttributes.restype = ctypes.c_size_t
_lib.meshopt_simplify.argtypes = [
    _P_UINT, _P_UINT, ctypes.c_size_t, _P_FLOAT, ctypes.c_size_t, ctypes.c_size_t,
    ctypes.c_size_t, ctypes.c_float, ctypes.c_uint, _P_FLOAT]
_lib.meshopt_simplify.restype = ctypes.c_size_t


def simplify(tris, positions, target_tris, attributes=None, weights=None, lock_border=False,
             prune=False, target_error=1.0, vertex_lock=None):
    """meshoptimizer edge-collapse simplification (direct C call with explicit argtypes).

    Vertices are never moved: the result indexes a subset of the input vertices.
    Returns (tris, absolute_error)."""
    idx = np.ascontiguousarray(tris.ravel(), np.uint32)
    pos = np.ascontiguousarray(positions, np.float32)
    dest = np.zeros_like(idx)
    opts = 0
    if lock_border:
        opts |= mo.SIMPLIFY_LOCK_BORDER
    if prune:
        opts |= mo.SIMPLIFY_PRUNE
    err = ctypes.c_float(0.0)
    if attributes is not None:
        attr = np.ascontiguousarray(attributes, np.float32)
        w = np.ascontiguousarray(weights, np.float32)
        lock_ptr = _P_UBYTE()
        if vertex_lock is not None:
            lock_arr = np.ascontiguousarray(vertex_lock, np.uint8)
            lock_ptr = lock_arr.ctypes.data_as(_P_UBYTE)
        n = _lib.meshopt_simplifyWithAttributes(
            dest.ctypes.data_as(_P_UINT), idx.ctypes.data_as(_P_UINT), idx.size,
            pos.ctypes.data_as(_P_FLOAT), len(pos), 12,
            attr.ctypes.data_as(_P_FLOAT), attr.shape[1] * 4, w.ctypes.data_as(_P_FLOAT), len(w),
            lock_ptr, int(target_tris) * 3, float(target_error), opts, ctypes.byref(err))
    else:
        n = _lib.meshopt_simplify(
            dest.ctypes.data_as(_P_UINT), idx.ctypes.data_as(_P_UINT), idx.size,
            pos.ctypes.data_as(_P_FLOAT), len(pos), 12,
            int(target_tris) * 3, float(target_error), opts, ctypes.byref(err))
    out = dest[:n].reshape(-1, 3).astype(np.int64)
    scale = _lib.meshopt_simplifyScale(pos.ctypes.data_as(_P_FLOAT), len(pos), 12)
    return out, float(err.value) * float(scale)


def optimize_order(tris, vertex_count):
    idx = np.ascontiguousarray(tris.ravel(), np.uint32)
    dest = np.zeros_like(idx)
    mo.optimize_vertex_cache(dest, idx, vertex_count=int(vertex_count))
    return dest.reshape(-1, 3).astype(np.int64)


def face_normals(positions, tris):
    a, b, c = positions[tris[:, 0]], positions[tris[:, 1]], positions[tris[:, 2]]
    n = np.cross(b - a, c - a)
    area2 = np.linalg.norm(n, axis=1)
    return n / np.maximum(area2, 1e-30)[:, None], area2 * 0.5


def edge_stats(tris, weld_ids):
    """Open (boundary) and non-manifold edge counts using welded vertex ids."""
    w = weld_ids[tris]
    e = np.concatenate([w[:, [0, 1]], w[:, [1, 2]], w[:, [2, 0]]])
    e.sort(axis=1)
    e = e[e[:, 0] != e[:, 1]]
    key = e[:, 0].astype(np.int64) * (1 << 31) + e[:, 1]
    _, counts = np.unique(key, return_counts=True)
    return {"edges": int(len(counts)), "boundaryEdges": int((counts == 1).sum()),
            "nonManifoldEdges": int((counts > 2).sum())}


def weld_by_position(positions, decimals=6):
    q = np.round(np.asarray(positions, np.float64), decimals)
    _, inverse = np.unique(q, axis=0, return_inverse=True)
    return inverse.ravel()


def mesh_report(name, positions, tris, normals=None, uv=None, weld_ids=None):
    """Quality statistics for one triangle mesh (render-vertex indexed)."""
    fn, area = face_normals(positions, tris)
    rep = {"name": name, "triangles": int(len(tris)), "renderVertices": int(len(np.unique(tris)))}
    rep["degenerateTriangles"] = int((area < 1e-12).sum())
    rep["surfaceArea"] = float(area.sum())
    used = positions[np.unique(tris)]
    rep["boundsMin"] = used.min(0).tolist()
    rep["boundsMax"] = used.max(0).tolist()
    if normals is not None:
        vn = normals[tris].mean(axis=1)
        dots = (vn * fn).sum(1)
        valid = area > 1e-12
        rep["facesOpposingVertexNormals"] = int(((dots < 0) & valid).sum())
        rep["facesOpposingVertexNormalsAreaPct"] = float(100 * area[(dots < 0) & valid].sum() / max(area.sum(), 1e-30))
    if uv is not None:
        u = uv[np.unique(tris)]
        rep["uvMin"] = u.min(0).tolist()
        rep["uvMax"] = u.max(0).tolist()
    if weld_ids is not None:
        rep.update(edge_stats(tris, weld_ids))
    return rep


def smooth_normals_angle(positions, tris, weld_ids, angle_deg=60.0):
    """Per-corner normals: area-weighted average of adjacent faces within angle of the corner's face."""
    fn, area = face_normals(positions, tris)
    cos_t = np.cos(np.radians(angle_deg))
    T = len(tris)
    corner_w = weld_ids[tris].ravel()
    corner_face = np.repeat(np.arange(T), 3)
    order = np.argsort(corner_w, kind="stable")
    sw = corner_w[order]
    bounds = np.flatnonzero(np.diff(sw)) + 1
    groups = np.split(order, bounds)
    out = np.zeros((T * 3, 3))
    weighted = fn * area[:, None]
    for g in groups:
        faces = corner_face[g]
        fns = fn[faces]
        sim = fns @ fns.T >= cos_t
        acc = sim.astype(np.float64) @ weighted[faces]
        out[g] = acc
    out /= np.maximum(np.linalg.norm(out, axis=1), 1e-30)[:, None]
    return out.reshape(T, 3, 3)


def dump_json(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1)
