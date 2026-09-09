"""Read saved Unity text; write camera requests without mutating Unity or the scene."""
from pathlib import Path
import hashlib,json,math,re
ROOT=Path(__file__).resolve().parents[5];out=Path(__file__).resolve().parent
scene=ROOT/'unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity';data=scene.read_bytes();blocks=re.split(r'(?=--- !u!)',data.decode());gos={};trans={};components=[]
def vec(s):return [float(x)for x in re.findall(r'[xyzw]: ([\d.eE+-]+)',s)]
for b in blocks:
 h=re.match(r'--- !u!(\d+) &(-?\d+)',b)
 if not h:continue
 if h[1]=='1':
  n=re.search(r'^  m_Name: (.*)$',b,re.M)
  if n:gos[h[2]]=n[1]
 if h[1]=='4':
  go=re.search(r'm_GameObject: \{fileID: (-?\d+)',b);p=re.search(r'm_LocalPosition: (.*)',b);q=re.search(r'm_LocalRotation: (.*)',b);f=re.search(r'm_Father: \{fileID: (-?\d+)',b)
  if go and p:trans[h[2]]={'go':go[1],'position':vec(p[1]),'rotation':vec(q[1]),'parent':f[1]if f else '0'}
 if h[1]=='114':components.append(b)
def rotate(q,v):
 x,y,z,w=q;vx,vy,vz=v;tx=2*(y*vz-z*vy);ty=2*(z*vx-x*vz);tz=2*(x*vy-y*vx);return [vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx]
def add(a,b):return [x+y for x,y in zip(a,b)]
def mul(a,k):return [x*k for x in a]
def norm(a):return mul(a,1/math.sqrt(sum(x*x for x in a)))
byname={gos.get(t['go']):t for t in trans.values()}
# Relevant roots/routes in the saved city have identity parents; refuse an implicit bad transform conversion.
for name in ['npc_vex','npc_torr','npc_linn','npc_mira']:
 parent=trans[byname[name]['parent']];assert parent['position']==[0,0,0] and parent['rotation']==[0,0,0,1],name
cameras=[]
def camera(name,position,target,fov=50):cameras.append({'name':name,'position':position,'target':target,'fov':fov})
# Direction is fixed on world axes for deterministic real-input movement under fixed cameras.
camera('cam_motion_jump_front',[32.5,2.2,.9],[41,1.45,.9],36)
camera('cam_motion_jump_side',[39.4,2.05,7],[39.4,1.5,0],50)
camera('cam_motion_jump_rear',[48.5,2.2,.9],[40,1.45,.9],40)
camera('cam_motion_stand_front',[37.2,1.85,.6],[43,1.6,.6],40)
camera('cam_motion_stand_side',[43,1.85,5.5],[43,1.6,0],40)
camera('cam_motion_stand_rear',[48.5,1.85,.6],[43,1.6,.6],40)
camera('cam_motion_edge_front',[12.8,3.2,10.2],[6.7,2,2.7],48)
camera('cam_motion_edge_side',[11,3.2,-3.5],[6.5,2,1],52)
guards=[]
for name,landmark in [('npc_vex','west_gate'),('npc_torr','mission_slab'),('npc_linn','oa_hill'),('npc_mira','basic_general')]:
 t=byname[name];p=t['position'];f=rotate(t['rotation'],[0,0,1]);right=rotate(t['rotation'],[1,0,0]);full=add(add(add(p,mul(f,3.5)),mul(right,1.3)),[0,1.3,0]);close=add(add(add(p,mul(f,1.8)),mul(right,.52)),[0,1.52,0])
 camera('cam_motion_'+name+'_full',full,add(add(p,[0,.96,0]),mul(right,.85)),43);camera('cam_motion_'+name+'_close',close,add(add(p,[0,1.4,0]),mul(right,.25)),42)
 guards.append({'actor':name,'landmark':landmark,'position':p,'fullCamera':'cam_motion_'+name+'_full','closeCamera':'cam_motion_'+name+'_close','idleSeconds':4,'talkSeconds':155/30,'minimumCompleteLoops':3})
walkers=[]
for b in components:
 if '  waypoints:'not in b:continue
 go=re.search(r'm_GameObject: \{fileID: (-?\d+)',b)[1];name=gos.get(go,'npc_yard_mechanic' if go=='1095515360' else None);assert name,go;refs=re.findall(r'\{fileID: (-?\d+)\}',b.split('  waypoints:')[1].split('  speed:')[0]);points=[trans[r]['position']for r in refs];speed=float(re.search(r'^  speed: (.+)',b,re.M)[1]);phase=float(re.search(r'^  phase: (.+)',b,re.M)[1]);corners=[]
 for i,p in enumerate(points):
  prev=points[(i-1)%len(points)];nxt=points[(i+1)%len(points)];incoming=norm(add(prev,mul(p,-1)));outgoing=norm(add(nxt,mul(p,-1)));bisect=norm(add(incoming,outgoing));position=add(add(p,mul(bisect,4.5)),[0,1.55,0]);cam='cam_motion_'+name+'_corner_'+str(i);camera(cam,position,add(p,[0,.9,0]),48);corners.append({'index':i,'camera':cam,'position':p,'previous':prev,'next':nxt})
 length=sum(math.dist(points[i],points[(i+1)%len(points)])for i in range(len(points)))
 walkers.append({'actor':name,'points':points,'speed':speed,'phase':phase,'routeLength':length,'routeSeconds':length/speed,'corners':corners})
plan={'status':'Prepared requests only; cameras and clips not yet captured','sourceScene':str(scene.relative_to(ROOT)),'sourceSceneSha256':hashlib.sha256(data).hexdigest(),'resolution':[1920,1080],'captureFps':60,'minimumGuardLoops':3,'cameras':cameras,'guards':guards,'walkers':walkers,'landmarks':[{'name':'qa_motion_wall','position':[44.5,0,-7.4]},{'name':'qa_motion_door','position':[15.4,.5,-18]}],'jumpInputs':{'front':['s'],'side':['d'],'rear':['w']},'reviewRequirements':['No visual acceptance from automated pass','Verify every video exists and ffprobe duration is adequate','Review normal speed before slow motion','Record per-shot exact defect timestamps','Preserve original failed clips and rerun only affected scenarios']}
(out/'capture-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'cameras':len(cameras),'guards':len(guards),'walkerCorners':sum(len(w['corners'])for w in walkers),'output':str(out/'capture-plan.json')},indent=2))
