using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
namespace AthenHill.Tests
{
 /// Milestone 3 (22 Nov 2026): key-gated Field Lattice Terminal, permanent unlock, combat safety lock,
 /// additive save/restore of unlockedTerminals & lastTerminalId, Continue wake point, two-way fast travel,
 /// and WorldMap relay marker.
 public class LatticeTerminalTests
 {
  const BindingFlags Any=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static FieldOrderSet Orders()=>AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset");
  static void Set(object target,string property,object value)=>target.GetType().GetProperty(property,Any).SetValue(target,value);

  string folder;
  [SetUp] public void MakeFolder(){folder=Path.Combine(Path.GetTempPath(),"ward-terminal-tests-"+System.Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);}
  [TearDown] public void RemoveFolder(){if(Directory.Exists(folder))Directory.Delete(folder,true);Time.timeScale=1;}

  sealed class Rig:System.IDisposable
  {
   public GameObject go;
   public GameSession session;
   public CraftingSession crafting;
   public PlayerCombat combat;
   public BermsTutorial tutorial;
   public FieldOrders orders;
   public WardSaveGame save;
   public ShopModel pack;
   public CraftingModel model;
   public Transform latticePoint;
   public Transform terminalWake;
   public WardenWaystation waystation;
   public LatticeTerminal terminal;

   public Rig(string folder,bool withTerminal=true)
   {
    go=new GameObject("terminal rig");go.SetActive(false);
    var input=go.AddComponent<GameInput>();
    input.definition=AssetDatabase.LoadAssetAtPath<InputActionAsset>("Assets/AthenHill/Data/Controls.inputactions");
    var playerGo=new GameObject("player");playerGo.transform.SetParent(go.transform);
    var motor=playerGo.AddComponent<PlayerMotor>();
    session=go.AddComponent<GameSession>();
    session.input=input;session.player=motor;session.catalog=City();session.npcs=new NpcAgent[0];

    var jackGo=new GameObject("lattice_jack");jackGo.transform.SetParent(go.transform);
    jackGo.transform.position=new Vector3(0f,0f,35.5f);
    latticePoint=jackGo.transform;
    session.latticePoint=latticePoint;

    crafting=go.AddComponent<CraftingSession>();crafting.data=Data();
    combat=playerGo.AddComponent<PlayerCombat>();crafting.combat=combat;
    var t=new GameObject("berms");t.transform.SetParent(go.transform);tutorial=t.AddComponent<BermsTutorial>();tutorial.session=session;tutorial.combat=combat;
    orders=go.AddComponent<FieldOrders>();orders.data=Orders();orders.crafting=crafting;orders.tutorial=tutorial;orders.combat=combat;
    save=go.AddComponent<WardSaveGame>();save.directoryOverride=folder;

    if(withTerminal)
    {
     var wsGo=new GameObject("waystation_berms_mid");wsGo.transform.SetParent(go.transform);
     wsGo.transform.position=new Vector3(-185f,0f,42f);
     waystation=wsGo.AddComponent<WardenWaystation>();
     waystation.id=LatticeTerminalLogic.DefaultWaystationId;
     waystation.displayName="Warden waystation";
     waystation.session=session;
     waystation.player=combat;

     var wakeGo=new GameObject("wake_point");wakeGo.transform.SetParent(wsGo.transform);
     wakeGo.transform.position=new Vector3(-183f,0f,44f);
     terminalWake=wakeGo.transform;
     waystation.respawnPoint=terminalWake;

     terminal=wsGo.AddComponent<LatticeTerminal>();
     terminal.terminalId=LatticeTerminalLogic.DefaultWaystationId;
     terminal.displayName=LatticeTerminalLogic.DefaultDisplayName;
     terminal.requiredKeyId=LatticeTerminalLogic.DefaultKeyId;
     terminal.session=session;
     terminal.waystation=waystation;
     terminal.wakePoint=terminalWake;
     waystation.terminal=terminal;
    }

    go.SetActive(true);
    typeof(GameSession).GetMethod("Awake",Any).Invoke(session,null);
    if(session.Map)typeof(WorldMap).GetMethod("Awake",Any).Invoke(session.Map,null);
    typeof(GameInput).GetMethod("OnEnable",Any).Invoke(input,null);
    if(waystation)typeof(WardenWaystation).GetMethod("OnEnable",Any).Invoke(waystation,null);
    if(terminal)typeof(LatticeTerminal).GetMethod("OnEnable",Any).Invoke(terminal,null);

    // Ensure berms_relay_key exists in the ShopModel item list even if CityCatalog hasn't been patched yet.
    var items=new List<ItemSpec>(City().items??System.Array.Empty<ItemSpec>());
    if(!items.Any(x=>x!=null&&x.id==LatticeTerminalLogic.DefaultKeyId))
     items.Add(new ItemSpec{id=LatticeTerminalLogic.DefaultKeyId,name="Warden Relay Key",maxStack=1,excludeFromTrade=true});
    pack=new ShopModel(items.ToArray(),City().startingCredits);
    model=new CraftingModel(Data(),items.ToArray(),pack,()=>combat.hasPistol);
    Set(session,"Shop",pack);Set(session,"State",CityState.MainMenu);
    Set(crafting,"Model",model);Set(crafting,"Session",session);Set(crafting,"Loot",new LootBook(1729));
    combat.BindLoadout(model.Loadout);
   }

