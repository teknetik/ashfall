using UnityEditor;
using UnityEngine;

namespace AthenHill.Editor
{
 public sealed class StartupMenuArtImporter : AssetPostprocessor
 {
  void OnPreprocessTexture()
  {
   if(!assetPath.StartsWith("Assets/AthenHill/UI/MenuArt/"))return;
   var importer=(TextureImporter)assetImporter;
   importer.textureType=TextureImporterType.Default;
   importer.maxTextureSize=4096;
   importer.textureCompression=TextureImporterCompression.CompressedHQ;
   importer.mipmapEnabled=false;
   importer.npotScale=TextureImporterNPOTScale.None;
   importer.wrapMode=TextureWrapMode.Clamp;
   importer.filterMode=FilterMode.Bilinear;
   importer.sRGBTexture=true;
  }
 }
}
