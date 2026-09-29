using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Editor
{
 /// One-time authoring helper for the "Scavenger's Arc" content (29 September 2026). It writes the v2 items into
 /// CityCatalog.asset and the weapon, mod, recipe, loot and label tables into WardCrafting.asset.
 /// The saved assets are authoritative afterwards: edit them in the Inspector. This helper refuses to run over
 /// v2 content unless GAMEPLAY_V2_FORCE=1 is set (authoring only; it would discard Inspector edits).
 /// Batch: -executeMethod AthenHill.Editor.GameplayV2Content.BuildData -quit
 public static class GameplayV2Content
 {
  public const string CityPath="Assets/AthenHill/Data/CityCatalog.asset";
  public const string CraftPath="Assets/AthenHill/Data/Crafting/WardCrafting.asset";
  const string Weapon="weapon_scrap_pistol",Station="station_field_fabricator";
  static bool Force=>Environment.GetEnvironmentVariable("GAMEPLAY_V2_FORCE")=="1";

  public static void BuildData()
  {
   var city=AssetDatabase.LoadAssetAtPath<CityCatalog>(CityPath);
   var craft=AssetDatabase.LoadAssetAtPath<CraftingCatalog>(CraftPath);
   if(!city||!craft)throw new Exception("CityCatalog or WardCrafting asset missing.");
   if(craft.recipes.Any(r=>r.id=="recipe_barrel_bored_alloy")&&!Force)throw new Exception("WardCrafting already holds Gameplay v2 content; edit the asset instead (GAMEPLAY_V2_FORCE=1 rebuilds it and discards edits).");
   Undo.RecordObjects(new UnityEngine.Object[]{city,craft},"Gameplay v2 content");
   city.items=Items(city.items);
   WriteCrafting(craft);
   CraftingDataExporter.Validate(city,craft);
   EditorUtility.SetDirty(city);EditorUtility.SetDirty(craft);
   AssetDatabase.SaveAssets();
   Debug.Log($"GAMEPLAY_V2_CONTENT items={city.items.Length} recipes={craft.recipes.Length} mods={craft.modifiers.Length} lootTables={craft.lootTables.Length}");
  }

  static ItemSpec Item(string id,string name,string description,ItemRarity rarity,string icon,int sell,int maxStack,bool tradeable,params string[] tags)=>
   new ItemSpec{id=id,name=name,description=description,rarity=rarity,icon=icon,sellPrice=tradeable?sell:0,buyPrice=0,maxStack=maxStack,excludeFromTrade=!tradeable,sellOnly=tradeable,tags=tags};

  /// Keeps every existing row, order and ID (the first three are Basic General's stock), updates salvage
  /// economics and presentation, then appends the new parts, components and mods.
  static ItemSpec[] Items(ItemSpec[] existing)
  {
   var list=existing.ToList();
   ItemSpec Get(string id)=>list.First(x=>x.id==id);
   Get("water_flask").icon="flask-icon";Get("medkit").icon="medkit-icon";Get("scrap_coil").icon="scrap-icon";
   foreach(var id in new[]{"water_flask","medkit","scrap_coil"})Get(id).rarity=ItemRarity.Common;
   void Salvage(string id,ItemRarity rarity,int sell,string description=null)
   {
    var x=Get(id);x.rarity=rarity;x.icon="scrap-icon";x.sellPrice=sell;x.buyPrice=0;x.excludeFromTrade=false;x.sellOnly=true;
    if(description!=null)x.description=description;
   }
   Salvage("scrap_alloy",ItemRarity.Common,1);
   Salvage("nanite_residue",ItemRarity.Common,1);
   Salvage("copper_filament",ItemRarity.Common,1);
   Salvage("droid_servo_damaged",ItemRarity.Uncommon,3);
   Salvage("micro_capacitor",ItemRarity.Uncommon,3,"An intact low-voltage capacitor from a drone's charge bus. Charge cell cores need two.");
   var grip=Get("grip_stabilised_pistol");grip.rarity=ItemRarity.Uncommon;grip.icon="pistol-icon";grip.tags=new[]{"weapon_mod","weapon_mod:grip","mark:1"};
   void Add(ItemSpec item){if(list.Any(x=>x.id==item.id))list[list.FindIndex(x=>x.id==item.id)]=item;else list.Add(item);}
   // Raw salvage
   Add(Item("optic_lens_cracked","Cracked Optic Lens","A scrap drone's targeting lens, cracked at the rim but still true at the centre.",ItemRarity.Uncommon,"scrap-icon",4,10,true,"salvage","salvage:drone","component","component:optic","tier:1"));
   Add(Item("actuator_intact","Intact Actuator","A heavy worker-droid joint actuator with its feedback loop unbroken. Rare in the Berms.",ItemRarity.Rare,"scrap-icon",0,10,false,"salvage","salvage:droid","component","component:actuator","tier:2"));
   Add(Item("lattice_shard","Quantum Lattice Shard","A sliver of quantum-stable lattice from Tir's old fabrication cores. It hums against the palm.",ItemRarity.Rare,"lattice-icon",0,10,false,"salvage","lattice","tier:2"));
   Add(Item("foreman_control_core","Foreman Control Core","The depot foreman's command core. Its stored shift schedules include full Mark II pistol schematics.",ItemRarity.Rare,"scrap-icon",0,1,false,"salvage","component","component:control","tier:2","unique"));
   // Refined components (fabricated, never traded)
   Add(Item("alloy_plate","Refined Alloy Plate","Scrap alloy pressed and nanite-bonded into a true, stress-relieved plate.",ItemRarity.Common,"scrap-icon",0,20,false,"refined","refined:alloy"));
   Add(Item("wound_coil","Wound Copper Coil","Salvaged conductor rewound on a field jig; the heart of any charge circuit.",ItemRarity.Common,"scrap-icon",0,20,false,"refined","refined:coil"));
   Add(Item("charge_cell_core","Charge Cell Core","Two capacitors and a wound coil sealed in nanite resin: a stable nano-charge store.",ItemRarity.Uncommon,"scrap-icon",0,10,false,"refined","refined:cell"));
   // Pistol mods
   Add(Item("barrel_bored_alloy","Bored Alloy Barrel","A refined-alloy barrel bored true on the fabricator. Hits harder and carries further.",ItemRarity.Uncommon,"pistol-icon",0,3,false,"weapon_mod","weapon_mod:barrel","mark:1"));
   Add(Item("cell_salvaged_capacitor","Salvaged Capacitor Cell","A larger nano cell built around a charge core. More shots before the pistol runs dry.",ItemRarity.Uncommon,"pistol-icon",0,3,false,"weapon_mod","weapon_mod:cell","mark:1"));
   Add(Item("grip_gyro_braced","Gyro-Braced Grip","A grip braced by a live actuator loop. It fights recoil and nudges your aim onto moving machines.",ItemRarity.Rare,"pistol-icon",0,3,false,"weapon_mod","weapon_mod:grip","mark:2"));
   Add(Item("barrel_lattice_focused","Lattice-Focused Barrel","A lattice shard seats behind a salvaged optic, focusing each nano pulse. Heavy hits, slightly slower cycling.",ItemRarity.Rare,"pistol-icon",0,3,false,"weapon_mod","weapon_mod:barrel","mark:2"));
   Add(Item("cell_overclocked","Overclocked Charge Cell","Twin charge cores tuned through a lattice shard: deep reserves, cheap shots, fast refill.",ItemRarity.Rare,"pistol-icon",0,3,false,"weapon_mod","weapon_mod:cell","mark:2"));
   return list.ToArray();
  }

  static CraftIngredient I(string id,int n)=>new CraftIngredient{kind="item",id=id,quantity=n};
  static CraftIngredient T(string tag,int n)=>new CraftIngredient{kind="tag",id=tag,quantity=n};
  static CraftUnlock Acquire(string id)=>new CraftUnlock{type="acquireItem",id=id};
  static CraftUnlock Order(string id)=>new CraftUnlock{type="orderStart",id=id};
  static CraftEffect Add(string stat,float v)=>new CraftEffect{stat=stat,op="add",value=v};
  static CraftEffect Pct(string stat,float v)=>new CraftEffect{stat=stat,op="percent",value=v};
  static CraftModifier Mod(string item,string slot,params CraftEffect[] effects)=>new CraftModifier{id="mod_"+item,itemId=item,slot=slot,weaponIds=new[]{Weapon},effects=effects};
  static CraftRecipe R(string id,string name,RecipeGroup group,string output,bool needsPistol,string hint,CraftUnlock[] unlocks,params CraftIngredient[] inputs)=>
   new CraftRecipe{id=id,name=name,group=group,stationId=Station,requiresWeaponId=needsPistol?Weapon:"",outputItemId=output,outputQuantity=1,inputs=inputs,unlocks=unlocks,lockedHint=hint};
  static LootEntry L(string id,int min,int max,float chance=1,int pity=0,bool untilCollected=false)=>new LootEntry{itemId=id,minQuantity=min,maxQuantity=max,chance=chance,pityAfter=pity,guaranteeUntilCollected=untilCollected};

  static void WriteCrafting(CraftingCatalog c)
  {
   var old=c.weapons.FirstOrDefault(w=>w.id==Weapon);
   c.weapons=new[]{new CraftWeapon{id=Weapon,name=old!=null?old.name:"Scrap Pistol",stats=WeaponStats.ScrapPistol,minStats=WeaponStats.DefaultMin,maxStats=WeaponStats.DefaultMax,slots=new[]{"grip","barrel","cell"}}};
   c.modifiers=new[]
   {
    new CraftModifier{id="mod_grip_stabilised",itemId="grip_stabilised_pistol",slot="grip",weaponIds=new[]{Weapon},effects=new[]{Add("recoil",-7)}},
    Mod("barrel_bored_alloy","barrel",Pct("damage",20),Add("range",10)),
    Mod("cell_salvaged_capacitor","cell",Add("nanoMax",35),Pct("nanoRegen",15)),
    Mod("grip_gyro_braced","grip",Add("recoil",-15),Add("aimAssist",1)),
    Mod("barrel_lattice_focused","barrel",Pct("damage",45),Add("range",25),Pct("fireInterval",8)),
    Mod("cell_overclocked","cell",Add("nanoMax",60),Add("nanoPerShot",-2),Pct("nanoRegen",30)),
   };
   c.stations=new[]{new CraftStation{id=Station,name="Warden Field Fabricator"}};
   const string charge="order_keep_charge",bore="order_bore_true",core="foreman_control_core";
   const string foremanHint="Ossa thinks the depot foreman's control core still holds Mark II schematics.";
   c.recipes=new[]
   {
    R("recipe_wound_coil","Wound Copper Coil",RecipeGroup.Component,"wound_coil",false,"Ossa issues this schematic with her Keep the Charge order.",new[]{Order(charge)},I("copper_filament",2),T("material:conductive",1)),
    R("recipe_charge_cell_core","Charge Cell Core",RecipeGroup.Component,"charge_cell_core",false,"Recover a micro capacitor from a scrap drone to learn this.",new[]{Order(charge),Acquire("micro_capacitor")},T("component:capacitor",2),I("wound_coil",1),T("nanite:tier1",3)),
    R("recipe_alloy_plate","Refined Alloy Plate",RecipeGroup.Component,"alloy_plate",false,"Ossa issues this schematic with her Bore It True order.",new[]{Order(bore)},I("scrap_alloy",3),T("nanite:tier1",2)),
    new CraftRecipe{id="recipe_grip_stabilised_pistol",name="Stabilised Pistol Grip",group=RecipeGroup.MarkI,stationId=Station,requiresWeaponId=Weapon,outputItemId="grip_stabilised_pistol",outputQuantity=1,
     inputs=new[]{T("component:servo",1),I("scrap_alloy",2),T("nanite:tier1",5)},unlocks=new[]{Acquire("droid_servo_damaged")},lockedHint="Salvage a worker-droid servo at the machine depot to learn this."},
    R("recipe_cell_salvaged_capacitor","Salvaged Capacitor Cell",RecipeGroup.MarkI,"cell_salvaged_capacitor",true,"Ossa issues this schematic with her Keep the Charge order.",new[]{Order(charge)},I("charge_cell_core",1),I("scrap_alloy",2)),
    R("recipe_barrel_bored_alloy","Bored Alloy Barrel",RecipeGroup.MarkI,"barrel_bored_alloy",true,"Ossa issues this schematic with her Bore It True order.",new[]{Order(bore)},I("alloy_plate",2),I("wound_coil",1)),
    R("recipe_grip_gyro_braced","Gyro-Braced Grip",RecipeGroup.MarkII,"grip_gyro_braced",true,foremanHint,new[]{Acquire(core)},I("actuator_intact",1),I("alloy_plate",2)),
    R("recipe_barrel_lattice_focused","Lattice-Focused Barrel",RecipeGroup.MarkII,"barrel_lattice_focused",true,foremanHint,new[]{Acquire(core)},I("lattice_shard",1),I("alloy_plate",2),I("wound_coil",2),T("component:optic",1)),
    R("recipe_cell_overclocked","Overclocked Charge Cell",RecipeGroup.MarkII,"cell_overclocked",true,foremanHint,new[]{Acquire(core)},I("charge_cell_core",2),I("lattice_shard",1)),
   };
   c.lootTables=new[]
   {
    new LootTable{id="loot_feral_scrap_drone",entries=new[]{L("scrap_alloy",1,2),L("nanite_residue",2,3),L("copper_filament",1,1,.6f,2),L("micro_capacitor",1,1,.45f,2),L("optic_lens_cracked",1,1,.3f,3)}},
    new LootTable{id="loot_feral_worker_droid",entries=new[]{L("droid_servo_damaged",1,1),L("scrap_alloy",1,2),L("nanite_residue",1,2),L("copper_filament",1,1,.65f,2),L("micro_capacitor",1,1,.2f,4),L("actuator_intact",1,1,.06f)}},
    new LootTable{id="loot_depot_foreman",entries=new[]{L(core,1,1,0,0,true),L("actuator_intact",1,2),L("lattice_shard",1,1,.5f,1),L("scrap_alloy",2,4),L("nanite_residue",3,5),L("micro_capacitor",1,2,.6f,1),L("droid_servo_damaged",1,1,.5f)}},
    new LootTable{id="loot_scrap_heap",entries=new[]{L("scrap_alloy",1,3,.9f,1),L("nanite_residue",1,2,.7f,2),L("copper_filament",1,2,.6f,2),L("micro_capacitor",1,1,.2f,4),L("optic_lens_cracked",1,1,.08f),L("lattice_shard",1,1,.03f)}},
   };
   c.slotLabels=new[]{new IdLabel{id="grip",label="Grip"},new IdLabel{id="barrel",label="Barrel"},new IdLabel{id="cell",label="Nano cell"}};
   c.tagLabels=new[]
   {
    new IdLabel{id="component:servo",label="Any servo"},new IdLabel{id="nanite:tier1",label="Any tier-one nanites"},
    new IdLabel{id="material:conductive",label="Any conductor (coil or filament)"},new IdLabel{id="component:capacitor",label="Any capacitor"},
    new IdLabel{id="component:optic",label="Any optic lens"},
   };
   c.statLabels=new[]
   {
    new StatLabel{stat="damage",label="Damage",format="0.#"},
    new StatLabel{stat="fireInterval",label="Fire interval",format="0.00",unit=" s",lowerIsBetter=true},
    new StatLabel{stat="range",label="Range",format="0",unit=" m"},
    new StatLabel{stat="recoil",label="Recoil",format="0.#",lowerIsBetter=true},
    new StatLabel{stat="nanoMax",label="Nano capacity",format="0"},
    new StatLabel{stat="nanoPerShot",label="Nano per shot",format="0.#",lowerIsBetter=true},
    new StatLabel{stat="nanoRegen",label="Nano refill",format="0.#",unit="/s"},
    new StatLabel{stat="aimAssist",label="Aim assist",format="0.#",unit="°"},
   };
  }
 }
}
