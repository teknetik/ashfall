using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// One Buy parts purchase; listeners may append words to the notice (e.g. " Schematic discovered: …").
 public sealed class PartPurchase{public string itemId,note="";}
 /// Journal (5 Oct 2026) replaces the old City notes screen in place; Stash (the home locker) and Rest (the home bunk)
 /// are appended.
 public enum CityState { Boot,Play,Dialogue,Shop,Grid,Paused,Inventory,Journal,Credits,Error,Settings,MainMenu,Fabricator,Stash,Rest }
 public class GameSession:MonoBehaviour,IQuestState
 {
  public CityCatalog catalog;
  [Tooltip("Character progression rules. When unassigned, loads Resources/CharacterCatalog.")]
  public CharacterCatalog characterCatalog;
  public CharacterModel Character {get;private set;}
  public GameSettings Settings {get;private set;}
  /// The mission journal (5 Oct 2026). It has no authored settings, so a scene without one gets one here.
  public QuestJournal Journal {get;private set;}
  void Awake(){Settings=GetComponent<GameSettings>();if(!Settings)Settings=gameObject.AddComponent<GameSettings>();Journal=GetComponent<QuestJournal>();if(!Journal)Journal=gameObject.AddComponent<QuestJournal>();reducedMotion=Settings.ReadReducedMotion(reducedMotion);RadioLine.timing=radioTiming??new RadioQueue.Timing();}
  void SettingsChanged(){muted=Settings.Sound.muted;if(ActiveNpc)ActiveNpc.SetVoiceLevel(Settings.Sound.effects);Changed?.Invoke();}
  public GameInput input;
  public PlayerMotor player;
  public FollowCamera follow;
  public NpcAgent[] npcs;
  [Min(0)]public float interactionRange=2.4f;
  public bool reducedMotion,muted;
  public Transform hillPoint,latticePoint,ringPoint;
  public float hillRadius=7,hillMinimumHeight=1,latticeRange=3.15f;
  public Vector2 ringHalfSize=new Vector2(5.4f,2.8f);
  public CityState State {get;private set;}=CityState.Boot;
  public bool HasStarted {get;private set;}
  public string DetailItemId {get;private set;}
  public string ActiveStationId {get;private set;}
  /// The workbench the fabricator window was opened at (its title and subtitle head the window).
  public CraftingStationMarker ActiveStation {get;private set;}
  CityState settingsReturn=CityState.Paused;
  public ShopModel Shop {get;private set;}
  public NpcAgent ActiveNpc {get;private set;}
  public string dialogueNode="greeting",notice="",selectedDestination="";
  public float GridProgress {get;private set;}
  public readonly List<string> Log=new List<string>();
  public readonly HashSet<string> Spoken=new HashSet<string>();
  /// Story flags set by dialogue choices (DialogueChoice.setFlag); saved with the game.
  public readonly HashSet<string> Flags=new HashSet<string>();
  public bool visitedHill,boughtFlask,soldScrap,linked;
  [Header("Messages")]
  [Tooltip("Warden radio lines: on screen for Base + Seconds Per Word × words (clamped), one at a time, and only counting down during play.")]
  public RadioQueue.Timing radioTiming=new RadioQueue.Timing();
  [Tooltip("Short system notices: on screen for 2.5 s + this many seconds per word, clamped to 4–10 s.")]
  [Min(0)]public float noticeSecondsPerWord=.25f;
  /// The radio channel (Ossa's briefings). Separate from notices, so pickups and prompts never overwrite a briefing.
  public RadioQueue RadioLine {get;}=new RadioQueue();
  public event Action Changed;
  public event Action<CitySoundCue> SoundRequested;
  /// Plays a UI cue through CityAudio (e.g. a finished or stopped fabrication at the workbench).
  public void Cue(CitySoundCue cue)=>SoundRequested?.Invoke(cue);
  public int LogRevision {get;private set;}
  bool ringInside;float noticeTime;
  public bool Complete=>visitedHill&&Spoken.Count==4&&boughtFlask&&soldScrap&&linked;
  public string Objective=>!visitedHill?"Reach the Hill Tree.":Spoken.Count<4?$"Meet the colonists · {Spoken.Count}/4 conversations":!boughtFlask||!soldScrap?"Buy a flask and sell your scrap at Basic General.":!linked?"Use the Lattice Jack in the north court.":"A place on the hill. City visit complete.";
  public DialogueNode Dialogue=>ActiveNpc?ActiveNpc.definition.nodes.First(x=>x.id==dialogueNode):null;
  public const int MaxChoices=3;
  /// The current node's choices whose conditions hold (at most MaxChoices; the HUD shows one button each).
  public DialogueChoice[] Choices=>DialogueFlow.Choices(Dialogue,this,MaxChoices);
  /// The node a colonist opens with: the first entry whose condition holds, else "greeting".
  public string StartNode(NpcDefinition d)=>DialogueFlow.StartNode(d,this);
  /// A conversation started (after the opening node was chosen): field orders count report visits from it.
  public event Action<NpcAgent> Talked;
  // ---- IQuestState (dialogue conditions)
  FieldOrders questOrders;BermsTutorial questTutorial;PlayerCombat questCombat;bool questBound;
  void BindQuest()
  {
   if(questBound)return;questBound=true;
   questOrders=GetComponent<FieldOrders>();
   questTutorial=questOrders&&questOrders.tutorial?questOrders.tutorial:FindAnyObjectByType<BermsTutorial>();
   questCombat=player?player.GetComponent<PlayerCombat>():null;
  }
  bool IQuestState.PrimerComplete{get{BindQuest();return questTutorial&&questTutorial.Step==BermsStep.Complete;}}
  bool IQuestState.HasPistol{get{BindQuest();return questCombat&&questCombat.hasPistol;}}
  string IQuestState.CurrentOrderId{get{BindQuest();return questOrders&&questOrders.Progress!=null?questOrders.Progress.Current?.id:null;}}
  OrderStage IQuestState.Stage{get{BindQuest();return questOrders&&questOrders.Ready?questOrders.Progress.Stage(questOrders.crafting.Model,Shop):OrderStage.NotStarted;}}
  bool IQuestState.CurrentReported{get{BindQuest();return questOrders&&questOrders.Progress!=null&&questOrders.Progress.CurrentReported;}}
  public bool HasFlag(string id)=>!string.IsNullOrEmpty(id)&&Flags.Contains(id);
  public void SetFlag(string id){if(!string.IsNullOrEmpty(id)&&Flags.Add(id)){FlagSet?.Invoke(id);Changed?.Invoke();}}
  /// A story flag was recorded (autosave hook).
  public event Action<string> FlagSet;
  /// Display name of the colonist at the open counter (Mira when none, as Basic General was the only counter).
  public string Vendor=>ActiveNpc&&ActiveNpc.definition?ActiveNpc.definition.displayName:"Mira";
  public ShopProfile ActiveShop=>ActiveNpc&&ActiveNpc.definition&&ActiveNpc.definition.shop!=null?ActiveNpc.definition.shop:DefaultShop;
  static readonly ShopProfile DefaultShop=new ShopProfile();
  void Start()
  {
   Settings.Changed+=SettingsChanged;muted=Settings.Sound.muted;Settings.ApplySound();
   Shop=new ShopModel(catalog.items,catalog.startingCredits);
   if(!characterCatalog)characterCatalog=Resources.Load<CharacterCatalog>("CharacterCatalog");
   if(characterCatalog)
   {
    Character=new CharacterModel(characterCatalog,Shop);
    Shop.CapacityFailure=Character.CapacityFailure;
    Character.Changed+=OnCharacterChanged;
    if(player)
    {
     var combat=player.GetComponent<PlayerCombat>();
     if(combat)combat.BindCharacter(Character);
    }
   }
   else Debug.LogError("CharacterCatalog is missing from Resources; progression is unavailable.");
   Log.Add("Linn: Meet me on the hill.");SetState(CityState.MainMenu);
  }
  void OnCharacterChanged()=>Changed?.Invoke();
  void OnDestroy(){if(Settings)Settings.Changed-=SettingsChanged;if(Character!=null)Character.Changed-=OnCharacterChanged;Time.timeScale=1;AudioListener.pause=false;AudioListener.volume=1;}
  // Do not change session state from OnApplicationFocus. Linux launchers and
  // window managers can report a transient focus loss while the player window is
  // still opening, which otherwise starts the game paused with movement disabled.
  // The explicit Escape and HUD pause controls remain available.
  void Update()
  {
   var keyboard=UnityEngine.InputSystem.Keyboard.current;
   if(keyboard?.tabKey.wasPressedThisFrame==true)ToggleInventory();
   else if(keyboard?.jKey.wasPressedThisFrame==true)ToggleJournal();
   if(input.Cancel){if(State==CityState.Play)SetState(CityState.Paused);else Close();}
   if(State==CityState.Play)
   {
    if(input.Pressed("Reset"))ResetPlayer();
    if(input.Pressed("Interact"))Interact();
    for(int i=1;i<=HotbarModel.Slots;i++)if(input.Pressed("Slot"+HotbarModel.Key(i)))UseHotbar(i);
    var p=player.transform.position;
    if(!visitedHill&&hillPoint&&new Vector2(p.x-hillPoint.position.x,p.z-hillPoint.position.z).magnitude<hillRadius&&p.y>hillPoint.position.y+hillMinimumHeight){visitedHill=true;Changed?.Invoke();}
    bool inside=NearRing&&p.y>ringPoint.position.y-.2f;
    if(inside&&!ringInside){Notify("Destination offline. The far ring has gone quiet.","Ring Gate");SoundRequested?.Invoke(CitySoundCue.Unavailable);}ringInside=inside;
   }
   if(State==CityState.Grid&&GridProgress<1){GridProgress=Mathf.Min(1,GridProgress+Time.deltaTime/Mathf.Max(.01f,catalog.transitionSeconds));Changed?.Invoke();}
   if(noticeTime>0){noticeTime-=Time.unscaledDeltaTime;if(noticeTime<=0){notice="";Changed?.Invoke();}}
   if(RadioLine.Tick(Time.unscaledDeltaTime,State==CityState.Play))Changed?.Invoke();
  }
  public NpcAgent Nearest=>npcs.Where(n=>n&&Vector3.Distance(n.transform.position,player.transform.position)<=interactionRange).OrderBy(n=>Vector3.Distance(n.transform.position,player.transform.position)).FirstOrDefault();
  bool NearLattice=>latticePoint&&Vector3.Distance(player.transform.position,latticePoint.position)<latticeRange;
  bool NearRing=>ringPoint&&Mathf.Abs(player.transform.position.x-ringPoint.position.x)<ringHalfSize.x&&Mathf.Abs(player.transform.position.z-ringPoint.position.z)<ringHalfSize.y;
  WorldInteractable NearWorld=>player?WorldInteractable.Nearest(player.transform.position):null;
  public string Prompt=>State!=CityState.Play?"":Nearest?$"E · Talk to {Nearest.definition.displayName}":NearLattice?"E · Use Lattice Jack":NearRing?"E · Check Ring Gate":NearWorld?NearWorld.prompt:"";
  public void Interact()
  {
   if(State!=CityState.Play)return;
   var n=Nearest;
   if(n){ActiveNpc=n;dialogueNode=StartNode(n.definition);n.talking=true;if(n.countsForCityVisit)Spoken.Add(n.definition.id);SetState(CityState.Dialogue);AddLog(n.definition.displayName,Dialogue.text);SpeakDialogue();Talked?.Invoke(n);}
   else if(NearLattice){GridProgress=0;selectedDestination="";SetState(CityState.Grid);AddLog("Lattice Jack","Signal acquired. Opening the sector lattice.");SoundRequested?.Invoke(CitySoundCue.LatticeOpen);}
   else if(!NearRing&&NearWorld)NearWorld.Use();
   else {Notify(NearRing?"Destination offline. The far ring has gone quiet.":"Move closer to a colonist or terminal.",NearRing?"Ring Gate":"System");SoundRequested?.Invoke(CitySoundCue.Unavailable);}
  }
  public void Choose(int index)
  {
   if(State!=CityState.Dialogue)return;
   var choices=Choices;if(index<0||index>=choices.Length)return;
   var choice=choices[index];AddLog("You",choice.label);
   SetFlag(choice.setFlag);
   if(choice.action=="shop")SetState(CityState.Shop);
   else if(choice.action=="close")Close();
   else if(choice.action=="lease_home")
   {
    // Linn's housing roll: the lease is taken (credits paid) before the conversation moves on; a refusal stays here.
    if(LeaseHome()){dialogueNode=choice.next;AddLog(ActiveNpc.definition.displayName,Dialogue.text);SpeakDialogue();Changed?.Invoke();}
   }
   else if(choice.action=="fabricator"&&ActiveNpc.workbench)
   {
    // "Use the bench": straight from the conversation to the workbench the colonist keeps.
    var bench=ActiveNpc.workbench;ActiveNpc.StopSpeaking();ActiveNpc.talking=false;ActiveNpc=null;
    ActiveStation=bench;ActiveStationId=bench.stationId;SetState(CityState.Fabricator);
   }
   else {dialogueNode=choice.next;AddLog(ActiveNpc.definition.displayName,Dialogue.text);SpeakDialogue();Changed?.Invoke();}
  }
  public bool Trade(string id,bool buy)
  {
   if(State!=CityState.Shop)return false;
   var spec=Shop.Spec(id);string message="";
   // A counter trades only its own stock (Field Supply: field gear; Basic General leaves that gear to Field Supply).
   bool stocked=spec!=null&&(buy?MerchantStock.CanBuy(spec,ActiveShop)&&!MerchantStock.UsesPartsPrice(spec,ActiveShop):MerchantStock.CanSell(spec,ActiveShop));
   bool ok=stocked&&Shop.Trade(id,buy,out message,Vendor);
   if(!stocked)message=spec==null?"That item is not available.":MerchantStock.IsMagazine(spec)?$"{spec.name} is on the magazine shelf.":buy?$"{Vendor} does not stock {spec.name}.":$"{Vendor} does not buy {spec.name}.";
   if(ok&&buy&&id=="water_flask")boughtFlask=true;
   if(ok&&!buy&&id=="scrap_coil")soldScrap=true;
   Notify(message,Vendor);SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   if(ok)Traded?.Invoke();
   return ok;
  }
  /// A counter's Sell salvage list (Basic General, Salvage): one atomic sale of several units of salvage the trader buys
  /// but does not stock.
  public bool SellSalvage(string id,int count)
  {
   if(State!=CityState.Shop)return false;
   string message=$"{Vendor} does not buy that.";
   bool ok=ActiveShop.salvage&&ShopModel.BuysAsSalvage(Shop.Spec(id))&&Shop.Sell(id,count,out message);
   Notify(message,Vendor);SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   if(ok)Traded?.Invoke();
   return ok;
  }
  /// A counter's Buy parts list: one common or uncommon crafting part at its premium parts price.
  public bool BuyPart(string id)
  {
   if(State!=CityState.Shop)return false;
   string message=$"{Vendor} does not sell parts.";
   bool ok=ActiveShop.parts&&Shop.BuyPart(id,1,out message,Vendor);
   var purchase=new PartPurchase{itemId=id};
   if(ok)PartBought?.Invoke(purchase);
   Notify(message+purchase.note,Vendor);SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   if(ok)Traded?.Invoke();
   return ok;
  }
  /// A counter's digital magazine shelf (Field Supply): one atomic purchase that downloads the magazine to the field slate
  /// and teaches every schematic it lists (CraftingModel.ReadMagazine). Nothing enters the pack; ownership is the set of
  /// known recipes, so it is saved with the crafting state. Nothing changes if the credits fall short or it is owned.
  public bool BuyMagazine(string id)
  {
   if(State!=CityState.Shop)return false;
   var spec=Shop.Spec(id);var model=GetComponent<CraftingSession>()?.Model;string message;bool ok=false;
   var taught=model!=null&&spec!=null?model.MagazineRecipes(id).ToList():new List<CraftRecipe>();
   if(!ActiveShop.magazines)message=$"{Vendor} has no magazine shelf.";
   else if(spec==null||!MerchantStock.IsMagazine(spec)||spec.buyPrice<=0||spec.excludeFromTrade)message="That magazine is not on the shelf.";
   else if(model==null||taught.Count==0)message=$"{spec.name} has nothing your field slate can use yet.";
   else if(model.OwnsMagazine(id))message=$"{spec.name} is already on your field slate.";
   else if(Shop.Credits<spec.buyPrice)message=$"You need {spec.buyPrice-Shop.Credits} more credits for {spec.name}.";
   else if(!Shop.TryApply(Array.Empty<KeyValuePair<string,int>>(),-spec.buyPrice,out _))message="This trade cannot be completed.";
   else
   {
    var learned=model.ReadMagazine(id);ok=true;
    message=$"Downloaded {spec.name} for {spec.buyPrice} credits. "+CraftingText.Discovered(learned.Count>0?learned:taught)+" Make them at Brann's workbench in Salvage.";
   }
   Notify(message,Vendor);SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   if(ok){MagazineBought?.Invoke(id);Traded?.Invoke();}
   return ok;
  }
  /// A magazine was downloaded (QA and autosave hooks).
  public event Action<string> MagazineBought;
  // ---- Consumables (5 Oct 2026): used from the hotbar slot the player put them on; also usable from code (QA, tests).
  float consumableReady;
  /// Uses one carried unit of a consumable: heals (× Healing efficiency) and/or refills and overclocks the weapon charge.
  /// Refused, with nothing used, when it would do nothing (full health, no weapon), while cooling down or outside play.
  public bool UseItem(string id)
  {
   if(State!=CityState.Play||Shop==null)return false;
   var spec=catalog.Consumable(id);var item=Shop.Spec(id);
   var combat=player?player.GetComponent<PlayerCombat>():null;
   string message;bool ok=false;
   if(spec==null||item==null)message="That item cannot be used.";
   else if(Shop.Quantity(id)<1)message=$"No {item.name} carried."+(item.HasTag("field_supply")?" Field Supply stocks them.":"");
   else if(Time.time<consumableReady)message="Still steadying from the last one.";
   else
   {
    var health=combat?combat.Health:null;
    float missing=health?health.max-health.Current:0;
    bool heals=spec.restoreHealth>0&&health&&health.Alive&&missing>.5f;
    bool charges=(spec.restoreNano>0||spec.overclockSeconds>0)&&combat&&combat.hasPistol;
    if(!heals&&!charges)message=spec.restoreHealth>0?"You are not hurt.":combat&&!combat.hasPistol?"You have no nano weapon to charge.":$"{item.name} would do nothing now.";
    else if(!Shop.TryApply(new[]{new KeyValuePair<string,int>(id,-1)},0,out _))message="That item cannot be used.";
    else
    {
     ok=true;consumableReady=Time.time+catalog.consumableCooldown;var parts=new List<string>();
     if(heals)
     {
      float before=health.Current;health.Heal(spec.restoreHealth*HealingScale);
      parts.Add($"+{Mathf.RoundToInt(health.Current-before)} health");
     }
     if(charges)
     {
      float before=combat.Nano;combat.Recharge(spec.restoreNano,spec.overclockSeconds,spec.overclockRegen);
      if(combat.Nano-before>=.5f)parts.Add($"+{Mathf.RoundToInt(combat.Nano-before)} nano");
      if(spec.overclockSeconds>0)parts.Add($"regulator overclocked {spec.overclockSeconds:0} s");
     }
     message=$"Used {item.name}: {string.Join(", ",parts)}. {Shop.Quantity(id)} left.";
    }
   }
   Notify(message,"Field Pack");
   if(ok){ItemUsed?.Invoke(id);SoundRequested?.Invoke(CitySoundCue.Trade);}else SoundRequested?.Invoke(CitySoundCue.Unavailable);
   return ok;
  }
  /// Medkit multiplier: the character's Healing efficiency (Medicine raises it); 1 without a character catalog row.
  public float HealingScale=>Character!=null&&Character.Data.derivedStats.Any(d=>d!=null&&d.id=="healingEfficiency")?Mathf.Max(0,Character.Stat("healingEfficiency")):1;
  /// A consumable was used (autosave hook; the pack changed).
  public event Action<string> ItemUsed;
  /// A trade or salvage sale completed (autosave hook).
  public event Action Traded;
  /// A crafting part was bought (the crafting session reveals schematics that use it, as for a pickup, and appends
  /// them to the purchase notice).
  public event Action<PartPurchase> PartBought;
  // ---- The home (5 Oct 2026): Linn's lease, the locker (stash) and the bunk (rest). See WardHome.
  /// The home whose locker or bunk window is open (or the one Linn leases).
  public WardHome ActiveHome {get;private set;}
  /// The home locker's contents (saved with the game). Exists from the start so saves and QA can reach it.
  public StashModel Stash=>stash??=new StashModel(Home?Home.lockerSlots:60);
  StashModel stash;
  WardHome home;bool homeSearched;
  public WardHome Home{get{if(!home&&!homeSearched){homeSearched=true;home=FindAnyObjectByType<WardHome>();}return home;}}
  /// The locker or bunk changed something the save must keep (autosave hook).
  public event Action HomeChanged;
  /// Raised by the locker window after a batch move (Store all salvage).
  public void NotifyHomeChanged(){HomeChanged?.Invoke();Changed?.Invoke();}
  /// Dialogue action "lease_home": pays the home's lease and records the flag. False (with the reason as a notice) when
  /// already leased or the credits fall short.
  public bool LeaseHome()
  {
   var h=Home;int price=h?h.leasePrice:40;string speaker=Vendor;
   if(HasFlag(WardHome.LeasedFlag)){Notify("The container home is already yours.",speaker);return false;}
   if(Shop.Credits<price){Notify($"The lease is {price} credits. You need {price-Shop.Credits} more.",speaker);SoundRequested?.Invoke(CitySoundCue.Unavailable);return false;}
   if(!Shop.TryApply(Array.Empty<KeyValuePair<string,int>>(),-price,out _)){Notify("The lease cannot be paid right now.",speaker);return false;}
   SetFlag(WardHome.LeasedFlag);
   Notify($"Lease taken for {price} credits. The rust-red container home on the south wall, behind the Nanofab yard, is yours.","Ward");
   SoundRequested?.Invoke(CitySoundCue.Trade);Traded?.Invoke();
   return true;
  }
  public void OpenStash(WardHome at)
  {
   if(State!=CityState.Play||!at)return;
   if(!at.Leased){Notify("The locker is chained. Linn on the hill holds the lease.","Ward");return;}
   ActiveHome=at;SetState(CityState.Stash);
  }
  public void OpenRest(WardHome at)
  {
   if(State!=CityState.Play||!at)return;
   if(!at.Leased)return;
   ActiveHome=at;SetState(CityState.Rest);
  }
  /// Locker window: moves count units of an item from the pack into the locker (or back with take).
  public bool MoveStash(string id,int count,bool store)
  {
   if(State!=CityState.Stash||Stash==null)return false;
   var spec=Shop.Spec(id);string name=spec!=null?spec.name:id;
   bool ok=store?Stash.Store(Shop,id,count,out var reason):Stash.Take(Shop,id,count,out reason);
   string message=ok?(store?$"Stored {count} × {name} in the locker.":$"Took {count} × {name} from the locker."):reason switch
   {
    "locker_full"=>$"The locker is full ({Stash.SlotCapacity} stacks). Take something out first.",
    "not_carried"=>$"You do not carry that many {name}.",
    "not_stored"=>$"The locker does not hold that many {name}.",
    "stack_full"=>$"Your pack cannot hold more {name} (limit {spec?.maxStack}).",
    _=>reason!=null&&reason.Contains("capacity")?reason:"That cannot be moved."
   };
   Notify(message,"Home locker");SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   if(ok){if(store)SetFlag(WardHome.StoredFlag);HomeChanged?.Invoke();Changed?.Invoke();}
   return ok;
  }
  /// Bunk: rest until a time of day (hour &lt; 0 = just get up). Restores vitality and the weapon charge, saves the game,
  /// and from now on Continue starts at the bunk.
  public void Rest(float hour)
  {
   if(State!=CityState.Rest)return;
   var at=ActiveHome;var clock=FindAnyObjectByType<CityTimeOfDay>();
   if(hour>=0&&clock)clock.SetHour(hour);
   var combat=player?player.GetComponent<PlayerCombat>():null;
   if(combat){combat.Health.Restore();combat.Recharge(combat.Stats.nanoMax,0,0);}
   bool slept=hour>=0;
   SetFlag(WardHome.RestedFlag);
   Close();
   if(at&&at.wakePoint)WakeAt(at.wakePoint);
   Notify(slept?$"You sleep until {(hour<12?"morning":"evening")}. Rested; your progress is saved, and Continue starts here.":"You rest a while. Rested; your progress is saved, and Continue starts here.","Home");
   HomeChanged?.Invoke();
  }
  /// Puts the player on their feet at a point (the bunk's wake point), facing its forward.
  public void WakeAt(Transform point)
  {
   if(!point||!player)return;
   player.Teleport(point.position);if(player.visual)player.visual.rotation=Quaternion.Euler(0,point.eulerAngles.y,0);
   if(follow){follow.yaw=point.eulerAngles.y;follow.pitch=8;}
  }
  public void SelectDestination(int index)
  {
   if(State!=CityState.Grid||GridProgress<1||index<0||index>=catalog.destinations.Length)return;
   var node=catalog.destinations[index];selectedDestination=node.id;linked=true;Notify("Link established to "+node.name+".","Lattice Jack");SoundRequested?.Invoke(CitySoundCue.LatticeLink);
  }
  /// The ten-slot hotbar (5 Oct 2026). Assignments live in the HotbarModel and are saved with the game.
  public HotbarModel Quickbar=>quickbar??=new HotbarModel(id=>catalog&&catalog.Consumable(id)!=null&&Shop?.Spec(id)!=null);
  HotbarModel quickbar;
  /// Hotbar key 1–9 or 0 (slot 10): 1 draws or holsters the primary weapon, 2 the sidearm; 3–0 use the item assigned
  /// from the field pack.
  public void UseHotbar(int slot)
  {
   if(State!=CityState.Play)return;
   var weapon=HotbarModel.WeaponSlot(slot);
   if(weapon!=null){var combat=player?player.GetComponent<PlayerCombat>():null;if(combat)combat.ToggleDraw(weapon);return;}
   if(!HotbarModel.IsItemSlot(slot)||Quickbar==null)return;
   var id=Quickbar.Item(slot);
   if(id!=null){UseItem(id);return;}
   Notify($"Hotbar {HotbarModel.Key(slot)} is empty. In your field pack (Tab), drag a medkit or nano recharge onto the hotbar strip, or select one and press {HotbarModel.Key(slot)}.","Field Pack");
   SoundRequested?.Invoke(CitySoundCue.Unavailable);
  }
  /// Assigns a pack item to a hotbar slot (the field pack's strip); the refusal is a notice.
  public bool AssignHotbar(int slot,string itemId)
  {
   if(Quickbar==null)return false;
   var item=Shop?.Spec(itemId);
   bool ok=Quickbar.Assign(slot,itemId,out var reason);
   string name=item!=null?item.name:itemId;
   if(ok)Notify($"{name} on hotbar {HotbarModel.Key(slot)}.","Field Pack");
   else Notify(reason=="weapon_slot"?"Hotbar 1 and 2 hold your primary weapon and sidearm.":reason=="not_usable"?$"{name} cannot be used from the hotbar. Medkits and nano recharges can.":"That is not a hotbar slot.","Field Pack");
   SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);
   return ok;
  }
  public void StartGame(){if(State!=CityState.MainMenu)return;HasStarted=true;SetState(CityState.Play);}
  public CityVisitState CaptureCityVisit()=>new CityVisitState{visitedHill=visitedHill,boughtFlask=boughtFlask,soldScrap=soldScrap,linked=linked,spoken=Spoken.OrderBy(x=>x).ToArray(),selectedDestination=selectedDestination,flags=Flags.OrderBy(x=>x,StringComparer.Ordinal).ToArray()};
  /// Save restore of the city-visit checklist (conversations, flask, scrap sale, lattice link).
  public void RestoreCityVisit(CityVisitState city)
  {
   if(city==null)return;
   visitedHill=city.visitedHill;boughtFlask=city.boughtFlask;soldScrap=city.soldScrap;linked=city.linked;
   Spoken.Clear();if(city.spoken!=null)foreach(var id in city.spoken)if(!string.IsNullOrEmpty(id)&&npcs!=null&&npcs.Any(n=>n&&n.definition&&n.definition.id==id))Spoken.Add(id);
   selectedDestination=city.selectedDestination??"";
   Flags.Clear();if(city.flags!=null)foreach(var f in city.flags)if(!string.IsNullOrEmpty(f))Flags.Add(f);
   Changed?.Invoke();
  }
  /// Field rewards (Outer Berms patrols): credits and items change together, then the log records it.
  public void Reward(int credits,string itemId,int quantity,string speaker,string text)
  {
   if(!Shop.Grant(itemId,quantity,credits,out string message)){Notify(message);return;}
   // The Warden's words go on the radio; the banner states what was received.
   if(speaker=="System")Notify(text,speaker);else{Radio(text,speaker);Notify(message);}
   SoundRequested?.Invoke(CitySoundCue.Trade);
  }
