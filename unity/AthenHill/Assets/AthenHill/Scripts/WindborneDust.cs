using UnityEngine;

namespace AthenHill
{
    // Keeps world-space wind dust emitters centred on the viewer and honours Reduced Motion.
    // The particle systems themselves are ordinary saved scene objects.
    public sealed class WindborneDust : MonoBehaviour
    {
        public GameSession session;
        public Transform viewer;
        public ParticleSystem[] systems = new ParticleSystem[0];
        [Tooltip("Emitter height above the ground plane; particles simulate in world space.")]
        public float height = 0f;
        [Tooltip("Scale emission and drift speed with the weather (WeatherConditions). Off for local effects such as the cookfire.")]
        public bool followWeather;
        bool hidden;
        float[] baseRates, baseSpeeds;
        float appliedEmission = 1, appliedSpeed = 1;

        void OnEnable()
        {
            if (baseRates != null || !followWeather) return;
            baseRates = new float[systems.Length]; baseSpeeds = new float[systems.Length];
            for (int i = 0; i < systems.Length; i++)
            {
                if (!systems[i]) continue;
                baseRates[i] = systems[i].emission.rateOverTimeMultiplier;
                baseSpeeds[i] = systems[i].velocityOverLifetime.speedModifierMultiplier;
            }
        }

        void LateUpdate()
        {
            if (viewer)
            {
                var p = viewer.position;
                transform.position = new Vector3(p.x, height, p.z);
            }
            bool reduced = session && session.reducedMotion;
            if (followWeather && baseRates != null) FollowWeather();
            if (hidden == reduced) return;
            hidden = reduced;
            foreach (var system in systems)
            {
                if (!system) continue;
                if (reduced) system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                else system.Play(true);
            }
        }

        void FollowWeather()
        {
            float emission = WeatherConditions.DustEmission;
            // Drift speed follows the gusting wind more gently than the sway does.
            float speed = Mathf.Lerp(1, WeatherConditions.WindStrength, .6f);
            if (Mathf.Abs(emission - appliedEmission) < .01f && Mathf.Abs(speed - appliedSpeed) < .02f) return;
            appliedEmission = emission; appliedSpeed = speed;
            for (int i = 0; i < systems.Length; i++)
            {
                if (!systems[i]) continue;
                var em = systems[i].emission; em.rateOverTimeMultiplier = baseRates[i] * emission;
                var v = systems[i].velocityOverLifetime; v.speedModifierMultiplier = baseSpeeds[i] * speed;
            }
        }

        void OnDisable()
        {
            if (baseRates == null) return;
            for (int i = 0; i < systems.Length; i++)
            {
                if (!systems[i]) continue;
                var em = systems[i].emission; em.rateOverTimeMultiplier = baseRates[i];
                var v = systems[i].velocityOverLifetime; v.speedModifierMultiplier = baseSpeeds[i];
            }
            appliedEmission = appliedSpeed = 1;
        }
    }
}
