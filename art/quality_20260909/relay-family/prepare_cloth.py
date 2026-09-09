"""Lossless source copy and exact dielectric roughness -> URP alpha packing."""
from PIL import Image, ImageOps
from pathlib import Path
import shutil,json,hashlib
r=Path('/home/teknetik/code/ao2');src=r/'refs/quality_20260909/basic-general/materials/fabric_pattern_07';out=r/'art/quality_20260909/relay-family/revision-01/textures';out.mkdir(parents=True,exist_ok=True)
n=Image.open(src/'fabric_pattern_07_nor_gl_4k.jpg');n.save(out/'ClothNormal.png')
rgh=Image.open(src/'fabric_pattern_07_rough_4k.jpg').convert('L');zero=Image.new('L',rgh.size,0);Image.merge('RGBA',(zero,zero,zero,ImageOps.invert(rgh))).save(out/'ClothMetalSmooth.png')
(out/'manifest.json').write_text(json.dumps({'source':'CC0 Poly Haven fabric_pattern_07; original maps and download hashes retained in refs/quality_20260909/basic-general/materials','normal':'Decoded original 4K JPEG pixels stored losslessly; OpenGL tangent normal convention retained','metalSmooth':'R=0 dielectric; G/B=0; A=255-original roughness','files':[{ 'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'dimensions':Image.open(p).size}for p in out.glob('*.png')]},indent=2))
