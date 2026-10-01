using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
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
    /// 1 October 2026: Berms road ground to the V2 terrain standard (art-direction review item 12). The playable Outer
    /// Berms floor (`Outer Berms/Berms ground`, road and range) gets the basin's layered V2 look plus the West Gate splat
    /// (road gravel, sand drifts, crust, packed ruts), and the road from the checkpoint to the depot gets edge stones.
    /// The ground mesh and its collider are never changed. Sources: art/berms_road_20261001 (README for the run order).
    /// Batch: -executeMethod AthenHill.Editor.BermsRoadPass.RunBatch --steps survey|capture:&lt;dir&gt;:&lt;cam+cam..&gt;|...
    /// </summary>
    public static class BermsRoadPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string ArtSrc = "../../art/berms_road_20261001/";
        public const string Evidence = "../evidence/berms-road/20261001/";
        public const string GroundPath = "Outer Berms/Berms ground";
        const string GroundMat = "Assets/AthenHill/Art/WestGate/Ground/BermsGround.mat";

        // survey window (world metres): the Berms ground footprint (x -104..-60, z -54..48) plus a margin
        const float X0 = -110f, X1 = -54f, Z0 = -60f, Z1 = 54f;
        static bool InWindow(Bounds b) => b.max.x >= X0 && b.min.x <= X1 && b.max.z >= Z0 && b.min.z <= Z1;
        static bool InWindow(Vector3 p) => p.x >= X0 && p.x <= X1 && p.z >= Z0 && p.z <= Z1;

        public static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };

        // ------------------------------------------------------------------ survey (read-only, -nographics)
        /// Ground mesh (world vertices with colours and normals), a 0.5 m height grid (Berms ground collider and the highest
        /// non-trigger surface), colliders, gameplay markers, renderers, decals, lights, cameras, the ground material and the
        /// footstep map, written to art/berms_road_20261001/survey.json. Also refreshes the whole-scene audit. Never saves.
        public static string Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToList();
            var groundT = all.FirstOrDefault(t => PathOf(t) == GroundPath);
            if (!groundT) throw new Exception(GroundPath + " not found");
            var groundCol = groundT.GetComponent<MeshCollider>();
            var groundMf = groundT.GetComponent<MeshFilter>();
            var groundR = groundT.GetComponent<MeshRenderer>();
            var mesh = groundMf.sharedMesh;
            var verts = mesh.vertices; var cols = mesh.colors; var nrm = mesh.normals;
            var gv = new List<float[]>(verts.Length);
            for (int i = 0; i < verts.Length; i++)
            {
                var w = groundT.TransformPoint(verts[i]); var n = groundT.TransformDirection(nrm[i]);
                var c = cols.Length == verts.Length ? cols[i] : Color.clear;
                gv.Add(new[] { (float)Math.Round(w.x, 3), (float)Math.Round(w.y, 4), (float)Math.Round(w.z, 3), (float)Math.Round(c.r, 3), (float)Math.Round(c.g, 3), (float)Math.Round(c.b, 3), (float)Math.Round(n.x, 4), (float)Math.Round(n.y, 4), (float)Math.Round(n.z, 4) });
            }
            var ground = new
            {
                path = GroundPath,
                position = V(groundT.position), rotation = V(groundT.eulerAngles), scale = V(groundT.lossyScale),
                mesh = mesh.name, meshAsset = AssetDatabase.GetAssetPath(mesh),
                colliderMesh = groundCol && groundCol.sharedMesh ? groundCol.sharedMesh.name : null,
                colliderMeshAsset = groundCol && groundCol.sharedMesh ? AssetDatabase.GetAssetPath(groundCol.sharedMesh) : null,
                colliderSameMesh = groundCol && groundCol.sharedMesh == mesh,
                vertexCount = verts.Length, triangles = mesh.triangles.Length / 3, hasColors = cols.Length == verts.Length,
                indexFormat = mesh.indexFormat.ToString(),
                bounds = new { min = V(groundR.bounds.min), max = V(groundR.bounds.max) },
                material = groundR.sharedMaterials.Select(m => m ? AssetDatabase.GetAssetPath(m) : null).ToArray(),
                shadows = groundR.shadowCastingMode.ToString(), receiveShadows = groundR.receiveShadows,
                isStatic = groundT.gameObject.isStatic, staticFlags = GameObjectUtility.GetStaticEditorFlags(groundT.gameObject).ToString(),
                layer = groundT.gameObject.layer,
                vertices = gv,
            };
            // other users of the ground material (the range's earth bank)
            var gmat = AssetDatabase.LoadAssetAtPath<Material>(GroundMat);
            var users = all.Select(t => t.GetComponent<Renderer>()).Where(r => r && r.sharedMaterials.Contains(gmat)).Select(r =>
            {
                var m = r.GetComponent<MeshFilter>() ? r.GetComponent<MeshFilter>().sharedMesh : null;
                return new { path = PathOf(r.transform), active = r.gameObject.activeInHierarchy, mesh = m ? m.name : null, meshAsset = m ? AssetDatabase.GetAssetPath(m) : null,
                             vertices = m ? m.vertexCount : 0, hasColors = m && m.colors.Length == m.vertexCount, hasUV = m && m.uv.Length == m.vertexCount, min = V(r.bounds.min), max = V(r.bounds.max) };
            }).ToArray();

            var grid = new List<float[]>();
            const float step = .5f;
            for (float z = -54f; z <= 48f + 1e-3f; z += step)
                for (float x = -104f; x <= -60f + 1e-3f; x += step)
                {
                    float gy = float.NaN, top = float.NaN;
                    if (groundCol.Raycast(new Ray(new Vector3(x, 80, z), Vector3.down), out var gh, 200)) gy = gh.point.y;
                    var hits = Physics.RaycastAll(new Vector3(x, 80, z), Vector3.down, 200, ~(1 << 8), QueryTriggerInteraction.Ignore);
                    if (hits.Length > 0) top = hits.Max(q => q.point.y);
                    grid.Add(new[] { x, z, (float)Math.Round(gy, 3), (float)Math.Round(top, 3) });
                }
            var colliders = new List<object>();
            foreach (var c in all.SelectMany(t => t.GetComponents<Collider>()))
            {
                if (!c.gameObject.activeInHierarchy || !c.enabled || c == groundCol) continue;
                var b = c.bounds; if (!InWindow(b)) continue;
                object obb = null;
                if (c is BoxCollider bc)
                {
                    var s = Vector3.Scale(bc.size, c.transform.lossyScale);
                    obb = new { center = V(c.transform.TransformPoint(bc.center)), size = V(new Vector3(Mathf.Abs(s.x), Mathf.Abs(s.y), Mathf.Abs(s.z))), yaw = c.transform.eulerAngles.y, pitch = c.transform.eulerAngles.x, roll = c.transform.eulerAngles.z };
                }
                colliders.Add(new { path = PathOf(c.transform), type = c.GetType().Name, trigger = c.isTrigger, layer = c.gameObject.layer, min = V(b.min), max = V(b.max), obb });
            }
            var markers = new List<object>();
            void Mark(string kind, Transform t, object extra = null) { if (t && InWindow(t.position)) markers.Add(new { kind, path = PathOf(t), pos = V(t.position), yaw = t.eulerAngles.y, active = t.gameObject.activeInHierarchy, extra }); }
            foreach (var n in UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("npc", n.transform);
            foreach (var w in UnityEngine.Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("interactable", w.transform, new { w.prompt, w.range });
            foreach (var r in UnityEngine.Object.FindObjectsByType<RangeTarget>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("target", r.transform);
            foreach (var e in UnityEngine.Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                Mark("encounter", e.transform, new { e.displayName });
                foreach (var s in e.spawns) if (s.point) Mark("spawn", s.point, new { prefab = s.prefab ? s.prefab.name : null, aggro = s.prefab ? s.prefab.aggroRadius : 0, leash = s.prefab ? s.prefab.leashRadius : 0, wander = s.prefab ? s.prefab.wanderRadius : 0 });
            }
            foreach (var w in UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (w.waypoints != null) foreach (var p in w.waypoints) Mark("route", p, new { walker = w.name });
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks) foreach (Transform t in landmarks.transform) Mark("landmark", t);
            foreach (var t in all.Where(t => t.name.Contains("Respawn") || t.name.Contains("abricator") || t.name.StartsWith("Salvage node") || t.name.Contains("cache") || t.name.Contains("Cache")))
                Mark("misc", t);
            var lights = all.Select(t => t.GetComponent<Light>()).Where(l => l && InWindow(l.transform.position))
                .Select(l => new { path = PathOf(l.transform), pos = V(l.transform.position), type = l.type.ToString(), l.range, l.intensity, shadows = l.shadows.ToString(), active = l.gameObject.activeInHierarchy }).ToArray();
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c && InWindow(c.transform.position))
                .Select(c => new { name = c.name, path = PathOf(c.transform), pos = V(c.transform.position), fwd = V(c.transform.forward), c.fieldOfView }).ToArray();
            var decals = all.Select(t => t.GetComponent<DecalProjector>()).Where(d => d && InWindow(d.transform.position))
                .Select(d => new { path = PathOf(d.transform), active = d.gameObject.activeInHierarchy, pos = V(d.transform.position), size = V(d.size), rot = V(d.transform.eulerAngles), mat = d.material ? d.material.name : null }).ToArray();
            var renderers = new List<object>();
            foreach (var r in all.Select(t => t.GetComponent<Renderer>()).Where(r => r && InWindow(r.bounds)))
            {
                var m = r is SkinnedMeshRenderer s ? s.sharedMesh : r.TryGetComponent<MeshFilter>(out var mf) ? mf.sharedMesh : null;
                long tris = 0; if (m) for (int k = 0; k < m.subMeshCount; k++) tris += (long)m.GetIndexCount(k) / 3;
                var pr = PrefabUtility.GetNearestPrefabInstanceRoot(r.gameObject);
                renderers.Add(new { path = PathOf(r.transform), active = r.gameObject.activeInHierarchy, r.enabled, tris, min = V(r.bounds.min), max = V(r.bounds.max),
                                    mats = r.sharedMaterials.Select(x => x ? x.name : null).ToArray(), shadows = r.shadowCastingMode.ToString(),
                                    prefab = pr ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(pr) : null });
            }
            var berms = scene.GetRootGameObjects().First(g => g.name == "Outer Berms").transform;
            var groups = berms.Cast<Transform>().Select(t => new { name = t.name, active = t.gameObject.activeSelf, children = t.childCount,
                                                                   renderers = t.GetComponentsInChildren<Renderer>(true).Length }).ToArray();
            var fa = UnityEngine.Object.FindAnyObjectByType<FootstepAudio>();
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            var result = new
            {
                scene = ScenePath, utc = DateTime.UtcNow.ToString("O"), window = new[] { X0, X1, Z0, Z1 }, gridStep = step,
                ground, materialUsers = users, material = DumpMaterial(gmat),
                footsteps = fa ? new { rect = new[] { fa.bermsRect.x, fa.bermsRect.y, fa.bermsRect.z, fa.bermsRect.w }, fa.bermsWidth, fa.bermsHeight, cells = fa.bermsSurfaces.Length, path = PathOf(fa.transform) } : null,
                bermsGroups = groups,
                chunkSourceRoots = chunks ? chunks.sourceRoots.Where(t => t).Select(PathOf).ToArray() : null,
                grid, colliders, markers, lights, cameras = cams, decals, renderers,
                roots = scene.GetRootGameObjects().Select(g => g.name).ToArray(),
            };
            Directory.CreateDirectory(ArtSrc);
            File.WriteAllText(ArtSrc + "survey.json", JsonConvert.SerializeObject(result));
            // refresh the whole-scene audit (StreetDressingAudit.Dump is private; same tool, same output format)
            var dump = typeof(StreetDressingAudit).GetMethod("Dump", BindingFlags.NonPublic | BindingFlags.Static);
            Directory.CreateDirectory(Evidence);
            dump.Invoke(null, new object[] { Evidence + "audit.json" });
            return $"survey: {gv.Count} ground vertices, {grid.Count} grid samples, {colliders.Count} colliders, {markers.Count} markers, {renderers.Count} renderers, {decals.Length} decals; audit refreshed";
        }

        public static object DumpMaterial(Material m)
        {
            if (!m) return null;
            var sh = m.shader;
            var props = new Dictionary<string, object>();
            for (int i = 0; i < sh.GetPropertyCount(); i++)
            {
                var n = sh.GetPropertyName(i);
                switch (sh.GetPropertyType(i))
                {
                    case ShaderPropertyType.Float: case ShaderPropertyType.Range: props[n] = m.GetFloat(n); break;
                    case ShaderPropertyType.Color: { var c = m.GetColor(n); props[n] = new[] { c.r, c.g, c.b, c.a }; break; }
                    case ShaderPropertyType.Vector: { var v = m.GetVector(n); props[n] = new[] { v.x, v.y, v.z, v.w }; break; }
                    case ShaderPropertyType.Texture: { var t = m.GetTexture(n); props[n] = t ? AssetDatabase.GetAssetPath(t) : null; break; }
                    default: props[n] = "?"; break;
                }
            }
            return new { name = m.name, path = AssetDatabase.GetAssetPath(m), shader = sh.name, keywords = m.shaderKeywords, props };
        }

        // ------------------------------------------------------------------ build: importers + material (-nographics)
        const string GroundDir = "Assets/AthenHill/Art/BermsRoad/Ground/";
        const string PrefabDir = "Assets/AthenHill/Prefabs/WestGate/";
        public const string StonesRootName = "Berms road edge stones";
        public const string CamRootName = "Berms road review cameras";
        static JObject Json(string name) => JObject.Parse(File.ReadAllText(ArtSrc + name));
        static string MatPath => (string)Json("material.json")["path"];

        public static string BuildAssets()
        {
            AssetDatabase.Refresh();
            var log = new List<string>();
            foreach (var (path, srgb) in new[] { (GroundDir + "BermsRoadLayers_AH.png", true), (GroundDir + "BermsRoadLayers_NRA.png", false) })
            {
                var ti = (TextureImporter)AssetImporter.GetAtPath(path) ?? throw new Exception("missing " + path);
                var st = new TextureImporterSettings(); ti.ReadTextureSettings(st);
                st.textureShape = TextureImporterShape.Texture2DArray; st.flipbookRows = 5; st.flipbookColumns = 1;
                ti.SetTextureSettings(st);
                ti.sRGBTexture = srgb; ti.mipmapEnabled = true; ti.streamingMipmaps = true; ti.isReadable = false;
                ti.wrapMode = TextureWrapMode.Repeat; ti.filterMode = FilterMode.Trilinear; ti.anisoLevel = 8;
                ti.maxTextureSize = 16384; ti.textureCompression = TextureImporterCompression.CompressedHQ;
                var ps = ti.GetPlatformTextureSettings("Standalone"); ps.overridden = true; ps.maxTextureSize = 16384; ps.textureCompression = TextureImporterCompression.CompressedHQ; ps.format = TextureImporterFormat.Automatic;
                ti.SetPlatformTextureSettings(ps);
                ti.SaveAndReimport();
                var arr = AssetDatabase.LoadAssetAtPath<Texture2DArray>(path) ?? throw new Exception("not a Texture2DArray: " + path);
                log.Add($"{Path.GetFileName(path)} {arr.width}x{arr.height}x{arr.depth} {arr.format} mips {arr.mipmapCount}");
            }
            foreach (var (path, comp) in new[] { (GroundDir + "BermsRoadSplat.png", TextureImporterCompression.CompressedHQ), (GroundDir + "BermsRoadSplat2.png", TextureImporterCompression.Uncompressed) })
            {
                var ti = (TextureImporter)AssetImporter.GetAtPath(path) ?? throw new Exception("missing " + path);
                ti.textureShape = TextureImporterShape.Texture2D; ti.sRGBTexture = false; ti.mipmapEnabled = true; ti.streamingMipmaps = true;
                ti.isReadable = false; ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Trilinear; ti.anisoLevel = 4;
                ti.maxTextureSize = 4096; ti.textureCompression = comp; ti.alphaSource = TextureImporterAlphaSource.FromInput; ti.alphaIsTransparency = false;
                var ps = ti.GetPlatformTextureSettings("Standalone"); ps.overridden = true; ps.maxTextureSize = 4096; ps.textureCompression = comp;
                ps.format = comp == TextureImporterCompression.Uncompressed ? TextureImporterFormat.RGBA32 : TextureImporterFormat.Automatic;
                ti.SetPlatformTextureSettings(ps);
                ti.SaveAndReimport();
                var t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                log.Add($"{Path.GetFileName(path)} {t.width}x{t.height} {t.format}");
            }
            // the old arrays, for the record (slice size after import)
            foreach (var path in new[] { "Assets/AthenHill/Art/WestGate/Ground/BermsGroundLayers_AH.png" })
            {
                var arr = AssetDatabase.LoadAssetAtPath<Texture2DArray>(path);
                if (arr) log.Add($"(old) {Path.GetFileName(path)} {arr.width}x{arr.height}x{arr.depth} {arr.format}");
            }

            var cfg = Json("material.json");
            var shader = Shader.Find((string)cfg["shader"]) ?? throw new Exception("shader missing: " + cfg["shader"]);
            if (ShaderUtil.ShaderHasError(shader))
                throw new Exception("shader has errors: " + string.Join(" | ", ShaderUtil.GetShaderMessages(shader).Select(m => m.message + " @" + m.line)));
            var path0 = (string)cfg["path"];
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path0);
            bool create = !mat;
            if (create) mat = new Material(shader) { name = Path.GetFileNameWithoutExtension(path0) }; else mat.shader = shader;
            var src = AssetDatabase.LoadAssetAtPath<Material>((string)cfg["copyFrom"]) ?? throw new Exception("missing " + cfg["copyFrom"]);
            var copied = new List<string>();
            void Copy(string from, string to)
            {
                if (!src.HasProperty(from) || !mat.HasProperty(to)) return;
                int idx = shader.FindPropertyIndex(to);
                switch (shader.GetPropertyType(idx))
                {
                    case ShaderPropertyType.Texture: mat.SetTexture(to, src.GetTexture(from)); break;
                    case ShaderPropertyType.Color: mat.SetColor(to, src.GetColor(from)); break;
                    case ShaderPropertyType.Vector: mat.SetVector(to, src.GetVector(from)); break;
                    default: mat.SetFloat(to, src.GetFloat(from)); break;
                }
                copied.Add(to);
            }
            foreach (var p in cfg["copyProps"]) Copy((string)p, (string)p);
            foreach (var kv in (JObject)cfg["copyAs"]) Copy(kv.Key, (string)kv.Value);
            foreach (var kv in (JObject)cfg["textures"])
                mat.SetTexture(kv.Key, AssetDatabase.LoadAssetAtPath<Texture>((string)kv.Value) ?? throw new Exception("missing texture " + kv.Value));
            foreach (var kv in (JObject)cfg["floats"]) mat.SetFloat(kv.Key, (float)kv.Value);
            foreach (var kv in (JObject)cfg["colors"]) { var c = kv.Value.Select(x => (float)x).ToArray(); mat.SetColor(kv.Key, new Color(c[0], c[1], c[2], c[3])); }
            foreach (var kv in (JObject)cfg["vectors"]) { var c = kv.Value.Select(x => (float)x).ToArray(); mat.SetVector(kv.Key, new Vector4(c[0], c[1], c[2], c[3])); }
            if (create) AssetDatabase.CreateAsset(mat, path0); else EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
            log.Add($"material {path0} ({(create ? "created" : "updated")}), copied {copied.Count} values from {src.name}");
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "build.json", JsonConvert.SerializeObject(new { utc = DateTime.UtcNow.ToString("O"), log, material = DumpMaterial(mat) }, Formatting.Indented));
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ apply (shared by preview captures and install)
        static GameObject Ground(UnityEngine.SceneManagement.Scene scene)
        {
            var berms = scene.GetRootGameObjects().First(g => g.name == "Outer Berms").transform;
            return berms.Find("Berms ground")?.gameObject ?? throw new Exception(GroundPath + " missing");
        }

        static float GroundY(MeshCollider col, float x, float z) =>
            col.Raycast(new Ray(new Vector3(x, 80, z), Vector3.down), out var hit, 200) ? hit.point.y : float.NaN;

        static float GroundMin(MeshCollider col, float x, float z, float r)
        {
            float m = GroundY(col, x, z);
            for (int i = 0; i < 12; i++) { float a = i * Mathf.PI / 6; m = Mathf.Min(m, GroundY(col, x + Mathf.Cos(a) * r, z + Mathf.Sin(a) * r)); }
            return m;
        }

        static readonly Dictionary<string, float> RockHeight = new() { ["PH_RockA"] = .15f, ["PH_RockB"] = .08f, ["PH_RockC"] = .09f, ["PH_RockD"] = .12f };

        static GameObject Rock(UnityEngine.SceneManagement.Scene scene, Transform parent, string kind, string name)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabDir + kind + ".prefab") ?? throw new Exception("missing prefab " + kind);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            go.name = name; go.transform.SetParent(parent, false);
            return go;
        }

        /// Assigns the V2 material and builds the edge stones and cairns in the open scene (not saved). Returns the stones root.
        static GameObject Apply(UnityEngine.SceneManagement.Scene scene, Dictionary<string, object> record)
        {
            Physics.SyncTransforms();
            var ground = Ground(scene);
            var col = ground.GetComponent<MeshCollider>();
            var mr = ground.GetComponent<MeshRenderer>();
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MatPath) ?? throw new Exception("build the material first: " + MatPath);
            record["previousMaterial"] = AssetDatabase.GetAssetPath(mr.sharedMaterial);
            record["groundMesh"] = AssetDatabase.GetAssetPath(ground.GetComponent<MeshFilter>().sharedMesh);
            record["groundColliderMesh"] = AssetDatabase.GetAssetPath(col.sharedMesh);
            mr.sharedMaterial = mat;
            record["material"] = MatPath;

            var layout = Json("edge_stones.json");
            var root = new GameObject(StonesRootName);
            root.transform.SetParent(ground.transform.parent, false);
            var stonesT = new GameObject("Edge stones").transform; stonesT.SetParent(root.transform, false);
            var cairnsT = new GameObject("Cairns").transform; cairnsT.SetParent(root.transform, false);
            int n = 0; var placed = new List<object>();
            foreach (JObject s in layout["stones"])
            {
                string kind = (string)s["prefab"]; float x = (float)s["x"], z = (float)s["z"], sc = (float)s["scale"], r = (float)s["r"];
                float h = RockHeight[kind] * sc;
                float y = GroundMin(col, x, z, Mathf.Max(r * .8f, .1f)) - (float)s["sink"] * h;
                if (float.IsNaN(y)) throw new Exception("no ground under stone at " + x + "," + z);
                var go = Rock(scene, stonesT, kind, $"Edge stone {++n:00} {kind.Substring(3)}");
                var tilt = s["tilt"].Select(t => (float)t).ToArray();
                go.transform.SetPositionAndRotation(new Vector3(x, y, z), Quaternion.Euler(tilt[0], (float)s["yaw"], tilt[1]));
                go.transform.localScale = Vector3.one * sc;
                placed.Add(new { name = go.name, pos = V(go.transform.position), sc });
            }
            var cairns = new List<object>();
            foreach (JObject c in layout["cairns"])
            {
                float cx = (float)c["x"], cz = (float)c["z"];
                float gy = GroundMin(col, cx, cz, .35f);
                var cr = new GameObject((string)c["name"]); cr.transform.SetParent(cairnsT, false); cr.transform.position = new Vector3(cx, gy, cz);
                var tierTop = new Dictionary<int, float> { [-1] = gy + .05f };
                var rends = new List<Renderer>();
                foreach (JObject r in c["rocks"])
                {
                    string kind = (string)r["prefab"]; int tier = (int)r["tier"]; float sc = (float)r["scale"]; float h = RockHeight[kind] * sc;
                    float baseY = tierTop[tier - 1] - (tier == 0 ? .3f : .38f) * h;
                    var go = Rock(scene, cr.transform, kind, $"Cairn rock t{tier} {kind.Substring(3)}");
                    var tilt = r["tilt"].Select(t => (float)t).ToArray();
                    go.transform.SetPositionAndRotation(new Vector3(cx + (float)r["dx"], baseY, cz + (float)r["dz"]), Quaternion.Euler(tilt[0], (float)r["yaw"], tilt[1]));
                    go.transform.localScale = Vector3.one * sc;
                    tierTop[tier] = Mathf.Max(tierTop.TryGetValue(tier, out var t0) ? t0 : float.MinValue, baseY + h);
                    rends.AddRange(go.GetComponentsInChildren<Renderer>(true).Where(x => x.name.EndsWith("_LOD0")));
                }
                var b = rends[0].bounds; foreach (var x in rends) b.Encapsulate(x.bounds);
                var box = cr.AddComponent<BoxCollider>();
                box.center = cr.transform.InverseTransformPoint(new Vector3(b.center.x, (b.min.y + b.max.y) / 2 + .02f, b.center.z));
                box.size = new Vector3(b.size.x * .85f, b.size.y, b.size.z * .85f);
                cairns.Add(new { name = cr.name, pos = V(cr.transform.position), height = Math.Round(b.max.y - gy, 3), rocks = rends.Count });
            }
            foreach (var t in root.GetComponentsInChildren<Transform>(true).Where(t => !PrefabUtility.IsPartOfPrefabInstance(t.gameObject)))
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
            record["stones"] = placed.Count; record["cairns"] = cairns; record["stonePositions"] = placed;
            return root;
        }

        // ------------------------------------------------------------------ footsteps (the Berms ground map follows the splat)
        static string RebakeFootsteps(UnityEngine.SceneManagement.Scene scene, Dictionary<string, object> record, bool toNew)
        {
            var fa = UnityEngine.Object.FindAnyObjectByType<FootstepAudio>() ?? throw new Exception("FootstepAudio missing");
            if (!toNew)
            {
                var before = JObject.Parse(File.ReadAllText(Evidence + "footsteps-before.json"));
                fa.bermsWidth = (int)before["width"]; fa.bermsHeight = (int)before["height"]; fa.bermsSurfaces = Convert.FromBase64String((string)before["cells"]);
                EditorUtility.SetDirty(fa); return "footsteps restored";
            }
            if (!File.Exists(Evidence + "footsteps-before.json"))
                File.WriteAllText(Evidence + "footsteps-before.json", JsonConvert.SerializeObject(new { fa.bermsWidth, width = fa.bermsWidth, height = fa.bermsHeight, rect = new[] { fa.bermsRect.x, fa.bermsRect.y, fa.bermsRect.z, fa.bermsRect.w }, cells = Convert.ToBase64String(fa.bermsSurfaces) }));
            var s1 = new Texture2D(2, 2); s1.LoadImage(File.ReadAllBytes(GroundDir + "BermsRoadSplat.png"));
            var s2 = new Texture2D(2, 2); s2.LoadImage(File.ReadAllBytes(GroundDir + "BermsRoadSplat2.png"));
            // same rule as CharacterFeelPass (R gravel road / G sand / B crust heard as gravel; bare ground as sand), plus
            // loose gravel (splat 2 R) heard as gravel
            var rect = fa.bermsRect;
            int w = Mathf.RoundToInt(2 / rect.z), h = Mathf.RoundToInt(2 / rect.w);
            var grid = new byte[w * h]; var tally = new int[6]; int changed = 0;
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
            {
                var c = s1.GetPixelBilinear((x + .5f) / w, (y + .5f) / h); var c2 = s2.GetPixelBilinear((x + .5f) / w, (y + .5f) / h);
                var sfc = c.g >= c.r && c.g >= c.b || Mathf.Max(c.r, c.g, c.b) < .15f ? FootSurface.Sand : FootSurface.Gravel;
                if (c2.r > .5f) sfc = FootSurface.Gravel;
                grid[y * w + x] = (byte)sfc; tally[(int)sfc]++;
                if (fa.bermsSurfaces.Length == w * h && fa.bermsSurfaces[y * w + x] != (byte)sfc) changed++;
            }
            UnityEngine.Object.DestroyImmediate(s1); UnityEngine.Object.DestroyImmediate(s2);
            Undo.RecordObject(fa, "Berms footsteps");
            fa.bermsWidth = w; fa.bermsHeight = h; fa.bermsSurfaces = grid; EditorUtility.SetDirty(fa);
            record["footsteps"] = new { w, h, sand = tally[(int)FootSurface.Sand], gravel = tally[(int)FootSurface.Gravel], changedCells = changed };
            return $"footsteps {w}x{h}: sand {tally[(int)FootSurface.Sand]}, gravel {tally[(int)FootSurface.Gravel]}, changed {changed}";
        }

        // ------------------------------------------------------------------ review cameras (player height; lookbook names)
        static void AddReviewCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (old) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(CamRootName);
            foreach (JObject c in JArray.Parse(File.ReadAllText(ArtSrc + "review_cameras.json")))
            {
                var p = c["pos"].Select(x => (float)x).ToArray(); var t = c["target"].Select(x => (float)x).ToArray();
                var go = new GameObject((string)c["name"]); go.transform.SetParent(root.transform, false);
                var pos = new Vector3(p[0], p[1], p[2]);
                go.transform.SetPositionAndRotation(pos, Quaternion.LookRotation(new Vector3(t[0], t[1], t[2]) - pos, Vector3.up));
                var k = go.AddComponent<Camera>(); k.enabled = false; k.fieldOfView = (float)c["fov"]; k.nearClipPlane = .05f; k.farClipPlane = 650;
            }
        }

        // ------------------------------------------------------------------ install (one time, -nographics)
        public static string Install()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var berms = scene.GetRootGameObjects().First(g => g.name == "Outer Berms").transform;
            if (berms.Find(StonesRootName)) throw new Exception("The Berms road pass is already installed; edit it in place or use toggle.");
            Directory.CreateDirectory(Evidence + "rollback");
            File.Copy(ScenePath, Evidence + "rollback/before-berms-road.unity", true);
            var record = new Dictionary<string, object> { ["utc"] = DateTime.UtcNow.ToString("O"), ["rollbackScene"] = Evidence + "rollback/before-berms-road.unity" };
            Apply(scene, record);
            record["footstepResult"] = RebakeFootsteps(scene, record, true);
            AddReviewCameras(scene);
            record["reviewCameras"] = JArray.Parse(File.ReadAllText(ArtSrc + "review_cameras.json")).Select(c => (string)c["name"]).ToArray();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        /// Rollback/measurement: "old" puts back the previous ground material, footstep map and hides the stones; "new" re-applies.
        public static string Toggle(bool on)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var ground = Ground(scene);
            var rec = JObject.Parse(File.ReadAllText(Evidence + "install.json"));
            var mat = AssetDatabase.LoadAssetAtPath<Material>(on ? MatPath : (string)rec["previousMaterial"]);
            ground.GetComponent<MeshRenderer>().sharedMaterial = mat;
            var root = ground.transform.parent.Find(StonesRootName); if (root) root.gameObject.SetActive(on);
            var r = RebakeFootsteps(scene, new Dictionary<string, object>(), on);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return (on ? "V2 ground on" : "previous ground restored") + "; " + r;
        }

        /// Idempotent adjustments to the installed pass: the cairns cast shadows (they stand 0.65 m proud; the flat-laid
        /// edge stones keep the West Gate scatter's no-shadow setting).
        public static string Tune()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = Ground(scene).transform.parent.Find(StonesRootName) ?? throw new Exception("not installed");
            int n = 0;
            foreach (var r in root.Find("Cairns").GetComponentsInChildren<MeshRenderer>(true))
            {
                if (r.shadowCastingMode == ShadowCastingMode.On) continue;
                r.shadowCastingMode = ShadowCastingMode.On;
                PrefabUtility.RecordPrefabInstancePropertyModifications(r); n++;
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "cairn renderers now casting shadows: " + n;
        }

        public static string ReviewCameras()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            AddReviewCameras(scene);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "review cameras: " + scene.GetRootGameObjects().First(g => g.name == CamRootName).transform.childCount;
        }

        // ------------------------------------------------------------------ verify (saved scene, -nographics)
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Physics.SyncTransforms();
            var r = new Dictionary<string, object>();
            var survey = JObject.Parse(File.ReadAllText(ArtSrc + "survey.json"));
            var ground = Ground(scene);
            var mr = ground.GetComponent<MeshRenderer>(); var col = ground.GetComponent<MeshCollider>(); var mf = ground.GetComponent<MeshFilter>();
            r["groundMaterial"] = AssetDatabase.GetAssetPath(mr.sharedMaterial);
            r["materialIsV2"] = AssetDatabase.GetAssetPath(mr.sharedMaterial) == MatPath;
            r["shader"] = mr.sharedMaterial ? mr.sharedMaterial.shader.name : null;
            r["shaderSupported"] = mr.sharedMaterial && mr.sharedMaterial.shader.isSupported;
            r["shaderErrors"] = mr.sharedMaterial ? ShaderUtil.GetShaderMessages(mr.sharedMaterial.shader).Where(m => m.severity == UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error).Select(m => m.message).ToArray() : null;
            var m = mr.sharedMaterial;
            r["missingTextures"] = m ? new[] { "_Splat", "_Splat2", "_AlbedoHeight", "_NormalRoughAO", "_RockTex", "_Geology", "_RockDetailAlbedo", "_RockDetailNormal" }.Where(p => !m.GetTexture(p)).ToArray() : null;
            r["groundMeshUnchanged"] = AssetDatabase.GetAssetPath(mf.sharedMesh) == (string)survey["ground"]["meshAsset"] && mf.sharedMesh.vertexCount == (int)survey["ground"]["vertexCount"];
            r["groundColliderUnchanged"] = col && col.enabled && col.sharedMesh == mf.sharedMesh && AssetDatabase.GetAssetPath(col.sharedMesh) == (string)survey["ground"]["colliderMeshAsset"];
            var bank = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Renderer>(true)).FirstOrDefault(x => PathOf(x.transform) == "Outer Berms/Warden training range/Backstop/Backstop earth bank");
            r["earthBankMaterial"] = bank ? AssetDatabase.GetAssetPath(bank.sharedMaterial) : null;
            var root = ground.transform.parent.Find(StonesRootName);
            r["installed"] = root != null;
            if (root)
            {
                r["active"] = root.gameObject.activeInHierarchy;
                var inst = root.GetComponentsInChildren<Transform>(true).Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
                r["prefabInstances"] = inst.Length;
                r["prefabLinksBroken"] = inst.Count(t => !PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject));
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Count(x => x.sharedMaterials.Any(q => !q));
                r["uniformScale"] = inst.All(t => Mathf.Abs(t.localScale.x - t.localScale.y) < 1e-4f && Mathf.Abs(t.localScale.x - t.localScale.z) < 1e-4f);
                long lod0 = 0, lod1 = 0;
                foreach (var g in root.GetComponentsInChildren<LODGroup>(true))
                {
                    var lods = g.GetLODs();
                    long Tris(LOD l) => l.renderers.Where(x => x && x.GetComponent<MeshFilter>()).Sum(x => { var mm = x.GetComponent<MeshFilter>().sharedMesh; long t = 0; for (int k = 0; k < mm.subMeshCount; k++) t += mm.GetIndexCount(k) / 3; return t; });
                    lod0 += Tris(lods[0]); if (lods.Length > 1) lod1 += Tris(lods[1]);
                }
                r["lod0TrianglesAll"] = lod0; r["lod1TrianglesAll"] = lod1;
                r["colliders"] = root.GetComponentsInChildren<Collider>(true).Select(c => PathOf(c.transform) + " " + c.bounds.size).ToArray();
                r["lights"] = root.GetComponentsInChildren<Light>(true).Length;
                // floaters: every stone's LOD0 bottom must be at or below the ground under it
                var floating = new List<string>();
                var colG = col;
                foreach (var t in inst)
                {
                    var rr = t.GetComponentsInChildren<Renderer>(true).FirstOrDefault(x => x.name.EndsWith("_LOD0")); if (!rr) continue;
                    var b = rr.bounds;
                    float gy = GroundY(colG, b.center.x, b.center.z);
                    if (!t.parent.name.StartsWith("Cairn") && b.min.y > gy + .01f) floating.Add(t.name + $" {b.min.y - gy:0.000}");
                }
                r["floatingStones"] = floating;
            }
            // gameplay untouched: markers, colliders and landmarks as surveyed
            var moved = new List<string>();
            var lm = scene.GetRootGameObjects().First(g => g.name == "Landmarks").transform;
            foreach (JObject mk in survey["markers"])
            {
                if ((string)mk["kind"] != "landmark") continue;
                var name = ((string)mk["path"]).Split('/').Last(); var t = lm.Find(name);
                var p = mk["pos"].Select(x => (float)x).ToArray();
                if (!t || Vector3.Distance(t.position, new Vector3(p[0], p[1], p[2])) > .01f) moved.Add(name);
            }
            r["landmarksMoved"] = moved;
            r["encounters"] = UnityEngine.Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Select(e => e.name).ToArray();
            var tut = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            r["tutorialTargets"] = tut ? tut.targets.Count(t => t && t.gameObject.activeInHierarchy) : 0;
            var fa = UnityEngine.Object.FindAnyObjectByType<FootstepAudio>();
            r["footstepCells"] = fa ? fa.bermsSurfaces.Length : 0;
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks) { r["chunkFingerprintMatches"] = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks); r["chunkEditing"] = chunks.editingSources; }
            r["reviewCameras"] = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName)?.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray();
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify-saved-scene.json", json);
            return json;
        }

        // ------------------------------------------------------------------ editor captures (graphics; at most 6 per run)
        /// Renders views through a clone of MainCamera (StreetDressingPass.Capture). `views` is a list of scene camera names
        /// ("cam_a+cam_b") or "@file.json" with [{name,pos,target,fov}] for poses that are not in the scene yet. With
        /// `preview` the V2 ground and the stones are applied to the opened scene first (never saved). Nothing is saved.
        public static string CaptureViews(string outDir, string views, bool preview)
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (preview) Apply(scene, new Dictionary<string, object>());
            var list = new List<(string name, Vector3 pos, Vector3 target, float fov)>();
            if (views.StartsWith("@"))
            {
                foreach (JObject v in JArray.Parse(File.ReadAllText(views.Substring(1))))
                {
                    var p = v["pos"].Select(x => (float)x).ToArray(); var t = v["target"].Select(x => (float)x).ToArray();
                    list.Add(((string)v["name"], new Vector3(p[0], p[1], p[2]), new Vector3(t[0], t[1], t[2]), (float)(v["fov"] ?? 60)));
                }
            }
            else
            {
                var camsByName = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Camera>(true)).GroupBy(c => c.name).ToDictionary(g => g.Key, g => g.First());
                foreach (var n in views.Split('+'))
                {
                    if (!camsByName.TryGetValue(n, out var c)) throw new Exception("camera not found: " + n);
                    list.Add((n, c.transform.position, c.transform.position + c.transform.forward * 5f, c.fieldOfView));
                }
            }
            if (list.Count > 6) throw new Exception($"{list.Count} views in one run; capture at most 6 per Unity run");
            return string.Join(",", StreetDressingPass.Capture(outDir, list));
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.BermsRoadPass.RunBatch --steps survey[,...]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "survey" };
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "capture" => CaptureViews(parts[1], parts[2], parts.Length > 3 && parts[3] == "preview"),
                        "build" => BuildAssets(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "cameras" => ReviewCameras(),
                        "tune" => Tune(),
                        "toggle" => Toggle(parts[1] == "new"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BermsRoadPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
