"""Read-only comparison of retained and candidate GLB skeletons/animation; no Blender or Unity state."""
import json,struct,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
def load(path):
 b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);blob=b[28+n:]
 def acc(i):
  a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];types={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'};w={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
  return np.frombuffer(blob,dtype=types[a['componentType']],count=a['count']*w,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,w).copy()
 return j,acc
def rot(q):
 x,y,z,w=np.asarray(q)/np.linalg.norm(q)
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def inspect(path):
 j,acc=load(path);nodes=j['nodes'];index={n['name']:i for i,n in enumerate(nodes)};parent={c:i for i,n in enumerate(nodes) for c in n.get('children',[])};out={}
 for a in j['animations']:
  tracks=[(ch['target']['node'],ch['target']['path'],acc(a['samplers'][ch['sampler']]['input']).ravel(),acc(a['samplers'][ch['sampler']]['output'])) for ch in a['channels']]
  end=max(t[-1] for _,_,t,_ in tracks);frames=[]
  for time in np.linspace(0,end,65):
   values={}
   for node,path,t,v in tracks:
    k=min(len(t)-2,max(0,np.searchsorted(t,time)-1));u=float(np.clip((time-t[k])/max(t[k+1]-t[k],1e-8),0,1))
    v0=v[k];v1=v[k+1];v1=-v1 if path=='rotation' and np.dot(v0,v1)<0 else v1;values[node,path]=v0*(1-u)+v1*u
   world={}
   def matrix(i):
    if i in world:return world[i]
    n=nodes[i];m=np.eye(4);m[:3,:3]=rot(values.get((i,'rotation'),n.get('rotation',[0,0,0,1])))@np.diag(values.get((i,'scale'),n.get('scale',[1,1,1])));m[:3,3]=values.get((i,'translation'),n.get('translation',[0,0,0]));world[i]=(matrix(parent[i])@m) if i in parent else m;return world[i]
   chest=matrix(index['Spine']);hips=matrix(index['Hips'])[:3,3];row={'time':float(time),'hips':hips.tolist()}
   for side in ['Left','Right']:
    shoulder=matrix(index[side+'Shoulder'])[:3,3];upper=matrix(index[side+'Arm'])[:3,3];d=chest[:3,:3].T@(upper-shoulder);d/=np.linalg.norm(d);row[side]=d.tolist()
   frames.append(row)
  out[a['name']]={'duration':float(end),'frames':frames}
 return out
before=inspect(ROOT/'rollback/colonist.glb');after=inspect(ROOT/'colonist_polish.glb');result={}
for tag,clips in [('before',before),('after',after)]:
 ref=clips['idle']['frames'][0];rows={}
 for name,c in clips.items():
  rows[name]={}
  for side in ['Left','Right']:
   rows[name][side+'ShoulderMaxDegreesFromIdle']=max(math.degrees(math.acos(float(np.clip(np.dot(ref[side],f[side]),-1,1)))) for f in c['frames'])
  rows[name]['hipVerticalRangeMetres']=float(np.ptp([f['hips'][1] for f in c['frames']]))
 result[tag]=rows
# Preserve node names, hierarchy and rest transforms exactly within floating-point tolerance.
j0,a0=load(ROOT/'rollback/colonist.glb');j1,a1=load(ROOT/'colonist_polish.glb')
assert [n['name'] for n in j0['nodes']]==[n['name'] for n in j1['nodes']]
for old,new in zip(j0['nodes'],j1['nodes']):
 for k in ['translation','rotation','scale']:
  if k in old or k in new: assert np.allclose(old.get(k),new.get(k),atol=1e-6),(old['name'],k)
assert np.allclose(a0(j0['skins'][0]['inverseBindMatrices']),a1(j1['skins'][0]['inverseBindMatrices']),atol=1e-6)
result['unchanged_rest_nodes_and_bind_matrices']=True
(ROOT/'motion-comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
