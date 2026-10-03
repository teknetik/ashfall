import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT/'fit'/'bootplates.blend'))
render_views(str(OUT/'fit'/'bootclose'),(-0.17,-0.03,0.1),0.32,views=('front','rside','quarter','rquarter'),res=(450,450))
