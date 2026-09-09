using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Tests
{
    public class CharacterMotionAssetTests
    {
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
