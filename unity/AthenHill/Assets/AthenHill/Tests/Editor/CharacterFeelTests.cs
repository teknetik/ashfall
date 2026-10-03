using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Tests
{
 /// 27 Sep 2026 character-feel pass: serialized wiring for the calm guard idles, idle variation and look-at,
 /// surface footsteps, the layered pistol shot and the first-person view model.
 public class CharacterFeelTests
 {
  const string Scene="Assets/AthenHill/Scenes/AthenHill.unity";
  static readonly string[] GuardModelCharacters={"Warden Ossa","Warden Rell","npc_torr","npc_mira","npc_linn","npc_vex"};

  static T[] All<T>(UnityEngine.SceneManagement.Scene scene) where T:Component=>scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<T>(true)).ToArray();

  [Test] public void WardGuardPrefabUsesCalmIdleVariationAndLookAt()
  {
   var root=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/WardGuard.prefab");
   var actor=root.GetComponent<ActorAnimation>();
   Assert.That(actor.idle.name,Does.StartWith("idle_calm_"),"The scanning Meshy idle made the Wardens look paranoid.");
   Assert.That(actor.talk.name,Does.StartWith("talk_calm_"));
   Assert.That(actor.randomIdlePhase,Is.True);Assert.That(actor.idleSpeedJitter,Is.InRange(.02f,.2f));
   var look=root.GetComponent<ActorLookAt>();
   Assert.That(look,Is.Not.Null);Assert.That(look.head,Is.Not.Null);Assert.That(look.neck,Is.Not.Null);
   Assert.That(look.maxYaw,Is.LessThanOrEqualTo(60));Assert.That(look.maxPitch,Is.LessThanOrEqualTo(25));
  }

  [Test] public void GuardModelCharactersDoNotShareOneScanningLoop()
  {
   var scene=EditorSceneManager.OpenPreviewScene(Scene);
   try
   {
    // 3 Oct 2026 (WardNpcInstall): each of the six former guard-model characters now has its own model; the old guard
    // visual stays in the scene inactive for rollback, so test the actor each NpcAgent actually drives.
    var actors=All<NpcAgent>(scene).Where(n=>GuardModelCharacters.Contains(n.name)).Select(n=>n.actor).ToArray();
    Assert.That(actors.All(a=>a&&a.enabled&&a.gameObject.activeInHierarchy),Is.True,"Every character drives an active actor.");
    Assert.That(actors.Length,Is.EqualTo(6));
    foreach(var a in actors)
    {
     Assert.That(a.idle.name,Is.Not.EqualTo("idle_meshy"),a.name);Assert.That(a.talk.name,Is.Not.EqualTo("talk_meshy"),a.name);
     Assert.That(a.GetComponent<ActorLookAt>(),Is.Not.Null,a.name);
    }
    Assert.That(actors.Select(a=>a.idle.name).Distinct().Count(),Is.GreaterThanOrEqualTo(4),"Neighbours need different idle loops.");
    // placement-derived phases differ
    Assert.That(actors.Select(a=>Mathf.Round(Mathf.Repeat(Mathf.Abs(Mathf.Sin(a.transform.position.x*12.9898f+a.transform.position.z*78.233f+a.transform.position.y*37.719f)*43758.5453f),1)*20)).Distinct().Count(),Is.GreaterThanOrEqualTo(4));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void PlayerFootstepsCoverEverySurfaceAndReplaceTheDistanceCadence()
  {
   var scene=EditorSceneManager.OpenPreviewScene(Scene);
   try
   {
    var player=All<PlayerMotor>(scene).Single();
    var steps=player.GetComponent<FootstepAudio>();
    Assert.That(steps,Is.Not.Null);Assert.That(steps.source,Is.Not.Null);
    Assert.That(steps.leftFoot,Is.Not.Null);Assert.That(steps.rightFoot,Is.Not.Null);
    foreach(FootSurface s in System.Enum.GetValues(typeof(FootSurface)))
    {
     var set=steps.sets.Single(x=>x.surface==s);
     Assert.That(set.walk.Length,Is.GreaterThanOrEqualTo(8),s+" walk variants");
     Assert.That(set.run.Length,Is.GreaterThanOrEqualTo(8),s+" run variants");
     Assert.That(set.walk.Concat(set.run).Concat(set.land).All(c=>c),Is.True,s+" missing clip");
    }
    Assert.That(steps.bermsSurfaces.Length,Is.EqualTo(steps.bermsWidth*steps.bermsHeight));
    Assert.That(steps.bermsSurfaces.Distinct().Count(),Is.GreaterThanOrEqualTo(2),"Berms map should hold sand and gravel.");
    Assert.That(steps.volume,Is.LessThan(.8f),"Player steps were too loud.");
    Assert.That(All<CityAudio>(scene).Single().footsteps,Is.EqualTo(steps));
    var apron=All<Collider>(scene).First(c=>c.name=="Concrete apron");
    Assert.That(steps.SurfaceAt(apron.transform,apron.bounds.center),Is.EqualTo(FootSurface.Concrete));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }

  [Test] public void PistolHasLayeredShotAimPoseAndFirstPersonViewModel()
  {
   var scene=EditorSceneManager.OpenPreviewScene(Scene);
   try
   {
    var combat=All<PlayerCombat>(scene).Single();
    Assert.That(combat.shotMech.Length,Is.GreaterThanOrEqualTo(5));Assert.That(combat.shotBody.Length,Is.GreaterThanOrEqualTo(5));Assert.That(combat.shotTail.Length,Is.GreaterThanOrEqualTo(5));
    Assert.That(combat.emptyClips.Length+combat.drawClips.Length+combat.holsterClips.Length,Is.GreaterThanOrEqualTo(5));
    Assert.That(combat.tailSource,Is.Not.Null);Assert.That(combat.thirdPersonFlash,Is.Not.Null);
    var pose=combat.GetComponent<PlayerWeaponPose>();
    Assert.That(pose,Is.Not.Null);Assert.That(pose.aimClip,Is.Not.Null);Assert.That(pose.mixRoot,Is.Not.Null);Assert.That(pose.rightHand,Is.Not.Null);
    var vm=combat.viewModel;
    Assert.That(vm,Is.Not.Null);
    Assert.That(vm.rig&&vm.pistol&&vm.muzzle&&vm.flash&&vm.visuals&&vm.holdClip&&vm.overlayCamera&&vm.viewCamera,Is.True,"view model references");
    Assert.That(vm.visuals.activeSelf,Is.False,"Hidden until first person with the pistol drawn.");
    int layer=LayerMask.NameToLayer("ViewModel");
    Assert.That(layer,Is.GreaterThan(0));
    Assert.That(vm.visuals.GetComponentsInChildren<Renderer>(true).All(r=>r.gameObject.layer==layer),Is.True);
    Assert.That(vm.viewCamera.cullingMask&(1<<layer),Is.EqualTo(0),"Main camera must not draw the view model (it would clip into walls).");
    Assert.That(vm.overlayCamera.cullingMask,Is.EqualTo(1<<layer));
    Assert.That(vm.viewCamera.GetUniversalAdditionalCameraData().cameraStack,Does.Contain(vm.overlayCamera));
    Assert.That(vm.overlayCamera.GetUniversalAdditionalCameraData().renderType,Is.EqualTo(CameraRenderType.Overlay));
   }
   finally{EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
