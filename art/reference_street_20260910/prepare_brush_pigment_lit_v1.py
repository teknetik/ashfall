"""Offline channel packing and immutable receiver contract, never touches Assets.

Run with the bundled NumPy/Pillow Python. This is numeric channel composition,
not a repaint: Base RGB bytes and opacity R bytes are copied without conversion.
"""
from pathlib import Path
import hashlib, json, re, struct
import numpy as np
from PIL import Image

R = Path('/home/teknetik/code/ao2')
A = R/'art/reference_street_20260910'
S = A/'brush-pigment-v1'
O = A/'brush-pigment-lit-v1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = R/'art/reference_street_20260909/brush-graffiti-meshes-v3.json'
old = json.loads((S/'authoring-contract.json').read_text())
assert sha(source) == old['sourceSha256']
parts = json.loads(source.read_text())
assert len(parts) == 2 and [p['text'] for p in parts] == ['THE FACTORIES','NEVER SLEEP.']
assert not O.exists(), 'Retain existing candidate; use a separately reviewed revision.'
maps = {}
for key in ('BaseColor','Roughness','Opacity'):
    p = S/(key+'.png')
    raw = p.read_bytes()
    w,h,depth,kind = struct.unpack('>IIBB',raw[16:26])
    assert (w,h,depth) == (4096,4096,8), (key,w,h,depth)
    image = np.array(Image.open(p).convert('RGB'))
    # Scalar authority is explicitly R. PNG RGB dithering may differ by one code
    # value across channels; never average them or apply the sRGB transfer curve.
    if key != 'BaseColor': assert np.max(np.ptp(image.astype(np.int16),axis=2)) <= 1
    maps[key] = image

opacity = maps['Opacity'][:,:,0]
def sample(uv):
    xy = np.mod(uv,1)*4096-.5
    ix = np.floor(xy).astype(np.int32); f=xy-ix
    # Blender/Unity UV V=0 is bottom; PNG row zero is top.
    x=ix[:,0];y=ix[:,1];fx=f[:,0];fy=f[:,1]
    return ((opacity[4095-y%4096,x%4096]*(1-fx)+opacity[4095-y%4096,(x+1)%4096]*fx)*(1-fy)
       +(opacity[4095-(y+1)%4096,x%4096]*(1-fx)+opacity[4095-(y+1)%4096,(x+1)%4096]*fx)*fy)/255

coverage=[];targets=[]
report=json.loads((R/'unity/evidence/reference-street/20260909/metal-v3-installation.json').read_text())
material='Assets/AthenHill/Art/ReferenceStreet/20260909/BrushPaint.mat'
scene=R/'unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity'
scene_text=scene.read_text()
for part in parts:
    pos=np.asarray(part['positions']);uv=np.asarray(part['uv']);idx=np.asarray(part['indices']).reshape(-1,3)
    assert np.max(np.ptp(pos,axis=0)[0]) == 0, 'No lettering thickness is authorized.'
    assert np.max(abs(uv-pos[:,[2,1]]/4))<.000001, 'Actual metric UV0 changed.'
    assert not part['castsShadow'] and not part['collider']
    area=np.linalg.norm(np.cross(pos[idx[:,1]]-pos[idx[:,0]],pos[idx[:,2]]-pos[idx[:,0]]),axis=1)/2
    assert min(area)>0
    # Equal-area square-to-triangle integration, 225 samples per source triangle.
    ss=(np.arange(15)+.5)/15;u,v=np.meshgrid(ss,ss);root=np.sqrt(u.ravel());v=v.ravel()
    bary=np.stack((1-root,root*(1-v),root*v),axis=-1)
    sampleuv=np.einsum('ki,tij->tkj',bary,uv[idx])*2
    values=sample(sampleuv.reshape(-1,2)).reshape(len(idx),-1)
    cutrows=[{'cutoff':c,'retainedLetterAreaFraction':float(np.sum((values>=c).mean(1)*area)/area.sum())}for c in (.25,.35,.45,.55,.65,.75,.9)]
    coverage.append({'text':part['text'],'samples':int(values.size),'surfaceAreaM2':float(area.sum()),'cutoffs':cutrows})
    row=next(c for c in report['changes'] if c.get('path')==part['sourcePath'] and c.get('newMesh'))
    mesh=row['newMesh'];asset=R/'unity/AthenHill'/mesh
    guid=re.search(r'^guid: (\w+)',Path(str(asset)+'.meta').read_text(),re.M)[1]
    assert scene_text.count('guid: '+guid)==1, 'Expected exactly one saved mesh reference.'
    targets.append({'path':part['sourcePath'],'text':part['text'],'meshAsset':mesh,'meshGuid':guid,'meshSha256':sha(asset),'meshMetaSha256':sha(Path(str(asset)+'.meta')),
       'vertices':len(pos),'triangles':len(idx),'worldBoundsMin':pos.min(0).tolist(),'worldBoundsMax':pos.max(0).tolist(),'worldPositionToleranceMetres':.00003})

