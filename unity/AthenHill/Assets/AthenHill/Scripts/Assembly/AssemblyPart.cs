using System;
using UnityEngine;
namespace AthenHill
{
    /// One thing on the bench that can be handled: a part, a fastener, a tool, a fixture or a consumable. Built from a
    /// family's parts.json by AssemblyKitBuilder (CONTRACT.md section A); nothing here is authored by hand.
    /// The as-found pose (seated on its parent, or lying at its home place) is recorded at build time, so the bench can
    /// always be put back and a saved job replayed onto it.
    [DisallowMultipleComponent]
    public class AssemblyPart : MonoBehaviour
    {
        public string id = "", label = "";
        [Tooltip("part, fastener, tool, fixture or consumable")] public string kind = "part";
        [Tooltip("Contact class for sound: steel, alloy, wood, rubber, plastic, copper, glass, canvas, paper, ceramic")] public string material = "steel";
        [Tooltip("tiny, light, medium or heavy: sets the carry spring")] public string mass = "light";
        [Tooltip("Catalog item id when the part is an inventory item")] public string item = "";
        [Tooltip("The part it is seated on as found")] public string parentId = "";
        [Tooltip("Where it lies as found when it is not seated on a parent (a place id from the layout)")] public string homePlace = "";
        [Header("Seat")]
        [Tooltip("Turns about the insertion axis that seat: 1 one way only, 2 also reversed, 0 any angle")] public int symmetry = 1;
        public float tolMm = 5, tolDeg = 20;
        [Tooltip("Parts that hold this one in place (it will not come off while any of them is seated)")] public string[] heldBy = new string[0];
        [Tooltip("Point the hand holds (null = bounds centre)")] public Transform grab;
        [Tooltip("Tools: the working point; +Z points out of the tool")] public Transform tip;
        [Header("Fastener")]
        [Tooltip("slot or cross")] public string bit = "";
        public float turns = 6;
        public string[] holds = new string[0];
        [Header("Tool")]
        public string[] verbs = new string[0];
        public string[] tags = new string[0];
        [Tooltip("Settings the Flip control cycles through (screwdriver bits)")] public string[] modes = new string[0];
        [Tooltip("A continuous param the tool's own work turns (the drill's crank wheel; its spindle follows it)")] public string spinParam = "";
        [Header("Recorded at build time")]
        public Transform restParent;
        public Vector3 restPosition, restScale = Vector3.one; public Quaternion restRotation = Quaternion.identity;
        [Tooltip("Pose just clear of what it seats on, in the rest parent's space")] public Vector3 clearPosition; public Quaternion clearRotation = Quaternion.identity;
        public bool hasClear;
        [Tooltip("Own renderers' bounds in local space (children that are parts are not included)")] public Bounds localBounds = new Bounds(Vector3.zero, Vector3.one * .02f);
        public Renderer[] renderers = new Renderer[0];
        [Tooltip("Points on the part's own surface, in local space, for picking a real shape (a box is enough for a stand-in, and for anything big or skinned): the pointer has the part when it passes within Surface Radius of one of them. Empty = the box.")]
        public Vector3[] surface = new Vector3[0];
        [Tooltip("Local-space radius of each surface point (the spacing they were sampled at).")] public float surfaceRadius;
        [Tooltip("Where the hand holds a part that has no grab empty and whose box centre is not on it (the frame's is in the trigger guard): the surface point nearest the centre.")]
        public bool hasHandle; public Vector3 handle;

