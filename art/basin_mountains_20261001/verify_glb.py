"""Read BasinMountains.glb back and compare with work/chunks (Unity space): positions, normals, colours, triangles,
winding (upward faces after the glTFast X flip) and chunk-border seam (shared positions/normals identical)."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import glb_io
from scipy.spatial import cKDTree
GLB = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/Terrain/BasinMountains/BasinMountains.glb')
js, ms = glb_io.meshes(GLB)
rec = {'attributes': {}, 'chunks': {}}
allp = {}
for m in ms:
    src = np.load(HERE / 'work/chunks' / (m['node'] + '.npz'))
    U = np.stack([-m['P'][:, 0], m['P'][:, 1], m['P'][:, 2]], 1)         # glTFast: Unity = (-x, y, z)
    Nu = np.stack([-m['N'][:, 0], m['N'][:, 1], m['N'][:, 2]], 1)
    # match vertices by position (exporter may reorder)
    d, order = cKDTree(src['P'].astype(np.float64)).query(U)
    assert d.max() < 1e-4, 'unmatched vertices in ' + m['node']
    dn = np.abs(Nu - src['N'][order]).max()
    dc = np.abs(m['C'][:, :2] - src['C'][order][:, :2]).max()
    # winding in Unity space: glTFast flips X and the winding, so a CCW glTF face seen from +Y stays front-facing
    I = m['I']; a, b, c = m['P'][I[:, 0]], m['P'][I[:, 1]], m['P'][I[:, 2]]
    fn = np.cross(b - a, c - a)                                        # glTF space, right-handed
    up = (fn[:, 1] > 0).mean()
    rec['chunks'][m['node']] = dict(vertices=len(U), triangles=len(I), max_normal_diff=float(dn), max_color_diff=float(dc),
                                    faces_up_fraction=float(up))
    rec['attributes'][m['node']] = {k: (v['componentType'], v['type'], v.get('normalized', False)) for k, v in m['attrs'].items()}
    for p, n in zip(U.astype(np.float32).tolist(), Nu):
        allp.setdefault(tuple(p), []).append(n)
shared = [v for v in allp.values() if len(v) > 1]
rec['seam_vertices'] = len(shared)
rec['seam_max_normal_diff'] = float(max((np.abs(np.array(v) - v[0]).max() for v in shared), default=0))
rec['generator'] = js['asset'].get('generator')
(HERE / 'glb-verify.json').write_text(json.dumps(rec, indent=1))
print(json.dumps(rec, indent=1)[:2500])
