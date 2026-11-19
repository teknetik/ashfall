using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;
namespace AthenHill
{
 [RequireComponent(typeof(UIDocument))]
 public class CityHud:MonoBehaviour
 {
  public GameSession session;
  public Camera worldCamera;
  [Range(0,4)]public float tunnelSpeed=2;
  VisualElement root;
  HudWindowLayout windowLayout;
  SettingsPanel settingsPanel;
  CraftingSession crafting;
  WardSaveGame saveGame;
  bool hasSave;
  FabricatorPanel fabricator;
  MerchantPanel merchant;
  VisualElement modalFocus,radio,notice;
  readonly HashSet<string> iconClasses=new HashSet<string>{"flask-icon","medkit-icon","scrap-icon","pack-icon","pistol-icon","lattice-icon"};
  readonly Dictionary<NpcAgent,VisualElement> tags=new Dictionary<NpcAgent,VisualElement>();
  readonly List<VisualElement> compassTicks=new List<VisualElement>();
  readonly List<Label> compassLabels=new List<Label>();
  int logRevision=-1, lastPopupFrame=-10;
  int windowWidth,windowHeight;
  int gameplayCullingMask;
  CameraClearFlags gameplayClearFlags;
  bool menuCamera;
  CityState previous=CityState.Boot;
  [Tooltip("Colonist view for the field pack. Found in the scene when not assigned.")]
  public CharacterPreview characterPreview;
  // The field pack owns its grid, loadout and colonist view; the session owns only the modal state + inspected item id.
  PackPanel pack;
  HotbarView hotbar;
  JournalPanel journalPanel;
  WorldMapPanel worldMap;
  StashPanel stashPanel;
  RestPanel restPanel;
  QuestJournal journal;
  int markCount=-1;
  Label footerLeft,footerRight;
  // ---- Interface package (19 Nov 2026): lower-third dialogue while the conversation camera frames, adaptive HUD.
  [Tooltip("Adaptive interface: quiet seconds before a corner panel fades, and the fade lengths. Full mode ignores it.")]
  public AdaptiveHudModel adaptive=new AdaptiveHudModel();
  [Tooltip("Seconds after the last hit taken that the HUD counts as in combat (Adaptive keeps every panel up).")]
  [Min(0)]public float hurtHoldSeconds=6;
  public DialogueLayout Layout {get;private set;}
  public InterfaceMode Mode=>session&&session.Settings?session.Settings.Interface.Mode:InterfaceMode.Full;
  VisualElement shade,modal;
  readonly VisualElement[][] panelElements=new VisualElement[AdaptiveHudModel.Panels.Length][];
  Label[] noteLabels;readonly string[] noteTexts=new string[4];
  ConversationCamera conversation;PlayerCombat playerCombat;
  float dialogueSince=-1,lastHurt=float.NegativeInfinity;
  int lastHp=int.MinValue,lastNano=int.MinValue,adaptiveLogRevision=-1;
  bool panelsApplied;
  void Start()
  {
   root=GetComponent<UIDocument>().rootVisualElement;
   gameplayCullingMask=worldCamera.cullingMask;gameplayClearFlags=worldCamera.clearFlags;
   windowLayout=new HudWindowLayout(root);
   settingsPanel=new SettingsPanel(root.Q("settings-panel"),session.Settings,session);
   crafting=session.GetComponent<CraftingSession>();
   foreach(string name in new[]{"identity","compass","objective-box","chat","notice","radio","modal"})windowLayout.Add(root.Q(name),name);
   foreach(string name in new[]{"quickbar","top-actions","interaction","key-hints"})windowLayout.Add(root.Q(name),name,true);
   root.RegisterCallback<GeometryChangedEvent>(_=>UpdateWindowSize());
   UpdateWindowSize();
   root.Q("objective-box").RegisterCallback<GeometryChangedEvent>(e=>root.Q("top-actions").style.top=e.newRect.yMax+7);
   shade=root.Q("shade");modal=root.Q("modal");
   panelElements[(int)HudPanel.Identity]=new[]{root.Q("identity")};
   panelElements[(int)HudPanel.FieldNotes]=new[]{root.Q("objective-box"),root.Q("top-actions")};
   panelElements[(int)HudPanel.Log]=new[]{root.Q("chat")};
   panelElements[(int)HudPanel.KeyHints]=new[]{root.Q("key-hints")};
   panelElements[(int)HudPanel.Hotbar]=new[]{root.Q("quickbar")};
   panelElements[(int)HudPanel.Compass]=new[]{root.Q("compass")};
   noteLabels=new[]{root.Q<Label>("objective-title"),root.Q<Label>("objective"),root.Q<Label>("progress"),root.Q<Label>("credits")};
   adaptive.WakeAll(Time.unscaledTime);
   session.input.PointerOverUi=PointerOverControls;
   session.input.MenuPopupOpen=()=>PopupOpen()||Time.frameCount-lastPopupFrame<=1;

   footerLeft=root.Q<Label>("modal-footer-left");
   footerRight=root.Q<Label>("modal-footer-right");

   // Keyboard: arrows move one step (grid/list handlers consume the navigation event); scroll views follow focus;
   // in play, gameplay keys (WASD/arrows, Enter, Tab) never navigate or press HUD buttons.
   UiNavigation.KeepFocusVisible(root.Q<ScrollView>("modal-scroll"));UiNavigation.KeepFocusVisible(root.Q<ScrollView>("inventory-scroll"));
   root.RegisterCallback<NavigationMoveEvent>(GuardNavigation,TrickleDown.TrickleDown);
   root.RegisterCallback<NavigationSubmitEvent>(GuardPlay,TrickleDown.TrickleDown);
   // HUD controls are mouse and hotkey only (1–7, Tab/5, 6, Esc, E), so nothing in the HUD can hold keyboard focus —
   // including scroll views' scrollers, which UI Toolkit may make focusable again when they re-layout.
   HudUnfocusable();
   foreach(var scroll in root.Q("hud").Query<ScrollView>().ToList())scroll.RegisterCallback<GeometryChangedEvent>(_=>HudUnfocusable(scroll));
   root.Q("modal").RegisterCallback<FocusInEvent>(e=>modalFocus=e.target as VisualElement);
   radio=root.Q("radio");notice=root.Q("notice");
   radio.RegisterCallback<GeometryChangedEvent>(_=>PlaceNotice());
   foreach(var item in session.catalog.items)if(item!=null&&!string.IsNullOrEmpty(item.icon))iconClasses.Add(item.icon);
   pack=new PackPanel(root,session,crafting,characterPreview?characterPreview:FindAnyObjectByType<CharacterPreview>(),iconClasses);

   Bind("close",session.Close);Bind("resume",session.Close);Bind("reset",session.ResetPlayer);
   if(crafting)fabricator=new FabricatorPanel(root,session,crafting);
   merchant=new MerchantPanel(root,session,crafting);
   journal=session.Journal;
   journalPanel=new JournalPanel(root.Q("journal-panel"),session,journal);
   worldMap=new WorldMapPanel(root,session);
   stashPanel=new StashPanel(root.Q("stash-panel"),session,crafting);
   restPanel=new RestPanel(root.Q("rest-panel"),session);
   if(journal)journal.Changed+=Refresh;
   Bind("details-close",session.CloseItemDetails);
   Bind("inventory-button",()=>session.Open(CityState.Inventory));Bind("notes-button",()=>session.Open(CityState.Journal));Bind("pause-button",()=>session.Open(CityState.Paused));Bind("credits-button",()=>session.Open(CityState.Credits));Bind("interaction",session.Interact);
   Bind("hint-pause",()=>session.Open(CityState.Paused));
   Bind("quit",()=>Application.Quit());Show("quit",!Application.isEditor);
   Bind("settings-button",()=>session.Open(CityState.Settings));
   saveGame=session.GetComponent<WardSaveGame>();
   Bind("start-game",StartNewGame);Bind("startup-settings",()=>session.Open(CityState.Settings));
   Bind("continue-game",()=>{if(saveGame)saveGame.Continue();});
   Bind("confirm-new-game",()=>{ShowNewGameConfirm(false);if(saveGame)saveGame.NewGame();else session.StartGame();});
   Bind("cancel-new-game",()=>{ShowNewGameConfirm(false);root.Q<Button>("start-game").Focus();});
   root.Q("new-game-confirm").RegisterCallback<KeyDownEvent>(e=>{if(e.keyCode==KeyCode.Escape){ShowNewGameConfirm(false);root.Q<Button>("start-game").Focus();e.StopPropagation();}},TrickleDown.TrickleDown);
   Bind("mute",session.ToggleMute);Bind("reduced-motion",session.ToggleReducedMotion);
   Bind("reset-ui",()=>{windowLayout.Reset();session.Notify("UI positions reset.");});
   for(int i=0;i<GameSession.MaxChoices;i++){int index=i;Bind("choice"+i,()=>session.Choose(index));}
   for(int i=0;i<3;i++){int index=i;Bind("node"+i,()=>session.SelectDestination(index));}
   // The hotbar (5 Oct 2026): 1 primary weapon, 2 sidearm, 3–0 items assigned in the field pack.
   hotbar=new HotbarView(root,session,()=>session.player?session.player.GetComponent<PlayerCombat>():null);
   foreach(var npc in session.npcs)
   {
    var tag=new VisualElement{pickingMode=PickingMode.Ignore,usageHints=UsageHints.DynamicTransform};tag.AddToClassList("nametag");
    var marker=new VisualElement{pickingMode=PickingMode.Ignore};marker.AddToClassList("diamond");marker.AddToClassList("nametag-marker");tag.Add(marker);
    var label=new Label(npc.definition.displayName+"\n"+npc.definition.role){pickingMode=PickingMode.Ignore};label.AddToClassList("nametag-copy");tag.Add(label);
    root.Q("nametags").Add(tag);tags.Add(npc,tag);windowLayout.Add(tag,"nametag-"+npc.definition.id,false,true);
   }
   // Keep compass geometry and lettering stable; move it through GPU transforms.
   // Reassigning labels at every 15-degree boundary fragmented the UI vertex pages.
   string[] directions={"N","NE","E","SE","S","SW","W","NW"};
   for(int i=0;i<24;i++)
   {
    var tick=new VisualElement{pickingMode=PickingMode.Ignore,usageHints=UsageHints.DynamicTransform};tick.AddToClassList("compass-tick");tick.EnableInClassList("major",i%3==0);tick.style.left=0;root.Q("compass-track").Add(tick);compassTicks.Add(tick);
    var label=new Label(i%3==0?directions[i/3]:""){pickingMode=PickingMode.Ignore,usageHints=UsageHints.DynamicTransform};label.AddToClassList("compass-label");label.EnableInClassList("minor",i%6!=0);label.style.left=0;root.Q("compass-track").Add(label);compassLabels.Add(label);
   }
   session.Changed+=Refresh;Refresh();
  }

