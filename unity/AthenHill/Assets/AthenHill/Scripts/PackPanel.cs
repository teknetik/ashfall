using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;
namespace AthenHill
{
 // Ashfall field pack: compact item cells, immediate adjacent inspection, real slot and weight limits.
 // Loadout tabs expose an anatomical implant/armour map; the separate render pane follows the selected
 // weapon or character. Implant inspection is strictly 2D. Grid arrows and search remain usable while inspecting.
 public sealed class PackPanel
 {
  public enum Tab { Items, Schematics }
  const string ItemPrefix="inv-",SchematicPrefix="sch-",SlotPrefix="slot-",Sidearm="sidearm";
  /// Grid rows are always completed with empty cells, and never fewer than this many cells are drawn.
  public const int MinimumCells=24;
  static readonly string[] rarityClasses={"rarity-common","rarity-uncommon","rarity-rare"};
  static readonly Dictionary<RecipeGroup,string> groupChips=new Dictionary<RecipeGroup,string>{{RecipeGroup.Component,"Components"},{RecipeGroup.MarkI,"Mark I"},{RecipeGroup.MarkII,"Mark II"},{RecipeGroup.Weapon,"Weapons"},{RecipeGroup.WeaponMod,"Weapon mods"}};

  readonly VisualElement root,grid,empty,overview,overviewIcon,details,detailsIcon,filters,facts,stats,previewCol,previewView,previewFallback,progressFill,searchBox;
  readonly ScrollView scroll;
  readonly Label overviewName,overviewQuantity,overviewDescription,detailsTitle,detailsQuantity,detailsPrices,detailsDescription,emptyTitle,emptySubtitle,filterName,summary,credit,progressLabel,progressValue,searchPlaceholder,previewHint;
  readonly Button detailsClose,tabItems,tabSchematics;
  readonly TextField search;
  readonly GameSession session;
  readonly CraftingSession crafting;
  readonly CharacterPreview preview;
  readonly CityTimeOfDay clock;
  readonly CharacterLoadoutPanel characterPanel;
  readonly HashSet<string> iconClasses;
  readonly Dictionary<string,Button> tiles=new Dictionary<string,Button>();
  readonly List<string> keys=new List<string>();
  readonly List<Button> chips=new List<Button>();
  readonly Dictionary<string,VisualElement> slotCells=new Dictionary<string,VisualElement>();
  readonly Dictionary<string,Label> factValues=new Dictionary<string,Label>();
  readonly List<(StatLabel label,Label value,Label delta)> statRows=new List<(StatLabel,Label,Label)>();
  VisualElement vitalityFill,nanoFill,pistolHeading,pistolNote,slotCapacityFill,weightCapacityFill;
  Label slotCapacityText,weightCapacityText,capacityHelp;
  Label vitalityValue,nanoValue;
  IVisualElementScheduledItem live;
  string itemFilter="all",schematicFilter="all",searchText="",selectedItem,selectedSchematic,hoverKey,lastDetailId,signature,chipsFor;
  bool open,built,builtWithModel;
  int dragPointer=-1;float dragX;

  public Tab ActiveTab {get;private set;}
  public string SearchText=>searchText;
  public string Filter=>ActiveTab==Tab.Items?itemFilter:schematicFilter;
  /// Tile names in grid order (inv-<item id> or sch-<recipe id>).
  public IReadOnlyList<string> VisibleKeys=>keys;
  public string SelectedKey=>ActiveTab==Tab.Items?(selectedItem!=null?ItemPrefix+selectedItem:null):(selectedSchematic!=null?SchematicPrefix+selectedSchematic:null);
  public bool DetailsOpen=>!string.IsNullOrEmpty(session.DetailItemId);
  CraftingModel Model=>crafting?crafting.Model:null;
  PlayerCombat Combat=>crafting?crafting.combat:null;

  public PackPanel(VisualElement root,GameSession session,CraftingSession crafting,CharacterPreview preview,HashSet<string> iconClasses)
  {
   this.root=root;this.session=session;this.crafting=crafting;this.preview=preview;this.iconClasses=iconClasses;
   clock=UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
   grid=root.Q("inventory-grid");empty=root.Q("inventory-empty");scroll=root.Q<ScrollView>("inventory-scroll");
   overview=root.Q("inventory-overview");overviewIcon=root.Q("inventory-overview-icon");
   overviewName=root.Q<Label>("inventory-overview-name");overviewQuantity=root.Q<Label>("inventory-overview-quantity");overviewDescription=root.Q<Label>("inventory-overview-description");
   details=root.Q("inventory-details");detailsIcon=root.Q("details-icon");detailsTitle=root.Q<Label>("details-title");detailsQuantity=root.Q<Label>("details-quantity");
   detailsPrices=root.Q<Label>("details-prices");detailsDescription=root.Q<Label>("details-description");detailsClose=root.Q<Button>("details-close");
   emptyTitle=root.Q<Label>("inventory-empty-title");emptySubtitle=root.Q<Label>("inventory-empty-subtitle");
   filters=root.Q("pack-filters");filterName=root.Q<Label>("pack-filter-name");summary=root.Q<Label>("pack-summary");credit=root.Q<Label>("pack-credit");
   tabItems=root.Q<Button>("pack-tab-items");tabSchematics=root.Q<Button>("pack-tab-schematics");
   search=root.Q<TextField>("pack-search");searchBox=search?.parent;searchPlaceholder=root.Q<Label>("pack-search-placeholder");
   facts=root.Q("colonist-facts");stats=root.Q("you-stats");progressFill=root.Q("you-progress-fill");progressLabel=root.Q<Label>("you-progress-label");progressValue=root.Q<Label>("you-progress-value");
   previewCol=root.Q("preview-col");previewView=root.Q("preview-view");previewFallback=root.Q("preview-fallback");previewHint=root.Q<Label>("preview-hint");

   tabItems.clicked+=()=>SetTab(Tab.Items);tabSchematics.clicked+=()=>SetTab(Tab.Schematics);
   search.RegisterValueChangedCallback(e=>ApplySearch(e.newValue));
   search.RegisterCallback<FocusInEvent>(_=>searchBox?.AddToClassList("focused"));
   search.RegisterCallback<FocusOutEvent>(_=>searchBox?.RemoveFromClassList("focused"));
   search.RegisterCallback<KeyDownEvent>(e=>{if(e.keyCode==KeyCode.Return||e.keyCode==KeyCode.KeypadEnter){FocusGrid();e.StopPropagation();}},TrickleDown.TrickleDown);
   // Keyboard: every navigation event inside the pack column goes through one handler (grid, chips, tabs, search).
   root.Q("pack-col").RegisterCallback<NavigationMoveEvent>(Navigate,TrickleDown.TrickleDown);
   previewView.RegisterCallback<PointerDownEvent>(DragStart);
   previewView.RegisterCallback<PointerMoveEvent>(DragMove);
   previewView.RegisterCallback<PointerUpEvent>(DragEnd);
   previewView.RegisterCallback<PointerCaptureOutEvent>(_=>dragPointer=-1);
   previewView.RegisterCallback<ClickEvent>(e=>{if(e.clickCount==2&&preview)preview.Yaw=0;});
   characterPanel=new CharacterLoadoutPanel(root,session,crafting,()=>selectedItem,Refresh);
   BuildCapacity();
  }
  /// Slots, facts and stat rows come from the crafting data, which the crafting session loads after the HUD starts.
  void EnsureBuilt()
  {
   bool withModel=Model!=null;
   if(built&&builtWithModel==withModel)return;
   built=true;builtWithModel=withModel;
   BuildLoadout();BuildStats();
   tabSchematics.style.display=withModel?DisplayStyle.Flex:DisplayStyle.None;
   if(!withModel&&ActiveTab==Tab.Schematics)ActiveTab=Tab.Items;
  }

