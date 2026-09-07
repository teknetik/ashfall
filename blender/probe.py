"""Run inside the live Blender MCP session; writes the Phase 0 probe artifacts."""

from pathlib import Path
import json
import math
import shutil

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SCENE_NAME = "AthenHill_Phase0_Probe"
if bpy.data.scenes.get(SCENE_NAME):
    raise RuntimeError("Probe scene already exists; preserve the accepted scene and version the next run.")

for folder in ("blender/scenes", "blender/exports", "blender/previews", "public/assets", "previews"):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

# Use a new scene: keep the user's original scene and objects intact.
scene = bpy.data.scenes.new(SCENE_NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.world = bpy.data.worlds.new("PROBE_world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.24, 0.29, 0.36, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45


def material(name, rgb, roughness):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = 0.0
    value.diffuse_color = (*rgb, 1)
    return value


bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.object
cube.name = "PROBE_CUBE"
cube.data.name = "PROBE_CUBE_mesh"
# Ground-centred origin, Blender Z-up; GLB exporter converts to Three.js Y-up.
for vertex in cube.data.vertices:
    vertex.co.z += 1.0
cube.data.materials.append(material("PROBE_blue", (0.025, 0.19, 0.51), 0.78))
bevel = cube.modifiers.new("Probe_edge_bevel", "BEVEL")
bevel.width = 0.04
bevel.segments = 1
bpy.ops.object.modifier_apply(modifier=bevel.name)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
cube.data.uv_layers.active.name = "UV0"
cube.data.uv_layers.new(name="UV1", do_init=True)
cube["asset_role"] = "Phase 0 pipeline probe, original Blender geometry"
cube["units"] = "metres"
cube["expected_dimensions_m"] = [2.0, 2.0, 2.0]
cube["forward_axis_runtime"] = "+Z"

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.005))
ground = bpy.context.object
ground.name = "PROBE_render_ground"
ground.data.materials.append(material("PROBE_sand", (0.553, 0.376, 0.175), 0.92))

sun_data = bpy.data.lights.new("PROBE_sun", "SUN")
sun_data.energy = 2.3
sun_data.angle = math.radians(3)
sun = bpy.data.objects.new("PROBE_sun", sun_data)
scene.collection.objects.link(sun)
sun.location = (-6, -8, 10)
sun.rotation_euler = (Vector((0, 0, 0)) - sun.location).to_track_quat("-Z", "Y").to_euler()

fill_data = bpy.data.lights.new("PROBE_fill", "AREA")
fill_data.energy = 280
fill_data.shape = "DISK"
fill_data.size = 7
fill = bpy.data.objects.new("PROBE_fill", fill_data)
scene.collection.objects.link(fill)
fill.location = (4, 2, 6)
fill.rotation_euler = (Vector((0, 0, 1)) - fill.location).to_track_quat("-Z", "Y").to_euler()

# Positions are expressed in runtime (Y-up) coordinates, converted for Blender.
# These Phase 0 views frame the probe; city camera compositions come in Phase 1.
camera_positions = {
    "cam_gate": [-6, 3.5, 6],
    "cam_avenue": [-4, 2.4, 6],
    "cam_hill": [5, 3.5, 6],
    "cam_grid": [4, 5, -5],
    "cam_whompah": [-5, 2.8, -5],
    "cam_hero": [0, 2.5, 4.2],
}
cameras = {}
for name, (x, y, z) in camera_positions.items():
    camera_data = bpy.data.cameras.new(name)
    camera_data.lens = 42
    camera_data.clip_start = 0.1
    camera_data.clip_end = 250
    camera = bpy.data.objects.new(name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = (x, -z, y)
    camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    cameras[name] = camera

bpy.ops.object.select_all(action="DESELECT")
cube.select_set(True)
bpy.context.view_layer.objects.active = cube
export_path = ROOT / "public/assets/probe.glb"
bpy.ops.export_scene.gltf(filepath=str(export_path), export_format="GLB", use_selection=True, use_active_scene=True,
                          export_yup=True, export_apply=True, export_extras=True)
shutil.copy2(export_path, ROOT / "blender/exports/probe.glb")

scene.camera = cameras["cam_hill"]
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.filepath = str(ROOT / "previews/probe.png")
bpy.ops.render.render(write_still=True)
shutil.copy2(ROOT / "previews/probe.png", ROOT / "blender/previews/probe.png")

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
for name, camera in cameras.items():
    scene.camera = camera
    scene.render.filepath = str(ROOT / f"blender/previews/{name}.png")
    bpy.ops.render.render(write_still=True)

scene.camera = cameras["cam_hill"]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "blender/scenes/00_probe.blend"))
cube.data.calc_loop_triangles()
metadata = {
    "phase": 0,
    "blender_version": bpy.app.version_string,
    "source": "Original geometry authored through live Blender MCP",
    "scene": scene.name,
    "mesh": cube.name,
    "dimensions_m": list(cube.dimensions),
    "origin_blender": list(cube.location),
    "scale": list(cube.scale),
    "triangles": len(cube.data.loop_triangles),
    "materials": len(cube.data.materials),
    "uv_layers": [layer.name for layer in cube.data.uv_layers],
    "glb_bytes": export_path.stat().st_size,
    "export_active_scene_only": True,
    "cameras_runtime_y_up": camera_positions,
    "preview": "previews/probe.png",
    "runtime_asset": "public/assets/probe.glb",
    "scope": "Pipeline verification only; city, player, references and visual acceptance pending later phases.",
}
(ROOT / "blender/probe-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2))
