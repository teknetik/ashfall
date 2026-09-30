using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
namespace AthenHill
{
 /// Ward save game: one versioned JSON file (credits, pack, fitted mods, schematics, craft counts, the primer step and
 /// pistol, field-order progress, loot bad-luck counters and generator state, city-visit checklist).
 /// Autosaves after fabrication, fitting/removal, salvage pickups, completed orders and trades, and on quit.
 /// Continue restores every state machine consistently; an unreadable or newer save falls back to a new game with a
 /// notice and is kept aside, never deleted.
 [RequireComponent(typeof(GameSession))]
 public class WardSaveGame:MonoBehaviour
 {
  public string fileName="ward-save.json";
  [Tooltip("Tests and tools can point saves at another folder. Empty = Application.persistentDataPath (development QA runs with --athen-qa use <qa folder>/save).")]
  public string directoryOverride;
  public GameSession Session {get;private set;}
  CraftingSession crafting;FieldOrders orders;BermsTutorial tutorial;PlayerCombat combat;
  bool dirty,subscribed,applying;
  public string LastError {get;private set;}
  public string LastSaveReason {get;private set;}
  public int SaveCount {get;private set;}
  /// Raised after a successful write (argument: reason).
  public event Action<string> Saved;
  public string SaveDirectory
  {
   get
   {
    if(!string.IsNullOrEmpty(directoryOverride))return directoryOverride;
    var args=Environment.GetCommandLineArgs();
    int i=Array.IndexOf(args,"--athen-save-dir");if(i>=0&&i+1<args.Length)return Path.GetFullPath(args[i+1]);
    if(Debug.isDebugBuild){i=Array.IndexOf(args,"--athen-qa");if(i>=0&&i+1<args.Length)return Path.Combine(Path.GetFullPath(args[i+1]),"save");}
    return Application.persistentDataPath;
   }
  }
  public string SavePath=>Path.Combine(SaveDirectory,fileName);
  public bool HasSave=>File.Exists(SavePath);
  public bool Ready=>Bind()&&Session.Shop!=null&&crafting&&crafting.Model!=null&&crafting.Loot!=null&&(!orders||orders.Progress!=null||orders.data);
  bool bound;
  bool Bind()
  {
   if(!Session)Session=GetComponent<GameSession>();
   if(!Session)return false;
   if(bound&&crafting)return true;
   bound=true;
   if(!crafting)crafting=GetComponent<CraftingSession>();
   if(!orders)orders=GetComponent<FieldOrders>();
   if(!tutorial)tutorial=orders&&orders.tutorial?orders.tutorial:FindAnyObjectByType<BermsTutorial>();
   if(!combat)combat=crafting&&crafting.combat?crafting.combat:FindAnyObjectByType<PlayerCombat>();
   return true;
  }
  IEnumerator Start()
  {
   Bind();
   while(!Ready)yield return null;
   Subscribe();
  }
  void Subscribe()
  {
   if(subscribed||!Ready)return;subscribed=true;
   crafting.Model.Changed+=MarkDirty;crafting.Collected+=OnCollected;Session.Traded+=MarkDirty;
   if(orders)orders.Completed+=OnOrderCompleted;
  }
  void OnDestroy()
  {
   if(!subscribed)return;
   if(crafting){if(crafting.Model!=null)crafting.Model.Changed-=MarkDirty;crafting.Collected-=OnCollected;}
   if(Session)Session.Traded-=MarkDirty;
   if(orders)orders.Completed-=OnOrderCompleted;
  }
  void MarkDirty(){if(!applying)dirty=true;}
  void OnCollected(LootPickup _)=>MarkDirty();
  void OnOrderCompleted(FieldOrder _)=>MarkDirty();
  // Coalesce every change in a frame into one write.
  void LateUpdate(){if(dirty&&Session&&Session.HasStarted){dirty=false;SaveNow("autosave");}}
  void OnApplicationQuit(){if(Session&&Session.HasStarted&&Ready)SaveNow("quit");}

