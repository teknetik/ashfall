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
    // Scoped one-time installer. Existing scene identifiers and interaction code remain intact.
    public static class PlatformTerminalPass
    {
        const string Folder = "Assets/AthenHill/Art/PlatformTerminals";
        const string ModelPath = Folder + "/terminal-lod0.glb";
        const string RootName = "Ward platform terminals 20260908";
        const float TargetHeight = 1.65f;
        static readonly string[] Parts = { "foot", "body", "screen_bezel", "interface", "lower_access", "vent", "vent.001", "button" };
        static readonly Vector3[] Slots = { new Vector3(5,1.5f,-4), new Vector3(-5,1.5f,-4), new Vector3(-5,1.5f,1) };

        [MenuItem("Athen Hill/Quality/Prepare platform terminal assets")]
        public static void PrepareAssets()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play before preparing terminal assets.");
            var sources=new GameObject[3];
            for(int lod=0;lod<3;lod++)
            {
                var path=Folder+"/terminal-lod"+lod+".glb";
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                sources[lod]=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if(!sources[lod])throw new Exception("Measured terminal LOD did not import: "+path);
            }
            ConfigureTexture("BaseColor.png", true, false);
            ConfigureTexture("Normal.png", false, true);
            ConfigureTexture("MetalSmooth.png", false, false);
            ConfigureTexture("save.png", true, false);
            ConfigureTexture("reclaim.png", true, false);
            ConfigureTexture("nameplate.png",true,false);
            var body=Material("Terminal PBR");
            body.SetColor("_BaseColor",Color.white); body.SetTexture("_BaseMap",Texture("BaseColor.png"));
            body.SetTexture("_BumpMap",Texture("Normal.png"));body.SetFloat("_BumpScale",1);
            body.SetTexture("_MetallicGlossMap",Texture("MetalSmooth.png"));body.SetFloat("_Metallic",1);body.SetFloat("_Smoothness",1);
            body.EnableKeyword("_NORMALMAP");body.EnableKeyword("_METALLICSPECGLOSSMAP");body.DisableKeyword("_EMISSION");
            body.SetColor("_EmissionColor",Color.black); body.enableInstancing=true;EditorUtility.SetDirty(body);
            foreach(var variant in new[]{"save","reclaim"})
            {
                var prefabPath=Folder+"/"+variant+".prefab";
                if(AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath)) throw new Exception("Terminal prefab already exists; preserve edited source and use a versioned revision: "+prefabPath);
                var template=new GameObject("Ward "+variant+" terminal (offline)");
                try
                {
                    var lods=new LOD[3];
                    for(int level=0;level<3;level++)
                    {
                        var visual=(GameObject)PrefabUtility.InstantiatePrefab(sources[level]);
                        visual.name="Terminal measured LOD"+level;visual.transform.SetParent(template.transform,false);
                        // All derivatives share the source's uniform normalization and origin; never fit LODs independently.
                        var b=BoundsOf(visual);
                        if(Mathf.Abs(b.size.y-TargetHeight)>.008f||b.size.x>.86f||b.size.z>.785f||Mathf.Abs(b.min.y)>.004f)throw new Exception("Measured derivative bounds changed unexpectedly: "+b);
                        int meshIndex=0;
                        foreach(var filter in visual.GetComponentsInChildren<MeshFilter>(true))
                        {
                            var mesh=filter.sharedMesh;
                            if(!mesh||mesh.uv.Length!=mesh.vertexCount)throw new Exception("Terminal source UV0 is missing.");
                            var path=Folder+"/Terminal LOD"+level+" mesh "+(meshIndex++)+".asset";
                            var copy=AssetDatabase.LoadAssetAtPath<Mesh>(path);
                            if(!copy)
                            {
                                copy=UnityEngine.Object.Instantiate(mesh);copy.name=mesh.name+" with tangents";
                                if(copy.tangents.Length!=copy.vertexCount)copy.RecalculateTangents();
                                if(copy.vertexCount!=mesh.vertexCount||!copy.triangles.SequenceEqual(mesh.triangles)||!copy.vertices.SequenceEqual(mesh.vertices)||!copy.uv.SequenceEqual(mesh.uv))throw new Exception("Tangent preparation changed derivative geometry or UVs.");
                                AssetDatabase.CreateAsset(copy,path);
                            }
                            filter.sharedMesh=copy;
                        }
                        var renderers=visual.GetComponentsInChildren<Renderer>(true);
                        foreach(var renderer in renderers)
                        {renderer.sharedMaterials=Enumerable.Repeat(body,renderer.GetComponent<MeshFilter>().sharedMesh.subMeshCount).ToArray();ConfigureRenderer(renderer);}
                        lods[level]=new LOD(new[]{.16f,.05f,.005f}[level],renderers){fadeTransitionWidth=.15f};
                    }
                    var lodGroup=template.AddComponent<LODGroup>();lodGroup.fadeMode=LODFadeMode.CrossFade;lodGroup.animateCrossFading=true;lodGroup.SetLODs(lods);lodGroup.RecalculateBounds();
                    AddDisplay(template.transform,variant);
                    AddNameplate(template.transform);
                    AddGasket(template.transform);
                    // Keep the tiny authored additions visible at every body LOD, and cull them with the whole terminal.
                    var bodyRenderers=lods.SelectMany(l=>l.renderers).ToArray();
                    var additions=template.GetComponentsInChildren<Renderer>(true).Where(r=>!bodyRenderers.Contains(r)).ToArray();
                    for(int level=0;level<lods.Length;level++)lods[level].renderers=lods[level].renderers.Concat(additions).ToArray();
                    lodGroup.SetLODs(lods);lodGroup.RecalculateBounds();
                    PrefabUtility.SaveAsPrefabAsset(template,prefabPath);
                }
                finally { UnityEngine.Object.DestroyImmediate(template); }
            }
            AssetDatabase.SaveAssets();
        }

        [MenuItem("Athen Hill/Quality/Install platform terminals")]
        public static void Install()
        {
            if(EditorApplication.isPlaying)throw new Exception("Exit Play before installation.");
            if(EditorSceneManager.GetActiveScene().path!=ImportBaseline.ScenePath)throw new Exception("Open the existing saved city before this scoped install.");
            if(GameObject.Find(RootName))throw new Exception("Platform terminals already installed; preserve the reviewed instances.");
            var authored=GameObject.Find("AuthoredWorld");if(!authored)throw new Exception("AuthoredWorld missing.");
            var old=new Transform[3][];var colliders=new BoxCollider[3][];
            for(int slot=0;slot<3;slot++)
            {
                string prefix="PROP_hill_market_"+slot.ToString("00")+"_";
                old[slot]=Parts.Select(part=>authored.transform.Find(prefix+part)).ToArray();
                if(old[slot].Any(part=>!part||!part.GetComponent<Renderer>()))throw new Exception("Expected exact legacy terminal parts missing for "+prefix);
                colliders[slot]=new[]{authored.transform.Find("COL_"+prefix+"body"),authored.transform.Find("COL_"+prefix+"foot")}.Select(t=>t?t.GetComponent<BoxCollider>():null).ToArray();
                if(colliders[slot].Any(c=>!c||c.isTrigger))throw new Exception("Expected existing physical colliders missing for "+prefix);
            }
            var prefabs=new[]{AssetDatabase.LoadAssetAtPath<GameObject>(Folder+"/save.prefab"),AssetDatabase.LoadAssetAtPath<GameObject>(Folder+"/reclaim.prefab")};
            if(prefabs.Any(p=>!p))throw new Exception("Prepare and inspect the terminal prefabs first.");
            var chunks=UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();if(!chunks)throw new Exception("City render chunk controller missing.");
            chunks.ShowSources(true);
            var root=new GameObject(RootName);
            var rows=new object[3];
            for(int slot=0;slot<3;slot++)
            {
                var instance=(GameObject)PrefabUtility.InstantiatePrefab(prefabs[slot==0?0:1]);
                instance.name="Platform terminal "+slot.ToString("00")+" "+(slot==0?"SAVE":"RECLAIM");
                instance.transform.SetParent(root.transform,false);instance.transform.position=Slots[slot];instance.transform.rotation=Quaternion.identity;
                foreach(var part in old[slot]){part.GetComponent<Renderer>().enabled=false;EditorUtility.SetDirty(part.GetComponent<Renderer>());}
                var b=BoundsOf(instance);
                // Existing collider object/component IDs survive. Fit the body and low footplate separately.
                FitCollider(colliders[slot][0],new Bounds(new Vector3(b.center.x,Slots[slot].y+.88f,b.center.z),new Vector3(b.size.x*.90f,1.54f,b.size.z*.90f)));
                FitCollider(colliders[slot][1],new Bounds(new Vector3(b.center.x,Slots[slot].y+.055f,b.center.z),new Vector3(b.size.x,.11f,b.size.z)));
                rows[slot]=new { instance.name, position=V(Slots[slot]), bounds=new{center=V(b.center),size=V(b.size)}, retiredRenderers=old[slot].Select(t=>t.name).ToArray(), retainedColliders=colliders[slot].Select(c=>c.name).ToArray(), gameplay="decorative/offline; no save or reclaim interaction added" };
            }
            // Imported hero sources stay independently instanced; old authored render chunks must be rebuilt.
            ReviewCamera("cam_platform_terminals",new Vector3(-9,5.5f,8),new Vector3(0,2.3f,-2),40);
            ReviewCamera("cam_platform_save_front",new Vector3(5,2.75f,-.7f),new Vector3(5,2.32f,-4),38);
            ReviewCamera("cam_platform_save_side",new Vector3(7.3f,2.9f,-2.0f),new Vector3(5,2.35f,-4),42);
            ReviewCamera("cam_platform_save_back",new Vector3(5,2.75f,-7.3f),new Vector3(5,2.32f,-4),38);
            ReviewCamera("cam_platform_save_screen",new Vector3(5,3.08f,-2.7f),new Vector3(5,2.78f,-3.90f),40);
            ReviewCamera("cam_platform_reclaim_front",new Vector3(-5,2.75f,-.7f),new Vector3(-5,2.32f,-4),38);
            AssetDatabase.SaveAssets();StaticRenderChunksEditor.Rebuild(chunks);
            EditorSceneManager.MarkSceneDirty(root.scene);EditorSceneManager.SaveOpenScenes();
            string evidence=Path.GetFullPath(Path.Combine(Application.dataPath,"../../evidence/quality/20260908/platform-terminals"));Directory.CreateDirectory(evidence);
            File.WriteAllText(Path.Combine(evidence,"install.json"),JsonConvert.SerializeObject(new{source=ModelPath,installedUtc=DateTime.UtcNow,slots=rows,missionTerminals="excluded by exact target paths",acceptance="Native views, access, Linn route and independent visual review pending"},Formatting.Indented));
        }

        static void AddDisplay(Transform parent,string variant)
        {
            const string meshPath=Folder+"/Solid seated display glass.asset";
            var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if(!mesh)
            {
                Func<float,float> z=y=>.36162f-.205625f*y+.012f;
                var front=new[]{new Vector3(-.156f,1.128f,z(1.128f)),new Vector3(.156f,1.128f,z(1.128f)),new Vector3(.156f,1.438f,z(1.438f)),new Vector3(-.156f,1.438f,z(1.438f))};
                var p=front.Concat(front.Select(v=>v-Vector3.forward*.004f)).ToArray();
                int[][] faces={new[]{0,1,2,3},new[]{7,6,5,4},new[]{0,4,5,1},new[]{1,5,6,2},new[]{2,6,7,3},new[]{3,7,4,0}};
                var vertices=new Vector3[24];var uv=new Vector2[24];var triangles=new int[36];
                for(int face=0;face<6;face++)
                {for(int c=0;c<4;c++){vertices[face*4+c]=p[faces[face][c]];uv[face*4+c]=face==0?new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)}[c]:Vector2.zero;}
                 int v=face*4,t=face*6;triangles[t]=v;triangles[t+1]=v+1;triangles[t+2]=v+2;triangles[t+3]=v;triangles[t+4]=v+2;triangles[t+5]=v+3;}
                mesh=new Mesh{name="Solid4mm terminal display behind gasket",vertices=vertices,uv=uv,triangles=triangles};mesh.RecalculateNormals();mesh.RecalculateTangents();mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,meshPath);
            }
            var mat=Material(variant+" offline display");mat.SetTexture("_BaseMap",Texture(variant+".png"));mat.SetColor("_BaseColor",Color.white);
            mat.SetFloat("_Metallic",0);mat.SetFloat("_Smoothness",.38f);mat.SetFloat("_Cull",0);
            mat.SetTexture("_EmissionMap",Texture(variant+".png"));mat.SetColor("_EmissionColor",Color.white*.3f);mat.EnableKeyword("_EMISSION");EditorUtility.SetDirty(mat);
            var display=new GameObject("Authored "+variant.ToUpperInvariant()+" OFFLINE display");display.transform.SetParent(parent,false);display.AddComponent<MeshFilter>().sharedMesh=mesh;
            var renderer=display.AddComponent<MeshRenderer>();renderer.sharedMaterial=mat;ConfigureRenderer(renderer);renderer.shadowCastingMode=ShadowCastingMode.Off;
        }
        static void AddNameplate(Transform parent)
        {
            const string path=Folder+"/Model plate ink.asset";var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(!mesh)
            {
                Func<float,float> z=y=>.33275f-.1668f*y+.0018f;
                mesh=new Mesh{name="Authored WARD SR-08 ink"};mesh.vertices=new[]{new Vector3(-.133f,1.479f,z(1.479f)),new Vector3(.133f,1.479f,z(1.479f)),new Vector3(.133f,1.545f,z(1.545f)),new Vector3(-.133f,1.545f,z(1.545f))};mesh.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)};mesh.triangles=new[]{0,1,2,0,2,3};mesh.RecalculateNormals();mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,path);
            }
            var mat=Material("Model plate ink");mat.SetTexture("_BaseMap",Texture("nameplate.png"));mat.SetColor("_BaseColor",Color.white);mat.SetFloat("_Metallic",0);mat.SetFloat("_Smoothness",.3f);mat.SetFloat("_AlphaClip",1);mat.SetFloat("_Cutoff",.25f);mat.SetFloat("_Cull",0);mat.EnableKeyword("_ALPHATEST_ON");mat.renderQueue=(int)RenderQueue.AlphaTest;EditorUtility.SetDirty(mat);
            var plate=new GameObject("Authored WARD SR-08 hardware label");plate.transform.SetParent(parent,false);plate.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=plate.AddComponent<MeshRenderer>();renderer.sharedMaterial=mat;ConfigureRenderer(renderer);renderer.shadowCastingMode=ShadowCastingMode.Off;
        }
        static void AddGasket(Transform parent)
        {
            var path=Folder+"/terminal-gasket.glb";AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);var asset=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(!asset)throw new Exception("Authored receiver gasket missing.");
            var mat=Material("Receiver gasket rubber");mat.SetColor("_BaseColor",new Color(.013f,.018f,.019f,1));mat.SetFloat("_Metallic",0);mat.SetFloat("_Smoothness",.22f);mat.enableInstancing=true;EditorUtility.SetDirty(mat);
            var gasket=(GameObject)PrefabUtility.InstantiatePrefab(asset);gasket.name="Authored receiver gasket";gasket.transform.SetParent(parent,false);
            foreach(var renderer in gasket.GetComponentsInChildren<Renderer>(true)){renderer.sharedMaterials=Enumerable.Repeat(mat,renderer.GetComponent<MeshFilter>().sharedMesh.subMeshCount).ToArray();ConfigureRenderer(renderer);}
        }
        static void FitCollider(BoxCollider c,Bounds world)
        {c.center=c.transform.InverseTransformPoint(world.center);var s=c.transform.lossyScale;c.size=new Vector3(world.size.x/Mathf.Abs(s.x),world.size.y/Mathf.Abs(s.y),world.size.z/Mathf.Abs(s.z));EditorUtility.SetDirty(c);}
        static void ReviewCamera(string name,Vector3 position,Vector3 target,float fov){if(!GameObject.Find(name))ImportBaseline.Camera(name,position,target,fov);}
        static float[] V(Vector3 v){return new[]{v.x,v.y,v.z};}
        static Bounds BoundsOf(GameObject root){var r=root.GetComponentsInChildren<Renderer>(true);if(r.Length==0)throw new Exception("No source renderers.");var b=r[0].bounds;foreach(var x in r.Skip(1))b.Encapsulate(x.bounds);return b;}
        static void ConfigureRenderer(Renderer r){r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;r.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;r.renderingLayerMask=3u;}
        static Texture2D Texture(string name){var t=AssetDatabase.LoadAssetAtPath<Texture2D>(Folder+"/"+name);if(!t)throw new Exception("Missing texture: "+name);return t;}
        static Material Material(string name){var path=Folder+"/"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);if(!m){m=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=name};AssetDatabase.CreateAsset(m,path);}return m;}
        static void ConfigureTexture(string name,bool srgb,bool normal)
        {var p=Folder+"/"+name;AssetDatabase.ImportAsset(p,ImportAssetOptions.ForceSynchronousImport);var i=AssetImporter.GetAtPath(p)as TextureImporter;if(!i)throw new Exception("Missing source texture: "+p);i.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;i.sRGBTexture=srgb;i.npotScale=TextureImporterNPOTScale.None;i.maxTextureSize=8192;i.mipmapEnabled=true;i.anisoLevel=8;i.textureCompression=TextureImporterCompression.CompressedHQ;i.isReadable=false;i.SaveAndReimport();}
    }
}
