"""STAGED source authoring; execute only through the live Blender operator.

ACTION='AUTHOR' writes a fresh candidate revision, maps and an isolated .blend.
ACTION='PREVIEW' renders that saved studio in albedo and opposed soft lights.
No Unity assets, original meshes, UV0 or existing Blender scene are changed.
Candidate-v1 source/script/recipe are retained. Candidate-v2 explicitly repairs
identified macro motifs and authors separate local contact contours. Door outputs
remain source layers until the standard-Lit per-leaf compositor is run.
"""
from pathlib import Path
import hashlib, json, math, struct, zlib
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
HERE = ROOT/'art/reference_street_20260910/metal-v4'
RECIPE_FILE = globals().get('METAL_RECIPE_FILE','recipe-v2.json')
assert Path(RECIPE_FILE).name == RECIPE_FILE and RECIPE_FILE.endswith('.json')
RECIPE_PATH = HERE/RECIPE_FILE
RECIPE = json.loads(RECIPE_PATH.read_text())
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
    """Six source windows on one4m field. Translation only; original physical grain."""
    quilt = RECIPE['coatQuilt']; cell = quilt['tileMetres']/quilt['cellsPerAxis']; overlap = quilt['overlapMetres']
    physical = RECIPE['coatSourceTileMetres']; cells = quilt['cellsPerAxis']
    ix = np.floor(x/cell).astype(np.int32); iy = np.floor(y/cell).astype(np.int32)
    sx = np.mod(x, cell); sy = np.mod(y, cell)
    bx = 1-smooth(0, overlap, sx); by = 1-smooth(0, overlap, sy)
    layout = np.asarray(quilt['layout'], np.int32)
    origins = np.asarray([w['rectPixels'][:2] for w in RECIPE['coatPhotoWindows']], np.float32)
    def at(cx, cy, px, py):
        # Integer source-phase offsets fit inside the reviewed1280px window margin.
        xx = np.mod(cx,cells); yy = np.mod(cy,cells); index = layout[yy,xx]
        shift_x = np.mod(xx*17+yy*31,quilt['phaseMarginPixels']+1)
        shift_y = np.mod(xx*29+yy*11,quilt['phaseMarginPixels']+1)
        u = (origins[index,0]+shift_x)/4096+px/physical
        v = 1-(origins[index,1]+quilt['windowPixels']-shift_y)/4096+py/physical
        return sample(a,u,v)
    q00=at(ix,iy,sx,sy);q10=at(ix-1,iy,np.minimum(sx,overlap)+cell,sy)
    q01=at(ix,iy-1,sx,np.minimum(sy,overlap)+cell);q11=at(ix-1,iy-1,np.minimum(sx,overlap)+cell,np.minimum(sy,overlap)+cell)
    return ((q00*(1-bx[...,None])+q10*bx[...,None])*(1-by[...,None])
            +(q01*(1-bx[...,None])+q11*bx[...,None])*by[...,None])


def repair_coat_sources(source):
    """Paired donor repairs in private working arrays; all original PNGs retained."""
    keys=('coat_color','coat_normal','coat_roughness')
    original={key:source[key] for key in keys}; result={key:a.copy() for key,a in original.items()}
    records=[]
    for repair in RECIPE['coatSourceRepairs']:
        points=np.asarray(repair['pointsPixels'],np.float32);radius=repair['radiusPixels'];feather=repair['featherPixels']
        x0,y0=np.floor(points.min(0)-radius-feather-1).astype(int);x1,y1=np.ceil(points.max(0)+radius+feather+1).astype(int)
        dx,dy=repair['donorOffsetPixels'];assert min(x0,y0,x0+dx,y0+dy)>=0 and max(x1,y1,x1+dx,y1+dy)<4096
        xx,yy=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1));distance=np.full(xx.shape,np.inf)
        pairs=list(zip(points[:-1],points[1:])) if len(points)>1 else [(points[0],points[0])]
        for a,b in pairs:
            delta=b-a;t=np.clip(((xx-a[0])*delta[0]+(yy-a[1])*delta[1])/(float(delta@delta)+1e-12),0,1)
            distance=np.minimum(distance,np.hypot(xx-a[0]-t*delta[0],yy-a[1]-t*delta[1]))
        weight=(1-smooth(radius-feather,radius+feather,distance)).astype(np.float32)[...,None]
        for key in keys:
            donor=original[key][4095-(yy+dy),xx+dx]
            old=result[key][4095-yy,xx]
            result[key][4095-yy,xx]=old*(1-weight)+donor*weight
        records.append(dict(repair,affectedPixels=int((weight[:,:,0]>0).sum()),fullyReplacedPixels=int((weight[:,:,0]>.9999).sum())))
    for key in keys: source[key]=result[key]
    (OUT/'source-repair-record.json').write_text(json.dumps({'method':'Explicit bounded source-pixel donor translation; identical repair weights/coordinates for color,normal,roughness. No source file writes, scale/orientation changes or global filtering.','repairs':records,'outsideFootprintsUnchanged':True,'donorsReadFromUnmodifiedSourceArrays':True},indent=2)+'\n')
    return source