O.mkdir()
rgba=np.dstack((maps['BaseColor'],opacity))
packed=np.zeros_like(rgba);packed[:,:,3]=255-maps['Roughness'][:,:,0]
Image.fromarray(rgba,'RGBA').save(O/'BaseRGBA.png')
Image.fromarray(packed,'RGBA').save(O/'MetalSmooth.png')
checkcolor=np.asarray(Image.open(O/'BaseRGBA.png'));checkpacked=np.asarray(Image.open(O/'MetalSmooth.png'))
assert np.array_equal(checkcolor[:,:,:3],maps['BaseColor']) and np.array_equal(checkcolor[:,:,3],opacity)
assert not checkpacked[:,:,:3].any() and np.array_equal(checkpacked[:,:,3],255-maps['Roughness'][:,:,0])
contract={'schema':1,'revision':'brush-pigment-lit-v1','sourceMeshExport':str(source.relative_to(R)),'sourceMeshSha256':sha(source),
 'sourceContract':str((S/'authoring-contract.json').relative_to(R)),'sourceContractSha256':sha(S/'authoring-contract.json'),
 'sourceMapRecords':[{'channel':k,'file':str((S/(k+'.png')).relative_to(R)),'sha256':sha(S/(k+'.png')),'size':[4096,4096],'bitDepth':8,'colorSpace':'sRGB' if k=='BaseColor' else 'raw scalar'}for k in maps],
 'packedMaps':[{'file':n,'sha256':sha(O/n),'size':[4096,4096],'channels':meaning}for n,meaning in [('BaseRGBA.png','RGB=source encoded sRGB BaseColor RGB; A=raw Opacity R'),('MetalSmooth.png','RGB=0; A=255−raw Roughness R')]],
 'targets':targets,'oldMaterial':{'asset':material,'sha256':sha(R/'unity/AthenHill'/material),'metaSha256':sha(R/'unity/AthenHill'/(material+'.meta'))},
 'observedSavedSceneSha256':sha(scene),'sceneHashIsNotAnExecutionLock':True,
 'metresPerTile':[2,2],'sourceUVMetres':4,'baseMapScale':[2,2],'baseMapOffset':[0,0],'baseColor':[1,1,1,1],
 'cutoff':.45,'cutoffReason':'Sparse opacity losses preserve the original thin strokes and perimeter geometry. Retain the authored .45 threshold for source audition; measured actual-letter coverage is attached. Do not increase chip loss to imitate wear absent in the maps.',
 'material':'Universal Render Pipeline/Lit; opaque alpha clipping, cull off, metallic R0, smoothness from packed alpha, no normal/displacement/parallax, source shadow casting off retained',
 'geometryScope':'No mesh, UV, index, normal, tangent, transform, phrase, collider or visibility change; assign one new material to exactly two existing renderers.',
 'previewSubstrate':{'file':'art/reference_street_20260910/metal-v4/source-inspection-meshes.json','sha256':sha(A/'metal-v4/source-inspection-meshes.json'),'family':'ShutterSteel','materialFolder':'art/reference_street_20260910/metal-v4/candidate-v1/ShutterSteel'},
 'sourceAccepted':False,'nativeAccepted':False}
(O/'installer-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
audit={'sourceGeometry':{'triangles':sum(t['triangles']for t in targets),'parts':2,'zeroThickness':True,'UV0EqualsWorldZYDiv4':True,'unchangedOriginalJSON':sha(source)==old['sourceSha256']},
 'coverageIntegration':coverage,'mapOpacityRetainedFractionAt045':float(np.mean(opacity>=.45*255)),
 'rawChannels':{k:{'min':maps[k].min((0,1)).tolist(),'max':maps[k].max((0,1)).tolist(),'mean':maps[k].mean((0,1)).tolist()}for k in maps},
 'packing':{'RGBBytesPreserved':True,'opacityRawRToAlphaExact':True,'metallicRGBZero':True,'rawRoughnessComplementToAlphaExact':True,'packedPNGMode':'RGBA','dimensions':[4096,4096]},
 'limitation':'Numeric and source-map inspection only. Alpha/mips and source/native readability need matched views.'}
(O/'channel-geometry-check.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'output':str(O),'coverage':coverage,'opacityFullMapRetained':audit['mapOpacityRetainedFractionAt045']}))
