using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 // ==========================================================================
 // 1. Distress Signal Hunts (directional radio ping toward hidden drops)
 // ==========================================================================

 /// Pure bearing and range math for Outer Berms distress signal pings.
 public static class DistressSignalMath
 {
  static readonly string[] Cardinals = { "N", "NE", "E", "SE", "S", "SW", "W", "NW" };

  /// Compass bearing in degrees [0, 360) on the XZ plane: 0 = North (+Z), 90 = East (+X), 180 = South (-Z), 270 = West (-X).
  public static float BearingDegrees(Vector3 from, Vector3 to)
  {
   float dx = to.x - from.x;
   float dz = to.z - from.z;
   if (dx * dx + dz * dz < 1e-8f) return 0f;
   float deg = Mathf.Atan2(dx, dz) * Mathf.Rad2Deg;
   return (deg % 360f + 360f) % 360f;
  }

  public static string CardinalDirection(float bearingDegrees)
  {
   float norm = (bearingDegrees % 360f + 360f) % 360f;
   int idx = Mathf.FloorToInt((norm + 22.5f) / 45f) % 8;
   return Cardinals[idx];
  }

  public static float HorizontalDistance(Vector3 a, Vector3 b)
  {
   float dx = a.x - b.x;
   float dz = a.z - b.z;
   return Mathf.Sqrt(dx * dx + dz * dz);
  }

  public static bool ShouldPing(Vector3 player, Vector3 target, float triggerRadius, float arrivedRadius, bool resolved)
  {
   if (resolved || triggerRadius <= 0f) return false;
   float dist = HorizontalDistance(player, target);
   return dist <= triggerRadius && dist > Mathf.Max(0f, arrivedRadius);
  }

  public static string FormatPing(string label, Vector3 from, Vector3 to)
  {
   float dist = HorizontalDistance(from, to);
   float bearing = BearingDegrees(from, to);
   string dir = CardinalDirection(bearing);
   return $"Distress ping: {label} · {Mathf.RoundToInt(dist)} m {dir} ({Mathf.RoundToInt(bearing):000}°)";
  }
 }

 /// Hidden Karaveen drop or downed Warden supply pod that emits periodic directional radio pings
 /// once the player enters triggerRadius, until found/resolved.
 public class DistressSignalBeacon : MonoBehaviour
 {
  public const string ResolvedFlagPrefix = "distress:";

  public string signalId = "distress_karaveen_01";
  public string displayName = "Downed Warden supply pod";
  [Min(10f)] public float triggerRadius = 115f;
  [Min(2f)] public float arrivedRadius = 14f;
  [Min(3f)] public float pingIntervalSeconds = 18f;
  public Light strobeLight;

  public static readonly List<DistressSignalBeacon> All = new List<DistressSignalBeacon>();
  public bool Resolved => session && session.HasFlag(ResolvedFlagPrefix + signalId);
  public event Action<string> Pinged;

  GameSession session;
  float nextPingAt;

  void Start() => session = FindAnyObjectByType<GameSession>();
  void OnEnable() => All.Add(this);
  void OnDisable() => All.Remove(this);

  void Update()
  {
   if (!session || !session.HasStarted || session.State != CityState.Play || !session.player) return;
   if (Resolved)
   {
    if (strobeLight) strobeLight.enabled = false;
    return;
   }

   var playerPos = session.player.transform.position;
   float dist = DistressSignalMath.HorizontalDistance(playerPos, transform.position);
   if (dist <= arrivedRadius)
   {
    session.SetFlag(ResolvedFlagPrefix + signalId);
    session.Notify($"Located {displayName}.", "Radio");
    if (strobeLight) strobeLight.enabled = false;
    return;
   }

   if (Time.time >= nextPingAt && DistressSignalMath.ShouldPing(playerPos, transform.position, triggerRadius, arrivedRadius, false))
   {
    nextPingAt = Time.time + pingIntervalSeconds;
    string msg = DistressSignalMath.FormatPing(displayName, playerPos, transform.position);
    session.Notify(msg, "Radio");
    Pinged?.Invoke(msg);
   }
  }
 }

 // ==========================================================================
 // 2. Wake-Up Salvage Nodes (alerting nearby dormant droids when searched)
 // ==========================================================================

 /// Pure selection helper for wake-up salvage ambushes.
 public static class WakeUpSalvageLogic
 {
  public static List<int> SelectDormantToWake(
   Vector3 origin,
   float wakeRadius,
   IReadOnlyList<(Vector3 position, bool alive, bool engaged)> droids,
   int maxToWake)
  {
   var picked = new List<(int index, float sqrDist)>();
   if (droids == null || wakeRadius <= 0f || maxToWake <= 0) return new List<int>();
   float r2 = wakeRadius * wakeRadius;
   for (int i = 0; i < droids.Count; i++)
   {
    var d = droids[i];
    if (!d.alive || d.engaged) continue;
    float dx = d.position.x - origin.x;
    float dz = d.position.z - origin.z;
    float sqr = dx * dx + dz * dz;
    if (sqr <= r2) picked.Add((i, sqr));
   }
   picked.Sort((a, b) => a.sqrDist.CompareTo(b.sqrDist));
   int take = Math.Min(maxToWake, picked.Count);
   var result = new List<int>(take);
   for (int i = 0; i < take; i++) result.Add(picked[i].index);
   return result;
  }
 }

 /// Attach alongside a SalvageNode on high-value Band 2/3 wrecks.
 /// When the player begins searching the node, wakes up to maxDroidsToWake nearby dormant FeralDroids.
 [RequireComponent(typeof(SalvageNode))]
 public class WakeUpSalvageNode : MonoBehaviour
 {
  [Min(2f)] public float wakeRadius = 28f;
  [Min(1)] public int maxDroidsToWake = 3;
  [Min(0f)] public float alertDelaySeconds = 0.35f;
  public string warningMessage = "Power draw spike! Dormant droids waking nearby.";
  [Tooltip("Optional explicit droids to wake; when empty, scans FeralDroid.Active within Wake Radius.")]
  public FeralDroid[] explicitDroids = new FeralDroid[0];

  public event Action<int> DroidsWoken;

  SalvageNode node;
  GameSession session;
  bool triggeredThisSearch;

  void Awake() => node = GetComponent<SalvageNode>();
  void Start() => session = FindAnyObjectByType<GameSession>();

  void Update()
  {
   if (!node || node.Search == null) return;
   bool searching = node.Search.State == SalvageNodeState.Searching;
   if (searching && !triggeredThisSearch)
   {
    triggeredThisSearch = true;
    TriggerWakeUp();
   }
   else if (!searching)
   {
    triggeredThisSearch = false;
   }
  }

  public int TriggerWakeUp()
  {
   var pool = (explicitDroids != null && explicitDroids.Length > 0)
    ? explicitDroids.Where(d => d != null).ToList()
    : FeralDroid.Active.Where(d => d != null).ToList();

   var snapshot = new List<(Vector3 position, bool alive, bool engaged)>(pool.Count);
   for (int i = 0; i < pool.Count; i++)
   {
    var d = pool[i];
    bool alive = d.State != DroidState.Dead && (!d.Health || d.Health.Alive);
    snapshot.Add((d.transform.position, alive, d.Engaged));
   }

   var indices = WakeUpSalvageLogic.SelectDormantToWake(transform.position, wakeRadius, snapshot, maxDroidsToWake);
   for (int i = 0; i < indices.Count; i++)
    pool[indices[i]].JoinFight(alertDelaySeconds);

   if (indices.Count > 0)
   {
    if (!session) session = FindAnyObjectByType<GameSession>();
    if (session && !string.IsNullOrEmpty(warningMessage))
     session.Notify(warningMessage, "Warning");
    DroidsWoken?.Invoke(indices.Count);
   }
   return indices.Count;
  }
 }

 // ==========================================================================
 // 3. Roaming Feral Patrols (waypoint circuits between Outer Berms sites)
 // ==========================================================================

 /// Pure waypoint circuit stepper for roaming droid patrols.
 public sealed class PatrolRouteLogic
 {
  readonly Vector3[] waypoints;
  public bool Loop { get; }
  public float ArrivalRadius { get; }
  public int CurrentIndex { get; private set; }
  public int Direction { get; private set; } = 1;
  public int Count => waypoints.Length;
  public Vector3 CurrentWaypoint => waypoints.Length > 0 ? waypoints[CurrentIndex] : Vector3.zero;

  public PatrolRouteLogic(IReadOnlyList<Vector3> waypoints, bool loop = true, float arrivalRadius = 2.5f)
  {
   this.waypoints = waypoints != null ? waypoints.ToArray() : Array.Empty<Vector3>();
   Loop = loop;
   ArrivalRadius = Mathf.Max(0.1f, arrivalRadius);
   CurrentIndex = 0;
  }

  /// Checks whether position has arrived at CurrentWaypoint and advances CurrentIndex if so.
  public bool Advance(Vector3 position)
  {
   if (waypoints.Length <= 1) return false;
   if (DistressSignalMath.HorizontalDistance(position, CurrentWaypoint) > ArrivalRadius) return false;
   if (Loop)
   {
    CurrentIndex = (CurrentIndex + 1) % waypoints.Length;
   }
   else
   {
    int next = CurrentIndex + Direction;
    if (next >= waypoints.Length || next < 0)
    {
     Direction = -Direction;
     next = CurrentIndex + Direction;
    }
    CurrentIndex = Mathf.Clamp(next, 0, waypoints.Length - 1);
   }
   return true;
  }

  /// Steps current position horizontally toward CurrentWaypoint by speed * dt and advances on arrival.
  public Vector3 StepTowards(Vector3 current, float speed, float dt)
  {
   if (waypoints.Length == 0 || speed <= 0f || dt <= 0f) return current;
   var target = CurrentWaypoint;
   var delta = new Vector3(target.x - current.x, 0f, target.z - current.z);
   float dist = delta.magnitude;
   float step = speed * dt;
   Vector3 next = dist <= step || dist < 1e-5f
    ? new Vector3(target.x, current.y, target.z)
    : current + delta / dist * step;
   Advance(next);
   return next;
  }
 }

 /// Moves a small patrol of idle FeralDroids along a waypoint circuit between Outer Berms sites.
 /// Yields immediately whenever any member enters combat (Engaged).
 public class RoamingFeralPatrol : MonoBehaviour
 {
  public string patrolId = "patrol_mid_berms";
  public Transform[] waypoints = new Transform[0];
  public FeralDroid[] members = new FeralDroid[0];
  [Min(0.2f)] public float patrolSpeed = 1.9f;
  [Min(0.5f)] public float arrivalRadius = 2.5f;
  public bool loop = true;
  [Min(0f)] public float pauseAtWaypointSeconds = 2f;

  public PatrolRouteLogic Route { get; private set; }
  float pauseUntil;
  GameSession session;

  void Start()
  {
   session = FindAnyObjectByType<GameSession>();
   BuildRoute();
  }

  public void BuildRoute()
  {
   var pts = waypoints != null
    ? waypoints.Where(w => w != null).Select(w => w.position).ToList()
    : new List<Vector3>();
   Route = new PatrolRouteLogic(pts, loop, arrivalRadius);
  }

  void Update()
  {
   if (Route == null || Route.Count < 2) return;
   if (session && session.State != CityState.Play) return;
   if (Time.time < pauseUntil) return;

   bool anyAlive = false;
   for (int i = 0; i < members.Length; i++)
   {
    var d = members[i];
    if (!d || d.State == DroidState.Dead) continue;
    anyAlive = true;
    if (d.Engaged) return; // combat owns the droids while fighting
   }
   if (!anyAlive) return;

   int before = Route.CurrentIndex;
   Vector3 next = Route.StepTowards(transform.position, patrolSpeed, Time.deltaTime);
   Vector3 delta = next - transform.position;
   transform.position = next;
   for (int i = 0; i < members.Length; i++)
   {
    var d = members[i];
    if (!d || d.State != DroidState.Idle) continue;
    d.transform.position += delta;
    if (delta.sqrMagnitude > 1e-6f)
     d.transform.rotation = Quaternion.Slerp(d.transform.rotation, Quaternion.LookRotation(new Vector3(delta.x, 0f, delta.z)), Time.deltaTime * 4f);
   }
   if (Route.CurrentIndex != before && pauseAtWaypointSeconds > 0f)
    pauseUntil = Time.time + pauseAtWaypointSeconds;
  }
 }

 // ==========================================================================
 // 4. Repeatable Warden & Salvage Contracts
 // ==========================================================================

 public enum ContractKind { ClearDroids, GatherSalvage, SurveyArea }
 public enum ContractStatus { Available, Active, ReadyToTurnIn }

 public sealed class BermsContractSpec
 {
  public string Id { get; }
  public string Title { get; }
  public string Issuer { get; }
  public string Description { get; }
  public ContractKind Kind { get; }
  public string TargetId { get; }
  public int TargetCount { get; }
  public int RewardCredits { get; }
  public string RewardItemId { get; }
  public int RewardItemCount { get; }

  public BermsContractSpec(
   string id,
   string title,
   string issuer,
   string description,
   ContractKind kind,
   string targetId,
   int targetCount,
   int rewardCredits,
   string rewardItemId = "",
   int rewardItemCount = 0)
  {
   Id = id ?? "";
   Title = title ?? "";
   Issuer = issuer ?? "";
   Description = description ?? "";
   Kind = kind;
   TargetId = targetId ?? "";
   TargetCount = Math.Max(1, targetCount);
   RewardCredits = Math.Max(0, rewardCredits);
   RewardItemId = rewardItemId ?? "";
   RewardItemCount = Math.Max(0, rewardItemCount);
  }
 }

 /// Pure catalog of repeatable Warden & Salvage contracts for the Outer Berms.
 public static class BermsContractCatalog
 {
  static readonly BermsContractSpec[] Specs =
  {
   new BermsContractSpec(
    "contract_northgate_sweep",
    "Thin the Northgate Droids",
    "Ossa",
    "Clear 3 feral droids around Northgate scrap to keep the inner road passable.",
    ContractKind.ClearDroids,
    "northgate_scrap",
    3,
    45,
    "med_dressing",
    2),
   new BermsContractSpec(
    "contract_clear_knoll",
    "Clear Relay Knoll Gunners",
    "Ossa",
    "Knock out 2 ranged droids holding Relay Knoll so patrols can read the ridge.",
    ContractKind.ClearDroids,
    "relay_knoll",
    2,
    70,
    "medkit",
    1),
   new BermsContractSpec(
    "contract_capacitor_run",
    "Salvage Micro-Capacitors",
    "Brann",
    "Bring back 3 Micro-Capacitors from Berms wrecks for bench repairs.",
    ContractKind.GatherSalvage,
    "micro_capacitor",
    3,
    50,
    "alloy_plate",
    1),
   new BermsContractSpec(
    "contract_wash_biogel",
    "Recover Biogel from the Wash",
    "Brann",
    "Scavenge 2 Biogel Ampoules from mid-Berms wrecks or medical lockers.",
    ContractKind.GatherSalvage,
    "med_biogel",
    2,
    60,
    "scrap_alloy",
    2),
  };

  public static IReadOnlyList<BermsContractSpec> All => Specs;

  public static BermsContractSpec Find(string id)
  {
   if (string.IsNullOrEmpty(id)) return null;
   for (int i = 0; i < Specs.Length; i++)
    if (string.Equals(Specs[i].Id, id, StringComparison.Ordinal))
     return Specs[i];
   return null;
  }

  public static List<BermsContractSpec> ByIssuer(string issuer)
  {
   if (string.IsNullOrEmpty(issuer)) return new List<BermsContractSpec>(Specs);
   return Specs.Where(s => string.Equals(s.Issuer, issuer, StringComparison.OrdinalIgnoreCase)).ToList();
  }
 }

 /// Pure repeatable contract state & completion tracker.
 public sealed class BermsContractTracker
 {
  readonly Dictionary<string, int> completions = new Dictionary<string, int>(StringComparer.Ordinal);
  public BermsContractSpec Active { get; private set; }
  public int Progress { get; private set; }
  public int TotalCompleted { get; private set; }

  public ContractStatus Status
  {
   get
   {
    if (Active == null) return ContractStatus.Available;
    return Progress >= Active.TargetCount ? ContractStatus.ReadyToTurnIn : ContractStatus.Active;
   }
  }

  public bool CanTurnIn => Status == ContractStatus.ReadyToTurnIn;

  public int Completions(string contractId) =>
   !string.IsNullOrEmpty(contractId) && completions.TryGetValue(contractId, out int n) ? n : 0;

  public bool Accept(string contractId)
  {
   if (Active != null) return false;
   var spec = BermsContractCatalog.Find(contractId);
   if (spec == null) return false;
   Active = spec;
   Progress = 0;
   return true;
  }

  public bool RecordProgress(ContractKind kind, string targetId, int amount = 1)
  {
   if (Active == null || amount <= 0) return false;
   if (Active.Kind != kind) return false;
   if (!string.Equals(Active.TargetId, targetId, StringComparison.OrdinalIgnoreCase)) return false;
   int before = Progress;
   Progress = Math.Min(Active.TargetCount, Progress + amount);
   return Progress > before;
  }

  public bool Abandon()
  {
   if (Active == null) return false;
   Active = null;
   Progress = 0;
   return true;
  }

  public bool Complete(out BermsContractSpec completed)
  {
   completed = null;
   if (!CanTurnIn) return false;
   completed = Active;
   TotalCompleted++;
   completions[completed.Id] = Completions(completed.Id) + 1;
   Active = null;
   Progress = 0;
   return true;
  }
 }

 /// World-placed Warden or Salvage contract board (at Ossa's post or Brann's counter).
 /// Cycles available contracts for its issuer, tracks progress, and pays out repeatable rewards.
 [RequireComponent(typeof(WorldInteractable))]
 public class BermsContractBoard : MonoBehaviour
 {
  public string boardId = "ossa_contracts";
  [Tooltip("Optional issuer filter (\"Ossa\" or \"Brann\"); empty offers all contracts.")]
  public string issuerFilter = "Ossa";
  public string defaultPrompt = "E · Check Warden contracts";

  public BermsContractTracker Tracker { get; } = new BermsContractTracker();
  public event Action<BermsContractSpec> ContractAccepted;
  public event Action<BermsContractSpec> ContractCompleted;

  WorldInteractable interaction;
  GameSession session;
  CraftingSession crafting;
  int nextIndex;

  void Awake() => interaction = GetComponent<WorldInteractable>();

  void Start()
  {
   session = FindAnyObjectByType<GameSession>();
   crafting = session ? session.GetComponent<CraftingSession>() : FindAnyObjectByType<CraftingSession>();
   if (crafting) crafting.Collected += OnLootCollected;
   Refresh();
  }

  void OnEnable()
  {
   if (!interaction) interaction = GetComponent<WorldInteractable>();
   if (interaction) interaction.Used += Use;
   Refresh();
  }

  void OnDisable()
  {
   if (interaction) interaction.Used -= Use;
  }

  void OnDestroy()
  {
   if (crafting) crafting.Collected -= OnLootCollected;
  }

  void OnLootCollected(LootPickup pickup)
  {
   if (pickup?.taken == null || Tracker.Active == null || Tracker.Active.Kind != ContractKind.GatherSalvage) return;
   foreach (var stack in pickup.taken)
    if (Tracker.RecordProgress(ContractKind.GatherSalvage, stack.itemId, stack.quantity))
    {
     if (session) session.Notify($"Contract progress: {Tracker.Active.Title} ({Tracker.Progress}/{Tracker.Active.TargetCount})", Tracker.Active.Issuer);
     Refresh();
    }
  }

  public void NotifySiteDroidKilled(string siteSlug)
  {
   if (Tracker.RecordProgress(ContractKind.ClearDroids, siteSlug, 1))
   {
    if (session) session.Notify($"Contract progress: {Tracker.Active.Title} ({Tracker.Progress}/{Tracker.Active.TargetCount})", Tracker.Active.Issuer);
    Refresh();
   }
  }

  public void Use()
  {
   if (!session) session = FindAnyObjectByType<GameSession>();
   if (Tracker.CanTurnIn && Tracker.Complete(out var done))
   {
    if (session)
     session.Reward(done.RewardCredits, done.RewardItemId, done.RewardItemCount, done.Issuer, $"Contract complete: {done.Title}.");
    ContractCompleted?.Invoke(done);
    Refresh();
    return;
   }

   if (Tracker.Active != null)
   {
    if (session) session.Notify($"Active contract: {Tracker.Active.Title} ({Tracker.Progress}/{Tracker.Active.TargetCount}). {Tracker.Active.Description}", Tracker.Active.Issuer);
    return;
   }

   var list = BermsContractCatalog.ByIssuer(issuerFilter);
   if (list.Count == 0) return;
   var pick = list[nextIndex % list.Count];
   nextIndex = (nextIndex + 1) % list.Count;
   if (Tracker.Accept(pick.Id))
   {
    if (session)
    {
     session.Notify($"Contract accepted: {pick.Title}. {pick.Description}", pick.Issuer);
     session.Cue(CitySoundCue.Trade);
    }
    ContractAccepted?.Invoke(pick);
    Refresh();
   }
  }

  void Refresh()
  {
   if (!interaction) return;
   if (Tracker.CanTurnIn) interaction.prompt = $"E · Turn in contract: {Tracker.Active.Title}";
   else if (Tracker.Active != null) interaction.prompt = $"E · Contract status ({Tracker.Progress}/{Tracker.Active.TargetCount})";
   else interaction.prompt = defaultPrompt;
  }
 }
}
