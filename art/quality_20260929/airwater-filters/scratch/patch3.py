s = open('make_clearance_diagram.py').read()
s = s.replace("P.label(-3.55, 2.60, 'front wall (collider face z 2.70, plaster z 2.73)', 12)", "P.label(.6, 2.62, 'front wall (collider face z 2.70, plaster z 2.73)', 12)")
a = "P.label(-2.4, 3.22, 'DOOR (service entry): reveal x -2.45..-0.15, threshold to z 3.14', 13)\n"
s = s.replace(a, "")
s = s.replace("P.label(-2.05, 3.5, 'door approach zone", a.replace('-2.4, 3.22', '-2.4, 3.30') + "P.label(-2.05, 3.5, 'door approach zone")
s = s.replace("E.rect(3.14, 2.09, .08, 4.0, '#d78a4e', '#000', .6)", "E.rect(3.14, 2.09, .08, 1.5, '#d78a4e', '#000', .6); E.label(3.3, 3.45, 'riser continues to roof (y 7.08)', 12)")
s = s.replace("P.label(-2.05, 3.66,", "P.label(-2.4, 3.66,").replace("P.label(-2.05, 3.5, 'door approach", "P.label(-2.4, 3.48, 'door approach")
s = s.replace("P.label(.6, 3.42, 'new work", "P.label(.6, 3.50, 'new work")
open('make_clearance_diagram.py', 'w').write(s)
