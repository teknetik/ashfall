using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace AthenHill.Editor
{
 public class HudArtImporter:AssetPostprocessor
 {
  void OnPreprocessTexture()
  {
   if(!assetPath.StartsWith("Assets/AthenHill/UI/Art/"))return;
   var importer=(TextureImporter)assetImporter;
   importer.textureType=TextureImporterType.Default;
   importer.textureCompression=TextureImporterCompression.Uncompressed;
   importer.mipmapEnabled=false;
   importer.alphaIsTransparency=true;
   importer.wrapMode=TextureWrapMode.Clamp;
   importer.filterMode=FilterMode.Bilinear;
   importer.npotScale=TextureImporterNPOTScale.None;
   importer.maxTextureSize=512;
  }
  public static void BuildDevelopment()
  {
   foreach(var guid in AssetDatabase.FindAssets("t:Texture2D",new[]{"Assets/AthenHill/UI/Art"}))
    AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(guid),ImportAssetOptions.ForceUpdate);
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   LinuxBuild.Development();
   CopyFontLicence("Builds/LinuxDevelopment");
  }
  public static void BuildRelease()
  {
   EditorSceneManager.OpenScene(ImportBaseline.ScenePath);
   LinuxBuild.Release();
   CopyFontLicence("Builds/Linux");
  }
  public static void BuildBoth(){BuildDevelopment();BuildRelease();}
  static void CopyFontLicence(string directory)
  {
   System.IO.File.Copy("Assets/AthenHill/UI/Art/FONT-LICENSE.txt",directory+"/UI-FONT-LICENSE.txt",true);
  }
 }
}
