using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CharacterState
 {
  public int version=1,level=1,experience,attributePoints,skillPoints;
  public CountEntry[] attributes,skills;
  public SlotEntry[] equipped;
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
  readonly Dictionary<string,CharacterModifier[]> effects=new Dictionary<string,CharacterModifier[]>();
  Dictionary<string,CharacterStatBreakdown> calculated=new Dictionary<string,CharacterStatBreakdown>();
  Dictionary<string,CharacterStatBreakdown> pendingValues;
  Dictionary<string,string> pendingEquipment;
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
   attributes.Clear();skills.Clear();equipped.Clear();effects.Clear();Level=1;Experience=0;
   AttributePoints=Math.Max(0,Data.initialAttributePoints);SkillPoints=Math.Max(0,Data.initialSkillPoints);
   foreach(var a in Data.attributes)attributes[a.id]=Math.Max(0,a.initial);
   foreach(var s in Data.skills)skills[s.id]=Math.Max(0,s.initial);
   foreach(var e in Data.initialEquipment)if(e!=null&&Accepts(e.itemId,e.slot)&&pack.Spec(e.itemId)!=null)equipped[e.slot]=e.itemId;
  }
  public CharacterEquipment Equipment(string itemId)=>Data.Equipment(itemId);
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
  public float CarryWeight=>PackWeight+equipped.Values.Sum(Weight)+AttachmentWeight;
  float AttachmentWeight=>Mathf.Max(0,attachmentWeight?.Invoke()??0);
  public float PackWeightKg=>PackWeight;
  public float CarriedWeightKg=>CarryWeight;
  public float CarryCapacityKg=>CarryCapacity;
  public float CarryCapacity=>Stat("carryCapacity");
  public float StorageCapacity=>Stat("storageCapacity");
  public bool Overburdened=>CarryWeight>CarryCapacity||PackWeight>StorageCapacity;
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
   return Commit(next,delta,0,out reason);
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
   return Commit(next,new[]{new KeyValuePair<string,int>(id,1)},0,out reason);
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
   return Commit(next,Array.Empty<KeyValuePair<string,int>>(),0,out reason);
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
   return Commit(next,(current.upgradeIngredients??Array.Empty<CountEntry>()).Select(x=>new KeyValuePair<string,int>(x.id,-x.count)),-current.upgradeCredits,out reason);
  }
  bool Commit(Dictionary<string,string> next,IEnumerable<KeyValuePair<string,int>> changes,int creditDelta,out string reason)
  {
   var deltas=changes.ToArray();var values=Calculate(next);
   if(!CanStore(deltas,values,next,out reason))return false;
   pendingValues=values;pendingEquipment=next;
   try {if(!pack.TryApply(deltas,creditDelta,out reason))return false;}
   finally {pendingValues=null;pendingEquipment=null;}
   equipped.Clear();foreach(var e in next)equipped[e.Key]=e.Value;
   calculated=values;Changed?.Invoke();return true;
  }
  public bool CanApplyInventory(IEnumerable<KeyValuePair<string,int>> changes,out string reason)=>CanStore(changes,calculated,equipped,out reason);
  public string CapacityFailure(IReadOnlyDictionary<string,int> futurePack)
  {
   double weight=futurePack.Sum(x=>(double)Weight(x.Key)*x.Value);
   return CapacityReason(weight,pendingValues??calculated,pendingEquipment??equipped);
  }
  string CapacityReason(double packWeight,Dictionary<string,CharacterStatBreakdown> values,IReadOnlyDictionary<string,string> loadout)
  {
   double equippedWeight=loadout.Values.Sum(id=>(double)Weight(id));
   double oldEquippedWeight=equipped.Values.Sum(id=>(double)Weight(id));
   double oldStorage=Math.Max(0,PackWeight-StorageCapacity);
   double oldAttachmentWeight=AttachmentWeight;
   double oldCarry=Math.Max(0,PackWeight+oldEquippedWeight+oldAttachmentWeight-CarryCapacity);
   double storageLimit=values.TryGetValue("storageCapacity",out var storage)?storage.finalValue:double.MaxValue;
   double carryLimit=values.TryGetValue("carryCapacity",out var carry)?carry.finalValue:double.MaxValue;
   if(Math.Max(0,packWeight-storageLimit)>oldStorage+.001)return "Not enough storage capacity.";
   if(Math.Max(0,packWeight+equippedWeight+Math.Max(0,oldAttachmentWeight+pendingAttachmentDelta)-carryLimit)>oldCarry+.001)return "Not enough carrying capacity.";
   return null;
  }
  bool CanStore(IEnumerable<KeyValuePair<string,int>> changes,Dictionary<string,CharacterStatBreakdown> values,IReadOnlyDictionary<string,string> loadout,out string reason)
  {
   double weight=PackWeight;
   foreach(var c in changes)weight+=Weight(c.Key)*(double)c.Value;
   reason=CapacityReason(weight,values,loadout)??"ok";
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
  Dictionary<string,CharacterStatBreakdown> Calculate(Dictionary<string,string> loadout,bool includeEquipment=true)
  {
   var mods=effects.OrderBy(x=>x.Key,StringComparer.Ordinal).SelectMany(x=>x.Value).ToList();
   if(includeEquipment)
   {
    var independent=Calculate(new Dictionary<string,string>(),false);
    var active=new List<CharacterEquipment>();
    foreach(var id in loadout.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>x.Value))
    {
     var item=Equipment(id);if(item==null||!Meets(item.operatingRequirements,independent,out _))continue;
     active.Add(item);mods.AddRange(item.modifiers??Array.Empty<CharacterModifier>());
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
  public CharacterState Capture()=>new CharacterState{level=Level,experience=Experience,attributePoints=AttributePoints,skillPoints=SkillPoints,attributes=attributes.OrderBy(x=>x.Key).Select(x=>new CountEntry{id=x.Key,count=x.Value}).ToArray(),skills=skills.OrderBy(x=>x.Key).Select(x=>new CountEntry{id=x.Key,count=x.Value}).ToArray(),equipped=equipped.OrderBy(x=>x.Key).Select(x=>new SlotEntry{slot=x.Key,itemId=x.Value}).ToArray()};
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
   }
   Recalculate();return skipped;
  }
 }
}
