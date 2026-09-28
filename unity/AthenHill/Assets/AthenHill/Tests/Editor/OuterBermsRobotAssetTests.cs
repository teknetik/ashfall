using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 27 Sep 2026 robot pass: guards against the regressions found in the depot review (static worker clips from the
 /// Blender 5 slotted-action export, baked root drift, self-lit glTF material, fused drone rotors) and checks that the
 /// depot nest still spawns the two droid prefabs with their gameplay components.
 public class OuterBermsRobotAssetTests
 {
  const string WorkerGlb="Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb";
  const string WorkerPrefab="Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab";
  const string DronePrefab="Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab";

  [Test] public void WorkerClipsAnimateWithoutHorizontalRootDrift()
  {
   var clips=AssetDatabase.LoadAllAssetsAtPath(WorkerGlb).OfType<AnimationClip>().ToDictionary(c=>c.name);
   foreach(var name in new[]{"idle","walk","run","attack","hit","death"})
   {
    Assert.That(clips.ContainsKey(name),Is.True,name);
    var clip=clips[name];
    int varying=AnimationUtility.GetCurveBindings(clip).Count(b=>{var k=AnimationUtility.GetEditorCurve(clip,b).keys;return k.Max(x=>x.value)-k.Min(x=>x.value)>1e-3f;});
    Assert.That(varying,Is.GreaterThan(40),name+" must animate (a static export writes only constant curves)");
   }
   foreach(var name in new[]{"idle","walk","run"})
    foreach(var axis in new[]{"m_LocalPosition.x","m_LocalPosition.z"})
    {
     var b=AnimationUtility.GetCurveBindings(clips[name]).First(x=>x.path=="Armature/Hips"&&x.propertyName==axis);
     var k=AnimationUtility.GetEditorCurve(clips[name],b).keys;var mean=k.Average(x=>x.value);
     // armature units are centimetres; rest Hips x/z are within a few cm of the root
     Assert.That(Mathf.Abs(mean),Is.LessThan(10),name+" "+axis+" drifts the body off its collider");
    }
  }

  [Test] public void WorkerPrefabHasPbrMaterialTelegraphAndFootsteps()
  {
   var root=AssetDatabase.LoadAssetAtPath<GameObject>(WorkerPrefab);
   var fd=root.GetComponent<FeralDroid>();Assert.That(root.GetComponent<Health>(),Is.Not.Null);
   var smr=root.GetComponentInChildren<SkinnedMeshRenderer>(true);var m=smr.sharedMaterial;
   Assert.That(m.shader.name,Is.EqualTo("Universal Render Pipeline/Lit"));
   Assert.That(m.GetTexture("_BumpMap"),Is.Not.Null);Assert.That(m.GetTexture("_MetallicGlossMap"),Is.Not.Null);
   Assert.That(m.GetTexture("_EmissionMap"),Is.Not.Null,"emission restricted to the optics");Assert.That(m.IsKeywordEnabled("_EMISSION"),Is.True);
   Assert.That(fd.glowRenderers,Does.Contain(smr));
   Assert.That(fd.feet.Length,Is.EqualTo(2));Assert.That(fd.feet.All(f=>f&&f.IsChildOf(root.transform)),Is.True);
   Assert.That(fd.footDust,Is.Not.Null);Assert.That(fd.footstepClips.Length,Is.EqualTo(2));Assert.That(fd.windupClip,Is.Not.Null);
   Assert.That(new[]{fd.idle,fd.walk,fd.run,fd.attack,fd.hit,fd.death}.All(c=>c),Is.True);
   Assert.That(fd.eyeLight.type,Is.EqualTo(LightType.Spot));
  }

  [Test] public void DronePrefabHasSpinningRotorsDownwashAndHum()
  {
   var root=AssetDatabase.LoadAssetAtPath<GameObject>(DronePrefab);
   var fd=root.GetComponent<FeralDroid>();Assert.That(fd.kind,Is.EqualTo(DroidKind.Hover));Assert.That(root.GetComponent<Health>(),Is.Not.Null);
   Assert.That(fd.rotors.Length,Is.EqualTo(2));
   foreach(var r in fd.rotors)
   {
    Assert.That(r.IsChildOf(root.transform.Find("Visual")),Is.True,"rotors bob and bank with the visual");
    var mesh=r.GetComponent<MeshFilter>().sharedMesh;Assert.That(mesh.triangles.Length/3,Is.GreaterThan(500));
    Assert.That(mesh.bounds.center.magnitude,Is.LessThan(.2f),"rotor mesh must be pivoted on its shaft");
   }
   Assert.That(fd.downwash,Is.Not.Null);Assert.That(fd.motorLoop,Is.Not.Null);Assert.That(fd.motorLoop.clip,Is.Not.Null);Assert.That(fd.motorLoop.loop,Is.True);
   Assert.That(fd.glowRenderers.Length,Is.EqualTo(1));Assert.That(fd.glowRenderers[0].sharedMaterial.IsKeywordEnabled("_EMISSION"),Is.True);
   Assert.That(root.transform.Find("Visual/ScrapDrone").gameObject.activeSelf,Is.False,"fused original kept inactive");
  }

  [Test] public void DepotNestStillSpawnsTheDroidPrefabs()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try {
    var nest=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<DroidEncounter>(true)).Single(e=>e.name=="Machine depot nest");
    Assert.That(nest.spawns.Length,Is.EqualTo(3));
    Assert.That(nest.spawns.Count(s=>s.prefab&&s.prefab.name=="FeralWorkerDroid"),Is.EqualTo(2));
    Assert.That(nest.spawns.Count(s=>s.prefab&&s.prefab.name=="FeralScrapDrone"),Is.EqualTo(1));
    Assert.That(nest.player,Is.Not.Null);Assert.That(nest.session,Is.Not.Null);
    var hum=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<AudioSource>(true)).Single(a=>a.name=="Cradle hum");
    Assert.That(hum.clip,Is.Not.Null);Assert.That(hum.loop,Is.True);
   } finally {EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
