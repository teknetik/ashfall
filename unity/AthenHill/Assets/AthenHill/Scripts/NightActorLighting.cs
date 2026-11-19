using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill
{
    /// Night readability (19 Nov 2026, art/night_readability_20261119). Two night-only levers that cost no lights:
    /// 1. The moon key's shadow strength eases from its authored value (day) to nightKeyShadowStrength as the sun goes
    ///    down, so moon-shadowed streets keep some moonlight instead of falling to the ambient floor.
    /// 2. Actors (the player, the talking NPCs, walkers and the yard mechanic) get their own ambient probe at night: the
    ///    sky's ambient probe scaled up, plus a soft directional term from the viewer's side (a camera-side fill, as a
    ///    film character light would be). It is spherical-harmonic ambient on each renderer (CustomProvided probe), so it
    ///    adds no real-time light, no shadow map and nothing to the 32-light cap.
    /// Both are weighted by (1 - the clock's sun visibility): every frame with the sun up (06:30 to 17:30) is unchanged.
    /// Renderers another system already gives a custom probe (walk-in interiors) are left alone, and the player is
    /// skipped while InteriorLighting has them inside a room.
    [DefaultExecutionOrder(60)]
    [DisallowMultipleComponent]
    public sealed class NightActorLighting : MonoBehaviour
    {
        public CityTimeOfDay clock;
        [Header("Moon key")]
        [Tooltip("Key-light shadow strength with the sun fully down; the authored strength applies by day.")]
        [Range(0, 1)] public float nightKeyShadowStrength = 1;
        [Header("Actors at night")]
        [Tooltip("Extra multiple of the sky ambient probe on actors at full night (0 = the same ambient as the street).")]
        [Min(0)] public float actorAmbientGain = 0;
        [Tooltip("Colour of the camera-side fill on actors (linear intensity below).")]
        public Color viewerFillColor = new Color(.62f, .72f, 1f);
        [Min(0)] public float viewerFillIntensity = 0;
        [Tooltip("Degrees above the actor-to-camera line the fill comes from.")]
        [Range(-30, 75)] public float viewerFillElevation = 25;
        [Tooltip("Actors further than this from the camera keep the plain sky ambient.")]
        [Min(1)] public float maxDistance = 60;
        [Min(.25f)] public float rescanSeconds = 3;

        public float NightWeight { get; private set; }
        public int ActorsLit { get; private set; }

        sealed class Actor
        {
            public Transform root; public bool player;
            public readonly List<Renderer> renderers = new List<Renderer>();
            public readonly List<LightProbeUsage> usage = new List<LightProbeUsage>();
            public bool applied;
        }
        readonly List<Actor> actors = new List<Actor>();
        readonly HashSet<Renderer> known = new HashSet<Renderer>();
        readonly SphericalHarmonicsL2[] one = new SphericalHarmonicsL2[1];
        MaterialPropertyBlock block;
        InteriorLighting[] interiors = new InteriorLighting[0];
        float nextScan, authoredShadow = 1;
        Light key;

        void OnEnable()
        {
            if (!clock) clock = GetComponent<CityTimeOfDay>();
            block = new MaterialPropertyBlock();
            nextScan = 0;
        }

        void Scan()
        {
            nextScan = Time.unscaledTime + rescanSeconds;
            interiors = FindObjectsByType<InteriorLighting>(FindObjectsSortMode.None);
            actors.RemoveAll(a => !a.root);
            var roots = new List<(Transform root, bool player)>();
            foreach (var p in FindObjectsByType<PlayerMotor>(FindObjectsSortMode.None)) roots.Add((p.transform, true));
            foreach (var v in FindObjectsByType<FirstPersonViewModel>(FindObjectsInactive.Include, FindObjectsSortMode.None)) roots.Add((v.transform, true));
            foreach (var n in FindObjectsByType<NpcAgent>(FindObjectsSortMode.None)) roots.Add((n.transform, false));
            foreach (var w in FindObjectsByType<AmbientWalker>(FindObjectsSortMode.None)) roots.Add((w.transform, false));
            foreach (var a in FindObjectsByType<ActorAnimation>(FindObjectsSortMode.None)) roots.Add((a.transform, false));
            foreach (var (root, player) in roots)
            {
                var actor = actors.Find(x => x.root == root);
                if (actor == null) { actor = new Actor { root = root, player = player }; actors.Add(actor); }
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (known.Contains(r) || r is ParticleSystemRenderer || r is LineRenderer || r is TrailRenderer) continue;
                    known.Add(r);
                    // Interior props already carry an interior probe: leave them to InteriorLighting.
                    if (r.lightProbeUsage == LightProbeUsage.CustomProvided) continue;
                    actor.renderers.Add(r); actor.usage.Add(r.lightProbeUsage);
                }
            }
        }

        static SphericalHarmonicsL2 SkyProbe()
        {
            var sh = RenderSettings.ambientProbe;
            if (sh[0, 0] + sh[1, 0] + sh[2, 0] < 1e-5f)
            {
                sh = new SphericalHarmonicsL2();
                sh.AddAmbientLight(RenderSettings.ambientEquatorColor.linear * RenderSettings.ambientIntensity);
                sh.AddDirectionalLight(Vector3.up, (RenderSettings.ambientSkyColor.linear - RenderSettings.ambientEquatorColor.linear) * .5f, RenderSettings.ambientIntensity);
            }
            return sh;
        }

        bool PlayerInsideRoom()
        {
            foreach (var room in interiors) if (room && room.isActiveAndEnabled && room.PlayerInside > .001f) return true;
            return false;
        }

        void LateUpdate()
        {
            if (!clock || !clock.isActiveAndEnabled) return;
            if (Time.unscaledTime >= nextScan) Scan();
            float night = Mathf.Clamp01(1 - clock.SunVisibility);
            NightWeight = night;
            if (clock.keyLight)
            {
                if (key != clock.keyLight) { key = clock.keyLight; authoredShadow = key.shadowStrength; }
                key.shadowStrength = Mathf.Lerp(authoredShadow, nightKeyShadowStrength, night);
            }
            bool active = night > .001f && (actorAmbientGain > 0 || viewerFillIntensity > 0);
            var cam = Camera.main;
            bool playerInside = PlayerInsideRoom();
            var sky = SkyProbe();
            int lit = 0;
            foreach (var actor in actors)
            {
                if (!actor.root) continue;
                bool want = active && actor.root.gameObject.activeInHierarchy && !(actor.player && playerInside);
                if (want && cam && !actor.player && (actor.root.position - cam.transform.position).sqrMagnitude > maxDistance * maxDistance) want = false;
                if (!want) { if (actor.applied) Restore(actor, !(actor.player && playerInside)); continue; }
                var sh = sky * (1 + actorAmbientGain * night);
                if (viewerFillIntensity > 0 && cam)
                {
                    var flat = cam.transform.position - actor.root.position; flat.y = 0;
                    if (flat.sqrMagnitude < 1e-4f) flat = -cam.transform.forward;
                    flat.Normalize();
                    var dir = Quaternion.AngleAxis(-viewerFillElevation, Vector3.Cross(Vector3.up, flat).normalized) * flat;
                    sh.AddDirectionalLight(dir.normalized, viewerFillColor.linear, viewerFillIntensity * night);
                }
                one[0] = sh;
                foreach (var r in actor.renderers)
                {
                    if (!r) continue;
                    r.lightProbeUsage = LightProbeUsage.CustomProvided;
                    r.GetPropertyBlock(block); block.CopySHCoefficientArraysFrom(one); r.SetPropertyBlock(block);
                }
                actor.applied = true; lit++;
            }
            ActorsLit = lit;
        }

        void Restore(Actor actor, bool clearBlock)
        {
            for (int i = 0; i < actor.renderers.Count; i++)
            {
                var r = actor.renderers[i]; if (!r) continue;
                // While the player is inside a room InteriorLighting owns their probe: do not clear what it set.
                if (!clearBlock) continue;
                r.lightProbeUsage = actor.usage[i];
                r.GetPropertyBlock(block); block.Clear(); r.SetPropertyBlock(block);
            }
            actor.applied = false;
        }

        void OnDisable()
        {
            foreach (var actor in actors) if (actor.applied) Restore(actor, true);
            if (key) key.shadowStrength = authoredShadow;
            key = null; actors.Clear(); known.Clear();
        }
    }
}
