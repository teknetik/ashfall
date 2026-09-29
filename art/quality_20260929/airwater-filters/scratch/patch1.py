s = open('build_aw.py').read()
a = s.index("def crust(")
b = s.index("def stalactite(")
new_crust = '''def crust(p, pos, axis, r, h, seed, mat='Mineral', amp=.25):
    """Hard-water crust at a joint: lumpy lathe, thickest in the middle.  On horizontal joints it is weighted to the underside (water runs down
    and dries there); the upper half sinks inside the fitting so nothing reads as a floating fin."""
    ph = seed * 1.7
    ax = Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < .9 else Vector((1, 0, 0))
    e1 = ax.cross(ref).normalized(); e2 = ax.cross(e1).normalized()
    horiz = abs(ax.y) < .5
    sink = (r - .004) / (r + .011)

    def wp(a, hh):
        lump = 1 + amp * math.sin(3 * a + ph + hh * 70) * math.cos(2 * a - ph * .7 - hh * 55)
        if not horiz:
            return lump
        dy = math.cos(a) * e1.y + math.sin(a) * e2.y          # +1 top, -1 underside
        w = min(1.0, max(0.0, (dy + .1) / .5))                # 0 below the horizon .. 1 on top
        return lump * (1 - w * (1 - sink))
    p.lathe([(r + .0008, 0), (r + .006, .12 * h), (r + .011, .45 * h), (r + .009, .75 * h), (r + .0008, h)], mat, .3, pos=pos, axis=axis, segs=26, warp=wp)


'''
s = s[:a] + new_crust + s[b:]
# mineral runs: wider, thicker, browner-looking short streaks
s = s.replace("sec = [(-.5, -.0009), (.5, -.0009), (.5, .0009), (-.5, .0009)]", "sec = [(-.5, -.0013), (.5, -.0013), (.5, .0013), (-.5, .0013)]")
s = s.replace("scale_fn=lambda t: (w0 + (w1 - w0) * t) * (1 + .35 * math.sin(t * 19 + seed)) * (1 - t ** 4 * .6))",
              "scale_fn=lambda t: 2.4 * (w0 + (w1 - w0) * t) * (1 + .35 * math.sin(t * 19 + seed)) * (1 - t ** 3 * .75))")
s = s.replace("1.965, 1.55, .010, .006, 1.0", "1.965, 1.72, .010, .006, 1.0").replace("1.965, 1.72, .008, .004, 2.0", "1.965, 1.80, .008, .004, 2.0")
s = s.replace("1.965, 1.40, .012, .006, 3.0", "1.965, 1.70, .012, .006, 3.0").replace("1.965, 1.35, .010, .005, 4.0", "1.965, 1.75, .010, .005, 4.0").replace("1.965, 1.68, .007, .004, 5.0", "1.965, 1.82, .007, .004, 5.0")
open('build_aw.py', 'w').write(s)
