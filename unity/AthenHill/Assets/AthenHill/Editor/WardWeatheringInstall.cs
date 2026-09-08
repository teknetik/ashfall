using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AthenHill.Editor
{
    public static partial class WardWeatheringPass
    {
        static Transform dressing;
        static Material deposits;
        static string CollisionSignature() => JsonConvert.SerializeObject(UnityEngine.Object.FindObjectsByType<Collider>().OrderBy(c => c.GetEntityId().ToString()).Select(c => new { id = c.GetEntityId().ToString(), c.name, min = V(c.bounds.min), max = V(c.bounds.max), c.enabled, c.isTrigger }));

        [MenuItem("Athen Hill/Weathering/Install localized Ward wear")]
        public static void Install()
        {
            if (EditorApplication.isPlaying) throw new Exception("Exit Play first.");
            var scene = EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
            if (GameObject.Find("Ward surface wear")) throw new Exception("Wear already installed. Edit the saved projectors and material controls.");
            if (!File.Exists(Evidence + "/before-scene.unity")) throw new Exception("Capture the saved baseline first.");
            string gameplay = DistrictCityPass.GameplaySignature();
            string collision = CollisionSignature();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            SetupTextures(); EnableDecals();
            dressing = new GameObject("Ward surface wear").transform;
            var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
            chunks.ShowSources(true);
            ApplyMaterialVariation();
            var decalShader = AssetDatabase.LoadAssetAtPath<Shader>(Root + "/WardDecal.shadergraph");
            if (!decalShader || !decalShader.isSupported) throw new Exception("Decal shader is not supported.");
            deposits = DecalMaterial("Sand grime scuffs and runoff", "WeatheringAtlas", decalShader);

            // Shallow volumes cover only the support surface, not the terminal body or NPC.
            foreach (var terminal in GameObject.Find("Mission Terminal Upgrade").transform.Cast<Transform>())
            {
                var p = terminal.position;
                Floor(terminal.name + " embedded base dirt", new Vector3(p.x, .27f, p.z), 1.85f, 1.36f, 1, .48f, 8);
                Floor(terminal.name + " standing scuffs", new Vector3(p.x, .27f, -12.5f), 1.12f, 1.20f, 2, .30f, -14);
                Floor(terminal.name + " sheltered rear sand", new Vector3(p.x+.14f, .27f, -14.38f), 1.55f, .57f, 0, .58f, 176);
            }
            Floor("Mission slab outer sand lip", new Vector3(8f,.025f,-14.97f),6.6f,.68f,0,.46f,180);
            Floor("Mission slab west corner sand",new Vector3(11.55f,.025f,-13.95f),1.1f,1.65f,0,.42f,75);
            // Keep stair centers free. Deposits follow the riser/side intersections.
            foreach (var step in All().Where(t => t.name.StartsWith("ENV_hill_stair_") && t.GetComponent<MeshRenderer>()))
            {
                var b=step.GetComponent<Renderer>().bounds;
                if (step.name.Contains("west"))
                    foreach (float z in new[]{-1.78f,1.78f}) Floor(step.name+" sand "+z,new Vector3(b.center.x,b.max.y+.018f,z),.54f,.42f,0,.52f,z>0?0:180);
                else
                    foreach (float x in new[]{-1.78f,1.78f}) Floor(step.name+" sand "+x,new Vector3(x,b.max.y+.018f,b.center.z),.42f,.54f,0,.52f,x>0?90:-90);
            }
            Floor("West stair foot sheltered pocket",new Vector3(10.64f,.022f,1.66f),.78f,.76f,0,.50f,100);
            Floor("North stair foot sheltered pocket",new Vector3(1.7f,.022f,-10.67f),.75f,.77f,0,.48f,20);
            // Boundary-wall service bay: old markings under later paper notices.
            float wallX=46.48f;
            Wall("Wall base sand and grime",new Vector3(wallX,.32f,-11),new Vector2(8,.65f),1,.32f,Vector3.right);
            Wall("Runoff below coping joint",new Vector3(wallX,2.2f,-12.8f),new Vector2(1.05f,3.8f),3,.32f,Vector3.right);
            Wall("Localized iron fixing streak",new Vector3(wallX,1.9f,-8.4f),new Vector2(.6f,2.6f),3,.26f,Vector3.right);
            Floor("Wall foot sand ribbon",new Vector3(46.15f,.022f,-11.1f),.86f,8.0f,0,.47f,90);
            Notice("Old corporate cargo stencil","TubeStencil",new Vector3(wallX,2.15f,-10.55f),new Vector2(3.8f,2.0f),.35f,Vector3.right,decalShader);
            Notice("Warden recruitment paper","WardenPoster",new Vector3(wallX-.008f,1.65f,-9.4f),new Vector2(.72f,.92f),.95f,Vector3.right,decalShader);
            Notice("Karaveen delivery notice","KaraveenNotice",new Vector3(wallX-.009f,1.4f,-10.25f),new Vector2(.58f,.77f),.87f,Vector3.right,decalShader);
            Notice("Factory orders graffiti","FactoryGraffiti",new Vector3(wallX,1.5f,-13.7f),new Vector2(2.5f,1.2f),.56f,Vector3.right,decalShader);
            // A maintenance fitting gives the only green clumps a visible water source.
            Notice("Aquifer maintenance notice","AquiferNotice",new Vector3(wallX-.01f,1.65f,-6.7f),new Vector2(.84f,1.0f),.93f,Vector3.right,decalShader);
            ServicePipe(new Vector3(46.29f,.0f,-7.42f));
            Wall("Aquifer mineral drip",new Vector3(wallX,.45f,-7.42f),new Vector2(.6f,.9f),3,.42f,Vector3.right);
            Floor("Aquifer damp soil",new Vector3(46.12f,.02f,-7.42f),.85f,1.07f,1,.43f,33);
            // A few readable notices also sit within the main district route.
            Notice("Mission slab cargo stencil","TubeStencil",new Vector3(8,.270f,-12.9f),new Vector2(2.2f,.75f),.24f,Vector3.down,decalShader);
            // Deliberately placed small clumps, derived from the existing authored grass mesh.
            var dry = GrassMaterial(false); var green = GrassMaterial(true); var tuft=TuftMesh();
            foreach(var p in new[]{new Vector3(5.55f,.25f,-14.38f),new Vector3(8.42f,.25f,-14.4f),new Vector3(10.35f,.25f,-14.45f),new Vector3(11.6f,0,-14.6f),new Vector3(10.55f,.0f,1.94f),new Vector3(9.78f,.5f,1.91f),new Vector3(1.91f,.25f,-10.18f),new Vector3(46.18f,0,-12.2f),new Vector3(46.06f,0,-9.7f),new Vector3(46.09f,0,-14.25f)})
                Tuft(p,dry,tuft,.62f);
            Tuft(new Vector3(46.1f,0,-7.28f),green,tuft,.68f); Tuft(new Vector3(46.19f,0,-7.65f),green,tuft,.46f);
            DistrictCityPass.Camera("cam_wear_wall",new Vector3(41.8f,1.7f,-10.6f),new Vector3(46.3f,1.55f,-10.3f),65);
            StaticRenderChunksEditor.Rebuild(chunks);
            Physics.SyncTransforms();
            if (gameplay != DistrictCityPass.GameplaySignature() || collision != CollisionSignature()) throw new Exception("Gameplay or collision changed unexpectedly.");
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();
            File.WriteAllText(Evidence + "/installation.json", JsonConvert.SerializeObject(new { gameplayPreserved=true,collidersPreserved=true,technique="Screen Space / Medium normals / OpenGLCore",projectors=dressing.GetComponentsInChildren<DecalProjector>().Select(d=>new{d.name,p=V(d.transform.position),size=V(d.size),d.fadeFactor,d.drawDistance}),grassClumps=12,textureSource="Built-in ImageGen; full unmodified alpha atlas; original SVG notices",originalMaterialsRetained=true },Formatting.Indented));
            Capture("after-editor");
        }

        static void SetupTextures()
        {
            foreach(var path in Directory.GetFiles(Root,"*.png"))
            {
                var i=(TextureImporter)AssetImporter.GetAtPath(path);i.textureType=TextureImporterType.Default;i.sRGBTexture=true;i.alphaIsTransparency=true;i.mipmapEnabled=true;i.wrapMode=TextureWrapMode.Clamp;i.filterMode=FilterMode.Trilinear;i.anisoLevel=8;i.maxTextureSize=4096;i.textureCompression=TextureImporterCompression.CompressedHQ;i.streamingMipmaps=true;i.SaveAndReimport();
            }
        }
        static void EnableDecals()
        {
            var renderer=AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/Settings/PC_Renderer.asset");
            if (!File.Exists(Evidence+"/before-PC_Renderer.asset"))File.Copy("Assets/Settings/PC_Renderer.asset",Evidence+"/before-PC_Renderer.asset");
            var feature=renderer.rendererFeatures.OfType<DecalRendererFeature>().FirstOrDefault();
            if (!feature){feature=ScriptableObject.CreateInstance<DecalRendererFeature>();feature.name="Ward weathering decals";AssetDatabase.AddObjectToAsset(feature,renderer);renderer.rendererFeatures.Add(feature);}
            var so=new SerializedObject(feature);so.FindProperty("m_Settings.technique").enumValueIndex=2;so.FindProperty("m_Settings.maxDrawDistance").floatValue=70;so.FindProperty("m_Settings.screenSpaceSettings.normalBlend").enumValueIndex=1;so.FindProperty("m_Settings.decalLayers").boolValue=false;so.ApplyModifiedPropertiesWithoutUndo();
            // URP 17.6 screen-space pass reads cameraColor; an intermediate target is
            // required for Camera.Render inspection as well as the postprocessed player.
            var rendererState=new SerializedObject(renderer);rendererState.FindProperty("m_IntermediateTextureMode").intValue=1;rendererState.ApplyModifiedPropertiesWithoutUndo();
            feature.SetActive(true);renderer.SetDirty();EditorUtility.SetDirty(renderer);AssetDatabase.SaveAssets();
        }
        static void ApplyMaterialVariation()
        {
            var shader=AssetDatabase.LoadAssetAtPath<Shader>(Root+"/WeatheredLit.shader");
            if(!shader || !shader.isSupported)throw new Exception("Weathered Lit failed to compile.");
            var replacements=new Dictionary<Material,Material>();
            foreach(var path in new[]{"Assets/AthenHill/Materials/Paving.mat","Assets/AthenHill/Materials/AAA/PlazaPaving.mat","Assets/AthenHill/Materials/World/MAT_stone.mat"})
            {
                var original=AssetDatabase.LoadAssetAtPath<Material>(path);var variant=new Material(original){name=original.name+" Local wear",shader=shader};
                CopyGltfSurface(original, variant);
                variant.SetFloat("_WearStrength",path.Contains("stone")?.32f:.58f);variant.SetFloat("_WearScale",.24f);variant.SetFloat("_BaseWear",path.Contains("stone")?.28f:0);variant.SetColor("_WearTint",new Color(.51f,.48f,.41f,1));
                AssetDatabase.CreateAsset(variant,Root+"/"+variant.name+".mat");replacements[original]=variant;
            }
            foreach(var r in UnityEngine.Object.FindObjectsByType<MeshRenderer>().Where(r=>r.enabled))
            {
                var materials=r.sharedMaterials;bool changed=false;
                for(int i=0;i<materials.Length;i++)if(materials[i]&&replacements.TryGetValue(materials[i],out var replacement)){materials[i]=replacement;changed=true;}
                if(!changed)continue;r.sharedMaterials=materials;EditorUtility.SetDirty(r);if(PrefabUtility.IsPartOfPrefabInstance(r))PrefabUtility.RecordPrefabInstancePropertyModifications(r);
            }
        }
        // Shader assignment does not translate glTFast property names to URP Lit.
        // MAT_stone has scalar metallic/roughness and separate albedo/normal maps.
        internal static void CopyGltfSurface(Material source, Material target)
        {
            if (!source.HasProperty("baseColorTexture")) return;
            if (source.HasProperty("metallicRoughnessTexture") && source.GetTexture("metallicRoughnessTexture"))
                throw new Exception("Pack glTF roughness into URP smoothness before converting this material.");
            target.SetTexture("_BaseMap", source.GetTexture("baseColorTexture"));
            target.SetTextureScale("_BaseMap", source.GetTextureScale("baseColorTexture"));
            target.SetTextureOffset("_BaseMap", source.GetTextureOffset("baseColorTexture"));
            target.SetColor("_BaseColor", source.GetColor("baseColorFactor"));
            target.SetTexture("_BumpMap", source.GetTexture("normalTexture"));
            target.SetFloat("_Metallic", source.GetFloat("metallicFactor"));
            target.SetFloat("_Smoothness", 1f - source.GetFloat("roughnessFactor"));
            if (source.GetTexture("normalTexture")) target.EnableKeyword("_NORMALMAP");
            EditorUtility.SetDirty(target);
        }
        static Material DecalMaterial(string name,string texture,Shader shader)
        {
            var m=new Material(shader){name=name,enableInstancing=true};m.SetTexture("Base_Map",AssetDatabase.LoadAssetAtPath<Texture2D>(Root+"/"+texture+".png"));m.SetFloat("Normal_Blend",0);AssetDatabase.CreateAsset(m,Root+"/"+name+".mat");return m;
        }
        static DecalProjector Project(string name,Vector3 p,Vector2 size,float depth,Material material,float opacity,Vector3 direction)
        {
            var go=new GameObject(name);go.transform.SetParent(dressing,false);go.transform.position=p;go.transform.rotation=Quaternion.LookRotation(direction,Mathf.Abs(direction.y)>.9f?Vector3.forward:Vector3.up);
            var d=go.AddComponent<DecalProjector>();d.material=material;d.size=new Vector3(size.x,size.y,depth);d.pivot=Vector3.zero;d.fadeFactor=opacity;d.drawDistance=65;d.fadeScale=.78f;d.startAngleFade=60;d.endAngleFade=80;return d;
        }
        static void Tile(DecalProjector d,int tile){d.uvScale=new Vector2(.49f,.49f);d.uvBias=new Vector2(tile%2*.5f+.005f,tile<2?.505f:.005f);}
        static void Floor(string name,Vector3 p,float width,float length,int tile,float opacity,float yaw)
        {
            var d=Project(name,p,new Vector2(width,length),.075f,deposits,opacity,Vector3.down);d.transform.rotation=Quaternion.Euler(0,yaw,0)*d.transform.rotation;Tile(d,tile);
        }
        static void Wall(string name,Vector3 p,Vector2 size,int tile,float opacity,Vector3 direction){var d=Project(name,p,size,.11f,deposits,opacity,direction);Tile(d,tile);}
        static void Notice(string name,string tex,Vector3 p,Vector2 size,float opacity,Vector3 direction,Shader shader)=>Project(name,p,size,.06f,DecalMaterial(name,tex,shader),opacity,direction);
        static Material GrassMaterial(bool green)
        {
            var m=new Material(AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/Atmosphere/HillGrass.mat")){name=green?"Leak corner weeds":"Dusty joint weeds"};m.SetColor("_Root",new Color(.14f,.12f,.065f));m.SetColor("_Tip",green?new Color(.34f,.39f,.17f):new Color(.51f,.43f,.24f));m.SetColor("_Dry",new Color(.63f,.53f,.34f));m.SetFloat("_WindStrength",.018f);AssetDatabase.CreateAsset(m,Root+"/"+m.name+".mat");return m;
        }
        static Mesh TuftMesh()
        {
            var source=AssetDatabase.LoadAssetAtPath<Mesh>("Assets/AthenHill/Art/Atmosphere/Hill_grass_1.asset");var vertices=source.vertices.Take(8).ToArray();var min=new Vector3(vertices.Min(v=>v.x),vertices.Min(v=>v.y),vertices.Min(v=>v.z));var center=new Vector3(vertices.Average(v=>v.x),min.y,vertices.Average(v=>v.z));
            var mesh=new Mesh{name="Reused hill grass tuft"};mesh.vertices=vertices.Select(v=>v-center).ToArray();mesh.uv=source.uv.Take(8).ToArray();mesh.colors=source.colors.Take(8).ToArray();mesh.triangles=source.triangles.Take(12).ToArray();mesh.RecalculateNormals();mesh.RecalculateBounds();var b=mesh.bounds;b.Expand(.08f);mesh.bounds=b;AssetDatabase.CreateAsset(mesh,Root+"/JointWeed.asset");return mesh;
        }
        static void Tuft(Vector3 p,Material material,Mesh mesh,float scale)
        {
            var go=new GameObject(material.name);go.transform.SetParent(dressing,false);go.transform.position=p-Vector3.up*.012f;go.transform.rotation=Quaternion.Euler(0,(p.x*139+p.z*71)%360,0);go.transform.localScale=Vector3.one*scale;go.AddComponent<MeshFilter>().sharedMesh=mesh;var r=go.AddComponent<MeshRenderer>();r.sharedMaterial=material;r.shadowCastingMode=ShadowCastingMode.Off;r.receiveShadows=true;
        }
        static void ServicePipe(Vector3 p)
        {
            var material=new Material(AssetDatabase.LoadAssetAtPath<Material>("Assets/AthenHill/Materials/World/MAT_metal.mat")){name="Aquifer service pipe"};material.SetColor("_BaseColor",new Color(.29f,.34f,.30f));AssetDatabase.CreateAsset(material,Root+"/Aquifer service pipe.mat");
            var pipe=GameObject.CreatePrimitive(PrimitiveType.Cylinder);pipe.name="Aquifer seep fitting";UnityEngine.Object.DestroyImmediate(pipe.GetComponent<Collider>());pipe.transform.SetParent(dressing,false);pipe.transform.position=p+Vector3.up*.64f;pipe.transform.localScale=new Vector3(.085f,.48f,.085f);pipe.GetComponent<Renderer>().sharedMaterial=material;
            foreach(float y in new[]{.28f,1.04f}){var ring=GameObject.CreatePrimitive(PrimitiveType.Cylinder);ring.name="Service pipe collar";UnityEngine.Object.DestroyImmediate(ring.GetComponent<Collider>());ring.transform.SetParent(dressing,false);ring.transform.position=p+Vector3.up*y;ring.transform.localScale=new Vector3(.12f,.045f,.12f);ring.GetComponent<Renderer>().sharedMaterial=material;}
        }
    }
}
