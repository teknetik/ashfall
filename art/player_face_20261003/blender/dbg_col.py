import bpy
bpy.ops.wm.open_mainfile(filepath="/home/teknetik/code/ao2/art/tutorial_set_20261002/blender/mpfb/final_m0.25.blend")
o=bpy.data.objects['char1']; me=o.data
print('ATTRS', [(a.name,a.data_type,a.domain) for a in me.color_attributes], 'active', me.color_attributes.active_color_name if hasattr(me.color_attributes,'active_color_name') else None)
ca=me.color_attributes['Col']
al=[d.color[3] for d in ca.data]
print('ALPHA', min(al), max(al), sum(1 for a in al if a<0.99))
