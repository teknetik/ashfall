using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// Editor review stills for the district retrofit pass, with the lighting clock's default frame applied.
    /// Shots come from a JSON file (RETROFIT_SHOTS): [{name, eye[3], target[3], fov, ortho?}]. The scene is not saved.
    /// Native build captures remain the acceptance evidence.
    /// </summary>
    public static class DistrictRetrofitCapture
    {
        sealed class Shot { public string name; public float[] eye, target; public float fov = 60; public float ortho; public int w = 1600, h = 900; }

        public static void Run()
        {
            var scene = EditorSceneManager.OpenScene("Assets/AthenHill/Scenes/AthenHill.unity", OpenSceneMode.Single);
            var shots = JsonConvert.DeserializeObject<Shot[]>(File.ReadAllText(Environment.GetEnvironmentVariable("RETROFIT_SHOTS")));
            var outDir = Environment.GetEnvironmentVariable("RETROFIT_OUT"); Directory.CreateDirectory(outDir);
            var clock = UnityEngine.Object.FindFirstObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(clock.profile.defaultHour);
            clock.keyLight.transform.rotation = Quaternion.Euler(f.keyEuler); clock.keyLight.color = f.keyColor; clock.keyLight.intensity = f.keyIntensity;
            if (clock.skyFill) { clock.skyFill.color = f.fillColor; clock.skyFill.intensity = f.fillIntensity; }
            RenderSettings.ambientMode = AmbientMode.Trilight; RenderSettings.ambientSkyColor = f.ambientSky;
            RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
            var sky = new Material(clock.timeAwareSky);
            sky.SetColor("_Zenith", f.skyZenith); sky.SetColor("_Middle", f.skyMiddle); sky.SetColor("_Horizon", f.skyHorizon);
            sky.SetColor("_CloudLight", f.cloudLight); sky.SetColor("_CloudShade", f.cloudShade); sky.SetFloat("_Exposure", f.skyExposure);
            sky.SetFloat("_SunVisibility", f.sunVisibility); sky.SetVector("_SunDirection", -clock.keyLight.transform.forward);
            RenderSettings.skybox = sky; RenderSettings.sun = clock.keyLight;
            if (clock.gradingVolume && clock.gradingVolume.sharedProfile.TryGet<ColorAdjustments>(out var ca)) ca.postExposure.value = f.postExposure;
            bool noFog = Environment.GetEnvironmentVariable("RETROFIT_NOFOG") == "1";
            foreach (var s in shots)
            {
                var go = new GameObject("capture");
                var cam = go.AddComponent<Camera>();
                go.transform.position = new Vector3(s.eye[0], s.eye[1], s.eye[2]);
                var target = new Vector3(s.target[0], s.target[1], s.target[2]);
                if (s.ortho > 0) { go.transform.rotation = Quaternion.Euler(90, 0, 0); cam.orthographic = true; cam.orthographicSize = s.ortho; }
                else go.transform.LookAt(target);
                cam.fieldOfView = s.fov; cam.nearClipPlane = .1f; cam.farClipPlane = 650;
                var data = go.AddComponent<UniversalAdditionalCameraData>();
                data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
                data.volumeLayerMask = ~0; data.volumeTrigger = go.transform;
                bool fog = RenderSettings.fog; if (s.ortho > 0 || noFog) RenderSettings.fog = false;
                var rt = new RenderTexture(s.w, s.h, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 };
                cam.targetTexture = rt;
                for (int i = 0; i < 3; i++) cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(s.w, s.h, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, s.w, s.h), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(outDir, s.name + ".png"), tex.EncodeToPNG());
                RenderTexture.active = null; cam.targetTexture = null; rt.Release(); RenderSettings.fog = fog;
                UnityEngine.Object.DestroyImmediate(go); UnityEngine.Object.DestroyImmediate(tex);
            }
        }
    }
}
