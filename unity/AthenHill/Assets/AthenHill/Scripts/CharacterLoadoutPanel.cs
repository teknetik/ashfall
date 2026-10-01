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
    string value=name;var tab=new Button(()=>{section=value;selectedSlot=null;selectedSocket=null;selectedWeapon=null;signature=null;Refresh();}){text=name,name="character-tab-"+name.ToLowerInvariant()};
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
   capacity.text=$"CARRY {Character.CarryWeight:0.#} / {Character.CarryCapacity:0.#} kg   PACK {Character.PackWeight:0.#} / {Character.StorageCapacity:0.#} kg";
   capacity.EnableInClassList("overburdened",Character.Overburdened);UpdateVitals();
   foreach(var child in tabs.Children())child.EnableInClassList("active-tab",child.name=="character-tab-"+section.ToLowerInvariant());
   string next=section+"|"+Character.AttributePoints+":"+Character.SkillPoints+"|"+string.Join(";",Character.Data.slots.Select(s=>s.id+":"+Character.Equipped(s.id)))+"|"+
    (Craft==null?"":string.Join(";",new[]{"primary","secondary"}.Select(s=>WeaponSignature(Character.Equipped(s)))))+"|"+
    string.Join(";",Character.Data.attributes.Select(a=>Character.Attribute(a.id)))+"|"+string.Join(";",Character.Data.skills.Select(s=>Character.Skill(s.id)))+"|"+
    string.Join(";",Character.Data.derivedStats.Select(s=>Character.Stat(s.id)))+"|"+(crafting&&crafting.combat?crafting.combat.ActiveSlot:"");
   if(signature!=next)
   {
    signature=next;var focus=(root.focusController?.focusedElement as VisualElement)?.name;body.Clear();
    if(section=="STATS")BuildStats();else BuildEquipment();
    if(focus!=null)root.schedule.Execute(()=>{var target=root.Q(focus);if(target!=null&&target.enabledInHierarchy)target.Focus();else root.Q("character-tab-"+section.ToLowerInvariant())?.Focus();});
   }
   foreach(var cell in body.Query<Button>(className:"character-slot").ToList())cell.EnableInClassList("selected",cell.name=="equipment-"+selectedSlot||cell.name=="socket-"+selectedSocket);
   selection.text=selectedSlot!=null?SlotName(selectedSlot):selectedSocket!=null?"Socket: "+Craft?.Data.SlotName(selectedSocket):"";
   root.Q("character-equip").SetEnabled(section!="STATS"&&(selectedSlot!=null||selectedSocket!=null)&&selectedItem()!=null);
   root.Q("character-remove").SetEnabled(selectedSlot!=null&&Character.Equipped(selectedSlot)!=null||selectedSocket!=null&&Craft?.GetLoadout(selectedWeapon)?.Fitted(selectedSocket)!=null);
   root.Q("character-upgrade").style.display=section=="IMPLANTS"?DisplayStyle.Flex:DisplayStyle.None;
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
   foreach(var slot in Character.Data.slots.Where(s=>s.section==section||section=="ARMOUR"&&s.section=="STORAGE"))
   {
    string id=slot.id,item=Character.Equipped(id);
    var cell=EquipmentButton("equipment-"+id,slot.label,item,()=>{selectedSlot=id;selectedSocket=null;selectedWeapon=null;Refresh();});
    cell.userData=new Target{slot=id};BindDrag(cell,item,id,null,null);body.Add(cell);
    if((id=="primary"||id=="secondary")&&item!=null&&crafting&&crafting.combat)
    {
     var combat=crafting.combat;
     AddAction(body,combat.ActiveSlot==id?"Active weapon":"Make active",()=>{bool ok=combat.SelectWeapon(id);Result(ok,"This weapon is unavailable.","Active weapon changed.");},"activate-"+id);
    }
    if(item!=null)
    {
     var info=Character.Equipment(item);
     if(info!=null){var line=new Label(DescribeItem(item));line.AddToClassList("equipment-description");body.Add(line);}
     if(!Character.IsOperating(id,out string reason)){var warning=new Label(reason);warning.AddToClassList("character-result");warning.AddToClassList("rejected");body.Add(warning);}
    }
    var weapon=Craft?.FindWeapon(item);var loadout=weapon!=null?Craft.GetLoadout(weapon.id):null;
    if(loadout!=null)
    {
     Heading("MOD SOCKETS");
     foreach(var socket in loadout.Slots)
     {
      string key=socket,mod=loadout.Fitted(key),weaponId=weapon.id;
      var socketCell=EquipmentButton("socket-"+key,Craft.Data.SlotName(key),mod,()=>{selectedSocket=key;selectedSlot=null;selectedWeapon=weaponId;Refresh();});
      socketCell.userData=new Target{socket=key,weapon=weaponId};BindDrag(socketCell,mod,null,key,weaponId);body.Add(socketCell);
     }
     Heading("WEAPON STATS");
     var effective=loadout.WithCharacter(Character);
     foreach(var statId in WeaponStats.Ids)
     {
      int index=WeaponStats.IndexOf(statId);
      var stat=Craft.Data.statLabels?.FirstOrDefault(x=>x.stat==statId);
      string label=stat?.label??string.Concat(statId.Select((ch,i)=>i>0&&char.IsUpper(ch)?" "+char.ToLowerInvariant(ch):ch.ToString()));
      float mod=loadout.Stats[index]-loadout.Base[index],character=effective[index]-loadout.Stats[index];
      var row=new Foldout{text=$"{label}: {CraftingText.FormatStat(stat,effective[index])}",value=false,name="weapon-stat-"+statId};
      row.AddToClassList("character-breakdown");
      row.Add(new Label($"Base {CraftingText.FormatStat(stat,loadout.Base[index])}   Mod {mod:+0.##;-0.##;0}   Character {character:+0.##;-0.##;0}   Final {CraftingText.FormatStat(stat,effective[index])}"));
      body.Add(row);
     }
    }
   }
  }
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
   if(selectedSocket!=null&&Craft!=null)ok=Craft.TryRemove(selectedWeapon,selectedSocket,out reason);
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
    if(fromSocket!=null)reason="Weapon mods belong in a compatible weapon socket.";
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
