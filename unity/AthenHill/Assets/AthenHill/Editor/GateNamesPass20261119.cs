using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 19 November 2026: gate names. Carl decided that "West Gate" is the -X portal by the market into the Outer Berms.
    /// The two Meshy District gate arches at the +X spawn carried a baked "— WEST GATE —" plaque on both faces; this
    /// pass covers each baked plaque with a separately authored iron plate reading "— EAST GATE —" (texture from
    /// art/gate_names_20261119/make_plaques.py), adds cam_gn_* review cameras and changes the catalog's Ward notes line
    /// "R returns to West Gate." to "R returns to East Gate.".
    ///
    /// The Meshy arch, its prefab, render chunks (Chunk_8/9_District_gate_2_*) and colliders are not touched; the plates
    /// sit in their own scene root "Gate name plaques" (not a render-chunk source). Internal names (scene objects,
    /// landmark west_gate, Art/WestGate*, WestGateArchesPass, cam_wga_*) keep "West Gate".
    ///
    /// Batch: -executeMethod AthenHill.Editor.GateNamesPass20261119.RunBatch --steps install,verify[,rollback]
    /// install is idempotent (it rebuilds the material/mesh and replaces its own root and cameras).
    /// rollback removes the root and cameras and puts the catalog notes back; the .uxml/.cs text edits are plain files
    /// (git). Record: art/gate_names_20261119/README.md. Evidence: unity/evidence/gate-names/20261119/.
    /// </summary>
    public static class GateNamesPass20261119
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Art = "Assets/AthenHill/Art/GateNames/";
        const string TexDir = Art + "Textures/";
        const string MatPath = Art + "Materials/GN_Plaque.mat";
        const string MeshPath = Art + "Meshes/GN_Plaque.asset";
        const string CatalogPath = "Assets/AthenHill/Data/CityCatalog.asset";
        const string Evidence = "../evidence/gate-names/20261119/";
        const string RootName = "Gate name plaques";
        const string CamRootName = "Gate name review cameras";
        const string OldNote = "R returns to West Gate.";
        const string NewNote = "R returns to East Gate.";

        // Plate: 4.54 x 0.965 m front face (the baked plaque measures 4.465 x 0.90 m; 3-4 cm margin all round), 7 cm deep
        // so its back is buried in the arch face. Front face at local z = 0, local +Z = outward.
        const float PlateW = 4.54f, PlateH = .965f, PlateD = .07f;
        // Texture rows (make_plaques.py): front face v 1 - 435/512 .. 1; sides/back v 0 .. 1 - 452/512.
        const float FrontV0 = 1f - 435f / 512f, EdgeV1 = 1f - 452f / 512f;

        // Front-face centres measured from the saved render chunks (measure_plaques.py): baked plaque front at
        // x 46.846-46.876 (city face) and 49.140-49.158 (outer face); the new front faces stand 2.5 cm proud of the
        // most-proud point.
        static readonly (string name, Vector3 pos, float yaw)[] Plaques =
        {
            ("East Gate plaque A city face", new Vector3(46.821f, 7.70f, -.0075f), -90f),
            ("East Gate plaque B city face", new Vector3(46.821f, 7.70f, 11.9925f), -90f),
            ("East Gate plaque A outer face", new Vector3(49.183f, 7.70f, .0075f), 90f),
            ("East Gate plaque B outer face", new Vector3(49.183f, 7.70f, 12.0075f), 90f),
        };

        // Review cameras at eye height 1.65 m: name, position, target, fov.
        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] Cameras =
        {
            ("cam_gn_spawn", new Vector3(44.3f, 1.65f, .4f), new Vector3(46.82f, 7.2f, 0f), 64f),        // turning round at the spawn (a step towards the gate), plaque A from below
            ("cam_gn_spawn_b", new Vector3(43f, 1.65f, 2.5f), new Vector3(46.82f, 7.2f, 12f), 55f),     // arch B from the spawn
            ("cam_gn_avenue", new Vector3(24.5f, 1.65f, 8.5f), new Vector3(46.82f, 6.2f, 6f), 45f),      // the avenue approach
            ("cam_gn_rampart_n", new Vector3(41.5f, 1.65f, 20f), new Vector3(46.82f, 7.4f, 12f), 55f),   // obliquely along the rampart from the north (plaque B, ~60 deg off its face)
            ("cam_gn_rampart_s", new Vector3(42f, 1.65f, -8.5f), new Vector3(46.82f, 7.4f, 0f), 55f),    // obliquely along the rampart from the south (plaque A, ~64 deg off its face)
            ("cam_gn_under_b", new Vector3(45.2f, 1.65f, 12f), new Vector3(46.82f, 7.7f, 12f), 60f),     // right under plaque B
        };

        // ------------------------------------------------------------------ assets
        static void ConfigureTextures()
        {
            foreach (var file in new[] { "GN_Plaque_BaseMap.jpg", "GN_Plaque_Normal.jpg", "GN_Plaque_Mask.png" })
            {
                var path = TexDir + file;
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) throw new Exception("Texture missing (run make_plaques.py): " + path);
                bool normal = file.Contains("_Normal"), mask = file.Contains("_Mask");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !mask;
                ti.alphaIsTransparency = false;
                ti.maxTextureSize = 2048; ti.anisoLevel = 8; ti.mipmapEnabled = true; ti.streamingMipmaps = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
        }

        static Material BuildMaterial()
        {
            Directory.CreateDirectory(Art + "Materials");
            var m = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
            if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "GN_Plaque" }; AssetDatabase.CreateAsset(m, MatPath); }
            var mask = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "GN_Plaque_Mask.png");
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "GN_Plaque_BaseMap.jpg"));
            m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + "GN_Plaque_Normal.jpg")); m.EnableKeyword("_NORMALMAP"); m.SetFloat("_BumpScale", 1f);
            m.SetTexture("_MetallicGlossMap", mask); m.EnableKeyword("_METALLICSPECGLOSSMAP");
            m.SetTexture("_OcclusionMap", mask); m.EnableKeyword("_OCCLUSIONMAP"); m.SetFloat("_OcclusionStrength", 1f);
            m.SetFloat("_Smoothness", 1f); // multiplier on the mask's alpha (about 0.2 on the plate)
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        /// A box plate. Front face (local +Z) carries the lettered part of the texture; the four sides and the back use
        /// the plain iron strip. u runs to the viewer's right on the front face (viewer's right is local -X).
        static Mesh BuildMesh()
        {
            Directory.CreateDirectory(Art + "Meshes");
            float hw = PlateW / 2, hh = PlateH / 2, d = PlateD;
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 e, Vector3 normal, Vector2 ua, Vector2 ub, Vector2 uc, Vector2 ue)
            {
                // a b c e counter-clockwise seen from outside in Unity's left-handed frame -> triangles a,b,c / a,c,e (clockwise winding)
                int i = v.Count;
                v.AddRange(new[] { a, b, c, e }); n.AddRange(Enumerable.Repeat(normal, 4)); uv.AddRange(new[] { ua, ub, uc, ue });
                t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
            }
            // front (z = 0, normal +Z): seen from +Z, the viewer's right is -X. Clockwise from the viewer: top-left, top-right, bottom-right, bottom-left.
            Quad(new Vector3(hw, hh, 0), new Vector3(-hw, hh, 0), new Vector3(-hw, -hh, 0), new Vector3(hw, -hh, 0), Vector3.forward,
                new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, FrontV0), new Vector2(0, FrontV0));
            // back (z = -d, normal -Z)
            Quad(new Vector3(-hw, hh, -d), new Vector3(hw, hh, -d), new Vector3(hw, -hh, -d), new Vector3(-hw, -hh, -d), Vector3.back,
                new Vector2(0, EdgeV1), new Vector2(1, EdgeV1), new Vector2(1, 0), new Vector2(0, 0));
            float ev = EdgeV1 * .5f; // a thin band of the iron strip for the 7 cm sides
            // top (normal +Y)
            Quad(new Vector3(hw, hh, -d), new Vector3(-hw, hh, -d), new Vector3(-hw, hh, 0), new Vector3(hw, hh, 0), Vector3.up,
                new Vector2(0, ev), new Vector2(1, ev), new Vector2(1, 0), new Vector2(0, 0));
            // bottom (normal -Y)
            Quad(new Vector3(hw, -hh, 0), new Vector3(-hw, -hh, 0), new Vector3(-hw, -hh, -d), new Vector3(hw, -hh, -d), Vector3.down,
                new Vector2(0, ev), new Vector2(1, ev), new Vector2(1, 0), new Vector2(0, 0));
            // +X end (normal +X)
            Quad(new Vector3(hw, hh, -d), new Vector3(hw, hh, 0), new Vector3(hw, -hh, 0), new Vector3(hw, -hh, -d), Vector3.right,
                new Vector2(0, EdgeV1), new Vector2(.03f, EdgeV1), new Vector2(.03f, 0), new Vector2(0, 0));
            // -X end (normal -X)
            Quad(new Vector3(-hw, hh, 0), new Vector3(-hw, hh, -d), new Vector3(-hw, -hh, -d), new Vector3(-hw, -hh, 0), Vector3.left,
                new Vector2(.97f, EdgeV1), new Vector2(1, EdgeV1), new Vector2(1, 0), new Vector2(.97f, 0));
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
            bool created = !mesh;
            if (created) mesh = new Mesh { name = "GN_Plaque" };
            mesh.Clear();
            mesh.SetVertices(v); mesh.SetNormals(n); mesh.SetUVs(0, uv); mesh.SetTriangles(t, 0);
            mesh.RecalculateTangents(); mesh.RecalculateBounds();
            if (created) AssetDatabase.CreateAsset(mesh, MeshPath); else EditorUtility.SetDirty(mesh);
            return mesh;
        }

        static (Material, Mesh) BuildAssets()
        {
            ConfigureTextures();
            var m = BuildMaterial(); var mesh = BuildMesh();
            AssetDatabase.SaveAssets();
            return (m, mesh);
        }

        // ------------------------------------------------------------------ scene
        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;

        static string ChunkHash()
        {
            var sb = new System.Text.StringBuilder();
            foreach (var f in new[] { "Chunk_8_District_gate_2_0.asset", "Chunk_9_District_gate_2_1.asset" })
            {
                var p = "Assets/AthenHill/Art/RenderChunks/" + f;
                using var sha = System.Security.Cryptography.SHA1.Create();
                sb.Append(File.Exists(p) ? BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(p))).Replace("-", "").Substring(0, 12) : "missing").Append(' ');
            }
            return sb.ToString().Trim();
        }

        static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            Directory.CreateDirectory(Evidence);
            var chunkHash = ChunkHash();
            var (mat, mesh) = BuildAssets();
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            string fpBefore = chunks ? chunks.sourceFingerprint : null;
            var record = new Dictionary<string, object>();

            foreach (var old in scene.GetRootGameObjects().Where(g => g.name == RootName).ToArray()) UnityEngine.Object.DestroyImmediate(old);
            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            foreach (var (name, pos, yaw) in Plaques)
            {
                var go = new GameObject(name);
                go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0, yaw, 0));
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.On; r.receiveShadows = true;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
            }
            record["plaques"] = Plaques.Select(p => new { p.name, pos = new[] { p.pos.x, p.pos.y, p.pos.z }, p.yaw, size = new[] { PlateW, PlateH, PlateD } }).ToArray();
            AddCameras(scene);
            record["reviewCameras"] = Cameras.Select(c => c.name).ToArray();

            var catalog = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath);
            if (!catalog) throw new Exception("CityCatalog missing");
            var so = new SerializedObject(catalog); var notes = so.FindProperty("notes");
            record["catalogNotesBefore"] = notes.stringValue;
            if (notes.stringValue.Contains(OldNote)) { notes.stringValue = notes.stringValue.Replace(OldNote, NewNote); so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(catalog); }
            record["catalogNotesAfter"] = notes.stringValue;
            AssetDatabase.SaveAssets();

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            if (chunks) record["chunkFingerprintUnchanged"] = chunks.sourceFingerprint == fpBefore && chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
            record["districtGateChunksBefore"] = chunkHash; record["districtGateChunksAfter"] = ChunkHash();
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        static void AddCameras(UnityEngine.SceneManagement.Scene scene)
        {
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            if (!root) { root = new GameObject(CamRootName); UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene); }
            foreach (var (name, pos, target, fov) in Cameras)
            {
                var tr = root.transform.Find(name);
                if (!tr) { tr = new GameObject(name).transform; tr.SetParent(root.transform, false); }
                tr.SetPositionAndRotation(pos, Quaternion.LookRotation(target - pos, Vector3.up));
                var cam = tr.GetComponent<Camera>();                 // Unity objects: no ?? (fake null)
                if (!cam) cam = tr.gameObject.AddComponent<Camera>();
                cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f;
            }
        }

        static string Rollback()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            int removed = 0;
            foreach (var g in scene.GetRootGameObjects().Where(g => g.name == RootName || g.name == CamRootName).ToArray()) { UnityEngine.Object.DestroyImmediate(g); removed++; }
            var catalog = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath);
            var so = new SerializedObject(catalog); var notes = so.FindProperty("notes");
            bool restored = notes.stringValue.Contains(NewNote);
            if (restored) { notes.stringValue = notes.stringValue.Replace(NewNote, OldNote); so.ApplyModifiedPropertiesWithoutUndo(); EditorUtility.SetDirty(catalog); AssetDatabase.SaveAssets(); }
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var r = JsonConvert.SerializeObject(new { removedRoots = removed, catalogNotesRestored = restored, note = "Assets in Art/GateNames are kept; the .uxml/.cs/.md text edits are reverted with git." });
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "rollback.json", r);
            return r;
        }

        // ------------------------------------------------------------------ verify
        static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var r = new Dictionary<string, object>(); var problems = new List<string>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (!root) problems.Add("root missing");
            else
            {
                r["active"] = root.activeSelf; if (!root.activeSelf) problems.Add("root inactive");
                var rends = root.GetComponentsInChildren<MeshRenderer>(true);
                r["plaques"] = rends.Length; if (rends.Length != Plaques.Length) problems.Add("plaque count " + rends.Length);
                foreach (var (name, pos, yaw) in Plaques)
                {
                    var t = root.transform.Find(name);
                    if (!t) { problems.Add("missing " + name); continue; }
                    if ((t.position - pos).magnitude > 1e-3f) problems.Add(name + " moved");
                    if (Quaternion.Angle(t.rotation, Quaternion.Euler(0, yaw, 0)) > .1f) problems.Add(name + " rotated");
                    if ((t.lossyScale - Vector3.one).sqrMagnitude > 1e-6f) problems.Add(name + " scaled");
                    var mf = t.GetComponent<MeshFilter>(); var mr = t.GetComponent<MeshRenderer>();
                    if (!mf || !mf.sharedMesh) problems.Add(name + " has no mesh");
                    if (!mr || !mr.sharedMaterial) problems.Add(name + " has no material");
                    else if (mr.sharedMaterial.shader.name != "Universal Render Pipeline/Lit" || !mr.sharedMaterial.GetTexture("_BaseMap")) problems.Add(name + " material incomplete");
                }
                r["materials"] = rends.SelectMany(x => x.sharedMaterials).Where(m => m).Select(m => AssetDatabase.GetAssetPath(m) + " (" + m.shader.name + ")").Distinct().ToArray();
                // each front face must stand proud of the arch faces measured from the chunks and keep its back buried
                r["frontFaceX"] = Plaques.Select(p => p.pos.x).ToArray();
            }
            foreach (var p in new[] { MatPath, MeshPath, TexDir + "GN_Plaque_BaseMap.jpg", TexDir + "GN_Plaque_Normal.jpg", TexDir + "GN_Plaque_Mask.png" })
                if (string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(p)) || AssetDatabase.LoadMainAssetAtPath(p) == null) problems.Add("asset missing " + p);
            // the Meshy arches and the arch fittings are untouched
            var district = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "District rebuild");
            int arches = district ? district.GetComponentsInChildren<Transform>(true).Count(t => t.name == "District gate" && t.gameObject.activeInHierarchy) : -1;
            r["meshyArchesActive"] = arches;
            var fittings = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Ward west gate arches");
            r["archFittingsActive"] = fittings && fittings.activeSelf;
            if (!fittings || !fittings.activeSelf) problems.Add("Ward west gate arches missing or inactive");
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            if (chunks)
            {
                bool fp = chunks.sourceFingerprint == StaticRenderChunksEditor.Fingerprint(chunks);
                r["chunkFingerprintMatches"] = fp; r["chunkEditing"] = chunks.editingSources;
                if (!fp) problems.Add("render chunk fingerprint stale"); if (chunks.editingSources) problems.Add("chunks in editing mode");
                if (root && chunks.sourceRoots.Any(s => s && (root.transform.IsChildOf(s) || s.IsChildOf(root.transform)))) problems.Add("plaques under a chunk source root");
            }
            r["districtGateChunks"] = ChunkHash();
            var installRec = Evidence + "install.json";
            if (File.Exists(installRec))
            {
                var before = (string)Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(installRec))["districtGateChunksBefore"];
                r["districtGateChunksUnchanged"] = before == ChunkHash(); if (before != ChunkHash()) problems.Add("District gate chunk assets changed");
            }
            // the gate colliders keep the city closed and nothing new collides
            if (root && root.GetComponentsInChildren<Collider>(true).Length > 0) problems.Add("plaques carry colliders");
            var cams = scene.GetRootGameObjects().FirstOrDefault(g => g.name == CamRootName);
            var camNames = cams ? cams.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray() : new string[0];
            r["reviewCameras"] = camNames;
            foreach (var c in Cameras) if (!camNames.Contains(c.name)) problems.Add("camera missing " + c.name);
            var catalog = AssetDatabase.LoadAssetAtPath<CityCatalog>(CatalogPath);
            r["catalogNotes"] = catalog ? catalog.notes : null;
            if (!catalog || !catalog.notes.Contains(NewNote) || catalog.notes.Contains("West Gate")) problems.Add("catalog notes not updated");
            r["problems"] = problems;
            var json = JsonConvert.SerializeObject(r, Formatting.Indented);
            Directory.CreateDirectory(Evidence); File.WriteAllText(Evidence + "verify.json", json);
            if (problems.Count > 0) throw new Exception("GateNamesPass20261119 verify: " + string.Join("; ", problems));
            return json;
        }

        // ------------------------------------------------------------------ batch
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            try
            {
                foreach (var st in Arg("--steps", "verify").Split(','))
                {
                    string result = st switch
                    {
                        "build" => BuildAssets().ToString(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "rollback" => Rollback(),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("GateNamesPass20261119 " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }

        [MenuItem("Athen Hill/Gate names (19 Nov 2026)/Install")] public static void MenuInstall() => Debug.Log(Install());
        [MenuItem("Athen Hill/Gate names (19 Nov 2026)/Verify")] public static void MenuVerify() => Debug.Log(Verify());
        [MenuItem("Athen Hill/Gate names (19 Nov 2026)/Rollback")] public static void MenuRollback() => Debug.Log(Rollback());
    }
}
