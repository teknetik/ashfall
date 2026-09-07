using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    public static class ImportBaseline
    {
        public const string Art = "Assets/AthenHill/Art/Imported/";
        public const string ScenePath = "Assets/AthenHill/Scenes/AthenHill.unity";
        // glTFast reflects X. Preserve that importer convention for all source data.
        public static Vector3 Convert(float x, float y, float z) => new Vector3(-x,y,z);
        public static GameObject Import(string file, string name)
        {
            var asset=AssetDatabase.LoadAssetAtPath<GameObject>(Art+file);
            if(!asset) throw new Exception("Import not ready: "+file);
            var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);go.name=name;return go;
        }
        public static Camera Camera(string name, Vector3 p, Vector3 target, float fov=50)
        {
            var go=new GameObject(name);var c=go.AddComponent<Camera>();
            go.transform.position=p;go.transform.LookAt(target);c.fieldOfView=fov;
            c.aspect=16f/9;c.nearClipPlane=.08f;c.farClipPlane=250;c.enabled=false;
            c.backgroundColor=new Color(.48f,.60f,.7f);return c;
        }
        [MenuItem("Athen Hill/U1/Assemble import baseline")]
        public static void Assemble()
        {
            if(EditorApplication.isPlaying) throw new Exception("Exit Play before assembly.");
            if(File.Exists(ScenePath)) throw new Exception("The scene already exists. Open and edit it; assembly will not overwrite your changes.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var world=Import("world.glb","AuthoredWorld");
            var metadata=JObject.Parse(File.ReadAllText(Art+"world.glb.json"));
            var nodes=metadata["nodes"].ToDictionary(n=>(string)n["name"]);
            int count=0;
            foreach(var mf in world.GetComponentsInChildren<MeshFilter>(true))
            {
                if(!mf.name.StartsWith("COL_")) continue;
                if(!nodes.TryGetValue(mf.name,out var node)) throw new Exception("Missing collider metadata "+mf.name);
                string kind=(string)node["extras"]?["colliderKind"];
                if(kind=="box") {var col=mf.gameObject.AddComponent<BoxCollider>();col.center=mf.sharedMesh.bounds.center;col.size=mf.sharedMesh.bounds.size;}
                else if(kind=="cylinder") {var col=mf.gameObject.AddComponent<MeshCollider>();col.sharedMesh=mf.sharedMesh;col.convex=true;}
                else throw new Exception("Unknown collider kind "+kind);
                mf.GetComponent<Renderer>().enabled=false;count++;
            }
            if(count!=262) throw new Exception("Expected 262 authored colliders, got "+count);
            var ground=new GameObject("COL_Ground");var box=ground.AddComponent<BoxCollider>();box.center=new Vector3(0,-1,0);box.size=new Vector3(120,2,90);
            var player=Import("player-candidate.glb","PlayerCandidate");player.transform.position=Convert(-43,0,0);
            foreach(var r in player.GetComponentsInChildren<Renderer>()) {r.shadowCastingMode=r.name.Contains("shadow_proxy")?ShadowCastingMode.ShadowsOnly:ShadowCastingMode.Off;r.receiveShadows=true;}
            var npc=Import("npcs.glb","NpcImportAudition");npc.transform.position=Convert(-41.7f,0,-1.5f);
            var sun=new GameObject("Sun").AddComponent<Light>();sun.type=LightType.Directional;sun.transform.rotation=Quaternion.Euler(35,-35,0);sun.color=new Color(1,.87f,.69f);sun.intensity=2;sun.shadows=LightShadows.Soft;
            RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=new Color(.45f,.54f,.63f);RenderSettings.ambientEquatorColor=new Color(.55f,.46f,.34f);RenderSettings.ambientGroundColor=new Color(.24f,.21f,.18f);
            RenderSettings.fog=true;RenderSettings.fogMode=FogMode.Linear;RenderSettings.fogColor=new Color(.72f,.60f,.44f);RenderSettings.fogStartDistance=55;RenderSettings.fogEndDistance=180;
            Camera("cam_gate",Convert(-32,9,18),Convert(-48,3.4f,5));
            Camera("cam_avenue",Convert(-12,7,34),Convert(0,9,-5));
            Camera("cam_hill",Convert(23,14,27),Convert(0,9,0));
            Camera("cam_grid",Convert(-10,6,-28),Convert(0,2,-38));
            Camera("cam_whompah",Convert(13,6.5f,26),Convert(0,3,36));
            Camera("cam_hero",Convert(-5,3.4f,9),Convert(0,9,0));
            Camera("character",player.transform.position+new Vector3(-2,1.4f,3.7f),player.transform.position+Vector3.up,35);
            Camera("portrait",player.transform.position+new Vector3(-.55f,1.65f,1.5f),player.transform.position+Vector3.up*1.57f,35);
            var main=Camera("MainCamera",Convert(-38,2.4f,4),player.transform.position+Vector3.up*1.5f);main.enabled=true;main.tag="MainCamera";main.gameObject.AddComponent<AudioListener>();
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),ScenePath);
            Inspect();
        }
        [MenuItem("Athen Hill/U1/Inspect imports")]
        public static void Inspect()
        {
            var reports=new List<object>();
            foreach(var file in new[]{"world.glb","player-candidate.glb","npcs.glb","coordinate-probe.glb"})
            {
                var assets=AssetDatabase.LoadAllAssetsAtPath(Art+file);
                reports.Add(new {file,meshes=assets.OfType<Mesh>().Select(m=>new{name=m.name,vertices=m.vertexCount,triangles=(long)m.triangles.Length/3,colors=m.colors.Length,uv0=m.uv.Length,uv1=m.uv2.Length,bounds=m.bounds.ToString()}).ToArray(),materials=assets.OfType<Material>().Select(m=>new{name=m.name,shader=m.shader.name,keywords=m.shaderKeywords}).ToArray(),clips=assets.OfType<AnimationClip>().Select(c=>new{name=c.name,length=c.length,legacy=c.legacy}).ToArray()});
            }
            var probe=Import("coordinate-probe.glb","OrientationProbe");
            var markers=probe.GetComponentsInChildren<Transform>().Select(t=>new{name=t.name,position=new[]{t.position.x,t.position.y,t.position.z}}).ToArray();
            UnityEngine.Object.DestroyImmediate(probe);
            Directory.CreateDirectory("Captures");
            File.WriteAllText("Captures/import-report.json",JsonConvert.SerializeObject(new{unity=Application.unityVersion,pipeline=GraphicsSettings.currentRenderPipeline?.GetType().Name,colliders=UnityEngine.Object.FindObjectsByType<Collider>().Length,markers,assets=reports},Formatting.Indented));
            Debug.Log("Athen Hill import report saved.");
        }
    }
}
