using UnityEngine;

namespace AthenHill
{
    // Scene geometry/materials are saved assets. This component advances the wind clock; weather
    // (WeatherConditions, 1 without a WeatherDirector) and Outer Berms exposure scale its rate and drifting dust.
    public class CityAtmosphere : MonoBehaviour
    {
        public GameSession session;
        public ParticleSystem driftingDust;
        [Range(0f, 2f)] public float windSpeed = 1f;
        [Tooltip("World X boundary where Ward ends and the Outer Berms begin.")]
        public float bermsCityEdgeX = WastelandAtmosphere.DefaultCityEdgeX;
        [Tooltip("Transition distance in metres west of the wall.")]
        [Min(0f)] public float bermsBlendMetres = WastelandAtmosphere.DefaultBlendMetres;
        public float BermsWeight => bermsWeight;
        static readonly int TimeId = Shader.PropertyToID("_AthenAtmosphereTime");
        static readonly int PreviousTimeId = Shader.PropertyToID("_AthenAtmospherePreviousTime");
        float windTime, bermsWeight;
        bool dustHidden;
        float dustBaseRate = -1, dustScale = 1;

        void OnEnable()
        {
            Shader.SetGlobalFloat(TimeId, windTime); Shader.SetGlobalFloat(PreviousTimeId, windTime);
            if (driftingDust && dustBaseRate < 0) dustBaseRate = driftingDust.emission.rateOverTimeMultiplier;
            bermsWeight = 0f;
        }

        void Update()
        {
            bool reduced = session && session.reducedMotion;
            float targetBerms = session && session.player
                ? WastelandAtmosphere.BermsWeight(session.player.transform.position.x, bermsCityEdgeX, bermsBlendMetres)
                : 0f;
            bermsWeight = WastelandAtmosphere.SmoothWeight(bermsWeight, targetBerms, Time.deltaTime, reduced);
            Shader.SetGlobalFloat(PreviousTimeId, windTime);
            // Integrating the rate (not scaling time) keeps every shader's phase continuous while the wind rises and falls.
            float windMult = WastelandAtmosphere.WindRateMultiplier(bermsWeight, reduced);
            if (!reduced) windTime += Time.deltaTime * windSpeed * WeatherConditions.WindRate * windMult;
            Shader.SetGlobalFloat(TimeId, windTime);
            float targetDustScale = WeatherConditions.DustEmission * WastelandAtmosphere.DustEmissionMultiplier(bermsWeight, reduced);
            if (driftingDust && dustBaseRate >= 0 && Mathf.Abs(targetDustScale - dustScale) > .01f)
            {
                dustScale = targetDustScale;
                var em = driftingDust.emission; em.rateOverTimeMultiplier = dustBaseRate * dustScale;
            }
            if (!driftingDust || dustHidden == reduced) return;
            dustHidden = reduced;
            if (reduced) driftingDust.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            else driftingDust.Play();
        }

        void OnDisable()
        {
            bermsWeight = 0f;
            Shader.SetGlobalFloat(TimeId, 0f); Shader.SetGlobalFloat(PreviousTimeId, 0f);
            if (driftingDust && dustBaseRate >= 0) { var em = driftingDust.emission; em.rateOverTimeMultiplier = dustBaseRate; dustScale = 1; }
        }
    }
}
