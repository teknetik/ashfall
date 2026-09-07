"""Assign generated source textures without changing their pixels."""
files={'stone':'stone_paving_albedo.png','metal':'gunmetal_trim_albedo.png',
       'bark':'ancient_bark_albedo.png','leaf':'olive_foliage_atlas.png',
       'red':'free_column_canvas_albedo.png','cyan':'cyan_hologlass_atlas.png'}
for key,name in files.items():
    path=ROOT/'public/assets/textures'/name
    if not path.exists():continue
    mat=MATS[key];tree=mat.node_tree;bs=tree.nodes.get('Principled BSDF')
    tex=tree.nodes.get('SOURCE_albedo') or tree.nodes.new('ShaderNodeTexImage');tex.name='SOURCE_albedo'
    tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.colorspace_settings.name='sRGB'
    tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    if key=='leaf':
        tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
        mat.use_backface_culling=False;mat.surface_render_method='DITHERED';mat['alphaTest']=.35
    if key=='cyan':tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color'])

# Each card selects one atlas spray; coordinates convert top-left raster to UV.
leaf=bpy.data.objects.get('TREE_leaf_sprays')
if leaf and not leaf.get('atlasAssigned'):
    rects=[(0,0,704,624),(704,0,1254,624),(0,624,640,1254),(640,624,1254,1254)]
    uv=leaf.data.uv_layers.active
    for i,p in enumerate(leaf.data.polygons):
        x0,y0,x1,y1=rects[i%4];u0=x0/1254;u1=x1/1254;v0=1-y1/1254;v1=1-y0/1254
        # Existing four leaf vertices form a plane; remap to a rectangular spray.
        vs=[leaf.data.vertices[j] for j in p.vertices];c=sum((v.co for v in vs),Vector())/4
        a=vs[2].co-c;b=vs[1].co-c
        for v,co in zip(vs,[c-a-b,c+a-b,c+a+b,c-a+b]):v.co=co
        for li,coords in zip(p.loop_indices,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]):uv.data[li].uv=coords
    leaf['atlasAssigned']=True;leaf.data.update()
print('Generated materials assigned; source PNGs unchanged')
