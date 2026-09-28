using UnityEngine;
namespace AthenHill
{
 [RequireComponent(typeof(WorldInteractable))]
 public class RangeResetStation:MonoBehaviour
 {
  public BermsTutorial tutorial;
  public GameSession session;
  void OnEnable(){GetComponent<WorldInteractable>().Used+=ResetRange;}
  void OnDisable(){GetComponent<WorldInteractable>().Used-=ResetRange;}
  void ResetRange()
  {
   if(!tutorial||!session)return;
   if(tutorial.Step!=BermsStep.Targets&&tutorial.Step!=BermsStep.Complete)
   {session.Notify("Finish Ossa's field primer before resetting the range for practice.","Warden range");return;}
   foreach(var t in tutorial.targets)if(t)t.Raise();
   session.Notify("Three plates raised. Stand behind the firing line and keep your shots toward the berm.","Warden range");
  }
 }
}
