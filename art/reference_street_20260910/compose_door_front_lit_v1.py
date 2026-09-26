"""STAGED: execute through the exclusive live Blender operator after metal-v4 AUTHOR.
COMPOSE_SOURCE_REVISION='candidate-v1'; COMPOSE_REVISION='candidate-v1-litfront-v1'.
Writes new texture derivatives only. No scene, mesh, Unity, or original map mutation.
Source composition may run before live Unity Inspect. Saved recipe coordinates
define this reversible audition; live Inspect+Apply must confirm them before installation.
"""
from pathlib import Path
import hashlib, json, math, struct, zlib, datetime
import numpy as np
import bpy  # Deliberate live-authoring entry requirement; no bpy mutation is used.

ROOT = Path('/home/teknetik/code/ao2')
HERE = ROOT/'art/reference_street_20260910/metal-v4'
SOURCE_REVISION = globals().get('COMPOSE_SOURCE_REVISION', 'candidate-v1')
REVISION = globals().get('COMPOSE_REVISION', SOURCE_REVISION+'-litfront-v1')
for name in (SOURCE_REVISION, REVISION):
    assert name and all(c.isalnum() or c in '-_' for c in name)
SOURCE = HERE/SOURCE_REVISION
OUT = HERE/REVISION
CONTRACT = json.loads((HERE/'front-lit-contract.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def decode_generated_png16(path, srgb=False):
    """Exact numeric decoder for our own checked, 16-bit filter-0 source encoder.
    This bypasses Image.pixels/OCIO assumptions without changing provider files.
    Input CRCs and schema are verified; another PNG encoding fails closed.
    """
    compressed = bytearray(); layout = None
    with path.open('rb') as f:
        assert f.read(8) == b'\x89PNG\r\n\x1a\n'
        while True:
            size, kind = struct.unpack('>I4s', f.read(8)); data = f.read(size)
            crc, = struct.unpack('>I', f.read(4)); assert crc == zlib.crc32(kind+data)&0xffffffff
            if kind == b'IHDR':
                w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
                assert depth == 16 and color in (0,2,6) and (compression,filtering,interlace) == (0,0,0)
                channels = {0:1,2:3,6:4}[color]; layout = (w,h,channels)
            elif kind == b'IDAT': compressed.extend(data)
            elif kind == b'IEND': break
    assert layout is not None
    raw = np.frombuffer(zlib.decompress(compressed), np.uint8).reshape(h, 1+w*channels*2)
    assert not raw[:,0].any(), 'Only the staged producer filter-0 PNGs are supported'
    a = np.frombuffer(raw[:,1:].copy().tobytes(), '>u2').reshape(h,w,channels).astype(np.float32)/65535
    a = a[::-1].copy()  # Internal bottom-up UV convention, independent of Blender pixels.
    if srgb: a = np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)
    return a


def png16(path, array, srgb=False):
    assert not path.exists() and np.isfinite(array).all()
    a = np.clip(array,0,1)
    if srgb: a = np.where(a <= .0031308,a*12.92,1.055*np.power(a,1/2.4)-.055)
    if a.ndim == 2: a = a[...,None]
    assert a.shape[2] in (1,3,4)
    a = np.rint(a*65535).astype('>u2')
    def chunk(f,name,data): f.write(struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff))
    with path.open('xb') as f:
        f.write(b'\x89PNG\r\n\x1a\n');chunk(f,b'IHDR',struct.pack('>IIBBBBB',a.shape[1],a.shape[0],16,{1:0,3:2,4:6}[a.shape[2]],0,0,0))
        compressor=zlib.compressobj(6)
        for row in a[::-1]:
            data=compressor.compress(b'\0'+row.tobytes())
            if data: chunk(f,b'IDAT',data)
        chunk(f,b'IDAT',compressor.flush());chunk(f,b'IEND',b'')


def sample_repeat(a,u,v):
    h,w=a.shape[:2];x=np.mod(u,1)*w-.5;y=np.mod(v,1)*h-.5
    ix=np.floor(x).astype(np.int32);iy=np.floor(y).astype(np.int32);fx=(x-ix)[...,None];fy=(y-iy)[...,None]
    return ((a[iy%h,ix%w]*(1-fx)+a[iy%h,(ix+1)%w]*fx)*(1-fy)
            +(a[(iy+1)%h,ix%w]*(1-fx)+a[(iy+1)%h,(ix+1)%w]*fx)*fy)


def verify():
    assert not OUT.exists(), 'Fresh output folder required'
    assert CONTRACT['schema']==1 and CONTRACT['frontTriangles']==24 and CONTRACT['duplicateVertices']==48
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    recipe_file=manifest.get('recipeFile','recipe.json')
    assert Path(recipe_file).name==recipe_file and recipe_file.endswith('.json')
    assert manifest['recipeSha256']==sha(HERE/recipe_file)
    recipe=json.loads((HERE/recipe_file).read_text())
    # The contract's original recipe hash records its geometry preparation. A
    # later reviewed art recipe may change paint/wear while retaining exactly
    # the same door domains, target roster and hardware registration.
    assert CONTRACT['doors']==recipe['doors'], 'Authored layer coordinates/handles must match the saved front contract'
    assert recipe['physicalOutputTileMetres']==4, 'Quiet-coat world sampling assumes the authored4m tile'
    readback=json.loads((SOURCE/'color-readback-guard.json').read_text())
    assert len(readback)==len(manifest['sourceMaps']) and all(r['passed'] for r in readback), 'Original source readback guard must pass first'
    wanted={'CoatedSteel'}|{d['family'] for d in CONTRACT['doors']};records={}
    for family in manifest['outputs']:
        if family['family'] not in wanted: continue
        assert family['family'] not in records
        channels={}
        for m in family['channels']:
            assert m['channel'] not in channels and m['bitDepth']==16
            p=SOURCE/m['file'];assert p.parent==SOURCE/family['family'] and sha(p)==m['sha256']
            channels[m['channel']]=p
        assert set(channels)=={'BaseColor','Normal','Roughness','Metallic','Opacity','WearMask'}
        records[family['family']]={'width':family['width'],'height':family['height'],'channels':channels}
    assert set(records)==wanted
    assert records['CoatedSteel']['width']==records['CoatedSteel']['height']==4096
    for door in CONTRACT['doors']:
        density=recipe['doorProjectionPixelsPerMetre']
        width=math.ceil((door['worldZRange'][1]-door['worldZRange'][0])*density/4)*4
        height=math.ceil((door['worldYRange'][1]-door['worldYRange'][0])*density/4)*4
        assert (records[door['family']]['width'],records[door['family']]['height'])==(width,height), 'Layer domain/density differs'
    return manifest,records


