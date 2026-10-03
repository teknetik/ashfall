"""Render one final_*.blend at rest and at idle frame 40 (side + front) for the rest-match comparison.
Usage: blender_mpfb.sh restcmp.py -- BLEND OUTPREFIX"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if rig.animation_data:
    for t in rig.animation_data.nla_tracks: t.mute = True
    rig.animation_data.action = None
render_views(a[1] + '_rest', (0, 0, 0.95), 1.95, views=('side', 'front'), res=(450, 900))
if rig.animation_data and 'idle' in bpy.data.actions:
    rig.animation_data.action = bpy.data.actions['idle']; bpy.context.scene.frame_set(40)
    render_views(a[1] + '_idle', (0, 0, 0.95), 1.95, views=('side', 'front'), res=(450, 900))
