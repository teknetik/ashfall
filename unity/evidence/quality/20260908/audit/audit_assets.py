#!/usr/bin/env python3
"""Reproducible read-only source/import audit. Does not open or mutate Unity.

Run from repository root: python unity/evidence/quality/20260908/audit/audit_assets.py
Requires numpy and Pillow. Input inventory is an explicitly dated saved-Editor export.
Geometry read from GLB/Unity text meshes/retained Blender export JSON is measured,
not rendered; visibility, source visual acceptance and active GPU mip remain unknown.
"""
from __future__ import annotations
import collections, hashlib, io, json, math, re, struct, faulthandler
from pathlib import Path
import numpy as np
from PIL import Image
faulthandler.enable()
faulthandler.dump_traceback_later(120, repeat=True)

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PROJECT = ROOT / 'unity/AthenHill'
INVENTORY = OUT / 'current-scene-audit.json'
SCENE = PROJECT / 'Assets/AthenHill/Scenes/AthenHill.unity'
DATA = json.loads(INVENTORY.read_text())
FBX_DATA = json.loads((OUT/'runtime-buffers-and-materials.json').read_text()) if (OUT/'runtime-buffers-and-materials.json').exists() else {'fbx':[]}
FBX = {(r['path'],r['name']):dict(r,indices=np.asarray(r['indices']).reshape(-1,3),tangents=r['tangents'] or None,normals=r['normals'] or None,uv=r['uv'] or None) for r in FBX_DATA['fbx']}
cache = {}

def relative(p): return str(p.relative_to(ROOT))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def summary(values):
    v=np.asarray(values); v=v[np.isfinite(v)]
    return dict(min=float(v.min()),p50=float(np.percentile(v,50)),p95=float(np.percentile(v,95)),max=float(v.max())) if len(v) else None

