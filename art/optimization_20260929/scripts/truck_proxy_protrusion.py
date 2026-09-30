"""Signed deviation of shadow-caster candidates from the source surface (mm, scene scale).

Positive = caster surface outside the visible source surface (would self-shadow the
visible LOD in the shadow map if larger than the URP depth/normal bias)."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import meshtools as mt
from truck_transfer import Source, normalize
W = 6.1975354 * 0.65 * 1000
src = Source()
rng = np.random.default_rng(3)
out = {}
cands = {"ShadowProxy": np.load("cache/truck_ShadowProxy.npz"),
         "LOD2": np.load("cache/truck_LOD2_geometry.npz"), "LOD1": np.load("cache/truck_LOD1_geometry.npz"),
         "meshopt160k": np.load("cache/truck_LOD0_baked_geometry.npz"), "meshopt40k": np.load("cache/truck_LOD1_meshopt_geometry.npz")}
inset = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
for name, d in cands.items():
    p = d["positions"].astype(np.float64); t = d["tris"].astype(np.int64)
    if inset and name == "ShadowProxy":
        n = np.zeros_like(p)
        fn, a = mt.face_normals(p, t)
        for i in range(3): np.add.at(n, t[:, i], fn * a[:, None])
        p = p - normalize(n) * (inset / W)
    a, b, c = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    m = rng.poisson(area / area.sum() * 400000)
    ti = np.repeat(np.arange(len(t)), m)
    r1, r2 = rng.random(len(ti)), rng.random(len(ti)); s = np.sqrt(r1)
    q = a[ti] * (1 - s)[:, None] + b[ti] * (s * (1 - r2))[:, None] + c[ti] * (s * r2)[:, None]
    tri, bary, dist = src.closest(q)
    _, nn, _, _ = src.attributes(tri, bary)
    fnrm = np.cross(src.b[tri] - src.a[tri], src.c[tri] - src.a[tri]); fnrm = normalize(fnrm)
    cpt = (src.a[tri] * bary[:, :1] + src.b[tri] * bary[:, 1:2] + src.c[tri] * bary[:, 2:3])
    sd = ((q - cpt) * fnrm).sum(1) * W
    out[name] = {"inset_mm": inset if name == "ShadowProxy" else 0, "samples": int(len(q)),
                 "outside_fraction": float((sd > 2).mean()), "outside_p95_mm": float(np.percentile(sd, 95)),
                 "outside_p99_mm": float(np.percentile(sd, 99)), "inside_p5_mm": float(np.percentile(sd, 5)),
                 "abs_mean_mm": float(np.abs(sd).mean())}
    mt.log(f"{name}: {out[name]}")
json.dump(out, open(f"truck/shadow-caster-deviation-inset{inset:g}.json", "w"), indent=1)
