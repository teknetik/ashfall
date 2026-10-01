"""Old vs new height profiles along rays from the city centre (Unity X/Z). Writes work/profiles.png."""
import math, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
W = Path(__file__).resolve().parent / 'work'
hf = np.load(W / 'heightfield.npz'); H = hf['H']; O = hf['old']
N, ORG = 1025, -512.0
def samp(A, x, z):
    i = np.clip(np.round(x - ORG).astype(int), 0, N - 1); j = np.clip(np.round(z - ORG).astype(int), 0, N - 1); return A[j, i]
angs = [180, 165, 195, 150, 210, 90, 0, 270, 45, 135, 225, 315]   # Unity bearing: 0 = +X (east), 90 = +Z (north)
fig, axs = plt.subplots(len(angs), 1, figsize=(14, 3 * len(angs)))
r = np.arange(0, 500, 0.5)
for ax, b in zip(axs, angs):
    x = np.cos(math.radians(b)) * r; z = np.sin(math.radians(b)) * r
    ax.plot(r, samp(O, x, z), 'k-', lw=1, label='old'); ax.plot(r, samp(H, x, z), 'r-', lw=1, label='new')
    ax.set_title('bearing %d (0=E, 90=N, 180=W)' % b); ax.set_ylim(-5, 85); ax.grid(alpha=.3); ax.set_aspect('equal')
axs[0].legend()
plt.tight_layout(); plt.savefig(W / 'profiles.png', dpi=60)
