#!/usr/bin/env python3
"""Markdown tables for the README from measure.py JSON outputs (before vs after at one hour)."""
import json, sys
from pathlib import Path

def load(p): return {(r['camera'], r['hour']): r for r in json.loads(Path(p).read_text())}

def main(pairs, hour):
    print('| camera | centre p50 before → after | near-black share before → after | p95 (lamp pools) before → after | clipped after | lights in view |')
    print('|---|---|---|---|---|---|')
    act = []
    for b, a in pairs:
        B, A = load(b), load(a)
        for k in sorted(A):
            if abs(k[1] - hour) > .01 or k not in B: continue
            fb, fa = B[k]['frame'], A[k]['frame']
            print('| %s | %.1f → %.1f | %.2f → %.2f | %.1f → %.1f | %.4f | %s |' % (k[0], fb['p50'], fa['p50'], fb['black'], fa['black'], fb['p95'], fa['p95'], fa['clipped'], A[k].get('lightsInView', {}).get('total', '-')))
            ba = {x['name']: x for x in B[k]['actors']}
            for x in A[k]['actors']:
                y = ba.get(x['name'])
                if y: act.append((k[0], x, y))
    print()
    print('| camera | actor | face before → after | torso before → after | ground before → after | face/ground before → after |')
    print('|---|---|---|---|---|---|')
    f = lambda v: '-' if v is None else ('%.1f' % v if isinstance(v, float) else str(v))
    for cam, x, y in act:
        print('| %s | %s | %s → %s | %s → %s | %s → %s | %s → %s |' % (cam, x['name'], f(y['face']), f(x['face']), f(y['torso']), f(x['torso']), f(y['ground']), f(x['ground']), f(y['faceOverGround']), f(x['faceOverGround'])))

if __name__ == '__main__':
    hour = float(sys.argv[1]); args = sys.argv[2:]
    main(list(zip(args[0::2], args[1::2])), hour)
