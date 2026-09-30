"""Truck review renders (Blender Cycles on CPU): source vs LODs at matched cameras.

blender -b --factory-startup --python truck_review.py

World units are metres in the scene: raw FBX coordinates x RAW_TO_WORLD (importer
619.75354 x FBX cm factor 0.01 x the scene root's 0.65). Cameras use a 50 degree
vertical FOV (the game's follow camera) at 1920x1080 so pixel density matches play.
LOD FBX files are loaded through Blender's FBX importer (validates the files and
their node transforms); their world bounds are compared with the source bounds.
Raw PNGs go to cache/renders/truck; compose_review.py builds the JPG sheets.
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc  # noqa: E402

MESHY = f"{bc.REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611"
TRUCK = f"{bc.ROOT}/truck"
OUT = f"{bc.CACHE}/renders/truck"
os.makedirs(OUT, exist_ok=True)
RAW_TO_WORLD = 6.1975354 * 0.65
RES = (1920, 1080)
SAMPLES = 48


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def material(name, base, normal, ms):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    n, l = nt.nodes, nt.links
    bsdf = n["Principled BSDF"]
    uv = n.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tb = n.new("ShaderNodeTexImage")
    tb.image = bc.load_image(base, "sRGB")
    tn = n.new("ShaderNodeTexImage")
    tn.image = bc.load_image(normal, "Non-Color")
    tm = n.new("ShaderNodeTexImage")
    tm.image = bc.load_image(ms, "Non-Color")
    for t in (tb, tn, tm):
        l.new(uv.outputs["UV"], t.inputs["Vector"])
    nm = n.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    l.new(tn.outputs["Color"], nm.inputs["Color"])
    l.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    sep = n.new("ShaderNodeSeparateColor")
    l.new(tm.outputs["Color"], sep.inputs["Color"])
    l.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
    # URP Lit: smoothness = map.a * _Smoothness (0.32); roughness = 1 - smoothness
    mul = n.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.32
    l.new(tm.outputs["Alpha"], mul.inputs[0])
    inv = n.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    l.new(mul.outputs[0], inv.inputs[1])
    l.new(inv.outputs[0], bsdf.inputs["Roughness"])
    return mat


def import_fbx(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, use_custom_normals=True)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    assert len(new) == 1, f"{path}: expected one mesh, got {len(new)}"
    ob = new[0]
    ob.name = name
    return ob


def world_bounds(ob):
    me = ob.data
    v = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    w = v @ M[:3, :3].T + M[:3, 3]
    return w.min(0), w.max(0)


def main():
    scene = bc.reset_scene()
    bc.cpu_cycles(scene, samples=SAMPLES, denoise=True)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    bc.studio_world(scene, strength=0.45, color=(0.62, 0.64, 0.68))
    rig = bpy.data.objects.new("rig", None)
    scene.collection.objects.link(rig)
    rig.matrix_world = Matrix.Scale(RAW_TO_WORLD, 4)

    log("source")
    d = np.load(f"{bc.CACHE}/truck_source_render.npz")
    tris = d["tris"]
    src = bc.mesh_from_arrays("source", d["positions"], tris, corner_uv=d["uv"][tris].reshape(-1, 2),
                              vertex_normals=d["normals"])
    src_min = d["positions"].min(0)
    src_max = d["positions"].max(0)
    del d, tris
    mat_src = material("source", f"{MESHY}/meshy_basecolor.png", f"{MESHY}/meshy_normal.png",
                       f"{MESHY}/meshy_metallic_smoothness.png")
    src.data.materials.append(mat_src)

    objs = {"source": src}
    bounds = {"sourceRaw": [src_min.tolist(), src_max.tolist()]}
    for name, fname, mat in (
            ("LOD0", "KaraveenTruck_LOD0_exact.fbx", mat_src),
            ("LOD1", "KaraveenTruck_LOD1.fbx", material("LOD1", f"{TRUCK}/textures/KaraveenTruck_LOD1_BaseColor.png",
                                                            f"{TRUCK}/textures/KaraveenTruck_LOD1_Normal.png",
                                                            f"{TRUCK}/textures/KaraveenTruck_LOD1_MetallicSmoothness.png")),
            ("LOD2", "KaraveenTruck_LOD2.fbx", material("LOD2", f"{TRUCK}/textures/KaraveenTruck_LOD2_BaseColor.png",
                                                            f"{TRUCK}/textures/KaraveenTruck_LOD2_Normal.png",
                                                            f"{TRUCK}/textures/KaraveenTruck_LOD2_MetallicSmoothness.png")),
            ("ShadowProxy", "KaraveenTruck_ShadowProxy.fbx", None),
            ("ShadowNear", "KaraveenTruck_ShadowNear.fbx", None)):
        ob = import_fbx(f"{TRUCK}/{fname}", name)
        bmin, bmax = world_bounds(ob)
        bounds[name] = {"blenderImportWorldMin": bmin.tolist(), "blenderImportWorldMax": bmax.tolist(),
                        "maxDeltaFromSourceRaw": float(max(np.abs(bmin - src_min).max(), np.abs(bmax - src_max).max())),
                        "matrixWorld": [list(r) for r in ob.matrix_world]}
        log(f"{name}: bounds {bmin} {bmax}")
        ob.data.materials.clear()
        if mat is not None:
            ob.data.materials.append(mat)
        else:
            gm = bpy.data.materials.new("proxy")
            gm.use_nodes = True
            gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.3, 0.3, 0.3, 1)
            ob.data.materials.append(gm)
        objs[name] = ob
    with open(f"{TRUCK}/import-bounds-check.json", "w") as fh:
        json.dump(bounds, fh, indent=1)
    # parent everything to the metre rig without changing their local placement
    for ob in objs.values():
        ob.parent = rig
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = Matrix.Identity(4)  # raw coordinates (import transform is identity in world)
    bpy.context.view_layer.update()
    zmin = float(src_min[2]) * RAW_TO_WORLD
    ground = bc.ground_plane(size=600, color=(0.42, 0.40, 0.37), z=zmin - 0.002)
    bc.add_sun("sun", elevation_deg=38, azimuth_deg=-60, strength=4.0)

    L = float(src_max[0]) * RAW_TO_WORLD  # half length along +x
    W = float(src_max[1]) * RAW_TO_WORLD
    H = float(src_max[2] - src_min[2]) * RAW_TO_WORLD
    centre = Vector((0, 0, zmin + 0.45 * H))
    eye = zmin + 1.7

    def cam_at(dist, name, target=centre, az_deg=-35.0, height=None):
        az = math.radians(az_deg)
        loc = Vector((target.x + dist * math.cos(az), target.y + dist * math.sin(az), height if height else eye))
        return bc.add_camera(name, loc, target, lens_fov_deg=50.0)

    corner = Vector((L * 0.82, -W * 0.8, zmin + 0.62 * H))
    cams = {
        "02m": cam_at(2.0, "cam02", target=corner, az_deg=-40.0, height=zmin + 1.7),
        "08m": cam_at(8.0 + L * 0.5, "cam08"),
        "16m": cam_at(16.0, "cam16"),
        "30m": cam_at(30.0, "cam30"),
        "45m": cam_at(45.0, "cam45"),
    }
    plan = {
        "02m": ["source", "LOD0"],
        "08m": ["source", "LOD0", "LOD1"],
        "16m": ["source", "LOD1"],
        "30m": ["source", "LOD1", "LOD2"],
        "45m": ["source", "LOD2"],
    }
    lod_names = ["source", "LOD0", "LOD1", "LOD2", "ShadowProxy", "ShadowNear"]

    def show(visible, shadow_from=None):
        for n in lod_names:
            ob = objs[n]
            ob.hide_render = n not in visible and n != shadow_from
            ob.visible_camera = n in visible
            ob.visible_diffuse = n in visible
            ob.visible_glossy = n in visible
            ob.visible_transmission = n in visible
            ob.visible_volume_scatter = n in visible
            ob.visible_shadow = (n == shadow_from) if shadow_from else (n in visible)

    for view, variants in plan.items():
        for v in variants:
            path = f"{OUT}/truck_{view}_{v}.png"
            if os.path.exists(path):
                continue
            show([v])
            t0 = time.time()
            bc.render_to(scene, cams[view], path, RES)
            log(f"render {view} {v} {time.time()-t0:.0f}s")
    # self-shadow checks: visual LOD does not cast; a shadows-only caster does.
    # near (LOD0 range): LOD1 mesh as caster; mid/far: the inset ShadowProxy.
    for view, cam, visible, caster in (("shadownear", "08m", "LOD0", "ShadowNear"),
                                       ("shadowmid", "16m", "LOD1", "ShadowProxy")):
        for tag, vis, cst in (("source", "source", "source"), (f"{visible}+{caster}", visible, caster)):
            path = f"{OUT}/truck_{view}_{tag}.png"
            if os.path.exists(path):
                continue
            show([vis], shadow_from=cst)
            t0 = time.time()
            bc.render_to(scene, cams[cam], path, RES)
            log(f"render {view} {tag} {time.time()-t0:.0f}s")
    log("done")


main()
