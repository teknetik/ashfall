"""Live Blender only. Prepare once, then render one named view/light per call.

All inspection materials use the actual proposed runtime maps and transforms.
The original V3 source scene and source studio remain unchanged on disk.
"""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910/canopy-weathering-v1'
ORIGINAL = ROOT / 'art/reference_street_20260910/canopy-v3/finery-canopy-v3.blend'
SCENE = 'Finery weathered canvas source inspection v1'
ACTION = globals().get('CANVAS_PREVIEW_ACTION', 'PREPARE')
VIEW = globals().get('CANVAS_VIEW', 'top')
LIGHT = globals().get('CANVAS_LIGHT', 'sun')
VIEWS = {
    'top': ((10.6, 6.3, -12.7), (14.55, 3.5, -18.4), 58),
    'under': ((11.1, 2.2, -14.5), (14.1, 3.55, -18.3), 56),
    'hem': ((10.9, 3.5, -17.4), (12.2, 3.35, -18.1), 48),
    'repair': ((12.8, 4.7, -18.0), (13.7, 3.3, -19.07), 40),
}


def B(p): return Vector((p[0], -p[2], p[1]))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    assert not (OUT / 'canvas-weathering-inspection-v1.blend').exists()
    assert SCENE not in bpy.data.scenes
    contract = json.loads((OUT / 'material-authoring-contract.json').read_text())
    with bpy.data.libraries.load(str(ORIGINAL), link=False) as (available, load):
        name = 'Finery tensioned canopy 20260910 v3 source scene'
        assert name in available.scenes
        load.scenes = [name]
    scene = load.scenes[0]
    scene.name = SCENE
    bpy.context.window.scene = scene
    specs = contract['familyContracts']
    materials = {}
    for family in ['Membrane', 'Valance', 'Seam', 'Repair']:
        spec = specs[family]
        m = bpy.data.materials.new(SCENE + ' ' + family); m.use_nodes = True
        ns, links = m.node_tree.nodes, m.node_tree.links
        ns.clear()
        bs = ns.new('ShaderNodeBsdfPrincipled'); bs.name = 'Physical canvas'
        out = ns.new('ShaderNodeOutputMaterial'); links.new(bs.outputs[0], out.inputs['Surface'])
        uv = ns.new('ShaderNodeTexCoord')
        macro = ns.new('ShaderNodeVectorMath'); macro.operation = 'MULTIPLY'
        macro.inputs[1].default_value = (.4/spec['metres'][0], .4/spec['metres'][1], 1)
        links.new(uv.outputs['UV'], macro.inputs[0])
        fine = ns.new('ShaderNodeVectorMath'); fine.operation = 'SCALE'
        fine.inputs['Scale'].default_value = .4/.3; links.new(uv.outputs['UV'], fine.inputs[0])

        def tex(path, coord, srgb, repeat=True):
            n = ns.new('ShaderNodeTexImage')
            n.image = bpy.data.images.load(str(path), check_existing=True)
            n.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
            n.extension = 'REPEAT' if repeat else 'EXTEND'
            links.new(coord, n.inputs[0])
            return n

        base = tex(OUT/family/'BaseColor.png', macro.outputs[0], True, family == 'Seam')
        rough = tex(OUT/family/'Roughness.png', macro.outputs[0], False, family == 'Seam')
        detail = tex(OUT/'DetailFabric/BaseColor.png', fine.outputs[0], True)
        normal = tex(ROOT/'refs/reference-street/20260910/cloth-candidates/book_pattern/book_pattern_nor_gl_4k.png', fine.outputs[0], False)
        strength = contract['detailAlbedoStrengthAudition']
        scale = ns.new('ShaderNodeVectorMath'); scale.operation = 'SCALE'
        scale.inputs['Scale'].default_value = 2*strength; links.new(detail.outputs[0], scale.inputs[0])
        offset = ns.new('ShaderNodeVectorMath'); offset.operation = 'ADD'
        offset.inputs[1].default_value = (1-strength,)*3; links.new(scale.outputs[0], offset.inputs[0])
        color = ns.new('ShaderNodeVectorMath'); color.operation = 'MULTIPLY'
        links.new(base.outputs[0], color.inputs[0]); links.new(offset.outputs[0], color.inputs[1])
        links.new(color.outputs[0], bs.inputs['Base Color']); links.new(rough.outputs[0], bs.inputs['Roughness'])
        n = ns.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value = contract['normalStrengthAudition']
        links.new(normal.outputs[0], n.inputs['Color']); links.new(n.outputs[0], bs.inputs['Normal'])
        bs.inputs['Metallic'].default_value = 0
        # No Blender-only sheen or transmission: current shipping variant is Lit.
        bs.inputs['Sheen Weight'].default_value = 0
        materials[family] = m
    assignment = []
    for obj in scene.objects:
        kind = obj.get('material')
        if kind not in ['CanopyRed', 'CanopySeam', 'CanopyRepair']: continue
        role = 'Seam' if kind == 'CanopySeam' else 'Repair' if kind == 'CanopyRepair' else 'Membrane' if obj.get('sourcePath', '').endswith('Ochre red courtyard awning') else 'Valance'
        obj.data.materials.clear(); obj.data.materials.append(materials[role])
        assignment.append({'object': obj.name, 'family': role, 'polygons': len(obj.data.polygons)})
    assert len(assignment) == 6
    world = bpy.data.worlds.new(SCENE + ' environment'); world.use_nodes = True; scene.world = world
    world.node_tree.nodes['Background'].inputs[0].default_value = (.4, .52, .69, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .6
    sun = bpy.data.lights.new(SCENE + ' light', 'SUN'); sun.energy = 2.2; sun.angle = .012
    light = bpy.data.objects.new(SCENE + ' light', sun); scene.collection.objects.link(light)
    camera_data = bpy.data.cameras.new(SCENE + ' camera'); camera = bpy.data.objects.new(SCENE + ' camera', camera_data)
    scene.collection.objects.link(camera); scene.camera = camera
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 32; scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600; scene.render.resolution_y = 1000; scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.exposure = 0; scene.view_settings.gamma = 1
    (OUT/'preview-bindings.json').write_text(json.dumps({'source':str(ORIGINAL),'sourceSha256':sha(ORIGINAL),'assignments':assignment,'materialsUseRuntimeMaps':True,'renderIsNotUnityAcceptance':True}, indent=2))
    bpy.data.libraries.write(str(OUT/'canvas-weathering-inspection-v1.blend'), {scene}, fake_user=True)
    print('Prepared actual-map source preview; no render or native acceptance yet.')


def render():
    assert VIEW in VIEWS and LIGHT in ['sun', 'opposed', 'albedo']
    scene = bpy.data.scenes[SCENE]; bpy.context.window.scene = scene
    path = OUT/'renders'/(VIEW+'-'+LIGHT+'.png'); assert not path.exists()
    path.parent.mkdir(exist_ok=True)
    position, target, lens = VIEWS[VIEW]
    camera = scene.camera; camera.location = B(position)
    camera.rotation_euler = (B(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.angle = math.radians(lens)
    light = scene.objects[SCENE+' light']
    light.rotation_euler = (.5, -.7, -.55) if LIGHT != 'opposed' else (.5, .7, 2.59)
    changed = []
    if LIGHT == 'albedo':
        for mat in bpy.data.materials:
            if not mat.name.startswith(SCENE+' '): continue
            ns, links = mat.node_tree.nodes, mat.node_tree.links
            bs = ns.get('Physical canvas')
            if bs is None: continue
            output = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
            emit = ns.new('ShaderNodeEmission'); source = bs.inputs['Base Color'].links[0].from_socket
            links.new(source, emit.inputs['Color']); links.new(emit.outputs[0], output.inputs['Surface'])
            changed.append((mat, emit, output, bs))
    try:
        scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    finally:
        for mat, emit, output, bs in changed:
            mat.node_tree.links.new(bs.outputs[0], output.inputs['Surface']); mat.node_tree.nodes.remove(emit)
    path.with_suffix('.json').write_text(json.dumps({'view':VIEW,'lighting':LIGHT,'positionUnity':position,'targetUnity':target,'lensDegrees':lens,'sha256':sha(path),'actualMaps':True,'nativeAccepted':False}, indent=2))
    print(str(path))


if ACTION == 'PREPARE': prepare()
elif ACTION == 'RENDER': render()
else: raise ValueError('Use PREPARE or RENDER')
