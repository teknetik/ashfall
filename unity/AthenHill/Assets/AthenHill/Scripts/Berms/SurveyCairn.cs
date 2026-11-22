using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Pure survey math for Outer Berms vantage / survey cairns.
 /// Finds all discoverable WorldMap sites within surveyRadius (~140 m) on the horizontal plane.
 public static class SurveyCairnLogic
 {
  public const string FlagPrefix = "cairn:";
  public const float DefaultSurveyRadius = 140f;

  public static string FlagFor(string cairnId) => string.IsNullOrEmpty(cairnId) ? "" : FlagPrefix + cairnId;

  /// Returns discoverable Berms sites within radius of origin (XZ plane) that are allowed and not yet discovered.
  public static List<MapPlace> SitesInRadius(
   Vector3 origin,
   float radius,
   IEnumerable<MapPlace> places,
   Func<string, bool> alreadyDiscovered = null,
   Func<string, bool> allowed = null)
  {
   var found = new List<MapPlace>();
   if (places == null || radius <= 0f) return found;
   foreach (var p in places)
   {
    if (p == null || p.kind != MapPlaceKind.Site || !p.Discoverable) continue;
    if (alreadyDiscovered != null && alreadyDiscovered(p.id)) continue;
    if (allowed != null && !allowed(p.id)) continue;
    var at = p.Position;
    if (WorldMapMath.WithinRadius(origin, new Vector3(at.x, 0f, at.y), radius))
     found.Add(p);
   }
   return found;
  }

  /// Marks all eligible sites within radius on a WorldMapDiscovery instance and returns the newly marked places.
  public static List<MapPlace> Survey(
   Vector3 origin,
   float radius,
   IEnumerable<MapPlace> places,
   WorldMapDiscovery discovery,
   Func<string, bool> allowed = null)
  {
   if (discovery == null) return new List<MapPlace>();
   var candidates = SitesInRadius(origin, radius, places, discovery.Has, allowed);
   var newlyMarked = new List<MapPlace>(candidates.Count);
   for (int i = 0; i < candidates.Count; i++)
    if (discovery.Add(candidates[i].id))
     newlyMarked.Add(candidates[i]);
   return newlyMarked;
  }
 }

 /// Climbable sandstone outcrop / Warden survey tripod in the Outer Berms.
 /// Interacting surveys all WorldMap sites within surveyRadius (~140 m) and marks them on the map (M).
 [RequireComponent(typeof(WorldInteractable))]
 public class SurveyCairn : MonoBehaviour
 {
  public string cairnId = "cairn_mid_ridge";
  public string displayName = "Warden survey cairn";
  [Tooltip("Horizontal radius (metres) surveyed from this vantage point.")]
  [Min(20f)] public float surveyRadius = SurveyCairnLogic.DefaultSurveyRadius;
  public string readyPrompt = "E · Survey the Berms from this ridge";
  public string surveyedPrompt = "E · Re-check survey cairn";
  public Light beaconLight;

  public static readonly List<SurveyCairn> All = new List<SurveyCairn>();
  public bool Surveyed => session && session.HasFlag(SurveyCairnLogic.FlagFor(cairnId));
  public event Action<IReadOnlyList<MapPlace>> SurveyedSites;

  WorldInteractable interaction;
  GameSession session;
  BermsTutorial tutorial;

  void Awake() => interaction = GetComponent<WorldInteractable>();

  void Start()
  {
   session = FindAnyObjectByType<GameSession>();
   tutorial = FindAnyObjectByType<BermsTutorial>();
   Refresh();
  }

  void OnEnable()
  {
   if (!interaction) interaction = GetComponent<WorldInteractable>();
   if (interaction) interaction.Used += Use;
   All.Add(this);
   Refresh();
  }

  void OnDisable()
  {
   if (interaction) interaction.Used -= Use;
   All.Remove(this);
  }

  public void Use()
  {
   if (!session) session = FindAnyObjectByType<GameSession>();
   if (!session) return;
   if (!tutorial) tutorial = FindAnyObjectByType<BermsTutorial>();
   var map = session.Map;
   var step = tutorial ? tutorial.Step : BermsStep.Complete;

   var marked = new List<MapPlace>();
   if (map)
   {
    var candidates = SurveyCairnLogic.SitesInRadius(
     transform.position,
     surveyRadius,
     map.Places,
     map.Discovered,
     id => WorldMapDiscovery.PrimerAllows(id, step));
    foreach (var site in candidates)
     if (map.Discover(site.id))
      marked.Add(site);
   }

   session.SetFlag(SurveyCairnLogic.FlagFor(cairnId));
   if (marked.Count > 0)
   {
    string names = string.Join(", ", marked.Select(m => m.name));
    session.Notify($"{displayName}: {marked.Count} site{(marked.Count == 1 ? "" : "s")} marked on your map ({names}) · M", "Map");
   }
   else
   {
    session.Notify($"{displayName}: every landmark within {surveyRadius:0} m is already on your map.", "Map");
   }
   session.Cue(CitySoundCue.Trade);
   Refresh();
   SurveyedSites?.Invoke(marked);
  }

  void Refresh()
  {
   bool done = Surveyed;
   if (interaction) interaction.prompt = done ? surveyedPrompt : readyPrompt;
   if (beaconLight) beaconLight.enabled = !done;
  }
 }
}
