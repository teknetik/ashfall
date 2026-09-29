using System;
using System.IO;
using UnityEngine;
namespace AthenHill
{
 [Serializable] public class CityVisitState {public bool visitedHill,boughtFlask,soldScrap,linked;public string[] spoken;public string selectedDestination;}
 /// Everything a Ward save restores. JsonUtility-friendly (arrays of plain records, no dictionaries).
 /// Version 1 (29 September 2026). Player position is not saved: a loaded game resumes at West Gate.
 [Serializable] public class WardSaveData
 {
  public const int CurrentVersion=1;
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
 }
 /// Reads and writes save files. Nothing here throws on bad input: unreadable files produce an error message.
 public static class WardSaveFile
 {
  public static string Serialize(WardSaveData data)=>JsonUtility.ToJson(data,true);
  public static bool TryParse(string json,out WardSaveData data,out string error)
  {
   data=null;
   if(string.IsNullOrWhiteSpace(json)){error="the save file is empty";return false;}
   if(json.TrimStart()[0]!='{'){error="the save file is not a Ward save";return false;}
   try{data=JsonUtility.FromJson<WardSaveData>(json);}
   catch(Exception e){error="the save file is damaged ("+e.GetType().Name+")";data=null;return false;}
   if(data==null){error="the save file is damaged";return false;}
   if(data.version<=0){error="the save file has no version (not a Ward save)";data=null;return false;}
   if(data.version>WardSaveData.CurrentVersion){error=$"the save was made by a newer build (save version {data.version}, this build reads {WardSaveData.CurrentVersion})";data=null;return false;}
   if(data.credits<0||data.purchases<0||data.sales<0){error="the save file holds impossible balances";data=null;return false;}
   if(!string.IsNullOrEmpty(data.bermsStep)&&!Enum.TryParse(data.bermsStep,out BermsStep _)){error="the save file names an unknown Outer Berms step";data=null;return false;}
   error=null;return true;
  }
  public static bool TryRead(string path,out WardSaveData data,out string error)
  {
   data=null;
   try{if(!File.Exists(path)){error="no save file";return false;}return TryParse(File.ReadAllText(path),out data,out error);}
   catch(Exception e)when(e is IOException||e is UnauthorizedAccessException){error="the save file could not be opened ("+e.Message+")";return false;}
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
