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
  public LayerMask worldMask=~(1<<8);
  public Transform spawn;
  public bool Grounded {get;private set;}
  public float Speed {get;private set;}
  public bool Blocked;
  CharacterController body;
  float vertical;
  void Awake(){body=GetComponent<CharacterController>();}
  void FixedUpdate()
  {
   float dt=Mathf.Min(Time.fixedDeltaTime,.05f);
   var previous=transform.position;
   var move=Blocked?Vector2.zero:input.Move;
   Vector3 forward=Vector3.ProjectOnPlane(view.forward,Vector3.up).normalized;
   Vector3 right=Vector3.Cross(Vector3.up,forward);
   Vector3 direction=Vector3.ClampMagnitude(forward*move.y+right*move.x,1);
   bool wasGrounded=Grounded||body.isGrounded;
   vertical=wasGrounded?-2:Mathf.Max(vertical-gravity*dt,-35);
   body.Move((direction*(input.Run?runSpeed:walkSpeed)+Vector3.up*vertical)*dt);
   Grounded=body.isGrounded;
   if(wasGrounded&&!Grounded&&vertical<=0 && Physics.SphereCast(transform.position+Vector3.up*.55f,.28f,Vector3.down,out var hit,.55f+groundSnap,worldMask,QueryTriggerInteraction.Ignore)&&hit.normal.y>.7f)
   {
    float drop=hit.distance-.27f;
    if(drop>0&&drop<=groundSnap){body.Move(Vector3.down*(drop+.02f));Grounded=body.isGrounded;}
   }
   Speed=Vector3.ProjectOnPlane(transform.position-previous,Vector3.up).magnitude/dt;
   if(direction.sqrMagnitude>.001f)visual.rotation=Quaternion.Slerp(visual.rotation,Quaternion.LookRotation(direction),1-Mathf.Exp(-turnSpeed*dt));
   actor.SetMotion(Speed,input.Run,false);
  }
  public void Teleport(Vector3 feet){if(!body)body=GetComponent<CharacterController>();body.enabled=false;transform.position=feet+Vector3.up*.015f;body.enabled=true;vertical=0;Grounded=false;Physics.SyncTransforms();}
  public void ReturnToGate(){Teleport(spawn.position);}
 }
}
