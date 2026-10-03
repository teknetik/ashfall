using UnityEngine;
namespace AthenHill
{
 /// Support-hand IK (3 Oct 2026): the weapon hold clips were authored for the previous colonist and rifle, so the left
 /// hand floated off the gun on the MPFB body. After the animation, the aim pose and the view-model placement, this
 /// solves the left arm (two bones) onto a support-grip point on the drawn weapon (the rifle's handguard, or cupping
 /// the pistol grip) and turns the hand to the grip frame. Used on the colonist and on both first-person rigs.
 [DefaultExecutionOrder(500)]
 [DisallowMultipleComponent]
 public class SupportHandIK:MonoBehaviour
 {
  public PlayerCombat combat;
  public Transform upper,lower,hand;
  [Tooltip("Support grip on the pistol (hand placed and turned to this frame).")]public Transform pistolGrip;
  [Tooltip("Support grip on the rifle handguard.")]public Transform rifleGrip;
  [Range(0,1)]public float pistolWeight=1,rifleWeight=1;
  [Tooltip("Colonist only: scale by the aim-pose weight, so the hand goes onto the rifle while it is raised and stays free in the lowered carry.")]
  public PlayerWeaponPose scaleByAim;
  [Min(.01f)]public float blendSeconds=.12f;
  [Tooltip("Elbow direction in the upper bone's parent space: the solved arm turns about the shoulder-hand line so the elbow points this way; zero = keep the animated bend plane.")]public Vector3 poleHint=Vector3.zero;
  float weight;Transform current;
  void LateUpdate()
  {
   if(!upper||!lower||!hand||!combat)return;
   Transform target=null;float want=0;
   if(combat.Armed){if(combat.RifleActive){target=rifleGrip;want=rifleWeight;}else{target=pistolGrip;want=pistolWeight;}}
   if(target&&!target.gameObject.activeInHierarchy){target=null;}
   if(!target)want=0;
   if(scaleByAim)want*=scaleByAim.Weight;
   if(target)current=target;
   weight=Mathf.MoveTowards(weight,want,Time.deltaTime/Mathf.Max(.01f,blendSeconds));
   if(weight<=0.0001f||!current)return;
   Solve(current,weight);
  }
  public void Solve(Transform target,float w)
  {
   Vector3 a=upper.position,b=lower.position,c=hand.position,t=Vector3.Lerp(c,target.position,w);
   float ab=(b-a).magnitude,bc=(c-b).magnitude;if(ab<1e-4f||bc<1e-4f)return;
   float d=Mathf.Clamp((t-a).magnitude,Mathf.Abs(ab-bc)+1e-3f,ab+bc-1e-3f);
   // elbow: current interior angle -> the angle that puts the hand at distance d
   var axis=Vector3.Cross(a-b,c-b);
   if(axis.sqrMagnitude<1e-8f)axis=poleHint.sqrMagnitude>0&&upper.parent?upper.parent.TransformDirection(poleHint):Vector3.up;
   axis.Normalize();
   float cur=Vector3.Angle(a-b,c-b);
   float desired=Mathf.Acos(Mathf.Clamp((ab*ab+bc*bc-d*d)/(2*ab*bc),-1,1))*Mathf.Rad2Deg;
   lower.rotation=Quaternion.AngleAxis(desired-cur,axis)*lower.rotation;   // opens/closes the elbow about its own bend axis
   // shoulder: swing the chain so the hand points at the target
   c=hand.position;
   upper.rotation=Quaternion.FromToRotation(c-a,t-a)*upper.rotation;
   // elbow direction (3 Oct 2026): with a pole hint the chain turns about the shoulder-hand line so the elbow points
   // that way (first-person arms: elbows down and out, never across the view)
   if(poleHint.sqrMagnitude>0&&upper.parent)
   {
    var sh=(t-a);if(sh.sqrMagnitude>1e-8f)
    {
     sh.Normalize();
     var e=Vector3.ProjectOnPlane(lower.position-a,sh);var p=Vector3.ProjectOnPlane(upper.parent.TransformDirection(poleHint),sh);
     if(e.sqrMagnitude>1e-8f&&p.sqrMagnitude>1e-8f)upper.rotation=Quaternion.AngleAxis(Vector3.SignedAngle(e,p,sh),sh)*upper.rotation;
    }
   }
   // hand: turn to the grip frame
   hand.rotation=Quaternion.Slerp(hand.rotation,target.rotation,w);
  }
 }
}
