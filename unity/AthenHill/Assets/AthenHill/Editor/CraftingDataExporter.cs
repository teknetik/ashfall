using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Editor
{
 public static class CraftingDataExporter
 {
  const string Root="Assets/AthenHill/Data/Crafting/Export/";
  static readonly JsonSerializerSettings Json=new JsonSerializerSettings{Formatting=Formatting.Indented,ContractResolver=new Newtonsoft.Json.Serialization.CamelCasePropertyNamesContractResolver()};
  public static void Export()
  {
   var city=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   var craft=AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
   if(!city||!craft)throw new Exception("Missing crafting source assets");
   Validate(city,craft);
   var records=new
   {
    schema="ward-crafting/1",
    generated=new{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,sources=new[]{"Assets/AthenHill/Data/CityCatalog.asset","Assets/AthenHill/Data/Crafting/WardCrafting.asset"}},
    // Additive to schema 1: rarity/sellOnly/icon on items, all base stats and bounds on weapons, recipe groups,
    // loot min/max quantity, bad-luck protection and first-collection guarantees. "quantity" mirrors minQuantity.
    items=city.items.Select((x,i)=>new{x.id,x.name,x.description,tags=x.tags??Array.Empty<string>(),x.maxStack,x.excludeFromTrade,x.buyPrice,x.sellPrice,x.startingQuantity,rarity=x.rarity.ToString(),x.sellOnly,x.icon,catalogIndex=i}).ToArray(),
    weapons=craft.weapons.Select(x=>new{x.id,x.name,baseStats=Stats(x.stats),minStats=Stats(x.minStats),maxStats=Stats(x.maxStats),x.slots,stateSource="PlayerCombat.hasPistol"}).ToArray(),
    modifiers=craft.modifiers,stations=craft.stations,
    recipes=craft.recipes.Select(x=>new{x.id,x.name,group=x.group.ToString(),x.stationId,x.requiresWeaponId,x.outputItemId,x.outputQuantity,x.inputs,x.knownByDefault,x.unlocks,x.lockedHint}).ToArray(),
    lootTables=craft.lootTables.Select(t=>new{t.id,entries=t.entries.Select(e=>new{e.itemId,quantity=e.minQuantity,e.minQuantity,maxQuantity=Math.Max(e.minQuantity,e.maxQuantity),e.chance,e.pityAfter,e.guaranteeUntilCollected}).ToArray()}).ToArray(),
    enemies=new[]{new{id="feral_scrap_drone",prefab="Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab",lootTableId="loot_feral_scrap_drone"},new{id="feral_worker_droid",prefab="Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab",lootTableId="loot_feral_worker_droid"},new{id="depot_foreman",prefab="Assets/AthenHill/Prefabs/OuterBerms/FeralDepotForeman.prefab",lootTableId="loot_depot_foreman"}},
    encounters=new object[]{new{id="first_contact",spawns=new[]{"feral_scrap_drone"},tutorial=true},new{id="machine_depot",spawns=new[]{"feral_worker_droid","feral_worker_droid","feral_scrap_drone"},tutorial=true},new{id="depot_foreman",spawns=new[]{"depot_foreman"},fieldOrder="order_depot_foreman"}},
    rules=new{allocation="dfs-declared-order;candidates:sellPrice,catalogIndex",statFormula="clamp(round3((base+sumAdd)*(1+sumPercent/100)),minStats,maxStats)",recoilDegreesPerPoint=.05,lootSeed=1729,lootRng="splitmix64; chance entries consume one roll each in declared order, ranges one more; pityAfter guarantees the next roll after N consecutive misses",legacyShopRows=new[]{"water_flask","medkit","scrap_coil"}}
   };
   var recipe=craft.recipes.Single(x=>x.id=="recipe_grip_stabilised_pistol");
   var pack=new ShopModel(city.items);
   var model=new CraftingModel(craft,city.items,pack,()=>true);
   model.Acquire("droid_servo_damaged");
   var initial=new[]{new KeyValuePair<string,int>("droid_servo_damaged",1),new KeyValuePair<string,int>("scrap_alloy",2),new KeyValuePair<string,int>("nanite_residue",5)};
   if(!pack.TryApply(initial,0,out _)||!model.TryCraft(recipe.id,recipe.stationId,out _)||!model.TryFit("grip_stabilised_pistol",out _)||model.RecoilStat!=31)throw new Exception("Runtime parity vector failed");
   var random=new LootRng(1729);
   var rolls=Enumerable.Range(0,5).Select(_=>random.NextDouble()).ToArray();
   var vectors=new{schema="ward-crafting-vectors/2",source="Unity Editor: ShopModel, CraftingModel, IngredientAllocator and LootRng (SplitMix64)",cases=new object[]{
    new{id="starter-craft-fit",input=initial.Select(x=>new{itemId=x.Key,quantity=x.Value}).ToArray(),output=new{servo=pack.Quantity("droid_servo_damaged"),alloy=pack.Quantity("scrap_alloy"),residue=pack.Quantity("nanite_residue"),gripCarried=pack.Quantity("grip_stabilised_pistol"),gripSlot=model.Loadout.Fitted("grip"),recoil=model.RecoilStat,kickDegrees=model.RecoilStat*.05f}},
    new{id="splitmix64-seed1729-first-five-rolls",values=rolls},
    new{id="loot_feral_scrap_drone-seed1729-first-three-rolls",values=Enumerable.Range(0,1).SelectMany(_=>{var book=new LootBook(1729);var t=craft.lootTables.Single(x=>x.id=="loot_feral_scrap_drone");return Enumerable.Range(0,3).Select(i=>book.Roll(t).Select(s=>new{s.itemId,s.quantity}).ToArray());}).ToArray()}
   }};
   Directory.CreateDirectory(Root);
   File.WriteAllText(Root+"ward-crafting.v1.json",JsonConvert.SerializeObject(records,Json));
   File.WriteAllText(Root+"ward-crafting.v1.vectors.json",JsonConvert.SerializeObject(vectors,Json));
   AssetDatabase.Refresh();Debug.Log("CRAFT_EXPORT validated runtime data and wrote "+Root);
  }
  static Dictionary<string,float> Stats(WeaponStats s)=>WeaponStats.Ids.Select((id,i)=>(id,i)).ToDictionary(x=>x.id,x=>s[x.i]);
  public static void Validate(CityCatalog city,CraftingCatalog craft)
  {
   string[] legacy={"water_flask","medkit","scrap_coil"};
   if(city.items.Length<9||!city.items.Take(3).Select(x=>x.id).SequenceEqual(legacy))throw new Exception("Legacy shop rows changed");
   if(city.items.Any(x=>x==null||!System.Text.RegularExpressions.Regex.IsMatch(x.id??"","^[a-z][a-z0-9_]*$")||x.maxStack<0)||city.items.Select(x=>x.id).Distinct().Count()!=city.items.Length)throw new Exception("Invalid or duplicate item ID/cap");
   var ids=city.items.Select(x=>x.id).ToHashSet();
   foreach(var recipe in craft.recipes)
   {
    if(!ids.Contains(recipe.outputItemId)||recipe.outputQuantity<1||!craft.stations.Any(x=>x.id==recipe.stationId)||!string.IsNullOrEmpty(recipe.requiresWeaponId)&&!craft.weapons.Any(x=>x.id==recipe.requiresWeaponId))throw new Exception("Recipe reference invalid: "+recipe.id);
    if(craft.recipes.Count(x=>x.id==recipe.id)!=1)throw new Exception("Duplicate recipe: "+recipe.id);
    if(recipe.unlocks!=null)foreach(var u in recipe.unlocks)if(u==null||u.type!="acquireItem"&&u.type!="orderStart"||u.type=="acquireItem"&&!ids.Contains(u.id))throw new Exception("Invalid unlock on "+recipe.id);
    if(recipe.inputs.Select(x=>x.kind+":"+x.id).Distinct().Count()!=recipe.inputs.Length)throw new Exception("Duplicate ingredient");
    foreach(var input in recipe.inputs)
     if(input.quantity<1||input.kind=="item"&&(!ids.Contains(input.id)||input.id==recipe.outputItemId)||input.kind=="tag"&&!city.items.Any(x=>x.tags!=null&&x.tags.Contains(input.id))||input.kind!="item"&&input.kind!="tag")throw new Exception("Invalid ingredient: "+input.id);
   }
   foreach(var weapon in craft.weapons)for(int i=0;i<WeaponStats.Count;i++)if(weapon.minStats[i]>weapon.maxStats[i]||weapon.stats[i]<weapon.minStats[i]||weapon.stats[i]>weapon.maxStats[i])throw new Exception($"Weapon {weapon.id} {WeaponStats.Ids[i]} outside its bounds");
   foreach(var mod in craft.modifiers)
   {
    if(!ids.Contains(mod.itemId)||mod.weaponIds==null||!mod.weaponIds.All(w=>craft.weapons.Any(x=>x.id==w&&x.slots.Contains(mod.slot))))throw new Exception("Invalid modifier: "+mod.id);
    if(mod.effects==null||mod.effects.Any(e=>WeaponStats.IndexOf(e.stat)<0||e.op!="add"&&e.op!="percent"))throw new Exception("Invalid modifier effect: "+mod.id);
   }
   foreach(var table in craft.lootTables)foreach(var entry in table.entries)
   {
    var item=ids.Contains(entry.itemId)?city.items.Single(x=>x.id==entry.itemId):null;
    int max=Math.Max(entry.minQuantity,entry.maxQuantity);
    if(item==null||entry.minQuantity<1||entry.chance<0||entry.chance>1||entry.chance==0&&!entry.guaranteeUntilCollected||entry.pityAfter<0||item.maxStack>0&&max>item.maxStack)throw new Exception($"Invalid loot entry {table.id}/{entry.itemId}");
   }
   var guaranteed=new ShopModel(city.items);
   foreach(var tableId in new[]{"loot_feral_scrap_drone","loot_feral_worker_droid","loot_feral_worker_droid","loot_feral_scrap_drone"})
   {
    var table=craft.lootTables.Single(x=>x.id==tableId);
    foreach(var entry in table.entries.Where(x=>x.chance>=1))if(!guaranteed.TryApply(new[]{new KeyValuePair<string,int>(entry.itemId,entry.minQuantity)},0,out _))throw new Exception("Tutorial loot exceeds cap");
   }
   if(!IngredientAllocator.TryAllocate(craft.recipes.Single(x=>x.id=="recipe_grip_stabilised_pistol").inputs,city.items,guaranteed,out _))throw new Exception("Tutorial fixed drops cannot satisfy recipe");
  }
 }
}
