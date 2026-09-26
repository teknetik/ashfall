"""STAGED source-only packager; exclusive live Blender operator runs after AUTHOR.
Set COATING_SOURCE_REVISION and COATING_PACKAGE_REVISION explicitly, then
RUN_METAL_COATING_PACKAGE=True. No scene/mesh/Assets mutation. Review is separate.
"""
from pathlib import Path
import datetime, hashlib, json, runpy, shutil
import numpy as np
import bpy  # Uses the existing live authoring session; no bpy operations.

ROOT=Path('/home/teknetik/code/ao2')
HERE=ROOT/'art/reference_street_20260910/metal-v4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def package():
    source_revision=globals().get('COATING_SOURCE_REVISION')
    revision=globals().get('COATING_PACKAGE_REVISION')
    for name in (source_revision,revision):
        assert name and all(c.isalnum() or c in '-_' for c in name), 'Explicit simple source and new package revision required'
    source=HERE/source_revision; out=HERE/revision
    assert not out.exists(), 'Preserve prior outputs; use a fresh package revision'
    manifest=json.loads((source/'manifest.json').read_text())
    recipe_file=manifest.get('recipeFile','recipe.json')
    assert Path(recipe_file).name==recipe_file and recipe_file.endswith('.json')
    assert sha(HERE/recipe_file)==manifest['recipeSha256']
    recipe=json.loads((HERE/recipe_file).read_text());contract=json.loads((HERE/'coating-contract.json').read_text())
    assert recipe['physicalOutputTileMetres']==4 and recipe['tilePixels']==4096
    assert sorted(recipe['shutter']['targets'])==sorted(r['path'] for r in contract['targets'] if r['group']=='ShutterSteel')
    readback=json.loads((source/'color-readback-guard.json').read_text())
    assert len(readback)==len(manifest['sourceMaps'])==6 and all(r['passed'] for r in readback)
    records={}
    for family in manifest['outputs']:
        name=family['family']
        if name not in ('CoatedSteel','ShutterSteel'): continue
        assert name not in records and family['width']==family['height']==4096
        channels={}
        for row in family['channels']:
            ch=row['channel'];p=source/row['file']
            assert ch not in channels and row['bitDepth']==16 and p.parent==source/name and sha(p)==row['sha256']
            channels[ch]=p
        assert set(channels)=={'BaseColor','Normal','Roughness','Metallic','Opacity','WearMask'}
        records[name]=channels
    assert set(records)=={'CoatedSteel','ShutterSteel'}
    codec_path=ROOT/'art/reference_street_20260910/compose_door_front_lit_v1.py'
    codec=runpy.run_path(str(codec_path),run_name='_coating_png_codec',init_globals={'RUN_DOOR_FRONT_COMPOSITE':False})
    decode=codec['decode_generated_png16'];encode=codec['png16']
    out.mkdir();families=[]
    try:
        for name,channels in records.items():
            dest=out/name;dest.mkdir();maps=[]
            for ch in ('BaseColor','Normal'):
                # Copy already-authored bytes: no second color conversion or normal remapping.
                a=decode(channels[ch]);assert a.shape==(4096,4096,3) and np.isfinite(a).all();del a
                p=dest/(ch+'.png');shutil.copyfile(channels[ch],p)
                assert sha(p)==sha(channels[ch])
                maps.append({'channel':ch,'file':p.name,'sha256':sha(p),'bitDepth':16,'space':'sRGB' if ch=='BaseColor' else 'linear','authoredBytesPreserved':True})
            # Recover the exact authored integer samples, invert roughness in integer
            # space, and retain all 65,536 levels in RGBA16. Never sample Unity mips.
            rough=np.rint(decode(channels['Roughness'])*65535).astype(np.uint16)
            metal=np.rint(decode(channels['Metallic'])*65535).astype(np.uint16)
            assert rough.shape==metal.shape==(4096,4096,1)
            packed=np.zeros((4096,4096,4),np.uint16);packed[:,:,0]=metal[:,:,0];packed[:,:,3]=65535-rough[:,:,0]
            p=dest/'MetalSmooth.png';encode(p,packed.astype(np.float32)/65535)
            check=np.rint(decode(p)*65535).astype(np.uint16)
            assert np.array_equal(check,packed), 'RGBA16 integer packing roundtrip differs'
            maps.append({'channel':'MetalSmooth','file':p.name,'sha256':sha(p),'bitDepth':16,'space':'linear','packing':'R=authored metallic;G=B=0;A=65535-authored roughness in uint16','integerRoundtripExact':True})
            families.append({'family':name,'width':4096,'height':4096,'physicalTileMetres':4,'maps':maps})
            del rough,metal,packed,check
        report={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packageRevision':revision,'sourceRevision':source_revision,'sourceManifestSha256':sha(source/'manifest.json'),'sourceReadbackSha256':sha(source/'color-readback-guard.json'),'sourceReadbackChecksPassed':6,'recipeFile':recipe_file,'recipeSha256':sha(HERE/recipe_file),'contractSha256':sha(HERE/'coating-contract.json'),'codecSha256':sha(codec_path),'scriptSha256':sha(ROOT/'art/reference_street_20260910/package_metal_coating_v1.py'),'families':families,'sourceAccepted':False,'nativeAccepted':False,'status':'Source packaging only. Root selects this revision after independent source/composite review; installation and native review pending.'}
        (out/'coating-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'output':str(out),'families':2,'exact16BitPacking':True,'nativeInstalled':False}))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps({'error':repr(error),'status':'Failed new output retained; originals untouched'},indent=2)+'\n');raise


if __name__=='__main__' or globals().get('RUN_METAL_COATING_PACKAGE',False):
    package()
