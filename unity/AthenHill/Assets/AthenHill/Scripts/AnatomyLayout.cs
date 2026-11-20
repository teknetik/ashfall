using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Body map of the IMPLANTS and ARMOUR loadout pages (20 Nov 2026, art/loadout_fix_20261120). Every slot has an anchor
 /// on the figure image itself (Resources/UI/ImplantBody.png, 1024 × 1536), stored as a fraction of the image (u right,
 /// v down) and the box column it uses. Arrange() fits the image into the map, puts the slot boxes in a column either side
 /// of the figure, close to their anchors' heights, and returns where each leader starts and the dot it ends on, in map
 /// pixels. The leader ends exactly on the anchor at any window size, because both come from the same image rectangle.
 /// To move a dot, edit the table below (measure on the 1024 × 1536 image: u = x / 1024, v = y / 1536).
 public static class AnatomyLayout
 {
  /// Slot box size (the .anatomy-slot USS rule matches), the space between stacked boxes, and the gap between a box
  /// column and the figure.
  public const float BoxWidth=112,BoxHeight=50,BoxSpacing=6,LeaderGap=10;
  /// Narrower boxes without the item illustration, used when the page is too narrow for the figure at full height
  /// (for example the ARMOUR page beside the colonist preview in a 4:3 window).
  public const float CompactBoxWidth=88;
  /// The inspector beside the map keeps at least this width (reference pixels); the map gives way first.
  public const float InspectorMinimum=160,MapMargin=12,FallbackWidth=900,FallbackHeight=400;
  /// The figure image's width / height.
  public const float ImageAspect=1024f/1536f;
  /// Horizontal extent of the figure (fingertip to fingertip) as fractions of the image width. The black margin outside
  /// it may sit under the boxes; every anchor lies inside it.
  public const float FigureLeft=.13f,FigureRight=.87f;

  public struct Anchor
  {
   public Vector2 uv;public bool right;public string part;
   public Anchor(string part,float x,float y,bool right){this.part=part;uv=new Vector2(x/1024f,y/1536f);this.right=right;}
  }
  // Pixel positions on the 1024 × 1536 figure. "Right" boxes sit on the image's right, which is the figure's left side.
  static readonly Anchor[] implantAnchors=
  {
   new Anchor("head",512,80,false),   // cranium
   new Anchor("eye",540,131,true),    // the eye socket on the image's right
   new Anchor("arms",683,410,true),   // upper arm (humerus)
   new Anchor("chest",512,385,false), // sternum
   new Anchor("wrist",792,735,true),  // wrist (carpals)
   new Anchor("waist",512,590,false), // waist (lumbar spine)
   new Anchor("hand",810,782,true),   // palm
   new Anchor("legs",415,880,false),  // thigh (femur)
   new Anchor("feet",653,1413,true),  // foot
  };
  static readonly Anchor[] armourAnchors=
  {
   new Anchor("head",512,80,false),
   new Anchor("arms",683,410,true),
   new Anchor("chest",512,385,false),
   new Anchor("storage",650,318,true), // shoulder, where the pack straps sit
   new Anchor("hands",810,782,true),
   new Anchor("legs",415,880,false),
   new Anchor("feet",653,1413,true),
  };
  /// The body part a slot id names: "implant_eye" → "eye", "armour_hands" → "hands", "storage" → "storage".
  public static string Part(string slotId)=>string.IsNullOrEmpty(slotId)?"":slotId.Contains("_")?slotId.Substring(slotId.IndexOf('_')+1):slotId;
  public static IReadOnlyList<Anchor> Anchors(bool implants)=>implants?implantAnchors:armourAnchors;
  public static bool TryAnchor(bool implants,string slotId,out Anchor anchor)
  {
   string part=Part(slotId);
   foreach(var a in Anchors(implants))if(a.part==part){anchor=a;return true;}
   anchor=default;return false;
  }
  /// The slot's anchor, or for a slot the table does not know, a point on the spine spread by its index (so a new slot
  /// still gets a box and a leader until it is given a proper anchor here).
  public static Anchor AnchorFor(bool implants,string slotId,int index,int count)
  {
   if(TryAnchor(implants,slotId,out var a))return a;
   float v=.1f+.8f*(count>1?index/(float)(count-1):.5f);
   return new Anchor(Part(slotId),512,v*1536,index%2==1);
  }

  public sealed class Placement {public string id;public Rect box;public Vector2 node,leaderStart;public bool right;}
  public sealed class Result {public float mapWidth,mapHeight,boxWidth=BoxWidth;public bool compact;public Rect image;public List<Placement> slots=new List<Placement>();}

  /// Lays the map out in a space availableWidth × height (the anatomy row: map plus inspector). Returns the map width,
  /// the image rectangle and, per slot, its box, leader start (the box edge facing the figure) and node (the anchor).
  public static Result Arrange(IList<(string id,Anchor anchor)> slots,float availableWidth,float height)
  {
   if(float.IsNaN(height)||height<=0)height=FallbackHeight;
   if(float.IsNaN(availableWidth)||availableWidth<=0)availableWidth=FallbackWidth;
   float figure=FigureRight-FigureLeft,full=height*ImageAspect;
   float Fit(float box)=>Mathf.Min(full,Mathf.Max(40,(Mathf.Max(2*(box+LeaderGap)+40,availableWidth-InspectorMinimum-MapMargin)-2*(box+LeaderGap))/figure));
   float imageWidth=Fit(BoxWidth),boxWidth=BoxWidth;bool compact=false;
   // Short of room, the compact boxes give the figure back at least a tenth of its size.
   if(imageWidth<full-.5f){float c=Fit(CompactBoxWidth);if(c>imageWidth*1.1f){imageWidth=c;boxWidth=CompactBoxWidth;compact=true;}}
   float side=boxWidth+LeaderGap,mapWidth=2*side+imageWidth*figure,imageHeight=imageWidth/ImageAspect;
   var r=new Result{mapWidth=mapWidth,mapHeight=height,boxWidth=boxWidth,compact=compact,image=new Rect(side-FigureLeft*imageWidth,(height-imageHeight)/2,imageWidth,imageHeight)};
   foreach(var s in slots)
   {
    var node=new Vector2(r.image.x+s.anchor.uv.x*r.image.width,r.image.y+s.anchor.uv.y*r.image.height);
    r.slots.Add(new Placement{id=s.id,node=node,right=s.anchor.right});
   }
   foreach(bool right in new[]{false,true})
   {
    var column=r.slots.Where(p=>p.right==right).OrderBy(p=>p.node.y).ToList();
    var centres=Stack(column.Select(p=>p.node.y).ToList(),height);
    for(int i=0;i<column.Count;i++)
    {
     var p=column[i];float x=right?mapWidth-boxWidth:0;
     p.box=new Rect(x,centres[i]-BoxHeight/2,boxWidth,BoxHeight);
     p.leaderStart=new Vector2(right?x:boxWidth,centres[i]);
    }
   }
   return r;
  }
  /// Box centres for one column: each as close to its anchor's height as the boxes allow, never overlapping, inside
  /// 0…height. Overlapping boxes merge into a group centred on their anchors' mean (the usual label-stacking method).
  static List<float> Stack(List<float> desired,float height)
  {
   float pitch=BoxHeight+BoxSpacing;int n=desired.Count;
   // When the column cannot fit, the pitch shrinks so the boxes still share the height evenly.
   if(n>0&&n*pitch-BoxSpacing>height)pitch=n>1?(height-BoxHeight)/(n-1):pitch;
   var groups=new List<(int first,int count,float top)>();
   for(int i=0;i<n;i++)
   {
    groups.Add((i,1,desired[i]-BoxHeight/2));
    while(true)
    {
     int g=groups.Count-1;
     var cur=groups[g];
     cur.top=Clamp(cur,height,pitch);groups[g]=cur;
     if(g==0)break;
     var prev=groups[g-1];
     if(prev.top+prev.count*pitch-BoxSpacing<=cur.top+.01f)break;
     int first=prev.first,count=prev.count+cur.count;float sum=0;
     for(int k=0;k<count;k++)sum+=desired[first+k]-BoxHeight/2-k*pitch;
     groups.RemoveAt(g);groups[g-1]=(first,count,sum/count);
    }
   }
   var centres=new List<float>(n);
   foreach(var g in groups)for(int k=0;k<g.count;k++)centres.Add(g.top+k*pitch+BoxHeight/2);
   return centres;
  }
  static float Clamp((int first,int count,float top) g,float height,float pitch)=>Mathf.Clamp(g.top,0,Mathf.Max(0,height-((g.count-1)*pitch+BoxHeight)));

  /// True when segment a–b crosses segment c–d (shared end points do not count).
  public static bool SegmentsCross(Vector2 a,Vector2 b,Vector2 c,Vector2 d)
  {
   float Cross(Vector2 o,Vector2 p,Vector2 q)=>(p.x-o.x)*(q.y-o.y)-(p.y-o.y)*(q.x-o.x);
   float d1=Cross(c,d,a),d2=Cross(c,d,b),d3=Cross(a,b,c),d4=Cross(a,b,d);
   return (d1>0&&d2<0||d1<0&&d2>0)&&(d3>0&&d4<0||d3<0&&d4>0);
  }
  /// True when segment a–b passes through the inside of the rectangle (touching its edge does not count).
  public static bool SegmentEntersRect(Vector2 a,Vector2 b,Rect r,float inset=.5f)
  {
   var inner=new Rect(r.x+inset,r.y+inset,r.width-2*inset,r.height-2*inset);
   if(inner.Contains(a)||inner.Contains(b))return true;
   var c=new[]{new Vector2(inner.xMin,inner.yMin),new Vector2(inner.xMax,inner.yMin),new Vector2(inner.xMax,inner.yMax),new Vector2(inner.xMin,inner.yMax)};
   for(int i=0;i<4;i++)if(SegmentsCross(a,b,c[i],c[(i+1)%4]))return true;
   return false;
  }
 }
}
