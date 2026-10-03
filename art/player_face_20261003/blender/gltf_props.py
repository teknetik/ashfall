import bpy
for p in bpy.ops.export_scene.gltf.get_rna_type().properties:
    if 'color' in p.identifier.lower() or 'alpha' in p.identifier.lower(): print('PROP', p.identifier, getattr(p,'default',None), [e.identifier for e in getattr(p,'enum_items',[])])
