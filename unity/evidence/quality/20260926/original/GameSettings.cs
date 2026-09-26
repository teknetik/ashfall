using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill
{
    [Serializable]
    public sealed class SoundOptions
    {
        public float master = 1, music = 1, ambience = 1, effects = 1;
        public bool muted;
    }

    [Serializable]
    public sealed class VideoOptions
    {
        public int width = 1920, height = 1080, windowMode, preset = 2;
        public int renderPercent = 100, shadows = 3, antiAliasing = 4, textureLimit;
        public bool postProcessing = true, vSync;
        public int frameLimit = 60;
        public VideoOptions Copy() => (VideoOptions)MemberwiseClone();
        public bool SameAs(VideoOptions other) => JsonUtility.ToJson(this) == JsonUtility.ToJson(other);
        public void UsePreset(int index)
        {
            preset = Mathf.Clamp(index, 0, 2);
            renderPercent = preset == 0 ? 75 : 100;
            shadows = preset + 1;
            antiAliasing = preset == 0 ? 1 : preset == 1 ? 2 : 4;
            textureLimit = preset == 0 ? 1 : 0;
            postProcessing = preset != 0;
        }
    }

    // Saved video is always the last confirmed setup. Previews never reach disk.
    [DefaultExecutionOrder(-100)]
    public sealed class GameSettings : MonoBehaviour
    {
        public SoundOptions Sound { get; private set; }
        public VideoOptions Video { get; private set; }
        public VideoOptions Draft { get; private set; }
        public bool Previewing { get; private set; }
        public int SecondsRemaining => Mathf.Max(0, Mathf.CeilToInt(deadline - Time.realtimeSinceStartup));
        public bool HasChanges => !Draft.SameAs(Video);
        public event Action Changed;
        public string VideoMessage { get; private set; } = "";
        public UniversalRenderPipelineAsset Pipeline => runtimePipeline;
        public static readonly int[] FrameLimits = { 0, 30, 60, 90, 120, 144, 165, 240 };
        string prefix = "AthenHill.Settings.v1.";
        RenderPipelineAsset originalPipeline;
        UniversalRenderPipelineAsset runtimePipeline;
        UniversalAdditionalCameraData[] cameras;
        bool[] originalPostProcessing;
        int originalTextureLimit, originalVSync, originalFrameLimit;
        float deadline;
        bool previousRunInBackground;
        VideoOptions beforePreview;

        void Awake()
        {
            if (Debug.isDebugBuild && Array.IndexOf(Environment.GetCommandLineArgs(), "--athen-qa") >= 0) prefix += "QA.";
            Sound = Read("Sound", new SoundOptions());
            Sound.master = Volume(Sound.master); Sound.music = Volume(Sound.music);
            Sound.ambience = Volume(Sound.ambience); Sound.effects = Volume(Sound.effects);
            var defaults = new VideoOptions { width = Screen.width, height = Screen.height, windowMode = Screen.fullScreen ? 1 : 0 };
            Video = Read("Video", defaults);
            Sanitize(Video);
            Draft = Video.Copy();
            ApplySound();
        }

        void Start()
        {
            originalPipeline = QualitySettings.renderPipeline;
            var source = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (source)
            {
                runtimePipeline = Instantiate(source);
                runtimePipeline.name = source.name + " (player settings)";
                QualitySettings.renderPipeline = runtimePipeline;
            }
            cameras = FindObjectsByType<UniversalAdditionalCameraData>();
            originalPostProcessing = cameras.Select(c => c.renderPostProcessing).ToArray();
            originalTextureLimit = QualitySettings.globalTextureMipmapLimit;
            originalVSync = QualitySettings.vSyncCount; originalFrameLimit = Application.targetFrameRate;
            ApplyQuality(Video);
            // An explicit launcher resolution is also a way to recover a setup.
            bool launcherDisplay = Environment.GetCommandLineArgs().Any(a => a.StartsWith("-screen-"));
            if (PlayerPrefs.HasKey(prefix + "Video") && !Application.isEditor && !launcherDisplay) ApplyDisplay(Video);
            else SyncDisplay(Video);
            Draft = Video.Copy();
        }

        T Read<T>(string key, T fallback) where T : class
        {
            try { return PlayerPrefs.HasKey(prefix + key) ? JsonUtility.FromJson<T>(PlayerPrefs.GetString(prefix + key)) ?? fallback : fallback; }
            catch (ArgumentException) { return fallback; }
        }
        static float Volume(float value) => float.IsNaN(value) || float.IsInfinity(value) ? 1 : Mathf.Clamp01(value);
        public void SaveSound()
        {
            Sound.master = Volume(Sound.master); Sound.music = Volume(Sound.music);
            Sound.ambience = Volume(Sound.ambience); Sound.effects = Volume(Sound.effects);
            ApplySound();
            PlayerPrefs.SetString(prefix + "Sound", JsonUtility.ToJson(Sound));
            Changed?.Invoke();
        }
        public void ApplySound() => AudioListener.volume = Sound.muted ? 0 : Sound.master;
        public void Flush() => PlayerPrefs.Save();
        public void ResetSound() { Sound = new SoundOptions(); SaveSound(); }

        public List<Vector2Int> Resolutions()
        {
            int maxW = Mathf.Max(Display.main.systemWidth, Screen.currentResolution.width, Screen.width, Screen.resolutions.Length > 0 ? Screen.resolutions.Max(r => r.width) : 0);
            int maxH = Mathf.Max(Display.main.systemHeight, Screen.currentResolution.height, Screen.height, Screen.resolutions.Length > 0 ? Screen.resolutions.Max(r => r.height) : 0);
            var sizes = Screen.resolutions.Select(r => new Vector2Int(r.width, r.height)).ToList();
            sizes.AddRange(new[] { new Vector2Int(1024, 768), new Vector2Int(1280, 720), new Vector2Int(1280, 800), new Vector2Int(1366, 768), new Vector2Int(1600, 900), new Vector2Int(1920, 1080), new Vector2Int(1920, 1200), new Vector2Int(2560, 1440), new Vector2Int(3440, 1440), new Vector2Int(3840, 2160) });
            sizes = sizes.Where(s => s.x >= 800 && s.y >= 600 && s.x <= maxW && s.y <= maxH).ToList();
            sizes.Add(new Vector2Int(Screen.width, Screen.height));
            sizes.Add(new Vector2Int(Draft.width, Draft.height));
            return sizes.Distinct().OrderBy(s => s.x).ThenBy(s => s.y).ToList();
        }
        void Sanitize(VideoOptions value)
        {
            value.width = Mathf.Clamp(value.width, 800, Mathf.Max(800, Display.main.systemWidth, Screen.resolutions.Length > 0 ? Screen.resolutions.Max(r => r.width) : 0));
            value.height = Mathf.Clamp(value.height, 600, Mathf.Max(600, Display.main.systemHeight, Screen.resolutions.Length > 0 ? Screen.resolutions.Max(r => r.height) : 0));
            value.windowMode = Mathf.Clamp(value.windowMode, 0, 1);
            value.preset = Mathf.Clamp(value.preset, 0, 3);
            value.renderPercent = Mathf.Clamp(value.renderPercent, 50, 100);
            value.shadows = Mathf.Clamp(value.shadows, 0, 3);
            value.textureLimit = Mathf.Clamp(value.textureLimit, 0, 2);
            if (value.antiAliasing != 1 && value.antiAliasing != 2 && value.antiAliasing != 4 && value.antiAliasing != 8) value.antiAliasing = 4;
            if (!FrameLimits.Contains(value.frameLimit)) value.frameLimit = 60;
        }
        static void SyncDisplay(VideoOptions value) { value.width = Screen.width; value.height = Screen.height; value.windowMode = Screen.fullScreen ? 1 : 0; }
        static void ApplyDisplay(VideoOptions value) => Screen.SetResolution(value.width, value.height, value.windowMode == 0 ? FullScreenMode.Windowed : FullScreenMode.FullScreenWindow);
        void ApplyQuality(VideoOptions value)
        {
            if (runtimePipeline)
            {
                runtimePipeline.renderScale = value.renderPercent / 100f;
                runtimePipeline.msaaSampleCount = value.antiAliasing;
                runtimePipeline.shadowDistance = value.shadows == 0 ? 0 : value.shadows == 1 ? 12 : 18;
                runtimePipeline.mainLightShadowmapResolution = value.shadows <= 1 ? 1024 : value.shadows == 2 ? 2048 : 4096;
            }
            QualitySettings.globalTextureMipmapLimit = value.textureLimit;
            QualitySettings.vSyncCount = value.vSync ? 1 : 0;
            Application.targetFrameRate = value.frameLimit == 0 ? -1 : value.frameLimit;
            if (cameras != null) foreach (var cameraData in cameras) if (cameraData) cameraData.renderPostProcessing = value.postProcessing;
        }
        public void BeginEdit()
        {
            if (Previewing) RevertVideo();
            SyncDisplay(Video); Draft = Video.Copy(); VideoMessage = ""; Changed?.Invoke();
        }
        public void Edit(Action<VideoOptions> edit, bool custom = false)
        {
            if (Previewing) return;
            edit(Draft); if (custom) Draft.preset = 3;
            VideoMessage = ""; Changed?.Invoke();
        }
        public void ResetVideo() { Edit(v => { var defaults = new VideoOptions { width = Video.width, height = Video.height, windowMode = Video.windowMode }; Draft = defaults; }); }
        public void DiscardVideo() { Draft = Video.Copy(); VideoMessage = "Changes discarded."; Changed?.Invoke(); }
        public void ApplyVideo()
        {
            if (Previewing || !HasChanges) return;
            Sanitize(Draft);
            beforePreview = Video.Copy(); SyncDisplay(beforePreview);
            previousRunInBackground = Application.runInBackground;
            Application.runInBackground = true; // The display recovery timer must run even if focus is lost.
            Previewing = true; deadline = Time.realtimeSinceStartup + 15;
            ApplyQuality(Draft);
            if (!Application.isEditor) ApplyDisplay(Draft);
            Changed?.Invoke();
        }
        public void KeepVideo()
        {
            if (!Previewing) return;
            Previewing = false; Application.runInBackground = previousRunInBackground; Video = Draft.Copy(); SyncDisplay(Video); Draft = Video.Copy();
            PlayerPrefs.SetString(prefix + "Video", JsonUtility.ToJson(Video)); PlayerPrefs.Save();
            VideoMessage = "Video settings saved."; Changed?.Invoke();
        }
        public void RevertVideo()
        {
            if (!Previewing) return;
            Previewing = false; Application.runInBackground = previousRunInBackground; Video = beforePreview.Copy(); Draft = Video.Copy();
            ApplyQuality(Video); if (!Application.isEditor) ApplyDisplay(Video);
            VideoMessage = "Previous video settings restored."; Changed?.Invoke();
        }
        public void EndEdit() { if (Previewing) RevertVideo(); Draft = Video.Copy(); Flush(); }
        void Update() { if (Previewing && Time.realtimeSinceStartup >= deadline) RevertVideo(); }
        void OnApplicationQuit() => Flush();
        void OnDestroy()
        {
            if (Previewing) Application.runInBackground = previousRunInBackground;
            if (runtimePipeline) { QualitySettings.renderPipeline = originalPipeline; Destroy(runtimePipeline); }
            if (cameras != null)
            {
                for (int i = 0; i < cameras.Length; i++) if (cameras[i]) cameras[i].renderPostProcessing = originalPostProcessing[i];
                QualitySettings.globalTextureMipmapLimit = originalTextureLimit;
                QualitySettings.vSyncCount = originalVSync; Application.targetFrameRate = originalFrameLimit;
            }
        }
    }
}
