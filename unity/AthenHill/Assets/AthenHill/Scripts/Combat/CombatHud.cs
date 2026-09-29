using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Combat layer on the city HUD document: live vitality/nano meters, the pistol hotbar slot (7),
 /// crosshair and hit marker, hurt edge flash, droid health bars and the Outer Berms field-notes line.
 /// Styles live in CityHUD.uss under "Outer Berms combat".
 [RequireComponent(typeof(UIDocument))]
 public class CombatHud:MonoBehaviour
 {
  public GameSession session;
  public PlayerCombat combat;
  public BermsTutorial tutorial;
  CraftingSession crafting;
  public Camera worldCamera;
  [Min(1)]public float enemyBarDistance=32;
  [Tooltip("Seconds a salvage pickup toast stays on screen.")]
  [Min(.5f)]public float toastSeconds=4.5f;
  VisualElement root,hud,vitalBar,nanoBar,crosshair,hitMarker,flash,objectiveRow,aimHint;
  Label vitalValue,nanoValue,objective,guidance;
  Button slot7;
  readonly Dictionary<FeralDroid,VisualElement> bars=new Dictionary<FeralDroid,VisualElement>();
  float hitUntil,flashAlpha,toastUntil;
  VisualElement toast,toastLines,search,searchFill;
  Label searchLabel;
  void Start()
  {
   root=GetComponent<UIDocument>().rootVisualElement;hud=root.Q("hud");
   crafting=session?session.GetComponent<CraftingSession>():null;
   vitalBar=root.Q(className:"vital-bar");nanoBar=root.Q(className:"nano-bar");
   var values=root.Query<Label>(className:"vital-value").ToList();
   if(values.Count>1){vitalValue=values[0];nanoValue=values[1];}
   foreach(var bar in new[]{vitalBar,nanoBar})if(bar!=null)bar.style.flexGrow=0;
   crosshair=Element("crosshair",hud);
   foreach(var part in new[]{"up","down","left","right"})Element("crosshair-tick "+part,crosshair);
   Element("crosshair-dot",crosshair);
   hitMarker=Element("hit-marker",hud);
   foreach(var part in new[]{"a","b"})Element("hit-marker-stroke "+part,hitMarker);
   flash=Element("damage-flash",root);flash.SendToBack();
   var objectiveBox=root.Q("objective-box");
   objectiveRow=Element("berms-objective",objectiveBox);
   objectiveRow.Add(new Label("OUTER BERMS"){pickingMode=PickingMode.Ignore});objectiveRow[0].AddToClassList("small");objectiveRow[0].AddToClassList("berms-heading");
   objective=new Label{pickingMode=PickingMode.Ignore};objective.AddToClassList("berms-objective-text");objectiveRow.Add(objective);
   var hints=root.Q("key-hints");
   if(hints!=null)
   {
    aimHint=Element("hint panel aim-hint",hints);aimHint.SendToBack();
    aimHint.Add(new Label("RMB"){pickingMode=PickingMode.Ignore});aimHint[0].AddToClassList("hint-key");
    aimHint.Add(new Label("Aim · LMB/F Fire"){pickingMode=PickingMode.Ignore});
   }
   guidance=new Label{pickingMode=PickingMode.Ignore};guidance.AddToClassList("checkpoint-guidance");hud.Add(guidance);
   // Salvage pickup toast (rarity-coloured lines) and the scrap-heap search progress.
   toast=Element("panel loot-toast",hud);
   var toastHeading=new Label("SALVAGE"){pickingMode=PickingMode.Ignore};toastHeading.AddToClassList("small");toastHeading.AddToClassList("loot-toast-heading");toast.Add(toastHeading);
   toastLines=Element("loot-toast-lines",toast);Show(toast,false);
   var actions=root.Q("top-actions");
   if(actions!=null)actions.RegisterCallback<GeometryChangedEvent>(e=>toast.style.top=e.newRect.yMax+8);
   search=Element("panel search-progress",hud);
   searchLabel=new Label{pickingMode=PickingMode.Ignore};searchLabel.AddToClassList("search-progress-label");search.Add(searchLabel);
   searchFill=Element("search-progress-fill",Element("search-progress-track",search));Show(search,false);
   if(crafting)crafting.Collected+=ShowPickup;
   slot7=root.Q<Button>("slot7");
   if(slot7!=null)slot7.clicked+=()=>combat.ToggleDraw();
   combat.TargetHit+=(_,killed)=>{hitUntil=Time.unscaledTime+(killed?.28f:.14f);hitMarker.EnableInClassList("kill",killed);};
   combat.Hurt+=amount=>flashAlpha=Mathf.Clamp01(flashAlpha+amount/30f);
   combat.StatsChanged+=UpdatePistolTooltip;UpdatePistolTooltip();
   Refresh(true);
  }
  static VisualElement Element(string classes,VisualElement parent)
  {
   var e=new VisualElement{pickingMode=PickingMode.Ignore};
   foreach(var c in classes.Split(' '))e.AddToClassList(c);
   parent?.Add(e);return e;
  }
  bool pistolShown;
  void Refresh(bool force)
  {
   if(slot7!=null&&(force||pistolShown!=combat.hasPistol))
   {
    pistolShown=combat.hasPistol;
    slot7.SetEnabled(pistolShown);slot7.EnableInClassList("empty-slot",!pistolShown);
    var marker=slot7.Q(className:"empty-slot-marker");
    if(pistolShown&&marker!=null)
    {
     marker.RemoveFromHierarchy();
     slot7.Add(Element("item-art pistol-icon",null));
     var label=new Label("Pistol"){pickingMode=PickingMode.Ignore};label.AddToClassList("slot-label");slot7.Add(label);
     slot7.tooltip="Draw or holster the scrap pistol · 7";
    }
   }
  }
  void LateUpdate()
  {
   if(root==null||root.panel==null)return;
   Refresh(false);
   // CityHud disables the reserve slots at start; keep slot 7 in step with the pistol.
   if(slot7!=null&&slot7.enabledSelf!=pistolShown)slot7.SetEnabled(pistolShown);
   if(slot7!=null&&pistolShown&&slot7.tooltip!=pistolTooltip)slot7.tooltip=pistolTooltip;
   var h=combat.Health;
   if(vitalBar!=null)vitalBar.style.width=Length.Percent(h.Fraction*100);
   if(vitalValue!=null)vitalValue.text=$"{Mathf.CeilToInt(h.Current)} / {Mathf.RoundToInt(h.max)}";
   if(nanoBar!=null)nanoBar.style.width=Length.Percent(combat.Nano/Mathf.Max(1,combat.Stats.nanoMax)*100);
   if(nanoValue!=null)nanoValue.text=$"{Mathf.FloorToInt(combat.Nano)} / {Mathf.RoundToInt(combat.Stats.nanoMax)}";
   bool play=session.State==CityState.Play;
   Show(crosshair,play&&combat.Armed);crosshair.EnableInClassList("aiming",combat.Aiming);
   Show(hitMarker,play&&Time.unscaledTime<hitUntil);
   if(aimHint!=null)Show(aimHint,play&&combat.Armed);
   slot7?.EnableInClassList("selected",combat.Armed);
   flashAlpha=Mathf.MoveTowards(flashAlpha,0,Time.unscaledDeltaTime*(session.reducedMotion?3:1.6f));
   flash.style.opacity=flashAlpha*(session.reducedMotion?.5f:.85f);
   if(toast!=null&&toast.style.display==DisplayStyle.Flex&&Time.unscaledTime>toastUntil)Show(toast,false);
   var heap=SalvageNode.Searching;
   Show(search,play&&heap);
   if(play&&heap){searchLabel.text=$"Searching {heap.displayName.ToLowerInvariant()}…";searchFill.style.width=Length.Percent(heap.Progress*100);}
   bool showObjective=tutorial&&tutorial.ShowObjective;
   Show(objectiveRow,showObjective);
   if(showObjective)objective.text=tutorial.Step==BermsStep.Complete&&crafting!=null&&!string.IsNullOrEmpty(crafting.Objective)?crafting.Objective:tutorial.Objective;
   UpdateGuidance(play);
   UpdateBars(play);
  }
  string pistolTooltip="";
  /// Rebuilt only when the loadout changes, never per frame.
  void UpdatePistolTooltip()
  {
   var model=crafting?crafting.Model:null;
   var mods=model!=null?string.Join(", ",model.Loadout.FittedMods.Select(x=>CraftingText.ItemName(model,x.Value))):"";
   pistolTooltip=$"Draw or holster the scrap pistol · 7 · Damage {combat.Stats.damage:0.#} · Recoil {combat.Stats.recoil:0.#}"+(mods.Length>0?" · "+mods:"");
  }
  void OnDestroy(){if(combat)combat.StatsChanged-=UpdatePistolTooltip;if(crafting)crafting.Collected-=ShowPickup;}
  static string RarityClass(ItemRarity r)=>r==ItemRarity.Rare?"rarity-rare":r==ItemRarity.Uncommon?"rarity-uncommon":"rarity-common";
  void ToastLine(string text,params string[] classes)
  {
   var line=new Label(text){pickingMode=PickingMode.Ignore};line.AddToClassList("loot-toast-line");
   foreach(var c in classes)line.AddToClassList(c);
   toastLines.Add(line);
  }
  /// One readable card per pickup: each item in its rarity colour, then anything left behind and new schematics.
  void ShowPickup(LootPickup pickup)
  {
   if(toast==null||crafting.Model==null)return;
   toastLines.Clear();
   foreach(var s in pickup.taken){var spec=crafting.Model.Item(s.itemId);ToastLine($"+{s.quantity}  {(spec!=null?spec.name:s.itemId)}",RarityClass(spec!=null?spec.rarity:ItemRarity.Common));}
   if(pickup.taken.Count==0&&pickup.left.Count==0)ToastLine($"Nothing useful in the {(pickup.source??"heap").ToLowerInvariant()}.","loot-toast-muted");
   if(pickup.left.Count>0)ToastLine("Pack full · left in the cache: "+string.Join(", ",pickup.left.Select(x=>$"{CraftingText.ItemName(crafting.Model,x.itemId)} ×{x.quantity}")),"loot-toast-warning");
   foreach(var r in pickup.discovered)ToastLine("Schematic discovered · "+r.name,"loot-toast-schematic");
   toastUntil=Time.unscaledTime+toastSeconds;Show(toast,true);
  }
  void UpdateGuidance(bool play)
  {
   var target=tutorial?tutorial.GuidanceTarget:null;
   bool fabTarget=tutorial&&tutorial.Step==BermsStep.Complete&&crafting!=null&&crafting.TutorialStep=="Fabricate";
   if(fabTarget)target=crafting.fabricator;
   bool visible=play&&target&&tutorial.ShowObjective;
   if(visible)
   {
    var world=target.position+Vector3.up*1.8f;var vp=worldCamera.WorldToViewportPoint(world);
    visible=vp.z>0&&vp.x>.05f&&vp.x<.95f&&vp.y>.08f&&vp.y<.92f&&Vector3.Distance(world,combat.transform.position)<35;
    if(visible)
    {
     guidance.text=(fabTarget?"FIELD FABRICATOR":tutorial.Step==BermsStep.TakePistol?"ARMS LOCKER":"WARDEN OSSA")+$" · {Mathf.CeilToInt(Vector3.Distance(target.position,combat.transform.position))} m";
     var p=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);guidance.style.left=p.x-85;guidance.style.top=p.y-24;
    }
   }
   Show(guidance,visible);
  }
  void UpdateBars(bool play)
  {
   foreach(var d in FeralDroid.Active)if(d&&!bars.ContainsKey(d))
   {
    var bar=Element("enemy-bar",hud);Element("enemy-bar-fill",bar);
    var name=new Label(d.displayName){pickingMode=PickingMode.Ignore};name.AddToClassList("enemy-bar-name");bar.Add(name);
    bars[d]=bar;
   }
   List<FeralDroid> gone=null;
   foreach(var pair in bars)
   {
    var d=pair.Key;var bar=pair.Value;
    if(!d||!d.isActiveAndEnabled){(gone??=new List<FeralDroid>()).Add(d);continue;}
    var world=d.Health.AimPoint+Vector3.up*.9f;var vp=worldCamera.WorldToViewportPoint(world);
    bool engaged=d.Health.Alive&&(d.Health.Current<d.Health.max||d.State!=DroidState.Idle&&d.State!=DroidState.Returning);
    bool visible=play&&engaged&&vp.z>0&&vp.x>0&&vp.x<1&&vp.y>0&&vp.y<1&&Vector3.Distance(world,combat.transform.position)<enemyBarDistance;
    Show(bar,visible);
    if(!visible)continue;
    var p=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);
    bar.style.left=p.x-50;bar.style.top=p.y-14;
    bar[0].style.width=Length.Percent(d.Health.Fraction*100);
   }
   if(gone!=null)foreach(var d in gone){bars[d].RemoveFromHierarchy();bars.Remove(d);}
  }
  static void Show(VisualElement e,bool show){if(e!=null)e.style.display=show?DisplayStyle.Flex:DisplayStyle.None;}
 }
}
