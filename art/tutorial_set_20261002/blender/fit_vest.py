import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TOPZ=float(args[0]) if args else 1.50; MARGIN=float(args[1]) if len(args)>1 else 0.012
arm,body=load_final()
NECKZ=bone_head(arm,'neck').z; HIPZ=bone_head(arm,'Hips').z
TOPZ=NECKZ+TOPZ if TOPZ<0.5 else TOPZ
print('NECK %.3f HIPS %.3f TOP %.3f'%(NECKZ,HIPZ,TOPZ))
ws=world_verts(body)
band=[w for w in ws if NECKZ-0.25<w.z<NECKZ-0.17 and abs(w.x)<0.09]   # chest band inside the arms
xs=[w.x for w in band]; ys=[w.y for w in band]
cw=max(xs)-min(xs); cd=max(ys)-min(ys); cy=(max(ys)+min(ys))/2
print('CHEST width %.3f depth %.3f cy %.3f'%(cw,cd,cy))
c=import_piece(MESHY/'chest'/'model.glb','TS_FieldVest')
lo,hi=bounds(c); print('RAW',[round(v,3) for v in hi-lo])
FAC=float(args[2]) if len(args)>2 else 0.80
s=(cd+2*MARGIN)/((hi-lo).y*FAC)
c.scale=(s,s,s); apply(c); lo,hi=bounds(c)
c.location=(-(lo.x+hi.x)/2, cy-(lo.y+hi.y)/2, TOPZ-hi.z); apply(c)
CUT=float(args[3]) if len(args)>3 else 0.0
if 0<CUT<0.5: CUT=HIPZ+CUT
if CUT:
    bm=bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],plane_co=(0,0,CUT),plane_no=(0,0,1),clear_inner=True)
    bm.to_mesh(c.data); bm.free(); c.data.update()
lo,hi=bounds(c); print('FIT scale %.4f size %s z %.3f..%.3f'%(s,[round(v,3) for v in hi-lo],lo.z,hi.z))
print('STRIP',strip_inner(c,body)); n0=penetration(c,body); moved=push_out_smooth(c,body,offset=0.007,radius=0.07); n1=penetration(c,body)
print('PEN before',n0,'moved',moved,'after',n1)
clear_groups(c); skin_transfer(c,body,bones=['Hips','Spine02','Spine01','Spine','neck','LeftShoulder','RightShoulder','LeftArm','RightArm'])
print('UNWEIGHTED',ensure_weighted(c,'Spine')); bind(c,arm)
export_skinned([c],arm,OUT/'out'/'TS_FieldVest.glb')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fit'/'vest.blend'))
render_views(str(OUT/'fit'/'vest'),(0,0,1.2),0.95,views=('front','side','back','quarter'),res=(450,600))
