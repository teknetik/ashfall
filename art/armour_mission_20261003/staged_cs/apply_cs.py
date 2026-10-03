#!/usr/bin/env python3
"""Staged C# changes for the Warden kit chain (3 Oct 2026). Apply only while no Unity job owns the project:
    python3 art/armour_mission_20261003/staged_cs/apply_cs.py [--root ASSETS_ATHENHILL_DIR] [--check]
Idempotent: each edit is skipped when its new text is already present, and fails loudly when neither the old nor the
new text is found (the file moved on; re-stage the edit). --check reports without writing. New files are copied from
files/. Live files are backed up once to ../backup/ before the first change."""
import argparse, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
ap = argparse.ArgumentParser(); ap.add_argument('--root', type=Path, default=LIVE); ap.add_argument('--check', action='store_true')
args = ap.parse_args(); A = args.root.resolve(); live = A == LIVE

EDITS = [
 # ---- runtime -----------------------------------------------------------------------------------------------------
 ('Scripts/Combat/BermsTutorial.cs',
  '''  [Tooltip("Tutorial kit (2 Oct 2026): item:slot pairs equipped on the colonist when the primer completes (into the pack if that slot is already worn).")]
  public string[] kitItems={"field_helmet:armour_head","field_armguards:armour_arms","field_gloves:armour_hands","field_leggings:armour_legs"};
  [TextArea]public string kitNotice="Warden kit issued: scrap helmet, bracers, gloves and leg plates.";''',
  '''  [Tooltip("Optional item:slot pairs equipped on the colonist when the primer completes (into the pack if that slot is already worn). Empty since 3 Oct 2026: the Field armour pieces are built through Ossa's Warden Kit orders at Brann's bench.")]
  public string[] kitItems=new string[0];
  [TextArea]public string kitNotice="";'''),
 ('Scripts/Crafting/CraftingCatalog.cs',
  ''' /// Fabricator window grouping; new weapon families can have their own sections.
 public enum RecipeGroup { Component, MarkI, MarkII, Weapon, WeaponMod }''',
  ''' /// Fabricator window grouping; new weapon families can have their own sections. New values are appended so the
 /// serialized numbers stay valid (Armour = 5, 3 Oct 2026: the Warden kit pieces).
 public enum RecipeGroup { Component, MarkI, MarkII, Weapon, WeaponMod, Armour }'''),
 ('Scripts/PackPanel.cs',
  '''{RecipeGroup.Weapon,"Weapons"},{RecipeGroup.WeaponMod,"Weapon mods"}};''',
  '''{RecipeGroup.Weapon,"Weapons"},{RecipeGroup.WeaponMod,"Weapon mods"},{RecipeGroup.Armour,"Armour"}};'''),
 ('Scripts/Orders/FieldOrderProgress.cs',
  '''  public FieldOrderState Capture()=>new FieldOrderState{index=Index,testFired=''',
  '''  public FieldOrderState Capture()=>new FieldOrderState{index=Index,id=FreePlay?FieldOrderState.FreePlayId:Current?.id??"",testFired='''),
 ('Scripts/Orders/FieldOrderProgress.cs',
  '''   Index=Math.Max(-1,Math.Min(Data.orders.Length,state.index));
''',
  '''   Index=Math.Max(-1,Math.Min(Data.orders.Length,state.index));
   // 3 Oct 2026: orders can be inserted (the Warden kit chain), so a saved order id wins over its numeric index
   if(state.id==FieldOrderState.FreePlayId)Index=Data.orders.Length;
   else if(!string.IsNullOrEmpty(state.id)){int byId=Array.FindIndex(Data.orders,o=>o!=null&&o.id==state.id);if(byId>=0)Index=byId;}
'''),
 ('Scripts/Orders/FieldOrderProgress.cs',
  ''' /// order in progress asks for the visit once).
 [Serializable] public class FieldOrderState {public int index=-1;public string[] testFired;public string[] reported;}''',
  ''' /// order in progress asks for the visit once).
 /// id (3 Oct 2026): the current order's id ("#freeplay" after the last order). Restore prefers it to the index, so
 /// inserting orders keeps saves on the right order; saves without it fall back to the index.
 [Serializable] public class FieldOrderState {public const string FreePlayId="#freeplay";public int index=-1;public string id;public string[] testFired;public string[] reported;}'''),
 # ---- tests -------------------------------------------------------------------------------------------------------
 ('Tests/Editor/FieldOrderTests.cs',
  '''   Assert.That(set.orders.Select(o=>o.title),Is.EqualTo(new[]{"Steady Hands","Long Arm","Plate Carrier","Keep the Charge","Bore It True","The Depot Foreman","Mark II"}));
   Assert.That(set.orders.Select(o=>o.id).Distinct().Count(),Is.EqualTo(7));''',
  '''   // 3 Oct 2026: the four Warden Kit orders (armour built at Brann's bench) follow Steady Hands.
   Assert.That(set.orders.Select(o=>o.title),Is.EqualTo(new[]{"Steady Hands","Warden Kit: Helm","Warden Kit: Bracers","Warden Kit: Gloves","Warden Kit: Leg Plates","Long Arm","Plate Carrier","Keep the Charge","Bore It True","The Depot Foreman","Mark II"}));
   Assert.That(set.orders.Select(o=>o.id).Distinct().Count(),Is.EqualTo(11));'''),
 ('Tests/Editor/FieldOrderTests.cs',
  '''   Assert.That(run.orders.Index,Is.EqualTo(1));Assert.That(run.orders.Current.id,Is.EqualTo("order_long_arm"));
  }''',
  '''   Assert.That(run.orders.Index,Is.EqualTo(1));Assert.That(run.orders.Current.id,Is.EqualTo("order_kit_helmet"));
  }

  /// 3 Oct 2026: the Warden kit. Each piece is gathered from Berms salvage and built at Brann's bench (the order start
  /// reveals its schematic; FieldOrders does that in play); the helm reports to Brann first.
  static void WardenKit(Run run)
  {
   Assert.That(run.orders.Current.id,Is.EqualTo("order_kit_helmet"));run.model.OrderStarted(run.orders.Current.id);
   Assert.That(run.model.Knows("recipe_alloy_plate"),"the first kit order reveals alloy plate");
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Gather));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.Null.Or.Empty);
   Assert.That(run.orders.Objective(run.model,run.pack),Does.Contain("Strap Webbing 0/2").And.Contain("Refined Alloy Plate 0/2"));
   Give(run.pack,("scrap_alloy",6),("nanite_residue",4),("padded_liner",1),("strap_webbing",2),("rivet_stock",2));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Gather),"the plate is still to be rolled");
   run.Craft("recipe_alloy_plate",2);
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Report));Assert.That(run.orders.GuidanceKey(run.model,run.pack),Is.EqualTo("dealer"));
   Assert.That(run.orders.NoteReport("npc_brann"));
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate));
   run.Craft("recipe_field_helmet");Assert.That(run.Advance().Single().id,Is.EqualTo("order_kit_helmet"));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_kit_arms"));run.model.OrderStarted(run.orders.Current.id);
   Give(run.pack,("scrap_alloy",6),("nanite_residue",4),("strap_webbing",2),("rivet_stock",2));run.Craft("recipe_alloy_plate",2);
   Assert.That(run.orders.Stage(run.model,run.pack),Is.EqualTo(OrderStage.Fabricate),"only the helm reports to Brann");
   run.Craft("recipe_field_armguards");Assert.That(run.Advance().Single().id,Is.EqualTo("order_kit_arms"));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_kit_hands"));run.model.OrderStarted(run.orders.Current.id);
   Give(run.pack,("strap_webbing",2),("padded_liner",1),("rivet_stock",1),("copper_filament",2));
   run.Craft("recipe_field_gloves");Assert.That(run.Advance().Single().id,Is.EqualTo("order_kit_hands"));
   Assert.That(run.orders.Current.id,Is.EqualTo("order_kit_legs"));run.model.OrderStarted(run.orders.Current.id);
   Give(run.pack,("scrap_alloy",9),("nanite_residue",6),("padded_liner",2),("strap_webbing",3),("rivet_stock",3));run.Craft("recipe_alloy_plate",3);
   run.Craft("recipe_field_leggings");Assert.That(run.Advance().Single().id,Is.EqualTo("order_kit_legs"));
   foreach(var piece in new[]{"field_helmet","field_armguards","field_gloves","field_leggings"})Assert.That(run.pack.Quantity(piece),Is.EqualTo(1),piece);
   foreach(var used in new[]{"alloy_plate","strap_webbing","padded_liner","rivet_stock","scrap_alloy","nanite_residue","copper_filament"})Assert.That(run.pack.Quantity(used),Is.Zero,used);
  }'''),
 ('Tests/Editor/FieldOrderTests.cs',
  '''   Assert.That(run.Advance().Single().id,Is.EqualTo("order_steady_hands"));
   RifleAndCarrier(run);''',
  '''   Assert.That(run.Advance().Single().id,Is.EqualTo("order_steady_hands"));
   WardenKit(run);
   RifleAndCarrier(run);'''),
 ('Tests/Editor/FieldOrderTests.cs',
  '''   Give(run.pack,("rifle_receiver",1),("scrap_alloy",6),("copper_filament",3),("nanite_residue",4));   // the field toolkit is in the starting pack
   run.Craft("recipe_field_rifle");
   run.collected.Add("warden_plate_carrier");''',
  '''   Give(run.pack,("alloy_plate",7),("padded_liner",4),("strap_webbing",9),("rivet_stock",8),("copper_filament",2));
   foreach(var piece in new[]{"recipe_field_helmet","recipe_field_armguards","recipe_field_gloves","recipe_field_leggings"})run.Craft(piece);
   Give(run.pack,("rifle_receiver",1),("scrap_alloy",6),("copper_filament",3),("nanite_residue",4));   // the field toolkit is in the starting pack
   run.Craft("recipe_field_rifle");
   run.collected.Add("warden_plate_carrier");'''),
 ('Tests/Editor/FieldOrderTests.cs',
  '''new[]{"order_steady_hands","order_long_arm","order_plate_carrier","order_keep_charge","order_bore_true"}));''',
  '''new[]{"order_steady_hands","order_kit_helmet","order_kit_arms","order_kit_hands","order_kit_legs","order_long_arm","order_plate_carrier","order_keep_charge","order_bore_true"}));'''),
 ('Tests/Editor/FieldOrderTests.cs',
  '''   Assert.That(copy.Index,Is.EqualTo(1));Assert.That(copy.TestFired("order_steady_hands"));
''',
  '''   Assert.That(copy.Index,Is.EqualTo(1));Assert.That(copy.TestFired("order_steady_hands"));
   // 3 Oct 2026: the save names the current order; the id wins over the index (orders were inserted), unknown ids fall back
   Assert.That(run.orders.Capture().id,Is.EqualTo("order_kit_helmet"));
   copy.Restore(new FieldOrderState{index=1,id="order_long_arm"});Assert.That(copy.Current.id,Is.EqualTo("order_long_arm"));
   copy.Restore(new FieldOrderState{index=2,id="order_retired"});Assert.That(copy.Index,Is.EqualTo(2));
   copy.Restore(new FieldOrderState{index=3,id=FieldOrderState.FreePlayId});Assert.That(copy.FreePlay);
   copy.Restore(JsonUtility.FromJson<FieldOrderState>("{\\"index\\":1,\\"testFired\\":[]}"));Assert.That(copy.Index,Is.EqualTo(1),"older saves keep their index");
'''),
 ('Tests/Editor/SalvageShopTests.cs',
  '''Is.EqualTo(new[]{"order_steady_hands","order_long_arm"}),"the grip and the rifle orders ask for the visit");''',
  '''Is.EqualTo(new[]{"order_steady_hands","order_kit_helmet","order_long_arm"}),"the grip, the Warden helm and the rifle orders ask for the visit");'''),
 ('Tests/Editor/ShopSellTests.cs',
  '''Is.EquivalentTo(new[]{"droid_servo_damaged","scrap_alloy","nanite_residue","copper_filament","micro_capacitor","optic_lens_cracked"}));
  }''',
  '''Is.EquivalentTo(new[]{"droid_servo_damaged","scrap_alloy","nanite_residue","copper_filament","micro_capacitor","optic_lens_cracked","strap_webbing","padded_liner","rivet_stock"}));
  }'''),
 ('Tests/Editor/GameplayV2FixesTests.cs',
  '''   Assert.That(v2.Count,Is.EqualTo(19));   // 2 Oct 2026: + the Warden rifle receiver''',
  '''   Assert.That(v2.Count,Is.EqualTo(22));   // 2 Oct 2026: + the Warden rifle receiver; 3 Oct: + webbing, liner, rivets'''),
 ('Tests/Editor/HudPanelsTests.cs',
  '''"WEAPONS","WEAPON MODS"}));''',
  '''"WEAPONS","WEAPON MODS","ARMOUR"}));'''),
 ('Tests/Editor/PackPanelTests.cs',
  '''Is.EqualTo(new[]{"ALL","COMPONENTS","MARK I","MARK II","WEAPONS","WEAPON MODS"}));''',
  '''Is.EqualTo(new[]{"ALL","COMPONENTS","MARK I","MARK II","WEAPONS","WEAPON MODS","ARMOUR"}));'''),
 ('Tests/Editor/RecipeChainTests.cs',
  '''   Assert.That(model.Acquire("foreman_control_core").Select(r=>r.id),Is.EquivalentTo(new[]{"recipe_grip_gyro_braced","recipe_barrel_lattice_focused","recipe_cell_overclocked"}));
   Assert.That(model.KnownRecipes.Count,Is.EqualTo(Data().recipes.Length));''',
  '''   Assert.That(model.Acquire("foreman_control_core").Select(r=>r.id),Is.EquivalentTo(new[]{"recipe_grip_gyro_braced","recipe_barrel_lattice_focused","recipe_cell_overclocked"}));
   // 3 Oct 2026: each Warden Kit order reveals its armour schematic (alloy plate is already known here)
   Assert.That(model.OrderStarted("order_kit_helmet").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_helmet"}));
   Assert.That(model.OrderStarted("order_kit_arms").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_armguards"}));
   Assert.That(model.OrderStarted("order_kit_hands").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_gloves"}));
   Assert.That(model.OrderStarted("order_kit_legs").Select(r=>r.id),Is.EqualTo(new[]{"recipe_field_leggings"}));
   Assert.That(model.KnownRecipes.Count,Is.EqualTo(Data().recipes.Length));'''),
 ('Tests/Editor/SaveGameTests.cs',
  '''  [Test] public void FullRoundTripRestoresEveryStateMachine()
  {
   string path;''',
  '''  [Test] public void FullRoundTripRestoresEveryStateMachine()
  {
   string path;int carrier=System.Array.FindIndex(Orders().orders,o=>o.id=="order_plate_carrier");   // 3 Oct 2026: index 6 after the kit orders'''),
 ('Tests/Editor/SaveGameTests.cs',
  '''    a.orders.Restore(new FieldOrderState{index=2,testFired=new[]{"order_steady_hands"}});''',
  '''    a.orders.Restore(new FieldOrderState{index=carrier,testFired=new[]{"order_steady_hands"}});'''),
 ('Tests/Editor/SaveGameTests.cs',
  '''Does.StartWith("Field order 3/7 · Plate Carrier · 37 cr"));''',
  '''Does.StartWith($"Field order {carrier+1}/{Orders().orders.Length} · Plate Carrier · 37 cr"));'''),
 ('Tests/Editor/SaveGameTests.cs',
  '''     Assert.That(b.orders.Progress.Index,Is.EqualTo(2));''',
  '''     Assert.That(b.orders.Progress.Index,Is.EqualTo(carrier));'''),
]
NEW_FILES = ['Tests/Editor/WardenKitTests.cs', 'Tests/Editor/WardenKitTests.cs.meta']