def capsule(x, y, start, end, radius, feather=.0008):
    dx = end[0]-start[0]; dy = end[1]-start[1]
    t = np.clip(((x-start[0])*dx+(y-start[1])*dy)/(dx*dx+dy*dy+1e-12), 0, 1)
    distance = np.hypot(x-start[0]-t*dx, y-start[1]-t*dy)
    # Submillimetre chip-edge variation only inside an authored physical stroke.
    edge = .00045*np.sin(x*2417+y*1679)*np.sin(x*1133-y*2087)
    return 1-smooth(radius+edge-feather, radius+edge+feather, distance)



def polygon_mask(x, y, vertices, feather=.00065):
    """Physical authored contour; no random field or procedural cloud coverage."""
    points=np.asarray(vertices,np.float32);inside=np.zeros_like(x,dtype=bool);distance=np.full(x.shape,np.inf,dtype=np.float32)
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        dx,dy=b-a;inside^=((a[1]>y)!=(b[1]>y))&(x<(dx*(y-a[1])/(dy+1e-20)+a[0]))
        t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy+1e-15),0,1)
        distance=np.minimum(distance,np.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
    return smooth(-feather,feather,np.where(inside,distance,-distance))


def shutter_masks(z, y):
    wear=np.zeros_like(z);bare=np.zeros_like(z);dust=np.zeros_like(z);rub=np.zeros_like(z);s=RECIPE['shutter']
    for tile in (-3,-2,-1,0,1):
        zz=z+4*tile
        for chip in s['chipIslands']:
            row=chip['row'];lower=s['firstBottomY']+row*s['pitchM']
            edge_y=lower+.0015 if chip['edge']=='bottom' else lower+s['slatHeightM']-.0015
            outline=np.asarray(s['chipProfiles'][chip['profile']],np.float32).copy()
            outline[:,0]=s['zRange'][0]+chip['fromLeftMetres']+outline[:,0]*chip['lengthMetres']
            outline[:,1]=edge_y+outline[:,1]*chip['depthMetres']
            patch=polygon_mask(zz,y,outline,feather=.00055)
            wear=np.maximum(wear,patch*(.88 if row<7 else .65))
        # Different hand contacts around the actual two lift handles, not four identical dashes.
        for index,h in enumerate(s['liftHandles']):
            side=-.11 if index==0 else .115;hx=h['z']+side;hy=h['y']
            profile=[[-.026,-.018],[-.019,-.033],[.003,-.04],[.023,-.022],[.029,.012],[.009,.034],[-.01,.024],[-.015,.004]] if index==0 else [[-.013,-.009],[-.008,-.03],[.012,-.037],[.027,-.018],[.024,.015],[.007,.021],[-.01,.008]]
            rub=np.maximum(rub,polygon_mask(zz,y,[(hx+a,hy+b) for a,b in profile],.003)*(.32 if index==0 else .21))
            chip=[(hx-.017,hy-.019),(hx-.008,hy-.025),(hx-.004,hy-.021),(hx+.002,hy-.02),(hx-.001,hy-.014),(hx-.01,hy-.012)] if index==0 else [(hx+.009,hy+.012),(hx+.017,hy+.009),(hx+.023,hy+.014),(hx+.02,hy+.02),(hx+.013,hy+.019)]
            wear=np.maximum(wear,polygon_mask(zz,y,chip)*.76)
        in_width=smooth(-10.68,-10.66,zz)*(1-smooth(-7.34,-7.32,zz))
        dust=np.maximum(dust,in_width*(1-smooth(.515,.64,y))*.16)
    return wear,bare*(1-wear),dust,rub


def door_masks(z, y, door):
    wear=np.zeros_like(z);bare=np.zeros_like(z);h=door['handle'];profile=RECIPE['doorWearProfiles'][door['family']]
    translated=lambda points:[(h['z']+a,h['y']+b) for a,b in points]
    rub=polygon_mask(z,y,translated(profile['rubOutline']),.004)*profile['rubCoverage']
    for contour in profile['chips']: wear=np.maximum(wear,polygon_mask(z,y,translated(contour))*.85)
    for stroke in profile['scrapes']:
        p=translated(stroke)
        for a,b in zip(p[:-1],p[1:]):bare=np.maximum(bare,capsule(z,y,a,b,.00085,feather=.00055)*.62)
    # A few actual hardware joints have small irregular paint losses. The leaves
    # deliberately use different joint selections and different lower contacts.
    family_index=['FieldDoor0','FieldDoor1','FineryDoor0','FineryDoor1'].index(door['family'])
    for index in profile['hingeIndices']:
        joint=door['hinges'][index];x=joint['z'];yy=joint['y'];side=1 if (family_index+index)%2 else -1
        contour=[(x+side*dx,yy+dy) for dx,dy in [(-.019,-.018),(-.008,-.024),(.001,-.02),(.009,-.03),(.022,-.028),(.026,-.016),(.018,-.012),(.007,-.014),(-.005,-.009),(-.015,-.012)]]
        wear=np.maximum(wear,polygon_mask(z,y,contour)*.62)
    lo,hi=door['worldZRange'];bottom=door['worldYRange'][0]
    for i,offset in enumerate(profile['lowerContact']):
        x=lo+offset;depth=.0045 if i==0 else .0028;length=.021 if i%2==0 else .012
        poly=RECIPE['shutter']['chipProfiles'][(family_index+i)%4]
        wear=np.maximum(wear,polygon_mask(z,y,[(x+a*length,bottom+.011+b*depth) for a,b in poly])*.72)
    dust=(1-smooth(bottom+.016,bottom+.14,y))*.16
    return wear,bare*(1-wear),dust,rub


def material_arrays(source, x, y, wear, bare, dust, rub):
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
    oxide = oc*.70 + (ol[..., None]*np.array([1.18, .54, .20], np.float32))*.30
    c = c*(1-wear[..., None])+oxide*wear[..., None]
    n = normalized(n*(1-wear[..., None])+on*wear[..., None])
    r = r*(1-wear)+rough_oxide*wear
    c = c*(1-bare[..., None])+np.array([.28, .27, .24], np.float32)*bare[..., None]
    r = r*(1-bare)+coat_sample(source['coat_roughness'], x+.23, y+.17)[..., 0]*bare
    # Hand rubbing changes only these authored coated contact zones. Keep source
    # roughness variation everywhere else; no all-over dry/flat replacement.
    c = c*(1-.05*rub[...,None])
    r = r*(1-rub)+np.maximum(r-.06,.12)*rub
    c = c*(1-dust[..., None])+np.array([.16, .133, .094], np.float32)*dust[..., None]
    r = r*(1-dust)+.92*dust
    return c, n*.5+.5, r, bare*.9, np.maximum.reduce([wear, bare, dust, rub]), wear


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
        else: masks = (np.zeros_like(x),)*4
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
    source = repair_coat_sources(source)
    records = [make_maps(source, 'CoatedSteel'), make_maps(source, 'ShutterSteel')]
    records += [make_maps(source, d['family'], d) for d in RECIPE['doors']]
    del source
    make_studio()
    (OUT/'manifest.json').write_text(json.dumps({'status':'SOURCE CANDIDATE; no native acceptance', 'recipeSha256':sha(RECIPE_PATH), 'recipeFile':RECIPE_FILE, 'authorScriptSha256':sha(ROOT/'art/reference_street_20260910/author_metal_v4.py'), 'sourceMaps':RECIPE['sources'], 'outputs':records, 'doorProjectionWarning':'Existing UVs alias multiple surfaces. Door outputs require front-facing depth-limited projection, not tiled Lit assignment.'}, indent=2)+'\n')
    print(json.dumps({'source':str(OUT/'metal-v4-source.blend'), 'families':len(records), 'nativeInstalled':False}))
elif ACTION == 'PREVIEW':
    preview()
else:
    raise ValueError('ACTION must be AUTHOR or PREVIEW')
