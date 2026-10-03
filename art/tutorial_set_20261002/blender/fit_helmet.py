import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MARGIN=float(args[0]) if args else 0.016; DROP=float(args[1]) if len(args)>1 else 0.0
arm,body=load_final()
ws=world_verts(body)
top=max(w.z for w in ws)
cap=[w for w in ws if w.z>top-0.13]             # skull + hair above the ears
xs=[w.x for w in cap]; ys=[w.y for w in cap]
hw=max(xs)-min(xs); hd=max(ys)-min(ys); cx=(max(xs)+min(xs))/2; cy=(max(ys)+min(ys))/2
print('HEAD top %.3f width %.3f depth %.3f centre %.3f %.3f'%(top,hw,hd,cx,cy))
h=import_piece(MESHY/'helmet'/'model.glb','TS_Helmet')
lo,hi=bounds(h)
# inner shell width ~ 0.82 of the outer (ear cups stick out); scale so the shell clears the hair by MARGIN each side
s=(hd+2*MARGIN)/((hi-lo).y*0.93)
h.scale=(s,s,s); apply(h); lo,hi=bounds(h)
h.location=(cx-(lo.x+hi.x)/2, cy-(lo.y+hi.y)/2+0.006, top+MARGIN*0.9-hi.z-DROP); apply(h)
n0=penetration(h,body)
moved=push_out(h,body,offset=0.004,max_dist=0.05,smooth=6)
n1=penetration(h,body)
lo,hi=bounds(h)
print('HELMET scale %.4f size %s pen before %s moved %d after %s'%(s,[round(v,3) for v in hi-lo],n0,moved,n1))
clear_groups(h); skin_rigid(h,'Head'); print('UNWEIGHTED',ensure_weighted(h,'Head')); bind(h,arm)
export_skinned([h],arm,OUT/'out'/'TS_Helmet.glb')
render_views(str(OUT/'fit'/'helmet'),(cx,cy,top-0.12),0.42,views=('front','side','back','quarter'),res=(500,500))
