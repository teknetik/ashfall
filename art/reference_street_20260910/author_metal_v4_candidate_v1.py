"""STAGED source authoring; execute only through the live Blender operator.

ACTION='AUTHOR' writes a fresh candidate revision, maps and an isolated .blend.
ACTION='PREVIEW' renders that saved studio in albedo and opposed soft lights.
No Unity assets, original meshes, UV0 or existing Blender scene are changed.
Door outputs are projected source layers, never replacement tiled Lit textures.
"""
from pathlib import Path
import hashlib, json, math, struct, zlib
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
HERE = ROOT/'art/reference_street_20260910/metal-v4'
RECIPE = json.loads((HERE/'recipe.json').read_text())
REVISION = globals().get('REVISION', RECIPE['outputRevision'])
assert REVISION.replace('-', '').replace('_', '').isalnum()
OUT = HERE/REVISION
SCENE = 'Reference metal v4 ' + REVISION
ACTION = globals().get('ACTION', 'AUTHOR')
CHANNELS = ('BaseColor', 'Normal', 'Roughness', 'Metallic', 'Opacity', 'WearMask')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    guard = RECIPE['guards']
    assert sha(HERE/'installed-registration.json') == guard['registrationSha256']
    assert sha(HERE/'source-inspection-meshes.json') == guard['inspectionMeshesSha256']
    assert sha(HERE/'source-inspection-hardware.json') == guard['hardwareInspectionSha256']
    for record in RECIPE['sources'].values():
        assert sha(ROOT/record['file']) == record['sha256'], record['file']
    for record in json.loads((HERE/'installed-registration.json').read_text())['roster']:
        p = ROOT/'unity/AthenHill'/record['meshAsset']
        assert sha(p) == record['meshSha256'], str(p)
    for path, digest in guard['existingMetalMaterialHashes'].items():
        assert sha(ROOT/path) == digest, path
    # Scene identity is recorded, not an execution lock: unrelated native work
    # may continue. A future installer must independently verify world transforms.


COLOR_READBACK = []


def raw_png_first_row(path):
    """Read original PNG samples without any colour-management library."""
    decompressor = zlib.decompressobj(); scan = b''; layout = None
    with path.open('rb') as f:
        assert f.read(8) == b'\x89PNG\r\n\x1a\n'
        while True:
            size, kind = struct.unpack('>I4s', f.read(8)); data = f.read(size); f.read(4)
            if kind == b'IHDR':
                w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
                assert depth in (8,16) and color in (0,2,6) and interlace == 0
                channels = {0:1,2:3,6:4}[color]; bpp = channels*(depth//8); stride = w*bpp
                layout = (w,h,depth,channels,bpp,stride)
            elif kind == b'IDAT':
                assert layout is not None
                scan += decompressor.decompress(data, stride+1-len(scan))
                if len(scan) == stride+1: break
            elif kind == b'IEND': raise AssertionError('PNG has no complete first scanline')
    filter_type = scan[0]; row = np.frombuffer(scan[1:], dtype=np.uint8).copy()
    # First scanline has a zero previous row. Thus Up is identity and Paeth
    # reduces to Sub. Average still depends on reconstructed left bytes.
    assert filter_type in (0,1,2,3,4)
    if filter_type in (1,3,4):
        for i in range(bpp, len(row)):
            left = int(row[i-bpp]); predictor = left//2 if filter_type == 3 else left
            row[i] = (int(row[i])+predictor)&255
    dtype = '>u2' if depth == 16 else np.uint8
    values = np.frombuffer(row.tobytes(), dtype=dtype).reshape(w,channels).astype(np.float64)/(65535 if depth == 16 else 255)
    return values, depth


def verify_image_readback(key, path, pixels):
    raw, depth = raw_png_first_row(path)
    columns = [37, 613, 1777, 2843, 4001]
    encoded = raw[columns, :3 if raw.shape[1] > 1 else 1]
    observed = pixels[-1,columns,:encoded.shape[1]]  # PNG top = Blender last row.
    expected = np.where(encoded <= .04045, encoded/12.92, ((encoded+.055)/1.055)**2.4) if key.endswith('color') else encoded
    error = float(np.max(np.abs(expected-observed)))
    encoded_error = float(np.max(np.abs(encoded-observed)))
    # Source precision is retained: reject 8-bit decoding of these 16-bit maps.
    tolerance = 2/65535 if depth == 16 else 2/255
    record = {'source':str(path.relative_to(ROOT)), 'sourceBitDepth':depth,
              'pngColumnsAtTopRow':columns, 'maxExpectedReadbackError':error,
              'maxEncodedReadbackError':encoded_error,
              'expected':'explicit sRGB EOTF scene-linear' if key.endswith('color') else 'raw linear numeric channels',
              'tolerance':tolerance, 'passed':error <= tolerance}
    COLOR_READBACK.append(record)
    (OUT/'color-readback-guard.json').write_text(json.dumps(COLOR_READBACK,indent=2)+'\n')
    assert record['passed'], ('Colour/precision readback failed before material generation: '+key+
        '; expected '+record['expected']+'; observed error='+str(error)+
        '. If encoded RGB matches instead, do not run png16 on it without an explicit reviewed EOTF conversion.')

def read_source(key):
    record = RECIPE['sources'][key]
    im = bpy.data.images.load(str(ROOT/record['file']), check_existing=False)
    try:
        im.colorspace_settings.name = 'sRGB' if key.endswith('color') else 'Non-Color'
        w, h = im.size
        data = np.empty(w*h*4, dtype=np.float32)
        im.pixels.foreach_get(data)
        channels = 1 if key.endswith('roughness') else 3
        pixels = data.reshape(h, w, 4)
        verify_image_readback(key, ROOT/record['file'], pixels)
        return pixels[:, :, :channels].copy()
    finally:
        bpy.data.images.remove(im)  # Only the new private image datablock.


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def normalized(n):
    return n/np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-8)


