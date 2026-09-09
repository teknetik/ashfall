"""Extract/ground the licensed Meshy animation; preserve original mesh/texture bytes separately.
This is channel/data processing, not character reauthoring. Re-run from repo root.
"""
import copy, hashlib, json, struct, sys
from pathlib import Path
import numpy as np
root=Path('unity/evidence/quality/20260908/movement')
idle='--idle' in sys.argv
kind='idle' if idle else 'chat'
clipName='idle' if idle else 'talk'
p=root/('source/guard-idle.glb' if idle else 'source/guard-stand-and-chat.glb')
b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+n]);raw=b[28+n:]
dtypes={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}
components={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}
def read(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']]
 return np.frombuffer(raw,dtype=dtypes[a['componentType']],count=a['count']*components[a['type']],offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],-1).copy()
def matrix(t,r,s):
 x,y,z,w=r;q=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]);m=np.eye(4);m[:3,:3]=q*np.array(s);m[:3,3]=t;return m
parents={c:i for i,n in enumerate(g['nodes'])for c in n.get('children',[])}
anim=g['animations'][0];channels=[(c,read(anim['samplers'][c['sampler']]['input']),read(anim['samplers'][c['sampler']]['output']))for c in anim['channels']]
pr=g['meshes'][0]['primitives'][0];pos=read(pr['attributes']['POSITION']);ids=read(pr['attributes']['JOINTS_0']);weights=read(pr['attributes']['WEIGHTS_0']);skin=g['skins'][0];bind=read(skin['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);p4=np.column_stack([pos,np.ones(len(pos))]);rows=[]
frameCount=max(len(ts) for c,ts,v in channels)
for frame in range(frameCount):
 t=(frame+1)/30;trs=[[n.get('translation',[0,0,0]),n.get('rotation',[0,0,0,1]),n.get('scale',[1,1,1])]for n in g['nodes']]
 for c,times,values in channels:
  j=min(int(np.searchsorted(times[:,0],t)),len(values)-1)
  value=values[j] if len(values)>2 else values[0]
  trs[c['target']['node']][{'translation':0,'rotation':1,'scale':2}[c['target']['path']]]=value
 worlds={}
 def mat(i):
  if i not in worlds:worlds[i]=(mat(parents[i])if i in parents else np.eye(4))@matrix(*trs[i])
  return worlds[i]
 bm=np.stack([mat(i)for i in skin['joints']])@bind
 posed=np.zeros_like(p4)
 for j in range(4):posed+=np.einsum('nij,nj->ni',bm[ids[:,j]],p4)*weights[:,j,None]
 rows.append({'frame':frame,'skinLow':float(posed[:,1].min()),'skinHigh':float(posed[:,1].max()),'leftFoot':mat(1)[:3,3].tolist(),'rightFoot':mat(5)[:3,3].tolist()})
lowest=min(r['skinLow']for r in rows)
hipchannel=next((c,ts,v)for c,ts,v in channels if g['nodes'][c['target']['node']]['name']=='Hips'and c['target']['path']=='translation')
hipFirst=hipchannel[2][0]
# Match the existing guard's authored X/Z anchor. Skin's 8 cm source hover is removed.
shift=np.array([hipFirst[0]-.011360078118741512,lowest*100,hipFirst[2]-.8771359920501709],dtype='<f4')
out={key:copy.deepcopy(g[key])for key in ['asset','scene','scenes','nodes','animations']}
out['animations'][0]['name']=clipName;out['asset']['generator']='Ward movement pass: animation-only Meshy extraction; constant hips grounding/anchor correction; original retained.'
for node in out['nodes']:
 for key in ['mesh','skin','weights']:node.pop(key,None)
out['accessors']=[];out['bufferViews']=[];binary=bytearray();remap={}
for c in out['animations'][0]['channels']:
 s=out['animations'][0]['samplers'][c['sampler']]
 for key in ['input','output']:
  old=s[key]
  if old in remap:s[key]=remap[old];continue
  a=copy.deepcopy(g['accessors'][old]);v=read(old)
  if key=='output'and c['target']['node']==23 and c['target']['path']=='translation':v-=shift
  if key=='input':v-=1/30 # Start at zero rather than retaining one-frame leading hold.
  while len(binary)%4:binary.append(0)
  offset=len(binary);data=v.tobytes();binary.extend(data)
  a['bufferView']=len(out['bufferViews']);a.pop('byteOffset',None)
  if 'min'in a:a['min']=v.min(axis=0).tolist()
  if 'max'in a:a['max']=v.max(axis=0).tolist()
  out['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
  remap[old]=len(out['accessors']);s[key]=len(out['accessors']);out['accessors'].append(a)
while len(binary)%4:binary.append(0)
out['buffers']=[{'byteLength':len(binary)}]
j=json.dumps(out,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
result=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary
output=Path('unity/AthenHill/Assets/AthenHill/Art/CharacterMotion/Source/'+('GuardIdleSource.glb' if idle else 'GuardChatSource.glb'));output.write_bytes(result)
manifest={'taskId':'01a082ab-7fe4-7301-b5c9-4cff610300dc' if idle else '01a082a4-2bc8-7549-8e49-5a8fdd1fc1f4','rigTaskId':'01a07c81-2534-7259-af07-0a4df613e278','actionId':0 if idle else 56,'actionName':'Idle' if idle else 'Stand_and_Chat','status':'SUCCEEDED','creditsConsumed':3,'postProcess':{'operation_type':'change_fps','fps':30},'source':str(p),'sourceSha256':hashlib.sha256(b).hexdigest(),'derived':str(output),'derivedSha256':hashlib.sha256(result).hexdigest(),'sourceFrames':frameCount,'durationSeconds':(frameCount-1)/30,'channels':72,'rebaseHipsCentimetres':shift.tolist(),'sourceMinimumSkinY':lowest,'groundedMaximumSkinY':max(r['skinLow']for r in rows)-lowest,'preserved':['all skeletal keyframes','existing guard model/material/skin weights','full source file'],'sourceDocumentation':'https://docs.meshy.ai/en/api/animation-library','statusOfVisualAcceptance':'Awaiting Unity/native review; source/data inspection is not visual acceptance.'}
(root/('meshy-'+kind+'-task.json')).write_text(json.dumps(manifest,indent=2)+'\n');(root/('meshy-'+kind+'-source-samples.json')).write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(manifest,indent=2))
