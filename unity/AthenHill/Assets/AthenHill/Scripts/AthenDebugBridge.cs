using System.Linq;
using UnityEngine;
namespace AthenHill
{
 public class AthenDebugBridge : MonoBehaviour
 {
  public PlayerMotor player;
  public FollowCamera follow;
  public Transform landmarks;
  public string selectedCamera="follow";
  public float fps;
  float sum;int frames;
  void Update(){sum+=Time.unscaledDeltaTime;frames++;if(sum>=.5f){fps=frames/sum;sum=0;frames=0;}}
  public void Goto(string name)
  {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
   var t=landmarks.Find(name);if(!t)throw new System.ArgumentException("Unknown landmark: "+name);player.Teleport(t.position);
#endif
  }
  public void View(string name)
  {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
   if(name=="follow"){follow.FixedView=false;follow.GetComponent<Camera>().fieldOfView=50;selectedCamera=name;return;}
   var c=Object.FindObjectsByType<Camera>(FindObjectsSortMode.None).FirstOrDefault(x=>x.name==name);
   if(!c)throw new System.ArgumentException("Unknown camera: "+name);
   follow.FixedView=true;follow.transform.SetPositionAndRotation(c.transform.position,c.transform.rotation);follow.GetComponent<Camera>().fieldOfView=c.fieldOfView;selectedCamera=name;
#endif
  }
  public void ResetPlayer(){player.ReturnToGate();follow.yaw=-90;follow.pitch=17;View("follow");}
 }
}
