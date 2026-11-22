using System;
using UnityEngine;

namespace AthenHill
{
    /// Field Rifle ballistic ammunition types (Milestone 4, Outer Berms progression).
    /// Starter sidearms (Scrap Pistol) remain nano-only; upgraded ballistic weapons can cycle and consume these rounds.
    public enum RifleAmmoKind
    {
        Standard = 0,
        AP = 1,
        EMP = 2
    }

    /// Pure rules, constants, and math for Outer Berms ballistic progression (Milestones 1 & 4):
    /// - Torso-armour exposure check (HasChestArmour) and 1.35x ranged ballistic exposure penalty when unarmoured.
    /// - Threat band boundaries (Band 1 / Band 2 / Band 3) and ranged droid bolt baselines.
    /// - Weapon-specific ammo types (Standard / AP / EMP), item IDs, cycling, graceful fallback, AP bonus, and EMP strip.
    /// No Unity lifecycle so Edit Mode tests exercise every rule directly.
    public static class BermsBallistics
    {
        // ---- Torso armour & ranged ballistic exposure (Milestone 1)
        public const string ChestArmourSlot = "armour_chest";
        /// Ranged bolts deal 1.35x damage before mitigation when the player has no chest armour equipped.
        public const float ExposedRangedMultiplier = 1.35f;

        // ---- Distinct camera punch parameters for exposed vs armoured ranged hits
        public const float ExposedHitKickDegrees = 4.2f;
        public const float ExposedHitSideKickDegrees = 2.4f;
        public const float ExposedHitRecoverSeconds = .24f;
        public const float ArmouredHitKickDegrees = 1.4f;
        public const float ArmouredHitSideKickDegrees = .7f;
        public const float ArmouredHitRecoverSeconds = .14f;

        // ---- Outer Berms threat band X boundaries (west is -X) and ranged bolt tuning baselines
        public const float Band1StartX = -58.3f;
        public const float Band2StartX = -160f;
        public const float Band3StartX = -320f;
        public const float GunnerBoltDamage = 17f;
        public const float LancerBoltDamage = 30f;
        public const float PostSentinelBoltDamage = 24f;

        // ---- Field Rifle ammunition item IDs (Milestone 4)
        public const string AmmoStandardId = "ammo_rifle_standard";
        public const string AmmoApId = "ammo_rifle_ap";
        public const string AmmoEmpId = "ammo_rifle_emp";

        public static readonly RifleAmmoKind[] AllAmmoKinds =
        {
            RifleAmmoKind.Standard,
            RifleAmmoKind.AP,
            RifleAmmoKind.EMP
        };

        // ---- Per-ammo combat modifiers
        public const float StandardDamageScale = 1f;
        public const float StandardArmourPenBonus = 0f;
        public const float ApDamageScale = 1.05f;
        public const float ApArmourPenBonus = 10f;
        public const float EmpDamageScale = .9f;
        public const float EmpArmourPenBonus = 2f;
        public const float EmpRoundStunSeconds = .75f;
        public const float EmpRoundStripFraction = .35f;
        public const float EmpRoundStripSeconds = 5f;

        /// True when the character has any torso armour equipped in the chest slot.
        public static bool HasChestArmour(CharacterModel character)
            => character != null && !string.IsNullOrEmpty(character.Equipped(ChestArmourSlot));

        /// True when the character has no torso armour and is exposed to ranged ballistic fire.
        public static bool IsExposedToRanged(CharacterModel character)
            => !HasChestArmour(character);

        /// Ranged ballistic hit mitigation: unarmoured torso takes ExposedRangedMultiplier (1.35x) incoming damage
        /// before standard physical mitigation; any equipped chest armour removes the exposure multiplier.
        public static float ComputeRangedPhysicalDamage(CharacterModel character, float incoming)
        {
            if (incoming <= 0 || float.IsNaN(incoming)) return 0;
            if (character == null) return incoming;
            float scaled = HasChestArmour(character) ? incoming : incoming * ExposedRangedMultiplier;
            return PlayerCombat.ComputePhysicalDamage(character, scaled);
        }

        /// Returns 0 inside Ward, 1 in Band 1 (Inner Approach), 2 in Band 2 (Mid-Berms), 3 in Band 3 (Outer Ring).
        public static int ThreatBandForX(float worldX)
        {
            if (float.IsNaN(worldX) || worldX >= Band1StartX) return 0;
            if (worldX > Band2StartX) return 1;
            if (worldX > Band3StartX) return 2;
            return 3;
        }

