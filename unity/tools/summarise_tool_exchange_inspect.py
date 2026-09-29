"""Print a short summary of evidence/tool-exchange/20260929-light/inspect.json (t_e14abefb)."""
import json, sys
d = json.load(open(sys.argv[1]))
print('building', d['buildingPos'], d['buildingYaw'])
print('lampish', json.dumps(d['lampish'])[:3000])
print('circuit', d['circuit'])
for l in d['lightsNearest40'][:16]:
    print(l['path'], l['type'], l['intensity'], l['range'], l['shadows'], l['enabled'], [round(x, 1) for x in l['pos']], round(l['dist'], 1))
print('dir', d['directional'], d['ambient'], d['totalPointSpotLights'])
for r in d['displayBounds']:
    print(r['name'], [round(x, 2) for x in r['center']], [round(x, 2) for x in r['size']])
