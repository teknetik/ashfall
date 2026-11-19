using System.IO;
using NUnit.Framework;
using UnityEditor;
namespace AthenHill.Tests
{
 /// 19 Nov 2026: the player arrives (spawn, R, Continue) at the +X arches, now called the East Gate; "West Gate" is
 /// only the -X Berms portal by the market (record: art/gate_names_20261119/README.md).
 public class GateNamesTests
 {
  const string Ui="Assets/AthenHill/UI/";

  [Test] public void MenusAndPausePanelNameTheEastGate()
  {
   var hud=File.ReadAllText(Ui+"CityHUD.uxml");var menu=File.ReadAllText(Ui+"StartupMenu.uxml");
   Assert.That(hud,Does.Contain("text=\"Return to East Gate\""));Assert.That(hud,Does.Contain("R · Return to East Gate"));
   Assert.That(menu,Does.Contain("Resume your saved game at East Gate"));Assert.That(menu,Does.Contain("Enter the city at East Gate"));
   Assert.That(hud+menu,Does.Not.Contain("West Gate"),"the spawn is not the West Gate");
  }

  [Test] public void CatalogNotesNameTheEastGate()
  {
   var catalog=AssetDatabase.LoadAssetAtPath<CityCatalog>("Assets/AthenHill/Data/CityCatalog.asset");
   Assert.That(catalog,Is.Not.Null);
   Assert.That(catalog.notes,Does.Contain("R returns to East Gate."));Assert.That(catalog.notes,Does.Not.Contain("West Gate"));
  }
 }
}
