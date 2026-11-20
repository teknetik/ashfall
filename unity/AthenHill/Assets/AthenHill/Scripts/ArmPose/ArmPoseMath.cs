using UnityEngine;
namespace AthenHill
{
 /// Pure arm-pose measures and soft limits (character arms pass, 20 Nov 2026; art/character_arms_20261120/README.md).
 /// All directions are world vectors; the torso frame (right, up, forward) comes from the chest bone's bind axes.
 /// "side" is +1 for the right arm and -1 for the left, so "lateral" = side * torso right points away from the body.
 public static class ArmPoseMath
 {
  /// Degrees the upper arm leans out of the torso's sagittal plane (positive = away from the body).
  public static float Abduction(Vector3 upperDir,Vector3 lateral)=>Mathf.Asin(Mathf.Clamp(Vector3.Dot(upperDir.normalized,lateral.normalized),-1,1))*Mathf.Rad2Deg;
  /// Degrees the upper arm points forward of the torso's frontal plane (positive = forward, negative = behind).
  public static float Forward(Vector3 upperDir,Vector3 forward)=>Mathf.Asin(Mathf.Clamp(Vector3.Dot(upperDir.normalized,forward.normalized),-1,1))*Mathf.Rad2Deg;
  /// Elbow flexion in degrees (0 = straight arm).
  public static float ElbowFlex(Vector3 upperDir,Vector3 foreDir)=>Vector3.Angle(upperDir,foreDir);
  /// The direction the forearm bends toward, perpendicular to the upper arm (zero for a straight arm).
  public static Vector3 BendDirection(Vector3 upperDir,Vector3 foreDir)
  {
   var u=upperDir.normalized;var b=foreDir-Vector3.Dot(foreDir,u)*u;
   return b.sqrMagnitude<1e-8f?Vector3.zero:b.normalized;
  }
  /// How far the elbow points out of the body, in degrees about the upper arm: 0 = the forearm bends toward the front of
  /// the upper arm (the biceps side: forward for a hanging arm, up for an arm raised forward), positive = the forearm
  /// bends across the body (elbow turned out, "gunslinger"), negative = it bends outward; +-180 = the elbow bends backward.
  public static float ElbowOut(Vector3 upperDir,Vector3 bendDir,Vector3 forward,Vector3 up,Vector3 lateral)
  {
   var u=upperDir.normalized;
   var front=Front(u,forward,up);
   var f=front-Vector3.Dot(front,u)*u;var m=-lateral-Vector3.Dot(-lateral,u)*u;
   if(f.sqrMagnitude<1e-8f||bendDir.sqrMagnitude<1e-8f)return 0;
   f.Normalize();
   m=m-Vector3.Dot(m,f)*f;if(m.sqrMagnitude<1e-8f)return 0;m.Normalize();
   return Mathf.Atan2(Vector3.Dot(bendDir,m),Vector3.Dot(bendDir,f))*Mathf.Rad2Deg;
  }
  /// The front of the upper arm (the side the elbow bends toward): forward turned by the arm's elevation in the sagittal
  /// plane (forward for a hanging arm, up for an arm raised forward).
  public static Vector3 Front(Vector3 upperDir,Vector3 forward,Vector3 up)
  {
   var u=upperDir.normalized;float theta=Mathf.Atan2(Vector3.Dot(u,forward),-Vector3.Dot(u,up));
   return forward*Mathf.Cos(theta)+up*Mathf.Sin(theta);
  }
  /// Palm facing about the forearm axis, in degrees: 0 = palm toward the body's midline (thigh, for a hanging arm),
  /// positive = turned so the palm faces back (pronation), negative = palm forward (supination), +-180 = palm out.
  public static float PalmFacing(Vector3 foreDir,Vector3 palmNormal,Vector3 lateral,float side)
  {
   var f=foreDir.normalized;
   var m=-lateral-Vector3.Dot(-lateral,f)*f;
   if(m.sqrMagnitude<1e-6f)return 0;   // forearm pointing straight across the body: undefined
   m.Normalize();
   var back=side*Vector3.Cross(f,m);
   var p=palmNormal-Vector3.Dot(palmNormal,f)*f;
   return Mathf.Atan2(Vector3.Dot(p,back),Vector3.Dot(p,m))*Mathf.Rad2Deg;
  }
  /// The pulled value: values above target come down by pull (0..1) of their excess; below target they are kept.
  public static float PullDown(float value,float target,float pull)=>value>target?target+(value-target)*(1-Mathf.Clamp01(pull)):value;
  /// A soft ceiling: up to limit unchanged, above it the excess is kept at the given share (0 = hard limit).
  public static float SoftMax(float value,float limit,float keep)=>value>limit?limit+(value-limit)*Mathf.Clamp01(keep):value;
  /// The unit direction with the same sagittal heading as dir but leaning out of the sagittal plane by abduction degrees.
  public static Vector3 WithAbduction(Vector3 dir,Vector3 lateral,float abductionDeg)
  {
   var l=lateral.normalized;var s=dir-Vector3.Dot(dir,l)*l;
   if(s.sqrMagnitude<1e-8f)return dir.normalized;
   s.Normalize();float a=abductionDeg*Mathf.Deg2Rad;
   return (s*Mathf.Cos(a)+l*Mathf.Sin(a)).normalized;
  }
  /// The unit direction pointing forward by forwardDeg with its sideways part kept (the trade is between forward and
  /// vertical, in the sagittal plane), so lowering a forward reach never swings the arm out.
  public static Vector3 WithForward(Vector3 dir,Vector3 forward,Vector3 up,float forwardDeg)
  {
   var f=forward.normalized;var u=(up-Vector3.Dot(up,f)*f).normalized;
   dir.Normalize();
   float F=Vector3.Dot(dir,f),U=Vector3.Dot(dir,u);var side=dir-F*f-U*u;
   float s2=side.sqrMagnitude;
   float F2=Mathf.Sin(forwardDeg*Mathf.Deg2Rad);
   float rest=Mathf.Max(0,1-s2);
   F2=Mathf.Clamp(F2,-Mathf.Sqrt(rest),Mathf.Sqrt(rest));
   float U2=Mathf.Sqrt(Mathf.Max(0,rest-F2*F2))*(U>0?1:-1);
   return (side+f*F2+u*U2).normalized;
  }
  /// Rotation about axis by the angle (degrees, magnitude) in whichever direction moves measure(rotated) toward target.
  public static Quaternion TurnToward(Vector3 axis,float magnitude,System.Func<Quaternion,float> measure,float target)
  {
   if(Mathf.Abs(magnitude)<1e-3f||axis.sqrMagnitude<1e-8f)return Quaternion.identity;
   var a=Quaternion.AngleAxis(magnitude,axis);var b=Quaternion.AngleAxis(-magnitude,axis);
   return Mathf.Abs(Mathf.DeltaAngle(measure(a),target))<=Mathf.Abs(Mathf.DeltaAngle(measure(b),target))?a:b;
  }
 }
}
