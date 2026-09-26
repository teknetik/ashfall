"""Original brush-stroke lettering, author/export through the live Blender MCP.

Creates a new source scene without altering any old Blender scenes. Retains the
exact existing phrase and clips paint to the twenty saved shutter slat bounds.
No font asset, generated image, extracted lettering, or runtime reconstruction.
Output positions/normals are world Unity metres; material recipe is explicit.
"""
import bpy
import bmesh
import hashlib
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT/'art/reference_street_20260909'
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT/'brush-graffiti-v1.blend').exists(), 'Preserve prior graffiti source'
assert 'Reference street brush lettering v1' not in bpy.data.scenes
source_path = ROOT/'art/building_weathering_20260909/unity-source.json'
rows = json.loads(source_path.read_text())
slats = sorted([r for r in rows if 'Rolled shutter slat' in r['name']],
               key=lambda row:row['bounds']['min'][1])
assert len(slats) == 20
rng = random.Random(9091947)
scene = bpy.data.scenes.new('Reference street brush lettering v1')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'

# Original centerline drawings. Curved letters have deliberately asymmetric
# strokes and open joins, unlike the previous mechanically regular font mesh.
glyphs = {
 'A': [[(0,0),(.29,.99),(.62,.02)],[(.13,.39),(.47,.43)]],
 'C': [[(.59,.84),(.40,1),(.15,.91),(.03,.60),(.05,.21),(.26,.02),(.55,.13)]],
 'E': [[(.03,0),(.00,1),(.55,.96)],[(.04,.50),(.45,.54)],[(.04,.03),(.59,.08)]],
 'F': [[(.05,.00),(.01,.98),(.58,1)],[(.04,.54),(.46,.56)]],
 'H': [[(.03,0),(.01,1)],[(.57,.02),(.59,.96)],[(.04,.48),(.58,.53)]],
 'I': [[(.29,.02),(.28,.98)],[(.06,.98),(.50,1)],[(.07,.00),(.53,.04)]],
 'L': [[(.04,1),(.01,.04),(.58,0)]],
 'N': [[(.03,0),(.03,1),(.56,.07),(.61,1)]],
 'O': [[(.28,1),(.08,.87),(.02,.52),(.10,.13),(.31,.02),(.56,.18),(.61,.57),(.51,.9),(.28,1)]],
 'P': [[(.03,0),(.02,.99),(.40,.99),(.61,.82),(.54,.61),(.34,.52),(.05,.53)]],
 'R': [[(.03,0),(.01,1),(.38,.99),(.59,.83),(.54,.62),(.33,.54),(.04,.54)],[(.28,.53),(.65,.01)]],
 'S': [[(.58,.88),(.40,1),(.13,.90),(.02,.72),(.16,.56),(.47,.43),(.60,.24),(.43,.04),(.15,.03),(.01,.16)]],
 'T': [[(.01,.98),(.67,1)],[(.33,.98),(.29,.00)]],
 'V': [[(.01,1),(.29,.02),(.64,.98)]],
 '.': [[(.23,.03),(.25,.07)]]
}


def clip_y(polygon, limit, greater):
    if not polygon:return []
    result = []
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        ia = a[1] >= limit if greater else a[1] <= limit
        ib = b[1] >= limit if greater else b[1] <= limit
        if ia: result.append(a)
        if ia != ib:
            fraction = (limit-a[1])/(b[1]-a[1])
            result.append((a[0]+(b[0]-a[0])*fraction, limit))
    return result


def brush_polygons(points, radius):
    samples=[]
    for start, end in zip(points, points[1:]):
        distance=math.dist(start,end)
        count=max(2,math.ceil(distance/.009))
        for i in range(count):
            t=i/count
            samples.append((start[0]+(end[0]-start[0])*t,
                            start[1]+(end[1]-start[1])*t))
    samples.append(points[-1])
    phase=rng.uniform(0,math.tau)
    left=[];right=[]
    for i, sample in enumerate(samples):
        previous=samples[max(0,i-1)];following=samples[min(len(samples)-1,i+1)]
        dx=following[0]-previous[0];dy=following[1]-previous[1]
        length=math.hypot(dx,dy) or 1
        # Bristle edges, uneven paint loading and tapered stroke ends. These
        # are millimetre irregularities, not large angular slabs of lettering.
        end_weight=min(1,(i+1)/3,(len(samples)-i)/3)
        half=radius*(.84+.12*math.sin(i*.72+phase))*max(.47,end_weight)
        a=half+rng.uniform(-.0024,.0024)
        b=half+rng.uniform(-.0024,.0024)
        left.append((sample[0]-dy/length*a,sample[1]+dx/length*a))
        right.append((sample[0]+dy/length*b,sample[1]-dx/length*b))
    for i in range(len(samples)-1):
        # Occasional sub-centimetre dry-brush gaps; most strokes stay continuous.
        if 3<i<len(samples)-4 and rng.random()<.012: continue
        yield [left[i],right[i],right[i+1],left[i+1]]


def B(point): return Vector((point[0],-point[2],point[1]))
def U(point): return [round(point.x,6),round(point.z,6),round(-point.y,6)]

