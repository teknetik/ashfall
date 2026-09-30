"""Ward oasis tree review renders (Blender Cycles, CPU only).

blender -b --factory-startup --python tree_review.py
Source = WardTree_LOD0 geometry (from cache/tree_*.npz, identical data to the FBX);
LOD2 and the shadow proxy are loaded through Blender's FBX importer. Scene scale
0.88 (the scene instance's uniform scale). Leaves are alpha-clipped at 0.35 as in
leaves.mat (double-sided); bark uses the albedo maps. Views:
  front45 / side45 / hill90 : source LOD0 vs LOD2 silhouettes at 1080p, 50 deg FOV
  under / ground            : source (all casting) vs LOD0 visible + proxy-only casting
  foot55 / foot30           : top-down ground shadow, tree invisible to camera
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

TREE_ART = f"{bc.REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree"
OUT = f"{bc.CACHE}/renders/tree"
os.makedirs(OUT, exist_ok=True)
SCALE = 0.88
RES = (1920, 1080)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def materials():
    mats = {}
    for part in ("leaves", "branches", "trunk"):
        m = bpy.data.materials.new(part)
        m.use_nodes = True
        n, l = m.node_tree.nodes, m.node_tree.links
        bsdf = n["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.75
        uv = n.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        tex = n.new("ShaderNodeTexImage")
        tex.image = bc.load_image(f"{TREE_ART}/{part}-albedo.png", "sRGB")
        l.new(uv.outputs["UV"], tex.inputs["Vector"])
        l.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if part == "leaves":
            gt = n.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.35
            l.new(tex.outputs["Alpha"], gt.inputs[0])
            l.new(gt.outputs[0], bsdf.inputs["Alpha"])
            bsdf.inputs["Transmission Weight"].default_value = 0.0
            try:
                bsdf.inputs["Subsurface Weight"].default_value = 0.0
            except KeyError:
                pass
        mats[part] = m
    return mats


def source_objects(mats):
    obs = {}
    for part in ("leaves", "branches", "trunk"):
        d = np.load(f"{bc.CACHE}/tree_{part}.npz")
        tri = d["tri_corners"]
        ob = bc.mesh_from_arrays(f"src_{part}", d["cp"], d["corner_cp"][tri],
                                 corner_uv=d["uv"][tri].reshape(-1, 2),
                                 corner_normals=d["normals"][tri].reshape(-1, 3))
        ob.data.materials.append(mats[part])
        obs[part] = ob
        log(f"source {part}: {len(tri)} tris")
    return obs


def import_parts(path, prefix, mats):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, use_custom_normals=True)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    obs = {}
    for o in new:
        part = next(p for p in ("leaves", "branches", "trunk") if o.name.endswith(p) or p in o.name)
        o.data.materials.clear()
        o.data.materials.append(mats[part])
        o.name = f"{prefix}_{part}"
        obs[part] = o
    return obs


def main():
    scene = bc.reset_scene()
    bc.cpu_cycles(scene, samples=32, denoise=True)
    scene.cycles.transparent_max_bounces = 48
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 1
    scene.view_settings.view_transform = "AgX"
    bc.studio_world(scene, strength=0.5, color=(0.62, 0.66, 0.72))
    mats = materials()
    rig = bpy.data.objects.new("rig", None)
    scene.collection.objects.link(rig)
    rig.matrix_world = Matrix.Scale(SCALE, 4)
    groups = {"source": source_objects(mats)}
    bounds = {}
    for name, fname in (("LOD2", "WardTree_LOD2.fbx"), ("proxy", "WardTree_ShadowProxy.fbx")):
        groups[name] = import_parts(f"{bc.ROOT}/tree/{fname}", name, mats)
        for part, o in groups[name].items():
            M = np.array(o.matrix_world)
            v = np.zeros(len(o.data.vertices) * 3, np.float32)
            o.data.vertices.foreach_get("co", v)
            w = v.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            bounds[f"{name}_{part}"] = {"min": w.min(0).tolist(), "max": w.max(0).tolist(),
                                        "matrixWorldIsIdentity": bool(np.allclose(M, np.eye(4), atol=1e-5))}
    for part, o in groups["source"].items():
        v = np.zeros(len(o.data.vertices) * 3, np.float32)
        o.data.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        bounds[f"source_{part}"] = {"min": v.min(0).tolist(), "max": v.max(0).tolist()}
    with open(f"{bc.ROOT}/tree/import-bounds-check.json", "w") as fh:
        json.dump(bounds, fh, indent=1)
    for g in groups.values():
        for o in g.values():
            o.parent = rig
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    zmin = bounds["source_trunk"]["min"][2] * SCALE
    ground = bc.ground_plane(size=800, color=(0.46, 0.42, 0.36), z=zmin)
    sun = bc.add_sun("sun", elevation_deg=50, azimuth_deg=-60, strength=4.0)
    canopy = Vector((-0.7 * SCALE, 0.4 * SCALE, zmin + 9.0))

    def cam(name, dist, az, height, target=canopy, fov=50.0):
        a = math.radians(az)
        return bc.add_camera(name, Vector((target.x + dist * math.cos(a), target.y + dist * math.sin(a), height)),
                             target, fov)

    cams = {
        "front45": cam("front45", 45, 270, zmin + 1.7),
        "side45": cam("side45", 45, 0, zmin + 1.7),
        "hill90": cam("hill90", 90, 135, zmin + 20.0),
        "under": bc.add_camera("under", Vector((7.0, -6.0, zmin + 1.7)), Vector((0.0, 1.0, zmin + 12.0)), 75.0),
        "ground": bc.add_camera("ground", Vector((5.5, -7.5, zmin + 1.7)), Vector((0.5, 0.5, zmin)), 60.0),
    }
    top = bc.add_camera("top", Vector((canopy.x, canopy.y, zmin + 60)), Vector((canopy.x, canopy.y, zmin)),
                        ortho_scale=46.0)

    def show(visible, casters, camera_visible_tree=True):
        for gname, g in groups.items():
            for o in g.values():
                vis = gname in visible
                cast = gname in casters
                o.hide_render = not (vis or cast)
                o.visible_camera = vis and camera_visible_tree
                o.visible_diffuse = vis
                o.visible_glossy = vis
                o.visible_transmission = vis
                o.visible_shadow = cast

    spec = []

    def shoot(view, tag, camera, visible, casters, res=RES, cam_tree=True):
        path = f"{OUT}/tree_{view}_{tag}.png"
        if not os.path.exists(path):
            show(visible, casters, cam_tree)
            t0 = time.time()
            bc.render_to(scene, camera, path, res)
            log(f"render {view} {tag} {time.time()-t0:.0f}s")

    for view in ("front45", "side45", "hill90"):
        for tag in ("source", "LOD2"):
            shoot(view, tag, cams[view], [tag], [tag])
        spec.append([view, ["source", "LOD2"], None if view == "hill90" else [0.5, 0.75]])
    for view in ("under", "ground"):
        shoot(view, "source", cams[view], ["source"], ["source"])
        shoot(view, "proxy", cams[view], ["source"], ["proxy"])
        spec.append([view, ["source", "proxy"], None])
    for view, el, az in (("foot55", 55, 30), ("foot30", 30, 200)):
        el_r, az_r = math.radians(el), math.radians(az)
        d = -Vector((math.cos(el_r) * math.cos(az_r), math.cos(el_r) * math.sin(az_r), math.sin(el_r)))
        sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        # centre the ortho view on the shadow: shift along the ground projection of the sun direction
        shift = 9.0 / math.tan(el_r)
        top.location = Vector((canopy.x - math.cos(az_r) * shift, canopy.y - math.sin(az_r) * shift, zmin + 60))
        for tag, caster in (("source", "source"), ("proxy", "proxy")):
            shoot(view, tag, top, [], [caster], res=(1400, 1400), cam_tree=False)
        spec.append([view, ["source", "proxy"], None])
    with open(f"{OUT}/spec.json", "w") as fh:
        json.dump(spec, fh)
    log("done")


main()
