"""Inspect original GLB, retain embedded maps, prepare lossless Unity channel pack."""
import hashlib, io, json, struct, shutil
from pathlib import Path
from PIL import Image
R=Path('/home/teknetik/code/ao2');O=R/'meshy/platform-terminals-20260908';P=O/'source/terminal.glb'
raw=P.read_bytes();assert raw[:4]==b'glTF';chunks={};at=12
while at<len(raw):
 size,kind=struct.unpack_from('<II',raw,at);chunks[kind]=raw[at+8:at+8+size];at+=8+size
doc=json.loads(chunks[0x4e4f534a]);binary=chunks[0x004e4942]
folder=O/'embedded-textures';folder.mkdir(parents=True,exist_ok=True);images=[]
for i,item in enumerate(doc.get('images',[])):
 assert 'bufferView'in item, 'Expected self-contained source textures.'
 view=doc['bufferViews'][item['bufferView']];off=view.get('byteOffset',0);data=binary[off:off+view['byteLength']]
 ext='.jpg' if item['mimeType']=='image/jpeg' else '.png';path=folder/(str(i)+ext);path.write_bytes(data)
 im=Image.open(io.BytesIO(data));images.append({'index':i,'name':item.get('name'),'path':str(path.relative_to(R)),'size':list(im.size),'sha256':hashlib.sha256(data).hexdigest()})
def tex(index):return images[doc['textures'][index]['source']]
def rgb(index):return Image.open(R/tex(index)['path']).convert('RGB')
assert len(doc['materials'])==1,'Inspect material separation before generalizing importer.'
mat=doc['materials'][0];pbr=mat['pbrMetallicRoughness'];base=tex(pbr['baseColorTexture']['index']);normal=tex(mat['normalTexture']['index']);mr=tex(pbr['metallicRoughnessTexture']['index'])
runtime=R/'art/quality_20260908/platform-terminals/textures';runtime.mkdir(exist_ok=True)
# Prefer the separately delivered original PNG maps to the GLB's JPEG encodings.
original=O/'source/terminal_textures'
shutil.copy2(original/'base_color.png',runtime/'BaseColor.png');shutil.copy2(original/'normal.png',runtime/'Normal.png')
metal=Image.open(original/'metallic.png').convert('L');rough=Image.open(original/'roughness.png').convert('L');assert metal.size==rough.size
smooth=rough.point(lambda value:255-value)
Image.merge('RGBA',(metal,Image.new('L',metal.size,0),Image.new('L',metal.size,0),smooth)).save(runtime/'MetalSmooth.png')
report={'source':str(P.relative_to(R)),'sha256':hashlib.sha256(raw).hexdigest(),'triangles':sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),'attributes':[list(p['attributes'])for m in doc['meshes']for p in m['primitives']],'images':images,'materials':doc['materials'],'bindings':{'base':base,'normal':normal,'metallicRoughness':mr},'runtime_conversion':'Separately delivered full original PNG base/normal files copied byte-for-byte; metallic PNG -> Unity R and255-roughness PNG -> Unity A. GLB embedded JPEGs preserved for source comparison. Normal remains OpenGL tangent convention; no Y flip.','original_pngs':[{'path':str(p.relative_to(R)),'size':list(Image.open(p).size),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in original.glob('*.png')]}
(O/'source-buffer-inspection.json').write_text(json.dumps(report,indent=2));(O/'source/glb-document.json').write_text(json.dumps(doc,indent=2))
print(json.dumps({'triangles':report['triangles'],'images':images,'attributes':report['attributes']},indent=2))
