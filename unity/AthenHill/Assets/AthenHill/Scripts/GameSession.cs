using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// One Buy parts purchase; listeners may append words to the notice (e.g. " Schematic discovered: …").
 public sealed class PartPurchase{public string itemId,note="";}
 public enum CityState { Boot,Play,Dialogue,Shop,Grid,Paused,Inventory,Notes,Credits,Error,Settings,MainMenu,Fabricator }
 public class GameSession:MonoBehaviour,IQuestState
 {
  public CityCatalog catalog;
  [Tooltip("Character progression rules. When unassigned, loads Resources/CharacterCatalog.")]
  public CharacterCatalog characterCatalog;
  public CharacterModel Character {get;private set;}
  public GameSettings Settings {get;private set;}
  void Awake(){Settings=GetComponent<GameSettings>();if(!Settings)Settings=gameObject.AddComponent<GameSettings>();reducedMotion=Settings.ReadReducedMotion(reducedMotion);RadioLine.timing=radioTiming??new RadioQueue.Timing();}
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
   if(UnityEngine.InputSystem.Keyboard.current?.tabKey.wasPressedThisFrame==true)ToggleInventory();
   if(input.Cancel){if(State==CityState.Play)SetState(CityState.Paused);else Close();}
   if(State==CityState.Play)
   {
    if(input.Pressed("Reset"))ResetPlayer();
    if(input.Pressed("Interact"))Interact();
    for(int i=1;i<=6;i++)if(input.Pressed("Slot"+i))Hotbar(i);
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
   bool ok=Shop.Trade(id,buy,out string message,Vendor);
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
  /// A trade or salvage sale completed (autosave hook).
  public event Action Traded;
  /// A crafting part was bought (the crafting session reveals schematics that use it, as for a pickup, and appends
  /// them to the purchase notice).
  public event Action<PartPurchase> PartBought;
  public void SelectDestination(int index)
  {
   if(State!=CityState.Grid||GridProgress<1||index<0||index>=catalog.destinations.Length)return;
   var node=catalog.destinations[index];selectedDestination=node.id;linked=true;Notify("Link established to "+node.name+".","Lattice Jack");SoundRequested?.Invoke(CitySoundCue.LatticeLink);
  }
  public void Hotbar(int slot)
  {
   if(State!=CityState.Play)return;
   if(slot<3){string id=slot==1?"water_flask":"medkit";var i=catalog.items.First(x=>x.id==id);Notify($"{i.name} · {Shop.Quantity(id)} carried. {i.description}");}
   else if(slot==3){if(NearLattice)Interact();else Notify("The Lattice Jack is in the north court, beyond the hill.");}
   else if(slot==4){if(Nearest)Interact();else Notify("Move close to a colonist to talk.");}
   else Open(slot==5?CityState.Inventory:CityState.Notes);
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
  public void Close(){if(State==CityState.Settings){if(Settings.Previewing){Settings.RevertVideo();return;}Settings.EndEdit();SetState(settingsReturn);return;}if(State==CityState.MainMenu||State==CityState.Boot)return;if(State==CityState.Inventory&&DetailItemId!=null){CloseItemDetails();return;}DetailItemId=null;ActiveStationId=null;ActiveStation=null;if(ActiveNpc){ActiveNpc.StopSpeaking();ActiveNpc.talking=false;}ActiveNpc=null;GridProgress=0;SetState(CityState.Play);}
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
