#!/usr/bin/env python3
"""Copy a family that passed its checks into the Unity project (CONTRACT.md: '<family>.glb' and '<family>.parts.json'
in Assets/AthenHill/Art/Bench/<Family>/). No Blender, no Unity. Refuses when check.json is missing or failing, when
the GLB was not baked, or when the GLB is newer than the check.

Usage: python3 kit/publish.py <family dir> [extra file ...]      extra files are copied from <family>/export/ as well,
keeping their folder: 'tex/grip__dirty_color.png' lands in Art/Bench/Grip/tex/, the path parts.json gives under wipes
"""
import json, os, shutil, sys

fam_dir = os.path.abspath(sys.argv[1]); fam = os.path.basename(fam_dir.rstrip('/'))
exp = os.path.join(fam_dir, 'export')
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
dst = os.path.join(root, 'unity', 'AthenHill', 'Assets', 'AthenHill', 'Art', 'Bench', fam.capitalize())
ck = os.path.join(exp, 'check.json'); glb = os.path.join(exp, fam + '.glb'); st = os.path.join(exp, 'stats.json')
if not os.path.exists(ck) or not json.load(open(ck)).get('ok'):
    sys.exit('not published: %s is missing or failing' % ck)
if json.load(open(st)).get('nobake'):
    sys.exit('not published: %s was built with --nobake (flat authoring colours)' % glb)
if os.path.getmtime(glb) > os.path.getmtime(ck) + 1:
    sys.exit('not published: %s is newer than check.json, run check.py again' % glb)
os.makedirs(dst, exist_ok=True)
out = []
for src, name in [(glb, fam + '.glb'), (os.path.join(exp, 'parts.json'), fam + '.parts.json')] + [(os.path.join(exp, x), x) for x in sys.argv[2:]]:      # extras keep their folder (tex/...), as parts.json names them
    os.makedirs(os.path.dirname(os.path.join(dst, name)), exist_ok=True)
    shutil.copy2(src, os.path.join(dst, name)); out.append('%s (%d KB)' % (name, os.path.getsize(src) // 1024))
print('published to', dst, ':', ', '.join(out))