material = bpy.data.materials.new('Reference street matte bone paint')
material.use_nodes = True
bs = material.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value = (.73,.66,.53,1)
bs.inputs['Roughness'].default_value = .92
bs.inputs['Metallic'].default_value = 0
material['unity_material_key']='BrushPaint'
material['authoring']='Original brush line geometry, high-albedo matte paint with no inherited base texture'

out=[]
for line, text, baseline, width in [('upper','THE FACTORIES',2.205,2.59),
                                    ('lower','NEVER SLEEP.',1.685,2.52)]:
    widths=[.36 if c==' ' else .34 if c=='.' else .72 for c in text]
    total=sum(widths)
    xscale=width/total
    cursor=0
    vertices=[];faces=[]
    for char,advance in zip(text,widths):
        if char==' ':cursor+=advance;continue
        tilt=rng.uniform(-.10,.10)
        height=rng.uniform(.387,.427)
        baseline_jitter=rng.uniform(-.021,.020)
        shear=rng.uniform(.04,.16)
        for stroke in glyphs[char]:
            points=[]
            for gx,gy in stroke:
                px=(cursor+gx+gy*shear)*xscale
                py=gy*height
                # Small per-glyph angle plus a slight upward line drift.
                localx=gx*xscale
                points.append((px-py*math.sin(tilt),
                               baseline+baseline_jitter+py*math.cos(tilt)+localx*math.sin(tilt)+.035*px/width))
            for polygon in brush_polygons(points,rng.uniform(.0145,.021)):
                lo=min(p[1]for p in polygon);hi=max(p[1]for p in polygon)
                for slat in slats:
                    bottom=slat['bounds']['min'][1]+.0012
                    top=slat['bounds']['max'][1]-.0012
                    if hi<bottom or lo>top:continue
                    clipped=clip_y(clip_y(polygon,bottom,True),top,False)
                    if len(clipped)<3:continue
                    start=len(vertices)
                    zstart=-9+width/2
                    # Retained front plane, 9 mm proud of the saved slat face.
                    vertices.extend(B((17.936,y,zstart-x))for x,y in clipped)
                    faces.append(tuple(range(start,start+len(clipped))))
        cursor+=advance
    mesh=bpy.data.meshes.new('Factory brush '+line)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:
        if face.normal.x>0:face.normal_flip()
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    uv=mesh.uv_layers.new(name='UV0 four metre paint')
    for loop in mesh.loops:
        point=mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=(-point.y/4,point.z/4)
    obj=bpy.data.objects.new('Factory brush '+line,mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj['family']='field_supply';obj['material_key']='BrushPaint'
    obj['reference_only']=False;obj['castsShadow']=False
    mesh.calc_loop_triangles()
    positions=[];normals=[];coords=[];indices=[]
    for triangle in mesh.loop_triangles:
        for li in triangle.loops:
            positions.append(U(mesh.vertices[mesh.loops[li].vertex_index].co))
            normals.append([-1,0,0]);coords.append(list(uv.data[li].uv))
            indices.append(len(indices))
    out.append({'name':obj.name,'family':'field_supply','material':'BrushPaint',
                'positions':positions,'normals':normals,'uv':coords,'indices':indices,
                'castsShadow':False,'collider':False,'text':text})

(OUT/'brush-graffiti-meshes-v1.json').write_text(json.dumps(out,separators=(',',':')))
manifest={
 'source':'brush-graffiti-v1.blend','meshExport':'brush-graffiti-meshes-v1.json',
 'coordinateConvention':'Unity world metres, +Y up; Blender is (x,-z,y)',
 'phrase':['THE FACTORIES','NEVER SLEEP.'],
 'parts':len(out),'triangles':sum(len(part['indices'])//3 for part in out),
 'target':'Field Supply existing rolled shutter',
 'replace':'Disable old visual objects whose material is BuildingWeathering/20260909/Materials/GraffitiSolid.mat under Field Supply and Finery weathering/field_supply; retain old meshes/objects for recovery',
 'transform':'Create group at identity; positions are already world space. Do not apply old source transforms again.',
 'material':{'key':'BrushPaint','shader':'Universal Render Pipeline/Lit',
              'baseColor':[.73,.66,.53,1],'metallic':0,'smoothness':.08,
              'baseMap':None,'normalMap':None,'metallicGlossMap':None,
              'cull':0,'emission':[0,0,0],'renderQueue':'opaque',
              'note':'Do not clone WardPlaster; its inherited base map darkens the lettering'},
 'preservation':'Old lettering source, scene objects, phrase, slat geometry and all colliders retained',
 'sourceInput':{'file':str(source_path),'sha256':hashlib.sha256(source_path.read_bytes()).hexdigest()},
 'license':'Original stroke geometry authored in this project; no font or external image dependencies',
 'reviewStatus':'Candidate source only; inspect readability and slat gaps in saved native player'}
(OUT/'brush-graffiti-manifest-v1.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'brush-graffiti-v1.blend'))
print(json.dumps({'parts':len(out),'triangles':manifest['triangles'],
                  'export':str(OUT/'brush-graffiti-meshes-v1.json')}))
