using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill.Tests
{
 /// Gameplay v2 native QA fixes (30 Sep 2026): keyboard selection and navigation, the radio channel, persistent caches,
 /// nest re-form rule, the elite Foreman, Buy parts, icons, save wording and order 2 pacing.
 public class GameplayV2FixesTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  const string Station="station_field_fabricator";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static VisualElement Hud()=>AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/CityHUD.uxml").CloneTree();
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public ShopModel pack;public CraftingModel model;
   public Rig(CityState state,int credits=25)
   {
    go=new GameObject("fixes rig");go.SetActive(false);
    session=go.AddComponent<GameSession>();session.catalog=City();crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    var player=new GameObject("combat");player.transform.SetParent(go.transform);combat=player.AddComponent<PlayerCombat>();combat.hasPistol=true;crafting.combat=combat;
    pack=new ShopModel(City().items,credits);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",state);Set(session,"ActiveStationId",Station);
    Set(crafting,"Model",model);Set(crafting,"Session",session);combat.BindLoadout(model.Loadout);
   }
   public void Dispose(){Object.DestroyImmediate(go);Time.timeScale=1;}
  }
  static void Craft(CraftingModel model,string recipe,int times=1){model.Unlock(recipe);for(int i=0;i<times;i++)Assert.That(model.TryCraft(recipe,Station,out var r),r+" "+recipe);}
  /// All three Mark I mods fabricated and fitted (the QA repro state).
  static void FitMarkOne(Rig rig)
  {
   Give(rig.pack,("droid_servo_damaged",1),("scrap_alloy",12),("nanite_residue",14),("copper_filament",6),("micro_capacitor",2));
   Craft(rig.model,"recipe_grip_stabilised_pistol");Craft(rig.model,"recipe_wound_coil",2);Craft(rig.model,"recipe_charge_cell_core");
   Craft(rig.model,"recipe_cell_salvaged_capacitor");Craft(rig.model,"recipe_alloy_plate",2);Craft(rig.model,"recipe_barrel_bored_alloy");
   foreach(var mod in new[]{"grip_stabilised_pistol","cell_salvaged_capacitor","barrel_bored_alloy"})Assert.That(rig.model.TryFit(mod,out var r),r);
  }

  // ------------------------------------------------------------------ keyboard navigation
  [Test] public void GridAndListStepsMoveExactlyOneCell()
  {
   var five=Enumerable.Range(0,12).Select(i=>new Rect(i%5*94,i/5*94,84,84)).ToList();
   Assert.That(UiNavigation.Columns(five),Is.EqualTo(5),"columns come from the laid-out tiles, not a constant");
   Assert.That(UiNavigation.Columns(Enumerable.Range(0,7).Select(i=>new Rect(i%3*106,i/3*106,96,96)).ToList()),Is.EqualTo(3));
   Assert.That(UiNavigation.Columns(new List<Rect>()),Is.EqualTo(1));
   var D=NavigationMoveEvent.Direction.Down;var U=NavigationMoveEvent.Direction.Up;var L=NavigationMoveEvent.Direction.Left;var R=NavigationMoveEvent.Direction.Right;
   Assert.That(UiNavigation.GridStep(0,12,5,R),Is.EqualTo(1));Assert.That(UiNavigation.GridStep(1,12,5,R),Is.EqualTo(2),"flask → alloy → the next tile, never none");
   Assert.That(UiNavigation.GridStep(4,12,5,R),Is.EqualTo(5),"continues onto the next row");
   Assert.That(UiNavigation.GridStep(11,12,5,R),Is.EqualTo(11));Assert.That(UiNavigation.GridStep(0,12,5,L),Is.EqualTo(0));
   Assert.That(UiNavigation.GridStep(2,12,5,D),Is.EqualTo(7));Assert.That(UiNavigation.GridStep(7,12,5,U),Is.EqualTo(2));Assert.That(UiNavigation.GridStep(2,12,5,U),Is.EqualTo(2));
   Assert.That(UiNavigation.GridStep(8,12,5,D),Is.EqualTo(11),"down onto a shorter last row lands on its last tile");
   Assert.That(UiNavigation.GridStep(11,12,5,D),Is.EqualTo(11));
   Assert.That(UiNavigation.ListStep(0,9,1),Is.EqualTo(1));Assert.That(UiNavigation.ListStep(8,9,1),Is.EqualTo(8));Assert.That(UiNavigation.ListStep(0,9,-1),Is.EqualTo(0));
  }

  [Test] public void FabricatorListIsOneTabStopAndOnlyExplicitNavigationSelects()
  {
   using var rig=new Rig(CityState.Fabricator);
   var root=Hud();var panel=new FabricatorPanel(root,rig.session,rig.crafting);
   foreach(var r in Data().recipes)rig.model.Unlock(r.id);
   panel.Opened();
   var buttons=root.Query<Button>(className:"fab-recipe").ToList();
   Assert.That(buttons.Count(b=>b.focusable),Is.EqualTo(1),"only the selected schematic is a tab stop");
   Assert.That(buttons.Single(b=>b.focusable).name,Is.EqualTo("fab-recipe-"+panel.Selected));
   // One ↓ is one schematic, in list order, through every schematic (none unreachable).
   var order=panel.Order.ToList();Assert.That(order.Count,Is.EqualTo(Data().recipes.Length));
   panel.Select(order[0]);
   for(int i=1;i<order.Count;i++){Assert.That(panel.Move(1));Assert.That(panel.Selected,Is.EqualTo(order[i]));Assert.That(buttons.Count(b=>b.focusable),Is.EqualTo(1));}
   Assert.That(panel.Move(1),Is.False,"stops at the end");Assert.That(panel.Selected,Is.EqualTo(order[^1]));
   for(int i=order.Count-2;i>=0;i--){Assert.That(panel.Move(-1));Assert.That(panel.Selected,Is.EqualTo(order[i]));}
   // Tab order inside the window: the selected schematic, then the actions, then the slot cards.
   panel.Select("recipe_grip_stabilised_pistol");
   var modal=root.Q("fabricator-panel");
   var tabStops=modal.Query<Button>().ToList().Where(b=>b.focusable).Select(b=>b.name).ToList();
   Assert.That(tabStops[0],Does.StartWith("fab-recipe-"));
   Assert.That(tabStops.Skip(1).Take(3),Is.EqualTo(new[]{"fabricator-craft","fabricator-fit","fabricator-remove"}));
   Assert.That(tabStops.Skip(4),Is.EqualTo(new[]{"fab-slot-grip","fab-slot-barrel","fab-slot-cell"}));
  }

  [Test] public void FabricatorActionsWorkOnTheVisiblySelectedModAndKeepFocus()
  {
   using var rig=new Rig(CityState.Fabricator);
   FitMarkOne(rig);
   var root=Hud();var panel=new FabricatorPanel(root,rig.session,rig.crafting);
   panel.Opened();
   // QA bug 1: grip selected, then Remove must remove the grip — not the cell the old Tab path passed through.
   panel.Select("recipe_grip_stabilised_pistol");
   Assert.That(root.Q<Label>("fabricator-recipe").text,Is.EqualTo("Stabilised Pistol Grip"));
   Assert.That(root.Q<Button>("fabricator-remove").enabledSelf);
   panel.Remove();
   Assert.That(rig.model.Loadout.Fitted("grip"),Is.Null);
   Assert.That(rig.model.Loadout.Fitted("cell"),Is.EqualTo("cell_salvaged_capacitor"));Assert.That(rig.model.Loadout.Fitted("barrel"),Is.EqualTo("barrel_bored_alloy"));
   Assert.That(((VisualElement)panel.FocusAfterAction).name,Is.EqualTo("fabricator-fit"),"after Remove, Fit takes focus");
   panel.Fit();
   Assert.That(rig.model.Loadout.Fitted("grip"),Is.EqualTo("grip_stabilised_pistol"));
   Assert.That(((VisualElement)panel.FocusAfterAction).name,Is.EqualTo("fab-recipe-recipe_grip_stabilised_pistol"),"after Fit, focus returns to the selected schematic");
   Assert.That(((VisualElement)panel.FocusAfterAction).focusable);
   // A fitted mod's guidance is not a red failure line.
   var reason=root.Q<Label>("fab-reason");Assert.That(reason.text,Does.StartWith("Fitted to your Scrap Pistol"));Assert.That(reason.ClassListContains("blocked"),Is.False);
   // Stats header: four separate, readable columns.
   var header=root.Q(className:"fab-stat-header");
   Assert.That(header.Query<Label>().ToList().Select(l=>l.text),Is.EqualTo(new[]{"STAT","NOW","WITH MOD","CHANGE"}));
  }

  [Test] public void ModDescriptionsCompareAgainstTheCurrentLoadout()
  {
   using var rig=new Rig(CityState.Fabricator);
   FitMarkOne(rig);
   var loadout=rig.model.Loadout;
   Assert.That(loadout.Stats.recoil,Is.EqualTo(31));Assert.That(loadout.Stats.damage,Is.EqualTo(40.8f).Within(1e-4));
   string Plain(string s)=>s.Replace('\u00A0',' ').Replace('\u2215','/');
   var gyro=Plain(FabricatorPanel.ModSummary(rig.model,loadout.Modifier("grip_gyro_braced")));
   Assert.That(gyro,Does.Contain("replaces Stabilised Pistol Grip").And.Contain("31 → 23"));Assert.That(gyro,Does.Not.Contain("38 →"));
   var lattice=Plain(FabricatorPanel.ModSummary(rig.model,loadout.Modifier("barrel_lattice_focused")));
   Assert.That(lattice,Does.Contain("40.8 → 49.3"));Assert.That(lattice,Does.Not.Contain("34 →"));
   var fitted=Plain(FabricatorPanel.ModSummary(rig.model,loadout.Modifier("grip_stabilised_pistol")));
   Assert.That(fitted,Does.Contain("fitted").And.Contain("38 → 31"),"a fitted mod shows what it adds over an empty slot");
   // Each change stays on one line: no ordinary space or slash inside "Nano refill 30/s → 39/s".
   var cell=FabricatorPanel.ModSummary(rig.model,loadout.Modifier("cell_overclocked"));
   var refill=cell.Split(new[]{" · "},System.StringSplitOptions.None).Single(s=>s.Contains("refill"));
   Assert.That(refill,Does.Not.Contain(" ").And.Not.Contain("/"),refill);Assert.That(Plain(refill),Does.Contain("→"));
  }

  [Test] public void UxmlHasTheNewLayoutAndRadioElements()
  {
   using var rig=new Rig(CityState.Shop);
   var root=Hud();var panel=new MerchantPanel(root,rig.session,rig.crafting);panel.Refresh();
   foreach(var name in new[]{"radio","fab-columns","fab-recipes","fab-detail","fab-pistol","merchant-columns","merchant-browser","merchant-detail","merchant-scroll"})Assert.That(root.Q(name),Is.Not.Null,name);
   foreach(var name in new[]{"radio-text","radio-speaker","merchant-balance","merchant-price"})Assert.That(root.Q<Label>(name),Is.Not.Null,name);
   var shop=root.Q("shop-panel");var names=shop.Query<Button>().ToList().Select(b=>b.name).ToList();
   Assert.That(names.Take(2),Is.EqualTo(new[]{"merchant-tab-buy","merchant-tab-sell"}),"buy and sell are explicit modes above one stock browser");
   Assert.That(root.Q("merchant-scroll").parent,Is.EqualTo(root.Q("merchant-browser")));
   Assert.That(root.Q("merchant-trade").GetFirstAncestorOfType<ScrollView>(),Is.Not.EqualTo(root.Q("merchant-scroll")),"checkout is outside the scrolling stock");
   Assert.That(root.Q("merchant-columns").Children().Select(c=>c.name),Is.EqualTo(new[]{"merchant-browser","merchant-detail"}));
   var startup=AssetDatabase.LoadAssetAtPath<VisualTreeAsset>("Assets/AthenHill/UI/StartupMenu.uxml").CloneTree();
   Assert.That(startup.Q("new-game-confirm").parent,Is.EqualTo(startup.Q("startup-actions").parent),"the confirmation takes the actions' place");
  }

  // ------------------------------------------------------------------ radio channel
  [Test] public void RadioLinesStayLongEnoughQueueAndPauseOutsidePlay()
  {
   var radio=new RadioQueue();
   string briefing=string.Join(" ",Enumerable.Repeat("word",58));
   Assert.That(radio.timing.For(briefing),Is.GreaterThanOrEqualTo(18),"a 58-word briefing is readable");
   Assert.That(radio.timing.For("Short line."),Is.EqualTo(radio.timing.minSeconds));
   Assert.That(radio.Say(briefing,"Warden Ossa"));Assert.That(radio.Say("Next order.","Warden Ossa",1),Is.False);
   Assert.That(radio.Say(briefing,"Warden Ossa"),Is.False,"duplicates are ignored");Assert.That(radio.Pending,Is.EqualTo(1));
   Assert.That(radio.Tick(100,false),Is.False);Assert.That(radio.Text,Is.EqualTo(briefing),"the clock stops outside play");
   Assert.That(radio.Tick(radio.timing.For(briefing)-.5f,true),Is.False);Assert.That(radio.Text,Is.EqualTo(briefing));
   Assert.That(radio.Tick(1,true));Assert.That(radio.Showing,Is.False,"a short gap before the next line");
   Assert.That(radio.Tick(1.1f,true));Assert.That(radio.Text,Is.EqualTo("Next order."));
   Assert.That(radio.Tick(radio.timing.maxSeconds,true));Assert.That(radio.Showing,Is.False);Assert.That(radio.Text,Is.Null);
  }

  [Test] public void PickupsAndNoticesNeverOverwriteTheRadio()
  {
   using var rig=new Rig(CityState.Play);
   rig.session.Radio("Keep the charge: find two micro capacitors.","Warden Ossa");
   rig.session.Notify("Search interrupted.","Field Pack");
   rig.session.Record("Collected: Scrap Alloy ×2","Field Pack");
   Assert.That(rig.session.RadioLine.Text,Is.EqualTo("Keep the charge: find two micro capacitors."));Assert.That(rig.session.RadioLine.Speaker,Is.EqualTo("Warden Ossa"));
   Assert.That(rig.session.notice,Is.EqualTo("Search interrupted."));
   Assert.That(rig.session.Log.Last(),Is.EqualTo("Field Pack: Collected: Scrap Alloy ×2"),"pickups are logged without a banner");
   Assert.That(rig.session.Log,Does.Contain("Warden Ossa: Keep the charge: find two micro capacitors."));
  }

  // ------------------------------------------------------------------ world: caches, nests, Foreman
  [Test] public void CachesPersistAndTheCapRetiresTheOldestNonRareFirst()
  {
   var caches=new List<(float,bool)>{(10,false),(5,true),(20,false),(1,false),(30,false)};
   Assert.That(SalvageCache.EvictionOrder(caches,5),Is.Empty);
   Assert.That(SalvageCache.EvictionOrder(caches,3),Is.EqualTo(new[]{3,0}),"oldest first");
   Assert.That(SalvageCache.EvictionOrder(caches,1),Is.EqualTo(new[]{3,0,2,4}),"rare parts last");
   var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/SalvageCache.prefab").GetComponent<SalvageCache>();
   Assert.That(prefab.lifetimeSeconds,Is.GreaterThanOrEqualTo(300));
   var go=new GameObject("crafting");try{var c=go.AddComponent<CraftingSession>();Assert.That(c.cacheLifetimeSeconds,Is.EqualTo(600));Assert.That(c.maxCaches,Is.InRange(8,20));}finally{Object.DestroyImmediate(go);}
   // A revived droid forgets its old cache instead of despawning it.
   var source=File.ReadAllText("Assets/AthenHill/Scripts/Crafting/LootSource.cs");
   Assert.That(Regex.Match(source,@"public void Revived\(\)\s*\{[^}]*\}").Value,Does.Not.Contain("Despawn"));
  }

  [Test] public void NestsReformOnlyAfterTimeAndAnAwayStreak()
  {
   Assert.That(DroidEncounter.ShouldReform(240,239,true,999,45),Is.False,"too soon");
   Assert.That(DroidEncounter.ShouldReform(240,300,false,999,45),Is.False,"player near");
   Assert.That(DroidEncounter.ShouldReform(240,300,true,30,45),Is.False,"not away long enough");
   Assert.That(DroidEncounter.ShouldReform(240,300,true,45,45));
   Assert.That(DroidEncounter.ShouldReform(0,999,true,999,0),Is.False,"respawn off");
   Assert.That(DroidEncounter.ShouldReform(120,121,true,.01f,0),"away 0 keeps the old rule");
  }

  [Test] public void ForemanIsAnEliteWithinTheWorkerBehaviour()
  {
   var foreman=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab");
   var worker=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab");
   var f=foreman.GetComponent<FeralDroid>();var w=worker.GetComponent<FeralDroid>();
   Assert.That(PrefabUtility.GetCorrespondingObjectFromSource(foreman),Is.EqualTo(worker),"still a variant of the worker (no AI fork)");
   Assert.That(foreman.GetComponent<Health>().max,Is.InRange(1200,1600));
   Assert.That(f.slamEvery,Is.InRange(2,4));Assert.That(f.slamWindupSeconds,Is.GreaterThan(f.windupSeconds+.4f),"the slam has a longer tell");
   Assert.That(f.slamDamage,Is.GreaterThan(f.strikeDamage));Assert.That(f.slamRadius,Is.GreaterThan(f.attackRange));
   Assert.That(f.staggerThreshold,Is.GreaterThan(100));Assert.That(f.staggerImmunity,Is.GreaterThanOrEqualTo(5));
   Assert.That(w.slamEvery,Is.Zero);Assert.That(w.staggerThreshold,Is.Zero,"workers keep their behaviour");
   Assert.That(Enumerable.Range(1,9).Where(n=>FeralDroid.IsSlam(n,3)),Is.EqualTo(new[]{3,6,9}));Assert.That(FeralDroid.IsSlam(3,0),Is.False);
   Assert.That(FeralDroid.Staggers(159,160),Is.False);Assert.That(FeralDroid.Staggers(160,160));Assert.That(FeralDroid.Staggers(1,0));
   // Fight length for a player with Mark I mods (damage 40.8, 15 shots per 135-nano cell, ~0.6 s refill delay):
   // sustained ~60 DPS at ~85% hits leaves 20–40 s of fighting, before escorts and dodging slams.
   float seconds=foreman.GetComponent<Health>().max/(40.8f*15/(15*.28f+135/34.5f)*.85f);
   Assert.That(seconds,Is.InRange(20,40));
  }

  [Test] public void HealthBarsSitJustAboveTheModelAtAnyScale()
  {
   float Top(string path,out float oldAnchor)
   {
    var go=Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));
    try
    {
     go.transform.position=Vector3.zero;
     var h=go.GetComponent<Health>();oldAnchor=go.transform.TransformPoint(h.aimOffset).y+.9f;
     var d=go.GetComponent<FeralDroid>();
     float top=(float)typeof(FeralDroid).GetMethod("MeasureTop",Any).Invoke(d,null);
     if(d.kind==DroidKind.Walker)Assert.That(d.BarAnchor.y,Is.EqualTo(top+.3f).Within(.02f),path+": the bar follows the head bone");
     return top;
    }
    finally{Object.DestroyImmediate(go);}
   }
   float worker=Top("Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab",out var workerOld);
   float foreman=Top("Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab",out var foremanOld);
   float drone=Top("Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab",out _);
   TestContext.WriteLine($"bar anchors (head bone + 0.3 m; drone: top + 0.25 m): worker {worker+.3f:0.00} m (was {workerOld:0.00}), Foreman {foreman+.3f:0.00} m (was {foremanOld:0.00}), drone {drone+.25f:0.00} m");
   Assert.That(foreman/worker,Is.EqualTo(1.3f).Within(.08f),"the Foreman's bar scales with its 1.3× model");
   // Worker head end 1.85 m, Foreman 1.3 × that; the old anchors (aim point + 0.9 m) sat 0.4–0.6 m higher.
   Assert.That(worker,Is.InRange(1.6f,2.2f));Assert.That(foreman,Is.InRange(2.1f,2.8f));Assert.That(drone,Is.InRange(.1f,.8f));
   Assert.That(foreman+.25f,Is.LessThan(foremanOld));Assert.That(worker+.25f,Is.LessThan(workerOld));
  }

  // ------------------------------------------------------------------ economy, icons, saves, pacing
  [Test] public void MiraSellsCommonAndUncommonPartsAtAPremiumOnly()
  {
   var items=City().items;
   Assert.That(items.Where(ShopModel.SellsAsPart).Select(x=>x.id),Is.EquivalentTo(new[]{"scrap_alloy","nanite_residue","copper_filament","droid_servo_damaged","micro_capacitor","optic_lens_cracked"}));
   foreach(var item in items.Where(ShopModel.SellsAsPart)){Assert.That(item.partsPrice,Is.GreaterThanOrEqualTo(item.sellPrice*3),item.id);Assert.That(item.rarity,Is.Not.EqualTo(ItemRarity.Rare));}
   Assert.That(items.Where(x=>x.rarity==ItemRarity.Rare).Any(ShopModel.SellsAsPart),Is.False,"rare parts stay loot-only");
   // The original three rows and their prices are untouched.
   Assert.That(items.Take(3).Select(x=>(x.id,x.buyPrice,x.sellPrice)),Is.EqualTo(new[]{("water_flask",4,2),("medkit",9,4),("scrap_coil",2,1)}));
   var pack=new ShopModel(items,30);
   Assert.That(pack.BuyPart("micro_capacitor",2,out var m),m);Assert.That(pack.Credits,Is.EqualTo(6));Assert.That(pack.Quantity("micro_capacitor"),Is.EqualTo(2));Assert.That(pack.Purchases,Is.EqualTo(1));
   Assert.That(pack.BuyPart("micro_capacitor",1,out m),Is.False);Assert.That(m,Does.Contain("6 more credits"));Assert.That(pack.Credits,Is.EqualTo(6));
   Assert.That(pack.BuyPart("actuator_intact",1,out m),Is.False);Assert.That(m,Does.Contain("Rare parts"));
   Assert.That(pack.BuyPart("water_flask",1,out _),Is.False,"supplies stay in their own rows");
   Assert.That(pack.Trade("micro_capacitor",true,out m),Is.False,"the legacy Buy path still refuses salvage");
   var full=new ShopModel(items,500);Give(full,("micro_capacitor",10));
   Assert.That(full.BuyPart("micro_capacitor",1,out m),Is.False);Assert.That(m,Does.Contain("limit 10"));Assert.That(full.Credits,Is.EqualTo(500));
  }

  [Test] public void PartsListBuysThroughTheSessionAndRevealsSchematics()
  {
   using var rig=new Rig(CityState.Shop,40);
   var root=Hud();var panel=new MerchantPanel(root,rig.session,rig.crafting);panel.Refresh();
   var parts=City().items.Where(ShopModel.SellsAsPart).ToArray();Assert.That(parts.Length,Is.EqualTo(6));
   foreach(var part in parts)Assert.That(root.Q<Button>("merchant-item-"+part.id),Is.Not.Null,part.id+" remains stocked");
   panel.Select("micro_capacitor");Assert.That(root.Q<Button>("merchant-trade").text,Is.EqualTo("Buy one · 12 cr"));
   Assert.That(rig.model.Knows("recipe_charge_cell_core"),Is.False);
   string found=null,note=null;
   rig.session.PartBought+=purchase=>
   {
    found=purchase.itemId;
    typeof(CraftingSession).GetMethod("OnPartBought",Any).Invoke(rig.crafting,new object[]{purchase});note=purchase.note;
   };
   void Trade()=>typeof(MerchantPanel).GetMethod("Trade",Any).Invoke(panel,null);
   Trade();
   Assert.That(found,Is.EqualTo("micro_capacitor"));Assert.That(rig.pack.Credits,Is.EqualTo(28));Assert.That(rig.pack.Quantity("micro_capacitor"),Is.EqualTo(1));
   Assert.That(rig.model.Knows("recipe_charge_cell_core"));Assert.That(note,Is.EqualTo(" Schematic discovered: Charge Cell Core."),"merchant purchase raises the same acquisition event as the old parts control");
   Assert.That(root.Q("merchant-item-scrap_alloy").Q<Label>(className:"merchant-row-meta").text,Does.Contain("0 carried"));
   panel.Select("optic_lens_cracked");Trade();Trade();Assert.That(rig.pack.Credits,Is.Zero);
   Assert.That(root.Q<Button>("merchant-trade").enabledSelf,Is.False,"disabled when credits fall short");
   int before=rig.pack.Quantity("optic_lens_cracked");Trade();
   Assert.That(rig.pack.Quantity("optic_lens_cracked"),Is.EqualTo(before),"the underlying action also rejects an unaffordable purchase");Assert.That(rig.pack.Credits,Is.Zero);
  }

  [Test] public void EveryItemHasItsOwnIllustration()
  {
   var uss=File.ReadAllText("Assets/AthenHill/UI/CityHUD.uss")+"\n"+File.ReadAllText("Assets/AthenHill/UI/MerchantPanel.uss");
   var v2=City().items.Where(x=>x.HasTag("salvage")||x.HasTag("refined")||x.HasTag("weapon_mod")).Where(x=>x.id!="scrap_coil"&&x.id!="rifle_precision_barrel").ToList();
   Assert.That(v2.Count,Is.EqualTo(18));
   Assert.That(v2.Select(x=>x.icon).Distinct().Count(),Is.EqualTo(v2.Count),"no two salvage items share an icon");
   Assert.That(v2.Any(x=>x.icon=="scrap-icon"||x.icon=="pistol-icon"||x.icon=="lattice-icon"),Is.False);
   foreach(var item in City().items.Where(x=>!string.IsNullOrEmpty(x.icon)))
   {
    var m=Regex.Match(uss,@"\."+Regex.Escape(item.icon)+@"\s*\{\s*background-image:\s*url\(""Art/([^""]+)""\)");
    Assert.That(m.Success,item.id+" icon rule");
    var png="Assets/AthenHill/UI/Art/"+m.Groups[1].Value;
    var tex=AssetDatabase.LoadAssetAtPath<Texture2D>(png);Assert.That(tex,Is.Not.Null,png);
    if(v2.Contains(item)){Assert.That(tex.width,Is.EqualTo(192));Assert.That(tex.height,Is.EqualTo(192));}
   }
  }

  [Test] public void DamagedSavesExplainThemselvesInPlainWords()
  {
   foreach(var text in new[]{"{\"version\":1,\"credits\":","{\"version\":1,\"credits\":12,\"items\":[{\"itemId\":\"scrap_al","{ not json at all","","[1,2]","{\"version\":9}"})
   {
    Assert.That(WardSaveFile.TryParse(text,out _,out var error),Is.False,text);
    Assert.That(error,Does.Not.Contain("Exception").And.Not.Contain("("+"Argument"),text);
    Assert.That(error,Does.Not.Match(@"[A-Z][a-z]+Exception"),text);
   }
  }

  [Test] public void OrderTwoNeedsAboutOneDepotClearAndAFewHeaps()
  {
   // Same model as unity/evidence/gameplay-v2/20260930-fixes/loot_sim.py (depot-first), on the real tables.
   var data=Data();LootTable T(string id)=>data.lootTables.Single(t=>t.id==id);
   var nest=new[]{"loot_feral_scrap_drone","loot_feral_worker_droid","loot_feral_worker_droid"};
   var heaps=Enumerable.Repeat("loot_scrap_heap",6).Concat(new[]{"loot_wreck_carcass","loot_wreck_carcass","loot_drone_wreck"}).ToArray();
   int runs=400,within=0,second=0;
   for(int seed=1;seed<=runs;seed++)
   {
    var book=new LootBook((ulong)seed*0x9E3779B97F4A7C15UL);int cap=0,cu=0;
    void Add(List<ItemStack> got){foreach(var s in got){if(s.itemId=="micro_capacitor")cap+=s.quantity;if(s.itemId=="copper_filament")cu+=s.quantity;}}
    Add(book.Roll(T("loot_feral_scrap_drone")));foreach(var t in nest)Add(book.Roll(T(t)));
    bool Done()=>cap>=2&&cu>=2;
    int clears=0,searched=0;
    while(!Done()&&clears<5)
    {
     clears++;foreach(var t in nest)Add(book.Roll(T(t)));
     for(int h=0;h<heaps.Length&&!Done();h++){searched++;Add(book.Roll(T(heaps[h])));}
     if(!Done())searched=0;
    }
    if(clears<=1&&searched<=3)within++;
    if(clears>=2)second++;
   }
   Assert.That(within/(float)runs,Is.GreaterThanOrEqualTo(.9f),"≥90% finish within one depot clear and three heaps");
   Assert.That(second,Is.Zero,"never a second depot clear when every cache is collected");
  }
 }
}
