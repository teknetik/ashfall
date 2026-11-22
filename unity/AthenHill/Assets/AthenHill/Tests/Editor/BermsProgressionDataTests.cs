using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;

namespace AthenHill.Tests
{
    /// Outer Berms M2/M3/M4 data tests (22 Nov 2026): layered armour items & recipes, Warden Relay Key drop,
    /// medical/ammo/dormant-nano items & recipes, and seeded LootBook Monte Carlo verification of the 3-5 run
    /// bare-minimum chest rig (field_vest) chase.
    public class BermsProgressionDataTests
    {
        const string Station = "station_field_fabricator";
        static CityCatalog City() => AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
        static CraftingCatalog Data() => AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
        static LootTable Table(string id) => Data().lootTables.Single(x => x.id == id);

        [Test]
        public void AllProgressionItemsAndConsumablesExist()
        {
            var city = City();
            var byId = city.items.ToDictionary(x => x.id);

            string[] requiredItems =
            {
                // M2 Stage 1 (field_vest)
                "salvaged_chest_plate", "chest_rig_harness",
                // M2 Stage 2 (warden_plate_carrier)
                "ceramic_ballistic_plate", "nanoweave_backing", "rig_harness_frame",
                // M2 Stage 3 (field_boots & field_helmet)
                "tread_strut", "reinforced_sole", "armoured_shell_casing", "optic_visor_lens",
                // M3 Waystation Relay Key
                "berms_relay_key",
                // M4 Medical
                "med_dressing", "med_biogel", "med_nanosuture", "field_bandage",
                // M4 Ammo
                "propellant_tin", "hardened_slug_core", "capacitor_filament",
                "ammo_rifle_standard", "ammo_rifle_ap", "ammo_rifle_emp",
                // M4 Dormant Nano (Band 3 TBC seeds)
                "nano_dormant_matrix", "nano_resonator_shard", "nano_targeting_core",
            };

            foreach (var id in requiredItems)
                Assert.That(byId.ContainsKey(id), Is.True, "Missing CityCatalog item: " + id);

            // Key item properties
            var key = byId["berms_relay_key"];
            Assert.That(key.HasTag("key"), Is.True);
            Assert.That(key.excludeFromTrade, Is.True);
            Assert.That(key.maxStack, Is.EqualTo(1));

            // Field Bandage consumable entry
            var bandage = city.Consumable("field_bandage");
            Assert.That(bandage, Is.Not.Null, "field_bandage consumable spec missing");
            Assert.That(bandage.restoreHealth, Is.EqualTo(30f).Within(1e-3f));

            // Dormant Nano seeds tagged nano_tech & Rare
            foreach (var id in new[] { "nano_dormant_matrix", "nano_resonator_shard", "nano_targeting_core" })
            {
                var item = byId[id];
                Assert.That(item.HasTag("nano_tech"), Is.True, id + " should have nano_tech tag");
                Assert.That(item.rarity, Is.EqualTo(ItemRarity.Rare), id + " should be Rare");
                Assert.That(item.sellPrice, Is.GreaterThanOrEqualTo(40), id + " should have high credit value");
            }
        }

        [Test]
        public void AllProgressionRecipesExistAndCraftCleanly()
        {
            var city = City();
            var data = Data();
            var byId = data.recipes.ToDictionary(r => r.id);

            string[] requiredRecipes =
            {
                "recipe_field_vest",
                "recipe_warden_plate_carrier",
                "recipe_field_boots",
                "recipe_field_helmet",
                "recipe_field_bandage",
                "recipe_medkit",
                "recipe_trauma_kit",
                "recipe_ammo_rifle_standard",
                "recipe_ammo_rifle_ap",
                "recipe_ammo_rifle_emp",
            };

            foreach (var id in requiredRecipes)
                Assert.That(byId.ContainsKey(id), Is.True, "Missing recipe: " + id);

            // Verify Stage 1 chest rig ingredients
            var vest = byId["recipe_field_vest"];
            Assert.That(vest.outputItemId, Is.EqualTo("field_vest"));
            Assert.That(vest.inputs.Single(i => i.id == "salvaged_chest_plate").quantity, Is.EqualTo(3));
            Assert.That(vest.inputs.Single(i => i.id == "chest_rig_harness").quantity, Is.EqualTo(2));
            Assert.That(vest.inputs.Single(i => i.id == "alloy_plate").quantity, Is.EqualTo(2));

            // Verify Stage 2 chest upgrade ingredients
            var carrier = byId["recipe_warden_plate_carrier"];
            Assert.That(carrier.outputItemId, Is.EqualTo("warden_plate_carrier"));
            Assert.That(carrier.inputs.Single(i => i.id == "ceramic_ballistic_plate").quantity, Is.EqualTo(3));
            Assert.That(carrier.inputs.Single(i => i.id == "nanoweave_backing").quantity, Is.EqualTo(2));
            Assert.That(carrier.inputs.Single(i => i.id == "rig_harness_frame").quantity, Is.EqualTo(1));

            // Verify Stage 3 boots & helmet deeper parts
            var boots = byId["recipe_field_boots"];
            Assert.That(boots.inputs.Any(i => i.id == "tread_strut"), Is.True);
            Assert.That(boots.inputs.Any(i => i.id == "reinforced_sole"), Is.True);
            var helmet = byId["recipe_field_helmet"];
            Assert.That(helmet.inputs.Any(i => i.id == "armoured_shell_casing"), Is.True);
            Assert.That(helmet.inputs.Any(i => i.id == "optic_visor_lens"), Is.True);

            // Craft Field Vest end-to-end via CraftingModel
            var pack = new ShopModel(city.items);
            var model = new CraftingModel(data, city.items, pack, () => true);
            Assert.That(model.Acquire("salvaged_chest_plate").Select(r => r.id), Does.Contain("recipe_field_vest"));
            Assert.That(pack.TryApply(new[]
            {
                new KeyValuePair<string, int>("salvaged_chest_plate", 3),
                new KeyValuePair<string, int>("chest_rig_harness", 2),
                new KeyValuePair<string, int>("alloy_plate", 2),
            }, 0, out var giveErr), Is.True, giveErr);
            Assert.That(model.TryCraft("recipe_field_vest", Station, out var craftErr), Is.True, craftErr);
            Assert.That(pack.Quantity("field_vest"), Is.EqualTo(1));

            // Craft Field Bandage & Standard Ammo batch
            Assert.That(model.Acquire("med_dressing").Select(r => r.id), Does.Contain("recipe_field_bandage"));
            Assert.That(model.Acquire("propellant_tin").Select(r => r.id), Does.Contain("recipe_ammo_rifle_standard"));
            Assert.That(pack.TryApply(new[]
            {
                new KeyValuePair<string, int>("med_dressing", 2),
                new KeyValuePair<string, int>("scrap_alloy", 1),
                new KeyValuePair<string, int>("propellant_tin", 1),
            }, 0, out giveErr), Is.True, giveErr);
            Assert.That(model.TryCraft("recipe_field_bandage", Station, out craftErr), Is.True, craftErr);
            Assert.That(pack.Quantity("field_bandage"), Is.EqualTo(1));
            Assert.That(model.TryCraft("recipe_ammo_rifle_standard", Station, out craftErr), Is.True, craftErr);
            Assert.That(pack.Quantity("ammo_rifle_standard"), Is.EqualTo(12));
        }