  // ------------------------------------------------------------------ lifecycle
  /// The pack opened: focus the selected cell (or Close when there is none), start the colonist view and live stats.
  public void Opened()
  {
   open=true;signature=null;
   if(preview)preview.Yaw=0; // the colonist faces the player each time the pack opens
   Refresh();
   root.schedule.Execute(()=>{if(!FocusSelected())root.Q<Button>("close")?.Focus();});
   live??=root.schedule.Execute(UpdateLive).Every(200);
   live.Resume();
  }
  public void Closed()
  {
   open=false;hoverKey=null;live?.Pause();
   characterPanel.CancelDrag();
   if(dragPointer>=0&&previewView.HasPointerCapture(dragPointer))previewView.ReleasePointer(dragPointer);
   dragPointer=-1;
   if(preview)preview.SetActive(false);
  }

  public void Refresh()
  {
   if(session==null||session.Shop==null||session.catalog==null)return;
   EnsureBuilt();
   credit.text=$"{session.Shop.Credits} cr";
   tabItems.EnableInClassList("active-tab",ActiveTab==Tab.Items);tabSchematics.EnableInClassList("active-tab",ActiveTab==Tab.Schematics);
   if(chipsFor!=ActiveTab.ToString())BuildChips();
   foreach(var chip in chips)chip.EnableInClassList("active-chip",(string)chip.userData==Filter);
   RebuildGrid();
   UpdateOverview();
   UpdateCapacity();
   UpdateDetails();
   UpdateYou();
   characterPanel.Refresh();
   RefreshPreview();
  }
  void BuildCapacity()
  {
   var box=root.Q("pack-capacity");if(box==null)return;
   (Label text,VisualElement fill) Meter(string name)
   {
    var cell=new VisualElement();cell.AddToClassList("pack-capacity-meter");
    var text=new Label{name=name};text.AddToClassList("pack-capacity-value");cell.Add(text);
    var track=new VisualElement();track.AddToClassList("pack-capacity-track");
    var fill=new VisualElement();fill.AddToClassList("pack-capacity-fill");track.Add(fill);cell.Add(track);box.Add(cell);return(text,fill);
   }
   var slots=Meter("pack-slot-capacity");slotCapacityText=slots.text;slotCapacityFill=slots.fill;
   var weight=Meter("pack-weight-capacity");weightCapacityText=weight.text;weightCapacityFill=weight.fill;
   capacityHelp=new Label("Limited by slots and weight.");capacityHelp.AddToClassList("pack-capacity-help");box.Add(capacityHelp);
  }
  void UpdateCapacity()
  {
   if(slotCapacityText==null)return;
   var character=session.Character;
   int used=character?.PackSlotsUsed??session.Shop.Carried.Count();int max=character?.PackSlotCapacity??0;
   slotCapacityText.text=max>0?$"SLOTS  {used} / {max}":$"SLOTS  {used}";
   float weight=character?.CarryWeight??session.Shop.Carried.Sum(x=>(session.Shop.Spec(x.Key)?.weightKg??0)*x.Value),limit=character?.CarryCapacity??0;
   weightCapacityText.text=limit>0?$"WEIGHT  {weight:0.0} / {limit:0.#} kg":$"WEIGHT  {weight:0.0} kg";
   slotCapacityFill.style.width=Length.Percent(max>0?Mathf.Clamp01(used/(float)max)*100:0);
   weightCapacityFill.style.width=Length.Percent(limit>0?Mathf.Clamp01(weight/limit)*100:0);
   weightCapacityFill.EnableInClassList("capacity-full",limit>0&&weight>=limit);slotCapacityFill.EnableInClassList("capacity-full",max>0&&used>=max);
   capacityHelp.text=character!=null?$"One stack per slot · pack {character.PackWeight:0.0} / {character.StorageCapacity:0.#} kg":"One item stack occupies one slot.";
  }
  void RefreshPreview()
  {
   bool wants=characterPanel.WantsPreview;
   bool weapon=characterPanel.CurrentSection=="PRIMARY"||characterPanel.CurrentSection=="SECONDARY";
   string item=characterPanel.PreviewWeaponItem;
   bool available=preview;
   if(preview)
   {
    if(weapon)
    {
     var definition=Model?.FindWeapon(item);
     GameObject source=definition?.previewPrefab;
     if(!source&&item=="field_rifle")source=Resources.Load<GameObject>("WeaponPreviews/FieldRifle");
     if(!source&&item=="scrap_pistol"&&Combat)source=Combat.heldPistol;
     available=preview.SetWeapon(source,definition!=null?Model.GetLoadout(definition.id):null);
    }
    else preview.ShowCharacter();
    preview.SetActive(open&&wants&&available);
    if(preview.Active&&preview.Texture)previewView.style.backgroundImage=new StyleBackground(Background.FromRenderTexture(preview.Texture));
    else previewView.style.backgroundImage=StyleKeyword.None;
   }
   previewCol.style.display=wants?DisplayStyle.Flex:DisplayStyle.None;
   previewFallback.style.display=preview&&preview.Active?DisplayStyle.None:DisplayStyle.Flex;
   previewHint.style.display=DisplayStyle.Flex;
   previewHint.text=preview&&preview.Active?"Drag to rotate":weapon?(item==null?"Equip a weapon to inspect":"Preview model unavailable"):"Character preview unavailable";
   var name=root.Q<Label>("preview-name");if(name!=null)name.text=weapon?(session.Shop.Spec(item)?.name??"NO WEAPON"):"COLONIST";

  }

