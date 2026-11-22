using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 22 November 2026 (Carl: "recreate her the same way you did for the main character ... start with linn, brann, ossa.
    /// then the rest"): colonists rebuilt by the hero base route (Rodin mesh, Meshy rig with fingers, repainted face), see
    /// art/npc_rebuild_20261122. Assets only: each prefab is rebuilt in place through WardNpcInstall's import and prefab
    /// steps, so NpcAgent roots, definitions, dialogue, colliders and routes are untouched and the scene is not saved.
    /// Afterwards CharacterArmsPass20261120 install re-wires the arm correctors onto the new bones (that one saves the scene).
    ///
    /// Batch: RunBatch -nographics --steps build,verify [--npcs linn,brann,ossa]
    /// Rollback: art/npc_rebuild_20261122/unity/install.sh rollback
    /// </summary>
    public static class NpcRebuildPass20261122
    {
        const string Record = "../../art/npc_rebuild_20261122/build/out/";
        const string Report = "../../art/npc_rebuild_20261122/unity/";
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const uint InteriorLayer = 1u << 7;

        static WardNpcInstall.Spec S(string key, string title, float height, string idle, string talk, WardNpcInstall.Mount mount = WardNpcInstall.Mount.None, string prefab = null)
            => new WardNpcInstall.Spec { key = key, title = title, npcId = "npc_" + key, height = height, idle = idle, talk = talk, mount = mount, record = Record, prefabPath = prefab };

        static readonly WardNpcInstall.Spec[] All = {
            S("linn", "Linn", 1.63f, "idle_252", "talk_310"),
            S("brann", "Brann", 1.84f, "idle_246", "talk_309", prefab: "Assets/AthenHill/Prefabs/SalvageDealer.prefab"),
            S("ossa", "Ossa", 1.75f, "idle_243", "talk_313", WardNpcInstall.Mount.ThighHolsterPistol),
            S("mira", "Mira", 1.68f, "idle_244", "talk_313"),
            S("torr", "Torr", 1.76f, "idle_246", "talk_309"),
            S("vex", "Vex", 1.80f, "idle_243", "talk_314"),
            S("rell", "Rell", 1.88f, "idle_252", "talk_314", WardNpcInstall.Mount.BackRifle),
            S("tamsin", "Tamsin", 1.76f, "idle_248", "talk_309"),
        };
        /// Behind a counter in a lit interior: the interior lamps shine on rendering layer 7.
        static readonly string[] Indoors = { "brann", "tamsin" };

        static WardNpcInstall.Spec[] Chosen()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, "--npcs");
            var keys = i >= 0 ? a[i + 1].Split(',') : All.Select(s => s.key).ToArray();
            return All.Where(s => keys.Contains(s.key) && File.Exists(Record + s.key + "/rigged_fixed.glb")).ToArray();
        }

        static object Build()
        {
            var specs = Chosen(); var report = new Dictionary<string, object>();
            report["import"] = WardNpcInstall.Import(specs);
            foreach (var s in specs)
            {
                // BuildPrefabs keeps an existing material; the new body has its own textures, so copy the imported one over it.
                var src = AssetDatabase.LoadAllAssetsAtPath(s.Model).OfType<Material>().FirstOrDefault() ?? throw new Exception("No material in " + s.Model);
                var mat = AssetDatabase.LoadAssetAtPath<Material>(s.Material);
                if (mat) { EditorUtility.CopySerialized(src, mat); mat.name = s.title; EditorUtility.SetDirty(mat); }
            }
            AssetDatabase.SaveAssets();
            report["prefab"] = WardNpcInstall.BuildPrefabs(specs);
            foreach (var s in specs.Where(x => Indoors.Contains(x.key)))
            {
                var root = PrefabUtility.LoadPrefabContents(s.Prefab);
                try
                {
                    foreach (var r in root.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask |= InteriorLayer;
                    PrefabUtility.SaveAsPrefabAsset(root, s.Prefab);
                }
                finally { PrefabUtility.UnloadPrefabContents(root); }
            }
            AssetDatabase.SaveAssets();
            return report;
        }

        /// The three ambient walkers on the same route, through WardWalkerInstall's import and prefab steps.
        static object Walkers()
        {
            foreach (var w in WardWalkerInstall.Specs) w.record = Record;
            var report = new Dictionary<string, object> { ["import"] = WardWalkerInstall.Import() };
            foreach (var w in WardWalkerInstall.Specs)
            {
                var src = AssetDatabase.LoadAllAssetsAtPath(w.Model).OfType<Material>().FirstOrDefault() ?? throw new Exception("No material in " + w.Model);
                var mat = AssetDatabase.LoadAssetAtPath<Material>(w.Material);
                if (mat) { EditorUtility.CopySerialized(src, mat); mat.name = w.title; EditorUtility.SetDirty(mat); }
            }
            AssetDatabase.SaveAssets();
            report["prefab"] = WardWalkerInstall.BuildPrefabs();
            return report;
        }

        static object Verify()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var problems = new List<string>(); var rows = new List<object>();
            var agents = Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            foreach (var s in Chosen())
            {
                var found = agents.Where(a => a.definition && a.definition.id == s.npcId).ToArray();
                if (found.Length == 0) { problems.Add(s.key + ": no active NpcAgent"); continue; }
                foreach (var npc in found)
                {
                    string at = s.key + "@" + npc.name;
                    var actor = npc.actor;
                    if (!actor) { problems.Add(at + ": NpcAgent.actor is missing"); continue; }
                    if (PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(actor.gameObject) != s.Prefab) problems.Add(at + ": actor is not the rebuilt prefab");
                    var smrs = actor.GetComponentsInChildren<SkinnedMeshRenderer>(false).OrderByDescending(r => r.sharedMesh.triangles.Length).ToArray();
                    if (smrs.Length != 2) { problems.Add(at + ": " + smrs.Length + " active skinned meshes, expected LOD0 and LOD1"); continue; }
                    var mat = smrs[0].sharedMaterial;
                    var baseMap = mat ? mat.GetTexture("baseColorTexture") : null;
                    if (!baseMap || baseMap.width != 4096) problems.Add(at + ": base colour is not the new 4096 map");
                    if (!mat || !mat.GetTexture("normalTexture")) problems.Add(at + ": no normal map");
                    if (Indoors.Contains(s.key) && (smrs[0].renderingLayerMask & InteriorLayer) == 0) problems.Add(at + ": not on the interior light layer");
                    var anim = actor.animationSource;
                    if (!anim || !actor.idle || !actor.talk) { problems.Add(at + ": clips not wired"); continue; }
                    foreach (var clip in new[] { actor.idle, actor.talk })
                        if (AnimationUtility.GetCurveBindings(clip).Any(b => b.path.Length > 0 && !anim.transform.Find(b.path))) problems.Add(at + ": unresolved paths in " + clip.name);
                    actor.idle.SampleAnimation(anim.gameObject, 0);
                    var p = WardNpcInstall.Skin(smrs[0], actor.transform);
                    float height = (p.Max(v => v.y) - p.Min(v => v.y)) * actor.transform.lossyScale.y, sole = p.Min(v => v.y);
                    if (Mathf.Abs(height - s.height) > .05f) problems.Add(at + ": height " + height);
                    if (Mathf.Abs(sole) > .04f) problems.Add(at + ": sole " + sole);
                    var look = actor.GetComponent<ActorLookAt>();
                    if (!look || !look.head || !look.neck) problems.Add(at + ": look-at not wired");
                    var arms = actor.GetComponentInChildren<ArmPoseCorrector>() ?? actor.GetComponentInParent<ArmPoseCorrector>();
                    bool armsBound = arms && arms.leftArm && arms.rightArm && arms.leftHand && arms.rightHand && arms.leftArm.IsChildOf(anim.transform);
                    bool fingers = armsBound && arms.rightFingers != null && arms.rightFingers.Length == 15 && arms.rightFingers.All(t => t);
                    if (!armsBound) problems.Add(at + ": arm corrector not on the new bones (run the arms install)");
                    else if (!fingers) problems.Add(at + ": fingers not wired (run the arms install)");
                    string mount = s.mount == WardNpcInstall.Mount.ThighHolsterPistol ? WardNpcInstall.PistolMount : s.mount == WardNpcInstall.Mount.BackRifle ? WardNpcInstall.RifleMount : null;
                    if (mount != null && !actor.GetComponentsInChildren<Transform>().Any(t => t.name == mount)) problems.Add(at + ": weapon mount missing");
                    rows.Add(new { who = at, height, sole, triangles = smrs.Select(r => r.sharedMesh.triangles.Length / 3).ToArray(), bones = smrs[0].bones.Length, armsBound, fingers });
                }
            }
            foreach (var w in WardWalkerInstall.Specs)
            {
                var walker = Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).FirstOrDefault(x => x.name == w.walker);
                var actor = walker ? walker.actor : null;
                if (!actor || PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(actor.gameObject) != w.Prefab) { problems.Add(w.key + ": walker actor missing or not its prefab"); continue; }
                if (!actor.animationSource || !actor.walk) { problems.Add(w.key + ": walk not wired"); continue; }
                if (AnimationUtility.GetCurveBindings(actor.walk).Any(b => b.path.Length > 0 && !actor.animationSource.transform.Find(b.path))) problems.Add(w.key + ": unresolved walk paths");
                var arms = actor.GetComponentInChildren<ArmPoseCorrector>() ?? actor.GetComponentInParent<ArmPoseCorrector>();
                if (!arms || !arms.leftArm || !arms.rightArm) problems.Add(w.key + ": arm corrector not on the new bones (run the arms install)");
                float rate = actor.walkStrideSpeed > 0 ? walker.speed / actor.walkStrideSpeed : 0;
                if (rate < .8f || rate > 1.3f) problems.Add(w.key + ": walk playback rate " + rate + " (feet would slide or race)");
                rows.Add(new { who = w.key, walker.speed, stride = actor.walkStrideSpeed, rate });
            }
            return new { ok = problems.Count == 0, problems, rows };
        }

        public static void RunBatch()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, "--steps");
            int code = 0;
            try
            {
                foreach (var step in (i >= 0 ? a[i + 1] : "verify").Split(','))
                {
                    object r = step switch { "build" => Build(), "walkers" => Walkers(), "verify" => Verify(), _ => throw new ArgumentException("unknown step " + step) };
                    string json = JsonConvert.SerializeObject(r, Formatting.Indented);
                    File.WriteAllText(Report + step + "-result.json", json);
                    Debug.Log("NpcRebuildPass20261122 " + step + "\n" + json);
                    if (step == "verify" && json.Contains("\"ok\": false")) code = 2;
                }
            }
            catch (Exception e) { Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }
    }
}
