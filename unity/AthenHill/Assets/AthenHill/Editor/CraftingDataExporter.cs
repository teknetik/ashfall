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
    items=city.items.Select((x,i)=>new{x.id,x.name,x.description,tags=x.tags??Array.Empty<string>(),x.maxStack,x.excludeFromTrade,x.buyPrice,x.sellPrice,x.startingQuantity,catalogIndex=i}).ToArray(),
    weapons=craft.weapons.Select(x=>new{x.id,x.name,baseStats=new{recoil=x.recoil},x.slots,stateSource="PlayerCombat.hasPistol"}).ToArray(),
    modifiers=craft.modifiers,stations=craft.stations,recipes=craft.recipes,lootTables=craft.lootTables,
    enemies=new[]{new{id="feral_scrap_drone",prefab="Assets/AthenHill/Prefabs/OuterBerms/FeralScrapDrone.prefab",lootTableId="loot_feral_scrap_drone"},new{id="feral_worker_droid",prefab="Assets/AthenHill/Prefabs/OuterBerms/FeralWorkerDroid.prefab",lootTableId="loot_feral_worker_droid"}},
    encounters=new[]{new{id="first_contact",spawns=new[]{"feral_scrap_drone"},tutorial=true},new{id="machine_depot",spawns=new[]{"feral_worker_droid","feral_worker_droid","feral_scrap_drone"},tutorial=true}},
    rules=new{allocation="dfs-declared-order;candidates:sellPrice,catalogIndex",statFormula="clamp(round1((base+sumAdd)*(1+sumPercent/100)),0,100)",recoilDegreesPerPoint=.05,lootSeed=1729,legacyShopRows=new[]{"water_flask","medkit","scrap_coil"}}
   };
   var recipe=craft.recipes.Single();
   var pack=new ShopModel(city.items);
   var model=new CraftingModel(craft,city.items,pack,()=>true);
   model.Acquire("droid_servo_damaged");
   var initial=new[]{new KeyValuePair<string,int>("droid_servo_damaged",1),new KeyValuePair<string,int>("scrap_alloy",2),new KeyValuePair<string,int>("nanite_residue",5)};
   if(!pack.TryApply(initial,0,out _)||!model.TryCraft(recipe.id,recipe.stationId,out _)||!model.TryFit("grip_stabilised_pistol",out _)||model.RecoilStat!=31)throw new Exception("Runtime parity vector failed");
   var random=new System.Random(1729);
   var rolls=Enumerable.Range(0,5).Select(_=>random.NextDouble()).ToArray();
   var vectors=new{schema="ward-crafting-vectors/1",source="Unity Editor: ShopModel, CraftingModel, IngredientAllocator and System.Random",cases=new object[]{
    new{id="starter-craft-fit",input=initial.Select(x=>new{itemId=x.Key,quantity=x.Value}).ToArray(),output=new{servo=pack.Quantity("droid_servo_damaged"),alloy=pack.Quantity("scrap_alloy"),residue=pack.Quantity("nanite_residue"),gripCarried=pack.Quantity("grip_stabilised_pistol"),gripSlot=model.GripSlot,recoil=model.RecoilStat,kickDegrees=model.RecoilStat*.05f}},
    new{id="seed1729-first-five-rolls",values=rolls}
   }};
   Directory.CreateDirectory(Root);
   File.WriteAllText(Root+"ward-crafting.v1.json",JsonConvert.SerializeObject(records,Json));
   File.WriteAllText(Root+"ward-crafting.v1.vectors.json",JsonConvert.SerializeObject(vectors,Json));
   AssetDatabase.Refresh();Debug.Log("CRAFT_EXPORT validated runtime data and wrote "+Root);
  }
  public static void Validate(CityCatalog city,CraftingCatalog craft)
  {
   string[] legacy={"water_flask","medkit","scrap_coil"};
   if(city.items.Length<9||!city.items.Take(3).Select(x=>x.id).SequenceEqual(legacy))throw new Exception("Legacy shop rows changed");
   if(city.items.Any(x=>x==null||!System.Text.RegularExpressions.Regex.IsMatch(x.id??"","^[a-z][a-z0-9_]*$")||x.maxStack<0)||city.items.Select(x=>x.id).Distinct().Count()!=city.items.Length)throw new Exception("Invalid or duplicate item ID/cap");
   var ids=city.items.Select(x=>x.id).ToHashSet();
   foreach(var recipe in craft.recipes)
   {
    if(!ids.Contains(recipe.outputItemId)||recipe.outputQuantity<1||!craft.stations.Any(x=>x.id==recipe.stationId)||!craft.weapons.Any(x=>x.id==recipe.requiresWeaponId))throw new Exception("Recipe reference invalid: "+recipe.id);
    if(recipe.inputs.Select(x=>x.kind+":"+x.id).Distinct().Count()!=recipe.inputs.Length)throw new Exception("Duplicate ingredient");
    foreach(var input in recipe.inputs)
     if(input.quantity<1||input.kind=="item"&&(!ids.Contains(input.id)||input.id==recipe.outputItemId)||input.kind=="tag"&&!city.items.Any(x=>x.tags!=null&&x.tags.Contains(input.id))||input.kind!="item"&&input.kind!="tag")throw new Exception("Invalid ingredient: "+input.id);
   }
   foreach(var table in craft.lootTables)foreach(var entry in table.entries)if(!ids.Contains(entry.itemId)||entry.quantity<1||entry.chance<=0||entry.chance>1||city.items.Single(x=>x.id==entry.itemId).maxStack>0&&entry.quantity>city.items.Single(x=>x.id==entry.itemId).maxStack)throw new Exception("Invalid loot entry");
   var guaranteed=new ShopModel(city.items);
   foreach(var tableId in new[]{"loot_feral_scrap_drone","loot_feral_worker_droid","loot_feral_worker_droid","loot_feral_scrap_drone"})
   {
    var table=craft.lootTables.Single(x=>x.id==tableId);
    foreach(var entry in table.entries.Where(x=>x.chance>=1))if(!guaranteed.TryApply(new[]{new KeyValuePair<string,int>(entry.itemId,entry.quantity)},0,out _))throw new Exception("Tutorial loot exceeds cap");
   }
   if(!IngredientAllocator.TryAllocate(craft.recipes.Single().inputs,city.items,guaranteed,out _))throw new Exception("Tutorial fixed drops cannot satisfy recipe");
  }
 }
}
