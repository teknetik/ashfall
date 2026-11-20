"""Diff two Unity scene files by YAML document (fileID): lists added, removed and changed documents with the GameObject
they belong to. Usage: python3 scene_diff.py before.unity after.unity"""
import re,sys
def docs(p):
    out={};cur=None;buf=[]
    for line in open(p,encoding='utf-8'):
        m=re.match(r'--- !u!(\d+) &(-?\d+)',line)
        if m:
            if cur:out[cur]=''.join(buf)
            cur=(m.group(2));buf=[line]
        elif cur:buf.append(line)
    if cur:out[cur]=''.join(buf)
    return out
a,b=docs(sys.argv[1]),docs(sys.argv[2])
names={}
for d in (a,b):
    for k,v in d.items():
        m=re.search(r'm_Name: (.*)',v)
        if v.split('\n',2)[1].startswith('GameObject:') and m:names[k]=m.group(1)
def owner(v):
    m=re.search(r'm_GameObject: \{fileID: (-?\d+)\}',v);return names.get(m.group(1),'?') if m else names.get(None,'')
def kind(v):return v.split('\n',2)[1].rstrip(':')
added=[k for k in b if k not in a];removed=[k for k in a if k not in b];changed=[k for k in a if k in b and a[k]!=b[k]]
print(f'documents: before {len(a)} after {len(b)}; added {len(added)} removed {len(removed)} changed {len(changed)}')
for title,keys,src in (('ADDED',added,b),('REMOVED',removed,a),('CHANGED',changed,b)):
    from collections import Counter
    c=Counter((kind(src[k]),names.get(k) if kind(src[k])=='GameObject' else owner(src[k])) for k in keys)
    print(title)
    for (k,n),cnt in sorted(c.items(),key=lambda x:(x[0][1] or '',x[0][0])):print(f'  {cnt:4d} {k:28s} {n}')