def glb(path):
    key=str(path)
    if key in cache:return cache[key]
    raw=path.read_bytes(); magic,version,length=struct.unpack_from('<4sII',raw)
    if magic!=b'glTF' or version!=2:raise ValueError('Not glTF 2')
    chunks={}; pos=12
    while pos<length:
        size,typ=struct.unpack_from('<II',raw,pos);chunks[typ]=raw[pos+8:pos+8+size];pos+=8+size
    doc=json.loads(chunks[0x4e4f534a]); blob=chunks.get(0x004e4942,b'')
    def accessor(index):
        a=doc['accessors'][index]
        if 'sparse' in a:raise ValueError('Sparse accessor requires separate decoder')
        b=doc['bufferViews'][a['bufferView']]
        if b.get('buffer',0)!=0:raise ValueError('External buffer unavailable')
        dtype=np.dtype({5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']])
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        vals=np.ndarray((a['count'],n),dtype=dtype,buffer=blob,offset=b.get('byteOffset',0)+a.get('byteOffset',0),strides=(b.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
        if a.get('normalized') and dtype.kind in 'iu':vals=np.maximum(vals.astype(float)/np.iinfo(dtype).max,-1)
        return vals
    meshes=[]
    for mi,m in enumerate(doc.get('meshes',[])):
        pos=[]; inds=[]; attrs=collections.defaultdict(list);offset=0; modes=[]
        for primitive in m['primitives']:
            pp=accessor(primitive['attributes']['POSITION']); pos.append(pp)
            ii=accessor(primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(pp))
            mode=primitive.get('mode',4);modes.append(mode)
            if mode==4: inds.append(ii.reshape(-1,3)+offset)
            elif mode==5: inds.append(np.asarray([(ii[i+1],ii[i],ii[i+2]) if i%2 else (ii[i],ii[i+1],ii[i+2]) for i in range(len(ii)-2)])+offset)
            elif mode==6: inds.append(np.asarray([(ii[0],ii[i+1],ii[i+2]) for i in range(len(ii)-2)])+offset)
            else: raise ValueError('Non-triangle source mode '+str(mode))
            for attr in ['NORMAL','TANGENT','TEXCOORD_0']:
                if attr in primitive['attributes']:attrs[attr].append(accessor(primitive['attributes'][attr]))
            offset+=len(pp)
        meshes.append(dict(name=m.get('name',str(mi)),positions=np.concatenate(pos),indices=np.concatenate(inds),
            normals=np.concatenate(attrs['NORMAL']) if len(attrs['NORMAL'])==len(pos) else None,
            tangents=np.concatenate(attrs['TANGENT']) if len(attrs['TANGENT'])==len(pos) else None,
            uv=np.concatenate(attrs['TEXCOORD_0']) if len(attrs['TEXCOORD_0'])==len(pos) else None,
            submeshes=len(pos),primitiveModes=modes))
    images=[]
    for im in doc.get('images',[]):
        try:
            if 'bufferView' in im:
                v=doc['bufferViews'][im['bufferView']];b=blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
            else:b=(path.parent/im['uri']).read_bytes()
            pic=Image.open(io.BytesIO(b));images.append(dict(name=im.get('name'),size=list(pic.size),sha256=hashlib.sha256(b).hexdigest()))
        except Exception as ex:images.append(dict(name=im.get('name'),error=str(ex)))
    value=dict(path=relative(path),sha256=hashlib.sha256(raw).hexdigest(),meshes=meshes,images=images,materials=doc.get('materials',[]))
    cache[key]=value;return value

def unity_mesh(path):
    text=path.read_text();start=text.index('  m_VertexData:');end=text.index('    _typelessdata:',start)
    header=text[start:end];count=int(re.search(r'm_VertexCount: (\d+)',header)[1])
    channels=[tuple(map(int,m)) for m in re.findall(r'- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)',header)]
    raw=bytes.fromhex(re.search(r'_typelessdata: ([0-9a-fA-F]+)',text[end:])[1])
    formats={0:('<f4',4),1:('<f2',2),2:('u1',1),3:('i1',1),4:('<u2',2),5:('<i2',2),6:('u1',1),7:('i1',1),8:('<u2',2),9:('<i2',2),10:('<u4',4),11:('<i4',4)}
    strides={}
    for stream,offset,fmt,dim in channels:
        if dim:strides[stream]=max(strides.get(stream,0),offset+formats[fmt][1]*dim)
    starts={};cursor=0
    for stream in sorted(strides):starts[stream]=cursor;cursor=(cursor+count*strides[stream]+15)//16*16
    def channel(index):
        if index>=len(channels) or not channels[index][3]:return None
        stream,offset,fmt,dim=channels[index];dtype,sz=formats[fmt]
        arr=np.ndarray((count,dim),dtype=dtype,buffer=raw,offset=starts[stream]+offset,strides=(strides[stream],sz)).copy()
        if fmt in [2,3,4,5]:arr=np.maximum(arr.astype(float)/np.iinfo(arr.dtype).max,-1)
        return arr
    indexformat=int(re.search(r'm_IndexFormat: (\d+)',text)[1]);ib=bytes.fromhex(re.search(r'm_IndexBuffer: ([0-9a-fA-F]+)',text)[1])
    dtype='<u4' if indexformat else '<u2';sz=np.dtype(dtype).itemsize
    sub=text[text.index('  m_SubMeshes:'):text.index('  m_Shapes:')]
    indices=[]
    for first,n,top,base in re.findall(r'firstByte: (\d+)\s+indexCount: (\d+)\s+topology: (\d+)\s+baseVertex: (\d+)',sub):
        if int(top)!=0:raise ValueError('Non triangle Unity topology')
        indices.append(np.frombuffer(ib,dtype=dtype,count=int(n),offset=int(first)).reshape(-1,3)+int(base))
    return dict(name=re.search(r'm_Name: (.*)',text)[1],positions=channel(0),normals=channel(1),tangents=channel(2),uv=channel(4),indices=np.concatenate(indices),submeshes=len(indices))

def metrics(g,scale=(1,1,1),uvscale=(1,1),pixels=None):
    p=np.asarray(g['positions'],dtype=float)*np.asarray(scale);ii=np.asarray(g['indices'],dtype=int).reshape(-1,3)
    pts=p[ii];e1=pts[:,1]-pts[:,0];e2=pts[:,2]-pts[:,0]
    ar=np.linalg.norm(np.cross(e1,e2),axis=1)*.5;valid=ar>1e-12
    out=dict(vertices=len(p),triangles=len(ii),surfaceArea=float(ar.sum()),zeroAreaTriangles=int((~valid).sum()),finitePositions=bool(np.isfinite(p).all()),boundsSize=(p.max(0)-p.min(0)).tolist())
    for label,key in [('normals','normals'),('tangents','tangents')]:
        v=g.get(key)
        if v is None:out[label]=None;continue
        v=np.asarray(v,dtype=float);length=np.linalg.norm(v[:,:3],axis=1)
        out[label]=dict(finite=bool(np.isfinite(v).all()),zeroLength=int((length<1e-7).sum()),nonUnit=int((abs(length-1)>.02).sum()),length=summary(length))
        if label=='tangents' and g.get('normals') is not None:
            nn=np.asarray(g['normals']);dot=abs(np.sum(nn[:,:3]*v[:,:3],axis=1));out[label]['nonOrthogonalToNormals']=int((dot>.02).sum());out[label]['invalidHandedness']=int((abs(abs(v[:,3])-1)>.01).sum())
    uv=g.get('uv')
    if uv is None:out['uv0']=None;return out
    uv=np.asarray(uv,dtype=float)*np.asarray(uvscale);uu=uv[ii];u1=uu[:,1]-uu[:,0];u2=uu[:,2]-uu[:,0]
    det=u1[:,0]*u2[:,1]-u1[:,1]*u2[:,0];uva=abs(det)*.5;ok=valid&(uva>1e-14)
    uvout=dict(finite=bool(np.isfinite(uv).all()),zeroAreaTriangles=int((uva<1e-14).sum()),geometricAreaWithZeroUV=float(ar[valid&~ok].sum()),summedUVArea=float(uva.sum()),range=[uv.min(0).tolist(),uv.max(0).tolist()])
    if ok.any():
        # Jacobian maps an orthonormal triangle plane to UV; singular-value ratio
        # describes anisotropic stretch independently of texel density.
        l=np.linalg.norm(e1[ok],axis=1);xp=(e1[ok]*e2[ok]).sum(1)/l;yp=2*ar[ok]/l
        J=np.empty((sum(ok),2,2));J[:,:,0]=u1[ok]/l[:,None];J[:,:,1]=(u2[ok]-u1[ok]*xp[:,None]/l[:,None])/yp[:,None]
        sv=np.linalg.svd(J,compute_uv=False);ratio=sv[:,0]/np.maximum(sv[:,1],1e-20)
        uvout['anisotropy']=summary(ratio);uvout['surfaceFractionAnisotropyOver4']=float(ar[ok][ratio>4].sum()/ar[valid].sum())
        if pixels:
            density=np.sqrt(uva[ok]*pixels[0]*pixels[1]/ar[ok]);uvout['texelsPerMetre']=summary(density)
            uvout['texelsPerMetreAreaAggregate']=float(np.sqrt(uva[ok].sum()*pixels[0]*pixels[1]/ar[ok].sum()))
    out['uv0']=uvout;return out

source_json={}
for path in [ROOT/'art/courtyard_20260908/mesh-data.json',ROOT/'art/phase1_20260908/finery-mesh-data.json',ROOT/'art/phase1_20260908/finery-lamp-mesh.json',ROOT/'art/phase1_20260908/tree-root-mesh.json']:
    d=json.loads(path.read_text());d=d if isinstance(d,list) else [d]
    source_json[relative(path)]={r['name']:dict(r,indices=np.asarray(r['indices']).reshape(-1,3)) for r in d}

def original_for(m):
    p=m['path'];name=m['name'];path=None
    if '/Courtyard/Meshes/' in p:path='art/courtyard_20260908/mesh-data.json'
    elif '/Phase1/Finery/Meshes/' in p:
        for path in ['art/phase1_20260908/finery-mesh-data.json','art/phase1_20260908/finery-lamp-mesh.json']:
            if name in source_json[path]:return source_json[path][name],path,'original Blender evaluated export'
            match=next((r for n,r in source_json[path].items() if re.sub(r'[^a-zA-Z0-9_-]','_',n)==name),None)
            if match is not None:return match,path,'original Blender evaluated export; importer-sanitized mesh name'
        return None,None,'unavailable source name'
    elif '/Phase1/Tree/' in p:path='art/phase1_20260908/tree-root-mesh.json'
    if path:
        rows=source_json[path];r=rows.get(name) or (next(iter(rows.values())) if len(rows)==1 else None)
        return r,path,'original Blender evaluated export'
    if '/Salvage/' in p:
        kind=Path(p).stem;path=f'meshy/salvage-20260908/{kind}/{kind}.glb'
    elif '/District/' in p:
        kind=Path(p).stem
        if kind=='rigged':path='meshy/district-20260908/mechanic/rigged.glb'
        else:path=f'meshy/district-20260908/{kind}/{kind}.glb'
    elif '/RingGate/' in p:path='meshy/ring-gate-v1/model/ring-gate.glb'
    elif '/MissionTerminal/' in p:path='meshy/mission-terminal-v1/model/mission-terminal.glb'
    elif 'ward-guard.glb' in p or '/VexSurface/' in p:path='meshy/ward-guard/model/character-rigged.glb'
    elif p.endswith('/colonist.glb'):path='meshy/mpc/Meshy_AI_Character_output.glb'
    elif p.endswith('.glb'):path='unity/AthenHill/'+p
    elif '/Traveler/' in p:return None,'meshy/Meshy_AI_weathered_traveler_ri_biped/Meshy_AI_weathered_traveler_ri_biped_Animation_Walking_withSkin.fbx','FBX requires live importer/source comparison'
    if path and (ROOT/path).is_file():
        d=glb(ROOT/path);rows=d['meshes'];r=next((r for r in rows if r['name']==name),None)
        if r is None and len(rows)==1:r=rows[0]
        return r,path,'retained glTF source export' if path.startswith('meshy/') else 'retained imported GLB (earlier authoring source not independently compared)'
    return None,None,'no independent retained geometry decoded'

byid={m['id']:m for m in DATA['meshes']};mats={m['id']:m for m in DATA['materials']}
instances=collections.defaultdict(list)
for i in DATA['instances']:instances[i['meshId']].append(i)
ledger=[];failures=[];comparisons=[];source_records={}
for m in DATA['meshes']:
    if len(ledger)%100==0:print('Measuring runtime mesh',len(ledger),m['path'],flush=True)
    rows=instances[m['id']];active=[i for i in rows if i['active'] and i['sourceVisible'] and not i['generated']]
    generated=any(i['generated'] for i in rows)
    row=dict(mesh=m,classification='derived render chunk' if generated else 'active source' if active else 'inactive/hidden source',activeInstanceCount=len(active),instances=rows,
        materialIds=sorted(set(mid for i in rows for mid in i['materials'])),lod='No LODGroup in dated saved inventory; same mesh at every authored viewing distance',visualReview='unreviewed individually; family evidence is partial',decision='review pending')
    src,srcpath,basis=original_for(m) if not generated else (None,None,'derived chunk has no separate authoring source')
    row['sourcePath']=srcpath;row['sourceComparisonBasis']=basis
    geom=None;geom_basis=None
    if (m['path'],m['name']) in FBX:
        geom=FBX[(m['path'],m['name'])];geom_basis='Unity Editor imported runtime mesh buffer (read-only export)'
    elif m['path'].endswith('.asset') and (PROJECT/m['path']).exists():
        try:geom=unity_mesh(PROJECT/m['path']);geom_basis='current serialized Unity mesh asset'
        except Exception as ex:failures.append(dict(mesh=m['path'],stage='Unity decode',error=str(ex)))
    elif m['path'].endswith('.glb'):
        try:
            gs=glb(PROJECT/m['path'])['meshes'];geom=next((g for g in gs if g['name']==m['name']),None)
            if geom is None and len(gs)==1:geom=gs[0]
            geom_basis='imported GLB buffer; counts cross-checked with Editor export'
        except Exception as ex:failures.append(dict(mesh=m['path'],stage='GLB decode',error=str(ex)))
    if src is not None:
        source_metrics=metrics(src);row['sourceMetrics']=source_metrics
        nt=source_metrics['triangles'];nv=source_metrics['vertices']
        row['comparison']=dict(sourceTriangles=nt,runtimeTriangles=m['triangles'],triangleReductionPercent=100*(nt-m['triangles'])/nt if nt else None,sourceVertices=nv,runtimeVertices=m['vertices'],vertexChange=m['vertices']-nv,vertexComparisonNote='FBX import may split vertex attributes; changed vertex count alone does not prove silhouette loss')
        if srcpath.startswith('meshy/'):comparisons.append(dict(runtimePath=m['path'],runtimeName=m['name'],activeInstanceCount=len(active),sourcePath=srcpath,**row['comparison']))
    if geom is not None:
        row['geometryMetrics']=metrics(geom);row['geometryMetricsBasis']=geom_basis
        row['countMatchesSavedInventory']=len(geom['positions'])==m['vertices'] and len(geom['indices'])==m['triangles']
    elif src is not None:
        geom=src;geom_basis='source-space estimate; FBX runtime vertex buffer not inspected'
    if geom is not None and active:
        density=[]
        for i in active:
            material=mats.get(i['materials'][0]) if len(i['materials'])==1 else None
            tx=next((t for t in material['textures'] if t['property'] in ['_BaseMap','baseColorTexture'] and t['width']>0),None) if material else None
            if tx:
                scale=i['scale']
                # Meshy FBX convention in this project is centimetre-scaled source;
                # derive diagonal size ratio from Unity local mesh bounds to glTF.
                if geom_basis.startswith('source-space'):
                    ss=np.asarray(row['sourceMetrics']['boundsSize']);rt=np.asarray(m['size']);factor=np.divide(rt,ss,out=np.ones(3),where=ss>1e-10);scale=np.asarray(scale)*factor
                mm=metrics(geom,scale,tx['scale'],[tx['width'],tx['height']])
                density.append(dict(instance=i['path'],material=material['path'],texture=tx['path'],basis=geom_basis,uv=mm['uv0'],worldSurfaceArea=mm['surfaceArea']))
        row['instanceTexelDensity']=density
    ledger.append(row)

for p in sorted((ROOT/'meshy').rglob('*.glb')):
    print('Measuring retained source',relative(p),flush=True)
    try:
        d=glb(p);source_records[relative(p)]={k:v for k,v in d.items() if k!='meshes'}
        source_records[relative(p)]['meshes']=[dict(name=g['name'],submeshes=g['submeshes'],**metrics(g)) for g in d['meshes']]
    except Exception as ex:failures.append(dict(source=relative(p),stage='source GLB decode',error=str(ex)))

textures=[]
for m in DATA['materials']:
    for t in m['textures']:
        if not t['path'] or not t['width']:continue
        rr=dict(material=m['path'],shader=m['shader'],property=t['property'],texturePath=t['path'],importedDimensions=[t['width'],t['height']],uvScale=t['scale'],activeMip='unavailable; requires player texture instrumentation')
        p=PROJECT/t['path']
        if p.suffix.lower() in ['.png','.jpg','.jpeg','.tga','.exr'] and p.exists():
            try:pic=Image.open(p);rr['sourceFileDimensions']=list(pic.size);rr['dimensionRetention']=[t['width']/pic.width,t['height']/pic.height];rr['sha256']=sha(p)
            except Exception as ex:rr['sourceImageReadError']=str(ex)
            meta=Path(str(p)+'.meta')
            if meta.exists():
                s=meta.read_text();rr['importerSettings']={k:re.findall(r'^\s*'+k+r': (.*)$',s,re.M) for k in ['sRGBTexture','convertToNormalMap','textureType','maxTextureSize','textureCompression','streamingMipmaps','mipMapBias','aniso','mipmaps','enableMipMap','npotScale']}
        elif p.suffix=='.glb' and p.exists():
            gg=glb(p);candidates=[im for im in gg['images'] if im.get('name')==t['name']]
            rr['sourceEmbeddedImageCandidates']=candidates if candidates else gg['images'];rr['sourceImageResolutionMatchByName']=bool(candidates)
        textures.append(rr)

active=[r for r in ledger if r['classification']=='active source'];chunks=[r for r in ledger if r['classification']=='derived render chunk']
groups=collections.defaultdict(lambda:dict(uniqueMeshes=0,instances=0,triangles=0,vertices=0,missingTangents=0))
for r in active:
    p=r['mesh']['path'];i=r['instances'][0]['path'];family=p.split('/Meshes/')[0] if '/Meshes/' in p else p
    if '/Courtyard/' in p:family='Courtyard/'+i.split('/')[1]
    g=groups[family];g['uniqueMeshes']+=1;g['instances']+=r['activeInstanceCount'];g['triangles']+=r['mesh']['triangles']*r['activeInstanceCount'];g['vertices']+=r['mesh']['vertices']*r['activeInstanceCount'];g['missingTangents']+=not r['mesh']['tangents']
totals=dict(inputInventory=relative(INVENTORY),inputSha256=sha(INVENTORY),inventoryCapturedUtc=DATA['capturedUtc'],sourceFingerprint=DATA['fingerprint'],currentSavedSceneSha256=sha(SCENE),
    allMeshRecords=len(ledger),activeUniqueMeshes=len(active),activeInstances=sum(r['activeInstanceCount'] for r in active),activeSourceTriangles=sum(r['mesh']['triangles']*r['activeInstanceCount'] for r in active),
    activeSourceVertices=sum(r['mesh']['vertices']*r['activeInstanceCount'] for r in active),generatedChunkMeshes=len(chunks),generatedChunkTriangles=sum(r['mesh']['triangles'] for r in chunks),
    independentOrRetainedSourceCompared=sum('sourceMetrics' in r for r in active),currentAssetOrImportedBufferInspected=sum('geometryMetrics' in r for r in active),
    activeMeshesMissingTangents=sum(not r['mesh']['tangents'] for r in active),activeMeshesMissingNormals=sum(not r['mesh']['normals'] for r in active),activeMeshesMissingUV0=sum(not r['mesh']['uv0'] for r in active),
    lodGroups=DATA['lods'],actorCount=len(DATA['actors']),materials=len(DATA['materials']),coverageLimit='Accounting is exhaustive for the dated inventory. Visual reviews are incomplete; this script does not determine visibility, active mip, shader correctness or acceptance.')
dump('unique-assets.json',ledger);dump('source-exports.json',list(source_records.values()));dump('meshy-comparisons.json',comparisons);dump('texture-imports.json',textures);dump('family-costs.json',dict(sorted(groups.items(),key=lambda kv:-kv[1]['triangles'])));dump('decode-failures.json',failures);dump('summary.json',totals)
print(json.dumps(totals,indent=2));print('Decode failures:',len(failures))
