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
  VisualElement root,hud,vitalBar,nanoBar,crosshair,hitMarker,flash,objectiveRow,aimHint;
  Label vitalValue,nanoValue,objective,guidance;
  Button slot7;
  readonly Dictionary<FeralDroid,VisualElement> bars=new Dictionary<FeralDroid,VisualElement>();
  float hitUntil,flashAlpha;
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
  void OnDestroy(){if(combat)combat.StatsChanged-=UpdatePistolTooltip;}
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
