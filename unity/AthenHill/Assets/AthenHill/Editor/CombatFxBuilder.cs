using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Authors the combat effect assets from the procedural textures in Art/FX/Textures
    /// (unity/tools/make_fx_textures.py): URP particle materials, a debris shard mesh, and two pooled prefabs —
    /// Prefabs/FX/DroidDeathBurst and Prefabs/FX/HitFlash — used by CombatFx. Re-running rebuilds the materials and
    /// prefabs in place (their GUIDs are kept), so tuning here and re-running is the edit workflow.
    public static class CombatFxBuilder
    {
        const string Root = "Assets/AthenHill/Art/FX", Tex = Root + "/Textures", Mat = Root + "/Materials", PrefabDir = "Assets/AthenHill/Prefabs/FX";

        [MenuItem("Athen Hill/Combat/Build combat FX prefabs")]
        public static void Build()
        {
            Directory.CreateDirectory(Mat); Directory.CreateDirectory(PrefabDir); AssetDatabase.Refresh();
            var smokeTex = Texture(Tex + "/FX_SmokeFlipbook.png", true, 2048);
            var fireTex = Texture(Tex + "/FX_FireFlipbook.png", false, 1024);
            var sparkTex = Texture(Tex + "/FX_Spark.png", false, 128);
            var glowTex = Texture(Tex + "/FX_Glow.png", false, 128);

            var smoke = ParticleMaterial("FX_Smoke", "Universal Render Pipeline/Particles/Lit", smokeTex, blend: 0, flipbookBlend: true);
            var fire = ParticleMaterial("FX_Fire", "Universal Render Pipeline/Particles/Unlit", fireTex, blend: 2, flipbookBlend: true);
            var spark = ParticleMaterial("FX_Spark", "Universal Render Pipeline/Particles/Unlit", sparkTex, blend: 2, flipbookBlend: false);
            var glow = ParticleMaterial("FX_Glow", "Universal Render Pipeline/Particles/Unlit", glowTex, blend: 2, flipbookBlend: false);
            fire.SetColor("_BaseColor", new Color(3.2f, 2.4f, 1.6f)); spark.SetColor("_BaseColor", new Color(6f, 4.5f, 3f)); glow.SetColor("_BaseColor", new Color(5f, 3.8f, 2.6f));
            var debrisMat = ParticleMaterial("FX_Debris", "Universal Render Pipeline/Particles/Lit", null, blend: -1, flipbookBlend: false);
            debrisMat.SetColor("_BaseColor", new Color(.23f, .21f, .19f)); debrisMat.SetFloat("_Metallic", .6f); debrisMat.SetFloat("_Smoothness", .35f);
            var shard = ShardMesh();

            BuildDeathBurst(smoke, fire, spark, glow, debrisMat, shard);
            BuildHitFlash(spark, glow);
            AssetDatabase.SaveAssets();
            Debug.Log("COMBAT_FX built prefabs in " + PrefabDir);
        }

        public static void BuildBatch() { Build(); EditorApplication.Exit(0); }

        static void BuildDeathBurst(Material smoke, Material fire, Material spark, Material glow, Material debris, Mesh shard)
        {
            var root = new GameObject("DroidDeathBurst"); var fx = root.AddComponent<FxBurst>();
            fx.lifetime = 9; fx.flashIntensity = 38; fx.flashSeconds = .18f; fx.burnSeconds = 5.5f; fx.burnIntensity = 2.4f;
            var lightGo = new GameObject("Flash light"); lightGo.transform.SetParent(root.transform, false); lightGo.transform.localPosition = Vector3.up * .5f;
            var light = lightGo.AddComponent<Light>(); light.type = LightType.Point; light.color = new Color(1f, .7f, .42f); light.range = 9; light.intensity = 0; light.shadows = LightShadows.None; light.enabled = false;
            fx.flash = light;
            var systems = new List<ParticleSystem>(); var optional = new List<ParticleSystem>();

            // Core flash: one big additive glow for a couple of frames.
            var core = System(root, "Flash glow", glow, 1.2f, .1f, .14f, 0, 0, 3.6f, 4.2f);
            Burst(core, 1); Colors(core, new Color(1f, .9f, .75f), new Color(1f, .45f, .15f), 1f, 0f); systems.Add(core);

            // Sparks: hot stretched streaks that fall and bounce.
            var sp = System(root, "Sparks", spark, 1.2f, .35f, 1.2f, 4f, 12f, .04f, .08f);
            var m = sp.main; m.gravityModifier = 1.3f; m.maxParticles = 120;
            Burst(sp, 95); Shape(sp, ParticleSystemShapeType.Sphere, .25f);
            Colors(sp, new Color(1f, .95f, .8f), new Color(1f, .35f, .08f), 1f, 0f);
            Stretch(sp, .055f, 1.6f); Collide(sp, .3f, .45f); systems.Add(sp);

            // Debris: lit metal shards tumbling out and settling.
            var db = System(root, "Debris", debris, 4f, 2.6f, 4f, 2.5f, 6.5f, .05f, .14f);
            m = db.main; m.gravityModifier = 2.2f; m.startRotation3D = true; m.startRotationX = Range(0, 6.28f); m.startRotationY = Range(0, 6.28f); m.startRotationZ = Range(0, 6.28f);
            Burst(db, 16); Shape(db, ParticleSystemShapeType.Hemisphere, .3f);
            var rot = db.rotationOverLifetime; rot.enabled = true; rot.separateAxes = true; rot.x = Range(-6, 6); rot.y = Range(-6, 6); rot.z = Range(-6, 6);
            Colors(db, Color.white, Color.white, 1f, 1f, fadeTail: true); Collide(db, .25f, .6f);
            var dr = db.GetComponent<ParticleSystemRenderer>(); dr.renderMode = ParticleSystemRenderMode.Mesh; dr.mesh = shard; dr.alignment = ParticleSystemRenderSpace.Local;
            dr.SetActiveVertexStreams(new List<ParticleSystemVertexStream> { ParticleSystemVertexStream.Position, ParticleSystemVertexStream.Normal, ParticleSystemVertexStream.Color, ParticleSystemVertexStream.UV });
            dr.shadowCastingMode = ShadowCastingMode.On; systems.Add(db); optional.Add(db);

            // Fireball: short additive flame bloom.
            var fb = System(root, "Fireball", fire, .8f, .4f, .75f, .5f, 2f, 1.4f, 2.4f);
            Burst(fb, 10); Shape(fb, ParticleSystemShapeType.Sphere, .35f); Sheet(fb, 4, 4, false);
            Colors(fb, new Color(1f, .92f, .7f), new Color(.9f, .22f, .05f), 1f, 0f);
            Grow(fb, 1.6f); systems.Add(fb);

            // Smoke plume: lit, soft, billowing up and spreading.
            var sm = System(root, "Smoke plume", smoke, 4.5f, 3.8f, 6.5f, .6f, 1.4f, 1.3f, 2.2f);
            m = sm.main; m.startDelay = .05f; m.gravityModifier = -.08f; m.startRotation = Range(0, 6.28f); m.maxParticles = 60;
            var em = sm.emission; em.rateOverTime = 10; Burst(sm, 8, keepRate: true);
            Shape(sm, ParticleSystemShapeType.Cone, .35f, 18);
            Sheet(sm, 8, 8, false); Grow(sm, 3.2f);
            var rotS = sm.rotationOverLifetime; rotS.enabled = true; rotS.z = Range(-.4f, .4f);
            Colors(sm, new Color(.13f, .12f, .11f), new Color(.4f, .38f, .35f), .0f, 0f, smokeAlpha: true);
            var noise = sm.noise; noise.enabled = true; noise.strength = .35f; noise.frequency = .35f; noise.scrollSpeed = .2f;
            systems.Add(sm);

            // Burn: small flames licking the wreck for a few seconds.
            var burn = System(root, "Burn", fire, 5.5f, .45f, .85f, .2f, .7f, .45f, .8f);
            var eb = burn.emission; eb.rateOverTime = 9; Shape(burn, ParticleSystemShapeType.Circle, .45f); Sheet(burn, 4, 4, true);
            Colors(burn, new Color(1f, .8f, .45f), new Color(.8f, .2f, .04f), 1f, 0f); systems.Add(burn);

            // Embers: tiny drifting sparks above the burn.
            var emb = System(root, "Embers", spark, 5.5f, 1.2f, 2.4f, .3f, 1.1f, .02f, .035f);
            var ee = emb.emission; ee.rateOverTime = 8; Shape(emb, ParticleSystemShapeType.Circle, .5f); m = emb.main; m.gravityModifier = -.12f;
            var en = emb.noise; en.enabled = true; en.strength = .6f; en.frequency = .8f;
            Colors(emb, new Color(1f, .75f, .35f), new Color(.9f, .2f, .05f), 1f, 0f); Stretch(emb, .03f, 1.2f); systems.Add(emb); optional.Add(emb);

            fx.systems = systems.ToArray(); fx.optional = optional.ToArray();
            Save(root, PrefabDir + "/DroidDeathBurst.prefab");
        }

        static void BuildHitFlash(Material spark, Material glow)
        {
            var root = new GameObject("HitFlash"); var fx = root.AddComponent<FxBurst>();
            fx.lifetime = .6f; fx.flashIntensity = 7; fx.flashSeconds = .07f;
            var lightGo = new GameObject("Flash light"); lightGo.transform.SetParent(root.transform, false);
            var light = lightGo.AddComponent<Light>(); light.type = LightType.Point; light.color = new Color(.75f, .9f, 1f); light.range = 3; light.intensity = 0; light.shadows = LightShadows.None; light.enabled = false;
            fx.flash = light;
            var g = System(root, "Glow", glow, .2f, .05f, .07f, 0, 0, .35f, .5f); Burst(g, 1); Colors(g, new Color(.85f, .95f, 1f), new Color(.4f, .7f, 1f), 1f, 0f);
            var s = System(root, "Sparks", spark, .3f, .15f, .35f, 2.5f, 6f, .02f, .04f);
            var m = s.main; m.gravityModifier = 1f; Burst(s, 9); Shape(s, ParticleSystemShapeType.Sphere, .05f); Stretch(s, .04f, 1.3f);
            Colors(s, new Color(1f, .95f, .85f), new Color(1f, .5f, .15f), 1f, 0f);
            fx.systems = new[] { g, s }; fx.optional = new ParticleSystem[0];
            Save(root, PrefabDir + "/HitFlash.prefab");
        }

        static ParticleSystem System(GameObject root, string name, Material mat, float duration, float lifeMin, float lifeMax, float speedMin, float speedMax, float sizeMin, float sizeMax)
        {
            var go = new GameObject(name); go.transform.SetParent(root.transform, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var m = ps.main; m.duration = duration; m.loop = false; m.playOnAwake = false; m.simulationSpace = ParticleSystemSimulationSpace.World;
            m.startLifetime = Range(lifeMin, lifeMax); m.startSpeed = Range(speedMin, speedMax); m.startSize = Range(sizeMin, sizeMax);
            m.scalingMode = ParticleSystemScalingMode.Hierarchy; m.maxParticles = 80;
            var e = ps.emission; e.rateOverTime = 0;
            var sh = ps.shape; sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = .1f;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            r.sortingFudge = 0; r.minParticleSize = 0; r.maxParticleSize = 2;
            if (mat && mat.shader.name.Contains("Lit") && mat.HasProperty("_FlipbookBlending") && mat.GetFloat("_FlipbookBlending") > 0)
                r.SetActiveVertexStreams(new List<ParticleSystemVertexStream> { ParticleSystemVertexStream.Position, ParticleSystemVertexStream.Normal, ParticleSystemVertexStream.Color, ParticleSystemVertexStream.UV, ParticleSystemVertexStream.UV2, ParticleSystemVertexStream.AnimBlend });
            else if (mat && mat.HasProperty("_FlipbookBlending") && mat.GetFloat("_FlipbookBlending") > 0)
                r.SetActiveVertexStreams(new List<ParticleSystemVertexStream> { ParticleSystemVertexStream.Position, ParticleSystemVertexStream.Color, ParticleSystemVertexStream.UV, ParticleSystemVertexStream.UV2, ParticleSystemVertexStream.AnimBlend });
            return ps;
        }

        static ParticleSystem.MinMaxCurve Range(float a, float b) => new ParticleSystem.MinMaxCurve(a, b);
        static void Burst(ParticleSystem ps, int count, bool keepRate = false) { var e = ps.emission; e.enabled = true; if (!keepRate) e.rateOverTime = 0; e.SetBursts(new[] { new ParticleSystem.Burst(0, (short)count) }); }
        static void Shape(ParticleSystem ps, ParticleSystemShapeType type, float radius, float angle = 25) { var s = ps.shape; s.enabled = true; s.shapeType = type; s.radius = radius; s.angle = angle; if (type == ParticleSystemShapeType.Cone || type == ParticleSystemShapeType.Circle || type == ParticleSystemShapeType.Hemisphere) s.rotation = new Vector3(-90, 0, 0); }
        static void Stretch(ParticleSystem ps, float velocityScale, float lengthScale) { var r = ps.GetComponent<ParticleSystemRenderer>(); r.renderMode = ParticleSystemRenderMode.Stretch; r.velocityScale = velocityScale; r.lengthScale = lengthScale; }
        static void Collide(ParticleSystem ps, float bounce, float dampen) { var c = ps.collision; c.enabled = true; c.type = ParticleSystemCollisionType.World; c.mode = ParticleSystemCollisionMode.Collision3D; c.quality = ParticleSystemCollisionQuality.Medium; c.bounce = bounce; c.dampen = dampen; c.lifetimeLoss = 0; c.radiusScale = .5f; }
        static void Grow(ParticleSystem ps, float end) { var s = ps.sizeOverLifetime; s.enabled = true; s.size = new ParticleSystem.MinMaxCurve(1, new AnimationCurve(new Keyframe(0, 1f / end, 0, 2.5f), new Keyframe(1, 1, 0, 0))); }
        static void Sheet(ParticleSystem ps, int x, int y, bool randomRow)
        {
            var t = ps.textureSheetAnimation; t.enabled = true; t.mode = ParticleSystemAnimationMode.Grid; t.numTilesX = x; t.numTilesY = y;
            t.animation = ParticleSystemAnimationType.WholeSheet; t.frameOverTime = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 0, 1, 1));
            t.startFrame = randomRow ? Range(0, x * y - 1) : new ParticleSystem.MinMaxCurve(0); t.cycleCount = randomRow ? 2 : 1;
        }
        static void Colors(ParticleSystem ps, Color from, Color to, float alphaStart, float alphaEnd, bool fadeTail = false, bool smokeAlpha = false)
        {
            var g = new Gradient();
            GradientAlphaKey[] alpha = smokeAlpha
                ? new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(.92f, .07f), new GradientAlphaKey(.7f, .45f), new GradientAlphaKey(0, 1) }
                : fadeTail ? new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, .8f), new GradientAlphaKey(0, 1) }
                : new[] { new GradientAlphaKey(alphaStart, 0), new GradientAlphaKey(alphaEnd, 1) };
            g.SetKeys(new[] { new GradientColorKey(from, 0), new GradientColorKey(to, 1) }, alpha);
            var c = ps.colorOverLifetime; c.enabled = true; c.color = new ParticleSystem.MinMaxGradient(g);
        }

        static Material ParticleMaterial(string name, string shaderName, Texture2D tex, int blend, bool flipbookBlend)
        {
            string path = Mat + "/" + name + ".mat";
            var shader = Shader.Find(shaderName); if (!shader) throw new InvalidOperationException("Missing shader " + shaderName);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat) { mat = new Material(shader) { name = name }; AssetDatabase.CreateAsset(mat, path); }
            mat.shader = shader;
            if (tex) mat.SetTexture("_BaseMap", tex);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Surface", blend < 0 ? 0 : 1); if (blend >= 0) mat.SetFloat("_Blend", blend);
            mat.SetFloat("_FlipbookBlending", flipbookBlend ? 1 : 0);
            mat.SetFloat("_SoftParticlesEnabled", blend >= 0 ? 1 : 0); mat.SetFloat("_SoftParticlesNearFadeDistance", 0); mat.SetFloat("_SoftParticlesFarFadeDistance", .6f);
            mat.SetFloat("_CameraFadingEnabled", blend >= 0 ? 1 : 0); mat.SetFloat("_CameraNearFadeDistance", .3f); mat.SetFloat("_CameraFarFadeDistance", 1.2f);
            if (mat.HasProperty("_ReceiveShadows")) mat.SetFloat("_ReceiveShadows", 1);
            // Matte, non-reflective particles: with "preserve specular" alpha blending, sky reflections would light
            // the whole quad even where the texture is transparent (visible square cards).
            if (mat.HasProperty("_BlendModePreserveSpecular")) mat.SetFloat("_BlendModePreserveSpecular", 0);
            if (blend >= 0 && mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", 0);
            if (blend >= 0 && mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", 0);
            // Same calls URP's own particle shader GUIs make (ParticlesLitShader / ParticlesUnlitShader).
            if (shaderName.EndsWith("/Lit")) BaseShaderGUI.SetMaterialKeywords(mat, LitGUI.SetMaterialKeywords, ParticleGUI.SetMaterialKeywords);
            else BaseShaderGUI.SetMaterialKeywords(mat, null, ParticleGUI.SetMaterialKeywords);
            EditorUtility.SetDirty(mat); return mat;
        }

        static Texture2D Texture(string path, bool srgb, int max)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var imp = (TextureImporter)AssetImporter.GetAtPath(path);
            if (imp == null) throw new InvalidOperationException("Missing FX texture " + path + " — run unity/tools/make_fx_textures.py");
            imp.textureType = TextureImporterType.Default; imp.sRGBTexture = srgb; imp.alphaSource = TextureImporterAlphaSource.FromInput; imp.alphaIsTransparency = true;
            imp.mipmapEnabled = true; imp.wrapMode = TextureWrapMode.Clamp; imp.maxTextureSize = max; imp.textureCompression = TextureImporterCompression.CompressedHQ; imp.streamingMipmaps = false;
            imp.SaveAndReimport(); return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Mesh ShardMesh()
        {
            string path = Root + "/FX_DebrisShard.asset";
            var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (!mesh) { mesh = new Mesh { name = "FX_DebrisShard" }; AssetDatabase.CreateAsset(mesh, path); }
            // An irregular bent plate: reads as a torn panel fragment when tumbling. Unit size; particles scale it.
            var v = new[] { new Vector3(-.5f, 0, -.35f), new Vector3(.45f, .05f, -.5f), new Vector3(.55f, 0, .3f), new Vector3(-.1f, .12f, .5f), new Vector3(-.55f, .02f, .2f),
                            new Vector3(-.5f, -.08f, -.35f), new Vector3(.45f, -.03f, -.5f), new Vector3(.55f, -.08f, .3f), new Vector3(-.1f, .04f, .5f), new Vector3(-.55f, -.06f, .2f) };
            var tris = new List<int> { 0, 3, 1, 1, 3, 2, 0, 4, 3, 5, 6, 8, 6, 7, 8, 5, 8, 9 };
            for (int i = 0; i < 5; i++) { int a = i, b = (i + 1) % 5, c = a + 5, d = b + 5; tris.AddRange(new[] { a, b, c, b, d, c }); }
            mesh.Clear(); mesh.vertices = v; mesh.triangles = tris.ToArray();
            mesh.uv = new Vector2[v.Length]; mesh.RecalculateNormals(); mesh.RecalculateBounds(); EditorUtility.SetDirty(mesh);
            return mesh;
        }

        static void Save(GameObject root, string path)
        {
            PrefabUtility.SaveAsPrefabAsset(root, path, out bool ok); UnityEngine.Object.DestroyImmediate(root);
            if (!ok) throw new InvalidOperationException("Could not save " + path);
        }
    }
}
