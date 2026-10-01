using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
namespace AthenHill
{
 // THESIS: The Warden field fabricator as a worn workbench console.
 // STORY: choose a schematic, see what you have against what it needs, fabricate, then fit it and watch the numbers move.
 // FORM: three columns (schematics | the selected schematic | the pistol's slots and a current vs. preview stats table).
 // Layout lives in CityHUD.uxml/.uss; every name and number here comes from the catalogs.
 // KEYBOARD: the schematic list is one Tab stop. Only the selected schematic can take focus, so Tab never passes
 // through (and never changes) the selection: Tab goes list → enabled actions → slot cards. ↑/↓ in the list (or a
 // click / Enter) is the only way to change the selection, and every action works on the visibly selected schematic.
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
  string slotsWeapon;
  public string Selected {get;private set;}
  /// Schematics in list order (the order ↑/↓ walks).
  public IReadOnlyList<string> Order=>order;
  CraftingModel Model=>crafting?crafting.Model:null;
  WeaponLoadout LoadoutFor(CraftRecipe recipe)
  {
   var model=Model;if(model==null)return null;
   var mod=recipe!=null?model.Loadout.Modifier(recipe.outputItemId):null;
   return model.GetLoadout(recipe?.requiresWeaponId)??model.GetLoadout(recipe?.outputWeaponId)??model.GetLoadout(mod?.weaponIds?.FirstOrDefault())??model.Loadout;
  }
  WeaponLoadout SelectedLoadout=>LoadoutFor(Recipe);
  public FabricatorPanel(VisualElement root,GameSession session,CraftingSession crafting)
  {
   this.session=session;this.crafting=crafting;
   list=root.Q("fab-recipe-list");inputs=root.Q("fabricator-ingredients");slots=root.Q("fab-slots");stats=root.Q("fab-stats");
   title=root.Q<Label>("fabricator-recipe");description=root.Q<Label>("fab-description");reason=root.Q<Label>("fab-reason");pistolTitle=root.Q<Label>("fabricator-stat");
   craft=root.Q<Button>("fabricator-craft");fit=root.Q<Button>("fabricator-fit");remove=root.Q<Button>("fabricator-remove");
   craft.clicked+=Craft;fit.clicked+=Fit;remove.clicked+=Remove;
   list.RegisterCallback<NavigationMoveEvent>(ListNavigate,TrickleDown.TrickleDown);
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
     // Click / Enter chooses the schematic and offers its first available action. Focus alone never selects.
     var b=new Button(()=>Choose(id)){name="fab-recipe-"+id,focusable=false};b.AddToClassList("fab-recipe");
     var name=new Label(r.name){pickingMode=PickingMode.Ignore};name.AddToClassList("fab-recipe-name");b.Add(name);
     var state=new Label{pickingMode=PickingMode.Ignore};state.AddToClassList("fab-recipe-state");b.Add(state);
     list.Add(b);recipeButtons[id]=b;order.Add(id);
    }
   }
   BuildSlots();
   var header=new VisualElement{pickingMode=PickingMode.Ignore};header.AddToClassList("fab-stat-row");header.AddToClassList("fab-stat-header");
   header.Add(Cell("STAT","fab-stat-name"));header.Add(Cell("NOW","fab-stat-cell","fab-stat-now"));header.Add(Cell("WITH MOD","fab-stat-cell","fab-stat-preview"));header.Add(Cell("CHANGE","fab-stat-cell","fab-stat-delta"));
   foreach(var l in header.Children())l.AddToClassList("small");
   stats.Add(header);
   foreach(var stat in model.Data.statLabels??new StatLabel[0])
   {
    if(stat==null||WeaponStats.IndexOf(stat.stat)<0)continue;
    var row=new VisualElement{pickingMode=PickingMode.Ignore};row.AddToClassList("fab-stat-row");
    var name=Cell(stat.label,"fab-stat-name");
    var current=Cell("","fab-stat-cell","fab-stat-now");var preview=Cell("","fab-stat-cell","fab-stat-preview");var delta=Cell("","fab-stat-cell","fab-stat-delta");
    row.Add(name);row.Add(current);row.Add(preview);row.Add(delta);stats.Add(row);statRows.Add((stat,current,preview,delta));
   }
  }
  void BuildSlots()
  {
   var model=Model;var loadout=SelectedLoadout;
   if(loadout==null||slotsWeapon==loadout.WeaponId)return;
   slotsWeapon=loadout.WeaponId;slots.Clear();slotButtons.Clear();
   foreach(var slot in loadout.Slots)
   {
    var s=slot;
    var b=new Button(()=>SelectSlot(s)){name="fab-slot-"+slot};b.AddToClassList("fab-slot");
    var label=new Label(model.Data.SlotName(slot).ToUpperInvariant()){pickingMode=PickingMode.Ignore};label.AddToClassList("small");label.AddToClassList("fab-slot-label");b.Add(label);
    var mod=new Label{pickingMode=PickingMode.Ignore};mod.AddToClassList("fab-slot-mod");b.Add(mod);
    slots.Add(b);slotButtons[slot]=b;
   }
  }
  static Label Cell(string text,params string[] classes){var l=new Label(text){pickingMode=PickingMode.Ignore};foreach(var c in classes)l.AddToClassList(c);return l;}
  /// Called when the fabricator opens: picks the current field order's part (or the last choice) and focuses it.
  public void Opened()
  {
   Build();if(Model==null)return;
   var orders=session.GetComponent<FieldOrders>();
   var target=orders&&orders.Ready?orders.Progress.RecipeFor(Model,orders.Progress.Current):null;
   string pick=target!=null&&Model.Knows(target.id)?target.id:Selected!=null&&recipeButtons.ContainsKey(Selected)?Selected:order.FirstOrDefault(Model.Knows)??order.FirstOrDefault();
   if(pick!=null){Selected=null;Select(pick);}
   // Ready to act on the current order's part: Enter fabricates (then fits) straight away, as before v2.
   // Otherwise focus the schematic list (↑/↓ browse).
   Focusable focusTarget=craft.enabledSelf?craft:fit.enabledSelf?fit:SelectedButton;
   if(focusTarget!=null)craft.schedule.Execute(focusTarget.Focus);
  }
  Button SelectedButton=>Selected!=null&&recipeButtons.TryGetValue(Selected,out var b)?b:null;
  /// Changes the selected schematic (explicit list navigation, click or Enter, a slot card, or opening the window).
  public void Select(string recipeId)
  {
   if(recipeId==null||Selected==recipeId||built&&!recipeButtons.ContainsKey(recipeId))return;
   Selected=recipeId;Refresh();
  }
  /// ↑/↓ in the list: one schematic per press, stopping at the ends. Returns false when already at that end.
  public bool Move(int delta)
  {
   int i=order.IndexOf(Selected);if(i<0)return false;
   int next=UiNavigation.ListStep(i,order.Count,delta);
   if(next==i)return false;
   Select(order[next]);FocusSelected();return true;
  }
  /// Click / Enter on a schematic: select it, then move to its first available action.
  public void Choose(string recipeId){Select(recipeId);FocusAction();}
  void SelectSlot(string slot)
  {
   var model=Model;if(model==null)return;
   var loadout=SelectedLoadout;var fitted=loadout.Fitted(slot);
   var recipe=fitted!=null?model.Data.recipes.FirstOrDefault(r=>r.outputItemId==fitted):model.Data.recipes.FirstOrDefault(r=>model.Knows(r.id)&&loadout.Accepts(loadout.Modifier(r.outputItemId))&&loadout.Modifier(r.outputItemId)?.slot==slot);
   if(recipe!=null){Select(recipe.id);FocusSelected();}
  }
  void FocusSelected(){var b=SelectedButton;if(b!=null){b.focusable=true;b.Focus();}}
  /// Where an action hands focus: the first enabled action, else the selected schematic.
  public Focusable ActionFocus=>craft.enabledSelf?craft:fit.enabledSelf?fit:remove.enabledSelf?remove:SelectedButton;
  void FocusAction(){var f=ActionFocus;if(f==SelectedButton)FocusSelected();else f?.Focus();}
  /// Arrows inside the list: ↑/↓ step the selection, → jumps to the actions, ← stays. Each press is handled once
  /// here and withheld from UI Toolkit's own focus navigation (which previously moved focus a second time).
  void ListNavigate(NavigationMoveEvent e)
  {
   switch(e.direction)
   {
    case NavigationMoveEvent.Direction.Up:Move(-1);break;
    case NavigationMoveEvent.Direction.Down:Move(1);break;
    case NavigationMoveEvent.Direction.Right:FocusAction();break;
    case NavigationMoveEvent.Direction.Left:break;
    default:return; // Tab / Shift+Tab: ordinary focus order (list → actions → slots).
   }
   UiNavigation.Consume(e,list);
  }
  CraftRecipe Recipe=>Model?.Recipe(Selected);
  CraftModifier Mod=>Recipe!=null?Model.Loadout.Modifier(Recipe.outputItemId):null;
  // Action handlers (the buttons' click / Enter). They always act on Selected.
  public void Craft()
  {
   var r=Recipe;if(r==null)return;
   if(crafting.Craft(r.id,out _))AfterAction(Mod!=null?fit:craft);
  }
  public void Fit(){var r=Recipe;if(r!=null&&crafting.Fit(SelectedLoadout.WeaponId,r.outputItemId,out _))AfterAction(null);}
  public void Remove(){var m=Mod;if(m!=null&&crafting.Remove(SelectedLoadout.WeaponId,m.slot,out _))AfterAction(fit);}
  /// The element focus moves to after a successful action (the pressed button usually disables itself).
  public Focusable FocusAfterAction {get;private set;}
  void AfterAction(Button preferred)
  {
   Refresh();
   Focusable target=preferred!=null&&preferred.enabledSelf?preferred:SelectedButton;
   if(target is Button b&&b==SelectedButton)b.focusable=true;
   FocusAfterAction=target;
   if(target!=null)craft.schedule.Execute(target.Focus);
  }
  public void Refresh()
  {
   var model=Model;
   if(model==null){title.text="The fabricator is still starting up.";return;}
   Build();BuildSlots();
   var loadout=SelectedLoadout;
   var pack=session.Shop;
   foreach(var pair in recipeButtons)
   {
    var r=model.Recipe(pair.Key);bool known=model.Knows(r.id);bool ready=known&&model.CanCraft(r.id,session.ActiveStationId,out _);
    var mod=model.Loadout.Modifier(r.outputItemId);bool isFitted=mod!=null&&LoadoutFor(r).Fitted(mod.slot)==r.outputItemId;
    int carried=pack.Quantity(r.outputItemId);
    bool selected=pair.Key==Selected;
    pair.Value.EnableInClassList("locked",!known);pair.Value.EnableInClassList("ready",ready);pair.Value.EnableInClassList("selected",selected);pair.Value.EnableInClassList("fitted",isFitted);
    // Roving tab stop: only the selected schematic is focusable.
    pair.Value.focusable=selected;
    pair.Value.Q<Label>(className:"fab-recipe-state").text=!known?"Locked":isFitted?"Fitted":ready?"Ready":carried>0?$"×{carried}":"";
    pair.Value.tooltip=!known?CraftingText.Reason("recipe_locked",model,r):r.name;
   }
   foreach(var pair in slotButtons)
   {
    var item=loadout.Fitted(pair.Key);
    pair.Value.Q<Label>(className:"fab-slot-mod").text=item!=null?CraftingText.ItemName(model,item):"Empty";
    pair.Value.EnableInClassList("empty",item==null);
    pair.Value.EnableInClassList("selected",Mod!=null&&Mod.slot==pair.Key);
   }
   pistolTitle.text=loadout.WeaponName.ToUpperInvariant();
   var recipe=Recipe;var selectedMod=Mod;
   inputs.Clear();
   if(recipe==null){title.text="Choose a schematic.";description.text="";reason.text="";craft.SetEnabled(false);fit.SetEnabled(false);remove.SetEnabled(false);FillStats(model,null);return;}
   var output=model.Item(recipe.outputItemId);
   bool knownRecipe=model.Knows(recipe.id);
   title.text=recipe.name+(recipe.outputQuantity>1?$" ×{recipe.outputQuantity}":"");
   description.text=(output!=null?output.description:"")+(selectedMod!=null?"\n"+ModSummary(model,selectedMod):"");
   var conditions=new List<string>();
   foreach(var requirement in recipe.requirements??Array.Empty<CharacterRequirement>())
   {
    if(requirement==null)continue;
    string label=session.Character?.Data.Label(requirement.stat)??requirement.stat;
    conditions.Add($"{label}: {session.Character?.Stat(requirement.stat)??0:0.#} / {requirement.minimum:0.#}");
   }
   foreach(var tool in recipe.requiredTools??Array.Empty<string>())conditions.Add($"Tool: {CraftingText.ItemName(model,tool)} ({(pack.Quantity(tool)>0?"carried":"missing")})");
   foreach(var id in recipe.requiredSchematics??Array.Empty<string>())conditions.Add($"Schematic: {model.Recipe(id)?.name??id} ({(model.Knows(id)?"known":"unknown")})");
   if(conditions.Count>0)description.text+="\n"+string.Join("\n",conditions);
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
   bool fitted=selectedMod!=null&&loadout.Fitted(selectedMod.slot)==recipe.outputItemId;
   int carriedOut=pack.Quantity(recipe.outputItemId);
   bool canFit=selectedMod!=null&&model.CanFit(loadout.WeaponId,recipe.outputItemId,out _);
   fit.SetEnabled(canFit);fit.text=selectedMod!=null?$"Fit to {model.Data.SlotName(selectedMod.slot).ToLowerInvariant()}":"Fit to weapon";
   bool canRemove=selectedMod!=null&&loadout.Fitted(selectedMod.slot)!=null&&model.HasWeapon(loadout.WeaponId);
   remove.SetEnabled(canRemove);remove.text=selectedMod!=null?$"Remove {model.Data.SlotName(selectedMod.slot).ToLowerInvariant()} mod":"Remove";
   var (why,blocked)=Guidance(model,recipe,selectedMod,knownRecipe,canCraft,craftReason,fitted,canFit,carriedOut);
   reason.text=why;
   reason.EnableInClassList("blocked",blocked);
   reason.EnableInClassList("fitted",fitted);
   FillStats(model,selectedMod!=null&&!fitted?selectedMod:null);
  }
  /// One line of guidance in words, and whether it reports a blocker (red).
  (string text,bool blocked) Guidance(CraftingModel model,CraftRecipe recipe,CraftModifier mod,bool known,bool canCraft,string craftReason,bool fitted,bool canFit,int carried)
  {
   if(!known)return (CraftingText.Reason("recipe_locked",model,recipe),false);
   if(fitted)
   {
    string another=!canCraft&&craftReason=="missing_ingredients"?CraftingText.Shortfall(model,recipe):"";
    return ($"Fitted to your {SelectedLoadout.WeaponName}."+(another.Length>0?$" Another would need {another}.":""),false);
   }
   if(canFit)return (carried>1?$"You carry {carried}; fit one here.":"Ready to fit.",false);
   if(!canCraft)return (CraftingText.Reason(craftReason,model,recipe),true);
   if(mod==null)return ("Components are used by other schematics; they are not fitted.",false);
   return (carried>0?CraftingText.Reason("missing_weapon",model):"Fabricate it, then fit it here.",false);
  }
  /// "Grip mod · replaces Stabilised Pistol Grip: Recoil 31 → 23 · Aim assist 3.5° → 4.5°". Always measured against
  /// the CURRENT loadout; for the fitted mod, what it adds over an empty slot.
  public static string ModSummary(CraftingModel model,CraftModifier mod)
  {
   var loadout=model.GetLoadout(mod.weaponIds?.FirstOrDefault())??model.Loadout;var slot=model.Data.SlotName(mod.slot);
   var current=loadout.Fitted(mod.slot);
   if(current==mod.itemId)return $"{slot} mod · fitted: "+CraftingText.StatChanges(model.Data,loadout.Preview(mod.slot,null),loadout.Stats);
   var changes=CraftingText.StatChanges(model.Data,loadout.Stats,loadout.Preview(mod.slot,mod.itemId));
   return (current!=null?$"{slot} mod · replaces {CraftingText.ItemName(model,current)}: ":$"{slot} mod: ")+(changes.Length>0?changes:"no change");
  }
  void FillStats(CraftingModel model,CraftModifier preview)
  {
   var loadout=SelectedLoadout;var now=loadout.Stats;
   var next=preview!=null?loadout.Preview(preview.slot,preview.itemId):now;
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
