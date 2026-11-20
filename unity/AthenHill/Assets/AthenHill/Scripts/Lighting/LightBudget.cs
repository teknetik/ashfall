using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    /// Light budget (20 Nov 2026, art/light_budget_20261120/README.md). URP on the Linux OpenGL Core player draws at most 32
    /// lights per camera (sun, sky fill and 30 local lights); at night 26-183 were in view, so URP dropped lamps and their
    /// pools popped in and out. This keeps the lights enabled in the rendering camera's view under `hardCap` by design:
    /// the most important lamps stay real, the rest keep their emissive bulbs (the light clock's materials, untouched here)
    /// and get a cheap screen-space pool (a box drawn with LampPool.shader, which lights the depth buffer with the lamp's own
    /// colour, cone, cookie and falloff). Promotion and demotion cross-fade over `fadeSeconds` with hysteresis and a hold.
    ///
    /// Owners keep control: the light clock (CityLightCircuit) rewrites its lamps every LateUpdate and this runs after it
    /// (execution order 2000), so the hour, night-only, daytime strength, distance fade and shadow rules are untouched;
    /// static lamps are owned by nobody else. Lamps driven by other scripts (interiors, fires, combat FX, droid eyes, loot
    /// glows) are never touched here, only counted, and the budget for managed lamps shrinks by their number.
    /// Switch: ATHEN_LIGHT_BUDGET=0 (development players) starts with the budget off; LightBudget.Active.enabled at runtime.
    [DefaultExecutionOrder(2000)]
    [DisallowMultipleComponent]
    public sealed class LightBudget : MonoBehaviour
    {
        public enum LampOwner { Circuit = 0, Static = 1, Marker = 2 }

        [Serializable]
        public sealed class Lamp
        {
            public Light light;
            public LampOwner owner;
            [Tooltip("Marker lamps: the salvage node whose Ready state says whether the marker is lit (it switches the light on change only).")]
            public SalvageNode marker;
            [Tooltip("Importance multiplier in the ranking (1 = normal).")]
            [Min(0)] public float priority = 1;
            [Tooltip("Draw a pool while the lamp is demoted. Off for lights restricted to other rendering layers.")]
            public bool pool = true;
            [Tooltip("Per-lamp pool brightness multiplier on top of poolGain.")]
            [Min(0)] public float poolScale = 1;
        }

        public static LightBudget Active { get; private set; }

        public CityLightCircuit circuit;
        public Lamp[] lamps = Array.Empty<Lamp>();
        public Material poolMaterial;
        [Header("Budget")]
        [Tooltip("Local lights allowed in the camera's view (managed + every other enabled light). URP keeps 32 minus the two directional lights; two more slots are left for combat FX.")]
        [Range(4, 30)] public int hardCap = 28;
        [Range(0, 6)] public int fadeMargin = 2;
        [Range(1, 3)] public float hysteresis = 1.35f;
        [Min(0)] public float minHoldSeconds = 1f;
        [Min(.05f)] public float fadeSeconds = .6f;
        [Range(0, 60)] public int offscreenKeep = 12;
        [Min(1)] public float pinBoost = 4f;
        [Tooltip("Ranking frustum is the camera's widened by this factor on its field of view, so lamps just off screen are decided before they enter it.")]
        [Range(1, 1.8f)] public float wideFovScale = 1.3f;
        [Tooltip("Lamps further than this from the camera are never real (the clock fades lamps out between 90 and 150 m anyway).")]
        [Min(10)] public float maxRealDistance = 150;
        [Tooltip("Near preference in the ranking (metres): scores are multiplied by 1 / (1 + (d / nearMetres)^2). 0 = off.")]
        [Min(0)] public float nearMetres = 15;
        [Header("Pools")]
        [Tooltip("Overall pool brightness relative to the real light (1 = the same Lambert term with poolAlbedo).")]
        [Min(0)] public float poolGain = 1f;
        [Tooltip("Assumed surface albedo (linear) the pool lights: Ward sandstone and paving.")]
        public Color poolAlbedo = new Color(.42f, .36f, .30f);
        [Tooltip("Extra pool multiplier for spots with a cookie (the shop wall lamps): measured against the real light on 20 Nov their pools came out about 3x brighter than the plain lamps' did.")]
        [Min(0)] public float cookiePoolScale = .35f;
        [Tooltip("Extra pool multiplier for lamps that cast shadows (the pool has none, so it lights more than the real light does).")]
        [Min(0)] public float shadowedPoolScale = .6f;
        [Tooltip("Pools are drawn only while the clock's lamp strength is at least this (they are invisible in daylight).")]
        [Range(0, 1)] public float poolMinStrength = .15f;
        [Tooltip("Pools stop at this fraction of the lamp's range (the last part of URP's falloff is nearly black); the pool box shrinks with it. 1 = full range.")]
        [Range(.5f, 1)] public float poolRangeScale = .85f;
        [Tooltip("At most this many pools are drawn per frame, the brightest and largest on screen first (a lamp mid cross-fade always keeps its pool). 0 = no cap.")]
        [Min(0)] public int maxPools = 44;
        [Tooltip("Pools whose box would be smaller than this many pixels in radius on screen are not drawn.")]
        [Min(0)] public float minPoolPixels = 6;
        [Tooltip("Pools further than this are not drawn (sub-pixel and fogged).")]
        [Min(10)] public float poolMaxDistance = 120;

        public LightBudgetStats Stats { get; private set; }
        public int UnmanagedInView { get; private set; }
        public int LightsInView { get; private set; }
        public int ManagedLamps => count;
        public Camera RenderingCamera { get; private set; }
        public bool PoolsActive { get; private set; }
        public int PoolsDrawn { get; private set; }

        struct Owned { public bool enabled; public float intensity; public bool wroteEnabled; public float wroteIntensity; }
        LampBudgetState[] states; Owned[] owned; Vector3[] centres; float[] luminance;
        int count; int[] order; float[] keys; float[] poolKeys; bool[] poolCand, poolShow;
        Lamp[] live;
        readonly List<Light> others = new List<Light>();
        readonly HashSet<Light> managedSet = new HashSet<Light>();
        float nextRescan;
        Renderer[] poolRenderers; MaterialPropertyBlock block; Material[] poolMaterials;
        Mesh cube; Transform poolRoot;
        readonly Plane[] planes = new Plane[6], widePlanes = new Plane[6];
        bool started;
        static readonly int LightPosId = Shader.PropertyToID("_LightPos"), LightColorId = Shader.PropertyToID("_LightColor"),
            SpotDirId = Shader.PropertyToID("_SpotDir"), SpotId = Shader.PropertyToID("_SpotParams"), CookieId = Shader.PropertyToID("_CookieTex"),
            CookieParamsId = Shader.PropertyToID("_CookieParams"), CookieRightId = Shader.PropertyToID("_CookieRight"), CookieUpId = Shader.PropertyToID("_CookieUp"),
            AlbedoId = Shader.PropertyToID("_Albedo"), PoolCutId = Shader.PropertyToID("_PoolCut");

        void Awake()
        {
#if UNITY_EDITOR || DEBUG
            var env = Environment.GetEnvironmentVariable("ATHEN_LIGHT_BUDGET");
            if (env == "0" || env == "off") { Debug.Log("LightBudget: ATHEN_LIGHT_BUDGET=" + env + ", starting off"); enabled = false; }
#endif
        }

        void OnEnable()
        {
            if (!Application.isPlaying) return;
            Active = this;
            if (started) Begin();
        }

        void Start() { started = true; if (isActiveAndEnabled) Begin(); }

        void Begin()
        {
            var list = new List<Lamp>(); managedSet.Clear();
            foreach (var l in lamps) if (l != null && l.light && l.light.type != LightType.Directional && managedSet.Add(l.light)) list.Add(l);
            live = list.ToArray(); count = live.Length;
            states = new LampBudgetState[count]; owned = new Owned[count]; centres = new Vector3[count]; luminance = new float[count];
            order = new int[count]; keys = new float[count]; poolKeys = new float[count]; poolCand = new bool[count]; poolShow = new bool[count];
            for (int i = 0; i < count; i++)
            {
                var l = live[i].light;
                owned[i] = new Owned { enabled = l.enabled, intensity = l.intensity, wroteEnabled = l.enabled, wroteIntensity = l.intensity };
                // everything starts real and is ranked down in the first frames (instant demotions out of view)
                states[i] = new LampBudgetState { real = true, fade = 1, sinceChange = 10 };
                centres[i] = PoolCentre(l);
                var c = LinearColour(l); luminance[i] = .2126f * c.r + .7152f * c.g + .0722f * c.b;
            }
            BuildPools();
            Rescan();
        }

        void OnDisable()
        {
            if (Active == this) Active = null;
            if (live != null)
                for (int i = 0; i < count; i++)
                {
                    var l = live[i].light; if (!l) continue;
                    // hand the light back exactly as its owner last set it
                    l.enabled = owned[i].enabled; l.intensity = owned[i].intensity;
                }
            if (poolRenderers != null) foreach (var r in poolRenderers) if (r) r.enabled = false;
            Stats = default; PoolsActive = false;
        }

        void OnDestroy()
        {
            if (poolMaterials != null) foreach (var m in poolMaterials) if (m) Destroy(m);
            if (poolRoot) Destroy(poolRoot.gameObject);
            if (cube) Destroy(cube);
        }

        bool OwnerEnabled(int i) { var l = live[i].light; return l.enabled != owned[i].wroteEnabled ? l.enabled : owned[i].enabled; }
        float OwnerIntensity(int i) { var l = live[i].light; return !Mathf.Approximately(l.intensity, owned[i].wroteIntensity) ? l.intensity : owned[i].intensity; }

        static Color LinearColour(Light l)
        {
            var c = l.color.linear;
            if (GraphicsSettings.lightsUseColorTemperature && l.useColorTemperature) c *= Mathf.CorrelatedColorTemperatureToRGB(l.colorTemperature);
            return c;
        }

        /// Where the lamp's light lands: a ray along a spot's axis (or down from a point light) to the first surface.
        static Vector3 PoolCentre(Light l)
        {
            var t = l.transform; var dir = l.type == LightType.Spot ? t.forward : Vector3.down;
            if (Physics.Raycast(t.position, dir, out var hit, Mathf.Max(.5f, l.range), ~0, QueryTriggerInteraction.Ignore)) return hit.point;
            return t.position + dir * l.range * .5f;
        }

        static Mesh UnitCube()
        {
            var m = new Mesh { name = "Light budget pool box", hideFlags = HideFlags.DontSave };
            var v = new Vector3[8];
            for (int i = 0; i < 8; i++) v[i] = new Vector3((i & 1) == 0 ? -.5f : .5f, (i & 2) == 0 ? -.5f : .5f, (i & 4) == 0 ? -.5f : .5f);
            m.vertices = v;
            m.triangles = new[] { 0,2,1, 1,2,3, 4,5,6, 5,7,6, 0,1,4, 1,5,4, 2,6,3, 3,6,7, 0,4,2, 2,4,6, 1,3,5, 3,7,5 };
            m.RecalculateBounds();
            return m;
        }

        void BuildPools()
        {
            if (poolRoot) Destroy(poolRoot.gameObject);
            if (poolMaterials != null) foreach (var m in poolMaterials) if (m) Destroy(m);
            poolRenderers = new Renderer[count]; poolMaterials = new Material[count];
            if (!poolMaterial) return;
            if (!cube) cube = UnitCube();
            poolRoot = new GameObject("Light budget pools (runtime)") { hideFlags = HideFlags.DontSave }.transform;
            poolRoot.SetParent(transform, false);
            for (int i = 0; i < count; i++)
            {
                var lamp = live[i]; var l = lamp.light;
                if (!lamp.pool || ((uint)l.renderingLayerMask & 1u) == 0) continue;
                var go = new GameObject("pool " + l.name) { hideFlags = HideFlags.DontSave };
                go.transform.SetParent(poolRoot, false);
                // Fit the box to what the lamp can light: a spot narrower than 180 degrees lights only a cone in front of it.
                float reach = l.range * poolRangeScale; float half = l.type == LightType.Spot ? l.spotAngle * .5f : 180;
                if (half < 89)
                {
                    float side = 2 * reach * Mathf.Sin(Mathf.Deg2Rad * half);
                    go.transform.SetPositionAndRotation(l.transform.position + l.transform.forward * reach * .5f, l.transform.rotation);
                    go.transform.localScale = new Vector3(side, side, reach);
                }
                else { go.transform.SetPositionAndRotation(l.transform.position, Quaternion.identity); go.transform.localScale = Vector3.one * (2 * reach); }
                go.AddComponent<MeshFilter>().sharedMesh = cube;
                var r = go.AddComponent<MeshRenderer>();
                r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false; r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off; r.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                r.allowOcclusionWhenDynamic = false;
                var mat = new Material(poolMaterial) { name = "pool " + l.name, hideFlags = HideFlags.DontSave };
                SetupPoolMaterial(mat, l);
                r.sharedMaterial = mat; r.enabled = false;
                poolRenderers[i] = r; poolMaterials[i] = mat;
            }
        }

        void SetupPoolMaterial(Material mat, Light l)
        {
            var t = l.transform; float range = Mathf.Max(.1f, l.range);
            mat.SetVector(LightPosId, new Vector4(t.position.x, t.position.y, t.position.z, 1f / (range * range)));
            mat.SetVector(AlbedoId, (Vector4)poolAlbedo);   // vectors: SetColor would gamma-convert a linear value a second time
            mat.SetFloat(PoolCutId, poolRangeScale);
            if (l.type == LightType.Spot)
            {
                float cosOuter = Mathf.Cos(Mathf.Deg2Rad * l.spotAngle * .5f), cosInner = Mathf.Cos(Mathf.Deg2Rad * Mathf.Max(0, l.innerSpotAngle) * .5f);
                float a = 1f / Mathf.Max(.001f, cosInner - cosOuter), b = -cosOuter * a;
                mat.SetVector(SpotDirId, t.forward);
                mat.SetVector(SpotId, new Vector4(a, b, 1, 0));
                if (l.cookie is Texture2D cookie)
                {
                    bool single = cookie.format == TextureFormat.Alpha8 || cookie.format == TextureFormat.R8 || cookie.format == TextureFormat.BC4 || cookie.format == TextureFormat.R16;
                    float tanHalf = Mathf.Tan(Mathf.Deg2Rad * Mathf.Min(170, l.spotAngle) * .5f);
                    mat.SetTexture(CookieId, cookie);
                    mat.SetVector(CookieParamsId, new Vector4(1, tanHalf, single ? (cookie.format == TextureFormat.Alpha8 ? 2 : 1) : 0, 0));
                    mat.SetVector(CookieRightId, t.right); mat.SetVector(CookieUpId, t.up);
                }
                else mat.SetVector(CookieParamsId, Vector4.zero);
            }
            else { mat.SetVector(SpotId, new Vector4(0, 1, 0, 0)); mat.SetVector(CookieParamsId, Vector4.zero); }
        }

        /// Every other enabled local light in the scene is counted against the budget (rescanned, so spawned FX count).
        void Rescan()
        {
            others.Clear();
            foreach (var l in FindObjectsByType<Light>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                if (l.type != LightType.Directional && !managedSet.Contains(l)) others.Add(l);
            nextRescan = Time.unscaledTime + 2f;
        }

        public static Camera FindRenderingCamera()
        {
            var main = Camera.main;
            if (main && main.isActiveAndEnabled && !main.targetTexture) return main;
            Camera best = null;
            foreach (var c in Camera.allCameras) if (!c.targetTexture && (!best || c.depth > best.depth)) best = c;
            return best;
        }

        static bool InFrustum(Plane[] p, Light l) => GeometryUtility.TestPlanesAABB(p, new Bounds(l.transform.position, Vector3.one * (2 * l.range)));

        public LightBudgetSettings Settings => new LightBudgetSettings
        { hardCap = hardCap, fadeMargin = fadeMargin, hysteresis = hysteresis, minHoldSeconds = minHoldSeconds, fadeSeconds = fadeSeconds, offscreenKeep = offscreenKeep, pinBoost = pinBoost };

        void LateUpdate()
        {
            if (states == null) return;
            var cam = FindRenderingCamera(); RenderingCamera = cam;
            if (!cam) return;
            if (Time.unscaledTime >= nextRescan) Rescan();
            GeometryUtility.CalculateFrustumPlanes(cam, planes);
            float wideFov = Mathf.Min(170, cam.fieldOfView * wideFovScale);
            var wideProj = Matrix4x4.Perspective(wideFov, cam.aspect * wideFovScale, cam.nearClipPlane, cam.farClipPlane);
            GeometryUtility.CalculateFrustumPlanes(wideProj * cam.worldToCameraMatrix, widePlanes);
            var eye = cam.transform.position;
            var viewer = circuit && circuit.viewer ? circuit.viewer.position : eye;

            // The clock rewrites its lamps every LateUpdate before this runs; if it is off, track them like static lamps.
            bool circuitLive = circuit && circuit.isActiveAndEnabled;
            int unmanaged = 0;
            foreach (var l in others) if (l && l.isActiveAndEnabled && l.intensity > 0 && InFrustum(planes, l)) unmanaged++;
            UnmanagedInView = unmanaged;

            for (int i = 0; i < count; i++)
            {
                var lamp = live[i]; var l = lamp.light;
                if (!l) { states[i].wanted = false; continue; }
                bool on; float intensity;
                if (lamp.owner == LampOwner.Circuit && circuitLive) { on = l.enabled; intensity = l.intensity; }   // the clock rewrote both this frame
                else if (lamp.owner == LampOwner.Marker && lamp.marker && lamp.marker.Search != null)
                { on = lamp.marker.isActiveAndEnabled && lamp.marker.Search.State == SalvageNodeState.Ready; intensity = OwnerIntensity(i); }
                else { on = OwnerEnabled(i); intensity = OwnerIntensity(i); }
                owned[i].enabled = on; owned[i].intensity = intensity;
                bool active = on && l.gameObject.activeInHierarchy && intensity > .002f;
                float d = Vector3.Distance(eye, centres[i]);
                ref var s = ref states[i];
                s.wanted = active && d < maxRealDistance + l.range;
                s.inView = s.wanted && InFrustum(planes, l);
                s.inWide = s.inView || (s.wanted && InFrustum(widePlanes, l));
                s.score = LightBudgetMath.Score(intensity, l.range, luminance[i], lamp.priority, d, nearMetres);
                s.pinned = (viewer - l.transform.position).sqrMagnitude < l.range * l.range * .64f;
            }
            var stats = LightBudgetMath.Step(states, count, Settings, unmanaged, Time.unscaledDeltaTime, order, keys);
            Stats = stats; LightsInView = stats.enabledInView + unmanaged;

            float strength = circuit ? circuit.CurrentStrength : 1;
            PoolsActive = poolMaterial && strength >= poolMinStrength;
            float pixelsPerUnit = Screen.height * .5f / Mathf.Tan(Mathf.Deg2Rad * cam.fieldOfView * .5f);
            for (int i = 0; i < count; i++)
            {
                var lamp = live[i]; var l = lamp.light; if (!l) continue;
                ref var s = ref states[i];
                float w = LightBudgetMath.LightWeight(s.fade);
                bool lit = s.wanted && w > 0;
                float intensity = owned[i].intensity * (s.wanted ? Mathf.Max(w, 0) : 1);
                if (s.wanted) { if (l.enabled != lit) l.enabled = lit; if (lit) l.intensity = intensity; }
                else if (owned[i].enabled && l.enabled && Vector3.Distance(eye, centres[i]) >= maxRealDistance + l.range) l.enabled = false;   // beyond the budget's reach: off, not left burning uncounted
                owned[i].wroteEnabled = l.enabled; owned[i].wroteIntensity = l.intensity;
                // pool candidates: demoted (or fading) lamps in the widened view, near enough and big enough on screen
                poolCand[i] = false;
                if (!poolRenderers[i] || !PoolsActive || !s.wanted || !s.inWide) continue;
                float pw = LightBudgetMath.PoolWeight(s.fade);
                if (pw <= .001f) continue;
                float d = Vector3.Distance(eye, centres[i]); if (d >= poolMaxDistance) continue;
                float reach = l.range * poolRangeScale;
                bool fading = s.fade > 0;
                if (!fading && reach / Mathf.Max(.1f, d) * pixelsPerUnit < minPoolPixels) continue;
                poolCand[i] = true;
                poolKeys[i] = fading ? float.PositiveInfinity : LightBudgetMath.PoolKey(owned[i].intensity, reach, luminance[i], d);
            }
            PoolsDrawn = LightBudgetMath.SelectPools(poolKeys, poolCand, count, maxPools > 0 ? maxPools : int.MaxValue, poolShow, order, keys);
            for (int i = 0; i < count; i++)
            {
                var r = poolRenderers[i]; if (!r) continue;
                bool show = poolShow[i];
                if (r.enabled != show) r.enabled = show;
                if (!show) continue;
                var lamp = live[i]; var l = lamp.light;
                float pw = LightBudgetMath.PoolWeight(states[i].fade);
                float k = poolGain * lamp.poolScale * (l.cookie ? cookiePoolScale : 1) * (l.shadows != LightShadows.None ? shadowedPoolScale : 1);
                poolMaterials[i].SetVector(LightColorId, (Vector4)(LinearColour(l) * (owned[i].intensity * pw * k)));
            }
        }

        /// Development / QA: the current per-lamp state (name, real, fade, in view, score).
        public IEnumerable<(string name, bool real, float fade, bool inView, float score, bool wanted)> Lamps()
        {
            if (states == null) yield break;
            for (int i = 0; i < count; i++) if (live[i].light) yield return (live[i].light.name, states[i].real, states[i].fade, states[i].inView, states[i].score, states[i].wanted);
        }

        /// Re-reads tunable pool parameters (albedo) into the runtime materials after a tune.
        public void RefreshPools() { if (states != null) BuildPools(); }
    }
}
