using UnityEngine;
using UnityEngine.Audio;
namespace AthenHill
{
    /// A speaker for ambient barks (a talking colonist's NpcAgent root or an ambient walker's root). It holds the lines,
    /// the distances that wake each trigger and its own voice emitter; BarkDirector decides when it speaks.
    [DisallowMultipleComponent]
    public class NpcBarker : MonoBehaviour
    {
        public BarkSet barks;
        [Tooltip("Talking colonist on this root (found automatically). Empty for ambient walkers.")]
        public NpcAgent agent;
        [Tooltip("Metres. Walking inside this greets (or acknowledges a milestone); stepping back beyond it plus Rearm Margin re-arms.")]
        [Min(0)] public float greetRadius = 5.5f;
        [Min(0)] public float rearmMargin = 3;
        [Tooltip("Metres. Idle remarks only while the player is this close and in sight.")]
        [Min(0)] public float idleRadius = 9;
        [Tooltip("Metres. Reacts to a weapon drawn or reached for inside the walls within this distance.")]
        [Min(0)] public float weaponRadius = 12;
        [Tooltip("Metres. Ambient walkers make a passing remark when the player comes this close.")]
        [Min(0)] public float passRadius = 3.2f;
        [Tooltip("Height of the mouth above the root (voice emitter and line-of-sight end).")]
        public float voiceHeight = 1.55f;
        [Range(0, 1)] public float voiceGain = .75f;
        [Tooltip("Spatial blend of the bark voice (1 = fully positional).")]
        [Range(0, 1)] public float spatialBlend = .85f;
        [Min(1)] public float maxDistance = 18;
        /// Runtime state kept by BarkDirector.
        [System.NonSerialized] public ApproachGate approach;
        [System.NonSerialized] public float nextIdle = -1;
        [System.NonSerialized] public string orderAcknowledged;
        AudioSource voice;
        public bool Walker => !agent;
        public string SpeakerId => agent && agent.definition ? agent.definition.id : barks ? barks.speakerId : name;
        public string DisplayName => agent && agent.definition ? agent.definition.displayName : barks && !string.IsNullOrEmpty(barks.displayName) ? barks.displayName : name;
        public Vector3 Mouth => transform.position + Vector3.up * voiceHeight;
        public bool Speaking => voice && voice.isPlaying;
        void Awake() { if (!agent) agent = GetComponent<NpcAgent>(); }
        public void Play(AudioClip clip, float effectsLevel, AudioMixerGroup group)
        {
            if (!clip) return;
            if (!voice)
            {
                var emitter = new GameObject("Bark voice");
                emitter.transform.SetParent(transform, false);
                emitter.transform.localPosition = new Vector3(0, voiceHeight, 0);
                voice = emitter.AddComponent<AudioSource>();
                voice.playOnAwake = false;
                voice.minDistance = 1.5f;
                voice.rolloffMode = AudioRolloffMode.Linear;
                voice.priority = 90;
            }
            voice.spatialBlend = spatialBlend; voice.maxDistance = maxDistance;
            if (group) voice.outputAudioMixerGroup = group;
            SetLevel(effectsLevel);
            voice.clip = clip; voice.Play();
        }
        public void SetLevel(float effectsLevel) { if (voice) voice.volume = voiceGain * Mathf.Clamp01(effectsLevel); }
        public void Stop() { if (voice) { voice.Stop(); voice.clip = null; } }
        void OnDisable() { Stop(); if (agent) agent.barking = false; }
        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(.35f, .84f, .84f, .6f);
            Gizmos.DrawWireSphere(transform.position, Walker ? passRadius : greetRadius);
            Gizmos.color = new Color(.64f, .54f, .38f, .4f);
            if (!Walker) Gizmos.DrawWireSphere(transform.position, idleRadius);
        }
    }
}
