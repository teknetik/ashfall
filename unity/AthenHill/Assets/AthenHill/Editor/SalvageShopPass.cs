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
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>
    /// 1 October 2026: the Salvage shop on the north avenue becomes a walk-in workshop and trade counter, and the first
    /// field order runs through it (Carl: "make the salvage shop walkable. i want it part of the tutorial mission ... the
    /// salvage shop should be open to trade and have the equipment in there and an npc to trade with and some quest
    /// dialog. from the robot tutorial part i get the loot and go to salvage shop and get to upgrade my pistol").
    ///
    /// Geometry: art/salvage_shop_20261001/salvage_interior.py (called by the north avenue Salvage authoring script) opens
    /// the loading bay and fits out the ground floor; the record (Art/WardShops/Models/salvage.json) carries the walk-in
    /// colliders, the pendant lamp points and the room bounds. This pass:
    ///  materials  SS_* materials for the interior (timber, boards, enamel shades, warm bulbs).
    ///  models     re-imports the Salvage models and patches Prefabs/WardShops/Salvage.prefab in place (material slots
    ///             re-mapped by name with the night facade's substitutions kept, LODGroup rebuilt with the interior
    ///             parts, interior renderers unshadowed on the interior light layer, walk-in colliders from the record).
    ///  data       Brann's NpcDefinition (Data/npc_brann.asset: quest-aware openings, trade profile), the first field
    ///             order's report to Brann, field-order texts pointing at his workbench, the station's name.
    ///  install    scene root "Salvage shop interior" (re-runnable: replaces itself): InteriorLighting, pendant lamps on
    ///             the interior light layer, a night-only bay spill on the Ward lighting clock, Brann, the workbench and its
    ///             station, props, decals, an interior reflection probe and review cameras; rewires the session (npcs,
    ///             CraftingSession.fabricator, FieldOrders guidance "fabricator"/"dealer"), retires the field tool cart's
    ///             station (the cart stays as dressing), updates Ossa's primer completion line and adds landmarks.
    ///  verify     saved-scene checks and walk-path clearance -> evidence/salvage-shop/20261001/verify.json.
    ///  bake       (graphics) bakes the interior reflection probe.  capture:HOUR:cam+cam (graphics, at most 6 cameras).
    /// Batch: -executeMethod AthenHill.Editor.SalvageShopPass.RunBatch --steps materials,models,data,install,verify -nographics.
    /// </summary>
    public static class SalvageShopPass
    {
        const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        const string Evidence = "../evidence/salvage-shop/20261001/";
        const string ModelDir = "Assets/AthenHill/Art/WardShops/Models/";
        const string PrefabPath = "Assets/AthenHill/Prefabs/WardShops/Salvage.prefab";
        const string MatDir = "Assets/AthenHill/Art/SalvageShop/Materials/";
        const string ArtDir = "Assets/AthenHill/Art/SalvageShop/";
        const string BrannPath = "Assets/AthenHill/Data/npc_brann.asset";
        const string OrdersPath = "Assets/AthenHill/Data/Crafting/WardFieldOrders.asset";
        const string CraftingPath = "Assets/AthenHill/Data/Crafting/WardCrafting.asset";
        const string ShopPath = "Ward shops (north avenue)/Salvage";
        const string CartPath = "Outer Berms/West Gate outpost/Outpost/Field fabricator";
        public const string RootName = "Salvage shop interior";
        public const string StationId = "station_field_fabricator";
        public const uint InteriorLayer = 1u << 7;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        // world region round the Salvage parcel (root (-18.1, 0, 18), yaw 90: the building runs x -25.1..-18.1, z 14.2..21.8)
        static readonly Bounds Region = new Bounds(new Vector3(-19.5f, 5f, 18f), new Vector3(17f, 14f, 15f));
        const float Floor = .5f;

        static string PathOf(Transform t) => t.parent ? PathOf(t.parent) + "/" + t.name : t.name;
        static float[] A(Vector3 v) => new[] { (float)Math.Round(v.x, 3), (float)Math.Round(v.y, 3), (float)Math.Round(v.z, 3) };
        static Vector3 V3(JToken t) => new Vector3((float)t[0], (float)t[1], (float)t[2]);
        static JObject Record() => JObject.Parse(File.ReadAllText(ModelDir + "salvage.json"));
        static Transform Find(UnityEngine.SceneManagement.Scene scene, string path)
        {
            var parts = path.Split('/');
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == parts[0]);
            if (!root) return null;
            var t = root.transform;
            for (int i = 1; i < parts.Length && t; i++) t = t.Find(parts[i]);
            return t;
        }

        // ------------------------------------------------------------------ materials
        static Material Mat(string name, Func<Material> make, Action<Material> setup)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m) return m;
            m = make(); m.name = name; setup(m);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }
        public static Dictionary<string, Material> Materials()
        {
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var timber = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/TrainingRange/Materials/TR_TimberDark.mat");
            var boards = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/TrainingRange/Materials/TR_Timber.mat");
            if (!timber || !boards) throw new Exception("Training range timber materials missing");
            var d = new Dictionary<string, Material>
            {
                // old joists, darkened by years of workshop smoke; the deck boards a little paler (metre UVs, 1.2 m repeat)
                ["SS_Timber"] = Mat("SS_Timber", () => new Material(timber), m => { m.SetColor("_BaseColor", new Color(.62f, .55f, .48f)); }),
                ["SS_Boards"] = Mat("SS_Boards", () => new Material(boards), m => { m.SetColor("_BaseColor", new Color(.7f, .62f, .54f)); }),
                ["SS_Enamel"] = Mat("SS_Enamel", () => new Material(lit), m => { m.SetColor("_BaseColor", new Color(.8f, .78f, .72f)); m.SetFloat("_Smoothness", .62f); }),
                ["SS_BulbWarm"] = Mat("SS_BulbWarm", () => new Material(lit), m =>
                {
                    m.SetColor("_BaseColor", new Color(1f, .9f, .74f)); m.SetFloat("_Smoothness", .8f);
                    m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", new Color(1f, .7f, .4f) * 4f);
                    // URP drops _EMISSION on save without a GI flag (ward render notes)
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                }),
            };
            AssetDatabase.SaveAssets();
            return d;
        }

        // ------------------------------------------------------------------ models + prefab patch
        static Material Lookup(Dictionary<string, Material> mats, string name)
        {
            name = name.Replace(" (Instance)", "");
            if (mats.TryGetValue(name, out var m)) return m;
            var trimmed = System.Text.RegularExpressions.Regex.Replace(name, @"\.\d+$", "");
            return mats.TryGetValue(trimmed, out m) ? m : null;
        }

        public static string Models()
        {
            foreach (var lod in new[] { 0, 1 }) AssetDatabase.ImportAsset(ModelDir + $"Salvage_LOD{lod}.glb", ImportAssetOptions.ForceUpdate);
            var mats = WardShopsPass.BuildMaterials(false);
            foreach (var kv in Materials()) mats[kv.Key] = kv.Value;
            var rec = Record();
            var log = new List<string>();
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                var levels = new List<LOD>();
                int interior = 0, kept = 0, unmapped = 0;
                foreach (var (lod, cut) in new[] { (0, WardShopsPass.Lod0ScreenHeight), (1, .01f) })
                {
                    var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelDir + $"Salvage_LOD{lod}.glb");
                    var lodRoot = root.transform.Find("LOD" + lod) ?? throw new Exception("prefab has no LOD" + lod);
                    var rs = new List<Renderer>();
                    foreach (var r in lodRoot.GetComponentsInChildren<Renderer>(true))
                    {
                        var src = model.GetComponentsInChildren<Renderer>(true).FirstOrDefault(x => x.name == r.name);
                        if (!src) { log.Add("no source for " + r.name); continue; }
                        var want = src.sharedMaterials.Select(m => m ? Lookup(mats, m.name) : null).ToArray();
                        unmapped += want.Count(m => !m);
                        // keep a later pass's 1:1 substitutions (the night facade's NF_Glass_North for WS_Glass): a material on
                        // the prefab that the name mapping never produces replaces the mapped one the prefab no longer uses
                        var current = r.sharedMaterials;
                        // (only project materials count: a renderer new to the prefab still carries the importer's own)
                        string modelPath = AssetDatabase.GetAssetPath(model);
                        var extra = current.Where(m => m && !want.Contains(m) && AssetDatabase.GetAssetPath(m) != modelPath).Distinct().ToList();
                        var missing = want.Where(m => m && !current.Contains(m)).Distinct().ToList();
                        var swap = new Dictionary<Material, Material>();
                        for (int i = 0; i < Math.Min(extra.Count, missing.Count); i++) swap[missing[i]] = extra[i];
                        var slots = want.Select((m, i) => m && swap.TryGetValue(m, out var s) ? s : m ?? (i < current.Length ? current[i] : null)).ToArray();
                        kept += swap.Count;
                        r.sharedMaterials = slots;
                        bool isInterior = r.name.Contains("_Interior");
                        if (isInterior)
                        {
                            interior++;
                            r.shadowCastingMode = ShadowCastingMode.Off;
                            r.renderingLayerMask |= InteriorLayer;
                            r.receiveShadows = true;
                            if (r is MeshRenderer mr) { mr.motionVectorGenerationMode = MotionVectorGenerationMode.Camera; mr.receiveGI = ReceiveGI.LightProbes; }
                            GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                        }
                        rs.Add(r);
                    }
                    levels.Add(new LOD(cut, rs.ToArray()));
                }
                var group = root.GetComponent<LODGroup>();
                group.SetLODs(levels.ToArray());
                group.RecalculateBounds();
                // walk-in colliders from the record replace the solid body
                var cols = root.transform.Find("Colliders");
                foreach (Transform c in cols.Cast<Transform>().ToArray()) UnityEngine.Object.DestroyImmediate(c.gameObject);
                foreach (var c in rec["colliders"])
                {
                    var go = new GameObject((string)c["name"]); go.transform.SetParent(cols, false);
                    var b = go.AddComponent<BoxCollider>(); b.center = V3(c["center"]); b.size = V3(c["size"]);
                    GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
                }
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                log.Add($"prefab patched: LOD0 {levels[0].renderers.Length} / LOD1 {levels[1].renderers.Length} renderers, interior {interior}, substitutions kept {kept}, unmapped slots {unmapped}, colliders {rec["colliders"].Count()}");
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ data
        static DialogueChoice C(string label, string next = null, string action = null, string requires = null, string flag = null)
            => new DialogueChoice { id = (next ?? action ?? "x") + "_" + Math.Abs(label.GetHashCode() % 997), label = label, next = next ?? "", action = action ?? "", requires = requires ?? "", setFlag = flag ?? "" };
        static DialogueNode N(string id, string title, string text, params DialogueChoice[] choices) => new DialogueNode { id = id, title = title, text = text, choices = choices };

        public static string Data()
        {
            var brann = AssetDatabase.LoadAssetAtPath<NpcDefinition>(BrannPath);
            bool created = !brann;
            if (created) brann = ScriptableObject.CreateInstance<NpcDefinition>();
            brann.id = "npc_brann"; brann.displayName = "Brann"; brann.role = "Salvage dealer";
            var trade = C("Show me what you trade.", action: "shop");
            var bench = C("Let me use the bench.", action: "fabricator", requires: "pistol");
            var bye = C("Later, Brann.", action: "close");
            brann.entries = new[]
            {
                new DialogueEntry { node = "first_visit", requires = "!primer, !flag:brann_met" },
                new DialogueEntry { node = "report_ready", requires = "order:order_steady_hands, !reported, stage:Report" },
                new DialogueEntry { node = "report_early", requires = "order:order_steady_hands, !reported" },
                new DialogueEntry { node = "steady_gather", requires = "order:order_steady_hands, stage:Gather" },
                new DialogueEntry { node = "steady_bench", requires = "order:order_steady_hands, stage:Fabricate" },
                new DialogueEntry { node = "steady_fit", requires = "order:order_steady_hands, stage:Fit" },
                new DialogueEntry { node = "steady_test", requires = "order:order_steady_hands, stage:TestFire" },
                new DialogueEntry { node = "orders", requires = "primer, !freeplay" },
            };
            brann.nodes = new[]
            {
                N("greeting", "Salvage", "Salvage. I buy what comes back over the Berms, strip it, and sell the parts that still work. What do you need?",
                    trade, bench, C("Who are you?", "about")),
                N("first_visit", "Salvage",
                    "Brann. This is Salvage: I buy what the machines out on the Berms leave behind, strip it, and sell what still works. You've no sidearm and nothing to sell yet. The Wardens issue arms at Ossa's post beyond the market gate. Come back when the Berms have given you something.",
                    C("Show me what you trade anyway.", action: "shop", flag: "brann_met"), C("Who are you?", "about", flag: "brann_met"), C("I'll be back.", action: "close", flag: "brann_met")),
                N("about", "Brann",
                    "Ward runs on what comes back over the Berms. Servos, coils, charge cells: the depot out there used to make them. Now we pull them out of the machines that kept working after the people stopped. I pay fair for salvage, and my bench at the back is the best in Ward for turning it into something useful.",
                    trade, C("Back to business.", "greeting"), bye),
                N("report_ready", "Steady Hands",
                    "Ossa radioed ahead: said you cleared the depot nest. Let's see the haul... a worker servo, still twitching. Good. A scrap pistol kicks like a mule; a grip built round that servo takes the kick out of it. The bench is at the back.",
                    C("Show me the bench.", "bench_how"), C("Trade first.", action: "shop"), C("Later.", action: "close")),
                N("report_early", "Steady Hands",
                    "Ossa radioed ahead about you. Want a steadier grip on that pistol? I build them round a worker servo, and I'm out of servos. The worker droids at the old machine depot carry them, south along the service road. Bring one back with a couple of measures of scrap alloy and the bench is yours.",
                    C("Where's the depot?", "depot"), trade, C("I'll find one.", action: "close")),
                N("bench_how", "The workbench",
                    "Pick the Stabilised Pistol Grip from the schematics and fabricate it: one servo, two measures of scrap alloy, five of tier-one nanites. Then fit it to the pistol at the same bench. Short of alloy or nanites? I sell both, and servos too if you've the credits.",
                    C("Use the bench.", action: "fabricator", requires: "pistol"), trade, C("Thanks, Brann.", action: "close")),
                N("depot", "The machine depot",
                    "Out through the market gate, past Ossa's post, then south along the service road. The old machine depot is where the worker droids nest. They drop servos when you put them down. Watch their clamps.",
                    trade, C("I'll find one.", action: "close")),
                N("steady_gather", "Steady Hands",
                    "No servo yet? The worker droids at the depot carry them. Bring one back, with two measures of scrap alloy and some nanites, and the bench is yours.",
                    trade, C("Where's the depot?", "depot"), bye),
                N("steady_bench", "Steady Hands",
                    "That servo's ready. Bench is at the back: fabricate the grip, then fit it to the pistol right there.",
                    C("Use the bench.", action: "fabricator", requires: "pistol"), C("How does the bench work?", "bench_how"), bye),
                N("steady_fit", "Steady Hands",
                    "That's a good grip. Fit it to the pistol at the bench before you walk out with it in your pocket.",
                    C("Use the bench.", action: "fabricator", requires: "pistol"), trade, bye),
                N("steady_test", "Steady Hands",
                    "Feels steadier, doesn't it? Take it out past the gate and put a few shots into something. Ossa won't believe it until she hears it.",
                    trade, bench, C("On my way.", action: "close")),
                N("orders", "Salvage",
                    "Ossa keeps sending schematics to my bench. Whatever she's after next, the bench is yours, and I'm buying whatever the Berms give up.",
                    bench, trade, bye),
            };
            brann.shop = new ShopProfile { title = "Salvage", subtitle = "Brann · Parts and salvage", supplies = false, parts = true, salvage = true };
            if (created) AssetDatabase.CreateAsset(brann, BrannPath); else EditorUtility.SetDirty(brann);

            var mira = AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/npc_mira.asset");
            mira.shop = new ShopProfile(); EditorUtility.SetDirty(mira);

            var set = AssetDatabase.LoadAssetAtPath<FieldOrderSet>(OrdersPath);
            var o = set.orders;
            var steady = o.Single(x => x.id == "order_steady_hands");
            steady.brief = "Salvage a worker-droid servo at the machine depot, then take it to Brann at Salvage for a steadier pistol grip.";
            steady.reportTo = "npc_brann";
            steady.reportBrief = "Take the servo to Brann at Salvage, on the north avenue inside the walls. His workbench can make the {item}.";
            steady.reportGuidance = "dealer";
            void Line(string id, Func<FieldOrder, string> get, Action<FieldOrder, string> put, string from, string to)
            {
                var order = o.Single(x => x.id == id); var s = get(order) ?? "";
                if (s.Contains(from)) put(order, s.Replace(from, to));
            }
            Line("order_keep_charge", x => x.startLine, (x, v) => x.startLine = v, "I've sent charge-cell schematics to the fabricator.", "I've sent charge-cell schematics to Brann's bench.");
            Line("order_bore_true", x => x.startLine, (x, v) => x.startLine = v, "The fabricator can press alloy into proper plate", "Brann's bench can press alloy into proper plate");
            Line("order_depot_foreman", x => x.completeLine, (x, v) => x.completeLine = v, "They're in the fabricator now.", "They're on Brann's bench now.");
            set.fabricateFormat = "Fabricate the {item} at Brann's workbench in Salvage, on the north avenue.";
            set.fitFormat = "Fit the {item} to your {weapon} at Brann's workbench in Salvage.";
            set.freePlayObjective = "Free hunting: the Depot Foreman re-forms in the processing hall. Recover lattice shards and actuators for the other Mark II mods, and sell surplus salvage to Brann at Salvage or Mira at Basic General.";
            EditorUtility.SetDirty(set);

            var crafting = AssetDatabase.LoadAssetAtPath<CraftingCatalog>(CraftingPath);
            foreach (var st in crafting.stations) if (st.id == StationId) st.name = "Salvage workbench";
            EditorUtility.SetDirty(crafting);
            AssetDatabase.SaveAssets();
            return $"brann {(created ? "created" : "updated")} ({brann.nodes.Length} nodes, {brann.entries.Length} openings); order 1 reports to {steady.reportTo}; texts updated";
        }

        // ------------------------------------------------------------------ install
        sealed class Prop { public string name, path; public Vector2 xz; public float yaw, support; public float fitWidth; }
        // shop-local layout (x along the facade, +x south; z out to the avenue; floor at y 0.5). support < 0 = floor.
        static Prop P(string name, string path, float x, float z, float yaw, float support = -1, float fitWidth = 0)
            => new Prop { name = name, path = path, xz = new Vector2(x, z), yaw = yaw, support = support, fitWidth = fitWidth };
        const string SD = "Assets/AthenHill/Prefabs/StreetDressing/", TR = "Assets/AthenHill/Prefabs/TrainingRange/", SS = "Assets/AthenHill/Prefabs/SalvageShop/";
        const string TE = "Assets/AthenHill/Art/WardShops/ToolExchangeProps/";
        static Prop[] Layout(float counterTop) => new[]
        {
            // racks (1.23 x 0.57 m bays, the heavy stand 1.29 x 0.68 m) against the north wall; one behind the counter
            P("Parts rack · north 1", SS + "SS_PartsRack.prefab", -3.075f, -1.78f, 90),
            P("Parts rack · north 2", SS + "SS_PartsRack.prefab", -3.075f, -3.03f, 90),
            P("Heavy salvage stand", SS + "SS_PartsRackHeavy.prefab", -3.02f, -4.45f, 90),
            P("Parts rack · behind the counter", SS + "SS_PartsRack.prefab", 3.075f, -2.55f, -90),
            P("Parts rack · south", SS + "SS_PartsRack.prefab", 3.075f, -4.3f, -90),
            P("Tool cart", SD + "SD_tool_cart.prefab", -2.85f, -6.0f, 90),
            P("Compressor", TR + "TRP_compressor.prefab", 0.12f, -6.12f, 0),
            P("Steel drum", SD + "SD_drum_steel_blue.prefab", 0.72f, -0.82f, 20),
            P("Gas bottle", SD + "SD_gas_bottle.prefab", 0.5f, -0.62f, 0),
            P("Hand truck", SD + "SD_hand_truck.prefab", -3.1f, -0.85f, 75),
            P("Broom", SD + "SD_broom.prefab", -3.24f, -1.2f, 90),
            P("Brann's stool", SD + "SD_stool_wood.prefab", 2.75f, -1.25f, 15),
            P("Parts tote under the hoist", SD + "SD_tote_blue.prefab", 2.0f, -5.15f, 8),
            P("Tyre", SD + "SD_tyre.prefab", 3.0f, -6.05f, 0),
            P("Wheel rim", SD + "SD_rim_a.prefab", 2.65f, -6.15f, 40),
            P("Drone chassis on the counter", TE + "TE_drone_chassis.glb", 1.4f, -1.75f, -70, counterTop, .55f),
            P("Toolbox on the counter", SD + "SD_toolbox.prefab", 1.42f, -3.35f, 12, counterTop),
            P("Oil tin on the counter", SD + "SD_oil_tin.prefab", 1.3f, -2.85f, 0, counterTop),
            P("Rag on the counter", SD + "SD_rag.prefab", 1.5f, -2.25f, 30, counterTop),
        };

        static GameObject Instantiate(string path, Transform parent)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!asset) return null;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent.gameObject.scene);
            go.transform.SetParent(parent, false);
            return go;
        }
        static Bounds WorldBounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled && !(r is ParticleSystemRenderer)).ToArray();
            var b = rs.Length > 0 ? rs[0].bounds : new Bounds(go.transform.position, Vector3.zero);
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }
        /// Places a prop in shop-local coordinates with its renderer bounds resting on the support height.
        static GameObject Place(Transform root, Prop p, List<string> log)
        {
            var go = Instantiate(p.path, root);
            if (!go) { log.Add("missing " + p.path); return null; }
            go.name = p.name;
            go.transform.localRotation = Quaternion.Euler(0, p.yaw, 0);
            go.transform.localPosition = new Vector3(p.xz.x, 0, p.xz.y);
            if (p.fitWidth > 0)
            {
                go.transform.localScale = Vector3.one;
                var rot = go.transform.localRotation; go.transform.localRotation = Quaternion.identity;
                var b0 = WorldBounds(go); go.transform.localRotation = rot;
                float w = Mathf.Max(b0.size.x, b0.size.z);
                if (w > 1e-3f) go.transform.localScale = Vector3.one * (p.fitWidth / w);
            }
            // full detail only up close (about 6 m for a 2.2 m rack): from the street the lighter LOD1 reads the same
            foreach (var g in go.GetComponentsInChildren<LODGroup>(true))
            {
                var lods = g.GetLODs();
                if (lods.Length > 1 && lods[0].screenRelativeTransitionHeight < .6f) { lods[0].screenRelativeTransitionHeight = .6f; g.SetLODs(lods); }
            }
            float support = p.support < 0 ? Floor : p.support;
            var b = WorldBounds(go);
            float lift = root.TransformPoint(new Vector3(0, support, 0)).y - b.min.y;
            go.transform.position += Vector3.up * lift;
            // indoors the sun only reaches the bay floor on summer mornings: the props stay out of the sun's shadow
            // map (the racks alone are ~500k triangles at LOD0), and the lamps cast none
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                r.renderingLayerMask |= InteriorLayer;
                r.shadowCastingMode = ShadowCastingMode.Off;
            }
            return go;
        }

        static Light Lamp(Transform parent, string name, Vector3 local, Color c, float intensity, float range, LightType type = LightType.Point, float angle = 120)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.localPosition = local;
            if (type == LightType.Spot) go.transform.localRotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
            var l = go.AddComponent<Light>(); l.type = type; l.color = c; l.intensity = intensity; l.range = range; l.shadows = LightShadows.None;
            if (type == LightType.Spot) { l.spotAngle = angle; l.innerSpotAngle = angle * .55f; }
            l.renderingLayerMask = (int)InteriorLayer;
            return l;
        }

        static readonly (string name, Vector3 pos, Vector3 target, float fov)[] Cameras =
        {
            // shop-local metres; y is absolute (floor 0.5, eye 1.62 above it)
            ("cam_ss_bay", new Vector3(-1.2f, 2.12f, 3.4f), new Vector3(-1.0f, 1.5f, -4.8f), 60),
            ("cam_ss_counter", new Vector3(-1.9f, 2.12f, -1.15f), new Vector3(2.3f, 1.75f, -2.6f), 60),
            ("cam_ss_bench", new Vector3(0.45f, 2.12f, -3.1f), new Vector3(-1.3f, 1.35f, -6.25f), 60),
            ("cam_ss_racks", new Vector3(0.7f, 2.12f, -1.3f), new Vector3(-3.0f, 1.55f, -4.1f), 60),
            ("cam_ss_brann", new Vector3(0.62f, 2.15f, -2.45f), new Vector3(2.3f, 2.1f, -2.55f), 45),
            ("cam_ss_inside_out", new Vector3(1.4f, 2.12f, -5.5f), new Vector3(-1.3f, 1.9f, 1.0f), 60),
        };

        public static string Install()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var log = new List<string>();
            var shop = Find(scene, ShopPath) ?? throw new Exception("Salvage shop instance missing: " + ShopPath);
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var crafting = session.GetComponent<CraftingSession>();
            var orders = session.GetComponent<FieldOrders>();
            var tutorial = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>(FindObjectsInactive.Include);
            var circuit = UnityEngine.Object.FindAnyObjectByType<CityLightCircuit>(FindObjectsInactive.Include);
            var rec = Record();
            var interior = (JObject)rec["interior"] ?? throw new Exception("salvage.json has no interior record: re-run the Salvage authoring");
            float counterTop = (float)interior["counter"]["top"] + .055f;       // the timber slab

            // re-runnable: unhook and remove a previous install
            var old = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (old)
            {
                var oldNpcs = old.GetComponentsInChildren<NpcAgent>(true);
                session.npcs = session.npcs.Where(n => n && !oldNpcs.Contains(n)).ToArray();
                var oldLights = new HashSet<Light>(old.GetComponentsInChildren<Light>(true));
                circuit.practicalLights = circuit.practicalLights.Where(l => l && !oldLights.Contains(l)).ToArray();
                circuit.nightOnlyLights = circuit.nightOnlyLights.Where(l => l && !oldLights.Contains(l)).ToArray();
                UnityEngine.Object.DestroyImmediate(old);
                log.Add("replaced previous install");
            }
            var root = new GameObject(RootName).transform;
            root.SetPositionAndRotation(shop.position, shop.rotation);
            var b = interior["bounds"];
            var bmin = V3(b[0]); var bmax = V3(b[1]);

            // lamps: three pendants (the shades are in the shop model) and the workbench light, on the interior light layer
            var lamps = new GameObject("Lamps").transform; lamps.SetParent(root, false);
            var warm = new Color(1f, .76f, .5f);
            var lights = new List<Light>();
            foreach (var l in interior["lamps"])
            {
                var p = V3(l["pos"]) + Vector3.down * .07f;
                bool bench = ((string)l["name"]).Contains("workbench");
                lights.Add(Lamp(lamps, (string)l["name"] + " light", p, warm, bench ? 2.5f : 2.2f, bench ? 5.5f : 7f, LightType.Spot, bench ? 120 : 140));
            }
            // soft fill so the far corners are not black (no shadows; the room's own bounce stands in for GI)
            lights.Add(Lamp(lamps, "Room bounce", new Vector3(0.2f, 2.9f, -3.4f), new Color(1f, .82f, .62f), .45f, 6.5f));
            // night: lamplight spilling out of the open bay onto the porch (street light layer, Ward lighting clock)
            var spillGo = new GameObject("Bay spill"); spillGo.transform.SetParent(lamps, false);
            spillGo.transform.localPosition = new Vector3(-1.35f, 3.25f, -0.75f);
            spillGo.transform.localRotation = Quaternion.LookRotation(new Vector3(0, -2.6f, 3.2f).normalized, Vector3.up);
            var spill = spillGo.AddComponent<Light>(); spill.type = LightType.Spot; spill.color = warm; spill.intensity = 2.2f; spill.range = 7f;
            spill.spotAngle = 95; spill.innerSpotAngle = 50; spill.shadows = LightShadows.None;
            circuit.practicalLights = circuit.practicalLights.Concat(new[] { spill }).ToArray();
            circuit.nightOnlyLights = circuit.nightOnlyLights.Concat(new[] { spill }).ToArray();

            // props
            var props = new GameObject("Props").transform; props.SetParent(root, false);
            int placed = 0;
            foreach (var p in Layout(counterTop)) if (Place(props, p, log)) placed++;
            // a crashed scrap drone from the Berms hangs level from the hoist hook in a sling, waiting to be stripped
            var hook = V3(interior["hook"]);
            var droid = Instantiate("Assets/AthenHill/Prefabs/OuterBermsDepot/DP_CrashedDrone.prefab", props);
            if (droid)
            {
                droid.name = "Crashed drone on the hoist";
                droid.transform.localPosition = new Vector3(hook.x, 0, hook.z); droid.transform.localRotation = Quaternion.Euler(0, -75, 0);
                var db = WorldBounds(droid);
                droid.transform.position += Vector3.up * (root.TransformPoint(new Vector3(0, hook.y - .1f, 0)).y - db.max.y);
                foreach (var c in droid.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                foreach (var r in droid.GetComponentsInChildren<Renderer>(true)) { r.renderingLayerMask |= InteriorLayer; r.shadowCastingMode = ShadowCastingMode.Off; }
                // one box so nobody walks through it (it hangs at head height in the corner)
                var hb = WorldBounds(droid);
                var col = new GameObject("COL_HangingDrone"); col.transform.SetParent(props, true); col.transform.position = hb.center;
                col.AddComponent<BoxCollider>().size = hb.size;
                placed++;
            }
            else log.Add("missing DP_CrashedDrone");

            // workbench + its station (the E prompt sits at the worktop front)
            var benchGo = Instantiate(SS + "SS_Workbench.prefab", root);
            Transform benchRoot;
            if (benchGo)
            {
                // 1.17 m deep (rear frame included): its back stands 2 cm off the rear wall
                benchGo.name = "Workbench"; benchGo.transform.localPosition = new Vector3(-1.3f, Floor, -6.48f + .585f + .02f); benchGo.transform.localRotation = Quaternion.identity;
                foreach (var r in benchGo.GetComponentsInChildren<Renderer>(true)) { r.renderingLayerMask |= InteriorLayer; r.shadowCastingMode = ShadowCastingMode.Off; }
                foreach (var g in benchGo.GetComponentsInChildren<LODGroup>(true))
                {
                    var lods = g.GetLODs();
                    if (lods.Length > 1 && lods[0].screenRelativeTransitionHeight < .6f) { lods[0].screenRelativeTransitionHeight = .6f; g.SetLODs(lods); }
                }
                benchRoot = benchGo.transform;
            }
            else
            {
                // fallback until the hero bench exists: the training range repair bench
                benchGo = Instantiate(TR + "TR_RepairBench.prefab", root);
                if (!benchGo) throw new Exception("no workbench prefab");
                benchGo.name = "Workbench (stand-in)"; benchGo.transform.localPosition = new Vector3(-1.3f, Floor, -6.0f);
                log.Add("SS_Workbench missing: TR_RepairBench stands in");
                benchRoot = benchGo.transform;
            }
            var stationGo = new GameObject("Workbench station"); stationGo.transform.SetParent(root, false);
            var use = benchRoot.Find("Use point");
            stationGo.transform.localPosition = use ? root.InverseTransformPoint(use.position) + Vector3.up * .9f : new Vector3(-1.3f, Floor + .9f, -5.3f);
            var prompt = stationGo.AddComponent<WorldInteractable>(); prompt.prompt = "E · Use Brann's workbench"; prompt.range = 1.7f;
            var station = stationGo.AddComponent<CraftingStationMarker>();
            station.stationId = StationId; station.session = session; station.title = "Salvage workbench"; station.subtitle = "Brann's Salvage · Fabricate parts and fit pistol mods";
            var lightPoint = benchRoot.Find("Light point");
            // the print head's cyan, cast down on the worktop (at the lens it blew the head out at eye height)
            var glowAt = (lightPoint ? root.InverseTransformPoint(lightPoint.position) : new Vector3(-1.3f, Floor + 1.6f, -5.65f)) + new Vector3(0, -.38f, .12f);
            lights.Add(Lamp(lamps, "Fabricator glow", glowAt, new Color(.35f, .85f, 1f), .45f, 2.2f));

            // Brann behind the counter, facing the room
            var npcRoot = new GameObject("npc_brann").transform; npcRoot.SetParent(root, false);
            npcRoot.localPosition = new Vector3(2.3f, Floor, -2.55f); npcRoot.localRotation = Quaternion.Euler(0, -90, 0);
            var dealer = Instantiate("Assets/AthenHill/Prefabs/SalvageDealer.prefab", npcRoot) ?? throw new Exception("SalvageDealer prefab missing");
            dealer.name = "SalvageDealer"; dealer.transform.localPosition = Vector3.zero; dealer.transform.localRotation = Quaternion.identity;
            foreach (var r in dealer.GetComponentsInChildren<Renderer>(true)) r.renderingLayerMask |= InteriorLayer;
            // indoors and seen only from the avenue or inside: no skinning or animation while he is off screen
            foreach (var smr in dealer.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = false;
            foreach (var an in dealer.GetComponentsInChildren<Animation>(true)) an.cullingType = AnimationCullingType.BasedOnRenderers;
            var agent = npcRoot.gameObject.AddComponent<NpcAgent>();
            agent.definition = AssetDatabase.LoadAssetAtPath<NpcDefinition>(BrannPath) ?? throw new Exception("run the data step first");
            agent.actor = dealer.GetComponent<ActorAnimation>(); agent.countsForCityVisit = false; agent.workbench = station;
            session.npcs = session.npcs.Where(n => n).Concat(new[] { agent }).ToArray();

            // oil and grime on the floor (training range oil decal)
            var oil = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/TrainingRange/Materials/TR_DecalOil.mat");
            if (oil)
            {
                var decals = new GameObject("Decals").transform; decals.SetParent(root, false);
                foreach (var (n, x, z, s, yaw) in new[] { ("Oil under the hoist", 2.0f, -5.1f, 1.3f, 20f), ("Oil at the bench", -1.0f, -5.15f, 1.1f, 70f), ("Oil in the bay", -1.6f, -1.3f, 1.5f, 140f), ("Oil by the racks", -2.4f, -3.4f, .9f, 10f) })
                {
                    var go = new GameObject("Decal · " + n); go.transform.SetParent(decals, false);
                    go.transform.localPosition = new Vector3(x, Floor + .25f, z);
                    go.transform.localRotation = Quaternion.Euler(90, yaw, 0);
                    var d = go.AddComponent<DecalProjector>(); d.material = oil; d.size = new Vector3(s, s, .6f); d.pivot = Vector3.zero;
                    d.fadeFactor = .85f; d.drawDistance = 40; d.renderingLayerMask = uint.MaxValue;
                }
            }

            // interior reflection: box projected over the room (baked by the "bake" step)
            var probeGo = new GameObject("Interior reflection"); probeGo.transform.SetParent(root, false);
            probeGo.transform.localPosition = (bmin + bmax) / 2;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = ReflectionProbeMode.Baked; probe.boxProjection = true;
            probe.size = new Vector3(bmax.x - bmin.x, bmax.y - bmin.y, bmax.z - bmin.z); probe.blendDistance = .4f; probe.importance = 2;
            probe.intensity = .45f; probe.resolution = 128; probe.clearFlags = ReflectionProbeClearFlags.Skybox;
            var baked = AssetDatabase.LoadAssetAtPath<Cubemap>(ArtDir + "SalvageInteriorReflection.exr");
            if (baked) { probe.customBakedTexture = baked; probe.mode = ReflectionProbeMode.Custom; }

            // lighting for the room: interior ambient for the shell parts, props and Brann; the player blends in at the bay
            var il = root.gameObject.AddComponent<InteriorLighting>();
            il.localBounds = new Bounds((bmin + bmax) / 2, bmax - bmin);
            il.openingDirection = Vector3.forward;
            // the bay's outline at the facade (a little generous: the reveals and roller box narrow it)
            var bay = interior["bay"]; float bx0 = (float)bay["x"][0], bx1 = (float)bay["x"][1], btop = (float)bay["top"];
            il.openingCorners = new[] { new Vector3(bx0, Floor, .05f), new Vector3(bx1, Floor, .05f), new Vector3(bx1, btop, .05f), new Vector3(bx0, btop, .05f) };
            il.interiorRoots = new[] { props, npcRoot, benchRoot };
            il.renderers = shop.GetComponentsInChildren<Renderer>(true).Where(r => r.name.Contains("_Interior")).ToList();
            il.lamps = lights.ToArray();
            foreach (var r in il.renderers) r.renderingLayerMask |= InteriorLayer;

            // session wiring: the workbench replaces the field cart's station (the cart stays, as outpost dressing)
            var cart = Find(scene, CartPath);
            if (cart)
            {
                foreach (var m in cart.GetComponents<CraftingStationMarker>()) m.enabled = false;
                foreach (var w in cart.GetComponents<WorldInteractable>()) w.enabled = false;
                log.Add("field cart station retired (components disabled; cart kept)");
            }
            crafting.fabricator = stationGo.transform;
            var targets = orders.guidanceTargets.Where(t => t != null && t.key != "fabricator" && t.key != "dealer").ToList();
            targets.Add(new FieldOrders.Target { key = "fabricator", label = "SALVAGE WORKBENCH", point = stationGo.transform });
            targets.Add(new FieldOrders.Target { key = "dealer", label = "BRANN · SALVAGE", point = npcRoot });
            orders.guidanceTargets = targets.ToArray();
            tutorial.lineComplete = "Clean work. Take that salvage to Brann at Salvage, on the north avenue inside the walls. His bench can turn a worker servo into a steadier grip for that pistol. The depot always fills up again.";

            // landmarks (QA teleports) and review cameras
            var landmarks = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Landmarks");
            if (landmarks)
                foreach (var (n, local) in new[] { ("salvage_shop", new Vector3(-1.35f, Floor, 2.2f)), ("salvage_counter", new Vector3(.55f, Floor, -2.55f)), ("salvage_bench", new Vector3(-1.3f, Floor, -4.6f)) })
                {
                    var t = landmarks.transform.Find(n) ?? new GameObject(n).transform;
                    t.SetParent(landmarks.transform, true); t.position = root.TransformPoint(local);
                }
            var camRoot = new GameObject("Salvage shop review cameras").transform; camRoot.SetParent(root, false);
            foreach (var (n, pos, target, fov) in Cameras)
            {
                var go = new GameObject(n); go.transform.SetParent(camRoot, false);
                go.transform.localPosition = pos; go.transform.localRotation = Quaternion.LookRotation(target - pos, Vector3.up);
                var cam = go.AddComponent<Camera>(); cam.enabled = false; cam.fieldOfView = fov; cam.nearClipPlane = .05f; cam.farClipPlane = 650;
            }

            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (!t.GetComponent<Light>() && !t.GetComponent<Camera>() && !t.GetComponentInParent<NpcAgent>() && !t.GetComponent<WorldInteractable>())
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.OccludeeStatic | StaticEditorFlags.BatchingStatic);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            log.Add($"props {placed}, lamps {lights.Count}+spill, interior renderers {il.renderers.Count}, npcs {session.npcs.Length}");
            return string.Join("; ", log);
        }

        // ------------------------------------------------------------------ verify
        public static string Verify()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var problems = new List<string>();
            var r = new Dictionary<string, object>();
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            r["installed"] = root != null;
            if (!root) problems.Add("not installed");
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var crafting = session.GetComponent<CraftingSession>();
            var orders = session.GetComponent<FieldOrders>();
            var brann = session.npcs.FirstOrDefault(n => n && n.definition && n.definition.id == "npc_brann");
            r["brannInSession"] = brann != null; if (!brann) problems.Add("Brann not in GameSession.npcs");
            var station = crafting.fabricator ? crafting.fabricator.GetComponent<CraftingStationMarker>() : null;
            r["station"] = station ? PathOf(station.transform) : null;
            if (!station || !station.enabled || station.stationId != StationId || !station.session) problems.Add("workbench station not wired");
            if (brann && brann.workbench != station) problems.Add("Brann's workbench is not the station");
            var cart = Find(scene, CartPath);
            r["cartStationDisabled"] = cart && cart.GetComponents<CraftingStationMarker>().All(m => !m.enabled) && cart.GetComponents<WorldInteractable>().All(w => !w.enabled);
            if (!(bool)r["cartStationDisabled"]) problems.Add("field cart still a station");
            foreach (var key in new[] { "fabricator", "dealer", "depot", "foreman" })
                if (!orders.guidanceTargets.Any(t => t != null && t.key == key && t.point)) problems.Add("guidance " + key);
            // E-prompt rule: world interactables keep 2.4 m + their range from every colonist's stand point
            if (station)
                foreach (var n in session.npcs.Where(x => x))
                    if (Vector3.Distance(station.transform.position, n.transform.position) < session.interactionRange + station.GetComponent<WorldInteractable>().range)
                        problems.Add($"workbench inside {n.name}'s talk range");
            if (brann && station) r["benchToBrann"] = Math.Round(Vector3.Distance(brann.transform.position, station.transform.position), 2);
            // dialogue data: every opening and choice condition parses; every next node exists
            foreach (var def in AssetDatabase.FindAssets("t:NpcDefinition").Select(g => AssetDatabase.LoadAssetAtPath<NpcDefinition>(AssetDatabase.GUIDToAssetPath(g))))
            {
                foreach (var e in def.entries ?? new DialogueEntry[0])
                {
                    foreach (var p in QuestConditions.Problems(e.requires)) problems.Add($"{def.id} entry {e.node}: {p}");
                    if (!def.nodes.Any(n => n.id == e.node)) problems.Add($"{def.id} entry node {e.node} missing");
                }
                foreach (var n in def.nodes)
                    foreach (var c in n.choices ?? new DialogueChoice[0])
                    {
                        foreach (var p in QuestConditions.Problems(c.requires)) problems.Add($"{def.id}/{n.id} choice: {p}");
                        if (string.IsNullOrEmpty(c.action) && !def.nodes.Any(x => x.id == c.next)) problems.Add($"{def.id}/{n.id} '{c.label}' dead end");
                    }
            }
            // walk path: a 1.8 m capsule (r 0.3) clears the porch -> bay -> counter front -> bench front
            var shop = Find(scene, ShopPath);
            Physics.SyncTransforms();
            var path = new[] { new Vector3(-1.35f, 0, 2.6f), new Vector3(-1.35f, 0, .6f), new Vector3(-1.35f, 0, -.6f), new Vector3(-1.0f, 0, -1.8f), new Vector3(.55f, 0, -2.55f), new Vector3(-.4f, 0, -3.6f), new Vector3(-1.3f, 0, -4.95f) };
            var blocked = new List<string>();
            for (int i = 0; i < path.Length; i++)
            {
                var w = shop.TransformPoint(path[i] + Vector3.up * Floor);
                var hits = Physics.OverlapCapsule(w + Vector3.up * .36f, w + Vector3.up * 1.5f, .3f, ~(1 << 8), QueryTriggerInteraction.Ignore);
                foreach (var h in hits) blocked.Add($"point {i} {A(w)}: {PathOf(h.transform)}");
                if (i > 0)
                {
                    var a = shop.TransformPoint(path[i - 1] + Vector3.up * Floor);
                    if (Physics.CapsuleCast(a + Vector3.up * .36f, a + Vector3.up * 1.5f, .28f, (w - a).normalized, out var hit, (w - a).magnitude, ~(1 << 8), QueryTriggerInteraction.Ignore))
                        blocked.Add($"leg {i - 1}->{i}: {PathOf(hit.transform)}");
                }
                // floor under foot
                if (!Physics.Raycast(w + Vector3.up * .5f, Vector3.down, out var g, 1f, ~(1 << 8), QueryTriggerInteraction.Ignore) || Mathf.Abs(g.point.y - w.y) > .06f)
                    blocked.Add($"point {i}: no floor at {A(w)}");
            }
            r["pathBlocked"] = blocked; problems.AddRange(blocked);
            if (root)
            {
                var il = root.GetComponent<InteriorLighting>();
                r["interiorRenderers"] = il ? il.renderers.Count : 0;
                r["lamps"] = il ? il.lamps.Length : 0;
                r["props"] = root.transform.Find("Props")?.childCount ?? 0;
                r["missingMaterials"] = root.GetComponentsInChildren<Renderer>(true).Concat(shop.GetComponentsInChildren<Renderer>(true))
                    .Where(x => x.sharedMaterials.Any(m => !m)).Select(x => PathOf(x.transform)).ToArray();
                if (((string[])r["missingMaterials"]).Length > 0) problems.Add("missing materials");
            }
            var group = shop.GetComponent<LODGroup>();
            r["lodRenderers"] = group.GetLODs().Select(l => l.renderers.Length).ToArray();
            r["interiorInLods"] = group.GetLODs().SelectMany(l => l.renderers).Count(x => x && x.name.Contains("_Interior"));
            r["colliders"] = shop.Find("Colliders").Cast<Transform>().Select(t => t.name).ToArray();
            r["problems"] = problems;
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "verify.json", JsonConvert.SerializeObject(r, Formatting.Indented));
            return problems.Count == 0 ? "verify ok" : "verify problems: " + string.Join(" | ", problems.Take(12));
        }

        // ------------------------------------------------------------------ graphics steps
        public static string Bake()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var root = scene.GetRootGameObjects().First(g => g.name == RootName);
            var probe = root.GetComponentInChildren<ReflectionProbe>(true);
            probe.mode = ReflectionProbeMode.Baked;
            // the room as it renders in play (13:00 ambient through its interior probe), not the editor's sky-lit walls
            ApplyRoom(root, 13f);
            Directory.CreateDirectory(ArtDir);
            var path = ArtDir + "SalvageInteriorReflection.exr";
            if (!Lightmapping.BakeReflectionProbe(probe, path)) throw new Exception("interior reflection bake failed");
            AssetDatabase.ImportAsset(path);
            probe.customBakedTexture = AssetDatabase.LoadAssetAtPath<Cubemap>(path); probe.mode = ReflectionProbeMode.Custom;
            EditorUtility.SetDirty(probe);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            return "baked " + path;
        }

        /// The room's runtime lighting (custom ambient probe) applied for an editor render, from this hour's ambient.
        static void ApplyRoom(GameObject root, float hour)
        {
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>(FindObjectsInactive.Include);
            var f = clock.profile.Evaluate(hour);
            var (s0, e0, g0) = (RenderSettings.ambientSkyColor, RenderSettings.ambientEquatorColor, RenderSettings.ambientGroundColor);
            RenderSettings.ambientSkyColor = f.ambientSky; RenderSettings.ambientEquatorColor = f.ambientEquator; RenderSettings.ambientGroundColor = f.ambientGround;
            root.GetComponent<InteriorLighting>()?.ApplyInEditor();
            RenderSettings.ambientSkyColor = s0; RenderSettings.ambientEquatorColor = e0; RenderSettings.ambientGroundColor = g0;
        }

        /// Measurement: a prefab's renderer bounds at the origin (size, min, max) and each renderer's local bounds.
        static string PrefabBounds(string path)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
            try
            {
                var b = WorldBounds(go);
                var parts = go.GetComponentsInChildren<Renderer>(true).Select(r => $"{r.name} local {r.localBounds.size} rot {r.transform.rotation.eulerAngles}");
                return $"{path}: size {b.size} min {b.min} max {b.max}; " + string.Join("; ", parts.Take(6));
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }

        static int captured;
        public static string Capture(string hourText, string camList, string outDir)
        {
            var names = camList.Split('+');
            captured += names.Length;
            if (captured > 6) throw new Exception("at most 6 cameras per Unity run (VRAM rule)");
            float hour = float.Parse(hourText, Inv);
            var scene = EditorSceneManager.OpenScene(ScenePath);
            var root = scene.GetRootGameObjects().FirstOrDefault(g => g.name == RootName);
            if (root) ApplyRoom(root, hour);
            ShaderUtil.allowAsyncCompilation = false;
            DuskStartPass.Preview(hour, Path.Combine(outDir, "warmup"), names[0]);
            return DuskStartPass.Preview(hour, outDir, names);
        }

        // ------------------------------------------------------------------ survey (read-only)
        public static string Survey()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var all = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Transform>(true)).ToArray();
            var near = new List<object>();
            foreach (var t in all)
            {
                foreach (var r in t.GetComponents<Renderer>())
                    if (r.bounds.Intersects(Region))
                        near.Add(new { kind = "renderer", path = PathOf(t), active = t.gameObject.activeInHierarchy, r.enabled, c = A(r.bounds.center), s = A(r.bounds.size), mats = r.sharedMaterials.Select(m => m ? m.name : "null").ToArray() });
                foreach (var c in t.GetComponents<Collider>())
                    if (c.bounds.Intersects(Region))
                        near.Add(new { kind = "collider:" + c.GetType().Name, path = PathOf(t), active = t.gameObject.activeInHierarchy, c.enabled, c.isTrigger, layer = LayerMask.LayerToName(t.gameObject.layer), c = A(c.bounds.center), s = A(c.bounds.size) });
            }
            var session = UnityEngine.Object.FindAnyObjectByType<GameSession>(FindObjectsInactive.Include);
            var npcs = session.npcs.Where(n => n).Select(n => new
            {
                path = PathOf(n.transform), id = n.definition ? n.definition.id : null, pos = A(n.transform.position), yaw = n.transform.eulerAngles.y,
                n.countsForCityVisit, components = n.GetComponents<Component>().Select(c => c.GetType().Name).ToArray(),
                prefab = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(n.gameObject),
            }).ToArray();
            var stations = all.Select(t => t.GetComponent<CraftingStationMarker>()).Where(m => m).Select(m => new
            {
                path = PathOf(m.transform), m.stationId, pos = A(m.transform.position), active = m.gameObject.activeInHierarchy, m.enabled,
                prompt = m.GetComponent<WorldInteractable>()?.prompt, range = m.GetComponent<WorldInteractable>()?.range,
            }).ToArray();
            var orders = session.GetComponent<FieldOrders>();
            var guidance = orders ? orders.guidanceTargets.Select(g => new { g.key, g.label, point = g.point ? PathOf(g.point) : null, pos = g.point ? A(g.point.position) : null }).ToArray() : null;
            var crafting = session.GetComponent<CraftingSession>();
            var walkers = all.Select(t => t.GetComponent<AmbientWalker>()).Where(w => w).Select(w => new
            { path = PathOf(w.transform), route = w.waypoints == null ? null : w.waypoints.Select(o => o ? A(o.position) : null).ToArray() }).ToArray();
            var lights = all.Select(t => t.GetComponent<Light>()).Where(l => l && Vector3.Distance(l.transform.position, Region.center) < 22).Select(l => new
            { path = PathOf(l.transform), active = l.gameObject.activeInHierarchy, type = l.type.ToString(), pos = A(l.transform.position), l.range, l.intensity, shadows = l.shadows.ToString(), layers = l.renderingLayerMask }).ToArray();
            var probes = all.Select(t => t.GetComponent<ReflectionProbe>()).Where(p => p).Select(p => new { path = PathOf(p.transform), pos = A(p.transform.position), size = A(p.size), p.boxProjection, mode = p.mode.ToString(), p.importance, active = p.gameObject.activeInHierarchy }).ToArray();
            var landmarks = GameObject.Find("Landmarks");
            var marks = landmarks ? landmarks.GetComponentsInChildren<Transform>(true).Where(t => t != landmarks.transform).Select(t => new { t.name, pos = A(t.position) }).ToArray() : null;
            var shop = all.FirstOrDefault(t => PathOf(t) == ShopPath);
            var shopCols = shop ? shop.GetComponentsInChildren<BoxCollider>(true).Select(b => new { path = PathOf(b.transform), center = A(b.center), size = A(b.size), wc = A(b.bounds.center), ws = A(b.bounds.size) }).ToArray() : null;
            var tutorial = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>(FindObjectsInactive.Include);
            var report = new
            {
                date = DateTime.Now.ToString("s", Inv),
                layers = Enumerable.Range(0, 32).Select(i => i + ":" + LayerMask.LayerToName(i)).Where(s => !s.EndsWith(":")).ToArray(),
                occlusionData = StaticOcclusionCulling.umbraDataSize,
                lightProbeCount = LightmapSettings.lightProbes ? LightmapSettings.lightProbes.count : 0,
                interactionRange = session.interactionRange,
                npcs, stations, guidance, fabricator = crafting && crafting.fabricator ? PathOf(crafting.fabricator) : null,
                tutorialComplete = tutorial ? tutorial.lineComplete : null,
                walkers, lights, probes, landmarks = marks, shopCols, near,
            };
            Directory.CreateDirectory(Evidence);
            File.WriteAllText(Evidence + "survey.json", JsonConvert.SerializeObject(report, Formatting.Indented));
            return $"near {near.Count}, npcs {npcs.Length}, stations {stations.Length}, walkers {walkers.Length}";
        }

        /// -executeMethod AthenHill.Editor.SalvageShopPass.RunBatch --steps materials,models,data,install,verify
        /// (graphics steps: bake, capture:HOUR:cam+cam [--out dir]).
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string k, string d) { int i = Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            var steps = Arg("--steps", "survey").Split(',');
            var outDir = Arg("--out", Evidence + "editor");
            try
            {
                foreach (var st in steps)
                {
                    var parts = st.Split(':');
                    string result = parts[0] switch
                    {
                        "survey" => Survey(),
                        "materials" => "materials " + Materials().Count,
                        "models" => Models(),
                        "data" => Data(),
                        "install" => Install(),
                        "verify" => Verify(),
                        "bake" => Bake(),
                        "bounds" => PrefabBounds(parts[1]),
                        "capture" => Capture(parts[1], parts[2], outDir),
                        _ => throw new Exception("unknown step " + st),
                    };
                    Debug.Log("SalvageShopPass " + st + ": " + result);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
