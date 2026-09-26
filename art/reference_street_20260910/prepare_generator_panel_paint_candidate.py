"""STAGED separate offline source authoring operation; no app launch.
Reauthors only protected paint/ink interiors as locally fitted paint color.
No global blur or FFT notch. Same-class, same-UV-chart samples only. Original
textures and every protected edge/gutter pixel are unchanged. The result is an
additive study awaiting source review, not an accepted or installed material.
"""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image,ImageFilter
R=Path('/home/teknetik/code/ao2');D=R/'meshy/ground-detail-20260910/generator-v3-source/grille-spatial-audit';T=R/'meshy/ground-detail-20260910/generator-v2/model_textures';O=R/'meshy/ground-detail-20260910/generator-v4-panel-study'
SOURCE_SHA='d8df166e127e2fd27e7904e69091d54f5b36934906a6b997a250b7b6efc0599f'

def erode_labels(labels,radius=2):
 """Label-safe interior mask, protecting exact boundaries including UV gutters."""
 h,w=labels.shape;valid=labels>0
 for dy in range(-radius,radius+1):
  for dx in range(-radius,radius+1):
   shifted=np.zeros_like(labels);ya=max(0,-dy);yb=min(h,h-dy);xa=max(0,-dx);xb=min(w,w-dx)
   shifted[ya:yb,xa:xb]=labels[ya+dy:yb+dy,xa+dx:xb+dx];valid&=shifted==labels
 return valid

def synthesize_paint_interiors(rgb,labels,allowed,radius=4):
 """Robust local degree-zero color fit; samples never cross class/chart edges.
 Edge pixels themselves are excluded by allowed. Nonperiodic salient details
 must also be excluded before this function. No unseen source image is edited.
 """
 out=rgb.copy();ys,xs=np.nonzero(allowed);h,w=labels.shape
 offsets=np.array([(dy,dx)for dy in range(-radius,radius+1)for dx in range(-radius,radius+1)],np.int32)
 for start in range(0,len(ys),4096):
  yy=ys[start:start+4096];xx=xs[start:start+4096];ny=yy[:,None]+offsets[:,0];nx=xx[:,None]+offsets[:,1];inside=(ny>=0)&(ny<h)&(nx>=0)&(nx<w);ny=np.clip(ny,0,h-1);nx=np.clip(nx,0,w-1)
  accept=inside&(labels[ny,nx]==labels[yy,xx,None]);values=rgb[ny,nx].astype(np.float64);values[~accept]=np.nan
  median=np.nanmedian(values,axis=1);residual=np.abs(values-median[:,None,:]);weights=np.minimum(1,.045/np.maximum(residual,1e-8));weights[~accept]=0
  fitted=np.nansum(values*weights,axis=1)/np.maximum(np.sum(weights,axis=1),1e-12)
  out[yy,xx]=fitted
 return out

