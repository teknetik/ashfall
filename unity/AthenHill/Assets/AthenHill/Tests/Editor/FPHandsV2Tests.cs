using System.Linq;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Tests
{
 /// 27 Sep 2026 pm (request #6): the first-person two-hand grip mesh is attached to the view-model pistol at unit scale,
 /// on the ViewModel layer, with the player-matched materials, and the old colonist-cut arms are hidden (kept for rollback).
 public class FPHandsV2Tests
 {
  const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";

  [Test] public void ViewModelUsesTheGripHandsAndHidesTheOldArms()
  {
   var scene=EditorSceneManager.OpenPreviewScene(Scene);
   try
   {
    // 3 Oct 2026: a second view model exists for the field rifle; this test is about the pistol's grip hands
    var vm=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<FirstPersonViewModel>(true)).Single(v=>!v.rifle);
    var hands=vm.pistol.Find("FP hands v2");
    // 3 Oct 2026 (player_face_20261003): the pistol view model shows the player's own MPFB arms (same skin as the body)
    // with solved finger grips; the authored grip mesh stays attached but inactive for rollback.
    if(hands&&!hands.gameObject.activeSelf)
    {
     var arms=vm.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s=>!s.transform.IsChildOf(vm.pistol)&&!s.name.StartsWith("FP armour")).ToArray();
     Assert.That(arms.Length,Is.GreaterThan(0),"player arms on the pistol view model");
     foreach(var s in arms)
     {
      Assert.That(s.enabled,Is.True,s.name);
      Assert.That(s.sharedMaterials.Any(m=>m&&m.name=="PlayerSkin"),Is.True,"arms use the body's PlayerSkin: "+s.name);
      Assert.That(s.shadowCastingMode,Is.EqualTo(UnityEngine.Rendering.ShadowCastingMode.Off),s.name);
     }
     var grip=vm.GetComponentInChildren<PlayerHandGrip>(true);
     Assert.That(grip,Is.Not.Null,"finger grip on the pistol arms");
     Assert.That(grip.pistolRight.Length,Is.EqualTo(grip.rightFingers.Length),"solved shooting-hand grip");
     Assert.That(grip.pistolLeft.Length,Is.EqualTo(grip.leftFingers.Length),"solved support-hand grip");
     var iks=vm.GetComponentsInChildren<SupportHandIK>(true);
     Assert.That(iks.Count(k=>k.pistolGrip&&k.pistolGrip.IsChildOf(vm.pistol)),Is.EqualTo(2),"both hands IK'd onto grip points on the view-model pistol");
     var armsRig=vm.GetComponent<ViewModelArmsRig>();
     Assert.That(armsRig&&armsRig.arms&&armsRig.arms!=vm.rig,Is.True,"weapon-driven: arms anchored to the camera, the pistol on its own mount");
     return;
    }
    Assert.That(hands,Is.Not.Null,"PlayerFPHands_v2 is not attached to the view-model pistol");
    Assert.That(hands.gameObject.activeSelf,Is.True);
    Assert.That(hands.localPosition.magnitude,Is.LessThan(1e-4f));Assert.That(Quaternion.Angle(hands.localRotation,Quaternion.identity),Is.LessThan(.01f));
    Assert.That(Vector3.Distance(hands.lossyScale,Vector3.one),Is.LessThan(1e-3f),"authored in metres in the pistol frame");
    var rs=hands.GetComponentsInChildren<Renderer>(true);
    Assert.That(rs.Length,Is.GreaterThan(0));
    foreach(var r in rs)
    {
     Assert.That(r.gameObject.layer,Is.EqualTo(vm.pistol.gameObject.layer),r.name);
     Assert.That(r.shadowCastingMode,Is.EqualTo(UnityEngine.Rendering.ShadowCastingMode.Off),r.name);
     Assert.That(r.sharedMaterials.All(m=>m&&m.name.StartsWith("FPHands")),Is.True,r.name);
    }
    var meshes=hands.GetComponentsInChildren<MeshFilter>(true).Select(f=>f.sharedMesh).ToArray();
    int tris=meshes.Sum(m=>m.triangles.Length/3);
    // 27 Sep eve (v5, CC0 MakeHuman hand, 2 x 54,144 tris = 110,328): the view-model hands fill a large part of the
    // screen, so the old 40k ceiling (a v2 procedural-mesh assumption) was raised; cost is judged by native frame time
    // (AGENTS.md §6/§7). The floor still catches a missing or degenerate mesh.
    Assert.That(tris,Is.InRange(8000,150000));
    // human scale: the pair spans roughly a grip width plus two hands across, and the forearms run back out of frame
    var b=meshes[0].bounds;
    Assert.That(b.size.x,Is.InRange(.12f,.80f));Assert.That(b.min.z,Is.LessThan(-.3f));
    foreach(var s in vm.rig.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s=>!s.transform.IsChildOf(vm.pistol)))
     Assert.That(s.enabled,Is.False,"old arms "+s.name+" should be hidden");
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
