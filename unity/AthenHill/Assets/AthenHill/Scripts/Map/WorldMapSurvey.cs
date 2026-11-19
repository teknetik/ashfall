using System;
using UnityEngine;
namespace AthenHill
{
 /// Top-down survey pictures of the saved scene for the world map (19 Nov 2026), rendered by the Editor installer
 /// (WorldMapInstall20261119, step "survey", needs graphics) into Resources/WorldMap/WorldMapSurvey.asset. Each layer is
 /// an orthographic, north-up render; worldRect is exactly the x/z rectangle the picture covers, which is the whole
 /// world-to-map transform (u = (x - xMin) / width, v = (z - zMin) / height). Without this asset, or with a layer whose
 /// texture is missing, the map draws its schematic instead.
 [CreateAssetMenu(menuName="Athen Hill/World map survey",fileName="WorldMapSurvey")]
 public class WorldMapSurvey:ScriptableObject
 {
  public const string ResourcePath="WorldMap/WorldMapSurvey";
  [Serializable] public class Layer
  {
   public string id;
   public Texture2D texture;
   [Tooltip("World x (xMin, width) and z (yMin, height) covered by the picture.")]
   public Rect worldRect;
   [Tooltip("Pixels per metre of the render (for the record).")]
   public float pixelsPerMetre;
   [Tooltip("Drawn above the layers before it (the city detail sits over the Berms overview).")]
   public int order;
  }
  public Layer[] layers=new Layer[0];
  [Tooltip("Survey sun: elevation and compass bearing (degrees) used for the render.")]
  public Vector2 sunElevationBearing=new Vector2(55,135);
  public string renderedUtc,scene;
  [Serializable] public class Anchor {public string id;public Vector3 position;}
  [Tooltip("City place positions read from the saved scene by the installer (step \"anchors\"); they replace the schematic's recorded positions.")]
  public Anchor[] anchors=new Anchor[0];
  public bool Usable(Layer l)=>l!=null&&l.texture&&l.worldRect.width>0&&l.worldRect.height>0;
  public static WorldMapSurvey Load()=>Resources.Load<WorldMapSurvey>(ResourcePath);
 }
}
