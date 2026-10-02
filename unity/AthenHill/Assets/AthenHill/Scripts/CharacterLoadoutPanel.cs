using System;
using System.Linq;
using UnityEngine;
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
  public string PreviewWeaponItem=>Character?.Equipped(section=="PRIMARY"?"primary":"secondary");
  string dragItem,dragSlot,dragSocket,dragWeapon;
  int pointer=-1;
  Vector2 origin;
  bool dragging;
  VisualElement source;
  Label ghost;
  CharacterModel Character=>session.Character;
  CraftingModel Craft=>crafting?crafting.Model:null;

  public CharacterLoadoutPanel(VisualElement root,GameSession session,CraftingSession crafting,Func<string> selectedItem,Action changed)
  {
   this.root=root;this.session=session;this.crafting=crafting;this.selectedItem=selectedItem;this.changed=changed;
   host=root.Q("character-loadout");
   if(host==null)return;
   tabs=new VisualElement();tabs.AddToClassList("character-tabs");host.Add(tabs);
   foreach(var name in new[]{"PRIMARY","SECONDARY","STATS","IMPLANTS","ARMOUR"})
   {
    string value=name;var tab=new Button(()=>{section=value;selectedSlot=null;selectedSocket=null;selectedWeapon=null;selectedModification=-1;signature=null;changed();}){text=name,name="character-tab-"+name.ToLowerInvariant()};
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
   scroll.RegisterCallback<FocusInEvent>(e=>{if(e.target is VisualElement v)scroll.ScrollTo(v);});
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
    signature=next;var focus=(root.focusController?.focusedElement as VisualElement)?.name;body.Clear();
    if(section=="STATS")BuildStats();else BuildEquipment();
    if(focus!=null)root.schedule.Execute(()=>{var target=root.Q(focus);if(target!=null&&target.enabledInHierarchy)target.Focus();else root.Q("character-tab-"+section.ToLowerInvariant())?.Focus();});
   }
   foreach(var cell in body.Query<Button>(className:"character-slot").ToList())cell.EnableInClassList("selected",cell.name=="equipment-"+selectedSlot||cell.name=="socket-"+selectedSocket||selectedModification>=0&&cell.name=="modification-socket-"+selectedModification);
   selection.style.display=section=="STATS"?DisplayStyle.None:DisplayStyle.Flex;
   root.Q("character-equip").parent.style.display=section=="STATS"?DisplayStyle.None:DisplayStyle.Flex;
   selection.text=selectedModification>=0?SlotName(selectedSlot)+" · "+Character.ModificationSockets(selectedSlot)[selectedModification].label:selectedSlot!=null?SlotName(selectedSlot):selectedSocket!=null?"Socket: "+Craft?.Data.SlotName(selectedSocket):"";
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
   return loadout==null?"":weapon.id+":"+string.Join(";",loadout.Slots.Select(s=>s+":"+loadout.Fitted(s)));
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
  void ChooseSlot(string id)
  {
   selectedSlot=id;selectedSocket=null;selectedWeapon=null;selectedModification=-1;signature=null;Refresh();
  }
  void ChooseModification(int index){selectedModification=index;signature=null;Refresh();}
  static void Copy(VisualElement target,string text,string cls="equipment-description")
  {var l=new Label(text);foreach(var c in cls.Split(' '))l.AddToClassList(c);target.Add(l);}
  void BuildAnatomy()
  {
   bool implants=section=="IMPLANTS";
   var layout=new VisualElement{name="anatomy-layout"};layout.AddToClassList("anatomy-layout");body.Add(layout);
   var map=new VisualElement{name=implants?"implant-body-map":"armour-body-map"};map.AddToClassList("anatomy-map");layout.Add(map);
   var image=new Image{name="anatomy-image",pickingMode=PickingMode.Ignore,scaleMode=ScaleMode.ScaleToFit,image=Resources.Load<Texture2D>("UI/ImplantBody")};
   image.AddToClassList("anatomy-image");if(!implants)image.AddToClassList("armour-anatomy-image");map.Add(image);
   var all=Character.Data.slots.Where(s=>s.section==section||section=="ARMOUR"&&s.section=="STORAGE").ToArray();
   for(int n=0;n<all.Length;n++)
   {
    var slot=all[n];string id=slot.id,item=Character.Equipped(id);var position=AnatomyPosition(id,n,implants);
    var cell=EquipmentButton("equipment-"+id,slot.label,item,()=>ChooseSlot(id));cell.AddToClassList("anatomy-slot");
    cell.style.top=position.y;if(position.x>0)cell.style.right=0;else cell.style.left=0;
    cell.userData=new Target{slot=id};BindDrag(cell,item,id,null,null);map.Add(cell);
    var lead=new VisualElement{pickingMode=PickingMode.Ignore};lead.AddToClassList("anatomy-leader");lead.style.top=position.y+24;
    if(position.x>0)lead.style.right=103;else lead.style.left=103;map.Add(lead);
    var dot=new VisualElement{pickingMode=PickingMode.Ignore};dot.AddToClassList("anatomy-node");dot.style.top=position.y+20;
    if(position.x>0)dot.style.right=127;else dot.style.left=127;map.Add(dot);
   }
   var inspector=new VisualElement{name="equipment-inspector"};inspector.AddToClassList("equipment-inspector");layout.Add(inspector);
   if(selectedSlot==null){Copy(inspector,"Select a body slot to inspect its equipment.");return;}
   string equipped=Character.Equipped(selectedSlot);
   Copy(inspector,SlotName(selectedSlot).ToUpperInvariant(),"equipment-inspector-heading");
   Copy(inspector,ItemName(equipped),"equipment-inspector-title");
   if(equipped==null)
   {
    Copy(inspector,implants?"No implant installed. Select a compatible implant from your pack and choose Equip selected. Each implant supports three augmentations.":"No armour fitted. Select a compatible component from your pack and choose Equip selected.");
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
  static Vector2 AnatomyPosition(string id,int fallback,bool implants)
  {
   string part=id.Contains("_")?id.Substring(id.IndexOf('_')+1):id;
   if(implants)
   {
    switch(part){case "head":return new Vector2(0,12);case "arms":return new Vector2(1,83);case "chest":return new Vector2(0,142);case "wrist":return new Vector2(1,212);case "waist":return new Vector2(0,271);case "hand":return new Vector2(1,326);case "legs":return new Vector2(0,391);case "feet":return new Vector2(1,455);}
   }
   else
   {
    switch(part){case "head":return new Vector2(0,12);case "arms":return new Vector2(1, 90);case "chest":return new Vector2(0,153);case "hands":return new Vector2(1,236);case "legs":return new Vector2(0,320);case "feet":return new Vector2(1,434);case "storage":return new Vector2(1,153);}
   }
   return new Vector2(fallback%2,12+fallback*59);
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
   var icon=new VisualElement{pickingMode=PickingMode.Ignore};icon.AddToClassList("character-slot-icon");icon.AddToClassList(session.Shop.Spec(item)?.icon??"pack-icon");b.Add(icon);
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
    CancelDrag();pointer=e.pointerId;origin=e.position;source=element;dragItem=item;dragSlot=slot;dragSocket=socket;dragWeapon=weapon;
    source.CapturePointer(pointer);
   },TrickleDown.TrickleDown);
   element.RegisterCallback<PointerMoveEvent>(Move,TrickleDown.TrickleDown);
   element.RegisterCallback<PointerUpEvent>(Drop,TrickleDown.TrickleDown);
   element.RegisterCallback<MouseMoveEvent>(e=>MoveAt(e.mousePosition),TrickleDown.TrickleDown);
   element.RegisterCallback<MouseUpEvent>(e=>{if(pointer>=0&&e.button==0){bool wasDragging=dragging;DropAt(e.mousePosition);if(wasDragging)e.StopImmediatePropagation();}},TrickleDown.TrickleDown);
   element.RegisterCallback<PointerCancelEvent>(_=>CancelDrag());
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
   if(!dragging)
   {
    dragging=true;ghost=new Label(ItemName(dragItem)){pickingMode=PickingMode.Ignore};ghost.AddToClassList("equipment-drag-ghost");root.Add(ghost);
   }
   var p=root.WorldToLocal(position);ghost.style.left=p.x+14;ghost.style.top=p.y+14;
  }
  void Drop(PointerUpEvent e)
  {
   if(pointer!=e.pointerId)return;
   bool wasDragging=dragging;DropAt(e.position);if(wasDragging)e.StopImmediatePropagation();
  }
  void DropAt(Vector2 position)
  {
   if(!dragging){CancelDrag();return;}
   var target=root.panel?.Pick(position);Target destination=null;bool pack=false;
   for(var v=target;v!=null;v=v.parent){if(v.userData is Target t)destination=t;if(v.name=="pack-col")pack=true;}
   string item=dragItem,slot=dragSlot,socket=dragSocket,weapon=dragWeapon;CancelDrag();
   if(destination!=null)Place(item,slot,socket,weapon,destination.slot,destination.socket,destination.weapon);
   else if(pack&&(slot!=null||socket!=null))
   {
    string reason;bool ok=socket!=null?Craft.TryRemove(weapon,socket,out reason):Character.TryUnequip(slot,out reason);Result(ok,reason,"Returned to pack.");
   }
   else Result(false,"Drop onto an equipment slot, a compatible socket, or the pack.",null);
  }
  public void CancelDrag()
  {
   if(pointer>=0&&source!=null&&source.HasPointerCapture(pointer))source.ReleasePointer(pointer);
   ghost?.RemoveFromHierarchy();ghost=null;pointer=-1;dragging=false;source=null;dragItem=dragSlot=dragSocket=dragWeapon=null;
  }
 }
}
