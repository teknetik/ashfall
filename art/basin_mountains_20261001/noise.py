"""Vectorised 2D gradient noise, fBm, ridged multifractal and domain warp (numpy). Deterministic per seed."""
import numpy as np

_GRAD = np.array([[np.cos(a), np.sin(a)] for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)])


class Perlin:
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        p = rng.permutation(256)
        self.perm = np.concatenate([p, p]).astype(np.int64)
        self.off = rng.uniform(0, 256, 2)

    def __call__(self, x, y):
        x = x + self.off[0]; y = y + self.off[1]
        xi = np.floor(x); yi = np.floor(y)
        xf = x - xi; yf = y - yi
        xi = xi.astype(np.int64) & 255; yi = yi.astype(np.int64) & 255
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        P = self.perm
        def g(ix, iy, dx, dy):
            h = P[P[ix] + iy] & 15
            return _GRAD[h, 0] * dx + _GRAD[h, 1] * dy
        n00 = g(xi, yi, xf, yf); n10 = g(xi + 1, yi, xf - 1, yf)
        n01 = g(xi, yi + 1, xf, yf - 1); n11 = g(xi + 1, yi + 1, xf - 1, yf - 1)
        nx0 = n00 + u * (n10 - n00); nx1 = n01 + u * (n11 - n01)
        return (nx0 + v * (nx1 - nx0)) * 1.41  # ~[-1, 1]


def fbm(X, Z, seed, wavelength, octaves=5, lacunarity=2.03, gain=0.5, rot=True):
    total = np.zeros_like(X); amp = 1.0; norm = 0.0; f = 1.0 / wavelength
    for o in range(octaves):
        n = Perlin(seed * 131 + o)
        if rot:  # rotate each octave to hide grid alignment
            c, s = np.cos(0.6 * o + 0.3), np.sin(0.6 * o + 0.3)
            x, z = (X * c - Z * s) * f, (X * s + Z * c) * f
        else:
            x, z = X * f, Z * f
        total += amp * n(x, z); norm += amp
        amp *= gain; f *= lacunarity
    return total / norm


def ridged(X, Z, seed, wavelength, octaves=6, lacunarity=2.07, gain=2.0, offset=1.0, H=1.0):
    """Musgrave ridged multifractal, normalised to about [0, 1] (sharp crests at 1)."""
    result = np.zeros_like(X); weight = np.ones_like(X); f = 1.0 / wavelength; norm = 0.0
    for o in range(octaves):
        n = Perlin(seed * 977 + o)
        c, s = np.cos(0.7 * o + 0.1), np.sin(0.7 * o + 0.1)
        x, z = (X * c - Z * s) * f, (X * s + Z * c) * f
        signal = offset - np.abs(n(x, z))
        signal = signal * signal * weight
        w = (lacunarity ** (-H * o))
        result += signal * w; norm += w
        weight = np.clip(signal * gain, 0, 1)
        f *= lacunarity
    return result / norm


def warp(X, Z, seed, wavelength, amount, octaves=3):
    wx = fbm(X, Z, seed, wavelength, octaves)
    wz = fbm(X, Z, seed + 7, wavelength, octaves)
    return X + amount * wx, Z + amount * wz
