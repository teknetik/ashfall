# Shared helpers for the Scrap Pistol mod attachments (30 Sep 2026).
# Frames:
#   glTF pistol space  : ScrapPistol.glb node space (identity node). Muzzle toward glTF -X, up +Y, player's right = glTF -Z.
#   Blender pistol     : what Blender's glTF importer makes of it: B = (gx, -gz, gy)  -> forward -X, up +Z, right +Y.
#   "metric" frame     : Blender pistol frame scaled by S (0.13674, the in-game scale) so 1 unit = 1 m. All modelling
#                        happens in this frame; export divides by S so attachments land in the pistol's own glTF units.
#   Unity holder frame : 'View model pistol' / 'Berms held pistol' (Unity axes, metres), from pistol_frame.json:
#                        holder = (-S*gz + 0.00067, S*gy + 0.00012, -S*gx + 0.08376)
import bpy, math, os, json
from mathutils import Matrix, Vector, Quaternion

ROOT = '/home/teknetik/code/ao2/'
ART = ROOT + 'art/pistol_mods_20260930/'
PISTOL_GLB = ROOT + 'unity/AthenHill/Assets/AthenHill/Art/OuterBerms/ScrapPistol.glb'
HANDS_GLB = ROOT + 'unity/AthenHill/Assets/AthenHill/Art/CharacterMotion/FirstPerson/PlayerFPHands_v5.glb'
FRAME_JSON = ROOT + 'art/character_feel_20260927/fp_arms/pistol_frame.json'
S = 0.13674  # glTF unit -> metres (FPGripPass dump: ScrapPistol ls=0.13674 under the unit-scale holder)
HOLDER_T = Vector((0.00067, 0.00012, 0.08376))  # ScrapPistol local position in the holder (Unity)


def unity_holder_to_metric(v):
    """Unity holder-frame point (metres) -> metric Blender pistol frame."""
    return Vector((-(v[2] - HOLDER_T.z), v[0] - HOLDER_T.x, v[1] - HOLDER_T.y))


def unity_dir_to_metric(d):
    return Vector((-d[2], d[0], d[1]))


def metric_to_gltf(v):
    """metric Blender pistol frame -> glTF pistol units."""
    return Vector((v[0] / S, v[2] / S, -v[1] / S))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def import_pistol():
    objs = import_glb(PISTOL_GLB)
    mesh = [o for o in objs if o.type == 'MESH'][0]
    for o in objs:
        if o.parent is None:
            o.matrix_world = Matrix.Scale(S, 4) @ o.matrix_world
    mesh.name = 'ScrapPistol'
    return mesh


# Hands glb (glTF) h -> Unity holder (-hx, hy, hz) -> metric. In Blender-import coords b=(hx,-hz,hy):
# metric = (b.y + Tz, -b.x - Tx, b.z - Ty)
HANDS_TO_METRIC = Matrix(((0, 1, 0, HOLDER_T.z), (-1, 0, 0, -HOLDER_T.x), (0, 0, 1, -HOLDER_T.y), (0, 0, 0, 1)))


def import_hands():
    objs = import_glb(HANDS_GLB)
    for o in objs:
        if o.parent is None:
            o.matrix_world = HANDS_TO_METRIC @ o.matrix_world
    return [o for o in objs if o.type == 'MESH']


def frame_info():
    return json.load(open(FRAME_JSON))


def vec3(s):
    return [float(x) for x in s.split(',')]


def camera(name, loc, look_dir, up, fov_deg=50.0, vertical=True, ortho=None, clip_start=0.01):
    cd = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    f = Vector(look_dir).normalized()
    u = Vector(up).normalized()
    r = f.cross(u).normalized()
    u = r.cross(f).normalized()
    # Blender camera: looks along -Z, up +Y, right +X
    M = Matrix((r, u, -f)).transposed().to_4x4()
    M.translation = Vector(loc)
    cam.matrix_world = M
    cd.clip_start = clip_start
    cd.clip_end = 100
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    else:
        cd.sensor_fit = 'VERTICAL' if vertical else 'AUTO'
        cd.angle_y = math.radians(fov_deg) if vertical else cd.angle_y
        if not vertical:
            cd.angle = math.radians(fov_deg)
    return cam


def fp_camera(kind='hip', name=None):
    """In-game first-person eye (FirstPersonViewModel pose from pistol_frame.json)."""
    info = frame_info()
    p = vec3(info[kind]['pos'])
    q = vec3(info[kind]['rot'])  # x y z w (Unity)
    uq = Quaternion((q[3], q[0], q[1], q[2]))
    # Unity quaternion is for a left-handed frame; rotate the basis vectors in Unity space then map to metric.
    fwd_u = rot_unity(q, (0, 0, 1))
    up_u = rot_unity(q, (0, 1, 0))
    return camera(name or ('cam_fp_' + kind), unity_holder_to_metric(p), unity_dir_to_metric(fwd_u), unity_dir_to_metric(up_u),
                  fov_deg=float(info.get('fov', 50)))


def rot_unity(q, v):
    # plain quaternion rotation (the handedness does not change q*v as a linear map on Unity coordinates)
    x, y, z, w = q
    qv = Vector((x, y, z))
    vv = Vector(v)
    t = 2 * qv.cross(vv)
    return vv + w * t + qv.cross(t)


def setup_render(res=(1600, 900), samples=96, engine='CYCLES'):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Base Contrast'
    except Exception:
        pass
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 16
    return sc


def world_sky(strength=1.0, sun_elev=38.0, sun_rot=210.0, shade=False):
    w = bpy.data.worlds.new('sky') if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        try:
            sky.sky_type = t
            break
        except Exception:
            pass
    try:
        sky.sun_elevation = math.radians(sun_elev)
        sky.sun_rotation = math.radians(sun_rot)
        sky.sun_disc = False
        sky.air_density = 1.0
        sky.aerosol_density = 3.0
    except Exception:
        pass
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w


def sun_lamp(elev=38.0, azim=210.0, energy=4.5, color=(1.0, 0.86, 0.68), angle=0.6):
    ld = bpy.data.lights.new('sun', 'SUN')
    ld.energy = energy
    ld.color = color
    ld.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', ld)
    bpy.context.scene.collection.objects.link(o)
    e = math.radians(elev)
    a = math.radians(azim)
    d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))  # toward the sun
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def ground(z=-1.1, color=(0.42, 0.33, 0.24), size=40):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    g = bpy.context.active_object
    g.name = 'ground'
    m = bpy.data.materials.new('sand')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = 0.95
    g.data.materials.append(m)
    return g


def shade_blocker(sun, dist=3.0, size=6.0):
    """Big occluder between the sun and the subject: subject in open shade (skylight + ground bounce)."""
    d = (sun.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
    bpy.ops.mesh.primitive_plane_add(size=size, location=d * dist)
    p = bpy.context.active_object
    p.name = 'shade_blocker'
    p.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    p.visible_camera = False
    m = bpy.data.materials.new('blocker')
    m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.2, 0.17, 0.14, 1)
    p.data.materials.append(m)
    return p


def render(path, cam):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)
