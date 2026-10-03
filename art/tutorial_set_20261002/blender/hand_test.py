import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
import math
arm,body=load_final('v7')
CURL={'01':12,'02':22,'03':16}
for pb in arm.pose.bones:
    n=pb.name
    for k,a in CURL.items():
        if n.endswith('_'+k+'_r') or n.endswith('_'+k+'_l'):
            if n.startswith('thumb'): a*=0.5
            pb.rotation_mode='XYZ'; pb.rotation_euler=(math.radians(a),0,0)
bpy.context.view_layer.update()
h=arm.matrix_world@arm.data.bones['RightHand'].head_local
for ax in ['X']:
    render_views(str(OUT/'mpfb'/'hand_curlX'),(h.x-0.06,h.y-0.03,h.z-0.06),0.28,views=('front','rside','top'),res=(400,400))