  public void SetTab(Tab tab)
  {
   if(ActiveTab==tab)return;
   ActiveTab=tab;hoverKey=null;signature=null;
   if(DetailsOpen)session.CloseItemDetails();
   Refresh();
  }
  public void SetFilter(string id)
  {
   if(ActiveTab==Tab.Items)itemFilter=InventoryView.FindCategory(id).id;else schematicFilter=id??"all";
   signature=null;Refresh();
  }
  public void SetSearch(string text){search.SetValueWithoutNotify(text??"");ApplySearch(text);}
  void ApplySearch(string text)
  {
   searchText=text??"";
   searchPlaceholder.style.display=string.IsNullOrEmpty(searchText)?DisplayStyle.Flex:DisplayStyle.None;
   Refresh();
  }

  // ------------------------------------------------------------------ grid
  sealed class Entry {public string key,name,icon,count;public ItemRarity rarity;public bool ready,shortParts;}
  List<Entry> Entries()
  {
   var list=new List<Entry>();
   if(ActiveTab==Tab.Items)
   {
    foreach(var item in InventoryView.Items(session.catalog.items,session.Shop,InventoryView.FindCategory(itemFilter),searchText))
     list.Add(new Entry{key=ItemPrefix+item.id,name=item.name,icon=item.icon,count=$"×{session.Shop.Quantity(item.id)}",rarity=item.rarity});
   }
   else if(Model!=null)
   {
    foreach(var r in KnownSchematics())
    {
     if(schematicFilter!="all"&&r.group.ToString()!=schematicFilter)continue;
     var output=Model.Item(r.outputItemId);
     if(!InventoryView.Matches(r.name,searchText))continue;
     bool ready=Ready(r);
     list.Add(new Entry{key=SchematicPrefix+r.id,name=r.name,icon=output?.icon,count=r.outputQuantity>1?$"×{r.outputQuantity}":"",rarity=output?.rarity??ItemRarity.Common,ready=ready,shortParts=!ready});
    }
   }
   return list;
  }
  IEnumerable<CraftRecipe> KnownSchematics()=>Model==null?Enumerable.Empty<CraftRecipe>():Model.Data.recipes.Where(r=>r!=null&&Model.Knows(r.id)).OrderBy(r=>r.group);
  bool Ready(CraftRecipe r)=>r.inputs==null||r.inputs.All(i=>Model.Available(i)>=i.quantity);

  void RebuildGrid()
  {
   var entries=Entries();
   // Pack selection follows the visible cells; a filtered-out selection moves to the first visible cell.
   string sel=ActiveTab==Tab.Items?selectedItem:selectedSchematic;
   string prefix=ActiveTab==Tab.Items?ItemPrefix:SchematicPrefix;
   if(sel==null||!entries.Any(e=>e.key==prefix+sel))sel=entries.Count>0?entries[0].key.Substring(prefix.Length):null;
   if(ActiveTab==Tab.Items)selectedItem=sel;else selectedSchematic=sel;
   string sig=ActiveTab+"|"+string.Join(";",entries.Select(e=>e.key+":"+e.count+":"+e.ready));
   if(sig!=signature)
   {
    signature=sig;
    var focused=root.focusController?.focusedElement as VisualElement;
    string focusKey=focused!=null&&tiles.ContainsValue(focused as Button)?focused.name:null;
    tiles.Clear();keys.Clear();grid.Clear();
    foreach(var e in entries)grid.Add(Tile(e));
    int columns=WidthColumns(),cells=Mathf.Max(MinimumCells,Mathf.CeilToInt(entries.Count/(float)columns)*columns);
    for(int i=entries.Count;i<cells;i++){var c=new VisualElement{pickingMode=PickingMode.Ignore};c.AddToClassList("pack-cell");grid.Add(c);}
    if(focusKey!=null)root.schedule.Execute(()=>{if(!(tiles.TryGetValue(focusKey,out var b)&&Focus(b)))FocusSelected();});
   }
   foreach(var pair in tiles)pair.Value.EnableInClassList("selected",pair.Key==SelectedKey);
   bool none=entries.Count==0;
   empty.style.display=none?DisplayStyle.Flex:DisplayStyle.None;
   bool packEmpty=ActiveTab==Tab.Items?!InventoryView.Items(session.catalog.items,session.Shop).Any():!KnownSchematics().Any();
   emptyTitle.text=ActiveTab==Tab.Items?packEmpty?"Your field pack is empty.":"Nothing here matches.":packEmpty?"No schematics known yet.":"No schematics match.";
   emptySubtitle.text=ActiveTab==Tab.Items?packEmpty?"Supplies you acquire will appear here.":"Try another filter or clear the search.":packEmpty?"Salvage and field orders reveal schematics.":"Try another filter or clear the search.";
   grid.style.display=none&&packEmpty?DisplayStyle.None:DisplayStyle.Flex;
   // Footer: the filter heading and plain counts.
   if(ActiveTab==Tab.Items)
   {
    var cat=InventoryView.FindCategory(itemFilter);
    filterName.text=cat.id=="all"?"ALL ITEMS":cat.label.ToUpperInvariant();
    var carried=InventoryView.Items(session.catalog.items,session.Shop).ToList();
    summary.text=$"{entries.Count} of {carried.Count} kinds · {carried.Sum(i=>session.Shop.Quantity(i.id))} items carried";
   }
   else
   {
    filterName.text=schematicFilter=="all"?"ALL SCHEMATICS":Model!=null&&Enum.TryParse(schematicFilter,out RecipeGroup g)?Model.Data.GroupName(g).ToUpperInvariant():schematicFilter;
    int known=KnownSchematics().Count(),total=Model!=null?Model.Data.recipes.Length:0;
    summary.text=$"{known} of {total} known · {KnownSchematics().Count(Ready)} with parts on hand";
   }
  }