#if UNITY_EDITOR || DEBUG
  public void DevChanged(string message){Notify(message,"Dev");}
  public bool DevResetCityVisit()
  {
   if(State!=CityState.Play&&State!=CityState.Paused)return false;
   visitedHill=boughtFlask=soldScrap=linked=false;
   Spoken.Clear();selectedDestination="";
   DevChanged("City visit and dialogue flags reset; inventory and tutorial unchanged.");return true;
  }
#endif
  /// J: the journal opens from play and closes back to it.
  public void ToggleJournal()
  {
   if(State==CityState.Play)Open(CityState.Journal);
   else if(State==CityState.Journal)Close();
  }
  public void ToggleInventory()
  {
   if(State==CityState.Play)Open(CityState.Inventory);
   else if(State==CityState.Inventory){DetailItemId=null;Close();}
  }
  public void OpenItemDetails(string id)
  {
   if(State!=CityState.Inventory||Shop==null||Shop.Quantity(id)<=0)return;
   DetailItemId=id;Changed?.Invoke();
  }
  public void CloseItemDetails(){if(DetailItemId==null)return;DetailItemId=null;Changed?.Invoke();}
  /// A workbench (CraftingStationMarker) was used: its fabricator window opens. Only a nearby station can open it.
  public void OpenFabricator(CraftingStationMarker station)
  {
   if(State!=CityState.Play||!station||string.IsNullOrEmpty(station.stationId))return;
   ActiveStation=station;ActiveStationId=station.stationId;SetState(CityState.Fabricator);
  }
  public void Open(CityState state)
  {
   if(state==CityState.Fabricator)return; // Only the nearby station can open this modal.
   if(State==CityState.MainMenu){if(state!=CityState.Settings)return;settingsReturn=CityState.MainMenu;Settings.BeginEdit();SetState(state);return;}
   if(State==CityState.Play||State==CityState.Paused){if(state==CityState.Settings){settingsReturn=CityState.Paused;Settings.BeginEdit();}SetState(state);}
  }
  public void Close(){if(State==CityState.Settings){if(Settings.Previewing){Settings.RevertVideo();return;}Settings.EndEdit();SetState(settingsReturn);return;}if(State==CityState.MainMenu||State==CityState.Boot)return;if(State==CityState.Inventory&&DetailItemId!=null){CloseItemDetails();return;}DetailItemId=null;ActiveStationId=null;ActiveStation=null;ActiveHome=null;if(ActiveNpc){ActiveNpc.StopSpeaking();ActiveNpc.talking=false;}ActiveNpc=null;GridProgress=0;SetState(CityState.Play);}
  public void ResetPlayer(){if(!HasStarted)return;Close();player.ReturnToGate();follow.yaw=-90;follow.pitch=17;follow.FixedView=false;}
  public void ToggleMute(){Settings.Sound.muted=!Settings.Sound.muted;Settings.SaveSound();Settings.Flush();}
  public void ToggleReducedMotion(){reducedMotion=!reducedMotion;Settings.SaveReducedMotion(reducedMotion);Changed?.Invoke();}
  void SpeakDialogue(){if(ActiveNpc)ActiveNpc.Speak(Dialogue,Settings,FindAnyObjectByType<CityAudio>()?.steps);}
  void SetState(CityState state){if(State==CityState.Dialogue&&state!=CityState.Dialogue&&ActiveNpc)ActiveNpc.StopSpeaking();State=state;input.SetGameplay(state==CityState.Play);player.Blocked=state!=CityState.Play;player.Talking=state==CityState.Dialogue;Time.timeScale=state==CityState.MainMenu||state==CityState.Paused||state==CityState.Settings?0:1;AudioListener.pause=state==CityState.Paused;Changed?.Invoke();}
  public void Notify(string text,string speaker="System"){notice=text;noticeTime=Mathf.Clamp(2.5f+noticeSecondsPerWord*RadioQueue.Words(text),4,10);AddLog(speaker,text);Changed?.Invoke();}
  /// A radio line (field briefings): logged now, shown on the radio channel when its turn comes. gapBefore leaves a
  /// short silence after the previous line; tag lets stale lines be dropped (RadioQueue.IsStale); urgent jumps the queue.
  public void Radio(string text,string speaker,float gapBefore=0,string tag=null,bool urgent=false){if(string.IsNullOrWhiteSpace(text))return;AddLog(speaker,text);RadioLine.Say(text,speaker,gapBefore,tag,urgent);Changed?.Invoke();}
  /// Event log only (no banner): pickups already have their own toast.
  public void Record(string text,string speaker="System"){if(!string.IsNullOrWhiteSpace(text))AddLog(speaker,text);}
  void AddLog(string speaker,string text){LogRevision++;Log.Add(speaker+": "+text);if(Log.Count>16)Log.RemoveAt(0);Changed?.Invoke();}
 }
}
