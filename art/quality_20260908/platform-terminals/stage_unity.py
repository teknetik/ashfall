"""Copy reviewed source derivatives and isolated installer; does not operate Unity."""
from pathlib import Path
import hashlib,json,shutil
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/platform-terminals';A=R/'unity/AthenHill/Assets/AthenHill/Art/PlatformTerminals'
assert (O/'display-repair.json').is_file(), 'Finish the seated display source repair first.'
repair=json.loads((O/'display-repair.json').read_text());assert all(r['removed_glass_faces']>0 for r in repair['lods'])
files=[(O/('terminal-lod'+str(i)+'.glb'),A/('terminal-lod'+str(i)+'.glb'))for i in range(3)]
files += [(O/'terminal-gasket.glb',A/'terminal-gasket.glb')]
files += [(O/'textures'/name,A/name)for name in ['BaseColor.png','Normal.png','MetalSmooth.png']]
files += [(O/'displays'/name,A/name)for name in ['save.png','reclaim.png','nameplate.png']]
files += [(O/'PlatformTerminalPass.cs',R/'unity/AthenHill/Assets/AthenHill/Editor/PlatformTerminalPass.cs')]
rows=[]
for src,dst in files:
 assert src.is_file(),src
 digest=hashlib.sha256(src.read_bytes()).hexdigest()
 if dst.exists():assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest, 'Refusing to replace a different already-staged asset: '+str(dst)
 else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 rows.append({'source':str(src.relative_to(R)),'destination':str(dst.relative_to(R)),'sha256':digest,'bytes':dst.stat().st_size})
(O/'unity-staging-manifest.json').write_text(json.dumps({'state':'Files staged; root must refresh/compile, prepare prefabs, install, capture native and obtain critic review.','files':rows},indent=2))
print(json.dumps(rows,indent=2))
