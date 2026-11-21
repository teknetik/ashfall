#!/usr/bin/env python3
"""Copy a checked, baked family to the Unity project (CONTRACT.md A: only with a passing check.json).
The fixtures family's own copy of tools/src/publish.py (21 Nov 2026). .meta files beside the copies are left alone.
Usage: python3 fixtures/src/publish_fx.py fixtures
Writes <family>.glb and <family>.parts.json to unity/AthenHill/Assets/AthenHill/Art/Bench/<Family>/ and, for the
fixtures, first notes in parts.json the jaw value at which the vise closes on each thing the check placed in it."""
import json, os, shutil, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.abspath(os.path.join(HERE, '..', '..'))
ROOT = os.path.abspath(os.path.join(PROG, '..', '..'))
U = os.path.join(ROOT, 'unity', 'AthenHill', 'Assets', 'AthenHill', 'Art', 'Bench')
bad = False
for fam in sys.argv[1:]:
    exp = os.path.join(PROG, fam, 'export')
    ck = json.load(open(os.path.join(exp, 'check.json')))
    st = json.load(open(os.path.join(exp, 'stats.json')))
    pj_path = os.path.join(exp, 'parts.json')
    pj = json.load(open(pj_path))
    if not ck.get('ok') or ck.get('nobake') or st.get('nobake'):
        print('NOT PUBLISHED', fam, 'check ok:', ck.get('ok'), 'check on a nobake build:', ck.get('nobake'), 'stats nobake:', st.get('nobake')); bad = True; continue
    if ck.get('generated', '') < pj.get('generated', ''):
        print('NOT PUBLISHED', fam, 'check.json is older than parts.json: run the check again'); bad = True; continue
    if fam == 'fixtures':
        snug = {r['part']: {'mark': r['mark'], 'jaw': r['jaw'], 'gap_mm': r['gap_mm']} for r in (ck.get('rests') or {}).get('rests', []) if r.get('jaw') is not None}
        for h in (ck.get('vise') or {}).get('holds', []):
            snug[h['thing']] = {'jaw': h['jaw'], 'gap_mm': h['gap_mm'], 'size_source': h['size_source']}
        for p in pj['params']:
            if p['id'] == 'fixtures.vise_jaw':
                p['snug_at'] = snug
        json.dump(pj, open(pj_path, 'w'), indent=1)
    d = os.path.join(U, fam.capitalize())
    os.makedirs(d, exist_ok=True)
    shutil.copyfile(os.path.join(exp, pj['glb']), os.path.join(d, pj['glb']))
    shutil.copyfile(pj_path, os.path.join(d, fam + '.parts.json'))
    extra = sorted({w[k] for pp in pj['parts'] for w in pp.get('wipes', []) for k in ('color', 'normal', 'orm') if w.get(k)})
    for rel in extra:                 # the as-found set, at the path parts.json gives (tex/...), beside the GLB
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(exp, rel), os.path.join(d, rel))
        print('  copied', rel)
    h = hashlib.sha256(open(os.path.join(d, pj['glb']), 'rb').read()).hexdigest()[:16]
    print('PUBLISHED', fam, '->', os.path.relpath(d, ROOT), os.path.getsize(os.path.join(d, pj['glb'])) // 1024, 'KB', 'sha256', h,
          'tris', st['tris_total'], 'parts', len(pj['parts']), 'params', len(pj['params']))
sys.exit(1 if bad else 0)
