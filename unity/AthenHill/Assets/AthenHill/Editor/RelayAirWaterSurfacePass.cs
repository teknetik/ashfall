using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    /// <summary>Focused source export for the approved Relay and Air + Water surface revision.</summary>
    public static class RelayAirWaterSurfacePass
    {
        static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        static string Source=>Path.Combine(Repo,"art/relay_airwater_surfaces_20260909");
        static string Evidence=>Path.Combine(Repo,"unity/evidence/relay-airwater-surfaces/20260909");
        const string Folder="Assets/AthenHill/Art/RelayAirWaterSurfaces/20260909";
        const string RootName="Relay and Air Water surface wear";
        static string PathOf(Transform t)=>t.parent?PathOf(t.parent)+"/"+t.name:t.name;
        static float[] A(Vector3 v)=>new[]{v.x,v.y,v.z};
        static Vector3 V(float[] v)=>new Vector3(v[0],v[1],v[2]);
        static string Safe(string s)=>new string(s.Select(c=>char.IsLetterOrDigit(c)||c=='_'?c:'_').ToArray());
        sealed class Part {public string name,sourcePath,family,material;public float[][] positions,normals,uv;public int[] indices;}
        sealed class Deposit {public string name;public float[] position,size,direction;public int tile;public float opacity,depth;}
        static string Collision()=>JsonConvert.SerializeObject(UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsInactive.Include).Where(c=>c.gameObject.scene.IsValid()).OrderBy(c=>PathOf(c.transform)).Select(c=>new{path=PathOf(c.transform),id=GlobalObjectId.GetGlobalObjectIdSlow(c).ToString(),c.enabled,c.isTrigger,active=c.gameObject.activeInHierarchy,matrix=Enumerable.Range(0,16).Select(i=>c.transform.localToWorldMatrix[i]).ToArray(),boxCenter=c is BoxCollider b?A(b.center):null,boxSize=c is BoxCollider b2?A(b2.size):null,mesh=c is MeshCollider m?AssetDatabase.GetAssetPath(m.sharedMesh):null}));
        public static void ExportSources()
        {
            var scene=EditorSceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved city in Edit mode.");
            var file=Path.Combine(Source,"unity-source.json");
            if(File.Exists(file))throw new InvalidOperationException("Preserve the frozen source export.");
            var roots=new[]{"relay_works","air_water"}.Select(id=>GameObject.Find("Ward shop architecture/"+id)).ToArray();
            if(roots.Any(r=>!r))throw new InvalidOperationException("Expected active authored shops missing.");
            var rows=roots.SelectMany(root=>root.GetComponentsInChildren<MeshFilter>(false).Where(f=>f.sharedMesh&&f.GetComponent<MeshRenderer>()).Select(f=>{
                var t=f.transform;var mesh=f.sharedMesh;var renderer=f.GetComponent<MeshRenderer>();
                return new {name=f.name,path=PathOf(t),family=root.name,meshPath=AssetDatabase.GetAssetPath(mesh),positions=mesh.vertices.Select(v=>A(t.TransformPoint(v))).ToArray(),normals=mesh.normals.Select(v=>A(t.TransformDirection(v).normalized)).ToArray(),uv=mesh.uv.Select(v=>new[]{v.x,v.y}).ToArray(),uv1Count=mesh.uv2.Length,indices=mesh.triangles,bounds=new{min=A(renderer.bounds.min),max=A(renderer.bounds.max)},materials=renderer.sharedMaterials.Select(m=>new{name=m.name,path=AssetDatabase.GetAssetPath(m),shader=m.shader.name,color=A(new Vector3(m.color.r,m.color.g,m.color.b)),baseMap=AssetDatabase.GetAssetPath(m.GetTexture("_BaseMap")),normalMap=AssetDatabase.GetAssetPath(m.GetTexture("_BumpMap")),mapScale=new[]{m.GetTextureScale("_BaseMap").x,m.GetTextureScale("_BaseMap").y}}).ToArray()};
            })).ToArray();
            File.WriteAllText(file,JsonConvert.SerializeObject(rows));
            File.WriteAllText(Path.Combine(Source,"unity-placement.json"),JsonConvert.SerializeObject(roots.Select(r=>new{id=r.name,position=A(r.transform.position),rotation=A(r.transform.eulerAngles),scale=A(r.transform.localScale),front=A(r.transform.forward)}),Formatting.Indented));
            Debug.Log("Exported "+rows.Length+" saved Relay/Air + Water source meshes.");
        }
        [MenuItem("Athen Hill/Weathering/Apply Relay and Air Water surfaces")]
        public static void Apply()
        {
            var scene=EditorSceneManager.GetActiveScene();
            if(EditorApplication.isPlayingOrWillChangePlaymode||scene.path!=ImportBaseline.ScenePath||scene.isDirty)throw new InvalidOperationException("Open the saved city in Edit mode.");
            if(Directory.Exists(Folder)||GameObject.Find(RootName))throw new InvalidOperationException("Preserve installed surfaces; do not repeat installation.");
            var parts=JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Path.Combine(Source,"facade-meshes-v2.json")));
            var deposits=JsonConvert.DeserializeObject<Deposit[]>(File.ReadAllText(Path.Combine(Source,"localized-deposits.json")));
            var all=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Transform>(true)).GroupBy(PathOf).ToDictionary(g=>g.Key,g=>g.First());
            var materials=new Dictionary<string,Material>();
            foreach(var key in new[]{"Plaster","Stone","Steel"})
            {
                var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/FacadeMaterials/20260909/"+key+"/"+key+".mat");
                if(!material)throw new InvalidDataException("Missing reviewed shared surface: "+key);
                materials[key]=material;
            }
            foreach(var p in parts)
            {
                if(p.family!="relay_works"&&p.family!="air_water")throw new InvalidDataException("Unexpected shop");
                if(p.positions.Length!=p.normals.Length||p.positions.Length!=p.uv.Length||p.indices.Any(i=>i<0||i>=p.positions.Length)||!materials.ContainsKey(p.material))throw new InvalidDataException("Invalid source mesh: "+p.name);
                if(p.sourcePath!=null&&(!p.sourcePath.StartsWith("Ward shop architecture/"+p.family+"/")||!all.ContainsKey(p.sourcePath)||!all[p.sourcePath].GetComponent<MeshFilter>()))throw new InvalidDataException("Missing saved source: "+p.sourcePath);
                if(p.sourcePath!=null&&all[p.sourcePath].GetComponent<MeshFilter>().sharedMesh.uv2.Length>0)throw new InvalidDataException("Preserve existing lightmap UVs before changing topology: "+p.sourcePath);
            }
            var gameplay=DistrictCityPass.GameplaySignature();var collision=Collision();
            Directory.CreateDirectory(Folder+"/Meshes");AssetDatabase.Refresh();
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
            var root=new GameObject(RootName);var changes=new List<object>();int index=0,oldTriangles=0;
            foreach(var p in parts)
            {
                Transform t=p.sourcePath!=null?all[p.sourcePath]:null;
                if(!t)
                {
                    var group=root.transform.Find(p.family);if(!group){group=new GameObject(p.family).transform;group.SetParent(root.transform,false);}
                    t=new GameObject(p.name).transform;t.SetParent(group,false);
                    t.position=p.positions.Select(V).Aggregate(Vector3.zero,(a,b)=>a+b)/p.positions.Length;
                    t.gameObject.AddComponent<MeshFilter>();t.gameObject.AddComponent<MeshRenderer>();
                }
                var filter=t.GetComponent<MeshFilter>();var renderer=t.GetComponent<MeshRenderer>();
                var originalMesh=AssetDatabase.GetAssetPath(filter.sharedMesh);var originalMaterials=renderer.sharedMaterials.Select(AssetDatabase.GetAssetPath).ToArray();
                if(filter.sharedMesh)oldTriangles+=filter.sharedMesh.triangles.Length/3;
                var mesh=new Mesh{name=p.name+" aged surface",indexFormat=IndexFormat.UInt32};
                mesh.vertices=p.positions.Select(v=>t.InverseTransformPoint(V(v))).ToArray();mesh.normals=p.normals.Select(v=>t.InverseTransformDirection(V(v)).normalized).ToArray();mesh.uv=p.uv.Select(v=>new Vector2(v[0],v[1])).ToArray();mesh.triangles=p.indices;mesh.RecalculateTangents();mesh.RecalculateBounds();
                var path=Folder+"/Meshes/"+(index++).ToString("D3")+"_"+Safe(p.name)+".asset";AssetDatabase.CreateAsset(mesh,path);
                filter.sharedMesh=mesh;renderer.sharedMaterials=new[]{materials[p.material]};EditorUtility.SetDirty(filter);EditorUtility.SetDirty(renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(filter);PrefabUtility.RecordPrefabInstancePropertyModifications(renderer);
                changes.Add(new{p.sourcePath,instancePath=PathOf(t),p.family,p.material,originalMesh,originalMaterials,newMesh=path});
            }
            var depositMaterial=AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Art/Weathering/Sand grime scuffs and runoff.mat");
            if(!depositMaterial)throw new InvalidDataException("Expected installed runoff atlas");
            var groupDeposits=new GameObject("Localized service and drainage deposits").transform;groupDeposits.SetParent(root.transform,false);
            foreach(var p in deposits)
            {
                var go=new GameObject(p.name);go.transform.SetParent(groupDeposits,false);go.transform.position=V(p.position);var dir=V(p.direction);go.transform.rotation=Quaternion.LookRotation(dir,Mathf.Abs(dir.y)>.9f?Vector3.forward:Vector3.up);
                var d=go.AddComponent<DecalProjector>();d.material=depositMaterial;d.size=new Vector3(p.size[0],p.size[1],p.depth);d.pivot=Vector3.zero;d.fadeFactor=p.opacity;d.drawDistance=65;d.fadeScale=.78f;d.startAngleFade=60;d.endAngleFade=80;d.uvScale=new Vector2(.49f,.49f);d.uvBias=new Vector2(p.tile%2*.5f+.005f,p.tile<2?.505f:.005f);
            }
            PrefabUtility.SaveAsPrefabAssetAndConnect(root,Folder+"/SurfaceWear.prefab",InteractionMode.AutomatedAction);
            chunks.sourceRoots=chunks.sourceRoots.Concat(new[]{root.transform}).ToArray();EditorUtility.SetDirty(chunks);
            if(gameplay!=DistrictCityPass.GameplaySignature()||collision!=Collision())throw new InvalidOperationException("Unexpected gameplay or collision change");
            AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);EditorSceneManager.SaveScene(scene);
            File.WriteAllText(Path.Combine(Evidence,"installation.json"),JsonConvert.SerializeObject(new{utc=DateTime.UtcNow,changes,replacements=parts.Count(p=>p.sourcePath!=null),additions=parts.Count(p=>p.sourcePath==null),decals=deposits.Length,triangles=parts.Sum(p=>p.indices.Length/3),oldTriangles,netTriangleChange=parts.Sum(p=>p.indices.Length/3)-oldTriangles,gameplayPreserved=true,collidersPreserved=true,newTextureBytes=0,source="Live Blender MCP: relay-airwater-surfaces-v2.blend",status="Native review pending"},Formatting.Indented));
        }
    }
}
