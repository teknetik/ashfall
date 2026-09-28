using UnityEngine;
namespace AthenHill
{
 [RequireComponent(typeof(CharacterController))]
 public class PlayerMotor : MonoBehaviour
 {
  public GameInput input;
  public Transform view;
  public Transform visual;
  public ActorAnimation actor;
  [Min(0)] public float walkSpeed=3.4f,runSpeed=6,gravity=22,groundSnap=.4f,turnSpeed=14;
  [Min(0)] public float jumpHeight=1.2f;
  public LayerMask worldMask=~(1<<8);
  public Transform spawn;
  public bool Grounded {get;private set;}
  public float Speed {get;private set;}
  public float VerticalSpeed => vertical;
  public bool JumpStarted {get;private set;}
  public bool Blocked,Talking;
  /// Set by PlayerCombat: aiming slows movement and turns the colonist to the camera heading.
  public float SpeedScale {get;set;}=1;
  public bool FaceView {get;set;}
  public float FaceYaw {get;set;}
  CharacterController body;
  float vertical;
  readonly PlayerRenderPose renderPose=new PlayerRenderPose();
  Vector3 visualLocalPosition;
  Transform presentationVisual;
  float RenderFraction=>PlayerRenderPose.Fraction(Time.timeAsDouble,Time.fixedTimeAsDouble,Time.fixedDeltaTime);
  public Vector3 RenderPosition=>isActiveAndEnabled?renderPose.Position(RenderFraction):transform.position;
  void Awake(){body=GetComponent<CharacterController>();}
  void OnEnable()
  {
   if(visual&&visual!=transform&&presentationVisual!=visual)
   {
    presentationVisual=visual;
    visualLocalPosition=visual.localPosition;
   }
   renderPose.Reset(transform.position,visual?visual.rotation:transform.rotation);
  }
  void FixedUpdate()
  {
   RestoreSimulationVisual();
   float dt=Mathf.Min(Time.fixedDeltaTime,.05f);
   var previous=transform.position;
   var move=Blocked?Vector2.zero:input.Move;
   Vector3 forward=Vector3.ProjectOnPlane(view.forward,Vector3.up).normalized;
   Vector3 right=Vector3.Cross(Vector3.up,forward);
   Vector3 direction=Vector3.ClampMagnitude(forward*move.y+right*move.x,1);
   bool wasGrounded=Grounded||body.isGrounded;
   bool jump=input.ConsumeJump();
   if(wasGrounded&&vertical<=0)vertical=-2;
   else vertical=Mathf.Max(vertical-gravity*dt,-35);
   JumpStarted=jump&&!Blocked&&wasGrounded&&vertical<=0;
   if(JumpStarted)vertical=Mathf.Sqrt(2*gravity*jumpHeight);
   var collisions=body.Move((direction*(input.Run&&SpeedScale>=1?runSpeed:walkSpeed*SpeedScale)+Vector3.up*vertical)*dt);
   if((collisions&CollisionFlags.Above)!=0&&vertical>0)vertical=0;
   Grounded=body.isGrounded;
   if(wasGrounded&&!Grounded&&vertical<=0 && Physics.SphereCast(transform.position+Vector3.up*.55f,.28f,Vector3.down,out var hit,.55f+groundSnap,worldMask,QueryTriggerInteraction.Ignore)&&hit.normal.y>.7f)
   {
    float drop=hit.distance-.27f;
    if(drop>0&&drop<=groundSnap){body.Move(Vector3.down*(drop+.02f));Grounded=body.isGrounded;}
   }
   Speed=Vector3.ProjectOnPlane(transform.position-previous,Vector3.up).magnitude/dt;
   if(FaceView)visual.rotation=Quaternion.Slerp(visual.rotation,Quaternion.Euler(0,FaceYaw,0),1-Mathf.Exp(-turnSpeed*1.6f*dt));
   else if(direction.sqrMagnitude>.001f)visual.rotation=Quaternion.Slerp(visual.rotation,Quaternion.LookRotation(direction),1-Mathf.Exp(-turnSpeed*dt));
   if(actor)actor.SetGroundMotion(Speed,input.Run&&SpeedScale>=1,Talking,Grounded,vertical,JumpStarted,dt);
   renderPose.Record(transform.position,visual?visual.rotation:transform.rotation);
   ActorMotionTrace.Sample(this);
  }
  void LateUpdate()
  {
   if(!presentationVisual)return;
   // Offset only the visual child. Physics, interactions and QA keep the current root.
   presentationVisual.localPosition=visualLocalPosition;
   presentationVisual.position+=RenderPosition-transform.position;
   presentationVisual.rotation=renderPose.Rotation(RenderFraction);
  }
  void RestoreSimulationVisual()
  {
   if(!presentationVisual)return;
   presentationVisual.localPosition=visualLocalPosition;
   presentationVisual.rotation=renderPose.SimulationRotation;
  }
  void OnDisable(){RestoreSimulationVisual();}
  public void Teleport(Vector3 feet){if(!body)body=GetComponent<CharacterController>();RestoreSimulationVisual();body.enabled=false;transform.position=feet+Vector3.up*.015f;body.enabled=true;vertical=0;Speed=0;Grounded=false;JumpStarted=false;renderPose.Reset(transform.position,visual?visual.rotation:transform.rotation);if(actor)actor.ResetGroundMotion();Physics.SyncTransforms();}
  public void ReturnToGate(){Teleport(spawn.position);}
 }
}