  Button Tile(Entry e)
  {
   var tile=new Button{name=e.key,tooltip=e.name+(string.IsNullOrEmpty(e.count)?"":" · "+e.count)};
   tile.AddToClassList("inventory-tile");
   if(e.rarity!=ItemRarity.Common)tile.AddToClassList(e.rarity==ItemRarity.Rare?"tile-rare":"tile-uncommon");
   tile.EnableInClassList("ready",ActiveTab==Tab.Schematics&&e.ready);tile.EnableInClassList("short",e.shortParts);
   var icon=new VisualElement{pickingMode=PickingMode.Ignore};icon.AddToClassList("inventory-tile-icon");SetIcon(icon,e.icon);tile.Add(icon);
   if(!string.IsNullOrEmpty(e.count)){var qty=new Label(e.count){pickingMode=PickingMode.Ignore};qty.AddToClassList("inventory-tile-qty");tile.Add(qty);}
   var name=new Label(e.name){pickingMode=PickingMode.Ignore};name.AddToClassList("inventory-tile-name");tile.Add(name);
   var bar=new VisualElement{pickingMode=PickingMode.Ignore};bar.AddToClassList("inventory-tile-bar");tile.Add(bar);
   string key=e.key;
   tile.RegisterCallback<PointerEnterEvent>(_=>{hoverKey=key;UpdateOverview();});
   tile.RegisterCallback<PointerLeaveEvent>(_=>{if(hoverKey==key)hoverKey=null;UpdateOverview();});
   tile.RegisterCallback<FocusInEvent>(_=>Select(key));
   tile.RegisterCallback<ClickEvent>(ev=>Select(key));
   tile.RegisterCallback<KeyDownEvent>(ev=>OnTileKey(ev,key));
   tiles[key]=tile;keys.Add(key);
   if(key.StartsWith(ItemPrefix))characterPanel.BindInventory(tile,key.Substring(ItemPrefix.Length));
   return tile;
  }
  void Select(string key)
  {
   if(key.StartsWith(ItemPrefix))selectedItem=key.Substring(ItemPrefix.Length);else if(key.StartsWith(SchematicPrefix))selectedSchematic=key.Substring(SchematicPrefix.Length);
   foreach(var pair in tiles)pair.Value.EnableInClassList("selected",pair.Key==key);
   if(DetailsOpen)session.CloseItemDetails();
   UpdateOverview();UpdateDetails();characterPanel.Refresh();
  }
  void OnTileKey(KeyDownEvent ev,string key)
  {
   if(ev.keyCode!=KeyCode.Return&&ev.keyCode!=KeyCode.KeypadEnter)return;
   // Inspection is an adjacent selection, so Enter must not create a second modal state to dismiss.
   Select(key);ev.StopPropagation();
  }
  /// Grid columns, read from the laid-out cells (the grid wraps to its width); from the width before layout.
  public int Columns()
  {
   var cells=new List<Rect>();foreach(var child in grid.Children())cells.Add(child.layout);
   bool laidOut=cells.Count>1&&!float.IsNaN(cells[0].width)&&cells[0].width>0;
   return laidOut?UiNavigation.Columns(cells):WidthColumns();
  }
  /// Cells per row for the grid's width (64 px cells, 5 px gutters); the authored width before the first layout.
  int WidthColumns(){float w=grid.resolvedStyle.width;if(float.IsNaN(w)||w<=0)w=414;return Mathf.Max(1,Mathf.FloorToInt((w+.5f)/69f));}

