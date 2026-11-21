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
  [Header("Showcase camera (19 Nov 2026; found on this object when empty)")]
  [Tooltip("Over-the-shoulder framing during dialogue. It only overlays the pose written here; yaw, pitch and zoom are never changed.")]
  public ConversationCamera conversation;
  [Tooltip("While photo mode is open it owns this transform and lens, and this component writes nothing.")]
  public PhotoMode photo;
  public bool FirstPerson=>boom<=.01f&&!FixedView;
  /// Set by a CameraConfineZone while the player is inside it: first person, zoom held.
  public bool Confined{get=>confined;set=>confined=value;}
  bool confined,wasConfined;float confinedBoom;
  public float Distance=>distance;
  public bool PlayerHidden {get;private set;}
  float distance,aimBlend,baseFieldOfView;
  Camera lens;
  GameSettings settingsCache;bool settingsSearched;
  GameSettings settings{get{if(!settingsCache&&!settingsSearched){settingsSearched=true;settingsCache=FindAnyObjectByType<GameSettings>();}return settingsCache;}}
  bool lensTouched;
  float recoilRecovery,recoilTime;
  public void ApplyShotKick(float degrees,float recoverFraction,float recoverSeconds)
  {
   if(FixedView)return;
   pitch=Mathf.Clamp(pitch-degrees,aimMode?-70:-80,aimMode?70:80);
   recoilRecovery+=degrees*Mathf.Clamp01(recoverFraction);
   recoilTime=Mathf.Max(.01f,recoverSeconds);
  }
  // 20 Nov 2026 (Steady Hands bench, craft agent): the weapon's handling adds a sideways step (part recovered like the
  // pitch kick) and, when recovery is slow, one overshoot past the rest point that settles back. Additive to the kick above.
  float sideRecovery,sideTime,settleBack,settleTime,settleAfter;
  public void ApplyShotKick(float degrees,float sideDegrees,float recoverFraction,float recoverSeconds,float overshoot)
  {
   if(FixedView)return;
   ApplyShotKick(degrees,recoverFraction,recoverSeconds);
   float keep=Mathf.Clamp01(recoverFraction);
   if(sideDegrees!=0){yaw+=sideDegrees;sideRecovery+=sideDegrees*keep;sideTime=Mathf.Max(.01f,recoverSeconds);}
   float past=degrees*keep*Mathf.Clamp(overshoot,0,.5f);
   if(past>0){recoilRecovery+=past;settleBack=past;settleAfter=recoilTime;settleTime=Mathf.Max(.01f,recoverSeconds*.6f);}
   else{settleBack=0;}
  }
  void RecoverHandling(float dt)
  {
   if(sideRecovery!=0){float step=sideRecovery*Mathf.Min(1,dt/Mathf.Max(.0001f,sideTime));yaw-=step;sideRecovery-=step;sideTime=Mathf.Max(0,sideTime-dt);if(Mathf.Abs(sideRecovery)<1e-4f)sideRecovery=0;}
   if(settleBack>0){if(settleAfter>0){settleAfter-=dt;return;}float step=Mathf.Min(settleBack,dt*settleBack/Mathf.Max(.0001f,settleTime));pitch=Mathf.Clamp(pitch-step,aimMode?-70:-80,aimMode?70:80);settleBack-=step;settleTime=Mathf.Max(0,settleTime-dt);}
  }
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
   if(!conversation)conversation=GetComponent<ConversationCamera>();
   if(!photo)photo=GetComponent<PhotoMode>();
  }
  void LateUpdate()
  {
   if(photo&&photo.IsOpen)return;
   // The bench camera (AssemblyCameraRig, 20 Nov 2026) owns this transform and lens; the colonist stands where the lens is, so only its shadow is drawn.
   if(CinematicCamera.BenchActive){HidePlayer(true);if(conversation)conversation.Suspend();return;}
   if(FixedView||!target){HidePlayer(false);if(conversation)conversation.Suspend();return;}
   aimBlend=Mathf.MoveTowards(aimBlend,aimMode?1:0,aimBlendSpeed*Time.unscaledDeltaTime);
   // Mouse look is always on in play (GameInput locks the cursor and drops the lock's recentring jump).
   var delta=input.Look;
   if(delta!=Vector2.zero)
   {
    float scale=sensitivity*(settings?settings.Controls.Sensitivity:1);float limit=aimMode?70:80;
    yaw+=delta.x*scale;pitch=Mathf.Clamp(pitch-delta.y*scale*(settings&&settings.Controls.invertY?-1:1),-limit,limit);
   }
   if(recoilRecovery>0){float step=Mathf.Min(recoilRecovery,Time.deltaTime*recoilRecovery/Mathf.Max(.0001f,recoilTime));pitch=Mathf.Clamp(pitch+step,aimMode?-70:-80,aimMode?70:80);recoilRecovery-=step;recoilTime=Mathf.Max(0,recoilTime-Time.deltaTime);}
   RecoverHandling(Time.deltaTime);
   // A tight interior (CameraConfineZone: the container home) holds the view in first person and gives the player's
   // own zoom back at the door.
   if(confined!=wasConfined){wasConfined=confined;if(confined){confinedBoom=boom;boom=0;}else boom=confinedBoom;}
   float scroll=confined?0:input.Zoom;
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
   Vector3 behind=rotation*Vector3.back;
   float wanted=activeBoom;
   if(activeBoom>0&&Physics.SphereCast(focus,sweepRadius,behind,out var hit,activeBoom,worldMask,QueryTriggerInteraction.Ignore))wanted=Mathf.Min(activeBoom,Mathf.Max(.12f,hit.distance-.04f));
   distance=wanted<distance?wanted:Mathf.Lerp(distance,wanted,1-Mathf.Exp(-recoverySpeed*Time.deltaTime));
   // The conversation camera overlays the finished gameplay pose; at weight 0 it is left exactly as computed.
   var position=focus+behind*distance;var pose=rotation;
   float lensFov=lens?Mathf.Lerp(baseFieldOfView,aimFieldOfView,aimBlend):0,talk=0;
   if(conversation&&conversation.isActiveAndEnabled)talk=conversation.Compose(targetPosition,FirstPerson,ref position,ref pose,ref lensFov);
   if(lens)
   {
    // Only touch the lens while aiming or framing a conversation; otherwise follow whatever field of view is set elsewhere.
    if(aimBlend>0||talk>0){lens.fieldOfView=lensFov;lensTouched=true;}
    else{if(lensTouched){lens.fieldOfView=baseFieldOfView;lensTouched=false;}baseFieldOfView=lens.fieldOfView;}
   }
   transform.SetPositionAndRotation(position,pose);
   HidePlayer(talk>0&&conversation.Framing?conversation.HidesPlayer:distance<.65f);
  }
  /// Photo mode shows the whole colonist from any angle; the next gameplay frame puts the first-person hiding back.
  public void ShowPlayerForPhoto(){HidePlayer(false);}
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
