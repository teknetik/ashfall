using UnityEngine;

namespace AthenHill
{
    // Scene geometry/materials are saved assets. This component only advances the wind clock.
    public class CityAtmosphere : MonoBehaviour
    {
        public GameSession session;
        public ParticleSystem driftingDust;
        [Range(0f, 2f)] public float windSpeed = 1f;
        static readonly int TimeId = Shader.PropertyToID("_AthenAtmosphereTime");
        float windTime;
        bool dustHidden;

        void OnEnable() { Shader.SetGlobalFloat(TimeId, windTime); }

        void Update()
        {
            bool reduced = session && session.reducedMotion;
            if (!reduced) windTime += Time.deltaTime * windSpeed;
            Shader.SetGlobalFloat(TimeId, windTime);
            if (!driftingDust || dustHidden == reduced) return;
            dustHidden = reduced;
            if (reduced) driftingDust.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            else driftingDust.Play();
        }

        void OnDisable() { Shader.SetGlobalFloat(TimeId, 0f); }
    }
}
