using System;
using UnityEngine;

namespace AthenHill
{
    /// <summary>
    /// Pure, deterministic wasteland danger calculations for the Outer Berms (21 Nov 2026).
    /// Separated from MonoBehaviour state so Edit Mode tests can verify every threshold,
    /// zone boundary, cooldown, and Reduced-Motion cap without a scene.
    /// </summary>
    public static class BermsDangerMath
    {
        [Serializable]
        public struct DangerZone
        {
            public string id;
            public string displayName;
            public Vector3 center;
            [Min(5f)] public float radius;
            [Min(1)] public int tier;
            [TextArea(2, 4)] public string warningLine;
        }

        public static DangerZone[] DefaultTier3Zones() => new[]
        {
            new DangerZone
            {
                id = "reaper_den",
                displayName = "Reaper Den",
                center = new Vector3(-242f, 0.1f, 142f),
                radius = 58f,
                tier = 3,
                warningLine = "Warden telemetry · Entering Reaper Den — heavy scrap-reaper pack ahead. Stay in cover and watch your flanks."
            },
            new DangerZone
            {
                id = "post_relay",
                displayName = "Post Relay",
                center = new Vector3(-432f, 4.1f, 22f),
                radius = 58f,
                tier = 3,
                warningLine = "Warden telemetry · Post Relay perimeter — high-tier wheeled sentinels active in this sector."
            },
            new DangerZone
            {
                id = "fans_camp",
                displayName = "Fans Camp",
                center = new Vector3(-492f, 5.1f, -108f),
                radius = 62f,
                tier = 3,
                warningLine = "Warden telemetry · Fans Camp red zone — armoured holdouts detected. Extreme caution."
            },
            new DangerZone
            {
                id = "southern_cache",
                displayName = "Southern Cache",
                center = new Vector3(-252f, 0.4f, -152f),
                radius = 54f,
                tier = 3,
                warningLine = "Warden telemetry · Southern Cache dead zone — heavy reaper and sentinel signatures nearby."
            }
        };

        /// <summary>
        /// Normalized westward depth into the Outer Berms: 0 inside Ward (playerX >= cityEdgeX),
        /// rising smoothly to 1 at deepBermsX.
        /// </summary>
        public static float DepthFactor(float playerX, float cityEdgeX = -58.3f, float deepBermsX = -460f)
        {
            if (float.IsNaN(playerX) || playerX >= cityEdgeX) return 0f;
            float span = Mathf.Max(1f, cityEdgeX - deepBermsX);
            return Mathf.Clamp01((cityEdgeX - playerX) / span);
        }

        /// <summary>
        /// Normalized pressure (0..1) from nearby active feral droids. Closer droids, danger-tier
        /// droids, and larger packs push the score higher.
        /// </summary>
        public static float DroidProximityPressure(
            float nearestDroidDistance,
            bool hasDangerTier,
            int activeDroidsWithinRange,
            float maxRange = 65f)
        {
            if (activeDroidsWithinRange <= 0 || float.IsNaN(nearestDroidDistance) || float.IsInfinity(nearestDroidDistance))
                return 0f;
            float range = Mathf.Max(1f, maxRange);
            if (nearestDroidDistance >= range) return 0f;

            float proximity = 1f - Mathf.Clamp01(Mathf.Max(0f, nearestDroidDistance) / range);
            float basePressure = Mathf.Pow(proximity, 1.35f) * 0.65f;
            float packBonus = Mathf.Clamp01((activeDroidsWithinRange - 1) * 0.10f) * 0.20f;
            float dangerBonus = hasDangerTier ? 0.25f * Mathf.Lerp(0.45f, 1f, proximity) : 0f;
            return Mathf.Clamp01(basePressure + packBonus + dangerBonus);
        }

