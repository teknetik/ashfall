using System;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CraftIngredient {public string kind,id;public int quantity;}
 /// type: acquireItem (the item first enters the pack) or orderStart (a field order becomes current).
 [Serializable] public class CraftUnlock {public string type,id;}
 /// Fabricator window grouping; new weapon families can have their own sections.
 public enum RecipeGroup { Component, MarkI, MarkII, Weapon, WeaponMod }
 [Serializable] public class CraftRecipe
 {
  public string id,name,stationId,requiresWeaponId,outputItemId;
  [Tooltip("Weapon definition produced by this schematic. Its socket layout is defined by Output Slots.")]
  public string outputWeaponId;
  public string[] outputSlots;
  public CraftIngredient[] inputs;
  public int outputQuantity=1;
  public bool knownByDefault;
  public CraftUnlock[] unlocks;
  public CharacterRequirement[] requirements;
  [Tooltip("Carried tools required for fabrication. Tools are not consumed.")]
  public string[] requiredTools;
  [Tooltip("Additional schematic IDs that must be known before this recipe can be made.")]
  public string[] requiredSchematics;
  public RecipeGroup group;
  [Tooltip("Shown in the fabricator while the schematic is unknown: where it can be learned.")]
  [TextArea]public string lockedHint;
 }
 /// stat: a WeaponStats field name (damage, fireInterval, range, recoil, nanoMax, nanoPerShot, nanoRegen, aimAssist).
 /// op: add (flat) or percent (summed, applied once after the flat terms).
 [Serializable] public class CraftEffect {public string stat,op;public float value;}
 [Serializable] public class CraftModifier
 {
  public string id,itemId,slot;
  public string[] weaponIds;
  public CraftEffect[] effects;
  public CharacterRequirement[] requirements;
  public string[] requiredTools;
 }
 [Serializable] public class CraftWeapon
 {
  public string id,name,itemId,recipeId;
  [Tooltip("Unmodified weapon numbers. PlayerCombat reads the effective values from the fitted loadout.")]
  public WeaponStats stats=WeaponStats.ScrapPistol;
  [Tooltip("Effective stats are clamped to these bounds after every fitted mod applies.")]
  public WeaponStats minStats=WeaponStats.DefaultMin,maxStats=WeaponStats.DefaultMax;
  public string[] slots;
 }
 [Serializable] public class CraftStation {public string id,name;}
 /// Player-facing name for a slot or ingredient tag ID (e.g. grip → "Grip", nanite:tier1 → "Any tier-one nanites").
 [Serializable] public class IdLabel {public string id,label;}
 /// Fabricator stats table row: label, number format, unit and whether a lower value is the improvement.
 [Serializable] public class StatLabel {public string stat,label,format="0.#",unit;public bool lowerIsBetter;}
 [Serializable] public class LootEntry
 {
  public string itemId;
  [UnityEngine.Serialization.FormerlySerializedAs("quantity")][Min(1)]public int minQuantity=1;
  [Tooltip("Inclusive; values below Min Quantity mean exactly Min Quantity.")]
  [Min(1)]public int maxQuantity=1;
  [Range(0,1)]public float chance=1;
  [Tooltip("Bad-luck protection: after this many consecutive misses (per table and item) the next roll always drops. 0 = off.")]
  [Min(0)]public int pityAfter;
  [Tooltip("Always drops until the player has collected this item once; afterwards Chance applies. For unique story parts.")]
  public bool guaranteeUntilCollected;
 }
 [Serializable] public class LootTable {public string id;public LootEntry[] entries;}
 [CreateAssetMenu(menuName="Athen Hill/Ward crafting catalog")]
 public class CraftingCatalog:ScriptableObject
 {
  public CraftWeapon[] weapons;
  public CraftModifier[] modifiers;
  public CraftStation[] stations;
  public CraftRecipe[] recipes;
  public LootTable[] lootTables;
  [Header("Presentation")]
  public IdLabel[] slotLabels,tagLabels;
  [Tooltip("Fabricator list headings by RecipeGroup name (Component, MarkI, MarkII).")]
  public IdLabel[] groupLabels;
  public StatLabel[] statLabels;
  public string SlotName(string slot)=>Label(slotLabels,slot);
  public string TagName(string tag)=>Label(tagLabels,tag);
  public string GroupName(RecipeGroup group)=>Label(groupLabels,group.ToString());
  static string Label(IdLabel[] set,string id){if(set!=null)foreach(var x in set)if(x!=null&&x.id==id&&!string.IsNullOrEmpty(x.label))return x.label;return id;}
  public StatLabel Stat(string stat){if(statLabels!=null)foreach(var x in statLabels)if(x!=null&&x.stat==stat)return x;return null;}
 }
}
