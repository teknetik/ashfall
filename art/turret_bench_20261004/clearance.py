"""Turret on the bastion deck: lowest turret vertex over the return footprint vs the return's top, and the turret's
closest approach to any bastion vertex (other than the deck under its base). Unity bastion-local placement x,z,yaw."""
import bpy, math, sys, numpy as np
from mathutils import Matrix
from pathlib import Path
R = Path(__file__).resolve().parents[2]
M = R / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Models"; T = R / "unity/AthenHill/Assets/AthenHill/Art/TurretBench/sentinel_turret"
args = sys.argv[sys.argv.index("--") + 1:]
side = args[0]; opts = [tuple(map(float, a.split(","))) for a in args[1:]]
S = 1 if side == "S" else -1
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(M / f"WL_GateBastion{side}_LOD0.glb"))
B = np.concatenate([np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) for o in bpy.context.scene.objects if o.type == "MESH"])
U = np.stack([-B[:, 0], B[:, 2], -B[:, 1]], 1)      # to Unity local
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(T / "sentinel_turret_LOD0.glb"))
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
Tv = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]); Tv = np.stack([-Tv[:, 0], Tv[:, 2], -Tv[:, 1]], 1)
from mathutils.kdtree import KDTree
kd = KDTree(len(U))
for j, p in enumerate(U): kd.insert(p, j)
kd.balance()
for (x, z, yaw) in opts:
    a = math.radians(yaw); c, s = math.cos(a), math.sin(a)
    P = np.stack([Tv[:, 0] * c + Tv[:, 2] * s + x, Tv[:, 1] + 0.37, -Tv[:, 0] * s + Tv[:, 2] * c + z], 1)
    up = P[P[:, 1] > 0.45]                       # above the base plate
    q = [kd.find(p) for p in up]
    d = np.array([r[2] for r in q]); i = np.array([r[1] for r in q])
    k = np.argmin(d)
    print(f"RES side {side} x {x} z {z} yaw {yaw}: closest bastion vertex {d[k]*100:.1f} cm at turret point {up[k].round(2)} bastion {U[i[k]].round(2)}; turret top {P[:,1].max():.2f}")
