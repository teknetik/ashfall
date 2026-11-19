using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
namespace AthenHill
{
 /// The map's view of the world (19 Nov 2026): north-up, world X to the right and world Z up the sheet. The view is a
 /// centre in world metres (x, z), a scale in panel pixels per metre and the viewport size in panel pixels. Everything
 /// the panel draws goes through WorldToPanel, so the schematic, the survey picture and the markers can never disagree.
 [Serializable]
 public struct MapView
 {
  public Vector2 centre;
  public float scale;
  public Vector2 size;
  public MapView(Vector2 centre,float scale,Vector2 size){this.centre=centre;this.scale=scale;this.size=size;}
  /// World x/z (metres) to panel pixels (y grows downwards, so north is up).
  public Vector2 WorldToPanel(Vector2 world)=>new Vector2(size.x*.5f+(world.x-centre.x)*scale,size.y*.5f-(world.y-centre.y)*scale);
  public Vector2 WorldToPanel(Vector3 world)=>WorldToPanel(new Vector2(world.x,world.z));
  public Vector2 PanelToWorld(Vector2 panel)=>new Vector2(centre.x+(panel.x-size.x*.5f)/scale,centre.y-(panel.y-size.y*.5f)/scale);
  /// A world rectangle (x/z) as a panel rectangle (for the survey pictures).
  public Rect WorldRectToPanel(Rect world)
  {
   var a=WorldToPanel(new Vector2(world.xMin,world.yMax));var b=WorldToPanel(new Vector2(world.xMax,world.yMin));
   return Rect.MinMaxRect(a.x,a.y,b.x,b.y);
  }
  /// Moves the view by a panel-pixel drag (the sheet follows the pointer).
  public MapView Pan(Vector2 panelDelta){var v=this;v.centre+=new Vector2(-panelDelta.x/scale,panelDelta.y/scale);return v;}
  /// Zooms by factor, keeping the world point under the panel point still.
  public MapView ZoomAt(Vector2 panelPoint,float factor,float minScale,float maxScale)
  {
   var v=this;var anchor=PanelToWorld(panelPoint);
   v.scale=Mathf.Clamp(scale*factor,minScale,maxScale);
   v.centre=anchor-new Vector2((panelPoint.x-size.x*.5f)/v.scale,-(panelPoint.y-size.y*.5f)/v.scale);
   return v;
  }
  /// Keeps the view's centre inside the world bounds (the sheet can be pushed to its edge, never lost off screen).
  public MapView Clamp(Rect bounds){var v=this;v.centre=new Vector2(Mathf.Clamp(centre.x,bounds.xMin,bounds.xMax),Mathf.Clamp(centre.y,bounds.yMin,bounds.yMax));return v;}
  /// The scale at which bounds fill the viewport (with a margin in pixels).
  public static float FitScale(Rect bounds,Vector2 size,float margin=24)
  {
   if(bounds.width<=0||bounds.height<=0||size.x<=0||size.y<=0)return 1;
   return Mathf.Max(.01f,Mathf.Min((size.x-margin*2)/bounds.width,(size.y-margin*2)/bounds.height));
  }
 }

 /// A tracked-mission marker as the map shows it: a point, or an area when the target is a moving machine (the map
 /// is a navigator's sheet, not a radar, so a droid's live position is never drawn).
 public struct MapMarker
 {
  public bool shown,area;
  public Vector2 position;
  public float radius;
  public static readonly MapMarker None=new MapMarker();
 }

 /// Pure rules behind the world map (tested in WorldMapTests).
 public static class WorldMapMath
 {
  /// What the sheet covers: the city (x -60..60, z -45..45) and the Outer Berms bowl west of it (to about x -570).
  public static readonly Rect DefaultBounds=Rect.MinMaxRect(-600,-260,80,240);
  /// The city's walls (perimeter walls pass, 1 Oct 2026), for the city-scale default view and label switching.
  public static readonly Rect CityBounds=Rect.MinMaxRect(-60,-45,60,45);
  /// Panel pixels per metre: zoomed right in (a shop front is about 140 pixels wide).
  public const float MaxScale=14;
  /// Below this scale the city's shop names would overlap; one WARD label stands for them.
  public const float CityLabelScale=3.2f;

