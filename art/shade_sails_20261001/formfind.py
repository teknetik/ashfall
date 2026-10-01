"""Shade-sail form finding (force density method), pure numpy: shared by sails.py (layout/clearance checks, plain
Python), author_sails.py (Blender geometry) and make_textures.py (UV layout for the canvas maps).

A tensioned sail is a prestressed membrane bounded by hem cables and pinned at its corners. The force density method
(Schek 1974) gives its equilibrium shape from a linear solve: for every free node i, sum_j q_ij (x_j - x_i) + p_i = 0,
with q the force density (force / length) of each link. The membrane is a regular grid of links with q = 1 (uniform
prestress T); the hem links get q_c, chosen so that the hem cable curves inwards with the sag a sailmaker cuts for
(about 6-8 % of the edge span: a hem with tension Tc between membrane tension T has radius R = Tc / T, sag L^2 / 8R).
A small area load adds the slight belly of a real sail. Corner nodes (the fabric corners, short of the fixing points
by the corner hardware) are fixed. Units: metres, Unity axes (X east, Y up, Z north).

Quads use an (n+1) x (m+1) grid (bilinear start); triangles a barycentric grid. The same parametric grid sampled every
k-th node gives the LOD1 surface, so both LODs lie on one shape.
"""
import math
import numpy as np


