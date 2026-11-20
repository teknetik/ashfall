using System;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UIElements;

namespace AthenHill
{
 // Equipment changes commit through the models only, including pointer and keyboard actions.
 public sealed class CharacterLoadoutPanel
 {
  readonly VisualElement root,host,tabs,body;
  readonly Label capacity,message,selection,vitals;
  readonly GameSession session;
  readonly CraftingSession crafting;
  readonly Func<string> selectedItem;
  readonly Action changed;
  readonly ScrollView scroll;
  string section="SECONDARY",selectedSlot,selectedSocket,selectedWeapon,signature;
  int selectedModification=-1;
  public string CurrentSection=>section;
  public bool WantsPreview=>section!="IMPLANTS";
  bool AnatomySection=>section=="IMPLANTS"||section=="ARMOUR";
  public string PreviewWeaponItem=>Character?.Equipped(section=="PRIMARY"?"primary":"secondary");
  string dragItem,dragSlot,dragSocket,dragWeapon;
  int pointer=-1,dragBar,releasedTicks;
  Vector2 origin,lastPointer;
  bool dragging;
  VisualElement source,dropHover;
  Label ghost;
  // The body map of the IMPLANTS / ARMOUR page (rebuilt with the page); laid out by ArrangeAnatomy.
  VisualElement anatomyLayout,anatomyMap,anatomyLeaders;
  Image anatomyImage;
  readonly System.Collections.Generic.List<(string id,AnatomyLayout.Anchor anchor,VisualElement cell,VisualElement node)> anatomySlots=new System.Collections.Generic.List<(string,AnatomyLayout.Anchor,VisualElement,VisualElement)>();
  AnatomyLayout.Result anatomy;
  CharacterModel Character=>session.Character;
  CraftingModel Craft=>crafting?crafting.Model:null;
  /// A carried item was dropped on a cell of the field pack's HOTBAR strip (item, hotbar slot 1–10).
  public Action<string,int> DroppedOnHotbar;
  /// A HOTBAR strip cell was dragged onto another cell (from, to) or off the strip (from, 0).
  public Action<int,int> MovedOnHotbar;

