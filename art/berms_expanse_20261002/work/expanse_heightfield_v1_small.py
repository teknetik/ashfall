#!/usr/bin/env python3
"""Outer Berms expansion heightfield (2 Oct 2026), derived from art/basin_mountains_20261001/basin_heightfield.py.

Carl: "expand the outer berms, push back the mountains if required". Same generator, same layout and erosion, with
three changes (footprint.json):

1. **Push.** West of the city (X < -62) the landform is evaluated at a remapped X: the first `floor_keep` metres of
   floor beyond the wall are stretched over `floor_keep + push` metres, and everything beyond moves `push` metres
   further west. The push fades out between |Z| = z_full and z_zero, so the hills north and south of the city keep
   their place and the western ring opens into a bay. Noise is evaluated at the remapped point too, so the same
   massifs reappear further out instead of new ones.
2. **Depot rise.** The old Berms ground climbs 7-11 m on its south-west edge (the depot's conveyor stands on that
   slope). The old footprint's edge heights are carried outward and fall off with distance, so the slope becomes a
   rocky spur in the new floor instead of a cliff.
3. **Playable floor.** Inside the `playable` polygon the surface is kept walkable: capped at a smoothed floor level
   plus a little relief, rising toward the polygon edge at most `edge_slope`. The original Berms ground footprint
   still keeps the OLD surface exactly (lock and 7 m blend unchanged), so every installed object stays grounded.

Run (memory-capped):  $O/heavy.sh uv run --with numpy --with numba --with scipy --with pillow --with matplotlib python expanse_heightfield.py
Output: work/heightfield.npz (+ work/hillshade.png), heightfield.json
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
BASIN = HERE.parent / 'basin_mountains_20261001'
sys.path.insert(0, str(BASIN))
import basin_heightfield as bh  # noqa: E402
import noise, stream_power  # noqa: E402

WORK = HERE / 'work'
FP = json.loads((HERE / 'footprint.json').read_text())
N, CELL, ORG = bh.N, bh.CELL, bh.ORG
smoothstep = bh.smoothstep


def remap_x(X, Z, push):
    """Bay-shaped push: floor stretched, ring moved west; fades out with |Z|."""
    w = 1 - smoothstep(push['z_full'], push['z_zero'], np.abs(Z))
    P = push['metres'] * w; D0 = push['floor_keep']
    u = np.maximum(-62.0 - X, 0.0)
    # smooth hand-over from the stretched floor (slope D0/(D0+P)) to the shifted ring (slope 1) over 12 m
    lin = u * D0 / np.maximum(D0 + P, 1e-6)
    shift = u - P
    k = smoothstep(D0 + P - 6, D0 + P + 6, u)
    up = np.where(P > 1e-6, lin * (1 - k) + np.maximum(shift, lin) * k, u)
    return np.where(X < -62.0, -62.0 - up, X)


def polygon_fields(X, Z, poly):
    """Inside mask and distances (m) to the polygon edge, inside and outside."""
    path = MPath(np.array(poly, float))
    inside = path.contains_points(np.stack([X.ravel(), Z.ravel()], 1)).reshape(X.shape)
    d_in = ndimage.distance_transform_edt(inside) * CELL
    d_out = ndimage.distance_transform_edt(~inside) * CELL
    return inside, d_in, d_out


def main():
    t0 = time.time(); WORK.mkdir(exist_ok=True)
    P = bh.P
    rec = dict(params=P, footprint=FP, grid=dict(n=N, cell=CELL, origin=ORG))
    X, Z = bh.grid()
    old = bh.old_surface(); rec['old_cover'] = float(np.isfinite(old).mean())
    geo = bh.geology_r(X, Z)
    Xr = remap_x(X, Z, FP['push'])
    H, a, t, s = bh.landform(Xr, Z, rec)
    print('landform (pushed)', round(time.time() - t0, 1), flush=True)
    # ---- old Berms footprint lock (exactly as the basin pass), and its edge carried outward as the depot rise
    x0, x1, z0, z1 = FP['old']
    dxo = np.maximum(np.maximum(x0 - X, X - x1), 0); dzo = np.maximum(np.maximum(z0 - Z, Z - z1), 0)
    outside = np.hypot(dxo, dzo)
    inside_old = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Z - z0, z1 - Z))
    w = smoothstep(0.75, 7.0, outside)
    have_old = np.isfinite(old)
    oldz = np.where(have_old, old, H)
    in_old = outside == 0
    _, (ji, ii) = ndimage.distance_transform_edt(~in_old, return_indices=True)
    edge_raw = oldz[ji, ii]                                             # old height at the nearest footprint point
    lockz = np.where(in_old, oldz, edge_raw)                            # blend target: old inside, its edge outside
    edge_h = ndimage.gaussian_filter(edge_raw, 3.0 / CELL)
    floor0 = -1.2
    rise = np.maximum(edge_h - floor0, 0) * (1 + 0.12 * noise.fbm(X, Z, 72, 14.0, 3))
    L = (8.0 + 2.0 * rise) * (1 + 0.35 * noise.fbm(X, Z, 71, 30.0, 3))  # 11 m rise falls off over ~30 m (about 20 deg)
    spur = floor0 + rise * np.cos(np.clip(outside / np.maximum(L, 4.0), 0, 1) * np.pi / 2) ** 2
    playable = FP['playable']
    inF, dF_in, dF_out = polygon_fields(X, Z, playable)
    # the spur only matters on the playable floor and just beyond it
    spur_w = (inF | (dF_out < 20)) & ~in_old
    H = np.where(spur_w, bh.smax(H, spur, 2.0), H)
    # pre-erosion floor cap: hills may not intrude into the playable floor (they start at its edge)
    fl = FP['floor']
    base = np.clip(ndimage.gaussian_filter(np.where(inF, H, np.nan_to_num(H)), 18 / CELL), -1.6, 1.2)
    cap = base + fl['max_relief'] + np.maximum(fl['edge_ramp'] - dF_in, 0) * fl['edge_slope']
    capm = inF & ~in_old
    H = np.where(capm, np.minimum(H, np.maximum(cap, spur)), H)
    H = lockz + (H - lockz) * w
    # stream-power incision (2 m): drainage to the city basin, the old footprint and the playable floor
    k = int(P['sp_cell'] / CELL)
    Hc = np.ascontiguousarray(H[::k, ::k]).astype(np.float64)
    tc = t[::k, ::k]
    on_floor = (dF_in > 4) & (spur < floor0 + 1.0)                     # the spur is eroded, the floor is base level
    outlet = (tc < 6.0) | (outside[::k, ::k] == 0) | on_floor[::k, ::k]
    outlet[0, :] = outlet[-1, :] = outlet[:, 0] = outlet[:, -1] = True
    erod = np.ascontiguousarray((0.75 + 0.5 * (0.5 + 0.5 * noise.fbm(X[::k, ::k], Z[::k, ::k], 61, 80.0, 3))) * w[::k, ::k])
    H0c = Hc.copy()
    stream_power.incise(Hc, outlet, np.zeros_like(Hc), erod, P['sp_K'], P['sp_m'], P['sp_dt'], P['sp_iters'], P['sp_diff'], P['sp_cell'], P['sp_area_cap'])
    pk0 = ndimage.maximum_filter(H0c + 1.8, size=31); pk1 = ndimage.maximum_filter(Hc + 1.8, size=31)
    ratio = ndimage.gaussian_filter(np.clip(pk0 / np.maximum(pk1, 0.5), 1.0, P['peak_restore_max']), 12)
    Hc = (Hc + 1.8) * ratio - 1.8
    dc = Hc - H0c
    rec['incision'] = dict(min=float(dc.min()), p1=float(np.percentile(dc, 1)), max=float(dc.max()))
    yy = np.arange(N) / k
    dcu = ndimage.map_coordinates(dc, np.meshgrid(yy, yy, indexing='ij'), order=3, mode='nearest')
    H = H + dcu
    print('stream power', round(time.time() - t0, 1), rec['incision'], flush=True)
    outlet1 = (t < 6.0) | (outside == 0) | on_floor; outlet1[0, :] = outlet1[-1, :] = outlet1[:, 0] = outlet1[:, -1] = True
    erod1 = np.ascontiguousarray((0.7 + 0.6 * (0.5 + 0.5 * noise.fbm(X, Z, 62, 40.0, 3))) * w)
    gy, gx = np.gradient(bh.blur(H, 2.0), CELL); slope0 = np.hypot(gx, gy)
    seed = P['gully_seed'] * (noise.fbm(X, Z, 63, 13.0, 3) + 0.5 * noise.fbm(X, Z, 64, 5.0, 2))
    H = np.ascontiguousarray(H + seed * smoothstep(0.15, 0.6, slope0) * w)
    H1 = H.copy()
    stream_power.incise(H, outlet1, np.zeros_like(H), erod1, P['sp1_K'], P['sp1_m'], 1.0, P['sp1_iters'], P['sp1_diff'], CELL)
    rec['incision1'] = dict(min=float((H - H1).min()), p1=float(np.percentile(H - H1, 1)))
    print('stream power 1 m', round(time.time() - t0, 1), flush=True)
    Ht, hard = bh.terrace(H, X, Z, geo, rec)
    H = H + (Ht - H) * w
    mount = smoothstep(1.0, 6.0, H + 1.8) * (t > 8) * w
    bh.erode(H, mount.astype(np.float64), P['drops_fine'], 8, 2, 0.05, P['erode_capacity'], 0.01, P['erode_speed'], P['deposit_speed'], 0.015, 4.0, 40)
    print('fine erosion', round(time.time() - t0, 1), flush=True)
    H = bh.thermal(H, smoothstep(2, 6, H + 1.8) * (1 - hard) * 0.6 * w, 37.0, 6)
    gy, gx = np.gradient(H, CELL); slope = np.hypot(gx, gy)
    H = H + P['detail_amp'] * noise.fbm(X, Z, 51, 7.0, 3) * smoothstep(0.3, 1.0, slope) * mount
    rk = noise.ridged(X, Z, 52, 14.0, 3, gain=1.5) - 0.45
    H = H + P['rock_detail'] * rk * smoothstep(0.35, 1.1, slope) * mount * (0.5 + 0.5 * hard)
    # ---- final playable floor: walkable relief inside the polygon (smooth floor + small undulation), the spur kept,
    # rising toward the edge no steeper than edge_slope
    base = ndimage.gaussian_filter(np.where(inF, np.minimum(H, 2.0), 0.0), 10 / CELL) / np.maximum(ndimage.gaussian_filter(inF.astype(float), 10 / CELL), 1e-3)
    base = np.clip(base, -1.6, 1.6)
    und = 0.6 * noise.fbm(X, Z, 81, 34.0, 3) + 0.25 * noise.fbm(X, Z, 84, 13.0, 2) + 0.08 * noise.fbm(X, Z, 82, 5.0, 2)
    floorH = base + und
    cap = np.maximum(floorH + np.maximum(fl['edge_ramp'] - dF_in, 0) * fl['edge_slope'], spur + 0.25 * noise.fbm(X, Z, 83, 9.0, 3))
    soft = smoothstep(0, 6, dF_in)
    Hfl = np.minimum(H, cap)
    Hfl = np.maximum(Hfl, floorH - 0.6)                                 # no pits in the floor
    H = np.where(capm, H + (Hfl - H) * soft, H)
    # ---- final old-footprint lock (as before) and no moat around it
    floor_ok = np.where(outside < 45, spur - 0.6 - 0.2 * np.maximum(spur - floor0, 0), -1e9)   # gullies may cut the spur, not a moat
    H = np.maximum(H, floor_ok)
    Hf = lockz + (H - lockz) * w
    Hf = np.where(t < 0, -1.8, Hf)
    # basin triangles more than 3 m inside the new ground mesh (playable + skirt) are hidden and dropped
    ground_in = dF_out <= FP['skirt']
    d_ground_in = ndimage.distance_transform_edt(ground_in) * CELL
    drop = (d_ground_in > 3.0) | (inside_old > 3.0)
    rec['lock'] = dict(berms=FP['old'], berms_exact_margin=0.75, berms_blend_to=7.0, drop_inside=3.0, ground='playable + skirt')
    sun, sky = bh.bake_light(Hf, X, Z)
    dev = np.where(have_old, Hf - old, np.nan)
    gy, gx = np.gradient(Hf, CELL); sl = np.degrees(np.arctan(np.hypot(gx, gy)))
    rec['stats'] = dict(h_min=float(Hf.min()), h_max=float(Hf.max()),
                        lock_max_dev=float(np.nanmax(np.abs(np.where(w == 0, dev, 0)))),
                        playable_h=[float(Hf[inF].min()), float(np.percentile(Hf[inF], 50)), float(Hf[inF].max())],
                        playable_slope_p95=float(np.percentile(sl[inF & ~in_old], 95)), playable_slope_max=float(sl[inF & ~in_old].max()),
                        playable_area_m2=float(inF.sum() * CELL * CELL), old_area_m2=float(in_old.sum() * CELL * CELL),
                        seconds=time.time() - t0)
    np.savez_compressed(WORK / 'heightfield.npz', H=Hf.astype(np.float32), sun=sun.astype(np.float32), sky=sky.astype(np.float32),
                        old=old.astype(np.float32), w=w.astype(np.float32), drop=drop, t=t.astype(np.float32),
                        playable=inF, d_in=dF_in.astype(np.float32), d_out=dF_out.astype(np.float32))
    (HERE / 'heightfield.json').write_text(json.dumps(rec, indent=1))
    bh.hillshade(Hf, WORK / 'hillshade.png', extra=drop)
    print(json.dumps(rec['stats'], indent=1))


if __name__ == '__main__':
    main()
