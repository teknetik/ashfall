using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 19 Nov 2026: the world map's pure rules (view transform, scale bar, discovery, old saves, the tracked marker) and
 /// its key binding.
 public class WorldMapTests
 {
  static MapView View()=>new MapView(new Vector2(-100,20),2,new Vector2(1000,600));

  [Test] public void ViewMapsWorldToPanelNorthUpAndBack()
  {
   var v=View();
   Assert.That(v.WorldToPanel(new Vector2(-100,20)),Is.EqualTo(new Vector2(500,300)));
   var north=v.WorldToPanel(new Vector2(-100,70));var east=v.WorldToPanel(new Vector2(-50,20));
   Assert.That(north.y,Is.EqualTo(200).Within(1e-3),"50 m north is 100 px up");
   Assert.That(east.x,Is.EqualTo(600).Within(1e-3),"50 m east is 100 px right");
   foreach(var w in new[]{new Vector2(-580,-250),new Vector2(60,44),new Vector2(0,0)})
    Assert.That((v.PanelToWorld(v.WorldToPanel(w))-w).magnitude,Is.LessThan(1e-3f));
   Assert.That(v.WorldToPanel(new Vector3(-100,55,20)),Is.EqualTo(new Vector2(500,300)),"height does not move a point on the sheet");
   var r=v.WorldRectToPanel(Rect.MinMaxRect(-110,10,-90,30));
   Assert.That(r.xMin,Is.EqualTo(480).Within(1e-3));Assert.That(r.yMin,Is.EqualTo(280).Within(1e-3),"the rectangle's north edge is its top");
   Assert.That(r.width,Is.EqualTo(40).Within(1e-3));Assert.That(r.height,Is.EqualTo(40).Within(1e-3));
  }

  [Test] public void ZoomKeepsThePointUnderThePointerAndPanFollowsTheDrag()
  {
   var v=View();var at=new Vector2(800,150);var under=v.PanelToWorld(at);
   var z=v.ZoomAt(at,2.5f,.5f,14);
   Assert.That(z.scale,Is.EqualTo(5).Within(1e-4));
   Assert.That((z.PanelToWorld(at)-under).magnitude,Is.LessThan(1e-3f));
   Assert.That(v.ZoomAt(at,100,.5f,14).scale,Is.EqualTo(14),"zoom is clamped");
   var grabbed=v.PanelToWorld(new Vector2(300,300));
   var p=v.Pan(new Vector2(40,-25));
   Assert.That((p.WorldToPanel(grabbed)-new Vector2(340,275)).magnitude,Is.LessThan(1e-3f),"the sheet moves with the pointer");
   var c=new MapView(new Vector2(5000,-5000),1,new Vector2(10,10)).Clamp(WorldMapMath.DefaultBounds);
   Assert.That(c.centre,Is.EqualTo(new Vector2(WorldMapMath.DefaultBounds.xMax,WorldMapMath.DefaultBounds.yMin)));
   Assert.That(MapView.FitScale(WorldMapMath.DefaultBounds,new Vector2(1048,1048),24),Is.EqualTo(1000f/680).Within(1e-4));
  }

  [Test] public void ScaleBarUsesRoundLengthsOfAReadableSize()
  {
   foreach(float s in new[]{.4f,1,1.3f,2.2f,6,14})
   {
    float m=WorldMapMath.ScaleBarMetres(s);float px=m*s;
    float mant=m/Mathf.Pow(10,Mathf.Floor(Mathf.Log10(m)));
    Assert.That(new[]{1f,2f,5f}.Any(x=>Mathf.Abs(x-mant)<1e-3f),$"{m} m is 1, 2 or 5 × 10^n");
    Assert.That(px,Is.InRange(69.9f,70*2.5f+.1f),$"scale {s}: {px} px");
   }
   Assert.That(WorldMapMath.MetresText(200),Is.EqualTo("200 m"));Assert.That(WorldMapMath.MetresText(2000),Is.EqualTo("2 km"));
  }

  [Test] public void SlugsAreStableIds()
  {
   Assert.That(WorldMapMath.Slug("Fallen Tube pylon"),Is.EqualTo("fallen_tube_pylon"));
   Assert.That(WorldMapMath.Slug("  Air + Water "),Is.EqualTo("air_water"));
   Assert.That(WorldMapMath.Slug(null),Is.EqualTo(""));
  }

  [Test] public void ASiteIsDiscoveredOnceWithinItsRadiusOnTheGround()
  {
   var d=new WorldMapDiscovery();
   var site=new MapPlace("site:relay_knoll","Relay knoll",MapPlaceKind.Site,-330,8,55);
   var city=new MapPlace("city:salvage","Salvage",MapPlaceKind.Shop,-19.8f,18);
   Assert.That(d.Visit(new Vector3(-250,0,8),new[]{site,city}),Is.Empty,"80 m away");
   Assert.That(d.Has(site.id),Is.False);
   var now=d.Visit(new Vector3(-280,30,8),new[]{site,city});
   Assert.That(now.Select(p=>p.id),Is.EqualTo(new[]{site.id}),"50 m away on the plane, 30 m lower");
   Assert.That(d.Visit(new Vector3(-330,0,8),new[]{site,city}),Is.Empty,"found once");
   Assert.That(d.Visit(new Vector3(-19.8f,0,18),new[]{city}),Is.Empty,"city places are never 'discovered', they are always known");
   Assert.That(WorldMapMath.WithinRadius(Vector3.zero,new Vector3(3,0,4),5),Is.True);
   Assert.That(WorldMapMath.WithinRadius(Vector3.zero,new Vector3(3,0,4.01f),5),Is.False);
  }

  [Test] public void OverlappingLabelsKeepTheHigherPriorityOneOrTheSelectedPlace()
  {
   // Native QA 19 Nov 2026: "Node 07 goods dock" (service) sat on "Lattice Jack" (landmark) at the city scale.
   var jack=new WorldMapMath.LabelBox{id="city:lattice_jack",rect=new Rect(100,100,90,19),priority=WorldMapMath.LabelPriority(MapPlaceKind.Landmark)};
   var dock=new WorldMapMath.LabelBox{id="city:goods_dock",rect=new Rect(130,104,130,17),priority=WorldMapMath.LabelPriority(MapPlaceKind.Service)};
   var far=new WorldMapMath.LabelBox{id="city:salvage",rect=new Rect(400,300,60,17),priority=WorldMapMath.LabelPriority(MapPlaceKind.Shop)};
   Assert.That(WorldMapMath.Declutter(new[]{dock,jack,far}),Is.EquivalentTo(new[]{"city:goods_dock"}));
   Assert.That(WorldMapMath.Declutter(new[]{dock,jack,far},"city:goods_dock"),Is.EquivalentTo(new[]{"city:lattice_jack"}),"the place chosen in the list wins");
   dock.rect=new Rect(130,140,130,17);   // zoomed in: the two no longer touch
   Assert.That(WorldMapMath.Declutter(new[]{dock,jack,far}),Is.Empty);
  }

  [Test] public void ThePrimerDepotIsNotDiscoveredBeforeThePrimerSendsThePlayerThere()
  {
   // Native QA 19 Nov 2026: a new game walking out of the gate passed within 55 m of the depot and marked it.
   var depot=new MapPlace(WorldMapDiscovery.DepotId,"Machine depot",MapPlaceKind.Site,-80,-40,55);
   var knoll=new MapPlace("site:relay_knoll","Relay knoll",MapPlaceKind.Site,-330,8,55);
   var nearDepot=new Vector3(-54,0,5);   // the primer's walk out of the gate, ~51 m from the depot
   foreach(var step in new[]{BermsStep.Approach,BermsStep.TakePistol,BermsStep.Draw,BermsStep.Targets,BermsStep.FirstContact})
   {
    var d=new WorldMapDiscovery();
    Assert.That(d.Visit(nearDepot,new[]{depot},id=>WorldMapDiscovery.PrimerAllows(id,step)),Is.Empty,step.ToString());
    Assert.That(d.Visit(new Vector3(-330,0,8),new[]{knoll},id=>WorldMapDiscovery.PrimerAllows(id,step)).Count,Is.EqualTo(1),"other sites keep the radius rule at "+step);
   }
   foreach(var step in new[]{BermsStep.Depot,BermsStep.Complete})
   {
    var d=new WorldMapDiscovery();
    Assert.That(d.Visit(nearDepot,new[]{depot},id=>WorldMapDiscovery.PrimerAllows(id,step)).Select(p=>p.id),Is.EqualTo(new[]{depot.id}),step.ToString());
   }
  }

  [Test] public void AnOldSaveLoadsWithOnlyWhatItsProgressImplies()
  {
   // a version 4 save written before the map existed (shaped like a mid-game save: primer done, home leased)
   const string old="{\"version\":4,\"credits\":120,\"bermsStep\":\"Complete\",\"hasPistol\":true,\"city\":{\"visitedHill\":true,\"flags\":[\"home_asked\",\"home_leased\",\"waystation:berms_mid\"]},\"journal\":{\"tracked\":\"\",\"chosen\":false}}";
   Assert.That(WardSaveFile.TryParse(old,out var data,out var error),error);
   Assert.That(data.map==null||data.map.discovered==null||data.map.discovered.Length==0,"no map state in the old save");
   var d=new WorldMapDiscovery();
   d.Restore(data.map,WorldMapDiscovery.Implied(data.city.flags,data.bermsStep=="Complete"));
   Assert.That(d.Found.OrderBy(x=>x),Is.EqualTo(new[]{WorldMapDiscovery.DepotId,"waystation:berms_mid"}));
   Assert.That(WorldMapDiscovery.Downed(data.map),Is.Null);
   // before the primer is done and without a waystation: nothing at all
   var fresh=new WorldMapDiscovery();fresh.Add("site:stale");
   fresh.Restore(null,WorldMapDiscovery.Implied(new[]{"home_asked"},false));
   Assert.That(fresh.Found,Is.Empty,"restore replaces what was there");
  }

  [Test] public void MapStateRoundTripsThroughTheSaveFile()
  {
   var d=new WorldMapDiscovery();d.Add("site:northgate_scrap");d.Add("waystation:berms_mid");
   var data=new WardSaveData{version=WardSaveData.CurrentVersion,credits=5,map=d.Capture(new Vector2(-210.5f,-40))};
   Assert.That(WardSaveFile.TryParse(WardSaveFile.Serialize(data),out var back,out var error),error);
   var e=new WorldMapDiscovery();e.Restore(back.map,WorldMapDiscovery.Implied(null,false));
   Assert.That(e.Found.OrderBy(x=>x),Is.EqualTo(new[]{"site:northgate_scrap","waystation:berms_mid"}));
   Assert.That(WorldMapDiscovery.Downed(back.map),Is.EqualTo(new Vector2(-210.5f,-40)));
   Assert.That(WardSaveData.CurrentVersion,Is.EqualTo(4),"the map is additive: older v4 readers ignore it");
  }

  [Test] public void TheTrackedMarkerIsAPointOrAnAreaNeverADroid()
  {
   Assert.That(WorldMapMath.TrackedMarker(null,false,null).shown,Is.False);
   var linn=WorldMapMath.TrackedMarker(new Vector3(1.5f,4,-2),false,null);
   Assert.That(linn.shown&&!linn.area,Is.True);Assert.That(linn.position,Is.EqualTo(new Vector2(1.5f,-2)));
   var sites=new[]{new Vector2(-330,8),new Vector2(-205,74)};
   var gunner=WorldMapMath.TrackedMarker(new Vector3(-311,0,30),true,sites);
   Assert.That(gunner.area,Is.True);Assert.That(gunner.position,Is.EqualTo(new Vector2(-330,8)),"a droid near a site marks the site");
   Assert.That(gunner.radius,Is.GreaterThan(0));
   var stray=WorldMapMath.TrackedMarker(new Vector3(-511.3f,0,-188.9f),true,sites);
   Assert.That(stray.area,Is.True);Assert.That(stray.position,Is.EqualTo(new Vector2(-500,-200)),"far from any site: a 25 m grid square, not the droid");
  }

  [Test] public void SchematicPlacesSitOnTheSheet()
  {
   foreach(var p in WorldMapSchematic.CityPlaces())Assert.That(Rect.MinMaxRect(-60,-45,60,45).Contains(p.position)||p.kind==MapPlaceKind.Gate,p.id);
   foreach(var p in WorldMapSchematic.BermsPlaces())Assert.That(WorldMapMath.DefaultBounds.Contains(p.position),p.id);
   foreach(var b in WorldMapSchematic.Bowl)Assert.That(WorldMapMath.DefaultBounds.Contains(b),b.ToString());
   var ids=WorldMapSchematic.CityPlaces().Concat(WorldMapSchematic.BermsPlaces()).Select(p=>p.id).ToList();
   Assert.That(ids.Distinct().Count(),Is.EqualTo(ids.Count));
  }

  /// 19 Nov 2026 (Carl): "West Gate" is the -X portal by the market into the Berms; the +X spawn arches are the East
  /// Gate. Positions decide which gate a label belongs to.
  [Test] public void GateLabelsFollowTheCompass()
  {
   var east=WorldMapSchematic.CityPlaces().Single(p=>p.id=="city:barred_gates");
   var west=WorldMapSchematic.BermsPlaces().Single(p=>p.id=="berms:west_gate");
   Assert.That(east.name,Is.EqualTo("East Gate"));Assert.That(east.position.x,Is.GreaterThan(45),"the East Gate is the +X spawn arches");
   Assert.That(west.name,Is.EqualTo("West Gate"));Assert.That(west.position.x,Is.LessThan(-55),"the West Gate is the -X Berms portal");
   var all=WorldMapSchematic.CityPlaces().Concat(WorldMapSchematic.BermsPlaces()).ToList();
   Assert.That(all.Where(p=>p.name.Contains("West Gate")).All(p=>p.position.x<0),"no +X place is called West Gate");
   Assert.That(all.Where(p=>p.name.Contains("East Gate")).All(p=>p.position.x>0),"no -X place is called East Gate");
  }

  [Test] public void MOpensTheMapAndNothingElse()
  {
   var input=JObject.Parse(File.ReadAllText("Assets/AthenHill/Data/Controls.inputactions"));
   var maps=input["maps"].Children<JObject>().ToList();
   var onM=maps.SelectMany(m=>m["bindings"].Children<JObject>().Where(b=>(string)b["path"]=="<Keyboard>/m").Select(b=>(string)m["name"]+"/"+(string)b["action"])).ToList();
   Assert.That(onM,Is.EqualTo(new[]{"UI/Map"}));
   var ids=maps.SelectMany(m=>m["actions"].Children<JObject>()).Select(a=>(string)a["id"]).ToList();
   Assert.That(ids.Distinct().Count(),Is.EqualTo(ids.Count),"action ids are unique");
  }
 }
}
