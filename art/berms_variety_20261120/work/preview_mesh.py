import json, sys, numpy as np
sys.path.insert(0,'.')
import meshes  # rebuilds objects in memory (cheap)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
names = sys.argv[1:]
fig = plt.figure(figsize=(16, 5 * len(names)))
for n, name in enumerate(names):
    ob = [o for o in meshes.objects if o['name'] == name][0]
    P, I, N = ob['P'], ob['I'], ob['N']
    ax = fig.add_subplot(len(names), 1, n + 1, projection='3d')
    tri = P[I][:, :, [0, 2, 1]]
    fn = np.cross(P[I[:,1]]-P[I[:,0]], P[I[:,2]]-P[I[:,0]]); fn /= np.linalg.norm(fn,axis=1,keepdims=True)+1e-9
    light = np.clip(fn @ np.array([-0.5, 0.75, -0.4]) / 1.0, 0.1, 1)
    pc = Poly3DCollection(tri, facecolors=plt.cm.copper(light), edgecolors='none'); ax.add_collection3d(pc)
    mn, mx = P.min(0), P.max(0); c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[2]-r, c[2]+r); ax.set_zlim(c[1]-r*0.4, c[1]+r*0.4); ax.view_init(25, -60)
    ax.set_title(name)
fig.savefig('work/mesh_preview.png', dpi=60, bbox_inches='tight')