        [Test]
        public void RelayKeyIsGuaranteedUntilCollectedOnForemanAndStrongbox()
        {
            foreach (var tableId in new[] { "loot_depot_foreman", "loot_caravan_strongbox" })
            {
                var table = Table(tableId);
                var entry = table.entries.SingleOrDefault(e => e.itemId == "berms_relay_key");
                Assert.That(entry, Is.Not.Null, tableId + " missing berms_relay_key");
                Assert.That(entry.guaranteeUntilCollected, Is.True, tableId + " should guarantee key until collected");

                var book = new LootBook(20261122);
                var first = book.Roll(table);
                Assert.That(first.Any(x => x.itemId == "berms_relay_key" && x.quantity == 1), Is.True, tableId + " first roll must drop key");

                book.MarkCollected("berms_relay_key");
                for (int i = 0; i < 20; i++)
                    Assert.That(book.Roll(table).Any(x => x.itemId == "berms_relay_key"), Is.False, tableId + " should not re-drop key after collection");
            }
        }

        [Test]
        public void DormantNanoSeedsDropOnBandThreeTables()
        {
            Assert.That(Table("loot_post_sentinel").entries.Any(e => e.itemId == "nano_dormant_matrix" && e.chance > 0 && e.pityAfter > 0), Is.True);
            Assert.That(Table("loot_scrap_reaper").entries.Any(e => e.itemId == "nano_resonator_shard" && e.chance > 0 && e.pityAfter > 0), Is.True);
            var sb = Table("loot_nextlevel_strongbox");
            foreach (var id in new[] { "nano_dormant_matrix", "nano_resonator_shard", "nano_targeting_core" })
                Assert.That(sb.entries.Any(e => e.itemId == id && e.chance > 0 && e.pityAfter > 0), Is.True, "strongbox missing " + id);
        }

        [Test]
        public void FieldVestPartsAverageThreeToFiveRunsWithPityCap()
        {
            var worker = Table("loot_feral_worker_droid");
            var heap = Table("loot_scrap_heap");
            var outer = Table("loot_berms_outer");
            var wreck = Table("loot_wreck_carcass");
            var droneWreck = Table("loot_drone_wreck");

            // Confirm pityAfter == 4 on Stage 1 parts
            Assert.That(worker.entries.Single(e => e.itemId == "salvaged_chest_plate").pityAfter, Is.EqualTo(4));
            Assert.That(wreck.entries.Single(e => e.itemId == "chest_rig_harness").pityAfter, Is.EqualTo(4));

            const int trials = 200;
            int totalRuns = 0;
            int maxRuns = 0;

            for (int t = 0; t < trials; t++)
            {
                var book = new LootBook((ulong)(1000 + t * 37));
                int plates = 0, harnesses = 0, runs = 0;
                while ((plates < 3 || harnesses < 2) && runs < 30)
                {
                    runs++;
                    // One Band 1 / edge-of-Band-2 run: 2 workers, 1 scrap heap, 1 outer crate, 1 wreck, 1 drone wreck
                    LootTable[] runSources = { worker, worker, heap, outer, wreck, droneWreck };
                    foreach (var src in runSources)
                    {
                        foreach (var drop in book.Roll(src))
                        {
                            if (drop.itemId == "salvaged_chest_plate") plates += drop.quantity;
                            else if (drop.itemId == "chest_rig_harness") harnesses += drop.quantity;
                        }
                    }
                }
                totalRuns += runs;
                if (runs > maxRuns) maxRuns = runs;
            }

            double avgRuns = (double)totalRuns / trials;
            Assert.That(avgRuns, Is.InRange(3.0, 5.0), $"Expected 3-5 runs average for field_vest, got {avgRuns:F2} (max {maxRuns})");
            Assert.That(maxRuns, Is.LessThanOrEqualTo(6), $"Pity cap should prevent extreme bad luck; got max {maxRuns} runs");
        }
    }
}
