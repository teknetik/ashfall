using System.IO;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Tests
{
 /// 5 Oct 2026: always-on mouse look, the configurable hotbar, the mission journal and the leased container home
 /// (locker, lease, save v4).
 public class HomeJournalHotbarTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static NpcDefinition Npc(string id)=>AssetDatabase.LoadAssetAtPath<NpcDefinition>($"Assets/AthenHill/Data/{id}.asset");
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);
  string folder;
  [SetUp] public void MakeFolder(){folder=Path.Combine(Path.GetTempPath(),"ward-home-tests-"+System.Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);}
  [TearDown] public void RemoveFolder(){if(Directory.Exists(folder))Directory.Delete(folder,true);Time.timeScale=1;}

  /// A live session with crafting, combat, the primer, field orders, the journal and the save.
  sealed class Rig:System.IDisposable
  {
   public GameObject go;public GameSession session;public CraftingSession crafting;public PlayerCombat combat;public BermsTutorial tutorial;public FieldOrders orders;public WardSaveGame save;public QuestJournal journal;public ShopModel pack;public CraftingModel model;
   public Rig(string folder,int credits=0)
   {
    go=new GameObject("home rig");go.SetActive(false);
    var input=go.AddComponent<GameInput>();input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var motor=go.AddComponent<PlayerMotor>();go.AddComponent<Health>();combat=go.AddComponent<PlayerCombat>();
    session=go.AddComponent<GameSession>();session.input=input;session.player=motor;session.catalog=City();session.npcs=new NpcAgent[0];
    crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    crafting.combat=combat;combat.session=session;
    var t=new GameObject("berms");t.transform.SetParent(go.transform);tutorial=t.AddComponent<BermsTutorial>();tutorial.session=session;tutorial.combat=combat;
    orders=go.AddComponent<FieldOrders>();orders.data=Orders();orders.crafting=crafting;orders.tutorial=tutorial;orders.combat=combat;
    save=go.AddComponent<WardSaveGame>();save.directoryOverride=folder;
    journal=go.AddComponent<QuestJournal>();
    go.SetActive(true);
    typeof(GameInput).GetMethod("OnEnable",Any).Invoke(input,null);
    typeof(QuestJournal).GetMethod("Awake",Any).Invoke(journal,null);
    // Edit mode runs no Awake: health starts full and the combat rig binds to it as in play.
    foreach(var c in new MonoBehaviour[]{combat.GetComponent<Health>(),combat})c.GetType().GetMethod("Awake",Any)?.Invoke(c,null);
    pack=new ShopModel(City().items,credits);model=new CraftingModel(Data(),City().items,pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.MainMenu);Set(session,"Journal",journal);
    Set(crafting,"Model",model);Set(crafting,"Session",session);Set(crafting,"Loot",new LootBook(1729));
    combat.BindLoadout(model.Loadout);
   }
   public void Play(){Set(session,"State",CityState.Play);Set(session,"HasStarted",true);}
   public void Dispose(){Object.DestroyImmediate(go);}
  }

  // ------------------------------------------------------------------ input
  [Test] public void LeftMouseFiresAndTheOrbitHoldIsGone()
  {
   var asset=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
   var map=asset.FindActionMap("Gameplay",true);
   Assert.That(map.FindAction("Orbit",false),Is.Null,"no hold-to-look action any more");
   var fire=map.FindAction("Fire",true);
   Assert.That(fire.bindings.Select(b=>b.path),Is.SupersetOf(new[]{"<Mouse>/leftButton","<Keyboard>/f"}));
   Assert.That(map.FindAction("Slot0",true).bindings.Single().path,Is.EqualTo("<Keyboard>/0"));
   Assert.That(map.FindAction("FreeCursor",true).bindings.Single().path,Is.EqualTo("<Keyboard>/leftAlt"));
   for(int i=1;i<=HotbarModel.Slots;i++)Assert.That(map.FindAction("Slot"+HotbarModel.Key(i),false),Is.Not.Null,"hotbar key "+HotbarModel.Key(i));
  }

  [Test] public void ControlOptionsClampSensitivity()
  {
   var c=new ControlOptions();Assert.That(c.Sensitivity,Is.EqualTo(1f));
   c.sensitivity=5;Assert.That(c.Sensitivity,Is.EqualTo(ControlOptions.MinSensitivity/100f));
   c.sensitivity=1000;Assert.That(c.Sensitivity,Is.EqualTo(ControlOptions.MaxSensitivity/100f));
  }

  // ------------------------------------------------------------------ hotbar
  [Test] public void HotbarKeepsWeaponsOnOneAndTwoAndMovesItemsBetweenSlots()
  {
   var bar=new HotbarModel(id=>id=="medkit"||id=="nano_cell"||id=="trauma_kit");
   Assert.That(bar.Item(3),Is.EqualTo("medkit"));Assert.That(bar.Item(4),Is.EqualTo("nano_cell"));
   Assert.That(HotbarModel.WeaponSlot(1),Is.EqualTo("primary"));Assert.That(HotbarModel.WeaponSlot(2),Is.EqualTo("secondary"));
   Assert.That(HotbarModel.Key(10),Is.EqualTo("0"));
   Assert.That(bar.Assign(1,"medkit",out var reason),Is.False);Assert.That(reason,Is.EqualTo("weapon_slot"));
   Assert.That(bar.Assign(5,"scrap_coil",out reason),Is.False);Assert.That(reason,Is.EqualTo("not_usable"));
   Assert.That(bar.Assign(10,"medkit",out reason),reason);
   Assert.That(bar.Item(10),Is.EqualTo("medkit"));Assert.That(bar.Item(3),Is.Null,"assigning again moves the item");
   Assert.That(bar.Swap(4,10));Assert.That(bar.Item(4),Is.EqualTo("medkit"));Assert.That(bar.Item(10),Is.EqualTo("nano_cell"));
   Assert.That(bar.Clear(10));Assert.That(bar.Clear(10),Is.False);
   var saved=bar.Capture();
   var other=new HotbarModel(id=>id=="medkit"||id=="nano_cell");
   other.Restore(saved);Assert.That(other.Item(4),Is.EqualTo("medkit"));Assert.That(other.Item(3),Is.Null);Assert.That(other.Item(10),Is.Null);
   other.Restore(null);Assert.That(other.Item(3),Is.EqualTo("medkit"),"a save from before the hotbar gets the defaults");
   other.Restore(new HotbarEntry[0]);Assert.That(Enumerable.Range(1,10).All(i=>other.Item(i)==null),"an empty saved bar stays empty");
   other.Restore(new[]{new HotbarEntry{slot=2,itemId="medkit"},new HotbarEntry{slot=5,itemId="medkit"},new HotbarEntry{slot=6,itemId="medkit"},new HotbarEntry{slot=7,itemId="scrap_coil"}});
   Assert.That(other.Item(5),Is.EqualTo("medkit"));Assert.That(other.Item(6),Is.Null,"one slot per item");Assert.That(other.Item(7),Is.Null);
  }

  [Test] public void HotbarSlotsUseExactlyTheAssignedItem()
  {
   using(var rig=new Rig(folder))
   {
    rig.Play();var health=rig.combat.Health;
    rig.pack.Restore(0,0,0,new[]{new System.Collections.Generic.KeyValuePair<string,int>("medkit",2),new System.Collections.Generic.KeyValuePair<string,int>("trauma_kit",1)});
    Assert.That(rig.session.AssignHotbar(7,"scrap_coil"),Is.False,"salvage is not a hotbar item");
    Assert.That(rig.session.AssignHotbar(2,"trauma_kit"),Is.False,"2 is the sidearm");
    Assert.That(rig.session.AssignHotbar(10,"trauma_kit"));
    health.Damage(30,Vector3.zero);
    rig.session.UseHotbar(10);
    Assert.That(rig.pack.Quantity("trauma_kit"),Is.Zero,"slot 0 used the trauma kit, not the smaller medkit");Assert.That(rig.pack.Quantity("medkit"),Is.EqualTo(2));
    Assert.That(rig.session.Quickbar.Item(10),Is.EqualTo("trauma_kit"),"the assignment stays at zero");
    rig.session.UseHotbar(9);
    Assert.That(rig.session.notice,Does.Contain("Hotbar 9 is empty"));
   }
  }

  // ------------------------------------------------------------------ locker
  [Test] public void LockerMovesAreAtomicAndRespectPackLimits()
  {
   var city=City();var pack=new ShopModel(city.items,0);var stash=new StashModel(2);
   pack.Restore(0,0,0,new[]{new System.Collections.Generic.KeyValuePair<string,int>("scrap_coil",5),new System.Collections.Generic.KeyValuePair<string,int>("scrap_alloy",3),new System.Collections.Generic.KeyValuePair<string,int>("copper_filament",1)});
   Assert.That(stash.Store(pack,"scrap_coil",6,out var reason),Is.False);Assert.That(reason,Is.EqualTo("not_carried"));
   Assert.That(stash.Store(pack,"scrap_coil",5,out reason),reason);Assert.That(pack.Quantity("scrap_coil"),Is.Zero);Assert.That(stash.Quantity("scrap_coil"),Is.EqualTo(5));
   Assert.That(stash.Store(pack,"scrap_alloy",1,out reason),reason);
   Assert.That(stash.Store(pack,"copper_filament",1,out reason),Is.False,"two stacks fill a two-slot locker");Assert.That(reason,Is.EqualTo("locker_full"));
   Assert.That(pack.Quantity("copper_filament"),Is.EqualTo(1),"a refused store changes nothing");
   Assert.That(stash.Store(pack,"scrap_alloy",2,out reason),reason+": an existing stack takes more without a new slot");
   Assert.That(stash.Take(pack,"scrap_coil",2,out reason),reason);Assert.That(pack.Quantity("scrap_coil"),Is.EqualTo(2));Assert.That(stash.Quantity("scrap_coil"),Is.EqualTo(3));
   // a stack cap on the pack side refuses a take and leaves both sides as they were
   var capped=city.items.First(i=>i.maxStack>0&&i.maxStack<50);
   var p2=new ShopModel(city.items,0);p2.Restore(0,0,0,null);var s2=new StashModel(4);
   s2.Restore(new[]{new ItemStack(capped.id,capped.maxStack+3)},null);
   Assert.That(s2.Take(p2,capped.id,capped.maxStack+1,out reason),Is.False);Assert.That(p2.Quantity(capped.id),Is.Zero);Assert.That(s2.Quantity(capped.id),Is.EqualTo(capped.maxStack+3));
   Assert.That(s2.TakeableCount(p2,capped.id),Is.EqualTo(capped.maxStack));
   // restore skips unknown items and never drops stacks beyond the capacity
   var s3=new StashModel(1);
   var skipped=s3.Restore(new[]{new ItemStack("scrap_coil",2),new ItemStack("scrap_alloy",1),new ItemStack("no_such_item",4)},id=>city.items.Any(i=>i.id==id));
   Assert.That(skipped,Is.EqualTo(new[]{"no_such_item"}));Assert.That(s3.SlotsUsed,Is.EqualTo(2));
  }

  [Test] public void BenchUsesThePackFirstThenTheHomeLocker()
  {
   var city=City();var pack=new ShopModel(city.items,0);
   pack.Restore(0,0,0,new[]{new System.Collections.Generic.KeyValuePair<string,int>("scrap_alloy",1),new System.Collections.Generic.KeyValuePair<string,int>("nanite_residue",2)});
   var model=new CraftingModel(Data(),city.items,pack,()=>true);var stash=new StashModel();
   Assert.That(model.Unlock("recipe_alloy_plate"));
   var alloy=Data().recipes.First(r=>r.id=="recipe_alloy_plate").inputs.First(i=>i.id=="scrap_alloy");
   Assert.That(model.CanCraft("recipe_alloy_plate","station_field_fabricator",out var reason),Is.False,"one alloy in the pack is not three");
   stash.Restore(new[]{new ItemStack("scrap_alloy",5)},null);
   model.Reserve=stash;bool open=false;model.ReserveOpen=()=>open;
   Assert.That(model.CanCraft("recipe_alloy_plate","station_field_fabricator",out reason),Is.False,"a closed locker (no lease) adds nothing");
   open=true;
   Assert.That(model.Available(alloy),Is.EqualTo(6));Assert.That(model.FromReserve(alloy),Is.EqualTo(5));
   Assert.That(model.TryCraft("recipe_alloy_plate","station_field_fabricator",out reason),reason);
   Assert.That(pack.Quantity("scrap_alloy"),Is.Zero,"the pack's alloy is used first");Assert.That(stash.Quantity("scrap_alloy"),Is.EqualTo(3),"two more come from the locker");
   Assert.That(pack.Quantity("alloy_plate"),Is.EqualTo(1));Assert.That(pack.Quantity("nanite_residue"),Is.Zero);
   // the pack short of nanites and the locker without any: nothing is taken from either
   Assert.That(model.TryCraft("recipe_alloy_plate","station_field_fabricator",out reason),Is.False);Assert.That(stash.Quantity("scrap_alloy"),Is.EqualTo(3));
  }

  [Test] public void LeaseCostsCreditsOnceAndUnlocksTheHome()
  {
   using(var rig=new Rig(folder,25))
   {
    rig.Play();
    Assert.That(rig.session.LeaseHome(),Is.False,"25 credits do not cover the 40 credit lease");
    Assert.That(rig.pack.Credits,Is.EqualTo(25));Assert.That(rig.session.HasFlag(WardHome.LeasedFlag),Is.False);
    rig.pack.Grant(null,0,30,out _);
    Assert.That(rig.session.LeaseHome());Assert.That(rig.pack.Credits,Is.EqualTo(15));Assert.That(rig.session.HasFlag(WardHome.LeasedFlag));
    Assert.That(rig.session.LeaseHome(),Is.False,"only once");Assert.That(rig.pack.Credits,Is.EqualTo(15));
   }
  }

  [Test] public void LinnOffersTheLeaseOnlyAfterThePrimerAndUntilItIsTaken()
  {
   var linn=Npc("npc_linn");
   var greeting=linn.nodes.First(n=>n.id=="greeting");
   var ask=greeting.choices.Single(c=>c.id=="housing");
   Assert.That(ask.requires,Is.EqualTo("primer, !flag:home_leased"));Assert.That(ask.setFlag,Is.EqualTo(WardHome.AskedFlag));
   Assert.That(greeting.choices.Length,Is.LessThanOrEqualTo(GameSession.MaxChoices));
   var housing=linn.nodes.Single(n=>n.id=="housing");
   Assert.That(housing.choices.Single(c=>c.id=="lease").action,Is.EqualTo("lease_home"));
   Assert.That(linn.nodes.Any(n=>n.id=="housing_leased"));
   foreach(var c in linn.nodes.SelectMany(n=>n.choices))Assert.That(QuestConditions.Problems(c.requires),Is.Empty,c.id);
   var ossa=Npc("npc_ossa");
   Assert.That(ossa.nodes.First(n=>n.id=="range").text,Does.Contain("Draw with 2"));
   Assert.That(ossa.nodes.First(n=>n.id=="locker").text,Does.Contain("Press 2"));
   Assert.That(City().consumables.All(c=>!string.IsNullOrEmpty(c.hotbarLabel)),"every consumable has a short hotbar label");
  }

  // ------------------------------------------------------------------ save v4
  [Test] public void SaveKeepsHotbarLockerAndTrackedMission()
  {
   using(var rig=new Rig(folder,60))
   {
    rig.save.Apply(new WardSaveData{version=3,credits=60,items=new[]{new ItemStack("scrap_coil",4),new ItemStack("medkit",1)},bermsStep="Complete",hasPistol=true,orders=new FieldOrderState{index=0,id="order_steady_hands"}});
    rig.Play();
    Assert.That(rig.session.Quickbar.Item(3),Is.EqualTo("medkit"),"a v3 save gets the default hotbar");
    Assert.That(rig.session.Stash.SlotsUsed,Is.Zero);
    rig.session.Quickbar.Assign(10,"medkit",out _);
    Set(rig.session,"State",CityState.Stash);
    Assert.That(rig.session.MoveStash("scrap_coil",3,true));
    Assert.That(rig.session.HasFlag(WardHome.StoredFlag));
    Set(rig.session,"State",CityState.Play);
    Assert.That(rig.journal.Missions.Single(m=>m.id==QuestJournal.HomeId).Active);
    Assert.That(rig.journal.Track(QuestJournal.HomeId));
    var data=rig.save.Capture();
    Assert.That(data.version,Is.EqualTo(4));
    var json=WardSaveFile.Serialize(data);
    Assert.That(WardSaveFile.TryParse(json,out var back,out var error),error);
    using(var other=new Rig(folder))
    {
     other.save.Apply(back);
     Assert.That(other.session.Quickbar.Item(10),Is.EqualTo("medkit"));Assert.That(other.session.Quickbar.Item(3),Is.Null);
     Assert.That(other.session.Stash.Quantity("scrap_coil"),Is.EqualTo(3));Assert.That(other.pack.Quantity("scrap_coil"),Is.EqualTo(1));
     Assert.That(other.journal.TrackedId,Is.EqualTo(QuestJournal.HomeId));
    }
   }
  }

  // ------------------------------------------------------------------ journal
  [Test] public void JournalListsMissionsAndHandsTrackingOn()
  {
   using(var rig=new Rig(folder,60))
   {
    rig.Play();
    var missions=rig.journal.Missions;
    Assert.That(missions.Select(m=>m.id),Is.EquivalentTo(new[]{QuestJournal.ArrivalId,QuestJournal.PrimerId}),"a new colonist: the city visit and the primer");
    Assert.That(rig.journal.TrackedId,Is.EqualTo(QuestJournal.ArrivalId),"the city visit is tracked first");
    Assert.That(missions.First(m=>m.id==QuestJournal.ArrivalId).steps.First().current);
    // not picked by the player: tracking follows the primer once it has begun
    rig.tutorial.Restore(BermsStep.TakePistol);typeof(QuestJournal).GetField("dirty",Any).SetValue(rig.journal,true);
    Assert.That(rig.journal.Tracked.id,Is.EqualTo(QuestJournal.PrimerId));Assert.That(rig.journal.TrackedChosen,Is.False);
    // picked: the city visit stays tracked while the primer moves on
    Assert.That(rig.journal.Track(QuestJournal.ArrivalId));rig.tutorial.Restore(BermsStep.Draw);typeof(QuestJournal).GetField("dirty",Any).SetValue(rig.journal,true);
    Assert.That(rig.journal.Tracked.id,Is.EqualTo(QuestJournal.ArrivalId));
    // the primer done and the first order running: the order and the home appear; tracking moves to the order chain
    rig.save.Apply(new WardSaveData{version=3,credits=60,bermsStep="Complete",hasPistol=true,orders=new FieldOrderState{index=0,id="order_steady_hands"}});
    rig.Play();
    missions=rig.journal.Missions;
    Assert.That(missions.Any(m=>m.id==QuestJournal.OrderPrefix+"order_steady_hands"&&m.Active));
    Assert.That(missions.Single(m=>m.id==QuestJournal.PrimerId).status,Is.EqualTo(MissionStatus.Complete));
    var home=missions.Single(m=>m.id==QuestJournal.HomeId);Assert.That(home.Active);Assert.That(home.steps.Count,Is.EqualTo(3));
    Assert.That(rig.journal.TrackedId,Is.EqualTo(QuestJournal.OrderPrefix+"order_steady_hands"));
    Assert.That(rig.journal.Track(QuestJournal.PrimerId),Is.False,"a completed mission cannot be tracked");
    Assert.That(rig.journal.Track(QuestJournal.HomeId));Assert.That(rig.journal.Tracked.id,Is.EqualTo(QuestJournal.HomeId));
    // the home completes: tracking hands over to the next active mission
    rig.session.SetFlag(WardHome.LeasedFlag);rig.session.SetFlag(WardHome.StoredFlag);
    typeof(QuestJournal).GetField("dirty",Any).SetValue(rig.journal,true);
    Assert.That(rig.journal.Missions.Single(m=>m.id==QuestJournal.HomeId).status,Is.EqualTo(MissionStatus.Complete));
    Assert.That(rig.journal.TrackedId,Is.EqualTo(QuestJournal.OrderPrefix+"order_steady_hands"));
   }
  }

  // ------------------------------------------------------------------ scene
  [Test] public void SceneHasTheLeasedHomeWiredOnTheSouthWall()
  {
   var scene=UnityEditor.SceneManagement.EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try
   {
    T[] All<T>()where T:Component=>scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<T>(true)).ToArray();
    var home=All<WardHome>().Single();
    Assert.That(home.gameObject.activeInHierarchy);
    Assert.That(Vector3.Distance(home.transform.position,new Vector3(27.5f,0,-41.4f)),Is.LessThan(.6f),"the rust container on the south wall");
    Assert.That(home.session,Is.Not.Null);Assert.That(home.leasePrice,Is.EqualTo(40));Assert.That(home.lockerFeedsBench);
    Assert.That(home.door,Is.Not.Null);Assert.That(home.door.leaf,Is.Not.Null);Assert.That(home.door.leafCollider,Is.Not.Null);Assert.That(home.door.lockedPrompt,Is.Not.Null);
    Assert.That(home.locker,Is.Not.Null);Assert.That(home.bunk,Is.Not.Null);Assert.That(home.lockerPoint,Is.Not.Null);Assert.That(home.wakePoint,Is.Not.Null);
    Assert.That(home.locker!=home.bunk);
    var zone=home.GetComponentInChildren<CameraConfineZone>(true);Assert.That(zone,Is.Not.Null);
    var local=zone.transform.InverseTransformPoint(home.wakePoint.position+Vector3.up*zone.chestHeight)-zone.center;
    Assert.That(Mathf.Abs(local.x)<=zone.size.x/2&&Mathf.Abs(local.z)<=zone.size.z/2,"the wake point is inside the confined interior");
    var bridge=All<AthenDebugBridge>().Single();
    foreach(var name in new[]{"home_door","home_inside","home_locker","home_bunk"})Assert.That(bridge.landmarks.Find(name),Is.Not.Null,name);
    Assert.That(Vector3.Distance(bridge.landmarks.Find("home_locker").position,home.locker.transform.position),Is.LessThan(home.locker.range));
    Assert.That(Vector3.Distance(bridge.landmarks.Find("home_bunk").position,home.bunk.transform.position),Is.LessThan(home.bunk.range));
    Assert.That(Vector3.Distance(bridge.landmarks.Find("home_door").position,home.door.transform.position),Is.LessThan(home.door.openDistance));
    // the WallHomeA it replaced stays in the scene, inactive
    Assert.That(scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<Transform>(true)).Any(t=>t.name=="Wall home south 2"&&!t.gameObject.activeInHierarchy));
   }
   finally{UnityEditor.SceneManagement.EditorSceneManager.ClosePreviewScene(scene);}
  }

  // ------------------------------------------------------------------ interface
  [Test] public void HudHasTheJournalLockerAndRestPanelsAndTenSlots()
  {
   var uxml=File.ReadAllText("Assets/AthenHill/UI/CityHUD.uxml");
   foreach(var name in new[]{"journal-panel","stash-panel","rest-panel","objective-title"})Assert.That(uxml,Does.Contain($"name=\"{name}\""),name);
   for(int i=1;i<=10;i++)Assert.That(uxml,Does.Contain($"name=\"slot{i}\""));
   Assert.That(uxml,Does.Contain("Open journal · J"));
   Assert.That(System.Enum.GetNames(typeof(CityState)),Is.SupersetOf(new[]{"Journal","Stash","Rest"}));
   Assert.That(System.Enum.GetNames(typeof(CityState)),Does.Not.Contain("Notes"));
  }
 }
}