        /// Where it is now: seat, clear, held, loose, gone, or a place id.
        [NonSerialized] public string place = "seat";
        [NonSerialized] public int modeIndex;
        /// The tool's setting: one of its own modes, or the bit seated in it (SEAM.md section 3: `tools.bit_slot` has tag bit:slot).
        public string Mode
        {
            get
            {
                if (modes != null && modes.Length > 0) return modes[((modeIndex % modes.Length) + modes.Length) % modes.Length];
                var bit = SeatedBit; return bit ? bit.BitKind : "";
            }
        }
        public string BitKind { get { foreach (var t in tags ?? new string[0]) if (t.StartsWith("bit:")) return t.Substring(4); return ""; } }
        public bool IsBit => BitKind != "";
        /// The bit part sitting directly in this tool (a child part with a bit: tag), or null.
        public AssemblyPart SeatedBit { get { foreach (Transform c in transform) { var p = c.GetComponent<AssemblyPart>(); if (p && p.IsBit && p.gameObject.activeSelf) return p; } return null; } }
        public bool IsTool => kind == "tool" && !IsBit;
        public bool IsFixture => kind == "fixture";
        /// Used up or marked where it is (a test card, a speck of grit): never carried in the hand.
        public bool IsConsumable => kind == "consumable";
        public bool IsFastener => kind == "fastener";
        public bool Gone => place == "gone";
        /// Still on the part it was found on (seated, or backed out but not yet lifted away).
        public bool OnParent => place == "seat" || place == "clear";
        public Vector3 GrabPoint => grab ? grab.position : transform.TransformPoint(hasHandle ? handle : localBounds.center);
        public Vector3 TipPoint => tip ? tip.position : GrabPoint;
        /// From the part's origin to its grab point when the part has a given world rotation.
        public Vector3 GrabOffsetAt(Quaternion rotation) => rotation * Vector3.Scale(grab ? transform.InverseTransformPoint(grab.position) : hasHandle ? handle : localBounds.center, transform.lossyScale);
        public bool HasTag(string tag) => !string.IsNullOrEmpty(tag) && (id == tag || Array.IndexOf(tags ?? new string[0], tag) >= 0);

        public Pose RestWorld => new Pose(restParent ? restParent.TransformPoint(restPosition) : restPosition, (restParent ? restParent.rotation : Quaternion.identity) * restRotation);
        public Pose ClearWorld => hasClear ? new Pose(restParent ? restParent.TransformPoint(clearPosition) : clearPosition, (restParent ? restParent.rotation : Quaternion.identity) * clearRotation) : RestWorld;
        /// Unit direction from seated to clear (the way it comes off), world space; up when the part has no clear pose.
        public Vector3 RemovalAxis { get { var d = ClearWorld.position - RestWorld.position; return d.sqrMagnitude > 1e-10f ? d.normalized : Vector3.up; } }
        public float Travel => Vector3.Distance(ClearWorld.position, RestWorld.position);
        /// The same axis in the part's own space, for a part that is lying somewhere else (the tool roll's strap).
        public Vector3 LocalRemovalAxis { get { var d = Quaternion.Inverse(restRotation) * (clearPosition - restPosition); return hasClear && d.sqrMagnitude > 1e-10f ? d.normalized : Vector3.up; } }

        /// Ray against the part: its own box (in local space, padded so tiny parts can be picked) and, where the part has
        /// surface points, its real shape inside that box (a housing whose box swallows the scales beside it is only picked
        /// where it is). Distance along the ray, or -1.
        public float Raycast(Ray ray, float padMetres) => Raycast(ray, padMetres, out _);
        /// The same; `byHold` is true when only the hold point's catch took the ray (the shape itself was not under it).
        public float Raycast(Ray ray, float padMetres, out bool byHold)
        {
            byHold = false;
            var inv = transform.worldToLocalMatrix;
            var o = inv.MultiplyPoint3x4(ray.origin); var d = inv.MultiplyVector(ray.direction);
            float scale = d.magnitude; if (scale < 1e-9f) return -1; d /= scale;
            var lossy = transform.lossyScale; float s = Mathf.Max(1e-6f, Mathf.Abs(lossy.x));
            var b = localBounds; b.Expand(padMetres * 2 / s);
            if (!b.IntersectRay(new Ray(o, d), out float t) || t < 0) return -1;
            if (surface == null || surface.Length == 0) return t / scale;
            // (the pad that makes a tiny box pickable would make every real shape 6 mm fatter and neighbours in the dish one lump)
            float r = surfaceRadius + padMetres * .35f / s, r2 = r * r, best = float.MaxValue;
            for (int i = 0; i < surface.Length; i++)
            {
                var v = surface[i] - o; float along = Vector3.Dot(v, d);
                if (along < 0 || along >= best) continue;
                if (v.sqrMagnitude - along * along <= r2) best = along;
            }
            // the hold point is where the hand goes for it: a pointer close to it has the part even where the shape is open there
            // (between the handles of a pair of cutters)
            if (grab || hasHandle)
            {
                var v = (grab ? transform.InverseTransformPoint(grab.position) : handle) - o; float along = Vector3.Dot(v, d), rg = Mathf.Max(r, .012f / s);
                bool shapeHit = best < float.MaxValue;
                if (along >= 0 && along < best && v.sqrMagnitude - along * along <= rg * rg) { best = along; byHold = !shapeHit; }
            }
            return best < float.MaxValue ? best / scale : -1;
        }
    }
}
