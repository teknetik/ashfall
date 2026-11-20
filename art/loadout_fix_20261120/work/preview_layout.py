"""Python port of AnatomyLayout.Arrange for a quick offline preview (not used by the game)."""
import subprocess, sys
BW,BH,SP,GAP,INS,MM=112,50,6,10,160,12
CBW=88
ASP=1024/1536; FL,FR=.13,.87
IMPL=[("head",512,80,0),("eye",540,131,1),("arms",683,410,1),("chest",512,385,0),("wrist",792,735,1),("waist",512,590,0),("hand",810,782,1),("legs",415,880,0),("feet",653,1413,1)]
ARM=[("head",512,80,0),("arms",683,410,1),("chest",512,385,0),("storage",650,318,1),("hands",810,782,1),("legs",415,880,0),("feet",653,1413,1)]
def stack(des,H):
    pitch=BH+SP;n=len(des)
    if n and n*pitch-SP>H: pitch=(H-BH)/(n-1)
    groups=[]
    for i,d in enumerate(des):
        groups.append([i,1,d-BH/2])
        while True:
            g=groups[-1]; g[2]=min(max(g[2],0),max(0,H-((g[1]-1)*pitch+BH)))
            if len(groups)==1: break
            p=groups[-2]
            if p[2]+p[1]*pitch-SP<=g[2]+.01: break
            first,count=p[0],p[1]+g[1]; s=sum(des[first+k]-BH/2-k*pitch for k in range(count))
            groups.pop(); groups[-1]=[first,count,s/count]
    return [g[2]+k*pitch+BH/2 for g in groups for k in range(g[1])]
def arrange(slots,W,H):
    fig=FR-FL;full=H*ASP
    fit=lambda b:min(full,max(40,(max(2*(b+GAP)+40,W-INS-MM)-2*(b+GAP))/fig))
    iw=fit(BW);bw=BW
    if iw<full-.5:
        c=fit(CBW)
        if c>iw*1.1: iw=c;bw=CBW
    global BWX;BWX=bw
    side=bw+GAP;mw=2*side+iw*fig
    ih=iw/ASP; img=(side-FL*iw,(H-ih)/2,iw,ih)
    out={}
    for n,x,y,r in slots: out[n]=dict(node=(img[0]+x/1024*iw,img[1]+y/1536*ih),right=r)
    for r in (0,1):
        col=sorted([k for k in out if out[k]['right']==r],key=lambda k:out[k]['node'][1])
        cs=stack([out[k]['node'][1] for k in col],H)
        for k,c in zip(col,cs):
            x=mw-BWX if r else 0; out[k]['box']=(x,c-BH/2); out[k]['start']=(x if r else BWX,c)
    return mw,img,out
def draw(slots,W,H,path,S=2):
    mw,img,out=arrange(slots,W,H)
    cmd=['magick','-size',f'{int(mw*S)}x{int(H*S)}','xc:#0c1d22','(', '/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Resources/UI/ImplantBody.png','-resize',f'{int(img[2]*S)}x{int(img[3]*S)}!',')','-geometry',f'+{int(img[0]*S)}+{int(img[1]*S)}','-composite']
    for k,v in out.items():
        sx,sy=v['start'];nx,ny=v['node'];bx,by=v['box']
        cmd+=['-stroke','#58b9c2','-strokewidth','2','-draw',f'line {sx*S},{sy*S} {nx*S},{ny*S}','-fill','#071d23','-stroke','#426166','-draw',f'rectangle {bx*S},{by*S} {(bx+BWX)*S},{(by+BH)*S}','-fill','#16434b','-stroke','#83e2e3','-draw',f'circle {nx*S},{ny*S} {nx*S+9},{ny*S}','-stroke','none','-fill','#bca581','-pointsize','24','-draw',f'text {(bx+30)*S},{(by+30)*S} "{k.upper()}"']
    subprocess.run(cmd+[path],check=True); print(path,round(mw),[round(x) for x in img])
draw(ARM,510,447,'prev_armour_510x447.png'); draw(ARM,654,450,'prev_armour_654x450.png')