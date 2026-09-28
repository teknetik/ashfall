using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>
    /// 27 September 2026 robot pass for the Outer Berms droids (sources: art/outer_berms_depot_20260927,
    /// make_robot_textures.py; art/outer_berms_20260926/merge_worker_droid.py + fix_worker_root_motion.py).
    ///
    /// Menu: Athen Hill → Outer Berms → Robots: build and apply. Idempotent: rebuilds the URP Lit materials, the dust
    /// and rotor-blur effect materials, splits the scrap drone's fused rotors into separate meshes, and edits the two
    /// droid prefabs in place (Health, FeralDroid tuning, colliders and DroidEncounter references are untouched):
    /// worker — URP Lit with the restored normal + metal/roughness maps and an optics-only emission map, foot bones,
    /// foot dust, footstep and wind-up clips; drone — weathered URP Lit body, two spinning rotors with blur discs,
    /// ground downwash, a rotor hum loop and a wind-up clip. Retired visuals stay in the prefab, inactive.
    /// </summary>
    public static class OuterBermsRobotPass
    {
        const string Art = "Assets/AthenHill/Art/OuterBerms/";
        const string TexDir = Art + "Textures/";
        const string MatDir = Art + "Materials/";
        const string MeshDir = Art + "Meshes/";
        const string Audio = "Assets/AthenHill/Audio/ElevenLabs/Combat/";
        const string WorkerPrefab = "Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab";
        const string DronePrefab = "Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab";
        const string Evidence = "../evidence/outer-berms-depot/20260927/";

        [MenuItem("Athen Hill/Outer Berms/Robots: build and apply")]
        public static void Menu() => Debug.Log(Apply());

        public static string Apply()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first");
            var record = new Dictionary<string, object>();
            ConfigureTextures();
            var worker = RobotMaterial("RB_WorkerDroid", "WorkerDroid", new Color(1.1f, .45f, .1f));
            var drone = RobotMaterial("RB_ScrapDrone", "ScrapDrone", new Color(1.1f, .3f, .08f));
            // the Meshy drone's lens is several overlapping shells on separate atlas islands, so an emission map on the
            // body lit only a crescent under the dome; the lens glow is a fitted emissive cap instead (LensCap)
            drone.SetTexture("_EmissionMap", null); drone.SetColor("_EmissionColor", Color.black); drone.DisableKeyword("_EMISSION");
            drone.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; EditorUtility.SetDirty(drone);
            var lens = LensMaterial();
            var dust = EffectMaterial("RB_DustPuff", "Assets/AthenHill/Art/Atmosphere/Dustbowl/SoftPuff.png", new Color(.62f, .52f, .4f, .55f));
            var blur = EffectMaterial("RB_RotorBlur", RotorBlurTexture(), new Color(.3f, .27f, .24f, .9f));
            var parts = SplitDrone(record);
            record["worker"] = ApplyWorker(worker, dust);
            record["drone"] = ApplyDrone(drone, lens, dust, blur, parts);
            foreach (var m in new[] { worker, lens }) { m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; m.EnableKeyword("_EMISSION"); EditorUtility.SetDirty(m); }
            AssetDatabase.SaveAssets();
            record["emissionKeyword"] = worker.IsKeywordEnabled("_EMISSION") && lens.IsKeywordEnabled("_EMISSION");
            Directory.CreateDirectory(Evidence);
            var json = JsonConvert.SerializeObject(record, Formatting.Indented);
            File.WriteAllText(Evidence + "robot-pass.json", json);
            return json;
        }

        // ------------------------------------------------------------------ textures and materials
        static void ConfigureTextures()
        {
            AssetDatabase.Refresh();
            foreach (var path in Directory.GetFiles(TexDir, "*.png").Select(p => p.Replace('\\', '/')))
            {
                if (AssetImporter.GetAtPath(path) is not TextureImporter ti) continue;
                var file = Path.GetFileNameWithoutExtension(path);
                bool normal = file.EndsWith("_Normal"), linear = file.EndsWith("_Mask") || file.EndsWith("_Emission");
                ti.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                ti.sRGBTexture = !normal && !linear;
                ti.maxTextureSize = 2048; ti.anisoLevel = 8; ti.mipmapEnabled = true; ti.streamingMipmaps = true;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                if (file.EndsWith("_Emission")) { ti.maxTextureSize = 1024; var ps = ti.GetPlatformTextureSettings("Standalone"); ps.overridden = true; ps.maxTextureSize = 1024; ti.SetPlatformTextureSettings(ps); }
                if (file.StartsWith("RB_RotorBlur")) { ti.alphaIsTransparency = true; ti.wrapMode = TextureWrapMode.Clamp; ti.maxTextureSize = 256; ti.sRGBTexture = true; ti.textureType = TextureImporterType.Default; }
                ti.SaveAndReimport();
            }
        }

        static Material LoadOrCreate(string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
            return m;
        }

        /// URP Lit: base, normal, metallic(R)/occlusion(G)/smoothness(A) mask, optics-only emission.
        static Material RobotMaterial(string name, string stem, Color glow)
        {
            var m = LoadOrCreate(name, Shader.Find("Universal Render Pipeline/Lit"));
            m.shader = Shader.Find("Universal Render Pipeline/Lit");
            Texture2D T(string s) => AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + stem + "_" + s + ".png");
            m.SetTexture("_BaseMap", T("BaseMap")); m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_BumpMap", T("Normal")); m.SetFloat("_BumpScale", 1.4f); m.EnableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", T("Mask")); m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1);
            m.SetTexture("_EmissionMap", T("Emission")); m.SetColor("_EmissionColor", glow); m.EnableKeyword("_EMISSION");
            // RealtimeEmissive (not None): URP's material validation drops _EMISSION from Lit materials flagged None
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            m.SetFloat("_Cull", 2); m.doubleSidedGI = false; m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        /// Soft transparent particle/disc material cloned from the dust-bowl smoke (URP Particles Simple Lit).
        static Material EffectMaterial(string name, string texture, Color tint)
        {
            var template = AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Atmosphere/Dustbowl/CookfireSmoke.mat");
            var path = MatDir + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(template) { name = name }; Directory.CreateDirectory(MatDir); AssetDatabase.CreateAsset(m, path); }
            else { m.shader = template.shader; m.CopyPropertiesFromMaterial(template); }
            m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(texture)); m.SetColor("_BaseColor", tint);
            if (m.HasProperty("_Cull")) m.SetFloat("_Cull", 0);
            EditorUtility.SetDirty(m);
            return m;
        }

        /// Motion-blurred two-blade rotor disc (hub hole, smeared blades, soft rim).
        static string RotorBlurTexture()
        {
            var path = TexDir + "RB_RotorBlur.png";
            const int N = 256; var tex = new Texture2D(N, N, TextureFormat.RGBA32, false);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float u = (x + .5f) / N * 2 - 1, v = (y + .5f) / N * 2 - 1, r = Mathf.Sqrt(u * u + v * v), th = Mathf.Atan2(v, u);
                    float radial = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.1f, .24f, r)) * (1 - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.86f, 1f, r)));
                    float blades = .45f + .55f * Mathf.Pow(.5f + .5f * Mathf.Cos(2 * th), 3);
                    float streak = .85f + .15f * Mathf.PerlinNoise(r * 22, .5f);
                    float a = Mathf.Clamp01(radial * blades * streak * .42f);
                    tex.SetPixel(x, y, new Color(1, 1, 1, a));
                }
            File.WriteAllBytes(path, tex.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            if (AssetImporter.GetAtPath(path) is TextureImporter ti)
            { ti.alphaIsTransparency = true; ti.wrapMode = TextureWrapMode.Clamp; ti.maxTextureSize = 256; ti.mipmapEnabled = true; ti.SaveAndReimport(); }
            return path;
        }

        // ------------------------------------------------------------------ scrap drone rotor split
        class DroneParts { public Mesh body; public Mesh[] rotors; public Vector3[] pivots; public float bladeRadius; }

        /// The Meshy drone is one fused mesh. Rotor blades + hub caps are the triangles above the rotor shafts
        /// (blade plane ≈ 0.21–0.27 m, within 0.66 m of each shaft axis, outside the central sphere); they become two
        /// meshes pivoted on their shaft axes so FeralDroid can spin them. The body keeps everything else.
        static DroneParts SplitDrone(Dictionary<string, object> record)
        {
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Art + "ScrapDrone.glb");
            var src = model.GetComponentInChildren<MeshFilter>().sharedMesh;
            var V = src.vertices; var N = src.normals; var UV = src.uv; var TG = src.tangents; var I = src.triangles;
            int nt = I.Length / 3; var C = new Vector3[nt];
            for (int t = 0; t < nt; t++) C[t] = (V[I[3 * t]] + V[I[3 * t + 1]] + V[I[3 * t + 2]]) / 3f;
            // shaft axes: thin columns between the motor pods and the blades
            var axes = new Vector2[2]; var sides = new[] { -1f, 1f };
            for (int s = 0; s < 2; s++)
            {
                var pts = Enumerable.Range(0, nt).Where(t => C[t].y > .14f && C[t].y < .2f && C[t].x * sides[s] > .45f).Select(t => new Vector2(C[t].x, C[t].z)).ToArray();
                if (pts.Length < 20) throw new Exception("Drone split: shaft " + s + " not found (" + pts.Length + ")");
                axes[s] = pts.Aggregate(Vector2.zero, (a, p) => a + p) / pts.Length;
            }
            var owner = new int[nt];
            for (int t = 0; t < nt; t++)
            {
                owner[t] = -1;
                for (int s = 0; s < 2; s++)
                {
                    var c = C[t]; float dAxis = Vector2.Distance(new Vector2(c.x, c.z), axes[s]);
                    bool blade = c.y > .205f || (dAxis > .1f && c.y > .15f);
                    if (blade && dAxis < .66f && new Vector2(c.x, c.z).magnitude > .33f && c.x * sides[s] > .15f) owner[t] = s;
                }
            }
            float hubY = .24f; var parts = new DroneParts { rotors = new Mesh[2], pivots = new Vector3[2] };
            Mesh Build(string name, int who, Vector3 pivot)
            {
                var map = new Dictionary<int, int>(); var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var tg = new List<Vector4>(); var tri = new List<int>();
                for (int t = 0; t < nt; t++)
                {
                    if (owner[t] != who) continue;
                    for (int k = 0; k < 3; k++)
                    {
                        int i = I[3 * t + k];
                        if (!map.TryGetValue(i, out int j)) { j = v.Count; map[i] = j; v.Add(V[i] - pivot); n.Add(N[i]); uv.Add(UV[i]); if (TG.Length > 0) tg.Add(TG[i]); }
                        tri.Add(j);
                    }
                }
                var m = new Mesh { name = name, indexFormat = v.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                m.SetVertices(v); m.SetNormals(n); m.SetUVs(0, uv); if (tg.Count == v.Count) m.SetTangents(tg); m.SetTriangles(tri, 0); m.RecalculateBounds();
                if (tg.Count != v.Count) m.RecalculateTangents();
                Directory.CreateDirectory(MeshDir);
                var path = MeshDir + name + ".asset"; var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (old) { old.Clear(); EditorUtility.CopySerialized(m, old); UnityEngine.Object.DestroyImmediate(m); return old; }
                AssetDatabase.CreateAsset(m, path); return m;
            }
            parts.body = Build("ScrapDrone_Body", -1, Vector3.zero);
            for (int s = 0; s < 2; s++)
            {
                parts.pivots[s] = new Vector3(axes[s].x, hubY, axes[s].y);
                parts.rotors[s] = Build("ScrapDrone_Rotor" + (s == 0 ? "A" : "B"), s, parts.pivots[s]);
            }
            parts.bladeRadius = parts.rotors.Max(r => r.vertices.Max(p => new Vector2(p.x, p.z).magnitude));
            record["droneSplit"] = new { bodyTriangles = parts.body.triangles.Length / 3, rotorTriangles = parts.rotors.Select(r => r.triangles.Length / 3).ToArray(),
                pivots = parts.pivots.Select(p => new[] { p.x, p.y, p.z }).ToArray(), bladeRadius = parts.bladeRadius };
            return parts;
        }

        static Material LensMaterial()
        {
            var path = TexDir + "RB_LensGlow.png";
            const int N = 128; var tex = new Texture2D(N, N, TextureFormat.RGBA32, false);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float u = (x + .5f) / N * 2 - 1, v = (y + .5f) / N * 2 - 1, r = Mathf.Sqrt(u * u + v * v);
                    // hot pupil, glowing iris ring, darker rim
                    float g = Mathf.Clamp01(1.1f - r * .9f) * .55f + Mathf.Exp(-Mathf.Pow((r - .45f) / .14f, 2)) * .5f + Mathf.Exp(-r * r / .02f) * .6f;
                    g = Mathf.Clamp01(g) * (1 - Mathf.SmoothStep(.85f, 1f, r));
                    tex.SetPixel(x, y, new Color(g, g, g, 1));
                }
            File.WriteAllBytes(path, tex.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            if (AssetImporter.GetAtPath(path) is TextureImporter ti) { ti.wrapMode = TextureWrapMode.Clamp; ti.sRGBTexture = false; ti.maxTextureSize = 128; ti.SaveAndReimport(); }
            var m = LoadOrCreate("RB_ScrapDroneLens", Shader.Find("Universal Render Pipeline/Lit"));
            m.SetColor("_BaseColor", new Color(.2f, .035f, .02f)); m.SetFloat("_Smoothness", .93f); m.SetFloat("_Metallic", 0);
            m.SetTexture("_EmissionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(path)); m.SetColor("_EmissionColor", new Color(1f, .28f, .07f)); m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive; m.enableInstancing = true; EditorUtility.SetDirty(m);
            return m;
        }

        /// Shallow dome over the drone's lens glass, in body-mesh space, with UVs projected front-on so the radial glow
        /// texture centres on the pupil. Centre/radius measured from the lens-glass texels on the Meshy mesh (dark red
        /// glass and its orange ring: centroid glTF (-0.015, 0.06, 0.26), ring radius ~0.07; Unity mesh x = -glTF x).
        /// The front-most vertices are the housing lip below the lens, so they cannot be used to place it.
        static Mesh LensCap(Mesh body, out Vector3 centre)
        {
            const float radius = .066f;
            var v = body.vertices;
            // surface depth at the lens centre: the front-most vertex within 2 cm of the lens axis
            var near = v.Where(p => new Vector2(p.x - .015f, p.y - .06f).magnitude < .02f).ToArray();
            float z = near.Length > 0 ? near.Max(p => p.z) : .266f;
            centre = new Vector3(.015f, .06f, z);
            var m = new Mesh { name = "ScrapDrone_Lens" }; var P = new List<Vector3>(); var UV = new List<Vector2>(); var T = new List<int>();
            const int seg = 20, rings = 5; float depth = .026f;
            P.Add(new Vector3(0, 0, .004f)); UV.Add(new Vector2(.5f, .5f));
            for (int r = 1; r <= rings; r++)
                for (int k = 0; k < seg; k++)
                {
                    float f = (float)r / rings, a = k * Mathf.PI * 2 / seg;
                    P.Add(new Vector3(Mathf.Cos(a) * radius * f, Mathf.Sin(a) * radius * f, .004f - depth * f * f));
                    UV.Add(new Vector2(.5f + Mathf.Cos(a) * f * .5f, .5f + Mathf.Sin(a) * f * .5f));
                }
            for (int k = 0; k < seg; k++) T.AddRange(new[] { 0, 1 + (k + 1) % seg, 1 + k });
            for (int r = 1; r < rings; r++)
                for (int k = 0; k < seg; k++)
                {
                    int a0 = 1 + (r - 1) * seg + k, a1 = 1 + (r - 1) * seg + (k + 1) % seg, b0 = a0 + seg, b1 = a1 + seg;
                    T.AddRange(new[] { a0, a1, b1, a0, b1, b0 });
                }
            m.SetVertices(P); m.SetUVs(0, UV); m.SetTriangles(T, 0); m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            // face +z (front); flip if the winding came out facing back
            if (m.normals[0].z < 0) { for (int t = 0; t < T.Count; t += 3) (T[t + 1], T[t + 2]) = (T[t + 2], T[t + 1]); m.SetTriangles(T, 0); m.RecalculateNormals(); m.RecalculateTangents(); }
            var path = MeshDir + "ScrapDrone_Lens.asset"; var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (old) { old.Clear(); EditorUtility.CopySerialized(m, old); UnityEngine.Object.DestroyImmediate(m); return old; }
            AssetDatabase.CreateAsset(m, path); return m;
        }

        static Mesh DiscMesh()
        {
            var path = MeshDir + "RB_RotorDisc.asset";
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (m) return m;
            m = new Mesh { name = "RB_RotorDisc" };
            m.vertices = new[] { new Vector3(-1, 0, -1), new Vector3(1, 0, -1), new Vector3(1, 0, 1), new Vector3(-1, 0, 1) };
            m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            m.normals = Enumerable.Repeat(Vector3.up, 4).ToArray();
            m.triangles = new[] { 0, 2, 1, 0, 3, 2 }; m.RecalculateBounds();
            Directory.CreateDirectory(MeshDir); AssetDatabase.CreateAsset(m, path); return m;
        }

        // ------------------------------------------------------------------ prefab edits
        static AudioClip Clip(string n) => AssetDatabase.LoadAssetAtPath<AudioClip>(Audio + n + ".wav");

        static ParticleSystem DustSystem(Transform parent, string name, Material mat, bool downwash)
        {
            var existing = parent.Find(name);
            if (existing) UnityEngine.Object.DestroyImmediate(existing.gameObject);
            var go = new GameObject(name, typeof(ParticleSystem)); go.transform.SetParent(parent, false);
            var ps = go.GetComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = true; main.loop = true; main.duration = 1; main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.maxParticles = downwash ? 48 : 36; main.gravityModifier = downwash ? -.02f : .05f;
            main.startLifetime = downwash ? new ParticleSystem.MinMaxCurve(.8f, 1.5f) : new ParticleSystem.MinMaxCurve(.6f, 1.1f);
            main.startSpeed = downwash ? new ParticleSystem.MinMaxCurve(1.2f, 2.4f) : new ParticleSystem.MinMaxCurve(.25f, .7f);
            main.startSize = downwash ? new ParticleSystem.MinMaxCurve(.35f, .7f) : new ParticleSystem.MinMaxCurve(.18f, .38f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.startColor = new Color(1, 1, 1, 1);
            var em = ps.emission; em.enabled = true; em.rateOverTime = 0;
            var shape = ps.shape; shape.enabled = true;
            if (downwash) { shape.shapeType = ParticleSystemShapeType.Circle; shape.radius = .35f; shape.radiusThickness = 0; shape.rotation = new Vector3(-90, 0, 0); }
            else { shape.shapeType = ParticleSystemShapeType.Hemisphere; shape.radius = .12f; shape.rotation = new Vector3(-90, 0, 0); }
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, new AnimationCurve(new Keyframe(0, .5f), new Keyframe(1, 1.6f)));
            var col = ps.colorOverLifetime; col.enabled = true; var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(downwash ? .45f : .7f, .15f), new GradientAlphaKey(0, 1) });
            col.color = g;
            var vel = ps.limitVelocityOverLifetime; vel.enabled = true; vel.limit = downwash ? 1.2f : .5f; vel.dampen = .15f;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = mat; r.renderMode = ParticleSystemRenderMode.Billboard; r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            r.sortingFudge = 2; r.maxParticleSize = .6f;
            return ps;
        }

        static object ApplyWorker(Material mat, Material dust)
        {
            var root = PrefabUtility.LoadPrefabContents(WorkerPrefab);
            try
            {
                var fd = root.GetComponent<FeralDroid>();
                var smr = root.GetComponentInChildren<SkinnedMeshRenderer>(true);
                smr.sharedMaterial = mat; smr.shadowCastingMode = ShadowCastingMode.On;
                // the death fall and the attack lunge leave the import bounds; keep the corpse from being culled
                var b = smr.localBounds; b.Expand(new Vector3(150, 60, 150)); smr.localBounds = b;
                fd.glowRenderers = new Renderer[] { smr };
                fd.glowCalm = new Color(1.1f, .45f, .1f); fd.glowHostile = new Color(3.2f, 1f, .2f); fd.glowWindup = new Color(8f, 4.6f, 2f); fd.hitFlash = 4;
                fd.windupClip = Clip("droid-windup"); fd.windupVolume = .9f;
                fd.footstepClips = new[] { Clip("droid-step-1"), Clip("droid-step-2") }.Where(c => c).ToArray(); fd.footstepVolume = .55f;
                var bones = root.GetComponentsInChildren<Transform>(true);
                fd.feet = new[] { "LeftToeBase", "RightToeBase" }.Select(n => bones.First(t => t.name == n)).ToArray();
                fd.footDust = DustSystem(root.transform, "Foot dust", dust, false);
                // the optic light was a point light inside the droid's own silhouette and lit its arms orange during the
                // wind-up; as a forward spot it throws the optic's glare onto the ground and the target instead
                if (fd.eyeLight) { var l = fd.eyeLight; l.type = LightType.Spot; l.spotAngle = 80; l.innerSpotAngle = 30; l.range = 8; l.color = new Color(1f, .55f, .2f); l.shadows = LightShadows.None; }
                PrefabUtility.SaveAsPrefabAsset(root, WorkerPrefab);
                return new { material = mat.name, feet = fd.feet.Select(f => f.name).ToArray(), steps = fd.footstepClips.Length, windup = fd.windupClip ? fd.windupClip.name : null };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }

        static object ApplyDrone(Material mat, Material lensMat, Material dust, Material blurMat, DroneParts parts)
        {
            var root = PrefabUtility.LoadPrefabContents(DronePrefab);
            try
            {
                var fd = root.GetComponent<FeralDroid>();
                var visual = root.transform.Find("Visual");
                var old = visual.Find("ScrapDrone");
                var rig = visual.Find("ScrapDrone rig");
                if (rig) UnityEngine.Object.DestroyImmediate(rig.gameObject);
                rig = new GameObject("ScrapDrone rig", typeof(MeshFilter), typeof(MeshRenderer)).transform;
                rig.SetParent(visual, false); rig.localPosition = old.localPosition; rig.localRotation = old.localRotation; rig.localScale = old.localScale;
                rig.SetSiblingIndex(old.GetSiblingIndex() + 1);
                rig.GetComponent<MeshFilter>().sharedMesh = parts.body;
                var body = rig.GetComponent<MeshRenderer>(); body.sharedMaterial = mat;
                old.gameObject.SetActive(false);   // retired fused mesh (static rotors), kept for rollback
                var disc = DiscMesh(); var rotors = new List<Transform>();
                for (int s = 0; s < 2; s++)
                {
                    var r = new GameObject("Rotor " + (s == 0 ? "A" : "B"), typeof(MeshFilter), typeof(MeshRenderer)).transform;
                    r.SetParent(rig, false); r.localPosition = parts.pivots[s];
                    r.GetComponent<MeshFilter>().sharedMesh = parts.rotors[s];
                    var mr = r.GetComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = ShadowCastingMode.Off;
                    var d = new GameObject("Blur disc", typeof(MeshFilter), typeof(MeshRenderer)).transform;
                    d.SetParent(r, false); d.localPosition = new Vector3(0, .004f, 0); d.localScale = Vector3.one * parts.bladeRadius * 1.02f;
                    d.GetComponent<MeshFilter>().sharedMesh = disc;
                    var dr = d.GetComponent<MeshRenderer>(); dr.sharedMaterial = blurMat; dr.shadowCastingMode = ShadowCastingMode.Off; dr.receiveShadows = false;
                    rotors.Add(r);
                }
                fd.rotors = rotors.ToArray(); fd.rotorSpeed = 1500; fd.rotorWindupSpeed = 2800;
                var capMesh = LensCap(parts.body, out var capCentre);
                var cap = new GameObject("Lens glow", typeof(MeshFilter), typeof(MeshRenderer)).transform;
                cap.SetParent(rig, false); cap.localPosition = capCentre;
                cap.GetComponent<MeshFilter>().sharedMesh = capMesh;
                var capR = cap.GetComponent<MeshRenderer>(); capR.sharedMaterial = lensMat; capR.shadowCastingMode = ShadowCastingMode.Off;
                fd.glowRenderers = new Renderer[] { capR };
                // native review: the first wind-up flare (11, 5, 2) blew the lens out to a flat yellow splat
                fd.glowCalm = new Color(1f, .28f, .07f); fd.glowHostile = new Color(2.6f, .6f, .1f); fd.glowWindup = new Color(6f, 2f, .5f); fd.hitFlash = 4;
                fd.windupClip = Clip("drone-windup"); fd.windupVolume = .85f;
                fd.downwash = DustSystem(root.transform, "Rotor downwash", dust, true); fd.downwashRate = 26;
                var hum = root.transform.Find("Rotor hum");
                if (hum) UnityEngine.Object.DestroyImmediate(hum.gameObject);
                var loop = new GameObject("Rotor hum", typeof(AudioSource)).GetComponent<AudioSource>(); loop.transform.SetParent(root.transform, false);
                loop.clip = Clip("drone-rotor"); loop.loop = true; loop.playOnAwake = true; loop.spatialBlend = 1; loop.dopplerLevel = .3f;
                loop.rolloffMode = AudioRolloffMode.Linear; loop.minDistance = 1.5f; loop.maxDistance = 20; loop.volume = 1;
                loop.outputAudioMixerGroup = fd.voice ? fd.voice.outputAudioMixerGroup : null;
                fd.motorLoop = loop;
                if (fd.eyeLight)
                {
                    var l = fd.eyeLight; l.type = LightType.Spot; l.spotAngle = 75; l.innerSpotAngle = 30; l.range = 7; l.color = new Color(1f, .42f, .15f); l.shadows = LightShadows.None;
                    l.transform.localPosition = new Vector3(0, -.02f, .3f); l.transform.localRotation = Quaternion.Euler(22, 0, 0);
                }
                PrefabUtility.SaveAsPrefabAsset(root, DronePrefab);
                return new { material = mat.name, rotors = rotors.Count, bladeRadius = parts.bladeRadius, hum = loop.clip ? loop.clip.name : null, windup = fd.windupClip ? fd.windupClip.name : null };
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }
    }
}
