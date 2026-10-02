using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// The story state dialogue conditions read (GameSession implements it from the primer, the field orders and flags).
 public interface IQuestState
 {
  bool PrimerComplete {get;}
  bool HasPistol {get;}
  /// Id of the current field order, or null (before the primer ends and in free play).
  string CurrentOrderId {get;}
  OrderStage Stage {get;}
  /// The current order's report-to colonist has been visited (FieldOrder.reportTo).
  bool CurrentReported {get;}
  bool HasFlag(string id);
 }
 /// Dialogue conditions (NpcDefinition entries and choices): comma-separated terms that must all hold; "!" negates one.
 ///  primer          the Outer Berms primer is complete
 ///  pistol          the scrap pistol is carried
 ///  order:ID        that field order is current
 ///  stage:NAME      the current order's stage (OrderStage: NotStarted, Gather, Report, Fabricate, Fit, TestFire, Hunt, Craft, FreePlay)
 ///  reported        the current order's report-to colonist has been visited
 ///  freeplay        every field order is done
 ///  flag:ID         a story flag set by a dialogue choice (saved)
 /// e.g. "order:order_steady_hands, !reported" or "primer, !flag:brann_met".
 public static class QuestConditions
 {
  static readonly HashSet<string> Keys=new HashSet<string>{"primer","pistol","order","stage","reported","freeplay","flag"};
  public static bool Evaluate(string expression,IQuestState state)
  {
   if(string.IsNullOrWhiteSpace(expression))return true;
   foreach(var raw in expression.Split(','))
   {
    var term=raw.Trim();if(term.Length==0)continue;
    bool negate=term[0]=='!';if(negate)term=term.Substring(1).Trim();
    if(Term(term,state)==negate)return false;
   }
   return true;
  }
  static void Split(string term,out string key,out string value)
  {
   int colon=term.IndexOf(':');
   key=colon<0?term:term.Substring(0,colon).Trim();value=colon<0?null:term.Substring(colon+1).Trim();
  }
  static bool Term(string term,IQuestState s)
  {
   Split(term,out var key,out var value);
   if(s==null)return false;
   switch(key)
   {
    case "primer":return s.PrimerComplete;
    case "pistol":return s.HasPistol;
    case "order":return s.CurrentOrderId==value;
    case "stage":return string.Equals(s.Stage.ToString(),value,StringComparison.OrdinalIgnoreCase);
    case "reported":return s.CurrentReported;
    case "freeplay":return s.Stage==OrderStage.FreePlay;
    case "flag":return !string.IsNullOrEmpty(value)&&s.HasFlag(value);
    default:Debug.LogWarning("Unknown dialogue condition: "+term);return false;
   }
  }
  /// Terms this evaluator does not understand (data validation).
  public static IEnumerable<string> Problems(string expression)
  {
   if(string.IsNullOrWhiteSpace(expression))yield break;
   foreach(var raw in expression.Split(','))
   {
    var term=raw.Trim().TrimStart('!').Trim();if(term.Length==0)continue;
    Split(term,out var key,out var value);
    if(!Keys.Contains(key))yield return term;
    else if((key=="order"||key=="flag"||key=="stage")&&string.IsNullOrEmpty(value))yield return term;
    else if(key=="stage"&&!Enum.TryParse(value,true,out OrderStage _))yield return term;
   }
  }
 }
 /// How a conversation opens and which choices it offers, from the colonist's data and the story state.
 public static class DialogueFlow
 {
  /// The node a colonist opens with: the first entry whose condition holds (and whose node exists), else "greeting".
  public static string StartNode(NpcDefinition d,IQuestState state)
  {
   if(d&&d.entries!=null)foreach(var e in d.entries)
    if(e!=null&&!string.IsNullOrEmpty(e.node)&&d.nodes!=null&&System.Array.Exists(d.nodes,x=>x!=null&&x.id==e.node)&&QuestConditions.Evaluate(e.requires,state))return e.node;
   return "greeting";
  }
  /// A node's choices whose conditions hold, at most max (the HUD has one button each).
  public static DialogueChoice[] Choices(DialogueNode node,IQuestState state,int max)
  {
   var list=new List<DialogueChoice>();
   if(node?.choices!=null)foreach(var c in node.choices)if(c!=null&&QuestConditions.Evaluate(c.requires,state)){list.Add(c);if(list.Count>=max)break;}
   return list.ToArray();
  }
 }
}
