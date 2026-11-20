#!/usr/bin/env python3
"""Hero base: put the Unity-side code in place (idempotent). Run at the start of the Unity window, before any install.
  * copies HeroBasePass20261120.cs into Assets/AthenHill/Editor;
  * adds a guard line to the three earlier steps that copy the previous (MPFB) body's files over colonist.glb or the
    armour (ColonistBackPass20261120 install and rollback, PlayerFace20261003 rollback), so they refuse to run while the
    hero base is installed.
Usage: apply.py [--revert]    Exact-match edits only; prints what it did. Run unity/tools/compile_check.py afterwards."""
import shutil, sys
from pathlib import Path
ROOT = Path('/home/teknetik/code/ao2'); ED = ROOT / 'unity/AthenHill/Assets/AthenHill/Editor'; HERE = Path(__file__).resolve().parent
REVERT = '--revert' in sys.argv
EDITS = [
    ('ColonistBackPass20261120.cs',
     '        static string Install()\n        {\n            var rb = Path.Combine(ArtDir, "rollback"); Directory.CreateDirectory(rb);',
     '        static string Install()\n        {\n            HeroBasePass20261120.Guard("ColonistBackPass20261120 install");\n            var rb = Path.Combine(ArtDir, "rollback"); Directory.CreateDirectory(rb);'),
    ('ColonistBackPass20261120.cs',
     '        static string Rollback()\n        {\n            var rb = Path.Combine(ArtDir, "rollback"); var restored = new List<string>();',
     '        static string Rollback()\n        {\n            HeroBasePass20261120.Guard("ColonistBackPass20261120 rollback");\n            var rb = Path.Combine(ArtDir, "rollback"); var restored = new List<string>();'),
    ('PlayerFace20261003.cs',
     '        static string Rollback()\n        {\n            var prevModel=',
     '        static string Rollback()\n        {\n            HeroBasePass20261120.Guard("PlayerFace20261003 rollback");\n            var prevModel='),
    # grip solvers: finger thickness of the hero hands at game scale (build/fingers.json: fingers 12.9 mm, thumb about 15 mm;
    # the MPFB fingers were 8.2 mm), so solved fingers rest on the weapon instead of sinking 4-5 mm into it
    ('PlayerFace20261003.cs',
     'Cap(f0.position,f1.position,.009f);Cap(f1.position,f2.position,.008f);Cap(f2.position,tip,.0075f);',
     'Cap(f0.position,f1.position,.0135f);Cap(f1.position,f2.position,.0125f);Cap(f2.position,tip,.012f);   // hero base hands (20 Nov 2026)'),
    ('PlayerFace20261003.cs',
     'float r=thumb?.0095f:.0082f;',
     'float r=thumb?.0145f:.0125f;   // hero base hands (20 Nov 2026); MPFB: .0095 / .0082'),
    ('RifleHandsPass20261120.cs',
     'public static float FingerRadius=.0102f,ThumbRadius=.0115f;',
     'public static float FingerRadius=.0145f,ThumbRadius=.0165f;   // hero base hands + 2 mm (20 Nov 2026); MPFB: .0102 / .0115'),
]
done = []
for name, old, new in EDITS:
    p = ED / name; s = p.read_text()
    a, b = (new, old) if REVERT else (old, new)
    if b in s and a not in s: done.append(f'{name}: already {"reverted" if REVERT else "applied"}'); continue
    assert s.count(a) == 1, f'{name}: expected exactly one match, found {s.count(a)}'
    p.write_text(s.replace(a, b)); done.append(f'{name}: {"reverted" if REVERT else "guard added"}')
dst = ED / 'HeroBasePass20261120.cs'
if REVERT:
    for f in (dst, dst.with_suffix('.cs.meta')):
        if f.exists(): f.unlink(); done.append(f'removed {f.name}')
else:
    src = HERE / 'HeroBasePass20261120.cs'
    if not dst.exists() or dst.read_bytes() != src.read_bytes(): shutil.copyfile(src, dst); done.append('copied HeroBasePass20261120.cs')
    else: done.append('HeroBasePass20261120.cs up to date')
print('\n'.join(done))
