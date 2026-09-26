"""Execute once through the live Blender MCP before the corrected metal bake.

Reject/archive the circular-target first bake, verify retained source disk
hashes, and reload those authoritative images into Blender. No Unity changes.
Then run the corrected author_metal_materials.py with ACTION='BAKE'.
"""
import bpy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/reference_street_20260909'
archive=OUT/'rejected-metal-bake-v1'
assert not archive.exists(), 'Preserve previous rejection record; do not repeat the archive operation'
contract=json.loads((OUT/'metal-import-contract.json').read_text())
source_dir=Path(contract['provenance']['localSource'])
verified=[]
for source in contract['provenance']['inputs']:
    path=source_dir/source['file']
    observed=hashlib.sha256(path.read_bytes()).hexdigest()
    assert observed==source['sha256'], 'Original disk input changed: '+str(path)
    reloaded=[]
    for image in bpy.data.images:
        if image.source=='FILE' and image.filepath and Path(bpy.path.abspath(image.filepath)).resolve()==path.resolve():
            image.reload();reloaded.append(image.name)
    verified.append({'file':str(path),'sha256':observed,'matchesAuthoredInput':True,'reloadedImages':reloaded})

plane=bpy.data.objects['Reference four metre metal bake tile']
plane.data.materials.clear()
plane.data.materials.append(bpy.data.materials['Reference street ShutterSteel'])
plane.active_material_index=0
for face in plane.data.polygons:face.material_index=0
assert len(plane.data.materials)==1

archive.mkdir()
archived=[]
for family in ['ShutterSteel','AgedSteel']:
    current=OUT/'textures'/family
    if not current.exists():continue
    rows=[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
          for p in sorted(current.iterdir()) if p.is_file()]
    current.rename(archive/family)
    archived.append({'family':family,'files':rows})
assert archived, 'No earlier bakes found to preserve'
record={'utc':datetime.now(timezone.utc).isoformat(),
        'status':'Rejected; rebake required',
        'reason':'Unused AgedSteel slot on the bake plane selected a photographic input as an additional Cycles bake target; circular dependency warnings and duplicate bake completions observed',
        'correction':'One material slot; source image pixels reloaded from originals verified against pre-bake disk hashes',
        'originalDiskInputsUnchanged':True,'verifiedInputs':verified,'archived':archived,
        'correctedBakeScript':'author_metal_materials.py','correctedSourceBlend':'metal-studio-v2.blend'}
(archive/'rejection.json').write_text(json.dumps(record,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'metal-studio-v2.blend'))
print(json.dumps(record))