  // ------------------------------------------------------------------ keyboard
  bool Focus(VisualElement v){if(v==null||v.panel==null||!v.enabledInHierarchy)return false;v.Focus();return true;}
  bool FocusSelected()=>SelectedKey!=null&&tiles.TryGetValue(SelectedKey,out var b)&&Focus(b);
  void FocusGrid(){if(!FocusSelected()&&keys.Count>0)Focus(tiles[keys[0]]);}
  Button ActiveChip()=>chips.FirstOrDefault(c=>(string)c.userData==Filter)??chips.FirstOrDefault();
  Button ActiveTabButton()=>ActiveTab==Tab.Items?tabItems:tabSchematics;
  void Navigate(NavigationMoveEvent e)
  {
   if(session.State!=CityState.Inventory||!UiNavigation.IsArrow(e.direction))return;
   var focused=root.focusController?.focusedElement as VisualElement;
   if(focused==null)return;
   var dir=e.direction;
   if(search.Contains(focused)||focused==search)
   {
    // WASD type into the box; only the arrow keys leave it (Left/Right stay with the text cursor).
    var k=Keyboard.current;
    if(k!=null&&k.upArrowKey.isPressed&&dir==NavigationMoveEvent.Direction.Up)Focus(ActiveTabButton());
    else if(k!=null&&k.downArrowKey.isPressed&&dir==NavigationMoveEvent.Direction.Down)FocusGrid();
    UiNavigation.Consume(e,root);return;
   }
   int chip=chips.IndexOf(focused as Button);
   if(chip>=0)
   {
    if(dir==NavigationMoveEvent.Direction.Left){if(chip>0)Focus(chips[chip-1]);else Focus(search);}
    else if(dir==NavigationMoveEvent.Direction.Right){if(chip<chips.Count-1)Focus(chips[chip+1]);}
    else if(dir==NavigationMoveEvent.Direction.Up)Focus(ActiveTabButton());
    else FocusGrid();
    UiNavigation.Consume(e,root);return;
   }
   if(focused==tabItems||focused==tabSchematics)
   {
    var other=focused==tabItems?tabSchematics:tabItems;
    if(dir==NavigationMoveEvent.Direction.Down)Focus(ActiveChip());
    else if((dir==NavigationMoveEvent.Direction.Right&&focused==tabItems||dir==NavigationMoveEvent.Direction.Left&&focused==tabSchematics)&&other.resolvedStyle.display!=DisplayStyle.None)Focus(other);
    UiNavigation.Consume(e,root);return;
   }
   int index=keys.IndexOf(focused.name);
   if(index<0||!tiles.ContainsKey(focused.name))return;
   int columns=Columns();
   if(dir==NavigationMoveEvent.Direction.Up&&index<columns){Focus(ActiveChip());UiNavigation.Consume(e,root);return;}
   int target=UiNavigation.GridStep(index,keys.Count,columns,dir);
   if(target>=0)Focus(tiles[keys[target]]);
   UiNavigation.Consume(e,root);
  }

  void BuildChips()
  {
   chipsFor=ActiveTab.ToString();chips.Clear();filters.Clear();
   var defs=new List<(string id,string label)>();
   if(ActiveTab==Tab.Items)defs.AddRange(InventoryView.Categories.Select(c=>(c.id,c.label)));
   else{defs.Add(("all","All"));if(Model!=null)foreach(RecipeGroup g in Enum.GetValues(typeof(RecipeGroup)))if(Model.Data.recipes.Any(r=>r!=null&&r.group==g))defs.Add((g.ToString(),groupChips.TryGetValue(g,out var s)?s:g.ToString()));}
   foreach(var (id,label) in defs)
   {
    string chipId=id;
    var chip=new Button(()=>SetFilter(chipId)){name="pack-filter-"+id,text=label.ToUpperInvariant(),userData=id};
    chip.AddToClassList("pack-chip");filters.Add(chip);chips.Add(chip);
   }
  }

  // ------------------------------------------------------------------ selected item, schematic or slot
  void UpdateOverview()
  {
   string key=hoverKey??SelectedKey;
   foreach(var pair in slotCells)pair.Value.EnableInClassList("selected",hoverKey==SlotPrefix+pair.Key);
   if(key!=null&&key.StartsWith(SlotPrefix)){SlotOverview(key.Substring(SlotPrefix.Length));return;}
   if(key!=null&&key.StartsWith(SchematicPrefix)&&Model!=null)
   {
    var r=Model.Recipe(key.Substring(SchematicPrefix.Length));
    if(r!=null)
    {
     var output=Model.Item(r.outputItemId);
     var parts=r.inputs==null?"":string.Join(" · ",r.inputs.Select(i=>$"{CraftingText.InputName(Model,i)} {Mathf.Min(Model.Available(i),99)}/{i.quantity}"));
     ShowOverview(r.name,output?.icon,output?.rarity??ItemRarity.Common,$"{Model.Data.GroupName(r.group).ToUpperInvariant()} · {(Ready(r)?"PARTS ON HAND":"PARTS SHORT")}",
      (parts.Length>0?"Parts: "+parts+"\n":"")+"Fabricate at "+CraftingText.Workbench+".");
     return;
    }
   }
   if(key!=null&&key.StartsWith(ItemPrefix))
   {
    var item=session.Shop.Spec(key.Substring(ItemPrefix.Length));
    if(item!=null)
    {
     int q=session.Shop.Quantity(item.id);
     ShowOverview(item.name,item.icon,item.rarity,$"{q} CARRIED{(item.maxStack>0?$" OF {item.maxStack}":"")} · {RarityName(item.rarity).ToUpperInvariant()}{Kind(item)}",
      string.IsNullOrWhiteSpace(item.description)?"No description recorded.":item.description);
     return;
    }
   }
   ShowOverview(ActiveTab==Tab.Items?"No item selected.":"No schematic selected.",null,ItemRarity.Common,"","",false);
  }
  static string Kind(ItemSpec item){var c=InventoryView.Categories.FirstOrDefault(x=>x.tag!=null&&item.HasTag(x.tag));return c!=null?" · "+c.label.ToUpperInvariant():"";}
  void ShowOverview(string name,string icon,ItemRarity rarity,string sub,string description,bool showIcon=true)
  {
   overviewName.text=name;overviewQuantity.text=sub;overviewDescription.text=description;
   foreach(var c in rarityClasses)overviewName.RemoveFromClassList(c);
   if(rarity!=ItemRarity.Common)overviewName.AddToClassList(rarityClasses[(int)rarity]);
   SetIcon(overviewIcon,icon,!showIcon);
  }
  void SlotOverview(string slot)
  {
   var combat=Combat;var model=Model;
   if(slot==Sidearm)
   {
    if(combat&&combat.hasPistol&&model!=null)
    {
     int fitted=model.Loadout.FittedMods.Count(),total=model.Loadout.Slots.Count;
     ShowOverview(model.Loadout.WeaponName,"pistol-icon",ItemRarity.Common,$"SIDEARM · {fitted} OF {total} MODS FITTED","Nanite-fed scrap pistol. Its shots draw on nano. Mods are fitted at "+CraftingText.Workbench+".");
    }
    else ShowOverview("No sidearm",null,ItemRarity.Common,"SIDEARM · EMPTY","No sidearm carried.",false);
    return;
   }
   if(model==null)return;
   string slotName=model.Data.SlotName(slot);
   var id=model.Loadout.Fitted(slot);var item=id!=null?model.Item(id):null;
   if(item!=null)
   {
    var changes=CraftingText.StatChanges(model.Data,model.Loadout.Preview(slot,null),model.Loadout.Stats);
    ShowOverview(item.name,item.icon,item.rarity,$"{slotName.ToUpperInvariant()} MOD · FITTED · {RarityName(item.rarity).ToUpperInvariant()}",(string.IsNullOrWhiteSpace(item.description)?"":item.description+"\n")+(changes.Length>0?"Fitted: "+changes:""));
   }
   else ShowOverview($"Empty {slotName.ToLowerInvariant()} slot",null,ItemRarity.Common,$"{slotName.ToUpperInvariant()} MOD · EMPTY",combat&&combat.hasPistol?$"Fit a {slotName.ToLowerInvariant()} mod at "+CraftingText.Workbench+".":"No sidearm carried.",false);
  }
  static string RarityName(ItemRarity r)=>r==ItemRarity.Rare?"Rare":r==ItemRarity.Uncommon?"Uncommon":"Common";

