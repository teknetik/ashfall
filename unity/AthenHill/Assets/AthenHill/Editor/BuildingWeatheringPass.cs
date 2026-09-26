using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace AthenHill.Editor
{
    /// <summary>Explicit, recoverable import of two Blender-authored facade weathering sets.</summary>
    public static class BuildingWeatheringPass
    {
        const string Folder="Assets/AthenHill/Art/BuildingWeathering/20260909";
        const string RootName="Field Supply and Finery weathering";
        static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        static string Source=>Path.Combine(Repo,"art/building_weathering_20260909");
        static string Evidence=>Path.Combine(Repo,"unity/evidence/building-weathering/20260909");
        [UnityEditor.Callbacks.PostProcessBuild(100)]
        public static void CopyFontNotice(BuildTarget target,string playerPath)
        {
            File.Copy(Path.Combine(Source,"DejaVu-LICENSE.txt"),Path.Combine(Path.GetDirectoryName(playerPath),"WEATHERING-FONT-LICENSE.txt"),true);
        }
        sealed class Part {public string name,family,sourcePath,material;public float[][] positions,normals,uv;public int[] indices;public bool castsShadow;}
        sealed class Decal {public string name;public float[] position,size,direction;public int tile;public float opacity,depth;}
        static Vector3 V(float[] p)=>new Vector3(p[0],p[1],p[2]);
        static float[] A(Vector3 p)=>new[]{p.x,p.y,p.z};
        static string Safe(string s)=>new string(s.Select(c=>char.IsLetterOrDigit(c)||c=='_'||c=='-'?c:'_').ToArray());
        static string PathOf(Transform t)=>t.parent?PathOf(t.parent)+"/"+t.name:t.name;
        static string Collision()=>JsonConvert.SerializeObject(UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Where(c=>c.gameObject.scene.IsValid()).OrderBy(c=>PathOf(c.transform)).Select(c=>new{path=PathOf(c.transform),id=GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(),c.enabled,c.isTrigger,matrix=Enumerable.Range(0,16).Select(i=>c.transform.localToWorldMatrix[i]).ToArray(),boxCenter=A(c is BoxCollider b?b.center:Vector3.zero),boxSize=A(c is BoxCollider b2?b2.size:Vector3.zero),mesh=c is MeshCollider m?AssetDatabase.GetAssetPath(m.sharedMesh):null}));
        static Material Load(string path){var m=AssetDatabase.LoadAssetAtPath<Material>(path);if(!m)throw new InvalidDataException("Material absent: "+path);return m;}
        static Material Clone(string name,string path,Color tint)
        {
            var m=new Material(Load(path)){name="Weathering "+name,enableInstancing=true};m.SetColor("_BaseColor",tint);AssetDatabase.CreateAsset(m,Folder+"/Materials/"+name+".mat");return m;
        }
        static Dictionary<string,Material> Materials()
        {
            const string shared=WardBuildingMaterials.Folder;
            const string courtyard="Assets/AthenHill/Art/Courtyard/Materials/";
            var m=new Dictionary<string,Material>();
            m["ExposedStone"]=Clone("ExposedStone",shared+"/WardStone/WardStone.mat",new Color(.86f,.79f,.67f));
            m["OxideRust"]=Clone("OxideRust",shared+"/WardWornSteel/WardWornSteel.mat",new Color(.76f,.54f,.35f));
            m["CrackDust"]=Clone("CrackDust",shared+"/WardStone/WardStone.mat",new Color(.24f,.20f,.15f));
            m["DryBlood"]=Clone("DryBlood",shared+"/WardPlaster/WardPlaster.mat",new Color(.20f,.045f,.029f));
            m["DryBlood"].SetFloat("_Smoothness",.02f);
            foreach(var key in new[]{"Karaveen","Paper","Warden"})m[key]=Clone(key,courtyard+key+".mat",Color.white);
            m["Graffiti"]=Clone("Graffiti",courtyard+"Graffiti.mat",new Color(.75f,.68f,.50f));
            m["GraffitiSolid"]=Clone("GraffitiSolid",shared+"/WardPlaster/WardPlaster.mat",new Color(.84f,.78f,.60f));
            m["GraffitiSolid"].SetFloat("_Cull",0);
            foreach(var key in new[]{"Karaveen","Paper","Warden","Graffiti","CrackDust","DryBlood"})m[key].SetFloat("_Cull",0);
            return m;
        }
        static Mesh CreateMesh(Part p,Transform original,Vector3 pivot)
        {
            var m=new Mesh{name=p.name,indexFormat=IndexFormat.UInt32};
            m.vertices=p.positions.Select(v=>original?original.InverseTransformPoint(V(v)):V(v)-pivot).ToArray();
            m.normals=p.normals.Select(v=>original?original.InverseTransformDirection(V(v)).normalized:V(v)).ToArray();
            m.uv=p.uv.Select(v=>new Vector2(v[0],v[1])).ToArray();m.triangles=p.indices;m.RecalculateTangents();m.RecalculateBounds();return m;
        }
        [MenuItem("Athen Hill/Weathering/Update authored mesh revision")]
        public static void UpdateMeshes()
        {
            var scene=EditorSceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved city in Edit mode first.");
            var parts=JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source,"weathering-meshes-v3.json")));
            var all=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g=>g.Key,g=>g.First());
            var updates=new List<(Mesh target,Mesh source)>();
            for(int i=0;i<parts.Length;i++)
            {
                var p=parts[i];var path=Folder+"/Meshes/"+i.ToString("D3")+"_"+Safe(p.name)+".asset";
                var target=AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if(!target)throw new InvalidDataException("Revision does not match installed mesh: "+path);
                Transform original=p.sourcePath!=null?all[p.sourcePath]:null;
                var instance=all.Values.FirstOrDefault(t=>{var filter=t.GetComponent<MeshFilter>();return filter&&filter.sharedMesh==target;});
                if(!instance)throw new InvalidDataException("Installed instance absent: "+p.name);
                updates.Add((target,CreateMesh(p,original,instance.position)));
            }
            var gameplay=DistrictCityPass.GameplaySignature();var collision=Collision();
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
            foreach(var pair in updates){EditorUtility.CopySerialized(pair.source,pair.target);EditorUtility.SetDirty(pair.target);UnityEngine.Object.DestroyImmediate(pair.source);}
            AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.SaveScene(scene);
            if(gameplay!=DistrictCityPass.GameplaySignature()||collision!=Collision())throw new InvalidOperationException("Gameplay or collision changed unexpectedly.");
            File.WriteAllText(Path.Combine(Evidence,"mesh-revision-v3.json"),JsonConvert.SerializeObject(new{utc=DateTime.UtcNow,meshes=parts.Length,triangles=parts.Sum(p=>p.indices.Length/3),source="Live Blender MCP: weathering-v3.blend",correction="Retain triangle winding for the orientation preserving axis conversion at both import and export.",gameplayPreserved=true,collidersPreserved=true},Formatting.Indented));
        }
        [MenuItem("Athen Hill/Weathering/Install two Blender weathered facades")]
        public static void Install()
        {
            var scene=EditorSceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved city in Edit mode, preserving existing edits.");
            if(GameObject.Find(RootName)||Directory.Exists(Folder))throw new InvalidOperationException("Weathering assets already exist. Preserve and edit them; do not reinstall.");
            var parts=JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source,"weathering-meshes-v3.json")));
            var decals=JsonConvert.DeserializeObject<Decal[]>(File.ReadAllText(Path.Combine(Source,"weathering-decals-v1.json")));
            var all=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g=>g.Key,g=>g.First());
            foreach(var p in parts)
            {
                if(p.family!="field_supply"&&p.family!="finery")throw new InvalidDataException("Unexpected family");
                if(p.positions.Length!=p.normals.Length||p.positions.Length!=p.uv.Length||p.indices.Any(i=>i<0||i>=p.positions.Length))throw new InvalidDataException("Invalid buffers: "+p.name);
                if(p.sourcePath!=null&&(!all.ContainsKey(p.sourcePath)||!all[p.sourcePath].GetComponent<MeshFilter>()))throw new InvalidDataException("Missing original: "+p.sourcePath);
            }
            var gameplay=DistrictCityPass.GameplaySignature();var collision=Collision();
            Directory.CreateDirectory(Evidence);Directory.CreateDirectory(Folder+"/Meshes");Directory.CreateDirectory(Folder+"/Materials");AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var materials=Materials();var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
            var changes=new List<object>();var root=new GameObject(RootName);int i=0;
            foreach(var p in parts)
            {
                Transform original=p.sourcePath!=null?all[p.sourcePath]:null;
                Vector3 pivot=Vector3.zero;if(!original){foreach(var v in p.positions)pivot+=V(v);pivot/=p.positions.Length;}
                var mesh=CreateMesh(p,original,pivot);string path=Folder+"/Meshes/"+(i++).ToString("D3")+"_"+Safe(p.name)+".asset";AssetDatabase.CreateAsset(mesh,path);
                if(original)
                {
                    var f=original.GetComponent<MeshFilter>();changes.Add(new{p.sourcePath,originalMesh=AssetDatabase.GetAssetPath(f.sharedMesh),weatheredMesh=path});f.sharedMesh=mesh;EditorUtility.SetDirty(f);PrefabUtility.RecordPrefabInstancePropertyModifications(f);
                }
                else
                {
                    var group=root.transform.Find(p.family);if(!group){group=new GameObject(p.family).transform;group.SetParent(root.transform,false);}
                    var go=new GameObject(p.name);go.transform.SetParent(group,false);go.transform.position=pivot;go.AddComponent<MeshFilter>().sharedMesh=mesh;
                    var r=go.AddComponent<MeshRenderer>();r.sharedMaterial=materials.ContainsKey(p.material)?materials[p.material]:Load(p.material);r.shadowCastingMode=p.castsShadow?ShadowCastingMode.On:ShadowCastingMode.Off;r.receiveShadows=true;
                }
            }
            var dg=new GameObject("Localized drainage and foundation deposits").transform;dg.SetParent(root.transform,false);
            var deposit=Load("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            foreach(var p in decals)
            {
                var go=new GameObject(p.name);go.transform.SetParent(dg,false);go.transform.position=V(p.position);var dir=V(p.direction);go.transform.rotation=Quaternion.LookRotation(dir,Mathf.Abs(dir.y)>.9f?Vector3.forward:Vector3.up);
                var d=go.AddComponent<DecalProjector>();d.material=deposit;d.size=new Vector3(p.size[0],p.size[1],p.depth);d.pivot=Vector3.zero;d.fadeFactor=p.opacity;d.drawDistance=65;d.fadeScale=.78f;d.startAngleFade=60;d.endAngleFade=80;
                d.uvScale=new Vector2(.49f,.49f);d.uvBias=new Vector2(p.tile%2*.5f+.005f,p.tile<2?.505f:.005f);
            }
            PrefabUtility.SaveAsPrefabAssetAndConnect(root,Folder+"/BuildingWeathering.prefab",InteractionMode.AutomatedAction);
            chunks.sourceRoots=chunks.sourceRoots.Concat(new[]{root.transform}).ToArray();EditorUtility.SetDirty(chunks);
            if(gameplay!=DistrictCityPass.GameplaySignature()||collision!=Collision())throw new InvalidOperationException("Gameplay or collision changed unexpectedly.");
            File.WriteAllText(Path.Combine(Evidence,"installation.json"),JsonConvert.SerializeObject(new{utc=DateTime.UtcNow,changes,additions=parts.Count(p=>p.sourcePath==null),triangles=parts.Sum(p=>p.indices.Length/3),decals=decals.Length,gameplayPreserved=true,collidersPreserved=true,source="Live Blender MCP, weathering-v3.blend",status="Native review pending"},Formatting.Indented));
            AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.SaveScene(scene);
        }
    }
}
