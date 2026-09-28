using UnityEngine;
namespace AthenHill
{
 /// Calm, deliberate head behaviour layered on top of an actor's legacy idle/talk clips (applied in LateUpdate,
 /// after the Animation component has sampled). Levels the gaze of library idles whose heads droop or tilt,
 /// turns toward the player when they come close (clamped and eased, like a Warden acknowledging a visitor),
 /// holds eye contact while talking, and otherwise makes a slow glance every 10-20 s instead of scanning.
 [DisallowMultipleComponent]
 public class ActorLookAt:MonoBehaviour
 {
  public ActorAnimation actor;
  public Transform head,neck;
  [Tooltip("Player head target. Found automatically when empty.")]
  public Transform target;
  [Tooltip("Metres. Inside this radius the actor turns its head toward the player.")]
  [Min(0)]public float focusRadius=4;
  [Range(0,90)]public float maxYaw=45;
  [Range(0,45)]public float maxPitch=15;
  [Tooltip("How strongly the head is held to a level forward gaze when nobody is near (0 = clip only).")]
  [Range(0,1)]public float restWeight=.7f;
  [Range(0,1)]public float focusWeight=.9f;
  [Tooltip("Share of the correction carried by the neck; the head takes the rest.")]
  [Range(0,1)]public float neckShare=.35f;
  [Tooltip("Seconds for the gaze to settle on a new direction.")]
  [Min(.05f)]public float settleSeconds=.55f;
  [Tooltip("Random glance interval (seconds) while idle.")]
  public Vector2 glanceInterval=new Vector2(10,20);
  [Range(0,60)]public float glanceYaw=28;
  [Min(0)]public float glanceHold=2.4f;
  [Tooltip("Skip the head work beyond this camera distance.")]
  [Min(1)]public float activeDistance=40;
  public bool Focused {get;private set;}
  Vector3 faceLocal,upLocal,neckFaceLocal,neckUpLocal;
  float yaw,pitch,yawVelocity,pitchVelocity,weight,weightVelocity,nextGlance,glanceUntil,glanceTarget;
  bool ready;
  void Start()
  {
   if(!actor)actor=GetComponent<ActorAnimation>();
   if(!head||!neck)
    foreach(var t in GetComponentsInChildren<Transform>(true)){if(!head&&t.name=="Head")head=t;if(!neck&&t.name=="neck")neck=t;}
   if(!target){var player=FindAnyObjectByType<PlayerMotor>();if(player)target=player.transform;}
   ready=head&&BindAxes(head,out faceLocal,out upLocal);
   if(ready&&neck&&!BindAxes(neck,out neckFaceLocal,out neckUpLocal))neck=null;
   var r=new System.Random(transform.position.GetHashCode());
   nextGlance=Time.time+Mathf.Lerp(glanceInterval.x,glanceInterval.y,(float)r.NextDouble());
   enabled=ready;
  }
  /// The face and up axes of a bone in its own space, from the skin bind pose (the rig faces the actor forward there).
  bool BindAxes(Transform bone,out Vector3 face,out Vector3 up)
  {
   face=up=Vector3.zero;
   foreach(var skin in GetComponentsInChildren<SkinnedMeshRenderer>(true))
   {
    if(!skin.sharedMesh)continue;
    int i=System.Array.IndexOf(skin.bones,bone);
    if(i<0||i>=skin.sharedMesh.bindposes.Length)continue;
    var bind=skin.sharedMesh.bindposes[i].inverse.rotation;           // bone rotation in skin space at bind
    var skinToActor=Quaternion.Inverse(transform.rotation)*skin.transform.rotation;
    var inv=Quaternion.Inverse(skinToActor*bind);
    face=inv*Vector3.forward;up=inv*Vector3.up;return true;
   }
   return false;
  }
  void LateUpdate()
  {
   var cam=Camera.main;
   if(cam&&(cam.transform.position-transform.position).sqrMagnitude>activeDistance*activeDistance){Focused=false;return;}
   bool talking=actor&&actor.talk&&actor.CurrentClip==actor.talk.name;
   var eyes=head.position;
   float wantYaw=0,wantPitch=0,wantWeight=restWeight;
   Focused=false;
   if(target)
   {
    var to=target.position+Vector3.up*1.55f-eyes;
    var local=Quaternion.Inverse(transform.rotation)*to;
    float y=Mathf.Atan2(local.x,local.z)*Mathf.Rad2Deg;
    float p=Mathf.Atan2(local.y,new Vector2(local.x,local.z).magnitude)*Mathf.Rad2Deg;
    // Only look at someone in front; a player behind the actor is not tracked over the shoulder.
    if((talking||to.magnitude<focusRadius)&&Mathf.Abs(y)<maxYaw+50)
    {Focused=true;wantYaw=Mathf.Clamp(y,-maxYaw,maxYaw);wantPitch=Mathf.Clamp(p,-maxPitch,maxPitch);wantWeight=focusWeight;}
   }
   if(!Focused)
   {
    if(Time.time>=nextGlance)
    {
     glanceTarget=Random.Range(-glanceYaw,glanceYaw);glanceUntil=Time.time+glanceHold*Random.Range(.8f,1.3f);
     nextGlance=Time.time+Random.Range(glanceInterval.x,glanceInterval.y);
    }
    if(Time.time<glanceUntil)wantYaw=glanceTarget;
   }
   float dt=Time.deltaTime;
   yaw=Mathf.SmoothDamp(yaw,wantYaw,ref yawVelocity,settleSeconds,Mathf.Infinity,dt);
   pitch=Mathf.SmoothDamp(pitch,wantPitch,ref pitchVelocity,settleSeconds,Mathf.Infinity,dt);
   weight=Mathf.SmoothDamp(weight,wantWeight,ref weightVelocity,settleSeconds,Mathf.Infinity,dt);
   var gaze=transform.rotation*Quaternion.Euler(-pitch,yaw,0);
   var desired=Quaternion.LookRotation(gaze*Vector3.forward,gaze*Vector3.up);
   if(neck)Aim(neck,neckFaceLocal,neckUpLocal,desired,weight*neckShare);
   Aim(head,faceLocal,upLocal,desired,weight);
  }
  static void Aim(Transform bone,Vector3 face,Vector3 up,Quaternion desired,float w)
  {
   var current=Quaternion.LookRotation(bone.rotation*face,bone.rotation*up);
   bone.rotation=Quaternion.Slerp(Quaternion.identity,desired*Quaternion.Inverse(current),w)*bone.rotation;
  }
 }
}
