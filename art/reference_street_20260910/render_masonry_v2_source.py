import bpy
bpy.context.window.scene=bpy.data.scenes['hero-masonry-v2']
bpy.ops.render.render(write_still=True)
