using System;
using UnityEngine;
namespace AthenHill
{
 /// requires: a QuestConditions expression (empty = always offered). setFlag: a story flag recorded (and saved) when the
 /// choice is taken. action: "" (go to next), "close", "shop" (this colonist's counter) or "fabricator" (the workbench
 /// the colonist keeps, NpcAgent.workbench).
 [Serializable] public class DialogueChoice {public string id,label,next,action;[Tooltip("QuestConditions expression; empty = always offered.")]public string requires;public string setFlag;}
 [Serializable] public class DialogueNode {public string id,title;[TextArea(3,8)]public string text;[Tooltip("Offline spoken take for this node; the text remains the subtitle and fallback.")]public AudioClip voice;public DialogueChoice[] choices;}
 /// A conversation opening: the first entry whose condition holds picks the node the colonist greets with.
 [Serializable] public class DialogueEntry {public string node;[Tooltip("QuestConditions expression; empty = always.")]public string requires;}
 /// What this colonist's counter offers ("shop" choices). Basic General shows all three lists.
 [Serializable] public class ShopProfile
 {
  public string title="Basic General",subtitle="Mira · Supplies, parts and salvage";
  [Tooltip("Tradeable catalog items with a buy price, including supplies and equipment.")]public bool supplies=true;
  [Tooltip("Common and uncommon crafting parts at their parts price.")]public bool parts=true;
  [Tooltip("Raw salvage bought at its sell price.")]public bool salvage=true;
 }
 [CreateAssetMenu(menuName="Athen Hill/NPC definition")]
 public class NpcDefinition : ScriptableObject
 {
  public string id,displayName,role;
  [Tooltip("Openings tried in order; none matching (or none listed) opens at \"greeting\".")]
  public DialogueEntry[] entries=new DialogueEntry[0];
  public DialogueNode[] nodes;
  public ShopProfile shop=new ShopProfile();
 }
}
