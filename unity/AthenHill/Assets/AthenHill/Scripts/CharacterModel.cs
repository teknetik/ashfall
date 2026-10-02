using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CharacterModificationEntry
 {
  public string slot,itemId;
  public int socketIndex;
 }
 [Serializable] public class CharacterState
 {
  public const int CurrentVersion=2;
  public int version=CurrentVersion,level=1,experience,attributePoints,skillPoints;
  public CountEntry[] attributes,skills;
  public SlotEntry[] equipped;
  public CharacterModificationEntry[] modifications;
 }
 public sealed class CharacterStatBreakdown
 {
  public float baseValue,progression,dependencies,flat,percent,finalValue;
 }
 /// Authoritative character inputs. Inventory and equipment commit together before observers are notified.
 public sealed class CharacterModel
 {
  readonly ShopModel pack;
  readonly Dictionary<string,int> attributes=new Dictionary<string,int>(),skills=new Dictionary<string,int>();
  readonly Dictionary<string,string> equipped=new Dictionary<string,string>();
  readonly Dictionary<string,string> modifications=new Dictionary<string,string>();
  readonly Dictionary<string,CharacterModifier[]> effects=new Dictionary<string,CharacterModifier[]>();
  Dictionary<string,CharacterStatBreakdown> calculated=new Dictionary<string,CharacterStatBreakdown>();
  Dictionary<string,CharacterStatBreakdown> pendingValues;
  Dictionary<string,string> pendingEquipment,pendingModifications;
  Func<float> attachmentWeight;
  float pendingAttachmentDelta;
  public CharacterCatalog Data {get;}
  public int Level {get;private set;}=1;
  public int Experience {get;private set;}
  public int AttributePoints {get;private set;}
  public int SkillPoints {get;private set;}
  public IReadOnlyDictionary<string,string> EquippedItems=>equipped;
  public event Action Changed;
  public Func<CharacterEquipment,string,bool> InstallationAllowed {get;set;}
  public CharacterModel(CharacterCatalog data,ShopModel pack)
  {
   Data=data??throw new ArgumentNullException(nameof(data));this.pack=pack??throw new ArgumentNullException(nameof(pack));
   Reset();Recalculate();
  }
  void Reset()
  {
   attributes.Clear();skills.Clear();equipped.Clear();modifications.Clear();effects.Clear();Level=1;Experience=0;
   AttributePoints=Math.Max(0,Data.initialAttributePoints);SkillPoints=Math.Max(0,Data.initialSkillPoints);
   foreach(var a in Data.attributes)attributes[a.id]=Math.Max(0,a.initial);
   foreach(var s in Data.skills)skills[s.id]=Math.Max(0,s.initial);
   foreach(var e in Data.initialEquipment)if(e!=null&&Accepts(e.itemId,e.slot)&&pack.Spec(e.itemId)!=null)equipped[e.slot]=e.itemId;
  }
  public CharacterEquipment Equipment(string itemId)=>Data.Equipment(itemId);
  public CharacterModification Modification(string itemId)=>Data.Modification(itemId);
  public int PackSlotsUsed=>pack.Carried.Count();
  public int PackSlotCapacity=>SlotCapacity(calculated);
  int SlotCapacity(Dictionary<string,CharacterStatBreakdown> values)=>Math.Max(1,Data.basePackSlots+Mathf.FloorToInt(values.TryGetValue("packSlots",out var slots)?slots.finalValue:0));
  static string ModificationKey(string slot,int index)=>slot+":"+index;
  static readonly CharacterModificationSocket[] ImplantSockets={
   new CharacterModificationSocket{id="augmentation_1",label="Augmentation 1",type="implant"},
   new CharacterModificationSocket{id="augmentation_2",label="Augmentation 2",type="implant"},
   new CharacterModificationSocket{id="augmentation_3",label="Augmentation 3",type="implant"}};
  IReadOnlyList<CharacterModificationSocket> Sockets(string itemId,string slot)
  {
   var item=Equipment(itemId);
   if(item==null||!Accepts(itemId,slot))return Array.Empty<CharacterModificationSocket>();
   if(slot.StartsWith("implant_",StringComparison.Ordinal))return ImplantSockets;
   return item.modificationSockets??Array.Empty<CharacterModificationSocket>();
  }
  public IReadOnlyList<CharacterModificationSocket> ModificationSockets(string equipmentSlot)=>Sockets(Equipped(equipmentSlot),equipmentSlot);
  public string InstalledModification(string equipmentSlot,int socketIndex)=>equipmentSlot!=null&&modifications.TryGetValue(ModificationKey(equipmentSlot,socketIndex),out var id)?id:null;
  bool AcceptsModification(string hostId,string slot,int index,string itemId)
  {
   var sockets=Sockets(hostId,slot);var item=Modification(itemId);
   return item!=null&&pack.Spec(itemId)!=null&&index>=0&&index<sockets.Count&&sockets[index]!=null&&
    (item.slots==null||item.slots.Length==0||item.slots.Contains(slot))&&item.socketTypes?.Contains(sockets[index].type)==true;
  }
  public bool CanInstallModification(string equipmentSlot,int socketIndex,string itemId,out string reason)
  {
   if(!AcceptsModification(Equipped(equipmentSlot),equipmentSlot,socketIndex,itemId)){reason="This component is incompatible with that socket.";return false;}
   if(InstalledModification(equipmentSlot,socketIndex)==itemId){reason="That component is already installed.";return false;}
   if(pack.Quantity(itemId)<1){reason="This component is not in your inventory.";return false;}
   var next=new Dictionary<string,string>(modifications);next.Remove(ModificationKey(equipmentSlot,socketIndex));
   if(!CanInstall(Equipment(Equipped(equipmentSlot)),equipmentSlot,Calculate(equipped,true,next),out reason))return false;
   return Meets(Modification(itemId).requirements,Calculate(equipped,true,next),out reason);
  }
  public bool TryInstallModification(string equipmentSlot,int socketIndex,string itemId,out string reason)
  {
   if(!CanInstallModification(equipmentSlot,socketIndex,itemId,out reason))return false;
   var next=new Dictionary<string,string>(modifications);var key=ModificationKey(equipmentSlot,socketIndex);
   var changes=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(next.TryGetValue(key,out var previous))changes.Add(new KeyValuePair<string,int>(previous,1));
   next[key]=itemId;
   return Commit(new Dictionary<string,string>(equipped),changes,0,out reason,next);
  }
  public bool TryRemoveModification(string equipmentSlot,int socketIndex,out string reason)
  {
   var id=InstalledModification(equipmentSlot,socketIndex);
   if(id==null){reason="That component socket is empty.";return false;}
   var next=new Dictionary<string,string>(modifications);next.Remove(ModificationKey(equipmentSlot,socketIndex));
   return Commit(new Dictionary<string,string>(equipped),new[]{new KeyValuePair<string,int>(id,1)},0,out reason,next);
  }
  void ReturnModifications(string slot,Dictionary<string,string> next,List<KeyValuePair<string,int>> changes)
  {
   foreach(var entry in next.Where(x=>x.Key.StartsWith(slot+":",StringComparison.Ordinal)).ToArray())
   {changes.Add(new KeyValuePair<string,int>(entry.Value,1));next.Remove(entry.Key);}
  }
  float ModificationWeight(IReadOnlyDictionary<string,string> installed)=>installed.Values.Sum(Weight);
  public string Equipped(string slot)=>slot!=null&&equipped.TryGetValue(slot,out var id)?id:null;
  public int BaseAttribute(string id)=>id!=null&&attributes.TryGetValue(id,out var value)?value:0;
  public int TrainedSkill(string id)=>id!=null&&skills.TryGetValue(id,out var value)?value:0;
  public float Attribute(string id)=>Stat(id);
  public float Skill(string id)=>Stat(id);
  public float Stat(string id)=>id!=null&&calculated.TryGetValue(id,out var value)?value.finalValue:0;
  public CharacterStatBreakdown Breakdown(string id)
  {
   if(id==null||!calculated.TryGetValue(id,out var b))return new CharacterStatBreakdown();
   return new CharacterStatBreakdown{baseValue=b.baseValue,progression=b.progression,dependencies=b.dependencies,flat=b.flat,percent=b.percent,finalValue=b.finalValue};
  }
  float Weight(string id)=>Mathf.Max(0,pack.Spec(id)?.weightKg??Data.Weight(id));
  public float PackWeight=>(float)pack.Carried.Sum(x=>(double)Weight(x.Key)*x.Value);
  public float CarryWeight=>PackWeight+equipped.Values.Sum(Weight)+AttachmentWeight+ModificationWeight(modifications);
  float AttachmentWeight=>Mathf.Max(0,attachmentWeight?.Invoke()??0);
  public float PackWeightKg=>PackWeight;
  public float CarriedWeightKg=>CarryWeight;
  public float CarryCapacityKg=>CarryCapacity;
  public float CarryCapacity=>Stat("carryCapacity");
  public float StorageCapacity=>Stat("storageCapacity");
  public bool Overburdened=>CarryWeight>CarryCapacity||PackWeight>StorageCapacity||PackSlotsUsed>PackSlotCapacity;
  public void BindAttachmentWeight(Func<float> source){attachmentWeight=source;Changed?.Invoke();}
  internal bool TryTransferAttachment(IEnumerable<KeyValuePair<string,int>> changes,float attachmentDelta,out string reason)
  {
   pendingAttachmentDelta=attachmentDelta;
   try{return pack.TryApply(changes,0,out reason);}
   finally{pendingAttachmentDelta=0;}
  }
  public bool Accepts(string itemId,string slot)=>slot!=null&&Data.slots.Any(x=>x.id==slot)&&Equipment(itemId)?.slots?.Contains(slot)==true;
  public bool Meets(CharacterRequirement[] requirements,out string reason)=>Meets(requirements,calculated,out reason);
  bool Meets(CharacterRequirement[] requirements,Dictionary<string,CharacterStatBreakdown> values,out string reason)
  {
   foreach(var r in requirements??Array.Empty<CharacterRequirement>())
   {
    if(r==null||string.IsNullOrEmpty(r.stat)||!values.TryGetValue(r.stat,out var value)||value.finalValue+.0001f<r.minimum)
    {reason=r==null?"Invalid requirement.":$"Requires {Data.Label(r.stat)} {r.minimum:0.#}.";return false;}
   }
   reason="ok";return true;
  }
  public bool IsOperating(string slot,out string reason)
  {
   var item=Equipment(Equipped(slot));
   if(item==null){reason="Empty slot.";return false;}
   return Meets(item.operatingRequirements,Calculate(new Dictionary<string,string>(),false),out reason);
  }
  public bool CanEquip(string itemId,string slot,out string reason)
  {
   if(!Accepts(itemId,slot)){reason="This item is incompatible with that slot.";return false;}
   if(Equipped(slot)==itemId){reason="That item is already equipped.";return false;}
   if(pack.Quantity(itemId)<1){reason="This item is not in your inventory.";return false;}
   var next=new Dictionary<string,string>(equipped);next.Remove(slot);
   return CanInstall(Equipment(itemId),slot,Calculate(next),out reason);
  }
  bool CanInstall(CharacterEquipment item,string slot,Dictionary<string,CharacterStatBreakdown> values,out string reason)
  {
   if(!Meets(item.requirements,values,out reason))return false;
   if((!string.IsNullOrEmpty(item.installationFacility)&&InstallationAllowed==null)||(InstallationAllowed!=null&&!InstallationAllowed(item,slot)))
   {reason="This installation requires access to "+(string.IsNullOrEmpty(item.installationFacility)?"a specialist facility.":item.installationFacility+".");return false;}
   reason="ok";return true;
  }
  public bool TryEquip(string itemId,string slot,out string reason)
  {
   if(!CanEquip(itemId,slot,out reason))return false;
   var next=new Dictionary<string,string>(equipped);var delta=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(itemId,-1)};
   if(next.TryGetValue(slot,out var old))delta.Add(new KeyValuePair<string,int>(old,1));next[slot]=itemId;
   var nextMods=new Dictionary<string,string>(modifications);ReturnModifications(slot,nextMods,delta);
   return Commit(next,delta,0,out reason,nextMods);
  }
  /// Tutorial/reward grant. Never replaces owned equipment or depends on free inventory space.
  public bool TryGrantEquipped(string itemId,string slot,out string reason)
  {
   if(!Accepts(itemId,slot)||pack.Spec(itemId)==null){reason="This reward is incompatible with that slot.";return false;}
   if(Equipped(slot)!=null){reason="The reward slot is occupied.";return false;}
   if(!CanInstall(Equipment(itemId),slot,calculated,out reason))return false;
   var next=new Dictionary<string,string>(equipped){[slot]=itemId};
   equipped[slot]=itemId;
   calculated=Calculate(next);
   Changed?.Invoke();reason="ok";return true;
  }
  public bool TryUnequip(string slot,out string reason)
  {
   var id=Equipped(slot);if(id==null){reason="That slot is empty.";return false;}
   var next=new Dictionary<string,string>(equipped);next.Remove(slot);
   var changes=new List<KeyValuePair<string,int>>{new KeyValuePair<string,int>(id,1)};
   var nextMods=new Dictionary<string,string>(modifications);ReturnModifications(slot,nextMods,changes);
   return Commit(next,changes,0,out reason,nextMods);
  }
  public bool TryMove(string source,string destination,out string reason)
  {
   var id=Equipped(source);var previous=Equipped(destination);
   if(source==destination||id==null||!Accepts(id,destination)||(previous!=null&&!Accepts(previous,source)))
   {reason="These equipment slots are incompatible.";return false;}
   var next=new Dictionary<string,string>(equipped);next.Remove(source);next.Remove(destination);
   var values=Calculate(next);
   if(!CanInstall(Equipment(id),destination,values,out reason)||(previous!=null&&!CanInstall(Equipment(previous),source,values,out reason)))return false;
   next[destination]=id;if(previous!=null)next[source]=previous;
   var nextMods=new Dictionary<string,string>(modifications);
   var changes=new List<KeyValuePair<string,int>>();
   ReturnModifications(source,nextMods,changes);ReturnModifications(destination,nextMods,changes);changes.Clear();
   foreach(var move in new[]{new KeyValuePair<string,string>(source,destination),new KeyValuePair<string,string>(destination,source)})
    foreach(var entry in modifications.Where(x=>x.Key.StartsWith(move.Key+":",StringComparison.Ordinal)))
    {
     if(!int.TryParse(entry.Key.Substring(move.Key.Length+1),out int index)||!next.TryGetValue(move.Value,out var host)||!AcceptsModification(host,move.Value,index,entry.Value))
     {reason="An installed component is incompatible with the destination slot.";return false;}
     nextMods[ModificationKey(move.Value,index)]=entry.Value;
    }
   return Commit(next,changes,0,out reason,nextMods);
  }
  public bool TryUpgradeImplant(string slot,out string reason)
  {
   var current=Equipment(Equipped(slot));var nextItem=Equipment(current?.upgradeToItemId);
   if(slot==null||!slot.StartsWith("implant_",StringComparison.Ordinal)||current==null||nextItem==null||pack.Spec(nextItem.itemId)==null||!Accepts(nextItem.itemId,slot))
   {reason="No further implant upgrade is available.";return false;}
   if(current.upgradeCredits<0||(current.upgradeIngredients??Array.Empty<CountEntry>()).Any(x=>x==null||x.count<1))
   {reason="This upgrade has invalid costs.";return false;}
   var next=new Dictionary<string,string>(equipped);next.Remove(slot);
   if(!CanInstall(nextItem,slot,Calculate(next),out reason))return false;
   next[slot]=nextItem.itemId;
   var nextMods=new Dictionary<string,string>(modifications);
   var changes=(current.upgradeIngredients??Array.Empty<CountEntry>()).Select(x=>new KeyValuePair<string,int>(x.id,-x.count)).ToList();
   for(int index=0;index<ModificationSockets(slot).Count;index++)
    if(nextMods.TryGetValue(ModificationKey(slot,index),out var module)&&!AcceptsModification(nextItem.itemId,slot,index,module))
    {changes.Add(new KeyValuePair<string,int>(module,1));nextMods.Remove(ModificationKey(slot,index));}
   return Commit(next,changes,-current.upgradeCredits,out reason,nextMods);
  }
  bool Commit(Dictionary<string,string> next,IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out string reason,Dictionary<string,string> nextMods=null)
  {
   nextMods=nextMods??new Dictionary<string,string>(modifications);
   var deltas=changes.ToArray();var values=Calculate(next,true,nextMods);
   if(!CanStore(deltas,values,next,out reason,nextMods))return false;
   pendingValues=values;pendingEquipment=next;pendingModifications=nextMods;
   try {if(!pack.TryApply(deltas,creditDelta,out reason))return false;}
   finally {pendingValues=null;pendingEquipment=null;pendingModifications=null;}
   equipped.Clear();foreach(var e in next)equipped[e.Key]=e.Value;
   modifications.Clear();foreach(var entry in nextMods)modifications[entry.Key]=entry.Value;
   calculated=values;Changed?.Invoke();return true;
  }
  public bool CanApplyInventory(IEnumerable<KeyValuePair<string,int>> changes,out string reason)=>CanStore(changes,calculated,equipped,out reason);
  public string CapacityFailure(IReadOnlyDictionary<string,int> futurePack)
  {
   double weight=futurePack.Sum(x=>(double)Weight(x.Key)*x.Value);
   return CapacityReason(weight,futurePack.Count(x=>x.Value>0),pendingValues??calculated,pendingEquipment??equipped,pendingModifications??modifications);
  }
  string CapacityReason(double packWeight,int packSlots,Dictionary<string,CharacterStatBreakdown> values,IReadOnlyDictionary<string,string> loadout,IReadOnlyDictionary<string,string> installed)
  {
   double equippedWeight=loadout.Values.Sum(id=>(double)Weight(id));
   double oldEquippedWeight=equipped.Values.Sum(id=>(double)Weight(id));
   double oldStorage=Math.Max(0,PackWeight-StorageCapacity);
   double oldAttachmentWeight=AttachmentWeight+ModificationWeight(modifications);
   double oldCarry=Math.Max(0,PackWeight+oldEquippedWeight+oldAttachmentWeight-CarryCapacity);
   double storageLimit=values.TryGetValue("storageCapacity",out var storage)?storage.finalValue:double.MaxValue;
   double carryLimit=values.TryGetValue("carryCapacity",out var carry)?carry.finalValue:double.MaxValue;
   if(Math.Max(0,packSlots-SlotCapacity(values))>Math.Max(0,PackSlotsUsed-PackSlotCapacity))return "Not enough pack slot capacity.";
   if(Math.Max(0,packWeight-storageLimit)>oldStorage+.001)return "Not enough storage capacity.";
   if(Math.Max(0,packWeight+equippedWeight+Math.Max(0,AttachmentWeight+pendingAttachmentDelta)+ModificationWeight(installed)-carryLimit)>oldCarry+.001)return "Not enough carrying capacity.";
   return null;
  }
  bool CanStore(IEnumerable<KeyValuePair<string,int>> changes,Dictionary<string,CharacterStatBreakdown> values,IReadOnlyDictionary<string,string> loadout,out string reason,IReadOnlyDictionary<string,string> installed=null)
  {
   var future=pack.Carried.ToDictionary(x=>x.Key,x=>(long)x.Value);
   foreach(var c in changes)if(c.Key!=null)future[c.Key]=(future.TryGetValue(c.Key,out var quantity)?quantity:0)+c.Value;
   double weight=future.Sum(x=>(double)Weight(x.Key)*x.Value);
   reason=CapacityReason(weight,future.Count(x=>x.Value>0),values,loadout,installed??modifications)??"ok";
   return reason=="ok";
  }
  public bool TryRaiseAttribute(string id,out string reason)
  {
   var a=Data.attributes.FirstOrDefault(x=>x.id==id);
   if(a==null||a.cost<1||BaseAttribute(id)>=a.maximum){reason="This attribute cannot be increased.";return false;}
   if(AttributePoints<a.cost){reason="Not enough attribute points.";return false;}
   AttributePoints-=a.cost;attributes[id]++;Recalculate();reason="ok";return true;
  }
  public bool TryRaiseSkill(string id,out string reason)
  {
   var s=Data.skills.FirstOrDefault(x=>x.id==id);
   if(s==null||s.cost<1||s.trainingStep<1||TrainedSkill(id)>=s.maximum){reason="This skill cannot be trained further.";return false;}
   if(SkillPoints<s.cost){reason="Not enough skill points.";return false;}
   SkillPoints-=s.cost;skills[id]=(int)Math.Min(s.maximum,(long)skills[id]+s.trainingStep);Recalculate();reason="ok";return true;
  }
  public bool GrantExperience(int amount,out string reason)
  {
   if(amount<0||Data.experiencePerLevel<1){reason="Invalid experience award.";return false;}
   long total=(long)Experience+amount,levels=total/Data.experiencePerLevel;
   long a=(long)AttributePoints+levels*Math.Max(0,Data.attributePointsPerLevel),s=(long)SkillPoints+levels*Math.Max(0,Data.skillPointsPerLevel);
   if((long)Level+levels>int.MaxValue||a>int.MaxValue||s>int.MaxValue){reason="Progression limit reached.";return false;}
   Experience=(int)(total%Data.experiencePerLevel);Level+=(int)levels;AttributePoints=(int)a;SkillPoints=(int)s;Recalculate();reason="ok";return true;
  }
  public void SetEffects(string source,IEnumerable<CharacterModifier> modifiers)
  {
   if(string.IsNullOrEmpty(source))throw new ArgumentException("Effects require a stable source ID.",nameof(source));
   if(modifiers==null)effects.Remove(source);
   else effects[source]=modifiers.Where(x=>x!=null).Select(x=>new CharacterModifier{stat=x.stat,flat=x.flat,percent=x.percent}).ToArray();
   Recalculate();
  }
  public void Recalculate(){calculated=Calculate(equipped);Changed?.Invoke();}
  Dictionary<string,CharacterStatBreakdown> Calculate(Dictionary<string,string> loadout,bool includeEquipment=true,IReadOnlyDictionary<string,string> installed=null)
  {
   var mods=effects.OrderBy(x=>x.Key,StringComparer.Ordinal).SelectMany(x=>x.Value).ToList();
   if(includeEquipment)
   {
    var independent=Calculate(new Dictionary<string,string>(),false);
    var active=new List<CharacterEquipment>();
    foreach(var equippedItem in loadout.OrderBy(x=>x.Key,StringComparer.Ordinal))
    {
     var item=Equipment(equippedItem.Value);if(item==null||!Meets(item.operatingRequirements,independent,out _))continue;
     active.Add(item);mods.AddRange(item.modifiers??Array.Empty<CharacterModifier>());
     var sockets=Sockets(item.itemId,equippedItem.Key);
     for(int index=0;index<sockets.Count;index++)
      if((installed??modifications).TryGetValue(ModificationKey(equippedItem.Key,index),out var moduleId)&&AcceptsModification(item.itemId,equippedItem.Key,index,moduleId))
      {
       var module=Modification(moduleId);
       if(Meets(module.operatingRequirements,independent,out _))mods.AddRange(module.modifiers??Array.Empty<CharacterModifier>());
      }
    }
    var effectiveAttributes=new Dictionary<string,CharacterStatBreakdown>();
    foreach(var a in Data.attributes)AddStat(effectiveAttributes,mods,a.id,a.initial,BaseAttribute(a.id)-a.initial,null,0,100000);
    foreach(var item in active)
    {
     if((effectiveAttributes.TryGetValue("strength",out var str)&&str.finalValue<item.comfortableStrength)||(effectiveAttributes.TryGetValue("endurance",out var end)&&end.finalValue<item.comfortableEndurance))
     {
      mods.Add(new CharacterModifier{stat="movementSpeed",percent=-Mathf.Clamp01(item.movementPenalty)});
      mods.Add(new CharacterModifier{stat="stamina",percent=-Mathf.Clamp01(item.staminaPenalty)});
     }
    }
   }
   var result=new Dictionary<string,CharacterStatBreakdown>();
   foreach(var a in Data.attributes)AddStat(result,mods,a.id,a.initial,BaseAttribute(a.id)-a.initial,null,0,100000);
   foreach(var s in Data.skills)AddStat(result,mods,s.id,s.initial,TrainedSkill(s.id)-s.initial,s.dependencies,0,100000);
   foreach(var d in Data.derivedStats)AddStat(result,mods,d.id,d.initial,d.perLevel*(Level-1),d.dependencies,d.minimum,d.maximum);
   return result;
  }
  static void AddStat(Dictionary<string,CharacterStatBreakdown> result,List<CharacterModifier> mods,string id,float basis,float progression,CharacterDependency[] dependencies,float minimum,float maximum)
  {
   var value=new CharacterStatBreakdown{baseValue=basis,progression=progression};
   foreach(var d in dependencies??Array.Empty<CharacterDependency>())if(d!=null&&result.TryGetValue(d.stat,out var source))value.dependencies+=source.finalValue*d.factor;
   foreach(var m in mods)if(m!=null&&m.stat==id){value.flat+=m.flat;value.percent+=m.percent;}
   value.finalValue=Mathf.Clamp((value.baseValue+value.progression+value.dependencies+value.flat)*Mathf.Max(0,1+value.percent),minimum,Mathf.Max(minimum,maximum));
   result[id]=value;
  }
  public CharacterState Capture()=>new CharacterState{level=Level,experience=Experience,attributePoints=AttributePoints,skillPoints=SkillPoints,attributes=attributes.OrderBy(x=>x.Key).Select(x=>new CountEntry{id=x.Key,count=x.Value}).ToArray(),skills=skills.OrderBy(x=>x.Key).Select(x=>new CountEntry{id=x.Key,count=x.Value}).ToArray(),equipped=equipped.OrderBy(x=>x.Key).Select(x=>new SlotEntry{slot=x.Key,itemId=x.Value}).ToArray(),modifications=modifications.OrderBy(x=>x.Key).Select(x=>new CharacterModificationEntry{slot=x.Key.Substring(0,x.Key.LastIndexOf(':')),socketIndex=int.Parse(x.Key.Substring(x.Key.LastIndexOf(':')+1)),itemId=x.Value}).ToArray()};
  public List<string> Restore(CharacterState state)
  {
   Reset();var skipped=new List<string>();
   if(state!=null)
   {
    Level=Math.Max(1,state.level);Experience=Mathf.Clamp(state.experience,0,Math.Max(0,Data.experiencePerLevel-1));AttributePoints=Math.Max(0,state.attributePoints);SkillPoints=Math.Max(0,state.skillPoints);
    foreach(var a in state.attributes??Array.Empty<CountEntry>())if(a!=null){var spec=Data.attributes.FirstOrDefault(x=>x.id==a.id);if(spec!=null)attributes[a.id]=Mathf.Clamp(a.count,0,spec.maximum);else skipped.Add(a.id);}
    foreach(var s in state.skills??Array.Empty<CountEntry>())if(s!=null){var spec=Data.skills.FirstOrDefault(x=>x.id==s.id);if(spec!=null)skills[s.id]=Mathf.Clamp(s.count,0,spec.maximum);else skipped.Add(s.id);}
    equipped.Clear();
    foreach(var e in state.equipped??Array.Empty<SlotEntry>())if(e!=null){if(Accepts(e.itemId,e.slot)&&pack.Spec(e.itemId)!=null&&!equipped.ContainsKey(e.slot))equipped[e.slot]=e.itemId;else skipped.Add(e.itemId);}
    foreach(var entry in state.modifications??Array.Empty<CharacterModificationEntry>())if(entry!=null)
    {
     var key=ModificationKey(entry.slot,entry.socketIndex);
     if(AcceptsModification(Equipped(entry.slot),entry.slot,entry.socketIndex,entry.itemId)&&!modifications.ContainsKey(key))modifications[key]=entry.itemId;
     else skipped.Add(entry.itemId);
    }
   }
   Recalculate();return skipped;
  }
 }
}
