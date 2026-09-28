# Blender preview renders for build_fp_hands_v2.py: the in-game eye positions at hip and ADS (from pistol_frame.json)
# plus orthographic checks from the sides, front, below and behind. Preview only; Unity renders are the evidence.
import bpy, math
from mathutils import Vector, Quaternion, Matrix

def U2B(v): return Vector((v[0], v[2], v[1]))

def unity_cam(pos, rot, fov, name):
    p = [float(x) for x in pos.split(',')]; q = [float(x) for x in rot.split(',')]
    m = Quaternion((q[3], q[0], q[1], q[2])).to_matrix()
    fwd = U2B(m @ Vector((0, 0, 1))); up = U2B(m @ Vector((0, 1, 0)))
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(cam)
    z = -fwd.normalized(); y = up.normalized(); x = y.cross(z)
    cam.matrix_world = Matrix.Translation(U2B(p)) @ Matrix((x, y, z)).transposed().to_4x4()
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(fov); cam.data.clip_start = .01
    return cam

def ortho(name, loc_u, look_u, up_u=(0, 1, 0), scale=.32):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale; cam.data.clip_start = .001
    f = (U2B(look_u) - U2B(loc_u)).normalized(); up = U2B(up_u)
    z = -f; x = up.cross(z).normalized(); y = z.cross(x)
    cam.matrix_world = Matrix.Translation(U2B(loc_u)) @ Matrix((x, y, z)).transposed().to_4x4()
    return cam

def run(hands, extra, pistol, outdir, info):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.42, .36, .30, 1); bg.inputs[1].default_value = .7
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.data.color = (1, .82, .62)
    # low warm dusk key from behind-left of the shooter
    sun.matrix_world = Matrix.Rotation(math.radians(-70), 4, 'X') @ Matrix.Rotation(math.radians(35), 4, 'Z').to_4x4()
    sc.view_settings.view_transform = 'Standard'
    gm = bpy.data.materials.new('gun'); gm.use_nodes = True
    b = gm.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (.12, .13, .14, 1); b.inputs['Metallic'].default_value = .7; b.inputs['Roughness'].default_value = .4
    pistol.data.materials.clear(); pistol.data.materials.append(gm)
    views = [unity_cam(info['ads']['pos'], info['ads']['rot'], info['fov'], 'ads'), unity_cam(info['hip']['pos'], info['hip']['rot'], info['fov'], 'hip'),
             ortho('right', (.5, -.02, .02), (0, -.02, .02)), ortho('left', (-.5, -.02, .02), (0, -.02, .02)),
             ortho('front', (0, -.02, .5), (0, -.02, 0)), ortho('below', (0, -.5, .0), (0, 0, 0), (0, 0, 1)),
             ortho('behind', (0, .02, -.5), (0, .02, 0))]
    # behind at eye level with a longer lens, like the photo reference
    c = unity_cam('0,0.02,-0.55', '0,0,0,1', 22, 'photo'); views.append(c)
    for cam in views:
        sc.camera = cam; sc.render.filepath = outdir + '/' + cam.name + '.png'
        bpy.ops.render.render(write_still=True)
    pistol.hide_render = True
    for cam in views[2:5]:
        sc.camera = cam; sc.render.filepath = outdir + '/' + cam.name + '_nopistol.png'
        bpy.ops.render.render(write_still=True)
    pistol.hide_render = False
