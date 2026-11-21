using System;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CraftIngredient {public string kind,id;public int quantity;}
 /// type: acquireItem (the item first enters the pack), orderStart (a field order becomes current) or magazine (the
 /// digital magazine with that item ID is bought at a counter's magazine shelf, e.g. Field Supply) or identify (20 Nov 2026:
 /// the id is "<npc id>:<dialogue node id>"; the schematic is learned when that colonist's dialogue node is shown, e.g.
 /// npc_ossa:servo_look. Salvage is not self-explaining: someone who knows it has to say what it could become).
 [Serializable] public class CraftUnlock {public string type,id;}
 /// Fabricator window grouping; new weapon families can have their own sections. New values are appended so the
 /// serialized numbers stay valid (Armour = 5, 3 Oct 2026: the Warden kit pieces; Gear = 6 packs and pack upgrades and
 /// ArmourMod = 7 armour upgrades, 5 Oct 2026: Field Supply's magazines).
 public enum RecipeGroup { Component, MarkI, MarkII, Weapon, WeaponMod, Armour, Gear, ArmourMod }
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
  [Tooltip("Seconds at the bench before the part is made (timed crafting, 3 Oct 2026). Parts are used and the output given only when the timer completes; closing the bench, Cancel or taking damage stops it and nothing is used. 0 = instant.")]
  [Min(0)]public float craftSeconds;
  [Tooltip("Skill this schematic exercises (CharacterCatalog skill id: engineering, electronics, nanotechnology, robotics). Empty = none. 20 Nov 2026.")]
  public string skill;
  [Tooltip("Experience granted when the craft completes (character XP; 100 per level). Skill points from levelling are the main way skills grow.")]
  [Min(0)]public int craftXp;
  [Tooltip("Skill points gained from use on the first completed craft of this schematic. Later crafts gain Use Repeat Factor times the last gain; never above the catalog's Use Gain Cap. Fractions accumulate.")]
  [Min(0)]public float skillUse;
  [Tooltip("Hands-on bench job (AssemblyRecipe id in Data/Assembly, Steady Hands bench 20 Nov 2026). Set = the first one is made by hand at the bench; the timed craft opens only after one hand-made success and then makes Standard quality. Empty = timed craft only.")]
  public string assembly;
 }
 /// stat: a WeaponStats field name (damage, fireInterval, range, recoil, nanoMax, nanoPerShot, nanoRegen, aimAssist).
 /// op: add (flat) or percent (summed, applied once after the flat terms).
 /// byQuality (20 Nov 2026): optional explicit values for Rough, Standard and Fine crafted quality (three entries); empty =
 /// value scaled by the modifier's qualityScale.
 [Serializable] public class CraftEffect {public string stat,op;public float value;public float[] byQuality;}
 [Serializable] public class CraftModifier
 {
  public string id,itemId,slot;
  public string[] weaponIds;
  public CraftEffect[] effects;
  public CharacterRequirement[] requirements;
  public string[] requiredTools;
  [Tooltip("Effect scale for Rough, Standard and Fine crafted quality when an effect has no By Quality values (three entries; empty = 0.75, 1, 1.25).")]
  public float[] qualityScale;
 }
 [Serializable] public class CraftWeapon
 {
  public string id,name,itemId,recipeId;
  [Tooltip("Optional source mesh for the inventory 3D inspection. A display-only copy is rendered; gameplay components never run.")]
  public GameObject previewPrefab;
  [Tooltip("Unmodified weapon numbers. PlayerCombat reads the effective values from the fitted loadout.")]
  public WeaponStats stats=WeaponStats.ScrapPistol;
  [Tooltip("Effective stats are clamped to these bounds after every fitted mod applies.")]
  public WeaponStats minStats=WeaponStats.DefaultMin,maxStats=WeaponStats.DefaultMax;
  public string[] slots;
  [Tooltip("Condition lost per shot (20 Nov 2026, Phase 3). Condition is the weapon's Durability stat; a weapon whose base Durability is 0 does not wear.")]
  [Min(0)]public float wearPerShot;
 }
 /// Weapon condition, field repair and bench overhaul numbers (20 Nov 2026, Phase 3). All in data; the catalog holds one set.
 /// Condition (Durability) runs from the weapon's cap down to 0 (jammed). Under SpreadBelow the shot cone widens up to SpreadMaxScale
 /// at 0; under MisfireBelow a trigger pull may misfire (nothing fired or spent), up to MisfireMaxChance just above 0.
 /// A field repair with a RepairTool carried (a few RepairSeconds, stopped by damage, drawing or firing) restores RepairAmounts[repairs
 /// so far] and lowers the cap by CapLossPerRepair; a weapon whose cap is under BrokenBelow, or that has used every entry of
 /// RepairAmounts, is broken: field repair is refused and the bench Overhaul (OverhaulInputs at OverhaulStationId) restores the cap.
 [Serializable] public class ConditionRules
 {
  [Min(0)]public float spreadBelow=50,spreadMaxScale=2,misfireBelow=30;
  [Range(0,1)]public float misfireMaxChance=.35f;
  public float[] repairAmounts=new[]{30f,20f,12f,6f};
  [Min(0)]public float capLossPerRepair=8,brokenBelow=70,repairSeconds=4;
  public string repairTool="tool:screwdriver";
  public string overhaulStationId="station_field_fabricator";
  public CraftIngredient[] overhaulInputs;
 }
 /// tools: tool tags this fixed bench provides to whoever works at it (tool:vise, tool:grinder, tool:solder, tool:nanite_press,
 /// tool:welder). Carried tools are items tagged the same way (Field Toolkit: tool:screwdriver); a recipe's requiredTools entry
 /// is an item id or a tool tag, met by a carried item OR the station's tool (20 Nov 2026).
 [Serializable] public class CraftStation {public string id,name;public string[] tools;}
 /// A colonist hands over an item when a dialogue node is shown ("npc_brann:toolkit"), once: only while the item is not carried
 /// and the story flag is unset; the flag is set on the first showing.
 [Serializable] public class NodeGift {public string topic,itemId,flag;[Min(1)]public int quantity=1;}
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
  public NodeGift[] nodeGifts;
  [Header("Weapon condition (20 Nov 2026)")]
  public ConditionRules condition=new ConditionRules();
  [Header("Skill use (20 Nov 2026)")]
  [Tooltip("Most skill points one completed craft can add from use, however high the recipe's Skill Use.")]
  [Min(0)]public float useGainCap=1.5f;
  [Tooltip("Each repeat craft of the same schematic gains this fraction of the previous gain (diminishing returns).")]
  [Range(0,1)]public float useRepeatFactor=0.5f;
  [Header("Presentation")]
  public IdLabel[] slotLabels,tagLabels;
  [Tooltip("Fabricator list headings by RecipeGroup name (Component, MarkI, MarkII).")]
  public IdLabel[] groupLabels;
  public StatLabel[] statLabels;
  [Tooltip("Steady Hands bench (20 Nov 2026): the loose grip's rattle (asm.rattle.*) and the damper's settling tick (asm.damper.tick), used by PlayerCombat when its own clip fields are empty. Bound by art/steady_hands_bench_20261120/data/apply_data.py.")]
  public AudioClip[] rattleClips,damperClips;
  public string SlotName(string slot)=>Label(slotLabels,slot);
  public string TagName(string tag)=>Label(tagLabels,tag);
  public string GroupName(RecipeGroup group)=>Label(groupLabels,group.ToString());
  static string Label(IdLabel[] set,string id){if(set!=null)foreach(var x in set)if(x!=null&&x.id==id&&!string.IsNullOrEmpty(x.label))return x.label;return id;}
  public StatLabel Stat(string stat){if(statLabels!=null)foreach(var x in statLabels)if(x!=null&&x.stat==stat)return x;return null;}
 }
}
