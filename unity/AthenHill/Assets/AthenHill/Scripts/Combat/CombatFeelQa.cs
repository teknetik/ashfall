using UnityEngine;

namespace AthenHill
{
    /// Read-only combat feel state for the dev bridge (dev.state → combat.feel) and the NativeQa snapshot
    /// (combat.feel), so a native check can assert hit markers, weak points, shake and the low-vitality vignette.
    /// Plain values only.
    public static class CombatFeelQa
    {
        public static object State(PlayerCombat combat)
        {
            if (!combat) return new { available = false };
            var hud = Object.FindAnyObjectByType<CombatHud>();
            var impulse = Object.FindAnyObjectByType<CameraImpulse>();
            var fx = Object.FindAnyObjectByType<CombatFx>();
            var last = combat.LastHit;
            return new
            {
                available = true,
                hits = combat.Hits,
                criticalHits = combat.CriticalHits,
                weakPointHits = combat.WeakPointHits,
                kills = combat.Kills,
                lastHit = last.target ? new { critical = last.critical, weakPoint = last.weakPoint, killed = last.killed, dealt = last.dealt, zone = last.zone } : null,
                marker = hud ? new
                {
                    shown = hud.MarkerShown.ToString(),
                    hits = hud.Markers.Hits,
                    criticals = hud.Markers.Criticals,
                    kills = hud.Markers.Kills,
                    ticks = hud.TicksPlayed,
                    lowVitality = hud.LowVitality,
                } : null,
                shake = impulse ? new
                {
                    impulses = impulse.Impulses,
                    trauma = impulse.Trauma,
                    lastAngle = impulse.LastAngle,
                    peakAngle = impulse.PeakAngle,
                    suppressed = impulse.Suppressed,
                } : null,
                criticalFlashes = fx ? fx.CriticalFlashes : 0,
                fxLights = FxBurst.LightsLit,
                fxLightCap = FxBurst.MaxLights,
                weatherVisibility = WeatherConditions.Visibility,
                weakPoints = WeakPointCount(),
                criticalStaggers = CriticalStaggers(),
                // Native QA (19 Nov 2026): where each live droid's weak point is, so a check can aim the camera at it.
                weakPointZones = WeakPointZones(),
                lastShotSoundSet = combat.LastShotSoundSet,
                lastCone = combat.LastCone,
                droidAudio = DroidAudio(),
                boltFlybys = DroidBolt.Flybys,
                boltImpacts = DroidBolt.Impacts,
            };
        }

        static object[] DroidAudio()
        {
            var list = new System.Collections.Generic.List<object>();
            foreach (var d in FeralDroid.Active)
                if (d) list.Add(new { droid = d.displayName, played = d.VoicesPlayed, dropped = d.VoicesDropped, last = d.LastVoiceClip, roll = d.RollLevel, rollPlaying = d.RollPlaying });
            return list.ToArray();
        }

        static object[] WeakPointZones()
        {
            var list = new System.Collections.Generic.List<object>();
            foreach (var d in FeralDroid.Active)
            {
                if (!d || !d.Health || !d.Health.Alive) continue;
                var w = d.GetComponent<DroidWeakPoint>();
                if (!w || !w.isActiveAndEnabled) continue;
                var c = w.Centre;
                list.Add(new { droid = d.displayName, centre = new[] { c.x, c.y, c.z }, radius = w.WorldRadius, hits = w.Hits, state = d.State.ToString() });
            }
            return list.ToArray();
        }

        static int WeakPointCount()
        {
            int n = 0;
            foreach (var d in FeralDroid.Active) if (d && d.GetComponent<DroidWeakPoint>()) n++;
            return n;
        }

        static int CriticalStaggers()
        {
            int n = 0;
            foreach (var d in FeralDroid.Active) if (d) n += d.CriticalStaggers;
            return n;
        }
    }
}
