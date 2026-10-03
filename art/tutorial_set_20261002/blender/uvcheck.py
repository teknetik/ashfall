import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
reset()
a=[o for o in import_glb(MESHY/'jumpsuit'/'model.glb') if o.type=='MESH']
b=[o for o in import_glb('/home/teknetik/code/ao2/meshy/main-char-20261002/blender/player_rig_input.glb') if o.type=='MESH']
arm,body=load_body()
for o in a+b+[body]: print('M',o.name,len(o.data.vertices),len(o.data.polygons),len(o.data.loops))
def uvs(o):
    l=o.data.uv_layers.active.data; return sorted((round(x.uv[0],4),round(x.uv[1],4)) for x in l)[::997]
print('UVEQ retex-vs-input',uvs(a[0])==uvs(b[0]),' input-vs-rigged',uvs(b[0])==uvs(body))
