"""Create a narrow material-only contract from retained source/installation data.

No geometry or application state is modified. All material scales are derived
from the physical UV density of the recorded world-space source buffers.
"""
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/reference_street_20260909'
original_file=ROOT/'art/building_weathering_20260909/unity-source.json'
facade_file=ROOT/'art/facade_materials_20260909/facade-meshes-v2.json'
install_file=ROOT/'unity/evidence/facade-materials/20260909/installation.json'
original=json.loads(original_file.read_text())
facade=json.loads(facade_file.read_text())
installed=json.loads(install_file.read_text())
by_path={row['path']:row for row in original}
current_mesh={row['sourcePath']:row['newMesh']for row in installed['changes']}

prefixes=[
 'field_supply Shutter guide rail ', 'field_supply Shutter drum casing',
 'field_supply Shutter ground rail', 'field_supply Staff door steel jamb ',
 'field_supply Staff door leaf ', 'field_supply Staff door inset inner ',
 'field_supply Staff door stamped panel ', 'field_supply Staff door overlapping meeting strip',
 'field_supply Shop sign frame', 'field_supply Front canopy post ',
 'field_supply Canopy side beam ', 'field_supply Post base shoe ',
 'field_supply Loading roof', 'field_supply Canopy masonry attachment '
]
field=[row for row in original if row['family']=='field_supply'
       and any(row['name'].startswith(prefix)for prefix in prefixes)
       and row['materials'][0]['name']in ['WardPaint','WardSteel']
       and not any(word in row['name']for word in ['washer','hex','bolt'])]
doors=[row for row in original if row['family']=='finery'
       and row['name'] in ['Door leaf 0','Door leaf 1','Door inset worn steel 0','Door inset worn steel 1']]
louvres=[row for row in facade if row['family']=='finery' and row['material']=='Steel']
assert len(field)==37,(len(field),[row['name']for row in field])
assert len(doors)==4 and len(louvres)==50
assert all(row['materials'][0]['name']in ['WardPaint','WardSteel']for row in field)
assert all(row['materials'][0]['name']=='Finery coated door'for row in doors)


def inspect(row):
    ratios=[];large_angles=[]
    for k in range(0,len(row['indices']),3):
        ids=row['indices'][k:k+3]
        a,b,c=[row['positions'][i]for i in ids]
        ta,tb,tc=[row['uv'][i]for i in ids]
        u=[b[j]-a[j]for j in range(3)];v=[c[j]-a[j]for j in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        area2=math.sqrt(sum(q*q for q in cross))
        for edge,delta in [(u,[tb[j]-ta[j]for j in range(2)]),(v,[tc[j]-ta[j]for j in range(2)])]:
            length=math.sqrt(sum(q*q for q in edge))
            uvlength=math.hypot(*delta)
            if length>.12 and uvlength>.00001:ratios.append(uvlength/length)
        if area2>.04:
            avg=[sum(row['normals'][i][j]for i in ids)/3 for j in range(3)]
            norm=math.sqrt(sum(q*q for q in avg))
            if norm>0:
                dot=max(-1,min(1,sum(cross[j]*avg[j]for j in range(3))/(area2*norm)))
                large_angles.append(math.degrees(math.acos(dot)))
    return {'medianUvUnitsPerMetre':statistics.median(ratios)if ratios else None,
            'largeFaceCount':len(large_angles),
            'maxLargeFaceNormalDeviationDegrees':max(large_angles)if large_angles else None}


groups=[]
for name, rows, scale, density in [
        ('FieldCoatedSteel',field,.1875,4/3),
        ('FineryDoorCoatedSteel',doors,.25,1),
        ('FineryLouvreCoatedSteel',louvres,1,.25)]:
    targets=[]
    for row in rows:
        path=row.get('sourcePath',row.get('path'))
        source=by_path[path]
        metrics=inspect(row)
        # Long primitive face edges are the reliable material-density evidence;
        # smaller bevel triangles use face-dependent projections.
        observed=metrics['medianUvUnitsPerMetre']
        assert observed is not None and abs(observed-density)<.005,(path,metrics,density)
        targets.append({'path':path,'name':row['name'],
                        'expectedMeshPath':current_mesh.get(path,source['meshPath']),
                        'expectedMaterialPath':('Assets/AthenHill/Art/FacadeMaterials/20260909/Steel/Steel.mat'
                                                 if name=='FineryLouvreCoatedSteel'else source['materials'][0]['path']),
                        'recordedSourceMaterial':source['materials'][0]['name'],
                        'uvAndNormalEvidence':metrics})
    groups.append({'materialVariant':name,'sourceTextureFamily':'AgedSteel',
                    'uvScale':[scale,scale],'uvOffset':[0,0],
                    'sourceUvUnitsPerMetre':density,'finalPhysicalTileMetres':4,
                    'targetSourcePaths':[target['path']for target in targets],'targets':targets})

contract={
 'created':'2026-09-09','materialFamily':'AgedSteel','sourceBakeRevision':2,
 'sourceTextureDirectory':'textures/AgedSteel','targetCount':sum(len(g['targets'])for g in groups),
 'groups':groups,
 'targetSourcePaths':[p for group in groups for p in group['targetSourcePaths']],
 'import':'Clone the newly baked AgedSteel material three times; set _BaseMap texture scale/offset for each group. All URP Lit surface maps use the transformed base UV. Assign only listed source renderers; preserve mesh/UV0/transforms/colliders.',
 'verifyBeforeAssignment':'Current MeshFilter.sharedMesh asset path must match expectedMeshPath. A different mesh means the UV proof is stale: stop assigning that renderer and inspect it.',
 'preserve':['Field Supply ShutterSteel lip material','Brass handles/hinges/ridge cap/rainwater pipe',
             'Rubber gaskets, door seals and recessed backing','Shop name letters and sign face',
             'Stone/plaster/mortar','Finery red cloth canopy and its existing courtyard assembly',
             'Bare kickplates and small fasteners','Main roof sheets/seams and rear services'],
 'provenance':[{'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
               for path in [original_file,facade_file,install_file]],
 'scopeNotes':['37 Field Supply canopy/door/guide/frame visuals; four Finery coated door panels; fifty already remapped Finery louvres/mullions.',
               'Field source UV density is 4/3 per metre, so scale .1875 yields .25 per metre. Finery door density is 1 per metre, so scale .25 yields .25 per metre. Finery louvres already have four-metre UV0, so scale1.',
               'Material assignment is optional until AgedSteel corrected bake and native surface audition have passed.'],
 'normalReview':'Large original primitive planes retain their existing authored construction normals; no smoothing/geometry change is proposed by this material-only contract.'}
path=OUT/'aged-steel-assignment-contract.json'
assert not path.exists(),'Preserve the existing assignment contract'
path.write_text(json.dumps(contract,indent=2))
print(json.dumps({'contract':str(path),'targetCount':contract['targetCount'],
                  'groups':[{'name':g['materialVariant'],'count':len(g['targets']),'uvScale':g['uvScale'],
                             'maxLargeFaceDeviation':max((t['uvAndNormalEvidence']['maxLargeFaceNormalDeviationDegrees']or 0)for t in g['targets'])}
                            for g in groups]}))