        /// <summary>
        /// Combined local wasteland threat intensity in [0, 1]. Returns 0 inside Ward's walls.
        /// </summary>
        public static float ThreatLevel(
            float playerX,
            float cityEdgeX,
            float deepBermsX,
            float nearestDroidDistance,
            bool hasDangerTier,
            int activeDroidsWithinRange,
            bool inTier3Zone = false,
            float maxDroidRange = 65f)
        {
            if (float.IsNaN(playerX) || playerX >= cityEdgeX) return 0f;
            float depth = DepthFactor(playerX, cityEdgeX, deepBermsX);
            float droids = DroidProximityPressure(nearestDroidDistance, hasDangerTier, activeDroidsWithinRange, maxDroidRange);
            float zoneBonus = inTier3Zone ? 0.20f : 0f;
            return Mathf.Clamp01(depth * 0.45f + droids * 0.55f + zoneBonus);
        }

        /// <summary>
        /// Ground ash/dust wisp emission rate (particles/sec). Always 0 outside the Berms;
        /// strictly capped under Reduced Motion.
        /// </summary>
        public static float AshEmissionRate(float threatLevel, bool inBerms, bool reducedMotion, float maxRate = 18f)
        {
            if (!inBerms || maxRate <= 0f) return 0f;
            float t = Mathf.Clamp01(threatLevel);
            if (t <= 0.04f) return 0f;
            float rate = Mathf.Lerp(1.5f, maxRate, t);
            return reducedMotion ? Mathf.Min(rate * 0.25f, 3f) : rate;
        }

        /// <summary>
        /// Seconds between distant ambient electrical crackles. Shortens as threat rises.
        /// </summary>
        public static float CrackleInterval(float threatLevel, float minInterval = 6f, float maxInterval = 22f)
        {
            float lo = Mathf.Max(0.5f, minInterval);
            float hi = Mathf.Max(lo, maxInterval);
            float t = Mathf.Clamp01(threatLevel);
            return Mathf.Lerp(hi, lo, t);
        }

        /// <summary>
        /// Index of the closest matching danger zone whose horizontal (X, Z) radius contains position, or -1.
        /// </summary>
        public static int FindDangerZoneIndex(Vector3 position, DangerZone[] zones)
        {
            if (zones == null || zones.Length == 0) return -1;
            int best = -1;
            float bestDistSq = float.PositiveInfinity;
            for (int i = 0; i < zones.Length; i++)
            {
                float r = Mathf.Max(0f, zones[i].radius);
                if (r <= 0f) continue;
                float dx = position.x - zones[i].center.x;
                float dz = position.z - zones[i].center.z;
                float d2 = dx * dx + dz * dz;
                if (d2 <= r * r && d2 < bestDistSq)
                {
                    bestDistSq = d2;
                    best = i;
                }
            }
            return best;
        }

        /// <summary>
        /// Returns true when entering a new danger zone whose cooldown has expired.
        /// </summary>
        public static bool ShouldWarnZoneEntry(
            int zoneIndex,
            int previousZoneIndex,
            float now,
            float lastWarnedAt,
            float cooldownSeconds = 90f)
        {
            if (zoneIndex < 0 || zoneIndex == previousZoneIndex) return false;
            return now - lastWarnedAt >= Mathf.Max(0f, cooldownSeconds);
        }
    }

