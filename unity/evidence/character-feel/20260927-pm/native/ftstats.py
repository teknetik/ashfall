import json, sys, statistics
out = {}
for path in sys.argv[1:]:
    d = json.load(open(path))
    ms = sorted(s['dt'] * 1000 for s in d if s.get('dt'))
    if not ms:
        continue
    q = lambda p: ms[min(len(ms) - 1, int(round(p * (len(ms) - 1))))]
    out[path.split('/native/')[-1]] = {
        'samples': len(ms), 'seconds': round(sum(ms) / 1000, 1),
        'avg_fps': round(1000 / statistics.mean(ms), 1),
        'p50_ms': round(q(.5), 2), 'p95_ms': round(q(.95), 2), 'p99_ms': round(q(.99), 2), 'max_ms': round(ms[-1], 2),
        'over_16_67ms': sum(1 for m in ms if m > 16.67), 'over_33ms': sum(1 for m in ms if m > 33.3),
        'max_submitted_tris': max(s.get('tris', 0) for s in d), 'max_setpass': max(s.get('setPass', 0) for s in d)}
print(json.dumps(out, indent=1))
