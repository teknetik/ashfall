using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// <summary>Saved Blender landscape and terrain materials. No runtime generation.</summary>
    public static class TerrainPass
    {
        const string Root="Assets/AthenHill/Art/Terrain/";
        const string Materials="Assets/AthenHill/Materials/Terrain/";
        const string Evidence="../evidence/terrain/20260908/";
        static string Gameplay() => JsonConvert.SerializeObject(new {
            colliders=UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include,FindObjectsSortMode.InstanceID)
                .Select(x=>new {x.name,position=x.transform.position.ToString("R"),bounds=x.bounds.ToString("R"),x.enabled}).ToArray(),
            npcs=UnityEngine.Object.FindObjectsByType<NpcAgent>(FindObjectsSortMode.InstanceID)
                .Select(x=>new{x.name,position=x.transform.position.ToString("R")}).ToArray(),
            walkers=UnityEngine.Object.FindObjectsByType<AmbientWalker>(FindObjectsSortMode.InstanceID)
                .Select(x=>new{x.name,data=EditorJsonUtility.ToJson(x)}).ToArray()
        });

        [MenuItem("Athen Hill/Terrain/Apply desert landscape")]
        public static void Apply()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Exit Play mode first.");
            var scene=EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
            string before=Gameplay();
            Directory.CreateDirectory(Materials);Directory.CreateDirectory(Evidence);
            AssetDatabase.Refresh();
            var importer=(TextureImporter)AssetImporter.GetAtPath(Root+"Geology.png");
            importer.sRGBTexture=false;importer.mipmapEnabled=true;importer.streamingMipmaps=true;
            importer.wrapMode=TextureWrapMode.Repeat;importer.anisoLevel=8;importer.maxTextureSize=1024;
            importer.textureCompression=TextureImporterCompression.CompressedHQ;importer.SaveAndReimport();
            var albedoImporter=(TextureImporter)AssetImporter.GetAtPath(Root+"SandstoneAlbedo.png");
            albedoImporter.sRGBTexture=true;albedoImporter.mipmapEnabled=true;albedoImporter.streamingMipmaps=true;
            albedoImporter.wrapMode=TextureWrapMode.Repeat;albedoImporter.anisoLevel=8;albedoImporter.maxTextureSize=2048;
            albedoImporter.textureCompression=TextureImporterCompression.CompressedHQ;albedoImporter.SaveAndReimport();
            var soilImporter=(TextureImporter)AssetImporter.GetAtPath(Root+"HillSoilAlbedo.png");
            soilImporter.sRGBTexture=true;soilImporter.mipmapEnabled=true;soilImporter.streamingMipmaps=true;
            soilImporter.wrapMode=TextureWrapMode.Repeat;soilImporter.anisoLevel=8;soilImporter.maxTextureSize=2048;
            soilImporter.textureCompression=TextureImporterCompression.CompressedHQ;soilImporter.SaveAndReimport();
            var shader=Shader.Find("Athen Hill/Desert Terrain");
            if(!shader||ShaderUtil.ShaderHasError(shader))throw new InvalidOperationException("Terrain shader has errors.");
            var material=AssetDatabase.LoadAssetAtPath<Material>(Materials+"SandstoneBasin.mat");
            if(!material){material=new Material(shader);AssetDatabase.CreateAsset(material,Materials+"SandstoneBasin.mat");}
            material.shader=shader;material.SetTexture("_Geology",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"Geology.png"));
            material.SetTexture("_RockTex",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"SandstoneAlbedo.png"));
            material.SetFloat("_DetailScale",.073f);material.SetFloat("_Relief",.14f);material.SetFloat("_HazeDensity",.0048f);
            EditorUtility.SetDirty(material);
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            var retired=GameObject.Find("AuthoredWorld").GetComponentsInChildren<MeshRenderer>(true)
                .Where(x=>x.name.StartsWith("ENV_sandstone_mesa_")||x.name.StartsWith("ENV_mesa_buttress_")).ToArray();
            foreach(var r in retired)r.enabled=false;
            var old=GameObject.Find("Desert Landscape");
            if(old)UnityEngine.Object.DestroyImmediate(old);
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"DesertBasin.glb");
            if(!model)throw new InvalidOperationException("Blender terrain GLB has not imported.");
            var terrain=(GameObject)PrefabUtility.InstantiatePrefab(model);terrain.name="Desert Landscape";
            foreach(var r in terrain.GetComponentsInChildren<MeshRenderer>(true))
            {
                r.sharedMaterial=material;r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=false;
                r.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;
            }
            foreach(var c in UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None))c.farClipPlane=650;
            var sky=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/DesertSky.mat");
            sky.SetFloat("_RidgeStrength",0);EditorUtility.SetDirty(sky);
            var ground=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_grass.mat");
            ground.SetTexture("_Geology",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"Geology.png"));ground.SetTexture("_RockTex",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"SandstoneAlbedo.png"));ground.SetTexture("_GroundTex",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"HillSoilAlbedo.png"));EditorUtility.SetDirty(ground);
            AddHillStones(ground);
            StaticRenderChunksEditor.Rebuild(chunks);
            string after=Gameplay();
            if(before!=after)throw new InvalidOperationException("Terrain pass changed gameplay roots or collision.");
            AtmospherePass.BakeSkyReflection();
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence+"authoring.json",JsonConvert.SerializeObject(new {
                gameplayPreserved=before==after,retiredMeshCount=retired.Length,
                terrainTriangles=terrain.GetComponentsInChildren<MeshFilter>().Sum(x=>x.sharedMesh.triangles.Length/3),
                terrainRenderers=terrain.GetComponentsInChildren<MeshRenderer>().Length,
                bounds=terrain.GetComponentsInChildren<MeshRenderer>().Select(x=>new{x.name,bounds=x.bounds.ToString("R")}),
                gameplay=JsonConvert.DeserializeObject(before)
            },Formatting.Indented));
            Capture();
        }
        static void AddHillStones(Material ground)
        {
            var old=GameObject.Find("Hill weathered stones");if(old)UnityEngine.Object.DestroyImmediate(old);
            var model=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"HillStones.glb");
            if(!model)throw new InvalidOperationException("Hill stone GLB has not imported.");
            var stones=(GameObject)PrefabUtility.InstantiatePrefab(model);stones.name="Hill weathered stones";
            foreach(var r in stones.GetComponentsInChildren<MeshRenderer>())
            {r.sharedMaterial=ground;r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=true;}
        }
        public static void Capture()
        {
            Directory.CreateDirectory(Evidence+"editor");
            PortDiagnostics.Capture("cam_hill");
            foreach(var name in new[]{"cam_hill","cam_avenue","cam_gate","cam_grid","cam_whompah","cam_hero"})
            {PortDiagnostics.Capture(name);File.Copy("Captures/Fixed/"+name+".png",Evidence+"editor/"+name+".png",true);}
        }
        public static void ApplyAndBuild()
        {
            Apply();LinuxBuild.Development();File.Copy("Captures/linux-build.json",Evidence+"development-build.json",true);
            LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"release-build.json",true);
        }
        public static void RefreshAndBuild()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
            foreach(var name in new[]{"Athen Hill/Desert Terrain","Athen Hill/Hill Ground"})
            {
                var shader=Shader.Find(name);
                if(!shader||ShaderUtil.ShaderHasError(shader))throw new InvalidOperationException("Invalid shader: "+name);
            }
            AtmospherePass.BakeSkyReflection();
            EditorSceneManager.SaveOpenScenes();AssetDatabase.SaveAssets();Capture();
            LinuxBuild.Development();File.Copy("Captures/linux-build.json",Evidence+"development-build.json",true);
            LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"release-build.json",true);
        }
        public static void Release()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath,OpenSceneMode.Single);
            LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"release-build.json",true);
        }
    }
}
