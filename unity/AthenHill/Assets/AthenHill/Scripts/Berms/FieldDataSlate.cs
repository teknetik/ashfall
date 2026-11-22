using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// One lore-grounded Field Data Slate or Warden Patrol Log found in the Outer Berms.
 /// Preserves Tir's canonical lore (lore.md): corporate collapse, feral industrial AIs, goods-only Quantum Tubes,
 /// Karaveen caravans, Warden patrols, and the unresolved mystery of Tir's isolation.
 public sealed class FieldSlateEntry
 {
  public string Id { get; }
  public string Title { get; }
  public string Author { get; }
  public string LocationHint { get; }
  public string Body { get; }
  /// Optional 3-digit Warden cipher code unlocked by reading this slate (empty if none).
  public string CipherCode { get; }
  /// Optional LockedSalvageCache id that this slate's cipher opens.
  public string CipherTargetCacheId { get; }
  public int Band { get; }

  public FieldSlateEntry(string id, string title, string author, string locationHint, string body, string cipherCode = "", string cipherTargetCacheId = "", int band = 1)
  {
   Id = id ?? "";
   Title = title ?? "";
   Author = author ?? "";
   LocationHint = locationHint ?? "";
   Body = body ?? "";
   CipherCode = cipherCode ?? "";
   CipherTargetCacheId = cipherTargetCacheId ?? "";
   Band = Mathf.Clamp(band, 1, 3);
  }

  public bool HasCipher => !string.IsNullOrEmpty(CipherCode);
 }

 /// Pure catalog and flag-based collection helpers for Outer Berms Field Data Slates.
 /// Uses GameSession story flags ("slate:<id>" and "cipher:<code>") so progress saves automatically without save-schema changes.
 public static class FieldSlateCatalog
 {
  public const string FlagPrefix = "slate:";
  public const string CipherFlagPrefix = "cipher:";

  public static string FlagFor(string slateId) => string.IsNullOrEmpty(slateId) ? "" : FlagPrefix + slateId;
  public static string CipherFlagFor(string cipherCode) => string.IsNullOrEmpty(cipherCode) ? "" : CipherFlagPrefix + cipherCode;

  static readonly FieldSlateEntry[] Entries =
  {
   new FieldSlateEntry(
    "slate_northgate_watch",
    "Northgate Patrol Log 14",
    "Warden Cpl. Halv",
    "Northgate scrap · inner redoubt",
    "Worker frames at Northgate are still running old ore-sorting schedules from before the Fall. They ignore scrap heaps until you step inside their sorting lane. Stashed spare plates in the redoubt strongbox before pulling back to the West Gate. Cipher 417.",
    "417",
    "cache_northgate_cipher",
    1),
   new FieldSlateEntry(
    "slate_karaveen_manifest",
    "Karaveen Waybill · Hauler Nine",
    "Caravan Master Taro",
    "Caravan ambush · east wash",
    "Two crates of glazed cistern ware and bolt cloth bound for the south settlements that have no Quantum Tube branch. Lost our lead tractor to ranged gunners past the ambush ridge. If Warders find this wreck, leave the harness bolts—take the dressings.",
    "",
    "",
    1),
   new FieldSlateEntry(
    "slate_waystation_handoff",
    "Waystation Relay Shift Note",
    "Warden Sgt. Rell",
    "Warden waystation · mid-Berms",
    "Mid-Berms Lattice terminal dropped off the Ward link after third watch lost the relay key near the machine depot. Locked the spare supply crate before cycling back to the gate post. Anyone with the key: reset the crate latch with cipher 803.",
    "803",
    "cache_waystation_cipher",
    2),
   new FieldSlateEntry(
    "slate_tube_branch_09",
    "Cargo Conduit Log · Branch 09",
    "Pre-Fall Logistics Tech",
    "Fallen Tube pylon · southwest dunes",
    "Automated goods-shunt on Branch 09 aborted mid-transfer when orbital receivers stopped answering. Vacuum containment held for six days before the pylon sheared. Freight canisters spilled across the lee slope—refined alloy and sealed nanite stock.",
    "",
    "",
    2),
   new FieldSlateEntry(
    "slate_nanofab_scrap_audit",
    "Salvage Yield Memo",
    "Brann · Salvage Bench",
    "Scrapper camp · south road",
    "Unarmoured runners do not last two bursts against mid-Berms gunners. Pull ballistic plates and canvas webbing from the inner wrecks first; once you have a base chest rig on, hunt ceramic inserts and nanoweave from the deeper strongboxes.",
    "",
    "",
    2),
   new FieldSlateEntry(
    "slate_relay_knoll_stand",
    "Last Watch at Relay Knoll",
    "Warden Scout Dera",
    "Relay knoll · high ridge",
    "Dust front rolled in off the western rim and cut the gunners' optics in half. Used the squall to slip the line and bury our spare optics and trauma supplies in the knoll cipher box. Code 269. Hold the ridge when the wind rises.",
    "269",
    "cache_knoll_cipher",
    2),
   new FieldSlateEntry(
    "slate_aquifer_loop",
    "Automated Pump Schedule 4412",
    "Corrupted Industrial AI",
    "Aquifer derrick · north basin",
    "DIRECTIVE 4412-B: MAINTAIN EXTRACTION QUOTA. UNSCHEDULED BIOLOGICAL OBSTRUCTIONS DETECTED AT PERIMETER. DISPATCHING SENTINEL UNITS TO CLEAR CONVEYOR RIGHT-OF-WAY. AWAITING CORPORATE OVERRIDE... [NO CARRIER]",
    "",
    "",
    3),
   new FieldSlateEntry(
    "slate_orbital_silence",
    "Long-Band Telemetry Fragment",
    "Unattributed Relay Archive",
    "West fans outpost · outer rim",
    "Supply freighters are forty-two cycles overdue. No corporate acknowledgement on any band. Half the engineers think the conglomerate collapsed; the rest argue Tir was quarantined once the factory AIs went feral. Either way, no one is coming to pull us out.",
    "",
    "",
    3),
  };

  public static IReadOnlyList<FieldSlateEntry> All => Entries;

  public static FieldSlateEntry Find(string id)
  {
   if (string.IsNullOrEmpty(id)) return null;
   for (int i = 0; i < Entries.Length; i++)
    if (string.Equals(Entries[i].Id, id, StringComparison.Ordinal))
     return Entries[i];
   return null;
  }

  public static List<FieldSlateEntry> Collected(IEnumerable<string> flags)
  {
   var result = new List<FieldSlateEntry>();
   if (flags == null) return result;
   var set = flags as HashSet<string> ?? new HashSet<string>(flags, StringComparer.Ordinal);
   for (int i = 0; i < Entries.Length; i++)
    if (set.Contains(FlagFor(Entries[i].Id)))
     result.Add(Entries[i]);
   return result;
  }

  public static int CollectedCount(IEnumerable<string> flags) => Collected(flags).Count;

  public static bool HasCipher(IEnumerable<string> flags, string cipherCode)
  {
   if (flags == null || string.IsNullOrEmpty(cipherCode)) return false;
   string want = CipherFlagFor(cipherCode);
   foreach (var f in flags)
    if (string.Equals(f, want, StringComparison.Ordinal))
     return true;
   return false;
  }

  public static List<string> CollectedCiphers(IEnumerable<string> flags)
  {
   var codes = new List<string>();
   if (flags == null) return codes;
   foreach (var entry in Collected(flags))
    if (entry.HasCipher && !codes.Contains(entry.CipherCode))
     codes.Add(entry.CipherCode);
   return codes;
  }

  /// Records a slate as collected and unlocks its cipher flag if it carries one.
  public static bool Collect(string slateId, Func<string, bool> hasFlag, Action<string> setFlag, out FieldSlateEntry entry, out bool newlyCollected)
  {
   entry = Find(slateId);
   newlyCollected = false;
   if (entry == null || setFlag == null) return false;
   string slateFlag = FlagFor(entry.Id);
   newlyCollected = hasFlag == null || !hasFlag(slateFlag);
   setFlag(slateFlag);
   if (entry.HasCipher) setFlag(CipherFlagFor(entry.CipherCode));
   return true;
  }
 }

 /// World interactable Field Data Slate placed in the Outer Berms.
 /// Interacting records the slate's story flag (and any cipher code flag) on GameSession and notifies the player.
 [RequireComponent(typeof(WorldInteractable))]
 public class FieldDataSlate : MonoBehaviour
 {
  [Tooltip("Catalog id from FieldSlateCatalog (e.g. slate_northgate_watch).")]
  public string slateId = "slate_northgate_watch";
  public string unreadPrompt = "E · Read field data slate";
  public string readPrompt = "E · Re-read field data slate";
  [Header("Presentation")]
  public Light statusLight;
  public Renderer[] screenRenderers = new Renderer[0];
  [ColorUsage(false, true)] public Color unreadEmission = new Color(0.25f, 1.4f, 1.6f);
  [ColorUsage(false, true)] public Color readEmission = new Color(0.18f, 0.25f, 0.28f);

  public static readonly List<FieldDataSlate> All = new List<FieldDataSlate>();
  public FieldSlateEntry Entry => FieldSlateCatalog.Find(slateId);
  public bool Collected => session && session.HasFlag(FieldSlateCatalog.FlagFor(slateId));
  public event Action<FieldSlateEntry, bool> Read;

  WorldInteractable interaction;
  GameSession session;
  MaterialPropertyBlock block;
  static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");

  void Awake() => interaction = GetComponent<WorldInteractable>();

  void Start()
  {
   session = FindAnyObjectByType<GameSession>();
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
   if (!FieldSlateCatalog.Collect(slateId, session.HasFlag, session.SetFlag, out var entry, out bool newlyCollected)) return;
   string cipherNote = entry.HasCipher ? $" [Warden cipher {entry.CipherCode} logged]" : "";
   string prefix = newlyCollected ? $"Data slate logged: {entry.Title} ({entry.Author}). " : $"{entry.Title}: ";
   session.Notify(prefix + entry.Body + cipherNote, "Ward Notes");
   session.Cue(CitySoundCue.Trade);
   Refresh();
   Read?.Invoke(entry, newlyCollected);
  }

  void Refresh()
  {
   bool read = Collected;
   if (interaction) interaction.prompt = read ? readPrompt : unreadPrompt;
   if (statusLight) statusLight.enabled = !read;
   if (screenRenderers != null && screenRenderers.Length > 0)
   {
    block ??= new MaterialPropertyBlock();
    var c = read ? readEmission : unreadEmission;
    for (int i = 0; i < screenRenderers.Length; i++)
    {
     var r = screenRenderers[i];
     if (!r) continue;
     r.GetPropertyBlock(block);
     block.SetColor(EmissionId, c);
     r.SetPropertyBlock(block);
    }
   }
  }
 }
}