  // ------------------------------------------------------------------ adjacent item details (click / keyboard selection)
  void UpdateDetails()
  {
   string detailId=session.DetailItemId??(ActiveTab==Tab.Items?selectedItem:null);
   bool detailsOpen=!string.IsNullOrEmpty(detailId);
   details.style.display=DisplayStyle.Flex;
   detailsClose.style.display=DisplayStyle.None;
   scroll.SetEnabled(true);grid.SetEnabled(true);
   if(detailsOpen)
   {
    var item=session.catalog.items.FirstOrDefault(i=>i!=null&&i.id==detailId);
    int quantity=session.Shop.Quantity(detailId);
    detailsTitle.text=item!=null?item.name:"Item details";
    detailsQuantity.text=item!=null?$"{quantity} carried · {RarityName(item.rarity)}":$"{quantity} carried";
    foreach(var c in rarityClasses)detailsTitle.RemoveFromClassList(c);
    if(item!=null&&item.rarity!=ItemRarity.Common)detailsTitle.AddToClassList(rarityClasses[(int)item.rarity]);
    detailsPrices.text=item!=null&&!item.excludeFromTrade?item.sellOnly?$"Brann at Salvage and Mira at Basic General buy this for {item.sellPrice} cr":$"Basic General list price - Buy {item.buyPrice} cr / Sell {item.sellPrice} cr":item!=null&&item.rarity==ItemRarity.Rare?"Rare part · neither Mira nor Brann will trade it":"";
    detailsDescription.text=item!=null&&!string.IsNullOrWhiteSpace(item.description)?item.description:"No description recorded.";
    if(item!=null){var equipment=characterPanel.DescribeItem(item.id);if(equipment.Length>0)detailsDescription.text+="\n\n"+equipment;}
    if(Model!=null&&item!=null){var uses=KnownUses(Model,item);if(uses.Length>0)detailsDescription.text+="\n\nKnown uses: "+uses+" ("+CraftingText.WorkbenchName+")";}
    SetIcon(detailsIcon,item?.icon);
    lastDetailId=detailId;
    string stack=item!=null&&item.maxStack>0?$"{quantity} / {item.maxStack}":$"{quantity} · no stack limit";
    var measured=$"Weight   {item?.weightKg??0:0.00} kg each\nStack   {stack}\nSlot size   1 stack";
    detailsQuantity.text+="\n"+measured;
   }
   else
   {
    if(ActiveTab==Tab.Schematics&&Model!=null&&selectedSchematic!=null)
    {
     var recipe=Model.Recipe(selectedSchematic);
     if(recipe!=null)
     {
      var output=Model.Item(recipe.outputItemId);detailsTitle.text=recipe.name;detailsQuantity.text=Ready(recipe)?"PARTS ON HAND":"PARTS SHORT";detailsPrices.text="Fabricate at Brann's workbench";
      detailsDescription.text=(output?.description??"")+"\n\n"+string.Join("\n",(recipe.inputs??Array.Empty<CraftIngredient>()).Select(i=>$"{CraftingText.InputName(Model,i)}   {Model.Available(i)} / {i.quantity}"));SetIcon(detailsIcon,output?.icon);return;
     }
    }
    lastDetailId=null;detailsTitle.text=ActiveTab==Tab.Schematics?"SCHEMATICS":"ITEM DETAILS";detailsQuantity.text="";detailsPrices.text="";
    detailsDescription.text=ActiveTab==Tab.Schematics?"Select a schematic to see its parts in the pack. Fabrication takes place at Brann's workbench in Salvage.":"Select an item to inspect its weight, value, requirements and uses.";
    SetIcon(detailsIcon,null,true);
   }
  }
  /// Known schematics that consume this item, directly or through one of its tags.
  static string KnownUses(CraftingModel model,ItemSpec item)=>string.Join(", ",model.Data.recipes.Where(r=>model.Knows(r.id)&&r.outputItemId!=item.id&&r.inputs!=null&&r.inputs.Any(i=>i.kind=="item"?i.id==item.id:item.HasTag(i.id))).Select(r=>r.name));

