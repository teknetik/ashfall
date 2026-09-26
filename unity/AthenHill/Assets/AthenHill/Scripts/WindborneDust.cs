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
        bool hidden;

        void LateUpdate()
        {
            if (viewer)
            {
                var p = viewer.position;
                transform.position = new Vector3(p.x, height, p.z);
            }
            bool reduced = session && session.reducedMotion;
            if (hidden == reduced) return;
            hidden = reduced;
            foreach (var system in systems)
            {
                if (!system) continue;
                if (reduced) system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                else system.Play(true);
            }
        }
    }
}
