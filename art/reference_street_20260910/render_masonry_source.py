import bpy
s=bpy.data.scenes['hero-masonry-v1'];bpy.context.window.scene=s
bpy.ops.render.render(write_still=True)
