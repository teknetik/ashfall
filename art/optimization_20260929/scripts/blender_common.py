"""Blender-side helpers (bpy) shared by the bake and review-render scripts."""
import math
import os

import bpy
import numpy as np

REPO = "/home/teknetik/code/ao2"
ROOT = f"{REPO}/art/optimization_20260929"
CACHE = f"{ROOT}/cache"


def cpu_cycles(scene, samples=32, denoise=True):
    prefs = bpy.context.preferences
    try:
        prefs.addons["cycles"].preferences.compute_device_type = "NONE"
    except Exception:
        pass
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    if denoise:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.use_adaptive_sampling = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = max(1, (os.cpu_count() or 4) - 4)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def mesh_from_arrays(name, positions, tris, corner_uv=None, vertex_normals=None, corner_normals=None,
                     sharp_angle_deg=None, uv_name="UVMap"):
    positions = np.ascontiguousarray(positions, np.float32)
    tris = np.ascontiguousarray(tris, np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(positions))
    me.vertices.foreach_set("co", positions.ravel())
    me.loops.add(tris.size)
    me.loops.foreach_set("vertex_index", tris.ravel())
    me.polygons.add(len(tris))
    me.polygons.foreach_set("loop_start", np.arange(0, tris.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    if corner_uv is not None:
        uvl = me.uv_layers.new(name=uv_name)
        uvl.data.foreach_set("uv", np.ascontiguousarray(corner_uv, np.float32).ravel())
    me.shade_smooth()
    if vertex_normals is not None:
        me.normals_split_custom_set_from_vertices(np.ascontiguousarray(vertex_normals, np.float32).reshape(-1, 3))
    elif corner_normals is not None:
        me.normals_split_custom_set(np.ascontiguousarray(corner_normals, np.float32).reshape(-1, 3))
    elif sharp_angle_deg is not None:
        set_sharp_by_angle(me, sharp_angle_deg)
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_sharp_by_angle(me, angle_deg):
    """Mark edges sharper than angle_deg as sharp (smooth-by-angle without modifiers)."""
    n_e = len(me.edges)
    edge_verts = np.zeros(n_e * 2, np.int32)
    me.edges.foreach_get("vertices", edge_verts)
    loop_edges = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get("edge_index", loop_edges)
    pn = np.zeros(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3)
    face_of_loop = np.repeat(np.arange(len(me.polygons)), 3)
    order = np.argsort(loop_edges, kind="stable")
    le = loop_edges[order]
    fo = face_of_loop[order]
    sharp = np.zeros(n_e, bool)
    # edges with exactly 2 faces: compare normals; boundary / non-manifold edges sharp
    counts = np.bincount(le, minlength=n_e)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    two = np.flatnonzero(counts == 2)
    f0 = fo[starts[two]]
    f1 = fo[starts[two] + 1]
    dots = (pn[f0] * pn[f1]).sum(1)
    sharp[two[dots < math.cos(math.radians(angle_deg))]] = True
    sharp[counts != 2] = True
    attr = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    attr.data.foreach_set("value", sharp)
    return int(sharp.sum())


def corner_arrays(ob):
    """Return (tris (T,3) vertex ids, corner uv (C,2), corner normals (C,3)) of a triangle mesh."""
    me = ob.data
    loops_v = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", loops_v)
    uv = np.zeros(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    cn = np.zeros(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    return loops_v.reshape(-1, 3), uv.reshape(-1, 2), cn.reshape(-1, 3)


def load_image(path, colorspace):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    img.alpha_mode = "CHANNEL_PACKED"
    return img


def save_image(img, path):
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()


def look_at(ob, target):
    from mathutils import Vector
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera(name, location, target, lens_fov_deg=50.0, ortho_scale=None):
    cam = bpy.data.cameras.new(name)
    if ortho_scale is not None:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    else:
        cam.sensor_fit = "VERTICAL"
        cam.angle_y = math.radians(lens_fov_deg)
    cam.clip_start = 0.05
    cam.clip_end = 2000
    ob = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    look_at(ob, target)
    return ob


def studio_world(scene, strength=0.35, color=(0.62, 0.62, 0.62)):
    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength
    scene.world = world


def add_sun(name, elevation_deg, azimuth_deg, strength=3.5, angle_deg=0.53):
    sun = bpy.data.lights.new(name, "SUN")
    sun.energy = strength
    sun.angle = math.radians(angle_deg)
    ob = bpy.data.objects.new(name, sun)
    bpy.context.scene.collection.objects.link(ob)
    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    # light points along -Z of the object; aim it from (az, el) toward origin
    from mathutils import Vector
    direction = -Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return ob


def ground_plane(size=400.0, color=(0.5, 0.5, 0.5), z=0.0, name="ground"):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = 0.9
    me.materials.append(mat)
    return ob


def render_to(scene, camera, path, res=(1280, 720)):
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
