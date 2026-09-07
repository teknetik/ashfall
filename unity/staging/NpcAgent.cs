using UnityEngine;
namespace AthenHill
{
 public class NpcAgent : MonoBehaviour
 {
  public NpcDefinition definition;
  public ActorAnimation actor;
  public bool talking;
  void Update(){actor.SetMotion(0,false,talking);}
 }
}
