using System;
using System.IO;
using UnityEngine;
namespace AthenHill
{
 /// flags (1 Oct 2026): story flags set by dialogue choices; absent in older saves (none set).
 [Serializable] public class CityVisitState {public bool visitedHill,boughtFlask,soldScrap,linked;public string[] spoken;public string selectedDestination;public string[] flags;}
 /// Everything a Ward save restores. JsonUtility-friendly (arrays of plain records, no dictionaries).
 /// Version 4 (5 Oct 2026) adds the hotbar assignments, the home locker and the tracked journal mission; v3 saves load
 /// with the default hotbar (3 medkit, 4 nano cell), an empty locker and an automatically tracked mission. Earlier
 /// builds refuse a v4 save, so the locker's contents are never dropped by an older reader.
 /// Version 3 preserves nested implant/armour components; earlier builds reject it rather than losing modules.
 /// Version 2 adds character progression and equipment. Version 1 starts with the catalog's character defaults.
 /// Player position is not saved: a loaded game resumes at West Gate, or at the home bunk once the player has rested there.
 [Serializable] public class WardSaveData
 {
  public const int CurrentVersion=4;
  public int version;
  public string savedUtc,build;
  public int credits,purchases,sales;
  public ItemStack[] items;
  public CraftingState crafting;
  public LootState loot;
  public string bermsStep;
  public bool hasPistol;
  public FieldOrderState orders;
  public CityVisitState city;
  public CharacterState character;
  public HotbarEntry[] hotbar;
  public ItemStack[] stash;
  public JournalState journal;
 }
 /// Reads and writes save files. Nothing here throws on bad input: unreadable files produce an error message.
 public static class WardSaveFile
 {
  public static string Serialize(WardSaveData data)=>JsonUtility.ToJson(data,true);
  public static bool TryParse(string json,out WardSaveData data,out string error)
  {
   data=null;
   if(string.IsNullOrWhiteSpace(json)){error="the file is empty";return false;}
   if(json.TrimStart()[0]!='{'){error="the file is not a Ward save";return false;}
   try{data=JsonUtility.FromJson<WardSaveData>(json);}
   // Player-facing words only; the exception detail goes to the log.
   catch(Exception e){Debug.LogWarning("Ward save could not be parsed: "+e.Message);error="the file is damaged or incomplete";data=null;return false;}
   if(data==null){error="the file is damaged or incomplete";return false;}
   if(data.version<=0){error="the file is not a Ward save";data=null;return false;}
   if(data.version>WardSaveData.CurrentVersion){Debug.LogWarning($"Ward save version {data.version} is newer than this build reads ({WardSaveData.CurrentVersion}).");error="it was made by a newer build of the game";data=null;return false;}
   if(data.character!=null&&data.character.version>CharacterState.CurrentVersion){error="its character data was made by a newer build of the game";data=null;return false;}
   if(data.credits<0||data.purchases<0||data.sales<0){error="the file is damaged (impossible balances)";data=null;return false;}
   if(!string.IsNullOrEmpty(data.bermsStep)&&!Enum.TryParse(data.bermsStep,out BermsStep _)){error="the file is damaged (unknown Outer Berms progress)";data=null;return false;}
   error=null;return true;
  }
  public static bool TryRead(string path,out WardSaveData data,out string error)
  {
   data=null;
   try{if(!File.Exists(path)){error="no save file";return false;}return TryParse(File.ReadAllText(path),out data,out error);}
   catch(Exception e)when(e is IOException||e is UnauthorizedAccessException){Debug.LogWarning("Ward save read failed: "+e.Message);error="the file could not be opened";return false;}
  }
  /// Writes beside the target, then swaps it in, so a crash mid-write never leaves a half-written save.
  public static void Write(string path,WardSaveData data)
  {
   Directory.CreateDirectory(Path.GetDirectoryName(path));
   string temp=path+".tmp";
   File.WriteAllText(temp,Serialize(data));
   if(File.Exists(path))
   {
    try{File.Replace(temp,path,null);return;}
    catch(Exception e)when(e is PlatformNotSupportedException||e is IOException){File.Copy(temp,path,true);File.Delete(temp);return;}
   }
   File.Move(temp,path);
  }
 }
}
