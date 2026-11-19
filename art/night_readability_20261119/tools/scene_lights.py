"""Read-only survey of the saved scene YAML: lights (type, intensity, range, layer mask) by GameObject name."""
import re,sys
p=sys.argv[1] if len(sys.argv)>1 else 'unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity'
t=open(p).read()
docs=re.split(r'^--- !u!(\d+) &(\d+)(?: stripped)?\n',t,flags=re.M)
objs={}
for i in range(1,len(docs),3):
    objs[docs[i+1]]=(docs[i],docs[i+2])
def name(go):
    d=objs.get(go)
    if not d: return '?'
    m=re.search(r'm_Name: (.*)',d[1]); return m.group(1) if m else '?'
for fid,(cls,body) in objs.items():
    if cls!='108': continue
    go=re.search(r'm_GameObject: \{fileID: (\d+)',body).group(1)
    g=lambda k: (re.search(r'\n  '+k+r': ([^\n]*)',body) or [None,'-'])[1]
    print(f"{name(go)[:48]:48} type={g('m_Type')} I={g('m_Intensity')} R={g('m_Range')} RL={g('m_RenderingLayerMask')} sh={g('m_Shadows')[:30] if False else ''} cull={re.search(r'm_CullingMask:\s*serializedVersion: 2\s*m_Bits: (\d+)',body).group(1) if re.search(r'm_CullingMask:\s*serializedVersion: 2\s*m_Bits: (\d+)',body) else '-'}")