def sample(a, u, v):
    """Bilinear translation sampling in original source pixels, Blender bottom-up."""
    h, w = a.shape[:2]
    x = np.mod(u, 1)*w-.5
    y = np.mod(v, 1)*h-.5
    ix = np.floor(x).astype(np.int32); iy = np.floor(y).astype(np.int32)
    fx = (x-ix)[..., None]; fy = (y-iy)[..., None]
    return ((a[iy % h, ix % w]*(1-fx) + a[iy % h, (ix+1) % w]*fx)*(1-fy)
            + (a[(iy+1) % h, ix % w]*(1-fx) + a[(iy+1) % h, (ix+1) % w]*fx)*fy)


def coat_sample(a, x, y):
    """Overlap quilt: four translated samples, no warped/mirrored source axes."""
    x0, top, x1, bottom = RECIPE['coatSourceCropPixels']
    physical = RECIPE['coatSourceTileMetres']
    px, py = RECIPE['coatQuiltPeriodMetres']
    ox = (x1-x0)/4096*physical-px
    oy = (bottom-top)/4096*physical-py
    sx = np.mod(x, px); sy = np.mod(y, py)
    bx = 1-smooth(0, ox, sx); by = 1-smooth(0, oy, sy)
    u = x0/4096+sx/physical
    v = 1-bottom/4096+sy/physical
    # Shift only within crop-overlap strips; zero-weight samples are clamped
    # inside the verified source region instead of reading a photographed seam.
    u2 = x0/4096+(np.minimum(sx, ox)+px)/physical
    v2 = 1-bottom/4096+(np.minimum(sy, oy)+py)/physical
    a00 = sample(a, u, v); a10 = sample(a, u2, v)
    a01 = sample(a, u, v2); a11 = sample(a, u2, v2)
    return ((a00*(1-bx[..., None])+a10*bx[..., None])*(1-by[..., None])
            +(a01*(1-bx[..., None])+a11*bx[..., None])*by[..., None])


