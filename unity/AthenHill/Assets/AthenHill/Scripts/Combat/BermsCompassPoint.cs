using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 /// A place the Wardens have marked in the Outer Berms (2 Oct 2026): shown on the HUD compass while the player is in
 /// the Berms, with its name and distance when it sits under the centre of the compass. Sites dim once their encounter is
 /// cleared; the waystation shows only after it has been found.
 public class BermsCompassPoint:MonoBehaviour
 {
  public enum Kind { Site, Waystation, Gate }
  public string displayName="Site";
  public Kind kind;
  [Tooltip("Optional: the site's droid cluster (the marker dims while it is cleared).")]
  public DroidEncounter encounter;
  [Tooltip("Optional: shown only once this waystation has been found.")]
  public WardenWaystation waystation;
  [Min(10)]public float maxDistance=650;
  public static readonly List<BermsCompassPoint> All=new List<BermsCompassPoint>();
  public bool Shown=>kind!=Kind.Waystation||!waystation||waystation.Found;
  public bool Cleared=>encounter&&encounter.Cleared;
  void OnEnable(){All.Add(this);}
  void OnDisable(){All.Remove(this);}
 }
}
