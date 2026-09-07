using UnityEngine;
namespace AthenHill
{
 public class FollowCamera : MonoBehaviour
 {
  public Transform target;
  public GameInput input;
  [Min(.1f)] public float boom=4.2f,targetHeight=1.5f,sweepRadius=.23f;
  public float yaw=-90,pitch=17,sensitivity=.13f,recoverySpeed=7;
  public LayerMask worldMask=~(1<<8);
  public bool FixedView;
  float distance;
  void Awake(){distance=boom;}
  void LateUpdate()
  {
   if(FixedView||!target)return;
   if(input.Orbit){var delta=input.Look;yaw+=delta.x*sensitivity;pitch=Mathf.Clamp(pitch-delta.y*sensitivity,-10,65);}
   Vector3 focus=target.position+Vector3.up*targetHeight;
   Quaternion rotation=Quaternion.Euler(pitch,yaw,0);
   Vector3 behind=rotation*Vector3.back;
   float wanted=boom;
   if(Physics.SphereCast(focus,sweepRadius,behind,out var hit,boom,worldMask,QueryTriggerInteraction.Ignore))wanted=Mathf.Max(.12f,hit.distance-.04f);
   distance=wanted<distance?wanted:Mathf.Lerp(distance,wanted,1-Mathf.Exp(-recoverySpeed*Time.deltaTime));
   transform.SetPositionAndRotation(focus+behind*distance,rotation);
  }
 }
}
