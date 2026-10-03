import sys, bpy; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
import importlib
mp = importlib.import_module('bl_ext.user_default.mpfb.services.humanservice'); HumanService = mp.HumanService
reset_keep = bpy.ops.wm.read_factory_settings  # MPFB stays registered as an extension
bpy.ops.wm.read_homefile(use_empty=True)
macro = {"gender": 1.0, "age": 0.5, "muscle": 0.9, "weight": 0.62, "proportions": 0.85, "height": 0.86, "cupsize": 0.5,
         "firmness": 0.5, "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}}
bm = HumanService.create_human(macro_detail_dict=macro, scale=0.1)
lo, hi = eval_bounds(bm); print('BASE height %.3f' % (hi - lo).z, len(bm.data.vertices))
rig = HumanService.add_builtin_rig(bm, 'game_engine')
print('RIG', rig.name, len(rig.data.bones))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'mpfb' / 'base_v2.blend'))
render_views(str(OUT / 'mpfb' / 'base_v2'), (0, 0, (hi - lo).z / 2), (hi - lo).z * 1.05, views=('front', 'side', 'back'), res=(450, 900))
