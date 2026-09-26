"""Read-only binary FBX UV inspection; no Blender/Unity application operations.
Checks raw triangle order against the live exported spatial audit before using
UV corners for semantic panel masks. Writes additive numeric diagnostics only.
"""
from pathlib import Path
import hashlib,json,struct,zlib,numpy as np
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source';F=R/'meshy/ground-detail-20260910/generator-v2/model.fbx'
expected='a20285618ba776f5e87268e446bee03a6d1a3a51e521497ec61527460e3881d0'
buf=F.read_bytes();assert hashlib.sha256(buf).hexdigest()==expected
assert buf[:23]==b'Kaydara FBX Binary  \x00\x1a\x00';version=struct.unpack_from('<I',buf,23)[0];assert version==7400

def prop(p):
 typ=chr(buf[p]);p+=1
 dt={'Y':('<h',2),'C':('<?',1),'I':('<i',4),'F':('<f',4),'D':('<d',8),'L':('<q',8)}
 if typ in dt:
  fmt,size=dt[typ];return struct.unpack_from(fmt,buf,p)[0],p+size
 if typ in 'ilfdb':
  count,encoding,n=struct.unpack_from('<III',buf,p);p+=12;raw=buf[p:p+n];p+=n
  if encoding:assert encoding==1;raw=zlib.decompress(raw)
  value=np.frombuffer(raw,dtype={'i':'<i4','l':'<i8','f':'<f4','d':'<f8','b':'u1'}[typ]);assert len(value)==count;return value,p
 if typ in 'SR':
  n=struct.unpack_from('<I',buf,p)[0];p+=4;raw=buf[p:p+n];return raw,p+n
 raise ValueError(typ)
def node(p):
 end,count,plen=struct.unpack_from('<III',buf,p);n=buf[p+12];p+=13
 if end==0:return None,p
 name=buf[p:p+n].decode();p+=n;props=[]
 for _ in range(count):v,p=prop(p);props.append(v)
 children=[]
 while p<end:
  c,p=node(p)
  if c is None:break
  children.append(c)
 assert p==end,(name,p,end)
 return {'name':name,'props':props,'children':children},end
roots=[];p=27
while p<len(buf):
 n,p=node(p)
 if n is None:break
 roots.append(n)
def allnodes(ns):
 for n in ns:
  yield n;yield from allnodes(n['children'])
geos=[n for n in allnodes(roots) if n['name']=='Geometry'];assert len(geos)==1
g=geos[0];children={n['name']:n for n in g['children']};poly=children['PolygonVertexIndex']['props'][0];ends=poly<0;assert np.array_equal(np.flatnonzero(ends),np.arange(2,len(poly),3));tri=poly.copy();tri[ends]=-tri[ends]-1;tri=tri.reshape(-1,3)
live=np.load(O/'grille-spatial-audit/source-positions-triangles.npz');assert np.array_equal(tri,live['triangles']),'UV corner correspondence must be audited before semantic masks'
layers=[n for n in g['children'] if n['name']=='LayerElementUV'];assert len(layers)==1;u={n['name']:n['props']for n in layers[0]['children']};assert u['MappingInformationType'][0]==b'ByPolygonVertex';assert u['ReferenceInformationType'][0]==b'IndexToDirect'
uv=u['UV'][0].reshape(-1,2);indices=u['UVIndex'][0];assert len(indices)==tri.size;corners=uv[indices].reshape(-1,3,2)
D=O/'grille-spatial-audit';path=D/'source-uv-corners.npz';assert not path.exists();np.savez_compressed(path,uv=corners.astype(np.float32))
record={'method':'Read-only raw binary FBX UV extraction','fbxVersion':version,'fbxSha256':expected,'rawTriangleOrderEqualsLiveAudit':True,'triangles':len(tri),'uvVertices':len(uv),'uvCorners':len(indices),'uvRange':[uv.min(0).tolist(),uv.max(0).tolist()],'uvMapping':'ByPolygonVertex IndexToDirect','output':str(path),'sourceChanged':False};(D/'uv-extraction-contract.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
