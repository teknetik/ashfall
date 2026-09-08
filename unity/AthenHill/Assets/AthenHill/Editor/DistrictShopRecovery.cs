using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
 public static class DistrictShopRecovery
 {
  const string Evidence = DistrictCityPass.Evidence + "/recovery";
  public static void RestoreAndBuild()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   Directory.CreateDirectory(Evidence);
   var signature = DistrictCityPass.GameplaySignature();
   var chunks = UnityEngine.Object.FindAnyObjectByType<StaticRenderChunks>();
   chunks.ShowSources(true);
   var transforms = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
   var district = transforms.Single(t => t.name == DistrictCityPass.RootName);
   for (int i = 0; i < DistrictCityPass.ShopRoots.Length; i++)
   {
    var previous = transforms.Single(t => t.name == DistrictCityPass.ShopRoots[i]);
    var rejected = district.Find("District " + ImportDistrictAssets.Names[i]);
    if (!rejected) throw new Exception("Missing replacement " + ImportDistrictAssets.Names[i]);
    rejected.gameObject.SetActive(false);
    previous.gameObject.SetActive(true);
    PrefabUtility.RecordPrefabInstancePropertyModifications(previous.gameObject);
    PrefabUtility.RecordPrefabInstancePropertyModifications(rejected.gameObject);
   }
   // Inspect at pedestrian eye height as well as the original overview cameras.
   DistrictCityPass.Camera("cam_shop_recovery_close", new Vector3(12.5f, 2.1f, -10f), new Vector3(20.6f, 4.3f, -12.6f), 68);
   DistrictCityPass.Camera("cam_shop_recovery_field", new Vector3(11.8f, 2.1f, -7f), new Vector3(20.6f, 4f, -9f), 60);
   DistrictCityPass.Camera("cam_shop_recovery_finery", new Vector3(11.8f, 2.1f, -17f), new Vector3(20.6f, 4f, -18f), 60);
   StaticRenderChunksEditor.Rebuild(chunks);
   if (DistrictCityPass.GameplaySignature() != signature) throw new Exception("Gameplay roots changed during shop recovery.");
   EditorSceneManager.MarkSceneDirty(district.gameObject.scene);
   EditorSceneManager.SaveScene(district.gameObject.scene);
   AssetDatabase.SaveAssets();
   ShaderUtil.allowAsyncCompilation = false;
   foreach (var name in new[] {"cam_shop_recovery_close", "cam_shop_recovery_field", "cam_shop_recovery_finery", "cam_hill", "cam_avenue"})
   {
    PortDiagnostics.Capture(name); PortDiagnostics.Capture(name);
    File.Copy("Captures/Fixed/" + name + ".png", Evidence + "/" + name + ".png", true);
   }
   File.WriteAllText(Evidence + "/restored.json", JsonConvert.SerializeObject(new {
    restored = DistrictCityPass.ShopRoots,
    disabled = ImportDistrictAssets.Names.Take(7),
    gameplayPreserved = true,
    reason = "Rejected distorted shop replacements. Previous shop instances restored without replacing the scene or changing gameplay."
   }, Formatting.Indented));
   LinuxBuild.Development(); File.Copy("Captures/linux-build.json", Evidence + "/linux-development-build.json", true);
   LinuxBuild.Release(); File.Copy("Captures/linux-build.json", Evidence + "/linux-release-build.json", true);
  }
 }
}
