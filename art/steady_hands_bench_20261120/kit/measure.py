# kit/measure.py: measuring a skin or a build. Bounds, silhouettes as masks, section rows, circle fits.
# Used to hold a rebuilt object to the outline of an existing one (the scrap pistol against the Meshy mesh).
import bpy, bmesh, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# view name -> (ray direction, image-right axis, image-up axis); a mask pixel is 1 where a ray along the direction hits
VIEWS = {
    'side': ((0, 1, 0), (1, 0, 0), (0, 0, 1)),     # looking along +Y: columns X, rows Z
    'top': ((0, 0, -1), (1, 0, 0), (0, 1, 0)),     # looking down: columns X, rows Y
    'front': ((1, 0, 0), (0, 1, 0), (0, 0, 1)),    # looking along +X: columns Y, rows Z
}


def world_bvh(objs):
    """One BVH of several objects in world space (evaluated meshes)."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [tuple(off + i for i in p.vertices) for p in me.polygons]
        oe.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), verts


def bounds(objs):
    _, verts = world_bvh(objs)
    a = np.array([tuple(v) for v in verts])
    return a.min(0), a.max(0)


def silhouette(objs, view, lo, hi, step=0.0005):
    """Binary mask of the projection of objs in a view. lo, hi: world box corners; step: metres per pixel.
    Returns (mask[rows, cols], origin (u0, v0), step). Row 0 is the lowest v."""
    d, ua, va = (Vector(x) for x in VIEWS[view])
    tree, _ = world_bvh(objs)
    lo, hi = Vector(lo), Vector(hi)
    u0, u1 = sorted((lo.dot(ua), hi.dot(ua)))
    v0, v1 = sorted((lo.dot(va), hi.dot(va)))
    far = 2.0
    nu = int(round((u1 - u0) / step)) + 1
    nv = int(round((v1 - v0) / step)) + 1
    m = np.zeros((nv, nu), np.uint8)
    for j in range(nv):
        for i in range(nu):
            o = ua * (u0 + i * step) + va * (v0 + j * step) - d * far
            if tree.ray_cast(o, d, far * 2)[0] is not None:
                m[j, i] = 1
    return m, (u0, v0), step


def compare_masks(a, b, step):
    """IoU, the area that differs (cm2) and the largest distance (mm) from a pixel that differs to the other outline."""
    inter = int((a & b).sum()); union = int((a | b).sum())
    diff = (a ^ b).astype(bool)
    worst = 0.0
    if diff.any():
        # distance of each differing pixel to the nearest pixel where the masks agree and are filled / empty
        from collections import deque
        agree = ~diff
        dist = np.full(a.shape, -1, np.int32)
        q = deque()
        ys, xs = np.nonzero(agree)
        for y, x in zip(ys, xs):
            dist[y, x] = 0
        # seed only pixels next to a differing pixel, then breadth-first into the differing region
        H, W = a.shape
        for y, x in zip(*np.nonzero(diff)):
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and agree[yy, xx]:
                    dist[y, x] = 1; q.append((y, x)); break
        while q:
            y, x = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and dist[yy, xx] < 0:
                    dist[yy, xx] = dist[y, x] + 1; q.append((yy, xx))
        worst = float(dist[diff].max()) * step * 1000
    return {'iou': round(inter / max(1, union), 4), 'diff_cm2': round(float(diff.sum()) * step * step * 1e4, 2),
            'max_dev_mm': round(worst, 2)}


def save_mask_png(path, masks, colours=((255, 80, 60), (60, 160, 255))):
    """Overlay up to two masks (first red, second blue, both = grey) as a PNG, row 0 at the bottom."""
    a = masks[0].astype(bool); b = masks[1].astype(bool) if len(masks) > 1 else np.zeros_like(a)
    H, W = a.shape
    img = np.full((H, W, 4), 1.0, np.float32)
    img[a & ~b, :3] = np.array(colours[0]) / 255
    img[b & ~a, :3] = np.array(colours[1]) / 255
    img[a & b, :3] = 0.45
    im = bpy.data.images.new('_mask', W, H, alpha=True)
    im.pixels.foreach_set(img.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)


def fit_circle(pts):
    """Least-squares circle through 2D points: (cx, cy, r, rms)."""
    P = np.array(pts, float)
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    r = math.sqrt(c + cx * cx + cy * cy)
    rms = float(np.sqrt(((np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r) ** 2).mean()))
    return float(cx), float(cy), r, rms


def section_ring(tree, x, centre, r_start=0.06, n=72):
    """Points where rays cast inward toward (y, z) = centre at station x first hit: the outer section there."""
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        d = Vector((0, math.cos(a), math.sin(a)))
        o = Vector((x, centre[0], centre[1])) + d * r_start
        h = tree.ray_cast(o, -d, r_start)[0]
        if h is not None:
            out.append((h.y, h.z))
    return out
