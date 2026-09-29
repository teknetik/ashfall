using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// Offline look-development preview of the combat FX prefabs in the real scene lighting. Run in batch mode WITH
    /// graphics (no -nographics): -executeMethod AthenHill.Editor.CombatFxPreview.RenderBatch --fx-out DIR [--fx-cam cam_depot_yard]
    /// Places a DroidDeathBurst 7 m in front of the named review camera, simulates it to fixed times, renders each frame
    /// through a URP camera to PNG. The scene is opened but never saved.
    public static class CombatFxPreview
    {
        static readonly float[] Times = { .04f, .12f, .35f, .8f, 1.6f, 3f, 5f, 7.5f };

        public static void RenderBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string name, string fallback) { int i = Array.IndexOf(args, name); return i >= 0 && i + 1 < args.Length ? args[i + 1] : fallback; }
            string outDir = Arg("--fx-out", "../evidence/combat-fx/preview"); string camName = Arg("--fx-cam", "cam_depot_yard");
            float dist = float.Parse(Arg("--fx-dist", "6"), System.Globalization.CultureInfo.InvariantCulture), side = float.Parse(Arg("--fx-side", "0"), System.Globalization.CultureInfo.InvariantCulture);
            float hour = float.Parse(Arg("--fx-hour", "13"), System.Globalization.CultureInfo.InvariantCulture);
            Directory.CreateDirectory(outDir);
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath, OpenSceneMode.Single);
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            ApplyHour(clock, hour);
            var review = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include).FirstOrDefault(c => c.name == camName);
            if (!review) throw new InvalidOperationException("No camera " + camName);
            var prefab = AssetDatabase.LoadAssetAtPath<FxBurst>("Assets/AthenHill/Prefabs/FX/DroidDeathBurst.prefab");
            var fx = UnityEngine.Object.Instantiate(prefab);
            var fwd = review.transform.forward; fwd.y = 0; fwd.Normalize();
            var right = Vector3.Cross(Vector3.up, fwd); var at = review.transform.position + fwd * dist + right * side;
            if (Physics.Raycast(at + Vector3.up * 5, Vector3.down, out var hit, 30)) at = hit.point;
            fx.transform.position = at + Vector3.up * .35f;

            var camGo = new GameObject("FX preview camera"); var cam = camGo.AddComponent<Camera>();
            cam.transform.SetPositionAndRotation(review.transform.position, Quaternion.LookRotation((at + Vector3.up * 1.2f) - review.transform.position));
            cam.fieldOfView = 50; cam.nearClipPlane = .1f; cam.farClipPlane = 2000;
            var data = camGo.AddComponent<UniversalAdditionalCameraData>(); data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            var rt = new RenderTexture(1280, 720, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 }; cam.targetTexture = rt;
            var tex = new Texture2D(1280, 720, TextureFormat.RGB24, false);
            cam.Render(); // warm-up: the first render after load has no shadows/lighting yet
            foreach (var t in Times)
            {
                foreach (var ps in fx.systems) { ps.Simulate(t, true, true, true); }
                if (fx.flash) { float i = t < fx.flashSeconds ? fx.flashIntensity * Mathf.Pow(1 - t / fx.flashSeconds, 2) : (t < fx.flashSeconds + fx.burnSeconds ? fx.burnIntensity * (1 - (t - fx.flashSeconds) / fx.burnSeconds) : 0); fx.flash.intensity = i; fx.flash.enabled = i > .02f; }
                cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1280, 720), 0, 0); tex.Apply(); RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine(outDir, string.Format("fx-{0}-h{1:00}-t{2:0.00}.png", camName, hour, t)), tex.EncodeToPNG());
            }
            Debug.Log("COMBAT_FX_PREVIEW wrote " + Times.Length + " frames to " + outDir);
            EditorApplication.Exit(0);
        }

        static void ApplyHour(CityTimeOfDay clock, float hour)
        {
            if (!clock || !clock.profile || !clock.keyLight) return;
            var f = clock.profile.Evaluate(hour);
            clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
            RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
        }
    }
}