def main():
 assert not O.exists(),'Preserve previous panel source study'
 assert hashlib.sha256((T/'base_color.png').read_bytes()).hexdigest()==SOURCE_SHA
 proof=json.loads((D/'uv-extraction-contract.json').read_text());assert proof['rawTriangleOrderEqualsLiveAudit']
 a=np.load(D/'source-positions-triangles.npz');v=a['vertices'];f=a['triangles'];uv=np.load(D/'source-uv-corners.npz')['uv'];vf=v[f];mins=vf.min(1);maxs=vf.max(1)
 lo=np.array([-.440,-.230,.693]);hi=np.array([.235,-.200,.812]);candidate=(maxs[:,0]>=lo[0])&(mins[:,0]<=hi[0])&(maxs[:,2]>=lo[2])&(mins[:,2]<=hi[2])&(maxs[:,1]<-.190);ids=np.flatnonzero(candidate)
 # UV-chart continuity uses both exact source vertex identity and UV coordinates.
 parent=np.arange(len(ids));edge_faces={}
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for j,index in enumerate(ids):
  corners=[(int(vertex),int(round(float(u[0])*1e7)),int(round(float(u[1])*1e7)))for vertex,u in zip(f[index],uv[index])]
  for k in range(3):
   key=tuple(sorted((corners[k],corners[(k+1)%3])))
   if key in edge_faces:parent[root(j)]=root(edge_faces[key])
   else:edge_faces[key]=j
 groups={};chartFor={}
 for j,index in enumerate(ids):
  rr=root(j)
  if rr not in groups:groups[rr]=len(groups)+1
  chartFor[int(index)]=groups[rr]
 image=Image.open(T/'base_color.png').convert('RGBA');source=np.asarray(image);assert source.shape==(4096,4096,4);height,width=source.shape[:2];charts=np.zeros((height,width),np.int32)
 # Exact pixel-centre barycentric world mask; not merely triangle-centroid painting.
 for index in ids:
  q=uv[index].astype(float)*[width,-height]+[-.5,height-.5];xmin=max(0,int(np.floor(q[:,0].min())));xmax=min(width-1,int(np.ceil(q[:,0].max())));ymin=max(0,int(np.floor(q[:,1].min())));ymax=min(height-1,int(np.ceil(q[:,1].max())))
  if xmax<xmin or ymax<ymin:continue
  x,y=np.meshgrid(np.arange(xmin,xmax+1),np.arange(ymin,ymax+1));ab=q[1]-q[0];ac=q[2]-q[0];den=ab[0]*ac[1]-ab[1]*ac[0]
  if abs(den)<1e-9:continue
  dx=x-q[0,0];dy=y-q[0,1];b=(dx*ac[1]-dy*ac[0])/den;c=(ab[0]*dy-ab[1]*dx)/den;aa=1-b-c;inside=(aa>=-1e-8)&(b>=-1e-8)&(c>=-1e-8)
  pos=aa[...,None]*vf[index,0]+b[...,None]*vf[index,1]+c[...,None]*vf[index,2];inside&=((pos>=lo)&(pos<=hi)).all(-1)
  block=charts[ymin:ymax+1,xmin:xmax+1];block[inside]=chartFor[int(index)]
 semantic=charts>0;assert semantic.sum()>80000,'Semantic mask unexpectedly small; inspect geometry/UV contract'
 rgb=source[:,:,:3].astype(np.float32)/255
 # A 3x3 median is used only to classify material/ink, never as the final output.
 classifier=np.asarray(Image.fromarray(source[:,:,:3]).filter(ImageFilter.MedianFilter(3))).astype(np.float32)/255
 mx=classifier.max(2);mn=classifier.min(2);chroma=mx-mn;kind=np.zeros((height,width),np.int32)
 kind[(mx<.55)&(chroma<.14)]=1
 kind[(mn>.54)&(chroma<.15)]=2
 kind[(classifier[:,:,0]>classifier[:,:,1]*1.30)&(classifier[:,:,0]>classifier[:,:,2]*1.35)&(classifier[:,:,0]>.25)]=3
 metallic=np.asarray(Image.open(T/'metallic.png').convert('L').resize((width,height),Image.Resampling.BILINEAR)).astype(np.float32)/255
 # Preserve exposed-metal candidates; this operation authors paint/ink only.
 kind[metallic>.42]=0;kind[~semantic]=0
 labels=np.where(kind>0,charts*4+kind,0).astype(np.int32);interior=erode_labels(labels,2)
 # Protect narrow nonperiodic scuffs as well as material/glyph boundaries.
 salient=(np.abs(rgb-classifier).max(2)>.20)
 salient=np.asarray(Image.fromarray((salient*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0
 interior&=~salient
 assert interior.sum()>10000,'Insufficient safely classified paint area; inspect instead of broadening silently'
 linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 fitted=synthesize_paint_interiors(linear,labels,interior,4)
 # Keep each authored class's mean linear color, preserving broad color balance.
 corrections=[]
 for k in (1,2,3):
  region=interior&(kind==k)
  if not region.any():continue
  correction=linear[region].mean(0)-fitted[region].mean(0);fitted[region]+=correction;corrections.append({'class':k,'linearMeanCorrection':correction.tolist(),'pixels':int(region.sum())})
 fitted=np.clip(fitted,0,1);srgb=np.where(fitted<=.0031308,fitted*12.92,1.055*fitted**(1/2.4)-.055)
 result=source.copy();result[interior,:3]=np.rint(srgb[interior]*255).astype('uint8')
 assert np.array_equal(result[~interior],source[~interior]);assert np.array_equal(result[:,:,3],source[:,:,3])
 # All recorded boundaries, including glyph silhouettes, stay byte-for-byte original.
 protected=semantic&~interior;assert np.array_equal(result[protected],source[protected])
 O.mkdir();Image.fromarray(result).save(O/'base_color-authored-paint.png');Image.fromarray((interior*255).astype('uint8')).save(O/'authored-paint-mask.png');Image.fromarray((semantic*255).astype('uint8')).save(O/'semantic-panel-mask.png');Image.fromarray((protected*255).astype('uint8')).save(O/'protected-source-detail-mask.png')
 np.savez_compressed(O/'semantic-labels.npz',uvChart=charts,paintClass=kind,authoredInterior=interior,sourceFaceIds=ids)
 diff=np.abs(result[:,:,:3].astype(np.int16)-source[:,:,:3].astype(np.int16));Image.fromarray(np.clip(diff*5,0,255).astype('uint8')).save(O/'difference-times-five-diagnostic.png')
 record={'status':'Authored painted-panel interior source candidate; not accepted or installed','method':'Same-class and same-UV-chart robust local color fitting. Authored interiors keep class mean linear color. Protected boundaries/scuffs/gutters retain exact source pixels. No global blur/FFT notch.','originalBaseColorSha256':SOURCE_SHA,'originalFilesChanged':False,'dimensions':[width,height],'semanticWorldBoundsBlender':[lo.tolist(),hi.tolist()],'semanticPixels':int(semantic.sum()),'authoredInteriorPixels':int(interior.sum()),'protectedSemanticPixels':int(protected.sum()),'uvCharts':len(groups),'classMeanCorrections':corrections,'outsideAuthoredMaskChangedPixels':int(np.any(diff[~interior],axis=-1).sum()),'protectedBoundaryChangedPixels':int(np.any(diff[protected],axis=-1).sum()),'meanAbsoluteByteDeltaInAuthoredRGB':float(diff[interior].mean()),'maxByteDelta':int(diff.max()),'candidateBaseColorSha256':hashlib.sha256((O/'base_color-authored-paint.png').read_bytes()).hexdigest(),'authoringMaskSha256':hashlib.sha256((O/'authored-paint-mask.png').read_bytes()).hexdigest(),'sourceAccepted':False,'nativeAccepted':False,'limitations':['Automatic paint/ink classes and protected edges require visual mask review; exact pixel preservation does not itself prove semantic classification was right.','Small glyph strokes and scratches may remain wholly original if they cannot support a safe interior. Their remaining grid is not concealed as fixed.','Review albedo/marked residual at source texel density; reject lost nonperiodic wear or waxy paint interiors.','This study has no source normal/roughness edits; the separate live material audition uses fine authored paint normal/roughness only inside its explicit mask.']}
 (O/'panel-study-manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