def backup(rel):
    if not live: return
    src, dst = A / rel, HERE.parent / 'backup' / rel
    if src.exists() and not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)


texts, log, bad = {}, [], False
for rel, old, new in EDITS:
    s = texts.setdefault(rel, (A / rel).read_text())
    if new in s: log.append(f'present  {rel}: {new.strip().splitlines()[0][:70]}')
    elif s.count(old) == 1: texts[rel] = s.replace(old, new, 1); log.append(f'apply    {rel}: {new.strip().splitlines()[0][:70]}')
    else: bad = True; log.append(f'MISSING  {rel} ({s.count(old)} matches): {old.strip().splitlines()[0][:70]}')
for rel in NEW_FILES:
    src, dst = HERE / 'files' / rel, A / rel
    log.append(('present  ' if dst.exists() and dst.read_bytes() == src.read_bytes() else 'create   ') + rel)
print('\n'.join(log))
if bad: sys.exit('some edits did not match; nothing written')
if args.check: sys.exit(0)
for rel, s in texts.items():
    if (A / rel).read_text() != s: backup(rel); (A / rel).write_text(s); print('wrote', rel)
for rel in NEW_FILES:
    src, dst = HERE / 'files' / rel, A / rel
    if not dst.exists() or dst.read_bytes() != src.read_bytes(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst); print('wrote', rel)
