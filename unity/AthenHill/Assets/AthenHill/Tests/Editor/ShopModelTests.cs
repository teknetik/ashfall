using NUnit.Framework;
namespace AthenHill.Tests
{
 public class ShopModelTests
 {
  static ItemSpec[] Items()=>new[]{new ItemSpec{id="water_flask",name="Water Flask",buyPrice=4,sellPrice=2},new ItemSpec{id="medkit",name="Medkit",buyPrice=9,sellPrice=4},new ItemSpec{id="scrap_coil",name="Scrap Coil",buyPrice=2,sellPrice=1,startingQuantity=1}};
  [Test]public void BuyAndSellEachTransferExactlyOne(){var s=new ShopModel(Items());Assert.That(s.Trade("water_flask",true,out _));Assert.That(s.Credits,Is.EqualTo(21));Assert.That(s.Quantity("water_flask"),Is.EqualTo(1));Assert.That(s.Trade("scrap_coil",false,out _));Assert.That(s.Credits,Is.EqualTo(22));Assert.That(s.Quantity("scrap_coil"),Is.Zero);Assert.That(s.Purchases,Is.EqualTo(1));Assert.That(s.Sales,Is.EqualTo(1));}
  [Test]public void FailedTradesDoNotChangeAnyBalance(){var s=new ShopModel(Items(),3);Assert.That(s.Trade("water_flask",true,out _),Is.False);Assert.That(s.Trade("medkit",false,out _),Is.False);Assert.That(s.Trade("unknown",true,out _),Is.False);Assert.That(s.Trade(null,false,out _),Is.False);Assert.That(s.Credits,Is.EqualTo(3));Assert.That(s.Quantity("scrap_coil"),Is.EqualTo(1));Assert.That(s.Purchases+s.Sales,Is.Zero);}
  [Test]public void OverflowCannotLoseAnItem(){var s=new ShopModel(Items(),int.MaxValue);Assert.That(s.Trade("scrap_coil",false,out _),Is.False);Assert.That(s.Credits,Is.EqualTo(int.MaxValue));Assert.That(s.Quantity("scrap_coil"),Is.EqualTo(1));Assert.That(s.Sales,Is.Zero);}
  [Test]public void CatalogEditsCannotMutateAnExistingSession(){var data=Items();var s=new ShopModel(data);data[0].buyPrice=100;Assert.That(s.Trade("water_flask",true,out _));Assert.That(s.Credits,Is.EqualTo(21));}
 }
}
