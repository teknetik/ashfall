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

  public const string OrdersPath="Assets/AthenHill/Data/Crafting/WardFieldOrders.asset";
  /// Ossa's five field orders. Batch: -executeMethod AthenHill.Editor.GameplayV2Content.BuildOrders -quit
  public static void BuildOrders()
  {
   var set=AssetDatabase.LoadAssetAtPath<FieldOrderSet>(OrdersPath);
   if(set&&!Force)throw new Exception(OrdersPath+" exists; edit it in the Inspector (GAMEPLAY_V2_FORCE=1 rebuilds it).");
   bool created=!set;if(created)set=ScriptableObject.CreateInstance<FieldOrderSet>();
   set.orders=new[]
   {
    new FieldOrder{id="order_steady_hands",title="Steady Hands",goal=FieldOrderGoal.FitMod,targetItemId="grip_stabilised_pistol",requireTestFire=true,guidance="depot",
     brief="Salvage a worker-droid servo at the machine depot, then steady the scrap pistol with a fabricated grip.",
     startLine="",completeLine="Stabilised grip tested. Your pistol holds steadier."},
    new FieldOrder{id="order_keep_charge",title="Keep the Charge",goal=FieldOrderGoal.FitMod,targetItemId="cell_salvaged_capacitor",guidance="depot",rewardCredits=20,
     brief="Build a bigger nano cell: wind a copper coil, seal two micro capacitors into a charge core, then fabricate and fit the {item}.",
     startLine="That pistol runs dry after a dozen shots. I've sent charge-cell schematics to the fabricator. Scrap drones carry micro capacitors, and the scrap heaps hide a few. Wind a coil, seal a core, fit the cell.",
     completeLine="That cell holds a proper charge now. You'll outlast a drone swarm."},
    new FieldOrder{id="order_bore_true",title="Bore It True",goal=FieldOrderGoal.FitMod,targetItemId="barrel_bored_alloy",guidance="depot",rewardCredits=25,
     brief="Press scrap alloy into refined plates, wind a coil, then fabricate and fit the {item}.",
     startLine="Your barrel is rolled sheet scrap. The fabricator can press alloy into proper plate: three measures of alloy and two of nanites a plate. Bore a true barrel and your shots will hit like they mean it.",
     completeLine="Now it hits like it means it. The workers won't shrug that off."},
    new FieldOrder{id="order_depot_foreman",title="The Depot Foreman",goal=FieldOrderGoal.CollectItem,targetItemId="foreman_control_core",activateEncounter="foreman",guidance="foreman",rewardCredits=40,
     brief="Destroy the Depot Foreman in the processing hall and recover the {item} from its wreck.",
     startLine="Listen. Something big just woke in the depot's processing hall: a foreman unit, still running its old shift. It's slow, but it hits hard and shrugs off a stagger. When its optics flare red, step back. Put it down and bring me its control core.",
     completeLine="That core still holds its shift schedules, and Mark II pistol schematics with them. They're in the fabricator now."},
    new FieldOrder{id="order_mark_two",title="Mark II",goal=FieldOrderGoal.CraftFromGroup,targetGroup=RecipeGroup.MarkII,guidance="foreman",rewardCredits=50,
     brief="Fabricate any Mark II pistol mod. The foreman carries actuators and quantum lattice shards, and its cradle keeps reviving it.",
     startLine="Mark II work needs rare parts: intact actuators and quantum lattice shards. The foreman carries both, and its charging cradle keeps reviving it. Build me something Warden-grade.",
     completeLine="That's Warden-grade work. The Berms are yours to hunt now; the depot always fills up again."},
   };
   set.freePlayObjective="Free hunting: the Depot Foreman re-forms in the processing hall. Recover lattice shards and actuators for the other Mark II mods, and sell surplus salvage to Mira at Basic General.";
   set.freePlayGuidance="";
   if(created)AssetDatabase.CreateAsset(set,OrdersPath);else EditorUtility.SetDirty(set);
   AssetDatabase.SaveAssets();
   Debug.Log("GAMEPLAY_V2_ORDERS "+set.orders.Length+" orders at "+OrdersPath);
  }
  const string Prefabs="Assets/AthenHill/Prefabs/OuterBerms/";
  const string Mats="Assets/AthenHill/Art/OuterBerms/Materials/";
  public const string CachePrefab=Prefabs+"SalvageCache.prefab",NodePrefab=Prefabs+"SalvageHeapNode.prefab",ForemanPrefab=Prefabs+"FeralDepotForeman.prefab";

  /// Builds the salvage cache, the searchable heap marker and the Depot Foreman prefab variant (plus their materials).
  /// Batch: -executeMethod AthenHill.Editor.GameplayV2Content.BuildPrefabs -quit
  public static void BuildPrefabs()
  {
   foreach(var path in new[]{CachePrefab,NodePrefab,ForemanPrefab})
    if(AssetDatabase.LoadAssetAtPath<GameObject>(path)&&!Force)throw new Exception(path+" exists; edit the prefab instead (GAMEPLAY_V2_FORCE=1 rebuilds it).");
   var beacon=EmissiveMaterial(Mats+"SalvageBeacon.mat");
   var mote=CopyMaterial("Assets/AthenHill/Art/OuterBerms/BermsSparks.mat","Assets/AthenHill/Art/OuterBerms/SalvageMote.mat",m=>{m.SetColor("_BaseColor",Color.white);if(m.HasProperty("_Color"))m.SetColor("_Color",Color.white);});
   var foremanBody=CopyMaterial(Mats+"RB_WorkerDroid.mat",Mats+"RB_ForemanDroid.mat",m=>{m.SetColor("_BaseColor",new Color(.78f,.6f,.46f));m.SetColor("_EmissionColor",new Color(1.4f,.18f,.08f));});
   BuildCache(beacon,mote);BuildNode(mote);BuildForeman(foremanBody);
   AssetDatabase.SaveAssets();
   Debug.Log("GAMEPLAY_V2_PREFABS "+string.Join(", ",CachePrefab,NodePrefab,ForemanPrefab));
  }
  static Material EmissiveMaterial(string path)
  {
   var m=AssetDatabase.LoadAssetAtPath<Material>(path);
   if(!m){m=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(m,path);}
   m.SetColor("_BaseColor",new Color(.16f,.17f,.17f));m.SetFloat("_Metallic",.7f);m.SetFloat("_Smoothness",.55f);
   m.EnableKeyword("_EMISSION");m.SetColor("_EmissionColor",new Color(1.5f,1.35f,1.1f));
   m.globalIlluminationFlags=MaterialGlobalIlluminationFlags.RealtimeEmissive;
   EditorUtility.SetDirty(m);return m;
  }
  static Material CopyMaterial(string from,string to,Action<Material> edit)
  {
   var m=AssetDatabase.LoadAssetAtPath<Material>(to);
   if(!m){if(!AssetDatabase.CopyAsset(from,to))throw new Exception("Cannot copy "+from);m=AssetDatabase.LoadAssetAtPath<Material>(to);}
   edit(m);EditorUtility.SetDirty(m);return m;
  }
  static ParticleSystem Motes(Transform parent,string name,Material material,float rate,float lifetime,float speed,float radius,int max)
  {
   var go=new GameObject(name,typeof(ParticleSystem));go.transform.SetParent(parent,false);
   go.transform.localRotation=Quaternion.Euler(-90,0,0);
   var ps=go.GetComponent<ParticleSystem>();ps.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
   var main=ps.main;main.loop=true;main.playOnAwake=true;main.startLifetime=lifetime;main.startSpeed=speed;main.startSize=new ParticleSystem.MinMaxCurve(.03f,.06f);
   main.maxParticles=max;main.simulationSpace=ParticleSystemSimulationSpace.World;main.gravityModifier=-.02f;main.startColor=Color.white;
   var emission=ps.emission;emission.rateOverTime=rate;
   var shape=ps.shape;shape.shapeType=ParticleSystemShapeType.Cone;shape.angle=12;shape.radius=radius;
   var color=ps.colorOverLifetime;color.enabled=true;
   var g=new Gradient();g.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.9f,.25f),new GradientAlphaKey(0,1)});color.color=g;
   var r=go.GetComponent<ParticleSystemRenderer>();r.sharedMaterial=material;r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;r.receiveShadows=false;
   return ps;
  }
  static Light PointLight(Transform parent,string name,Vector3 at,Color color,float intensity,float range)
  {
   var l=new GameObject(name,typeof(Light)).GetComponent<Light>();l.transform.SetParent(parent,false);l.transform.localPosition=at;
   l.type=LightType.Point;l.color=color;l.intensity=intensity;l.range=range;l.shadows=LightShadows.None;
   return l;
  }
  static void BuildCache(Material beacon,Material mote)
  {
   var root=new GameObject("SalvageCache");
   try
   {
    var use=root.AddComponent<WorldInteractable>();use.prompt="E · Collect salvage";use.range=2.3f;
    var cache=root.AddComponent<SalvageCache>();
    // Visual: the Meshy industrial-scrap stack at uniform 0.36 scale (≈0.65 × 0.45 × 0.4 m), no collider so it never blocks.
    var scrap=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/AthenHill/Prefabs/Salvage/scrap.prefab"));
    scrap.name="Salvage bundle";scrap.transform.SetParent(root.transform,false);scrap.transform.localScale=Vector3.one*.36f;
    foreach(var c in scrap.GetComponentsInChildren<Collider>(true))UnityEngine.Object.DestroyImmediate(c);
    foreach(var r in scrap.GetComponentsInChildren<Renderer>(true))r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.On;
    var tag=GameObject.CreatePrimitive(PrimitiveType.Cylinder);tag.name="Salvage beacon";
    UnityEngine.Object.DestroyImmediate(tag.GetComponent<Collider>());
    tag.transform.SetParent(root.transform,false);tag.transform.localPosition=new Vector3(.14f,.46f,.04f);tag.transform.localRotation=Quaternion.Euler(0,0,-12);tag.transform.localScale=new Vector3(.045f,.2f,.045f);
    var tr=tag.GetComponent<MeshRenderer>();tr.sharedMaterial=beacon;tr.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
    cache.glowRenderers=new Renderer[]{tr};
    cache.glowLight=PointLight(root.transform,"Glow light",new Vector3(0,.7f,0),Color.white,1.2f,3.2f);
    cache.motes=Motes(root.transform,"Motes",mote,6,1.8f,.25f,.25f,20);cache.motes.transform.localPosition=new Vector3(0,.25f,0);
    PrefabUtility.SaveAsPrefabAsset(root,CachePrefab);
   }
   finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  static void BuildNode(Material mote)
  {
   var root=new GameObject("SalvageHeapNode");
   try
   {
    var use=root.AddComponent<WorldInteractable>();use.prompt="E · Search the scrap heap";use.range=2.6f;
    var node=root.AddComponent<SalvageNode>();
    node.readyLight=PointLight(root.transform,"Search marker light",new Vector3(0,1.1f,0),new Color(.45f,.9f,.95f),.55f,2.6f);
    node.readyMotes=Motes(root.transform,"Search motes",mote,2.5f,2.6f,.18f,.6f,12);node.readyMotes.transform.localPosition=new Vector3(0,.3f,0);
    var main=node.readyMotes.main;main.startColor=new Color(.55f,.95f,1f,.7f);
    PrefabUtility.SaveAsPrefabAsset(root,NodePrefab);
   }
   finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  /// Prefab variant of the feral worker droid: the same behaviour with heavier serialized tuning.
  static void BuildForeman(Material body)
  {
   var source=AssetDatabase.LoadAssetAtPath<GameObject>(Prefabs+"FeralWorkerDroid.prefab");
   var root=(GameObject)PrefabUtility.InstantiatePrefab(source);
   try
   {
    root.name="FeralDepotForeman";root.transform.localScale=Vector3.one*1.3f;
    var health=root.GetComponent<Health>();health.max=400;health.regenPerSecond=0;
    var d=root.GetComponent<FeralDroid>();
    d.displayName="Depot Foreman";
    d.wanderSpeed=.8f;d.chaseSpeed=2.5f;d.turnSpeed=5;d.aggroRadius=12;d.leashRadius=22;d.attackRange=2.5f;d.wanderRadius=2.5f;
    d.alertSeconds=1f;d.windupSeconds=1f;d.recoverSeconds=1.25f;d.staggerSeconds=.15f;d.staggerImmunity=5;
    d.strikeDamage=30;d.repairPerSecond=5;d.corpseSeconds=20;
    d.walkStrideSpeed*=1.3f;d.runStrideSpeed*=1.3f;d.footLift*=1.3f;d.footPlant*=1.3f;
    d.glowCalm=new Color(1.3f,.16f,.08f);d.glowHostile=new Color(4f,.45f,.2f);d.glowWindup=new Color(10f,2.2f,1f);d.hitFlash=3;
    d.eyeCalm=.7f;d.eyeHostile=3f;
    if(d.eyeLight)d.eyeLight.color=new Color(1f,.22f,.12f);
    if(d.voice)d.voice.pitch=.78f;
    var loot=root.GetComponent<LootSource>();loot.lootTableId="loot_depot_foreman";
    foreach(var r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))if(r.sharedMaterial&&r.sharedMaterial.name=="RB_WorkerDroid")r.sharedMaterial=body;
    PrefabUtility.SaveAsPrefabAsset(root,ForemanPrefab);
   }
   finally{UnityEngine.Object.DestroyImmediate(root);}
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
    new LootTable{id="loot_wreck_carcass",entries=new[]{L("scrap_alloy",1,3),L("droid_servo_damaged",1,1,.35f,3),L("nanite_residue",1,2,.8f,2),L("copper_filament",1,2,.5f,2),L("micro_capacitor",1,1,.15f,5),L("actuator_intact",1,1,.04f),L("lattice_shard",1,1,.02f)}},
    new LootTable{id="loot_drone_wreck",entries=new[]{L("scrap_alloy",1,2),L("micro_capacitor",1,1,.35f,3),L("optic_lens_cracked",1,1,.3f,3),L("nanite_residue",1,2,.8f,2),L("copper_filament",1,1,.5f,2)}},
   };
   c.groupLabels=new[]{new IdLabel{id="Component",label="Refined components"},new IdLabel{id="MarkI",label="Mark I pistol mods"},new IdLabel{id="MarkII",label="Mark II pistol mods"}};
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
