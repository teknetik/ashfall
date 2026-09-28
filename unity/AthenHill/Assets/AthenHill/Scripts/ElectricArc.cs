using UnityEngine;

namespace AthenHill
{
    /// Intermittent electrical arc from damaged equipment (the depot's broken charging cradle, a shorting hall lamp):
    /// a burst of sparks, a short light flash with a stutter, and a crackle. Interval, flash and burst size are
    /// Inspector-tunable. Reduced motion keeps the flash dim and steady.
    public sealed class ElectricArc : MonoBehaviour
    {
        public GameSession session;
        public ParticleSystem sparks;
        public Light flash;
        public AudioSource voice;
        public AudioClip[] clips = new AudioClip[0];
        [Min(.1f)] public float minInterval = 1.6f, maxInterval = 4.5f;
        [Min(0)] public float flashIntensity = 3.2f, flashSeconds = .22f;
        [Min(0)] public int burst = 22;
        [Tooltip("Arcs pause while the listener is farther than this (no cost at the gate).")]
        [Min(1)] public float activeDistance = 45;
        float next, flashStart = -9;
        Transform listener;

        void OnEnable() { next = Time.time + Random.Range(.3f, maxInterval); if (flash) flash.intensity = 0; }

        void Update()
        {
            bool reduced = session && session.reducedMotion;
            if (flash)
            {
                float t = (Time.time - flashStart) / Mathf.Max(.01f, flashSeconds);
                float v = t < 1 ? (1 - t) * (reduced ? .4f : (Mathf.PerlinNoise(Time.time * 60, 3) > .35f ? 1 : .25f)) : 0;
                flash.intensity = flashIntensity * v;
                flash.enabled = v > 0;
            }
            if (Time.time < next) return;
            next = Time.time + Random.Range(minInterval, maxInterval);
            if (!listener) { var l = FindAnyObjectByType<AudioListener>(); listener = l ? l.transform : null; }
            if (listener && (listener.position - transform.position).sqrMagnitude > activeDistance * activeDistance) return;
            flashStart = Time.time;
            if (sparks) sparks.Emit(reduced ? burst / 3 : burst);
            if (voice && clips.Length > 0) { voice.pitch = Random.Range(.9f, 1.12f); voice.PlayOneShot(clips[Random.Range(0, clips.Length)], Random.Range(.7f, 1f)); }
        }
    }
}
