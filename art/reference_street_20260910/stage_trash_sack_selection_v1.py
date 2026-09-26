"""STAGED live-Blender candidate selection only. No masks/FBX/Unity exports.
Exclusive operator sets TRASH_SELECTION_REVISION='selection-v1' and
RUN_TRASH_SACK_SELECTION=True. Fresh scene/import and output folder only.
The face classes remain provisional until all coverage views are reviewed.
"""
from pathlib import Path
from collections import defaultdict
import datetime, hashlib, json, struct, zlib
import numpy as np
import bpy
from mathutils import Vector

ROOT=Path('/home/teknetik/code/ao2')
HERE=ROOT/'art/reference_street_20260910/trash-cloth-v3-plan'
CONTOUR=HERE/'selection-contours-v1.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def read_raw_fbx(path):
    """Read the guarded source arrays without relying on unstable imported face IDs."""
    b=path.read_bytes();assert b[:23]==b'Kaydara FBX Binary  \x00\x1a\x00'
    version=struct.unpack_from('<I',b,23)[0];wide=version>=7500
    def prop(pos):
        t=chr(b[pos]);pos+=1
        if t in 'YCFDIL':
            fmt={'Y':'h','C':'?','F':'f','D':'d','I':'i','L':'q'}[t]
            return struct.unpack_from('<'+fmt,b,pos)[0],pos+struct.calcsize(fmt)
        if t in 'fdilcb':
            n,encoding,size=struct.unpack_from('<III',b,pos);pos+=12
            assert encoding in (0,1);data=b[pos:pos+size];data=zlib.decompress(data) if encoding else data
            a=np.frombuffer(data,dtype={'f':'<f4','d':'<f8','i':'<i4','l':'<i8','c':'u1','b':'u1'}[t]);assert len(a)==n
            return a,pos+size
        if t in 'RS':
            n=struct.unpack_from('<I',b,pos)[0];pos+=4;v=b[pos:pos+n]
            return v.decode('utf8','replace') if t=='S' else v,pos+n
        raise ValueError('Unexpected FBX property '+t)
    def node(pos):
        fmt='<QQQB' if wide else '<IIIB';end,count,size,length=struct.unpack_from(fmt,b,pos);pos+=struct.calcsize(fmt)
        if end==0:return None,pos
        name=b[pos:pos+length].decode();pos+=length;props=[];children=[]
        for _ in range(count):v,pos=prop(pos);props.append(v)
        while pos<end:
            child,pos=node(pos)
            if child is None:break
            children.append(child)
        assert pos==end
        return {'name':name,'props':props,'children':children},end
    nodes=[];pos=27
    while True:
        n,pos=node(pos)
        if n is None:break
        nodes.append(n)
    find=lambda ns,name:[n for n in ns if n['name']==name]
    objects=find(nodes,'Objects')[0]['children'];geometries=find(objects,'Geometry');assert len(geometries)==1
    g=geometries[0]['children'];vertices=find(g,'Vertices')[0]['props'][0].reshape(-1,3)
    ends=find(g,'PolygonVertexIndex')[0]['props'][0];assert np.array_equal(np.flatnonzero(ends<0),np.arange(2,len(ends),3))
    faces=np.where(ends<0,-ends-1,ends).reshape(-1,3)
    layers=find(g,'LayerElementUV');assert len(layers)==1;uvnode=layers[0]['children']
    assert find(uvnode,'MappingInformationType')[0]['props'][0]=='ByPolygonVertex'
    assert find(uvnode,'ReferenceInformationType')[0]['props'][0]=='IndexToDirect'
    uv=find(uvnode,'UV')[0]['props'][0].reshape(-1,2);ui=find(uvnode,'UVIndex')[0]['props'][0].reshape(-1,3)
    return vertices,faces,uv[ui]


def projected(points,projection):
    a,b,_=projection['axes'];s=projection['scale'];c=projection['centre'];half=projection['size']/2
    return np.stack(((points[...,a]-c[a])*s+half,half-(points[...,b]-c[b])*s),axis=-1)