  public WardSaveData Capture()
  {
   Bind();var shop=Session.Shop;
   return new WardSaveData
   {
    version=WardSaveData.CurrentVersion,savedUtc=DateTime.UtcNow.ToString("o"),build=Application.version,
    credits=shop.Credits,purchases=shop.Purchases,sales=shop.Sales,
    items=shop.Carried.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>new ItemStack(x.Key,x.Value)).ToArray(),
    crafting=crafting.Model.Capture(),loot=crafting.Loot.Capture(),
    bermsStep=tutorial?tutorial.Step.ToString():BermsStep.Approach.ToString(),hasPistol=combat&&combat.hasPistol,
    orders=orders?orders.Capture():null,city=Session.CaptureCityVisit()
   };
  }
  public bool SaveNow(string reason)
  {
   if(!Ready)return false;
   try{WardSaveFile.Write(SavePath,Capture());LastError=null;LastSaveReason=reason;SaveCount++;Saved?.Invoke(reason);return true;}
   catch(Exception e)when(e is IOException||e is UnauthorizedAccessException)
   {LastError=e.Message;Debug.LogWarning("Ward save failed: "+e.Message);return false;}
  }
  /// Restores a parsed save into the running session. Returns what could not be restored (unknown IDs etc.).
  public List<string> Apply(WardSaveData data)
  {
   Bind();var skipped=new List<string>();
   applying=true;
   try
   {
    var known=new HashSet<string>(Session.catalog.items.Select(x=>x.id));
    if(data.items!=null)skipped.AddRange(data.items.Where(x=>x!=null&&!known.Contains(x.itemId)).Select(x=>x.itemId));
    Session.Shop.Restore(data.credits,data.purchases,data.sales,data.items?.Where(x=>x!=null).Select(x=>new KeyValuePair<string,int>(x.itemId,x.quantity)));
    skipped.AddRange(crafting.Model.Restore(data.crafting));
    if(data.loot!=null&&!crafting.Loot.Restore(data.loot))skipped.Add("loot generator state");
    var step=Enum.TryParse(data.bermsStep,out BermsStep parsed)?parsed:BermsStep.Approach;
    // The pistol is carried exactly from the Draw step on; the save flag cannot contradict the primer.
    if(combat)combat.RestorePistol(step>=BermsStep.Draw);
    if(tutorial)tutorial.Restore(step);
    if(orders)orders.Restore(data.orders);
    Session.RestoreCityVisit(data.city);
   }
   finally{applying=false;dirty=false;}
   return skipped;
  }
  /// Start-menu Continue. Unreadable saves are moved aside and a new game starts with a notice.
  public bool Continue()
  {
   if(!Ready||Session.State!=CityState.MainMenu)return false;
   if(!WardSaveFile.TryRead(SavePath,out var data,out var error))
   {
    string kept=QuarantineSave();
    Session.StartGame();
    Session.Notify($"Your saved game could not be loaded ({error}), so a new game has started."+(kept!=null?" The unreadable file was kept beside your saves, not deleted.":""),"Ward");
    SaveNow("new game after unreadable save");
    return false;
   }
   var skipped=Apply(data);
   Session.StartGame();
   var o=orders&&orders.Progress!=null?orders.Progress.Current:null;
   Session.Notify("Welcome back to Ward. Progress restored"+(o!=null?$" · field order: {o.title}":"")+"."+(skipped.Count>0?" Some saved entries no longer exist and were skipped: "+string.Join(", ",skipped.Distinct())+".":""),"Ward");
   return true;
  }
  /// Start-menu New Game (after the menu's overwrite confirmation). The previous save is kept as a .previous copy.
  public void NewGame()
  {
   if(!Ready||Session.State!=CityState.MainMenu)return;
   if(HasSave)
   {
    try{File.Copy(SavePath,Path.Combine(SaveDirectory,Path.GetFileNameWithoutExtension(fileName)+".previous.json"),true);}
    catch(Exception e)when(e is IOException||e is UnauthorizedAccessException){Debug.LogWarning("Could not keep the previous save: "+e.Message);}
   }
   Session.StartGame();
   SaveNow("new game");
  }
  string QuarantineSave()
  {
   try
   {
    if(!File.Exists(SavePath))return null;
    string kept=Path.Combine(SaveDirectory,Path.GetFileNameWithoutExtension(fileName)+".unreadable-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")+".json");
    File.Move(SavePath,kept);return kept;
   }
   catch(Exception e)when(e is IOException||e is UnauthorizedAccessException){Debug.LogWarning("Could not move the unreadable save aside: "+e.Message);return null;}
  }
  /// One line for the start menu, e.g. "Field order 3/5 · Bore It True · saved 29 Sep 23:41". Null without a save.
  public string Summary()
  {
   Bind();if(!HasSave)return null;
   if(!WardSaveFile.TryRead(SavePath,out var data,out _))return "The saved game cannot be read; Continue starts a new game.";
   var set=orders?orders.data:null;string progress;
   int index=data.orders?.index??-1;
   if(set!=null&&index>=0&&index<set.orders.Length)progress=$"Field order {index+1}/{set.orders.Length} · {set.orders[index].title}";
   else if(set!=null&&index>=set.orders.Length)progress="Free hunting in the Outer Berms";
   else progress=Enum.TryParse(data.bermsStep,out BermsStep s)&&s>BermsStep.Approach?"Outer Berms primer":"Arrived at West Gate";
   string when=DateTime.TryParse(data.savedUtc,null,System.Globalization.DateTimeStyles.RoundtripKind,out var t)?" · saved "+t.ToLocalTime().ToString("d MMM HH:mm"):"";
   return progress+$" · {data.credits} cr"+when;
  }
 }
}
