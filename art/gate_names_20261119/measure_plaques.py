"""Find the baked "WEST GATE" plaques on the two Meshy District gate arches (+X spawn) in Unity world space.

Reads the saved render-chunk meshes (world-space vertices, read only; nothing is written back) and the Meshy
base_color atlas, and renders orthographic texture projections of the city face (-X) and the outer face (+X) of each
arch, so the plaque's world rectangle can be measured. Writes review/face_<arch>_<side>.png and plaques.json.

    uv run --with pillow --with numpy python measure_plaques.py

Vertex layout of the chunk meshes: float3 position, float3 normal, float4 tangent, float2 uv (stride 48).
"""
import json, re, struct
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHUNKS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/RenderChunks"
TEX = ROOT / "unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/District/gate/base_color.png"
OUT = HERE / "review"
PX = 200  # pixels per metre in the projections


def read_chunk(path):
    t = path.read_text()
    vc = int(re.search(r"m_VertexCount: (\d+)", t).group(1))
    data = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", t).group(1))
    fmt = int(re.search(r"m_IndexFormat: (\d+)", t).group(1))
    ib = bytes.fromhex(re.search(r"m_IndexBuffer: ([0-9a-f]+)", t).group(1))
    a = np.frombuffer(data, dtype="<f4").reshape(vc, 12)
    idx = np.frombuffer(ib, dtype="<u4" if fmt else "<u2").astype(np.int64).reshape(-1, 3)
    return a[:, 0:3].astype(np.float64), a[:, 3:6].astype(np.float64), a[:, 10:12].astype(np.float64), idx


def project(pos, nrm, uv, tris, tex, side, z0, z1, y0, y1):
    """Rasterise faces whose normal points to `side` (-1: -X, +1: +X), nearest face to that side wins."""
    W, H = int((z1 - z0) * PX), int((y1 - y0) * PX)
    img = np.zeros((H, W, 3), np.uint8)
    depth = np.full((H, W), np.inf)
    th, tw = tex.shape[:2]
    for t in tris:
        p, n, u = pos[t], nrm[t], uv[t]
        fn = np.cross(p[1] - p[0], p[2] - p[0])
        if np.linalg.norm(fn) < 1e-12:
            continue
        fn /= np.linalg.norm(fn)
        if fn[0] * side < 0.5:
            continue
        # screen: column = (z - z0) for -X view seen from -X (z grows to the right when looking +X? keep world z left->right)
        sx = (p[:, 2] - z0) * PX if side < 0 else (z1 - p[:, 2]) * PX
        sy = (y1 - p[:, 1]) * PX
        d = p[:, 0] * side * -1  # distance from the viewer on `side`
        xmin, xmax = int(max(0, np.floor(sx.min()))), int(min(W - 1, np.ceil(sx.max())))
        ymin, ymax = int(max(0, np.floor(sy.min()))), int(min(H - 1, np.ceil(sy.max())))
        if xmin > xmax or ymin > ymax:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + .5, np.arange(ymin, ymax + 1) + .5)
        x0, y0_, x1_, y1_, x2, y2 = sx[0], sy[0], sx[1], sy[1], sx[2], sy[2]
        den = (y1_ - y2) * (x0 - x2) + (x2 - x1_) * (y0_ - y2)
        if abs(den) < 1e-9:
            continue
        w0 = ((y1_ - y2) * (gx - x2) + (x2 - x1_) * (gy - y2)) / den
        w1 = ((y2 - y0_) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        dd = w0 * d[0] + w1 * d[1] + w2 * d[2]
        uu = w0 * u[0, 0] + w1 * u[1, 0] + w2 * u[2, 0]
        vv = w0 * u[0, 1] + w1 * u[1, 1] + w2 * u[2, 1]
        ys, xs = np.nonzero(m)
        ys += ymin; xs += xmin
        dsel = dd[m]
        closer = dsel < depth[ys, xs]
        ys, xs, dsel = ys[closer], xs[closer], dsel[closer]
        tx = np.clip((uu[m][closer] % 1) * tw, 0, tw - 1).astype(int)
        ty = np.clip((1 - vv[m][closer] % 1) * th, 0, th - 1).astype(int)
        depth[ys, xs] = dsel
        img[ys, xs] = tex[ty, tx, :3]
    return img, depth


def main():
    OUT.mkdir(exist_ok=True)
    tex = np.asarray(Image.open(TEX).convert("RGB"))
    result = {}
    for f in sorted(CHUNKS.glob("Chunk_*_District_gate_*.asset")):
        pos, nrm, uv, tris = read_chunk(f)
        zc = round(float(pos[:, 2].mean()))
        name = "A" if abs(zc) < 6 else "B"
        for side, label in ((-1, "city"), (1, "outer")):
            z0, z1, y0, y1 = zc - 5.8, zc + 5.8, 0.0, 9.0
            img, depth = project(pos, nrm, uv, tris, tex, side, z0, z1, y0, y1)
            Image.fromarray(img).save(OUT / f"face_{name}_{label}.png")
            # depth map (x of the nearest face) for measuring how far the plaque stands proud
            np.save(OUT / f"depth_{name}_{label}.npy", depth)
            result[f"{name}_{label}"] = {"chunk": f.name, "z0": z0, "z1": z1, "y0": y0, "y1": y1, "px_per_m": PX,
                                         "side": side}
        result[name + "_bounds"] = {"min": pos.min(0).round(3).tolist(), "max": pos.max(0).round(3).tolist()}
    (HERE / "projections.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
