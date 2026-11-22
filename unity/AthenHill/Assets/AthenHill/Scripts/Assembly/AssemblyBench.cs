using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Audio;
using UnityEngine.UIElements;
namespace AthenHill
{
    /// What the pointer (or the keyboard focus ring) is on: a part or a marker.
    public struct AssemblyHit
    {
        public AssemblyPart part; public AssemblyMarker marker; public Vector3 point; public float distance;
        public bool Valid => part || marker;
        public string Id => part ? part.id : marker ? marker.id : "";
        public Vector3 Position => part ? part.GrabPoint : marker ? marker.transform.position : point;
        public static AssemblyHit Of(AssemblyPart p) => new AssemblyHit { part = p, point = p ? p.GrabPoint : Vector3.zero };
        public static AssemblyHit Of(AssemblyMarker m) => new AssemblyHit { marker = m, point = m ? m.transform.position : Vector3.zero };
    }

    /// The bench as a set of parts, markers and mechanisms (the scene root "Steady Hands bench"). It knows where every
    /// part is as found, can put the whole set back, and can replay a job's finished actions onto it, so the scene is
    /// always a function of the job and a saved job needs no part positions. It holds no job logic of its own.
    [DisallowMultipleComponent]
    public class AssemblyBench : MonoBehaviour
    {
        public AssemblyRecipe recipe;
        public AssemblySettings settings;
        public AssemblyAudioTable audioTable;
        public string stationId = "station_field_fabricator";
        [Tooltip("A point on the work surface; its up is the bench normal.")] public Transform surface;
        [Tooltip("Half extents (x, z) of the area a carried object may be taken over, around the surface point.")] public Vector2 reach = new Vector2(1.08f, .6f);
        [Tooltip("Parts that are off their parents and lying free are kept under this.")] public Transform loose;
        [Tooltip("Root of the cam_bench_* review cameras; the session uses them as its shots.")] public Transform cameraRoot;
        public Material ghostMaterial, lineMaterial;
        /// A part whose own emissive material the bench drives (the pistol's status lamp): effect "part=0.5".
        [Serializable] public class Lamp { public string part = ""; [ColorUsage(false, true)] public Color color = Color.cyan; [Range(0, 1)] public float asFound = 1; }
        public Lamp[] lamps = new Lamp[0];
        static readonly int Emission = Shader.PropertyToID("_EmissionColor"), EmissiveFactor = Shader.PropertyToID("emissiveFactor");
        MaterialPropertyBlock lampBlock;
        public bool SetLamp(string partId, float level)
        {
            var lamp = Array.Find(lamps, l => l.part == partId); var p = Part(partId);
            if (lamp == null || !p) return false;
            lampBlock ??= new MaterialPropertyBlock();
            foreach (var r in p.renderers) if (r) { r.GetPropertyBlock(lampBlock); lampBlock.SetColor(Emission, lamp.color * Mathf.Clamp01(level)); lampBlock.SetColor(EmissiveFactor, lamp.color * Mathf.Clamp01(level)); r.SetPropertyBlock(lampBlock); }
            return true;
        }
        /// Two parts change places (the screwdriver's bit and the one in the block).
        public void Swap(AssemblyPart a, AssemblyPart b)
        {
            if (!a || !b) return;
            var pa = a.transform.parent; var pb = b.transform.parent; var posA = a.transform.position; var rotA = a.transform.rotation; string placeA = a.place;
            Attach(a.transform, pb, b.transform.position, b.transform.rotation); Attach(b.transform, pa, posA, rotA);
            a.place = b.place == "seat" ? "at:" + b.id : b.place; b.place = placeA == "seat" ? "at:" + a.id : placeA;
        }
        public StyleSheet hudStyle;
        public AudioMixerGroup mixerGroup;

