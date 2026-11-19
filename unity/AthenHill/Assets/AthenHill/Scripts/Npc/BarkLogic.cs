using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
    /// Pure bark rules (no scene access), so line choice, cooldowns and no-repeat can be tested in Edit Mode.
    public static class BarkRules
    {
        /// [from, to) on a 24 h clock; from > to wraps past midnight; equal ends or a 24 h span mean any hour.
        public static bool InHours(Vector2 hours, float hour)
        {
            float from = hours.x, to = hours.y;
            if (to - from >= 24 || Mathf.Approximately(from, to)) return true;
            hour = Mathf.Repeat(hour, 24); from = Mathf.Repeat(from, 24); to = Mathf.Repeat(to, 24);
            return from < to ? hour >= from && hour < to : hour >= from || hour < to;
        }
        /// A line with an hour window speaks for that time of day, so it is preferred over an any-hour line.
        public static bool TimeSpecific(Vector2 hours) => !(hours.y - hours.x >= 24 || Mathf.Approximately(hours.x, hours.y));
        public static bool Eligible(BarkLine l, BarkTrigger trigger, float hour, Func<string, bool> holds, Func<BarkLine, bool> spentOnce)
            => l != null && l.trigger == trigger && !string.IsNullOrWhiteSpace(l.text) && l.weight > 0 && InHours(l.hours, hour)
               && (string.IsNullOrWhiteSpace(l.requires) || holds == null || holds(l.requires))
               && !(l.once && spentOnce != null && spentOnce(l));
        /// Picks one eligible line: lines not heard recently first (recent is oldest first), time-of-day lines ahead of
        /// any-hour ones, then by weight with roll in [0, 1). When every eligible line was heard recently, the one heard
        /// longest ago. Null when nothing is eligible.
        public static BarkLine Pick(IList<BarkLine> lines, BarkTrigger trigger, float hour, Func<string, bool> holds, Func<BarkLine, bool> spentOnce, IReadOnlyList<string> recent, double roll)
        {
            if (lines == null) return null;
            var fresh = new List<BarkLine>(); BarkLine stalest = null; int stalestAt = int.MaxValue;
            foreach (var l in lines)
            {
                if (!Eligible(l, trigger, hour, holds, spentOnce)) continue;
                int at = Index(recent, l.id);
                if (at < 0) fresh.Add(l);
                else if (at < stalestAt) { stalestAt = at; stalest = l; }
            }
            if (fresh.Count == 0) return stalest;
            if (fresh.Exists(l => TimeSpecific(l.hours))) fresh.RemoveAll(l => !TimeSpecific(l.hours));
            float total = 0; foreach (var l in fresh) total += l.weight;
            float pick = (float)(Math.Max(0, Math.Min(.999999, roll)) * total);
            foreach (var l in fresh) { if (pick < l.weight) return l; pick -= l.weight; }
            return fresh[fresh.Count - 1];
        }
        static int Index(IReadOnlyList<string> recent, string id)
        {
            if (recent == null || id == null) return -1;
            for (int i = 0; i < recent.Count; i++) if (recent[i] == id) return i;
            return -1;
        }
        /// What a speaker says when the player walks up: an outstanding acknowledgement first, then a recent field order,
        /// then the ordinary greeting (a walker's passing remark).
        public static readonly BarkTrigger[] ApproachOrder = { BarkTrigger.Acknowledge, BarkTrigger.OrderDone, BarkTrigger.Greeting, BarkTrigger.Passing };
        /// Seconds a caption stays up: the take's length plus a beat, never shorter than its reading time.
        public static float CaptionSeconds(string text, float clipSeconds, float minSeconds = 2.2f, float maxSeconds = 8, float secondsPerWord = .3f)
        {
            float read = 1 + secondsPerWord * RadioQueue.Words(text);
            return Mathf.Clamp(Mathf.Max(read, clipSeconds > 0 ? clipSeconds + .5f : 0), minSeconds, Mathf.Max(minSeconds, maxSeconds));
        }
        /// Story flag that records a once-only line as spoken (saved with the other flags).
        public static string OnceFlag(string speakerId, string lineId) => "bark." + speakerId + "." + lineId;
    }

    /// Cooldowns and recent lines for every speaker (runtime only: nothing here is saved).
    public sealed class BarkMemory
    {
        readonly Dictionary<string, float> readyAt = new Dictionary<string, float>();
        readonly Dictionary<string, List<string>> recent = new Dictionary<string, List<string>>();
        /// How many of a speaker's latest lines are held back from repeating.
        public int recentCapacity = 3;
        /// No bark from anyone before this time (the gap between two barks, or a grace after a window closes).
        public float GlobalReadyAt { get; private set; }
        static string Key(string speaker, BarkTrigger t) => speaker + "|" + (int)t;
        public bool Ready(string speaker, BarkTrigger trigger, float now) => now >= GlobalReadyAt && (!readyAt.TryGetValue(Key(speaker, trigger), out var r) || now >= r);
        public bool TriggerReady(string speaker, BarkTrigger trigger, float now) => !readyAt.TryGetValue(Key(speaker, trigger), out var r) || now >= r;
        /// Holds one speaker's trigger until a time (e.g. no greeting straight after a conversation with them).
        public void Hold(string speaker, BarkTrigger trigger, float until) { var k = Key(speaker, trigger); if (!readyAt.TryGetValue(k, out var r) || r < until) readyAt[k] = until; }
        public void HoldAll(float until) { if (until > GlobalReadyAt) GlobalReadyAt = until; }
        public void Spoke(string speaker, string lineId, BarkTrigger trigger, float now, float cooldown, float globalGap)
        {
            Hold(speaker, trigger, now + Mathf.Max(0, cooldown));
            HoldAll(now + Mathf.Max(0, globalGap));
            if (!recent.TryGetValue(speaker, out var list)) recent[speaker] = list = new List<string>();
            list.Remove(lineId); list.Add(lineId);
            while (list.Count > Mathf.Max(0, recentCapacity)) list.RemoveAt(0);
        }
        static readonly List<string> None = new List<string>();
        public IReadOnlyList<string> Recent(string speaker) => recent.TryGetValue(speaker, out var l) ? l : None;
        public void Clear() { readyAt.Clear(); recent.Clear(); GlobalReadyAt = 0; }
    }

    /// Edge trigger with hysteresis: true once when the distance drops inside the radius; re-arms only after the
    /// player has stepped back beyond radius + margin, so loitering at the edge does not repeat a greeting.
    public struct ApproachGate
    {
        bool inside;
        public bool Inside => inside;
        public bool Enter(float distance, float radius, float margin)
        {
            if (!inside && distance <= radius) { inside = true; return true; }
            if (inside && distance > radius + Mathf.Max(0, margin)) inside = false;
            return false;
        }
        /// Treat the player as already inside (they were in conversation here), so leaving and returning greets again.
        public void Occupy() => inside = true;
    }
}
