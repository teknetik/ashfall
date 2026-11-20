using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    /// <summary>
    /// 20 November 2026 (showcase phase 2): Outer Berms ground variety. The bowl between the sites read as one flat sand
    /// look for hundreds of metres. This pass is additive: it never moves sites, encounters, spawns, loot, the road, the
    /// range, the waystation, landmarks or any existing collider, and never changes the walkable ground mesh.
    /// Sources, layout and run order: art/berms_variety_20261120/README.md.
    ///
    /// * Ground regions: the 54 expanse ground tiles (Outer Berms/Berms expanse/Ground) swap BermsGroundV2.mat for
    ///   Art/BermsVariety/Ground/BermsVarietyGround.mat (shader "Athen Hill/Berms Ground V3" = V2 + a bowl-wide region
    ///   mask: clay pans, hardpan, wind sand in the lee of ridges, gravel fans with desert varnish, dry wash beds, wheel and
    ///   track marks, scorched and glassed ground and old craters). The old Berms ground keeps V2.
    /// * Scene root "Outer Berms/Berms variety": Earthworks and Craters (generated meshes on the same ground material),
    ///   Outcrops (generated sandstone ledges on SandstoneBasinV3.mat), Wreckage and Clusters (existing kit prefabs), and
    ///   the review cameras cam_bv_*. Everything comes from art/berms_variety_20261120 (placements.json, the GLB, masks).
    /// * Footsteps: FootstepAudio's Berms variety map (sand / gravel / stone) under the expanse ground and the earthworks.
    ///
    /// Steps (RunBatch --steps a,b,...): survey (read-only, -nographics), material (textures + material), install
    /// (re-runnable: removes its own root first), toggle:on|off (A/B switch: root, tile material, footstep map), verify
    /// (-> evidence verify.json), rollback (= toggle:off, leaves the inactive root for recovery), uninstall (deletes the
    /// root after rollback), capture:HOUR:cam+cam[:before|after|both] (graphics; at most six cameras per Unity run).
    /// </summary>
    public static class BermsVarietyPass20261120
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        public const string Art = "../../art/berms_variety_20261120/";
        public const string Evidence = "../evidence/showcase_phase2/20261120/berms_variety/";
        const string AssetDir = "Assets/AthenHill/Art/BermsVariety/";
        const string GroundMatV2 = "Assets/AthenHill/Art/BermsRoad/Ground/BermsGroundV2.mat";
        const string GroundMatV3 = AssetDir + "Ground/BermsVarietyGround.mat";
        const string ShaderV3 = "Athen Hill/Berms Ground V3";
        const string RockMatV = AssetDir + "Rock/BermsVarietyRock.mat";   // URP Lit, Poly Haven Cliff Side (fix round 20 Nov; was SandstoneBasinV3)
        const string RockDir = AssetDir + "Rock/";
        const string Glb = AssetDir + "Meshes/BermsVarietyRelief.glb";
        const string SplatA = AssetDir + "Ground/BermsVarietySplatA.png";
        const string SplatB = AssetDir + "Ground/BermsVarietySplatB.png";
        const string RootName = "Berms variety";
        const string CamRootName = "Berms variety review cameras";
        const string TilesPath = "Outer Berms/Berms expanse/Ground";
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        // survey window (world metres): the bowl and its edges
        const float X0 = -590f, X1 = -50f, Z0 = -275f, Z1 = 275f;
        static bool InWindow(Bounds b) => b.max.x >= X0 && b.min.x <= X1 && b.max.z >= Z0 && b.min.z <= Z1;
        static bool InWindow(Vector3 p) => p.x >= X0 && p.x <= X1 && p.z >= Z0 && p.z <= Z1;
        public static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] V(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static JToken Json(string file) => JToken.Parse(File.ReadAllText(Art + file));
        static Scene OpenScene() => EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        static Transform Find(Scene s, string path)
        {
            var parts = path.Split('/');
            var r = s.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]); if (!r) return null;
            var t = r.transform; for (int i = 1; i < parts.Length && t; i++) t = t.Find(parts[i]);
            return t;
        }

        // ------------------------------------------------------------------ survey (read-only)
        /// Everything the layout must keep clear, from the saved scene: encounters and spawns, droid home/leash data,
        /// salvage and loot interactables, landmarks, the waystation, cameras, every collider and every site renderer in
        /// the bowl, the ground tiles and their material, and the footstep component. -> art/.../survey.json
        public static string Survey()
        {
            var scene = OpenScene(); Physics.SyncTransforms();
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToList();
            var mine = Find(scene, "Outer Berms/" + RootName);
            bool Mine(Transform t) => mine && (t == mine || t.IsChildOf(mine));
            var markers = new List<object>();
            void Mark(string kind, Transform t, object extra = null) { if (t && InWindow(t.position) && !Mine(t)) markers.Add(new { kind, path = PathOf(t), pos = V(t.position), yaw = Math.Round(t.eulerAngles.y, 1), active = t.gameObject.activeInHierarchy, extra }); }
            foreach (var e in Object.FindObjectsByType<DroidEncounter>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                Mark("encounter", e.transform, new { e.displayName, e.activateWithin, e.parkBeyond, e.packRadius });
                foreach (var s in e.spawns)
                {
                    if (!s.point) continue;
                    var d = s.prefab;
                    Mark("spawn", s.point, new { prefab = d ? d.name : null, kind = d ? d.kind.ToString() : null, wander = d ? d.wanderRadius : 0, leash = d ? d.leashRadius : 0, aggro = d ? d.aggroRadius : 0 });
                }
            }
            foreach (var d in Object.FindObjectsByType<FeralDroid>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("droid", d.transform, new { kind = d.kind.ToString(), d.wanderRadius, d.leashRadius });
            foreach (var s in Object.FindObjectsByType<SalvageNode>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("salvage", s.transform);
            foreach (var w in Object.FindObjectsByType<WorldInteractable>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("interactable", w.transform, new { w.prompt, w.range });
            foreach (var l in Object.FindObjectsByType<LootSource>(FindObjectsInactive.Include, FindObjectsSortMode.None)) if (!l.GetComponent<FeralDroid>()) Mark("loot", l.transform, new { l.lootTableId });
            foreach (var r in Object.FindObjectsByType<RangeTarget>(FindObjectsInactive.Include, FindObjectsSortMode.None)) Mark("target", r.transform);
            foreach (var w in Object.FindObjectsByType<WardenWaystation>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                Mark("waystation", w.transform, new { w.discoverRadius });
                if (w.respawnPoint) Mark("respawn", w.respawnPoint);
            }
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks) foreach (Transform t in landmarks.transform) Mark("landmark", t);
            foreach (var t in all.Where(t => t.name.Contains("Respawn") || t.name.Contains("Gate marker"))) Mark("misc", t);
            var colliders = new List<object>();
            var tiles = Find(scene, TilesPath);
            foreach (var c in all.SelectMany(t => t.GetComponents<Collider>()))
            {
                if (!c.gameObject.activeInHierarchy || !c.enabled || Mine(c.transform)) continue;
                if (tiles && c.transform.IsChildOf(tiles)) continue;
                var b = c.bounds; if (!InWindow(b)) continue;
                colliders.Add(new { path = PathOf(c.transform), type = c.GetType().Name, trigger = c.isTrigger, min = V(b.min), max = V(b.max) });
            }
            var renderers = new List<object>();
            var berms = Find(scene, "Outer Berms");
            foreach (var r in berms.GetComponentsInChildren<Renderer>(false))
            {
                if (r is ParticleSystemRenderer || r is LineRenderer || r is TrailRenderer || !r.enabled || Mine(r.transform)) continue;
                if (tiles && r.transform.IsChildOf(tiles)) continue;
                var p = PathOf(r.transform);
                if (p.StartsWith("Outer Berms/Berms ground")) continue;
                renderers.Add(new { path = p, min = V(r.bounds.min), max = V(r.bounds.max) });
            }
            var cams = all.Select(t => t.GetComponent<Camera>()).Where(c => c && InWindow(c.transform.position))
                .Select(c => new { name = c.name, pos = V(c.transform.position), fwd = V(c.transform.forward), c.fieldOfView }).ToArray();
            var tileInfo = tiles ? tiles.GetComponentsInChildren<MeshRenderer>(true).Select(r => new { path = PathOf(r.transform), mat = r.sharedMaterial ? AssetDatabase.GetAssetPath(r.sharedMaterial) : null }).ToArray() : null;
            var fa = Object.FindAnyObjectByType<FootstepAudio>(FindObjectsInactive.Include);
            var result = new
            {
                scene = ScenePath, utc = DateTime.UtcNow.ToString("O"), window = new[] { X0, X1, Z0, Z1 },
                markers, colliders, renderers, cameras = cams, tiles = tileInfo,
                footsteps = fa ? new { path = PathOf(fa.transform), rect = new[] { fa.bermsRect.x, fa.bermsRect.y, fa.bermsRect.z, fa.bermsRect.w }, fa.bermsWidth, fa.bermsHeight, varietyWidth = fa.varietyWidth, varietyCells = fa.varietySurfaces.Length } : null,
                bermsChildren = berms.Cast<Transform>().Select(t => new { t.name, active = t.gameObject.activeSelf }).ToArray(),
            };
            File.WriteAllText(Art + "survey.json", JsonConvert.SerializeObject(result, Formatting.Indented));
            return $"survey: {markers.Count} markers, {colliders.Count} colliders, {renderers.Count} renderers, {cams.Length} cameras";
        }

        // ------------------------------------------------------------------ material + textures
        public static string BuildMaterial()
        {
            Directory.CreateDirectory(AssetDir + "Ground");
            foreach (var p in new[] { SplatA, SplatB })
            {
                AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceSynchronousImport);
                var ti = AssetImporter.GetAtPath(p) as TextureImporter; if (!ti) throw new Exception("missing mask " + p);
                ti.textureType = TextureImporterType.Default; ti.sRGBTexture = false; ti.mipmapEnabled = true; ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.alphaIsTransparency = false; ti.wrapMode = TextureWrapMode.Clamp; ti.filterMode = FilterMode.Trilinear; ti.anisoLevel = 4;
                ti.maxTextureSize = 2048; ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.streamingMipmaps = false;
                var ps = ti.GetPlatformTextureSettings("Standalone"); ps.overridden = true; ps.maxTextureSize = 2048; ps.format = TextureImporterFormat.BC7; ti.SetPlatformTextureSettings(ps);
                ti.SaveAndReimport();
            }
            var shader = Shader.Find(ShaderV3); if (!shader) throw new Exception("shader not found: " + ShaderV3);
            var v2 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV2);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV3);
            if (!mat) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, GroundMatV3); }
            mat.shader = shader;
            // copy V2's values property by property (CopyPropertiesFromMaterial left later Set* calls ignored in batch runs)
            var v2s = v2.shader;
            for (int k = 0; k < v2s.GetPropertyCount(); k++)
            {
                var n = v2s.GetPropertyName(k); if (!mat.HasProperty(n)) continue;
                switch (v2s.GetPropertyType(k))
                {
                    case ShaderPropertyType.Texture: mat.SetTexture(n, v2.GetTexture(n)); break;
                    case ShaderPropertyType.Color: mat.SetColor(n, v2.GetColor(n)); break;
                    case ShaderPropertyType.Vector: mat.SetVector(n, v2.GetVector(n)); break;
                    case ShaderPropertyType.Float: case ShaderPropertyType.Range: mat.SetFloat(n, v2.GetFloat(n)); break;
                    case ShaderPropertyType.Int: mat.SetInt(n, v2.GetInt(n)); break;
                }
            }
            var spec = (JObject)Json("material.json");
            mat.SetTexture("_VarSplatA", AssetDatabase.LoadAssetAtPath<Texture2D>(SplatA));
            mat.SetTexture("_VarSplatB", AssetDatabase.LoadAssetAtPath<Texture2D>(SplatB));
            foreach (var kv in (JObject)spec["floats"]) mat.SetFloat(kv.Key, (float)kv.Value);
            foreach (var kv in (JObject)spec["vectors"]) { var a = kv.Value.Select(x => (float)x).ToArray(); mat.SetVector(kv.Key, new Vector4(a[0], a[1], a[2], a.Length > 3 ? a[3] : 0)); }
            foreach (var kv in (JObject)spec["colors"]) { var a = kv.Value.Select(x => (float)x).ToArray(); mat.SetColor(kv.Key, new Color(a[0], a[1], a[2], a.Length > 3 ? a[3] : 1)); }
            mat.enableInstancing = false;
            EditorUtility.SetDirty(mat); AssetDatabase.SaveAssets();
            BuildRockMaterial(spec);
            var texA = AssetDatabase.LoadAssetAtPath<Texture2D>(SplatA);
            var diag = $"shader={mat.shader.name} has={mat.HasProperty("_VarSplatA")} texA={(texA ? texA.width + "x" + texA.height + " " + texA.format : "null")} get={(mat.GetTexture("_VarSplatA") ? "set" : "null")} strength={mat.GetFloat("_VarStrength")}";
            AssetDatabase.ImportAsset(GroundMatV3, ImportAssetOptions.ForceSynchronousImport);
            var re = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV3);
            diag += $" reloaded get={(re.GetTexture("_VarSplatA") ? "set" : "null")}";
            if (!re.GetTexture("_VarSplatA")) throw new Exception("material did not keep its masks: " + diag);
            return "material " + GroundMatV3 + " (" + shader.name + ") " + diag;
        }

        /// cost:cam+cam (-nographics): what this pass adds in front of each review camera, estimated from its LODGroups
        /// (PC lodBias 2, 1920x1080, frustum culled): renderers drawn (~draw calls, one material each) and triangles in
        /// the colour pass, shadow-casting renderers and their triangles. -> Evidence/cost.json
        public static string Cost(string camList)
        {
            var scene = OpenScene(); const float bias = 2f;
            var root = Find(scene, "Outer Berms/" + RootName); if (!root) throw new Exception("not installed");
            var poses = Json("review_cameras.json")["cameras"].ToDictionary(c => (string)c["name"], c => (JObject)c);
            var go = new GameObject("__cost") { hideFlags = HideFlags.DontSave }; var cam = go.AddComponent<Camera>();
            cam.farClipPlane = 1600; cam.nearClipPlane = .05f; cam.aspect = 16f / 9f;
            var outp = new JObject();
            foreach (var n in camList.Split('+'))
            {
                var c = poses[n]; var pos = c["pos"].Select(v => (float)v).ToArray(); var tg = c["target"].Select(v => (float)v).ToArray();
                go.transform.position = new Vector3(pos[0], pos[1], pos[2]); go.transform.LookAt(new Vector3(tg[0], tg[1], tg[2])); cam.fieldOfView = (float)c["fov"];
                var planes = GeometryUtility.CalculateFrustumPlanes(cam);
                int draws = 0, shadowDraws = 0; long tris = 0, shadowTris = 0;
                var counted = new HashSet<Renderer>();
                foreach (var lg in root.GetComponentsInChildren<LODGroup>())
                {
                    var lods = lg.GetLODs(); if (lods.Length == 0) continue;
                    var wp = lg.transform.TransformPoint(lg.localReferencePoint);
                    float size = lg.size * Mathf.Max(lg.transform.lossyScale.x, Mathf.Max(lg.transform.lossyScale.y, lg.transform.lossyScale.z));
                    float d = Vector3.Distance(cam.transform.position, wp);
                    float rel = size / (2f * Mathf.Max(d / bias, .01f) * Mathf.Tan(cam.fieldOfView * .5f * Mathf.Deg2Rad));
                    int sel = -1; for (int k = 0; k < lods.Length; k++) if (rel >= lods[k].screenRelativeTransitionHeight) { sel = k; break; }
                    foreach (var l in lods) foreach (var r in l.renderers) if (r) counted.Add(r);
                    if (sel < 0) continue;
                    foreach (var r in lods[sel].renderers)
                    {
                        if (!r || !r.enabled || !r.gameObject.activeInHierarchy || !r.TryGetComponent<MeshFilter>(out var mf) || !mf.sharedMesh) continue;
                        long t = mf.sharedMesh.triangles.Length / 3;
                        bool vis = GeometryUtility.TestPlanesAABB(planes, r.bounds);
                        if (r.shadowCastingMode != ShadowCastingMode.ShadowsOnly && vis) { draws += r.sharedMaterials.Length; tris += t; }
                        if (r.shadowCastingMode != ShadowCastingMode.Off && Vector3.Distance(cam.transform.position, r.bounds.center) < 150) { shadowDraws += r.sharedMaterials.Length; shadowTris += t; }
                    }
                }
                foreach (var r in root.GetComponentsInChildren<Renderer>())
                {   // renderers outside any LODGroup
                    if (counted.Contains(r) || !r.enabled || !r.TryGetComponent<MeshFilter>(out var mf) || !mf.sharedMesh) continue;
                    if (GeometryUtility.TestPlanesAABB(planes, r.bounds)) { draws += r.sharedMaterials.Length; tris += mf.sharedMesh.triangles.Length / 3; }
                }
                outp[n] = new JObject { ["colourDraws"] = draws, ["colourTriangles"] = tris, ["shadowDrawsWithin150m"] = shadowDraws, ["shadowTriangles"] = shadowTris };
            }
            Object.DestroyImmediate(go);
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "cost.json", outp.ToString(Formatting.Indented));
            return outp.ToString(Formatting.None);
        }

        public static string ShaderInfo()
        {
            var sh = Shader.Find(ShaderV3);
            if (!sh) sh = AssetDatabase.LoadAssetAtPath<Shader>("Assets/AthenHill/Shaders/BermsGroundV3.shader");
            if (!sh) return "shader missing";
            var msgs = ShaderUtil.GetShaderMessages(sh).Select(m => $"{m.severity} {m.message} line {m.line}").ToArray();
            var props = Enumerable.Range(0, sh.GetPropertyCount()).Select(k => sh.GetPropertyName(k)).ToArray();
            var r = $"shader {sh.name}: hasError={ShaderUtil.ShaderHasError(sh)} supported={sh.isSupported} props={props.Length} var={string.Join(",", props.Where(p => p.StartsWith("_Var")))} messages={string.Join(" | ", msgs)}";
            File.WriteAllText(Evidence + "shaderinfo.txt", r);
            return r;
        }

        /// Tiling rock for the outcrop walls: Poly Haven "Cliff Side" (CC0, 1.83 m scan; the meshes map it at 2.3 m per tile
        /// with v = world height, so the bedding runs level), URP Lit with normal and occlusion maps.
        static void BuildRockMaterial(JObject spec)
        {
            void Tex(string file, bool normal, bool srgb)
            {
                var p = RockDir + file; AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceSynchronousImport);
                var ti = AssetImporter.GetAtPath(p) as TextureImporter; if (!ti) throw new Exception("missing " + p);
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default; ti.sRGBTexture = srgb;
                ti.mipmapEnabled = true; ti.wrapMode = TextureWrapMode.Repeat; ti.anisoLevel = 8; ti.maxTextureSize = 2048;
                ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.streamingMipmaps = true; ti.SaveAndReimport();
            }
            Tex("BV_CliffSide_BaseMap.jpg", false, true); Tex("BV_CliffSide_Normal.jpg", true, false); Tex("BV_CliffSide_AO.png", false, false);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var m = AssetDatabase.LoadAssetAtPath<Material>(RockMatV);
            if (!m) { m = new Material(lit); AssetDatabase.CreateAsset(m, RockMatV); }
            m.shader = lit;
            var rs = (JObject)spec["rock"];
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(RockDir + "BV_CliffSide_BaseMap.jpg"));
            m.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(RockDir + "BV_CliffSide_Normal.jpg"));
            m.SetTexture("_OcclusionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(RockDir + "BV_CliffSide_AO.png"));
            var bc = rs["baseColor"].Select(x => (float)x).ToArray(); m.SetColor("_BaseColor", new Color(bc[0], bc[1], bc[2], 1));
            m.SetFloat("_BumpScale", (float)rs["normalScale"]); m.SetFloat("_OcclusionStrength", (float)rs["occlusion"]);
            m.SetFloat("_Smoothness", (float)rs["smoothness"]); m.SetFloat("_Metallic", 0);
            m.EnableKeyword("_NORMALMAP"); m.EnableKeyword("_OCCLUSIONMAP");
            EditorUtility.SetDirty(m); AssetDatabase.SaveAssets();
            if (!m.GetTexture("_BaseMap")) throw new Exception("rock material lost its base map");
        }

        // ------------------------------------------------------------------ install
        public static string Install()
        {
            var scene = OpenScene();
            var berms = Find(scene, "Outer Berms"); var tiles = Find(scene, TilesPath);
            if (!berms || !tiles) throw new Exception("Outer Berms / expanse ground not found");
            var old = berms.Find(RootName); if (old) Object.DestroyImmediate(old.gameObject);
            var v2 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV2);
            var v3 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV3); if (!v3) throw new Exception("run the material step first");
            var rockMat = AssetDatabase.LoadAssetAtPath<Material>(RockMatV);
            if (!rockMat) throw new Exception("run the material step first (rock material)");
            var rec = new JObject { ["utc"] = DateTime.UtcNow.ToString("O") };
            var root = new GameObject(RootName).transform; root.SetParent(berms, false);
            var groundGo = Find(scene, "Outer Berms/Berms ground");
            int layer = groundGo ? groundGo.gameObject.layer : 0;
            var staticFlags = groundGo ? GameObjectUtility.GetStaticEditorFlags(groundGo.gameObject) : (StaticEditorFlags)0;

            // ---- generated relief chunks (earthworks, craters, outcrops)
            AssetDatabase.ImportAsset(Glb, ImportAssetOptions.ForceSynchronousImport);
            var meshes = AssetDatabase.LoadAllAssetsAtPath(Glb).OfType<Mesh>().ToDictionary(m => m.name);
            if (meshes.Count == 0) throw new Exception("no meshes in " + Glb);
            var place = (JObject)Json("placements.json");
            var groups = new Dictionary<string, Transform>();
            Transform Group(string n) { if (!groups.TryGetValue(n, out var g)) { g = new GameObject(n).transform; g.SetParent(root, false); groups[n] = g; } return g; }
            int chunks = 0; long t0 = 0, t1 = 0; var missingMeshes = new List<string>();
            foreach (JObject c in place["chunks"])
            {
                // a chunk has one or more parts (outcrops: rock walls + a cap/apron on the ground material); each part has
                // LOD0/LOD1 meshes "<name><suffix>_LOD0/1"; one collider "<name>_COL"; shadows through LOD1 proxies
                var name = (string)c["name"]; var group = (string)c["group"];
                var parts = c["parts"] is JArray pa ? pa.Cast<JObject>().ToList() : new List<JObject> { new JObject { ["suffix"] = "", ["material"] = c["material"], ["shadows"] = c["shadows"] } };
                if (!meshes.ContainsKey(name + (string)parts[0]["suffix"] + "_LOD0")) { missingMeshes.Add(name); continue; }
                meshes.TryGetValue(name + "_COL", out var mc);
                var chunk = new GameObject(name).transform; chunk.SetParent(Group(group), false);
                GameObjectUtility.SetStaticEditorFlags(chunk.gameObject, staticFlags); chunk.gameObject.layer = layer;
                MeshRenderer Part(string n, Mesh m, Material mat, ShadowCastingMode sh)
                {
                    var go = new GameObject(n, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(chunk, false);
                    go.GetComponent<MeshFilter>().sharedMesh = m; var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = mat;
                    r.shadowCastingMode = sh; r.receiveShadows = true; go.layer = layer;
                    GameObjectUtility.SetStaticEditorFlags(go, staticFlags);
                    return r;
                }
                var lod0 = new List<Renderer>(); var lod1 = new List<Renderer>(); var shadow = new List<Renderer>();
                foreach (var pt in parts)
                {
                    var sfx = (string)pt["suffix"]; var mat = (string)pt["material"] == "rock" ? rockMat : v3;
                    if (!meshes.TryGetValue(name + sfx + "_LOD0", out var m0)) { missingMeshes.Add(name + sfx); continue; }
                    meshes.TryGetValue(name + sfx + "_LOD1", out var m1);
                    var tag = sfx.Length > 0 ? sfx.TrimStart('_') + " " : "";
                    lod0.Add(Part(tag + "LOD0", m0, mat, ShadowCastingMode.Off)); t0 += m0.triangles.Length / 3;
                    if (m1) { lod1.Add(Part(tag + "LOD1", m1, mat, ShadowCastingMode.Off)); t1 += m1.triangles.Length / 3; }
                    if ((bool)pt["shadows"]) shadow.Add(Part(tag + "Shadow", m1 ? m1 : m0, mat, ShadowCastingMode.ShadowsOnly));
                }
                if (lod0.Count == 0) { Object.DestroyImmediate(chunk.gameObject); continue; }
                var lg = chunk.gameObject.AddComponent<LODGroup>();
                float cull = (float)c["cull"];
                lg.SetLODs(lod1.Count > 0
                    ? new[] { new LOD((float)c["lod1"], lod0.Concat(shadow).ToArray()), new LOD(cull, lod1.Concat(shadow).ToArray()) }
                    : new[] { new LOD(cull, lod0.Concat(shadow).ToArray()) });
                var bnd = lod0[0].bounds; foreach (var r in lod0) bnd.Encapsulate(r.bounds);
                lg.size = (float)c["size"]; lg.localReferencePoint = bnd.center;
                if (mc)
                {
                    var cg = new GameObject("Collider"); cg.transform.SetParent(chunk, false); cg.layer = layer; cg.isStatic = true;
                    cg.AddComponent<MeshCollider>().sharedMesh = mc;
                }
                chunks++;
            }
            rec["chunks"] = new JObject { ["count"] = chunks, ["lod0Triangles"] = t0, ["lod1Triangles"] = t1, ["missing"] = new JArray(missingMeshes) };
            Physics.SyncTransforms();

            // ---- ground height for prefabs: expanse tiles, the old ground and this pass's relief colliders
            var groundCols = tiles.GetComponentsInChildren<MeshCollider>(true).Cast<Collider>().ToList();
            if (groundGo && groundGo.GetComponent<MeshCollider>()) groundCols.Add(groundGo.GetComponent<MeshCollider>());
            groundCols.AddRange(root.GetComponentsInChildren<MeshCollider>(true));
            float GroundY(float x, float z)
            {
                var ray = new Ray(new Vector3(x, 300, z), Vector3.down); float best = float.NegativeInfinity;
                foreach (var c in groundCols) if (c && c.Raycast(ray, out var hit, 600) && hit.point.y > best) best = hit.point.y;
                return float.IsNegativeInfinity(best) ? 0 : best;
            }

            // ---- prefab instances (wreckage, clusters)
            int placed = 0, boxes = 0; var missingPrefabs = new List<string>();
            var clusterRoots = new Dictionary<string, Transform>();
            foreach (JObject p in place["prefabs"])
            {
                var path = "Assets/AthenHill/Prefabs/" + (string)p["prefab"] + ".prefab";
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (!asset) { missingPrefabs.Add(path); continue; }
                var gname = (string)p["group"]; var cname = (string)p["cluster"];
                var key = gname + "/" + cname;
                if (!clusterRoots.TryGetValue(key, out var cr)) { cr = new GameObject(cname).transform; cr.SetParent(Group(gname), false); clusterRoots[key] = cr; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, scene); go.transform.SetParent(cr, false);
                float x = (float)p["x"], z = (float)p["z"], s = (float)p["scale"];
                float y = GroundY(x, z) - (float)p["sink"];
                go.transform.SetPositionAndRotation(new Vector3(x, y, z), Quaternion.Euler((float)p["pitch"], (float)p["yaw"], (float)p["roll"]));
                go.transform.localScale = Vector3.one * s;
                bool sh = (bool)p["shadows"];
                foreach (var r in go.GetComponentsInChildren<Renderer>(true)) if (!sh) r.shadowCastingMode = ShadowCastingMode.Off;
                var col = (string)p["collider"];
                if (col == "off") foreach (var c in go.GetComponentsInChildren<Collider>(true)) c.enabled = false;
                else if (col == "box" && go.GetComponentsInChildren<Collider>(true).Length == 0) { AddBox(go); boxes++; }
                if (!go.GetComponentInChildren<LODGroup>(true))
                {   // kit pieces without LODs (DP_CrashedDrone, DP_DeadWorker): cull them by screen size
                    var lg = go.AddComponent<LODGroup>();
                    var rs = go.GetComponentsInChildren<Renderer>(true);
                    lg.SetLODs(new[] { new LOD((float)p["cull"], rs) }); lg.RecalculateBounds();
                }
                PrefabUtility.RecordPrefabInstancePropertyModifications(go.transform);
                placed++;
            }
            rec["prefabs"] = new JObject { ["placed"] = placed, ["boxColliders"] = boxes, ["missing"] = new JArray(missingPrefabs) };

            // ---- tile material
            var swapped = new JArray();
            foreach (var r in tiles.GetComponentsInChildren<MeshRenderer>(true))
                if (r.sharedMaterial == v2 || r.sharedMaterial == v3) { r.sharedMaterial = v3; swapped.Add(PathOf(r.transform)); }
            rec["tilesSwapped"] = swapped.Count;

            // ---- footsteps
            rec["footsteps"] = ApplyFootsteps(true);

            // ---- review cameras
            var camRoot = new GameObject(CamRootName).transform; camRoot.SetParent(root, false);
            int nc = 0;
            foreach (JObject c in Json("review_cameras.json")["cameras"])
            {
                var go = new GameObject((string)c["name"]); go.transform.SetParent(camRoot, false);
                var pos = c["pos"].Select(v => (float)v).ToArray(); var tg = c["target"].Select(v => (float)v).ToArray();
                go.transform.position = new Vector3(pos[0], pos[1], pos[2]); go.transform.LookAt(new Vector3(tg[0], tg[1], tg[2]));
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = (float)c["fov"]; cam.nearClipPlane = .05f; cam.farClipPlane = 1600;
                nc++;
            }
            rec["cameras"] = nc;
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "install.json", rec.ToString(Formatting.Indented));
            return $"install: {chunks} relief chunks ({t0} / {t1} tris), {placed} prefabs, {swapped.Count} tiles, {nc} cameras";
        }

        static void AddBox(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true).Where(r => !(r is ParticleSystemRenderer)).ToArray(); if (rs.Length == 0) return;
            var inv = go.transform.worldToLocalMatrix; Bounds? lb = null;
            foreach (var r in rs)
            {
                var b = r.bounds;
                for (int k = 0; k < 8; k++)
                {
                    var c = b.center + Vector3.Scale(b.extents, new Vector3((k & 1) == 0 ? -1 : 1, (k & 2) == 0 ? -1 : 1, (k & 4) == 0 ? -1 : 1));
                    var l = inv.MultiplyPoint3x4(c);
                    if (lb == null) lb = new Bounds(l, Vector3.zero); else { var t = lb.Value; t.Encapsulate(l); lb = t; }
                }
            }
            var bc = go.AddComponent<BoxCollider>(); bc.center = lb.Value.center; bc.size = lb.Value.size * .85f;
        }

        /// Footstep surfaces over the bowl from footsteps.json (written by masks.py), or cleared.
        static JObject ApplyFootsteps(bool on)
        {
            var fa = Object.FindAnyObjectByType<FootstepAudio>(FindObjectsInactive.Include);
            if (!fa) return new JObject { ["error"] = "no FootstepAudio" };
            if (on)
            {
                var j = Json("footsteps.json");
                var rect = j["rect"].Select(v => (float)v).ToArray();
                fa.varietyRect = new Vector4(rect[0], rect[1], rect[2], rect[3]);
                fa.varietyWidth = (int)j["width"]; fa.varietyHeight = (int)j["height"];
                fa.varietySurfaces = Convert.FromBase64String((string)j["cells"]);
                fa.varietyColliders = j["colliders"].Select(v => (string)v).ToArray();
            }
            else { fa.varietyWidth = 0; fa.varietyHeight = 0; fa.varietySurfaces = new byte[0]; }
            EditorUtility.SetDirty(fa);
            if (PrefabUtility.IsPartOfPrefabInstance(fa)) PrefabUtility.RecordPrefabInstancePropertyModifications(fa);
            return new JObject { ["path"] = PathOf(fa.transform), ["width"] = fa.varietyWidth, ["height"] = fa.varietyHeight, ["cells"] = fa.varietySurfaces.Length };
        }

        // ------------------------------------------------------------------ toggle / rollback / uninstall
        public static string Toggle(bool on, bool save = true)
        {
            var scene = OpenScene();
            var r = SetState(scene, on);
            if (save) { EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
            return r;
        }

        static string SetState(Scene scene, bool on)
        {
            var root = Find(scene, "Outer Berms/" + RootName);
            if (root) root.gameObject.SetActive(on);
            var v2 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV2); var v3 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV3);
            int n = 0;
            var tiles = Find(scene, TilesPath);
            if (tiles && v2 && v3) foreach (var mr in tiles.GetComponentsInChildren<MeshRenderer>(true))
                    if (mr.sharedMaterial == (on ? v2 : v3)) { mr.sharedMaterial = on ? v3 : v2; n++; }
            var fs = ApplyFootsteps(on && root);
            return $"{(on ? "on" : "off")}: root {(root ? "found" : "missing")}, {n} tile materials switched, footsteps {fs["cells"]}";
        }

        public static string Uninstall()
        {
            var scene = OpenScene(); SetState(scene, false);
            var root = Find(scene, "Outer Berms/" + RootName); if (root) Object.DestroyImmediate(root.gameObject);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "uninstalled";
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            var scene = OpenScene(); Physics.SyncTransforms();
            var r = new JObject { ["utc"] = DateTime.UtcNow.ToString("O") };
            var problems = new JArray();
            var root = Find(scene, "Outer Berms/" + RootName);
            r["installed"] = root != null; r["active"] = root && root.gameObject.activeInHierarchy;
            if (!root) problems.Add("root missing");
            var v3 = AssetDatabase.LoadAssetAtPath<Material>(GroundMatV3);
            var tiles = Find(scene, TilesPath);
            var tileRs = tiles ? tiles.GetComponentsInChildren<MeshRenderer>(true) : new MeshRenderer[0];
            r["tiles"] = tileRs.Length; r["tilesOnV3"] = tileRs.Count(t => t.sharedMaterial == v3);
            r["materialShader"] = v3 ? v3.shader.name : null;
            if (v3 && (!v3.GetTexture("_VarSplatA") || !v3.GetTexture("_VarSplatB"))) problems.Add("V3 material lacks its masks");
            if (root)
            {
                var rends = root.GetComponentsInChildren<Renderer>(true);
                int missingMat = rends.Count(x => x.sharedMaterials.Any(m => !m));
                int missingScripts = root.GetComponentsInChildren<Transform>(true).Sum(t => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
                var insts = root.GetComponentsInChildren<Transform>(true).Where(t => PrefabUtility.IsOutermostPrefabInstanceRoot(t.gameObject)).ToArray();
                int broken = insts.Count(t => PrefabUtility.IsPrefabAssetMissing(t.gameObject) || !PrefabUtility.GetCorrespondingObjectFromSource(t.gameObject));
                r["renderers"] = rends.Length; r["missingMaterials"] = missingMat; r["missingScripts"] = missingScripts;
                r["prefabInstances"] = insts.Length; r["brokenPrefabLinks"] = broken;
                if (missingMat > 0) problems.Add($"{missingMat} renderers with missing materials");
                if (missingScripts > 0) problems.Add($"{missingScripts} missing scripts");
                if (broken > 0) problems.Add($"{broken} broken prefab links");
                var groups = new JObject();
                foreach (Transform g in root) groups[g.name] = new JObject { ["children"] = g.childCount, ["renderers"] = g.GetComponentsInChildren<Renderer>(true).Length, ["colliders"] = g.GetComponentsInChildren<Collider>(true).Count(c => c.enabled) };
                r["groups"] = groups;
                long lod0 = 0, lod1 = 0;
                foreach (var lg in root.GetComponentsInChildren<LODGroup>(true))
                {
                    var lods = lg.GetLODs();
                    if (lods.Length > 0) lod0 += Tris(lods[0].renderers);
                    if (lods.Length > 1) lod1 += Tris(lods[1].renderers);
                }
                r["lod0Triangles"] = lod0; r["lod1Triangles"] = lod1;
                r["shadowCasters"] = rends.Count(x => x.shadowCastingMode != ShadowCastingMode.Off);
                r["cameras"] = root.GetComponentsInChildren<Camera>(true).Length;
                // gameplay positions unchanged since the survey, and nothing of this pass on top of them
                var survey = File.Exists(Art + "survey.json") ? JObject.Parse(File.ReadAllText(Art + "survey.json")) : null;
                var moved = new JArray(); var crowded = new JArray();
                var myCols = root.GetComponentsInChildren<Collider>(true).Where(c => c.enabled && c.gameObject.activeInHierarchy).ToArray();
                var mineSet0 = new HashSet<Collider>(myCols);
                if (survey != null)
                {
                    var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).GroupBy(t => PathOf(t), StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.First(), StringComparer.Ordinal);
                    foreach (JObject m in survey["markers"])
                    {
                        var p = (string)m["path"]; var kind = (string)m["kind"];
                        if (kind == "droid") continue;     // droids move at runtime only; spawns are the authority
                        if (!all.TryGetValue(p, out var t)) { moved.Add("missing " + p); continue; }
                        var pos = m["pos"].Select(v => (float)v).ToArray(); var want = new Vector3(pos[0], pos[1], pos[2]);
                        if ((t.position - want).sqrMagnitude > 1e-4f) moved.Add($"moved {p}");
                        float clear = kind == "spawn" ? 3f : kind == "salvage" || kind == "interactable" || kind == "loot" ? 2.5f : kind == "landmark" ? 2f : 0f;
                        if (clear > 0)
                        {   // non-convex mesh colliders have no ClosestPoint: test overlap of a capsule (0.3-1.8 m above the marker)
                            var near = Physics.OverlapCapsule(t.position + Vector3.up * (.3f + clear), t.position + Vector3.up * Mathf.Max(1.8f, .3f + clear), clear, ~0, QueryTriggerInteraction.Ignore);
                            var hit = near.FirstOrDefault(c => mineSet0.Contains(c));
                            if (hit) crowded.Add($"{kind} {p} within {clear} m of {PathOf(hit.transform)}");
                        }
                    }
                }
                r["gameplayMoved"] = moved; r["gameplayCrowded"] = crowded;
                // droid's-eye: from each spawn's eye (1.4 m) to the chest (1.2 m over the ground) of a player on rings
                // at 18 m and 30 m; how often is the first blocking hit this pass's geometry (cover) rather than open air
                // or something that was already there
                if (survey != null && root.gameObject.activeInHierarchy)
                {
                    var mineSet = new HashSet<Collider>(myCols);
                    var eyes = new JArray(); int total = 0, byMine = 0, byOther = 0;
                    foreach (JObject m in survey["markers"].Where(x => (string)x["kind"] == "spawn"))
                    {
                        var pos = m["pos"].Select(v => (float)v).ToArray(); var eye = new Vector3(pos[0], pos[1] + 1.4f, pos[2]);
                        int t = 0, mineN = 0, otherN = 0;
                        foreach (var ring in new[] { 18f, 30f })
                            for (int k = 0; k < 36; k++)
                            {
                                var dir = Quaternion.Euler(0, k * 10, 0) * Vector3.forward;
                                var p = new Vector3(pos[0], 0, pos[2]) + dir * ring;
                                if (!Physics.Raycast(p + Vector3.up * 80, Vector3.down, out var gh, 200, ~0, QueryTriggerInteraction.Ignore)) continue;
                                var chest = gh.point + Vector3.up * 1.2f; var d = chest - eye; t++;
                                var hits = Physics.RaycastAll(eye, d.normalized, d.magnitude - .3f, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance);
                                foreach (var h in hits)
                                {
                                    if (h.collider.GetComponentInParent<FeralDroid>() || h.collider.GetComponentInParent<PlayerMotor>()) continue;
                                    if (mineSet.Contains(h.collider)) mineN++; else otherN++;
                                    break;
                                }
                            }
                        total += t; byMine += mineN; byOther += otherN;
                        float share = t > 0 ? mineN / (float)t : 0;
                        if (share > 0.15f) eyes.Add(new JObject { ["spawn"] = (string)m["path"], ["blockedByPass"] = Math.Round(share, 3), ["blockedByOther"] = Math.Round(t > 0 ? otherN / (float)t : 0, 3) });
                    }
                    r["droidsEye"] = new JObject { ["rays"] = total, ["blockedByPass"] = byMine, ["blockedByOther"] = byOther, ["spawnsOver15pc"] = eyes };
                }
                foreach (var x in moved) problems.Add((string)x);
                foreach (var x in crowded) problems.Add((string)x);
            }
            var fa = Object.FindAnyObjectByType<FootstepAudio>(FindObjectsInactive.Include);
            r["footsteps"] = fa ? new JObject { ["width"] = fa.varietyWidth, ["height"] = fa.varietyHeight, ["cells"] = fa.varietySurfaces.Length, ["ok"] = fa.varietySurfaces.Length == fa.varietyWidth * fa.varietyHeight } : null;
            if (root && root.gameObject.activeSelf && (!fa || fa.varietyWidth == 0)) problems.Add("footstep variety map not applied");
            r["problems"] = problems; r["pass"] = problems.Count == 0;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", r.ToString(Formatting.Indented));
            return $"verify: {(problems.Count == 0 ? "PASS" : "FAIL " + problems.Count)}";
        }

        static long Tris(Renderer[] rs)
        {
            long n = 0;
            foreach (var x in rs) if (x && x.TryGetComponent<MeshFilter>(out var mf) && mf.sharedMesh && x.shadowCastingMode != ShadowCastingMode.ShadowsOnly) n += mf.sharedMesh.triangles.Length / 3;
            return n;
        }

        // ------------------------------------------------------------------ capture (graphics)
        /// capture:HOUR:cam+cam[:before|after|both]. Poses come from review_cameras.json (so "before" works on a scene
        /// without this pass) or from scene cameras of that name. "before"/"after" switch the pass in memory only; the
        /// scene is never saved. Files: Evidence/editor/&lt;mode&gt;/&lt;cam&gt;_&lt;HH.h&gt;.png. At most six cameras per run.
        static int captured;
        public static string Capture(string hourText, string camList, string mode)
        {
            var names = camList.Split('+');
            captured = Math.Max(captured, names.Length);
            if (names.Length > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            float hour = float.Parse(hourText, Inv);
            var scene = OpenScene();
            var poses = Json("review_cameras.json")["cameras"].ToDictionary(c => (string)c["name"], c => (JObject)c);
            ShaderUtil.allowAsyncCompilation = false;
            var modes = mode == "both" ? new[] { "before", "after" } : new[] { mode };
            var log = new List<string>();
            foreach (var m in modes)
            {
                if (m == "before" || m == "after") SetState(scene, m == "after");
                var specs = names.Select(n =>
                {
                    if (poses.TryGetValue(n, out var c))
                    {
                        string F(JToken a) => string.Join(",", a.Select(v => ((float)v).ToString(Inv)));
                        return $"{n}:{F(c["pos"])}:{F(c["target"])}:{((float)c["fov"]).ToString(Inv)}";
                    }
                    return n;
                }).ToArray();
                log.Add(Render(hour, Path.Combine(Evidence, "editor", m), specs));
            }
            return string.Join(" | ", log);
        }

        /// DuskStartPass.Preview with the gameplay far clip (1,600 m) for views across the bowl.
        static string Render(float hour, string outDir, string[] cameras)
        {
            var clock = Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(hour);
            var key = clock.keyLight; var fill = clock.skyFill;
            var kRot = key.transform.rotation;
            var skyMat = new Material(clock.timeAwareSky);
            VolumeProfile tmp = null; var shared = clock.gradingVolume ? clock.gradingVolume.sharedProfile : null;
            key.transform.rotation = Quaternion.Euler(f.keyEuler); key.color = f.keyColor; key.intensity = f.keyIntensity;
            if (fill) { fill.color = f.fillColor; fill.intensity = f.fillIntensity; }
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator;
            RenderSettings.ambientGroundColor = f.ambientGround; RenderSettings.fogColor = f.fogColor;
            Shader.SetGlobalVector("_AthenTerrainTime", new Vector4(1, TerrainTimeLighting.AuthoredShadowWeight(kRot, key.transform.rotation, f.sunVisibility), 0, 0));
            Shader.SetGlobalVector("_AthenTerrainHazeScale", TerrainTimeLighting.HazeScale(RenderSettings.fogColor, f.fogColor, QualitySettings.activeColorSpace == ColorSpace.Linear));
            skyMat.SetColor("_Zenith", f.skyZenith); skyMat.SetColor("_Middle", f.skyMiddle); skyMat.SetColor("_Horizon", f.skyHorizon);
            skyMat.SetColor("_CloudLight", f.cloudLight); skyMat.SetColor("_CloudShade", f.cloudShade); skyMat.SetColor("_RidgeColor", f.ridgeColor);
            skyMat.SetFloat("_Exposure", f.skyExposure); skyMat.SetFloat("_SunVisibility", f.sunVisibility); skyMat.SetVector("_SunDirection", -key.transform.forward);
            RenderSettings.skybox = skyMat; RenderSettings.sun = key;
            if (shared)
            {
                tmp = ScriptableObject.CreateInstance<VolumeProfile>();
                foreach (var comp in shared.components) tmp.components.Add(Object.Instantiate(comp));
                if (!tmp.TryGet(out UnityEngine.Rendering.Universal.ColorAdjustments ca)) ca = tmp.Add<UnityEngine.Rendering.Universal.ColorAdjustments>();
                ca.postExposure.overrideState = true; ca.postExposure.value = f.postExposure; clock.gradingVolume.sharedProfile = tmp;
            }
            var main = GameObject.Find("MainCamera").GetComponent<Camera>();
            var go = new GameObject("__bv") { hideFlags = HideFlags.DontSave }; var cam = go.AddComponent<Camera>(); cam.CopyFrom(main);
            var src = main.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            var dst = go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
            if (src) { dst.renderPostProcessing = src.renderPostProcessing; dst.antialiasing = src.antialiasing; dst.renderShadows = true; }
            cam.enabled = false; cam.nearClipPlane = .05f; cam.farClipPlane = 1600;
            var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 }; var tex = new Texture2D(1920, 1080, TextureFormat.RGB24, false);
            Directory.CreateDirectory(outDir);
            var done = new List<string>();
            foreach (var spec in cameras)
            {
                string name;
                if (spec.Contains(':'))
                {
                    var p = spec.Split(':'); name = p[0];
                    Vector3 Vec(string s) { var a = s.Split(',').Select(x => float.Parse(x, Inv)).ToArray(); return new Vector3(a[0], a[1], a[2]); }
                    go.transform.position = Vec(p[1]); go.transform.LookAt(Vec(p[2])); cam.fieldOfView = float.Parse(p[3], Inv);
                }
                else
                {
                    name = spec; var c = GameObject.Find(spec); if (!c) { done.Add("missing " + spec); continue; }
                    go.transform.SetPositionAndRotation(c.transform.position, c.transform.rotation); cam.fieldOfView = c.GetComponent<Camera>().fieldOfView;
                }
                cam.targetTexture = rt;
                for (int k = 0; k < 2; k++) cam.Render();
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0); tex.Apply();
                File.WriteAllBytes(Path.Combine(outDir, $"{name}_{hour.ToString("00.0", Inv)}.png"), tex.EncodeToPNG()); done.Add(name);
            }
            RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(go); rt.Release();
            if (shared) clock.gradingVolume.sharedProfile = shared;
            if (tmp) { foreach (var comp in tmp.components) Object.DestroyImmediate(comp); Object.DestroyImmediate(tmp); }
            return outDir + ": " + string.Join(",", done);
        }

        // ------------------------------------------------------------------ batch
        /// -executeMethod AthenHill.Editor.BermsVarietyPass20261120.RunBatch --steps survey|material|install|verify|toggle:on|toggle:off|rollback|uninstall
        /// (graphics: capture:HOUR:cam+cam[:before|after|both]).
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "--steps");
            var steps = i >= 0 ? args[i + 1].Split(',') : new[] { "verify" };
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "shaderinfo" => ShaderInfo(),
                        "cost" => Cost(parts[1]),
                        "material" => BuildMaterial(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "toggle" => Toggle(parts[1] == "on"),
                        "rollback" => Toggle(false),
                        "uninstall" => Uninstall(),
                        "capture" => Capture(parts[1], parts[2], parts.Length > 3 ? parts[3] : "after"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("BermsVarietyPass20261120 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
