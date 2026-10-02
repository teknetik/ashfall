using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Second fix batch after the native re-QA (30 Sep 2026): Tab stays in the modal, stale radio lines drop and urgent
 /// ones jump the queue, caches find a flat clear spot, the cache glow ranks rare > uncommon > common, and the feral
 /// droids cull with bounds that still cover every clip.
 public class GameplayV2Batch2Tests
 {
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  readonly List<GameObject> made=new List<GameObject>();
  [TearDown] public void Clean(){foreach(var g in made)if(g)Object.DestroyImmediate(g);made.Clear();}
  GameObject Box(string name,Vector3 centre,Vector3 size)
  {
   var g=new GameObject(name);g.transform.position=centre;g.AddComponent<BoxCollider>().size=size;made.Add(g);return g;
  }

  MerchantPanel Merchant(VisualElement root)
  {
   var go=new GameObject("merchant focus test");go.SetActive(false);made.Add(go);
   var session=go.AddComponent<GameSession>();session.catalog=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   typeof(GameSession).GetProperty("Shop").SetValue(session,new ShopModel(session.catalog.items));typeof(GameSession).GetProperty("State").SetValue(session,CityState.Shop);
   var panel=new MerchantPanel(root,session,null);panel.Refresh();return panel;
  }

  // ------------------------------------------------------------------ focus
  [Test] public void TabCyclesOnlyThroughTheModalsOwnControls()
  {
   Assert.That(UiNavigation.Cycle(-1,4,true),Is.EqualTo(0));Assert.That(UiNavigation.Cycle(-1,4,false),Is.EqualTo(3));
   Assert.That(UiNavigation.Cycle(3,4,true),Is.EqualTo(0),"wraps");Assert.That(UiNavigation.Cycle(0,4,false),Is.EqualTo(3));
   var root=Hud();Merchant(root);
   var shop=UiNavigation.TabStops(root.Q("modal"));
   Assert.That(shop,Is.Not.Empty);
   Assert.That(shop.Any(v=>v is Scroller||v.GetFirstAncestorOfType<Scroller>()!=null||v.name=="unity-slider"),Is.False,"no scrollbars in the Tab cycle");
   Assert.That(shop.Any(v=>root.Q("hud").Contains(v)),Is.False,"nothing behind the modal");
   Assert.That(shop.Select(v=>v.name),Does.Contain("close").And.Contain("merchant-tab-buy").And.Contain("merchant-tab-sell").And.Contain("merchant-trade"));
   // A disabled control is skipped; a field that delegates focus is one stop.
   var scope=new VisualElement();var a=new Button{name="a"};var b=new Button{name="b"};b.SetEnabled(false);var field=new TextField{name="field"};var scroll=new ScrollView();var inner=new Button{name="inner"};scroll.Add(inner);
   scope.Add(a);scope.Add(b);scope.Add(field);scope.Add(scroll);
   var stops=UiNavigation.TabStops(scope).Select(v=>v.name).ToList();
   Assert.That(stops,Does.Contain("a").And.Contain("inner"));Assert.That(stops,Does.Not.Contain("b"));
   Assert.That(stops.Count(n=>n=="field")+UiNavigation.TabStops(scope).Count(v=>field.Contains(v)&&v!=field),Is.LessThanOrEqualTo(1),"one stop per field");
  }

  [Test] public void BasicGeneralLayoutAndInventoryDetails()
  {
   var root=Hud();Merchant(root);
   Assert.That(root.Q("merchant-balance").parent,Is.EqualTo(root.Q("merchant-toolbar")),"the balance stays above both browsing and checkout");
   Assert.That(root.Q("merchant-columns").Children().Select(c=>c.name),Is.EqualTo(new[]{"merchant-browser","merchant-detail"}),"scrollable stock stays left of its inspector");
   Assert.That(root.Q("inventory-details").parent,Is.EqualTo(root.Q("inventory-content")));
   Assert.That(root.Q("inventory-content").Children().Take(2).Select(c=>c.name),Is.EqualTo(new[]{"pack-col","inventory-details"}),"item detail is immediately beside the grid");
   var uss=System.IO.File.ReadAllText("Assets/AthenHill/UI/CityHUD.uss");
   Assert.That(uss,Does.Contain("#fabricator-craft:disabled"));
   Assert.That(System.Text.RegularExpressions.Regex.Match(uss,@"\.inventory-details \{[^}]*\}").Value,Does.Not.Contain("position: absolute"));
  }

  // ------------------------------------------------------------------ radio
  [Test] public void StaleLinesDropAndUrgentLinesJumpTheQueue()
  {
   int index=2;
   var radio=new RadioQueue{IsStale=tag=>FieldOrders.IsStale(tag,index)};
   Assert.That(radio.Say("Order two done.","Ossa",0,FieldOrders.RadioTag(1,"done")));
   radio.Say("Order three briefing.","Ossa",4.5f,FieldOrders.RadioTag(2,"brief"));
   // Order three is completed inside the fabricator (the radio clock is stopped there).
   index=3;
   radio.Say("Order three done.","Ossa",0,FieldOrders.RadioTag(2,"done"));
   radio.Say("Order four briefing.","Ossa",4.5f,FieldOrders.RadioTag(3,"brief"));
   Assert.That(radio.Drop(),Is.EqualTo(1),"the order-three briefing is stale");
   Assert.That(radio.PendingTags,Is.EqualTo(new[]{"order:2:done","order:3:brief"}));
   Assert.That(radio.Text,Is.EqualTo("Order two done."),"the line on screen finishes");
   // An urgent combat warning interrupts, and the interrupted line resumes after it.
   radio.Tick(1,true);
   Assert.That(radio.Say("Optics flaring: step back!","Ossa",0,FieldOrders.RadioTag(3,"engage"),true));
   Assert.That(radio.Text,Is.EqualTo("Optics flaring: step back!"));
   Assert.That(radio.PendingTags.First(),Is.EqualTo("order:1:done"));
   // The interrupted "order two done" is superseded by now, so it is skipped when its turn comes.
   radio.Tick(radio.timing.maxSeconds,true);
   Assert.That(radio.Text,Is.EqualTo("Order three done."));
   index=4;radio.Tick(radio.timing.maxSeconds,true);
   Assert.That(radio.Showing,Is.False,"order four's briefing went stale (order four completed) and is skipped");Assert.That(radio.Pending,Is.Zero);
   Assert.That(FieldOrders.IsStale("order:3:brief",4));Assert.That(FieldOrders.IsStale("order:3:done",4),Is.False);Assert.That(FieldOrders.IsStale("order:2:done",4));
   Assert.That(FieldOrders.IsStale("primer",4),Is.False);Assert.That(FieldOrders.IsStale(null,4),Is.False);
   var orders=AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset").orders;
   var foreman=orders.Single(o=>o.id=="order_depot_foreman");
   Assert.That(foreman.urgentStart);Assert.That(foreman.engageLine,Does.Contain("step back"));
   // 2 Oct 2026: the Long Arm order's gunner leader also has an engage warning (the laser tell); nothing else does
   var longArm=orders.Single(o=>o.id=="order_long_arm");Assert.That(longArm.engageLine,Does.Contain("laser"));Assert.That(longArm.urgentStart,Is.False);
   Assert.That(orders.Where(o=>o!=foreman&&o!=longArm).All(o=>!o.urgentStart&&string.IsNullOrEmpty(o.engageLine)));
  }

  // ------------------------------------------------------------------ caches
  [Test] public void CachesLandFlatClearAndApart()
  {
   var half=new Vector3(.26f,.2f,.25f);int mask=~(1<<8);var q=Quaternion.identity;
   Box("ground",new Vector3(0,-.5f,0),new Vector3(40,1,40));
   Box("platform",new Vector3(10,.5f,0),new Vector3(4,1,4)); // top at y 1, edge at x 8
   Box("fence",new Vector3(-10,.6f,0),new Vector3(.1f,1.2f,3));
   Physics.SyncTransforms();
   // Open ground: the wreck point itself.
   Assert.That(SalvageCache.FindSpot(new Vector3(0,.3f,5),q,half,1.5f,.8f,.14f,mask,null,out var s));
   Assert.That(Vector3.Distance(s,new Vector3(0,0,5)),Is.LessThan(.01f));
   // Platform edge: the whole footprint ends up on one level.
   Assert.That(SalvageCache.FindSpot(new Vector3(8.1f,1.2f,0),q,half,1.5f,.8f,.14f,mask,null,out s));
   Assert.That(SalvageCache.Footprint(s,q,half,.14f,mask,out _),"flat under all corners");
   Assert.That(s.x-half.x>=8f-.01f||s.x+half.x<=8f+.01f,"not straddling the edge: "+s);
   // Fence: never straddled.
   Assert.That(SalvageCache.FindSpot(new Vector3(-10,.2f,0),q,half,1.5f,.8f,.14f,mask,null,out s));
   Assert.That(Mathf.Abs(s.x+10),Is.GreaterThan(half.x),"clear of the fence: "+s);
   // Separation from existing caches.
   var others=new List<Vector3>{new Vector3(0,0,-5)};
   Assert.That(SalvageCache.FindSpot(new Vector3(0,.3f,-5),q,half,1.5f,.8f,.14f,mask,others,out s));
   Assert.That(Vector3.Distance(new Vector3(s.x,0,s.z),new Vector3(0,0,-5)),Is.GreaterThanOrEqualTo(.8f));
   // Nowhere to rest (no ground in reach): falls back to the point itself and says so.
   Assert.That(SalvageCache.FindSpot(new Vector3(100,.5f,100),q,half,1.5f,.8f,.14f,mask,null,out s),Is.False);
   Assert.That(s,Is.EqualTo(new Vector3(100,.5f,100)));
  }

  [Test] public void CacheGlowRanksRareFirstAndOnlyPoolsLight()
  {
   var cache=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab").GetComponent<SalvageCache>();
   Assert.That(cache.CoreLuminance(ItemRarity.Rare),Is.GreaterThan(cache.CoreLuminance(ItemRarity.Uncommon)*1.5f),"rare is the most striking");
   Assert.That(cache.CoreLuminance(ItemRarity.Uncommon),Is.GreaterThan(cache.CoreLuminance(ItemRarity.Common)),"common stays subtle");
   var rare=cache.rareGlow;Assert.That(rare.b/rare.r,Is.LessThan(.1f),"rare amber is saturated");
   Assert.That(cache.LightIntensity(ItemRarity.Rare),Is.GreaterThan(cache.LightIntensity(ItemRarity.Uncommon)));
   Assert.That(cache.LightIntensity(ItemRarity.Uncommon),Is.GreaterThan(cache.LightIntensity(ItemRarity.Common)));
   foreach(ItemRarity r in System.Enum.GetValues(typeof(ItemRarity))){Assert.That(cache.LightRange(r),Is.LessThanOrEqualTo(1.5f),r.ToString());Assert.That(cache.LightIntensity(r),Is.LessThanOrEqualTo(.6f),r.ToString());}
   Assert.That(cache.glowLight.range,Is.LessThanOrEqualTo(1.5f));Assert.That(cache.glowLight.shadows,Is.EqualTo(LightShadows.None));
   Assert.That(cache.rarePulse,Is.InRange(.05f,.4f));
   // The footprint covers the prop's body.
   var body=cache.GetComponentsInChildren<MeshFilter>(true).First(f=>f.name.StartsWith("SalvageCache_Body_LOD0")).sharedMesh.bounds;
   Assert.That(cache.footprint.x,Is.GreaterThanOrEqualTo(body.extents.x));Assert.That(cache.footprint.z,Is.GreaterThanOrEqualTo(body.extents.z));
  }

  // ------------------------------------------------------------------ droids
  [Test] public void DroidCullingBoundsCoverEveryClip()
  {
   foreach(var path in new[]{"Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab","Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab"})
   {
    var go=Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));made.Add(go);
    var smr=go.GetComponentInChildren<SkinnedMeshRenderer>();var d=go.GetComponent<FeralDroid>();
    var envelope=DroidBounds.Measure(go,12);
    TestContext.WriteLine($"{path}: envelope {envelope} fitted {smr.localBounds}");
    Assert.That(DroidBounds.Covers(smr.localBounds,envelope),path+": the culling bounds cover the whole animation");
    float fitted=smr.localBounds.size.x*smr.localBounds.size.y*smr.localBounds.size.z,needed=envelope.size.x*envelope.size.y*envelope.size.z;
    Assert.That(fitted/needed,Is.LessThan(2.5f),path+": no longer effectively infinite");
    Assert.That(smr.updateWhenOffscreen,Is.False);
    Assert.That(d.animationSource.cullingType,Is.EqualTo(AnimationCullingType.BasedOnRenderers),"idle droids off screen do not animate");
    Assert.That(d.idleThrottleDistance,Is.GreaterThan(d.aggroRadius*2),"throttling never touches perception");
   }
   var drone=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab").GetComponent<FeralDroid>();
   Assert.That(drone.wreckMaxTravel,Is.InRange(1f,4f));Assert.That(drone.idleThrottleDistance,Is.GreaterThan(drone.aggroRadius*2));
  }
 }
}
