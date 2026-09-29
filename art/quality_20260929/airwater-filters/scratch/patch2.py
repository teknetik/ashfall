import re
s = open('build_aw.py').read()
s = s.replace("def crust(p, pos, axis, r, h, seed, mat='Mineral', amp=.25):", "def crust(p, pos, axis, r, h, seed, mat='Mineral', amp=.25, th=1.0):")
s = s.replace("p.lathe([(r + .0008, 0), (r + .006, .12 * h), (r + .011, .45 * h), (r + .009, .75 * h), (r + .0008, h)], mat, .3, pos=pos, axis=axis, segs=26, warp=wp)",
              "p.lathe([(r + .0008, 0), (r + .006 * th, .12 * h), (r + .011 * th, .45 * h), (r + .009 * th, .75 * h), (r + .0008, h)], mat, .3, pos=pos, axis=axis, segs=26, warp=wp)")
# flange / big-radius crusts: thin
s = s.replace("crust(p, (2.655, HY, HZ), (1, 0, 0), .055, .010, 60, amp=.25)", "crust(p, (2.6535, HY, HZ), (1, 0, 0), .0545, .008, 60, amp=.2, th=.3)")
s = s.replace("crust(p, (2.885, HY, HZ), (1, 0, 0), .055, .010, 61, amp=.3)", "crust(p, (2.860, HY, HZ), (1, 0, 0), .0545, .008, 61, amp=.2, th=.3)")
s = s.replace("crust(p, (cx, 1.990, cz), (0, 1, 0), .0525, .016, 30 + i, amp=.3)", "crust(p, (cx, 1.996, cz), (0, 1, 0), .0525, .012, 30 + i, amp=.2, th=.3)")
s = s.replace("crust(p, (RX, 2.905, RZ), (0, 1, 0), .040, .040, 71, amp=.35)", "crust(p, (RX, 2.905, RZ), (0, 1, 0), .040, .036, 71, amp=.35)")
open('build_aw.py', 'w').write(s)
