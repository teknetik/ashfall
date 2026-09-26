"""Live Blender MCP authoring/baking of the focused native-reviewed metal revision.

ACTION='AUTHOR' creates a new scene and copied material graphs from v2. Then
ACTION='BAKE', BAKE_FAMILY='ShutterSteel' or 'AgedSteel' bakes full-resolution
maps under textures-v3. V1/v2 sources, bakes and all Unity assets are untouched.
"""
import bpy, hashlib, json, math, time
from pathlib import Path

ROOT=Path('/home/teknetik/code/ao2');OUT=ROOT/'art/reference_street_20260909'
STUDIO='Reference street metal studio v3';PLANE='Reference four metre metal bake tile v3'
BLEND=OUT/'metal-studio-v3.blend'
ACTION=globals().get('ACTION','AUTHOR');BAKE_FAMILY=globals().get('BAKE_FAMILY','ShutterSteel')


def verified_reload():
    contract=json.loads((OUT/'metal-import-contract.json').read_text())
    source=Path(contract['provenance']['localSource']);rows=[]
    for item in contract['provenance']['inputs']:
        path=source/item['file'];actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual==item['sha256'],'Original disk input changed: '+str(path)
        for image in bpy.data.images:
            if image.source=='FILE'and image.filepath and Path(bpy.path.abspath(image.filepath)).resolve()==path.resolve():image.reload()
        rows.append({'file':str(path),'sha256':actual,'matchesOriginal':True})
    return rows