   public void Dispose()
   {
    if(terminal)typeof(LatticeTerminal).GetMethod("OnDisable",Any).Invoke(terminal,null);
    if(waystation)typeof(WardenWaystation).GetMethod("OnDisable",Any).Invoke(waystation,null);
    Object.DestroyImmediate(go);
   }
  }

  [Test] public void PureLogicEnforcesKeyGatingPermanentUnlockAndCombatLock()
  {
   // Combat lock overrides everything.
   Assert.That(LatticeTerminalLogic.EvaluateInteraction(false,true,true,out var msg),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.CombatBlocked));
   Assert.That(msg,Is.EqualTo(LatticeTerminalLogic.CombatBlockedMessage));
   Assert.That(LatticeTerminalLogic.EvaluateInteraction(true,false,true,out msg),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.CombatBlocked));
   Assert.That(LatticeTerminalLogic.CanUseTerminal(true,out var blocked),Is.False);
   Assert.That(blocked,Is.EqualTo(LatticeTerminalLogic.CombatBlockedMessage));
   Assert.That(LatticeTerminalLogic.CanUseTerminal(false,out blocked),Is.True);
   Assert.That(blocked,Is.Null);

   // Locked without key -> MissingKey.
   Assert.That(LatticeTerminalLogic.EvaluateInteraction(false,false,false,out msg),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.MissingKey));
   Assert.That(msg,Does.Contain("Warden Relay Key"));

   // Locked with key -> Unlocked.
   Assert.That(LatticeTerminalLogic.EvaluateInteraction(false,true,false,out msg),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.Unlocked));
   Assert.That(msg,Does.Contain("permanently online"));

   // Once unlocked, key is no longer required -> Online.
   Assert.That(LatticeTerminalLogic.EvaluateInteraction(true,false,false,out msg),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.Online));
   Assert.That(msg,Is.Null);
  }

  [Test] public void LiveTerminalRequiresKeyThenStaysPermanentlyOnline()
  {
   using var rig=new Rig(folder);
   rig.session.StartGame();

   Assert.That(rig.terminal.Unlocked,Is.False);
   Assert.That(rig.terminal.HasKey,Is.False);
   Assert.That(rig.terminal.Interact(),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.MissingKey));
   Assert.That(rig.terminal.Unlocked,Is.False);
   Assert.That(rig.session.HasFlag("terminal_hint:berms_mid"),Is.True,"one-time Ossa radio hint recorded");

   // Grant Warden Relay Key and unlock.
   Assert.That(rig.pack.Grant(LatticeTerminalLogic.DefaultKeyId,1,0,out var give),give);
   Assert.That(rig.terminal.HasKey,Is.True);
   Assert.That(rig.terminal.Interact(),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.Unlocked));
   Assert.That(rig.terminal.Unlocked,Is.True);
   Assert.That(rig.session.IsTerminalUnlocked("berms_mid"),Is.True);
   Assert.That(rig.session.LastTerminalId,Is.EqualTo("berms_mid"));
   Assert.That(rig.waystation.Found,Is.True,"unlocking the terminal marks its waystation found");

   // Remove the key from inventory: terminal remains permanently online.
   Assert.That(rig.pack.TryApply(new[]{new KeyValuePair<string,int>(LatticeTerminalLogic.DefaultKeyId,-1)},0,out _),Is.True);
   Assert.That(rig.terminal.HasKey,Is.False);
   Assert.That(rig.terminal.Unlocked,Is.True);
   Assert.That(rig.terminal.Interact(),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.Online));
  }

  [Test] public void EngagedDroidBlocksUnlockSaveAndFastTravel()
  {
   using var rig=new Rig(folder);
   rig.session.StartGame();
   Assert.That(rig.pack.Grant(LatticeTerminalLogic.DefaultKeyId,1,0,out _),Is.True);

   var droidGo=new GameObject("test_droid");
   FeralDroid droid=null;
   try
   {
    droid=droidGo.AddComponent<FeralDroid>();
    typeof(FeralDroid).GetMethod("OnEnable",Any).Invoke(droid,null);
    // Idle droid does not block.
    Assert.That(LatticeTerminalLogic.AnyDroidEngaged(),Is.False);

    // Put droid into Chase (Engaged = true).
    Set(droid,"State",DroidState.Chase);
    Assert.That(droid.Engaged,Is.True);
    Assert.That(LatticeTerminalLogic.AnyDroidEngaged(),Is.True);

    Assert.That(rig.terminal.Interact(),Is.EqualTo(LatticeTerminalLogic.InteractionOutcome.CombatBlocked));
    Assert.That(rig.terminal.Unlocked,Is.False);

    // Even if unlocked directly, ManualSave & FastTravelToWard & FastTravelToTerminal refuse while engaged.
    rig.session.UnlockTerminal("berms_mid");
    Assert.That(rig.terminal.ManualSave(),Is.False);
    Assert.That(rig.terminal.FastTravelToWard(),Is.False);
    Assert.That(rig.session.FastTravelToTerminal("berms_mid"),Is.False);

    // Dead droid does not block.
    Set(droid,"State",DroidState.Dead);
    Assert.That(LatticeTerminalLogic.AnyDroidEngaged(),Is.False);
    Assert.That(rig.terminal.ManualSave(),Is.True);
   }
   finally
   {
    if(droid)typeof(FeralDroid).GetMethod("OnDisable",Any).Invoke(droid,null);
    Object.DestroyImmediate(droidGo);
   }
  }

  [Test] public void SaveRestorePersistsTerminalsAndContinueWakesAtLastUnlockedTerminal()
  {
   // Additive compatibility: older v4 save without terminal fields parses cleanly.
   const string legacyV4="{\"version\":4,\"credits\":42,\"bermsStep\":\"Complete\"}";
   Assert.That(WardSaveFile.TryParse(legacyV4,out var legacy,out var err),err);
   Assert.That(WardSaveData.CurrentVersion,Is.EqualTo(4));
   Assert.That(legacy.unlockedTerminals,Is.Null.Or.Empty);
   Assert.That(legacy.lastTerminalId,Is.Null.Or.Empty);
   Assert.That(LatticeTerminalLogic.ResolveWakeTerminalId("berms_mid",legacy.unlockedTerminals),Is.Null);

   // Unlock, save at berms_mid, then Continue in a fresh Rig.
   using(var a=new Rig(folder))
   {
    a.session.StartGame();
    Assert.That(a.pack.Grant(LatticeTerminalLogic.DefaultKeyId,1,0,out _),Is.True);
    Assert.That(a.terminal.TryUnlock(),Is.True);
    Assert.That(a.save.SaveNow("terminal"),Is.True);
    Assert.That(WardSaveFile.TryRead(a.save.SavePath,out var written,out err),err);
    Assert.That(written.unlockedTerminals,Is.EqualTo(new[]{"berms_mid"}));
    Assert.That(written.lastTerminalId,Is.EqualTo("berms_mid"));
   }

   using(var b=new Rig(folder))
   {
    // Start player at origin so we verify Continue actually teleports to terminalWake.
    b.session.player.transform.position=Vector3.zero;
    Assert.That(b.save.Continue(),Is.True);
    Assert.That(b.session.IsTerminalUnlocked("berms_mid"),Is.True);
    Assert.That(b.session.LastTerminalId,Is.EqualTo("berms_mid"));
    Assert.That(b.terminal.Unlocked,Is.True);
    Assert.That(Vector3.Distance(b.session.player.transform.position,b.terminalWake.position),Is.LessThan(.1f),"Continue wakes player at unlocked lastTerminalId");
    Assert.That(b.session.notice,Does.Contain("Waystation Lattice Relay"));
   }
  }

  [Test] public void TwoWayFastTravelResolvesTargetsAndMovesPlayerBetweenWardAndWaystation()
  {
   // Pure destination resolution.
   var lockedTargets=LatticeTerminalLogic.ResolveWardJackDestinations(City().destinations,System.Array.Empty<string>());
   Assert.That(lockedTargets.Any(t=>t.isFastTravel),Is.False,"no fast-travel target while locked");

   var unlockedTargets=LatticeTerminalLogic.ResolveWardJackDestinations(City().destinations,new[]{"berms_mid"});
   var wayTarget=unlockedTargets.SingleOrDefault(t=>t.terminalId=="berms_mid");
   Assert.That(wayTarget.isFastTravel,Is.True);
   Assert.That(wayTarget.id,Is.EqualTo("terminal:berms_mid"));
   Assert.That(wayTarget.name,Is.EqualTo(LatticeTerminalLogic.WaystationGridLabel));

   var returnTarget=LatticeTerminalLogic.ResolveTerminalReturnTarget();
   Assert.That(returnTarget.id,Is.EqualTo(LatticeTerminalLogic.WardJackDestinationId));
   Assert.That(returnTarget.isFastTravel,Is.True);

   // Live two-way travel: Berms terminal -> Ward Lattice Jack -> back via CityState.Grid.
   using var rig=new Rig(folder);
   rig.session.StartGame();
   rig.session.UnlockTerminal("berms_mid");
   rig.session.WakeAt(rig.terminalWake);

   Assert.That(rig.terminal.FastTravelToWard(),Is.True);
   Assert.That(Vector3.Distance(rig.session.player.transform.position,rig.latticePoint.position),Is.LessThan(.1f));
   Assert.That(rig.session.linked,Is.True);
   Assert.That(rig.session.selectedDestination,Is.EqualTo(LatticeTerminalLogic.WardJackDestinationId));

   // Open Ward Lattice Jack Grid and travel back to berms_mid.
   Set(rig.session,"State",CityState.Grid);
   Set(rig.session,"GridProgress",1f);
   Assert.That(rig.session.GridDestinations.Any(t=>t.id=="terminal:berms_mid"&&t.name==LatticeTerminalLogic.WaystationGridLabel),Is.True);
   Assert.That(rig.session.SelectDestinationById("terminal:berms_mid"),Is.True);
   Assert.That(rig.session.State,Is.EqualTo(CityState.Play),"Grid closes after fast travel");
   Assert.That(Vector3.Distance(rig.session.player.transform.position,rig.terminalWake.position),Is.LessThan(.1f));
   Assert.That(rig.session.LastTerminalId,Is.EqualTo("berms_mid"));
  }

  [Test] public void WorldMapShowsLatticeRelayMarkerOnlyOnceUnlocked()
  {
   using var rig=new Rig(folder);
   rig.session.StartGame();
   var map=rig.session.Map;
   Assert.That(map,Is.Not.Null);

   var relayPlace=map.Places.FirstOrDefault(p=>p.id==WorldMapDiscovery.LatticeRelayId("berms_mid"));
   Assert.That(relayPlace,Is.Not.Null,"LatticeTerminal is registered on WorldMap");
   Assert.That(map.Shown(relayPlace),Is.False,"hidden while terminal is locked");

   rig.session.UnlockTerminal("berms_mid");
   Assert.That(map.Shown(relayPlace),Is.True,"shown once terminal is unlocked");

   // Verify implied terminal discovery on save restore.
   var implied=WorldMapDiscovery.ImpliedTerminals(new[]{"berms_mid"}).ToList();
   Assert.That(implied,Is.EqualTo(new[]{"lattice:berms_mid"}));
  }
 }
}