def capsule(x, y, start, end, radius, feather=.0008):
    dx = end[0]-start[0]; dy = end[1]-start[1]
    t = np.clip(((x-start[0])*dx+(y-start[1])*dy)/(dx*dx+dy*dy+1e-12), 0, 1)
    distance = np.hypot(x-start[0]-t*dx, y-start[1]-t*dy)
    # Submillimetre chip-edge variation only inside an authored physical stroke.
    edge = .00045*np.sin(x*2417+y*1679)*np.sin(x*1133-y*2087)
    return 1-smooth(radius+edge-feather, radius+edge+feather, distance)


def shutter_masks(z, y):
    wear = np.zeros_like(z); bare = np.zeros_like(z); dust = np.zeros_like(z)
    s = RECIPE['shutter']
    # Periodic copies in U respect the installed negative-world-Z / four-metre UV.
    for tile in (-3, -2, -1, 0, 1):
        zz = z+4*tile
        for row, choices in enumerate(s['rowSegmentChoices']):
            lower = s['firstBottomY']+row*s['pitchM']
            for choice in choices:
                lo, hi = s['lipSegmentsLocalFromLeftM'][choice]
                offset = .013*math.sin(row*1.71+choice)
                a = s['zRange'][0]+lo+offset; b = s['zRange'][0]+hi+offset
                yy = lower + (.003 if (row+choice) % 3 else s['slatHeightM']-.003)
                wear = np.maximum(wear, capsule(zz, y, (a, yy), (b, yy+.001), .0024+.0004*(row % 3)))
        for handle in s['liftHandles']:
            for shift in (-.115, .112):
                hx = handle['z']+shift
                bare = np.maximum(bare, capsule(zz, y, (hx-.023, 1.344), (hx+.018, 1.348), .0018))
                wear = np.maximum(wear, capsule(zz, y, (hx-.018, 1.302), (hx+.011, 1.300), .003))
        in_width = smooth(-10.68, -10.66, zz)*(1-smooth(-7.34, -7.32, zz))
        dust = np.maximum(dust, in_width*(1-smooth(.52, .72, y))*.24)
    return wear, bare*(1-wear), dust


def door_masks(z, y, door):
    wear = np.zeros_like(z); bare = np.zeros_like(z)
    h = door['handle']; n = int(door['family'][-1]); direction = -1 if n == 0 else 1
    # Three small strokes immediately outside the real plate/grip, not a halo
    # spread around an imagined handle in every repetition of the base texture.
    for dz, dy, length in [(.044, -.13, .038), (.063, -.055, .027), (.053, .115, .021)]:
        x = h['z']+direction*dz; yy = h['y']+dy
        bare = np.maximum(bare, capsule(z, y, (x, yy), (x+direction*length, yy+.009), .0017))
        wear = np.maximum(wear, capsule(z, y, (x-.006, yy-.005), (x+direction*length*.45, yy-.007), .0021))
    for index, hinge in enumerate(door['hinges']):
        x = hinge['z']; yy = hinge['y']
        wear = np.maximum(wear, capsule(z, y, (x-.025, yy-.045), (x+.018, yy-.048), .003))
        # A short mineral runoff below selected actual hardware, never all joints.
        if index == 0:
            wear = np.maximum(wear, capsule(z, y, (x+.007, yy-.048), (x+.011, yy-.107), .0013)*.48)
    lo, hi = door['worldZRange']; bottom = door['worldYRange'][0]
    for x, sign in [(lo+.016, 1), (hi-.018, -1)]:
        wear = np.maximum(wear, capsule(z, y, (x, bottom+.035), (x+sign*.044, bottom+.049), .004))
    dust = (1-smooth(bottom+.03, bottom+.19, y))*.24
    return wear, bare*(1-wear), dust


