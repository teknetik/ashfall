using UnityEngine;

namespace AthenHill
{
    /// Small ambient effects (barrel fire, flue smoke, steam puffs, exhaust haze) on ordinary saved ParticleSystems.
    /// Reduced Motion stops and clears them, as WindborneDust does for the cookfire. The particle colour follows the
    /// Ward lighting clock between a day and a night tint (clock lamp strength 0 = day, 1 = night). With Puff Seconds
    /// above zero the systems emit in intermittent puffs (steam vents). An optional fire light flickers at night and
    /// switches off by day (it is not on the City Light Circuit, which would overwrite the flicker).
    public sealed class AmbientLife : MonoBehaviour
    {
        public GameSession session;
        public CityTimeOfDay clock;
        public ParticleSystem[] systems = new ParticleSystem[0];
        [Tooltip("Multiplies each system's material colour in full daylight (clock lamp strength 0).")]
        public Color dayTint = Color.white;
        [Tooltip("Multiplies each system's material colour at night (clock lamp strength 1).")]
        public Color nightTint = Color.white;
        [Header("Intermittent puffs (Puff Seconds 0 = continuous)")]
        [Min(0)] public float puffSeconds;
        [Min(.1f)] public float minGap = 3f, maxGap = 7f;
        [Header("Optional fire light")]
        public Light fireLight;
        [Min(0)] public float fireIntensity = 1.6f;
        [Range(0, 1)] public float flicker = .35f;
        [Min(0)] public float flickerSpeed = 7f;
        [Tooltip("Fire light strength by day as a fraction of night; at 0 the light is off in daylight.")]
        [Range(0, 1)] public float fireDayStrength;

        static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        MaterialPropertyBlock block;
        ParticleSystemRenderer[] renderers;
        Color[] baseColors;
        bool hidden;
        float nextPuff, puffEnd, seed, lastLamp = -1;

        void OnEnable()
        {
            block ??= new MaterialPropertyBlock();
            renderers = new ParticleSystemRenderer[systems.Length];
            baseColors = new Color[systems.Length];
            for (int i = 0; i < systems.Length; i++)
            {
                if (!systems[i]) continue;
                renderers[i] = systems[i].GetComponent<ParticleSystemRenderer>();
                var m = renderers[i] ? renderers[i].sharedMaterial : null;
                baseColors[i] = m && m.HasProperty(BaseColorId) ? m.GetColor(BaseColorId) : Color.white;
            }
            seed = Random.value * 100f;
            hidden = false; lastLamp = -1;
            nextPuff = Time.time + Random.Range(0f, maxGap);
            if (puffSeconds > 0) SetEmission(false);
        }

        void SetEmission(bool on)
        {
            foreach (var s in systems) { if (!s) continue; var e = s.emission; e.enabled = on; }
        }

        void Update()
        {
            bool reduced = session && session.reducedMotion;
            if (reduced != hidden)
            {
                hidden = reduced;
                foreach (var s in systems)
                {
                    if (!s) continue;
                    if (reduced) s.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear); else s.Play(true);
                }
            }
            float lamp = clock ? clock.LampStrength : 1f;
            if (Mathf.Abs(lamp - lastLamp) > .005f)
            {
                lastLamp = lamp;
                var tint = Color.Lerp(dayTint, nightTint, lamp);
                for (int i = 0; i < renderers.Length; i++)
                {
                    if (!renderers[i]) continue;
                    renderers[i].GetPropertyBlock(block);
                    block.SetColor(BaseColorId, baseColors[i] * tint);
                    renderers[i].SetPropertyBlock(block);
                }
            }
            if (puffSeconds > 0 && !reduced)
            {
                if (Time.time >= nextPuff)
                {
                    puffEnd = Time.time + puffSeconds * Random.Range(.7f, 1.3f);
                    nextPuff = puffEnd + Random.Range(minGap, Mathf.Max(minGap, maxGap));
                    SetEmission(true);
                }
                else if (puffEnd > 0 && Time.time >= puffEnd) { puffEnd = 0; SetEmission(false); }
            }
            if (fireLight)
            {
                float strength = Mathf.Lerp(fireDayStrength, 1f, lamp);
                float n = 1f;
                if (!reduced)
                {
                    float t = Time.time * flickerSpeed + seed;
                    n = 1f - flicker + 2f * flicker * (Mathf.PerlinNoise(t, seed) * .7f + Mathf.PerlinNoise(t * 2.7f, seed + 3f) * .3f);
                }
                fireLight.intensity = fireIntensity * strength * n;
                fireLight.enabled = strength > .02f;
            }
        }

        void OnDisable()
        {
            if (renderers != null) foreach (var r in renderers) if (r) r.SetPropertyBlock(null);
            if (puffSeconds > 0) SetEmission(true);
        }
    }
}
