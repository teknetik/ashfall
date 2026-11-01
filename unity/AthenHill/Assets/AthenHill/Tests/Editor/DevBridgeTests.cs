using System.Reflection;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;

namespace AthenHill.Tests
{
    public class DevBridgeTests
    {
        static readonly ItemSpec[] Items = { new ItemSpec { id = "scrap_coil", name = "Scrap Coil", startingQuantity = 1 } };
        GameObject go;
        GameSession session;
        CityCatalog catalog;
        [SetUp] public void SetUp()
        {
            go = new GameObject("Dev bridge test session");
            session = go.AddComponent<GameSession>();
            catalog = ScriptableObject.CreateInstance<CityCatalog>();
            catalog.items = Items;
            session.catalog = catalog;
            typeof(GameSession).GetProperty("Shop").GetSetMethod(true).Invoke(session, new object[] { new ShopModel(Items) });
            typeof(GameSession).GetProperty("State").GetSetMethod(true).Invoke(session, new object[] { CityState.Play });
        }
        [TearDown] public void TearDown() { UnityEngine.Object.DestroyImmediate(go); UnityEngine.Object.DestroyImmediate(catalog); }
        static JObject Command(string action, string json = "") => JObject.Parse("{\"id\":\"test-1\",\"action\":\"" + action + "\"" + json + "}");
        [Test] public void MissingOrInvalidIdsAreRejectedBeforeAnyAction()
        {
            Assert.That(DevBridgeCommands.ReadId(new JObject()), Is.Null);
            Assert.That(DevBridgeCommands.ReadId(JObject.Parse("{\"id\":12}")), Is.Null);
            Assert.That(DevBridgeCommands.ReadId(JObject.Parse("{\"id\":\"" + new string('x', 65) + "\"}")), Is.Null);
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"quantity\":2"), null).code, Is.EqualTo("not_in_game"));
            Assert.That(DevBridgeCommands.Execute(JObject.Parse("{\"action\":\"dev.item.grant\"}"), null).code, Is.EqualTo("bad_id"));
        }
        [Test] public void AbsentSessionNeverAcceptsMutations()
        {
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"itemId\":\"scrap_coil\",\"quantity\":2"), null).code, Is.EqualTo("not_in_game"));
            Assert.That(JObject.FromObject(DevBridgeCommands.State(null))["available"]?.Value<bool>(), Is.False);
            typeof(GameSession).GetProperty("State").GetSetMethod(true).Invoke(session, new object[] { CityState.MainMenu });
            Assert.That(JObject.FromObject(DevBridgeCommands.State(session))["available"]?.Value<bool>(), Is.False);
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"itemId\":\"scrap_coil\",\"quantity\":2"), session).code, Is.EqualTo("not_in_game"));
        }
        [Test] public void ModelAdjustmentsAreAtomicAndNeverCountAsTrades()
        {
            var shop = new ShopModel(Items, 25);
            Assert.That(shop.Remove("scrap_coil", 2, out _), Is.False);
            Assert.That(shop.RemoveCredits(26, out _), Is.False);
            Assert.That(shop.Remove("unknown", 1, out _), Is.False);
            Assert.That(shop.Credits, Is.EqualTo(25));
            Assert.That(shop.Quantity("scrap_coil"), Is.EqualTo(1));
            Assert.That(shop.Grant("scrap_coil", 3, 0, out _), Is.True);
            Assert.That(shop.Remove("scrap_coil", 3, out _), Is.True);
            Assert.That(shop.RemoveCredits(5, out _), Is.True);
            Assert.That(shop.Credits, Is.EqualTo(20));
            Assert.That(shop.Quantity("scrap_coil"), Is.EqualTo(1));
            Assert.That(shop.Purchases + shop.Sales, Is.Zero);
            var full = new ShopModel(Items, int.MaxValue);
            Assert.That(full.Grant(null, 0, 1, out _), Is.False);
            Assert.That(full.Credits, Is.EqualTo(int.MaxValue));
        }
        [Test] public void ItemValidationAndCityResetCannotPretendToTrade()
        {
            foreach (var quantity in new[] { "0", "-1", "100", "1.5", "\"2\"" })
                Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"itemId\":\"scrap_coil\",\"quantity\":" + quantity), session).code, Is.EqualTo("invalid_range"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"itemId\":\"draft_servo\",\"quantity\":1"), session).code, Is.EqualTo("unknown_item"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.remove", ",\"itemId\":\"scrap_coil\",\"quantity\":2"), session).code, Is.EqualTo("insufficient"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.item.grant", ",\"itemId\":\"scrap_coil\",\"quantity\":3"), session).success, Is.True);
            Assert.That(DevBridgeCommands.Execute(Command("dev.credits.remove", ",\"amount\":26"), session).code, Is.EqualTo("insufficient"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.unknown"), session).code, Is.EqualTo("unknown_action"));
            Assert.That(session.Shop.Quantity("scrap_coil"), Is.EqualTo(4));
            Assert.That(session.Shop.Credits, Is.EqualTo(25));
            session.visitedHill = session.boughtFlask = session.soldScrap = session.linked = true;
            session.Spoken.Add("mira");
            Assert.That(DevBridgeCommands.Execute(Command("dev.interaction.resetCityVisit"), session).success, Is.True);
            Assert.That(session.visitedHill || session.boughtFlask || session.soldScrap || session.linked, Is.False);
            Assert.That(session.Spoken, Is.Empty);
            Assert.That(session.Shop.Quantity("scrap_coil"), Is.EqualTo(4));
            Assert.That(session.Shop.Credits, Is.EqualTo(25));
            Assert.That(session.Shop.Purchases + session.Shop.Sales, Is.Zero);
        }
        [Test] public void ClockRangesWeatherAndEncounterOrderFailClosed()
        {
            Assert.That(DevBridgeCommands.Execute(Command("dev.weather.set"), session).code, Is.EqualTo("unavailable"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.time.set", ",\"hour\":17"), session).code, Is.EqualTo("unavailable"));
            var clock = go.AddComponent<CityTimeOfDay>();
            foreach (var hour in new[] { "-0.1", "24", "1e100" })
                Assert.That(DevBridgeCommands.Execute(Command("dev.time.set", ",\"hour\":" + hour), session, clock: clock).code, Is.EqualTo("invalid_range"));
            foreach (var speed in new[] { "0.05", "121" })
                Assert.That(DevBridgeCommands.Execute(Command("dev.time.speed", ",\"speed\":" + speed), session, clock: clock).code, Is.EqualTo("invalid_range"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.time.pause", ",\"paused\":1"), session, clock: clock).code, Is.EqualTo("invalid_argument"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.time.pause", ",\"paused\":true"), session, clock: clock).success, Is.True);
            Assert.That(DevBridgeCommands.Execute(Command("dev.time.set", ",\"hour\":17.5"), session, clock: clock).success, Is.True);
            Assert.That(clock.Hour, Is.EqualTo(17.5f));
            var tutorial = go.AddComponent<BermsTutorial>();
            var encounter = go.AddComponent<DroidEncounter>();
            tutorial.firstContact = encounter;
            Assert.That(DevBridgeCommands.Execute(Command("dev.encounter.activate", ",\"key\":\"unknown\""), session, tutorial).code, Is.EqualTo("unknown_encounter"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.encounter.reset", ",\"key\":\"Dev bridge test session\""), session, tutorial).code, Is.EqualTo("not_spawned"));
            Assert.That(DevBridgeCommands.Execute(Command("dev.encounter.activate", ",\"key\":\"Dev bridge test session\""), session, tutorial).code, Is.EqualTo("tutorial_order"));
        }
    }
}
