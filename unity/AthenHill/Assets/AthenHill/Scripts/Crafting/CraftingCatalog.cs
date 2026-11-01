using System;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CraftIngredient {public string kind,id;public int quantity;}
 [Serializable] public class CraftUnlock {public string type,id;}
 [Serializable] public class CraftRecipe
 {
  public string id,name,stationId,requiresWeaponId,outputItemId;
  public CraftIngredient[] inputs;
  public int outputQuantity=1;
  public bool knownByDefault;
  public CraftUnlock[] unlocks;
 }
 [Serializable] public class CraftEffect {public string stat,op;public float value;}
 [Serializable] public class CraftModifier {public string id,itemId,slot;public string[] weaponIds;public CraftEffect[] effects;}
 [Serializable] public class CraftWeapon {public string id,name;public float recoil=38;public string[] slots;}
 [Serializable] public class CraftStation {public string id,name;}
 [Serializable] public class LootEntry {public string itemId;public int quantity;[Range(0,1)]public float chance=1;}
 [Serializable] public class LootTable {public string id;public LootEntry[] entries;}
 [CreateAssetMenu(menuName="Athen Hill/Ward crafting catalog")]
 public class CraftingCatalog:ScriptableObject
 {
  public CraftWeapon[] weapons;
  public CraftModifier[] modifiers;
  public CraftStation[] stations;
  public CraftRecipe[] recipes;
  public LootTable[] lootTables;
 }
}
