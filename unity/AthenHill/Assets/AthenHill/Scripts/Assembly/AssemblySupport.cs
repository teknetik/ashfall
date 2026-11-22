using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
    /// What is under a thing on the bench (22 Nov 2026, Carl: small scrap got hidden under anything thicker than it).
    /// A height map of what is drawn, seen from above, made from the meshes' own triangles when something is put down.
    /// A part comes to rest on top of a surface (mat, tray floor, open canvas). Where it would lie across a rim, under
    /// something or on another part, it slides to the nearest clear spot beside it.
    public sealed class AssemblySupport
    {
        const float Cell = .005f, Margin = .004f, Level = .007f, SurfaceHeight = .04f, SearchRadius = .4f, BackLimit = -.14f, FrontLimit = .585f;

        sealed class HeightMap
        {
            public readonly float x0, z0; public readonly int w, h;
            public readonly float[] top; public readonly bool[] surface;
            public HeightMap(Rect area)
            {
                x0 = area.xMin; z0 = area.yMin;
                w = Mathf.Max(1, Mathf.CeilToInt(area.width / Cell)); h = Mathf.Max(1, Mathf.CeilToInt(area.height / Cell));
                top = new float[w * h]; surface = new bool[w * h];
                for (int i = 0; i < top.Length; i++) { top[i] = float.NegativeInfinity; surface[i] = true; }
            }
            void Mark(int x, int z, float y, bool isSurface)
            {
                if (x < 0 || z < 0 || x >= w || z >= h) return;
                int i = z * w + x; if (y <= top[i]) return;
                top[i] = y; surface[i] = isSurface;
            }
            public void Triangle(Vector3 a, Vector3 b, Vector3 c, bool isSurface)
            {
                float ax = (a.x - x0) / Cell, az = (a.z - z0) / Cell, bx = (b.x - x0) / Cell, bz = (b.z - z0) / Cell, cx = (c.x - x0) / Cell, cz = (c.z - z0) / Cell;
                float minX = Mathf.Min(ax, Mathf.Min(bx, cx)), maxX = Mathf.Max(ax, Mathf.Max(bx, cx)), minZ = Mathf.Min(az, Mathf.Min(bz, cz)), maxZ = Mathf.Max(az, Mathf.Max(bz, cz));
                if (maxX < 0 || maxZ < 0 || minX >= w || minZ >= h) return;
                // the corners too: a pin or a wire is thinner than a cell
                Mark(Mathf.FloorToInt(ax), Mathf.FloorToInt(az), a.y, isSurface); Mark(Mathf.FloorToInt(bx), Mathf.FloorToInt(bz), b.y, isSurface); Mark(Mathf.FloorToInt(cx), Mathf.FloorToInt(cz), c.y, isSurface);
                float d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz); if (Mathf.Abs(d) < 1e-7f) return;
                for (int z = Mathf.Max(0, Mathf.CeilToInt(minZ - .5f)); z < h && z + .5f <= maxZ; z++)
                    for (int x = Mathf.Max(0, Mathf.CeilToInt(minX - .5f)); x < w && x + .5f <= maxX; x++)
                    {
                        float px = x + .5f - cx, pz = z + .5f - cz;
                        float u = ((bz - cz) * px + (cx - bx) * pz) / d, v = ((cz - az) * px + (ax - cx) * pz) / d;
                        if (u < 0 || v < 0 || u + v > 1) continue;
                        Mark(x, z, u * a.y + v * b.y + (1 - u - v) * c.y, isSurface);
                    }
            }
            /// The highest thing in a window, and whether the whole window is one clear, level surface.
            public float Window(Rect r, float floor, out bool clear)
            {
                float high = float.NegativeInfinity, low = float.PositiveInfinity; clear = true;
                int xa = Mathf.Max(0, Mathf.FloorToInt((r.xMin - x0) / Cell)), xb = Mathf.Min(w - 1, Mathf.FloorToInt((r.xMax - x0) / Cell));
                int za = Mathf.Max(0, Mathf.FloorToInt((r.yMin - z0) / Cell)), zb = Mathf.Min(h - 1, Mathf.FloorToInt((r.yMax - z0) / Cell));
                for (int z = za; z <= zb; z++)
                    for (int x = xa; x <= xb; x++)
                    {
                        int i = z * w + x; float y = Mathf.Max(floor, top[i]);
                        if (!surface[i] || y > SurfaceHeight) clear = false;
                        high = Mathf.Max(high, y); low = Mathf.Min(low, y);
                    }
                if (float.IsNegativeInfinity(high)) return floor;
                clear &= high - low <= Level;
                return high;
            }
        }

        readonly AssemblyBench bench;
        readonly Dictionary<Mesh, (Vector3[] vertices, int[] triangles)> shapes = new Dictionary<Mesh, (Vector3[], int[])>();
        Mesh baked;
        public AssemblySupport(AssemblyBench bench) { this.bench = bench; }
        Transform Frame => bench.surface ? bench.surface : bench.transform;

        float Floor
        {
            get
            {
                // the bare bench top is under the rubber's edge
                var rubber = bench.Part("fixtures.worksurface"); if (!rubber) return 0;
                var b = rubber.localBounds;
                return Mathf.Min(0, bench.HeightAbove(rubber.transform.TransformPoint(b.center - Vector3.up * b.extents.y)));
            }
        }

        static bool IsSurface(AssemblyPart p) => p.IsFixture && !(p.parentId ?? "").StartsWith("tools.") || p.id == "tools.roll";
        static bool InHand(AssemblyPart p)
        {
            for (var t = p.transform; t; t = t.parent) if (t.TryGetComponent<AssemblyPart>(out var q) && q.place == "held") return true;
            return false;
        }
        static bool PartOf(AssemblyPart p, List<AssemblyPart> roots)
        {
            foreach (var r in roots) if (p.transform.IsChildOf(r.transform)) return true;
            return false;
        }

        /// Every drawn triangle of a part's own renderers, in the surface's frame, handed to `take`.
        void Triangles(AssemblyPart p, Rect? area, System.Action<Vector3, Vector3, Vector3> take)
        {
            if (!p || p.Gone || !p.gameObject.activeInHierarchy) return;
            var toFrame = Frame.worldToLocalMatrix;
            foreach (var r in p.renderers)
            {
                if (!r || !r.enabled || !r.gameObject.activeInHierarchy) continue;
                var skin = r as SkinnedMeshRenderer; Vector3[] v; int[] t;
                if (skin)
                {
                    // the toolkit as it lies now: rolled, or open
                    if (!skin.sharedMesh) continue;
                    if (!baked) baked = new Mesh { hideFlags = HideFlags.HideAndDontSave };
                    skin.BakeMesh(baked, true); v = baked.vertices; t = baked.triangles;
                }
                else
                {
                    if (area.HasValue && !Meets(r.bounds, area.Value, toFrame)) continue;
                    var filter = r.GetComponent<MeshFilter>(); var mesh = filter ? filter.sharedMesh : null;
                    if (!mesh || !mesh.isReadable) continue;
                    if (!shapes.TryGetValue(mesh, out var shape)) shapes[mesh] = shape = (mesh.vertices, mesh.triangles);
                    v = shape.vertices; t = shape.triangles;
                }
                var m = toFrame * r.transform.localToWorldMatrix; var at = new Vector3[v.Length];
                for (int i = 0; i < v.Length; i++) at[i] = m.MultiplyPoint3x4(v[i]);
                for (int i = 0; i + 2 < t.Length; i += 3) take(at[t[i]], at[t[i + 1]], at[t[i + 2]]);
            }
        }
        static bool Meets(Bounds world, Rect area, Matrix4x4 toFrame)
        {
            var c = toFrame.MultiplyPoint3x4(world.center); float reach = world.extents.magnitude;
            return c.x + reach >= area.xMin && c.x - reach <= area.xMax && c.z + reach >= area.yMin && c.z - reach <= area.yMax;
        }

        HeightMap Others(Rect area, List<AssemblyPart> without)
        {
            var map = new HeightMap(area);
            foreach (var p in bench.Parts)
            {
                if (!p || PartOf(p, without) || InHand(p)) continue;
                bool surface = IsSurface(p);
                Triangles(p, area, (a, b, c) => map.Triangle(a, b, c, surface));
            }
            return map;
        }

        /// A part and what rides on it.
        bool Box(AssemblyPart part, out Vector3 min, out Vector3 max)
        {
            Vector3 lo = Vector3.positiveInfinity, hi = Vector3.negativeInfinity;
            foreach (var p in bench.Parts)
            {
                if (!p || !p.transform.IsChildOf(part.transform)) continue;
                Triangles(p, null, (a, b, c) => { lo = Vector3.Min(lo, Vector3.Min(a, Vector3.Min(b, c))); hi = Vector3.Max(hi, Vector3.Max(a, Vector3.Max(b, c))); });
            }
            if (float.IsInfinity(lo.x))
            {
                var b = part.localBounds;
                for (int i = 0; i < 8; i++)
                {
                    var q = Frame.InverseTransformPoint(part.transform.TransformPoint(b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))));
                    lo = Vector3.Min(lo, q); hi = Vector3.Max(hi, q);
                }
            }
            min = lo; max = hi; return true;
        }

        /// Moves a part, as it is turned now, to rest in sight where it is or at the nearest clear spot.
        public void Rest(AssemblyPart part)
        {
            Box(part, out var min, out var max);
            var foot = Rect.MinMaxRect(min.x - Margin, min.z - Margin, max.x + Margin, max.z + Margin);
            var area = Rect.MinMaxRect(foot.xMin - SearchRadius, foot.yMin - SearchRadius, foot.xMax + SearchRadius, foot.yMax + SearchRadius);
            var map = Others(area, new List<AssemblyPart> { part }); float floor = Floor;
            float height = map.Window(foot, floor, out bool clear); var shift = Vector2.zero;
            for (float r = .01f; r <= SearchRadius && !clear; r += .01f)
            {
                int spots = Mathf.Max(8, Mathf.CeilToInt(2 * Mathf.PI * r / .02f));
                for (int i = 0; i < spots; i++)
                {
                    float a = i * 2 * Mathf.PI / spots; var d = new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r;
                    if (min.x + d.x < -bench.reach.x || max.x + d.x > bench.reach.x || min.z + d.y < BackLimit || max.z + d.y > FrontLimit) continue;
                    float at = map.Window(new Rect(foot.position + d, foot.size), floor, out bool free);
                    if (!free) continue;
                    clear = true; height = at; shift = d; break;
                }
            }
            part.transform.position += Frame.TransformVector(new Vector3(shift.x, height + .0005f - min.y, shift.y));
        }

        /// The share of a part, seen from above, that has something else over it.
        public float Covered(AssemblyPart part) => Covered(part, new List<AssemblyPart> { part });
        float Covered(AssemblyPart part, List<AssemblyPart> without)
        {
            Box(part, out var min, out var max);
            var area = Rect.MinMaxRect(min.x, min.z, max.x + Cell, max.z + Cell);
            var own = new HeightMap(area);
            foreach (var p in bench.Parts) if (p && p.transform.IsChildOf(part.transform)) Triangles(p, null, (a, b, c) => own.Triangle(a, b, c, true));
            var others = Others(area, without); int seen = 0, under = 0;
            for (int i = 0; i < own.top.Length; i++)
            {
                if (float.IsNegativeInfinity(own.top[i])) continue;
                seen++; if (others.top[i] > own.top[i] + .0001f) under++;
            }
            return seen == 0 ? 0 : (float)under / seen;
        }

        /// Anything lying free that has just been covered (the roll opened over it, a part set on it) comes back out on top.
        public void Uncover()
        {
            var lying = new List<AssemblyPart>();
            foreach (var p in bench.Parts)
                if (p && !p.IsTool && !p.IsFixture && p.id != "tools.roll" && p.gameObject.activeInHierarchy && p.place != null && (p.place == "loose" || p.place.StartsWith("place.entry.")))
                    lying.Add(p);
            foreach (var p in lying)
            {
                // (things lying free that overlap as they were found, two sheets in a pile, do not count as covering each other)
                if (Covered(p, lying) <= .3f) continue;
                Rest(p);
                bench.Drop(p, new Pose(p.transform.position, p.transform.rotation));
            }
        }

        public void Release()
        {
            if (!baked) return;
            if (Application.isPlaying) Object.Destroy(baked); else Object.DestroyImmediate(baked);
        }
    }
}
