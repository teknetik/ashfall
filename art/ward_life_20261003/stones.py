"""Loose stone geometry for the Ward life pass (3 Oct 2026): gabion fill, spilled scree, rubble.

add_stone() builds one stone into a bmesh: an icosphere squashed to an ellipsoid, roughened with 3D noise and cut by
2-4 random planes so it reads as quarried/broken rock (gabion fill is angular, 10-25 cm). kind="block" makes a broken
dressed-block fragment instead (salvaged masonry used as fill: Ward rebuilt its baskets with the rubble of the Fall).
Coordinates are whatever frame the caller works in; `up` only orients the flattest axis.
"""
import math
import bmesh
from mathutils import Vector, Matrix, Euler
from mathutils import noise


def _shape_sphere(p, size, seed, cuts, abc):
    a, b, c = abc
    q = Vector((p.x * a, p.y * b, p.z * c)) * size * 0.5
    n = noise.noise(p * 2.6 + Vector((seed, seed * 0.7, seed * 1.3)))
    q += p.normalized() * size * 0.075 * n
    for (nv, d) in cuts:
        t = q.dot(nv) - d * size
        if t > 0:
            q -= nv * t
    return q


def _shape_block(p, size, seed, dims):
    m = max(abs(p.x), abs(p.y), abs(p.z)) or 1.0
    q = Vector((p.x / m * dims[0], p.y / m * dims[1], p.z / m * dims[2])) * 0.5 * size
    # rounded arrises + one broken face (the fracture side is rough)
    q = q.lerp(p.normalized() * q.length, 0.18)
    n = noise.noise(p * 3.1 + Vector((seed, 2 * seed, 0.5)))
    rough = 0.05 if p.x > 0.3 else 0.015
    q += p.normalized() * size * rough * n
    return q


def add_stone(bm, centre, size, rng, subdiv=2, kind="rock", rot=None, flatten_up=None):
    """Add one stone (nominal diameter `size` metres) to bm at `centre`. Returns the new faces."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    vs = res["verts"]
    seed = rng.uniform(0, 100)
    if kind == "block":
        dims = (1.0, rng.uniform(0.45, 0.7), rng.uniform(0.4, 0.6))
        shape = lambda p: _shape_block(p, size, seed, dims)
    else:
        cuts = []
        for _ in range(rng.randint(2, 4)):
            nv = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            cuts.append((nv, rng.uniform(0.2, 0.36)))
        abc = (1.0, rng.uniform(0.62, 0.95), rng.uniform(0.45, 0.78))
        shape = lambda p: _shape_sphere(p, size, seed, cuts, abc)
    R = (rot if rot is not None else Euler((rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 6.3)))).to_matrix()
    if flatten_up is not None:
        # lay the flattest (local z) axis along `up`, keep a random spin about it
        up = Vector(flatten_up).normalized()
        R = up.to_track_quat("Z", "Y").to_matrix() @ Euler((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, 6.3))).to_matrix()
    c = Vector(centre)
    for v in vs:
        v.co = c + R @ shape(v.co.copy())
    faces = list({f for v in vs for f in v.link_faces})
    for f in faces:
        f.smooth = True
    return faces
