using System;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 public enum ImplantTier { Improvised, Civilian, Industrial, Corporate, Military, Experimental }
 [Serializable] public class CharacterDependency { public string stat; public float factor; }
 [Serializable] public class CharacterModifier { public string stat; public float flat,percent; }
 [Serializable] public class CharacterRequirement { public string stat; public float minimum; }
 [Serializable] public class CharacterAttribute { public string id,label; public int initial=10,maximum=100,cost=1; }
 [Serializable] public class CharacterSkill
 {
  public string id,label,category;
  public int initial,maximum=1200,cost=1,trainingStep=5;
  public CharacterDependency[] dependencies=Array.Empty<CharacterDependency>();
 }
 [Serializable] public class CharacterDerivedStat
 {
  public string id,label,unit;
  public float initial,perLevel,minimum,maximum=100000;
  public CharacterDependency[] dependencies=Array.Empty<CharacterDependency>();
 }
 [Serializable] public class CharacterSlot { public string id,label,section; }
 [Serializable] public class CharacterModificationSocket
 {
  public string id,label,type;
 }
 [Serializable] public class CharacterModification
 {
  public string itemId;
  [Tooltip("Equipment slot IDs. Empty permits any slot whose socket type matches.")]
  public string[] slots=Array.Empty<string>();
  public string[] socketTypes=Array.Empty<string>();
  public CharacterRequirement[] requirements=Array.Empty<CharacterRequirement>();
  public CharacterRequirement[] operatingRequirements=Array.Empty<CharacterRequirement>();
  public CharacterModifier[] modifiers=Array.Empty<CharacterModifier>();
 }
 [Serializable] public class CharacterEquipment
 {
  public string itemId;
  public string[] slots=Array.Empty<string>();
  public ImplantTier tier;
  public int upgradeLevel;
  public float weight;
  [Tooltip("Armour component sockets. Implants always expose exactly three augmentation sockets.")]
  public CharacterModificationSocket[] modificationSockets=Array.Empty<CharacterModificationSocket>();
  public CharacterRequirement[] requirements=Array.Empty<CharacterRequirement>();
  public CharacterRequirement[] operatingRequirements=Array.Empty<CharacterRequirement>();
  public CharacterModifier[] modifiers=Array.Empty<CharacterModifier>();
  [Tooltip("Optional facility ID. Installation policy decides whether that facility is accessible.")]
  public string installationFacility;
  [Tooltip("Upgrade output is a distinct item ID, so its tier and upgrade survive removal, sale and reinstallation.")]
  public string upgradeToItemId;
  public CountEntry[] upgradeIngredients=Array.Empty<CountEntry>();
  public int upgradeCredits;
  [Tooltip("Below this Strength or Endurance, this piece applies its configured movement and stamina penalties.")]
  public float comfortableStrength,comfortableEndurance,movementPenalty,staminaPenalty;
 }
 [Serializable] public class CharacterItemWeight { public string itemId; public float weight; }
 [CreateAssetMenu(menuName="Athen Hill/Character catalog")]
 public sealed class CharacterCatalog:ScriptableObject
 {
  public CharacterAttribute[] attributes=Array.Empty<CharacterAttribute>();
  public CharacterSkill[] skills=Array.Empty<CharacterSkill>();
  [Tooltip("Derived dependencies must reference attributes, skills, or an earlier derived row.")]
  public CharacterDerivedStat[] derivedStats=Array.Empty<CharacterDerivedStat>();
  public CharacterSlot[] slots=Array.Empty<CharacterSlot>();
  public CharacterEquipment[] equipment=Array.Empty<CharacterEquipment>();
  public CharacterModification[] modifications=Array.Empty<CharacterModification>();
  [Min(1),Tooltip("Carried stacks available before equipment packSlots bonuses. Each item type uses one stack.")]
  public int basePackSlots=24;
  public CharacterItemWeight[] itemWeights=Array.Empty<CharacterItemWeight>();
  public SlotEntry[] initialEquipment=Array.Empty<SlotEntry>();
  public int initialAttributePoints=4,initialSkillPoints=20,attributePointsPerLevel=2,skillPointsPerLevel=10;
  public int experiencePerLevel=100;
  [Min(0)]public float armourAbsorptionPerPoint=.2f;
  public float defaultItemWeight=.1f;
  public CharacterEquipment Equipment(string itemId)=>equipment.FirstOrDefault(x=>x!=null&&x.itemId==itemId);
  public CharacterModification Modification(string itemId)=>(modifications??Array.Empty<CharacterModification>()).FirstOrDefault(x=>x!=null&&x.itemId==itemId);
  public string Label(string id)=>attributes.FirstOrDefault(x=>x.id==id)?.label??skills.FirstOrDefault(x=>x.id==id)?.label??derivedStats.FirstOrDefault(x=>x.id==id)?.label??id;
  public float Weight(string itemId)=>Mathf.Max(0,Equipment(itemId)?.weight??itemWeights.FirstOrDefault(x=>x.itemId==itemId)?.weight??defaultItemWeight);
 }
}