def material_arrays(source, x, y, wear, bare, dust):
    c = coat_sample(source['coat_color'], x, y)
    n = normalized(coat_sample(source['coat_normal'], x, y)*2-1)
    r = coat_sample(source['coat_roughness'], x, y)[..., 0]
    lum = c @ np.array([.2126, .7152, .0722], np.float32)
    blue = np.maximum(c[..., 2]-c[..., 0], c[..., 2]-c[..., 1])
    pigment = smooth(.002, .018, blue)
    charcoal = lum[..., None]*np.array([.93, 1, .97], np.float32)
    c = c*(1-pigment[..., None])+charcoal*pigment[..., None]
    # Photo roughness remains intact on quiet paint. Local source layers drive
    # oxidation/dust and handled abrasion; there is no global roughness flattening.
    oc = sample(source['oxide_color'], x/2, y/2)
    on = normalized(sample(source['oxide_normal'], x/2, y/2)*2-1)
    rough_oxide = sample(source['oxide_roughness'], x/2, y/2)[..., 0]
    # Retain fine real oxide variation; its gray surviving paint is suppressed
    # inside newly authored coating failures, not interpreted as exposed metal.
    ol = oc @ np.array([.2126, .7152, .0722], np.float32)
    oxide = oc*.55 + (ol[..., None]*np.array([1.18, .54, .20], np.float32))*.45
    c = c*(1-wear[..., None])+oxide*wear[..., None]
    n = normalized(n*(1-wear[..., None])+on*wear[..., None])
    r = r*(1-wear)+rough_oxide*wear
    c = c*(1-bare[..., None])+np.array([.28, .27, .24], np.float32)*bare[..., None]
    r = r*(1-bare)+coat_sample(source['coat_roughness'], x+.23, y+.17)[..., 0]*bare
    c = c*(1-dust[..., None])+np.array([.16, .133, .094], np.float32)*dust[..., None]
    r = r*(1-dust)+.92*dust
    return c, n*.5+.5, r, bare*.9, np.maximum.reduce([wear, bare, dust]), wear


