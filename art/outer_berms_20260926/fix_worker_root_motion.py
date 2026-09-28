#!/usr/bin/env python3
"""Remove baked horizontal root motion from the worker droid's Meshy clips (27 Sep 2026).

Run after merge_worker_droid.py:
  uv run --offline --with numpy python art/outer_berms_20260926/fix_worker_root_motion.py
FeralDroid moves the droid's root itself, so horizontal Hips translation in the clips makes the body drift off its
collider: Combat_Stance idle stood 0.46 m to the side, Hit_Reaction slid 1.5 m sideways and Knock_Down started 2 m
behind the root and ended 3.3 m back. The Hips x/z channels are rewritten in place in the GLB (same sizes):
loops keep only their sway about the rest position, the hit reaction is detrended, the attack keeps its forward
lunge but starts at rest, and the death keeps half of its knock-back. Vertical motion is untouched.
"""
import json, struct, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = ROOT / "unity/AthenHill/Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb"

b = bytearray(GLB_PATH.read_bytes())
jlen = struct.unpack_from("<I", b, 12)[0]
j = json.loads(b[20:20 + jlen])
bin_off = 20 + jlen + 8
names = [n.get("name") for n in j["nodes"]]
hips = names.index("Hips")
rest = np.array(j["nodes"][hips].get("translation", [0, 0, 0]), np.float32)


def view(acc_index):
    a = j["accessors"][acc_index]; bv = j["bufferViews"][a["bufferView"]]
    assert a["componentType"] == 5126 and not bv.get("byteStride")
    n = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[a["type"]]
    start = bin_off + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return start, np.frombuffer(bytes(b[start:start + a["count"] * n * 4]), "<f4").reshape(a["count"], n).copy()


report = {}
dirty_json = False
for anim in j["animations"]:
    for ch in anim["channels"]:
        if ch["target"]["node"] != hips or ch["target"]["path"] != "translation":
            continue
        s = anim["samplers"][ch["sampler"]]
        _, t = view(s["input"]); start, v = view(s["output"])
        t = t[:, 0]; xz = v[:, [0, 2]]; name = anim["name"]
        if name in ("idle", "walk", "run"):
            new = rest[[0, 2]] + (xz - xz.mean(0))
        elif name == "hit":
            f = ((t - t[0]) / max(t[-1] - t[0], 1e-6))[:, None]
            new = rest[[0, 2]] + (xz - (xz[0] + (xz[-1] - xz[0]) * f))
        elif name == "attack":
            new = rest[[0, 2]] + (xz - xz[0])
        elif name == "death":
            new = rest[[0, 2]] + (xz - xz[0]) * .5
        else:
            continue
        before = (xz.min(0).round(1).tolist(), xz.max(0).round(1).tolist())
        v[:, 0], v[:, 2] = new[:, 0], new[:, 1]
        b[start:start + v.nbytes] = v.astype("<f4").tobytes()
        acc = j["accessors"][s["output"]]
        if "min" in acc: acc["min"] = v.min(0).tolist(); acc["max"] = v.max(0).tolist(); dirty_json = True
        report[name] = {"xz_before_cm": before, "xz_after_cm": (new.min(0).round(1).tolist(), new.max(0).round(1).tolist())}

if dirty_json:
    # rewrite the JSON chunk (padded to 4 bytes with spaces) ahead of the unchanged binary chunk
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    rest_bytes = bytes(b[20 + jlen:])
    b = bytearray(b[:12]) + struct.pack("<I", len(js)) + b"JSON" + js + rest_bytes
    struct.pack_into("<I", b, 8, len(b))
GLB_PATH.write_bytes(bytes(b))
(ROOT / "art/outer_berms_20260926/worker-droid-root-motion.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report))