        /// True when Ossa should issue the one-time radio warning about entering Band 2 without chest armour.
        public static bool ShouldWarnUnarmouredBand2(float worldX, CharacterModel character, bool alreadyWarned)
            => !alreadyWarned && !float.IsNaN(worldX) && worldX <= Band2StartX && IsExposedToRanged(character);

        /// True for upgraded ballistic weapons (Field Rifle); false for nano-only starter sidearms (Scrap Pistol).
        public static bool UsesBallisticAmmo(string weaponId)
        {
            if (string.IsNullOrEmpty(weaponId)) return false;
            var id = weaponId.ToLowerInvariant();
            if (id.Contains("pistol") || id.Contains("nano")) return false;
            return id == "weapon_field_rifle" || id.Contains("rifle");
        }

        public static string ItemIdFor(RifleAmmoKind kind) => kind switch
        {
            RifleAmmoKind.AP => AmmoApId,
            RifleAmmoKind.EMP => AmmoEmpId,
            _ => AmmoStandardId
        };

        public static string DisplayName(RifleAmmoKind kind) => kind switch
        {
            RifleAmmoKind.AP => "AP Rounds",
            RifleAmmoKind.EMP => "EMP Rounds",
            _ => "Standard Slugs"
        };

        public static string ShortLabel(RifleAmmoKind kind) => kind switch
        {
            RifleAmmoKind.AP => "AP",
            RifleAmmoKind.EMP => "EMP",
            _ => "STD"
        };

        public static float DamageScaleFor(RifleAmmoKind kind) => kind switch
        {
            RifleAmmoKind.AP => ApDamageScale,
            RifleAmmoKind.EMP => EmpDamageScale,
            _ => StandardDamageScale
        };

        public static float ArmourPenBonusFor(RifleAmmoKind kind) => kind switch
        {
            RifleAmmoKind.AP => ApArmourPenBonus,
            RifleAmmoKind.EMP => EmpArmourPenBonus,
            _ => StandardArmourPenBonus
        };

        public static bool AppliesEmpStrip(RifleAmmoKind kind) => kind == RifleAmmoKind.EMP;

        /// Effective droid armour after an EMP round's armour strip is applied (unchanged for Standard/AP).
        public static float ApplyEmpRoundStrip(float baseArmour, RifleAmmoKind kind)
            => AppliesEmpStrip(kind)
                ? CombatVerbs.StrippedArmour(baseArmour, EmpRoundStripFraction)
                : Mathf.Max(0, float.IsNaN(baseArmour) ? 0 : baseArmour);

        /// Cycles to the next ammo kind. When quantityOf is supplied and at least one ammo type is stocked,
        /// skips empty ammo types; when no ammo is stocked (or quantityOf is null), cycles through all types cleanly.
        public static RifleAmmoKind NextAmmo(RifleAmmoKind current, Func<string, int> quantityOf = null)
        {
            int count = AllAmmoKinds.Length;
            int idx = (int)current;
            if (idx < 0 || idx >= count) idx = 0;

            if (quantityOf != null)
            {
                bool anyStocked = false;
                for (int i = 0; i < count; i++)
                {
                    if (quantityOf(ItemIdFor(AllAmmoKinds[i])) > 0) { anyStocked = true; break; }
                }
                if (anyStocked)
                {
                    for (int step = 1; step <= count; step++)
                    {
                        var candidate = AllAmmoKinds[(idx + step) % count];
                        if (quantityOf(ItemIdFor(candidate)) > 0) return candidate;
                    }
                }
            }
            return AllAmmoKinds[(idx + 1) % count];
        }

        /// Resolves the ammo kind to fire for a rifle shot:
        /// uses the selected kind if stocked, else falls back to the first stocked kind, else falls back gracefully
        /// to Standard without consuming stock (preserving compatibility with setups/tests that do not stock ammo).
        public static RifleAmmoKind ResolveActiveAmmo(RifleAmmoKind selected, Func<string, int> quantityOf, out bool usingStock)
        {
            if (quantityOf == null)
            {
                usingStock = false;
                return RifleAmmoKind.Standard;
            }
            if (quantityOf(ItemIdFor(selected)) > 0)
            {
                usingStock = true;
                return selected;
            }
            for (int i = 0; i < AllAmmoKinds.Length; i++)
            {
                var candidate = AllAmmoKinds[i];
                if (quantityOf(ItemIdFor(candidate)) > 0)
                {
                    usingStock = true;
                    return candidate;
                }
            }
            usingStock = false;
            return RifleAmmoKind.Standard;
        }
    }
}
