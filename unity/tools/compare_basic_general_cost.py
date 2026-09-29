"""Compare matched before/after dwell timing and memory for the Basic General counter pass."""
import json, sys
from pathlib import Path
R = Path(sys.argv[1])
def load(tag, stage):
    return json.loads((R / (tag + '-native') / ('basic-general-captures-%s.json' % stage)).read_text())
rows = []
out = {}
for stage in ('fixed', 'players'):
    b = load('before', stage); a = load('after', stage)
    for db, da in zip(b['dwell'], a['dwell']):
        assert db['view'] == da['view']
        def g(x, k, f): return None if x.get(k) is None else round(x[k][f], 2)
        row = dict(view=db['view'], before=dict(fps=round(db['averageFps'], 1), p50=round(db['p50Ms'], 2), p99=round(db['p99Ms'], 2), max=round(db['maxMs'], 2), frames=db['frames'], draws=g(db, 'draws', 'mean'), tris=g(db, 'tris', 'mean'), setPass=g(db, 'setPass', 'mean'), main=g(db, 'mainMs', 'mean'), gpu=g(db, 'gpuMs', 'mean')),
                   after=dict(fps=round(da['averageFps'], 1), p50=round(da['p50Ms'], 2), p99=round(da['p99Ms'], 2), max=round(da['maxMs'], 2), frames=da['frames'], draws=g(da, 'draws', 'mean'), tris=g(da, 'tris', 'mean'), setPass=g(da, 'setPass', 'mean'), main=g(da, 'mainMs', 'mean'), gpu=g(da, 'gpuMs', 'mean')),
                   loadBefore=b['loadAverage'], loadAfter=a['loadAverage'])
        rows.append(row)
        print(row['view'], 'before', row['before'], '\n   after ', row['after'])
out['rows'] = rows
mb = json.loads((R / 'before-native/memory.json').read_text()); ma = json.loads((R / 'after-native/memory.json').read_text())
out['memory'] = dict(before=mb, after=ma, deltaTextureCurrentMiB=round((ma['textureCurrentBytes'] - mb['textureCurrentBytes']) / 2**20, 1), deltaTextureDesiredMiB=round((ma['textureDesiredBytes'] - mb['textureDesiredBytes']) / 2**20, 1), deltaTextureFullMiB=round((ma['textureFullResolutionBytes'] - mb['textureFullResolutionBytes']) / 2**20, 1), deltaUnityAllocatedMiB=round((ma['unityAllocatedBytes'] - mb['unityAllocatedBytes']) / 2**20, 1))
print(json.dumps({k: v for k, v in out['memory'].items() if k.startswith('delta')}))
(R / 'localised-cost-comparison.json').write_text(json.dumps(out, indent=2))
