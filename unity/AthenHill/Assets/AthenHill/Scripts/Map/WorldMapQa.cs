using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// World map state and commands for the development QA bridge (NativeQa snapshot key "map"; commands "mapOpen" and
 /// "mapDiscover").
 public static class WorldMapQa
 {
  static float[] XZ(Vector2 v)=>new[]{v.x,v.y};
  /// u/v over the map's whole sheet (0..1, v up = north), so a check can compare marker positions without a layout.
  static float[] Sheet(Vector2 v){var b=WorldMapMath.DefaultBounds;return new[]{(v.x-b.xMin)/b.width,(v.y-b.yMin)/b.height};}
  public static object State(GameSession session)
  {
   var map=session?session.Map:null;
   if(!map)return new{installed=false};
   var marker=map.Tracked(out var mission);
   var panel=map.Panel;
   var respawn=map.RespawnStation;
   var survey=map.Survey;
   return new
   {
    installed=true,
    open=session.State==CityState.Map,
    discovered=map.DiscoveredIds.OrderBy(x=>x).ToArray(),
    places=map.Places.Select(p=>new{p.id,p.name,kind=p.kind.ToString(),shown=map.Shown(p),discovered=map.Discovered(p.id),cleared=map.Cleared(p),position=XZ(p.Position)}).ToArray(),
    tracked=new{mission=mission?.id,label=mission?.targetLabel,marker.shown,marker.area,marker.radius,world=marker.shown?XZ(marker.position):null,sheet=marker.shown?Sheet(marker.position):null,
     panel=marker.shown&&panel!=null&&panel.Shown?XZ(panel.View.WorldToPanel(marker.position)):null},
    respawn=respawn?respawn.Flag:"gate_post",
    lastDowned=map.LastDowned.HasValue?XZ(map.LastDowned.Value):null,
    survey=new{present=(bool)survey,layers=survey?survey.layers.Where(survey.Usable).Select(l=>l.id).ToArray():new string[0],shown=panel!=null&&panel.SurveyShown},
    view=panel!=null&&panel.Shown?new{centre=XZ(panel.View.centre),scale=panel.View.scale,size=XZ(panel.View.size)}:null,
   };
  }
  /// mapOpen {open}: opens or closes the map (opening works from plain play only, like M).
  public static void SetOpen(GameSession session,bool open)
  {
   if(open){if(session.State==CityState.Play)session.ToggleMap();if(session.State!=CityState.Map)throw new System.InvalidOperationException("The map opens from plain play only.");}
   else if(session.State==CityState.Map)session.ToggleMap();
  }
  /// mapDiscover {site}: marks a place discovered (development builds only).
  public static void Discover(GameSession session,string id)
  {
   var map=session?session.Map:null;
   if(!map)throw new System.InvalidOperationException("No world map in this scene.");
   if(map.Places.All(p=>p.id!=id))throw new System.ArgumentException("Unknown map place: "+id);
   map.Discover(id);
  }
 }
}
