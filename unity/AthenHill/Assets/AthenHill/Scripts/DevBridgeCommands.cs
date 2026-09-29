#if UNITY_EDITOR || DEBUG
using System;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace AthenHill
{
    /// <summary>Unity-authoritative, opt-in developer operations. No arbitrary prefab, position or scene writes.</summary>
    public static class DevBridgeCommands
    {
        static readonly Regex ItemId = new Regex("^[a-z][a-z0-9_]{1,63}$", RegexOptions.CultureInvariant);
        static readonly Regex CommandId = new Regex("^[A-Za-z0-9_-]{1,64}$", RegexOptions.CultureInvariant);
        public sealed class Result
        {
            public string code, message;
            public bool success => code == null;
            public static Result Ok() => new Result();
            public static Result Fail(string code, string message) => new Result { code = code, message = message };
        }
        public static string ReadId(JObject command)
        {
            var token = command?["id"];
            var id = token?.Type == JTokenType.String ? (string)token : null;
            return id != null && CommandId.IsMatch(id) ? id : null;
        }
        static bool Integer(JObject j, string key, int max, out int value)
        {
            value = 0;
            var t = j[key];
            if (t == null || t.Type != JTokenType.Integer) return false;
            try { value = (int)t; return value >= 1 && value <= max; }
            catch (Exception e) when (e is OverflowException || e is ArgumentException) { return false; }
        }
        static bool Number(JObject j, string key, float min, float max, bool maxExclusive, out float value)
        {
            value = 0;
            var t = j[key];
            if (t == null || (t.Type != JTokenType.Float && t.Type != JTokenType.Integer)) return false;
            try { value = (float)t; return ClockMath.Finite(value) && value >= min && (maxExclusive ? value < max : value <= max); }
            catch (Exception e) when (e is OverflowException || e is ArgumentException) { return false; }
        }
        static DroidEncounter Encounter(BermsTutorial tutorial, string key, GameSession session = null)
        {
            if (!tutorial || key == null) return null;
            if (tutorial.firstContact && key == tutorial.firstContact.gameObject.name) return tutorial.firstContact;
            if (tutorial.depot && key == tutorial.depot.gameObject.name) return tutorial.depot;
            // Field-order encounters (the Depot Foreman) are available once the primer is complete.
            var orders = session ? session.GetComponent<FieldOrders>() : null;
            if (orders && tutorial.Step == BermsStep.Complete)
                foreach (var b in orders.encounters) if (b != null && b.encounter && key == b.encounter.gameObject.name) return b.encounter;
            return null;
        }
        public static Result Execute(JObject command, GameSession session, BermsTutorial tutorial = null, CityTimeOfDay clock = null)
        {
            if (ReadId(command) == null) return Result.Fail("bad_id", "Command id must be 1–64 ASCII letters, digits, _ or -.");
            var action = command["action"]?.Type == JTokenType.String ? (string)command["action"] : null;
            if (action == null || !action.StartsWith("dev.", StringComparison.Ordinal)) return Result.Fail("unknown_action", "Unknown developer operation.");
            if (!session || session.Shop == null || session.catalog == null || session.State == CityState.Boot || session.State == CityState.MainMenu)
                return Result.Fail("not_in_game", "Start a playable session before using developer controls.");
            bool adjustable = session.State == CityState.Play || session.State == CityState.Paused || session.State == CityState.Inventory || session.State == CityState.Shop;
            if (action == "dev.state") return Result.Ok();
            if (action == "dev.weather.set" || action == "dev.weather.reset") return Result.Fail("unavailable", "No weather system exists in this build.");
            if (action == "dev.item.grant" || action == "dev.item.remove" || action == "dev.credits.grant" || action == "dev.credits.remove")
            {
                if (!adjustable) return Result.Fail("invalid_state", "This adjustment needs Play, Paused, Inventory or Shop.");
                bool itemAction = action.StartsWith("dev.item.", StringComparison.Ordinal);
                var id = command["itemId"]?.Type == JTokenType.String ? (string)command["itemId"] : null;
                if (itemAction && (id == null || !ItemId.IsMatch(id) || !session.catalog.items.Any(i => i != null && i.id == id)))
                    return Result.Fail("unknown_item", "Only items in the live Unity catalogue can be adjusted.");
                int n;
                if (!Integer(command, itemAction ? "quantity" : "amount", itemAction ? 99 : 10000, out n))
                    return Result.Fail("invalid_range", "Use an integer from 1–99 items or 1–10000 credits.");
                string message;
                bool ok;
                if (action == "dev.item.grant") ok = session.Shop.Grant(id, n, 0, out message);
                else if (action == "dev.item.remove") ok = session.Shop.Remove(id, n, out message);
                else if (action == "dev.credits.grant") ok = session.Shop.Grant(null, 0, n, out message);
                else ok = session.Shop.RemoveCredits(n, out message);
                if (!ok) return Result.Fail(action.EndsWith("remove", StringComparison.Ordinal) ? "insufficient" : "overflow", message);
                session.DevChanged(message); return Result.Ok();
            }
            if (action.StartsWith("dev.time.", StringComparison.Ordinal))
            {
                if (!clock || !clock.isActiveAndEnabled) return Result.Fail("unavailable", "No active authored day/night controller.");
                if (action == "dev.time.set")
                {
                    if (!Number(command, "hour", 0, 24, true, out float hour)) return Result.Fail("invalid_range", "Hour must be finite, from 0 up to but not including 24.");
                    clock.SetHour(hour);
                }
                else if (action == "dev.time.speed")
                {
                    if (!Number(command, "speed", .1f, 120, false, out float speed)) return Result.Fail("invalid_range", "Speed must be finite and between 0.1 and 120.");
                    clock.SetSpeed(speed);
                }
                else if (action == "dev.time.pause")
                {
                    if (command["paused"]?.Type != JTokenType.Boolean) return Result.Fail("invalid_argument", "Paused must be a JSON boolean.");
                    clock.Paused = (bool)command["paused"];
                }
                else if (action == "dev.time.reset") clock.ResetToAuthoredDefault();
                else return Result.Fail("unknown_action", "Unknown developer operation.");
                return Result.Ok();
            }
            if (action == "dev.interaction.resetCityVisit")
                return session.DevResetCityVisit() ? Result.Ok() : Result.Fail("invalid_state", "City visit reset requires Play or Paused.");
            if (action == "dev.range.raise")
            {
                if (!tutorial || tutorial.targets == null) return Result.Fail("unavailable", "No authored range targets available.");
                foreach (var target in tutorial.targets) if (target) target.Raise();
                return Result.Ok();
            }
            if (action == "dev.encounter.activate" || action == "dev.encounter.reset")
            {
                if (!tutorial || session.State != CityState.Play && session.State != CityState.Paused)
                    return Result.Fail("invalid_state", "An active tutorial and Play or Paused are required.");
                var key = command["key"]?.Type == JTokenType.String ? (string)command["key"] : null;
                var encounter = Encounter(tutorial, key, session);
                if (!encounter || !encounter.isActiveAndEnabled) return Result.Fail("unknown_encounter", "Only the tutorial-authored encounters (and, after the primer, field-order encounters) are supported.");
                if (action == "dev.encounter.activate")
                {
                    if (encounter.Spawned) return Result.Fail("already_spawned", "This encounter is already active; reset it instead.");
                    if (tutorial.Step != BermsStep.Complete && (encounter == tutorial.firstContact && tutorial.Step != BermsStep.FirstContact || encounter == tutorial.depot && tutorial.Step != BermsStep.Depot))
                        return Result.Fail("tutorial_order", "Reach this encounter's tutorial step first.");
                    if (encounter.spawns == null || encounter.spawns.Length < 1 || encounter.spawns.Length > 3 || encounter.spawns.Any(s => s == null || !s.point || !s.prefab) || !encounter.player || !encounter.session)
                        return Result.Fail("invalid_authored_spawns", "Authored spawn bindings are missing or exceed the encounter cap.");
                    encounter.Activate();
                    if (encounter.Droids.Count != encounter.Total) return Result.Fail("spawn_failed", "An authored droid failed to spawn.");
                }
                else
                {
                    if (!encounter.Spawned) return Result.Fail("not_spawned", "Activate this encounter before resetting it.");
                    if (encounter.Droids.Count != encounter.Total || encounter.Droids.Any(d => !d)) return Result.Fail("spawn_failed", "Authored droids are missing.");
                    foreach (var d in encounter.Droids) d.ResetToHome(true);
                }
                return Result.Ok();
            }
            return Result.Fail("unknown_action", "Unknown developer operation.");
        }
        static object StatsObject(WeaponStats s) => WeaponStats.Ids.Select((id, i) => new { id, i }).ToDictionary(x => x.id, x => s[x.i]);
        public static object State(GameSession session)
        {
            if (!session || session.Shop == null || !session.catalog || session.State == CityState.Boot || session.State == CityState.MainMenu)
                return new { schemaVersion = 1, available = false, reason = "No playable session", utc = DateTime.UtcNow.ToString("O") };
            var tutorial = UnityEngine.Object.FindAnyObjectByType<BermsTutorial>();
            var combat = UnityEngine.Object.FindAnyObjectByType<PlayerCombat>();
            var crafting = session.GetComponent<CraftingSession>();
            var craft = crafting ? crafting.Model : null;
            var orders = session.GetComponent<FieldOrders>();
            var clock = UnityEngine.Object.FindAnyObjectByType<CityTimeOfDay>();
            var authored = tutorial ? new[] { tutorial.firstContact, tutorial.depot }.Concat(orders ? orders.encounters.Where(b => b != null).Select(b => b.encounter) : Enumerable.Empty<DroidEncounter>()).Where(e => e).Distinct().ToArray() : new DroidEncounter[0];
            var encounters = tutorial ? authored.Select(e => new {
                key = e.gameObject.name, e.displayName, spawned = e.Spawned, total = e.Total, remaining = e.Remaining, cleared = e.Cleared, e.respawnSeconds
            }).ToArray() : null;
            object clockState = clock && clock.isActiveAndEnabled ? new { available = true, hour = clock.Hour, paused = clock.Paused, speed = clock.Speed, defaultHour = clock.profile ? clock.profile.defaultHour : 0, clock.ReducedMotionSpeedLimited } : (object)new { available = false, reason = "No active authored day/night controller" };
            return new {
                schemaVersion = 1, available = true, source = "unity", utc = DateTime.UtcNow.ToString("O"), frame = Time.frameCount, unscaledTime = Time.unscaledTime,
                build = new { unity = Application.unityVersion, version = Application.version, development = Debug.isDebugBuild },
                session = new { state = session.State.ToString(), objective = session.Objective, session.visitedHill, session.boughtFlask, session.soldScrap, session.linked, spoken = session.Spoken.OrderBy(x => x).ToArray(), session.selectedDestination, credits = session.Shop.Credits, purchases = session.Shop.Purchases, sales = session.Shop.Sales },
                items = session.catalog.items.Select(i => new { i.id, i.name, i.description, i.buyPrice, i.sellPrice, i.startingQuantity, i.maxStack, i.excludeFromTrade, tags = i.tags ?? Array.Empty<string>(), quantity = session.Shop.Quantity(i.id) }).ToArray(),
                combat = combat ? new { available = true, combat.hasPistol, armed = combat.Armed, aiming = combat.Aiming, nano = combat.Nano, health = combat.Health ? combat.Health.Current : 0, maxHealth = combat.Health ? combat.Health.max : 0, combat.Downs, inBerms = combat.InBerms, weaponId = craft?.Loadout.WeaponId, baseRecoil = craft?.BaseRecoil, recoil = craft?.RecoilStat, stats = StatsObject(combat.Stats), baseStats = StatsObject(combat.BaseStats), lastKickDegrees = combat.LastKickDegrees } : (object)new { available = false },
                crafting = craft != null ? new { available = true, knownRecipes = craft.KnownRecipes.OrderBy(x => x).ToArray(), crafts = craft.Crafts, gripSlot = craft.Loadout.Fitted("grip"), slots = craft.Loadout.FittedMods.OrderBy(x => x.Key).ToDictionary(x => x.Key, x => x.Value), craftCounts = craft.CraftCounts.OrderBy(x => x.Key).ToDictionary(x => x.Key, x => x.Value), lootEvents = crafting.LootEvents, lastLoot = crafting.LastLoot, tutorialStep = orders ? orders.LegacyGripStep : null, stationId = session.ActiveStationId, fabricatorOpen = session.State == CityState.Fabricator } : (object)new { available = false, reason = "Crafting session not initialized" },
                fieldOrders = orders && orders.Ready ? new { available = true, index = orders.Progress.Index, total = orders.data.orders.Length, id = orders.Progress.Current?.id, stage = orders.Stage.ToString(), objective = orders.Objective, freePlay = orders.Progress.FreePlay } : (object)new { available = false },
                tutorial = tutorial ? new { available = true, step = tutorial.Step.ToString(), targetsDown = tutorial.TargetsDown, targetsTotal = tutorial.targets?.Length ?? 0 } : (object)new { available = false },
                encounters, enemies = (encounters == null ? new FeralDroid[0] : authored.SelectMany(e => e.Droids).Where(d => d).Distinct().ToArray()).Select(d => new { name = d.displayName, kind = d.kind.ToString(), state = d.State.ToString(), health = d.Health ? d.Health.Current : 0, maxHealth = d.Health ? d.Health.max : 0, position = new[] { d.transform.position.x, d.transform.position.y, d.transform.position.z } }).ToArray(),
                clock = clockState, weather = new { available = false, reason = "No weather system in build" }
            };
        }
    }
}
#endif