  /// Native QA (19 Nov 2026): label declutter. "Node 07 goods dock" sat on "Lattice Jack" at the city scale. When two
  /// labels would overlap at the current zoom the higher-priority one is shown (the place selected in the list wins),
  /// and the other reappears once zooming in separates them.
  public struct LabelBox{public string id;public Rect rect;public int priority;}
  public static int LabelPriority(MapPlaceKind k)=>k switch{MapPlaceKind.Home=>6,MapPlaceKind.Gate=>5,MapPlaceKind.Landmark=>5,MapPlaceKind.Site=>4,MapPlaceKind.Waystation=>4,MapPlaceKind.BermsPlace=>3,MapPlaceKind.Shop=>2,_=>1};
  /// Estimated label size in panel pixels (no layout pass is needed to declutter on the frame the view changes).
  public static Vector2 LabelSize(string text,float fontSize)=>new Vector2((text?.Length??0)*fontSize*.56f+4,fontSize+4);
  public static HashSet<string> Declutter(IEnumerable<LabelBox> boxes,string selected=null)
  {
   var list=new List<LabelBox>(boxes);
   list.Sort((a,b)=>{int pa=a.id==selected?int.MaxValue:a.priority,pb=b.id==selected?int.MaxValue:b.priority;return pa!=pb?pb.CompareTo(pa):string.CompareOrdinal(a.id,b.id);});
   var kept=new List<Rect>();var hidden=new HashSet<string>(StringComparer.Ordinal);
   foreach(var b in list){bool clash=false;foreach(var k in kept)if(k.Overlaps(b.rect)){clash=true;break;}if(clash)hidden.Add(b.id);else kept.Add(b.rect);}
   return hidden;
  }

  /// A scale bar of a round length (1, 2 or 5 × 10^n metres) whose drawn length lies between minPixels and about
  /// 2.5 × minPixels.
  public static float ScaleBarMetres(float scale,float minPixels=70)
  {
   if(scale<=0||float.IsNaN(scale)||float.IsInfinity(scale))return 0;
   float wanted=minPixels/scale;
   float p=Mathf.Pow(10,Mathf.Floor(Mathf.Log10(wanted)));
   foreach(var m in new[]{1f,2f,5f,10f})if(m*p>=wanted-1e-4f)return m*p;
   return 10*p;
  }
  public static string MetresText(float metres)=>metres>=1000?$"{metres/1000:0.#} km":$"{metres:0} m";

  /// A stable id from a display name: "Fallen Tube pylon" -> "fallen_tube_pylon".
  public static string Slug(string name)
  {
   if(string.IsNullOrEmpty(name))return "";
   var sb=new StringBuilder(name.Length);bool gap=false;
   foreach(char c in name.ToLowerInvariant())
   {
    if(c>='a'&&c<='z'||c>='0'&&c<='9'){if(gap&&sb.Length>0)sb.Append('_');sb.Append(c);gap=false;}
    else gap=true;
   }
   return sb.ToString();
  }

  /// Discovery: the player stood within radius of the site, measured on the ground plane (a site on a knoll is found
  /// from its foot).
  public static bool WithinRadius(Vector3 player,Vector3 site,float radius)
  {
   float dx=player.x-site.x,dz=player.z-site.z;
   return radius>0&&dx*dx+dz*dz<=radius*radius;
  }

  /// The tracked mission's marker. A fixed target (a colonist, a terminal, the home locker) is a point. A machine
  /// target is shown as an area: centred on the nearest known site within snapRadius, else on the target snapped to a
  /// 25 m grid, so the sheet never tracks a droid.
  public static MapMarker TrackedMarker(Vector3? target,bool machine,IReadOnlyList<Vector2> sites,float snapRadius=120,float areaRadius=35)
  {
   if(!target.HasValue)return MapMarker.None;
   var p=new Vector2(target.Value.x,target.Value.z);
   if(float.IsNaN(p.x)||float.IsNaN(p.y))return MapMarker.None;
   if(!machine)return new MapMarker{shown=true,position=p};
   Vector2? best=null;float bestD=snapRadius*snapRadius;
   if(sites!=null)foreach(var s in sites){float d=(s-p).sqrMagnitude;if(d<=bestD){bestD=d;best=s;}}
   var centre=best??new Vector2(Mathf.Round(p.x/25)*25,Mathf.Round(p.y/25)*25);
   return new MapMarker{shown=true,area=true,position=centre,radius=areaRadius};
  }

  /// Angle for the player arrow: compass heading in degrees (0 = north, clockwise) to a panel rotation.
  public static Vector2 HeadingToPanel(float headingDegrees)
  {
   float r=headingDegrees*Mathf.Deg2Rad;
   return new Vector2(Mathf.Sin(r),-Mathf.Cos(r));
  }
 }
}
