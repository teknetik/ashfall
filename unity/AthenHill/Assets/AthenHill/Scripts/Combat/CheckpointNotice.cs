using UnityEngine;
namespace AthenHill
{
 /// Inspectable checkpoint signage; messages and speaker remain editable in the scene.
 [RequireComponent(typeof(WorldInteractable))]
 public class CheckpointNotice : MonoBehaviour
 {
  public GameSession session;
  public string speaker="West Gate checkpoint";
  [TextArea(3,8)] public string message;
  void OnEnable(){GetComponent<WorldInteractable>().Used+=Read;}
  void OnDisable(){GetComponent<WorldInteractable>().Used-=Read;}
  void Read(){if(session)session.Notify(message,speaker);}
 }
}
