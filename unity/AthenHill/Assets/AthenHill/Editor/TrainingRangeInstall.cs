using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// Warden training range (1 Oct 2026): installs art/training_range_20261001/layout.json into the saved scene under
    /// "Outer Berms/Warden training range". One time (refuses when the root exists; "reinstall" replaces only this root
    /// while authoring). Builds the earth backstop bank on the real ground, places the kit (props resolve their height
    /// against the Berms ground collider), retires the replaced range clutter (inactive, recorded), adds decals, lights on
    /// the Ward light clock and review cameras. Nothing here is a render-chunk source.
    /// </summary>
    public static class TrainingRangeInstall
    {
        const string ScenePath = TrainingRangePass.ScenePath;
        const string LayoutPath = TrainingRangePass.ArtSrc + "layout.json";
        const string Authored = TrainingRangePass.ArtSrc + "authored-assets.json";
        const string Evidence = TrainingRangePass.Evidence;
        static string PathOf(Transform t) => TrainingRangePass.PathOf(t);

        static MeshCollider ground, bermCol;
        static float GroundY(float x, float z, float fallback = float.NaN) =>
            ground.Raycast(new Ray(new Vector3(x, 60, z), Vector3.down), out var h, 200) ? h.point.y : fallback;

        static IEnumerable<Vector2> Footprint(Vector3 pos, float yaw, float[] size)
        {
            var q = Quaternion.Euler(0, yaw, 0); float hx = size[0] / 2, hz = size[2] / 2;
            foreach (var (u, v) in new[] { (-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz), (0f, 0f) })
            {
                var w = pos + q * new Vector3(u, 0, v); yield return new Vector2(w.x, w.z);
            }
        }

        public static string Install(bool replace)
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var berms = GameObject.Find("Outer Berms").transform;
            var existing = berms.Find(TrainingRangePass.RootName);
            if (existing && !replace) throw new Exception("The training range is already installed; edit the saved objects instead.");
            Directory.CreateDirectory(Evidence + "rollback");
            if (!replace || !File.Exists(Evidence + "rollback/scene-before-training-range.unity"))
                File.Copy(ScenePath, Evidence + "rollback/scene-before-training-range.unity", true);
            if (existing) UnityEngine.Object.DestroyImmediate(existing.gameObject);
            var layout = JObject.Parse(File.ReadAllText(LayoutPath));
            var authored = JObject.Parse(File.ReadAllText(Authored));
            ground = GameObject.Find("Outer Berms/Berms ground").GetComponent<MeshCollider>();
            var record = new Dictionary<string, object>();
            var root = new GameObject(TrainingRangePass.RootName).transform; root.SetParent(berms, false);
            var groups = new Dictionary<string, Transform>();
            Transform Group(string n) { if (!groups.TryGetValue(n, out var g)) { g = new GameObject(n).transform; g.SetParent(root, false); groups[n] = g; } return g; }

            // 1. earth backstop bank (on the real ground) + the revetment and cable runs authored in world space
            var berm = BuildBerm(Group("Backstop"), (JObject)layout["berm"], record);
            bermCol = berm.GetComponent<MeshCollider>();
            foreach (var (asset, group) in new[] { ("TR_Revetment", "Backstop"), ("TR_Cables", "Service apron") })
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(TrainingRangePass.PrefabDir + asset + ".prefab");
                var o = authored[asset]["origin"].Select(x => (float)x).ToArray();
                var g = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                g.transform.SetParent(Group(group), false); g.transform.SetPositionAndRotation(new Vector3(o[0], o[1], o[2]), Quaternion.identity);
                g.name = asset == "TR_Revetment" ? "Backstop revetment" : "Power cables";
            }
            Physics.SyncTransforms();

            // 2. the kit
            var placed = new List<GameObject>(); var ys = new List<float>(); var missing = new List<string>(); int shadowOff = 0;
            var items = layout["placements"].Cast<JObject>().ToList();
            foreach (var it in items)
            {
                var prefabPath = (string)it["prefab"];
                var extra = (JObject)it["extra"];
                GameObject prefab = null;
                foreach (var key in new[] { "number", "variant" })
                    if (!prefab && extra?[key] != null) prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath.Replace(".prefab", "_" + (int)extra[key] + ".prefab"));
                if (!prefab) prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (!prefab) { missing.Add(prefabPath); placed.Add(null); ys.Add(0); continue; }
                var pos = it["pos"].Select(x => (float)x).ToArray(); var e = it["euler"].Select(x => (float)x).ToArray();
                var size = it["size"].Select(x => (float)x).ToArray();
                float dy = (float)it["dy"]; var mode = (string)it["ymode"];
                var p = new Vector3(pos[0], pos[1], pos[2]);
                float y = pos[1];
                switch (mode)
                {
                    case "ground": y = GroundY(p.x, p.z, pos[1] - dy) + dy; break;
                    case "ground-min": y = Footprint(p, e[1], size).Select(f => GroundY(f.x, f.y, pos[1] + .02f - dy)).Min() - .02f + dy; break;
                    case "ground-max": y = Footprint(p, e[1], size).Select(f => GroundY(f.x, f.y, pos[1] - dy)).Max() + dy; break;
                    case "on": { int b = (int)it["stackedOn"]; y = ys[b] + (pos[1] - items[b]["pos"][1].Value<float>()); break; }
                    case "rel": { int b = (int)it["relTo"]; y = ys[b] + dy; break; }
                    case "berm":
                        y = bermCol.Raycast(new Ray(new Vector3(p.x, 60, p.z), Vector3.down), out var hb, 200) ? hb.point.y - .25f : GroundY(p.x, p.z) + dy; break;
                }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                go.transform.SetParent(Group((string)it["group"]), false);
                go.transform.SetPositionAndRotation(new Vector3(p.x, y, p.z), Quaternion.Euler(e[0], e[1], e[2]));
                go.name = (string)it["name"];
                if (!(bool)it["collider"]) foreach (var c in go.GetComponentsInChildren<Collider>(true)) c.enabled = false;
                // hand-sized and flat pieces (tools, cans, sacks, tyres laid flat, litter) cast no shadow: their contact
                // shadow is in the ground AO and decals; it saves a draw per shadow cascade each
                var rs = go.GetComponentsInChildren<Renderer>(true);
                if (rs.Length > 0)
                {
                    var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
                    if (Mathf.Max(bb.size.x, bb.size.z) < .65f || bb.size.y < .25f)
                        foreach (var r in rs) if (r.shadowCastingMode != ShadowCastingMode.Off) { r.shadowCastingMode = ShadowCastingMode.Off; shadowOff++; }
                }
                placed.Add(go); ys.Add(y);
            }
            record["placed"] = placed.Count(g => g); record["missingPrefabs"] = missing; record["shadowsOffSmallPieces"] = shadowOff;

            // 3. retire the replaced clutter (inactive, never deleted)
            Retire(layout, record);
            Physics.SyncTransforms();
            // 4. decals, impact scars, the droid's hit ring
            Decals(Group("Decals"), layout, placed, items, record);
            // 5. lights on the Ward light clock
            Lights(Group("Night lighting"), layout, placed, record);
            // 6. review cameras (scene root, so they survive an A/B toggle of the range)
            AddReviewCameras(scene, layout);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        // ------------------------------------------------------------------ earth bank
        static float Smooth(float a, float b, float x) { float t = Mathf.Clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }

        /// Earth backstop bank: a structured (along-toe s, behind-toe d) grid on the real ground. Behind the revetment the
        /// earth sits level with the wall top (the sandbag cap rests on it), rises to the crest and falls back to the
        /// desert floor; past both wall ends it falls away at the angle of repose with a spill cone round the end post. Rows
        /// in front of the wall face are sunk below ground (hidden by the sleepers). Vertices below the natural ground
        /// (the old mound behind plates 1–2) are left there, so the higher surface shows. Same Berms Ground material
        /// (world-space layers), vertex green = sky access for its baked occlusion, mesh collider.
        static GameObject BuildBerm(Transform parent, JObject b, Dictionary<string, object> record)
        {
            float H = (float)b["wallHeight"], Cr = (float)b["crestRise"], cf = (float)b["crestFrom"], ct = (float)b["crestTo"], bt = (float)b["backTo"];
            float amp = (float)b["noise"], step = (float)b["step"];
            var toe = b["earthToe"].Select(q => (p: new Vector2((float)q["pos"][0], (float)q["pos"][2]), wall: (int)q["wall"])).ToList();
            var wallBase = b["toeWorld"].Select(q => (p: new Vector2((float)q[0], (float)q[2]), y: (float)q[1])).ToList();
            var F = new Vector2(-66.2f, 7.6f);
            // arc length
            var sAt = new List<float> { 0 };
            for (int i = 1; i < toe.Count; i++) sAt.Add(sAt[i - 1] + Vector2.Distance(toe[i - 1].p, toe[i].p));
            float total = sAt[^1];
            Vector2 At(float s, out float wall)
            {
                int i = Mathf.Clamp(sAt.FindLastIndex(v => v <= s), 0, toe.Count - 2);
                float t = Mathf.Clamp01((s - sAt[i]) / (sAt[i + 1] - sAt[i]));
                wall = toe[i].wall == 1 && toe[i + 1].wall == 1 ? 1 : 0;
                return Vector2.Lerp(toe[i].p, toe[i + 1].p, t);
            }
            Vector2 Tangent(float s, float span) { var a = At(Mathf.Max(0, s - span), out _); var c = At(Mathf.Min(total, s + span), out _); return (c - a).normalized; }
            Vector2 Normal(float s, float span)
            {
                var t = Tangent(s, span); var n = new Vector2(-t.y, t.x);
                var p = At(s, out _); if (Vector2.Dot(n, F - p) < 0) n = -n; return n;      // toward the firing line
            }
            // wall base level (smoothed in layout.py) along the wall, by nearest wall toe sample
            float BaseY(Vector2 p)
            {
                float best = float.MaxValue; float y = 0;
                for (int i = 0; i < wallBase.Count - 1; i++)
                {
                    var a = wallBase[i].p; var c = wallBase[i + 1].p; var ab = c - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude); float d = Vector2.Distance(p, a + ab * t);
                    if (d < best) { best = d; y = Mathf.Lerp(wallBase[i].y, wallBase[i + 1].y, t); }
                }
                return y;
            }
            float[] ds = { -3.2f, -2.6f, -2.0f, -1.4f, -.85f, -.4f, -.05f, .1f, .16f, .4f, .66f, 1.0f, 1.4f, 1.8f, 2.1f, 2.4f, 2.8f, 3.2f, 3.6f, 4.1f, 4.7f, 5.4f, 6.1f, 6.9f, 7.7f, 8.4f, 8.8f, 9.4f };
            var P = new List<Vector3>(); var Cn = new List<Color>(); var UV = new List<Vector2>(); var I = new List<int>();
            float sWall0 = sAt[toe.FindIndex(q => q.wall == 1)], sWall1 = sAt[toe.FindLastIndex(q => q.wall == 1)];
            // rows: a regular step plus a 1 cm pair just outside each end post (the wall's sunk front and the earth wing
            // meet in a near-vertical face against the post, not across a whole row inside the first bay)
            const float endPost = .115f;
            var rows = new List<float>();
            for (float s = 0; s < total; s += step) rows.Add(s);
            rows.Add(total);
            rows.AddRange(new[] { sWall0 - endPost - .01f, sWall0 - endPost + .005f, sWall1 + endPost - .005f, sWall1 + endPost + .01f });
            rows = rows.Where(s => s >= 0 && s <= total).Distinct().OrderBy(s => s).ToList();
            rows = rows.Where((s, k) => k == 0 || s - rows[k - 1] > .004f).ToList();
            int ns = rows.Count;
            for (int i = 0; i < ns; i++)
            {
                float s = rows[i];
                var p0 = At(s, out float wall);
                bool onWall = s >= sWall0 - endPost && s <= sWall1 + endPost;
                // the crest is heaped by hand: its height and its front shoulder wander along the bank
                float crestVar = (Mathf.PerlinNoise(s * .16f + 3.3f, 7.1f) - .5f) * .7f + (Mathf.PerlinNoise(s * .55f + 11f, 2.2f) - .5f) * .22f;
                float shoulder = (Mathf.PerlinNoise(s * .23f + 5.5f, 1.7f) - .5f) * .7f;
                // past a wall end the bank falls away along the toe at about the angle of repose, and a half-cone of
                // spilled earth wraps round the end post (also banked against the first bay's foot), so no cut face shows
                const float repose = .72f;
                float outS = s < sWall0 ? sWall0 - s : s > sWall1 ? s - sWall1 : 0;
                var nNear = Normal(s, .8f); var nWide = Normal(s, 5f);
                float baseY = BaseY(p0);
                foreach (var d in ds)
                {
                    var n = Vector2.Lerp(nNear, nWide, Smooth(.7f, 3.5f, d)).normalized;
                    var xz = p0 - n * d;                                      // d > 0 is behind the toe (away from F)
                    float gy = GroundY(xz.x, xz.y, baseY);
                    float h;                                                   // height above the wall base level
                    if (d < .12f) h = float.NegativeInfinity;                  // in front of the sleeper face (or the wing's toe line)
                    else if (d < .66f) h = H - .03f;
                    else if (d < cf + shoulder) h = Mathf.Lerp(H - .03f, Cr + crestVar, Smooth(.66f, cf + shoulder, d));
                    else if (d < ct) h = Cr + crestVar;
                    else h = Mathf.Lerp(Cr + crestVar, 0, Smooth(ct, bt, d));
                    if (!float.IsNegativeInfinity(h)) h -= repose * outS;
                    // spill cones at both wall ends (apex just below the wall top on the toe line at the end post)
                    float cone = float.NegativeInfinity;
                    foreach (var sEnd in new[] { sWall0, sWall1 })
                    {
                        float dist = Mathf.Sqrt((s - sEnd) * (s - sEnd) + (d - .1f) * (d - .1f));
                        bool outside = sEnd == sWall0 ? s < sEnd : s > sEnd;
                        float apex = H - .3f;
                        if (outside || d < .12f) cone = Mathf.Max(cone, apex - repose * 1.15f * dist);
                    }
                    if (cone > 0) h = Mathf.Max(h, cone);
                    float lump = (Mathf.PerlinNoise(xz.x * .45f + 17.3f, xz.y * .45f + 3.1f) - .5f) * 3 * amp * Smooth(.6f, 1.6f, d) * Smooth(bt + .3f, bt - 1.5f, d);
                    lump += (Mathf.PerlinNoise(xz.x * 1.7f + 5f, xz.y * 1.7f + 9f) - .5f) * .05f * Smooth(.66f, 1.2f, d);
                    if (d < .12f) lump = (Mathf.PerlinNoise(xz.x * 1.3f + 2f, xz.y * 1.3f) - .5f) * .12f;
                    float y;
                    if (float.IsNegativeInfinity(h) || h <= 0) y = Mathf.Min(gy, baseY) - .35f;
                    else
                    {
                        y = Mathf.Max(baseY + h + lump, gy - .12f);
                        if (d >= bt || d <= -2.9f) y = gy - .15f;
                    }
                    P.Add(new Vector3(xz.x, y, xz.y)); UV.Add(new Vector2(xz.x, xz.y));
                    float occl = onWall && d < 1.0f ? Mathf.Lerp(.72f, 1f, Smooth(.16f, 1f, d)) : 1f;   // a little less sky in the wall's lee
                    Cn.Add(new Color(1, occl, 1, 1));
                }
            }
            int nd = ds.Length;
            for (int i = 0; i < ns - 1; i++)
                for (int k = 0; k < nd - 1; k++)
                {
                    int a = i * nd + k, c = (i + 1) * nd + k;
                    // skip quads that are entirely hidden (all four corners below ground or sunk)
                    I.AddRange(new[] { a, a + 1, c + 1, a, c + 1, c });
                }
            var mesh = new Mesh { name = "TR_BermEarth", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(P); mesh.SetColors(Cn); mesh.SetUVs(0, UV); mesh.SetTriangles(I, 0);
            // winding: make the normals face up
            mesh.RecalculateNormals();
            if (mesh.normals.Average(n => n.y) < 0) { I.Reverse(); mesh.SetTriangles(I, 0); mesh.RecalculateNormals(); }
            mesh.RecalculateBounds(); mesh.RecalculateTangents();
            var path = TrainingRangePass.StructDir + "TR_BermEarth.asset";
            if (AssetDatabase.LoadAssetAtPath<Mesh>(path)) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject("Backstop earth bank", typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider));
            go.transform.SetParent(parent, false);
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.GetComponent<MeshRenderer>(); mr.sharedMaterial = ground.GetComponent<MeshRenderer>().sharedMaterial;
            mr.shadowCastingMode = ShadowCastingMode.On; mr.receiveShadows = true;
            go.GetComponent<MeshCollider>().sharedMesh = mesh;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
            record["bermTriangles"] = I.Count / 3; record["bermLength"] = total;
            return go;
        }

        // ------------------------------------------------------------------ retire
        static void Retire(JObject layout, Dictionary<string, object> record)
        {
            var off = new List<string>();
            void Off(GameObject g, string why)
            {
                if (!g) return;
                if (!g.activeSelf) { off.Add(PathOf(g.transform) + (why != null ? " " + why : "") + " (already inactive: retired by an earlier install)"); return; }
                Undo.RecordObject(g, "Retire"); g.SetActive(false);
                if (PrefabUtility.IsPartOfPrefabInstance(g)) PrefabUtility.RecordPrefabInstancePropertyModifications(g);
                off.Add(PathOf(g.transform) + (why != null ? " " + why : ""));
            }
            foreach (var p in layout["retire"].Select(x => (string)x).Concat(layout["retireText"].Select(x => (string)x)))
                Off(GameObject.Find(p), null);
            foreach (JObject q in layout["retireScatter"])
            {
                var parent = GameObject.Find((string)q["parent"]); if (!parent) continue;
                var c = q["centre"].Select(x => (float)x).ToArray();
                Transform best = null; float bd = .45f;
                foreach (Transform t in parent.transform)
                {
                    if (t.name != (string)q["name"]) continue;
                    var rs = t.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) continue;
                    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                    float d = Vector2.Distance(new Vector2(b.center.x, b.center.z), new Vector2(c[0], c[1]));
                    if (d < bd) { bd = d; best = t; }
                }
                if (best) Off(best.gameObject, $"@({c[0]:0.0},{c[1]:0.0})");
            }
            record["retired"] = off;
        }

        // ------------------------------------------------------------------ decals
        static Material DecalMat(string kind)
        {
            var name = kind switch { "TR_DecalFiringLine" => "TR_DecalPaintLine", "TR_DecalLaneLine" => "TR_DecalPaintLine", _ => kind };
            var m = AssetDatabase.LoadAssetAtPath<Material>((name.StartsWith("WG_") ? TrainingRangePass.WestGateMats : TrainingRangePass.MatDir) + name + ".mat");
            if (!m) throw new Exception("decal material missing " + name);
            return m;
        }

        static DecalProjector Decal(Transform parent, string name, Material m, Vector3 pos, Quaternion rot, Vector3 size, float pivotZ, float fade, float draw, float a0, float a1)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.SetPositionAndRotation(pos, rot);
            var p = go.AddComponent<DecalProjector>(); p.material = m; p.size = size; p.pivot = new Vector3(0, 0, pivotZ);
            p.fadeFactor = fade; p.drawDistance = draw; p.fadeScale = .8f; p.startAngleFade = a0; p.endAngleFade = a1;
            return p;
        }

        static void Decals(Transform parent, JObject layout, List<GameObject> placed, List<JObject> items, Dictionary<string, object> record)
        {
            int n = 0;
            foreach (JObject d in layout["decals"])
            {
                var pos = d["pos"].Select(x => (float)x).ToArray(); var size = d["size"].Select(x => (float)x).ToArray();
                float gy = GroundY(pos[0], pos[2], pos[1]);
                var fwd = Quaternion.Euler(0, (float)d["yaw"], 0) * Vector3.forward;
                // projected straight down; ground and the tops of low things only
                Decal(parent, ((string)d["kind"]).Replace("TR_Decal", "Ground ") + " " + (++n), DecalMat((string)d["kind"]), new Vector3(pos[0], gy + .3f, pos[2]),
                      Quaternion.LookRotation(Vector3.down, fwd), new Vector3(size[0], size[1], size[2] + .3f), (size[2] + .3f) / 2, (float)d["opacity"], 45, 55, 80);
            }
            // impact scars where the line from the firing position through each plate meets the backstop
            var impacts = new List<object>();
            var F = new Vector3(-66.0f, .2f, 7.5f);                    // cam_checkpoint_plate* (the tutorial's eye at the line)
            foreach (var t in UnityEngine.Object.FindObjectsByType<RangeTarget>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var aim = t.GetComponent<Health>().AimPoint;
                var dir = (aim - F).normalized;
                var hits = Physics.RaycastAll(aim + dir * .9f, dir, 12, ~(1 << 8), QueryTriggerInteraction.Ignore).OrderBy(h => h.distance).ToArray();
                var hit = hits.FirstOrDefault(h => h.collider.transform.IsChildOf(parent.parent));
                if (!hit.collider) continue;
                var face = -new Vector3(dir.x, 0, dir.z).normalized;
                foreach (var (off, s, f) in new[] { (Vector3.zero, 2.4f, .95f), (new Vector3(0, .9f, 0), 1.8f, .7f) })
                {
                    var c = hit.point + off + face * .35f;
                    Decal(parent, "Impact scars " + t.name, DecalMat("TR_DecalImpacts"), c, Quaternion.LookRotation(-face, Vector3.up), new Vector3(s, s * .75f, 1.2f), .6f, f, 40, 40, 70);
                }
                impacts.Add(new { target = t.name, at = new[] { hit.point.x, hit.point.y, hit.point.z }, on = hit.collider.name });
                n += 2;
            }
            record["impactScars"] = impacts;
            // painted hit ring on the stripped worker droid's chest (faces the firing line)
            var worker = placed.FirstOrDefault(g => g && g.name.StartsWith("Worker droid shell"));
            if (worker)
            {
                var b = worker.GetComponentInChildren<Renderer>().bounds;
                var face = worker.transform.forward;
                var c = new Vector3(b.center.x, b.min.y + b.size.y * .58f, b.center.z) + face * 1.0f;
                Decal(parent, "Hit ring (worker droid)", DecalMat("TR_DecalHitZone"), c, Quaternion.LookRotation(-face, Vector3.up), new Vector3(.7f, .7f, 2.0f), 1.0f, 1f, 40, 60, 85);
                n++;
            }
            record["decals"] = n;
        }

        // ------------------------------------------------------------------ lights
        static void Lights(Transform parent, JObject layout, List<GameObject> placed, Dictionary<string, object> record)
        {
            var list = new List<Light>();
            foreach (JObject l in layout["lights"])
            {
                var pos = l["pos"].Select(x => (float)x).ToArray();
                var go = new GameObject((string)l["name"], typeof(Light)); go.transform.SetParent(parent, false);
                go.transform.position = new Vector3(pos[0], pos[1], pos[2]);
                var light = go.GetComponent<Light>();
                light.type = (string)l["type"] == "Spot" ? LightType.Spot : LightType.Point;
                if (l["target"] != null && l["target"].Type != JTokenType.Null)
                {
                    var t = l["target"].Select(x => (float)x).ToArray();
                    go.transform.rotation = Quaternion.LookRotation(new Vector3(t[0], t[1], t[2]) - go.transform.position);
                }
                var c = l["color"].Select(x => (float)x).ToArray();
                light.color = new Color(c[0], c[1], c[2]); light.intensity = (float)l["intensity"]; light.range = (float)l["range"];
                if (light.type == LightType.Spot) { light.spotAngle = (float)l["angle"]; light.innerSpotAngle = light.spotAngle * .55f; }
                light.shadows = (bool)l["shadows"] ? LightShadows.Soft : LightShadows.None;
                list.Add(light);
            }
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
            var root = parent.parent;
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(list).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !l.transform.IsChildOf(root)).Concat(list.Where(l => !l.name.Contains("Range live"))).ToArray();
            var emissive = new[] { "caged_hanging_light", "TR_LampGlow" }.Select(n => AssetDatabase.LoadAssetAtPath<Material>(TrainingRangePass.MatDir + n + ".mat")).Where(m => m).ToArray();
            circuit.emissiveMaterials = circuit.emissiveMaterials.Where(m => m && !emissive.Contains(m)).Concat(emissive).ToArray();
            EditorUtility.SetDirty(circuit);
            record["lights"] = list.Select(l => l.name).ToArray();
        }

        // ------------------------------------------------------------------ review cameras (player height; lookbook names)
        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene, JObject layout)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == TrainingRangePass.CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(TrainingRangePass.CamRootName);
            foreach (JObject c in layout["cameras"])
            {
                var p = c["pos"].Select(x => (float)x).ToArray(); var t = c["target"].Select(x => (float)x).ToArray();
                var go = new GameObject((string)c["name"]); go.transform.SetParent(root.transform, false);
                var pos = new Vector3(p[0], p[1], p[2]);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(new Vector3(t[0], t[1], t[2]) - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = (float)c["fov"]; k.nearClipPlane = .05f; k.farClipPlane = 650;
            }
        }

        /// Adds only the review cameras to the saved scene (matched "before" captures).
        public static string CamerasOnly()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            AddReviewCameras(scene, JObject.Parse(File.ReadAllText(LayoutPath)));
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "review cameras: " + scene.GetRootGameObjects().First(g => g.name == TrainingRangePass.CamRootName).transform.childCount;
        }

        /// Editor capture of every review camera plus the checkpoint range cameras (nothing saved).
        /// At most six cameras per Unity run (1 Oct VRAM rule): pass the batch as "cam_a+cam_b+..." (lookbook names).
        public static string CaptureViews(string outDir, string only = null)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var cams = new List<Camera>();
            var camRoot = scene.GetRootGameObjects().FirstOrDefault(g => g.name == TrainingRangePass.CamRootName);
            if (camRoot) cams.AddRange(camRoot.GetComponentsInChildren<Camera>(true));
            foreach (var n in new[] { "cam_checkpoint_range", "cam_checkpoint_target_close", "cam_westgate_range", "cam_berms_overview" })
            {
                var c = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).FirstOrDefault(x => x.name == n);
                if (c) cams.Add(c);
            }
            if (!string.IsNullOrEmpty(only)) { var want = only.Split('+'); cams = cams.Where(c => want.Contains(c.name)).ToList(); }
            if (cams.Count > 6) throw new Exception($"{cams.Count} cameras in one run; capture at most 6 per Unity run (capture:<dir>:cam_a+cam_b...)");
            var views = cams.Select(c => (c.name, c.transform.position, c.transform.position + c.transform.forward * 5f, c.fieldOfView)).ToList();
            return string.Join(",", StreetDressingPass.Capture(outDir, views));
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var layout = JObject.Parse(File.ReadAllText(LayoutPath));
            var r = new Dictionary<string, object>();
            var root = GameObject.Find("Outer Berms")?.transform.Find(TrainingRangePass.RootName);
            r["installed"] = root != null;
            if (root)
            {
                r["active"] = root.gameObject.activeInHierarchy;
                var inst = root.GetComponentsInChildren<Transform>(true).Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
                r["prefabInstances"] = inst.Length;
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(m => !m));
                long lod0 = 0, all = 0;
                foreach (var rr in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (!rr.enabled || rr is not MeshRenderer || !rr.TryGetComponent<MeshFilter>(out var mf) || !mf.sharedMesh) continue;
                    long t = 0; for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) t += mf.sharedMesh.GetIndexCount(s) / 3;
                    all += t;
                    var g = rr.GetComponentInParent<LODGroup>();
                    if (!g || g.GetLODs()[0].renderers.Contains(rr)) lod0 += t;
                }
                r["lod0Triangles"] = lod0; r["allLodTriangles"] = all;
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Count(c => c.enabled);
                r["decals"] = root.GetComponentsInChildren<DecalProjector>(true).Length;
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>();
                r["lightsOnClock"] = root.GetComponentsInChildren<Light>(true).Count(l => circuit.practicalLights.Contains(l));
                r["shadowCasters"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.enabled && x.shadowCastingMode != ShadowCastingMode.Off);
            }
            var stillOn = new List<string>();
            foreach (var p in layout["retire"].Select(x => (string)x).Concat(layout["retireText"].Select(x => (string)x)))
            { var g = GameObject.Find(p); if (g && g.activeSelf) stillOn.Add(p); }
            r["retiredStillActive"] = stillOn;
            // gameplay untouched
            var tut = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            r["tutorialTargets"] = tut ? tut.targets.Count(t => t && t.gameObject.activeInHierarchy && t.GetComponent<Health>()) : 0;
            r["tutorialLocker"] = tut && tut.locker; r["firstContact"] = tut && tut.firstContact; r["depot"] = tut && tut.depot;
            r["resetStation"] = UnityEngine.Object.FindObjectsByType<RangeResetStation>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Length;
            r["npcs"] = UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Where(n => n.transform.position.x < -55).Select(n => n.name).ToArray();
            var lm = scene.GetRootGameObjects().First(g => g.name == "Landmarks").transform;
            r["landmarks"] = new[] { "checkpoint_firingline", "checkpoint_range_reset", "checkpoint_locker", "checkpoint_board", "checkpoint_ossa", "checkpoint_rell", "checkpoint_road", "checkpoint_fabricator" }
                .ToDictionary(n => n, n => lm.Find(n) ? new[] { lm.Find(n).position.x, lm.Find(n).position.y, lm.Find(n).position.z } : null);
            // nothing new blocks the tutorial's shots: the eye at the firing line sees every plate's aim point
            Physics.SyncTransforms();
            var eye = new Vector3(-66.0f, .2f, 7.5f); var blocked = new List<string>();
            if (tut) foreach (var t in tut.targets)
                {
                    var aim = t.GetComponent<Health>().AimPoint;
                    if (Physics.Linecast(eye, aim, out var h, ~(1 << 8), QueryTriggerInteraction.Ignore) && h.collider.GetComponentInParent<Health>() != t.GetComponent<Health>())
                        blocked.Add(t.name + " by " + PathOf(h.collider.transform));
                }
            r["shotsBlocked"] = blocked;
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == TrainingRangePass.CamRootName)?.transform.childCount ?? 0;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }
    }
}
