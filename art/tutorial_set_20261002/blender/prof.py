import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
reset(); arm,body=load_body(); ws=world_verts(body)
for z in [0.95,1.0,1.05,1.1,1.15,1.2,1.25,1.3,1.35,1.4,1.45,1.5]:
    b=[w for w in ws if abs(w.z-z)<0.01 and abs(w.x)<0.05]; t=[w for w in ws if abs(w.z-z)<0.01 and abs(w.y)<0.2]
    print('Z %.2f ymin %.3f ymax %.3f | xhalf %.3f'%(z,min(w.y for w in b),max(w.y for w in b),max(abs(w.x) for w in t if abs(w.x)<0.25)))