        // ------------------------------------------------------------------ wipe masks (SEAM.md sections 7 and 10)
        [Tooltip("Every wipe on the bench, from the families' parts.json and the zones (part/zone, or part/wipe for a wipe over the whole part). Each has a mask from the start, as found.")]
        public string[] wipeIds = new string[0];
        readonly Dictionary<string, AssemblyWipeMask> wipes = new Dictionary<string, AssemblyWipeMask>();
        /// The coverage mask of a wipe, by id: the zone's marker id (servo.case_lid/dust), or part/wipe where the wipe is
        /// the whole part (materials.sheet_a_plug_1/punch). 0 is as found (the family's as-found set), 1 shows the model's
        /// own set. Every mask starts as found; the Wipe verb cleans it by strokes and an effect "~id" reveals it at once
        /// (a punch mark, tinning, a cured seam). The wipe shader is the integration pass's: it reads
        /// <see cref="AssemblyWipeMask.Texture"/> (or the cells) per id.
        public AssemblyWipeMask Wipe(string zoneId)
        {
            if (string.IsNullOrEmpty(zoneId)) return null;
            if (!wipes.TryGetValue(zoneId, out var m)) wipes[zoneId] = m = new AssemblyWipeMask(zoneId);
            return m;
        }
        public IEnumerable<AssemblyWipeMask> Wipes { get { foreach (var id in wipeIds) Wipe(id); return wipes.Values; } }
        /// Raised whenever a mask changes (a stroke, a rebuild): zone id.
        public event Action<AssemblyWipeMask> WipeChanged;
        internal void NotifyWipe(AssemblyWipeMask m) => WipeChanged?.Invoke(m);

        readonly Dictionary<string, AssemblyPart> parts = new Dictionary<string, AssemblyPart>();
        readonly Dictionary<string, AssemblyMarker> markers = new Dictionary<string, AssemblyMarker>();
        readonly Dictionary<string, AssemblyParam> mechanisms = new Dictionary<string, AssemblyParam>();
        bool indexed;

        public void Index(bool force = false)
        {
            if (indexed && !force) return;
            indexed = true; parts.Clear(); markers.Clear(); mechanisms.Clear();
            foreach (var p in GetComponentsInChildren<AssemblyPart>(true)) if (!string.IsNullOrEmpty(p.id)) parts[p.id] = p;
            foreach (var m in GetComponentsInChildren<AssemblyMarker>(true)) if (!string.IsNullOrEmpty(m.id)) markers[m.id] = m;
            foreach (var m in GetComponentsInChildren<AssemblyParam>(true)) if (!string.IsNullOrEmpty(m.id)) mechanisms[m.id] = m;
        }
        public AssemblyPart Part(string id) { Index(); return parts.TryGetValue(id ?? "", out var p) ? p : null; }
        public AssemblyMarker Marker(string id) { Index(); return markers.TryGetValue(id ?? "", out var m) ? m : null; }
        public AssemblyParam Param(string id) { Index(); return mechanisms.TryGetValue(id ?? "", out var m) ? m : null; }
        public IEnumerable<AssemblyPart> Parts { get { Index(); return parts.Values; } }
        public IEnumerable<AssemblyMarker> Markers { get { Index(); return markers.Values; } }
        public IEnumerable<AssemblyParam> Params { get { Index(); return mechanisms.Values; } }
        /// The first tool that has the id or carries the tag (tool:screwdriver).
        public AssemblyPart Tool(string idOrTag) { var p = Part(idOrTag); if (p) return p; foreach (var t in Parts) if (t.IsTool && t.HasTag(idOrTag)) return t; return null; }

        public Vector3 Up => surface ? surface.up : transform.up;
        public Vector3 SurfacePoint => surface ? surface.position : transform.position;
        /// Where a ray meets the plane `lift` metres above the work surface, kept inside the reach of the bench.
        public Vector3 OnSurface(Ray ray, float lift)
        {
            var plane = new Plane(Up, SurfacePoint + Up * lift);
            Vector3 p = plane.Raycast(ray, out float t) ? ray.GetPoint(t) : SurfacePoint + Up * lift;
            return ClampToReach(p);
        }
        public Vector3 ClampToReach(Vector3 world)
        {
            var frame = surface ? surface : transform;
            var l = frame.InverseTransformPoint(world);
            l.x = Mathf.Clamp(l.x, -reach.x, reach.x); l.z = Mathf.Clamp(l.z, -reach.y, reach.y);
            return frame.TransformPoint(l);
        }
        public float HeightAbove(Vector3 world) => Vector3.Dot(world - SurfacePoint, Up);

