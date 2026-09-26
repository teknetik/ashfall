"""Apply reviewed canvas finish, repeat rig checks, then schedule final renders via MCP."""
import bpy,importlib,sys
from pathlib import Path
OUT=Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
sys.path.insert(0,str(OUT))
import artisan_materials
importlib.reload(artisan_materials)
artisan_materials.create_canvas_materials()
bpy.context.view_layer.update()
exec(compile((OUT/'add_rafter_hangers.py').read_text(),str(OUT/'add_rafter_hangers.py'),'exec'),globals())
exec(compile((OUT/'refine_and_check.py').read_text(),str(OUT/'refine_and_check.py'),'exec'),globals())
exec(compile((OUT/'render_reviews.py').read_text(),str(OUT/'render_reviews.py'),'exec'),globals())
