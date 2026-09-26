using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>Explicit import of the reviewed Blender surface/material revision.</summary>
    public static class FacadeMaterialPass
    {
        const string Folder="Assets/AthenHill/Art/FacadeMaterials/20260909";
        static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        static string Source=>Path.Combine(Repo,"art/facade_materials_20260909");
        static string Evidence=>Path.Combine(Repo,"unity/evidence/facade-materials/20260909");
        sealed class Part {public string name,sourcePath,family,material;public float[][] positions,normals,uv;public int[] indices;}
        sealed class Manifest {public string[] disabledPaths;}
        static Vector3 V(float[] v)=>new Vector3(v[0],v[1],v[2]);
        static string PathOf(Transform t)=>t.parent?PathOf(t.parent)+"/"+t.name:t.name;
        static string Safe(string s)=>new string(s.Select(c=>char.IsLetterOrDigit(c)||c=='_'?c:'_').ToArray());
        static string Collision()=>JsonConvert.SerializeObject(UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Where(c=>c.gameObject.scene.IsValid()).OrderBy(c=>PathOf(c.transform)).Select(c=>new{path=PathOf(c.transform),id=GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(),c.enabled,c.isTrigger,active=c.gameObject.activeInHierarchy,matrix=Enumerable.Range(0,16).Select(i=>c.transform.localToWorldMatrix[i]).ToArray(),boxCenter=c is BoxCollider b?new[]{b.center.x,b.center.y,b.center.z}:null,boxSize=c is BoxCollider b2?new[]{b2.size.x,b2.size.y,b2.size.z}:null,mesh=c is MeshCollider m?AssetDatabase.GetAssetPath(m.sharedMesh):null}));
        static Texture2D ImportMap(string path,bool colour,bool normal)
        {
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
            var importer=(TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;
            importer.sRGBTexture=colour;importer.mipmapEnabled=true;importer.streamingMipmaps=true;
            importer.maxTextureSize=4096;importer.anisoLevel=8;importer.npotScale=TextureImporterNPOTScale.None;
            importer.textureCompression=TextureImporterCompression.CompressedHQ;importer.isReadable=false;importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static Material PrepareMaterial(string family)
        {
            string dir=Folder+"/"+family;Directory.CreateDirectory(dir);string src=Path.Combine(Source,"textures",family);
            File.Copy(Path.Combine(src,"BaseColor.png"),dir+"/BaseColor.png",false);
            File.Copy(Path.Combine(src,"Normal.png"),dir+"/Normal.png",false);
            // Retain the full source roughness/metallic bakes; URP needs smoothness in alpha.
            var rough=new Texture2D(2,2,TextureFormat.RGBA32,false,true);rough.LoadImage(File.ReadAllBytes(Path.Combine(src,"Roughness.png")));
            var metal=new Texture2D(2,2,TextureFormat.RGBA32,false,true);metal.LoadImage(File.ReadAllBytes(Path.Combine(src,"Metallic.png")));
            if(rough.width!=metal.width||rough.height!=metal.height)throw new InvalidDataException("Mismatched baked maps");
            var rr=rough.GetPixels32();var mm=metal.GetPixels32();
            for(int i=0;i<rr.Length;i++)rr[i]=new Color32(mm[i].r,0,0,(byte)(255-rr[i].r));
            var packed=new Texture2D(rough.width,rough.height,TextureFormat.RGBA32,false,true);packed.SetPixels32(rr);packed.Apply();File.WriteAllBytes(dir+"/MetalSmooth.png",packed.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(rough);UnityEngine.Object.DestroyImmediate(metal);UnityEngine.Object.DestroyImmediate(packed);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var material=new Material(Shader.Find("Universal Render Pipeline/Lit")){name="Facade "+family,enableInstancing=true};
            material.SetTexture("_BaseMap",ImportMap(dir+"/BaseColor.png",true,false));material.SetColor("_BaseColor",Color.white);
            material.SetTexture("_BumpMap",ImportMap(dir+"/Normal.png",false,true));material.SetFloat("_BumpScale",1);
            material.SetTexture("_MetallicGlossMap",ImportMap(dir+"/MetalSmooth.png",false,false));material.SetFloat("_Metallic",1);material.SetFloat("_Smoothness",1);
            material.EnableKeyword("_NORMALMAP");material.EnableKeyword("_METALLICSPECGLOSSMAP");material.SetFloat("_SmoothnessTextureChannel",0);
            AssetDatabase.CreateAsset(material,dir+"/"+family+".mat");return material;
        }
        [MenuItem("Athen Hill/Weathering/Apply refined facade materials and damage")]
        public static void Apply()
        {
            var scene=EditorSceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved city in Edit mode first.");
            if(Directory.Exists(Folder))throw new InvalidOperationException("Preserve the existing material revision; do not reinstall it.");
            var parts=JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source,"facade-meshes-v2.json")));
            var manifest=JsonConvert.DeserializeObject<Manifest>(File.ReadAllText(Path.Combine(Source,"geometry-manifest-v2.json")));
            var all=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g=>g.Key,g=>g.First());
            foreach(var part in parts)
            {
                if(part.family!="field_supply"&&part.family!="finery")throw new InvalidDataException("Unexpected facade");
                if(!all.ContainsKey(part.sourcePath)||!all[part.sourcePath].GetComponent<MeshFilter>())throw new InvalidDataException("Source absent: "+part.sourcePath);
                if(part.positions.Length!=part.normals.Length||part.positions.Length!=part.uv.Length||part.indices.Any(i=>i<0||i>=part.positions.Length))throw new InvalidDataException("Invalid mesh buffers");
            }
            foreach(var path in manifest.disabledPaths)
                if(!all.ContainsKey(path)||!path.StartsWith("Field Supply and Finery weathering/")||all[path].GetComponentsInChildren<Collider>(true).Length>0)throw new InvalidDataException("Unexpected overlay: "+path);
            var gameplay=DistrictCityPass.GameplaySignature();var collision=Collision();
            var materials=new Dictionary<string,Material>();foreach(string family in new[]{"Plaster","Stone","Steel"})materials[family]=PrepareMaterial(family);
            Directory.CreateDirectory(Folder+"/Meshes");AssetDatabase.Refresh();
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
            var changes=new List<object>();int index=0;
            foreach(var part in parts)
            {
                var t=all[part.sourcePath];var filter=t.GetComponent<MeshFilter>();var renderer=t.GetComponent<MeshRenderer>();
                var mesh=new Mesh{name=part.name+" refined",indexFormat=IndexFormat.UInt32};
                mesh.vertices=part.positions.Select(v=>t.InverseTransformPoint(V(v))).ToArray();mesh.normals=part.normals.Select(v=>t.InverseTransformDirection(V(v)).normalized).ToArray();mesh.uv=part.uv.Select(v=>new Vector2(v[0],v[1])).ToArray();mesh.triangles=part.indices;mesh.RecalculateTangents();mesh.RecalculateBounds();
                var path=Folder+"/Meshes/"+(index++).ToString("D3")+"_"+Safe(part.name)+".asset";AssetDatabase.CreateAsset(mesh,path);
                changes.Add(new{part.sourcePath,part.family,part.material,originalMesh=AssetDatabase.GetAssetPath(filter.sharedMesh),originalMaterials=renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray(),newMesh=path});
                filter.sharedMesh=mesh;renderer.sharedMaterials=new[]{materials[part.material]};EditorUtility.SetDirty(filter);EditorUtility.SetDirty(renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(filter);PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
            }
            foreach(var path in manifest.disabledPaths){var go=all[path].gameObject;go.SetActive(false);PrefabUtility.RecordPrefabInstancePropertyModifications(go);}
            if(gameplay!=DistrictCityPass.GameplaySignature()||collision!=Collision())throw new InvalidOperationException("Gameplay or collision changed unexpectedly");
            AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence,"installation.json"),JsonConvert.SerializeObject(new{utc=DateTime.UtcNow,changes,disabledOverlays=manifest.disabledPaths,parts=parts.Length,triangles=parts.Sum(p=>p.indices.Length/3),source="Live Blender MCP: facade-surfaces-v2.blend",textureSize=4096,tileMetres=4,gameplayPreserved=true,collidersPreserved=true,status="Native review pending"},Formatting.Indented));
        }
    }
}
