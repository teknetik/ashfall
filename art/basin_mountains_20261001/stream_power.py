"""Fluvial incision by the stream-power law with an implicit (Braun & Willett 2013) update and priority-flood
drainage routing (Barnes et al. 2014), in numba. dh/dt = U - K A^m S, plus a little hillslope diffusion.

Every node drains to an outlet (mask) through a priority-flood tree, so closed depressions do not trap flow; the
pop order is the topological stack used for drainage-area accumulation and for the implicit height update."""
import math
import numpy as np
import numba as nb

NB8 = np.array([[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]], dtype=np.int64)


@nb.njit(cache=True)
def _heap_push(keys, vals, size, k, v):
    i = size
    keys[i] = k; vals[i] = v
    while i > 0:
        p = (i - 1) >> 1
        if keys[p] <= keys[i]: break
        keys[p], keys[i] = keys[i], keys[p]
        vals[p], vals[i] = vals[i], vals[p]
        i = p
    return size + 1


@nb.njit(cache=True)
def _heap_pop(keys, vals, size):
    k = keys[0]; v = vals[0]
    size -= 1
    keys[0] = keys[size]; vals[0] = vals[size]
    i = 0
    while True:
        l = 2 * i + 1; r = l + 1; m = i
        if l < size and keys[l] < keys[m]: m = l
        if r < size and keys[r] < keys[m]: m = r
        if m == i: break
        keys[m], keys[i] = keys[i], keys[m]
        vals[m], vals[i] = vals[i], vals[m]
        i = m
    return k, v, size


@nb.njit(cache=True)
def route(h, outlet, cell):
    """Priority-flood receivers and stack. Returns rcv (-1 for outlets), stack order, filled heights, distances."""
    n0, n1 = h.shape
    N = n0 * n1
    visited = np.zeros(N, np.bool_)
    rcv = np.full(N, -1, np.int64)
    dist = np.ones(N) * cell
    stack = np.empty(N, np.int64)
    keys = np.empty(N, np.float64); vals = np.empty(N, np.int64); size = 0
    for j in range(n0):
        for i in range(n1):
            if outlet[j, i]:
                idx = j * n1 + i
                visited[idx] = True
                size = _heap_push(keys, vals, size, h[j, i], idx)
    ns = 0
    while size > 0:
        k, idx, size = _heap_pop(keys, vals, size)
        stack[ns] = idx; ns += 1
        j = idx // n1; i = idx - j * n1
        for q in range(8):
            jj = j + NB8[q, 0]; ii = i + NB8[q, 1]
            if jj < 0 or ii < 0 or jj >= n0 or ii >= n1: continue
            nidx = jj * n1 + ii
            if visited[nidx]: continue
            visited[nidx] = True
            rcv[nidx] = idx
            dist[nidx] = cell * (1.41421356 if NB8[q, 0] != 0 and NB8[q, 1] != 0 else 1.0)
            hv = h[jj, ii]
            size = _heap_push(keys, vals, size, hv if hv > k + 1e-4 else k + 1e-4, nidx)
    return rcv, stack[:ns], dist


@nb.njit(cache=True)
def incise(h, outlet, uplift, erodibility, K, m, dt, iters, diff, cell, area_cap=1e12):
    """Run `iters` implicit stream-power steps in place on h (metres). erodibility scales K per node."""
    n0, n1 = h.shape
    N = n0 * n1
    hf = h.ravel()
    U = uplift.ravel(); E = erodibility.ravel()
    area = np.empty(N)
    for it in range(iters):
        rcv, stack, dist = route(h, outlet, cell)
        for q in range(N): area[q] = cell * cell
        for s in range(stack.shape[0] - 1, -1, -1):
            i = stack[s]; r = rcv[i]
            if r >= 0: area[r] += area[i]
        for s in range(stack.shape[0]):
            i = stack[s]; r = rcv[i]
            if r < 0: continue
            hi = hf[i] + U[i] * dt
            if hi <= hf[r]:          # in a filled depression: no incision, only uplift
                hf[i] = hi; continue
            F = K * E[i] * dt * min(area[i], area_cap) ** m / dist[i]   # capped: no runaway gorges
            hf[i] = (hi + F * hf[r]) / (1.0 + F)
        if diff > 0:  # explicit hillslope diffusion (stable for diff <= 0.2)
            lap = np.zeros((n0, n1))
            for j in range(1, n0 - 1):
                for i in range(1, n1 - 1):
                    lap[j, i] = h[j - 1, i] + h[j + 1, i] + h[j, i - 1] + h[j, i + 1] - 4 * h[j, i]
            for j in range(1, n0 - 1):
                for i in range(1, n1 - 1):
                    if not outlet[j, i]: h[j, i] += diff * lap[j, i]
    return area.reshape(n0, n1)
