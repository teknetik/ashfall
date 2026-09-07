using System;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class DialogueChoice {public string id,label,next,action;}
 [Serializable] public class DialogueNode {public string id,title;[TextArea(3,8)]public string text;public DialogueChoice[] choices;}
 [CreateAssetMenu(menuName="Athen Hill/NPC definition")]
 public class NpcDefinition : ScriptableObject
 {
  public string id,displayName,role;
  public DialogueNode[] nodes;
 }
}
