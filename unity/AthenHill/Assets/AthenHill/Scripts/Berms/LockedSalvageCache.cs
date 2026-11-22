using System;
using System.Collections.Generic;
using UnityEngine;
namespace AthenHill
{
 public enum CacheLockType { Padlock, JunctionBox, CipherCrate }
 public enum CacheUnlockResult { Unlocked, AlreadyUnlocked, NeedsShoot, MissingItem, MissingCipher, NotReady }

 /// Pure state machine for interactive locked salvage caches in the Outer Berms.
 /// Supports 3 lightweight lock types:
 ///  - Padlock: shoot the lock off (broken via Health / damage).
 ///  - JunctionBox: spend a capacitor/cell item to power the latch open.
 ///  - CipherCrate: requires the matching 3-digit Warden cipher flag from a Field Data Slate.
 public sealed class LockedCacheLogic
 {
  public const string OpenFlagPrefix = "cache_open:";
  public const string LootedFlagPrefix = "cache_looted:";

  public string CacheId { get; }
  public CacheLockType LockType { get; }
  public string RequiredItemId { get; }
  public int RequiredItemCount { get; }
  public string RequiredCipherCode { get; }
  public bool Unlocked { get; private set; }
  public bool Looted { get; private set; }

  public string OpenFlag => string.IsNullOrEmpty(CacheId) ? "" : OpenFlagPrefix + CacheId;
  public string LootedFlag => string.IsNullOrEmpty(CacheId) ? "" : LootedFlagPrefix + CacheId;

  public LockedCacheLogic(string cacheId, CacheLockType lockType, string requiredItemId = "micro_capacitor", int requiredItemCount = 1, string requiredCipherCode = "")
  {
   CacheId = cacheId ?? "";
   LockType = lockType;
   RequiredItemId = string.IsNullOrEmpty(requiredItemId) ? "micro_capacitor" : requiredItemId;
   RequiredItemCount = Math.Max(1, requiredItemCount);
   RequiredCipherCode = requiredCipherCode ?? "";
  }

  public void RestoreState(bool unlocked, bool looted)
  {
   Unlocked = unlocked || looted;
   Looted = looted;
  }

  /// Padlock caches break open when shot / damaged.
  public CacheUnlockResult TryUnlockByDamage(float damage)
  {
   if (Unlocked) return CacheUnlockResult.AlreadyUnlocked;
   if (LockType != CacheLockType.Padlock || damage <= 0f) return CacheUnlockResult.NotReady;
   Unlocked = true;
   return CacheUnlockResult.Unlocked;
  }

  /// Interacting with E attempts to power a JunctionBox or enter a CipherCrate code.
  /// Padlock caches return NeedsShoot until broken by weapon fire.
  public CacheUnlockResult TryUnlockByInteract(Func<string, int> itemQuantity, Func<string, int, bool> consumeItem, Func<string, bool> hasFlag)
  {
   if (Unlocked) return CacheUnlockResult.AlreadyUnlocked;
   switch (LockType)
   {
    case CacheLockType.Padlock:
     return CacheUnlockResult.NeedsShoot;
    case CacheLockType.JunctionBox:
     if (itemQuantity == null || consumeItem == null) return CacheUnlockResult.NotReady;
     if (itemQuantity(RequiredItemId) < RequiredItemCount) return CacheUnlockResult.MissingItem;
     if (!consumeItem(RequiredItemId, RequiredItemCount)) return CacheUnlockResult.MissingItem;
     Unlocked = true;
     return CacheUnlockResult.Unlocked;
    case CacheLockType.CipherCrate:
     if (hasFlag == null || string.IsNullOrEmpty(RequiredCipherCode)) return CacheUnlockResult.MissingCipher;
     if (!hasFlag(FieldSlateCatalog.CipherFlagFor(RequiredCipherCode))) return CacheUnlockResult.MissingCipher;
     Unlocked = true;
     return CacheUnlockResult.Unlocked;
    default:
     return CacheUnlockResult.NotReady;
   }
  }

  /// Marks the cache looted once it is unlocked. Returns true on the first loot only.
  public bool MarkLooted()
  {
   if (!Unlocked || Looted) return false;
   Looted = true;
   return true;
  }
 }

 /// World-placed locked salvage cache in the Outer Berms.
 /// Plugs into WorldInteractable, Health (for Padlock shoot-to-break), ShopModel (for JunctionBox),
 /// GameSession.Flags (for CipherCrate & persistence), and CraftingSession.SearchHeap (for loot rolls).
 [RequireComponent(typeof(WorldInteractable))]
 public class LockedSalvageCache : MonoBehaviour
 {
  public string cacheId = "cache_berms_01";
  public string displayName = "Locked supply crate";
  public CacheLockType lockType = CacheLockType.Padlock;
  public string lootTableId = "loot_strongbox";
  [Tooltip("Item consumed to power open a JunctionBox cache (e.g. micro_capacitor or charge_cell_core).")]
  public string requiredItemId = "micro_capacitor";
  [Min(1)] public int requiredItemCount = 1;
  [Tooltip("3-digit Warden cipher code required for a CipherCrate (unlocked by reading the matching FieldDataSlate).")]
  public string requiredCipherCode = "417";
  [Header("References")]
  [Tooltip("Optional Health component on the padlock collider; breaking it unlocks Padlock caches.")]
  public Health padlockHealth;
  [Tooltip("Optional lock mesh/indicator hidden once unlocked.")]
  public GameObject lockVisual;
  public Light statusLight;

