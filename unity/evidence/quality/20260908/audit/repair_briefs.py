#!/usr/bin/env python3
"""Build concrete repair/capture briefs from the frozen quality-baseline inventory."""
import json, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
D=json.loads((HERE/'current-scene-audit.json').read_text())
mesh={m['id']:m for m in D['meshes']}
material={m['id']:m for m in D['materials']}
active=[i for i in D['instances'] if i['active'] and i['sourceVisible'] and not i['generated']]
names={'BLD_shop_e_01':'Relay Works','BLD_shop_e_02':'Air + Water','BLD_shop_e_03':'Tool Exchange','BLD_shop_e_04':'Salvage','BLD_shop_w_01':'Finery','BLD_shop_w_02':'Field Supply','BLD_shop_w_03':'Repairs','BLD_shop_w_04':'Thread + Hide'}
def save(name,data):(HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def evidence(name):return 'unity/evidence/phase1/20260908/final-native-02/'+name+'.png'
buildings=[];captures=[]
for i in active:
    if not i['path'].startswith('Post-war salvage/') or not i['path'].endswith('/Meshy visual') or not any(x in i['path'] for x in ['BLD_shop_','Basic General repaired','Vanguard Hall repaired']):continue
    key=next((k for k in names if k in i['path']),None)
    title=names[key] if key else 'Basic General' if 'General' in i['path'] else 'Vanguard Hall'
    m=mesh[i['meshId']];s=i['scale'];distortion=max(abs(x) for x in s)/min(abs(x) for x in s)
    brief=dict(name=title,path=i['path'],sourceAsset=i['meshPath'],center=i['center'],boundsMetres=i['size'],lossyScale=s,axisScaleRatio=distortion,runtimeTriangles=m['triangles'],runtimeVertices=m['vertices'],decision='replace',priority=1,
        construction='Author solid masonry/metal construction at human scale with door reveals, separate hardware, thick roof/eaves, intentional supports, independent readable lettering and rear service detail. Preserve parcel, gameplay roots and source recovery; fit whole assets uniformly.',
        texture='Use tiled material regions/trim detail at pedestrian texel density; controlled contact grime and grip/edge wear; do not stretch a unique facade atlas across the full building.',
        acceptance='Player-height front, doorway, both sides/back, roof and moving approach; source geometry plus native sun/shade inspection; no warped/fused parts, blocked route or paper-thin roof.',
        preserve='Existing shop name/IDs, porch and ground height, nearby NPC positions, thresholds, interaction clearance and all routes.',visualCoverage='No complete individual front/side/back/roof set; shared-shell defects inferred for unviewed sides only.')
    if title=='Vanguard Hall':
        brief['construction']='Replace melted door surround, warped facade/roof supports and baked lettering with real construction; retain the Phase 1 uniform proportions and refitted plinth footprint. Make a separate editable sign; do not reintroduce the old depth stretch.'
        brief['evidence']=[evidence('cam_p1_hall_front'),evidence('cam_p1_hall_door'),evidence('cam_grounding_hall_back')]
        brief['visualCoverage']='Native front, door and back reviewed. Door is severely warped and text smeared. Roof/support close review still missing.'
    elif title=='Basic General':
        brief['preserve']='Mira, counter/interaction reach, porch, atomic flask/scrap trading, IDs and route clearances.'
        brief['evidence']=[evidence('cam_salvage_general')]
        brief['visualCoverage']='Native front/oblique reviewed. Cloth/sign/stone have baked soft details; full side/back and close hardware missing.'
        brief['construction']='Rebuild modestly stretched support posts, thin canopy/roof connection, distorted fascia and fuzzy baked lettering; retain the small open shop footprint and counter access.'
    elif title=='Field Supply':
        brief['evidence']=[evidence('cam_shop_recovery_close')]
        brief['visualCoverage']='Native close frontage reviewed: weak near detail, black recess, stretched cloth and shared-shell distortion. Other sides unreviewed.'
    else:brief['evidence']=[evidence('cam_avenue'),evidence('cam_hill')]
    buildings.append(brief)
    cx,cy,cz=i['center'];sx,sy,sz=i['size'];sign=1 if cx>0 else -1
    if key:
        capture=dict(asset=title,path=i['path'],required=['front','door','back','side','roof'],proposed=[
            dict(name='audit_'+key+'_front',position=[sign*12.4,1.8,cz+1.8],target=[cx-sign*sx*.43,2.4,cz],fov=65),
            dict(name='audit_'+key+'_door',position=[cx-sign*(sx*.5+1.4),1.8,cz],target=[cx-sign*sx*.48,1.8,cz],fov=65),
            dict(name='audit_'+key+'_back',position=[cx+sign*(sx*.5+3),1.8,cz+2],target=[cx+sign*sx*.48,2.7,cz],fov=65),
            dict(name='audit_'+key+'_side',position=[cx,1.8,cz+sz*.5+2.7],target=[cx,2.5,cz+sz*.45],fov=65),
            dict(name='audit_'+key+'_roof',position=[cx-sign*7,sy+3,cz-7],target=[cx,sy,cz],fov=60)],note='Diagnostic proposed positions only; root must verify scene occlusion and camera safety before capture. Front sides follow the avenue-facing parcel, not old browser coordinates.')
        captures.append(capture)
finery=[i for i in active if '/Phase1/Finery/Meshes/' in i['meshPath']]
buildings.append(dict(name='Finery',path='Phase 1 Finery frontage',runtimeTriangles=sum(mesh[i['meshId']]['triangles'] for i in finery),parts=len(finery),decision='repair',priority=1,
    construction='Retain coherent solid openings/roof. Add less regular masonry wear, improve window support plausibility and rear service articulation; remove cloned long rust-drip patterns on door leaves/shutters with deliberate per-region UV/texture variants.',
    preserve='Existing courtyard, canopy, notices, 2.35 m door leaves, porch route, sign and collision proxy.',
    evidence=[evidence('cam_p1_finery_front'),evidence('cam_p1_finery_door'),evidence('cam_p1_finery_roof')],visualCoverage='Representative native front, door, roof reviewed, plus retained Blender back source. Every masonry part and rear native proximity are not individually reviewed.'))

characters=[]
for i in active:
    if not i['skin']:continue
    m=mesh[i['meshId']];mats=[material[x] for x in i['materials']]
    label='Vex' if '/npc_vex/' in i['path'] else 'Mira' if '/npc_mira/' in i['path'] else 'Torr' if '/npc_torr/' in i['path'] else 'Linn' if '/npc_linn/' in i['path'] else 'Player' if i['path'].startswith('Player/') else 'Yard mechanic' if 'mechanic' in i['path'] else i['path'].split('/')[1]
    tasks=[]
    if i['shadow']=='Off':tasks.append('Enable and inspect appropriate character shadows/contact in native sun and shade after profiling; currently casting Off.')
    if not m['tangents']:tasks.append('Generate compatible tangent data before binding tangent-space normals; preserve weights, bindposes, UVs and topology.')
    if label in ['Mira','Torr','Linn']:tasks.append('Audition original guard PBR normals/roughness and neutral albedo tint individually. Existing albedo tint is [0.62,0.66,0.59] with no supplied PBR detail maps.')
    if label=='Player':tasks.append('Remove full-albedo emissive contribution and blanket metallic response; retain controlled cyan practical emission with a deliberate mask. Current albedo is also the emissive texture, factor 1, and metallicFactor 1 without a metallic mask.')
    if label.startswith('npc_walker'):tasks.append('Recover or author garment/skin normal detail; inspect face/hands and cloth-metal separation using supplied compatible traveler source.')
    if label=='Vex':tasks.append('Source geometry/material repair: crisp armour seams, distinct undersuit, visor construction/reflection, hands and ankle/boot articulation. Retain helmet identity and reject the unassigned identity-changing 4K retexture.')
    tasks.append('Natural idle/turn/talk or walk transitions; verify deformation and foot contact in close moving views. Preserve role, model assignment, animator compatibility and existing movement/routes.')
    characters.append(dict(name=label,path=i['path'],sourceAsset=i['meshPath'],runtimeTriangles=m['triangles'],runtimeVertices=m['vertices'],normals=m['normals'],tangents=m['tangents'],uv0=m['uv0'],shadow=i['shadow'],scale=i['scale'],materials=mats,priority=1,decision='repair',tasks=tasks,
        evidence=[evidence('cam_p1_vex_face'),'unity/evidence/phase1/20260908/final-motion/vex-motion.mp4'] if label=='Vex' else [],visualCoverage='Vex face native frame reviewed; motion exists but not re-reviewed by this accounting task.' if label=='Vex' else 'Unreviewed individually in current native close-up; no acceptance inferred from shared model.'))

rejected=[]
for key in ['field','finery','repairs','salvage','thread','tools','water']:
    i=next(i for i in D['instances'] if '/District/Atlas/'+key+'.asset' in i['meshPath']);m=mesh[i['meshId']]
    issues={
      'field':'Faceted curved roof, collapsed/fused vertical wall detail, unsupported rooftop duct mass; reconstruct barn roof ribs/thickness and distinct access/supports.',
      'finery':'Broad thin/fused sheet side wings, irregular upper masonry geometry and repeated shell appearance; current authored Finery supersedes this candidate. Retain only as an inactive concept.',
      'repairs':'Thin curved roof edge, fused ribbed side supports and soft tiny sign; reconstruct useful service-bay opening/roof supports and separate lettering.',
      'salvage':'Heavy top container rests on indistinct fused supports, lumpy foundation and paper-thin roof scrap; rebuild credible load path and salvage racks.',
      'thread':'Crowded stacked ledges/cloth fused to facade, messy rear supports and implausible hanging volumes; separate fabric and frame, simplify and construct coherent levels.',
      'tools':'Melted sawtooth/gabled roof folds and fuzzy blank backside; rebuild folded metal panels with thickness, fasteners, drainage and a useful service rear.',
      'water':'Rounded tank shapes are lumpy; railings/pipes/supports fuse into the roof, unclear access; retain water motif but rebuild tank bands, pipes, service platform and safe support logic.'}[key]
    rejected.append(dict(name=key,path=i['path'],activeInHierarchy=i['active'],runtimeMesh=i['meshPath'],runtimeTriangles=m['triangles'],runtimeVertices=m['vertices'],source='meshy/district-20260908/'+key+'/'+key+'.glb',decision='replace' if key!='finery' else 'keep inactive',brief=issues,
        evidence=['unity/evidence/district/20260908/import/'+key+'-plusz.png','unity/evidence/district/20260908/import/'+key+'-minusz.png'],visualCoverage='Both retained source-audition oblique views reviewed in labelled contact sheet; no native placement acceptance, underside inspection or wireframe sign-off.',materialNote='Retained original 2K maps; rejected Unity atlas placements are historical and remain inactive. Do not enable on a scale/texture-only fix.'))

save('building-repair-briefs.json',buildings);save('character-repair-briefs.json',characters);save('rejected-building-briefs.json',rejected);save('capture-requests.json',captures)
print('Wrote',len(buildings),'building briefs,',len(characters),'actor briefs,',len(rejected),'rejected candidate briefs,',len(captures),'proposed camera groups')
