using UnityEngine;

namespace AthenHill
{
    /// Pure maths behind the combat feel pass (19 Nov 2026): weak-point rays, the hit marker's state and the camera
    /// impulse's trauma. No Unity lifecycle, so the Edit Mode tests drive it directly.
    public static class WeakPointMath
    {
        /// Distance along a ray to where it first enters a sphere. A ray that starts inside the sphere hits at 0.
        public static bool RayHitsSphere(Vector3 origin, Vector3 direction, Vector3 centre, float radius, float maxDistance, out float distance)
        {
            distance = -1;
            if (radius <= 0 || maxDistance < 0 || direction.sqrMagnitude < 1e-10f) return false;
            var dir = direction.normalized;
            var toCentre = centre - origin;
            float along = Vector3.Dot(toCentre, dir);
            float missSq = toCentre.sqrMagnitude - along * along;
            float rSq = radius * radius;
            if (missSq > rSq) return false;
            float half = Mathf.Sqrt(rSq - missSq);
            float exit = along + half;
            if (exit < 0) return false;
            distance = Mathf.Max(0, along - half);
            return distance <= maxDistance;
        }

        /// A weak-point hit multiplies what is left after armour, so armour still decides whether a weapon can hurt a
        /// droid at all; the weak point only rewards precision with a weapon that already gets through.
        public static float AfterArmour(float mitigated, float multiplier) => Mathf.Max(0, mitigated) * Mathf.Max(1, multiplier);

        /// Damage of one full nano charge against a droid, with this share of the hits on the weak point.
        public static float ChargeDamage(int shots, float mitigatedPerHit, float multiplier, float weakShare)
        {
            float share = Mathf.Clamp01(weakShare);
            return Mathf.Max(0, shots) * Mathf.Max(0, mitigatedPerHit) * ((1 - share) + share * Mathf.Max(1, multiplier));
        }
    }

    public enum HitMarkerKind { None, Hit, Critical, Kill }

    /// The crosshair hit marker: a kill outranks a critical, which outranks a hit. A lesser hit landing while a
    /// greater marker shows keeps the greater one on screen a little longer instead of replacing it.
    public sealed class HitMarkerState
    {
        public float hitSeconds = .14f, criticalSeconds = .22f, killSeconds = .38f;
        /// Kills and criticals open slightly larger and settle (skipped under Reduced Motion).
        public float popScale = 1.35f;
        /// Last share of the marker's time spent fading out.
        public float fadeShare = .35f;
        public HitMarkerKind Kind { get; private set; }
        public float Started { get; private set; } = -99;
        public float Until { get; private set; } = -99;
        public int Hits { get; private set; }
        public int Criticals { get; private set; }
        public int Kills { get; private set; }

        public static int Rank(HitMarkerKind kind) => (int)kind;
        public static HitMarkerKind KindFor(bool critical, bool killed) => killed ? HitMarkerKind.Kill : critical ? HitMarkerKind.Critical : HitMarkerKind.Hit;
        public float Seconds(HitMarkerKind kind) => kind == HitMarkerKind.Kill ? killSeconds : kind == HitMarkerKind.Critical ? criticalSeconds : kind == HitMarkerKind.Hit ? hitSeconds : 0;

        public HitMarkerKind Register(bool critical, bool killed, float now)
        {
            var kind = KindFor(critical, killed);
            if (kind == HitMarkerKind.Kill) Kills++; else if (kind == HitMarkerKind.Critical) Criticals++; else Hits++;
            if (Visible(now) && Rank(Kind) > Rank(kind)) { Until = Mathf.Max(Until, now + Seconds(kind)); return Kind; }
            Kind = kind; Started = now; Until = now + Seconds(kind);
            return Kind;
        }

        public bool Visible(float now) => Kind != HitMarkerKind.None && now < Until;
        public float Progress(float now) => Until > Started ? Mathf.Clamp01((now - Started) / (Until - Started)) : 1;

        public float Opacity(float now)
        {
            if (!Visible(now)) return 0;
            float p = Progress(now), fadeFrom = 1 - Mathf.Clamp01(fadeShare);
            return p <= fadeFrom ? 1 : Mathf.Clamp01((1 - p) / Mathf.Max(1e-4f, 1 - fadeFrom));
        }

        public float Scale(float now, bool reducedMotion)
        {
            if (!Visible(now) || reducedMotion || Kind == HitMarkerKind.Hit) return 1;
            float t = Mathf.Clamp01((now - Started) / .1f);
            return Mathf.Lerp(popScale, 1, 1 - (1 - t) * (1 - t));
        }

        public void Clear() { Kind = HitMarkerKind.None; Until = -99; }
    }

    /// Trauma model for camera shake: events add trauma (0..1), it decays linearly, and the shake amplitude is trauma
    /// squared, so small events stay subtle and large ones read clearly without a hard edge.
    public sealed class ImpulseState
    {
        public float decayPerSecond = 1.8f;
        public float Trauma { get; private set; }
        public float Shake => Trauma * Trauma;

        public void Add(float amount) { if (amount > 0 && !float.IsNaN(amount)) Trauma = Mathf.Clamp01(Trauma + amount); }
        public void Step(float deltaTime) { if (deltaTime > 0) Trauma = Mathf.Max(0, Trauma - decayPerSecond * deltaTime); }
        public void Clear() => Trauma = 0;

