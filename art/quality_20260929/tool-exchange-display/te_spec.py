"""Shared layout spec for the Tool Exchange display vignette (29 Sep 2026, task t_3751e0fd).

Used by BOTH the texture script (painted shadow-board outlines) and the geometry script, so the outlines painted on the
board register with the 3D tools that hang in front of them.

Frame ("A-space"): building-local metres, +X = screen-right from the avenue, +Y up, +Z towards the avenue. Origin = building
pivot (Unity 8?/-, see handoff.json), Y = 0 is porch/floor level. Same convention as the Basic General package.
Tool-local 2D frame: x along the tool (handle end -> working end), y across, z out of the board.
"""
import math

# ---- existing Tool Exchange revision 04 measurements (read from source.blend, A-space) -----------------------------
OPENING = dict(x0=-2.90, x1=-1.40, y0=0.78, y1=2.20)            # dressed opening between the reveals
WALL_REAR_Z = 2.45                                               # rear face of the front masonry
GLASS = dict(z0=2.543, z1=2.577, y0=0.83, y1=2.15, panes=[(-2.868, -2.183), (-2.118, -1.433)])
# new display alcove, built inside the closed shell BEHIND the wall (no interior gameplay)
BOARD = dict(x0=-2.90, x1=-1.40, y0=0.78, y1=2.20, zb=2.030, zf=2.042)     # perforated tool board, 12 mm thick
PPM = 2048.0                                                     # unique board map: 2048 px per metre
BOARD_W = BOARD['x1'] - BOARD['x0']
BOARD_H = BOARD['y1'] - BOARD['y0']
HOLE_PITCH, HOLE_D = 0.025, 0.0065

RAIL_Y = 1.955                                                   # timber peg rail centre height


def rot(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def place(poly, origin, deg):
    out = []
    for p in poly:
        q = rot(p, deg)
        out.append((q[0] + origin[0], q[1] + origin[1]))
    return out


# ---- silhouettes (metres, tool-local) ------------------------------------------------------------------------------
PIPE_WRENCH = [[(0, -.0135), (.30, -.0175), (.335, -.026), (.36, -.048), (.415, -.050), (.452, -.038), (.458, -.018), (.452, -.004),
                (.425, -.008), (.405, .010), (.385, .020), (.392, .048), (.372, .062), (.345, .056), (.335, .030), (.30, .0175), (0, .0135)]]
HAMMER = [[(0, -.0125), (.30, -.0135), (.30, .0135), (0, .0125)],
          [(.238, -.038), (.245, -.050), (.290, -.050), (.297, -.038), (.297, .038), (.290, .050), (.245, .050), (.238, .038)]]
CUTTERS = [[(0, .046), (0, .022), (.42, .006), (.42, .030)],
           [(0, -.046), (0, -.022), (.42, -.006), (.42, -.030)],
           [(.40, -.034), (.47, -.036), (.55, -.030), (.60, -.016), (.60, .016), (.55, .030), (.47, .036), (.40, .034)]]
SAW = [[(0, -.030), (.02, -.045), (.11, -.050), (.14, -.040), (.14, .055), (.11, .060), (.02, .050), (0, .030)],
       [(.14, -.040), (.64, -.020), (.64, .005), (.14, .058)]]

# placement on the board: origin = handle end (x, y in A-space metres), deg = rotation of the tool-local +x axis
# Board coordinates are metres in A-space; mullion centre is at x = -2.135, jamb reveals at -2.90 and -1.40.
PLACEMENT = {
    'PipeWrench': dict(polys=PIPE_WRENCH, origin=(-2.660, 1.925), deg=-88.0, drawn=True),
    'Handsaw':    dict(polys=SAW,         origin=(-2.360, 1.930), deg=-90.5, drawn=False),      # borrowed: outline only + tag
    'LumpHammer': dict(polys=HAMMER,      origin=(-2.020, 1.695), deg=1.5,   drawn=True),
    'BoltCutters': dict(polys=CUTTERS,    origin=(-2.075, 1.325), deg=-1.0,  drawn=True),
}
OUTLINE_GAP = 0.005        # painted outline stands 5 mm off the tool
OUTLINE_W = 0.0085         # and is 8.5 mm wide

# small board furniture (pegs), A-space x,y of the peg root (all project 55 mm from the board face)
PEGS = {
    'wrench_loop':  (-2.660, RAIL_Y - 0.0),       # on the rail
    'saw_loop':     (-2.360, RAIL_Y - 0.0),       # on the rail; carries the repair tag of the missing saw
    'spare_a':      (-1.780, RAIL_Y - 0.0),
    'spare_b':      (-1.560, RAIL_Y - 0.0),
}

BENCH = dict(y=0.962, z0=2.060, z1=2.420, x0=-2.90, x1=-1.40, thick=0.032)


if __name__ == '__main__':
    for k, v in PLACEMENT.items():
        xs = [p[0] for poly in v['polys'] for p in place(poly, v['origin'], v['deg'])]
        ys = [p[1] for poly in v['polys'] for p in place(poly, v['origin'], v['deg'])]
        print(k, 'x %.3f..%.3f  y %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys)))
