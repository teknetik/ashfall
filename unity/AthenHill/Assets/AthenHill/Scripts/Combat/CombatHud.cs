using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 /// Combat layer on the city HUD document: live vitality/nano meters (the weapon hotbar slots 1–2 are HotbarView's),
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
  [Tooltip("Guidance markers show while their target is on screen and within this many metres.")]
  [Min(5)]public float guidanceRange=60;
  VisualElement root,hud,vitalBar,nanoBar,crosshair,hitMarker,flash,aimHint;
  Label vitalValue,nanoValue,guidance;
  readonly Dictionary<FeralDroid,VisualElement> bars=new Dictionary<FeralDroid,VisualElement>();
  float hitUntil,flashAlpha,toastUntil;
  /// Damage direction indicators (ranged droids): pooled, each tracks its attacker's position and fades.
  class DamageDir{public VisualElement el;public Vector3 from;public float alpha;}
  readonly List<DamageDir> damageDirs=new List<DamageDir>();
  /// Compass markers for the Outer Berms sites, the waystation and the gate (BermsCompassPoint).
  readonly Dictionary<BermsCompassPoint,VisualElement> pois=new Dictionary<BermsCompassPoint,VisualElement>();
  VisualElement compassTrack;Label poiLabel;
  VisualElement toast,toastLines,search,searchFill;
  Label searchLabel,toastHeading;
  /// Threat tier per droid bar (DroidThreat): re-evaluated every TierRefreshSeconds and when the weapon stats change.
  readonly Dictionary<FeralDroid,ThreatTier> tiers=new Dictionary<FeralDroid,ThreatTier>();
  const float TierRefreshSeconds=.75f;
  float nextTierCheck;
  string lastKilledName;
  // Bar tints: Easy grey, Normal green, Danger red (fill, fill top edge, name label).
  static readonly Color EasyFill=new Color(.56f,.56f,.53f),EasyEdge=new Color(.72f,.72f,.68f),EasyName=new Color(.76f,.75f,.71f);
  static readonly Color NormalFill=new Color(.36f,.72f,.42f),NormalEdge=new Color(.55f,.86f,.58f),NormalName=new Color(.82f,.93f,.82f);
  static readonly Color DangerFill=new Color(.86f,.25f,.2f),DangerEdge=new Color(.98f,.5f,.42f),DangerName=new Color(.98f,.72f,.66f);
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
   var hints=root.Q("key-hints");
   if(hints!=null)
   {
    aimHint=Element("hint panel aim-hint",hints);aimHint.SendToBack();
    aimHint.Add(new Label("RMB"){pickingMode=PickingMode.Ignore});aimHint[0].AddToClassList("hint-key");
    aimHint.Add(new Label("Aim · LMB Fire"){pickingMode=PickingMode.Ignore});
   }
   guidance=new Label{pickingMode=PickingMode.Ignore};guidance.AddToClassList("checkpoint-guidance");hud.Add(guidance);
   // Salvage pickup toast (rarity-coloured lines) and the scrap-heap search progress.
   toast=Element("panel loot-toast",hud);
   toastHeading=new Label("SALVAGE"){pickingMode=PickingMode.Ignore};toastHeading.AddToClassList("small");toastHeading.AddToClassList("loot-toast-heading");toast.Add(toastHeading);
   toastLines=Element("loot-toast-lines",toast);Show(toast,false);
   var actions=root.Q("top-actions");
   if(actions!=null)actions.RegisterCallback<GeometryChangedEvent>(e=>toast.style.top=e.newRect.yMax+8);
   search=Element("panel search-progress",hud);
   searchLabel=new Label{pickingMode=PickingMode.Ignore};searchLabel.AddToClassList("search-progress-label");search.Add(searchLabel);
   searchFill=Element("search-progress-fill",Element("search-progress-track",search));Show(search,false);
   if(crafting)crafting.Collected+=ShowPickup;
   combat.TargetHit+=(target,killed)=>{hitUntil=Time.unscaledTime+(killed?.28f:.14f);hitMarker.EnableInClassList("kill",killed);if(killed&&target){var d=target.GetComponent<FeralDroid>();lastKilledName=d?d.displayName:null;}};
   combat.ExperienceAwarded+=ShowExperience;
   combat.Hurt+=amount=>flashAlpha=Mathf.Clamp01(flashAlpha+amount/30f);
   for(int i=0;i<4;i++){var pivot=Element("damage-dir",hud);Element("damage-dir-arc",pivot);damageDirs.Add(new DamageDir{el=pivot});}
   combat.HurtFrom+=ShowDamageDirection;
   compassTrack=root.Q("compass-track");
   var compass=root.Q("compass");
   if(compass!=null){poiLabel=new Label{name="compass-poi-label",pickingMode=PickingMode.Ignore};poiLabel.AddToClassList("compass-poi-label");compass.Add(poiLabel);Show(poiLabel,false);}
   // The tracked mission's marker (5 Oct 2026): everywhere, pinned to the compass edge with a chevron when off it.
   if(compassTrack!=null){trackedMarker=Element("compass-tracked diamond",compassTrack);trackedMarker.name="compass-tracked";trackedMarker.usageHints=UsageHints.DynamicTransform;Show(trackedMarker,false);}
   combat.StatsChanged+=()=>nextTierCheck=0;
  }
  static VisualElement Element(string classes,VisualElement parent)
  {
   var e=new VisualElement{pickingMode=PickingMode.Ignore};
   foreach(var c in classes.Split(' '))e.AddToClassList(c);
   parent?.Add(e);return e;
  }
  void LateUpdate()
  {
   if(root==null||root.panel==null)return;
   var h=combat.Health;
   if(vitalBar!=null)vitalBar.style.width=Length.Percent(h.Fraction*100);
   if(vitalValue!=null)vitalValue.text=$"{Mathf.CeilToInt(h.Current)} / {Mathf.RoundToInt(h.max)}";
   if(nanoBar!=null)nanoBar.style.width=Length.Percent(combat.Nano/Mathf.Max(1,combat.Stats.nanoMax)*100);
   if(nanoBar!=null)nanoBar.EnableInClassList("overclocked",combat.Overclocked);
   if(nanoValue!=null)nanoValue.text=$"{Mathf.FloorToInt(combat.Nano)} / {Mathf.RoundToInt(combat.Stats.nanoMax)}";
   bool play=session.State==CityState.Play;
   Show(crosshair,play&&combat.Armed);crosshair.EnableInClassList("aiming",combat.Aiming);
   Show(hitMarker,play&&Time.unscaledTime<hitUntil);
   if(aimHint!=null)Show(aimHint,play&&combat.Armed);
   flashAlpha=Mathf.MoveTowards(flashAlpha,0,Time.unscaledDeltaTime*(session.reducedMotion?3:1.6f));
   flash.style.opacity=flashAlpha*(session.reducedMotion?.5f:.85f);
   if(toast!=null&&toast.style.display==DisplayStyle.Flex&&Time.unscaledTime>toastUntil)Show(toast,false);
   var heap=SalvageNode.Searching;
   Show(search,play&&heap);
   if(play&&heap){searchLabel.text=string.IsNullOrEmpty(heap.progressLabel)?$"Searching the {heap.displayName.ToLowerInvariant()}…":heap.progressLabel;searchFill.style.width=Length.Percent(heap.Progress*100);}
   UpdateGuidance(play);
   UpdateBars(play);
   UpdateDamageDirections();
   UpdateCompassPoints(play);
  }
  void UpdateCompassPoints(bool play)
  {
   if(compassTrack==null||!worldCamera)return;
   bool berms=play&&combat.InBerms;
   float width=compassTrack.resolvedStyle.width;
   float heading=worldCamera.transform.eulerAngles.y;
   BermsCompassPoint centred=null;float best=7;
   foreach(var p in BermsCompassPoint.All)
   {
    if(!p)continue;
    if(!pois.TryGetValue(p,out var marker))
    {
     marker=new VisualElement{pickingMode=PickingMode.Ignore,usageHints=UsageHints.DynamicTransform};
     marker.AddToClassList("compass-poi");marker.AddToClassList(p.kind.ToString().ToLowerInvariant());
     compassTrack.Add(marker);pois[p]=marker;
    }
    var to=p.transform.position-combat.transform.position;to.y=0;float dist=to.magnitude;
    float delta=Mathf.DeltaAngle(heading,Mathf.Atan2(to.x,to.z)*Mathf.Rad2Deg);
    bool visible=berms&&!float.IsNaN(width)&&p.Shown&&dist<p.maxDistance&&dist>6&&Mathf.Abs(delta)<92;
    Show(marker,visible);
    if(!visible)continue;
    marker.EnableInClassList("cleared",p.Cleared);
    marker.style.translate=new Translate(new Length(width*.5f+delta*(width/190f)-5),new Length(0),0);
    if(Mathf.Abs(delta)<best){best=Mathf.Abs(delta);centred=p;}
   }
   // tracked mission marker
   var tracked=session&&session.Journal?session.Journal.Tracked:null;
   var target=play&&tracked!=null?tracked.target:null;
   bool trackedCentred=false;string trackedText=null;
   if(trackedMarker!=null)
   {
    bool show=target&&!float.IsNaN(width);
    Show(trackedMarker,show);
    if(show)
    {
     var to=target.position-combat.transform.position;to.y=0;float dist=to.magnitude;
     float delta=dist<.5f?0:Mathf.DeltaAngle(heading,Mathf.Atan2(to.x,to.z)*Mathf.Rad2Deg);
     // the compass shows ±95°; beyond that the marker waits at the edge, pointing the way to turn
     const float edge=88;bool off=Mathf.Abs(delta)>edge;
     float shown=Mathf.Clamp(delta,-edge,edge);
     trackedMarker.style.translate=new Translate(new Length(width*.5f+shown*(width/190f)-7),new Length(0),0);
     trackedMarker.EnableInClassList("edge-left",off&&delta<0);trackedMarker.EnableInClassList("edge-right",off&&delta>0);
     trackedCentred=Mathf.Abs(delta)<10||dist<6;
     trackedText=$"{(string.IsNullOrEmpty(tracked.targetLabel)?tracked.title.ToUpperInvariant():tracked.targetLabel)} · {Mathf.RoundToInt(dist)} m";
    }
   }
   if(poiLabel==null)return;
   Show(poiLabel,trackedCentred||centred);
   poiLabel.EnableInClassList("tracked",trackedCentred);
   if(trackedCentred)poiLabel.text=trackedText;
   else if(centred)poiLabel.text=$"{centred.displayName.ToUpperInvariant()} · {Mathf.RoundToInt(Vector3.Distance(centred.transform.position,combat.transform.position))} m"+(centred.Cleared?" · cleared":"");
  }
  VisualElement trackedMarker;
  void ShowDamageDirection(float amount,Vector3 from)
  {
   if(damageDirs.Count==0||(from-combat.transform.position).sqrMagnitude<1)return;
   // the same attacker refreshes its indicator; otherwise take the faintest
   DamageDir pick=null;
   foreach(var d in damageDirs)if(d.alpha>0&&(d.from-from).sqrMagnitude<4){pick=d;break;}
   if(pick==null){pick=damageDirs[0];foreach(var d in damageDirs)if(d.alpha<pick.alpha)pick=d;}
   pick.from=from;pick.alpha=Mathf.Clamp01(Mathf.Max(pick.alpha,.55f+amount/40f));
  }
  void UpdateDamageDirections()
  {
   if(!worldCamera)return;
   var fwd=worldCamera.transform.forward;fwd.y=0;
   foreach(var d in damageDirs)
   {
    if(d.alpha<=0){if(d.el.style.opacity.value!=0)d.el.style.opacity=0;continue;}
    d.alpha=Mathf.MoveTowards(d.alpha,0,Time.unscaledDeltaTime*.6f);
    var to=d.from-combat.transform.position;to.y=0;
    float angle=fwd.sqrMagnitude>1e-4f&&to.sqrMagnitude>1e-4f?Vector3.SignedAngle(fwd,to,Vector3.up):0;
    d.el.style.rotate=new Rotate(angle);d.el.style.opacity=d.alpha;
   }
  }
  void OnDestroy(){if(combat){combat.HurtFrom-=ShowDamageDirection;combat.ExperienceAwarded-=ShowExperience;}if(crafting)crafting.Collected-=ShowPickup;}
  /// Experience toast on a kill ("+12 XP"), with the level-up line and a Ward notice when the character levels.
  void ShowExperience(int amount,ThreatTier tier,bool levelled)
  {
   if(toast==null)return;
   toastLines.Clear();toastHeading.text="EXPERIENCE";
   string who=string.IsNullOrEmpty(lastKilledName)?"":" · "+lastKilledName;
   if(amount>0)ToastLine($"+{amount} XP{who}",tier==ThreatTier.Danger?"rarity-rare":"rarity-uncommon");
   else ToastLine($"Easy target · no XP{who}","loot-toast-muted");
   var character=combat.Character;
   if(levelled&&character!=null)
   {
    ToastLine($"Level {character.Level} · {character.Data.attributePointsPerLevel} attribute, {character.Data.skillPointsPerLevel} skill points","loot-toast-schematic");
    session.Notify($"Level {character.Level} reached. Spend your new points in the character sheet.","Ward");
   }
   else if(character!=null)ToastLine($"Level {character.Level} · {character.Experience} / {character.Data.experiencePerLevel} XP","loot-toast-muted");
   toastUntil=Time.unscaledTime+toastSeconds;Show(toast,true);
  }
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
   toastLines.Clear();toastHeading.text="SALVAGE";
   foreach(var s in pickup.taken){var spec=crafting.Model.Item(s.itemId);ToastLine($"+{s.quantity}  {(spec!=null?spec.name:s.itemId)}",RarityClass(spec!=null?spec.rarity:ItemRarity.Common));}
   if(pickup.taken.Count==0&&pickup.left.Count==0)ToastLine($"Nothing useful in the {(pickup.source??"heap").ToLowerInvariant()}.","loot-toast-muted");
   if(pickup.left.Count>0)ToastLine("Pack full · left in the cache: "+string.Join(", ",pickup.left.Select(x=>$"{CraftingText.ItemName(crafting.Model,x.itemId)} ×{x.quantity}")),"loot-toast-warning");
   foreach(var r in pickup.discovered)ToastLine("Schematic discovered · "+r.name,"loot-toast-schematic");
   toastUntil=Time.unscaledTime+toastSeconds;Show(toast,true);
  }
  /// The in-world label over the tracked mission's target (5 Oct 2026: follows the journal's tracked mission).
  void UpdateGuidance(bool play)
  {
   var tracked=session&&session.Journal?session.Journal.Tracked:null;
   var target=tracked?.target;string label=tracked?.targetLabel??tracked?.title?.ToUpperInvariant();
   bool visible=play&&target;
   // A tracked droid (the Depot Foreman) carries its own name and health bar once engaged; the marker steps aside.
   var droid=tracked?.droid;
   if(visible&&droid&&bars.TryGetValue(droid,out var droidBar)&&droidBar.style.display==DisplayStyle.Flex)visible=false;
   if(visible)
   {
    var world=droid&&droid.transform==target?droid.BarAnchor+Vector3.up*.45f:target.position+Vector3.up*1.8f;var vp=worldCamera.WorldToViewportPoint(world);
    visible=vp.z>0&&vp.x>.05f&&vp.x<.95f&&vp.y>.08f&&vp.y<.92f&&Vector3.Distance(world,combat.transform.position)<guidanceRange;
    if(visible)
    {
     guidance.text=label+$" · {Mathf.CeilToInt(Vector3.Distance(target.position,combat.transform.position))} m";
     var p=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);
     guidance.style.left=p.x-85;guidance.style.top=AvoidNametags(new Rect(p.x-85,p.y-24,170,24));
    }
   }
   Show(guidance,visible);
  }
  List<VisualElement> nametags;
  /// Declutter: a guidance marker that would sit on a colonist's nametag moves up above it.
  float AvoidNametags(Rect marker)
  {
   if(nametags==null||nametags.Count==0)nametags=root.Query(className:"nametag").ToList();
   float top=marker.y;
   foreach(var tag in nametags)
   {
    if(tag.style.display!=DisplayStyle.Flex)continue;
    var r=new Rect(tag.style.left.value.value,tag.style.top.value.value,tag.layout.width>0?tag.layout.width:200,tag.layout.height>0?tag.layout.height:48);
    var m=new Rect(marker.x,top,marker.width,marker.height);
    if(m.Overlaps(r))top=r.y-marker.height-4;
   }
   return top;
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
   bool refreshTiers=Time.unscaledTime>=nextTierCheck;
   if(refreshTiers)nextTierCheck=Time.unscaledTime+TierRefreshSeconds;
   foreach(var pair in bars)
   {
    var d=pair.Key;var bar=pair.Value;
    if(!d||!d.isActiveAndEnabled){(gone??=new List<FeralDroid>()).Add(d);continue;}
    // Threat tier tint (grey easy, green normal, red danger) relative to the equipped weapon and the character.
    if(refreshTiers||!tiers.ContainsKey(d))
    {
     var tier=DroidThreat.Tier(d,combat);
     if(!tiers.TryGetValue(d,out var shown)||shown!=tier){tiers[d]=tier;Tint(bar,tier);}
    }
    // Just above the droid's head as it animates, so scaled variants (the 1.3× Foreman) are not over-lifted.
    var world=d.BarAnchor;var vp=worldCamera.WorldToViewportPoint(world);
    bool engaged=d.Health.Alive&&(d.Health.Current<d.Health.max||d.State!=DroidState.Idle&&d.State!=DroidState.Returning);
    bool visible=play&&engaged&&vp.z>0&&vp.x>0&&vp.x<1&&vp.y>0&&vp.y<1&&Vector3.Distance(world,combat.transform.position)<enemyBarDistance;
    Show(bar,visible);
    if(!visible)continue;
    var p=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);
    bar.style.left=p.x-50;bar.style.top=p.y-14;
    bar[0].style.width=Length.Percent(d.Health.Fraction*100);
   }
   if(gone!=null)foreach(var d in gone){bars[d].RemoveFromHierarchy();bars.Remove(d);tiers.Remove(d);}
  }
  public ThreatTier TierShown(FeralDroid d)=>d&&tiers.TryGetValue(d,out var t)?t:ThreatTier.Normal;
  static void Tint(VisualElement bar,ThreatTier tier)
  {
   var fill=bar[0];var name=bar.Q<Label>(className:"enemy-bar-name");
   var (f,e,n)=tier==ThreatTier.Easy?(EasyFill,EasyEdge,EasyName):tier==ThreatTier.Danger?(DangerFill,DangerEdge,DangerName):(NormalFill,NormalEdge,NormalName);
   fill.style.backgroundColor=f;fill.style.borderTopColor=e;
   if(name!=null)name.style.color=n;
   foreach(var t in new[]{"tier-easy","tier-normal","tier-danger"})bar.RemoveFromClassList(t);
   bar.AddToClassList(tier==ThreatTier.Easy?"tier-easy":tier==ThreatTier.Danger?"tier-danger":"tier-normal");
  }
  static void Show(VisualElement e,bool show){if(e!=null)e.style.display=show?DisplayStyle.Flex:DisplayStyle.None;}
 }
}