  public CharacterLoadoutPanel(VisualElement root,GameSession session,CraftingSession crafting,Func<string> selectedItem,Action changed)
  {
   this.root=root;this.session=session;this.crafting=crafting;this.selectedItem=selectedItem;this.changed=changed;
   host=root.Q("character-loadout");
   if(host==null)return;
   tabs=new VisualElement();tabs.AddToClassList("character-tabs");host.Add(tabs);
   foreach(var name in new[]{"PRIMARY","SECONDARY","STATS","IMPLANTS","ARMOUR"})
   {
    string value=name;var tab=new Button(()=>{CancelDrag();section=value;selectedSlot=null;selectedSocket=null;selectedWeapon=null;selectedModification=-1;signature=null;changed();}){text=name,name="character-tab-"+name.ToLowerInvariant()};
    tab.AddToClassList("character-tab");tabs.Add(tab);
   }
   capacity=new Label{name="character-capacity"};capacity.AddToClassList("character-capacity");host.Add(capacity);
   vitals=new Label{name="character-vitals"};vitals.AddToClassList("character-vitals");host.Add(vitals);
   scroll=new ScrollView(ScrollViewMode.Vertical){name="character-scroll"};scroll.AddToClassList("character-scroll");host.Add(scroll);body=scroll.contentContainer;
   selection=new Label{name="equipment-selection"};selection.AddToClassList("character-selection");host.Add(selection);
   var actions=new VisualElement();actions.AddToClassList("character-actions");host.Add(actions);
   AddAction(actions,"Equip selected",()=>Place(selectedItem(),null,null,null,selectedSlot,selectedSocket,selectedWeapon),"character-equip");
   AddAction(actions,"Remove",RemoveSelected,"character-remove");
   AddAction(actions,"Upgrade",UpgradeSelected,"character-upgrade");
   message=new Label{name="equipment-result"};message.AddToClassList("character-result");host.Add(message);
   root.RegisterCallback<PointerMoveEvent>(Move,TrickleDown.TrickleDown);
   root.RegisterCallback<PointerUpEvent>(Drop,TrickleDown.TrickleDown);
   root.RegisterCallback<MouseMoveEvent>(e=>MoveAt(e.mousePosition),TrickleDown.TrickleDown);
   root.RegisterCallback<MouseUpEvent>(e=>{if(pointer>=0&&e.button==0){bool wasDragging=dragging;DropAt(e.mousePosition);if(wasDragging)e.StopImmediatePropagation();}},TrickleDown.TrickleDown);
   root.RegisterCallback<KeyDownEvent>(e=>{if(e.keyCode==KeyCode.Escape&&pointer>=0){CancelDrag();e.StopPropagation();}},TrickleDown.TrickleDown);
   root.RegisterCallback<PointerCancelEvent>(_=>CancelDrag());
   scroll.RegisterCallback<FocusInEvent>(e=>{if(!AnatomySection&&e.target is VisualElement v)scroll.ScrollTo(v);});
   scroll.contentViewport.RegisterCallback<GeometryChangedEvent>(_=>FitAnatomyViewport());
   // A release the panel never reported (pointer let go outside the window, focus lost mid-drag) still ends the drag:
   // two quiet ticks with the left button up drop it where the pointer last was.
   root.schedule.Execute(()=>
   {
    var mouse=Mouse.current;
    if(!dragging||mouse==null||mouse.leftButton.isPressed){releasedTicks=0;return;}
    if(++releasedTicks>=2)DropAt(lastPointer);
   }).Every(100);
  }
  static void AddAction(VisualElement target,string text,Action action,string name)
  {var b=new Button(action){text=text,name=name};b.AddToClassList("character-action");target.Add(b);}
  public void Refresh()
  {
   if(host==null)return;
   bool active=Character!=null;host.style.display=active?DisplayStyle.Flex:DisplayStyle.None;
   root.Q("loadout-left")?.parent.EnableInClassList("character-legacy-hidden",active);
   root.Q("you-stats")?.EnableInClassList("character-legacy-hidden",active);
   root.Q("you-progress-fill")?.parent.parent.EnableInClassList("character-legacy-hidden",active);
   if(!active)return;
   var availableSlots=Character.Data.slots.Where(s=>s.section==section||section=="ARMOUR"&&s.section=="STORAGE").ToArray();
   if(section!="STATS"&&(selectedSlot==null||!availableSlots.Any(s=>s.id==selectedSlot))&&selectedSocket==null)selectedSlot=availableSlots.FirstOrDefault()?.id;
   if(selectedModification>=0&&(selectedSlot==null||selectedModification>=Character.ModificationSockets(selectedSlot).Count))selectedModification=-1;
   capacity.text=$"CARRY {Character.CarryWeight:0.#} / {Character.CarryCapacity:0.#} kg   PACK {Character.PackWeight:0.#} / {Character.StorageCapacity:0.#} kg";
   capacity.EnableInClassList("overburdened",Character.Overburdened);UpdateVitals();
   foreach(var child in tabs.Children())child.EnableInClassList("active-tab",child.name=="character-tab-"+section.ToLowerInvariant());
   string next=section+"|"+selectedSlot+":"+selectedSocket+":"+selectedModification+"|"+Character.AttributePoints+":"+Character.SkillPoints+"|"+string.Join(";",Character.Data.slots.Select(s=>s.id+":"+Character.Equipped(s.id)))+"|"+
    (Craft==null?"":string.Join(";",new[]{"primary","secondary"}.Select(s=>WeaponSignature(Character.Equipped(s)))))+"|"+
    string.Join(";",Character.Data.attributes.Select(a=>Character.Attribute(a.id)))+"|"+string.Join(";",Character.Data.skills.Select(s=>Character.Skill(s.id)))+"|"+
    string.Join(";",Character.Data.derivedStats.Select(s=>Character.Stat(s.id)))+"|"+(crafting&&crafting.combat?crafting.combat.ActiveSlot:"")+"|"+
    string.Join(";",Character.Data.slots.SelectMany(s=>Character.ModificationSockets(s.id).Select((socket,index)=>s.id+":"+index+":"+Character.InstalledModification(s.id,index))))+"|"+selectedItem()+"|"+string.Join(";",session.Shop.Carried.Select(x=>x.Key+":"+x.Value));
   if(signature!=next)
   {
    signature=next;var focused=root.focusController?.focusedElement as VisualElement;
    // Rebuilds must restore only controls they removed, never an earlier pack/search selection.
    var focus=focused!=null&&body.Contains(focused)?focused.name:null;
    var previousInspector=body.Q<ScrollView>("equipment-inspector-scroll");
    bool keepInspectorOffset=previousInspector!=null&&(string)previousInspector.userData==selectedSlot;
    var inspectorOffset=previousInspector?.scrollOffset??Vector2.zero;
    body.Clear();anatomyLayout=anatomyMap=null;anatomy=null;anatomySlots.Clear();scroll.verticalScrollerVisibility=AnatomySection?ScrollerVisibility.Hidden:ScrollerVisibility.Auto;
    if(section=="STATS")BuildStats();else BuildEquipment();
    var nextInspector=body.Q<ScrollView>("equipment-inspector-scroll");
    if(focus!=null||keepInspectorOffset)root.schedule.Execute(()=>
    {
     if(keepInspectorOffset&&nextInspector?.panel!=null)nextInspector.scrollOffset=inspectorOffset;
     if(focus==null)return;
     var target=root.Q(focus);if(target!=null&&target.enabledInHierarchy)target.Focus();else root.Q("character-tab-"+section.ToLowerInvariant())?.Focus();
    });
   }
   foreach(var cell in body.Query<Button>(className:"character-slot").ToList())cell.EnableInClassList("selected",cell.name=="equipment-"+selectedSlot||cell.name=="socket-"+selectedSocket||selectedModification>=0&&cell.name=="modification-socket-"+selectedModification);
   // The body map's inspector already names the selected slot and what is in it.
   selection.style.display=section=="STATS"||AnatomySection?DisplayStyle.None:DisplayStyle.Flex;
   root.Q("character-equip").parent.style.display=section=="STATS"?DisplayStyle.None:DisplayStyle.Flex;
   selection.text=selectedModification>=0?SlotName(selectedSlot)+" · "+Character.ModificationSockets(selectedSlot)[selectedModification].label:selectedSlot!=null?SlotName(selectedSlot)+" · "+ItemName(Character.Equipped(selectedSlot)):selectedSocket!=null?"Socket: "+Craft?.Data.SlotName(selectedSocket)+" · "+ItemName(Craft?.GetLoadout(selectedWeapon)?.Fitted(selectedSocket)):"";
   root.Q("character-equip").SetEnabled(section!="STATS"&&(selectedSlot!=null||selectedSocket!=null)&&selectedItem()!=null);
   root.Q("character-remove").SetEnabled(selectedModification>=0?Character.InstalledModification(selectedSlot,selectedModification)!=null:selectedSlot!=null&&Character.Equipped(selectedSlot)!=null||selectedSocket!=null&&Craft?.GetLoadout(selectedWeapon)?.Fitted(selectedSocket)!=null);
   root.Q("character-upgrade").style.display=section=="IMPLANTS"&&selectedModification<0?DisplayStyle.Flex:DisplayStyle.None;
   root.Q("character-upgrade").SetEnabled(selectedSlot!=null&&Character.Equipped(selectedSlot)!=null);
  }
  void Heading(string text){var l=new Label(text);l.AddToClassList("character-heading");body.Add(l);}
  public void UpdateVitals()
  {
   if(vitals==null)return;
   var combat=crafting?crafting.combat:null;
   vitals.text=combat&&combat.Health?$"VITALITY {Mathf.CeilToInt(combat.Health.Current)} / {combat.Health.max:0}   NANO {Mathf.FloorToInt(combat.Nano)} / {combat.Stats.nanoMax:0}":"";
  }
  string ItemName(string id)=>session.Shop.Spec(id)?.name??id??"Empty";
  string SlotName(string id)=>Character.Data.slots.FirstOrDefault(s=>s.id==id)?.label??id;
  string WeaponSignature(string item)
  {
   var weapon=Craft.FindWeapon(item);var loadout=weapon!=null?Craft.GetLoadout(weapon.id):null;
   return loadout==null?"":weapon.id+":"+string.Join(";",loadout.Slots.Select(s=>s+":"+loadout.Fitted(s)))+":c"+Mathf.Ceil(loadout.Durability)+"/"+Mathf.Floor(loadout.MaxDurability)+"/"+loadout.Repairs+(crafting&&crafting.RepairJob!=null?"r":"");
  }
  public string DescribeItem(string item)
  {
   var def=Character?.Equipment(item);
   if(def==null)
   {
    if(Character?.Modification(item)!=null)return ModificationDescription(item);
    var mod=Craft?.Loadout.Modifier(item);if(mod==null)return "";
    string description="Socket: "+Craft.Data.SlotName(mod.slot);
    if(Character!=null&&mod.requirements?.Length>0)description+="\nRequires: "+string.Join(", ",mod.requirements.Select(r=>$"{Character.Data.Label(r.stat)} {Character.Stat(r.stat):0.#}/{r.minimum:0.#}"));
    if(mod.requiredTools?.Length>0)description+="\nTools: "+string.Join(", ",mod.requiredTools.Select(ItemName));
    return description;
   }
   string text=$"{def.weight:0.#} kg";
   if(def.slots.Any(s=>s.StartsWith("implant_")))text+=$"  |  {def.tier}  |  Upgrade {def.upgradeLevel}";
   if(def.requirements.Length>0)text+="\nRequires: "+string.Join(", ",def.requirements.Select(r=>$"{Character.Data.Label(r.stat)} {Character.Stat(r.stat):0.#}/{r.minimum:0.#}"));
   if(def.operatingRequirements.Length>0)text+="\nTo operate: "+string.Join(", ",def.operatingRequirements.Select(r=>$"{Character.Data.Label(r.stat)} {Character.Stat(r.stat):0.#}/{r.minimum:0.#}"));
   if(!string.IsNullOrEmpty(def.installationFacility))text+="\nInstall at: "+def.installationFacility;
   if(def.modifiers.Length>0)text+="\n"+string.Join(", ",def.modifiers.Select(m=>Character.Data.Label(m.stat)+" "+(m.flat!=0?m.flat.ToString("+0.##;-0.##;0"):"")+(m.percent!=0?$" {m.percent*100:+0.##;-0.##;0}%":"")));
   if(!string.IsNullOrEmpty(def.upgradeToItemId))text+="\nUpgrade: "+ItemName(def.upgradeToItemId)+$" ({def.upgradeCredits} cr"+string.Concat(def.upgradeIngredients.Select(i=>$", {i.count} {ItemName(i.id)}"))+")";
   return text;
  }
  void BuildEquipment()
  {
   if(section=="IMPLANTS"||section=="ARMOUR"){BuildAnatomy();return;}
   var slot=Character.Data.slots.FirstOrDefault(s=>s.section==section);
   if(slot==null){Copy(body,"No equipment slot is configured for this section.");return;}
   string item=Character.Equipped(slot.id);
   var cell=EquipmentButton("equipment-"+slot.id,slot.label,item,()=>ChooseSlot(slot.id));
   cell.userData=new Target{slot=slot.id};BindDrag(cell,item,slot.id,null,null);body.Add(cell);
   var picture=new VisualElement{name="weapon-picture",pickingMode=PickingMode.Ignore};picture.AddToClassList("weapon-picture");
   picture.AddToClassList(session.Shop.Spec(item)?.icon??"pack-icon");body.Add(picture);
   if(item==null){Copy(body,"Choose a carried weapon and equip it here. Its attachment sockets and statistics appear when fitted.");return;}
   if(crafting&&crafting.combat)
   {
    var combat=crafting.combat;
    AddAction(body,combat.ActiveSlot==slot.id?"Active weapon":"Make active",()=>{bool ok=combat.SelectWeapon(slot.id);Result(ok,"This weapon is unavailable.","Active weapon changed.");},"activate-"+slot.id);
   }
   var weapon=Craft?.FindWeapon(item);var loadout=weapon!=null?Craft.GetLoadout(weapon.id):null;
   if(loadout==null){Copy(body,DescribeItem(item));return;}
   BuildCondition(loadout);
   Heading("ATTACHMENT SLOTS");
   var sockets=new VisualElement();sockets.AddToClassList("weapon-sockets");body.Add(sockets);
   foreach(var socket in loadout.Slots)
   {
    string key=socket,mod=loadout.Fitted(key),weaponId=weapon.id;
    var socketCell=EquipmentButton("socket-"+key,Craft.Data.SlotName(key),mod,()=>{selectedSocket=key;selectedSlot=null;selectedWeapon=weaponId;selectedModification=-1;signature=null;Refresh();});
    socketCell.AddToClassList("weapon-socket");socketCell.userData=new Target{socket=key,weapon=weaponId};BindDrag(socketCell,mod,null,key,weaponId);sockets.Add(socketCell);
   }
   if(selectedSocket!=null)
   {
    var fitted=loadout.Fitted(selectedSocket);
    Copy(body,fitted!=null?ItemName(fitted)+"\n"+(session.Shop.Spec(fitted)?.description??""):"Select a compatible mod in your pack, then Equip selected.");
   }
   Heading("WEAPON STATS");
   var effective=loadout.WithCharacter(Character);
   foreach(var statId in WeaponStats.Ids)
   {
    int index=WeaponStats.IndexOf(statId);var stat=Craft.Data.statLabels?.FirstOrDefault(x=>x.stat==statId);
    string label=stat?.label??statId;
    float mod=loadout.Stats[index]-loadout.Base[index],character=effective[index]-loadout.Stats[index];
    var row=new Foldout{text=$"{label}   {CraftingText.FormatStat(stat,effective[index])}",value=false,name="weapon-stat-"+statId};
    row.AddToClassList("character-breakdown");row.Add(new Label($"Base {CraftingText.FormatStat(stat,loadout.Base[index])} · Mod {mod:+0.##;-0.##;0} · Character {character:+0.##;-0.##;0}"));body.Add(row);
   }
  }
  /// Condition line and the field repair action (20 Nov 2026, Phase 3). The repair runs a few seconds with the carried toolkit.
  void BuildCondition(WeaponLoadout loadout)
  {
   if(!loadout.HasCondition||Craft==null)return;
   Heading("CONDITION");
   var rules=Craft.Condition;
   string line=CraftingText.Condition(loadout,Craft);
   float next=WeaponCondition.NextRepairAmount(loadout,rules);
   if(!WeaponCondition.IsBroken(loadout,rules)&&next>0)line+=$"\nNext field repair: +{next:0.#}, best condition −{rules.capLossPerRepair:0.#}.";
   Copy(body,line);
   var job=crafting?crafting.RepairJob:null;
   string weaponId=loadout.WeaponId;
   if(job!=null&&job.recipeId==weaponId)
   {
    AddAction(body,"Stop repair",()=>{crafting.CancelRepair();signature=null;changed();},"weapon-repair-cancel");
    Copy(body,$"Repairing: {CraftingText.Duration(job.Remaining(Time.time))} left. Reopen this tab to refresh.");
    return;
   }
   AddAction(body,"Repair with toolkit",()=>{bool ok=crafting.BeginFieldRepair(weaponId,out string reason);message.text=ok?"":CraftingText.ConditionReason(reason,Craft,loadout);message.EnableInClassList("rejected",!ok);signature=null;changed();},"weapon-repair");
  }
  void ChooseSlot(string id)
  {
   selectedSlot=id;selectedSocket=null;selectedWeapon=null;selectedModification=-1;signature=null;Refresh();
  }
  void ChooseModification(int index){selectedModification=index;signature=null;Refresh();}
  static void Copy(VisualElement target,string text,string cls="equipment-description")
  {var l=new Label(text);foreach(var c in cls.Split(' '))l.AddToClassList(c);target.Add(l);}
  void FitAnatomyViewport()
  {
   var layout=body.Q("anatomy-layout");if(layout==null)return;
   float height=scroll.contentViewport.layout.height;
   // The map occupies the available viewport; only the adjacent inspector scrolls.
   // The fallback covers construction before the first resolved geometry event.
   if(float.IsNaN(height)||height<=0)height=400;
   layout.style.height=height;layout.style.minHeight=height;layout.style.maxHeight=height;
   scroll.scrollOffset=Vector2.zero;
   ArrangeAnatomy();
  }
  /// Places the figure, the slot boxes, the dots and the leader lines for the current size (AnatomyLayout.Arrange).
  void ArrangeAnatomy()
  {
   if(anatomyLayout==null||anatomyMap==null||anatomyLayout.panel==null&&anatomy!=null)return;
   float width=scroll.contentViewport.layout.width,height=anatomyLayout.resolvedStyle.height;
   if(float.IsNaN(height)||height<=0)height=anatomyLayout.style.height.value.value;
   var next=AnatomyLayout.Arrange(anatomySlots.Select(s=>(s.id,s.anchor)).ToList(),width,height);
   if(anatomy!=null&&Mathf.Abs(anatomy.mapWidth-next.mapWidth)<.25f&&Mathf.Abs(anatomy.mapHeight-next.mapHeight)<.25f)return;
   anatomy=next;
   anatomyMap.style.width=next.mapWidth;anatomyMap.style.minWidth=next.mapWidth;anatomyMap.style.maxWidth=next.mapWidth;
   var r=next.image;
   anatomyImage.style.left=r.x;anatomyImage.style.top=r.y;anatomyImage.style.width=r.width;anatomyImage.style.height=r.height;
   for(int i=0;i<anatomySlots.Count;i++)
   {
    var p=next.slots[i];var cell=anatomySlots[i].cell;var node=anatomySlots[i].node;
    cell.style.left=p.box.x;cell.style.top=p.box.y;cell.style.width=p.box.width;cell.style.height=p.box.height;cell.EnableInClassList("compact",next.compact);
    node.style.left=p.node.x;node.style.top=p.node.y;
   }
   anatomyLeaders.MarkDirtyRepaint();
  }
  void DrawLeaders(MeshGenerationContext context)
  {
   if(anatomy==null)return;
   var painter=context.painter2D;painter.lineCap=LineCap.Round;
   for(int pass=0;pass<2;pass++)
    for(int i=0;i<anatomy.slots.Count&&i<anatomySlots.Count;i++)
    {
     bool chosen=anatomySlots[i].id==selectedSlot;if(chosen!=(pass==1))continue;
     painter.strokeColor=chosen?new Color32(0x8b,0xe6,0xdf,0xff):new Color32(0x58,0xb9,0xc2,0xe6);painter.lineWidth=chosen?2f:1.4f;
     painter.BeginPath();painter.MoveTo(anatomy.slots[i].leaderStart);painter.LineTo(anatomy.slots[i].node);painter.Stroke();
    }
  }
  void BuildAnatomy()
  {
   bool implants=section=="IMPLANTS";
   var layout=new VisualElement{name="anatomy-layout"};layout.AddToClassList("anatomy-layout");body.Add(layout);
   anatomyLayout=layout;anatomy=null;anatomySlots.Clear();FitAnatomyViewport();
   var map=new VisualElement{name=implants?"implant-body-map":"armour-body-map"};map.AddToClassList("anatomy-map");layout.Add(map);anatomyMap=map;
   var image=new Image{name="anatomy-image",pickingMode=PickingMode.Ignore,scaleMode=ScaleMode.ScaleToFit,image=Resources.Load<Texture2D>("UI/ImplantBody")};
   image.AddToClassList("anatomy-image");if(!implants)image.AddToClassList("armour-anatomy-image");map.Add(image);anatomyImage=image;
   // Leaders are drawn over the figure and under the boxes and dots.
   var leaders=new VisualElement{name="anatomy-leaders",pickingMode=PickingMode.Ignore};leaders.AddToClassList("anatomy-leaders");leaders.generateVisualContent+=DrawLeaders;map.Add(leaders);anatomyLeaders=leaders;
   var all=Character.Data.slots.Where(s=>s.section==section||section=="ARMOUR"&&s.section=="STORAGE").ToArray();
   for(int n=0;n<all.Length;n++)
   {
    var slot=all[n];string id=slot.id,item=Character.Equipped(id);
    var cell=EquipmentButton("equipment-"+id,id=="storage"?"Pack":slot.label,item,()=>ChooseSlot(id));cell.AddToClassList("anatomy-slot");
    cell.userData=new Target{slot=id};BindDrag(cell,item,id,null,null);map.Add(cell);
    var dot=new VisualElement{name="anatomy-node-"+id,pickingMode=PickingMode.Ignore};dot.AddToClassList("anatomy-node");dot.EnableInClassList("selected",id==selectedSlot);map.Add(dot);
    anatomySlots.Add((id,AnatomyLayout.AnchorFor(implants,id,n,all.Length),cell,dot));
   }
   layout.RegisterCallback<GeometryChangedEvent>(_=>ArrangeAnatomy());
   ArrangeAnatomy();
   var inspectorScroll=new ScrollView(ScrollViewMode.Vertical){name="equipment-inspector-scroll",userData=selectedSlot};
   inspectorScroll.AddToClassList("equipment-inspector-scroll");layout.Add(inspectorScroll);
   inspectorScroll.RegisterCallback<FocusInEvent>(e=>{if(e.target is VisualElement v)inspectorScroll.ScrollTo(v);});
   var inspector=new VisualElement{name="equipment-inspector"};inspector.AddToClassList("equipment-inspector");inspectorScroll.Add(inspector);
   if(selectedSlot==null){Copy(inspector,"Select a body slot to inspect its equipment.");return;}
   string equipped=Character.Equipped(selectedSlot);
   Copy(inspector,SlotName(selectedSlot).ToUpperInvariant(),"equipment-inspector-heading");
   Copy(inspector,ItemName(equipped),"equipment-inspector-title");
   if(equipped==null)
   {
    var fits=Character.Data.equipment.Where(e=>e!=null&&e.slots!=null&&e.slots.Contains(selectedSlot)).Select(e=>ItemName(e.itemId)).Distinct().ToArray();
    if(fits.Length==0){Copy(inspector,$"Nothing made or sold in Ward fits the {SlotName(selectedSlot).ToLowerInvariant()} slot yet.");return;}
    Copy(inspector,implants?"No implant installed. Select a compatible implant from your pack and choose Equip selected. Each implant supports three augmentations.":"No armour fitted. Select a compatible component from your pack and choose Equip selected.");
    Copy(inspector,"Fits here: "+string.Join(", ",fits)+".");
    CompatibleEquipment(inspector,selectedSlot);return;
   }
   var illustration=new VisualElement{pickingMode=PickingMode.Ignore};illustration.AddToClassList("equipment-inspector-icon");illustration.AddToClassList(session.Shop.Spec(equipped)?.icon??"pack-icon");inspector.Add(illustration);
   Copy(inspector,session.Shop.Spec(equipped)?.description??"");Copy(inspector,DescribeItem(equipped));
   if(!Character.IsOperating(selectedSlot,out string reason))Copy(inspector,reason,"character-result rejected");
   var sockets=Character.ModificationSockets(selectedSlot);
   if(sockets.Count==0){Copy(inspector,"This component has no augmentation sockets.");return;}
   Copy(inspector,implants?$"AUGMENTATION SLOTS  {sockets.Count}":$"COMPONENT SLOTS  {sockets.Count}","character-heading");
   var strip=new VisualElement{name="modification-sockets"};strip.AddToClassList("modification-sockets");inspector.Add(strip);
   for(int i=0;i<sockets.Count;i++)
   {
    int index=i;string installed=Character.InstalledModification(selectedSlot,index);
    var socket=EquipmentButton("modification-socket-"+index,sockets[i].label,installed,()=>ChooseModification(index));
    socket.AddToClassList("modification-socket");socket.EnableInClassList("selected",selectedModification==index);strip.Add(socket);
   }
   if(selectedModification>=sockets.Count)selectedModification=-1;
   if(selectedModification>=0)BuildModificationPanel(inspector,selectedSlot,selectedModification);
   else Copy(inspector,"Select a socket to inspect, install or remove its augmentation.");
  }
  void CompatibleEquipment(VisualElement target,string slot)
  {
   var candidates=session.Shop.Carried.Where(x=>Character.Equipment(x.Key)?.slots.Contains(slot)==true).ToArray();
   foreach(var candidate in candidates)
   {
    string item=candidate.Key;AddAction(target,"Equip "+ItemName(item),()=>{bool ok=Character.TryEquip(item,slot,out string reason);Result(ok,reason,"Equipment updated.");},"equip-carried-"+item);
   }
   if(candidates.Length==0)Copy(target,"No compatible item carried.");
  }
  void BuildModificationPanel(VisualElement target,string slot,int index)
  {
   var pane=new VisualElement{name="augmentation-details"};pane.AddToClassList("augmentation-details");target.Add(pane);
   string installed=Character.InstalledModification(slot,index);var socket=Character.ModificationSockets(slot)[index];
   Copy(pane,socket.label.ToUpperInvariant(),"equipment-inspector-heading");
   Copy(pane,installed!=null?ItemName(installed):"Empty augmentation slot","equipment-inspector-title");
   if(installed!=null)
   {
    Copy(pane,session.Shop.Spec(installed)?.description??"");Copy(pane,ModificationDescription(installed));
    AddAction(pane,"Remove augmentation",()=>{bool ok=Character.TryRemoveModification(slot,index,out string reason);Result(ok,reason,"Augmentation returned to pack.");},"remove-augmentation");
   }
   Copy(pane,"COMPATIBLE AUGMENTATIONS","character-heading");
   int count=0;
   foreach(var entry in session.Shop.Carried)
   {
    string item=entry.Key;var mod=Character.Modification(item);if(mod==null)continue;
    if(mod.slots!=null&&mod.slots.Length>0&&!mod.slots.Contains(slot))continue;
    if(mod.socketTypes!=null&&mod.socketTypes.Length>0&&!mod.socketTypes.Contains(socket.type))continue;
    count++;bool can=Character.CanInstallModification(slot,index,item,out string why);
    var option=EquipmentButton("install-augmentation-"+item,"INSTALL",item,()=>{bool ok=Character.TryInstallModification(slot,index,item,out string reason);Result(ok,reason,"Augmentation installed.");});
    option.tooltip=can?ModificationDescription(item):HumanReason(why);option.SetEnabled(can);pane.Add(option);
   }
   if(count==0)Copy(pane,"No compatible augmentation carried. Merchant stock and the workbench list available parts.");
  }
  string ModificationDescription(string item)
  {
   var mod=Character.Modification(item);if(mod==null)return "";
   string text=(mod.slots?.Length??0)>0?"Fits: "+string.Join(", ",mod.slots.Select(SlotName)):"Fits: any body slot with a matching socket";
   text+="\nSocket type: "+((mod.socketTypes?.Length??0)>0?string.Join(", ",mod.socketTypes.Select(SocketTypeName)):"None configured");
   if((mod.modifiers?.Length??0)>0)text+="\n"+string.Join("\n",mod.modifiers.Select(m=>Character.Data.Label(m.stat)+" "+(m.flat!=0?m.flat.ToString("+0.##;-0.##;0"):"")+(m.percent!=0?$" {m.percent*100:+0.##;-0.##;0}%":"")));
   if((mod.requirements?.Length??0)>0)text+="\nRequires: "+string.Join(", ",mod.requirements.Select(r=>$"{Character.Data.Label(r.stat)} {Character.Stat(r.stat):0.#}/{r.minimum:0.#}"));
   if((mod.operatingRequirements?.Length??0)>0)text+="\nTo operate: "+string.Join(", ",mod.operatingRequirements.Select(r=>$"{Character.Data.Label(r.stat)} {Character.Stat(r.stat):0.#}/{r.minimum:0.#}"));
   return text;
  }
  static string SocketTypeName(string type)=>string.IsNullOrEmpty(type)?"Unspecified":char.ToUpperInvariant(type[0])+type.Substring(1).Replace('_',' ');
  Button EquipmentButton(string name,string label,string item,Action click)
  {
   var b=new Button(click){name=name,tooltip=label+": "+ItemName(item)};b.AddToClassList("character-slot");
   VisualElement icon;
   if(item==null){icon=new Label("+"){pickingMode=PickingMode.Ignore};icon.AddToClassList("character-slot-empty-mark");}
   else{icon=new VisualElement{pickingMode=PickingMode.Ignore};icon.AddToClassList(session.Shop.Spec(item)?.icon??"pack-icon");}
   icon.AddToClassList("character-slot-icon");b.Add(icon);
   var text=new VisualElement{pickingMode=PickingMode.Ignore};text.AddToClassList("character-slot-copy");
   var title=new Label(label.ToUpperInvariant()){pickingMode=PickingMode.Ignore};title.AddToClassList("character-slot-label");text.Add(title);
   var value=new Label(ItemName(item)){pickingMode=PickingMode.Ignore};value.AddToClassList("character-slot-value");text.Add(value);b.Add(text);
   b.EnableInClassList("empty",item==null);return b;
  }
  void BuildStats()
  {
   Heading($"ATTRIBUTES  /  {Character.AttributePoints} POINTS");
   foreach(var a in Character.Data.attributes)
   {
    string id=a.id;StatRow(id,a.label,Character.Attribute(id),()=>Raise(id,false),$"Increase {a.label} by 1 ({a.cost} attribute points)",Character.AttributePoints>=a.cost&&Character.BaseAttribute(id)<a.maximum);
   }
   Heading($"SKILLS  /  {Character.SkillPoints} POINTS");
   string category=null;
   foreach(var s in Character.Data.skills)
   {
    if(category!=s.category){category=s.category;Heading(category?.ToUpperInvariant()??"GENERAL");}
    string id=s.id;StatRow(id,s.label,Character.Skill(id),()=>Raise(id,true),$"Train {s.label} by {s.trainingStep} ({s.cost} skill points)",Character.SkillPoints>=s.cost&&Character.TrainedSkill(id)<s.maximum);
   }
   Heading("DERIVED STATS");
   foreach(var stat in Character.Data.derivedStats)
   {
    var b=Character.Breakdown(stat.id);
    var fold=new Foldout{text=$"{stat.label}   {b.finalValue:0.##}",value=false,name="breakdown-"+stat.id};fold.AddToClassList("character-breakdown");
    fold.Add(new Label(BreakdownText(stat.id)));body.Add(fold);
   }
  }
  string BreakdownText(string id)
  {
   var b=Character.Breakdown(id);return $"Base {b.baseValue:0.##}   Progression {b.progression:+0.##;-0.##;0}\nDependencies {b.dependencies:+0.##;-0.##;0}   Equipment {b.flat:+0.##;-0.##;0}\nModifier {b.percent*100:+0.##;-0.##;0}%   Total {b.finalValue:0.##}";
  }
  void StatRow(string id,string label,float value,Action raise,string tooltip,bool enabled)
  {
   var row=new VisualElement();row.AddToClassList("character-stat-row");
   var name=new Foldout{text=label,value=false};name.AddToClassList("character-stat-name");name.Add(new Label(BreakdownText(id)));row.Add(name);row.Add(new Label(value.ToString("0.##")));
   var plus=new Button(raise){text="+",name="raise-"+id,tooltip=tooltip};plus.SetEnabled(enabled);plus.AddToClassList("character-stat-increase");row.Add(plus);body.Add(row);
  }
  void Raise(string id,bool skill)
  {string reason;bool ok=skill?Character.TryRaiseSkill(id,out reason):Character.TryRaiseAttribute(id,out reason);Result(ok,reason,"Improved.");}
  void RemoveSelected()
  {
   string reason="Select an equipped item first.";bool ok=false;
   if(selectedModification>=0&&selectedSlot!=null)ok=Character.TryRemoveModification(selectedSlot,selectedModification,out reason);
   else if(selectedSocket!=null&&Craft!=null)ok=Craft.TryRemove(selectedWeapon,selectedSocket,out reason);
   else if(selectedSlot!=null)ok=Character.TryUnequip(selectedSlot,out reason);
   Result(ok,reason,"Returned to pack.");
  }
  void UpgradeSelected()
  {string reason="Select an implant first.";bool ok=selectedSlot!=null&&Character.TryUpgradeImplant(selectedSlot,out reason);Result(ok,reason,"Implant upgraded.");}
  void Result(bool ok,string reason,string success)
  {
   message.text=ok?success:HumanReason(reason);message.EnableInClassList("rejected",!ok);signature=null;changed();
  }
  string HumanReason(string reason)
  {
   if(string.IsNullOrWhiteSpace(reason))return "That item cannot be placed here.";
   if(reason.Contains(" "))return reason;
   if(Craft!=null)return CraftingText.Reason(reason,Craft);
   return reason.Replace('_',' ')+".";
  }
  void Place(string item,string fromSlot,string fromSocket,string fromWeapon,string toSlot,string toSocket,string toWeapon)
  {
   if(item==null){Result(false,"Select a carried item first.",null);return;}
   string reason="Select an equipment slot first.";bool ok=false;
   if(toSocket!=null&&Craft!=null)
   {
    var mod=Craft.GetLoadout(toWeapon)?.Modifier(item);
    if(fromSlot!=null||fromSocket!=null)reason="Return the item to your pack before fitting it.";
    else if(mod==null||mod.slot!=toSocket)reason="This mod does not fit the selected socket.";
    else ok=Craft.TryFit(toWeapon,item,out reason);
   }
   else if(toSlot!=null)
   {
    if(selectedModification>=0&&toSlot==selectedSlot&&fromSlot==null&&fromSocket==null&&Character.Modification(item)!=null)ok=Character.TryInstallModification(toSlot,selectedModification,item,out reason);
    else if(fromSocket!=null)reason="Weapon mods belong in a compatible weapon socket.";
    else if(fromSlot!=null)ok=Character.TryMove(fromSlot,toSlot,out reason);
    else ok=Character.TryEquip(item,toSlot,out reason);
   }
   Result(ok,reason,"Equipment updated.");
  }
  sealed class Target{public string slot,socket,weapon;}
  public void BindInventory(Button tile,string item)=>BindDrag(tile,item,null,null,null);
  void BindDrag(VisualElement element,string item,string slot,string socket,string weapon)
  {
   element.RegisterCallback<PointerDownEvent>(e=>
   {
    if(e.button!=0||e.ctrlKey||item==null||Character==null)return;
    Begin(e,element,item);dragSlot=slot;dragSocket=socket;dragWeapon=weapon;
    // Clickable owns capture until movement crosses the drag threshold.
   },TrickleDown.TrickleDown);
   DragCallbacks(element);
  }
  /// A cell of the field pack's HOTBAR strip (slots 3–0): dragging it onto another cell moves or swaps the two, dragging
  /// it off the strip clears it (MovedOnHotbar). Cells 1 and 2 follow the equipped weapons and do not drag.
  public void BindHotbarCell(VisualElement cell,int slot,Func<string> item)
  {
   cell.RegisterCallback<PointerDownEvent>(e=>
   {
    if(e.button!=0||e.ctrlKey||!HotbarModel.IsItemSlot(slot))return;
    string id=item();if(id==null)return;
    Begin(e,cell,id);dragBar=slot;
   },TrickleDown.TrickleDown);
   DragCallbacks(cell);
  }
  void Begin(PointerDownEvent e,VisualElement element,string item)
  {
   CancelDrag();pointer=e.pointerId;origin=lastPointer=e.position;source=element;dragItem=item;
  }
  // The same handlers on the root and on the pressed element: while an element holds the pointer, its events reach it
  // whichever way the panel dispatches captured events.
  void DragCallbacks(VisualElement element)
  {
   element.RegisterCallback<PointerMoveEvent>(Move,TrickleDown.TrickleDown);
   element.RegisterCallback<PointerUpEvent>(Drop,TrickleDown.TrickleDown);
   element.RegisterCallback<MouseMoveEvent>(e=>MoveAt(e.mousePosition),TrickleDown.TrickleDown);
   element.RegisterCallback<MouseUpEvent>(e=>{if(pointer>=0&&e.button==0){bool wasDragging=dragging;DropAt(e.mousePosition);if(wasDragging)e.StopImmediatePropagation();}},TrickleDown.TrickleDown);
   element.RegisterCallback<PointerCancelEvent>(_=>CancelDrag());
   element.RegisterCallback<PointerCaptureOutEvent>(_=>{if(dragging)CancelDrag();});
  }
  void Move(PointerMoveEvent e)
  {
   if(pointer!=e.pointerId||source==null)return;
   MoveAt(e.position);
   if(dragging)e.StopPropagation();
  }
  void MoveAt(Vector2 position)
  {
   if(pointer<0||source==null||!dragging&&Vector2.Distance(origin,position)<7)return;
   lastPointer=position;
   if(!dragging)
   {
    dragging=true;source.CapturePointer(pointer);RemoveGhosts();
    ghost=new Label(ItemName(dragItem)){name="equipment-drag-ghost",pickingMode=PickingMode.Ignore};ghost.AddToClassList("equipment-drag-ghost");root.Add(ghost);
    source.AddToClassList("drag-source");
   }
   var p=root.WorldToLocal(position);ghost.style.left=p.x+14;ghost.style.top=p.y+14;
   // Strip cells light up under a dragged item or cell.
   VisualElement over=null;
   for(var v=root.panel?.Pick(position);v!=null;v=v.parent)if(v.userData is HotbarDrop){over=v;break;}
   if(over!=dropHover){dropHover?.RemoveFromClassList("drop-target");dropHover=over;dropHover?.AddToClassList("drop-target");}
  }
  void Drop(PointerUpEvent e)
  {
   if(pointer!=e.pointerId)return;
   bool wasDragging=dragging;DropAt(e.position);if(wasDragging)e.StopImmediatePropagation();
  }
  void DropAt(Vector2 position)
  {
   if(!dragging){CancelDrag();return;}
   var target=root.panel?.Pick(position);Target destination=null;HotbarDrop bar=null;bool pack=false;
   for(var v=target;v!=null;v=v.parent){if(v.userData is Target t)destination=t;if(v.userData is HotbarDrop h)bar=h;if(v.name=="pack-col")pack=true;}
   string item=dragItem,slot=dragSlot,socket=dragSocket,weapon=dragWeapon;int fromBar=dragBar;CancelDrag();
   if(fromBar>0)
   {
    // A strip cell: onto another cell moves or swaps; anywhere else clears it.
    if(bar==null)MovedOnHotbar?.Invoke(fromBar,0);
    else if(bar.slot!=fromBar)MovedOnHotbar?.Invoke(fromBar,bar.slot);
   }
   else if(bar!=null)
   {
    // Hotbar 1/2 hold the weapons: a carried weapon dropped there is equipped; 3–0 take usable items.
    var weaponSlot=HotbarModel.WeaponSlot(bar.slot);
    if(slot!=null||socket!=null)Result(false,"Only carried items go on the hotbar. Return it to your pack first.",null);
    else if(weaponSlot!=null)Place(item,null,null,null,weaponSlot,null,null);
    else DroppedOnHotbar?.Invoke(item,bar.slot);
   }
   else if(destination!=null)Place(item,slot,socket,weapon,destination.slot,destination.socket,destination.weapon);
   else if(pack&&(slot!=null||socket!=null))
   {
    string reason;bool ok=socket!=null?Craft.TryRemove(weapon,socket,out reason):Character.TryUnequip(slot,out reason);Result(ok,reason,"Returned to pack.");
   }
   else Result(false,"Drop onto an equipment slot, a compatible socket, or the pack.",null);
  }
  /// Ends any drag and removes its floating label. Called on drop, Escape, a new press, a page change and on closing.
  public void CancelDrag()
  {
   var held=source;int id=pointer;
   ghost=null;pointer=-1;dragging=false;source=null;dragItem=dragSlot=dragSocket=dragWeapon=null;dragBar=0;releasedTicks=0;
   if(id>=0&&held!=null&&held.HasPointerCapture(id))held.ReleasePointer(id);
   held?.RemoveFromClassList("drag-source");
   dropHover?.RemoveFromClassList("drop-target");dropHover=null;
   RemoveGhosts();
  }
  /// At most one drag label exists: every one under the panel root is removed, not only the last one made.
  void RemoveGhosts()
  {
   if(root==null)return;
   foreach(var g in root.Query(className:"equipment-drag-ghost").ToList())g.RemoveFromHierarchy();
  }

 }
}
