using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
namespace AthenHill
{
    /// A global post-processing volume that exists only while a showcase camera needs it (19 Nov 2026). It owns a runtime
    /// profile with its own DepthOfField (and optionally ColorAdjustments for exposure) and never touches the saved grade
    /// asset or the time-of-day controller's runtime profile. Dispose destroys the object, the profile and its components.
    public sealed class TransientVolume : System.IDisposable
    {
        GameObject host;
        Volume volume;
        VolumeProfile profile;
        public DepthOfField DepthOfField { get; private set; }
        public ColorAdjustments ColorAdjustments { get; private set; }
        public bool Alive => volume;
        public Volume Volume => volume;

        public TransientVolume(string name, float priority, int layer, bool exposure)
        {
            host = new GameObject(name) { hideFlags = HideFlags.DontSave, layer = Mathf.Clamp(layer, 0, 31) };
            profile = ScriptableObject.CreateInstance<VolumeProfile>();
            profile.name = name + " (runtime)"; profile.hideFlags = HideFlags.DontSave;
            DepthOfField = profile.Add<DepthOfField>(true);
            DepthOfField.active = false;
            if (exposure)
            {
                // Only post exposure is ever overridden; the grade's contrast, filter and saturation pass through.
                ColorAdjustments = profile.Add<ColorAdjustments>(false);
                ColorAdjustments.postExposure.overrideState = false;
            }
            volume = host.AddComponent<Volume>();
            volume.isGlobal = true; volume.priority = priority; volume.weight = 1;
            volume.sharedProfile = profile;
        }

        /// Shallow-focus settings; aperture f/32 is close enough to "no blur" that blending in through it never pops.
        public void SetDepthOfField(bool on, DepthOfFieldMode mode, float focusDistance, float aperture, float focalLength, int blades = 6)
        {
            if (DepthOfField == null) return;
            DepthOfField.active = on;
            if (!on) return;
            DepthOfField.mode.Override(mode);
            DepthOfField.focusDistance.Override(Mathf.Max(.1f, focusDistance));
            DepthOfField.aperture.Override(Mathf.Clamp(aperture, 1, 32));
            DepthOfField.focalLength.Override(Mathf.Clamp(focalLength, 1, 300));
            DepthOfField.bladeCount.Override(Mathf.Clamp(blades, 3, 9));
            // Gaussian is far-field only: start a little behind the subject, fully soft 12 m further back.
            DepthOfField.gaussianStart.Override(Mathf.Max(0, focusDistance + 1.5f));
            DepthOfField.gaussianEnd.Override(Mathf.Max(0, focusDistance + 12));
        }

        /// Exposure compensation on top of the scene's current post exposure (EV). Zero leaves the grade alone.
        public void SetExposure(float sceneExposure, float compensation)
        {
            if (ColorAdjustments == null) return;
            bool on = Mathf.Abs(compensation) > 1e-4f;
            ColorAdjustments.active = on;
            ColorAdjustments.postExposure.overrideState = on;
            ColorAdjustments.postExposure.value = sceneExposure + compensation;
        }

        public void Dispose()
        {
            if (profile)
            {
                foreach (var component in profile.components) if (component) Kill(component);
                Kill(profile);
            }
            if (host) Kill(host);
            host = null; volume = null; profile = null; DepthOfField = null; ColorAdjustments = null;
        }

        static void Kill(Object o) { if (Application.isPlaying) Object.Destroy(o); else Object.DestroyImmediate(o); }

        /// A layer the camera's volume mask includes, preferring the layer the scene's own volumes already use.
        public static int LayerFor(Camera camera)
        {
            int mask = camera && camera.TryGetComponent<UniversalAdditionalCameraData>(out var data) ? data.volumeLayerMask.value : ~0;
            foreach (var v in Object.FindObjectsByType<Volume>(FindObjectsSortMode.None))
                if (v && (mask & (1 << v.gameObject.layer)) != 0) return v.gameObject.layer;
            for (int i = 0; i < 32; i++) if ((mask & (1 << i)) != 0) return i;
            return 0;
        }

        /// The post exposure the scene's own volumes resolve to (the highest-priority one that overrides it), so exposure
        /// compensation is added to the time-of-day value instead of replacing it.
        public static float SceneExposure(Volume exclude)
        {
            float best = float.NegativeInfinity, value = 0;
            foreach (var v in Object.FindObjectsByType<Volume>(FindObjectsSortMode.None))
            {
                if (!v || v == exclude || !v.isActiveAndEnabled || !v.isGlobal || v.priority < best) continue;
                var p = v.HasInstantiatedProfile() ? v.profile : v.sharedProfile;
                if (p && p.TryGet<ColorAdjustments>(out var c) && c.active && c.postExposure.overrideState) { best = v.priority; value = c.postExposure.value; }
            }
            return value;
        }
    }
}
