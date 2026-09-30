"""Authored nanite-core canister for the salvage cache (Blender 5.2, bmesh), in final metres.

Replaces Meshy's fused, lumpy canister so the rarity glow is its own renderer/material:
  * hardware - socket sleeve with a painted clamp band, glass lip rings, knurled top cap, valve boss, cap bolts
               and four guard bars (steel; joins the Body renderer as material slot 1, no emission)
  * core     - the glass / nanite-fluid column (own renderer; SalvageCache tints its _EmissionColor)
Coordinates: canister axis is +Z through the object origin; z values are the final height above the cache pivot
(ground contact), so procedural masks can use object-space z directly. The sleeve bottom is buried in the tray.
"""
import bmesh, math

Z_SLEEVE0 = 0.105      # hidden inside the tray
RIM = 0.207            # tray wall top next to the canister (measured on the Meshy body after normalising)
GLASS_Z0, GLASS_Z1, GLASS_R = 0.2135, 0.3325, 0.0402
FILL_Z = 0.3125        # nanite fluid level (emission mask)
KNURL_Z0, KNURL_Z1 = 0.3465, 0.3695
BAND_Z0, BAND_Z1 = 0.1745, 0.1955  # painted clamp band on the sleeve
TOP_Z = 0.393

# (radius, z) lathe profiles, bottom to top
SLEEVE = [(0.0, Z_SLEEVE0), (0.0520, Z_SLEEVE0), (0.0540, Z_SLEEVE0 + 0.003), (0.0540, 0.1725), (0.0560, 0.1745),
          (0.0572, 0.1760), (0.0572, 0.1940), (0.0560, 0.1955), (0.0540, 0.1975), (0.0540, 0.2040),
          (0.0512, 0.2085), (0.0470, 0.2090), (0.0462, 0.2100), (0.0462, 0.2160), (0.0440, 0.2175),
          (0.0400, 0.2175), (0.0, 0.2175)]
CAP = [(0.0, 0.3285), (0.0400, 0.3285), (0.0440, 0.3285), (0.0462, 0.3300), (0.0462, 0.3365), (0.0490, 0.3375),
       (0.0528, 0.3405), (0.0528, 0.3445), (0.0512, 0.3460), (0.0518, 0.3465), (0.0518, 0.3695), (0.0512, 0.3700),
       (0.0528, 0.3715), (0.0528, 0.3745), (0.0495, 0.3780), (0.0228, 0.3780), (0.0212, 0.3790),
       (0.0212, 0.3850), (0.0198, 0.3862), (0.0085, 0.3862), (0.0085, 0.3920), (0.0078, TOP_Z), (0.0, TOP_Z)]
CORE = [(0.0, GLASS_Z0), (GLASS_R, GLASS_Z0), (GLASS_R, GLASS_Z1), (0.0, GLASS_Z1)]
BAR_R, BAR_RING, BAR_Z0, BAR_Z1 = 0.0040, 0.0474, 0.2000, 0.3420
BOLT_RING, BOLT_R, BOLT_H = 0.0355, 0.0042, 0.0032


def lathe(bm, profile, segs, phase=0.0):
    rings = []
    for i in range(segs):
        a = phase + 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z)) for r, z in profile])
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for j in range(len(profile) - 1):
            try:
                bm.faces.new([a[j], b[j], b[j + 1], a[j + 1]])
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=[v for r in rings for v in r], dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-8)


def prism(bm, x, y, r, z0, z1, segs, cap_top=False, phase=0.0):
    lo = [bm.verts.new((x + r * math.cos(phase + 2 * math.pi * i / segs), y + r * math.sin(phase + 2 * math.pi * i / segs), z0)) for i in range(segs)]
    hi = [bm.verts.new((x + r * math.cos(phase + 2 * math.pi * i / segs), y + r * math.sin(phase + 2 * math.pi * i / segs), z1)) for i in range(segs)]
    for i in range(segs):
        bm.faces.new([lo[i], lo[(i + 1) % segs], hi[(i + 1) % segs], hi[i]])
    if cap_top:
        bm.faces.new(hi)


def build(bm_hw, bm_core, segs=48, bar_segs=10, bolts=True):
    lathe(bm_hw, SLEEVE, segs)
    lathe(bm_hw, CAP, segs)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        prism(bm_hw, BAR_RING * math.cos(a), BAR_RING * math.sin(a), BAR_R, BAR_Z0, BAR_Z1, bar_segs)
    if bolts:
        for k in range(4):
            a = math.radians(90 * k)
            prism(bm_hw, BOLT_RING * math.cos(a), BOLT_RING * math.sin(a), BOLT_R, 0.3775, 0.3780 + BOLT_H, 6,
                  cap_top=True, phase=math.radians(30) + a)
    lathe(bm_core, CORE, segs)
    for bm in (bm_hw, bm_core):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
