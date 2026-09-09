"""Stage full-resolution originals and exact URP roughness-channel conversion."""
import hashlib,json,pathlib,shutil
from PIL import Image,ImageOps

ROOT=pathlib.Path('/home/teknetik/code/ao2')
SOURCE=ROOT/'refs/quality_20260909/building-materials'
OUT=ROOT/'unity/AthenHill/Assets/AthenHill/Art/BuildingMaterials'
PAIRS={'WardPlaster':'beige_wall_001','WardStone':'rock_surface','WardConcrete':'rough_concrete','WardWornSteel':'rusty_metal_sheet'}

def gray8(image):
    # PIL's direct I;16 -> L clamps values over 255 instead of normalizing them.
    if image.mode.startswith('I;16') or image.mode=='I':
        return image.convert('F').point(lambda value:(value+128)/257).convert('L')
    return image.convert('L')

def stage():
    records=[]
    previous={r['slot']:r for r in json.loads((OUT/'material-manifest.json').read_text())} if (OUT/'material-manifest.json').exists() else {}
    for slot,asset in PAIRS.items():
        source=SOURCE/asset;record=json.loads((source/'download-manifest.json').read_text())
        maps={m['map']:m for m in record['maps']};target=OUT/slot;target.mkdir(parents=True,exist_ok=True)
        outputs={}
        for key,name in [('Diffuse','BaseColor.png'),('nor_gl','Normal.png')]:
            src=source/maps[key]['file'];dst=target/name
            if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()!=maps[key]['sha256']:raise RuntimeError('Preserve edited material source: '+str(dst))
            if not dst.exists():shutil.copyfile(src,dst)
            outputs[name]={'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'sourceIdentical':True,'size':Image.open(dst).size}
        source_rough=Image.open(source/maps['Rough']['file']);rough=gray8(source_rough)
        blank=Image.new('L',rough.size,0)
        metal=gray8(Image.open(source/maps['Metal']['file'])) if 'Metal' in maps else blank
        rgba=Image.merge('RGBA',(metal,blank,blank,ImageOps.invert(rough)))
        dst=target/'MetalSmooth.png'
        if dst.exists():
            if Image.open(dst).tobytes()!=rgba.tobytes():
                assert hashlib.sha256(dst.read_bytes()).hexdigest()==previous.get(slot,{}).get('outputs',{}).get(dst.name,{}).get('sha256'),'Preserve edited packed map: '+str(dst)
                rgba.save(dst)
        else:rgba.save(dst)
        assert Image.open(dst).getchannel('A').getextrema()==ImageOps.invert(rough).getextrema()
        outputs[dst.name]={'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'size':list(rough.size),'sourceRoughnessMode':source_rough.mode,'roughness8Extrema':rough.getextrema(),'packing':'R metallic; 16-bit data normalized with round(value/257); A = 255 - roughness; G/B zero','metallicSource':'source Metal' if 'Metal' in maps else 'zero: dielectric rock/plaster/concrete or painted and oxidized metal; no source metallic map'}
        records.append({'slot':slot,'asset':asset,'tileMetres':[x/1000 for x in record['dimensionsMillimetres']],'license':record['license'],'authors':record['authors'],'source':record['source'],'outputs':outputs})
    (OUT/'material-manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([{'slot':r['slot'],'tileMetres':r['tileMetres'],'originalDimensionsPreserved':True}for r in records]))

if __name__=='__main__':stage()