  /// Start menu: New Game asks before replacing a save; without a save it simply starts.
  void StartNewGame()
  {
   if(saveGame&&saveGame.HasSave){ShowNewGameConfirm(true);return;}
   if(saveGame&&saveGame.Ready)saveGame.NewGame();else session.StartGame();
  }
  /// The confirmation takes the place of the start actions (it never stacks below them over the footer).
  void ShowNewGameConfirm(bool show)
  {
   Show("new-game-confirm",show);Show("startup-actions",!show);root.Q("startup-actions").SetEnabled(!show);
   if(show)root.schedule.Execute(()=>root.Q<Button>("cancel-new-game").Focus());
  }
  /// Continue appears (and takes focus) only when a save exists; its line summarises the saved progress.
  void RefreshStartupSave()
  {
   hasSave=saveGame&&saveGame.HasSave;
   Show("continue-game",hasSave);
   root.Q<Label>("start-game-label").text=hasSave?"New Game":"Start Game";
   root.Q<Button>("start-game").EnableInClassList("arrival-primary",!hasSave);
   if(hasSave)root.Q<Label>("continue-summary").text=saveGame.Summary()??"";
   ShowNewGameConfirm(false);
  }
  public int InventoryColumns()=>pack!=null?pack.Columns():1;
  /// Makes every element under the HUD (or one HUD scroll view) non-focusable and outside the Tab order.
  void HudUnfocusable(VisualElement scope=null)
  {
   foreach(var v in (scope??root.Q("hud")).Query<VisualElement>().ToList()){if(v.focusable)v.focusable=false;if(v.tabIndex>=0)v.tabIndex=-1;}
  }
  /// Navigation: in play nothing moves; in a modal, Tab / Shift+Tab cycle only through the modal's own controls.
  void GuardNavigation(NavigationMoveEvent e)
  {
   if(session.State==CityState.Play){GuardPlay(e);return;}
   if(e.direction!=NavigationMoveEvent.Direction.Next&&e.direction!=NavigationMoveEvent.Direction.Previous)return;
   var scope=ModalScope();if(scope==null)return;
   var stops=UiNavigation.TabStops(scope);if(stops.Count==0)return;
   var focused=root.focusController?.focusedElement as VisualElement;
   int i=stops.FindLastIndex(s=>s==focused||focused!=null&&s.Contains(focused));
   int next=UiNavigation.Cycle(i,stops.Count,e.direction==NavigationMoveEvent.Direction.Next);
   stops[next].Focus();
   UiNavigation.Consume(e,root);
  }
  /// The element Tab cycles within: the open modal (or the inventory's details), the startup actions or the New Game
  /// confirmation. Null in play, in Settings (its fields manage their own focus) and while the developer overlay is up.
  VisualElement ModalScope()
  {
   var overlay=root.Q("developer-time-overlay");
   if(overlay!=null&&overlay.resolvedStyle.display==DisplayStyle.Flex)return null;
   switch(session.State)
   {
    case CityState.Play:case CityState.Boot:case CityState.Settings:return null;
    case CityState.MainMenu:{var confirm=root.Q("new-game-confirm");return confirm!=null&&confirm.resolvedStyle.display==DisplayStyle.Flex?confirm:root.Q("startup-content");}
    case CityState.Inventory:return root.Q("modal");
    default:return root.Q("modal");
   }
  }
  /// In play the HUD is mouse/hotkey only: navigation and submit events (WASD, arrows, Tab, Enter) never reach it.
  void GuardPlay(EventBase e)
  {
   if(session.State!=CityState.Play)return;
   UiNavigation.Consume(e,root);
   (root.focusController?.focusedElement as VisualElement)?.Blur();
  }
  /// Keeps keyboard focus on something usable in a modal: when the focused control disabled itself (e.g. the last
  /// scrap coil sold) or disappeared, focus its nearest enabled neighbour (same row first), else Close.
  void EnsureModalFocus()
  {
   var state=session.State;
   if(state==CityState.Play||state==CityState.MainMenu||state==CityState.Boot||state==CityState.Settings||state==CityState.Inventory)return;
   if(root.Q("shade").resolvedStyle.display==DisplayStyle.None)return; // e.g. the developer time overlay owns focus
   var focused=root.focusController?.focusedElement as VisualElement;
   if(focused!=null&&focused.panel!=null&&focused.enabledInHierarchy&&focused.visible&&focused.resolvedStyle.display!=DisplayStyle.None)return;
   if(state==CityState.Fabricator&&fabricator!=null){var f=fabricator.ActionFocus;if(f!=null){(f as VisualElement).focusable=true;f.Focus();return;}}
   var last=modalFocus;var close=root.Q<Button>("close");
   Button pick=null;
   if(last!=null&&last.panel!=null)
   {
    pick=last.parent?.Query<Button>().Where(Usable).ToList().FirstOrDefault(b=>b!=last);
    if(pick==null)
    {
     var all=root.Q("modal").Query<Button>().ToList();int i=all.IndexOf(last as Button);
     if(i>=0)pick=all.Skip(i+1).FirstOrDefault(Usable)??all.Take(i).Reverse().FirstOrDefault(b=>Usable(b)&&b!=close);
    }
   }
   (pick??close)?.Focus();
  }
  static bool Usable(Button b)=>b!=null&&b.focusable&&b.enabledInHierarchy&&b.visible&&b.resolvedStyle.display!=DisplayStyle.None&&b.panel!=null;
  /// Notices sit under the radio panel while a radio line is up, so both stay readable.
  void PlaceNotice()
  {
   if(notice==null||radio==null)return;
   bool radioUp=radio.resolvedStyle.display==DisplayStyle.Flex&&radio.layout.height>0;
   notice.style.top=radioUp?radio.layout.yMax+8:new StyleLength(StyleKeyword.Null);
  }
  void OnDestroy(){if(journal)journal.Changed-=Refresh;pack?.Closed();SetMenuCamera(false);settingsPanel?.Dispose();windowLayout?.Dispose();if(session){session.Changed-=Refresh;session.input.PointerOverUi=null;session.input.MenuPopupOpen=null;}}
  // The opaque arrival artwork needs no city draw/shadow passes behind it.
  // Keep the saved world loaded, and restore its camera before entering gameplay.
  void SetMenuCamera(bool enabled)
  {
   if(!worldCamera||menuCamera==enabled)return;
   menuCamera=enabled;
   worldCamera.cullingMask=enabled?0:gameplayCullingMask;
   worldCamera.clearFlags=enabled?CameraClearFlags.SolidColor:gameplayClearFlags;
  }
  bool PopupOpen()=>root?.panel?.visualTree.Q(className:"unity-base-dropdown__container-outer")!=null;
  bool PointerOverControls()
  {
   if(root?.panel==null||Mouse.current==null)return false;
   if(windowLayout!=null&&windowLayout.IsDragging)return true;
   var point=Mouse.current.position.ReadValue();point.y=Screen.height-point.y;
   var element=root.panel.Pick(RuntimePanelUtils.ScreenToPanel(root.panel,point));
   for(;element!=null;element=element.parent)if(element is Button||element is ScrollView||element.ClassListContains("movable-window"))return true;
   return false;
  }
  void Bind(string name,Action action){root.Q<Button>(name).clicked+=action;}
  void Show(string name,bool show){root.Q(name).style.display=show?DisplayStyle.Flex:DisplayStyle.None;}
  void Text(string name,string value){root.Q<Label>(name).text=value;}
  /// Field Notes (upper right) shows the tracked mission (5 Oct 2026): its title, current instruction and a mark per
  /// objective step.
  void UpdateObjective()
  {
   var m=journal?journal.Tracked:null;
   Text("objective-title",m!=null?m.title.ToUpperInvariant():"");
   Text("objective",m!=null?(string.IsNullOrEmpty(m.objective)?m.steps.FirstOrDefault(x=>x.current)?.text??"":m.objective):"No mission tracked. Press J to open your journal.");
   int total=m!=null?Mathf.Min(8,m.steps.Count):0,done=m!=null?Mathf.Min(total,m.StepsDone):0;
   Text("progress",m!=null?$"{done} / {m.steps.Count} · J journal":"");
   var marks=root.Q("progress-marks");
   if(marks!=null)
   {
    if(markCount!=total){markCount=total;marks.Clear();for(int i=0;i<total;i++){var mark=new VisualElement{name="mark"+i,pickingMode=PickingMode.Ignore};mark.AddToClassList("progress-mark");marks.Add(mark);}}
    for(int i=0;i<marks.childCount;i++)marks[i].EnableInClassList("complete",i<done);
   }
  }
  void UpdateWindowSize()
  {
   windowWidth=Screen.width;windowHeight=Screen.height;
   root.EnableInClassList("compact",root.resolvedStyle.width<1780);
   root.EnableInClassList("small-window",Screen.width<1500||Screen.height<900);
  }
  public void Refresh()
  {
   if(root==null||session.Shop==null)return;
   bool modal=session.State!=CityState.Play;
   if(previous!=session.State)windowLayout.CancelDrag();
   bool startup=!session.HasStarted;
   SetMenuCamera(startup);
   root.Q("hud").SetEnabled(!modal);Show("hud",!startup);
   Show("startup-screen",startup);Show("startup-content",session.State==CityState.MainMenu);
   root.Q("startup-content").SetEnabled(session.State==CityState.MainMenu);
   root.EnableInClassList("startup-settings",startup&&session.State==CityState.Settings);
   Show("shade",modal&&session.State!=CityState.MainMenu);Show("notice",!modal&&!string.IsNullOrEmpty(session.notice));Text("notice",session.notice);Text("modal-notice",session.notice);
   bool radioUp=session.HasStarted&&session.RadioLine.Showing;
   Show("radio",radioUp);
   if(radioUp){Text("radio-text",session.RadioLine.Text);Text("radio-speaker",(session.RadioLine.Speaker??"Radio").ToUpperInvariant()+" · RADIO");}
   PlaceNotice();
   root.Q("modal").EnableInClassList("wide-modal",session.State==CityState.Fabricator||session.State==CityState.Shop||session.State==CityState.Journal||session.State==CityState.Stash);
   root.Q("modal").EnableInClassList("merchant-modal",session.State==CityState.Shop);
   root.Q("modal").EnableInClassList("pack-modal",session.State==CityState.Inventory);
   UpdateObjective();
   Text("credits",$"{session.Shop.Credits} cr");
   hotbar.Refresh();
   if(logRevision!=session.LogRevision){logRevision=session.LogRevision;Text("log",string.Join("\n",session.Log));root.schedule.Execute(()=>{var scroll=root.Q<ScrollView>("log-scroll");scroll.scrollOffset=new Vector2(0,Mathf.Max(0,scroll.verticalScroller.highValue));});}
   Show("dialogue-panel",session.State==CityState.Dialogue);Show("shop-panel",session.State==CityState.Shop);Show("fabricator-panel",session.State==CityState.Fabricator);Show("inventory-panel",session.State==CityState.Inventory);Show("grid-panel",session.State==CityState.Grid);Show("pause-panel",session.State==CityState.Paused);Show("text-panel",session.State==CityState.Credits);
   Show("journal-panel",session.State==CityState.Journal);Show("stash-panel",session.State==CityState.Stash);Show("rest-panel",session.State==CityState.Rest);
   if(session.State==CityState.Fabricator)fabricator?.Refresh();
   Show("modal-notice",session.State!=CityState.Settings&&!string.IsNullOrEmpty(session.notice));
   bool settingsOpen=session.State==CityState.Settings;
   Show("settings-panel",settingsOpen);Show("modal-scroll",!settingsOpen);root.Q("modal").EnableInClassList("settings-modal",settingsOpen);
   root.Q<Button>("close").text=settingsOpen?session.Settings.Previewing?"Revert · Esc":"Back · Esc":session.State==CityState.Inventory?"Close · Tab / Esc":"Close · Esc";
   if(footerLeft!=null)footerLeft.text="FREE COLUMN  /  ATHEN HILL";
   if(footerRight!=null)footerRight.text="Tab · Select     Enter · Confirm";
   Text("modal-title",session.State.ToString());Text("modal-subtitle","");
   if(session.State==CityState.Fabricator)
   {
    var station=session.ActiveStation;
    Text("modal-title",station&&!string.IsNullOrEmpty(station.title)?station.title:"Field fabricator");Text("modal-subtitle",station?station.subtitle:"Fabricate parts and fit pistol mods");
    if(footerRight!=null)footerRight.text="↑↓ · Schematic     → · Actions     Tab · Next     Enter · Confirm";
   }
   UpdateDialogueLayout();
   if(session.State==CityState.Dialogue)
   {
    DialogueHeading();Text("dialogue-text",session.Dialogue.text);
    var choices=session.Choices;
    for(int i=0;i<GameSession.MaxChoices;i++){var b=root.Q<Button>("choice"+i);if(b==null)continue;bool on=i<choices.Length;b.style.display=on?DisplayStyle.Flex:DisplayStyle.None;if(on)b.text=choices[i].label;}
   }
   if(session.State==CityState.Shop)
   {
    var shop=session.ActiveShop;
    Text("modal-title",shop.title);Text("modal-subtitle",shop.subtitle);
    merchant.Refresh();
    if(footerRight!=null)footerRight.text="Select · Inspect     Buy / Sell · Trade     Esc · Close";
   }
   if(session.State==CityState.Grid)
   {
    Text("modal-title","Sector lattice");Text("modal-subtitle","Lattice Jack · Athen Hill uplink");Text("grid-status",session.GridProgress<1?"Opening the connection…":"Select a destination to establish a link.");root.Q<ProgressBar>("grid-progress").value=session.GridProgress*100;
    Show("grid-nodes",session.GridProgress>=1);for(int i=0;i<3;i++){var n=session.catalog.destinations[i];root.Q<Button>("node"+i).text=n.name+"\n"+n.description;}
    Text("grid-selection",session.selectedDestination==""?"This city slice ends at the uplink.":"Link established. Your position in Athen Hill is unchanged.");
   }
   if(settingsOpen){Text("modal-title","Settings");Text("modal-subtitle","Sound and video · Make the city your own");}
   if(session.State==CityState.Paused){Text("modal-title","City paused");Text("modal-subtitle","Take your time. The hill will be here.");root.Q<Button>("mute").text=session.muted?"Unmute audio":"Mute audio";root.Q<Button>("reduced-motion").text="Reduced motion: "+(session.reducedMotion?"On":"Off");}
   if(session.State==CityState.Inventory)
   {
    Text("modal-title","Field pack");Text("modal-subtitle","Pack, loadout and colonist");
    pack.Refresh();
    if(footerRight!=null)footerRight.text="Select to inspect · Drag to equip · Drag preview to turn · Tab / Esc close";
   }
   if(session.State==CityState.Journal)
   {
    Text("modal-title","Journal");Text("modal-subtitle","Missions · Ward notes");journalPanel.Refresh();
    if(footerRight!=null)footerRight.text="↑↓ · Mission     T · Track     J / Esc · Close";
   }
   worldMap?.Refresh(); // the world map (M) swaps the modal's scroll view for its sheet, and back
   if(session.State==CityState.Stash)
   {
    var home=session.ActiveHome;
    Text("modal-title","Home locker");Text("modal-subtitle",(home?home.displayName:"Container home")+" · south wall");stashPanel.Refresh();
    if(footerRight!=null)footerRight.text="Enter · Move one     Shift+Enter or double-click · Move all     Esc · Close";
   }
   if(session.State==CityState.Rest){Text("modal-title","Bunk");Text("modal-subtitle","Rest and save");}
   if(session.State==CityState.Credits){Text("modal-title","Credits and licences");Text("modal-subtitle","Athen Hill · An original colony city homage");Text("panel-text",session.catalog.credits?session.catalog.credits.text:"Credits unavailable.");}
   if(previous!=session.State)
   {
    if(previous==CityState.Inventory)pack.Closed();
    previous=session.State;HudUnfocusable();
    root.Q<ScrollView>("modal-scroll").scrollOffset=Vector2.zero;
    if(modal)
    {
     // Default modal focus goes to the close/primary button, except Inventory.
     // The pack manages its own focus (the selected cell, or Close when the pack is empty) so Enter inspects items
     // rather than accidentally closing the modal.
     if(session.State==CityState.Inventory)pack.Opened();
     else
     {
      if(session.State==CityState.Shop)merchant.Opened();
      else if(session.State==CityState.Journal)journalPanel.Opened();
      else if(session.State==CityState.Map&&worldMap!=null)worldMap.Opened();
      else if(session.State==CityState.Stash)stashPanel.Opened();
      else if(session.State==CityState.Rest)restPanel.Opened();
      else if(session.State==CityState.Fabricator&&fabricator!=null)fabricator.Opened();
      else
      {
       if(session.State==CityState.MainMenu)RefreshStartupSave();
       root.schedule.Execute(()=>root.Q<Button>(session.State==CityState.MainMenu?hasSave?"continue-game":"start-game":session.State==CityState.Dialogue?"choice0":session.State==CityState.Fabricator?"fabricator-craft":"close").Focus());
      }
     }
    }
    else root.focusController?.focusedElement?.Blur();
   }
   if(modal)root.schedule.Execute(EnsureModalFocus);
  }
  void LateUpdate()
  {
   if(root==null||root.panel==null)return;
   if(PopupOpen())lastPopupFrame=Time.frameCount;
   if(hasSave&&session.State==CityState.MainMenu){var c=root.Q<Button>("continue-game");bool ready=saveGame&&saveGame.Ready;if(c.enabledSelf!=ready)c.SetEnabled(ready);}
   if(windowWidth!=Screen.width||windowHeight!=Screen.height)UpdateWindowSize();
   UpdateCompass();
   bool tunnel=session.State==CityState.Grid&&session.GridProgress<1&&!session.reducedMotion;
   Show("tunnel",tunnel);
   if(tunnel)for(int i=0;i<4;i++){var ring=root.Q("tunnel-ring"+i);float phase=Mathf.Repeat(session.GridProgress*tunnelSpeed+i*.25f,1);float size=20+phase*480;ring.style.width=Length.Percent(size);ring.style.height=Length.Percent(size);ring.style.left=Length.Percent(50-size/2);ring.style.top=Length.Percent(50-size/2);ring.style.opacity=1-phase;}
   string prompt=session.Prompt;Show("interaction",!string.IsNullOrEmpty(prompt));root.Q<Button>("interaction").text=prompt;
   UpdateDialogueLayout();UpdatePanels(!string.IsNullOrEmpty(prompt));
   // Declutter: the colonist named by the interaction prompt needs no nametag (it would sit over shop signs).
   var prompted=!string.IsNullOrEmpty(prompt)?session.Nearest:null;
   foreach(var pair in tags)
   {
    var world=pair.Key.transform.position+Vector3.up*2.15f;var p=worldCamera.WorldToViewportPoint(world);
    bool visible=session.State==CityState.Play&&pair.Key!=prompted&&p.z>0&&p.x>0&&p.x<1&&p.y>0&&p.y<1&&Vector3.Distance(world,session.player.transform.position)<34&&InSight(world);
    pair.Value.style.display=visible?DisplayStyle.Flex:DisplayStyle.None;
    if(visible){var point=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);pair.Value.style.left=point.x-28;pair.Value.style.top=point.y-30;}
   }
  }
  ConversationCamera Conversation()
  {
   if(!conversation&&session.follow)conversation=session.follow.conversation?session.follow.conversation:session.follow.GetComponent<ConversationCamera>();
   return conversation;
  }
  /// Lower third only while the conversation camera frames the NPC (DialogueLayoutRule); otherwise the centred window
  /// over the shade, exactly as before. The class swaps the modal's styling; the saved drag offset waits meanwhile.
  void UpdateDialogueLayout()
  {
   if(shade==null)return;
   bool open=session.State==CityState.Dialogue&&session.ActiveNpc;
   if(!open)dialogueSince=-1;else if(dialogueSince<0)dialogueSince=Time.unscaledTime;
   var cam=Conversation();var follow=session.follow;
   bool cameraOn=ConversationCamera.Enabled&&cam&&cam.isActiveAndEnabled&&cam.framingEnabled&&!PhotoMode.Active;
   var next=DialogueLayoutRule.Choose(open,cameraOn,follow&&follow.FixedView,follow&&follow.FirstPerson,cam&&cam.Engaged,cam&&cam.Framing,open?Time.unscaledTime-dialogueSince:0);
   if(next==Layout)return;
   Layout=next;bool lower=next==DialogueLayout.LowerThird;
   shade.EnableInClassList("dialogue-lower-third",lower);
   windowLayout.Hold(modal,lower);
   if(open)DialogueHeading();
  }
  /// Centred: the colonist's name over the topic, as before. Lower third: a name plate (name in capitals, role · topic).
  void DialogueHeading()
  {
   var npc=session.ActiveNpc;var node=session.Dialogue;if(!npc||npc.definition==null||node==null)return;
   var d=npc.definition;
   if(Layout!=DialogueLayout.LowerThird){Text("modal-title",d.displayName);Text("modal-subtitle",node.title);return;}
   Text("modal-title",(d.displayName??"").ToUpperInvariant());
   Text("modal-subtitle",DialogueLayoutRule.NamePlateSubtitle(d.role,node.title));
  }
  PlayerCombat Combat(){if(!playerCombat&&session.player)playerCombat=session.player.GetComponent<PlayerCombat>();return playerCombat;}
  /// Feeds the adaptive model what changed this frame and applies the panels' opacity. In Full mode only the
  /// lower-third dialogue moves anything (the log, key hints and hotbar give way to it).
  void UpdatePanels(bool prompt)
  {
   float now=Time.unscaledTime;
   var combat=Combat();
   if(combat&&combat.Health)
   {
    int hp=Mathf.CeilToInt(combat.Health.Current),nano=Mathf.FloorToInt(combat.Nano);
    if(hp!=lastHp||nano!=lastNano)
    {
     if(lastHp!=int.MinValue){if(hp<lastHp)lastHurt=now;adaptive.Wake(HudPanel.Identity,now);}
     lastHp=hp;lastNano=nano;
    }
   }
   if(noteLabels!=null)for(int i=0;i<noteLabels.Length;i++)
   {
    var text=noteLabels[i]?.text;
    if(!string.Equals(text,noteTexts[i],StringComparison.Ordinal)){noteTexts[i]=text;adaptive.Wake(HudPanel.FieldNotes,now);}
   }
   if(adaptiveLogRevision!=session.LogRevision){adaptiveLogRevision=session.LogRevision;adaptive.Wake(HudPanel.Log,now);}
   var frame=new HudFrame
   {
    mode=Mode,lowerThird=Layout==DialogueLayout.LowerThird,windowOpen=session.State!=CityState.Play,
    combat=combat&&combat.Armed||now-lastHurt<hurtHoldSeconds,altHeld=session.input&&session.input.CursorFreed,
    prompt=prompt,reducedMotion=session.reducedMotion
   };
   if(!adaptive.Step(frame,now,Time.unscaledDeltaTime)&&panelsApplied)return;
   panelsApplied=true;
   foreach(var p in AdaptiveHudModel.Panels)
   {
    float a=adaptive.Alpha(p);
    foreach(var e in panelElements[(int)p])
    {
     if(e==null)continue;
     // Full opacity clears the inline values so the panel is exactly the authored one.
     if(a>=1){e.style.opacity=StyleKeyword.Null;e.style.visibility=StyleKeyword.Null;}
     else{e.style.opacity=a;e.style.visibility=a<AdaptiveHudModel.HiddenBelow?Visibility.Hidden:Visibility.Visible;}
    }
   }
  }
  /// Dev-bridge state (snapshot.json → hud): dialogue layout, interface mode, panel opacity and which are hidden.
  public static object Qa(){var hud=FindAnyObjectByType<CityHud>();return hud?hud.QaState():null;}
  object QaState()
  {
   bool radioUp=radio!=null&&radio.resolvedStyle.display==DisplayStyle.Flex,noticeUp=notice!=null&&notice.resolvedStyle.display==DisplayStyle.Flex;
   return new
   {
    dialogueLayout=DialogueLayoutRule.Id(Layout),
    shadeDimmed=shade!=null&&shade.resolvedStyle.display==DisplayStyle.Flex&&Layout!=DialogueLayout.LowerThird,
    modalHeld=modal!=null&&windowLayout!=null&&windowLayout.Held(modal),
    interfaceMode=Mode==InterfaceMode.Adaptive?"adaptive":"full",
    conversationCamera=ConversationCamera.Enabled,
    conversationCameraSetting=session&&session.Settings?session.Settings.Interface.conversationCamera:ConversationCamera.Enabled,
    barkCaptions=BarkDirector.CaptionsEnabled,
    hidden=AdaptiveHudModel.Panels.Where(p=>adaptive.Hidden(p)).Select(AdaptiveHudModel.Id).ToArray(),
    opacity=AdaptiveHudModel.Panels.ToDictionary(AdaptiveHudModel.Id,p=>adaptive.Alpha(p)),
    quietSeconds=adaptive.quietSeconds,
    topCentre=new{radio=radioUp,notice=noticeUp,depth=(radioUp?1:0)+(noticeUp?1:0)}
   };
  }
  static readonly RaycastHit[] sightHits=new RaycastHit[8];
  /// A nametag only shows when nothing solid stands between the camera and it (Brann works inside the Salvage shop;
  /// his name must not float on the street wall). The player's own capsule never hides a tag.
  bool InSight(Vector3 world)
  {
   var from=worldCamera.transform.position;var d=world-from;float len=d.magnitude;if(len<.01f)return true;
   var mask=session.follow?session.follow.worldMask:(LayerMask)~(1<<8);
   int n=Physics.RaycastNonAlloc(from,d/len,sightHits,len-.1f,mask,QueryTriggerInteraction.Ignore);
   for(int i=0;i<n;i++)if(!sightHits[i].collider.transform.IsChildOf(session.player.transform))return false;
   return true;
  }
  void UpdateCompass()
  {
   // North is world +Z; use the rendered camera so fixed review views agree too.
   float heading=worldCamera.transform.eulerAngles.y;
   var track=root.Q("compass-track");float width=track.resolvedStyle.width;
   if(float.IsNaN(width))return;
   for(int i=0;i<compassTicks.Count;i++)
   {
    float x=width*.5f+Mathf.DeltaAngle(heading,i*15)*(width/190f);
    compassTicks[i].style.translate=new Translate(new Length(x),new Length(0),0);
    compassLabels[i].style.translate=new Translate(new Length(x-17),new Length(0),0);
   }
  }
 }
}
