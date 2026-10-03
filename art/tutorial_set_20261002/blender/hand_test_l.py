import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
import math
arm,body=load_final()
for pb in arm.pose.bones:
    for k,a in {'01':55,'02':70,'03':45}.items():
        if pb.name.endswith('_'+k+'_l') or pb.name.endswith('_'+k+'_r'):
            pb.rotation_mode='XYZ'; pb.rotation_euler=(math.radians(a*(0.4 if pb.name.startswith('thumb') else 1)),0,0)
bpy.context.view_layer.update()
for s,v in (('Left','side'),('Right','rside')):
    h=arm.matrix_world@arm.data.bones[s+'Hand'].head_local
    render_views(str(OUT/'mpfb'/('handcurl_'+s)),(h.x,h.y-0.03,h.z-0.06),0.25,views=('front',v),res=(350,350))