def png16(path, array, srgb=False):
    """Explicit 16-bit PNG encoding: no view transform, lighting or OCIO bake."""
    assert not path.exists() and not path.with_suffix('.part').exists()
    a = np.clip(array, 0, 1)
    if srgb:
        a = np.where(a <= .0031308, a*12.92, 1.055*np.power(a, 1/2.4)-.055)
    if a.ndim == 2: a = a[..., None]
    assert a.shape[2] in (1, 3)
    a = np.rint(a*65535).astype('>u2')
    def chunk(f, name, data):
        f.write(struct.pack('>I', len(data))+name+data+struct.pack('>I', zlib.crc32(name+data)&0xffffffff))
    part = path.with_suffix('.part')
    with part.open('xb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        chunk(f, b'IHDR', struct.pack('>IIBBBBB', a.shape[1], a.shape[0], 16, 0 if a.shape[2] == 1 else 2, 0, 0, 0))
        compressor = zlib.compressobj(6)
        for row in a[::-1]:  # Input arrays use Blender's bottom-left origin.
            data = compressor.compress(b'\0'+row.tobytes())
            if data: chunk(f, b'IDAT', data)
        chunk(f, b'IDAT', compressor.flush()); chunk(f, b'IEND', b'')
    part.rename(path)


def make_maps(source, family, door=None):
    folder = OUT/family; folder.mkdir()
    if door:
        lo, hi = door['worldZRange']; bottom, top = door['worldYRange']
        density = RECIPE['doorProjectionPixelsPerMetre']
        w = math.ceil((hi-lo)*density/4)*4; h = math.ceil((top-bottom)*density/4)*4
        xs = np.linspace(lo, hi, w, endpoint=False, dtype=np.float32)+(hi-lo)/(2*w)
        ys = np.linspace(bottom, top, h, endpoint=False, dtype=np.float32)+(top-bottom)/(2*h)
    else:
        w = h = RECIPE['tilePixels']; xs = (np.arange(w, dtype=np.float32)+.5)*4/w; ys = (np.arange(h, dtype=np.float32)+.5)*4/h
    channels = {ch: np.empty((h, w, 3) if ch in ('BaseColor', 'Normal') else (h, w), np.float32) for ch in CHANNELS}
    for start in range(0, h, 128):
        end = min(h, start+128); x, y = np.meshgrid(xs, ys[start:end])
        if door: masks = door_masks(x, y, door)
        elif family == 'ShutterSteel': masks = shutter_masks(x, y)
        else: masks = (np.zeros_like(x),)*3
        # Independent slats can have translated coating scuffs, without rotating
        # normal-map axes or stretching scratches to match a modeled lip.
        sx = x.copy()
        if family == 'ShutterSteel':
            row = np.floor((y-.506)/.14)
            sx += np.mod(row*row*.137, .8)
        if door:
            opacity = np.maximum.reduce(masks)
            layer_masks = tuple(m/np.maximum(opacity, 1e-8) for m in masks)
            data = list(material_arrays(source, sx, y, *layer_masks))
            data[4] = opacity  # Unpremultiplied PBR layer; blend once in projection.
            data[5] = masks[0]
        else:
            data = material_arrays(source, sx, y, *masks)
        for ch, value in zip(CHANNELS, data): channels[ch][start:end] = value
        if not door: channels['Opacity'][start:end] = 1
    record = {'family': family, 'width': w, 'height': h, 'channels': [], 'use': 'Projected layer only' if door else 'Four metre material tile'}
    for ch, values in channels.items():
        p = folder/(ch+'.png'); png16(p, values, srgb=ch == 'BaseColor')
        record['channels'].append({'channel': ch, 'file': str(p.relative_to(OUT)), 'sha256': sha(p), 'bitDepth': 16, 'space': 'sRGB' if ch == 'BaseColor' else 'linear'})
    (folder/'maps.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def studio_material(scene, family, scale, door=None):
    m = bpy.data.materials.new(SCENE+' '+family+' '+str(scale)); m.use_nodes = True
    nodes = m.node_tree.nodes; links = m.node_tree.links; bs = nodes.get('Principled BSDF')
    uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UV0 retained'
    mapping = nodes.new('ShaderNodeVectorMath'); mapping.operation = 'SCALE'; mapping.inputs[3].default_value = scale; links.new(uv.outputs['UV'], mapping.inputs[0])
    def maps(folder, coord):
        result = {}
        for ch in CHANNELS:
            t = nodes.new('ShaderNodeTexImage'); t.label = folder+'/'+ch
            im = bpy.data.images.load(str(OUT/folder/(ch+'.png')), check_existing=True)
            im.colorspace_settings.name = 'sRGB' if ch == 'BaseColor' else 'Non-Color'; t.image = im
            t.extension = 'CLIP' if folder.startswith(('FieldDoor', 'FineryDoor')) else 'REPEAT'
            links.new(coord, t.inputs['Vector']); result[ch] = t.outputs['Color']
        return result
    base = maps('ShutterSteel' if family == 'ShutterSteel' else 'CoatedSteel', mapping.outputs['Vector'])
    if door:
        project = nodes.new('ShaderNodeUVMap'); project.uv_map = 'V4 preview projection ONLY'
        layer = maps(door['family'], project.outputs['UV'])
        # Projection U follows +worldZ; retained door UV0 U follows -worldZ.
        # Flip tangent X for this preview conversion only; exported projector
        # normals remain in their declared +Z/+Y image basis.
        sep_normal = nodes.new('ShaderNodeSeparateColor'); sep_normal.mode = 'RGB'
        links.new(layer['Normal'], sep_normal.inputs[0])
        flip = nodes.new('ShaderNodeMath'); flip.operation = 'SUBTRACT'; flip.inputs[0].default_value = 1
        links.new(sep_normal.outputs[0], flip.inputs[1])
        combine = nodes.new('ShaderNodeCombineColor'); combine.mode = 'RGB'
        links.new(flip.outputs[0], combine.inputs[0]); links.new(sep_normal.outputs[1], combine.inputs[1]); links.new(sep_normal.outputs[2], combine.inputs[2])
        layer['Normal'] = combine.outputs[0]
        geom = nodes.new('ShaderNodeNewGeometry'); sep = nodes.new('ShaderNodeSeparateXYZ'); links.new(geom.outputs['Normal'], sep.inputs[0])
        facing = nodes.new('ShaderNodeMath'); facing.operation = 'LESS_THAN'; facing.inputs[1].default_value = -.5; links.new(sep.outputs['X'], facing.inputs[0])
        opacity = nodes.new('ShaderNodeMath'); opacity.operation = 'MULTIPLY'; links.new(facing.outputs[0], opacity.inputs[0]); links.new(layer['Opacity'], opacity.inputs[1])
        for ch in ('BaseColor', 'Normal', 'Roughness', 'Metallic'):
            mix = nodes.new('ShaderNodeMixRGB'); links.new(opacity.outputs[0], mix.inputs[0]); links.new(base[ch], mix.inputs[1]); links.new(layer[ch], mix.inputs[2]); base[ch] = mix.outputs[0]
    links.new(base['BaseColor'], bs.inputs['Base Color']); links.new(base['Roughness'], bs.inputs['Roughness']); links.new(base['Metallic'], bs.inputs['Metallic'])
    normal = nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value = 1
    links.new(base['Normal'], normal.inputs['Color']); links.new(normal.outputs[0], bs.inputs['Normal'])
    # Retain unlit inspection connection without changing any unrelated material.
    emission = nodes.new('ShaderNodeEmission'); emission.name = 'V4 albedo inspection'; links.new(base['BaseColor'], emission.inputs['Color'])
    return m


def make_studio():
    assert SCENE not in bpy.data.scenes
    scene = bpy.data.scenes.new(SCENE); bpy.context.window.scene = scene
    scene.unit_settings.system = 'METRIC'; scene.render.engine = 'CYCLES'; scene.cycles.samples = 48
    scene.view_settings.view_transform = 'Standard'; scene.view_settings.look = 'None'; scene.view_settings.exposure = 0; scene.view_settings.gamma = 1
    scene.world = bpy.data.worlds.new(SCENE+' neutral world'); scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .4
    rows = json.loads((HERE/'source-inspection-meshes.json').read_text())
    guard = {r['path']: r for r in json.loads((HERE/'installed-registration.json').read_text())['roster']}
    doors = {d['family']: d for d in RECIPE['doors']}
    for row in rows:
        mesh = bpy.data.meshes.new(SCENE+' '+row['path']); pos = [(p[0], -p[2], p[1]) for p in row['positions']]
        faces = np.asarray(row['indices']).reshape(-1, 3).tolist(); mesh.from_pydata(pos, [], faces); mesh.update()
        # Unity-to-Blender axis transform has positive determinant; indices unchanged.
        mesh.normals_split_custom_set_from_vertices([(n[0], -n[2], n[1]) for n in row['normals']])
        uv = mesh.uv_layers.new(name='UV0 retained')
        for loop in mesh.loops: uv.data[loop.index].uv = row['uv'][loop.vertex_index]
        door = doors.get(row['family'])
        if door:
            projection = mesh.uv_layers.new(name='V4 preview projection ONLY')
            lo, hi = door['worldZRange']; bottom, top = door['worldYRange']
            for loop in mesh.loops:
                p = row['positions'][loop.vertex_index]
                projection.data[loop.index].uv = ((p[2]-lo)/(hi-lo), (p[1]-bottom)/(top-bottom))
        # The extra preview UV never overwrites UV0 and is not exported to Unity.
        mesh.uv_layers.active_index = 0
        obj = bpy.data.objects.new(row['path'].rsplit('/', 1)[-1], mesh); scene.collection.objects.link(obj)
        obj['originalSourcePath'] = row['path']; obj['notForUnityMeshExport'] = True
        obj.data.materials.append(studio_material(scene, row['family'], guard[row['path']]['currentBaseScale'][0], door))
    # Exact retained hardware is context for registration only. Its simple bronze
    # preview material is not a proposed replacement for installed hardware.
    context = bpy.data.materials.new(SCENE+' context hardware only'); context.use_nodes = True
    cb = context.node_tree.nodes['Principled BSDF']; cb.inputs['Base Color'].default_value = (.16,.105,.047,1); cb.inputs['Metallic'].default_value = .75; cb.inputs['Roughness'].default_value = .4
    ce = context.node_tree.nodes.new('ShaderNodeEmission'); ce.name = 'V4 albedo inspection'; ce.inputs['Color'].default_value = (.16,.105,.047,1)
    for row in json.loads((HERE/'source-inspection-hardware.json').read_text()):
        mesh = bpy.data.meshes.new(SCENE+' context '+row['path']); mesh.from_pydata([(p[0],-p[2],p[1]) for p in row['positions']], [], np.asarray(row['indices']).reshape(-1,3).tolist()); mesh.update()
        mesh.normals_split_custom_set_from_vertices([(n[0],-n[2],n[1]) for n in row['normals']])
        obj = bpy.data.objects.new(row['path'].rsplit('/',1)[-1], mesh); scene.collection.objects.link(obj); obj.data.materials.append(context); obj['contextOnly'] = True
    scene['sourceOnly'] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'metal-v4-source.blend'))
    return scene


