import json
d = json.load(open('/home/teknetik/code/ao2/art/relay_airwater_surfaces_20260909/facade-meshes-v2.json'))
print(len(d), [k for k in d[0]])
for m in d:
    if m['name'] in ('air_water Filter canister 0.9', 'air_water Filter canister 2.5', 'air_water Filter manifold', 'air_water Roof to filter downfeed', 'air_water Front masonry segment 3 0'):
        P = m['positions']
        mn = [min(p[i] for p in P) for i in range(3)]; mx = [max(p[i] for p in P) for i in range(3)]
        print(m['name'], m['material'], len(P), [round(x, 3) for x in mn], [round(x, 3) for x in mx], 'tris', len(m.get('indices', [])) // 3)
n = sum(len(m.get('indices', [])) // 3 for m in d if m['name'].startswith('air_water'))
print('air_water tris in export', n)