def author():
    assert not BLEND.exists()and STUDIO not in bpy.data.scenes,'Preserve earlier v3 authoring'
    original=OUT/'metal-studio-v2.blend'
    with bpy.data.libraries.load(str(original),link=False)as (available,loaded):
        # V2's final bake saves only AgedSteel as a scene user. Its common
        # photographic graph is also the base for ShutterSteel; v3 authors the
        # registered shutter edge field explicitly below.
        names=['Reference street AgedSteel']
        assert all(name in available.materials for name in names)
        loaded.materials=names
    sources={family:loaded.materials[0]for family in ['ShutterSteel','AgedSteel']}
    verified=verified_reload()
    scene=bpy.data.scenes.new(STUDIO);bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.cycles.samples=4
    scene.cycles.use_denoising=False;scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='CUDA'
        scene.cycles.device='GPU'if any(d.use for d in prefs.devices)else'CPU'
    except Exception:scene.cycles.device='CPU'
    mesh=bpy.data.meshes.new(PLANE);mesh.from_pydata([(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)],[],[(0,1,2,3)]);mesh.update()
    uv=mesh.uv_layers.new(name='UV0 four metre physical tile')
    for loop,p in zip(mesh.loops,[(0,0),(1,0),(1,1),(0,1)]):uv.data[loop.index].uv=p
    plane=bpy.data.objects.new(PLANE,mesh);scene.collection.objects.link(plane)
    bpy.context.view_layer.objects.active=plane;plane.select_set(True)
    materials={}
    for family,source in sources.items():
        mat=source.copy();mat.name='Reference street '+family+' v3';mat.use_fake_user=True;materials[family]=mat
        nt=mat.node_tree;nodes=nt.nodes;links=nt.links
        def node(kind,name):
            n=nodes.new(kind);n.name=n.label='V3 '+name;return n
        def wire(value,socket):
            if hasattr(value,'node'):links.new(value,socket)
            elif isinstance(value,(float,int))and hasattr(socket.default_value,'__len__'):socket.default_value=[value]*len(socket.default_value)
            else:socket.default_value=value
        def calc(op,a,b=0,name=None):
            n=node('ShaderNodeMath',name or op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs[1]);return n.outputs[0]
        def ramp(value,lo,hi,name):
            n=node('ShaderNodeMapRange',name);n.clamp=True;n.interpolation_type='SMOOTHSTEP'
            n.inputs['From Min'].default_value=lo;n.inputs['From Max'].default_value=hi;wire(value,n.inputs['Value']);return n.outputs['Result']
        def mix(a,b,f,name):
            n=node('ShaderNodeMixRGB',name);wire(f,n.inputs[0]);wire(a,n.inputs[1]);wire(b,n.inputs[2]);return n.outputs[0]
        uvnode=nodes['Existing UV0'];sep=node('ShaderNodeSeparateXYZ','Four metre axes');links.new(uvnode.outputs['UV'],sep.inputs[0])
        angles=[calc('MULTIPLY',sep.outputs[i],math.tau)for i in range(2)]
        ring=[calc('COSINE',angles[0]),calc('SINE',angles[0]),calc('COSINE',angles[1]),calc('SINE',angles[1])]
        def noise(xs,ys,name,detail=3):
            p=node('ShaderNodeCombineXYZ',name+' periodic coordinates')
            for i,s in enumerate([xs,xs,ys]):wire(calc('MULTIPLY',ring[i],s),p.inputs[i])
            n=node('ShaderNodeTexNoise',name);n.noise_dimensions='4D'
            wire(p.outputs[0],n.inputs['Vector']);wire(calc('MULTIPLY',ring[3],ys),n.inputs['W'])
            n.inputs['Scale'].default_value=1;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=.68
            return n.outputs['Fac']
        macro=noise(.8,1.1,'Weather exposure zones',2)
        patches=noise(7.3,10.2,'Connected two to ten centimetre coating losses',2)
        ragged=noise(25,31,'Ragged small failure margins',2)
        fine=noise(56,75,'Fine retained mineral pits',2)
        scratch=noise(3.5,145,'Horizontal handling scuffs',2)
        # Small physically scaled patches have sharp irregular margins, gated
        # into sparse clusters. Macro noise changes where wear occurs; it never
        # becomes a giant orange patch by itself.
        failure_field=calc('ADD',calc('MULTIPLY',patches,.82),calc('MULTIPLY',ragged,.18))
        losses=ramp(failure_field,.568,.633,'Connected coating break edges')
        exposure=ramp(macro,.32,.56,'Patch clusters follow exposure')
        losses=calc('MULTIPLY',losses,calc('ADD',.38,calc('MULTIPLY',exposure,.62)))
        edge=0
        if family=='ShutterSteel':
            metres=calc('MULTIPLY',sep.outputs['Y'],4)
            bottom=calc('PINGPONG',calc('SUBTRACT',metres,.506),.07)
            top=calc('PINGPONG',calc('SUBTRACT',metres,.634),.07)
            distance=calc('MINIMUM',bottom,top)
            lip=calc('SUBTRACT',1,ramp(distance,.003,.023,'Three to twenty three millimetre lip corrosion'))
            edge=calc('MULTIPLY',lip,calc('ADD',.20,calc('MULTIPLY',ramp(patches,.35,.57,'Intermittent lip breaks'),.80)))
        scratches=calc('MULTIPLY',ramp(scratch,.59,.67,'Short worn handling strokes'),ramp(ragged,.36,.58,'Broken scuff coverage'))
        wear=calc('MAXIMUM',losses,edge)
        wear=calc('MAXIMUM',wear,calc('MULTIPLY',scratches,.54))
        # Coating stays substantially darker than v2; wear has its own albedo
        # and roughness rather than using specular glare to suggest damage.
        paint=mix((.011,.017,.018,1),(.033,.040,.037,1),ramp(macro,.27,.73,'Dark charcoal exposure range'),'Dark weathered charcoal coating')
        paint=mix(paint,(.052,.048,.039,1),calc('MULTIPLY',ramp(fine,.41,.70,'Fine settled coating dust'),.20),'Subtle dusty mottling')
        oxide=mix((.074,.027,.009,1),(.26,.113,.035,1),ramp(ragged,.27,.72,'Mineral oxidation range'),'Deep brown and warm rust variation')
        oxide=mix(oxide,nodes['CC0 oxide colour'].outputs['Color'],.25,'Retained photographic oxide variation')
        color=mix(paint,oxide,wear,'Visible connected loss of coating')
        # A soft brown halo at eroded paint margins makes thin edges read at
        # about three metres without increasing the physical patch diameter.
        halo=calc('MULTIPLY',ramp(failure_field,.525,.582,'Thin oxidation margin'),calc('SUBTRACT',1,losses))
        color=mix(color,(.067,.045,.022,1),calc('MULTIPLY',halo,.24),'Oxidation at broken paint margins')
        bare=calc('MULTIPLY',scratches,calc('SUBTRACT',1,wear))
        color=mix(color,(.115,.111,.097,1),calc('MULTIPLY',bare,.38),'Exposed handling abrasions')
        rough=mix((.79,.79,.79,1),(.96,.96,.96,1),wear,'Paint versus porous oxide roughness')
        rough=mix(rough,(.54,.54,.54,1),calc('MULTIPLY',bare,.38),'Smoothed handling wear roughness')
        metal=calc('MULTIPLY',bare,.43)
        height=calc('SUBTRACT',calc('MULTIPLY',fine,.17),calc('MULTIPLY',wear,.58))
        height=calc('ADD',height,calc('MULTIPLY',ragged,.10))
        bump=node('ShaderNodeBump','Thin physical coating and oxide relief');bump.inputs['Distance'].default_value=.003
        wire(height,bump.inputs['Height']);wire(nodes['Restrained retained photographic relief'].outputs[0],bump.inputs['Normal'])
        bs=nodes['Reference street physical metal'];wire(color,bs.inputs['Base Color']);wire(rough,bs.inputs['Roughness']);wire(metal,bs.inputs['Metallic']);wire(bump.outputs['Normal'],bs.inputs['Normal'])
        for name,value in [('BaseColor',color),('Roughness',rough),('Metallic',metal)]:wire(value,nodes['Bake '+name].inputs['Color'])
        emit=node('ShaderNodeEmission','Bake WearMask');wire(wear,emit.inputs['Color']);emit.name='Bake WearMask'
        mat['revision']=3;mat['source']='Copied v2 material; medium-scale wear revised after native review'
    plane.data.materials.clear();plane.data.materials.append(materials['ShutterSteel'])
    record={'revision':3,'sourceBlend':'metal-studio-v2.blend','sourceBlendSha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'outputBlend':BLEND.name,'outputTextures':'textures-v3/<family>', 'verifiedOriginalInputs':verified,
            'physicalTileMetres':4,'changes':['Darker charcoal coating','Sparse connected 2–10 cm loss with irregular margins','Broken 3–23 mm shutter lip corrosion','Localized horizontal scuffs','Separate oxide/paint/abrasion roughness'],
            'uvContract':'Unchanged ShutterSteel physical UV registration and aged-steel-assignment-contract.json material scales',
            'reviewRequired':'Inspect full and 3 m crop bakes, then native sunlight/shade; source masking is not proof of runtime appearance',
            'preservation':'No old source/bake/Unity asset is changed'}
    (OUT/'metal-v3-manifest.json').write_text(json.dumps(record,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print(json.dumps({'studio':STUDIO,'source':str(BLEND),'materials':[m.name for m in materials.values()]}))


def bake(family):
    import numpy as np
    assert family in ['ShutterSteel','AgedSteel']
    scene=bpy.data.scenes[STUDIO];bpy.context.window.scene=scene;plane=scene.objects[PLANE]
    for obj in scene.objects:obj.select_set(False)
    bpy.context.view_layer.objects.active=plane;plane.select_set(True)
    mat=bpy.data.materials['Reference street '+family+' v3'];plane.data.materials.clear();plane.data.materials.append(mat)
    for face in plane.data.polygons:face.material_index=0
    plane.active_material_index=0;assert len(plane.data.materials)==1
    verified=verified_reload();nt=mat.node_tree;output=nt.nodes['Material output'];bs=nt.nodes['Reference street physical metal']
    folder=OUT/'textures-v3'/family;folder.mkdir(parents=True,exist_ok=True)
    channels=['BaseColor','Normal','Roughness','Metallic','WearMask']
    assert all(not (folder/(c+'.png')).exists()for c in channels),'Preserve completed/partial v3 maps'
    record={'revision':3,'family':family,'blender':bpy.app.version_string,'device':scene.cycles.device,'resolution':4096,'materialSlotCount':1,'verifiedOriginalInputs':verified,'maps':[]}
    for channel in channels:
        img=bpy.data.images.new('V3 '+family+' '+channel,4096,4096,alpha=False,float_buffer=False)
        img.colorspace_settings.name='sRGB'if channel=='BaseColor'else'Non-Color'
        target=nt.nodes.new('ShaderNodeTexImage');target.image=img;nt.nodes.active=target
        for n in nt.nodes:n.select=n==target
        value=bs.outputs['BSDF']if channel=='Normal'else nt.nodes['Bake '+channel].outputs[0]
        nt.links.new(value,output.inputs['Surface']);start=time.monotonic()
        bpy.ops.object.bake(type='NORMAL'if channel=='Normal'else'EMIT',normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z',use_clear=True,margin=24)
        path=folder/(channel+'.png');img.filepath_raw=str(path);img.file_format='PNG';img.save()
        row={'channel':channel,'seconds':round(time.monotonic()-start,3),'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if channel=='WearMask':
            pixels=np.empty(4096*4096*4,dtype=np.float32);img.pixels.foreach_get(pixels);mask=pixels[0::4]
            row['maskMean']=float(mask.mean());row['fractionOverHalf']=float((mask>.5).mean());row['fractionOverQuarter']=float((mask>.25).mean())
        record['maps'].append(row);nt.nodes.remove(target);bpy.data.images.remove(img)
    nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    (folder/'bake.json').write_text(json.dumps(record,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print(json.dumps(record))

if ACTION=='AUTHOR':author()
elif ACTION=='BAKE':bake(BAKE_FAMILY)
else:raise ValueError('ACTION must be AUTHOR or BAKE')
