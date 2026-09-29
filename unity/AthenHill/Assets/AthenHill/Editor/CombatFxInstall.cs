using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
    /// Adds the "Combat FX" scene object (CombatFx director wired to the session, follow camera, player and the two
    /// pooled prefabs). Refuses if a CombatFx already exists. Gameplay does not depend on it; delete the object to remove.
    public static class CombatFxInstall
    {
        [MenuItem("Athen Hill/Combat/Install combat FX in scene")]
        public static void Install()
        {
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            if (UnityEngine.Object.FindAnyObjectByType<CombatFx>(FindObjectsInactive.Include)) throw new InvalidOperationException("Combat FX is already installed.");
            var go = new GameObject("Combat FX"); var fx = go.AddComponent<CombatFx>();
            fx.session = UnityEngine.Object.FindAnyObjectByType<GameSession>();
            fx.follow = UnityEngine.Object.FindAnyObjectByType<FollowCamera>();
            fx.player = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>();
            fx.deathBurst = AssetDatabase.LoadAssetAtPath<FxBurst>("Assets/AthenHill/Prefabs/FX/DroidDeathBurst.prefab");
            fx.hitFlash = AssetDatabase.LoadAssetAtPath<FxBurst>("Assets/AthenHill/Prefabs/FX/HitFlash.prefab");
            fx.groundMask = LayerMask.GetMask("Default");
            if (!fx.session || !fx.follow || !fx.player || !fx.deathBurst || !fx.hitFlash) throw new InvalidOperationException("Combat FX references are incomplete.");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Debug.Log("COMBAT_FX installed in scene");
        }

        public static void InstallBatch() { Install(); EditorApplication.Exit(0); }
    }
}
