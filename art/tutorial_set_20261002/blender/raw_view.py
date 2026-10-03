import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
name=sys.argv[sys.argv.index('--')+1]
reset(); p=import_piece(MESHY/name/'model.glb',name)
lo,hi=bounds(p); print('RAWSIZE',name,[round(x,3) for x in hi-lo], len(p.data.polygons))
render_views(str(OUT/'raw'/name),(0,0,0),max(hi-lo)*1.1,views=('front','side','top'),res=(500,500))
