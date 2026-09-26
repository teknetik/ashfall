using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Tests
{
    public class CharacterMotionAssetTests
    {
        [Test]
        public void SavedPlayerShadowProxiesShareTheInterpolatedVisualHierarchy()
        {
            // Inspect the persisted scene without replacing the user's open scene.
            var scene = EditorSceneManager.OpenPreviewScene("Assets/AthenHill/Scenes/AthenHill.unity");
            try
            {
                var players = scene.GetRootGameObjects().SelectMany(root => root.GetComponentsInChildren<PlayerMotor>(true)).ToArray();
                Assert.That(players.Length, Is.EqualTo(1));
                var player = players[0];
                Assert.That(player.visual, Is.Not.Null);
                Assert.That(player.visual.parent, Is.EqualTo(player.transform));
                Assert.That(PrefabUtility.GetCorrespondingObjectFromSource(player.visual), Is.Not.Null,
                    "Keep the supplied player prefab editable and connected.");
                var proxies = player.GetComponentsInChildren<MeshRenderer>(true)
                    .Where(renderer => renderer.enabled && renderer.gameObject.activeInHierarchy &&
                        renderer.shadowCastingMode == ShadowCastingMode.ShadowsOnly).ToArray();
                Assert.That(proxies, Is.Not.Empty, "The current authored shadow proxy must not be lost during hierarchy edits.");
                foreach (var proxy in proxies)
                {
                    Assert.That(proxy.transform.IsChildOf(player.visual), Is.True,
                        "A shadow-only proxy on the physics root advances at 50 Hz ahead of the interpolated actor.");
                    Assert.That(proxy.GetComponentsInChildren<Collider>(true), Is.Empty,
                        "Presentation-only shadow geometry must not move collision with render interpolation.");
                }
                Assert.That(player.GetComponent<CharacterController>(), Is.Not.Null);
            }
            finally { EditorSceneManager.ClosePreviewScene(scene); }
        }

        [TestCase("Player/idle.anim")]
        [TestCase("Player/jump_takeoff.anim")]
        [TestCase("Player/jump_airborne.anim")]
        [TestCase("Player/jump_fall.anim")]
        [TestCase("Player/jump_landing.anim")]
        [TestCase("Player/jump_landing_moving.anim")]
        [TestCase("Guard/idle_meshy.anim")]
        [TestCase("Guard/talk_meshy.anim")]
        public void InstalledMotionHasRealBoneKeysAndNoActorRootTranslation(string file)
        {
            var clip=AssetDatabase.LoadAssetAtPath<AnimationClip>("Assets/AthenHill/Art/CharacterMotion/"+file);
            Assert.That(clip,Is.Not.Null,"Run the scoped CharacterMotionPass installer before asset qualification.");
            Assert.That(clip.legacy,Is.True,"Keep the supplied legacy rigs compatible.");
            Assert.That(clip.length,Is.GreaterThanOrEqualTo(.1f));
            var bindings=AnimationUtility.GetCurveBindings(clip);
            int animatedBones=bindings.Where(b=>b.propertyName.Contains("Rotation")).Where(b=>{
                var curve=AnimationUtility.GetEditorCurve(clip,b);
                return curve.length>=4&&curve.keys.Max(k=>k.value)-curve.keys.Min(k=>k.value)>.001f;
            }).Select(b=>b.path).Distinct().Count();
            Assert.That(animatedBones,Is.GreaterThanOrEqualTo(3),"Static aliases are not authored animation.");
            Assert.That(bindings.Any(b=>(b.path==""||b.path=="Armature")&&b.propertyName.Contains("Position")),Is.False,
                "Animation must not translate the actor/controller root.");
        }
    }
}
