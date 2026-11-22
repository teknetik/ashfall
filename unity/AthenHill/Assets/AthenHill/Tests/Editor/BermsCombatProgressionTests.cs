using System.Collections.Generic;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace AthenHill.Tests
{
    /// Edit Mode tests for Outer Berms combat & ammo progression (Milestones 1 & 4):
    /// - Unarmoured torso ranged ballistic exposure (1.35x) vs field_vest vs warden_plate_carrier
    /// - Non-ranged physical damage (melee/splash) preserved via PlayerCombat.ComputePhysicalDamage
    /// - Band 2 unarmoured Ossa warning gate
    /// - Field Rifle ammo cycling (Standard / AP / EMP), graceful fallback when unstocked, AP armour pen, EMP strip
    /// - Scrap Pistol remains nano-only
    public sealed class BermsCombatProgressionTests
    {
        static CityCatalog City() => AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
        static CharacterCatalog Characters() => AssetDatabase.LoadAssetAtPath<CharacterCatalog>("Assets/AthenHill/Resources/CharacterCatalog.asset");

        static CharacterModel CreateUnarmouredCharacter()
        {
            var pack = new ShopModel(City().items);
            var character = new CharacterModel(Characters(), pack);
            if (character.Equipped(BermsBallistics.ChestArmourSlot) != null)
                Assert.That(character.TryUnequip(BermsBallistics.ChestArmourSlot, out var reason), Is.True, reason);
            return character;
        }

        [Test]
        public void ExposedUnarmouredTakesBallisticExposureMultiplierWhileMeleeStaysUnchanged()
        {
            var character = CreateUnarmouredCharacter();
            Assert.That(BermsBallistics.HasChestArmour(character), Is.False);
            Assert.That(BermsBallistics.IsExposedToRanged(character), Is.True);

            float gunBolt = BermsBallistics.GunnerBoltDamage; // 17
            float baseRes = Mathf.Clamp01(character.Stat("physicalResistance"));
            float baseArmour = Mathf.Max(0, character.Stat("armour"));
            float expectedMelee = Mathf.Max(0, gunBolt * (1f - baseRes) - baseArmour * character.Data.armourAbsorptionPerPoint);
            float meleeDmg = PlayerCombat.ComputePhysicalDamage(character, gunBolt);
            float rangedDmg = BermsBallistics.ComputeRangedPhysicalDamage(character, gunBolt);

            Assert.That(meleeDmg, Is.EqualTo(expectedMelee).Within(1e-4f));
            Assert.That(rangedDmg, Is.EqualTo(PlayerCombat.ComputePhysicalDamage(character, gunBolt * BermsBallistics.ExposedRangedMultiplier)).Within(1e-4f));
            Assert.That(rangedDmg, Is.EqualTo(meleeDmg * BermsBallistics.ExposedRangedMultiplier).Within(1e-3f), "unarmoured exposed ranged hit applies 1.35x multiplier");
            Assert.That(PlayerCombat.ComputeRangedDamage(character, gunBolt), Is.EqualTo(rangedDmg).Within(1e-4f));
            Assert.That(BermsBallistics.ComputeRangedPhysicalDamage(character, 0f), Is.Zero);
            Assert.That(BermsBallistics.ComputeRangedPhysicalDamage(character, float.NaN), Is.Zero);
        }

        [Test]
        public void FieldVestAndWardenPlateCarrierRemoveExposureAndScaleProtection()
        {
            var character = CreateUnarmouredCharacter();
            float bolt = BermsBallistics.GunnerBoltDamage;
            float exposedDmg = BermsBallistics.ComputeRangedPhysicalDamage(character, bolt);

            // Stage 1: bare-minimum chest rig (field_vest)
            Assert.That(character.TryGrantEquipped("field_vest", BermsBallistics.ChestArmourSlot, out var reason), Is.True, reason);
            Assert.That(BermsBallistics.HasChestArmour(character), Is.True);
            Assert.That(BermsBallistics.IsExposedToRanged(character), Is.False);
            float vestDmg = BermsBallistics.ComputeRangedPhysicalDamage(character, bolt);
            Assert.That(vestDmg, Is.LessThan(bolt), "field_vest removes 1.35x exposure and mitigates incoming bolt damage");
            Assert.That(vestDmg, Is.LessThan(exposedDmg * .65f), "substantial survivability step over unarmoured");

            // Stage 2: upgraded chest armour (warden_plate_carrier)
            Assert.That(character.TryUnequip(BermsBallistics.ChestArmourSlot, out reason), Is.True, reason);
            Assert.That(character.TryGrantEquipped("warden_plate_carrier", BermsBallistics.ChestArmourSlot, out reason), Is.True, reason);
            Assert.That(BermsBallistics.HasChestArmour(character), Is.True);
            float carrierDmg = BermsBallistics.ComputeRangedPhysicalDamage(character, bolt);
            Assert.That(carrierDmg, Is.LessThan(vestDmg), "warden_plate_carrier absorbs more ranged damage than field_vest");
            Assert.That(carrierDmg, Is.LessThan(exposedDmg * .5f));
        }

        [Test]
        public void BandThresholdsAndOneTimeUnarmouredBand2Warning()
        {
            var character = CreateUnarmouredCharacter();
            Assert.That(BermsBallistics.ThreatBandForX(0f), Is.EqualTo(0));
            Assert.That(BermsBallistics.ThreatBandForX(-100f), Is.EqualTo(1));
            Assert.That(BermsBallistics.ThreatBandForX(-220f), Is.EqualTo(2));
            Assert.That(BermsBallistics.ThreatBandForX(-350f), Is.EqualTo(3));

            Assert.That(BermsBallistics.ShouldWarnUnarmouredBand2(-100f, character, false), Is.False, "Band 1 does not trigger Band 2 warning");
            Assert.That(BermsBallistics.ShouldWarnUnarmouredBand2(BermsBallistics.Band2StartX, character, false), Is.True);
            Assert.That(BermsBallistics.ShouldWarnUnarmouredBand2(-200f, character, true), Is.False, "one-time warning only");

            Assert.That(character.TryGrantEquipped("field_vest", BermsBallistics.ChestArmourSlot, out var reason), Is.True, reason);
            Assert.That(BermsBallistics.ShouldWarnUnarmouredBand2(-200f, character, false), Is.False, "wearing chest armour suppresses warning");
        }

        [Test]
        public void AmmoCyclingAndGracefulFallbackBehaveDeterministically()
        {
            Assert.That(BermsBallistics.ItemIdFor(RifleAmmoKind.Standard), Is.EqualTo("ammo_rifle_standard"));
            Assert.That(BermsBallistics.ItemIdFor(RifleAmmoKind.AP), Is.EqualTo("ammo_rifle_ap"));
            Assert.That(BermsBallistics.ItemIdFor(RifleAmmoKind.EMP), Is.EqualTo("ammo_rifle_emp"));

            // Unstocked cycling steps cleanly through all three kinds
            Assert.That(BermsBallistics.NextAmmo(RifleAmmoKind.Standard), Is.EqualTo(RifleAmmoKind.AP));
            Assert.That(BermsBallistics.NextAmmo(RifleAmmoKind.AP), Is.EqualTo(RifleAmmoKind.EMP));
            Assert.That(BermsBallistics.NextAmmo(RifleAmmoKind.EMP), Is.EqualTo(RifleAmmoKind.Standard));

            // Stocked cycling skips empty ammo types
            var partialStock = new Dictionary<string, int>
            {
                [BermsBallistics.AmmoStandardId] = 12,
                [BermsBallistics.AmmoApId] = 0,
                [BermsBallistics.AmmoEmpId] = 4
            };
            int Qty(string id) => partialStock.TryGetValue(id, out var q) ? q : 0;

            Assert.That(BermsBallistics.NextAmmo(RifleAmmoKind.Standard, Qty), Is.EqualTo(RifleAmmoKind.EMP));
            Assert.That(BermsBallistics.NextAmmo(RifleAmmoKind.EMP, Qty), Is.EqualTo(RifleAmmoKind.Standard));

            // ResolveActiveAmmo falls back to another stocked type if selected is empty
            var resolved = BermsBallistics.ResolveActiveAmmo(RifleAmmoKind.AP, Qty, out bool usingStock);
            Assert.That(usingStock, Is.True);
            Assert.That(resolved, Is.EqualTo(RifleAmmoKind.Standard));

            // Graceful fallback when inventory has zero ammo of all types (keeps existing rifle tests green)
            var fallback = BermsBallistics.ResolveActiveAmmo(RifleAmmoKind.AP, _ => 0, out usingStock);
            Assert.That(usingStock, Is.False);
            Assert.That(fallback, Is.EqualTo(RifleAmmoKind.Standard));
        }

        [Test]
        public void ApAmmoAddsArmourPenetrationAndEmpAmmoStripsDroidArmour()
        {
            float rifleDamage = 27f;
            float basePen = 4f;
            float platedArmour = 14f;

            float stdHit = WeaponBallistics.ArmourReduced(
                rifleDamage * BermsBallistics.DamageScaleFor(RifleAmmoKind.Standard),
                platedArmour,
                basePen + BermsBallistics.ArmourPenBonusFor(RifleAmmoKind.Standard));

            float apHit = WeaponBallistics.ArmourReduced(
                rifleDamage * BermsBallistics.DamageScaleFor(RifleAmmoKind.AP),
                platedArmour,
                basePen + BermsBallistics.ArmourPenBonusFor(RifleAmmoKind.AP));

            Assert.That(BermsBallistics.ArmourPenBonusFor(RifleAmmoKind.AP), Is.GreaterThan(0f));
            Assert.That(apHit, Is.GreaterThan(stdHit), "AP rounds punch through Band 2/3 droid armour");

            Assert.That(BermsBallistics.AppliesEmpStrip(RifleAmmoKind.EMP), Is.True);
            Assert.That(BermsBallistics.AppliesEmpStrip(RifleAmmoKind.Standard), Is.False);
            Assert.That(BermsBallistics.AppliesEmpStrip(RifleAmmoKind.AP), Is.False);

            float strippedArmour = BermsBallistics.ApplyEmpRoundStrip(platedArmour, RifleAmmoKind.EMP);
            Assert.That(strippedArmour, Is.LessThan(platedArmour));
            Assert.That(strippedArmour, Is.EqualTo(platedArmour * (1f - BermsBallistics.EmpRoundStripFraction)).Within(1e-4f));

            float followUpAfterEmp = WeaponBallistics.ArmourReduced(rifleDamage, strippedArmour, basePen);
            Assert.That(followUpAfterEmp, Is.GreaterThan(stdHit), "EMP armour strip increases follow-up damage");
        }

        [Test]
        public void ScrapPistolStaysNanoOnlyWhileFieldRifleUsesBallisticAmmo()
        {
            Assert.That(BermsBallistics.UsesBallisticAmmo("weapon_scrap_pistol"), Is.False);
            Assert.That(BermsBallistics.UsesBallisticAmmo("weapon_nano_carbine"), Is.False);
            Assert.That(BermsBallistics.UsesBallisticAmmo(null), Is.False);
            Assert.That(BermsBallistics.UsesBallisticAmmo("weapon_field_rifle"), Is.True);
            Assert.That(CombatHud.FormatAmmoHud(RifleAmmoKind.AP, 18), Does.Contain("AP").And.Contain("18"));
            Assert.That(CombatHud.FormatAmmoHud(RifleAmmoKind.Standard, 0), Does.Contain("STD").And.Contain("fallback"));
        }
    }
}
