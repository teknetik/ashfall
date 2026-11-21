using System;
using UnityEngine;
namespace AthenHill
{
 /// What completes a field order.
 ///  FitMod: the target mod is fitted (and, with Require Test Fire, a shot is fired with it fitted).
 ///  CollectItem: the target item has been collected into the pack at least once.
 ///  CraftFromGroup: any schematic of the target group has been fabricated.
 ///  CraftItem: the target item has been fabricated from its schematic (gather its inputs, optionally report, fabricate).
 public enum FieldOrderGoal { FitMod, CollectItem, CraftFromGroup, CraftItem }
 [Serializable] public class FieldOrder
 {
  public string id,title;
  public FieldOrderGoal goal;
  [Tooltip("FitMod: the mod item. CollectItem: the item to recover. CraftItem: the item to fabricate.")]
  public string targetItemId;
  [Tooltip("CraftFromGroup: any schematic in this group counts.")]
  public RecipeGroup targetGroup;
  [Tooltip("FitMod only: also fire one shot with the mod fitted.")]
  public bool requireTestFire;
  [Tooltip("Key of a FieldOrders encounter binding activated when this order starts (it stays available afterwards).")]
  public string activateEncounter;
  [Tooltip("Guidance key while gathering (fabricator guidance is automatic once the part can be fabricated or fitted).")]
  public string guidance;
  [Header("Identify (optional)")]
  [Tooltip("CraftItem and FitMod: Field Notes text while the player carries salvage the schematic needs but nobody has identified it yet (ItemSpec.identifyBy, e.g. the Damaged Servo shown to Ossa). {item} = target item name.")]
  [TextArea(2,4)]public string identifyBrief;
  [Tooltip("Guidance key for the Identify stage (FieldOrders guidance target). Empty = no marker.")]
  public string identifyGuidance;
  [Header("Report (optional)")]
  [Tooltip("FitMod and CraftItem: NpcDefinition id of the colonist the player takes the parts to before fabricating (Brann at Salvage for the first order). Until the player has spoken to them, a gathered order waits at its Report stage.")]
  public string reportTo;
  [Tooltip("Field Notes text for the Report stage. {item} = target item name.")]
  [TextArea(2,4)]public string reportBrief;
  [Tooltip("Guidance key for the Report stage (FieldOrders guidance target).")]
  public string reportGuidance;
  [Tooltip("The order's instruction, shown in Field Notes. {item} = target item name.")]
  [TextArea(2,4)]public string brief;
  [Header("Test fire after a bench build (Steady Hands bench, 20 Nov 2026; FitMod with Require Test Fire)")]
  [Tooltip("When the part was built by hand at the bench during this order, the test fire is a string of this many shots (1 or less = one shot, as before) and its group is judged.")]
  [Min(0)]public int testFireShots;
  [Tooltip("A string whose widest pair of shots is within this many degrees is tight; a wider one gets the poor line and one more string.")]
  [Min(0)]public float testFireTightDegrees=3.5f;
  [Tooltip("Radio line when a bench-built part reaches its test fire (empty = silent).")]
  [TextArea(1,3)]public string testFireLine;
  [TextArea(1,3)]public string testFireTightLine;
  [TextArea(1,3)]public string testFirePoorLine;
  [Tooltip("Where the judged string is fired from (world position, the Warden range's firing line) and how far from it a shot still counts (metres, on the ground plane). Radius 0 = anywhere.")]
  public Vector3 testFireAt;
  [Min(0)]public float testFireRadius;
  [Tooltip("Field Notes text while a bench-built part waits for its test fire. {item} = target item name. Empty = Test Fire Format.")]
  [TextArea(1,3)]public string testFireBrief;
  [Tooltip("Journal step for that test fire, and the marker's label.")]
  public string testFireStep,testFireLabel;
  [Tooltip("Voiced takes of the three lines above and of the completion line (empty = caption only). Played on the radio voice source as the line is queued.")]
  public AudioClip testFireVoice,testFireTightVoice,testFirePoorVoice,completeVoice;
  [Tooltip("Radio line when the order becomes current. Empty = silent (e.g. the primer already briefed it).")]
  [TextArea(2,5)]public string startLine;
  [TextArea(2,5)]public string completeLine;
  [Tooltip("The start line is time-critical (a combat warning): it jumps the radio queue instead of waiting behind other lines.")]
  public bool urgentStart;
  [Tooltip("Urgent radio line spoken once, the first time this order's encounter leader turns on the player. Empty = none.")]
  [TextArea(1,3)]public string engageLine;
  public string speaker="Warden Ossa";
  [Min(0)]public int rewardCredits;
  public ItemStack[] rewardItems=new ItemStack[0];
  [Tooltip("Schematics granted on completion (in addition to order-start unlocks in the crafting catalog).")]
  public string[] rewardRecipes=new string[0];
 }
 /// Ossa's field orders after the Outer Berms primer. Order text is data: the objective shown in Field Notes is built
 /// from these templates plus live recipe and inventory facts.
 [CreateAssetMenu(menuName="Athen Hill/Field orders")]
 public class FieldOrderSet:ScriptableObject
 {
  public FieldOrder[] orders=new FieldOrder[0];
  [Header("Objective templates · {brief} {item} {weapon} {recipe} {inputs} {count}")]
  [TextArea]public string gatherFormat="{brief}\n{recipe}: {inputs}";
  [TextArea]public string fabricateFormat="Fabricate the {item} at the field fabricator by Ossa's post.";
  [Tooltip("Fabricate stage when the part is made by hand at the bench (its schematic has a bench job: fabricate and fit in one visit). {stage} = the bench's current stage. Empty = Fabricate Format.")]
  [TextArea]public string benchFormat="Build and fit the {item} at Brann's bench.\n{stage}";
  [Tooltip("Journal step for the bench route (replaces the Fabricate and Fit steps). {item} = target item name.")]
  public string benchStepFormat="Build and fit the {item} at Brann's bench";
  [TextArea]public string fitFormat="Fit the {item} to your {weapon} at the field fabricator.";
  [TextArea]public string testFireFormat="Fire your upgraded pistol in the Outer Berms.";
  [TextArea]public string collectFormat="{brief}";
  [TextArea]public string craftGroupFormat="{brief}\nKnown schematics: {count}";
  [Tooltip("One ingredient in {inputs}: {name} {have}/{need}.")]
  public string inputFormat="{name} {have}/{need}";
  public string inputSeparator=" · ";
  [Header("After the last order")]
  [TextArea]public string freePlayObjective="Free hunting in the Outer Berms.";
  public string freePlayGuidance;
  [Tooltip("Seconds of radio silence between an order's completion line and the next order's briefing (the radio queue shows each line for its full reading time first).")]
  [Min(0)]public float nextLineDelay=4.5f;
 }
}
