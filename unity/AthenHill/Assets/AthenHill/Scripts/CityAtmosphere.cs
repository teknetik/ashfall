using UnityEngine;

namespace AthenHill
{
    // Scene geometry/materials are saved assets. This component only advances the wind clock; weather
    // (WeatherConditions, 1 without a WeatherDirector) scales its rate and the drifting dust emission.
    public class CityAtmosphere : MonoBehaviour
    {
        public GameSession session;
        public ParticleSystem driftingDust;
        [Range(0f, 2f)] public float windSpeed = 1f;
        static readonly int TimeId = Shader.PropertyToID("_AthenAtmosphereTime");
        static readonly int PreviousTimeId = Shader.PropertyToID("_AthenAtmospherePreviousTime");
        float windTime;
        bool dustHidden;
        float dustBaseRate = -1, dustScale = 1;

        void OnEnable()
        {
            Shader.SetGlobalFloat(TimeId, windTime); Shader.SetGlobalFloat(PreviousTimeId, windTime);
            if (driftingDust && dustBaseRate < 0) dustBaseRate = driftingDust.emission.rateOverTimeMultiplier;
        }

        void Update()
        {
            bool reduced = session && session.reducedMotion;
            Shader.SetGlobalFloat(PreviousTimeId, windTime);
            // Integrating the rate (not scaling time) keeps every shader's phase continuous while the wind rises and falls.
            if (!reduced) windTime += Time.deltaTime * windSpeed * WeatherConditions.WindRate;
            Shader.SetGlobalFloat(TimeId, windTime);
            if (driftingDust && dustBaseRate >= 0 && Mathf.Abs(WeatherConditions.DustEmission - dustScale) > .01f)
            {
                dustScale = WeatherConditions.DustEmission;
                var em = driftingDust.emission; em.rateOverTimeMultiplier = dustBaseRate * dustScale;
            }
            if (!driftingDust || dustHidden == reduced) return;
            dustHidden = reduced;
            if (reduced) driftingDust.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            else driftingDust.Play();
        }

        void OnDisable()
        {
            Shader.SetGlobalFloat(TimeId, 0f); Shader.SetGlobalFloat(PreviousTimeId, 0f);
            if (driftingDust && dustBaseRate >= 0) { var em = driftingDust.emission; em.rateOverTimeMultiplier = dustBaseRate; dustScale = 1; }
        }
    }
}