        /// 1 at the source, 0 at the radius, falling off quadratically so only close events really shake.
        public static float Falloff(float distance, float radius)
        {
            if (radius <= 0) return 0;
            float f = 1 - Mathf.Clamp01(distance / radius);
            return f * f;
        }

        /// Trauma for damage taken: a floor so any hit registers, plus the share of maximum vitality lost.
        public static float ForDamage(float damage, float maxHealth, float floor, float perVitality)
        {
            if (damage <= 0 || float.IsNaN(damage)) return 0;
            return Mathf.Clamp01(floor + perVitality * damage / Mathf.Max(1, maxHealth));
        }

        /// Trauma for a Phase 2 active combat verb (dodge, shove, EMP, overcharge).
        public static float ForVerb(CombatVerbKind kind, float dodge, float shove, float emp, float overcharge)
        {
            float raw = kind == CombatVerbKind.Dodge ? dodge
                : kind == CombatVerbKind.Shove ? shove
                : kind == CombatVerbKind.Emp ? emp
                : overcharge;
            return float.IsNaN(raw) || raw <= 0 ? 0 : Mathf.Clamp01(raw);
        }

        /// Settings slider (0..1) times the trauma amplitude; Reduced Motion removes shake entirely.
        public static float Amplitude(float shake, float settingScale, bool reducedMotion) => reducedMotion ? 0 : Mathf.Clamp01(shake) * Mathf.Clamp01(settingScale);
    }

    public enum CombatVerbKind { Dodge, Shove, Emp, Overcharge }

    /// Pure pose offsets for first-person weapon presentation (strafe tilt, dodge tuck, shove jab, EMP pulse and
    /// Nano Overcharge surge/hum). Always Reduced Motion safe and testable in Edit Mode.
    public static class ViewModelMotion
    {
        public static float StrafeRoll(float lateralSpeed, float maxSpeed, float maxDegrees, float aimBlend, bool reducedMotion)
        {
            if (reducedMotion || maxSpeed <= 0 || maxDegrees <= 0 || float.IsNaN(lateralSpeed)) return 0;
            float norm = Mathf.Clamp(lateralSpeed / maxSpeed, -1f, 1f);
            float aimScale = 1f - Mathf.Clamp01(aimBlend) * .7f;
            return -norm * maxDegrees * aimScale;
        }

        public static void VerbPose(float dodgeBlend, float shoveImpulse, float empImpulse, float overchargeSurge,
            bool overchargeActive, float time, float aimBlend, bool reducedMotion, out Vector3 offset, out Vector3 euler)
        {
            offset = Vector3.zero;
            euler = Vector3.zero;
            float aim = Mathf.Clamp01(aimBlend);
            if (reducedMotion)
            {
                if (overchargeActive) offset.y = .004f * (1f - aim * .5f);
                return;
            }
            float d = Smooth(dodgeBlend) * (1f - aim * .5f);
            if (d > 0)
            {
                offset += new Vector3(0, -.028f, -.03f) * d;
                euler += new Vector3(4f, 0, -6.5f) * d;
            }
            float s = Smooth(shoveImpulse);
            if (s > 0)
            {
                offset += new Vector3(-.025f, .01f, .11f) * s;
                euler += new Vector3(-6f, -10f, 12f) * s;
            }
            float e = Smooth(empImpulse);
            if (e > 0)
            {
                offset += new Vector3(0, -.022f, -.025f) * e;
                euler += new Vector3(5.5f, 0, -3.5f) * e;
            }
            float o = Smooth(overchargeSurge);
            if (o > 0)
            {
                offset += new Vector3(0, .018f, -.015f) * o;
                euler += new Vector3(-4.5f, 0, 2.5f) * o;
            }
            if (overchargeActive)
            {
                float humScale = 1f - aim * .65f;
                offset.x += Mathf.Sin(time * 42f) * .0008f * humScale;
                offset.y += (.004f + Mathf.Cos(time * 37f) * .0006f) * humScale;
            }
        }

        static float Smooth(float value)
        {
            if (float.IsNaN(value) || value <= 0) return 0;
            float t = Mathf.Clamp01(value);
            return t * t * (3f - 2f * t);
        }
    }

    /// Low-vitality vignette: off above the threshold, deepening toward zero vitality, with a slow heartbeat pulse that
    /// Reduced Motion holds steady.
    public static class VitalityWarning
    {
        public static float Intensity(float fraction, float threshold)
        {
            if (threshold <= 0 || float.IsNaN(fraction) || fraction >= threshold) return 0;
            return Mathf.Clamp01(1 - Mathf.Max(0, fraction) / threshold);
        }

        public static float Pulse(float intensity, float time, float beatsPerSecond, bool reducedMotion)
        {
            if (intensity <= 0) return 0;
            if (reducedMotion) return intensity * .8f;
            float beat = .5f + .5f * Mathf.Sin(time * beatsPerSecond * Mathf.PI * 2);
            return intensity * Mathf.Lerp(.6f, 1f, beat);
        }
    }
}
