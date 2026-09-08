using UnityEngine;
using UnityEngine.Rendering;
namespace AthenHill
{
 public class FollowCamera : MonoBehaviour
 {
  public Transform target;
  public GameInput input;
  [Min(0)] public float boom=4.2f;
  [Min(.1f)] public float targetHeight=1.5f,sweepRadius=.23f;
  [Min(.1f)] public float maxBoom=10,zoomStep=.7f,firstPersonHeight=1.65f;
  public float yaw=-90,pitch=17,sensitivity=.13f,recoverySpeed=7;
  public LayerMask worldMask=~(1<<8);
  public bool FixedView;
  public bool FirstPerson=>boom<=.01f&&!FixedView;
  public float Distance=>distance;
  public bool PlayerHidden {get;private set;}
  float distance;
  Renderer[] playerRenderers;
  ShadowCastingMode[] shadowModes;
  void Awake()
  {
   distance=boom;
   playerRenderers=target?target.GetComponentsInChildren<Renderer>(true):new Renderer[0];
   shadowModes=new ShadowCastingMode[playerRenderers.Length];
   for(int i=0;i<playerRenderers.Length;i++)shadowModes[i]=playerRenderers[i].shadowCastingMode;
  }
  void LateUpdate()
  {
   if(FixedView||!target){HidePlayer(false);return;}
   if(input.Orbit){var delta=input.Look;yaw+=delta.x*sensitivity;pitch=Mathf.Clamp(pitch-delta.y*sensitivity,-80,80);}
   float scroll=input.Zoom;
   if(scroll!=0){boom=Mathf.Clamp(boom-scroll*zoomStep,0,maxBoom);if(boom<.05f)boom=0;}
   Vector3 focus=target.position+Vector3.up*Mathf.Lerp(firstPersonHeight,targetHeight,Mathf.Clamp01(boom));
   Quaternion rotation=Quaternion.Euler(pitch,yaw,0);
   Vector3 behind=rotation*Vector3.back;
   float wanted=boom;
   if(boom>0&&Physics.SphereCast(focus,sweepRadius,behind,out var hit,boom,worldMask,QueryTriggerInteraction.Ignore))wanted=Mathf.Min(boom,Mathf.Max(.12f,hit.distance-.04f));
   distance=wanted<distance?wanted:Mathf.Lerp(distance,wanted,1-Mathf.Exp(-recoverySpeed*Time.deltaTime));
   transform.SetPositionAndRotation(focus+behind*distance,rotation);
   HidePlayer(distance<.65f);
  }
  void HidePlayer(bool hide)
  {
   if(PlayerHidden==hide)return;
   PlayerHidden=hide;
   // Keep the colonist's shadow, rig and movement active while the camera is inside it.
   for(int i=0;i<playerRenderers.Length;i++)if(playerRenderers[i])playerRenderers[i].shadowCastingMode=hide?ShadowCastingMode.ShadowsOnly:shadowModes[i];
  }
  void OnDisable(){HidePlayer(false);}
 }
}
