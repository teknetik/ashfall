using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace AthenHill.Editor
{
    // Scoped material/import recovery. Source models, topology, UVs and rigs stay intact.
    // Prepare changes only assets/importers; Install applies explicit renderer overrides.
    public static class ActorSurfaceFidelityPass
    {
        public const string Folder = "Assets/AthenHill/Art/ActorSurfaceFidelity";
        public const string Evidence = "../evidence/quality/20260908/actor-surfaces";
        const string Imported = "Assets/AthenHill/Art/Imported/Meshy/";
        const string GuardMaps = Imported + "VexSurface/OriginalPBR/";
        const string TravelerMaps = Imported + "Traveler/";
        const string MechanicMaps = Imported + "District/mechanic/";

        sealed class Target
        {
            public string root, family, source;
            public int vertices, triangles;
            public Target(string root, string family, string source, int vertices, int triangles)
            { this.root=root; this.family=family; this.source=source; this.vertices=vertices; this.triangles=triangles; }
        }
        static readonly Target[] Targets = {
            new("Player/MeshyPlayer", "Player", Imported+"colonist.glb",17522,10391),
            new("Colonists/npc_mira/WardGuard", "Guard", Imported+"ward-guard.glb",26859,38071),
            new("Colonists/npc_torr/WardGuard", "Guard", Imported+"ward-guard.glb",26859,38071),
            new("Colonists/npc_vex/WardGuard", "Guard", Imported+"ward-guard.glb",26859,38071),
            new("Colonists/npc_linn/WardGuard", "Guard", Imported+"ward-guard.glb",26859,38071),
            new("Colonists/npc_walker_01/Traveler", "Traveler", TravelerMaps+"Traveler.fbx",18276,10177),
            new("Colonists/npc_walker_02/Traveler", "Traveler", TravelerMaps+"Traveler.fbx",18276,10177),
            new("Colonists/npc_walker_03/Traveler", "Traveler", TravelerMaps+"Traveler.fbx",18276,10177),
            new("npc_yard_mechanic", "Mechanic", MechanicMaps+"rigged.fbx",9854,5587)
        };
        // Measured active assets only. UI, model importers and rejected candidates are excluded.
        static readonly string[] DimensionRecovery = {
            "Assets/AthenHill/Art/Textures/AAA/WallStone_NormalSource.png",
            "Assets/AthenHill/Art/Textures/AAA/WallStone_Albedo.png",
            "Assets/AthenHill/Art/Textures/AAA/Gunmetal_Albedo.png",
            "Assets/AthenHill/Art/Textures/AAA/Gunmetal_NormalSource.png",
            "Assets/AthenHill/Art/Textures/AAA/Paving_Albedo.png",
            "Assets/AthenHill/Art/Textures/AAA/Paving_NormalSource.png",
            "Assets/AthenHill/Art/Courtyard/Textures/KaraveenPoster.png",
            "Assets/AthenHill/Art/Courtyard/Textures/WardBanner.png",
            "Assets/AthenHill/Art/Courtyard/Textures/CourtyardCanvas.png",
            "Assets/AthenHill/Art/Terrain/HillSoilAlbedo.png",
            "Assets/AthenHill/Art/Terrain/SandstoneAlbedo.png",
            TravelerMaps+"Albedo.png"
        };

        static void CheckScene()
        {
            if(EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Finish Play/compilation before surface recovery.");
            if(EditorSceneManager.GetActiveScene().path!=ImportBaseline.ScenePath) throw new InvalidOperationException("Open the existing AthenHill scene; this installer never reloads it.");
            Directory.CreateDirectory(Evidence);
        }
        static string PathOf(Transform t)
        { var names=new List<string>(); while(t){names.Add(t.name);t=t.parent;} names.Reverse();return string.Join("/",names); }
        static SkinnedMeshRenderer RendererFor(Target t)
        {
            var go=GameObject.Find(t.root);
            if(!go)throw new InvalidOperationException("Missing assigned actor "+t.root);
            var rs=go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            if(rs.Length!=1 || !rs[0].sharedMesh || rs[0].sharedMaterials.Length!=1)throw new InvalidOperationException("Expected one supplied mesh/material on "+t.root);
            return rs[0];
        }
        static Mesh SourceFor(Target t)
        {
            var ms=AssetDatabase.LoadAllAssetsAtPath(t.source).OfType<Mesh>().Where(m=>m.vertexCount==t.vertices && m.triangles.Length/3==t.triangles).ToArray();
            if(ms.Length!=1)throw new InvalidOperationException("Expected exact retained source mesh for "+t.family);
            return ms[0];
        }
        static void Backup(string path)
        {
            if(!File.Exists(path))return;
            string dest=Evidence+"/before/"+path;
            if(File.Exists(dest))return;
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dest));File.Copy(path,dest);
        }
        static void Write(string name,object value)
        { File.WriteAllText(Evidence+"/"+name,JsonConvert.SerializeObject(value,Formatting.Indented)); }
        static string Hash(byte[] data)
        { using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(data)).Replace("-","").ToLowerInvariant(); }

        // Hash every preserved mesh channel, including all skin weights and blendshapes.
        // Vertex stream layout may change when tangents are added; compare semantic buffers.
        static string PreservedMeshHash(Mesh m)
        {
            using(var data=new MemoryStream()) using(var w=new BinaryWriter(data))
            {
                Action<Vector3[]> vectors=a=>{w.Write(a.Length);foreach(var v in a){w.Write(v.x);w.Write(v.y);w.Write(v.z);}};
                w.Write(m.vertexCount);w.Write((int)m.indexFormat);vectors(m.vertices);vectors(m.normals);
                for(int channel=0;channel<8;channel++)
                {
                    var uv=new List<Vector4>();m.GetUVs(channel,uv);w.Write(uv.Count);
                    foreach(var v in uv){w.Write(v.x);w.Write(v.y);w.Write(v.z);w.Write(v.w);}
                }
                var colors=m.colors32;w.Write(colors.Length);foreach(var c in colors){w.Write(c.r);w.Write(c.g);w.Write(c.b);w.Write(c.a);}
                w.Write(m.subMeshCount);for(int s=0;s<m.subMeshCount;s++){w.Write((int)m.GetTopology(s));w.Write(m.GetBaseVertex(s));var ii=m.GetIndices(s,false);w.Write(ii.Length);foreach(var i in ii)w.Write(i);}
                var bind=m.bindposes;w.Write(bind.Length);foreach(var b in bind)for(int i=0;i<16;i++)w.Write(b[i]);
                var perVertex=m.GetBonesPerVertex();var weights=m.GetAllBoneWeights();
                // These arrays view mesh-owned storage; do not dispose them.
                w.Write(perVertex.Length);foreach(var n in perVertex)w.Write(n);w.Write(weights.Length);foreach(var b in weights){w.Write(b.boneIndex);w.Write(b.weight);}
                w.Write(m.blendShapeCount);
                for(int s=0;s<m.blendShapeCount;s++)
                {
                    w.Write(m.GetBlendShapeName(s));w.Write(m.GetBlendShapeFrameCount(s));
                    for(int f=0;f<m.GetBlendShapeFrameCount(s);f++)
                    {
                        w.Write(m.GetBlendShapeFrameWeight(s,f));var v=new Vector3[m.vertexCount];var n=new Vector3[m.vertexCount];var t=new Vector3[m.vertexCount];
                        m.GetBlendShapeFrameVertices(s,f,v,n,t);vectors(v);vectors(n);vectors(t);
                    }
                }
                w.Flush();return Hash(data.ToArray());
            }
        }
        static void VerifyTangents(Mesh m)
        {
            var ts=m.tangents;var ns=m.normals;
            if(ts.Length!=m.vertexCount || ns.Length!=m.vertexCount)throw new InvalidOperationException("Missing tangent/normal channel on "+m.name);
            for(int i=0;i<ts.Length;i++)
            {
                var t=new Vector3(ts[i].x,ts[i].y,ts[i].z);
                if(float.IsNaN(t.x+t.y+t.z) || float.IsInfinity(t.x+t.y+t.z) || Mathf.Abs(t.magnitude-1)>.02f || Mathf.Abs(Vector3.Dot(t,ns[i]))>.02f || Mathf.Abs(Mathf.Abs(ts[i].w)-1)>.01f)
                    throw new InvalidOperationException("Invalid tangent on "+m.name+" vertex "+i);
            }
        }
        static Mesh PrepareMesh(Target t,List<object> checks)
        {
            var source=SourceFor(t);string hash=PreservedMeshHash(source);string path=Folder+"/"+t.family+"Tangents.asset";
            var result=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(!result)
            {
                result=Object.Instantiate(source);result.name=t.family+"Tangents";result.RecalculateTangents();
                if(PreservedMeshHash(result)!=hash)throw new InvalidOperationException("Tangent calculation changed source channels for "+t.family);
                VerifyTangents(result);AssetDatabase.CreateAsset(result,path);
            }
            if(PreservedMeshHash(result)!=hash)throw new InvalidOperationException("Existing fidelity mesh differs from source; retain artist changes and review "+path);
            VerifyTangents(result);
            checks.Add(new{t.family,source=t.source,clone=path,vertices=result.vertexCount,triangles=result.triangles.Length/3,preservedChannelsSha256=hash,exactSourceEquivalence=true,tangentCount=result.tangents.Length});
            return result;
        }

        static Texture2D Texture(string path,bool srgb,bool normal=false)
        {
            var i=AssetImporter.GetAtPath(path) as TextureImporter;
            if(!i)throw new FileNotFoundException("Missing supplied map",path);
            i.GetSourceTextureWidthAndHeight(out int w,out int h);
            var desiredType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;
            int maximum=Mathf.NextPowerOfTwo(Mathf.Max(w,h));
            bool change=i.textureType!=desiredType || i.sRGBTexture!=srgb || i.npotScale!=TextureImporterNPOTScale.None || i.maxTextureSize<maximum;
            if(change)
            {
                Backup(path+".meta");i.textureType=desiredType;i.sRGBTexture=srgb;i.npotScale=TextureImporterNPOTScale.None;i.maxTextureSize=Mathf.Max(i.maxTextureSize,maximum);i.SaveAndReimport();
            }
            var tex=AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if(tex.width!=w || tex.height!=h)throw new InvalidOperationException("Platform override still reduces supplied map "+path);
            return tex;
        }
        static Texture2D LoadRaw(string path)
        {var t=new Texture2D(2,2,TextureFormat.RGBA32,false,true);if(!t.LoadImage(File.ReadAllBytes(path),false)){Object.DestroyImmediate(t);throw new InvalidOperationException("Cannot decode map "+path);}return t;}
        static Texture2D Packed(string family,string metalPath,string roughPath,List<object> checks)
        {
            var metal=LoadRaw(metalPath);var rough=LoadRaw(roughPath);
            try
            {
                if(metal.width!=rough.width || metal.height!=rough.height)throw new InvalidOperationException("Mismatched supplied data-map sizes "+family);
                var mm=metal.GetPixels32();var rr=rough.GetPixels32();var packed=new Color32[mm.Length];
                for(int i=0;i<mm.Length;i++)packed[i]=new Color32(mm[i].r,0,0,(byte)(255-rr[i].r));
                string path=Folder+"/"+family+"MetallicSmoothness.png";
                if(!File.Exists(path))
                {
                    var outtex=new Texture2D(metal.width,metal.height,TextureFormat.RGBA32,false,true);
                    try{outtex.SetPixels32(packed);outtex.Apply();File.WriteAllBytes(path,outtex.EncodeToPNG());}
                    finally{Object.DestroyImmediate(outtex);}
                    AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
                }
                var verify=LoadRaw(path);
                try
                {
                    if(verify.width!=metal.width || verify.height!=metal.height || !verify.GetPixels32().SequenceEqual(packed))throw new InvalidOperationException("Existing packed asset differs from supplied R / inverted roughness channels: "+path);
                }
                finally{Object.DestroyImmediate(verify);}
                checks.Add(new{family,metalSource=metalPath,roughnessSource=roughPath,packed=path,width=metal.width,height=metal.height,metalSourceSha256=Hash(File.ReadAllBytes(metalPath)),roughnessSourceSha256=Hash(File.ReadAllBytes(roughPath)),packedSha256=Hash(File.ReadAllBytes(path)),channels="R = original metallic R; G/B = 0; A = 255 - original roughness R",allPixelsVerified=true});
                return Texture(path,false);
            }
            finally{Object.DestroyImmediate(metal);Object.DestroyImmediate(rough);}
        }
        static Material PrepareMaterial(string family,List<object> checks)
        {
            string path=Folder+"/"+family+".mat";var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            // Existing authored recovery materials are preserved on repeat runs.
            if(material)
            {
                if(family!="Player")
                {
                    string maps=family=="Guard"?GuardMaps:family=="Mechanic"?MechanicMaps:TravelerMaps;
                    Packed(family,maps+(family=="Traveler"?"Metallic.png":"metallic.png"),maps+(family=="Traveler"?"Roughness.png":"roughness.png"),checks);
                }
                VerifyMaterial(material,family);checks.Add(new{family,existingMaterialPreserved=true,bindingsVerified=true});return material;
            }
            var shader=Shader.Find("Universal Render Pipeline/Lit");if(!shader)throw new InvalidOperationException("URP Lit shader missing.");
            material=new Material(shader){name=family+" supplied surface",enableInstancing=true};
            material.SetColor("_BaseColor",Color.white);material.SetFloat("_Cull",2);material.SetFloat("_Metallic",0);material.SetFloat("_Smoothness",.25f);
            material.SetColor("_EmissionColor",Color.black);material.SetTexture("_EmissionMap",null);material.DisableKeyword("_EMISSION");
            if(family=="Player")
            {
                var source=AssetDatabase.LoadAllAssetsAtPath(Imported+"colonist.glb").OfType<Material>().Single();
                var albedo=source.GetTexture("baseColorTexture");if(!albedo || albedo.width!=4096 || albedo.height!=4096)throw new InvalidOperationException("Expected original 4K player albedo.");
                material.SetTexture("_BaseMap",albedo);
                checks.Add(new{family,baseMap=AssetDatabase.GetAssetPath(albedo),albedo.width,albedo.height,normal="unavailable in retained source",roughness="unavailable; conservative smoothness 0.25",metallic="unavailable; nonmetal 0",emission="disabled: supplied source incorrectly emits its entire albedo"});
            }
            else
            {
                string maps=family=="Guard"?GuardMaps:family=="Mechanic"?MechanicMaps:TravelerMaps;
                string albedo=maps+(family=="Traveler"?"Albedo.png":"base_color.png");
                string metal=maps+(family=="Traveler"?"Metallic.png":"metallic.png");
                string rough=maps+(family=="Traveler"?"Roughness.png":"roughness.png");
                material.SetTexture("_BaseMap",Texture(albedo,true));material.SetTexture("_MetallicGlossMap",Packed(family,metal,rough,checks));
                material.SetFloat("_Metallic",1);material.SetFloat("_Smoothness",1);material.SetFloat("_SmoothnessTextureChannel",0);material.EnableKeyword("_METALLICSPECGLOSSMAP");
                if(family!="Traveler")
                {material.SetTexture("_BumpMap",Texture(maps+"normal.png",false,true));material.SetFloat("_BumpScale",1);material.EnableKeyword("_NORMALMAP");}
                checks.Add(new{family,baseMap=albedo,normal=family=="Traveler"?"unavailable in retained source":maps+"normal.png",roughnessScale=1,metallicScale=1,albedoTint="white",emission="disabled"});
            }
            VerifyMaterial(material,family);AssetDatabase.CreateAsset(material,path);return material;
        }

        static void VerifyMaterial(Material material,string family)
        {
            if(material.shader.name!="Universal Render Pipeline/Lit" || material.IsKeywordEnabled("_EMISSION") || material.GetTexture("_EmissionMap") || material.GetColor("_EmissionColor").maxColorComponent>0)
                throw new InvalidOperationException("Expected non-emissive supplied surface shader on "+family);
            if(material.GetColor("_BaseColor")!=Color.white)throw new InvalidOperationException("Unexpected supplied albedo tint on "+family+"; preserve and review artist changes.");
            if(family=="Player")
            {
                var original=AssetDatabase.LoadAllAssetsAtPath(Imported+"colonist.glb").OfType<Material>().Single().GetTexture("baseColorTexture");
                if(material.GetTexture("_BaseMap")!=original || material.GetTexture("_BumpMap") || material.GetTexture("_MetallicGlossMap") || material.GetFloat("_Metallic")!=0)
                    throw new InvalidOperationException("Player binding no longer matches the supplied albedo-only recovery.");
                return;
            }
            string maps=family=="Guard"?GuardMaps:family=="Mechanic"?MechanicMaps:TravelerMaps;
            string albedo=maps+(family=="Traveler"?"Albedo.png":"base_color.png");
            if(AssetDatabase.GetAssetPath(material.GetTexture("_BaseMap"))!=albedo || AssetDatabase.GetAssetPath(material.GetTexture("_MetallicGlossMap"))!=Folder+"/"+family+"MetallicSmoothness.png" || !material.IsKeywordEnabled("_METALLICSPECGLOSSMAP") || material.GetFloat("_SmoothnessTextureChannel")!=0)
                throw new InvalidOperationException("Supplied PBR map/channel binding differs on "+family);
            if(family=="Traveler")
            {if(material.IsKeywordEnabled("_NORMALMAP") || material.GetTexture("_BumpMap"))throw new InvalidOperationException("No original traveler normal map is available.");}
            else if(AssetDatabase.GetAssetPath(material.GetTexture("_BumpMap"))!=maps+"normal.png" || !material.IsKeywordEnabled("_NORMALMAP"))throw new InvalidOperationException("Original normal map is missing on "+family);
        }

        static object ImporterState(string path)
        {
            var i=(TextureImporter)AssetImporter.GetAtPath(path);var t=AssetDatabase.LoadAssetAtPath<Texture2D>(path);i.GetSourceTextureWidthAndHeight(out int width,out int height);
            return new{path,sourceWidth=width,sourceHeight=height,importedWidth=t.width,importedHeight=t.height,i.maxTextureSize,npot=i.npotScale.ToString(),i.sRGBTexture,type=i.textureType.ToString(),i.mipmapEnabled,i.anisoLevel,i.streamingMipmaps,compression=i.textureCompression.ToString()};
        }
        static void RecoverMeasuredDimensions(List<object> reports)
        {
            foreach(string path in DimensionRecovery)
            {
                var importer=AssetImporter.GetAtPath(path) as TextureImporter;if(!importer)throw new FileNotFoundException("Missing measured texture",path);
                var before=ImporterState(path);importer.GetSourceTextureWidthAndHeight(out int width,out int height);
                int maximum=Mathf.NextPowerOfTwo(Mathf.Max(width,height));
                if(importer.npotScale!=TextureImporterNPOTScale.None || importer.maxTextureSize<maximum)
                {Backup(path+".meta");importer.npotScale=TextureImporterNPOTScale.None;importer.maxTextureSize=Mathf.Max(importer.maxTextureSize,maximum);importer.SaveAndReimport();}
                var texture=AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if(texture.width!=width || texture.height!=height)throw new InvalidOperationException("An explicit platform limit still reduces "+path+"; review that override before proceeding.");
                reports.Add(new{before,after=ImporterState(path),sourcePixelsUnchanged=true});
            }
        }
        static object RendererState(Target t)
        {
            var r=RendererFor(t);return new{t.root,t.family,renderer=PathOf(r.transform),mesh=AssetDatabase.GetAssetPath(r.sharedMesh),meshHash=PreservedMeshHash(r.sharedMesh),material=AssetDatabase.GetAssetPath(r.sharedMaterial),shader=r.sharedMaterial.shader.name,shadow=r.shadowCastingMode.ToString(),r.receiveShadows,
                localBoundsCenter=new[]{r.localBounds.center.x,r.localBounds.center.y,r.localBounds.center.z},localBoundsSize=new[]{r.localBounds.size.x,r.localBounds.size.y,r.localBounds.size.z},r.updateWhenOffscreen};
        }
        static string RigSignature(bool includeBounds=true)
        {
            return JsonConvert.SerializeObject(Targets.Select(t=>{
                var r=RendererFor(t);return new{t.root,renderer=PathOf(r.transform),rootBone=r.rootBone?PathOf(r.rootBone):null,bones=r.bones.Select(PathOf).ToArray(),
                    transforms=GameObject.Find(t.root).GetComponentsInChildren<Transform>(true).Select(x=>new{path=PathOf(x),p=x.localPosition.ToString("R"),q=x.localRotation.ToString("R"),s=x.localScale.ToString("R")}).ToArray(),
                    boundsCenter=includeBounds?r.localBounds.center.ToString("R"):null,boundsSize=includeBounds?r.localBounds.size.ToString("R"):null,r.updateWhenOffscreen};
            }));
        }
        const float CullingBoundsToleranceMetres=.0001f; // 0.1 mm in world space, not imported mesh units.
        sealed class CullingBoundsCheck
        {
            public string renderer;
            public float[] localCenterDelta,localSizeDelta;
            public float maximumWorldCornerDeltaMetres;
            public bool withinTolerance;
        }
        static CullingBoundsCheck CompareBounds(SkinnedMeshRenderer r,Bounds original)
        {
            var center=r.localBounds.center-original.center;var size=r.localBounds.size-original.size;
            float maximum=0;
            // Imported actors may be at 0.01 scale. Test all corresponding AABB
            // corners through the actual world matrix, including nonuniform parents.
            for(int i=0;i<8;i++)
            {
                var cornerDelta=center+Vector3.Scale(size*.5f,new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1));
                maximum=Mathf.Max(maximum,r.localToWorldMatrix.MultiplyVector(cornerDelta).magnitude);
            }
            return new CullingBoundsCheck{renderer=PathOf(r.transform),localCenterDelta=new[]{center.x,center.y,center.z},localSizeDelta=new[]{size.x,size.y,size.z},
                maximumWorldCornerDeltaMetres=maximum,withinTolerance=!float.IsNaN(maximum)&&!float.IsInfinity(maximum)&&maximum<=CullingBoundsToleranceMetres};
        }
        [MenuItem("Athen Hill/Characters/Prepare supplied surface fidelity assets")]
        public static void Prepare()
        {
            CheckScene();var before=Targets.Select(RendererState).ToArray();string rig=RigSignature();bool dirty=EditorSceneManager.GetActiveScene().isDirty;
            if(File.Exists(Evidence+"/prepared.json")&&!File.Exists(Evidence+"/prepared-first.json"))File.Copy(Evidence+"/prepared.json",Evidence+"/prepared-first.json");
            // Reject altered assignments/topology before creating assets or changing import settings.
            foreach(var t in Targets)if(PreservedMeshHash(RendererFor(t).sharedMesh)!=PreservedMeshHash(SourceFor(t)))throw new InvalidOperationException("Actor mesh differs from retained source, review before overriding "+t.root);
            Directory.CreateDirectory(Folder);AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var meshChecks=new List<object>();var mapChecks=new List<object>();var imports=new List<object>();
            foreach(var t in Targets.GroupBy(t=>t.family).Select(g=>g.First()))PrepareMesh(t,meshChecks);
            RecoverMeasuredDimensions(imports);
            foreach(var family in Targets.Select(t=>t.family).Distinct())PrepareMaterial(family,mapChecks);
            AssetDatabase.SaveAssets();
            if(RigSignature()!=rig || EditorSceneManager.GetActiveScene().isDirty!=dirty)throw new InvalidOperationException("Preparation unexpectedly changed scene state.");
            Write("prepared.json",new{capturedUtc=DateTime.UtcNow.ToString("o"),scene=EditorSceneManager.GetActiveScene().path,before,meshChecks,mapChecks,imports,sceneUnchanged=true,
                limitations=new[]{"Player delivery has albedo only; no invented source normal/roughness/metallic maps.","Traveler delivery has no normal texture.","This is source fidelity recovery, not source shape/animation/AAA visual acceptance."}});
        }
        [MenuItem("Athen Hill/Characters/Install supplied surface fidelity")]
        public static void Install()
        {
            CheckScene();Prepare();var before=Targets.Select(RendererState).ToArray();string rig=RigSignature(false);
            var original=Targets.Select(t=>{var r=RendererFor(t);return new{renderer=r,mesh=r.sharedMesh,materials=r.sharedMaterials,bounds=r.localBounds,shadow=r.shadowCastingMode,receive=r.receiveShadows};}).ToArray();
            CullingBoundsCheck[] boundsChecks=null;
            try
            {
                foreach(var t in Targets)
                {
                    var r=RendererFor(t);var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(Folder+"/"+t.family+"Tangents.asset");var mat=AssetDatabase.LoadAssetAtPath<Material>(Folder+"/"+t.family+".mat");
                    if(!mesh || !mat)throw new InvalidOperationException("Prepare surface assets first.");
                    if(PreservedMeshHash(r.sharedMesh)!=PreservedMeshHash(mesh))throw new InvalidOperationException("Mesh equivalence failed before assigning "+t.root);
                    var bounds=r.localBounds;
                    Undo.RecordObject(r,"Restore supplied actor surface");
                    // Unity can reset the serialized culling AABB when sharedMesh changes.
                    // Avoid reassigning the same mesh/bounds on repeated installs.
                    if(r.sharedMesh!=mesh){r.sharedMesh=mesh;r.localBounds=bounds;}
                    r.sharedMaterial=mat;r.shadowCastingMode=ShadowCastingMode.On;r.receiveShadows=true;
                    EditorUtility.SetDirty(r);PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                }
                boundsChecks=original.Select(state=>CompareBounds(state.renderer,state.bounds)).ToArray();
                Write("culling-bounds-check.json",new{capturedUtc=DateTime.UtcNow.ToString("o"),toleranceMetres=CullingBoundsToleranceMetres,
                    basis="Maximum corresponding culling-AABB corner displacement transformed by the renderer localToWorldMatrix; exact skeleton/transform/buffer checks remain separate.",boundsChecks});
                if(RigSignature(false)!=rig || boundsChecks.Any(check=>!check.withinTolerance))
                {
                    Write("install-signature-failure.json",new{beforeRig=JsonConvert.DeserializeObject(rig),afterRig=JsonConvert.DeserializeObject(RigSignature(false)),boundsChecks,toleranceMetres=CullingBoundsToleranceMetres});
                    throw new InvalidOperationException("Actor skeleton, transform, culling bounds or offscreen policy changed unexpectedly; see install-signature-failure.json.");
                }
            }
            catch
            {
                foreach(var state in original)
                {
                    var r=state.renderer;r.sharedMesh=state.mesh;r.sharedMaterials=state.materials;r.localBounds=state.bounds;r.shadowCastingMode=state.shadow;r.receiveShadows=state.receive;
                    EditorUtility.SetDirty(r);PrefabUtility.RecordPrefabInstancePropertyModifications(r);
                }
                throw;
            }
            AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            // Root owns coordinated save/chunk rebuild/build. This does not hide stale-source guards.
            Write("installed.json",new{capturedUtc=DateTime.UtcNow.ToString("o"),before,after=Targets.Select(RendererState).ToArray(),rigAndTransformsPreserved=true,
                cullingBoundsToleranceMetres=CullingBoundsToleranceMetres,boundsChecks,sceneNeedsSave=true});
            Debug.Log("Supplied actor surface recovery installed on nine existing renderers. Save scene, rebuild chunks if other source work changed, then review native sun/shade and motion.");
        }

        [MenuItem("Athen Hill/Characters/Recover interrupted surface install bounds")]
        public static void RecoverInterruptedInstallBounds()
        {
            CheckScene();
            const string baseline="../evidence/quality/20260908/before-scene.unity";
            const string expected="3c18885c33cce5d79ce65923ad8e3aba90760f494c08df02ababe69f977ede52";
            var bytes=File.ReadAllBytes(baseline);
            if(Hash(bytes)!=expected)throw new InvalidOperationException("The frozen pre-install scene identity differs. Review its original renderer bounds manually.");
            var yaml=System.Text.Encoding.UTF8.GetString(bytes);
            // These actor renderers are supplied prefab instances. With no local AABB
            // override in the frozen scene, their source prefab AABB is authoritative.
            if(yaml.Contains("m_AABB")||yaml.Contains("m_LocalAABB")||yaml.Contains("m_LocalBounds"))throw new InvalidOperationException("Frozen scene contains culling-bounds overrides; do not infer source-prefab bounds.");
            var before=Targets.Select(RendererState).ToArray();
            var recovery=Targets.Select(t=>
            {
                var r=RendererFor(t);var source=SourceFor(t);
                if(PreservedMeshHash(r.sharedMesh)!=PreservedMeshHash(source))throw new InvalidOperationException("Actor topology differs from baseline source: "+t.root);
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(t.source);
                if(!prefab)throw new InvalidOperationException("Missing supplied prefab: "+t.source);
                var renderers=prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s=>s.sharedMesh==source).ToArray();
                if(renderers.Length!=1)throw new InvalidOperationException("Expected exactly one original skinned source: "+t.source);
                return new{t.root,t.source,renderer=r,bounds=renderers[0].localBounds};
            }).ToArray();
            foreach(var state in recovery)
            {
                Undo.RecordObject(state.renderer,"Recover original actor culling bounds");state.renderer.localBounds=state.bounds;
                EditorUtility.SetDirty(state.renderer);PrefabUtility.RecordPrefabInstancePropertyModifications(state.renderer);
            }
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Write("bounds-recovery.json",new{capturedUtc=DateTime.UtcNow.ToString("o"),baseline,baselineSha256=expected,
                derivation="Original supplied SkinnedMeshRenderer.localBounds; frozen serialized prefab instances contain no AABB overrides.",before,after=Targets.Select(RendererState).ToArray()});
            Debug.Log("Restored the nine original source-prefab culling bounds only. Run Install supplied surface fidelity again; no scene save or build performed.");
        }
    }
}
