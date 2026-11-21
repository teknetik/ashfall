using System;
using UnityEngine;

namespace AthenHill
{
    /// Pure rules and timing for Phase 2 active combat verbs (21 Nov 2026):
    /// directional Dodge/Dash with evasion i-frames, close-quarters Shove, and two active Nano abilities
    /// (EMP Disruptor pulse and Nano Overcharge, with Eye-implant synergy).
    public static class CombatVerbs
    {
        // ---- Dodge / sidestep dash
        public const float DodgeDuration = .22f;
        public const float DodgeInvulnerableDuration = .18f;
        public const float DodgeSpeed = 13.5f;
        public const float DodgeCooldown = 1.4f;
        public const float DodgeNanoCost = 12f;

        // ---- Melee shove / rifle butt
        public const float ShoveRange = 2.8f;
        public const float ShoveHalfAngle = 65f;
        public const float ShoveKnockback = 2.2f;
        public const float ShoveStaggerSeconds = .85f;
        public const float ShoveDamage = 12f;
        public const float ShoveCooldown = 1.2f;

        // ---- Nano EMP Disruptor (Q)
        public const float EmpNanoCost = 30f;
        public const float EmpCooldown = 9f;
        public const float EmpRadius = 7.5f;
        public const float EmpStunSeconds = 1.8f;
        public const float EmpArmourStripFraction = .5f;
        public const float EmpArmourStripSeconds = 8f;

        // ---- Nano Overcharge (X)
        public const float OverchargeNanoCost = 25f;
        public const float OverchargeCooldown = 12f;
        public const float OverchargeDuration = 6f;
        public const float OverchargeEyeBonusSeconds = 2f;
        public const float OverchargeArmourPenBonus = 6f;
        public const float OverchargeFireIntervalScale = .8f;
        public const float OverchargeDamageScale = 1.2f;
        public const float EyeOverchargeWeakPointScale = 1.2f;

        /// Resolves the flat world dash direction: uses camera-relative movement input when held,
        /// otherwise dashes backward away from the aim line (or forward if viewForward is degenerate).
        public static Vector3 DodgeDirection(Vector2 moveInput, Vector3 viewForward)
        {
            var fwd = Vector3.ProjectOnPlane(viewForward, Vector3.up);
            if (fwd.sqrMagnitude < 1e-4f) fwd = Vector3.forward;
            else fwd.Normalize();
            var right = Vector3.Cross(Vector3.up, fwd);
            if (moveInput.sqrMagnitude > 1e-3f)
            {
                var dir = fwd * moveInput.y + right * moveInput.x;
                if (dir.sqrMagnitude > 1e-4f) return dir.normalized;
            }
            return -fwd;
        }

        /// True when a target at targetPos is within the close-quarters shove cone in front of origin/forward.
        public static bool InShoveCone(Vector3 origin, Vector3 forward, Vector3 targetPos, float range = ShoveRange, float halfAngle = ShoveHalfAngle)
        {
            var flatTo = targetPos - origin; flatTo.y = 0;
            float dist = flatTo.magnitude;
            if (dist > range) return false;
            if (dist < .25f) return true;
            var flatFwd = forward; flatFwd.y = 0;
            if (flatFwd.sqrMagnitude < 1e-4f) return true;
            return Vector3.Angle(flatFwd.normalized, flatTo / dist) <= halfAngle;
        }

        /// True when a target lies within the radial EMP pulse.
        public static bool InEmpRadius(Vector3 origin, Vector3 targetPos, float radius = EmpRadius)
        {
            var flat = targetPos - origin; flat.y = 0;
            return flat.sqrMagnitude <= radius * radius;
        }

        /// Effective droid armour after an active EMP armour-strip fraction (0..1).
        public static float StrippedArmour(float baseArmour, float stripFraction)
            => Mathf.Max(0, baseArmour * (1f - Mathf.Clamp01(stripFraction)));

        /// Overcharge duration, extended when the player has an Eye implant fitted.
        public static float OverchargeSeconds(bool hasEyeImplant)
            => OverchargeDuration + (hasEyeImplant ? OverchargeEyeBonusSeconds : 0f);

        /// Weak-point radius multiplier while Overcharge is active with an Eye implant fitted.
        public static float WeakPointRadiusScale(bool overchargeActive, bool hasEyeImplant)
            => overchargeActive && hasEyeImplant ? EyeOverchargeWeakPointScale : 1f;
    }

    /// Pure state machine for the player's directional dodge/dash.
    [Serializable]
    public sealed class DodgeState
    {
        public float ActiveUntil { get; private set; } = -99f;
        public float InvulnerableUntil { get; private set; } = -99f;
        public float ReadyAt { get; private set; } = -99f;
        public Vector3 Direction { get; private set; }

        public bool Active(float now) => now < ActiveUntil;
        public bool Invulnerable(float now) => now < InvulnerableUntil;
        public float CooldownRemaining(float now) => Mathf.Max(0, ReadyAt - now);

        public bool TryStart(float now, Vector3 worldDirection, float duration = CombatVerbs.DodgeDuration,
            float invulnDuration = CombatVerbs.DodgeInvulnerableDuration, float cooldown = CombatVerbs.DodgeCooldown)
        {
            if (now < ReadyAt || now < ActiveUntil) return false;
            var flat = new Vector3(worldDirection.x, 0, worldDirection.z);
            if (flat.sqrMagnitude < 1e-4f) return false;
            Direction = flat.normalized;
            ActiveUntil = now + Mathf.Max(.05f, duration);
            InvulnerableUntil = now + Mathf.Clamp(invulnDuration, 0, duration);
            ReadyAt = now + Mathf.Max(duration, cooldown);
            return true;
        }

        public void Reset()
        {
            ActiveUntil = -99f;
            InvulnerableUntil = -99f;
            ReadyAt = -99f;
            Direction = Vector3.zero;
        }
    }
}
