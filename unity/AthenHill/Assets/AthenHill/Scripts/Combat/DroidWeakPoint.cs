using UnityEngine;

namespace AthenHill
{
    /// A droid's critical zone (19 Nov 2026 combat feel pass): a sphere that follows an anchor (the optic light or a
    /// head bone, so it moves with the animation). A player shot whose ray passes through it is a weak-point hit:
    /// PlayerCombat multiplies the damage left after armour by Damage Multiplier, shows the critical marker and lets
    /// FeralDroid stagger sooner. Sizes are metres at the droid's own scale 1 and grow with the droid's root scale (the
    /// 1.3× Foreman), never with bone scales, which on the Meshy rigs are not in metres.
    [DisallowMultipleComponent]
    public class DroidWeakPoint : MonoBehaviour
    {
        [Tooltip("Transform the zone follows (the optic light or the head bone). Empty = this droid's root.")]
        public Transform anchor;
        [Tooltip("Offset from the anchor in the anchor's rotation, metres at droid scale 1.")]
        public Vector3 offset;
        [Tooltip("Zone radius, metres at droid scale 1.")]
        [Min(.02f)] public float radius = .19f;
        [Tooltip("Multiplier on the damage left after armour. Level-3 droids use a smaller one so the starter pistol still cannot take them.")]
        [Range(1, 3)] public float damageMultiplier = 1.5f;
        [Tooltip("How far behind the struck collider surface the zone may sit and still count (the optic is often inside the body collider).")]
        [Min(0)] public float depthTolerance = .42f;
        [Tooltip("Shown in QA state and logs: optic, core, sensor …")]
        public string label = "optic";

        /// Balance (README): ×1.5 on the level-1/2 droids; ×1.25 on level 3 and above, so a full starter-pistol charge
        /// with a quarter of its hits on the optic (ExpectedWeakShare) stays under 60 % of a Scrap Reaper's vitality,
        /// the same bar the next-level enemy test holds the pistol to without weak points.
        public const float DefaultMultiplier = 1.5f, Level3Multiplier = 1.25f, ExpectedWeakShare = .25f;
        public static float MultiplierFor(int level) => level >= 3 ? Level3Multiplier : DefaultMultiplier;
        public static float RadiusFor(DroidKind kind) => kind == DroidKind.Hover ? .16f : kind == DroidKind.Wheeled ? .21f : .19f;

        public int Hits { get; private set; }
        float RootScale => Mathf.Max(.01f, Mathf.Abs(transform.lossyScale.x));
        public float WorldRadius => radius * RootScale;
        public Vector3 Centre
        {
            get
            {
                var a = anchor ? anchor : transform;
                return a.position + a.rotation * (offset * RootScale);
            }
        }

        /// True when a shot along this ray enters the zone before reachDistance (the struck surface or aim point) plus
        /// the depth tolerance. distance is where along the ray it enters.
        public bool Test(Vector3 origin, Vector3 direction, float reachDistance, out float distance)
            => WeakPointMath.RayHitsSphere(origin, direction, Centre, WorldRadius, Mathf.Max(0, reachDistance) + depthTolerance * RootScale, out distance);

        public void NoteHit() => Hits++;

        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1f, .75f, .2f, .8f);
            Gizmos.DrawWireSphere(Centre, WorldRadius);
        }
    }
}
