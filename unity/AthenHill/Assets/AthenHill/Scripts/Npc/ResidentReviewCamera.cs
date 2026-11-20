using UnityEngine;
namespace AthenHill
{
    /// Residents pass (20 Nov 2026): a review camera that follows a walking resident, so a QA "view" of it frames the
    /// person wherever they are on their route (a fixed camera at one stop usually showed an empty wall). The Camera
    /// component stays disabled; NativeQa's "view" copies this transform into the game camera when it is called.
    /// Each frame it tries a set of directions around the resident's facing (30 degrees off first, as a person beside
    /// them would stand) and takes the first one with a clear line (sphere cast) from the head to the lens; if none is
    /// clear, the direction with the most room, never closer than Min Distance. Face: ~1.0 m at head height (long lens);
    /// Body: ~3 m, full figure; Beside: conversation distance (~1.4 m) at the player's eye height.
    [DisallowMultipleComponent]
    public sealed class ResidentReviewCamera : MonoBehaviour
    {
        public enum Framing { Face, Body, Beside }
        public Transform target;
        public Framing framing;
        [Tooltip("The resident's standing height (metres).")]
        [Min(1)] public float height = 1.75f;
        static readonly float[] Angles = { 30, -30, 55, -55, 0, 90, -90, 130, -130 };

        // QA only: release players skip the per-frame casts.
        void Awake() { if (!Application.isEditor && !Debug.isDebugBuild) enabled = false; }

        void LateUpdate()
        {
            if (!target) return;
            var t = target; var fwd = t.forward; fwd.y = 0; if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.forward; fwd.Normalize();
            float dist, minDist, lensHeight; Vector3 look;
            switch (framing)
            {
                case Framing.Face: look = t.position + Vector3.up * (height * .925f); dist = 1.0f; minDist = .65f; lensHeight = height * .93f; break;
                case Framing.Body: look = t.position + Vector3.up * (height * .5f); dist = 3.0f; minDist = 2.0f; lensHeight = 1.5f; break;
                default: look = t.position + Vector3.up * (height * .92f); dist = 1.4f; minDist = 1.0f; lensHeight = 1.62f; break;
            }
            Vector3 best = Vector3.zero; float bestRoom = -1;
            foreach (var a in Angles)
            {
                var dir = Quaternion.Euler(0, a, 0) * fwd;
                var pos = t.position + dir * dist + Vector3.up * lensHeight;
                var ray = pos - look; float len = ray.magnitude;
                float room = len;
                foreach (var hit in Physics.SphereCastAll(look, .12f, ray / len, len, ~0, QueryTriggerInteraction.Ignore))
                    if (!hit.transform.IsChildOf(t) && hit.distance < room) room = hit.distance;
                if (room >= len - .001f) { best = pos; bestRoom = len; break; }
                if (room > bestRoom) { bestRoom = room; best = look + ray / len * Mathf.Max(minDist, room - .1f); }
            }
            transform.SetPositionAndRotation(best, Quaternion.LookRotation(look - best, Vector3.up));
        }
    }
}
