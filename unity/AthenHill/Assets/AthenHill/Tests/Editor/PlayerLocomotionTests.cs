using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Tests
{
 public class PlayerLocomotionTests
 {
  [Test]
  public void LocomotionKeepsTheIdleShoulderAttachmentAndClosesItsLoop()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try
   {
    var motor=scene.GetRootGameObjects().SelectMany(r=>r.GetComponentsInChildren<PlayerMotor>(true)).Single();
    var actor=motor.actor;var root=actor.animationSource.gameObject;
    var bones=actor.animationSource.GetComponentsInChildren<Transform>(true).ToDictionary(t=>t.name);
    Vector3 Direction(string side)=>bones["Spine"].InverseTransformDirection(bones[side+"Arm"].position-bones[side+"Shoulder"].position).normalized;
    actor.idle.SampleAnimation(root,0);
    var left=Direction("Left");var right=Direction("Right");
    foreach(var clip in new[]{actor.walk,actor.run})
    {
     for(int f=0;f<=40;f++)
     {
      clip.SampleAnimation(root,clip.length*f/40);
      Assert.That(Vector3.Angle(left,Direction("Left")),Is.LessThan(6),clip.name+" must not collapse the left collarbone relative to idle");
      Assert.That(Vector3.Angle(right,Direction("Right")),Is.LessThan(6),clip.name+" must not collapse the right collarbone relative to idle");
     }
     clip.SampleAnimation(root,0);var rotations=bones.ToDictionary(p=>p.Key,p=>p.Value.localRotation);var hip=bones["Hips"].localPosition;
     clip.SampleAnimation(root,clip.length);
     Assert.That(Vector3.Distance(hip,bones["Hips"].localPosition),Is.LessThan(.0005f),clip.name+" pelvis loop seam");
     foreach(var b in bones)Assert.That(Quaternion.Angle(rotations[b.Key],b.Value.localRotation),Is.LessThan(.15f),clip.name+" loop seam at "+b.Key);
    }
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