  public static readonly List<LockedSalvageCache> All = new List<LockedSalvageCache>();
  public LockedCacheLogic Logic { get; private set; }
  public bool Unlocked => Logic != null && Logic.Unlocked;
  public bool Looted => Logic != null && Logic.Looted;
  public event Action<LockedSalvageCache> UnlockedEvent;
  public event Action<LockedSalvageCache> LootedEvent;

  WorldInteractable interaction;
  GameSession session;
  CraftingSession crafting;

  void Awake()
  {
   interaction = GetComponent<WorldInteractable>();
   Logic = new LockedCacheLogic(cacheId, lockType, requiredItemId, requiredItemCount, requiredCipherCode);
   if (lockType == CacheLockType.Padlock && !padlockHealth)
    padlockHealth = GetComponent<Health>() ?? GetComponentInChildren<Health>();
  }

  void Start()
  {
   session = FindAnyObjectByType<GameSession>();
   crafting = session ? session.GetComponent<CraftingSession>() : FindAnyObjectByType<CraftingSession>();
   if (session && Logic != null)
    Logic.RestoreState(session.HasFlag(Logic.OpenFlag), session.HasFlag(Logic.LootedFlag));
   if (padlockHealth && Unlocked) padlockHealth.enabled = false;
   Refresh();
  }

  void OnEnable()
  {
   if (!interaction) interaction = GetComponent<WorldInteractable>();
   if (interaction) interaction.Used += Use;
   if (padlockHealth) padlockHealth.Died += OnPadlockBroken;
   All.Add(this);
   Refresh();
  }

  void OnDisable()
  {
   if (interaction) interaction.Used -= Use;
   if (padlockHealth) padlockHealth.Died -= OnPadlockBroken;
   All.Remove(this);
  }

  void OnPadlockBroken()
  {
   if (Logic == null || Logic.TryUnlockByDamage(1f) != CacheUnlockResult.Unlocked) return;
   if (session && !string.IsNullOrEmpty(Logic.OpenFlag)) session.SetFlag(Logic.OpenFlag);
   if (session)
   {
    session.Notify($"{displayName} padlock shot off. Press E to loot.", "Salvage");
    session.Cue(CitySoundCue.Trade);
   }
   Refresh();
   UnlockedEvent?.Invoke(this);
  }

  public void Use()
  {
   if (Logic == null) return;
   if (!session) session = FindAnyObjectByType<GameSession>();
   if (!crafting && session) crafting = session.GetComponent<CraftingSession>();
   if (Looted)
   {
    if (session) session.Notify($"{displayName} is already empty.", "Salvage");
    return;
   }

   if (!Unlocked)
   {
    var result = Logic.TryUnlockByInteract(
     id => session && session.Shop != null ? session.Shop.Quantity(id) : 0,
     (id, count) => session && session.Shop != null && session.Shop.TryApply(new[] { new KeyValuePair<string, int>(id, -count) }, 0, out _),
     flag => session && session.HasFlag(flag));

    switch (result)
    {
     case CacheUnlockResult.NeedsShoot:
      if (session) { session.Notify($"{displayName} is held by a rusted padlock. Shoot the lock off.", "Salvage"); session.Cue(CitySoundCue.Unavailable); }
      return;
     case CacheUnlockResult.MissingItem:
      string itemName = session && session.Shop != null && session.Shop.Spec(Logic.RequiredItemId) != null
       ? session.Shop.Spec(Logic.RequiredItemId).name
       : Logic.RequiredItemId;
      if (session) { session.Notify($"Dead junction box. Requires {Logic.RequiredItemCount} × {itemName} to power the latch.", "Salvage"); session.Cue(CitySoundCue.Unavailable); }
      return;
     case CacheUnlockResult.MissingCipher:
      if (session) { session.Notify($"Warden cipher lock. Find the matching 3-digit code on a nearby patrol slate.", "Salvage"); session.Cue(CitySoundCue.Unavailable); }
      return;
     case CacheUnlockResult.Unlocked:
      if (session && !string.IsNullOrEmpty(Logic.OpenFlag)) session.SetFlag(Logic.OpenFlag);
      UnlockedEvent?.Invoke(this);
      break;
     case CacheUnlockResult.NotReady:
      return;
    }
   }

   if (Logic.MarkLooted())
   {
    if (session && !string.IsNullOrEmpty(Logic.LootedFlag)) session.SetFlag(Logic.LootedFlag);
    if (crafting) crafting.SearchHeap(lootTableId, transform.position, transform.parent, displayName);
    if (session) session.Cue(CitySoundCue.Trade);
    Refresh();
    LootedEvent?.Invoke(this);
   }
  }

  void Refresh()
  {
   if (lockVisual) lockVisual.SetActive(!Unlocked);
   if (statusLight) statusLight.enabled = !Looted;
   if (!interaction) return;
   if (Looted) interaction.prompt = $"{displayName} (empty)";
   else if (Unlocked) interaction.prompt = $"E · Open {displayName}";
   else
   {
    interaction.prompt = lockType switch
    {
     CacheLockType.Padlock => $"Shoot padlock · {displayName}",
     CacheLockType.JunctionBox => $"E · Power junction box ({requiredItemCount}× capacitor)",
     CacheLockType.CipherCrate => $"E · Enter Warden cipher · {displayName}",
     _ => $"E · {displayName}"
    };
   }
  }
 }
}