def compose():
    manifest,records=verify();OUT.mkdir();families=[]
    try:
        for door in CONTRACT['doors']:
            name=door['family'];record=records[name];w,h=record['width'],record['height'];dest=OUT/name;dest.mkdir()
            opacity=decode_generated_png16(record['channels']['Opacity']);assert opacity.shape==(h,w,1)
            lo,hi=door['worldZRange'];bottom,top=door['worldYRange']
            zs=(np.arange(w,dtype=np.float32)+.5)*(hi-lo)/w+lo
            ys=(np.arange(h,dtype=np.float32)+.5)*(top-bottom)/h+bottom
            maps=[];scalar={}
            for channel in ('BaseColor','Normal','Roughness','Metallic'):
                color=channel=='BaseColor';quiet=decode_generated_png16(records['CoatedSteel']['channels'][channel],color)
                layer=decode_generated_png16(record['channels'][channel],color);assert layer.shape[:2]==(h,w)
                out=np.empty_like(layer)
                for start in range(0,h,128):
                    end=min(h,start+128);z,y=np.meshgrid(zs,ys[start:end]);base=sample_repeat(quiet,z/4,y/4)
                    alpha=opacity[start:end]
                    if channel=='Normal':
                        # Coverage blend between complete material normals, not an added bump.
                        # Both inputs already use the declared +Z/+Y/-X front basis.
                        vector=(base*2-1)*(1-alpha)+(layer[start:end]*2-1)*alpha
                        vector/=np.maximum(np.linalg.norm(vector,axis=-1,keepdims=True),1e-8)
                        out[start:end]=vector*.5+.5
                    else: out[start:end]=base*(1-alpha)+layer[start:end]*alpha
                del quiet,layer
                if channel in ('Roughness','Metallic'): scalar[channel]=out
                else:
                    file=dest/(channel+'.png');png16(file,out,color);maps.append({'channel':channel,'file':file.name,'sha256':sha(file),'bitDepth':16,'space':'sRGB' if color else 'linear'})
                del out
            packed=np.zeros((h,w,4),np.float32);packed[:,:,0]=scalar['Metallic'][:,:,0];packed[:,:,3]=1-scalar['Roughness'][:,:,0]
            p=dest/'MetalSmooth.png';png16(p,packed);maps.append({'channel':'MetalSmooth','file':p.name,'sha256':sha(p),'bitDepth':16,'space':'linear','packing':'R=semantic metallic;G=B=0;A=1-semantic roughness'})
            check=decode_generated_png16(p);err=max(float(np.max(abs(check[:,:,0]-packed[:,:,0]))),float(np.max(abs(check[:,:,3]-packed[:,:,3]))));assert err<=.5/65535+np.finfo(np.float32).eps and not check[:,:,1:3].any()
            families.append({'family':name,'width':w,'height':h,'maps':maps,'worldZRange':door['worldZRange'],'worldYRange':door['worldYRange'],'packingMaxQuantizationError':err,'opaqueSurface':True})
            del opacity,scalar,packed,check
        report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'Standard URP Lit unique-front source derivatives; installation/source/native review pending','sourceRevision':SOURCE_REVISION,'sourceManifestSha256':sha(SOURCE/'manifest.json'),'recipeSha256':manifest['recipeSha256'],'recipeFile':manifest.get('recipeFile','recipe.json'),'contractSha256':sha(HERE/'front-lit-contract.json'),'scriptSha256':sha(ROOT/'art/reference_street_20260910/compose_door_front_lit_v1.py'),'normalBasis':'U=+worldZ,V=+worldY,N=-worldX','composite':'Quiet4m coat sampled in worldZ/Y, unpremultiplied door coverage blended exactly once; normal vectors normalized. Opaque output with semantic metallic/smoothness, no projection/overlay shader.','families':families,'geometryAuthored':False,'liveUnityInspectionRequiredBeforeInstallation':True,'sourceCompositionRequiresLiveUnity':False,'coordinateAuthority':'Saved authored recipe and exact front contract; current live geometry/handles must match during Inspect and Apply','nativeAccepted':False}
        (OUT/'composite-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'output':str(OUT),'families':len(families),'nativeInstalled':False}))
    except Exception as e:
        (OUT/'failure.json').write_text(json.dumps({'error':repr(e),'status':'Failed new output retained; originals untouched'},indent=2)+'\n');raise


if __name__=='__main__' or globals().get('RUN_DOOR_FRONT_COMPOSITE',False):
    compose()
