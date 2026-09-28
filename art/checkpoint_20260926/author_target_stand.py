import bpy,math
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2');k={};src=(ROOT/'art/ward_retrofit_20260926/kit.py').read_text().replace("nt.nodes['Principled BSDF']","next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')").replace("m.node_tree.nodes['Principled BSDF']","next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')");src=src[:src.index('M = {')]+src[src.index('# ---------------------------------------------------------------- mesh primitives'):];exec(compile(src,'ward-kit','exec'),k);k['M']={'rust':k['ph']('TargetRust','rusty_metal_04',metal=.45),'steel':k['flat']('TargetSteel',(.32,.33,.34),rough=.5,metal=.8),'plate_olive':k['ph']('TargetOlive','green_metal_rust',metal=.4),'panel':k['flat']('TargetNumberBacking',(.065,.075,.075))}
col=k['new_collection']('Steel target stand source');k['CUR']['coll']=col;M=k['M'];box=k['box'];span=k['span'];cyl=k['cyl']
for x in [-.40,.40]:
 box('Steel channel foot',(.15,.9,.07),M['rust'],loc=(x,0,.04),bevel=.008)
 for y in [-.39,.39]:box('Anchored end shoe',(.23,.17,.04),M['steel'],loc=(x,y,.03),bevel=.01)
 for y in [-.34,.34]:
  span('Triangulated leg',(x,y,.08),(x,0,.45),.06,.06,M['steel'])
  cyl('Anchor bolt',.025,.05,M['steel'],loc=(x,y,.10),sides=12)
box('Hinge crossbeam',(.98,.09,.09),M['plate_olive'],loc=(0,0,.45))
cyl('Steel hinge shaft',.045,1.08,M['steel'],loc=(-.54,0,.47),rot=(0,math.pi/2,0),sides=20)
box('Target number backing',(.37,.04,.18),M['panel'],loc=(0,.16,.27))
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/SteelTargetStand.glb'),export_format='GLB',use_selection=True,export_yup=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/checkpoint_20260926/target-stand-source.blend'))
print('Triangulated steel stand exported')
