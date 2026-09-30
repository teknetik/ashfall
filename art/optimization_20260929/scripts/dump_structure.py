import sys, array
sys.path.insert(0, '.')
import fbxlib
path = sys.argv[1]
root, ver = fbxlib.load(path)
def show(e, depth, maxdepth):
    props = []
    for v, t in zip(e.props, e.props_type):
        t = chr(t)
        if isinstance(v, array.array): props.append(f"{t}[{len(v)}]")
        elif isinstance(v, bytes): props.append(repr(v[:60]))
        else: props.append(repr(v))
    print('  '*depth + e.id.decode(), ' '.join(props))
    if depth < maxdepth:
        for c in e.elems:
            if c.id == b'P' and depth > 2: continue
            show(c, depth+1, maxdepth)
print('version', ver)
for top in root.elems:
    if top.id in (b'Objects',):
        for o in top.elems:
            if o.id in (b'Geometry',): show(o, 1, 4)
            elif o.id in (b'Model', b'Material'): show(o, 1, 1)
    elif top.id in (b'Definitions', b'Connections', b'Takes', b'Documents', b'References'):
        show(top, 0, 2)
    else:
        show(top, 0, 1)
