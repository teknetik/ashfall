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
  readonly Dictionary<NpcAgent,VisualElement> tags=new Dictionary<NpcAgent,VisualElement>();
  readonly List<VisualElement> compassTicks=new List<VisualElement>();
  readonly List<Label> compassLabels=new List<Label>();
  int logRevision=-1, lastPopupFrame=-10;
  int windowWidth,windowHeight;
  int gameplayCullingMask;
  CameraClearFlags gameplayClearFlags;
  bool menuCamera;
  CityState previous=CityState.Boot;
  // Inventory UI state is local to the HUD; the session owns only the modal state + inspected item id.
  VisualElement inventoryGrid,inventoryEmpty,inventoryOverviewIcon,inventoryDetails,detailsIcon;
  ScrollView inventoryScroll;
  Label inventoryOverviewName,inventoryOverviewQuantity,inventoryOverviewDescription,detailsTitle,detailsQuantity,detailsPrices,detailsDescription,footerLeft,footerRight;
  Button detailsClose;
  readonly Dictionary<string,Button> inventoryTiles=new Dictionary<string,Button>();
  readonly List<string> inventoryIds=new List<string>();
  string selectedItemId,hoverItemId,lastDetailId;
  void Start()
  {
   root=GetComponent<UIDocument>().rootVisualElement;
   gameplayCullingMask=worldCamera.cullingMask;gameplayClearFlags=worldCamera.clearFlags;
   windowLayout=new HudWindowLayout(root);
   settingsPanel=new SettingsPanel(root.Q("settings-panel"),session.Settings,session);
   crafting=session.GetComponent<CraftingSession>();
   foreach(string name in new[]{"identity","compass","objective-box","chat","notice","modal"})windowLayout.Add(root.Q(name),name);
   foreach(string name in new[]{"quickbar","top-actions","interaction","key-hints"})windowLayout.Add(root.Q(name),name,true);
   root.RegisterCallback<GeometryChangedEvent>(_=>UpdateWindowSize());
   UpdateWindowSize();
   root.Q("objective-box").RegisterCallback<GeometryChangedEvent>(e=>root.Q("top-actions").style.top=e.newRect.yMax+7);
   session.input.PointerOverUi=PointerOverControls;
   session.input.MenuPopupOpen=()=>PopupOpen()||Time.frameCount-lastPopupFrame<=1;

   // Inventory elements (dynamic grid + overview + details overlay).
   inventoryGrid=root.Q("inventory-grid");
   inventoryEmpty=root.Q("inventory-empty");
   inventoryScroll=root.Q<ScrollView>("inventory-scroll");
   inventoryOverviewIcon=root.Q("inventory-overview-icon");
   inventoryOverviewName=root.Q<Label>("inventory-overview-name");
   inventoryOverviewQuantity=root.Q<Label>("inventory-overview-quantity");
   inventoryOverviewDescription=root.Q<Label>("inventory-overview-description");
   inventoryDetails=root.Q("inventory-details");
   detailsIcon=root.Q("details-icon");
   detailsTitle=root.Q<Label>("details-title");
   detailsQuantity=root.Q<Label>("details-quantity");
   detailsPrices=root.Q<Label>("details-prices");
   detailsDescription=root.Q<Label>("details-description");
   detailsClose=root.Q<Button>("details-close");
   footerLeft=root.Q<Label>("modal-footer-left");
   footerRight=root.Q<Label>("modal-footer-right");

   root.RegisterCallback<KeyDownEvent>(InventoryKeyNav,TrickleDown.TrickleDown);

   Bind("close",session.Close);Bind("resume",session.Close);Bind("reset",session.ResetPlayer);
   Bind("fabricator-craft",()=>{if(crafting!=null&&crafting.Craft(out _))root.Q<Button>("fabricator-fit").Focus();});
   Bind("fabricator-fit",()=>crafting?.Fit(out _));
   Bind("fabricator-remove",()=>crafting?.Remove(out _));
   Bind("details-close",session.CloseItemDetails);
   Bind("inventory-button",()=>session.Open(CityState.Inventory));Bind("notes-button",()=>session.Open(CityState.Notes));Bind("pause-button",()=>session.Open(CityState.Paused));Bind("credits-button",()=>session.Open(CityState.Credits));Bind("interaction",session.Interact);
   Bind("hint-pause",()=>session.Open(CityState.Paused));
   Bind("quit",()=>Application.Quit());Show("quit",!Application.isEditor);
   Bind("settings-button",()=>session.Open(CityState.Settings));
   Bind("start-game",session.StartGame);Bind("startup-settings",()=>session.Open(CityState.Settings));
   Bind("mute",session.ToggleMute);Bind("reduced-motion",session.ToggleReducedMotion);
   Bind("reset-ui",()=>{windowLayout.Reset();session.Notify("UI positions reset.");});
   for(int i=0;i<2;i++){int index=i;Bind("choice"+i,()=>session.Choose(index));}
   for(int i=0;i<3;i++){int index=i;Bind("buy"+i,()=>session.Trade(session.catalog.items[index].id,true));Bind("sell"+i,()=>session.Trade(session.catalog.items[index].id,false));Bind("node"+i,()=>session.SelectDestination(index));}
   for(int i=1;i<=6;i++){int slot=i;Bind("slot"+i,()=>{SelectSlot(slot);session.Hotbar(slot);});}
   // Spare slots complete the 1–0 row; the six existing actions keep their bindings.
   for(int i=7;i<=10;i++)root.Q<Button>("slot"+i).SetEnabled(false);
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

  static readonly string[] itemIconClasses={"flask-icon","medkit-icon","scrap-icon","pack-icon"};
  void SetItemIcon(VisualElement target,string id)
  {
   if(target==null)return;
   foreach(string c in itemIconClasses)target.RemoveFromClassList(c);
   if(id=="water_flask")target.AddToClassList("flask-icon");
   else if(id=="medkit")target.AddToClassList("medkit-icon");
   else if(id=="scrap_coil")target.AddToClassList("scrap-icon");
   else target.AddToClassList("pack-icon");
  }

  void EnsureInventoryGrid(IEnumerable<ItemSpec> items)
  {
   inventoryTiles.Clear();inventoryIds.Clear();
   inventoryGrid?.Clear();
   if(inventoryGrid==null)return;
   foreach(var item in items)
   {
    int quantity=session.Shop.Quantity(item.id);
    var tile=new Button{tooltip=$"{item.name} · ×{quantity}"};
    tile.name="inv-"+item.id;
    tile.AddToClassList("inventory-tile");
    var icon=new VisualElement{pickingMode=PickingMode.Ignore};
    icon.AddToClassList("inventory-tile-icon");
    SetItemIcon(icon,item.id);
    tile.Add(icon);
    var badge=new Label($"×{quantity}");
    badge.AddToClassList("inventory-tile-qty");
    badge.pickingMode=PickingMode.Ignore;
    tile.Add(badge);
    string id=item.id;
    tile.RegisterCallback<PointerEnterEvent>(_=>{hoverItemId=id;UpdateInventoryOverview();});
    tile.RegisterCallback<PointerLeaveEvent>(_=>{if(hoverItemId==id)hoverItemId=null;UpdateInventoryOverview();});
    tile.RegisterCallback<FocusInEvent>(_=>{selectedItemId=id;UpdateInventoryOverview();});
    tile.RegisterCallback<ClickEvent>(e=>{selectedItemId=id;UpdateInventoryOverview();if(e.shiftKey)session.OpenItemDetails(id);});
    tile.RegisterCallback<KeyDownEvent>(e=>{
     if(e.keyCode==KeyCode.Return||e.keyCode==KeyCode.KeypadEnter){session.OpenItemDetails(id);e.StopPropagation();}
    });
    inventoryGrid.Add(tile);
    inventoryTiles[id]=tile;
    inventoryIds.Add(id);
   }
  }

  void UpdateInventoryOverview()
  {
   if(session==null||session.Shop==null||session.catalog==null)return;
   string id=hoverItemId??selectedItemId;
   if(string.IsNullOrEmpty(id))
   {
    inventoryOverviewName.text="No item selected.";
    inventoryOverviewQuantity.text="";
    inventoryOverviewDescription.text="";
    SetItemIcon(inventoryOverviewIcon,null);
    return;
   }
   var item=session.catalog.items.FirstOrDefault(i=>i!=null&&i.id==id);
   if(item==null){inventoryOverviewName.text="No item selected.";inventoryOverviewQuantity.text="";inventoryOverviewDescription.text="";SetItemIcon(inventoryOverviewIcon,null);return;}
   int quantity=session.Shop.Quantity(id);
   inventoryOverviewName.text=item.name;
   inventoryOverviewQuantity.text=$"{quantity} carried";
   inventoryOverviewDescription.text=string.IsNullOrWhiteSpace(item.description)?"No description recorded.":item.description;
   SetItemIcon(inventoryOverviewIcon,id);
  }

  void InventoryKeyNav(KeyDownEvent e)
  {
   if(session.State!=CityState.Inventory||inventoryIds.Count==0||root?.focusController==null)return;
   bool detailsOpen=!string.IsNullOrEmpty(session.DetailItemId);
   if(detailsOpen)return;
   var focused=root.focusController.focusedElement as VisualElement;
   if(focused==null||focused.name==null||!focused.name.StartsWith("inv-"))return;
   string id=focused.name.Substring("inv-".Length);
   int index=inventoryIds.IndexOf(id);
   if(index<0)return;
   int columns=root.ClassListContains("small-window")?3:4;
   int target=index;
   switch(e.keyCode)
   {
    case KeyCode.LeftArrow:target=index-1;break;
    case KeyCode.RightArrow:target=index+1;break;
    case KeyCode.UpArrow:target=index-columns;break;
    case KeyCode.DownArrow:target=index+columns;break;
    case KeyCode.Return:
    case KeyCode.KeypadEnter:session.OpenItemDetails(id);e.StopPropagation();return;
    default:return;
   }
   target=Mathf.Clamp(target,0,inventoryIds.Count-1);
   string nextId=inventoryIds[target];
   if(inventoryTiles.TryGetValue(nextId,out var next))next.Focus();
   e.StopPropagation();
  }
  void OnDestroy(){SetMenuCamera(false);settingsPanel?.Dispose();windowLayout?.Dispose();if(session){session.Changed-=Refresh;session.input.PointerOverUi=null;session.input.MenuPopupOpen=null;}}
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
  void SelectSlot(int slot){for(int i=1;i<=6;i++)root.Q("slot"+i).EnableInClassList("selected",i==slot);}
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
   Text("objective",session.visitedHill&&session.Spoken.Count<4?"Meet the colonists":session.Objective);Text("progress",$"{session.Spoken.Count} / 4 conversations");
   for(int i=0;i<4;i++)root.Q("mark"+i).EnableInClassList("complete",i<session.Spoken.Count);
   Text("credits",$"{session.Shop.Credits} cr");
   if(logRevision!=session.LogRevision){logRevision=session.LogRevision;Text("log",string.Join("\n",session.Log));root.schedule.Execute(()=>{var scroll=root.Q<ScrollView>("log-scroll");scroll.scrollOffset=new Vector2(0,Mathf.Max(0,scroll.verticalScroller.highValue));});}
   Show("dialogue-panel",session.State==CityState.Dialogue);Show("shop-panel",session.State==CityState.Shop);Show("fabricator-panel",session.State==CityState.Fabricator);Show("inventory-panel",session.State==CityState.Inventory);Show("grid-panel",session.State==CityState.Grid);Show("pause-panel",session.State==CityState.Paused);Show("text-panel",session.State==CityState.Notes||session.State==CityState.Credits);
   if(session.State==CityState.Fabricator&&crafting?.Model!=null)
   {
    var model=crafting.Model;
    bool known=model.KnownRecipes.Contains("recipe_grip_stabilised_pistol");

    Text("fabricator-recipe",known?"Stabilised Pistol Grip · known schematic":"No known schematics · Unknown schematics: 1");
    Text("fabricator-ingredients",known?$"Any servo {session.Shop.Quantity("droid_servo_damaged")}/1  ·  Scrap Alloy {session.Shop.Quantity("scrap_alloy")}/2  ·  Any tier-one nanites {session.Shop.Quantity("nanite_residue")}/5\nOutput: Stabilised Pistol Grip ×1":"Salvage a worker-droid servo at the depot to learn this schematic.");
    Text("fabricator-stat",$"Scrap Pistol · Recoil {model.BaseRecoil:0} → 31 · Current {model.RecoilStat:0}");
    bool canCraft=model.CanCraft("recipe_grip_stabilised_pistol",session.ActiveStationId,out var craftReason);
    var craftButton=root.Q<Button>("fabricator-craft");craftButton.SetEnabled(canCraft);craftButton.tooltip=canCraft?"Consume parts to craft one grip":craftReason;
    var fitButton=root.Q<Button>("fabricator-fit");fitButton.SetEnabled(session.Shop.Quantity("grip_stabilised_pistol")>0&&model.GripSlot==null);fitButton.tooltip="Fit one carried grip to the pistol";
    root.Q<Button>("fabricator-remove").SetEnabled(model.GripSlot!=null);
   }
   Show("modal-notice",session.State!=CityState.Settings&&!string.IsNullOrEmpty(session.notice));
   bool settingsOpen=session.State==CityState.Settings;
   Show("settings-panel",settingsOpen);Show("modal-scroll",!settingsOpen);root.Q("modal").EnableInClassList("settings-modal",settingsOpen);
   root.Q<Button>("close").text=settingsOpen?session.Settings.Previewing?"Revert · Esc":"Back · Esc":session.State==CityState.Inventory?"Close · Tab / Esc":"Close · Esc";
   if(footerLeft!=null)footerLeft.text="FREE COLUMN  /  ATHEN HILL";
   if(footerRight!=null)footerRight.text="Tab · Select     Enter · Confirm";
   Text("modal-title",session.State.ToString());Text("modal-subtitle","");
   if(session.State==CityState.Fabricator){Text("modal-title","Field fabricator");Text("modal-subtitle","Warden outpost · Salvage and fit");}
   if(session.State==CityState.Dialogue){Text("modal-title",session.ActiveNpc.definition.displayName);Text("modal-subtitle",session.Dialogue.title);Text("dialogue-text",session.Dialogue.text);for(int i=0;i<2;i++)root.Q<Button>("choice"+i).text=session.Dialogue.choices[i].label;}
   if(session.State==CityState.Shop)
   {
    Text("modal-title","Basic General");Text("modal-subtitle","Mira · Supplies and salvage");Text("shop-credit",$"Available balance: {session.Shop.Credits} credits");
    for(int i=0;i<3;i++){var item=session.catalog.items[i];Text("item"+i,$"{item.name} · {session.Shop.Quantity(item.id)} carried\n{item.description}");var b=root.Q<Button>("buy"+i);b.text=$"Buy · {item.buyPrice} cr";b.SetEnabled(session.Shop.Credits>=item.buyPrice);var s=root.Q<Button>("sell"+i);s.text=$"Sell · {item.sellPrice} cr";s.SetEnabled(session.Shop.Quantity(item.id)>0);}
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
    Text("modal-title","Field pack");Text("modal-subtitle","Supplies and salvage");Text("pack-credit",$"{session.Shop.Credits} credits");
    var carried=InventoryView.Items(session.catalog.items,session.Shop).ToList();
    bool empty=carried.Count==0;
    inventoryEmpty.style.display=empty?DisplayStyle.Flex:DisplayStyle.None;
    inventoryGrid.style.display=empty?DisplayStyle.None:DisplayStyle.Flex;
    if(empty){selectedItemId=null;hoverItemId=null;lastDetailId=null;UpdateInventoryOverview();}
    else
    {
     if(string.IsNullOrEmpty(selectedItemId)||!carried.Any(i=>i.id==selectedItemId))selectedItemId=carried[0].id;
     EnsureInventoryGrid(carried);
     UpdateInventoryOverview();
     if(string.IsNullOrEmpty(session.DetailItemId)&&inventoryTiles.TryGetValue(selectedItemId,out var focus))root.schedule.Execute(focus.Focus);
    }

    // Details overlay: blocks interaction with the grid while open.
    bool detailsOpen=!string.IsNullOrEmpty(session.DetailItemId);
    inventoryDetails.style.display=detailsOpen?DisplayStyle.Flex:DisplayStyle.None;
    inventoryScroll?.SetEnabled(!detailsOpen);
    inventoryGrid?.SetEnabled(!detailsOpen);
    if(detailsOpen)
    {
     var item=session.catalog.items.FirstOrDefault(i=>i!=null&&i.id==session.DetailItemId);
     int quantity=session.Shop.Quantity(session.DetailItemId);
     detailsTitle.text=item!=null?item.name:"Item details";
     detailsQuantity.text=$"{quantity} carried";
     detailsPrices.text=item!=null&&!item.excludeFromTrade?$"Basic General list price - Buy {item.buyPrice} cr / Sell {item.sellPrice} cr":"";
     detailsDescription.text=item!=null&& !string.IsNullOrWhiteSpace(item.description)?item.description:"No description recorded.";
     if(crafting?.Model!=null&&item!=null&&crafting.Model.KnownRecipes.Contains("recipe_grip_stabilised_pistol")&&item.id!="grip_stabilised_pistol"&&new[]{"droid_servo_damaged","scrap_alloy","nanite_residue"}.Contains(item.id))detailsDescription.text+="\n\nKnown uses: Stabilised Pistol Grip (Field fabricator)";
     SetItemIcon(detailsIcon,session.DetailItemId);
     if(lastDetailId!=session.DetailItemId){lastDetailId=session.DetailItemId;root.schedule.Execute(()=>detailsClose?.Focus());}
     if(footerRight!=null)footerRight.text="Esc · Close details     Tab · Close pack";
    }
    else
    {
     if(lastDetailId!=null){lastDetailId=null;root.schedule.Execute(()=>{if(selectedItemId!=null&&inventoryTiles.TryGetValue(selectedItemId,out var b))b.Focus();});}
     if(footerRight!=null)footerRight.text="Arrows · Choose     Enter / Shift+click · Inspect     Tab / Esc · Close";
    }
   }
   if(session.State==CityState.Notes){Text("modal-title","City notes");Text("modal-subtitle","Field journal · Colony district");Text("panel-text",session.Objective+"\n\n"+$"Conversations {session.Spoken.Count}/4 · Flask {(session.boughtFlask?"acquired":"needed")} · Scrap {(session.soldScrap?"sold":"to sell")} · Link {(session.linked?"established":"pending")}"+"\n\n"+session.catalog.notes);}
   if(session.State==CityState.Credits){Text("modal-title","Credits and licences");Text("modal-subtitle","Athen Hill · An original colony city homage");Text("panel-text",session.catalog.credits?session.catalog.credits.text:"Credits unavailable.");}
   if(previous!=session.State)
   {
    previous=session.State;
    root.Q<ScrollView>("modal-scroll").scrollOffset=Vector2.zero;
    if(modal)
    {
     // Default modal focus goes to the close/primary button, except Inventory.
     // Inventory manages its own focus (grid tile or details-close) so Enter inspects items
     // rather than accidentally closing the modal.
     if(session.State==CityState.Inventory)
     {
      // If the pack is empty there is no tile focus target, so fall back to Close.
      if(inventoryIds.Count==0)root.schedule.Execute(()=>root.Q<Button>("close").Focus());
     }
     else
     {
      root.schedule.Execute(()=>root.Q<Button>(session.State==CityState.MainMenu?"start-game":session.State==CityState.Dialogue?"choice0":session.State==CityState.Fabricator?"fabricator-craft":"close").Focus());
     }
    }
    else root.focusController?.focusedElement?.Blur();
   }
  }
  void LateUpdate()
  {
   if(root==null||root.panel==null)return;
   if(PopupOpen())lastPopupFrame=Time.frameCount;
   if(windowWidth!=Screen.width||windowHeight!=Screen.height)UpdateWindowSize();
   UpdateCompass();
   var keyboard=Keyboard.current;
   if(keyboard!=null)for(int i=1;i<=6;i++)if(keyboard[(Key)((int)Key.Digit1+i-1)].wasPressedThisFrame)SelectSlot(i);
   bool tunnel=session.State==CityState.Grid&&session.GridProgress<1&&!session.reducedMotion;
   Show("tunnel",tunnel);
   if(tunnel)for(int i=0;i<4;i++){var ring=root.Q("tunnel-ring"+i);float phase=Mathf.Repeat(session.GridProgress*tunnelSpeed+i*.25f,1);float size=20+phase*480;ring.style.width=Length.Percent(size);ring.style.height=Length.Percent(size);ring.style.left=Length.Percent(50-size/2);ring.style.top=Length.Percent(50-size/2);ring.style.opacity=1-phase;}
   string prompt=session.Prompt;Show("interaction",!string.IsNullOrEmpty(prompt));root.Q<Button>("interaction").text=prompt;
   foreach(var pair in tags)
   {
    var world=pair.Key.transform.position+Vector3.up*2.15f;var p=worldCamera.WorldToViewportPoint(world);
    bool visible=session.State==CityState.Play&&p.z>0&&p.x>0&&p.x<1&&p.y>0&&p.y<1&&Vector3.Distance(world,session.player.transform.position)<34;
    pair.Value.style.display=visible?DisplayStyle.Flex:DisplayStyle.None;
    if(visible){var point=RuntimePanelUtils.CameraTransformWorldToPanel(root.panel,world,worldCamera);pair.Value.style.left=point.x-28;pair.Value.style.top=point.y-30;}
   }
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