def inside(points,polygon):
    x=points[...,0];y=points[...,1];answer=np.zeros(x.shape,bool)
    poly=np.asarray(polygon,float)
    for i in range(len(poly)):
        x1,y1=poly[i];x2,y2=poly[(i+1)%len(poly)]
        if y1==y2:continue
        answer^=((y1>y)!=(y2>y))&(x<(x2-x1)*(y-y1)/(y2-y1)+x1)
    return answer


def classify(raw_vertices,raw_faces,contours,projections):
    v=raw_vertices[raw_faces]
    samples=np.concatenate((v,(v[:,0:1]+v[:,1:2])/2,(v[:,1:2]+v[:,2:3])/2,(v[:,2:3]+v[:,0:1])/2,v.mean(1,keepdims=True)),axis=1)
    q={name:projected(samples,p) for name,p in projections.items()}
    excluded=np.zeros(samples.shape[:2],bool)
    for ex in contours['exclusions']:excluded|=inside(q['top'],ex['top'])
    eligible={};uncertain={}
    for name,row in contours['sacks'].items():
        coverage=np.ones(samples.shape[:2],bool)
        for view in ('top','front','side'):coverage&=inside(q[view],row[view])
        eligible[name]=coverage.all(1)&~excluded.any(1)
        uncertain[name]=coverage[:,-1]&~excluded.any(1)&~eligible[name]
    assert not (eligible['left']&eligible['central']).any(), 'Sack candidate volumes overlap'
    return eligible,uncertain


def mesh_digest(mesh):
    """Geometry/UV/corner-normal identity; selection and diagnostic materials excluded."""
    h=hashlib.sha256()
    def feed(collection,property,width,dtype):
        a=np.empty(len(collection)*width,dtype=dtype);collection.foreach_get(property,a);h.update(a.tobytes())
    feed(mesh.vertices,'co',3,np.float32);feed(mesh.loops,'vertex_index',1,np.int32)
    feed(mesh.polygons,'loop_start',1,np.int32);feed(mesh.polygons,'loop_total',1,np.int32)
    for uv in mesh.uv_layers:feed(uv.data,'uv',2,np.float32)
    assert len(mesh.corner_normals)==len(mesh.loops), 'Corner normal array unavailable'
    feed(mesh.corner_normals,'vector',3,np.float32)
    return h.hexdigest()


def correspondence(ob,raw_vertices,raw_faces,raw_uv):
    mesh=ob.data;assert len(mesh.vertices)==86482 and len(mesh.polygons)==179965 and len(mesh.uv_layers)==1
    assert all(p.loop_total==3 for p in mesh.polygons)
    p=np.array([ob.matrix_world@v.co for v in mesh.vertices],np.float64)
    expected=raw_vertices[:,[0,2,1]].copy();expected[:,1]*=-1
    error=float(np.max(np.abs(p-expected)));assert error<3e-6, 'FBX vertex order/world axis transform differs; do not use retained projection contours'
    raw_by_set=defaultdict(list)
    for i,f in enumerate(raw_faces):raw_by_set[tuple(sorted(map(int,f)))].append(i)
    duplicate_groups=[ids for ids in raw_by_set.values() if len(ids)>1]
    assert len(raw_faces)==180000 and len(raw_by_set)==179965 and len(duplicate_groups)==35 and all(len(ids)==2 for ids in duplicate_groups)
    uv=mesh.uv_layers[0];mapping=[];seen=set();duplicates=[];max_uv_error=0
    for poly in mesh.polygons:
        f=tuple(poly.vertices);key=tuple(sorted(f));assert key not in seen and key in raw_by_set;seen.add(key)
        imported_uv=np.array([uv.data[i].uv[:] for i in poly.loop_indices]);matches=[]
        for raw_id in raw_by_set[key]:
            for shift in range(3):
                ids=np.roll(raw_faces[raw_id],shift)
                if np.array_equal(ids,f):
                    error_uv=float(np.max(np.abs(np.roll(raw_uv[raw_id],shift,axis=0)-imported_uv)))
                    if error_uv<2e-6:matches.append((raw_id,error_uv))
        assert len(matches)==1, 'Imported polygon winding/UV does not match exactly one source triangle'
        raw_id,error_uv=matches[0];mapping.append(raw_id);max_uv_error=max(max_uv_error,error_uv)
        if len(raw_by_set[key])==2:duplicates.append({'importedPolygon':poly.index,'retainedRawPolygon':raw_id,'otherRawPolygon':next(i for i in raw_by_set[key] if i!=raw_id)})
    assert len(seen)==len(raw_by_set)
    return np.asarray(mapping,np.int32),{'maxWorldVertexError':error,'maxCornerUVError':max_uv_error,'rawTriangles':180000,'importedTriangles':179965,'oppositeWindingUVAlternatives':duplicates,'completeUniqueTriangleSetPreserved':True}


