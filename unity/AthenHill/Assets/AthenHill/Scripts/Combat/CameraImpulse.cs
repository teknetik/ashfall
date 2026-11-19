using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    /// Combat camera shake (19 Nov 2026). Sits beside FollowCamera on the main camera and never edits it: the offset is
    /// applied only while this camera renders (beginCameraRendering) and removed straight after (endCameraRendering).
    /// FollowCamera's own pose, the shot raycasts in PlayerCombat and the HUD's world-to-screen projection therefore
    /// all see the steady camera; only the picture moves.
    /// Sources: the player's shots (scaled by the weapon's recoil relative to its base), damage taken (by the share of
    /// vitality lost) and droid wrecks nearby (CombatFx calls AddAt). Scaled by Settings › Controls › Camera shake and
    /// off under Reduced Motion.
    [DisallowMultipleComponent]
    public class CameraImpulse : MonoBehaviour
    {
        public GameSession session;
        public PlayerCombat player;
        [Tooltip("Camera that shakes. Empty = the Camera on this object.")]
        public Camera view;
        [Header("Shape")]
        [Tooltip("Rotation at full shake (degrees): pitch, yaw, roll.")]
        public Vector3 maxAngles = new Vector3(2.2f, 1.6f, 2.4f);
        [Tooltip("Position offset at full shake (metres, camera space). Kept tiny so the lens never pokes through a wall it was swept against.")]
        public Vector3 maxOffset = new Vector3(.03f, .03f, 0);
        [Min(.1f)] public float frequency = 17;
        [Min(.01f)] public float decayPerSecond = 1.8f;
        [Header("Sources")]
        [Tooltip("Trauma per shot for semi-automatic and automatic weapons, scaled by the fitted recoil relative to the base weapon.")]
        [Range(0, 1)] public float shotTrauma = .2f, automaticShotTrauma = .11f;
        [Tooltip("Damage taken: a floor for any hit plus this much per whole vitality bar lost.")]
        [Range(0, 1)] public float hurtFloor = .22f;
        [Range(0, 3)] public float hurtPerVitality = 1.1f;
        [Tooltip("Default radius for AddAt events (droid wrecks).")]
        [Min(1)] public float eventRadius = 16;

        public int Impulses { get; private set; }
        public float Trauma => state.Trauma;
        /// Rotation applied in the last rendered frame (degrees, largest axis), for QA.
        public float LastAngle { get; private set; }
        public float PeakAngle { get; private set; }
        // A conversation framing or a photo-mode shot owns the camera: never shake it (CinematicCamera, showcase camera).
        public bool Suppressed => ReducedMotion || SettingScale <= 0 || CinematicCamera.UnderControl;

        readonly ImpulseState state = new ImpulseState();
        GameSettings settings;
        bool applied;
        Vector3 savedPosition;
        Quaternion savedRotation;
        float seed;

        bool ReducedMotion => session && session.reducedMotion;
        float SettingScale => settings ? settings.Controls.CameraShake : 1;

        void Awake()
        {
            if (!view) view = GetComponent<Camera>();
            seed = Random.value * 100;
        }

        void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering += Begin;
            RenderPipelineManager.endCameraRendering += End;
            if (player) { player.ShotFired += OnShot; player.Hurt += OnHurt; }
        }

        void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= Begin;
            RenderPipelineManager.endCameraRendering -= End;
            if (player) { player.ShotFired -= OnShot; player.Hurt -= OnHurt; }
            Restore();
        }

        void Start()
        {
            if (!session) session = FindAnyObjectByType<GameSession>();
            settings = session && session.Settings ? session.Settings : FindAnyObjectByType<GameSettings>();
            if (!player)
            {
                player = FindAnyObjectByType<PlayerCombat>();
                if (player && isActiveAndEnabled) { player.ShotFired += OnShot; player.Hurt += OnHurt; }
            }
        }

        public void Add(float trauma)
        {
            if (trauma <= 0 || Suppressed) return;
            state.Add(trauma);
            Impulses++;
        }

        /// An event at a world position: full trauma at the player, none at the radius (radius 0 = Event Radius).
        public void AddAt(Vector3 position, float trauma, float radius = 0)
        {
            if (!player) return;
            float r = radius > 0 ? radius : eventRadius;
            Add(trauma * ImpulseState.Falloff(Vector3.Distance(player.transform.position, position), r));
        }

        void OnShot()
        {
            if (!player) return;
            float t = player.Automatic ? automaticShotTrauma : shotTrauma;
            Add(t * Mathf.Clamp(player.RecoilScale, .25f, 2f));
        }

        void OnHurt(float amount)
        {
            if (!player || !player.Health) return;
            Add(ImpulseState.ForDamage(amount, player.Health.max, hurtFloor, hurtPerVitality));
        }

        void Update()
        {
            state.decayPerSecond = decayPerSecond;
            state.Step(Time.unscaledDeltaTime);
            if (Suppressed) state.Clear();
        }

        void Begin(ScriptableRenderContext context, Camera camera)
        {
            if (camera != view) return;
            // A frame whose end callback never came (an exception mid-render) must not restore a stale pose later:
            // FollowCamera has written a fresh one since, so start from it.
            applied = false;
            // only in play: photo mode, dialogue framing and menus own a still camera
            if (session && session.State != CityState.Play) { LastAngle = 0; return; }
            float amplitude = ImpulseState.Amplitude(state.Shake, SettingScale, ReducedMotion);
            if (amplitude <= 1e-4f) { LastAngle = 0; return; }
            float t = Time.unscaledTime * frequency;
            Vector3 n = new Vector3(Noise(t, 0), Noise(t, 1), Noise(t, 2));
            Vector3 angles = Vector3.Scale(maxAngles, n) * amplitude;
            Vector3 shift = Vector3.Scale(maxOffset, new Vector3(Noise(t, 3), Noise(t, 4), Noise(t, 5))) * amplitude;
            var tr = view.transform;
            savedPosition = tr.position; savedRotation = tr.rotation; applied = true;
            var rotation = savedRotation * Quaternion.Euler(angles);
            tr.SetPositionAndRotation(savedPosition + savedRotation * shift, rotation);
            LastAngle = Mathf.Max(Mathf.Abs(angles.x), Mathf.Abs(angles.y), Mathf.Abs(angles.z));
            PeakAngle = Mathf.Max(PeakAngle, LastAngle);
        }

        void End(ScriptableRenderContext context, Camera camera)
        {
            if (camera == view) Restore();
        }

        void Restore()
        {
            if (!applied || !view) { applied = false; return; }
            view.transform.SetPositionAndRotation(savedPosition, savedRotation);
            applied = false;
        }

        float Noise(float t, int axis) => Mathf.PerlinNoise(seed + axis * 13.7f, t) * 2 - 1;
    }
}
