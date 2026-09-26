public static class StagedApiCompileProbe {
public static object Request0() {
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
if (UnityEditor.EditorApplication.isPlaying || UnityEditor.EditorApplication.isCompiling || scene.isDirty) throw new System.InvalidOperationException("Require clean saved Edit mode");
if (scene.path != "Assets/AthenHill/Scenes/AthenHill.unity") throw new System.InvalidOperationException("Unexpected scene");
var plan = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText("/home/teknetik/code/ao2/art/quality_20260926/ground-review-cameras/plan.json"));
var cameras = UnityEngine.Object.FindObjectsByType<UnityEngine.Camera>(UnityEngine.FindObjectsInactive.Include, UnityEngine.FindObjectsSortMode.None);
UnityEngine.Camera source = null;
foreach (var camera in cameras) if (camera.name == "cam_gate") source = camera;
if (!source || source.enabled) throw new System.InvalidOperationException("Expected disabled cam_gate source");
foreach (var item in plan["cameras"]) foreach (var camera in cameras) if (camera.name == (string)item["name"]) throw new System.InvalidOperationException("Camera already exists: " + camera.name);
var chunks = UnityEngine.Object.FindAnyObjectByType<AthenHill.StaticRenderChunks>();
if (!chunks || chunks.editingSources || chunks.sourceFingerprint != AthenHill.Editor.StaticRenderChunksEditor.Fingerprint(chunks)) throw new System.InvalidOperationException("Render chunks are not current");
var beforeFingerprint = chunks.sourceFingerprint;
var backup = "/home/teknetik/code/ao2/art/quality_20260926/ground-review-cameras/before-cameras.unity";
if (System.IO.File.Exists(backup)) throw new System.InvalidOperationException("Refuse overwriting backup");
System.IO.File.Copy(scene.path, backup);
var group = new UnityEngine.GameObject("Quality review cameras 20260926");
UnityEditor.Undo.RegisterCreatedObjectUndo(group, "Add saved ground review cameras");
var records = new System.Collections.Generic.List<object>();
foreach (var item in plan["cameras"])
{
 var go = new UnityEngine.GameObject((string)item["name"]);
 go.transform.SetParent(group.transform, false);
 var p = item["position"]; var t = item["target"];
 var position = new UnityEngine.Vector3((float)p[0], (float)p[1], (float)p[2]);
 var target = new UnityEngine.Vector3((float)t[0], (float)t[1], (float)t[2]);
 go.transform.SetPositionAndRotation(position, UnityEngine.Quaternion.LookRotation(target-position));
 var camera = go.AddComponent<UnityEngine.Camera>();
 UnityEditor.EditorUtility.CopySerialized(source, camera);
 camera.enabled = false; camera.fieldOfView = (float)item["verticalFov"];
 camera.aspect = 16f/9f; camera.nearClipPlane = .08f; camera.farClipPlane = 250f;
 camera.targetTexture = null; go.tag = "Untagged";
 var sourceData = source.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
 if (sourceData) { var data = go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>(); UnityEditor.EditorUtility.CopySerialized(sourceData, data); }
 records.Add(new { name=go.name, position=new[]{position.x,position.y,position.z}, target=new[]{target.x,target.y,target.z}, fov=camera.fieldOfView, enabled=camera.enabled, audioListener=go.GetComponent<UnityEngine.AudioListener>() != null });
}
if (beforeFingerprint != AthenHill.Editor.StaticRenderChunksEditor.Fingerprint(chunks)) throw new System.InvalidOperationException("Unexpected render-source change");
UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(scene);
UnityEditor.SceneManagement.EditorSceneManager.SaveScene(scene);
var result = new { scene=scene.path, cameras=records, chunkFingerprint=beforeFingerprint, chunkFingerprintUnchanged=true, sourceMaterialUnchanged=true, backup=backup, dirtyAfterSave=scene.isDirty };
System.IO.File.WriteAllText("/home/teknetik/code/ao2/art/quality_20260926/ground-review-cameras/installation.json", Newtonsoft.Json.JsonConvert.SerializeObject(result, Newtonsoft.Json.Formatting.Indented));
return Newtonsoft.Json.JsonConvert.SerializeObject(result);
}
public static object Request1() {
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
if (UnityEditor.EditorApplication.isPlaying || UnityEditor.EditorApplication.isCompiling || scene.isDirty) throw new System.InvalidOperationException("Require clean saved Edit mode");
var path = "Assets/AthenHill/Art/Weathering/Paving Local wear.mat";
var material = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>(path);
if (!material || material.shader.name != "Athen Hill/Weathered Lit") throw new System.InvalidOperationException("Unexpected paving material");
var backup = "/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1/before-paving-material.mat";
if (System.IO.File.Exists(backup)) throw new System.InvalidOperationException("Backup already exists; inspect before resuming");
var output = "Assets/AthenHill/Art/Quality20260926/Paving";
if (UnityEditor.AssetDatabase.IsValidFolder(output)) throw new System.InvalidOperationException("Candidate folder already exists");
var baseMap=material.GetTexture("_BaseMap"); var baseScale=material.GetTextureScale("_BaseMap"); var baseOffset=material.GetTextureOffset("_BaseMap");
var originalNormal=material.GetTexture("_BumpMap"); var originalStrength=material.GetFloat("_BumpScale"); var originalSmoothness=material.GetFloat("_Smoothness");
System.IO.File.Copy(path, backup);
UnityEditor.AssetDatabase.CreateFolder("Assets/AthenHill/Art/Quality20260926", "Paving");
var files = new[]{"Normal-OpenGL.png", "MetallicSmoothness.png"};
var records = new System.Collections.Generic.List<object>();
foreach (var file in files)
{
 var target=output+"/"+file;
 System.IO.File.Copy("/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1/periodic-v2/"+file,target);
 UnityEditor.AssetDatabase.ImportAsset(target, UnityEditor.ImportAssetOptions.ForceSynchronousImport);
 var importer = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(target);
 bool normal=file=="Normal-OpenGL.png";
 importer.textureType=normal ? UnityEditor.TextureImporterType.NormalMap : UnityEditor.TextureImporterType.Default;
 importer.sRGBTexture=false; importer.convertToNormalmap=false; importer.flipGreenChannel=false;
 importer.npotScale=UnityEditor.TextureImporterNPOTScale.None; importer.maxTextureSize=2048;
 importer.wrapMode=UnityEngine.TextureWrapMode.Repeat; importer.filterMode=UnityEngine.FilterMode.Trilinear; importer.anisoLevel=8;
 importer.mipmapEnabled=true; importer.streamingMipmaps=true; importer.isReadable=false;
 importer.alphaSource=normal ? UnityEditor.TextureImporterAlphaSource.None : UnityEditor.TextureImporterAlphaSource.FromInput;
 importer.alphaIsTransparency=false; importer.textureCompression=UnityEditor.TextureImporterCompression.CompressedHQ;
 importer.SaveAndReimport();
 var texture=UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>(target);
 if (texture.width!=1254 || texture.height!=1254) throw new System.InvalidOperationException("Texture size changed: "+target);
 records.Add(new { path=target, guid=UnityEditor.AssetDatabase.AssetPathToGUID(target), width=texture.width, height=texture.height, format=texture.format.ToString(), colorSpace=texture.activeTextureColorSpace.ToString(), normal=normal, positiveGreen=true, convertToNormalmap=importer.convertToNormalmap, streamingMipmaps=texture.streamingMipmaps });
}
UnityEditor.Undo.RecordObject(material,"Audition authored paving normal");
material.SetTexture("_BumpMap",UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>(output+"/Normal-OpenGL.png"));
material.SetFloat("_BumpScale",1f); material.EnableKeyword("_NORMALMAP");
UnityEditor.EditorUtility.SetDirty(material); UnityEditor.AssetDatabase.SaveAssets();
if (material.GetTexture("_BaseMap")!=baseMap || material.GetTextureScale("_BaseMap")!=baseScale || material.GetTextureOffset("_BaseMap")!=baseOffset || material.GetFloat("_Smoothness")!=originalSmoothness) throw new System.InvalidOperationException("Unexpected albedo/UV/smoothness mutation");
var chunks=UnityEngine.Object.FindAnyObjectByType<AthenHill.StaticRenderChunks>();
if (chunks.sourceFingerprint!=AthenHill.Editor.StaticRenderChunksEditor.Fingerprint(chunks)) throw new System.InvalidOperationException("Unexpected source fingerprint change");
var result=new { phase="normal-only audition; not accepted", material=path, backup=backup, originalNormal=UnityEditor.AssetDatabase.GetAssetPath(originalNormal), originalStrength=originalStrength, originalSmoothness=originalSmoothness, textures=records, albedoUnchanged=true, geometryAndCollidersUnchanged=true, chunksCurrent=true, sceneDirty=scene.isDirty };
System.IO.File.WriteAllText("/home/teknetik/code/ao2/art/quality_20260926/west-gate-paving-v1/normal-only-installation.json", Newtonsoft.Json.JsonConvert.SerializeObject(result,Newtonsoft.Json.Formatting.Indented));
return Newtonsoft.Json.JsonConvert.SerializeObject(result);
}
}
