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
    // Focused source-content import. Never constructs the district at runtime.
    public static class CourtyardPass
    {
        const string Root="Assets/AthenHill/Art/Courtyard";
        const string Evidence="../evidence/courtyard/20260908";
        const string Source="../../art/courtyard_20260908/mesh-data.json";
        class Part
        {
            public string name,group;
            public float[][] positions,normals,uv;
            public int[] indices,triangleMaterials;
            public string[] materials;
        }
        static T Save<T>(T asset,string path) where T:UnityEngine.Object
        {
            var existing=AssetDatabase.LoadAssetAtPath<T>(path);
            if(existing){EditorUtility.CopySerialized(asset,existing);UnityEngine.Object.DestroyImmediate(asset);EditorUtility.SetDirty(existing);return existing;}
            AssetDatabase.CreateAsset(asset,path);return asset;
        }
        static string Safe(string name)=>string.Concat(name.Select(c=>char.IsLetterOrDigit(c)||c=='-'||c=='_'?c:'_'));
        static Vector3 V(float[] v)=>new Vector3(v[0],v[1],v[2]);
        static float[] A(Vector3 p)=>new[]{p.x,p.y,p.z};
        static Texture2D Texture(string file)=>AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"/Textures/"+file);

        [MenuItem("Athen Hill/Courtyard/Install authored courtyard")]
        public static void Install()
        {
            if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
            var scene=EditorSceneManager.GetActiveScene();
            if(scene.path!=ImportBaseline.ScenePath || scene.isDirty)throw new Exception("Save and open the authored city before installing.");
            if(GameObject.Find("Courtyard reference pass"))throw new Exception("Already installed. Edit its saved prefab instance; use Refresh geometry for authored revisions.");
            if(!File.Exists(Evidence+"/before-scene.unity"))throw new Exception("Capture the saved native baseline first.");
            string gameplay=DistrictCityPass.GameplaySignature();
            var oldColliders=UnityEngine.Object.FindObjectsByType<Collider>().ToDictionary(c=>c,c=>new{p=c.transform.position,r=c.transform.rotation,s=c.transform.lossyScale,c.enabled,c.isTrigger});
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();chunks.ShowSources(true);
            var parent=new GameObject("Courtyard reference pass");
            Import(parent.transform);
            var names=new HashSet<string>{"ENV_mission_plinth","BLD_shop_w_01_first_step","Plaza inset north"};
            foreach(var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include))
            {
                if(names.Contains(r.name)||r.name.StartsWith("ENV_hill_stair_north_")||r.name=="Dusty joint weeds"||r.name=="Leak corner weeds")
                {r.enabled=false;EditorUtility.SetDirty(r);if(PrefabUtility.IsPartOfPrefabInstance(r))PrefabUtility.RecordPrefabInstancePropertyModifications(r);}
            }
            chunks.sourceRoots=chunks.sourceRoots.Concat(new[]{parent.transform}).ToArray();
            AddCameras();Lighting();
            PrefabUtility.SaveAsPrefabAssetAndConnect(parent,Root+"/Courtyard.prefab",InteractionMode.AutomatedAction);
            AssetDatabase.SaveAssets();
            StaticRenderChunksEditor.Rebuild(chunks);
            if(gameplay!=DistrictCityPass.GameplaySignature())throw new Exception("Existing gameplay roots changed.");
            foreach(var pair in oldColliders)
            {
                var c=pair.Key;var b=pair.Value;
                if(!c||c.transform.position!=b.p||c.transform.rotation!=b.r||c.transform.lossyScale!=b.s||c.enabled!=b.enabled||c.isTrigger!=b.isTrigger)
                    throw new Exception("Existing collision changed.");
            }
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence+"/installation.json",JsonConvert.SerializeObject(new{gameplayPreserved=true,existingCollidersPreserved=true,parts=parent.GetComponentsInChildren<MeshRenderer>().Length,source=Source,reference="refs/courtyard_20260908/accepted-target.png"},Formatting.Indented));
            Capture();
        }

        [MenuItem("Athen Hill/Courtyard/Refresh authored geometry")]
        public static void RefreshGeometry()
        {
            if(EditorApplication.isPlaying)throw new Exception("Exit Play first.");
            var root=GameObject.Find("Courtyard reference pass");if(!root)throw new Exception("Install first.");
            var c=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();c.ShowSources(true);
            // Regenerates only this authored family's mesh assets, preserving saved transforms.
            Import(root.transform,true);
            PrefabUtility.SaveAsPrefabAssetAndConnect(root,Root+"/Courtyard.prefab",InteractionMode.AutomatedAction);
            // The guard hashes source files, so flush imported meshes before fingerprinting them.
            AssetDatabase.SaveAssets();
            StaticRenderChunksEditor.Rebuild(c);AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();Capture();
        }
        static void Import(Transform parent,bool refresh=false)
        {
            foreach(var f in new[]{"Meshes","Materials","Textures"})Directory.CreateDirectory(Root+"/"+f);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            SetupTextures();var mats=Materials();
            var parts=JsonConvert.DeserializeObject<Part[]>(File.ReadAllText(Source));
            string pivotPath=Root+"/AuthoredPivots.json";
            var previous=File.Exists(pivotPath)?JsonConvert.DeserializeObject<Dictionary<string,float[]>>(File.ReadAllText(pivotPath)):new Dictionary<string,float[]>();
            var next=new Dictionary<string,float[]>();
            var groups=new Dictionary<string,Transform>();
            foreach(var p in parts)
            {
                if(!groups.ContainsKey(p.group))
                {var found=parent.Find(p.group);if(!found){found=new GameObject(p.group).transform;found.SetParent(parent,false);}groups[p.group]=found;}
                var pos=p.positions.Select(V).ToArray();var bounds=new Bounds(pos[0],Vector3.zero);foreach(var v in pos)bounds.Encapsulate(v);var pivot=bounds.center;
                string key=p.group+"/"+p.name;next[key]=A(pivot);
                var m=new Mesh{name=p.name,indexFormat=IndexFormat.UInt32};m.vertices=pos.Select(v=>v-pivot).ToArray();m.normals=p.normals.Select(V).ToArray();m.uv=p.uv.Select(v=>new Vector2(v[0],v[1])).ToArray();m.subMeshCount=p.materials.Length;
                if(p.group=="Vegetation"||p.group=="Canopy")
                    m.colors=pos.Select(v=>new Color(1,1,1,p.group=="Vegetation"?Mathf.InverseLerp(bounds.min.y,bounds.max.y,v.y):Mathf.InverseLerp(16.82f,12.24f,v.x))).ToArray();
                for(int sub=0;sub<p.materials.Length;sub++)
                {var ii=new List<int>();for(int t=0;t<p.triangleMaterials.Length;t++)if(p.triangleMaterials[t]==sub){ii.Add(p.indices[t*3]);ii.Add(p.indices[t*3+1]);ii.Add(p.indices[t*3+2]);}m.SetTriangles(ii,sub);}
                m.RecalculateBounds();m.RecalculateTangents();
                m=Save(m,Root+"/Meshes/"+Safe(p.name)+".asset");
                var existing=groups[p.group].Find(p.name);var go=existing?existing.gameObject:new GameObject(p.name);
                if(!existing){go.transform.SetParent(groups[p.group],false);go.transform.position=pivot;}
                else if(!refresh)go.transform.position=pivot;
                else if(previous.ContainsKey(key))go.transform.position+=pivot-V(previous[key]);
                go.SetActive(true);
                var mf=go.GetComponent<MeshFilter>();if(!mf)mf=go.AddComponent<MeshFilter>();mf.sharedMesh=m;
                var mr=go.GetComponent<MeshRenderer>();if(!mr)mr=go.AddComponent<MeshRenderer>();mr.sharedMaterials=p.materials.Select(n=>mats[n]).ToArray();mr.receiveShadows=true;
                if(p.name=="Salvaged drum planter")
                {var collision=go.GetComponent<CapsuleCollider>();if(!collision)collision=go.AddComponent<CapsuleCollider>();collision.direction=1;collision.height=.79f;collision.radius=.315f;collision.center=Vector3.zero;}
                mr.shadowCastingMode=p.group=="Vegetation"||p.group=="Canopy"||p.group=="Wall graphics"?ShadowCastingMode.TwoSided:ShadowCastingMode.On;
                GameObjectUtility.SetStaticEditorFlags(go,StaticEditorFlags.BatchingStatic|StaticEditorFlags.ReflectionProbeStatic);
            }
            foreach(var key in previous.Keys)if(!next.ContainsKey(key)){var retired=parent.Find(key);if(retired)retired.gameObject.SetActive(false);}
            File.WriteAllText(pivotPath,JsonConvert.SerializeObject(next,Formatting.Indented));
            File.WriteAllText(Evidence+"/geometry-import.json",JsonConvert.SerializeObject(new{parts=parts.Length,triangles=parts.Sum(p=>p.indices.Length/3),vertices=parts.Sum(p=>p.positions.Length),sourceRetained=true,uv="UV0, authored metre scale; separate tangent normals"},Formatting.Indented));
        }

        static void SetupTextures()
        {
            string mask=Root+"/Textures/FactoryGraffitiMask.png",paint=Root+"/Textures/FactoryGraffiti.png";
            if(File.Exists(mask)&&!File.Exists(paint))
            {
                // The authored monochrome mask is packed into alpha for URP's cutout material.
                var src=new Texture2D(2,2,TextureFormat.RGBA32,false,true);src.LoadImage(File.ReadAllBytes(mask));
                var pixels=src.GetPixels32();for(int j=0;j<pixels.Length;j++)pixels[j]=new Color32(255,255,255,pixels[j].r);
                src.SetPixels32(pixels);src.Apply();File.WriteAllBytes(paint,src.EncodeToPNG());UnityEngine.Object.DestroyImmediate(src);AssetDatabase.ImportAsset(paint,ImportAssetOptions.ForceSynchronousImport);
            }
            foreach(var path in Directory.GetFiles(Root+"/Textures"))
            {
                if(path.EndsWith(".meta"))continue;var i=AssetImporter.GetAtPath(path) as TextureImporter;if(!i)continue;
                bool normal=path.Contains("nor_gl");i.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=!normal&&!path.Contains("rough")&&!path.Contains("Smoothness");
                i.mipmapEnabled=true;i.streamingMipmaps=true;i.wrapMode=path.Contains("Poster")||path.Contains("Banner")?TextureWrapMode.Clamp:TextureWrapMode.Repeat;i.filterMode=FilterMode.Trilinear;i.anisoLevel=16;i.maxTextureSize=4096;i.textureCompression=TextureImporterCompression.CompressedHQ;i.SaveAndReimport();
            }
            foreach(var name in new[]{"sandstone_cracks","rock_boulder_dry","sand_01","sand_03","rusty_painted_metal"})
            {
                string path=Root+"/Textures/"+name+"_Smoothness.png";if(File.Exists(path))continue;
                var src=new Texture2D(2,2,TextureFormat.RGBA32,false,true);src.LoadImage(File.ReadAllBytes(Root+"/Textures/"+name+"_rough_2k.jpg"));
                var pixels=src.GetPixels32();for(int j=0;j<pixels.Length;j++)pixels[j]=new Color32(0,0,0,(byte)(255-pixels[j].r));src.SetPixels32(pixels);src.Apply();File.WriteAllBytes(path,src.EncodeToPNG());UnityEngine.Object.DestroyImmediate(src);
                AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var i=(TextureImporter)AssetImporter.GetAtPath(path);i.sRGBTexture=false;i.mipmapEnabled=true;i.streamingMipmaps=true;i.maxTextureSize=4096;i.anisoLevel=16;i.textureCompression=TextureImporterCompression.CompressedHQ;i.SaveAndReimport();
            }
        }
        static Dictionary<string,Material> Materials()
        {
            var result=new Dictionary<string,Material>();var shader=Shader.Find("Universal Render Pipeline/Lit");if(!shader)throw new Exception("URP Lit missing.");
            Action<string,Color,string,float> make=(name,color,asset,normal)=>
            {
                bool thin=name.StartsWith("Straw")||name=="Leaf"||name=="Canvas"||name=="CanvasPatch";
                var selected=thin?Shader.Find("Athen Hill/Courtyard Thin Surface"):name.StartsWith("Stone")?Shader.Find("Athen Hill/Weathered Lit"):shader;
                var m=new Material(selected){name="Courtyard "+name,enableInstancing=true};m.SetColor("_BaseColor",color);m.SetFloat("_Smoothness",.1f);m.SetFloat("_Metallic",0);
                if(asset!=null){m.SetTexture("_BaseMap",Texture(asset+"_diff_2k.jpg"));m.SetTexture("_BumpMap",Texture(asset+"_nor_gl_2k.jpg"));m.SetFloat("_BumpScale",normal);m.EnableKeyword("_NORMALMAP");m.SetTexture("_MetallicGlossMap",Texture(asset+"_Smoothness.png"));m.SetFloat("_Smoothness",.08f);m.EnableKeyword("_METALLICSPECGLOSSMAP");}
                if(name.StartsWith("Straw")||name=="Leaf"||name=="Canvas"||name=="CanvasPatch"||name=="Paper"||name=="Warden"||name=="Karaveen")m.SetFloat("_Cull",0);
                if(name=="Iron"||name=="Brass"){m.SetFloat("_Metallic",.75f);m.SetFloat("_Smoothness",.25f);}
                if(name.StartsWith("Stone")){m.SetFloat("_WearStrength",.68f);m.SetFloat("_WearScale",.45f);m.SetFloat("_BaseWear",.22f);m.SetColor("_WearTint",new Color(.64f,.59f,.49f));}
                if(thin){m.SetFloat("_Transmission",name=="Canvas"||name=="CanvasPatch"?.10f:.35f);m.SetFloat("_RootShade",name=="Canvas"||name=="CanvasPatch"?0:.24f);m.SetFloat("_WindStrength",name=="Canvas"||name=="CanvasPatch"?.018f:.035f);}
                if(name=="Canvas"){m.SetTexture("_BaseMap",Texture("CourtyardCanvas.png"));m.SetColor("_BaseColor",new Color(.86f,.82f,.78f));}
                if(name=="Karaveen"){m.SetTexture("_BaseMap",Texture("KaraveenPoster.png"));m.SetColor("_BaseColor",Color.white);}
                if(name=="Warden"){m.SetTexture("_BaseMap",Texture("WardBanner.png"));m.SetTextureScale("_BaseMap",new Vector2(1,.86f));m.SetTextureOffset("_BaseMap",new Vector2(0,.14f));m.SetColor("_BaseColor",Color.white);}
                if(name=="Graffiti"){m.SetTexture("_BaseMap",Texture("FactoryGraffiti.png"));m.SetFloat("_AlphaClip",1);m.SetFloat("_Cutoff",.36f);m.SetFloat("_Cull",0);m.EnableKeyword("_ALPHATEST_ON");m.renderQueue=2450;m.SetOverrideTag("RenderType","TransparentCutout");}
                if(name=="Paper"){m.SetTexture("_BaseMap",Texture("KaraveenPoster.png"));m.SetTextureScale("_BaseMap",new Vector2(.22f,.20f));m.SetTextureOffset("_BaseMap",new Vector2(.08f,.78f));m.SetColor("_BaseColor",new Color(.64f,.65f,.59f));}
                result[name]=Save(m,Root+"/Materials/"+name+".mat");
            };
            make("Stone0",new Color(.76f,.87f,.96f),"sandstone_cracks",.67f);make("Stone1",new Color(.83f,.93f,1f),"sandstone_cracks",.67f);make("Stone2",new Color(.74f,.84f,.92f),"sandstone_cracks",.67f);make("Stone3",new Color(.82f,.90f,.97f),"sandstone_cracks",.67f);
            make("Sand",new Color(1.45f,1.36f,1.18f),"sand_03",.6f);
            make("Drum",new Color(.95f,.95f,.9f),"rusty_painted_metal",.5f);make("Mortar",new Color(.30f,.26f,.19f),null,0);make("Iron",new Color(.16f,.13f,.10f),null,0);make("Brass",new Color(.39f,.25f,.13f),null,0);
            make("Canvas",new Color(.42f,.09f,.048f),null,0);make("CanvasPatch",new Color(.56f,.19f,.095f),null,0);make("Rope",new Color(.40f,.33f,.22f),null,0);
            make("Straw0",new Color(.66f,.51f,.28f),null,0);make("Straw1",new Color(.78f,.63f,.38f),null,0);make("Straw2",new Color(.53f,.44f,.28f),null,0);make("Leaf",new Color(.45f,.49f,.23f),null,0);
            make("Paper",Color.white,null,0);make("Karaveen",Color.white,null,0);make("Warden",Color.white,null,0);make("Graffiti",new Color(.13f,.115f,.09f),null,0);return result;
        }
        static void AddCameras()
        {
            DistrictCityPass.Camera("cam_courtyard",new Vector3(1.7f,2.7f,-7.3f),new Vector3(9.5f,1.25f,-15.3f),58);
            DistrictCityPass.Camera("cam_courtyard_ground",new Vector3(4.0f,1.65f,-9.0f),new Vector3(8,.35f,-13.2f),61);
            DistrictCityPass.Camera("cam_courtyard_writing",new Vector3(13.8f,2,-13.8f),new Vector3(17.4f,2.1f,-16),55);
            DistrictCityPass.Camera("cam_courtyard_facade",new Vector3(12.1f,1.7f,-10.8f),new Vector3(18.1f,2,-14.2f),61);
        }
        static void Lighting()
        {
            var sun=GameObject.Find("Sun").GetComponent<Light>();var fill=GameObject.Find("Sky fill").GetComponent<Light>();
            File.WriteAllText(Evidence+"/before-lighting.json",JsonConvert.SerializeObject(new{sunRotation=A(sun.transform.eulerAngles),sun.intensity,sunColor=sun.color.ToString(),fill=fill.intensity,sky=RenderSettings.ambientSkyColor.ToString(),ground=RenderSettings.ambientGroundColor.ToString()},Formatting.Indented));
            sun.transform.rotation=Quaternion.Euler(42,220.6f,0);sun.color=new Color(1,.90f,.77f);sun.intensity=1.7f;sun.shadowBias=.025f;sun.shadowNormalBias=.12f;
            fill.intensity=.19f;RenderSettings.ambientSkyColor=new Color(.34f,.42f,.52f);RenderSettings.ambientEquatorColor=new Color(.40f,.38f,.33f);RenderSettings.ambientGroundColor=new Color(.27f,.23f,.18f);
            EditorUtility.SetDirty(sun);EditorUtility.SetDirty(fill);
        }
        [MenuItem("Athen Hill/Courtyard/Capture installed courtyard")]
        public static void Capture()
        {
            Directory.CreateDirectory(Evidence+"/after-editor");ShaderUtil.allowAsyncCompilation=false;
            foreach(var name in new[]{"cam_hill","cam_avenue","cam_gate","cam_grid","cam_whompah","cam_hero","cam_terminal","cam_wear_terminal","cam_wear_steps","cam_wear_wall","cam_courtyard","cam_courtyard_ground","cam_courtyard_facade","cam_courtyard_writing"})
            {PortDiagnostics.Capture(name);PortDiagnostics.Capture(name);File.Copy("Captures/Fixed/"+name+".png",Evidence+"/after-editor/"+name+".png",true);}
        }
        [MenuItem("Athen Hill/Courtyard/Bake courtyard reflection")]
        public static void BakeReflection()
        {
            var go=GameObject.Find("Courtyard reflection");if(!go)go=new GameObject("Courtyard reflection");go.transform.position=new Vector3(9,2,-14);
            var p=go.GetComponent<ReflectionProbe>();if(!p)p=go.AddComponent<ReflectionProbe>();p.mode=ReflectionProbeMode.Baked;p.resolution=256;p.size=new Vector3(22,10,22);p.boxProjection=true;p.blendDistance=4;p.intensity=.32f;p.clearFlags=ReflectionProbeClearFlags.Skybox;
            string path=Root+"/CourtyardReflection.exr";if(!Lightmapping.BakeReflectionProbe(p,path))throw new Exception("Courtyard reflection bake failed.");AssetDatabase.ImportAsset(path);p.customBakedTexture=AssetDatabase.LoadAssetAtPath<Cubemap>(path);p.mode=ReflectionProbeMode.Custom;EditorUtility.SetDirty(p);EditorSceneManager.SaveOpenScenes();Capture();
        }
        [MenuItem("Athen Hill/Courtyard/Build Linux players")]
        public static void Build()
        {
            EditorSceneManager.OpenScene(ImportBaseline.ScenePath);LinuxBuild.Development();File.Copy("Captures/linux-build.json",Evidence+"/development-build.json",true);LinuxBuild.Release();File.Copy("Captures/linux-build.json",Evidence+"/release-build.json",true);
        }
    }
}
