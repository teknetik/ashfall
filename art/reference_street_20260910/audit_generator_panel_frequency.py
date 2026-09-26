"""Read-only semantic UV and local spectrum diagnostics, not a degrid filter.
Requires raw FBX UV-order proof. No source texture is edited or material assigned.
"""
from pathlib import Path
import numpy as np,json
from PIL import Image,ImageDraw,ImageFilter
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source';D=O/'grille-spatial-audit';dest=O/'panel-frequency-audit-v4';dest.mkdir(exist_ok=False)
a=np.load(D/'source-positions-triangles.npz');v=a['vertices'];f=a['triangles'];c=v[f].mean(1);uv=np.load(D/'source-uv-corners.npz')['uv'];proof=json.loads((D/'uv-extraction-contract.json').read_text());assert proof['rawTriangleOrderEqualsLiveAudit']
selected=(c[:,0]>-.440)&(c[:,0]<.235)&(c[:,2]>.693)&(c[:,2]<.812)&(c[:,1]<-.200)
mask=Image.new('L',(4096,4096),0);draw=ImageDraw.Draw(mask)
for tri in uv[selected]:draw.polygon([(float(p[0]*4096),float((1-p[1])*4096))for p in tri],fill=255)
mask.save(dest/'semantic-front-panel-mask-diagnostic.png');ma=np.asarray(mask)>0
base=np.asarray(Image.open(R/'meshy/ground-detail-20260910/generator-v2/model_textures/base_color.png').convert('RGB')).astype(np.float32)/255
linear=np.where(base<=.04045,base/12.92,((base+.055)/1.055)**2.4);lum=linear@np.array([.2126,.7152,.0722],np.float32)
# Integral coverage permits only patches completely inside the semantic panel UV region.
def ii(a):return np.pad(a.cumsum(0).cumsum(1),((1,0),(1,0)))
protected=(base.max(2)>.58)|((base.max(2)-base.min(2))>.085)
protected=np.asarray(Image.fromarray((protected*255).astype('uint8')).filter(ImageFilter.MaxFilter(7)))>0
interior=ma&~protected
Image.fromarray((interior*255).astype('uint8')).save(dest/'protected-gray-background-mask-diagnostic.png')
integral=ii(interior.astype(np.int32));size=48;candidates=[]
ys,xs=np.nonzero(ma);bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
for y in range(bounds[1],bounds[3]-size,12):
 for x in range(bounds[0],bounds[2]-size,12):
  covered=(integral[y+size,x+size]-integral[y,x+size]-integral[y+size,x]+integral[y,x])/(size*size)
  if covered<1.0:continue
  rgb=base[y:y+size,x:x+size];q=lum[y:y+size,x:x+size]
  if float(rgb.mean())>.42 or float((rgb.max(2)-rgb.min(2)).mean())>.065:continue
  blocks=q.reshape(size//12,12,size//12,12).mean((1,3));score=float(blocks.std())
  candidates.append((score,x,y))
chosen=[]
for score,x,y in sorted(candidates):
 if all((x-xx)**2+(y-yy)**2>size**2*.75 for _,xx,yy in chosen):chosen.append((score,x,y))
 if len(chosen)==3:break
rows=[]
for i,(variation,x,y) in enumerate(chosen):
 q=lum[y:y+size,x:x+size].astype(float);yy,xx=np.mgrid[:size,:size];X=np.stack([np.ones(size*size),xx.ravel(),yy.ravel()],1);coef=np.linalg.lstsq(X,q.ravel(),rcond=None)[0];q-=np.einsum('ijk,k->ij',np.stack([np.ones_like(xx),xx,yy],2),coef)
 window=np.outer(np.hanning(size),np.hanning(size));fft=np.fft.fftshift(np.fft.fft2(q*window));energy=abs(fft)**2;freq=np.fft.fftshift(np.fft.fftfreq(size));fy,fx=np.meshgrid(freq,freq,indexing='ij');rad=np.sqrt(fx*fx+fy*fy);ratio=np.zeros_like(energy)
 for lo in np.arange(.08,.61,.015):
  group=(rad>=lo)&(rad<lo+.015);background=np.median(energy[group]);ratio[group]=energy[group]/max(background,1e-15)
 # Report one member of each conjugate pair, suppress nearby bins; no guessed notch is applied.
 eligible=(rad>.08)&(rad<.60)&((fy>0)|((fy==0)&(fx>0)));rank=np.where(eligible,ratio,0);peaks=[]
 for _ in range(8):
  j,k=np.unravel_index(rank.argmax(),rank.shape)
  if rank[j,k]<=0:break
  peaks.append({'cyclesPerPixelXY':[float(fx[j,k]),float(fy[j,k])],'radialPeriodPixels':float(1/rad[j,k]),'energyOverRadialMedian':float(ratio[j,k]),'fractionOfTotalDetrendedWindowEnergy':float(energy[j,k]/energy.sum())});rank[max(0,j-2):j+3,max(0,k-2):k+3]=0
 Image.fromarray(np.rint(base[y:y+size,x:x+size]*255).astype('uint8')).save(dest/f'patch-{i}-original-albedo.png')
 # Scientific spectrum visualization only, not altered material pixels.
 spectrum=np.log1p(energy);spectrum/=spectrum.max();Image.fromarray(np.rint(spectrum*255).astype('uint8')).resize((384,384)).save(dest/f'patch-{i}-log-spectrum.png')
 rows.append({'patch':i,'sourceRectXYWH':[x,y,size,size],'semanticCoverage':1.0,'blockMeanLinearLuminanceStd':variation,'peaks':peaks})
record={'sourceChanged':False,'filterApplied':False,'semanticFaceCount':int(selected.sum()),'semanticUVPixelCount':int(ma.sum()),'semanticUVBoundsPixels':bounds,'candidateBackgroundPatchCount':len(candidates),'patches':rows,'interpretation':'Spectral peaks are measurements for review, not automatically identified as woven-pattern frequency. Inspect repeated stable peak pairs and source edge profiles before choosing an island-local residual filter. Never blur the complete map or its gutters.'};(dest/'frequency-diagnostic.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
