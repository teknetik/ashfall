using UnityEngine;
namespace AthenHill
{
    public enum AssemblyMarkerKind { Place, Mark, Path, Zone }

    /// A named target on the bench that is not a part: a place something can lie or seat (mat outline, vise jaws, dish,
    /// the tang the grip slides onto), a point to aim a tool at, a line to follow, or an area to wipe. Marks, paths and
    /// zones come from a family's `__mark_`, `__path_` and `__zone_` empties; places come from the bench layout
    /// (art/steady_hands_bench_20261120/data/layout.json), bound to the art's `__mark_seat_*` empties where it has them.
    [DisallowMultipleComponent]
    public class AssemblyMarker : MonoBehaviour
    {
        public AssemblyMarkerKind kind;
        public string id = "";
        [Tooltip("The part this marker is on (it moves with it)")] public string ownerPart = "";
        [Tooltip("The transform whose space Approach is given in (the owner part; a place bound to a mark is parented to the mark, which may ride a bone)")] public Transform frame;
        [Tooltip("Place: part ids that may lie here; * = anything")] public string[] accepts = new string[0];
        [Tooltip("Place: contact class of the surface, for the seat sound")] public string material = "rubber";
        [Tooltip("Place: where the part comes in from, in metres in the space of what the place is on (up, for a place on the bench): it pulls in from pose + approach")] public Vector3 approach = new Vector3(0, .03f, 0);
        [Tooltip("Place: tolerances (0 = the part's own)")] public float tolMm, tolDeg;
        [Tooltip("Place: turns about the approach axis that seat (-1 = the part's own)")] public int symmetry = -1;
        [Tooltip("Place: a point on a surface of the real fixtures (not a full pose): a part is set down on it, its middle over the point and its underside on it, wherever its own origin is")] public bool restOn;
        [Tooltip("Place: mechanism that holds whatever lies here while it is closed (the vise jaw): the part cannot be taken until it is opened")] public string heldBy = "";
        [Tooltip("Place: the mechanism holds from this value up (a vise closed on the work is well short of 1)")] [Range(0, 1)] public float holdAbove = .5f;
        [Tooltip("Path: ordered points on the surface")] public Transform[] points = new Transform[0];
        [Tooltip("Zone: box size in this marker's space. Mark and Place: x is the pick radius")] public Vector3 size = new Vector3(.012f, .012f, .012f);
        [Tooltip("Zone: a wipe over the whole part that no hand works (a punch mark, tinning: an action's effect reveals it). Never picked.")] public bool passive;

        public bool Accepts(string partId) { foreach (var a in accepts) if (a == "*" || a == partId) return true; return false; }
        public Pose ApproachWorld { get { var f = frame ? frame : transform.parent; return new Pose(transform.position + (f ? f.TransformDirection(approach) : approach), transform.rotation); } }
        public float PickRadius => Mathf.Max(.006f, size.x);

        /// Ray against the marker: a sphere for marks and places, the box for zones, the nearest point for paths.
        public float Raycast(Ray ray)
        {
            if (kind == AssemblyMarkerKind.Zone)
            {
                var inv = transform.worldToLocalMatrix; var o = inv.MultiplyPoint3x4(ray.origin); var d = inv.MultiplyVector(ray.direction);
                float scale = d.magnitude; if (scale < 1e-9f) return -1;
                return new Bounds(Vector3.zero, size).IntersectRay(new Ray(o, d / scale), out float t) && t >= 0 ? t / scale : -1;
            }
            if (kind == AssemblyMarkerKind.Path)
            {
                float best = -1;
                foreach (var p in points) { if (!p) continue; float t = Sphere(ray, p.position, PickRadius); if (t >= 0 && (best < 0 || t < best)) best = t; }
                return best;
            }
            return Sphere(ray, transform.position, PickRadius);
        }
        public static float Sphere(Ray ray, Vector3 centre, float radius)
        {
            var oc = ray.origin - centre; float b = Vector3.Dot(oc, ray.direction), c = oc.sqrMagnitude - radius * radius, h = b * b - c;
            if (h < 0) return -1;
            float t = -b - Mathf.Sqrt(h);
            return t >= 0 ? t : (-b + Mathf.Sqrt(h) >= 0 ? 0 : -1);
        }
    }
}
