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
    var vm=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<FirstPersonViewModel>(true)).Single();
    var hands=vm.pistol.Find("FP hands v2");
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