def preview():
    scene = bpy.data.scenes.get(SCENE)
    assert scene is not None, 'Load the saved v4 source .blend first'
    folder = OUT/'previews'; folder.mkdir(exist_ok=False)
    bpy.context.window.scene = scene
    scene.render.resolution_x = 1920; scene.render.resolution_y = 1080; scene.render.resolution_percentage = 100
    cam_data = bpy.data.cameras.new(SCENE+' camera'); cam = bpy.data.objects.new(SCENE+' camera', cam_data); scene.collection.objects.link(cam); scene.camera = cam
    cam_data.type = 'ORTHO'
    light_data = bpy.data.lights.new(SCENE+' opposed soft source', 'AREA'); light = bpy.data.objects.new(SCENE+' opposed soft source', light_data); scene.collection.objects.link(light); light_data.energy = 550; light_data.shape = 'DISK'; light_data.size = 3
    mats = {m for obj in scene.objects if obj.type == 'MESH' for m in obj.data.materials}
    records = []
    for site, z, y, span in [('field', -8.35, 1.72, 5.4), ('finery', -18, 1.705, 3.35)]:
        target = Vector((18 if site == 'field' else 17, -z, y)); cam.location = target+Vector((-7, 0, .15)); cam.rotation_euler = (target-cam.location).to_track_quat('-Z', 'Y').to_euler(); cam_data.ortho_scale = span
        for mode, side in [('albedo', 0), ('soft-left', -1), ('soft-right', 1)]:
            for m in mats:
                nodes = m.node_tree.nodes; output = nodes.get('Material Output')
                selected = nodes['V4 albedo inspection'] if mode == 'albedo' else nodes['Principled BSDF']
                m.node_tree.links.new(selected.outputs[0], output.inputs['Surface'])
            light.location = target+Vector((-3, side*3, 3)); light.rotation_euler = (target-light.location).to_track_quat('-Z', 'Y').to_euler()
            p = folder/(site+'-'+mode+'.png'); scene.render.filepath = str(p); bpy.ops.render.render(write_still=True)
            records.append({'file':p.name, 'sha256':sha(p), 'sourceOnly':True, 'mode':mode})
    (folder/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'metal-v4-source-preview.blend'))


if ACTION == 'AUTHOR':
    verify(); OUT.mkdir(exist_ok=False)
    (OUT/'recipe-used.json').write_text(json.dumps(RECIPE, indent=2)+'\n')
    source = {key: read_source(key) for key in RECIPE['sources']}
    records = [make_maps(source, 'CoatedSteel'), make_maps(source, 'ShutterSteel')]
    records += [make_maps(source, d['family'], d) for d in RECIPE['doors']]
    del source
    make_studio()
    (OUT/'manifest.json').write_text(json.dumps({'status':'SOURCE CANDIDATE; no native acceptance', 'recipeSha256':sha(HERE/'recipe.json'), 'sourceMaps':RECIPE['sources'], 'outputs':records, 'doorProjectionWarning':'Existing UVs alias multiple surfaces. Door outputs require front-facing depth-limited projection, not tiled Lit assignment.'}, indent=2)+'\n')
    print(json.dumps({'source':str(OUT/'metal-v4-source.blend'), 'families':len(records), 'nativeInstalled':False}))
elif ACTION == 'PREVIEW':
    preview()
else:
    raise ValueError('ACTION must be AUTHOR or PREVIEW')
