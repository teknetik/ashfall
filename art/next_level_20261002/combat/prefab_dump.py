#!/usr/bin/env python3
"""Dump a Unity prefab/scene YAML hierarchy: GameObjects, their parents, active flags and MonoBehaviour script guids."""
import re,sys
path=sys.argv[1];filt=sys.argv[2] if len(sys.argv)>2 else None
txt=open(path).read()
docs=re.split(r'^--- !u!',txt,flags=re.M)[1:]
tr={};names={};comps={};father={}
def g(p,d):
    r=re.search(p,d);return r.group(1) if r else None
for d in docs:
    m=re.match(r'(\d+) &(\d+)',d);cls,fid=m.group(1),m.group(2)
    if cls=='1':names[fid]=(g(r'm_Name: (.*)',d),g(r'm_IsActive: (\d)',d))
    elif cls=='4':
        go=g(r'm_GameObject: \{fileID: (\d+)\}',d);tr[fid]=go
        if go:father[go]=g(r'm_Father: \{fileID: (\d+)\}',d)
    elif cls=='114':
        go=g(r'm_GameObject: \{fileID: (\d+)\}',d)
        if go:comps.setdefault(go,[]).append(g(r'guid: (\w{8})',d)+(' '+g(r'\n  displayName: (.*)',d) if g(r'\n  displayName: (.*)',d) else ''))
    elif cls in('33','23','137','65','136','54','95','111','108','82','120','198'):
        go=g(r'm_GameObject: \{fileID: (\d+)\}',d)
        if go:comps.setdefault(go,[]).append({'33':'MeshFilter','23':'MeshRenderer','137':'Skinned','65':'Box','136':'Capsule','54':'Rigidbody','95':'Animator','111':'Animation','108':'Light','82':'AudioSource','120':'LineRenderer','198':'Particles'}[cls])
def parentName(go):
    f=father.get(go);
    if not f or f=='0':return 'ROOT'
    pg=tr.get(f);return (names.get(pg,('?',))[0] if pg else 'stripped:'+f)
for fid,(n,a) in names.items():
    line=f"{fid} {n} [{'on' if a=='1' else 'OFF'}] parent={parentName(fid)} {comps.get(fid,[])}"
    if not filt or filt.lower() in line.lower():print(line)
