using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
 /// 20 Nov 2026 (rifle_hands_20261120): the weapon-driven arms anchor of the first-person view models.
 public class RifleHandsTests
 {
  static void Pose(float aim,float follow,Vector3 nominalPos,Quaternion nominalRot,Vector3 actualPos,Quaternion actualRot,out Vector3 p,out Quaternion r)
   =>ViewModelArmsRig.Pose(new Vector3(1,2,3),Quaternion.Euler(0,90,0),new Vector3(.1f,-.2f,0),Quaternion.Euler(0,20,0),new Vector3(0,-.15f,-.05f),Quaternion.Euler(0,30,0),aim,
     nominalPos,nominalRot,actualPos,actualRot,follow,out p,out r);

  [Test] public void NoFollowAndNoAimAnchorIsTheSingleCameraAnchor()
  {
   // the pistol's set-up: aim anchor off (same as hip), follow 0 -> exactly camPos + camRot * anchor
   var cam=new Vector3(1,2,3);var camRot=Quaternion.Euler(10,90,0);var a=new Vector3(.03f,-.26f,.02f);var ar=Quaternion.Euler(5,-10,0);
   ViewModelArmsRig.Pose(cam,camRot,a,ar,a,ar,.7f,Vector3.zero,Quaternion.identity,Vector3.one,Quaternion.Euler(30,0,0),0,out var p,out var r);
   Assert.That(Vector3.Distance(p,cam+camRot*a),Is.LessThan(1e-5f));
   Assert.That(Quaternion.Angle(r,camRot*ar),Is.LessThan(.01f));
  }

  [Test] public void AimBlendsBetweenTheTwoAnchors()
  {
   var n=Vector3.zero;var q=Quaternion.identity;
   Pose(0,0,n,q,n,q,out var p0,out var r0);Pose(1,0,n,q,n,q,out var p1,out var r1);Pose(.5f,0,n,q,n,q,out var ph,out _);
   var camRot=Quaternion.Euler(0,90,0);
   Assert.That(Vector3.Distance(p0,new Vector3(1,2,3)+camRot*new Vector3(.1f,-.2f,0)),Is.LessThan(1e-5f));
   Assert.That(Vector3.Distance(p1,new Vector3(1,2,3)+camRot*new Vector3(0,-.15f,-.05f)),Is.LessThan(1e-5f));
   Assert.That(Vector3.Distance(ph,(p0+p1)/2),Is.LessThan(1e-5f));
   Assert.That(Quaternion.Angle(r0,camRot*Quaternion.Euler(0,20,0)),Is.LessThan(.01f));
   Assert.That(Quaternion.Angle(r1,camRot*Quaternion.Euler(0,30,0)),Is.LessThan(.01f));
  }

  [Test] public void FullFollowMovesTheArmsRigidlyWithTheWeapon()
  {
   var nominalPos=new Vector3(1.2f,1.8f,3.4f);var nominalRot=Quaternion.Euler(0,90,0);
   var actualPos=nominalPos+new Vector3(.02f,-.05f,.01f);var actualRot=Quaternion.Euler(12,85,3);
   Pose(0,0,nominalPos,nominalRot,actualPos,actualRot,out var p0,out var r0);
   Pose(0,1,nominalPos,nominalRot,actualPos,actualRot,out var p1,out var r1);
   // the arms keep their pose relative to the weapon
   var relNominal=Matrix4x4.TRS(nominalPos,nominalRot,Vector3.one).inverse*Matrix4x4.TRS(p0,r0,Vector3.one);
   var relActual=Matrix4x4.TRS(actualPos,actualRot,Vector3.one).inverse*Matrix4x4.TRS(p1,r1,Vector3.one);
   Assert.That(Vector3.Distance(relNominal.GetColumn(3),relActual.GetColumn(3)),Is.LessThan(1e-4f));
   Assert.That(Quaternion.Angle(relNominal.rotation,relActual.rotation),Is.LessThan(.05f));
  }

  [Test] public void TwistDegreesIsSignedAboutTheAxis()
  {
   Assert.That(SupportHandIK.TwistDegrees(Quaternion.AngleAxis(70,Vector3.up),Vector3.up),Is.EqualTo(70).Within(.01f));
   Assert.That(SupportHandIK.TwistDegrees(Quaternion.AngleAxis(-40,Vector3.up),Vector3.up),Is.EqualTo(-40).Within(.01f));
   // a pure swing has no twist; swing after twist keeps the twist
   Assert.That(SupportHandIK.TwistDegrees(Quaternion.AngleAxis(50,Vector3.right),Vector3.up),Is.EqualTo(0).Within(.01f));
   Assert.That(SupportHandIK.TwistDegrees(Quaternion.AngleAxis(30,Vector3.right)*Quaternion.AngleAxis(60,Vector3.up),Vector3.up),Is.EqualTo(60).Within(.01f));
  }

  [Test] public void TwistShareMovesTwistIntoTheForearmAndKeepsTheHand()
  {
   var root=new GameObject("ik test");
   try
   {
    var upper=new GameObject("upper").transform;upper.SetParent(root.transform,false);
    var lower=new GameObject("lower").transform;lower.SetParent(upper,false);lower.localPosition=new Vector3(0,-.26f,0);
    var hand=new GameObject("hand").transform;hand.SetParent(lower,false);hand.localPosition=new Vector3(0,-.25f,0);
    lower.localRotation=Quaternion.Euler(-30,0,0);   // bent elbow
    var target=new GameObject("target").transform;target.SetParent(root.transform,false);
    target.position=new Vector3(.05f,-.3f,.25f);
    // the target wants the hand turned 80 degrees about the forearm axis from the rest (identity) relation
    float Twist(SupportHandIK k)=>SupportHandIK.TwistDegrees(k.hand.localRotation*Quaternion.Inverse(k.restHandLocal),k.hand.localPosition.normalized);
    var ik=root.AddComponent<SupportHandIK>();ik.upper=upper;ik.lower=lower;ik.hand=hand;ik.restHandLocal=Quaternion.identity;
    ik.Solve(target,1);var aimRot=lower.rotation*Quaternion.AngleAxis(80,Vector3.down);target.rotation=aimRot;
    lower.localRotation=Quaternion.Euler(-30,0,0);upper.localRotation=Quaternion.identity;
    ik.twistShare=0;ik.Solve(target,1);float full=Twist(ik);
    lower.localRotation=Quaternion.Euler(-30,0,0);upper.localRotation=Quaternion.identity;
    ik.twistShare=.6f;ik.Solve(target,1);float shared=Twist(ik);
    Assert.That(Quaternion.Angle(hand.rotation,target.rotation),Is.LessThan(.05f),"hand keeps the grip frame");
    Assert.That(Vector3.Distance(hand.position,target.position),Is.LessThan(.002f),"hand stays on the target");
    Assert.That(Mathf.Abs(full),Is.GreaterThan(20f),"the test case has a real wrist twist");
    Assert.That(shared,Is.EqualTo(full*.4f).Within(1.5f),"60 % of the twist moved into the forearm");
   }
   finally{Object.DestroyImmediate(root);}
  }

  [Test] public void DrawFollowHoldsTheArmsWhileLowered()
  {
   Assert.That(ViewModelArmsRig.FollowFor(0,1,.3f),Is.EqualTo(0),"no follow (the pistol) stays none");
   Assert.That(ViewModelArmsRig.FollowFor(.6f,1,1),Is.EqualTo(.6f).Within(1e-5f),"drawn: the normal follow");
   Assert.That(ViewModelArmsRig.FollowFor(.6f,1,0),Is.EqualTo(1).Within(1e-5f),"holstered: the draw follow");
   Assert.That(ViewModelArmsRig.FollowFor(.6f,1,.45f),Is.GreaterThan(.9f),"mid-draw stays near the draw follow");
   Assert.That(ViewModelArmsRig.FollowFor(.6f,0,.45f),Is.EqualTo(.6f).Within(1e-5f),"draw follow below follow is ignored");
  }

  [Test] public void PartialFollowSitsBetween()
  {
   var nominalPos=new Vector3(1,2,3.4f);var q=Quaternion.Euler(0,90,0);var actualPos=nominalPos+new Vector3(0,-.1f,0);
   Pose(0,0,nominalPos,q,actualPos,q,out var p0,out _);Pose(0,.6f,nominalPos,q,actualPos,q,out var p6,out _);
   Assert.That(p6.y-p0.y,Is.EqualTo(-.06f).Within(1e-5f));
  }
 }
}
