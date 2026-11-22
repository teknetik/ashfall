using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
 /// Milestone 5: Outer Berms Exploration, Secrets & Activities Edit Mode tests.
 public class BermsExplorationTests
 {
  // ------------------------------------------------------------------ Field Data Slates
  [Test] public void FieldSlateCatalogHasSixToEightLoreGroundedSlates()
  {
   var all = FieldSlateCatalog.All;
   Assert.That(all.Count, Is.InRange(6, 8));
   Assert.That(all.Select(s => s.Id).Distinct().Count(), Is.EqualTo(all.Count), "slate ids must be unique");
   foreach (var s in all)
   {
    Assert.That(s.Title, Is.Not.Empty, s.Id);
    Assert.That(s.Author, Is.Not.Empty, s.Id);
    Assert.That(s.Body, Is.Not.Empty, s.Id);
    Assert.That(s.Band, Is.InRange(1, 3), s.Id);
    // Lore canon check: Quantum Tubes are goods-only, never passenger transport.
    Assert.That(s.Body.ToLowerInvariant(), Does.Not.Contain("passenger tube"), s.Id);
   }
   var cipherSlates = all.Where(s => s.HasCipher).ToList();
   Assert.That(cipherSlates.Count, Is.GreaterThanOrEqualTo(2), "at least two slates carry cache ciphers");
   foreach (var s in cipherSlates)
    Assert.That(s.CipherCode.Length, Is.EqualTo(3), $"{s.Id} cipher should be 3 digits");
  }

  [Test] public void CollectingFieldSlatesRecordsFlagsAndUnlocksCiphers()
  {
   var flags = new HashSet<string>(StringComparer.Ordinal);
   Assert.That(FieldSlateCatalog.CollectedCount(flags), Is.EqualTo(0));

   Assert.That(FieldSlateCatalog.Collect("slate_northgate_watch", flags.Contains, f => flags.Add(f), out var entry, out bool newly), Is.True);
   Assert.That(newly, Is.True);
   Assert.That(entry.CipherCode, Is.EqualTo("417"));
   Assert.That(flags, Contains.Item("slate:slate_northgate_watch"));
   Assert.That(flags, Contains.Item("cipher:417"));
   Assert.That(FieldSlateCatalog.HasCipher(flags, "417"), Is.True);
   Assert.That(FieldSlateCatalog.CollectedCiphers(flags), Is.EqualTo(new[] { "417" }));
   Assert.That(FieldSlateCatalog.CollectedCount(flags), Is.EqualTo(1));

   // Re-reading the same slate succeeds but is not newly collected.
   Assert.That(FieldSlateCatalog.Collect("slate_northgate_watch", flags.Contains, f => flags.Add(f), out _, out bool secondRead), Is.True);
   Assert.That(secondRead, Is.False);

   // Unknown slate id fails cleanly.
   Assert.That(FieldSlateCatalog.Collect("slate_nonexistent", flags.Contains, f => flags.Add(f), out var missing, out _), Is.False);
   Assert.That(missing, Is.Null);
  }

  // ------------------------------------------------------------------ Locked Salvage Caches
  [Test] public void PadlockCacheRequiresShootingToUnlockThenLootsOnce()
  {
   var cache = new LockedCacheLogic("cache_pad_1", CacheLockType.Padlock);
   Assert.That(cache.Unlocked, Is.False);
   Assert.That(cache.TryUnlockByInteract(null, null, null), Is.EqualTo(CacheUnlockResult.NeedsShoot));
   Assert.That(cache.MarkLooted(), Is.False, "cannot loot while locked");

   Assert.That(cache.TryUnlockByDamage(0f), Is.EqualTo(CacheUnlockResult.NotReady));
   Assert.That(cache.TryUnlockByDamage(12f), Is.EqualTo(CacheUnlockResult.Unlocked));
   Assert.That(cache.Unlocked, Is.True);
   Assert.That(cache.TryUnlockByDamage(5f), Is.EqualTo(CacheUnlockResult.AlreadyUnlocked));

   Assert.That(cache.MarkLooted(), Is.True);
   Assert.That(cache.MarkLooted(), Is.False, "can only be looted once");
  }

  [Test] public void JunctionBoxCacheConsumesCapacitorToUnlock()
  {
   var inventory = new Dictionary<string, int>(StringComparer.Ordinal) { ["micro_capacitor"] = 0 };
   var cache = new LockedCacheLogic("cache_jbox_1", CacheLockType.JunctionBox, "micro_capacitor", 1);

   int Qty(string id) => inventory.TryGetValue(id, out int q) ? q : 0;
   bool Consume(string id, int count)
   {
    if (Qty(id) < count) return false;
    inventory[id] -= count;
    return true;
   }

   Assert.That(cache.TryUnlockByInteract(Qty, Consume, null), Is.EqualTo(CacheUnlockResult.MissingItem));
   Assert.That(cache.Unlocked, Is.False);

   inventory["micro_capacitor"] = 2;
   Assert.That(cache.TryUnlockByInteract(Qty, Consume, null), Is.EqualTo(CacheUnlockResult.Unlocked));
   Assert.That(cache.Unlocked, Is.True);
   Assert.That(inventory["micro_capacitor"], Is.EqualTo(1), "consumed exactly 1 micro_capacitor");
   Assert.That(cache.TryUnlockByInteract(Qty, Consume, null), Is.EqualTo(CacheUnlockResult.AlreadyUnlocked));
  }

  [Test] public void CipherCrateUnlocksOnlyAfterFindingMatchingSlateCode()
  {
   var flags = new HashSet<string>(StringComparer.Ordinal);
   var cache = new LockedCacheLogic("cache_waystation_cipher", CacheLockType.CipherCrate, requiredCipherCode: "803");

   Assert.That(cache.TryUnlockByInteract(null, null, flags.Contains), Is.EqualTo(CacheUnlockResult.MissingCipher));
   Assert.That(cache.Unlocked, Is.False);

   // Wrong cipher slate does not unlock it.
   FieldSlateCatalog.Collect("slate_northgate_watch", flags.Contains, f => flags.Add(f), out _, out _);
   Assert.That(cache.TryUnlockByInteract(null, null, flags.Contains), Is.EqualTo(CacheUnlockResult.MissingCipher));

   // Matching slate unlocks cipher 803.
   FieldSlateCatalog.Collect("slate_waystation_handoff", flags.Contains, f => flags.Add(f), out _, out _);
   Assert.That(cache.TryUnlockByInteract(null, null, flags.Contains), Is.EqualTo(CacheUnlockResult.Unlocked));
   Assert.That(cache.Unlocked, Is.True);

   // RestoreState supports save/load persistence.
   var restored = new LockedCacheLogic("cache_waystation_cipher", CacheLockType.CipherCrate, requiredCipherCode: "803");
   restored.RestoreState(false, true);
   Assert.That(restored.Unlocked, Is.True);
   Assert.That(restored.Looted, Is.True);
  }

  // ------------------------------------------------------------------ Survey Cairn
  [Test] public void SurveyCairnMarksSitesWithinSurveyRadiusAndRespectsPrimer()
  {
   var places = new[]
   {
    new MapPlace(WorldMapDiscovery.DepotId, "Machine depot", MapPlaceKind.Site, -110f, -20f, 55f),
    new MapPlace("site:northgate_scrap", "Northgate scrap", MapPlaceKind.Site, -132f, 64f, 55f),
    new MapPlace("site:caravan_ambush", "Caravan ambush", MapPlaceKind.Site, -205f, 74f, 55f),
    new MapPlace("site:west_outpost", "West fans outpost", MapPlaceKind.Site, -486f, -24f, 55f),
    new MapPlace("city:salvage", "Salvage", MapPlaceKind.Shop, -19.8f, 18f, 0f),
   };

   var cairnPos = new Vector3(-160f, 22f, 40f); // elevated ridge
   var discovery = new WorldMapDiscovery();

   // Before primer reaches Depot, Depot is excluded while other sites inside 140 m are marked.
   var first = SurveyCairnLogic.Survey(cairnPos, 140f, places, discovery, id => WorldMapDiscovery.PrimerAllows(id, BermsStep.FirstContact));
   Assert.That(first.Select(p => p.id), Is.EquivalentTo(new[] { "site:northgate_scrap", "site:caravan_ambush" }));
   Assert.That(discovery.Has("site:west_outpost"), Is.False, "outside 140 m radius");
   Assert.That(discovery.Has(WorldMapDiscovery.DepotId), Is.False, "blocked by primer step");

   // Once primer is complete, re-surveying picks up only the newly allowed Depot.
   var second = SurveyCairnLogic.Survey(cairnPos, 140f, places, discovery, id => WorldMapDiscovery.PrimerAllows(id, BermsStep.Complete));
   Assert.That(second.Select(p => p.id), Is.EqualTo(new[] { WorldMapDiscovery.DepotId }));
   Assert.That(SurveyCairnLogic.Survey(cairnPos, 140f, places, discovery), Is.Empty, "already surveyed");
  }

  // ------------------------------------------------------------------ Distress Signal Hunts
  [Test] public void DistressSignalBearingAndPingRangeAreAccurate()
  {
   var origin = Vector3.zero;
   Assert.That(DistressSignalMath.BearingDegrees(origin, new Vector3(0f, 0f, 50f)), Is.EqualTo(0f).Within(0.01f));
   Assert.That(DistressSignalMath.BearingDegrees(origin, new Vector3(50f, 0f, 0f)), Is.EqualTo(90f).Within(0.01f));
   Assert.That(DistressSignalMath.BearingDegrees(origin, new Vector3(0f, 0f, -50f)), Is.EqualTo(180f).Within(0.01f));
   Assert.That(DistressSignalMath.BearingDegrees(origin, new Vector3(-50f, 0f, 0f)), Is.EqualTo(270f).Within(0.01f));

   Assert.That(DistressSignalMath.CardinalDirection(0f), Is.EqualTo("N"));
   Assert.That(DistressSignalMath.CardinalDirection(45f), Is.EqualTo("NE"));
   Assert.That(DistressSignalMath.CardinalDirection(225f), Is.EqualTo("SW"));
   Assert.That(DistressSignalMath.CardinalDirection(355f), Is.EqualTo("N"));

   var target = new Vector3(-100f, 0f, 0f);
   Assert.That(DistressSignalMath.ShouldPing(new Vector3(-250f, 0f, 0f), target, 115f, 14f, false), Is.False, "too far");
   Assert.That(DistressSignalMath.ShouldPing(new Vector3(-150f, 0f, 0f), target, 115f, 14f, false), Is.True, "in ping band");
   Assert.That(DistressSignalMath.ShouldPing(new Vector3(-105f, 0f, 0f), target, 115f, 14f, false), Is.False, "already arrived");
   Assert.That(DistressSignalMath.ShouldPing(new Vector3(-150f, 0f, 0f), target, 115f, 14f, true), Is.False, "already resolved");

   string ping = DistressSignalMath.FormatPing("Downed Warden Pod", origin, target);
   Assert.That(ping, Does.Contain("Downed Warden Pod"));
   Assert.That(ping, Does.Contain("100 m"));
   Assert.That(ping, Does.Contain("W"));
  }

  // ------------------------------------------------------------------ Wake-Up Salvage Node
  [Test] public void WakeUpSalvageSelectsClosestDormantAliveDroidsWithinRadius()
  {
   var origin = new Vector3(-200f, 0f, 50f);
   var droids = new[]
   {
    (new Vector3(-205f, 0f, 50f), true, false),  // 0: 5 m, alive, dormant -> pick #1
    (new Vector3(-202f, 0f, 50f), false, false), // 1: 2 m, dead -> skip
    (new Vector3(-203f, 0f, 50f), true, true),   // 2: 3 m, already engaged -> skip
    (new Vector3(-218f, 0f, 50f), true, false),  // 3: 18 m, alive, dormant -> pick #3
    (new Vector3(-210f, 0f, 50f), true, false),  // 4: 10 m, alive, dormant -> pick #2
    (new Vector3(-240f, 0f, 50f), true, false),  // 5: 40 m, out of radius -> skip
   };

   var woken = WakeUpSalvageLogic.SelectDormantToWake(origin, 28f, droids, 2);
   Assert.That(woken, Is.EqualTo(new[] { 0, 4 }), "picks the 2 closest dormant alive droids");

   var allEligible = WakeUpSalvageLogic.SelectDormantToWake(origin, 28f, droids, 5);
   Assert.That(allEligible, Is.EqualTo(new[] { 0, 4, 3 }));
  }

  // ------------------------------------------------------------------ Roaming Feral Patrol
  [Test] public void RoamingPatrolLoopsAndPingPongsWaypoints()
  {
   var pts = new[] { new Vector3(0f, 0f, 0f), new Vector3(10f, 0f, 0f), new Vector3(10f, 0f, 10f) };

   // Loop mode
   var loopRoute = new PatrolRouteLogic(pts, loop: true, arrivalRadius: 1f);
   var pos = new Vector3(0f, 0f, 0f);
   Assert.That(loopRoute.Advance(pos), Is.True);
   Assert.That(loopRoute.CurrentIndex, Is.EqualTo(1));

   pos = loopRoute.StepTowards(pos, 5f, 1f);
   Assert.That(pos.x, Is.EqualTo(5f).Within(0.01f));
   Assert.That(loopRoute.CurrentIndex, Is.EqualTo(1));

   pos = loopRoute.StepTowards(pos, 5f, 1f); // arrives at (10,0,0) -> advances to 2
   Assert.That(loopRoute.CurrentIndex, Is.EqualTo(2));

   pos = loopRoute.StepTowards(pos, 10f, 1f); // arrives at (10,0,10) -> wraps to 0
   Assert.That(loopRoute.CurrentIndex, Is.EqualTo(0));

   // Ping-pong mode
   var bounce = new PatrolRouteLogic(pts, loop: false, arrivalRadius: 1f);
   bounce.Advance(pts[0]); // -> 1
   bounce.Advance(pts[1]); // -> 2
   Assert.That(bounce.CurrentIndex, Is.EqualTo(2));
   bounce.Advance(pts[2]); // reverses -> 1
   Assert.That(bounce.CurrentIndex, Is.EqualTo(1));
   bounce.Advance(pts[1]); // -> 0
   Assert.That(bounce.CurrentIndex, Is.EqualTo(0));
  }

  // ------------------------------------------------------------------ Repeatable Contracts
  [Test] public void RepeatableContractsTrackProgressAndAllowReacceptance()
  {
   Assert.That(BermsContractCatalog.ByIssuer("Ossa").Count, Is.GreaterThanOrEqualTo(2));
   Assert.That(BermsContractCatalog.ByIssuer("Brann").Count, Is.GreaterThanOrEqualTo(2));

   var tracker = new BermsContractTracker();
   Assert.That(tracker.Status, Is.EqualTo(ContractStatus.Available));
   Assert.That(tracker.Accept("contract_clear_knoll"), Is.True);
   Assert.That(tracker.Status, Is.EqualTo(ContractStatus.Active));
   Assert.That(tracker.Accept("contract_capacitor_run"), Is.False, "only one active contract at a time");

   // Wrong kind or target does not count.
   Assert.That(tracker.RecordProgress(ContractKind.GatherSalvage, "relay_knoll", 1), Is.False);
   Assert.That(tracker.RecordProgress(ContractKind.ClearDroids, "northgate_scrap", 1), Is.False);

   // Matching kills increment and clamp at TargetCount (2).
   Assert.That(tracker.RecordProgress(ContractKind.ClearDroids, "relay_knoll", 1), Is.True);
   Assert.That(tracker.CanTurnIn, Is.False);
   Assert.That(tracker.RecordProgress(ContractKind.ClearDroids, "relay_knoll", 5), Is.True);
   Assert.That(tracker.Progress, Is.EqualTo(2));
   Assert.That(tracker.CanTurnIn, Is.True);
   Assert.That(tracker.Status, Is.EqualTo(ContractStatus.ReadyToTurnIn));

   // Complete clears active and records completion.
   Assert.That(tracker.Complete(out var done), Is.True);
   Assert.That(done.Id, Is.EqualTo("contract_clear_knoll"));
   Assert.That(tracker.TotalCompleted, Is.EqualTo(1));
   Assert.That(tracker.Completions("contract_clear_knoll"), Is.EqualTo(1));
   Assert.That(tracker.Status, Is.EqualTo(ContractStatus.Available));

   // Repeatable: can accept the same contract again and abandon cleanly.
   Assert.That(tracker.Accept("contract_clear_knoll"), Is.True);
   Assert.That(tracker.Abandon(), Is.True);
   Assert.That(tracker.Status, Is.EqualTo(ContractStatus.Available));
  }
 }
}
