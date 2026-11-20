#!/usr/bin/env python3
"""Diff two Unity scene files document by document (fileID), so a pass can show that only its own objects changed.
Usage: scene_diff.py BEFORE.unity AFTER.unity [OUT.json]
Prints added, removed and changed documents with their class, fileID and the GameObject name they belong to; for a
changed PrefabInstance it lists the property modifications that differ."""
import json, re, sys
from pathlib import Path

DOC = re.compile(r'^--- !u!(\d+) &(-?\d+)( stripped)?$', re.M)


def docs(path):
    text = Path(path).read_text()
    marks = list(DOC.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[m.group(2)] = (m.group(1), text[m.start():end])
    return out


def names(d):
    """fileID -> GameObject name, for GameObjects and for components (through m_GameObject)."""
    go = {}
    for fid, (cls, body) in d.items():
        if cls == '1':
            m = re.search(r'^  m_Name: (.*)$', body, re.M)
            go[fid] = m.group(1) if m else '?'
    res = dict(go)
    for fid, (cls, body) in d.items():
        m = re.search(r'm_GameObject: \{fileID: (-?\d+)\}', body)
        if m and m.group(1) in go:
            res[fid] = go[m.group(1)]
    return res


def mods(body):
    """PrefabInstance modifications as (target, propertyPath) -> value lines."""
    out = {}
    for m in re.finditer(r'    - target: \{fileID: (-?\d+), guid: (\w+), type: \d+\}\n      propertyPath: (.*)\n      value: (.*)\n      objectReference: (.*)\n', body):
        out[(m.group(1), m.group(2), m.group(3))] = (m.group(4), m.group(5))
    return out


def main():
    a, b = docs(sys.argv[1]), docs(sys.argv[2])
    na, nb = names(a), names(b)
    added = [dict(fileID=k, cls=b[k][0], name=nb.get(k)) for k in b if k not in a]
    removed = [dict(fileID=k, cls=a[k][0], name=na.get(k)) for k in a if k not in b]
    changed = []
    for k in a:
        if k in b and a[k][1] != b[k][1]:
            entry = dict(fileID=k, cls=a[k][0], name=nb.get(k) or na.get(k))
            if a[k][0] == '1001':  # PrefabInstance
                ma, mb = mods(a[k][1]), mods(b[k][1])
                entry['modifications'] = [dict(target=t[0], property=t[2], before=ma.get(t, (None,))[0], after=mb.get(t, (None,))[0])
                                          for t in sorted(set(ma) | set(mb)) if ma.get(t) != mb.get(t)]
            else:
                la, lb = a[k][1].splitlines(), b[k][1].splitlines()
                entry['lines'] = [dict(before=x, after=y) for x, y in zip(la, lb) if x != y][:20] + \
                    ([dict(extra=len(lb) - len(la))] if len(la) != len(lb) else [])
            changed.append(entry)
    rep = dict(before=sys.argv[1], after=sys.argv[2], documentsBefore=len(a), documentsAfter=len(b), added=added, removed=removed, changed=changed)
    s = json.dumps(rep, indent=1)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(s)
    print('documents %d -> %d; added %d, removed %d, changed %d' % (len(a), len(b), len(added), len(removed), len(changed)))
    for e in added:
        print('  + %s %s %s' % (e['cls'], e['fileID'], e['name']))
    for e in removed:
        print('  - %s %s %s' % (e['cls'], e['fileID'], e['name']))
    for e in changed:
        print('  ~ %s %s %s' % (e['cls'], e['fileID'], e['name']))
        for m in e.get('modifications', []):
            print('      %s %s: %s -> %s' % (m['target'], m['property'], m['before'], m['after']))
        for l in e.get('lines', []):
            print('      %s' % l)


if __name__ == '__main__':
    main()
