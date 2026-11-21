# Frames of the scrap pistol (20 Nov 2026), after art/pistol_mods_20260930/src/pm_common.py.
#   glTF pistol space : ScrapPistol.glb node space. Muzzle toward glTF -X, up +Y, the player's right is glTF -Z.
#   metric frame      : what Blender's glTF importer makes of it, scaled by S so 1 unit = 1 m:
#                       forward (muzzle) -X, up +Z, the player's right +Y. ALL modelling happens here.
#   export            : pistol.glb is the metric frame divided by S (the pistol's own glTF units, axes and origin), so
#                       the rebuilt pistol drops in where ScrapPistol.glb is instanced (local scale 0.136736).
#                       grip.glb is the SAME frame in metres (not divided), so a grip family root placed on the pistol
#                       root with scale 1 is the fitted grip.
#   Unity holder frame: 'View model pistol' / 'Berms held pistol' (Unity axes, metres):
#                       holder = (-S*gz + 0.00067, S*gy + 0.00012, -S*gx + 0.08376)
import bpy, os
from mathutils import Matrix, Vector

ROOT = '/home/teknetik/code/ao2/'
U = ROOT + 'unity/AthenHill/Assets/AthenHill/'
PISTOL_GLB = U + 'Art/OuterBerms/ScrapPistol.glb'
MODS_GLB = ROOT + 'art/pistol_mods_20260930/export/PistolMods.glb'
S = 0.13674                                   # glTF pistol unit -> metres (in-game scale of the ScrapPistol instance)
HOLDER_T = Vector((0.00067, 0.00012, 0.08376))  # ScrapPistol local position in the holder (Unity)


def unity_holder_to_metric(v):
    return Vector((-(v[2] - HOLDER_T.z), v[0] - HOLDER_T.x, v[1] - HOLDER_T.y))


def metric_to_gltf(v):
    return Vector((v[0] / S, v[2] / S, -v[1] / S))


def gltf_to_metric(g):
    return Vector((g[0] * S, -g[2] * S, g[1] * S))


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def import_skin(name='SKIN_ScrapPistol'):
    """The Meshy pistol as a measuring skin, in the metric frame. Never exported."""
    objs = import_glb(PISTOL_GLB)
    mesh = [o for o in objs if o.type == 'MESH'][0]
    for o in objs:
        if o.parent is None:
            o.matrix_world = Matrix.Scale(S, 4) @ o.matrix_world
    bpy.context.view_layer.update()
    mesh.name = name
    return mesh


def import_mods():
    """The five other mods (and the present Stabilised grip) in the metric frame: {item id: object}."""
    objs = import_glb(MODS_GLB)
    for o in objs:
        if o.parent is None:
            o.matrix_world = Matrix.Scale(S, 4) @ o.matrix_world
    bpy.context.view_layer.update()
    return {o.name: o for o in objs if o.type == 'MESH'}
