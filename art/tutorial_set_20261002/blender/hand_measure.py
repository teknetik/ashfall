import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
arm,body=load_final('v7')
for s in ('r','l'):
    S='Right' if s=='r' else 'Left'
    h=bone_head(arm,S+'Hand'); m=bone_head(arm,'middle_01_'+s); i=bone_head(arm,'index_01_'+s); p=bone_head(arm,'pinky_01_'+s); t=bone_head(arm,'thumb_01_'+s)
    tail=bone_tail(arm,S+'Hand')
    print('HAND',S,'len %.3f knuckle dist %.3f'%((tail-h).length,(m-h).length),'palm centre along %.3f'%((h.lerp(m,0.55)-h).length), 'index-pinky %.3f'%(i-p).length)
