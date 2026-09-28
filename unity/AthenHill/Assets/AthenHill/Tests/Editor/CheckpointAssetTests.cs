using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace AthenHill.Tests
{
 public class CheckpointAssetTests
 {
  [Test] public void SavedCheckpointHasIndependentGuardDialogueAndConnectedLocker()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try {
    var all=scene.GetRootGameObjects();var session=all.SelectMany(g=>g.GetComponentsInChildren<GameSession>(true)).Single();
    Assert.That(session.npcs.Count(n=>n.countsForCityVisit),Is.EqualTo(4),"New guards must preserve the four-colonist city objective.");
    var guards=session.npcs.Where(n=>!n.countsForCityVisit).ToArray();Assert.That(guards.Length,Is.EqualTo(2));
    foreach(var guard in guards)
    {
     Assert.That(guard.definition.nodes.Any(n=>n.id=="greeting"));
     foreach(var n in guard.definition.nodes){Assert.That(n.choices.Length,Is.EqualTo(2));foreach(var choice in n.choices.Where(c=>c.action!="close"))Assert.That(guard.definition.nodes.Any(next=>next.id==choice.next),Is.True,"No dead-end dialogue choices");}
     Assert.That(guard.GetComponentsInChildren<Transform>().Any(t=>t.name=="Warden secured sidearm"),Is.True);
    }
    var tutorial=all.SelectMany(g=>g.GetComponentsInChildren<BermsTutorial>(true)).Single();
    Assert.That(tutorial.locker,Is.Not.Null);Assert.That(tutorial.targets.Length,Is.EqualTo(3));
    Assert.That(tutorial.briefingWarden.name,Is.EqualTo("Warden Ossa"));
    // 26 Sep West Gate outpost: new cabinet visual is active under the interaction root; the first-pass cabinet is kept inactive for rollback.
    Assert.That(tutorial.locker.GetComponentsInChildren<Transform>().Any(t=>t.name=="Arms locker visual"),Is.True);
    Assert.That(tutorial.locker.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Arms issue cabinet"&&!t.gameObject.activeSelf),Is.True);
    var resets=all.SelectMany(g=>g.GetComponentsInChildren<RangeResetStation>(true)).ToArray();Assert.That(resets.Length,Is.EqualTo(1));Assert.That(resets[0].tutorial,Is.EqualTo(tutorial));
    foreach(var plate in tutorial.targets){Assert.That(plate.transform.Find("Target number"),Is.Not.Null);Assert.That(plate.pivot.GetComponentsInChildren<Transform>().Any(t=>t.name.StartsWith("Painted bullseye")),Is.True);}
    var target=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/OuterBerms/RangeTarget.prefab");
    Assert.That(target.GetComponent<RangeTarget>().pivot,Is.Not.Null);Assert.That(target.GetComponent<Health>(),Is.Not.Null);
    Assert.That(target.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Steel target plate"),Is.True);
    Assert.That(target.GetComponentsInChildren<Transform>(true).Any(t=>t.name=="Steel target stand"),Is.True);

   } finally {EditorSceneManager.ClosePreviewScene(scene);}
  }

  /// Each checkpoint landmark must resolve to its intended target under GameSession's rules:
  /// colonists/Wardens win within interactionRange, otherwise the nearest WorldInteractable within its own range.
  [Test] public void WestGateLandmarksResolveToTheIntendedInteraction()
  {
   var scene=EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
   try {
    var all=scene.GetRootGameObjects();var session=all.SelectMany(g=>g.GetComponentsInChildren<GameSession>(true)).Single();
    var marks=all.Single(g=>g.name=="Landmarks").transform;
    var world=all.SelectMany(g=>g.GetComponentsInChildren<WorldInteractable>(false)).ToArray();
    var outpost=all.Single(g=>g.name=="Outer Berms").transform.Find("West Gate outpost");
    Assert.That(outpost,Is.Not.Null,"West Gate outpost root");
    Assert.That(outpost.Find("Gate/West Gate portal"),Is.Not.Null);Assert.That(outpost.Find("Outpost/Warden post container"),Is.Not.Null);
    string Target(string landmark)
    {
     var p=marks.Find(landmark).position;
     var npc=session.npcs.Where(n=>n&&Vector3.Distance(n.transform.position,p)<=session.interactionRange).OrderBy(n=>Vector3.Distance(n.transform.position,p)).FirstOrDefault();
     if(npc)return npc.name;
     var w=world.Where(x=>Vector3.Distance(x.transform.position,p)<=x.range).OrderBy(x=>Vector3.Distance(x.transform.position,p)).FirstOrDefault();
     return w?w.name:"none";
    }
    Assert.That(Target("checkpoint_ossa"),Is.EqualTo("Warden Ossa"));
    Assert.That(Target("checkpoint_rell"),Is.EqualTo("Warden Rell"));
    Assert.That(Target("checkpoint_locker"),Is.EqualTo("Warden arms locker"));
    Assert.That(Target("checkpoint_board"),Is.EqualTo("Checkpoint field briefing"));
    Assert.That(Target("checkpoint_range_reset"),Is.EqualTo("Range reset control"));
   } finally {EditorSceneManager.ClosePreviewScene(scene);}
  }
 }
}