def _grid_quad(C, n, m):
    """C: 4 corners in order (c0, c1, c2, c3) around the boundary. Nodes (i over c0->c1 [n], j over c0->c3 [m])."""
    C = np.asarray(C, float)
    idx = {}
    P, uv = [], []
    for j in range(m + 1):
        for i in range(n + 1):
            s, t = i / n, j / m
            p = (1 - s) * (1 - t) * C[0] + s * (1 - t) * C[1] + s * t * C[2] + (1 - s) * t * C[3]
            idx[(i, j)] = len(P)
            P.append(p)
            uv.append((s, t))
    E, F = [], []
    for j in range(m + 1):
        for i in range(n + 1):
            a = idx[(i, j)]
            if i < n:
                E.append((a, idx[(i + 1, j)]))
            if j < m:
                E.append((a, idx[(i, j + 1)]))
            if i < n and j < m:
                F.append((a, idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    # boundary loop c0 -> c1 -> c2 -> c3 -> c0
    loop = [idx[(i, 0)] for i in range(n)] + [idx[(n, j)] for j in range(m)] + \
           [idx[(i, m)] for i in range(n, 0, -1)] + [idx[(0, j)] for j in range(m, 0, -1)]
    corners = [idx[(0, 0)], idx[(n, 0)], idx[(n, m)], idx[(0, m)]]
    edges_of_side = [
        [(idx[(i, 0)], idx[(i + 1, 0)]) for i in range(n)],
        [(idx[(n, j)], idx[(n, j + 1)]) for j in range(m)],
        [(idx[(i + 1, m)], idx[(i, m)]) for i in range(n)][::-1],
        [(idx[(0, j + 1)], idx[(0, j)]) for j in range(m)][::-1],
    ]
    return np.array(P), np.array(uv), E, F, loop, corners, idx, edges_of_side


def _grid_tri(C, n):
    """C: 3 corners. Barycentric nodes (i, j), i + j <= n: p = c0 + i/n (c1 - c0) + j/n (c2 - c0)."""
    C = np.asarray(C, float)
    idx = {}
    P, uv = [], []
    for j in range(n + 1):
        for i in range(n + 1 - j):
            p = C[0] + (i / n) * (C[1] - C[0]) + (j / n) * (C[2] - C[0])
            idx[(i, j)] = len(P)
            P.append(p)
            uv.append((i / n, j / n))
    E, F = [], []
    for j in range(n + 1):
        for i in range(n + 1 - j):
            a = idx[(i, j)]
            if (i + 1, j) in idx:
                E.append((a, idx[(i + 1, j)]))
            if (i, j + 1) in idx:
                E.append((a, idx[(i, j + 1)]))
            if (i + 1, j) in idx and (i, j + 1) in idx:
                E.append((idx[(i + 1, j)], idx[(i, j + 1)]))
                F.append((a, idx[(i + 1, j)], idx[(i, j + 1)]))
                if (i + 1, j + 1) in idx:
                    F.append((idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    loop = [idx[(i, 0)] for i in range(n)] + [idx[(n - j, j)] for j in range(n)] + [idx[(0, j)] for j in range(n, 0, -1)]
    corners = [idx[(0, 0)], idx[(n, 0)], idx[(0, n)]]
    edges_of_side = [
        [(idx[(i, 0)], idx[(i + 1, 0)]) for i in range(n)],
        [(idx[(n - j, j)], idx[(n - j - 1, j + 1)]) for j in range(n)],
        [(idx[(0, j + 1)], idx[(0, j)]) for j in range(n)][::-1],
    ]
    return np.array(P), np.array(uv), E, F, loop, corners, idx, edges_of_side


class Sail:
    """Solved sail surface. Attributes: P (nodes), F (faces, quads or tris), loop (boundary node ids in order),
    corners, side_nodes (node ids along each side, corner to corner), grid info for LOD subsampling."""

    def __init__(self, corners, spacing=0.12, sag=0.07, belly=0.06, seed_q=None):
        self.C = np.asarray(corners, float)
        self.kind = "quad" if len(self.C) == 4 else "tri"
        L = [np.linalg.norm(self.C[(k + 1) % len(self.C)] - self.C[k]) for k in range(len(self.C))]
        self.side_len = L
        if self.kind == "quad":
            n = max(4, int(round(max(L[0], L[2]) / spacing)))
            m = max(4, int(round(max(L[1], L[3]) / spacing)))
            n += n % 4 and (4 - n % 4)       # multiples of 4 so LOD1 = every 4th node lands on the corners
            m += m % 4 and (4 - m % 4)
            self.n, self.m = n, m
            g = _grid_quad(self.C, n, m)
        else:
            n = max(4, int(round(max(L) / spacing)))
            n += n % 4 and (4 - n % 4)
            self.n, self.m = n, n
            g = _grid_tri(self.C, n)
        self.P0, self.uv, self.E, self.F, self.loop, self.corner_ids, self.idx, self.side_edges = g
        self.spacing = spacing
        self.sag_target = sag
        self.belly = belly
        self.solve()

    # ---------------------------------------------------------------- force density solve
    def _solve_once(self, qc_by_side, load):
        N = len(self.P0)
        fixed = np.zeros(N, bool)
        fixed[self.corner_ids] = True
        q = {}
        for (a, b) in self.E:
            q[(min(a, b), max(a, b))] = 1.0
        for s, edges in enumerate(self.side_edges):
            for (a, b) in edges:
                q[(min(a, b), max(a, b))] = qc_by_side[s]
        free = np.where(~fixed)[0]
        pos = {v: k for k, v in enumerate(free)}
        A = np.zeros((len(free), len(free)))
        B = np.zeros((len(free), 3))
        for (a, b), w in q.items():
            for (i, j) in ((a, b), (b, a)):
                if fixed[i]:
                    continue
                A[pos[i], pos[i]] += w
                if fixed[j]:
                    B[pos[i]] += w * self.P0[j]
                else:
                    A[pos[i], pos[j]] -= w
        B[:, 1] -= load
        X = np.linalg.solve(A, B)
        P = self.P0.copy()
        P[free] = X
        return P

    def side_sag(self, P, s):
        """Max distance of the side's hem from the straight chord between its corners, as a fraction of the span."""
        edges = self.side_edges[s]
        nodes = [edges[0][0]] + [e[1] for e in edges]
        a, b = P[nodes[0]], P[nodes[-1]]
        d = b - a
        L = np.linalg.norm(d)
        u = d / L
        dev = max(np.linalg.norm((P[k] - a) - u * np.dot(P[k] - a, u)) for k in nodes)
        return dev / L

    def solve(self):
        h = self.spacing
        # analytic start: hem tension Tc = L T / (8 sag), q_c = Tc / h (membrane T = q_m = 1 per link)
        qc = [max(4.0, L / (8 * self.sag_target) / h) for L in self.side_len]
        # area load per node for the belly: T grad^2 y = -rho  ->  y_mid ~ rho L^2 / (8 T)
        Lm = float(np.mean(self.side_len))
        rho = 8 * self.belly / (Lm * Lm)
        load = rho * h * h
        for _ in range(6):                                  # tune each side's hem to its target sag
            P = self._solve_once(qc, load)
            for s in range(len(qc)):
                got = self.side_sag(P, s)
                qc[s] *= max(0.6, min(1.6, (got / self.sag_target)))
        self.qc = qc
        self.P = self._solve_once(qc, load)
        self.sags = [round(self.side_sag(self.P, s), 4) for s in range(len(qc))]

    # ---------------------------------------------------------------- helpers
    def plane_uv(self):
        """Planar metre coordinates of every node in the best-fit plane of the corners (u along c0->c1)."""
        c = self.C.mean(0)
        X = self.C - c
        _, _, vt = np.linalg.svd(X)
        nrm = vt[2]
        if nrm[1] < 0:
            nrm = -nrm
        e1 = self.C[1] - self.C[0]
        e1 = e1 - nrm * np.dot(e1, nrm)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(nrm, e1)
        Q = self.P - c
        return np.stack([Q @ e1, Q @ e2], 1), c, e1, e2, nrm

    def lod_nodes(self, k):
        """Node ids and faces of the LOD grid sampled every k-th node (quads: k | n, m; tris: k | n)."""
        if self.kind == "quad":
            n, m = self.n // k, self.m // k
            keep = {}
            for j in range(m + 1):
                for i in range(n + 1):
                    keep[(i, j)] = self.idx[(i * k, j * k)]
            F = [(keep[(i, j)], keep[(i + 1, j)], keep[(i + 1, j + 1)], keep[(i, j + 1)]) for j in range(m) for i in range(n)]
        else:
            n = self.n // k
            keep = {}
            for j in range(n + 1):
                for i in range(n + 1 - j):
                    keep[(i, j)] = self.idx[(i * k, j * k)]
            F = []
            for j in range(n + 1):
                for i in range(n + 1 - j):
                    if (i + 1, j) in keep and (i, j + 1) in keep:
                        F.append((keep[(i, j)], keep[(i + 1, j)], keep[(i, j + 1)]))
                        if (i + 1, j + 1) in keep:
                            F.append((keep[(i + 1, j)], keep[(i + 1, j + 1)], keep[(i, j + 1)]))
        return keep, F

    def lowest(self):
        return float(self.P[:, 1].min())

    def height_at(self, x, z):
        """Height of the sail above (x, z) (nearest node within 1.5 spacings), or None outside the sail."""
        d = np.hypot(self.P[:, 0] - x, self.P[:, 2] - z)
        k = int(np.argmin(d))
        return float(self.P[k, 1]) if d[k] < 1.5 * self.spacing else None

    def outline(self):
        return self.P[self.loop]


def pull_in(fix, centroid, dist):
    """Fabric corner = fixing point moved towards the sail centroid (horizontally and along the slope) by the corner
    hardware length."""
    fix, centroid = np.asarray(fix, float), np.asarray(centroid, float)
    d = centroid - fix
    return fix + d / np.linalg.norm(d) * dist


def catenary(a, b, sag, n):
    """Parabolic catenary points from a to b with a vertical sag at mid-span."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    out = []
    for k in range(n + 1):
        t = k / n
        p = a + (b - a) * t
        p[1] -= 4 * sag * t * (1 - t)
        out.append(p)
    return np.array(out)
