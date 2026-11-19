using System;
using UnityEngine;
namespace AthenHill
{
    /// What makes a colonist speak outside dialogue (NPC life pass, 19 Nov 2026).
    public enum BarkTrigger { Greeting, Idle, Weapon, Acknowledge, OrderDone, Passing }

    [Serializable]
    public class BarkLine
    {
        [Tooltip("Stable id within this set (names the voice take and the once-only story flag).")]
        public string id;
        public BarkTrigger trigger;
        [TextArea(1, 3)] public string text;
        [Tooltip("Offline spoken take. Without one the line is caption-only (and skipped while captions are off).")]
        public AudioClip voice;
        [Tooltip("QuestConditions expression (primer, flag:home_leased, !primer…); empty = always.")]
        public string requires;
        [Tooltip("City clock window [from, to) in hours; wraps past midnight (21–5). 0–24 = any hour.")]
        public Vector2 hours = new Vector2(0, 24);
        [Tooltip("Spoken at most once per save (recorded as a story flag), e.g. acknowledging the primer.")]
        public bool once;
        [Min(0)] public float weight = 1;
    }

    /// One speaker's barks. Assigned to that speaker's NpcBarker; lines are edited in the Inspector.
    [CreateAssetMenu(menuName = "Athen Hill/NPC bark set")]
    public class BarkSet : ScriptableObject
    {
        [Tooltip("NpcDefinition id, or the walker's id (walker_daro…). Names the once-only flags.")]
        public string speakerId;
        [Tooltip("Caption name. A talking colonist's NpcDefinition display name takes precedence.")]
        public string displayName;
        public BarkLine[] lines = new BarkLine[0];
        public bool Has(BarkTrigger trigger)
        {
            if (lines != null) foreach (var l in lines) if (l != null && l.trigger == trigger && !string.IsNullOrWhiteSpace(l.text)) return true;
            return false;
        }
    }
}
