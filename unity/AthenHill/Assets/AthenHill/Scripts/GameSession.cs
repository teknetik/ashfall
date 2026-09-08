using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 public enum CityState { Boot,Play,Dialogue,Shop,Grid,Paused,Inventory,Notes,Credits,Error,Settings }
 public class GameSession:MonoBehaviour
 {
  public CityCatalog catalog;
  public GameSettings Settings {get;private set;}
  void Awake(){Settings=GetComponent<GameSettings>();if(!Settings)Settings=gameObject.AddComponent<GameSettings>();}
  void SettingsChanged(){muted=Settings.Sound.muted;Changed?.Invoke();}
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
  public ShopModel Shop {get;private set;}
  public NpcAgent ActiveNpc {get;private set;}
  public string dialogueNode="greeting",notice="",selectedDestination="";
  public float GridProgress {get;private set;}
  public readonly List<string> Log=new List<string>();
  public readonly HashSet<string> Spoken=new HashSet<string>();
  public bool visitedHill,boughtFlask,soldScrap,linked;
  public event Action Changed;
  public event Action<CitySoundCue> SoundRequested;
  public int LogRevision {get;private set;}
  bool ringInside;float noticeTime;
  public bool Complete=>visitedHill&&Spoken.Count==4&&boughtFlask&&soldScrap&&linked;
  public string Objective=>!visitedHill?"Reach the Hill Tree.":Spoken.Count<4?$"Meet the colonists · {Spoken.Count}/4 conversations":!boughtFlask||!soldScrap?"Buy a flask and sell your scrap at Basic General.":!linked?"Use the Lattice Jack in the north court.":"A place on the hill. City visit complete.";
  public DialogueNode Dialogue=>ActiveNpc?ActiveNpc.definition.nodes.First(x=>x.id==dialogueNode):null;
  void Start(){Settings.Changed+=SettingsChanged;muted=Settings.Sound.muted;Settings.ApplySound();Shop=new ShopModel(catalog.items,catalog.startingCredits);Log.Add("Linn: Meet me on the hill.");SetState(CityState.Play);}
  void OnDestroy(){if(Settings)Settings.Changed-=SettingsChanged;Time.timeScale=1;AudioListener.pause=false;AudioListener.volume=1;}
  void OnApplicationFocus(bool focused){if(!focused&&State==CityState.Play)SetState(CityState.Paused);}
  void Update()
  {
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
  }
  public NpcAgent Nearest=>npcs.Where(n=>n&&Vector3.Distance(n.transform.position,player.transform.position)<=interactionRange).OrderBy(n=>Vector3.Distance(n.transform.position,player.transform.position)).FirstOrDefault();
  bool NearLattice=>latticePoint&&Vector3.Distance(player.transform.position,latticePoint.position)<latticeRange;
  bool NearRing=>ringPoint&&Mathf.Abs(player.transform.position.x-ringPoint.position.x)<ringHalfSize.x&&Mathf.Abs(player.transform.position.z-ringPoint.position.z)<ringHalfSize.y;
  public string Prompt=>State!=CityState.Play?"":Nearest?$"E · Talk to {Nearest.definition.displayName}":NearLattice?"E · Use Lattice Jack":NearRing?"E · Check Ring Gate":"";
  public void Interact()
  {
   if(State!=CityState.Play)return;
   var n=Nearest;
   if(n){ActiveNpc=n;dialogueNode="greeting";n.talking=true;Spoken.Add(n.definition.id);SetState(CityState.Dialogue);AddLog(n.definition.displayName,Dialogue.text);}
   else if(NearLattice){GridProgress=0;selectedDestination="";SetState(CityState.Grid);AddLog("Lattice Jack","Signal acquired. Opening the sector lattice.");SoundRequested?.Invoke(CitySoundCue.LatticeOpen);}
   else {Notify(NearRing?"Destination offline. The far ring has gone quiet.":"Move closer to a colonist or terminal.",NearRing?"Ring Gate":"System");SoundRequested?.Invoke(CitySoundCue.Unavailable);}
  }
  public void Choose(int index)
  {
   if(State!=CityState.Dialogue||index<0||index>=Dialogue.choices.Length)return;
   var choice=Dialogue.choices[index];AddLog("You",choice.label);
   if(choice.action=="shop")SetState(CityState.Shop);
   else if(choice.action=="close")Close();
   else {dialogueNode=choice.next;AddLog(ActiveNpc.definition.displayName,Dialogue.text);Changed?.Invoke();}
  }
  public bool Trade(string id,bool buy)
  {
   if(State!=CityState.Shop)return false;
   bool ok=Shop.Trade(id,buy,out string message);
   if(ok&&buy&&id=="water_flask")boughtFlask=true;
   if(ok&&!buy&&id=="scrap_coil")soldScrap=true;
   Notify(message,"Mira");SoundRequested?.Invoke(ok?CitySoundCue.Trade:CitySoundCue.Unavailable);return ok;
  }
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
  public void Open(CityState state){if(State==CityState.Play||State==CityState.Paused){if(state==CityState.Settings)Settings.BeginEdit();SetState(state);}}
  public void Close(){if(State==CityState.Settings){if(Settings.Previewing){Settings.RevertVideo();return;}Settings.EndEdit();SetState(CityState.Paused);return;}if(ActiveNpc)ActiveNpc.talking=false;ActiveNpc=null;GridProgress=0;SetState(CityState.Play);}
  public void ResetPlayer(){Close();player.ReturnToGate();follow.yaw=-90;follow.pitch=17;follow.FixedView=false;}
  public void ToggleMute(){Settings.Sound.muted=!Settings.Sound.muted;Settings.SaveSound();Settings.Flush();}
  public void ToggleReducedMotion(){reducedMotion=!reducedMotion;Changed?.Invoke();}
  void SetState(CityState state){State=state;input.SetGameplay(state==CityState.Play);player.Blocked=state!=CityState.Play;player.Talking=state==CityState.Dialogue;Time.timeScale=state==CityState.Paused||state==CityState.Settings?0:1;AudioListener.pause=state==CityState.Paused;Changed?.Invoke();}
  public void Notify(string text,string speaker="System"){notice=text;noticeTime=4;AddLog(speaker,text);Changed?.Invoke();}
  void AddLog(string speaker,string text){LogRevision++;Log.Add(speaker+": "+text);if(Log.Count>16)Log.RemoveAt(0);Changed?.Invoke();}
 }
}
