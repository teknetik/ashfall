using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
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
    /// 5 October 2026: the player's home (Carl: "we need a place to store our loot" -> rent one of the container homes:
    /// "a locker and shelf rack as the stash, a bunk as a rest and save point"). Design and runtime: art/ward_home_20261005
    /// (PROGRESS.md, README_home.md); runtime components Scripts/Home (WardHome, HomeDoor, CameraConfineZone).
    ///
    /// Geometry: art/ward_home_20261005/home_interior.py through art/ward_buildings_20261003/author_buildings.py key
    /// `homep` -> Art/WardBuildings/Models/WallHomeP_LOD0/1/2.glb + homep.json (colliders, anchors, lights, mounts).
    /// Steps:
    ///  models     HP_* materials (Art/WardHome), re-imports the three models and builds Prefabs/WardBuildings/WallHomeP.prefab:
    ///             LODGroup (14/55/450 m like the other wall homes), the door leaf as its own child "Door leaf" pivoting
    ///             about local Y at the hinge (LOD0 leaf mesh, in LOD0 and LOD1, never static) with its closed-door
    ///             BoxCollider COL_DoorLeaf, colliders from the record, A's exterior mounts and the interior street-dressing
    ///             mounts, the porch light (Practical lights) and the interior lamps (Interior lights, rendering layer 7),
    ///             interior renderers unshadowed on the interior layer and ReflectionProbeStatic, and the gameplay
    ///             children: WardHome (root), Door (HomeDoor + locked WorldInteractable at door_centre), Locker and Bunk
    ///             interactables, Wake point, Camera zone (CameraConfineZone over interior_bounds).
    ///  install    scene root "Ward home" (re-runnable: replaces only itself) at the transform of the WallHomeA instance
    ///             "Ward building: wall homes (rust)/Wall home south 2", which goes inactive (never deleted); a WallHomeP
    ///             instance with the scene references (GameSession, FollowCamera) as overrides; InteriorLighting, an
    ///             interior reflection probe, review cameras cam_home_*; the porch light on the Ward lighting clock;
    ///             QA landmarks home_door/home_inside/home_locker/home_bunk under AthenDebugBridge.landmarks. Copies the
    ///             scene first (evidence/ward-home/20261005/scene-before-install.unity; the first copy also in rollback/).
    ///  verify     (-nographics) -> evidence/ward-home/20261005/verify.json: installed, prefab link, materials, old
    ///             instance inactive, every field wired, landmarks inside/outside, leaf collider enabled when closed,
    ///             capsule (r 0.3, h 1.8) clear door -> inside -> locker and -> bunk with the door open, and a YAML diff of
    ///             the saved scene against the pre-install copy (only this pass's objects may differ).
    ///  uninstall  removes the root, the landmarks and the circuit entries and re-activates the WallHomeA instance.
    ///  bake       (graphics) bakes the interior reflection probe (EXR clamped as in FieldSupplyShopPass).
    ///  capture:HOUR:cam+cam[:open] (graphics, at most 6 cameras per run; never saves).
    /// Batch: unity.sh LOG AthenHill.Editor.WardHomePass.RunBatch --steps models,install,verify -nographics
    /// </summary>
    public static class WardHomePass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string ModelDir = "Assets/AthenHill/Art/WardBuildings/Models/";
        const string Model = "WallHomeP";
        const string PrefabPath = "Assets/AthenHill/Prefabs/WardBuildings/WallHomeP.prefab";
        const string ArtDir = "Assets/AthenHill/Art/WardHome/";
        const string MatDir = ArtDir + "Materials/";
        const string TexDir = ArtDir + "Textures/";
        const string TexSource = "../../art/ward_home_20261005/textures/";
        const string Evidence = "../evidence/ward-home/20261005/";
        const string OldInstancePath = "Ward building: wall homes (rust)/Wall home south 2";
        public const string RootName = "Ward home";
        const string InstanceName = "Player home (WallHomeP)";
        public const uint InteriorLayer = 1u << 7;
        const float LodBias = 2f;
        static readonly float[] LodDistances = { 14f, 55f, 450f };
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        static readonly string[] MatSearch =
        {
            "Assets/AthenHill/Art/WardBuildings/Materials/", "Assets/AthenHill/Art/VanguardHall/Materials/", "Assets/AthenHill/Art/WardShops/Materials/",
            "Assets/AthenHill/Art/WestGate/Materials/", "Assets/AthenHill/Art/TrainingRange/Materials/", "Assets/AthenHill/Art/WestGateArches/Materials/",
            "Assets/AthenHill/Art/NightFacade/Materials/", "Assets/AthenHill/Art/SalvageShop/Materials/", "Assets/AthenHill/Art/FieldSupply/Materials/",
            "Assets/AthenHill/Art/WardLife/Materials/", MatDir,
        };

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "homep.json"));
        static JObject Anchor(JObject rec, string name) => (JObject)rec["anchors"][name] ?? throw new Exception("homep.json has no anchor " + name);

        static Transform FindPath(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!root) return null;
            var t = root.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Cast<Transform>().FirstOrDefault(c => c.name == parts[i]);
            return t;
        }

        static int Tris(Renderer r)
        {
            var mf = r ? r.GetComponent<MeshFilter>() : null;
            if (!mf || !mf.sharedMesh) return 0;
            int n = 0;
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) n += (int)mf.sharedMesh.GetIndexCount(s) / 3;
            return n;
        }

        // ------------------------------------------------------------------ materials
        static readonly Dictionary<string, Material> matCache = new Dictionary<string, Material>();
        static Material FindMat(string name)
        {
            name = Regex.Replace(name.Replace(" (Instance)", ""), @"\.\d+$", "");
            if (matCache.TryGetValue(name, out var m) && m) return m;
            foreach (var d in MatSearch)
            {
                m = AssetDatabase.LoadAssetAtPath<Material>(d + name + ".mat");
                if (m) { matCache[name] = m; return m; }
            }
            return null;
        }

        static Texture2D Texture(string file, bool clamp)
        {
            Directory.CreateDirectory(TexDir);
            var src = TexSource + file; var dst = TexDir + file;
            if (!File.Exists(src)) throw new Exception("texture source missing: " + src + " (art/ward_home_20261005/make_textures.py)");
            if (!File.Exists(dst) || !File.ReadAllBytes(dst).SequenceEqual(File.ReadAllBytes(src))) { File.Copy(src, dst, true); AssetDatabase.ImportAsset(dst); }
            var ti = (TextureImporter)AssetImporter.GetAtPath(dst);
            ti.textureType = TextureImporterType.Default; ti.sRGBTexture = true; ti.mipmapEnabled = true; ti.streamingMipmaps = true;
            ti.maxTextureSize = 1024; ti.textureCompression = TextureImporterCompression.CompressedHQ; ti.anisoLevel = 4;
            ti.wrapMode = clamp ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
            ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(dst);
        }

        /// New materials (README_home.md): HP_Insulation, HP_Mirror, HP_Photo, HP_Calendar, HP_Succulent.
        public static string Materials()
        {
            Directory.CreateDirectory(MatDir);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var made = new List<string>();
            void Make(string name, Color c, float smooth, float metal, Texture2D tex, float tile)
            {
                var path = MatDir + name + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                bool created = !m;
                if (created) m = new Material(lit) { name = name };
                m.SetColor("_BaseColor", c); m.SetFloat("_Smoothness", smooth); m.SetFloat("_Metallic", metal);
                m.SetTexture("_BaseMap", tex); m.SetTextureScale("_BaseMap", Vector2.one * tile);
                m.enableInstancing = true;
                if (created) { AssetDatabase.CreateAsset(m, path); made.Add(name); } else EditorUtility.SetDirty(m);
                matCache[name] = m;
            }
            Make("HP_Insulation", Color.white, .05f, 0, Texture("HP_Insulation.png", false), 2f);
            Make("HP_Mirror", new Color(.86f, .87f, .88f), .94f, 1f, null, 1f);
            Make("HP_Photo", Color.white, .55f, 0, Texture("HP_Photo.png", true), 1f);
            Make("HP_Calendar", Color.white, .15f, 0, Texture("HP_Calendar.png", true), 1f);
            Make("HP_Succulent", new Color(.33f, .43f, .30f), .45f, 0, null, 1f);
            AssetDatabase.SaveAssets();
            return "materials ok (created: " + (made.Count == 0 ? "none" : string.Join(",", made)) + ")";
        }

        // ------------------------------------------------------------------ prefab
        static bool IsInterior(string n) => n.Contains("_Interior") || n.Contains("_LockerStencil_");
        static bool IsLeaf(string n) => n.Contains("_DoorLeaf_");

        static void InteriorRenderer(Renderer r)
        {
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.renderingLayerMask |= InteriorLayer;
            r.receiveShadows = true;
            if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
        }

        public static string Models()
        {
            Materials();
            var rec = Record();
            for (int lod = 0; lod < 3; lod++) AssetDatabase.ImportAsset(ModelDir + $"{Model}_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));
            var missing = new HashSet<string>();
            var report = new Dictionary<string, object>();
            var root = new GameObject(Model);
            try
            {
                // ---- LOD holders; the leaf goes to its own pivot
                var hinge = V3(Anchor(rec, "door_hinge")["pos"]);
                var leafPivot = new GameObject("Door leaf").transform; leafPivot.SetParent(root.transform, false); leafPivot.localPosition = hinge;
                MeshRenderer leafRenderer = null;
                var levels = new List<LOD>();
                for (int lod = 0; lod < 3; lod++)
                {
                    var glb = ModelDir + $"{Model}_LOD{lod}.glb";
                    var src = AssetDatabase.LoadAssetAtPath<GameObject>(glb) ?? throw new Exception("Model not imported: " + glb);
                    var holder = new GameObject("LOD" + lod).transform; holder.SetParent(root.transform, false);
                    var rs = new List<Renderer>();
                    foreach (var mr in src.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        var mf = mr.GetComponent<MeshFilter>();
                        if (!mf || !mf.sharedMesh) continue;
                        bool leaf = IsLeaf(mr.name);
                        if (leaf && lod > 0) continue;               // one moving leaf (LOD0 mesh) serves LOD0 and LOD1
                        var go = new GameObject(mr.name);
                        var wp = src.transform.InverseTransformPoint(mr.transform.position);
                        var wr = Quaternion.Inverse(src.transform.rotation) * mr.transform.rotation;
                        if (leaf)
                        {
                            go.transform.SetParent(leafPivot, false);
                            go.transform.localPosition = wp - hinge; go.transform.localRotation = wr;
                        }
                        else { go.transform.SetParent(holder, false); go.transform.localPosition = wp; go.transform.localRotation = wr; }
                        go.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
                        var r = go.AddComponent<MeshRenderer>();
                        var slots = mr.sharedMaterials;
                        for (int i = 0; i < slots.Length; i++)
                        {
                            var m = slots[i] ? FindMat(slots[i].name) : null;
                            if (m) slots[i] = m; else missing.Add(mr.name + ":" + (slots[i] ? slots[i].name : "null"));
                        }
                        r.sharedMaterials = slots;
                        var n = mr.name;
                        bool noShadow = n.Contains("_Glass_") || n.Contains("_Sand_") || n.Contains("_Glow_") || n.Contains("_Hardware_");
                        r.shadowCastingMode = noShadow ? ShadowCastingMode.Off : ShadowCastingMode.On;
                        r.receiveShadows = true;
                        r.motionVectorGenerationMode = MotionVectorGenerationMode.Camera;
                        r.receiveGI = ReceiveGI.LightProbes; r.lightProbeUsage = LightProbeUsage.BlendProbes;
                        if (IsInterior(n)) InteriorRenderer(r);
                        if (leaf) leafRenderer = r;
                        rs.Add(r);
                    }
                    if (lod == 1 && leafRenderer) rs.Add(leafRenderer);
                    if (rs.Count == 0) throw new Exception("no renderers in " + glb);
                    report["LOD" + lod] = rs.Sum(Tris);
                    levels.Add(new LOD(.5f / (lod + 1), rs.ToArray()));
                }
                if (!leafRenderer) throw new Exception("no door leaf in " + Model + "_LOD0.glb");
                var g = root.AddComponent<LODGroup>();
                g.SetLODs(levels.ToArray()); g.fadeMode = LODFadeMode.None; g.RecalculateBounds();
                float H(float d) => Mathf.Clamp(g.size * LodBias / (2f * d * Mathf.Tan(30f * Mathf.Deg2Rad)), .003f, .98f);
                for (int i = 0; i < levels.Count; i++) levels[i] = new LOD(H(LodDistances[i]), levels[i].renderers);
                for (int i = 1; i < levels.Count; i++) if (levels[i].screenRelativeTransitionHeight >= levels[i - 1].screenRelativeTransitionHeight)
                        levels[i] = new LOD(levels[i - 1].screenRelativeTransitionHeight * .5f, levels[i].renderers);
                g.SetLODs(levels.ToArray()); g.RecalculateBounds();
                report["lodCuts"] = levels.Select(l => Math.Round(l.screenRelativeTransitionHeight, 4)).ToArray();

                // ---- colliders (the leaf's on the leaf)
                var cols = new GameObject("Colliders").transform; cols.SetParent(root.transform, false);
                BoxCollider leafCol = null;
                foreach (var c in rec["colliders"])
                {
                    var name = (string)c["name"];
                    if (name == "COL_DoorLeaf")
                    {
                        var lc = new GameObject(name); lc.transform.SetParent(leafPivot, false);
                        leafCol = lc.AddComponent<BoxCollider>(); leafCol.center = V3(c["local_center"]); leafCol.size = V3(c["size"]);
                        continue;
                    }
                    var go = new GameObject(name); go.transform.SetParent(cols, false);
                    var bc = go.AddComponent<BoxCollider>(); bc.center = V3(c["center"]); bc.size = V3(c["size"]);
                }
                if (!leafCol) throw new Exception("homep.json has no COL_DoorLeaf");
                report["colliders"] = cols.childCount + 1;

                // ---- mounts: A's exterior ones, the interior street dressing (unshadowed, interior layer)
                var fit = new GameObject("Fittings").transform; fit.SetParent(root.transform, false);
                var ifit = new GameObject("Interior fittings").transform; ifit.SetParent(root.transform, false);
                int mounts = 0;
                foreach (var mnt in rec["mounts"])
                {
                    var ppath = (string)mnt["path"] ?? "Assets/AthenHill/Prefabs/WestGate/" + (string)mnt["prefab"] + ".prefab";
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(ppath);
                    if (!prefab) { missing.Add("prefab " + ppath); continue; }
                    bool inside = (bool?)mnt["interior"] == true;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                    go.name = (string)mnt["name"];
                    go.transform.SetParent(inside ? ifit : fit, false);
                    go.transform.localPosition = V3(mnt["pos"]);
                    go.transform.localRotation = Quaternion.Euler(0, (float)mnt["yaw"], 0);
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    if (inside)
                    {
                        foreach (var r in go.GetComponentsInChildren<Renderer>(true)) InteriorRenderer(r);
                        foreach (var lg in go.GetComponentsInChildren<LODGroup>(true))
                        {
                            var lods = lg.GetLODs();
                            if (lods.Length > 1 && lods[0].screenRelativeTransitionHeight < .3f) { lods[0].screenRelativeTransitionHeight = .3f; lg.SetLODs(lods); }
                        }
                    }
                    mounts++;
                }
                report["mounts"] = mounts;

                // ---- lights: the porch light on the clock, the interior lamps (layer 7, unshadowed like the shops' lamps)
                var practical = new GameObject("Practical lights").transform; practical.SetParent(root.transform, false);
                var ilights = new GameObject("Interior lights").transform; ilights.SetParent(root.transform, false);
                foreach (var xl in rec["lights"])
                {
                    bool inside = (bool?)xl["interior"] == true;
                    var lg = new GameObject((string)xl["name"]); lg.transform.SetParent(inside ? ilights : practical, false);
                    var p = V3(xl["pos"]); lg.transform.localPosition = p;
                    var l = lg.AddComponent<Light>();
                    l.type = (string)xl["type"] == "spot" ? LightType.Spot : LightType.Point;
                    if (xl["target"] != null) lg.transform.localRotation = Quaternion.LookRotation(V3(xl["target"]) - p, Vector3.up);
                    var c = xl["color"]; l.color = new Color((float)c[0], (float)c[1], (float)c[2]);
                    l.intensity = (float)xl["intensity"]; l.range = (float)xl["range"];
                    if (l.type == LightType.Spot) { l.spotAngle = (float?)xl["angle"] ?? 120f; l.innerSpotAngle = (float?)xl["inner"] ?? 80f; }
                    l.shadows = LightShadows.None;
                    if (inside) l.renderingLayerMask = (int)InteriorLayer;
                }
                report["lights"] = new { practical = practical.childCount, interior = ilights.childCount };

                // ---- gameplay children
                Transform Child(string name, Vector3 pos, float yaw = 0)
                {
                    var t = new GameObject(name).transform; t.SetParent(root.transform, false);
                    t.localPosition = pos; t.localRotation = Quaternion.Euler(0, yaw, 0); return t;
                }
                var dh = Anchor(rec, "door_hinge");
                var doorT = Child("Door", V3(Anchor(rec, "door_centre")["pos"]));
                var lockedPrompt = doorT.gameObject.AddComponent<WorldInteractable>(); lockedPrompt.prompt = "E · Locked door"; lockedPrompt.range = 2.0f;
                var door = doorT.gameObject.AddComponent<HomeDoor>();
                door.leaf = leafPivot; door.closedYaw = (float)dh["closedYaw"]; door.openYaw = (float)dh["openYaw"];
                door.openDistance = 2.4f; door.leafCollider = leafCol; door.lockedPrompt = lockedPrompt;
                var lockerT = Child("Locker", V3(Anchor(rec, "locker_use")["pos"]), (float)Anchor(rec, "locker_use")["yaw"]);
                var locker = lockerT.gameObject.AddComponent<WorldInteractable>(); locker.prompt = "E · Open the locker"; locker.range = 1.6f;
                var bunkT = Child("Bunk", V3(Anchor(rec, "bunk_use")["pos"]), (float)Anchor(rec, "bunk_use")["yaw"]);
                var bunk = bunkT.gameObject.AddComponent<WorldInteractable>(); bunk.prompt = "E · Rest on the bunk"; bunk.range = 1.6f;
                var wakeT = Child("Wake point", V3(Anchor(rec, "wake_point")["pos"]), (float)Anchor(rec, "wake_point")["yaw"]);
                var zoneT = Child("Camera zone", Vector3.zero);
                var zone = zoneT.gameObject.AddComponent<CameraConfineZone>();
                var ib = Anchor(rec, "interior_bounds"); zone.center = V3(ib["center"]); zone.size = V3(ib["size"]);
                var home = root.AddComponent<WardHome>();
                home.leasePrice = 40; home.lockerSlots = 60; home.lockerFeedsBench = true;
                home.door = door; home.locker = locker; home.bunk = bunk; home.lockerPoint = lockerT; home.wakePoint = wakeT;

                // ---- static flags: everything but lights, the moving leaf and the gameplay children
                var moving = new HashSet<Transform>(leafPivot.GetComponentsInChildren<Transform>(true));
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (t.GetComponent<Light>() || moving.Contains(t) || t == doorT || t == lockerT || t == bunkT || t == wakeT || t == zoneT || t == root.transform) continue;
                    var flags = StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic;
                    var r = t.GetComponent<Renderer>();
                    if (r && (IsInterior(t.name) || t.IsChildOf(ifit))) flags = StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic;
                    if (t.IsChildOf(ifit) && !r) flags = StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic | StaticEditorFlags.ReflectionProbeStatic;
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, flags);
                }
                // the root itself: occludee + batching (its LODGroup does not move)
                GameObjectUtility.SetStaticEditorFlags(root, StaticEditorFlags.OccludeeStatic);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
            AssetDatabase.SaveAssets();
            report["unmapped"] = missing.OrderBy(x => x).ToArray();
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(report, Formatting.Indented);
            File.WriteAllText(Evidence + "models.json", json);
            if (missing.Count > 0) throw new Exception("unmapped materials or prefabs: " + string.Join(", ", missing.Take(12)));
            return json;
        }

        // ------------------------------------------------------------------ install
        public static readonly (string name, Vector3 pos, Vector3 target, float fov)[] Cameras =
        {
            // building-local metres (root = container centre at ground, +Z = street); eye 1.62 above the ground / the 0.5 floor
            ("cam_home_street", new Vector3(0.6f, 1.62f, 7.6f), new Vector3(0.2f, 1.45f, 0f), 50),
            // in the pocket between the container face and Nanofab 2's rear pier (local x 1.2..2.55 from z 3.1): the first two
            // tries (2.6, 4.0) and (1.55, 3.1) were inside the Nanofab's colliders
            ("cam_home_door", new Vector3(2.9f, 1.62f, 2.7f), new Vector3(1.2f, 1.3f, 0.6f), 66),
            ("cam_home_inside_bunk", new Vector3(1.35f, 2.12f, 0.9f), new Vector3(-2.6f, 1.15f, -0.35f), 62),
            ("cam_home_inside_locker", new Vector3(0.7f, 2.12f, 0.8f), new Vector3(2.6f, 1.35f, -0.95f), 62),
            ("cam_home_locker", new Vector3(1.1f, 2.1f, 0.55f), new Vector3(1.12f, 1.45f, -1.0f), 50),
            ("cam_home_bunk", new Vector3(-1.25f, 1.98f, 0.5f), new Vector3(-2.45f, 0.95f, -0.75f), 55),
        };

        static (Vector3 local, string name)[] Landmarks(JObject rec)
        {
            var dc = V3(Anchor(rec, "door_centre")["pos"]);
            var lu = V3(Anchor(rec, "locker_use")["pos"]);
            return new[]
            {
                (new Vector3(dc.x, 0f, dc.z + 1.6f), "home_door"),                       // street side, on the paving in front of the steps
                (V3(Anchor(rec, "door_inside")["pos"]), "home_inside"),
                (new Vector3(lu.x, (float)Anchor(rec, "locker_use")["floor_y"], lu.z + .05f), "home_locker"),
                (V3(Anchor(rec, "wake_point")["pos"]), "home_bunk"),
            };
        }

        static void Unhook(CityLightCircuit circuit, GameObject old)
        {
            if (!circuit || !old) return;
            var oldLights = new HashSet<Light>(old.GetComponentsInChildren<Light>(true));
            circuit.practicalLights = circuit.practicalLights.Where(l => l && !oldLights.Contains(l)).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !oldLights.Contains(l)).ToArray();
            EditorUtility.SetDirty(circuit);
        }

        static IEnumerable<ulong> FileIds(UnityEngine.Object o)
        {
            var id = GlobalObjectId.GetGlobalObjectIdSlow(o);
            if (id.targetPrefabId != 0)
            {
                yield return id.targetPrefabId;
                yield return (id.targetObjectId ^ id.targetPrefabId) & 0x7fffffffffffffffUL;   // stripped/added docs of the instance
            }
            else yield return id.targetObjectId;
        }
        static IEnumerable<ulong> SubtreeIds(GameObject go)
        {
            foreach (var t in go.GetComponentsInChildren<Transform>(true))
            {
                foreach (var x in FileIds(t.gameObject)) yield return x;
                foreach (var c in t.GetComponents<Component>()) if (c) foreach (var x in FileIds(c)) yield return x;
            }
        }

        public static string Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play mode first.");
            Directory.CreateDirectory(Evidence + "rollback");
            if (!File.Exists(Evidence + "rollback/scene-before-first-install.unity")) File.Copy(ScenePath, Evidence + "rollback/scene-before-first-install.unity");
            File.Copy(ScenePath, Evidence + "scene-before-install.unity", true);
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            var rec = Record();
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include) ?? throw new Exception("no GameSession");
            var follow = session.follow ? session.follow : UnityEngine.Object.FindAnyObjectByType<FollowCamera>(FindObjectsInactive.Include);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            var oldA = FindPath(scene, OldInstancePath) ?? throw new Exception("WallHomeA instance not found: " + OldInstancePath);
            var aSrc = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(oldA.gameObject);
            if (!aSrc.EndsWith("WallHomeA.prefab")) throw new Exception(OldInstancePath + " is not a WallHomeA instance (" + aSrc + ")");
            var replaced = new List<ulong>();
            var existing = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (existing)
            {
                replaced.AddRange(SubtreeIds(existing));
                Unhook(circuit, existing); UnityEngine.Object.DestroyImmediate(existing); log.Add("replaced previous install");
            }
            File.WriteAllText(Evidence + "replaced-ids.json", JsonConvert.SerializeObject(replaced.Distinct().Select(x => x.ToString(Inv)).ToArray()));
            var pos = oldA.position; var rot = oldA.rotation;
            log.Add($"WallHomeA instance at {string.Join(",", A(pos))} yaw {Math.Round(rot.eulerAngles.y, 2)}");
            if (Vector3.Distance(pos, new Vector3(27.5f, 0, -41.4f)) > .01f || Mathf.Abs(Mathf.DeltaAngle(rot.eulerAngles.y, 0)) > .1f)
                log.Add("NOTE: the WallHomeA instance is not at the briefed (27.5, 0, -41.4) yaw 0; the new home follows the scene");
            if (oldA.gameObject.activeSelf)
            {
                oldA.gameObject.SetActive(false);
                PrefabUtility.RecordPrefabInstancePropertyModifications(oldA.gameObject);
                log.Add("retired (inactive): " + OldInstancePath);
            }
            else log.Add("already inactive: " + OldInstancePath);

            var root = new GameObject(RootName);
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(root, scene);
            root.transform.SetPositionAndRotation(pos, rot);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) ?? throw new Exception("prefab missing (run models first): " + PrefabPath);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            inst.name = InstanceName;
            inst.transform.SetParent(root.transform, false);
            inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity;
            // scene references (overrides on the instance)
            var home = inst.GetComponent<WardHome>(); home.session = session; EditorUtility.SetDirty(home); PrefabUtility.RecordPrefabInstancePropertyModifications(home);
            var door = inst.GetComponentInChildren<HomeDoor>(true); door.session = session; EditorUtility.SetDirty(door); PrefabUtility.RecordPrefabInstancePropertyModifications(door);
            var zone = inst.GetComponentInChildren<CameraConfineZone>(true); zone.follow = follow; EditorUtility.SetDirty(zone); PrefabUtility.RecordPrefabInstancePropertyModifications(zone);

            // porch light on the Ward lighting clock (night only, as the other wall homes)
            var porch = inst.transform.Find("Practical lights").GetComponentsInChildren<Light>(true);
            if (circuit)
            {
                circuit.practicalLights = circuit.practicalLights.Where(l => l).Concat(porch).Distinct().ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l).Concat(porch).Distinct().ToArray();
                EditorUtility.SetDirty(circuit);
            }

            // interior lighting: ambient probe, lamps on layer 7, portal over the door and window (one rectangle covering both)
            var ib = Anchor(rec, "interior_bounds");
            var il = root.AddComponent<InteriorLighting>();
            il.localBounds = new Bounds(V3(ib["center"]), V3(ib["size"]));
            il.openingDirection = Vector3.forward;
            var win = rec["interior"]["window"]["frame"]; var dfr = rec["interior"]["door"]["frame"];
            float x0 = Mathf.Min((float)win[0], (float)dfr[0]), x1 = Mathf.Max((float)win[1], (float)dfr[1]), top = Mathf.Max((float)win[3], (float)dfr[2]);
            float floorY = (float)rec["interior"]["floor_y"];
            il.openingCorners = new[] { new Vector3(x0, floorY, 1.22f), new Vector3(x1, floorY, 1.22f), new Vector3(x1, top, 1.22f), new Vector3(x0, top, 1.22f) };
            il.facadeDepth = .12f;
            il.interiorRoots = new[] { inst.transform.Find("Interior fittings") };
            il.renderers = inst.GetComponentsInChildren<Renderer>(true).Where(r => IsInterior(r.name)).ToList();
            il.lamps = inst.transform.Find("Interior lights").GetComponentsInChildren<Light>(true);
            foreach (var r in il.renderers) r.renderingLayerMask |= InteriorLayer;

            // interior reflection, box projected over the room (baked by "bake")
            var probeGo = new GameObject("Interior reflection"); probeGo.transform.SetParent(root.transform, false);
            probeGo.transform.localPosition = il.localBounds.center;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = ReflectionProbeMode.Baked; probe.boxProjection = true;
            probe.size = il.localBounds.size; probe.blendDistance = .3f; probe.importance = 2;
            probe.intensity = .45f; probe.resolution = 128; probe.clearFlags = ReflectionProbeClearFlags.Skybox;
            probe.cullingMask = ~0;
            var baked = AssetDatabase.LoadAssetAtPath<Cubemap>(ArtDir + "WardHomeInteriorReflection.exr");
            if (baked) { probe.customBakedTexture = baked; probe.mode = ReflectionProbeMode.Custom; }

            // QA landmarks (direct children of AthenDebugBridge.landmarks, as Goto expects)
            var lmRoot = bridge && bridge.landmarks ? bridge.landmarks : scene.GetRootGameObjects().FirstOrDefault(g2 => g2.name == "Landmarks")?.transform;
            if (!lmRoot) throw new Exception("no landmarks transform (AthenDebugBridge.landmarks)");
            foreach (var (local, name) in Landmarks(rec))
            {
                var t = lmRoot.Find(name);
                if (!t) { t = new GameObject(name).transform; t.SetParent(lmRoot, true); log.Add("landmark + " + name); }
                t.position = root.transform.TransformPoint(local);
            }
            // review cameras
            var camRoot = new GameObject("Ward home review cameras").transform; camRoot.SetParent(root.transform, false);
            foreach (var (n, p, target, fov) in Cameras)
            {
                var go = new GameObject(n); go.transform.SetParent(camRoot, false);
                go.transform.localPosition = p; go.transform.localRotation = Quaternion.LookRotation(target - p, Vector3.up);
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
            }
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            string fpBefore = chunks ? chunks.sourceFingerprint : null;
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            var record = new Dictionary<string, object>
            {
                ["root"] = RootName, ["instance"] = PathOf(inst.transform), ["position"] = A(pos), ["yaw"] = Math.Round(rot.eulerAngles.y, 3),
                ["retired"] = OldInstancePath, ["porchLightOnCircuit"] = circuit != null, ["interiorRenderers"] = il.renderers.Count, ["lamps"] = il.lamps.Length,
                ["landmarks"] = Landmarks(rec).Select(l => l.name).ToArray(), ["cameras"] = Cameras.Select(c => c.name).ToArray(), ["log"] = log,
                ["chunkFingerprintUnchanged"] = chunks ? (object)(chunks.sourceFingerprint == fpBefore) : "no StaticRenderChunks",
            };
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "install.json", json);
            return json;
        }

        /// One-off (5 Oct 2026): remove the UniversalAdditionalLightData components the first bake saved onto lights outside
        /// this pass, i.e. those whose file ID is not in the pre-first-install scene copy. Components that come from a prefab
        /// asset are left alone.
        public static string RevertLightData()
        {
            var first = Evidence + "rollback/scene-before-first-install.unity";
            if (!File.Exists(first)) throw new Exception("no pre-first-install copy");
            var ids = new HashSet<ulong>(YamlDocs(first).Keys.Select(k => { var s = k.Split(':')[1]; return s.StartsWith("-") ? unchecked((ulong)long.Parse(s, Inv)) : ulong.Parse(s, Inv); }));
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var removed = new List<string>();
            foreach (var d in UnityEngine.Object.FindObjectsByType<UniversalAdditionalLightData>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (root && d.transform.IsChildOf(root.transform)) continue;
                var gid = GlobalObjectId.GetGlobalObjectIdSlow(d);
                if (gid.targetPrefabId != 0 && !PrefabUtility.IsAddedComponentOverride(d)) continue;     // part of a prefab asset
                if (ids.Contains(gid.targetObjectId)) continue;
                removed.Add(PathOf(d.transform));
                UnityEngine.Object.DestroyImmediate(d);
            }
            if (removed.Count > 0) { EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); }
            File.WriteAllText(Evidence + "revert-light-data.json", JsonConvert.SerializeObject(removed, Formatting.Indented));
            return $"removed {removed.Count}: " + string.Join(", ", removed);
        }

        public static string Uninstall()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            if (root) { Unhook(circuit, root); UnityEngine.Object.DestroyImmediate(root); }
            if (bridge && bridge.landmarks)
                foreach (var n in new[] { "home_door", "home_inside", "home_locker", "home_bunk" }) { var t = bridge.landmarks.Find(n); if (t) UnityEngine.Object.DestroyImmediate(t.gameObject); }
            var oldA = FindPath(scene, OldInstancePath);
            if (oldA) { oldA.gameObject.SetActive(true); PrefabUtility.RecordPrefabInstancePropertyModifications(oldA.gameObject); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "uninstalled; " + OldInstancePath + " active again";
        }

        // ------------------------------------------------------------------ verify
        static Dictionary<string, string> YamlDocs(string path)
        {
            var docs = new Dictionary<string, string>();
            string key = null; var sb = new System.Text.StringBuilder();
            var head = new Regex(@"^--- !u!(\d+) &(-?\d+)");
            foreach (var line in File.ReadLines(path))
            {
                var m = head.Match(line);
                if (m.Success)
                {
                    if (key != null) docs[key] = sb.ToString();
                    key = m.Groups[1].Value + ":" + m.Groups[2].Value; sb.Clear();
                }
                sb.AppendLine(line);
            }
            if (key != null) docs[key] = sb.ToString();
            return docs;
        }

        public static string Verify()
        {
            var problems = new List<string>();
            var r = new Dictionary<string, object>();
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var rec = Record();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (!root) { problems.Add("not installed"); return Finish(r, problems); }
            var inst = root.transform.Find(InstanceName);
            r["instance"] = inst ? PathOf(inst) : null;
            if (!inst) { problems.Add("no WallHomeP instance"); return Finish(r, problems); }
            r["prefabLinked"] = PrefabUtility.IsAnyPrefabInstanceRoot(inst.gameObject) && PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(inst.gameObject) == PrefabPath;
            if (!(bool)r["prefabLinked"]) problems.Add("instance not linked to " + PrefabPath);
            r["position"] = A(inst.position); r["yaw"] = Math.Round(inst.eulerAngles.y, 3);
            var oldA = FindPath(scene, OldInstancePath);
            r["oldInstanceFound"] = oldA != null; r["oldInstanceActive"] = oldA && oldA.gameObject.activeInHierarchy;
            if (!oldA) problems.Add("WallHomeA instance missing (should be inactive, never deleted)");
            else
            {
                if (oldA.gameObject.activeInHierarchy) problems.Add("WallHomeA instance still active");
                if (Vector3.Distance(oldA.position, inst.position) > .001f || Quaternion.Angle(oldA.rotation, inst.rotation) > .01f) problems.Add("home not at the WallHomeA transform");
            }
            var rends = root.GetComponentsInChildren<Renderer>(true);
            r["renderers"] = rends.Length;
            r["missingMaterials"] = rends.Where(x => x.sharedMaterials.Any(m => !m)).Select(x => PathOf(x.transform)).ToArray();
            if (((string[])r["missingMaterials"]).Length > 0) problems.Add("missing materials");
            var lg = inst.GetComponent<LODGroup>();
            r["lodTriangles"] = lg.GetLODs().Select(l => l.renderers.Where(x => x).Sum(Tris)).ToArray();

            // components wired
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var home = inst.GetComponent<WardHome>();
            var door = inst.GetComponentInChildren<HomeDoor>(true);
            var zone = inst.GetComponentInChildren<CameraConfineZone>(true);
            var il = root.GetComponent<InteriorLighting>();
            var wiring = new Dictionary<string, bool>
            {
                ["WardHome"] = home, ["WardHome.session"] = home && home.session == session && session, ["WardHome.door"] = home && home.door == door && door,
                ["WardHome.locker"] = home && home.locker, ["WardHome.bunk"] = home && home.bunk, ["WardHome.lockerPoint"] = home && home.lockerPoint,
                ["WardHome.wakePoint"] = home && home.wakePoint, ["HomeDoor.session"] = door && door.session == session,
                ["HomeDoor.leaf"] = door && door.leaf && door.leaf.name == "Door leaf", ["HomeDoor.leafCollider"] = door && door.leafCollider,
                ["HomeDoor.lockedPrompt"] = door && door.lockedPrompt && door.lockedPrompt.gameObject == door.gameObject,
                ["CameraConfineZone.follow"] = zone && zone.follow && session && zone.follow == session.follow,
                ["InteriorLighting.lamps"] = il && il.lamps.Length == 3 && il.lamps.All(l => l), ["InteriorLighting.renderers"] = il && il.renderers.Count > 0 && il.renderers.All(x => x),
                ["ReflectionProbe"] = root.GetComponentInChildren<ReflectionProbe>(true),
            };
            r["wiring"] = wiring;
            foreach (var kv in wiring) if (!kv.Value) problems.Add("not wired: " + kv.Key);
            if (home)
            {
                r["home"] = new { home.leasePrice, home.lockerSlots, home.lockerFeedsBench, locker = home.locker ? new { home.locker.prompt, home.locker.range } : null,
                                  bunk = home.bunk ? new { home.bunk.prompt, home.bunk.range } : null };
                if (home.leasePrice != 40 || home.lockerSlots != 60 || !home.lockerFeedsBench) problems.Add("WardHome values");
            }
            if (door)
            {
                r["door"] = new { door.closedYaw, door.openYaw, door.openDistance, lockedPrompt = door.lockedPrompt ? door.lockedPrompt.prompt : null,
                                  lockedRange = door.lockedPrompt ? door.lockedPrompt.range : 0, leafLocalYaw = Math.Round(door.leaf.localEulerAngles.y, 3),
                                  leafColliderEnabled = door.leafCollider && door.leafCollider.enabled };
                if (!door.leafCollider || !door.leafCollider.enabled) problems.Add("door leaf collider not enabled with the door closed");
                if (Mathf.Abs(Mathf.DeltaAngle(door.leaf.localEulerAngles.y, door.closedYaw)) > .01f) problems.Add("leaf not closed in the saved scene");
                if (door.leafCollider && !door.leafCollider.transform.IsChildOf(door.leaf)) problems.Add("leaf collider not on the leaf");
                if (GameObjectUtility.AreStaticEditorFlagsSet(door.leaf.gameObject, StaticEditorFlags.BatchingStatic)) problems.Add("door leaf is batching static (cannot swing)");
            }
            if (zone) r["cameraZone"] = new { center = A(zone.center), size = A(zone.size) };

            // landmarks
            var bridge = UnityEngine.Object.FindAnyObjectByType<AthenDebugBridge>(FindObjectsInactive.Include);
            var lm = new Dictionary<string, object>();
            var bounds = il ? il.localBounds : new Bounds();
            Transform L(string n) => bridge && bridge.landmarks ? bridge.landmarks.Find(n) : null;
            bool Inside(Vector3 w) { var p = root.transform.InverseTransformPoint(w + Vector3.up * 1.0f); return bounds.Contains(p); }
            foreach (var (_, n) in Landmarks(rec))
            {
                var t = L(n);
                if (!t) { problems.Add("landmark missing: " + n); continue; }
                lm[n] = new { pos = A(t.position), inside = Inside(t.position) };
            }
            var hd = L("home_door"); var hi = L("home_inside"); var hl = L("home_locker"); var hb = L("home_bunk");
            if (hd && Inside(hd.position)) problems.Add("home_door is inside");
            if (hd && door && Vector3.Distance(hd.position, door.transform.position) > 2.4f) problems.Add("home_door farther than 2.4 m from the door");
            if (hi && !Inside(hi.position)) problems.Add("home_inside is not inside");
            if (hl && (!Inside(hl.position) || !home || !home.locker || Vector3.Distance(hl.position, home.locker.transform.position) > home.locker.range)) problems.Add("home_locker not inside / not within the locker's range");
            if (hb && (!Inside(hb.position) || !home || !home.bunk || Vector3.Distance(hb.position, home.bunk.transform.position) > home.bunk.range)) problems.Add("home_bunk not inside / not within the bunk's range");
            if (hd && door && door.lockedPrompt && Vector3.Distance(hd.position, door.lockedPrompt.transform.position) > door.lockedPrompt.range + .6f) problems.Add("locked-door prompt far from home_door");
            r["landmarks"] = lm;
            if (hd && door) r["homeDoorToDoor"] = Math.Round(Vector3.Distance(hd.position, door.transform.position), 3);
            if (hl && home && home.locker) r["homeLockerToLocker"] = Math.Round(Vector3.Distance(hl.position, home.locker.transform.position), 3);
            if (hb && home && home.bunk) r["homeBunkToBunk"] = Math.Round(Vector3.Distance(hb.position, home.bunk.transform.position), 3);

            // capsule paths with the door open (leaf collider off, in memory only)
            bool leafWas = door && door.leafCollider && door.leafCollider.enabled;
            if (door && door.leafCollider) door.leafCollider.enabled = false;
            Physics.SyncTransforms();
            var blocked = new List<string>();
            var steps = new List<(string, Vector3[])>();
            if (hd && hi && hl && hb)
            {
                var dc = V3(Anchor(rec, "door_centre")["pos"]);
                Vector3 W(float x, float y, float z) => root.transform.TransformPoint(new Vector3(x, y, z));
                var approach = new[] { hd.position, W(dc.x, .15f, 2.12f), W(dc.x, .30f, 1.62f), W(dc.x, .502f, dc.z), hi.position };
                steps.Add(("door -> inside", approach));
                steps.Add(("inside -> locker", new[] { hi.position, hl.position }));
                steps.Add(("inside -> bunk", new[] { hi.position, W(.4f, .5f, .25f), W(-.8f, .5f, .22f), hb.position }));
            }
            const float rad = .3f, height = 1.8f, stepClear = .3f;   // ignore the bottom 0.3 m (the controller's step offset)
            int mask = ~(1 << 8);
            foreach (var (name, path) in steps)
            {
                for (int i = 0; i < path.Length; i++)
                {
                    var w = path[i];
                    var p0 = w + Vector3.up * (stepClear + rad); var p1 = w + Vector3.up * (height - rad);
                    foreach (var h in Physics.OverlapCapsule(p0, p1, rad, mask, QueryTriggerInteraction.Ignore))
                        blocked.Add($"{name} point {i} {string.Join(",", A(w))}: {PathOf(h.transform)}");
                    if (i > 0)
                    {
                        var a = path[i - 1];
                        var d = w - a;
                        if (Physics.CapsuleCast(a + Vector3.up * (stepClear + rad), a + Vector3.up * (height - rad), rad - .02f, d.normalized, out var hit, d.magnitude, mask, QueryTriggerInteraction.Ignore))
                            blocked.Add($"{name} leg {i - 1}->{i}: {PathOf(hit.transform)} at {string.Join(",", A(hit.point))}");
                    }
                    if (!Physics.Raycast(w + Vector3.up * .5f, Vector3.down, out var g, 1f, mask, QueryTriggerInteraction.Ignore) || Mathf.Abs(g.point.y - w.y) > .06f)
                        blocked.Add($"{name} point {i}: no floor at {string.Join(",", A(w))}");
                }
            }
            if (door && door.leafCollider) door.leafCollider.enabled = leafWas;
            r["paths"] = steps.Select(s => new { s.Item1, points = s.Item2.Select(A).ToArray() }).ToArray();
            r["pathBlocked"] = blocked; problems.AddRange(blocked);
            // the closed door blocks the doorway (leaf collider on)
            Physics.SyncTransforms();
            if (hd && hi && door && door.leafCollider && door.leafCollider.enabled)
            {
                var a = root.transform.TransformPoint(new Vector3(V3(Anchor(rec, "door_centre")["pos"]).x, .502f, 1.6f));
                var b = root.transform.TransformPoint(new Vector3(V3(Anchor(rec, "door_centre")["pos"]).x, .502f, .8f));
                bool shut = Physics.CapsuleCast(a + Vector3.up * .6f, a + Vector3.up * 1.5f, .28f, (b - a).normalized, out var hh, (b - a).magnitude, mask, QueryTriggerInteraction.Ignore) && hh.collider == door.leafCollider;
                r["closedDoorBlocks"] = shut;
                if (!shut) problems.Add("the closed leaf collider does not block the doorway");
            }

            // scene diff against the pre-install copy: only this pass's objects may differ
            var beforePath = Evidence + "scene-before-install.unity";
            if (File.Exists(beforePath))
            {
                var before = YamlDocs(beforePath); var after = YamlDocs(ScenePath);
                var allowed = new HashSet<ulong>(SubtreeIds(root));
                if (oldA) foreach (var x in FileIds(oldA.gameObject)) allowed.Add(x);
                var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
                if (circuit) foreach (var x in FileIds(circuit)) allowed.Add(x);
                if (bridge && bridge.landmarks)
                {
                    foreach (var x in FileIds(bridge.landmarks)) allowed.Add(x);
                    foreach (var n in new[] { "home_door", "home_inside", "home_locker", "home_bunk" }) { var t = bridge.landmarks.Find(n); if (t) foreach (var x in SubtreeIds(t.gameObject)) allowed.Add(x); }
                }
                var replaced = File.Exists(Evidence + "replaced-ids.json")
                    ? new HashSet<ulong>(JsonConvert.DeserializeObject<string[]>(File.ReadAllText(Evidence + "replaced-ids.json")).Select(s => ulong.Parse(s, Inv)))
                    : new HashSet<ulong>();
                ulong Id(string key) { var s = key.Split(':')[1]; return s.StartsWith("-") ? unchecked((ulong)long.Parse(s, Inv)) : ulong.Parse(s, Inv); }
                // stripped placeholders (scene references into a prefab instance) belong to their m_PrefabInstance
                var strippedOf = new Regex(@"^--- !u!\d+ &-?\d+ stripped[\s\S]*?m_PrefabInstance: {fileID: (-?\d+)}");
                bool OwnStripped(Dictionary<string, string> docs, string key)
                {
                    if (!docs.TryGetValue(key, out var text)) return false;
                    var m = strippedOf.Match(text);
                    if (!m.Success) return false;
                    var s = m.Groups[1].Value;
                    var pid = s.StartsWith("-") ? unchecked((ulong)long.Parse(s, Inv)) : ulong.Parse(s, Inv);
                    return allowed.Contains(pid) || replaced.Contains(pid);
                }
                bool Ok(string key) => key.StartsWith("1660057539:") || allowed.Contains(Id(key)) || replaced.Contains(Id(key))
                                       || OwnStripped(after, key) || OwnStripped(before, key);
                var added = after.Keys.Except(before.Keys).ToList(); var removed = before.Keys.Except(after.Keys).ToList();
                var changed = after.Keys.Intersect(before.Keys).Where(k => after[k] != before[k]).ToList();
                var unexpected = added.Where(k => !Ok(k)).Select(k => "added " + k).Concat(removed.Where(k => !Ok(k)).Select(k => "removed " + k))
                    .Concat(changed.Where(k => !Ok(k)).Select(k => "changed " + k)).ToList();
                r["sceneDiff"] = new { before = beforePath, added = added.Count, removed = removed.Count, changed = changed.Count, unexpected = unexpected.Take(40).ToArray(),
                                       unexpectedCount = unexpected.Count, changedExpected = changed.Where(Ok).ToArray() };
                if (unexpected.Count > 0) problems.Add($"scene diff: {unexpected.Count} unexpected document changes (first: {unexpected[0]})");
            }
            else problems.Add("no pre-install scene copy for the diff");
            r["cameras"] = root.GetComponentsInChildren<Camera>(true).Select(c => c.name).ToArray();
            // review cameras must not sit inside scenery: other roots' renderers whose bounds hold the eye, colliders within 0.2 m
            var mine = new HashSet<Renderer>(root.GetComponentsInChildren<Renderer>(true));
            var others = scene.GetRootGameObjects().Where(g2 => g2.activeInHierarchy && g2 != root).SelectMany(g2 => g2.GetComponentsInChildren<Renderer>(false))
                .Where(x => x.enabled && !(x is ParticleSystemRenderer) && x.bounds.size.magnitude < 40f).ToArray();
            var camClear = new Dictionary<string, object>();
            foreach (var c in root.GetComponentsInChildren<Camera>(true))
            {
                var p = c.transform.position;
                var inR = others.Where(x => !mine.Contains(x) && x.bounds.Contains(p)).Select(x => PathOf(x.transform)).Take(4).ToArray();
                var nearC = Physics.OverlapSphere(p, .2f, ~0, QueryTriggerInteraction.Ignore).Select(x => PathOf(x.transform)).Take(4).ToArray();
                camClear[c.name] = new { pos = A(p), insideRendererBounds = inR, collidersWithin20cm = nearC };
                if (nearC.Length > 0) problems.Add($"{c.name} inside a collider: {nearC[0]}");
            }
            r["cameraClearance"] = camClear;
            // scenery round the door approach (building-local box x -0.5..3.5, z 1.25..4.5): the leaf sweeps to z 2.3
            var appr = new List<object>();
            foreach (var c in UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (c.transform.IsChildOf(root.transform) || !c.enabled || c is TerrainCollider || c.bounds.size.x > 60) continue;
                var b = c.bounds;
                var bl = root.transform.InverseTransformPoint(b.min); var bh = root.transform.InverseTransformPoint(b.max);
                var mn = Vector3.Min(bl, bh); var mx = Vector3.Max(bl, bh);
                if (mx.x < -.5f || mn.x > 3.5f || mx.z < 1.25f || mn.z > 4.5f || mn.y > 2.5f) continue;
                appr.Add(new { collider = PathOf(c.transform), localMin = A(mn), localMax = A(mx) });
            }
            r["doorApproachScenery"] = appr;
            // the leaf's swept volume: its collider box through closedYaw -> openYaw in 5 degree steps against every scene
            // collider outside the home (the home's own walls, step and planter are checked in the authoring; the leaf
            // collider is off while open, so this is about the leaf passing through scenery)
            if (door && door.leaf && door.leafCollider is BoxCollider lb)
            {
                var swingHits = new HashSet<string>();
                float span = Mathf.DeltaAngle(door.closedYaw, door.openYaw);
                int n = Mathf.CeilToInt(Mathf.Abs(span) / 5f);
                var leafRot0 = door.leaf.localRotation;
                for (int i = 0; i <= n; i++)
                {
                    var rotW = root.transform.rotation * inst.rotation * Quaternion.Euler(0, door.closedYaw + span * i / n, 0);
                    var cW = door.leaf.position + rotW * lb.center;
                    foreach (var h in Physics.OverlapBox(cW, lb.size * .5f, rotW, ~0, QueryTriggerInteraction.Ignore))
                        if (!h.transform.IsChildOf(root.transform)) swingHits.Add($"{PathOf(h.transform)} at {Math.Round(door.closedYaw + span * i / n, 1)} deg");
                }
                r["leafSwing"] = new { from = door.closedYaw, to = door.openYaw, steps = n + 1, hits = swingHits.ToArray() };
                foreach (var h in swingHits) problems.Add("scenery in the door leaf's swing: " + h);
                // parked: the open leaf's box against the home's own street-face features (window frame, junction box, planter)
                var rotO = root.transform.rotation * inst.rotation * Quaternion.Euler(0, door.openYaw, 0);
                var cO = root.transform.InverseTransformPoint(door.leaf.position + rotO * lb.center);
                r["leafParkedCentre"] = A(cO);
            }
            return Finish(r, problems);
        }

        static string Finish(Dictionary<string, object> r, List<string> problems)
        {
            r["problems"] = problems;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return problems.Count == 0 ? "verify ok" : "verify problems: " + string.Join(" | ", problems.Take(14));
        }

        // ------------------------------------------------------------------ graphics steps
        static void ApplyRoom(GameObject root, float hour)
        {
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(hour);
            var (s0, e0, g0) = (RenderSettings.ambientSkyColor, RenderSettings.ambientEquatorColor, RenderSettings.ambientGroundColor);
            RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround;
            root.GetComponent<InteriorLighting>()?.ApplyInEditor();
            RenderSettings.ambientSkyColor = s0; RenderSettings.ambientEquatorColor = e0; RenderSettings.ambientGroundColor = g0;
        }
        public static string Bake()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            var probe = root.GetComponentInChildren<ReflectionProbe>(true);
            probe.mode = ReflectionProbeMode.Baked;
            ApplyRoom(root, 13f);
            // rendering the probe makes URP add UniversalAdditionalLightData to every light it draws; on 5 Oct the first bake
            // saved those into 12 objects outside this pass (Field Supply, Salvage, Nanofab 2, Watchtower 4, WallHomeB, gate B)
            var hadData = new HashSet<Light>(UnityEngine.Object.FindObjectsByType<UniversalAdditionalLightData>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Select(d => d.GetComponent<Light>()).Where(l => l));
            Directory.CreateDirectory(ArtDir);
            var path = ArtDir + "WardHomeInteriorReflection.exr";
            if (!Lightmapping.BakeReflectionProbe(probe, path)) throw new Exception("interior reflection bake failed");
            // clamp the few half-float-max pixels of street seen through the door (FieldSupplyShopPass.Bake)
            var clamp = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("magick", $"\"{Path.GetFullPath(path)}\" -fx \"min(u,6)\" \"{Path.GetFullPath(path)}\"") { UseShellExecute = false });
            clamp.WaitForExit();
            if (clamp.ExitCode != 0) throw new Exception("probe clamp failed (ImageMagick 'magick' on PATH?)");
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            probe.customBakedTexture = AssetDatabase.LoadAssetAtPath<Cubemap>(path); probe.mode = ReflectionProbeMode.Custom;
            EditorUtility.SetDirty(probe);
            int dropped = 0;
            foreach (var d in UnityEngine.Object.FindObjectsByType<UniversalAdditionalLightData>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                var l = d.GetComponent<Light>();
                if (!l || hadData.Contains(l) || d.transform.IsChildOf(root.transform)) continue;
                UnityEngine.Object.DestroyImmediate(d); dropped++;
            }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "baked " + path + $" (dropped {dropped} light data components URP added outside this pass)";
        }
        static int captured;
        public static string Capture(string hourText, string camList, string outDir, bool open)
        {
            var names = camList.Split('+');
            captured += names.Length;
            if (captured > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            float hour = float.Parse(hourText, Inv);
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (root)
            {
                ApplyRoom(root, hour);
                var door = root.GetComponentInChildren<HomeDoor>(true);
                if (open && door) door.leaf.localRotation = Quaternion.Euler(0, door.openYaw, 0);     // in memory only, never saved
            }
            ShaderUtil.allowAsyncCompilation = false;
            DuskStartPass.Preview(hour, Path.Combine(outDir, "warmup"), names[0]);
            return DuskStartPass.Preview(hour, outDir + (open ? "/open" : "/closed"), names);
        }

        /// -executeMethod AthenHill.Editor.WardHomePass.RunBatch --steps models,install,verify (graphics: bake, capture:HOUR:cam+cam[:open]) [--out dir]
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "verify").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var p = st.Split(':');
                    string result = p[0] switch
                    {
                        "materials" => Materials(),
                        "models" => Models(),
                        "install" => Install(),
                        "uninstall" => Uninstall(),
                        "revertlightdata" => RevertLightData(),
                        "verify" => Verify(),
                        "bake" => Bake(),
                        "capture" => Capture(p[1], p[2], outDir, p.Length > 3 && p[3] == "open"),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("WardHomePass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
