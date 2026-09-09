"""Turn the recorded Unity inventory into explicit, reviewable asset ledgers.
Unreviewed assets stay unreviewed; counts never imply visual acceptance.
"""
import json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'unity/evidence/phase1/20260908'
a=json.loads((E/'after-scene-audit.json').read_text());b=json.loads((E/'scene-audit.json').read_text())
meshes={m['id']:m for m in a['meshes']};instances=defaultdict(list)
for i in a['instances']:instances[i['meshId']].append(i)
rows=[]
for mid,items in instances.items():
 m=meshes[mid];active=[i for i in items if i['active'] and i['sourceVisible'] and not i['generated']]
 generated=all(i['generated'] for i in items)
 status='derived render chunk' if generated else 'active source' if active else 'inactive or hidden source'
 decision='keep; regenerate from source after edits' if generated else 'review pending; do not infer acceptance'
 if m['path'].startswith('Assets/AthenHill/Art/Phase1/Finery'):decision='repair integrated; first frontage review, rear articulation and ageing remain'
 if m['name']=='Connected root flare':decision='repair integrated; closed joins, remaining root-side UV stretch/crown work'
 if m['path'].endswith('WardGuardTangents.asset'):decision='restore integrated; original PBR and tangents, surface/pose quality remains'
 rows.append(dict(mesh=m,classification=status,activeInstances=len(active),instances=items,decision=decision))
rows.sort(key=lambda x:(x['classification'],x['mesh']['path'],x['mesh']['name']))
(E/'mesh-ledger.json').write_text(json.dumps(rows,indent=2))
lines=['# Phase 1 mesh ledger — 8 September 2026','',
'Generated from the saved Unity scene. Each row is a unique imported/runtime mesh asset, including hidden sources and generated chunks. This is an accounting ledger; individual visual review remains pending wherever stated. Source export-to-import comparisons are documented only for the focused repairs. Instance paths, transforms, bounds, map dimensions and material bindings are in [the JSON ledger](../unity/evidence/phase1/20260908/mesh-ledger.json) and [scene inventory](../unity/evidence/phase1/20260908/after-scene-audit.json). Duplicate hierarchy names are disambiguated by world position. Entity IDs are evidence-session identifiers.','',
'| Mesh / source asset | Class | Tris / vertices | Active instances | UV0 / normals / tangents | Decision |','| --- | --- | ---: | ---: | --- | --- |']
for r in rows:
 m=r['mesh'];name=m['name'].replace('|','/');path=m['path'].replace('|','/') or '(built-in/runtime)'
 lines.append(f"| {name}<br>{path} | {r['classification']} | {m['triangles']:,} / {m['vertices']:,} | {r['activeInstances']} | {m['uv0']} / {m['normals']} / {m['tangents']} | {r['decision']} |")
(ROOT/'docs/mesh-audit-assets.md').write_text('\n'.join(lines)+'\n')
# A separate building ledger has explicit instance-level tasks.
bm={m['id']:m for m in b['meshes']};buildings=[]
for i in b['instances']:
 if i['active'] and i['sourceVisible'] and i['path'].endswith('/Meshy visual') and ('BLD_shop_' in i['path'] or 'Vanguard Hall repaired' in i['path'] or 'Basic General' in i['path']):
  task='Replace distorted repeated Relay shell with a reviewed, individually varied frontage; uniform proportions; refit its own threshold/collision. Do not copy Finery blindly.'
  if 'shop_w_01' in i['path']:task='Finery frontage replaced in this pass. Review rear wall articulation, more localized weathering and final sign fit; retain courtyard assets.'
  if 'Vanguard Hall' in i['path']:task='Uniform-scale repair integrated. Replace/repair warped roof supports and fused facade detail; author readable hall lettering separately.'
  if 'Basic General' in i['path']:task='Review and repair soft close door/wall construction, modest nonuniform fitting, and separate shade/metal response; preserve Mira and trades.'
  buildings.append(dict(path=i['path'],center=i['center'],sizeBefore=i['size'],scaleBefore=i['scale'],triangles=bm[i['meshId']]['triangles'],vertices=bm[i['meshId']]['vertices'],followUp=task))
(E/'building-ledger.json').write_text(json.dumps(buildings,indent=2))
print(json.dumps(dict(uniqueMeshes=len(rows),buildings=len(buildings),ledger='docs/mesh-audit-assets.md')))