    /// <summary>
    /// Runtime ambient wasteland danger controller for the Outer Berms (21 Nov 2026).
    /// Zero extra real-time lights; fully Reduced-Motion safe. Drives subtle ground ash wisps,
    /// periodic distant electrical crackles/sparks on tagged hazards, and brief Warden-telemetry
    /// radio warnings when entering high-level Tier-3 territories.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class BermsDangerAtmosphere : MonoBehaviour
    {
        public GameSession session;
        public PlayerCombat player;
        [Tooltip("Parent containing tagged Berms density hazard FX (ElectricArc / smoke markers).")]
        public Transform hazardRoot;
        [Tooltip("Subtle ground ash/dust wisp particle system that follows the player in the Berms (no lights).")]
        public ParticleSystem ashWisps;
        [Tooltip("Optional ambient audio source for distant electrical crackles deep in the Berms.")]
        public AudioSource crackleSource;
        public AudioClip[] crackleClips = new AudioClip[0];
        public BermsDangerMath.DangerZone[] dangerZones = BermsDangerMath.DefaultTier3Zones();

        [Header("Tuning")]
        public float cityEdgeX = -58.3f;
        public float deepBermsX = -460f;
        [Min(5f)] public float droidScanRange = 65f;
        [Min(0.05f)] public float scanInterval = 0.35f;
        [Min(0f)] public float zoneWarnCooldown = 90f;
        [Min(0f)] public float maxAshRate = 18f;
        [Min(1f)] public float minCrackleInterval = 6f;
        [Min(2f)] public float maxCrackleInterval = 22f;
        [Range(0f, 1f)] public float maxCrackleVolume = 0.28f;
        [Range(0f, 1f)] public float crackleThreatThreshold = 0.22f;

        public float CurrentThreat { get; private set; }
        public string ActiveZoneId { get; private set; } = "";
        public int WarningsIssued { get; private set; }
        public int CrackleCount { get; private set; }

        ElectricArc[] cachedArcs = Array.Empty<ElectricArc>();
        float[] zoneLastWarnedAt = Array.Empty<float>();
        int currentZoneIndex = -1;
        float nextScanAt;
        float nextCrackleAt = 8f;

        void Start()
        {
            if (!session) session = FindAnyObjectByType<GameSession>();
            if (!player) player = FindAnyObjectByType<PlayerCombat>();
            if (player) cityEdgeX = player.cityEdgeX;
            if (hazardRoot) cachedArcs = hazardRoot.GetComponentsInChildren<ElectricArc>(true);
            SyncZoneTimers();
            nextCrackleAt = Time.time + UnityEngine.Random.Range(minCrackleInterval, maxCrackleInterval);
            if (ashWisps) SetAshRate(0f);
        }

        void SyncZoneTimers()
        {
            int count = dangerZones != null ? dangerZones.Length : 0;
            if (zoneLastWarnedAt.Length != count)
            {
                zoneLastWarnedAt = new float[count];
                for (int i = 0; i < count; i++) zoneLastWarnedAt[i] = -9999f;
            }
        }

        void Update()
        {
            if (!player) return;

            bool reduced = session && session.reducedMotion;
            Vector3 playerPos = player.transform.position;
            bool inBerms = playerPos.x < cityEdgeX;

            if (ashWisps && inBerms)
            {
                ashWisps.transform.position = new Vector3(playerPos.x, playerPos.y + 0.35f, playerPos.z);
            }

            if (Time.time >= nextScanAt)
            {
                nextScanAt = Time.time + scanInterval;
                SampleThreatAndZones(playerPos, inBerms, reduced);
            }

            if (inBerms && CurrentThreat >= crackleThreatThreshold && Time.time >= nextCrackleAt)
            {
                float interval = BermsDangerMath.CrackleInterval(CurrentThreat, minCrackleInterval, maxCrackleInterval);
                nextCrackleAt = Time.time + interval * UnityEngine.Random.Range(0.8f, 1.25f);
                TriggerAmbientCrackle(playerPos, reduced);
            }
        }

        void SampleThreatAndZones(Vector3 playerPos, bool inBerms, bool reduced)
        {
            if (!inBerms)
            {
                CurrentThreat = 0f;
                currentZoneIndex = -1;
                ActiveZoneId = "";
                SetAshRate(0f);
                return;
            }

            SyncZoneTimers();
            int zoneIdx = BermsDangerMath.FindDangerZoneIndex(playerPos, dangerZones);
            bool inTier3 = zoneIdx >= 0 && dangerZones[zoneIdx].tier >= 3;

            if (zoneIdx != currentZoneIndex)
            {
                if (zoneIdx >= 0 && session && session.State == CityState.Play)
                {
                    if (BermsDangerMath.ShouldWarnZoneEntry(zoneIdx, currentZoneIndex, Time.time, zoneLastWarnedAt[zoneIdx], zoneWarnCooldown))
                    {
                        zoneLastWarnedAt[zoneIdx] = Time.time;
                        string line = string.IsNullOrEmpty(dangerZones[zoneIdx].warningLine)
                            ? $"Warden telemetry · Entering {dangerZones[zoneIdx].displayName} — high-threat sector."
                            : dangerZones[zoneIdx].warningLine;
                        session.Notify(line, "Warden Telemetry");
                        WarningsIssued++;
                    }
                }
                currentZoneIndex = zoneIdx;
                ActiveZoneId = zoneIdx >= 0 ? (dangerZones[zoneIdx].id ?? "") : "";
            }

            float nearestDist = float.PositiveInfinity;
            bool hasDangerTier = false;
            int activeNearby = 0;
            float maxDistSq = droidScanRange * droidScanRange;

            var targets = Health.Targets;
            for (int i = 0; i < targets.Count; i++)
            {
                var h = targets[i];
                if (!h || !h.Alive || !h.gameObject.activeInHierarchy) continue;
                var droid = h.GetComponent<FeralDroid>();
                if (!droid) continue;

                float d2 = (droid.transform.position - playerPos).sqrMagnitude;
                if (d2 > maxDistSq) continue;

                activeNearby++;
                float d = Mathf.Sqrt(d2);
                if (d < nearestDist) nearestDist = d;

                if (!hasDangerTier)
                {
                    var threat = droid.GetComponent<DroidThreat>();
                    if ((threat && threat.level >= 3) || DroidThreat.Tier(droid, player) == ThreatTier.Danger)
                        hasDangerTier = true;
                }
            }

            CurrentThreat = BermsDangerMath.ThreatLevel(
                playerPos.x,
                cityEdgeX,
                deepBermsX,
                nearestDist,
                hasDangerTier,
                activeNearby,
                inTier3,
                droidScanRange);

            SetAshRate(BermsDangerMath.AshEmissionRate(CurrentThreat, true, reduced, maxAshRate));
        }

        void SetAshRate(float rate)
        {
            if (!ashWisps) return;
            var em = ashWisps.emission;
            em.rateOverTime = rate;
            if (rate > 0.01f)
            {
                if (!ashWisps.isPlaying) ashWisps.Play();
            }
            else if (ashWisps.isPlaying)
            {
                ashWisps.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            }
        }

        void TriggerAmbientCrackle(Vector3 playerPos, bool reduced)
        {
            if (session && session.State != CityState.Play) return;

            if (!reduced && cachedArcs != null && cachedArcs.Length > 0)
            {
                ElectricArc nearest = null;
                float bestD2 = 95f * 95f;
                for (int i = 0; i < cachedArcs.Length; i++)
                {
                    var arc = cachedArcs[i];
                    if (!arc || !arc.gameObject.activeInHierarchy || !arc.sparks) continue;
                    float d2 = (arc.transform.position - playerPos).sqrMagnitude;
                    if (d2 < bestD2 && d2 > 6f * 6f)
                    {
                        bestD2 = d2;
                        nearest = arc;
                    }
                }
                if (nearest && nearest.sparks)
                {
                    nearest.sparks.Emit(Mathf.Max(4, nearest.burst / 2));
                }
            }

            if (crackleSource && crackleClips != null && crackleClips.Length > 0)
            {
                var clip = crackleClips[UnityEngine.Random.Range(0, crackleClips.Length)];
                if (clip)
                {
                    float vol = Mathf.Lerp(0.08f, maxCrackleVolume, CurrentThreat) * (reduced ? 0.65f : 1f);
                    crackleSource.pitch = UnityEngine.Random.Range(0.84f, 1.08f);
                    crackleSource.PlayOneShot(clip, vol);
                    CrackleCount++;
                }
            }
        }
    }
}
