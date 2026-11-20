using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Character arms pass (20 Nov 2026): the pure measures behind ArmPoseCorrector and the survey.
 public class ArmPoseMathTests
 {
  static readonly Vector3 Right=Vector3.right,Fwd=Vector3.forward,Down=Vector3.down;
  [Test]
  public void AbductionIsTheLeanOutOfTheSagittalPlane()
  {
   var arm=Quaternion.AngleAxis(20,Fwd)*Down;          // right arm swung out 20 deg (rotation about forward moves down toward +x)
   Assert.AreEqual(20,Mathf.Abs(ArmPoseMath.Abduction(arm,Right)),.01f);
   Assert.Greater(ArmPoseMath.Abduction(new Vector3(.3f,-1,0),Right),0);
   Assert.Less(ArmPoseMath.Abduction(new Vector3(-.3f,-1,0),Right),0);
   Assert.AreEqual(0,ArmPoseMath.Abduction(new Vector3(0,-1,.5f),Right),.01f);
  }
  [Test]
  public void WithAbductionSetsTheLeanAndKeepsTheSwing()
  {
   var arm=new Vector3(.4f,-1,.3f).normalized;
   var d=ArmPoseMath.WithAbduction(arm,Right,6);
   Assert.AreEqual(6,ArmPoseMath.Abduction(d,Right),.01f);
   // the sagittal heading (forward vs down) is unchanged
   Assert.AreEqual(Mathf.Atan2(arm.z,-arm.y),Mathf.Atan2(d.z,-d.y),1e-4f);
   var e=ArmPoseMath.WithForward(new Vector3(0,-1,1).normalized,Fwd,Vector3.up,30);
   Assert.AreEqual(30,ArmPoseMath.Forward(e,Fwd),.01f);
   // lowering a forward-and-out reach keeps the lean out of the body
   var reach=new Vector3(.3f,-.1f,1).normalized;
   var lowered=ArmPoseMath.WithForward(reach,Fwd,Vector3.up,30);
   Assert.AreEqual(ArmPoseMath.Abduction(reach,Right),ArmPoseMath.Abduction(lowered,Right),.01f);
   Assert.AreEqual(30,ArmPoseMath.Forward(lowered,Fwd),.01f);
  }
  [Test]
  public void ElbowOutIsZeroForAForwardBendAndPositiveWhenTheForearmCrossesTheBody()
  {
   var upper=Down;
   Assert.AreEqual(0,ArmPoseMath.ElbowOut(upper,ArmPoseMath.BendDirection(upper,new Vector3(0,-1,1)),Fwd,Vector3.up,Right),.01f);
   // right arm: forearm bending toward the midline (-x) = elbow turned out
   Assert.AreEqual(90,ArmPoseMath.ElbowOut(upper,ArmPoseMath.BendDirection(upper,new Vector3(-1,-1,0)),Fwd,Vector3.up,Right),.01f);
   Assert.AreEqual(180,Mathf.Abs(ArmPoseMath.ElbowOut(upper,ArmPoseMath.BendDirection(upper,new Vector3(0,-1,-1)),Fwd,Vector3.up,Right)),.01f);
   Assert.AreEqual(45,ArmPoseMath.ElbowFlex(upper,new Vector3(0,-1,1)),.01f);
   // an arm raised forward bending up toward the face is a normal flexion, not a backward elbow
   Assert.AreEqual(0,ArmPoseMath.ElbowOut(Fwd,ArmPoseMath.BendDirection(Fwd,new Vector3(0,1,1)),Fwd,Vector3.up,Right),.01f);
  }
  [Test]
  public void PalmFacingIsZeroTowardTheThighAndPositiveWhenThePalmFacesBack()
  {
   // right arm hanging: palm toward the midline (-x)
   Assert.AreEqual(0,ArmPoseMath.PalmFacing(Down,Vector3.left,Right,1),.01f);
   Assert.AreEqual(90,ArmPoseMath.PalmFacing(Down,Vector3.back,Right,1),.01f);
   Assert.AreEqual(-90,ArmPoseMath.PalmFacing(Down,Vector3.forward,Right,1),.01f);
   // left arm mirrored: palm toward +x is the thigh, back is still +
   Assert.AreEqual(0,ArmPoseMath.PalmFacing(Down,Vector3.right,-Right,-1),.01f);
   Assert.AreEqual(90,ArmPoseMath.PalmFacing(Down,Vector3.back,-Right,-1),.01f);
  }
  [Test]
  public void PullAndSoftLimits()
  {
   Assert.AreEqual(8.5f,ArmPoseMath.PullDown(12,7,.7f),1e-4f);
   Assert.AreEqual(5,ArmPoseMath.PullDown(5,7,.7f));
   Assert.AreEqual(35+15*.3f,ArmPoseMath.SoftMax(50,35,.3f),1e-4f);
   Assert.AreEqual(20,ArmPoseMath.SoftMax(20,35,.3f));
  }
 }
}
