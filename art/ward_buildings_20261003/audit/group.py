import json,collections,sys
import gzip; d=json.load(gzip.open('audit/audit.json.gz'))
depth=int(sys.argv[1]) if len(sys.argv)>1 else 2
G=collections.defaultdict(lambda: dict(n=0,tris=0,act=0,en=0,mn=[1e9]*3,mx=[-1e9]*3,mats=collections.Counter(),meshassets=collections.Counter()))
for r in d['renderers']:
    c,s=r['center'],r['size']
    if abs(c[0])>62 or abs(c[2])>52: continue
    if not r['active']: continue
    if r['path'].startswith('City Render Chunks'): continue
    key='/'.join(r['path'].split('/')[:depth])
    g=G[key]; g['n']+=1; g['tris']+=r['tris']; g['en']+= r['enabled']
    for i in range(3):
        g['mn'][i]=min(g['mn'][i],c[i]-s[i]/2); g['mx'][i]=max(g['mx'][i],c[i]+s[i]/2)
    for m in r['mats']: g['mats'][m]+=1
    g['meshassets'][r.get('meshAsset') or '']+=1
for k,g in sorted(G.items(), key=lambda kv:-(kv[1]['mx'][1])):
    sz=[g['mx'][i]-g['mn'][i] for i in range(3)]
    if max(sz)<3: continue
    print(f"{k[:70]:70s} n={g['n']:4d} en={g['en']:4d} tris={g['tris']:8d} min=({g['mn'][0]:.0f},{g['mn'][1]:.1f},{g['mn'][2]:.0f}) size=({sz[0]:.1f},{sz[1]:.1f},{sz[2]:.1f}) mats={[m for m,_ in g['mats'].most_common(3)]}")
