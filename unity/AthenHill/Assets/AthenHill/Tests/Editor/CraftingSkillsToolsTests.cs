using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace AthenHill.Tests
{
 /// 20 Nov 2026, crafting rework phase 2: recipes name a skill and grant XP and a little skill use; tools are tagged items
 /// (Field Toolkit = tool:screwdriver) or fixed bench tools (station tools); Brann hands over a basic toolkit once.
 public class CraftingSkillsToolsTests
 {
  const string Station="station_field_fabricator",Grip="recipe_grip_stabilised_pistol",Rifle="recipe_field_rifle",Topic="npc_ossa:servo_look",GiftTopic="npc_brann:toolkit";
  static CityCatalog City()=>AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
  static CraftingCatalog Data()=>AssetDatabase.LoadAssetAtPath<CraftingCatalog>("Assets/AthenHill/Data/Crafting/WardCrafting.asset");
  static CharacterCatalog Chars()=>Resources.Load<CharacterCatalog>("CharacterCatalog");
  static NpcDefinition Npc(string name)=>AssetDatabase.LoadAssetAtPath<NpcDefinition>("Assets/AthenHill/Data/"+name+".asset");
  static void Give(ShopModel pack,params (string id,int n)[] items)=>Assert.That(pack.TryApply(items.Select(x=>new KeyValuePair<string,int>(x.id,x.n)),0,out var r),Is.True,r);
  static void GiveGripParts(ShopModel pack)=>Give(pack,("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
  static (ShopModel pack,CraftingModel model,CharacterModel character) Run(CraftingCatalog data=null,bool toolkit=true)
  {
   var pack=new ShopModel(City().items);
   if(!toolkit&&pack.Quantity("field_toolkit")>0)Give(pack,("field_toolkit",-pack.Quantity("field_toolkit")));
   var character=new CharacterModel(Chars(),pack);
   var model=new CraftingModel(data??Data(),City().items,pack,()=>true,character:character);model.HandsOnAvailable=_=>false; /* 20 Nov 2026: the timer route (Steady Hands bench: made by hand once first) */
   return (pack,model,character);
  }
  sealed class State:IQuestState
  {
   public bool primer=true,pistol=true,reported;public string order;public OrderStage stage;public readonly HashSet<string> flags=new HashSet<string>(),items=new HashSet<string>(),recipes=new HashSet<string>();
   public bool PrimerComplete=>primer;public bool HasPistol=>pistol;public string CurrentOrderId=>order;public OrderStage Stage=>stage;
   public bool CurrentReported=>reported;public bool HasFlag(string id)=>flags.Contains(id);
   public bool HasItem(string id)=>items.Contains(id);public bool KnowsRecipe(string id)=>recipes.Contains(id);
  }

  [Test] public void DataShapeSkillsToolsAndBrannsGift()
  {
   var data=Data();var grip=data.recipes.Single(r=>r.id==Grip);
   Assert.That(grip.requiredTools,Is.EqualTo(new[]{"tool:screwdriver"}));Assert.That(grip.skill,Is.EqualTo("engineering"));Assert.That(grip.craftXp,Is.GreaterThan(0));Assert.That(grip.skillUse,Is.GreaterThan(0));
   Assert.That(City().items.Single(i=>i.id=="field_toolkit").HasTag("tool:screwdriver"));
   Assert.That(data.recipes.Single(r=>r.id==Rifle).requiredTools,Is.EqualTo(new[]{"field_toolkit"}),"item-id entries keep working");
   var tools=data.stations.Single(s=>s.id==Station).tools;
   foreach(var t in new[]{"tool:vise","tool:grinder","tool:solder","tool:nanite_press","tool:welder"})Assert.That(tools,Does.Contain(t));
   var skills=Chars().skills.Select(s=>s.id).ToHashSet();
   foreach(var r in data.recipes.Where(r=>r.craftXp>0||r.skillUse>0))Assert.That(skills,Does.Contain(r.skill),r.id+" names a real skill");
   foreach(var r in data.recipes)Assert.That(r.skillUse,Is.LessThanOrEqualTo(data.useGainCap),r.id);
   Assert.That(data.nodeGifts.Single().topic,Is.EqualTo(GiftTopic));
   var brann=Npc("npc_brann");Assert.That(brann.nodes.Single(n=>n.id=="toolkit").voice,Is.Not.Null,"voiced");
   Assert.That(QuestConditions.Problems(brann.entries.Single(e=>e.node=="toolkit").requires),Is.Empty);
   foreach(var c in brann.nodes.Single(n=>n.id=="toolkit").choices){Assert.That(QuestConditions.Problems(c.requires),Is.Empty);Assert.That(string.IsNullOrEmpty(c.next)||brann.nodes.Any(n=>n.id==c.next),c.id);}
  }

  [Test] public void NoGripWithoutTheToolkitAndTheBenchSaysWhy()
  {
   var (pack,model,_)=Run(toolkit:false);
   model.Identify(Topic);GiveGripParts(pack);
   Assert.That(model.CanCraft(Grip,Station,out var reason),Is.False);Assert.That(reason,Is.EqualTo("missing_tool"));
   Assert.That(model.TryCraft(Grip,Station,out reason),Is.False);Assert.That(pack.Quantity("droid_servo_damaged"),Is.EqualTo(1),"nothing used");
   var text=CraftingText.Reason(reason,model,model.Recipe(Grip));
   Assert.That(text,Does.Contain("Screwdriver"));Assert.That(text,Does.Contain("Field Toolkit"),"says which carried item has it");
   Assert.That(model.ToolState("tool:screwdriver",Station),Is.EqualTo("missing"));Assert.That(CraftingText.ToolLine(model,"tool:screwdriver",Station),Does.Contain("missing"));
   Give(pack,("field_toolkit",1));
   Assert.That(model.CanCraft(Grip,Station,out reason),reason);Assert.That(model.ToolState("tool:screwdriver",Station),Is.EqualTo("carried"));
   Assert.That(model.TryCraft(Grip,Station,out reason),reason);Assert.That(pack.Quantity("field_toolkit"),Is.EqualTo(1),"tools are not consumed");
  }

  [Test] public void StationToolsSatisfyTagsAndCarriedItemsMatchByTagOrId()
  {
   var data=Object.Instantiate(Data());
   try
   {
    var grip=data.recipes.Single(r=>r.id==Grip);grip.requiredTools=new[]{"tool:vise"};
    var other=new CraftStation{id="station_plain",name="Plain bench",tools=new string[0]};
    data.stations=data.stations.Concat(new[]{other}).ToArray();grip.stationId="";
    var (pack,model,_)=Run(data,toolkit:false);model.Identify(Topic);GiveGripParts(pack);
    Assert.That(model.CanCraft(Grip,Station,out var reason),reason,"the Salvage workbench has the vise");
    Assert.That(model.ToolState("tool:vise",Station),Is.EqualTo("bench"));Assert.That(CraftingText.ToolLine(model,"tool:vise",Station),Does.Contain("at this bench"));
    Assert.That(model.CanCraft(Grip,"station_plain",out reason),Is.False);Assert.That(reason,Is.EqualTo("missing_tool"));
    Assert.That(CraftingText.Reason(reason,model,grip),Does.Contain("Bench vise"));
    Assert.That(model.TryCraft(Grip,Station,out reason),reason);
    // a tool tag also matches a carried item; the station-less call (fitting from the pack) still works
    grip.requiredTools=new[]{"tool:screwdriver"};
    Assert.That(model.CanCraft(Grip,Station,out reason),Is.False,"the bench has no screwdriver; it is carried");
    Give(pack,("field_toolkit",1),("droid_servo_damaged",1),("scrap_alloy",2),("nanite_residue",5));
    Assert.That(model.CanCraft(Grip,Station,out reason),reason);
    grip.requiredTools=new[]{"field_toolkit"};Assert.That(model.CanCraft(Grip,Station,out reason),reason,"item id entry");
    Give(pack,("field_toolkit",-1));Assert.That(model.CanCraft(Grip,Station,out reason),Is.False);
   }
   finally{Object.DestroyImmediate(data);}
  }

  [Test] public void CraftingGrantsXpAndAnEarnedSkillUseGainThatIsCappedAndDiminishing()
  {
   var (pack,model,character)=Run();
   var recipe=model.Recipe(Grip);model.Identify(Topic);
   int skill0=character.TrainedSkill("engineering");
   GiveGripParts(pack);
   Assert.That(model.TryCraft(Grip,Station,out var reason),reason);
   Assert.That(model.LastAward,Is.Not.Null);Assert.That(model.LastAward.xp,Is.EqualTo(recipe.craftXp));
   Assert.That(character.Experience,Is.EqualTo(recipe.craftXp));
   Assert.That(model.LastAward.skillGain,Is.EqualTo(recipe.skillUse).Within(1e-4),"first craft: the full use gain");
   Assert.That(character.TrainedSkill("engineering"),Is.EqualTo(skill0+(int)recipe.skillUse),"whole points go to the skill");
   Assert.That(CraftingText.AwardText(model,model.LastAward),Does.Contain("XP").And.Contain("Engineering"));
   // repeats halve and finally stop; fractions accumulate
   var gains=new List<float>{model.LastAward.skillGain};
   for(int i=0;i<8;i++){Give(pack,("grip_stabilised_pistol",-pack.Quantity("grip_stabilised_pistol")));GiveGripParts(pack);Assert.That(model.TryCraft(Grip,Station,out reason),reason);gains.Add(model.LastAward?.skillGain??0);}
   Assert.That(gains[1],Is.EqualTo(gains[0]*Data().useRepeatFactor).Within(1e-4));
   Assert.That(gains[2],Is.EqualTo(gains[1]*Data().useRepeatFactor).Within(1e-4));
   for(int i=1;i<gains.Count;i++)Assert.That(gains[i],Is.LessThanOrEqualTo(gains[i-1]));
   Assert.That(gains.Last(),Is.EqualTo(0f),"under 0.05 nothing more is gained from this schematic");
   float total=gains.Sum();Assert.That(total,Is.LessThanOrEqualTo(recipe.skillUse*2+1e-3f),"geometric sum is bounded");
   Assert.That(character.TrainedSkill("engineering")-skill0+character.SkillUseProgress("engineering"),Is.EqualTo(total).Within(.01f));
   // levelling is the main route: a skill point spent adds a whole training step, far more than any craft
   Assert.That(Chars().skills.Single(s=>s.id=="engineering").trainingStep,Is.GreaterThan(recipe.skillUse*2));
  }

  [Test] public void UseGainIsCappedPerCraftAndAGainOnlyHappensOnACompletedCraft()
  {
   var data=Object.Instantiate(Data());
   try
   {
    var recipe=data.recipes.Single(r=>r.id==Grip);recipe.skillUse=50;data.useGainCap=1.5f;
    var (pack,model,character)=Run(data);model.Identify(Topic);
    Assert.That(model.UseGain(recipe,0),Is.EqualTo(1.5f),"the cap, however high the recipe's number");
    float p0=character.SkillUseProgress("engineering");int s0=character.TrainedSkill("engineering");
    // a failed craft grants nothing
    Assert.That(model.TryCraft(Grip,Station,out _),Is.False);Assert.That(character.Experience,Is.EqualTo(0));Assert.That(character.TrainedSkill("engineering"),Is.EqualTo(s0));
    GiveGripParts(pack);Assert.That(model.TryCraft(Grip,Station,out var reason),reason);
    Assert.That(character.TrainedSkill("engineering")-s0+character.SkillUseProgress("engineering")-p0,Is.EqualTo(1.5f).Within(.002f));
    // a recipe with no skill grants XP only
    recipe.skill="";var award=model.UseGain(recipe,0);Assert.That(award,Is.EqualTo(0f));
   }
   finally{Object.DestroyImmediate(data);}
  }

  [Test] public void SkillUseSavesAndOlderCharacterSavesStillLoad()
  {
   var (pack,model,character)=Run();
   Assert.That(character.GrantSkillUse("engineering",1.75f,out int whole),Is.True);Assert.That(whole,Is.EqualTo(1));
   Assert.That(character.SkillUseProgress("engineering"),Is.EqualTo(.75f).Within(.001f));
   Assert.That(character.GrantSkillUse("nope",1,out _),Is.False);Assert.That(character.GrantSkillUse("engineering",0,out _),Is.False);
   var json=JsonUtility.ToJson(character.Capture());
   var restored=new CharacterModel(Chars(),new ShopModel(City().items));
   restored.Restore(JsonUtility.FromJson<CharacterState>(json));
   Assert.That(restored.TrainedSkill("engineering"),Is.EqualTo(character.TrainedSkill("engineering")));Assert.That(restored.SkillUseProgress("engineering"),Is.EqualTo(.75f).Within(.001f));
   // 0.75 + 0.5 crosses a whole point after the restore
   restored.GrantSkillUse("engineering",.5f,out whole);Assert.That(whole,Is.EqualTo(1));Assert.That(restored.SkillUseProgress("engineering"),Is.EqualTo(.25f).Within(.001f));
   // a save written before this field existed has no useProgress at all
   var old=JsonUtility.FromJson<CharacterState>(json);old.useProgress=null;
   var older=JsonUtility.FromJson<CharacterState>(System.Text.RegularExpressions.Regex.Replace(json,"\"useProgress\":\\[[^\\]]*\\],?",""));
   foreach(var state in new[]{old,older})
   {
    var fresh=new CharacterModel(Chars(),new ShopModel(City().items));
    Assert.That(fresh.Restore(state),Is.Empty);Assert.That(fresh.SkillUseProgress("engineering"),Is.EqualTo(0f));Assert.That(fresh.TrainedSkill("engineering"),Is.EqualTo(character.TrainedSkill("engineering")));
   }
   // spent skill points still work and the cap per skill holds
   var cap=Chars().skills.Single(s=>s.id=="engineering").maximum;
   Assert.That(character.GrantSkillUse("engineering",100000,out whole),Is.True);Assert.That(character.TrainedSkill("engineering"),Is.LessThanOrEqualTo(cap));
  }

  [Test] public void BrannGivesTheToolkitOnceOnlyWhenTheHandsAreEmpty()
  {
   var (pack,model,_)=Run(toolkit:false);var flags=new HashSet<string>();
   Assert.That(model.Gift("npc_brann:greeting",flags.Contains,out var flag),Is.Null);Assert.That(flag,Is.Null,"another node gives nothing");
   var given=model.Gift(GiftTopic,flags.Contains,out flag);
   Assert.That(given?.id,Is.EqualTo("field_toolkit"));Assert.That(pack.Quantity("field_toolkit"),Is.EqualTo(1));Assert.That(flag,Is.EqualTo("brann_toolkit"));
   flags.Add(flag);
   Give(pack,("field_toolkit",-1));
   Assert.That(model.Gift(GiftTopic,flags.Contains,out flag),Is.Null,"once only, even if the toolkit is gone again");Assert.That(pack.Quantity("field_toolkit"),Is.EqualTo(0));
   // already carrying one (new games start with it): nothing is given and no flag is spent
   var (pack2,model2,_)=Run();Assert.That(pack2.Quantity("field_toolkit"),Is.EqualTo(1));
   Assert.That(model2.Gift(GiftTopic,new HashSet<string>().Contains,out flag),Is.Null);Assert.That(flag,Is.Null);Assert.That(pack2.Quantity("field_toolkit"),Is.EqualTo(1));
  }

  [Test] public void BrannOffersTheToolkitTalkOnlyBeforeHeHasGivenIt()
  {
   var brann=Npc("npc_brann");var s=new State{primer=true};
   Assert.That(DialogueFlow.StartNode(brann,s),Is.EqualTo("toolkit"),"empty-handed, nothing flagged");
   s.flags.Add("brann_toolkit");Assert.That(DialogueFlow.StartNode(brann,s),Is.Not.EqualTo("toolkit"));
   s.flags.Clear();s.items.Add("field_toolkit");Assert.That(DialogueFlow.StartNode(brann,s),Is.Not.EqualTo("toolkit"),"old saves and new games that carry one");
   s.items.Clear();s.order="order_steady_hands";s.stage=OrderStage.Report;
   Assert.That(DialogueFlow.StartNode(brann,s),Is.EqualTo("toolkit"));
   var node=brann.nodes.Single(n=>n.id=="toolkit");
   Assert.That(DialogueFlow.Choices(node,s,9).Select(c=>c.next),Does.Contain("report_ready"),"the report goes on from the toolkit talk");
   s.stage=OrderStage.Gather;Assert.That(DialogueFlow.Choices(node,s,9).Select(c=>c.next),Does.Not.Contain("report_ready"));
  }

  [Test] public void SteadyHandsStillWorksEndToEndWithTheToolkitFromBrann()
  {
   var (pack,model,_)=Run(toolkit:false);var flags=new HashSet<string>();
   var orders=new FieldOrderProgress(AssetDatabase.LoadAssetAtPath<FieldOrderSet>("Assets/AthenHill/Data/Crafting/WardFieldOrders.asset"));
   Assert.That(orders.Begin().id,Is.EqualTo("order_steady_hands"));
   GiveGripParts(pack);model.Identify(Topic);
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Gather),"all parts, but no screwdriver yet");
   // Brann hands over the toolkit when the player talks to him (the same talk is the report)
   Assert.That(model.Gift(GiftTopic,flags.Contains,out _)?.id,Is.EqualTo("field_toolkit"));
   Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Report));
   Assert.That(orders.NoteReport("npc_brann"));Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Fabricate));
   Assert.That(model.TryCraft(Grip,Station,out var reason),reason);Assert.That(orders.Stage(model,pack),Is.EqualTo(OrderStage.Fit));
  }

  [Test] public void EveryExistingRecipeStaysCraftableByItsQuestPath()
  {
   var city=City();
   foreach(var template in Data().recipes)
   {
    var data=Object.Instantiate(Data());
    try
    {
     var recipe=data.recipes.Single(r=>r.id==template.id);recipe.requirements=new CharacterRequirement[0]; // skill levels are the quest path's job; this test is about parts and tools
     var pack=new ShopModel(city.items);
     var model=new CraftingModel(data,city.items,pack,()=>true,character:new CharacterModel(Chars(),pack));model.HandsOnAvailable=_=>false; /* 20 Nov 2026: the timer route (Steady Hands bench: made by hand once first) */
     // the toolkit comes with the player or from Brann; either way it is in the pack
     if(pack.Quantity("field_toolkit")==0)Assert.That(model.Gift(GiftTopic,new HashSet<string>().Contains,out _),Is.Not.Null);
     foreach(var id in recipe.requiredSchematics??new string[0])model.Unlock(id);
     model.Unlock(recipe.id);
     var weapon=string.IsNullOrEmpty(recipe.requiresWeaponId)?null:data.weapons.Single(w=>w.id==recipe.requiresWeaponId);
     if(weapon!=null&&pack.Quantity(weapon.itemId)==0)Give(pack,(weapon.itemId,1));
     foreach(var input in recipe.inputs)
     {
      var item=input.kind=="item"?city.items.Single(i=>i.id==input.id):city.items.First(i=>i.HasTag(input.id));
      int n=item.maxStack>0?System.Math.Min(input.quantity,item.maxStack):input.quantity;Give(pack,(item.id,n));
     }
     Assert.That(model.CanCraft(recipe.id,recipe.stationId,out var reason),Is.True,recipe.id+": "+reason+" "+CraftingText.Reason(reason,model,recipe));
    }
    finally{Object.DestroyImmediate(data);}
   }
  }
 }
}
