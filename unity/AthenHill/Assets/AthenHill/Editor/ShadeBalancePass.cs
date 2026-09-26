#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Staged audition. Only the Editor operator may invoke this against the
    // saved source scene. Existing noon/night/sun curves remain unchanged.
    public static class ShadeBalancePass
    {
        const string Previous = "Assets/AthenHill/Art/ReferenceStreet/20260909/WardReferenceDaylight.asset";
        const string PreviousHash = "0913b71941518b3b5ee015e7f4f2fe172268cfa755f9bd5c02af4ab63a5be5cf";
        const string Folder = "Assets/AthenHill/Art/ReferenceStreet/20260910/ShadeBalanceV1";
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static string Evidence => Path.Combine(Repo, "unity/evidence/reference-street/20260910/shade-balance-v1-install");
        static string Hash(string path) { using var s = File.OpenRead(path); using var h = SHA256.Create(); return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant(); }
        static void Record(string path, object value) => File.WriteAllText(Path.Combine(Evidence, path), JsonConvert.SerializeObject(value, Formatting.Indented));
        static string PathOf(Transform t) => AnimationUtility.CalculateTransformPath(t, null);
        static JObject FrameRecord(DayNightFrame frame) => JObject.Parse(JsonUtility.ToJson(frame));
        static T[] Components<T>(Scene scene) where T : Component => scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<T>(true)).ToArray();
        static string PreservedScene(Scene scene) => JsonConvert.SerializeObject(new {
            gameplay = DistrictCityPass.GameplaySignature(),
            transforms = Components<Transform>(scene).OrderBy(PathOf).Select(t => new { path = PathOf(t), transform = EditorJsonUtility.ToJson(t), active = t.gameObject.activeSelf }).ToArray(),
            colliders = Components<Collider>(scene).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
            renderers = Components<Renderer>(scene).OrderBy(c => PathOf(c.transform)).Select(c => new { path = PathOf(c.transform), data = EditorJsonUtility.ToJson(c) }).ToArray(),
            actors = Components<ActorAnimation>(scene).OrderBy(c => PathOf(c.transform)).Select(c => EditorJsonUtility.ToJson(c)).ToArray(),
            routes = Components<AmbientWalker>(scene).OrderBy(c => PathOf(c.transform)).Select(c => EditorJsonUtility.ToJson(c)).ToArray(),
            lights = Components<Light>(scene).OrderBy(c => PathOf(c.transform)).Select(c => EditorJsonUtility.ToJson(c)).ToArray()
        });

        public static void Apply()
        {
            var scene = SceneManager.GetActiveScene();
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating ||
                SceneManager.sceneCount != 1 || scene.path != ImportBaseline.ScenePath || scene.isDirty)
                throw new InvalidOperationException("Use the single saved native scene in settled Edit mode.");
            if (Directory.Exists(Folder) || Directory.Exists(Evidence)) throw new IOException("Preserve the existing lighting audition; use a new version.");
            var clock = Components<CityTimeOfDay>(scene).Single();
            var previous = AssetDatabase.LoadAssetAtPath<DayNightLightingProfile>(Previous);
            if (!previous || clock.profile != previous || Hash(Previous) != PreviousHash || !previous.IsValid(out _))
                throw new InvalidDataException("The recorded authored daylight profile changed.");
            var chunks = Components<StaticRenderChunks>(scene).Single();
            if (chunks.editingSources || chunks.sourceFingerprint != StaticRenderChunksEditor.Fingerprint(chunks))
                throw new InvalidOperationException("Rebuilt source chunks are required before the lighting audition.");
            if (Components<ActorAnimation>(scene).Length != 9 || Components<AmbientWalker>(scene).Length != 4)
                throw new InvalidOperationException("Preserve the full current actor roster.");
            string preserved = PreservedScene(scene), fingerprint = chunks.sourceFingerprint;
            var next = Object.Instantiate(previous); next.name = "Ward afternoon shade balance v1";
            int index = Array.FindIndex(next.frames, f => Mathf.Approximately(f.hour, 17.5f));
            if (index < 0 || next.frames.Count(f => Mathf.Approximately(f.hour, 17.5f)) != 1) throw new InvalidDataException("Expected the existing sunset key.");
            var frame = next.frames[index];
            frame.ambientSky = new Color(.29f, .37f, .48f, 1);
            frame.ambientEquator = new Color(.34f, .32f, .28f, 1);
            frame.ambientGround = new Color(.235f, .2f, .16f, 1);
            frame.fillIntensity = .15f;
            next.frames[index] = frame;
            if (!next.IsValid(out var reason)) throw new InvalidDataException(reason);
            // Changing a key's environment terms preserves the entire existing
            // clock/sun interpolation. No extra key is inserted into that curve.
            var proof = Enumerable.Range(0, 97).Select(i => {
                float hour = i / 4f; var a = previous.Evaluate(hour); var b = next.Evaluate(hour);
                b.ambientSky = a.ambientSky; b.ambientEquator = a.ambientEquator; b.ambientGround = a.ambientGround; b.fillIntensity = a.fillIntensity;
                if (JsonUtility.ToJson(a) != JsonUtility.ToJson(b)) throw new InvalidDataException("A non-environment clock field changed at " + hour);
                return new { hour, unchangedSunSkyExposureLamps = true };
            }).ToArray();
            Directory.CreateDirectory(Evidence); Directory.CreateDirectory(Folder);
            EditorSceneManager.SaveScene(scene, Path.Combine(Evidence, "before-scene.unity"), true);
            Record("clock-curve-preservation.json", proof);
            try
            {
                AssetDatabase.CreateAsset(next, Folder + "/WardAfternoonShade.asset");
                Undo.RecordObject(clock, "Audition afternoon environment balance");
                clock.profile = next; EditorUtility.SetDirty(clock);
                if (PreservedScene(scene) != preserved || chunks.sourceFingerprint != fingerprint || StaticRenderChunksEditor.Fingerprint(chunks) != fingerprint || Hash(Previous) != PreviousHash)
                    throw new InvalidDataException("Unrelated source content or retained daylight changed.");
                AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                Record("installation.json", new {
                    utc = DateTime.UtcNow.ToString("O"), scene = scene.path, sceneSha256 = Hash(scene.path),
                    previous = Previous, previousSha256 = PreviousHash, current = AssetDatabase.GetAssetPath(next),
                    before = new[] { previous.Evaluate(12), previous.Evaluate(16), previous.Evaluate(17.5f), previous.Evaluate(0) }.Select(FrameRecord).ToArray(),
                    after = new[] { next.Evaluate(12), next.Evaluate(16), next.Evaluate(17.5f), next.Evaluate(0) }.Select(FrameRecord).ToArray(),
                    preservedGeometryMaterialsCollidersActorsRoutesLights = true, sourceFingerprint = fingerprint,
                    scope = "Reversible late-day ambient/fill audition only. Native noon/16/17.5/night review required. No sun, sky, post-exposure, lamp, reflection-strength or clock timing change.",
                    artAccepted = false, performanceQualified = false
                });
            }
            catch (Exception e) { File.WriteAllText(Path.Combine(Evidence, "failure.txt"), e.ToString()); throw; }
        }
    }
}
#endif
