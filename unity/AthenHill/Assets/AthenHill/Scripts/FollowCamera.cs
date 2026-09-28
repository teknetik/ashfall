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
  [Header("Aim mode (set by PlayerCombat)")]
  public bool aimMode;
  [Min(.3f)] public float aimBoom=2.1f;
  public float aimShoulder=.55f,aimFieldOfView=48;
  [Min(.1f)] public float aimBlendSpeed=10;
  public bool FirstPerson=>boom<=.01f&&!FixedView;
  public float Distance=>distance;
  public bool PlayerHidden {get;private set;}
  float distance,aimBlend,baseFieldOfView;
  bool wasAiming;int settleFrames;
  Camera lens;
  bool lensTouched;
  PlayerMotor targetMotor;
  Renderer[] playerRenderers;
  ShadowCastingMode[] shadowModes;
  void Awake()
  {
   distance=boom;
   lens=GetComponent<Camera>();baseFieldOfView=lens?lens.fieldOfView:60;
   targetMotor=target?target.GetComponent<PlayerMotor>():null;
   playerRenderers=target?target.GetComponentsInChildren<Renderer>(true):new Renderer[0];
   shadowModes=new ShadowCastingMode[playerRenderers.Length];
   for(int i=0;i<playerRenderers.Length;i++)shadowModes[i]=playerRenderers[i].shadowCastingMode;
  }
  void LateUpdate()
  {
   if(FixedView||!target){HidePlayer(false);return;}
   aimBlend=Mathf.MoveTowards(aimBlend,aimMode?1:0,aimBlendSpeed*Time.unscaledDeltaTime);
   // Entering aim locks the cursor; the recentring shows up as one large raw delta, so skip the first frames.
   if(aimMode&&!wasAiming)settleFrames=2;
   wasAiming=aimMode;
   if(aimMode){var raw=input.RawLook;if(settleFrames>0)settleFrames--;else{yaw+=raw.x*sensitivity;pitch=Mathf.Clamp(pitch-raw.y*sensitivity,-70,70);}}
   else if(input.Orbit){var delta=input.Look;yaw+=delta.x*sensitivity;pitch=Mathf.Clamp(pitch-delta.y*sensitivity,-80,80);}
   float scroll=input.Zoom;
   if(scroll!=0){boom=Mathf.Clamp(boom-scroll*zoomStep,0,maxBoom);if(boom<.05f)boom=0;}
   var targetPosition=targetMotor&&targetMotor.transform==target?targetMotor.RenderPosition:target.position;
   float activeBoom=boom>0?Mathf.Lerp(boom,Mathf.Min(boom,aimBoom),aimBlend):0;
   Vector3 focus=targetPosition+Vector3.up*Mathf.Lerp(firstPersonHeight,targetHeight,Mathf.Clamp01(activeBoom));
   Quaternion rotation=Quaternion.Euler(pitch,yaw,0);
   if(activeBoom>0&&aimBlend>0)
   {
    // Shoulder offset, swept so it never pushes the lens into a wall.
    var side=rotation*Vector3.right;float shoulder=aimShoulder*aimBlend;
    if(Physics.SphereCast(focus,sweepRadius,side,out var sideHit,shoulder,worldMask,QueryTriggerInteraction.Ignore))shoulder=Mathf.Max(0,sideHit.distance-.05f);
    focus+=side*shoulder;
   }
   if(lens)
   {
    // Only touch the lens while aiming; otherwise follow whatever field of view is set elsewhere.
    if(aimBlend>0){lens.fieldOfView=Mathf.Lerp(baseFieldOfView,aimFieldOfView,aimBlend);lensTouched=true;}
    else{if(lensTouched){lens.fieldOfView=baseFieldOfView;lensTouched=false;}baseFieldOfView=lens.fieldOfView;}
   }
   Vector3 behind=rotation*Vector3.back;
   float wanted=activeBoom;
   if(activeBoom>0&&Physics.SphereCast(focus,sweepRadius,behind,out var hit,activeBoom,worldMask,QueryTriggerInteraction.Ignore))wanted=Mathf.Min(activeBoom,Mathf.Max(.12f,hit.distance-.04f));
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
