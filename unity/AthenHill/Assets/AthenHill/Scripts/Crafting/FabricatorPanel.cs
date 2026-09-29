using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 // THESIS: The Warden field fabricator as a worn workbench console.
 // STORY: choose a schematic, see what you have against what it needs, fabricate, then fit it and watch the numbers move.
 // FORM: schematic list (grouped, lock state) beside the selected recipe; the pistol's slots beside a current vs. preview
 // stats table. Layout lives in CityHUD.uxml/.uss; every name and number here comes from the catalogs.
 public sealed class FabricatorPanel
 {
  readonly GameSession session;
  readonly CraftingSession crafting;
  readonly VisualElement list,inputs,slots,stats;
  readonly Label title,description,reason,pistolTitle;
  readonly Button craft,fit,remove;
  readonly Dictionary<string,Button> recipeButtons=new Dictionary<string,Button>();
  readonly Dictionary<string,Button> slotButtons=new Dictionary<string,Button>();
  readonly List<(StatLabel label,Label current,Label preview,Label delta)> statRows=new List<(StatLabel,Label,Label,Label)>();
  readonly List<string> order=new List<string>();
  bool built;
  public string Selected {get;private set;}
  CraftingModel Model=>crafting?crafting.Model:null;
  public FabricatorPanel(VisualElement root,GameSession session,CraftingSession crafting)
  {
   this.session=session;this.crafting=crafting;
   list=root.Q("fab-recipe-list");inputs=root.Q("fabricator-ingredients");slots=root.Q("fab-slots");stats=root.Q("fab-stats");
   title=root.Q<Label>("fabricator-recipe");description=root.Q<Label>("fab-description");reason=root.Q<Label>("fab-reason");pistolTitle=root.Q<Label>("fabricator-stat");
   craft=root.Q<Button>("fabricator-craft");fit=root.Q<Button>("fabricator-fit");remove=root.Q<Button>("fabricator-remove");
   craft.clicked+=Craft;fit.clicked+=Fit;remove.clicked+=Remove;
   list.RegisterCallback<KeyDownEvent>(ListKeys,TrickleDown.TrickleDown);
  }
  void Build()
  {
   var model=Model;if(model==null||built)return;
   built=true;list.Clear();slots.Clear();stats.Clear();recipeButtons.Clear();slotButtons.Clear();statRows.Clear();order.Clear();
   foreach(RecipeGroup group in Enum.GetValues(typeof(RecipeGroup)))
   {
    var recipes=model.Data.recipes.Where(r=>r.group==group).ToList();if(recipes.Count==0)continue;
    var heading=new Label(model.Data.GroupName(group).ToUpperInvariant()){pickingMode=PickingMode.Ignore};heading.AddToClassList("small");heading.AddToClassList("fab-group");list.Add(heading);
    foreach(var r in recipes)
    {
     var id=r.id;
     var b=new Button(()=>{Select(id);FocusAction();}){name="fab-recipe-"+id};b.AddToClassList("fab-recipe");
     var name=new Label(r.name){pickingMode=PickingMode.Ignore};name.AddToClassList("fab-recipe-name");b.Add(name);
     var state=new Label{pickingMode=PickingMode.Ignore};state.AddToClassList("fab-recipe-state");b.Add(state);
     b.RegisterCallback<FocusInEvent>(_=>Select(id));
     list.Add(b);recipeButtons[id]=b;order.Add(id);
    }
   }
   foreach(var slot in model.Loadout.Slots)
   {
    var s=slot;
    var b=new Button(()=>SelectSlot(s)){name="fab-slot-"+slot};b.AddToClassList("fab-slot");
    var label=new Label(model.Data.SlotName(slot).ToUpperInvariant()){pickingMode=PickingMode.Ignore};label.AddToClassList("small");label.AddToClassList("fab-slot-label");b.Add(label);
    var mod=new Label{pickingMode=PickingMode.Ignore};mod.AddToClassList("fab-slot-mod");b.Add(mod);
    slots.Add(b);slotButtons[slot]=b;
   }
   var header=new VisualElement{pickingMode=PickingMode.Ignore};header.AddToClassList("fab-stat-row");header.AddToClassList("fab-stat-header");
   foreach(var text in new[]{"","NOW","WITH SELECTION",""}){var l=new Label(text){pickingMode=PickingMode.Ignore};l.AddToClassList("small");l.AddToClassList(header.childCount==0?"fab-stat-name":"fab-stat-cell");header.Add(l);}
   stats.Add(header);
   foreach(var stat in model.Data.statLabels??new StatLabel[0])
   {
    if(stat==null||WeaponStats.IndexOf(stat.stat)<0)continue;
    var row=new VisualElement{pickingMode=PickingMode.Ignore};row.AddToClassList("fab-stat-row");
    var name=new Label(stat.label){pickingMode=PickingMode.Ignore};name.AddToClassList("fab-stat-name");
    var current=new Label{pickingMode=PickingMode.Ignore};var preview=new Label{pickingMode=PickingMode.Ignore};var delta=new Label{pickingMode=PickingMode.Ignore};
    foreach(var c in new[]{current,preview,delta})c.AddToClassList("fab-stat-cell");
    delta.AddToClassList("fab-stat-delta");
    row.Add(name);row.Add(current);row.Add(preview);row.Add(delta);stats.Add(row);statRows.Add((stat,current,preview,delta));
   }
  }
  /// Called when the fabricator opens: picks the current field order's part (or the last choice) and focuses it.
  public void Opened()
  {
   Build();if(Model==null)return;
   var orders=session.GetComponent<FieldOrders>();
   var target=orders&&orders.Ready?orders.Progress.RecipeFor(Model,orders.Progress.Current):null;
   string pick=target!=null&&Model.Knows(target.id)?target.id:Selected!=null&&recipeButtons.ContainsKey(Selected)?Selected:order.FirstOrDefault(Model.Knows)??order.FirstOrDefault();
   if(pick!=null)Select(pick);
   // Ready to act on the current order's part: Enter fabricates (then fits) straight away, as before v2.
   // Otherwise focus the schematic list (↑/↓ browse).
   Focusable focusTarget=craft.enabledSelf?craft:fit.enabledSelf?fit:pick!=null&&recipeButtons.TryGetValue(pick,out var button)?button:null;
   if(focusTarget!=null)craft.schedule.Execute(focusTarget.Focus);
  }
  public void Select(string recipeId){if(Selected==recipeId)return;Selected=recipeId;Refresh();}
  void SelectSlot(string slot)
  {
   var model=Model;if(model==null)return;
   var fitted=model.Loadout.Fitted(slot);
   var recipe=fitted!=null?model.Data.recipes.FirstOrDefault(r=>r.outputItemId==fitted):model.Data.recipes.FirstOrDefault(r=>model.Knows(r.id)&&model.Loadout.Modifier(r.outputItemId)?.slot==slot);
   if(recipe!=null){Select(recipe.id);if(recipeButtons.TryGetValue(recipe.id,out var b))b.Focus();}
  }
  void FocusAction(){if(craft.enabledSelf)craft.Focus();else if(fit.enabledSelf)fit.Focus();}
  void ListKeys(KeyDownEvent e)
  {
   if(e.keyCode!=KeyCode.UpArrow&&e.keyCode!=KeyCode.DownArrow)return;
   int i=order.IndexOf(Selected);if(i<0)return;
   i=Mathf.Clamp(i+(e.keyCode==KeyCode.DownArrow?1:-1),0,order.Count-1);
   if(recipeButtons.TryGetValue(order[i],out var b))b.Focus();
   e.StopPropagation();
  }
  CraftRecipe Recipe=>Model?.Recipe(Selected);
  CraftModifier Mod=>Recipe!=null?Model.Loadout.Modifier(Recipe.outputItemId):null;
  void Craft()
  {
   var r=Recipe;if(r==null)return;
   if(crafting.Craft(r.id,out _)&&Mod!=null)fit.schedule.Execute(()=>{if(fit.enabledSelf)fit.Focus();});
  }
  void Fit(){var r=Recipe;if(r!=null)crafting.Fit(r.outputItemId,out _);}
  void Remove(){var m=Mod;if(m!=null)crafting.Remove(m.slot,out _);}
  public void Refresh()
  {
   var model=Model;
   if(model==null){title.text="The fabricator is still starting up.";return;}
   Build();
   var pack=session.Shop;
   foreach(var pair in recipeButtons)
   {
    var r=model.Recipe(pair.Key);bool known=model.Knows(r.id);bool ready=known&&model.CanCraft(r.id,session.ActiveStationId,out _);
    var mod=model.Loadout.Modifier(r.outputItemId);bool isFitted=mod!=null&&model.Loadout.Fitted(mod.slot)==r.outputItemId;
    int carried=pack.Quantity(r.outputItemId);
    pair.Value.EnableInClassList("locked",!known);pair.Value.EnableInClassList("ready",ready);pair.Value.EnableInClassList("selected",pair.Key==Selected);pair.Value.EnableInClassList("fitted",isFitted);
    pair.Value.Q<Label>(className:"fab-recipe-state").text=!known?"Locked":isFitted?"Fitted":ready?"Ready":carried>0?$"×{carried}":"";
    pair.Value.tooltip=!known?CraftingText.Reason("recipe_locked",model,r):r.name;
   }
   foreach(var pair in slotButtons)
   {
    var item=model.Loadout.Fitted(pair.Key);
    pair.Value.Q<Label>(className:"fab-slot-mod").text=item!=null?CraftingText.ItemName(model,item):"Empty";
    pair.Value.EnableInClassList("empty",item==null);
    pair.Value.EnableInClassList("selected",Mod!=null&&Mod.slot==pair.Key);
   }
   pistolTitle.text=model.Loadout.WeaponName.ToUpperInvariant();
   var recipe=Recipe;var selectedMod=Mod;
   inputs.Clear();
   if(recipe==null){title.text="Choose a schematic.";description.text="";reason.text="";craft.SetEnabled(false);fit.SetEnabled(false);remove.SetEnabled(false);FillStats(model,null);return;}
   var output=model.Item(recipe.outputItemId);
   bool knownRecipe=model.Knows(recipe.id);
   title.text=recipe.name+(recipe.outputQuantity>1?$" ×{recipe.outputQuantity}":"");
   description.text=(output!=null?output.description:"")+(selectedMod!=null?$"\n{model.Data.SlotName(selectedMod.slot)} mod · "+CraftingText.StatChanges(model.Data,model.Loadout.Base,WeaponLoadout.Compute(Weapon(model),new[]{selectedMod})):"");
   foreach(var input in recipe.inputs)
   {
    int have=model.Available(input);bool ok=have>=input.quantity;
    var row=new VisualElement{pickingMode=PickingMode.Ignore};row.AddToClassList("fab-input");row.EnableInClassList("short",!ok);
    var name=new Label(CraftingText.InputName(model,input)){pickingMode=PickingMode.Ignore};name.AddToClassList("fab-input-name");
    var count=new Label($"{have} / {input.quantity}"){pickingMode=PickingMode.Ignore};count.AddToClassList("fab-input-count");count.AddToClassList(ok?"have-ok":"have-short");
    row.Add(name);row.Add(count);inputs.Add(row);
   }
   bool canCraft=model.CanCraft(recipe.id,session.ActiveStationId,out var craftReason);
   craft.SetEnabled(canCraft);craft.text="Fabricate";
   bool fitted=selectedMod!=null&&model.Loadout.Fitted(selectedMod.slot)==recipe.outputItemId;
   bool canFit=selectedMod!=null&&!fitted&&pack.Quantity(recipe.outputItemId)>0&&crafting.combat&&crafting.combat.hasPistol;
   fit.SetEnabled(canFit);fit.text=selectedMod!=null?$"Fit to {model.Data.SlotName(selectedMod.slot).ToLowerInvariant()}":"Fit to pistol";
   bool canRemove=selectedMod!=null&&model.Loadout.Fitted(selectedMod.slot)!=null;
   remove.SetEnabled(canRemove);remove.text=selectedMod!=null?$"Remove {model.Data.SlotName(selectedMod.slot).ToLowerInvariant()} mod":"Remove";
   // One line of guidance in words: why fabrication is blocked, else why fitting is.
   string why=!canCraft?CraftingText.Reason(craftReason,model,recipe):"";
   if(canCraft&&selectedMod==null)why="Components are used by other schematics; they are not fitted.";
   if(canCraft&&selectedMod!=null&&!canFit&&!fitted)why=pack.Quantity(recipe.outputItemId)>0?CraftingText.Reason("missing_weapon",model):"Fabricate it, then fit it here.";
   if(fitted)why=Join(why,$"Fitted to your {model.Loadout.WeaponName}.");
   reason.text=why;
   reason.EnableInClassList("blocked",!canCraft&&knownRecipe);
   FillStats(model,selectedMod!=null&&!fitted?selectedMod:null);
  }
  static string Join(string a,string b)=>string.IsNullOrEmpty(a)?b:a+" "+b;
  static CraftWeapon Weapon(CraftingModel model)=>model.Data.weapons.First(w=>w.id==model.Loadout.WeaponId);
  void FillStats(CraftingModel model,CraftModifier preview)
  {
   var now=model.Loadout.Stats;
   var next=preview!=null?model.Loadout.Preview(preview.slot,preview.itemId):now;
   foreach(var (label,current,previewCell,delta) in statRows)
   {
    int i=WeaponStats.IndexOf(label.stat);
    current.text=CraftingText.FormatStat(label,now[i]);
    previewCell.text=preview!=null?CraftingText.FormatStat(label,next[i]):"—";
    float d=next[i]-now[i];
    delta.text=preview!=null?CraftingText.FormatDelta(label,d):"";
    delta.EnableInClassList("better",preview!=null&&Math.Abs(d)>.0005f&&CraftingText.Improves(label,d));
    delta.EnableInClassList("worse",preview!=null&&Math.Abs(d)>.0005f&&!CraftingText.Improves(label,d));
   }
  }
 }
}