        // ------------------------------------------------------------------ the art's axes, and drop areas (22 Nov 2026)
        bool? artAxes;
        /// The installed art works along the empties' +Y (Blender's +Z); the stand-ins along +Z. The screwdriver says which:
        /// its working axis runs from the hand to the blade.
        public bool ArtAxes
        {
            get
            {
                if (artAxes.HasValue) return artAxes.Value;
                var driver = Part("tools.screwdriver"); bool art = false;
                if (driver && driver.tip) { var length = (driver.TipPoint - driver.GrabPoint).normalized; art = Vector3.Dot(driver.tip.up, length) > Vector3.Dot(driver.tip.forward, length); }
                artAxes = art; return art;
            }
        }
        /// Out of the face a mark is on.
        public Vector3 Out(Transform mark) => ArtAxes ? mark.up : mark.forward;

        /// The pointer is over, or beside, the open surface a place is on (the pad, a mat, the tray): the part drops into
        /// place from anywhere there.
        public bool OverDropArea(AssemblyMarker place, Ray ray, Vector3 seatedAt)
        {
            if (!settings || !place) return false;
            var names = settings.snapSurfaces; var frame = surface ? surface : transform; float margin = settings.snapMargin;
            var seat = frame.InverseTransformPoint(seatedAt); Vector3 min = seat, max = seat;
            if (Array.IndexOf(names, place.id) >= 0) margin += place.PickRadius;
            else
            {
                var owner = Part(place.ownerPart); if (!owner || Array.IndexOf(names, owner.id) < 0) return false;
                var box = owner.localBounds;
                for (int i = 0; i < 8; i++)
                {
                    var corner = box.center + Vector3.Scale(box.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    var local = frame.InverseTransformPoint(owner.transform.TransformPoint(corner));
                    min = Vector3.Min(min, local); max = Vector3.Max(max, local);
                }
            }
            // where the pointer meets the surface, and where the part in the hand is seen over it
            bool Over(float height)
            {
                if (!new Plane(Up, SurfacePoint + Up * height).Raycast(ray, out float t)) return false;
                var at = frame.InverseTransformPoint(ray.GetPoint(t));
                return at.x >= min.x - margin && at.x <= max.x + margin && at.z >= min.z - margin && at.z <= max.z + margin;
            }
            return Over(HeightAbove(seatedAt)) || Over(settings.carryLift);
        }

        // ------------------------------------------------------------------ what lies on what (22 Nov 2026)
        AssemblySupport support;
        public AssemblySupport Support => support ??= new AssemblySupport(this);
        void OnDestroy() => support?.Release();

        // ------------------------------------------------------------------ where parts are
        static void Attach(Transform t, Transform parent, Vector3 position, Quaternion rotation)
        {
            if (t.parent != parent) t.SetParent(parent, true);
            t.SetPositionAndRotation(position, rotation);
        }

        /// The seated pose and the approach pose of a part for a target: a place id, or seat / start / clear.
        public bool TargetPose(AssemblyPart p, string target, out Transform parent, out Pose seated, out Pose approach, out AssemblyMarker place)
        {
            parent = null; seated = approach = default; place = null;
            if (!p) return false;
            if (target == "seat") { parent = p.restParent; seated = p.RestWorld; approach = p.ClearWorld; return true; }
            if (target == "start" || target == "clear")
            {
                parent = p.restParent; seated = p.ClearWorld;
                approach = new Pose(seated.position + p.RemovalAxis * .02f, seated.rotation); return true;
            }
            place = Marker(target);
            if (!place || place.kind != AssemblyMarkerKind.Place) { place = null; return false; }
            parent = place.transform; seated = new Pose(place.transform.position, place.transform.rotation); approach = place.ApproachWorld;
            if (p.IsTool && p.tip && p.HasTag("tool:punch") && ArtAxes && Part(place.ownerPart) is AssemblyPart pin && pin.hasClear && pin.OnParent)
            {
                // the punch stands in line with the pin, its point on the pin's end (22 Nov: it lay across it)
                var into = pin.RemovalAxis;
                seated = AssemblyToolPose.At(this, p, place.transform.position, into);
                approach = new Pose(seated.position - into * .03f, seated.rotation);
            }
            if (place.restOn)
            {
                // a point on a surface: the part is set down on it, whatever its own origin is (the gimbal's is 20 mm above its foot)
                var scale = p.transform.lossyScale; var c = seated.rotation * Vector3.Scale(p.localBounds.center, scale);
                var e = Vector3.Scale(p.localBounds.extents, scale); var up = Quaternion.Inverse(seated.rotation) * Up;
                var shift = Up * (Mathf.Abs(up.x * e.x) + Mathf.Abs(up.y * e.y) + Mathf.Abs(up.z * e.z)) - c;
                seated.position += shift; approach.position += shift;
            }
            return true;
        }

        /// Puts a part somewhere at once: a place id, seat, start, clear or gone.
        public void Put(AssemblyPart p, string target)
        {
            if (!p) return;
            if (target == "gone") { p.gameObject.SetActive(false); p.place = "gone"; return; }
            if (!TargetPose(p, target, out var parent, out var seated, out _, out _)) { Debug.LogWarning($"Assembly bench: no place '{target}' for {p.id}"); return; }
            if (!p.gameObject.activeSelf) p.gameObject.SetActive(true);
            Attach(p.transform, parent, seated.position, seated.rotation);
            if (target == "seat") p.transform.localScale = p.restScale;
            p.place = target == "start" ? "clear" : target;
        }
        /// Leaves a part lying free at a world pose.
        public void Drop(AssemblyPart p, Pose pose)
        {
            if (!p) return;
            Attach(p.transform, loose ? loose : transform, pose.position, pose.rotation); p.place = "loose";
        }

        public void ResetAsFound()
        {
            Index(true);
            foreach (var p in parts.Values)
            {
                if (!p.gameObject.activeSelf) p.gameObject.SetActive(true);
                if (p.restParent && p.transform.parent != p.restParent) p.transform.SetParent(p.restParent, true);
                p.transform.localPosition = p.restPosition; p.transform.localRotation = p.restRotation; p.transform.localScale = p.restScale;
                p.place = "seat"; p.modeIndex = 0;
            }
            foreach (var p in parts.Values) if (!string.IsNullOrEmpty(p.homePlace)) Put(p, p.homePlace);
            foreach (var m in mechanisms.Values) m.Set(m.asFound);
            foreach (var lamp in lamps) SetLamp(lamp.part, lamp.asFound);
            foreach (var w in new List<AssemblyWipeMask>(Wipes)) { w.Clear(); NotifyWipe(w); }
        }

        /// Rebuilds the scene from a job: as found, then every finished action's effects in table order.
        public void Rebuild(AssemblyJob job)
        {
            ResetAsFound();
            if (job == null) return;
            foreach (var step in job.Recipe.Steps)
            {
                foreach (var a in step.actions) if (job.ActionDone(step.id, a.key) && !job.ActionReplaced(step.id, a.key)) ApplyAction(a);
                if (job.IsDone(step.id)) foreach (var e in step.effects) ApplyEffect(e);
            }
            foreach (var pending in job.PendingRecoveries) if (pending.fault != null) foreach (var e in pending.fault.effects) ApplyEffect(e);
        }

        /// What an action leaves behind once done: where its part ends up, the mechanism it drove, and its listed effects.
        public void ApplyAction(AssemblyActionDef a)
        {
            if (a == null) return;
            var p = Part(a.part);
            if (a.verb == AssemblyVerbKind.Seat && p && a.mode != "inspect" && !string.IsNullOrEmpty(a.target)) Put(p, a.target);
            // a fastener still on what it was found in goes home or backs out; one started somewhere else (a case screw reused in a plate) stays there
            else if (a.verb == AssemblyVerbKind.Turn && p && p.IsFastener && string.IsNullOrEmpty(a.drive) && a.mode != "reveal" && p.OnParent) Put(p, a.turns < 0 ? "clear" : "seat");
            else if (a.verb == AssemblyVerbKind.Window && a.mode == "strike" && p && p.hasClear && string.IsNullOrEmpty(a.drive) && p.OnParent) Put(p, a.to < .5f ? "seat" : "clear");
            if (!string.IsNullOrEmpty(a.drive) && (a.verb == AssemblyVerbKind.Turn || a.verb == AssemblyVerbKind.Window)) { var m = Param(a.drive); if (m) m.Set(a.to); }
            // a finished wipe is clean (what was missed is in the action's precision, not on the surface)
            if (a.verb == AssemblyVerbKind.Wipe && !string.IsNullOrEmpty(a.target)) { var w = Wipe(a.target); if (w.Coverage < 1) { w.Fill(); NotifyWipe(w); } }
            foreach (var e in a.effects) ApplyEffect(e);
        }

        /// "part>place" (or >seat, >clear, >gone) moves a part; "param=0.5" sets a mechanism or a lamp; "~part/wipe" shows
        /// the model's own surface there ("~part/wipe=0.6" leaves that share of it clean, in patches). An effect may be
        /// tied to one mark of a several-mark action ("@servo.gimbal_race/detent_1:servo.gimbal_grit_1>gone"): it then
        /// happens when that mark is hit, and here like any other.
        public static string EffectBody(string effect) { if (effect != null && effect.StartsWith("@")) { int c = effect.IndexOf(':'); if (c > 0) return effect.Substring(c + 1); } return effect; }
        public bool ApplyEffect(string effect)
        {
            if (string.IsNullOrWhiteSpace(effect)) return false;
            effect = EffectBody(effect);
            if (effect.StartsWith("~"))
            {
                int eq = effect.IndexOf('='); string id = (eq > 0 ? effect.Substring(1, eq - 1) : effect.Substring(1)).Trim(); float share = 1;
                if (eq > 0 && !float.TryParse(effect.Substring(eq + 1).Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out share)) { Debug.LogWarning("Assembly bench: effect not understood: " + effect); return false; }
                if (Array.IndexOf(wipeIds, id) < 0 && !(Marker(id) is AssemblyMarker zone && zone.kind == AssemblyMarkerKind.Zone)) { Debug.LogWarning("Assembly bench: effect names an unknown wipe: " + effect); return false; }
                var w = Wipe(id); w.Set(share); NotifyWipe(w); return true;
            }
            int at = effect.IndexOf('>');
            if (at > 0)
            {
                var p = Part(effect.Substring(0, at).Trim());
                if (!p) { Debug.LogWarning("Assembly bench: effect names an unknown part: " + effect); return false; }
                Put(p, effect.Substring(at + 1).Trim()); return true;
            }
            at = effect.IndexOf('=');
            if (at > 0 && float.TryParse(effect.Substring(at + 1).Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v))
            {
                string id = effect.Substring(0, at).Trim(); var m = Param(id);
                if (m) { m.Set(v); return true; }
                if (SetLamp(id, v)) return true;
                Debug.LogWarning("Assembly bench: effect names an unknown mechanism or lamp: " + effect); return false;
            }
            Debug.LogWarning("Assembly bench: effect not understood: " + effect);
            return false;
        }

        /// The first thing still holding a part in place (a seated fastener or part, or a latch that is still home).
        public bool HeldInPlace(AssemblyPart p, out AssemblyPart blocker, out AssemblyParam latch)
        {
            blocker = null; latch = null;
            if (!p || !p.OnParent) return false;
            foreach (var id in p.heldBy ?? new string[0])
            {
                // a latch is a mechanism (the art may also have a part of the same id riding it): it holds until it is thrown
                var m = Param(id);
                if (m) { if (m.Value < .5f) { latch = m; return true; } continue; }
                var q = Part(id);
                if (q && q.place == "seat" && q.gameObject.activeInHierarchy) { blocker = q; return true; }
            }
            return false;
        }

        /// The mechanism clamping a part where it lies (the closed vise), or null when it is free to be taken.
        public AssemblyParam ClampOn(AssemblyPart p)
        {
            var place = p ? Marker(p.place) : null;
            var m = place && !string.IsNullOrEmpty(place.heldBy) ? Param(place.heldBy) : null;
            return m && m.Value >= place.holdAbove ? m : null;
        }

        // ------------------------------------------------------------------ picking
        /// The nearest part or marker under a ray. Markers win over the part they sit on, and of two things at nearly
        /// the same depth the smaller wins, so a screw can be picked off the plate it is in.
        public AssemblyHit Pick(Ray ray, Predicate<AssemblyHit> filter = null, float pad = .006f)
        {
            Index();
            var best = new AssemblyHit(); float bestScore = float.MaxValue;
            foreach (var m in markers.Values)
            {
                if (!m || m.passive || !m.gameObject.activeInHierarchy) continue;
                float t = m.Raycast(ray); if (t < 0) continue;
                var hit = new AssemblyHit { marker = m, distance = t, point = ray.GetPoint(t) };
                if (filter != null && !filter(hit)) continue;
                // of marks or places that overlap under the pointer, the one the pointer is nearest the middle of
                float score = t - .05f + (m.kind == AssemblyMarkerKind.Mark || m.kind == AssemblyMarkerKind.Place ? AssemblyVerb.DistanceToRay(ray, m.transform.position, out _) * 3 : 0);
                if (score < bestScore) { bestScore = score; best = hit; }
            }
            foreach (var p in parts.Values)
            {
                if (!p || !p.gameObject.activeInHierarchy) continue;
                float t = p.Raycast(ray, pad, out bool byHold); if (t < 0) continue;
                var hit = new AssemblyHit { part = p, distance = t, point = ray.GetPoint(t) };
                if (filter != null && !filter(hit)) continue;
                float size = Vector3.Scale(p.localBounds.size, p.transform.lossyScale).magnitude;
                // a hold point's catch (12 mm round a pin's head, the gap between a pair of cutters' handles) takes a part where its
                // shape is open; it does not take the press off another part whose own surface is under the pointer (the lead beside
                // the pin, the rotor inside the cradle): such a hit counts as 3 cm further away
                float score = t - Mathf.Clamp(.04f - size * .15f, 0, .04f) + (byHold ? .03f : 0);
                if (score < bestScore) { bestScore = score; best = hit; }
            }
            // a part that another seated part holds in place sits behind it: where the pointer is over both, it is the holder
            // that is taken hold of (the housing, not the spring inside it)
            for (int guard = 0; guard < 4 && best.part; guard++)
            {
                if (!HeldInPlace(best.part, out var blocker, out _) || !blocker) break;
                float tb = blocker.Raycast(ray, pad); if (tb < 0) break;
                var over = new AssemblyHit { part = blocker, distance = tb, point = ray.GetPoint(tb) };
                if (filter != null && !filter(over)) break;
                best = over;
            }
            return best;
        }

        /// The contact class of whatever a part would come to rest on at a target.
        public string ContactMaterial(AssemblyPart p, string target)
        {
            if (target == "seat" || target == "start" || target == "clear") { var parent = Part(p ? p.parentId : null); return parent ? parent.material : "steel"; }
            var place = Marker(target);
            return place ? place.material : "rubber";
        }
    }
}