  // ------------------------------------------------------------------ YOU: loadout, colonist card, progress, stats
  void BuildLoadout()
  {
   var slots=new List<string>{Sidearm};
   if(Model!=null)slots.AddRange(Model.Loadout.Slots);
   var left=root.Q("loadout-left");var right=root.Q("loadout-right");left.Clear();right.Clear();slotCells.Clear();
   int half=(slots.Count+1)/2;
   for(int i=0;i<slots.Count;i++)
   {
    string slot=slots[i];
    var box=new VisualElement{pickingMode=PickingMode.Ignore};box.AddToClassList("loadout-slot");
    var label=new Label(slot==Sidearm?"SIDEARM":Model.Data.SlotName(slot).ToUpperInvariant()){pickingMode=PickingMode.Ignore};label.AddToClassList("loadout-slot-label");box.Add(label);
    var cell=new VisualElement{name="pack-slot-"+slot,pickingMode=PickingMode.Position};cell.AddToClassList("loadout-cell");
    var icon=new VisualElement{pickingMode=PickingMode.Ignore};icon.AddToClassList("loadout-cell-icon");cell.Add(icon);
    var none=new Label("EMPTY"){pickingMode=PickingMode.Ignore};none.AddToClassList("loadout-cell-empty");cell.Add(none);
    var bar=new VisualElement{pickingMode=PickingMode.Ignore};bar.AddToClassList("inventory-tile-bar");cell.Add(bar);
    cell.RegisterCallback<PointerEnterEvent>(_=>{hoverKey=SlotPrefix+slot;UpdateOverview();});
    cell.RegisterCallback<PointerLeaveEvent>(_=>{if(hoverKey==SlotPrefix+slot)hoverKey=null;UpdateOverview();});
    box.Add(cell);(i<half?left:right).Add(box);slotCells[slot]=cell;
   }
   facts.Clear();factValues.Clear();
   foreach(var (id,label) in new[]{("location","LOCATION"),("time","TIME"),("credits","CREDITS"),("schematics","SCHEMATICS"),("mods","MODS FITTED"),("talks","CONVERSATIONS")})
   {
    if((id=="schematics"||id=="mods")&&Model==null)continue;
    if(id=="time"&&!clock)continue;
    var row=new VisualElement{pickingMode=PickingMode.Ignore};row.AddToClassList("colonist-fact");
    var l=new Label(label){pickingMode=PickingMode.Ignore};l.AddToClassList("colonist-fact-label");
    var v=new Label{name="colonist-"+id,pickingMode=PickingMode.Ignore};v.AddToClassList("colonist-fact-value");
    row.Add(l);row.Add(v);facts.Add(row);factValues[id]=v;
   }
  }
  void BuildStats()
  {
   stats.Clear();statRows.Clear();
   (VisualElement row,VisualElement fill,Label value) Vital(string name,string cls)
   {
    var row=new VisualElement{name="you-"+cls,pickingMode=PickingMode.Ignore};row.AddToClassList("you-stat");row.AddToClassList("vital");row.AddToClassList(cls);
    var line=new VisualElement{pickingMode=PickingMode.Ignore};line.AddToClassList("you-stat-line");
    var mark=new VisualElement{pickingMode=PickingMode.Ignore};mark.AddToClassList("you-stat-mark");
    var n=new Label(name){pickingMode=PickingMode.Ignore};n.AddToClassList("you-stat-name");
    var v=new Label{pickingMode=PickingMode.Ignore};v.AddToClassList("you-stat-value");
    line.Add(mark);line.Add(n);line.Add(v);row.Add(line);
    var track=new VisualElement{pickingMode=PickingMode.Ignore};track.AddToClassList("you-stat-track");
    var fill=new VisualElement{pickingMode=PickingMode.Ignore};fill.AddToClassList("you-stat-fill");track.Add(fill);row.Add(track);
    stats.Add(row);return (row,fill,v);
   }
   var vit=Vital("VITALITY","vitality");vitalityFill=vit.fill;vitalityValue=vit.value;
   var nano=Vital("NANO","nano");nanoFill=nano.fill;nanoValue=nano.value;
   pistolHeading=new VisualElement{pickingMode=PickingMode.Ignore};pistolHeading.AddToClassList("you-stat-heading");
   var ph=new Label(Model!=null?Model.Loadout.WeaponName.ToUpperInvariant():"SIDEARM"){pickingMode=PickingMode.Ignore};var pr=new Label("FITTED · VS BASE"){pickingMode=PickingMode.Ignore};
   pistolHeading.Add(ph);pistolHeading.Add(pr);stats.Add(pistolHeading);
   var grid2=new VisualElement{name="you-pistol-stats",pickingMode=PickingMode.Ignore};grid2.AddToClassList("you-stat-grid");stats.Add(grid2);
   if(Model!=null)foreach(var stat in Model.Data.statLabels??new StatLabel[0])
   {
    if(stat==null||WeaponStats.IndexOf(stat.stat)<0)continue;
    var row=new VisualElement{name="you-stat-"+stat.stat,pickingMode=PickingMode.Ignore};row.AddToClassList("you-stat");row.AddToClassList("you-stat-cell");
    var mark=new VisualElement{pickingMode=PickingMode.Ignore};mark.AddToClassList("you-stat-mark");
    var n=new Label(stat.label.ToUpperInvariant()){pickingMode=PickingMode.Ignore};n.AddToClassList("you-stat-name");
    var v=new Label{pickingMode=PickingMode.Ignore};v.AddToClassList("you-stat-value");
    var d=new Label{pickingMode=PickingMode.Ignore};d.AddToClassList("you-stat-delta");
    row.Add(mark);row.Add(n);row.Add(v);row.Add(d);grid2.Add(row);statRows.Add((stat,v,d));
   }
   pistolNote=new Label("No sidearm carried."){pickingMode=PickingMode.Ignore};pistolNote.AddToClassList("you-stat-note");stats.Add(pistolNote);
  }
  void UpdateYou()
  {
   var model=Model;var combat=Combat;
   bool pistol=combat&&combat.hasPistol&&model!=null;
   foreach(var pair in slotCells)
   {
    string icon=null;var rarity=ItemRarity.Common;
    if(pair.Key==Sidearm){if(combat&&combat.hasPistol)icon="pistol-icon";}
    else if(model!=null){var item=model.Item(model.Loadout.Fitted(pair.Key));if(item!=null){icon=item.icon;rarity=item.rarity;}}
    var cell=pair.Value;
    cell.EnableInClassList("empty",icon==null);
    cell.EnableInClassList("tile-uncommon",rarity==ItemRarity.Uncommon);cell.EnableInClassList("tile-rare",rarity==ItemRarity.Rare);
    var art=cell.Q(className:"loadout-cell-icon");art.style.display=icon!=null?DisplayStyle.Flex:DisplayStyle.None;if(icon!=null)SetIcon(art,icon);
    cell.Q<Label>(className:"loadout-cell-empty").style.display=icon==null?DisplayStyle.Flex:DisplayStyle.None;
    cell.Q(className:"inventory-tile-bar").style.display=icon!=null?DisplayStyle.Flex:DisplayStyle.None;
   }
   Fact("credits",$"{session.Shop.Credits} cr");
   Fact("talks",$"{session.Spoken.Count} / 4");
   if(model!=null){Fact("schematics",$"{model.KnownRecipes.Count} / {model.Data.recipes.Length}");Fact("mods",pistol?$"{model.Loadout.FittedMods.Count()} / {model.Loadout.Slots.Count}":"—");}
   // Progress: the field orders once they begin, the city visit before.
   var orders=session.GetComponent<FieldOrders>();
   if(orders&&orders.Ready&&orders.Progress.Started)
   {
    int n=orders.Progress.Data.orders.Length,done=Mathf.Min(orders.Progress.Index,n);
    progressLabel.text="FIELD ORDERS";progressValue.text=orders.Progress.FreePlay?$"{n} / {n} · Free hunting":$"{done} / {n}";
    progressFill.style.width=Length.Percent(n>0?100f*done/n:0);
   }
   else
   {
    int steps=(session.visitedHill?1:0)+session.Spoken.Count+(session.boughtFlask?1:0)+(session.soldScrap?1:0)+(session.linked?1:0);
    progressLabel.text="CITY VISIT";progressValue.text=$"{steps} / 8";progressFill.style.width=Length.Percent(100f*steps/8);
   }
   pistolHeading.style.display=pistol?DisplayStyle.Flex:DisplayStyle.None;
   root.Q("you-pistol-stats").style.display=pistol?DisplayStyle.Flex:DisplayStyle.None;
   pistolNote.style.display=pistol?DisplayStyle.None:DisplayStyle.Flex;
   if(pistol)
   {
    var now=model.Loadout.Stats;var baseStats=model.Loadout.Base;
    foreach(var (label,value,delta) in statRows)
    {
     int i=WeaponStats.IndexOf(label.stat);
     value.text=CraftingText.FormatStat(label,now[i]);
     float b=baseStats[i];float change=b!=0?(now[i]-b)/Mathf.Abs(b)*100f:0;
     bool changed=Mathf.Abs(now[i]-b)>.0005f;
     delta.text=changed?(change>0?"+":"−")+Mathf.Abs(change).ToString(Mathf.Abs(change)<10?"0.#":"0")+"%":"base";
     bool better=changed&&(change>0)!=label.lowerIsBetter;
     delta.EnableInClassList("better",changed&&better);delta.EnableInClassList("worse",changed&&!better);
    }
   }
   UpdateLive();
  }
  /// Values that move while the pack is open: vitality and nano regeneration, the clock, the location.
  void UpdateLive()
  {
   if(!open)return;
   characterPanel.UpdateVitals();
   var combat=Combat;
   if(combat&&combat.Health)
   {
    var h=combat.Health;vitalityFill.style.width=Length.Percent(h.Fraction*100);vitalityValue.text=$"{Mathf.CeilToInt(h.Current)} / {Mathf.RoundToInt(h.max)}";
    float max=Mathf.Max(1,combat.Stats.nanoMax);nanoFill.style.width=Length.Percent(Mathf.Clamp01(combat.Nano/max)*100);nanoValue.text=$"{Mathf.FloorToInt(combat.Nano)} / {Mathf.RoundToInt(max)}";
   }
   else{vitalityValue.text="—";nanoValue.text="—";}
   Fact("location",combat&&combat.InBerms?"Outer Berms":"Athen Hill");
   if(clock){float hour=Mathf.Repeat(clock.Hour,24);int h=Mathf.FloorToInt(hour),m=Mathf.FloorToInt((hour-h)*60);Fact("time",$"{h:00}:{m:00}");}
  }
  void Fact(string id,string value){if(factValues.TryGetValue(id,out var label)&&label.text!=value)label.text=value;}

  // ------------------------------------------------------------------ colonist view
  void DragStart(PointerDownEvent e)
  {
   if(e.button!=0||!preview||!preview.Active)return;
   dragPointer=e.pointerId;dragX=e.position.x;previewView.CapturePointer(dragPointer);e.StopPropagation();
  }
  void DragMove(PointerMoveEvent e)
  {
   if(dragPointer!=e.pointerId||!previewView.HasPointerCapture(dragPointer))return;
   preview.Drag(e.position.x-dragX);dragX=e.position.x;
  }
  void DragEnd(PointerUpEvent e){if(dragPointer!=e.pointerId)return;if(previewView.HasPointerCapture(dragPointer))previewView.ReleasePointer(dragPointer);dragPointer=-1;}

  /// Illustration class from the item's catalog record; the pack illustration otherwise (nothing when hidden).
  void SetIcon(VisualElement target,string icon,bool hide=false)
  {
   if(target==null)return;
   foreach(string c in iconClasses)target.RemoveFromClassList(c);
   target.style.display=hide?DisplayStyle.None:DisplayStyle.Flex;
   if(!hide)target.AddToClassList(!string.IsNullOrEmpty(icon)?icon:"pack-icon");
  }
 }
}