def make_material(name,color=None,base_image=None):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.72
    if color is not None:bs.inputs['Base Color'].default_value=color
    else:
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=base_image;mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
    return mat


def run():
    revision=globals().get('TRASH_SELECTION_REVISION');assert revision and all(c.isalnum() or c in '-_' for c in revision)
    out=HERE/revision;assert not out.exists(), 'Fresh candidate output required'
    contours=json.loads(CONTOUR.read_text());source=ROOT/contours['source'];assert sha(source)==contours['sourceSha256']
    projections={}
    for name,row in contours['projections'].items():
        p=HERE/row['file'];assert sha(p)==row['sha256'] and sha(HERE/row['image'])==row['imageSha256'];projections[name]=json.loads(p.read_text())
    raw_vertices,raw_faces,raw_uv=read_raw_fbx(source)
    eligible,uncertain=classify(raw_vertices,raw_faces,contours,projections)
    seeds=json.loads((HERE/'diagnostics/semantic-seeds.json').read_text())
    for seed in seeds:
        i=seed['fbxPolygonIndex']
        if 'exclusion' in seed['label']:assert not any(m[i] for m in eligible.values()) and not any(m[i] for m in uncertain.values())
        else:assert eligible['left' if 'left' in seed['label'] else 'central'][i], 'Known sack seed missing; inspect contour changes'
    previous=bpy.context.window.scene;scene=bpy.data.scenes.new('Trash sack candidate '+revision);bpy.context.window.scene=scene
    out.mkdir()
    try:
        before=set(scene.objects);bpy.ops.import_scene.fbx(filepath=str(source),use_image_search=False,use_custom_normals=True)
        imported=[o for o in scene.objects if o not in before];meshes=[o for o in imported if o.type=='MESH'];assert len(meshes)==1
        ob=meshes[0];mesh=ob.data;mapping,corr=correspondence(ob,raw_vertices,raw_faces,raw_uv);before_hash=mesh_digest(mesh)
        original_materials=[m.name if m else None for m in mesh.materials];original_indices=[p.material_index for p in mesh.polygons]
        selection={name:mask[mapping] for name,mask in eligible.items()};boundary={name:mask[mapping] for name,mask in uncertain.items()}
        # Store FACE-domain candidate labels only. These are not a UV texture mask.
        for name,mask in selection.items():
            attr=mesh.attributes.new('candidate_'+name+'_sack','BOOLEAN','FACE');attr.data.foreach_set('value',mask)
        base_path=source.parent/'model_textures/base_color.png';base_image=bpy.data.images.load(str(base_path),check_existing=False);base_image.colorspace_settings.name='sRGB'
        mats=[make_material(revision+' source albedo',base_image=base_image),make_material(revision+' LEFT candidate',contours['coverageColors']['left']),make_material(revision+' CENTRAL candidate',contours['coverageColors']['central']),make_material(revision+' UNCERTAIN edge',contours['coverageColors']['uncertain'])]
        mesh.materials.clear()
        for mat in mats:mesh.materials.append(mat)
        classes=np.zeros(len(mesh.polygons),np.int32);classes[boundary['left']|boundary['central']]=3;classes[selection['left']]=1;classes[selection['central']]=2
        mesh.polygons.foreach_set('material_index',classes);mesh.update()
        rosters={name:{'importedPolygonIDs':np.flatnonzero(mask).tolist(),'rawFBXPolygonIDs':mapping[mask].tolist(),'uncertainImportedPolygonIDs':np.flatnonzero(boundary[name]).tolist()} for name,mask in selection.items()}
        (out/'candidate-face-rosters.json').write_text(json.dumps({'status':'Candidate selection only; render review required before any semantic mask','sourceSha256':sha(source),'geometryUVNormalSha256':before_hash,'rosters':rosters},indent=2)+'\n')
        (out/'raw-import-correspondence.json').write_text(json.dumps({'audit':corr,'importedPolygonToRawFBXPolygon':mapping.tolist(),'originalImportedMaterialNames':original_materials,'originalImportedMaterialIndices':original_indices},indent=2)+'\n')
        # No scale/transform applied. Native Blender cameras inspect exactly the fresh source.
        scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
        preferences=bpy.context.preferences.addons.get('cycles')
        if preferences and any(d.use and d.type!='CPU' for d in preferences.preferences.devices):scene.cycles.device='GPU'
        scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
        scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new(revision+' neutral world');scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.32,.36,.42,1);bg.inputs[1].default_value=.6
        for name,pos,power,size in [('key',(-3,-4,5),850,4),('fill',(4,2,4),700,4),('bottom',(0,0,-4),450,4)]:
            light=bpy.data.lights.new(revision+' '+name,'AREA');light.energy=power;light.shape='DISK';light.size=size;obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
        camera=bpy.data.cameras.new(revision+' coverage camera');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);camera.type='ORTHO';camera.ortho_scale=2.65;scene.camera=cam
        views={'front':(0,-4,0),'back':(0,4,0),'top':(0,0,4),'right':(4,0,0),'left':(-4,0,0),'underside':(0,0,-4)};captures=[]
        for view,position in views.items():
            cam.location=position;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
            for mode in ('coverage','original-albedo'):
                mesh.polygons.foreach_set('material_index',classes if mode=='coverage' else np.zeros(len(classes),np.int32));mesh.update();file=out/(view+'-'+mode+'.png');assert not file.exists();scene.render.filepath=str(file);bpy.ops.render.render(write_still=True,scene=scene.name);captures.append({'view':view,'mode':mode,'file':file.name,'sha256':sha(file),'cameraPositionBlender':list(position)})
        mesh.polygons.foreach_set('material_index',classes);mesh.update();after_hash=mesh_digest(mesh);assert after_hash==before_hash, 'Geometry/UV/corner-normal bytes changed'
        cam.location=views['front'];cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
        blend=out/'trash-sack-selection-candidate.blend';bpy.data.libraries.write(str(blend),{scene},fake_user=True,compress=True)
        report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceSha256':sha(source),'contourSha256':sha(CONTOUR),'scriptSha256':sha(ROOT/'art/reference_street_20260910/stage_trash_sack_selection_v1.py'),'geometryUVNormalBefore':before_hash,'geometryUVNormalAfter':after_hash,'correspondence':corr,'selectedFaces':{name:int(mask.sum()) for name,mask in selection.items()},'uncertainFaces':{name:int(mask.sum()) for name,mask in boundary.items()},'scene':scene.name,'blend':blend.name,'blendSha256':sha(blend),'captures':captures,'sourceMapsPreserved':True,'freshImportedGeometryUVNormalBytesPreserved':True,'originalFBXFileUntouched':True,'rawAlternativeTrianglesNotExportedOrModified':True,'maskTextureAuthored':False,'runtimeMeshExported':False,'assetsChanged':False,'semanticSelectionAccepted':False,'requiredNext':'Review all native Blender coverage against original albedo; refine contours/face roster before authoring any UV DetailMask. Check atlas overlap/gutters after face acceptance.'}
        (out/'selection-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'output':str(out),'selectedFaces':report['selectedFaces'],'semanticAccepted':False,'maskAuthored':False}))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps({'error':repr(error),'status':'Failed candidate evidence retained; no source or Assets overwrite'},indent=2)+'\n');raise
    finally:bpy.context.window.scene=previous


if __name__=='__main__' or globals().get('RUN_TRASH_SACK_SELECTION',False):
    run()
