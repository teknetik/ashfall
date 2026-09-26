using UnityEngine;

namespace AthenHill
{
    // Gentle noise-driven flicker for a small open-fire practical light.
    [RequireComponent(typeof(Light))]
    public sealed class FireFlicker : MonoBehaviour
    {
        public GameSession session;
        [Min(0)] public float baseIntensity = 1.6f;
        [Range(0, 1)] public float flicker = .35f;
        [Min(0)] public float speed = 7f;
        Light fire;
        float seed;

        void OnEnable() { fire = GetComponent<Light>(); seed = Random.value * 100f; }

        void Update()
        {
            if (session && session.reducedMotion) { fire.intensity = baseIntensity; return; }
            float t = Time.time * speed + seed;
            float n = Mathf.PerlinNoise(t, seed) * .7f + Mathf.PerlinNoise(t * 2.7f, seed + 3f) * .3f;
            fire.intensity = baseIntensity * (1f - flicker + 2f * flicker * n);
        }
    }
}
