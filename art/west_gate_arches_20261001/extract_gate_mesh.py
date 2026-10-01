"""Extract the District gate arches (Meshy gate.fbx, two instances) in Unity WORLD space from the saved render-chunk
mesh assets (Assets/AthenHill/Art/RenderChunks/Chunk_*_District_gate_*.asset: text YAML, world-space vertices), so the
leaves can be fitted to the real intrados without opening Unity.

    python3 extract_gate_mesh.py            -> gate_world.obj (Unity coords), gate_profile.json (opening per depth slice)

Pure Python (struct only). Vertex layout: float3 position, float3 normal, float4 tangent, float2 uv (stride 48).
"""
import json, re, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHUNKS = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/RenderChunks"


def read_chunk(path):
    t = path.read_text()
    vc = int(re.search(r"m_VertexCount: (\d+)", t).group(1))
    data = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", t).group(1))
    fmt = int(re.search(r"m_IndexFormat: (\d+)", t).group(1))
    ib = bytes.fromhex(re.search(r"m_IndexBuffer: ([0-9a-f]+)", t).group(1))
    stride = len(data) // vc
    assert stride == 48, stride
    verts = [struct.unpack_from("<3f", data, i * stride) for i in range(vc)]
    idx = struct.unpack("<%d%s" % (len(ib) // (4 if fmt else 2), "I" if fmt else "H"), ib)
    tris = [idx[i:i + 3] for i in range(0, len(idx), 3)]
    return verts, tris


def tri_slice_x(a, b, c, x):
    """Segment where the plane X = x cuts triangle abc (points as (y, z)), or None."""
    pts = []
    for p, q in ((a, b), (b, c), (c, a)):
        if (p[0] - x) * (q[0] - x) < 0:
            t = (x - p[0]) / (q[0] - p[0])
            pts.append((p[1] + t * (q[1] - p[1]), p[2] + t * (q[2] - p[2])))
    return pts if len(pts) == 2 else None


def main():
    files = sorted(CHUNKS.glob("Chunk_*_District_gate_*.asset"))
    if not files:
        sys.exit("no District_gate chunks")
    allv, allt, out = [], [], []
    for f in files:
        v, t = read_chunk(f)
        base = len(allv)
        allv += v
        allt += [(a + base, b + base, c + base) for a, b, c in t]
    with open(HERE / "gate_world.obj", "w") as fo:
        fo.write("# District gate arches, Unity world metres (X east, Y up, Z north)\n")
        for p in allv:
            fo.write("v %.5f %.5f %.5f\n" % p)
        for a, b, c in allt:
            fo.write("f %d %d %d\n" % (a + 1, b + 1, c + 1))
    xs = [p[0] for p in allv]
    prof = {"files": [f.name for f in files], "verts": len(allv), "tris": len(allt),
            "x": [min(xs), max(xs)], "slices": {}}
    # opening of each arch at depth slices: for heights y, the free z interval around the arch centre
    for centre in (0.0, 12.0):
        arch = {}
        for xi in range(0, 35):
            x = 46.32 + xi * 0.1
            segs = []
            for a, b, c in allt:
                s = tri_slice_x(allv[a], allv[b], allv[c], x)
                if s and abs((s[0][1] + s[1][1]) / 2 - centre) < 5.9:
                    segs.append(s)
            rows = {}
            for yi in range(0, 90):
                y = 0.05 + yi * 0.1
                zl, zr = -99.0, 99.0
                hit = False
                for (y0, z0), (y1, z1) in segs:
                    if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
                        z = z0 + (y - y0) / (y1 - y0) * (z1 - z0)
                        hit = True
                        if z <= centre:
                            zl = max(zl, z)
                        else:
                            zr = min(zr, z)
                if hit:
                    rows[round(y, 2)] = [round(zl, 3), round(zr, 3)]
            arch[round(x, 2)] = rows
        prof["slices"][str(centre)] = arch
    (HERE / "gate_profile.json").write_text(json.dumps(prof))
    print("verts", len(allv), "tris", len(allt), "x", min(xs), max(xs))
    for centre in ("0.0", "12.0"):
        print("arch", centre)
        for x, rows in list(prof["slices"][centre].items())[::4]:
            # widest free span at 1 m, 3 m, 5 m and the crown (highest y with a finite span)
            def span(y):
                r = rows.get(y)
                return None if not r else (r[0], r[1])
            crown = max((y for y, r in rows.items() if r[0] > -98 and r[1] < 98 and r[1] - r[0] > 0.2), default=None)
            print(f"  x {x:6.2f}  y0.45 {span(0.45)}  y1.05 {span(1.05)}  y3.05 {span(3.05)}  y5.05 {span(5.05)}  crown~{crown}")


if __name__ == "__main__":
    main()
