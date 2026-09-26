"""Read-only staged source cut mask. No mesh/texture edits and no app calls."""
import numpy as np,json,hashlib
from pathlib import Path
R=Path('/home/teknetik/code/ao2');D=R/'meshy/ground-detail-20260910/generator-v3-source/grille-spatial-audit';O=R/'art/reference_street_20260910/generator-core-repair-inputs';O.mkdir(exist_ok=True)
a=np.load(D/'source-positions-triangles.npz');v=a['vertices'];f=a['triangles'];vf=v[f];c=vf.mean(1)
lo=np.array([-.456,-.232,.242]);hi=np.array([.254,-.120,.688]);inside=((vf>=lo)&(vf<=hi)).all((1,2))
rails=(c[:,0]>-.449)&(c[:,0]<.240)&(c[:,2]>.248)&(c[:,2]<.677)&(c[:,1]<-.176)
net=((c[:,0]+.138)**2+(c[:,2]-.465)**2<.216**2)&(c[:,1]<-.133)&(c[:,1]>-.230)
mask=inside&(rails|net);ids=np.flatnonzero(mask).astype(np.int32);assert 750000<len(ids)<830000
path=O/'proposed-guard-face-mask.npz';assert not path.exists();np.savez_compressed(path,removed_face_indices=ids)
record={'status':'Staged source audition selection; requires visual critique, not accepted geometry','originalFbxSha256':'a20285618ba776f5e87268e446bee03a6d1a3a51e521497ec61527460e3881d0','sourceVertices':len(v),'sourceTriangles':len(f),'sourceWorldPositionsFloat32Sha256':hashlib.sha256(v.tobytes()).hexdigest(),'sourceTriangleIndicesInt32Sha256':hashlib.sha256(f.tobytes()).hexdigest(),'removedFaces':len(ids),'retainedFaces':len(f)-len(ids),'removedFaceIndicesSha256':hashlib.sha256(ids.tobytes()).hexdigest(),'maskFileSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'strictAllowedWorldBoundsBlender':[lo.tolist(),hi.tolist()],'actualRemovedVertexBounds':[vf[mask].reshape(-1,3).min(0).tolist(),vf[mask].reshape(-1,3).max(0).tolist()],'outsideAllowedBoundsFacesDeleted':0,'rails':{'centerXBounds':[-.449,.240],'centerZBounds':[.248,.677],'frontYMaximum':-.176},'net':{'centerXZ':[-.138,.465],'radius':.216,'frontYMaximum':-.133},'caveat':'The net is fused into the Meshy surface. The strict mask retains every triangle crossing the stated outer bounds, including back-facing triangles extending into the fan body. Removed faces remain an inspectable object and the entire original core remains hidden for recovery. Source audition must check any retained cut-edge fragments through the new open guard.'}
(O/'mask-contract.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
