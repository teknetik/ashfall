using System;
using System.Collections.Generic;
namespace AthenHill
{
 /// Radio lines (Warden briefings) on their own channel: one line at a time, each on screen long enough to read
 /// (time scales with its word count), later lines wait their turn, and nothing else can overwrite them.
 /// The clock only runs while the city is in play, so a line that arrives during a menu is still there afterwards.
 /// Pure C#: GameSession supplies the elapsed time.
 public sealed class RadioQueue
 {
  public struct Line{public string text,speaker,tag;public float seconds,gapBefore;public bool urgent;}
  [Serializable]public class Timing
  {
   [UnityEngine.Tooltip("Seconds every radio line stays up, plus Seconds Per Word.")]
   [UnityEngine.Min(0)]public float baseSeconds=2.5f;
   [UnityEngine.Tooltip("Reading time per word (0.3 s ≈ 200 words a minute).")]
   [UnityEngine.Min(0)]public float secondsPerWord=.3f;
   [UnityEngine.Min(.5f)]public float minSeconds=5,maxSeconds=24;
   public float For(string text)=>Math.Min(maxSeconds,Math.Max(minSeconds,baseSeconds+secondsPerWord*Words(text)));
  }
  readonly List<Line> pending=new List<Line>();
  Line current;float remaining,gap;
  public Timing timing=new Timing();
  /// Lines whose tag this returns true for are stale: dropped from the queue instead of being shown (e.g. the
  /// briefing of a field order the player has already completed).
  public Func<string,bool> IsStale;
  public bool Showing=>current.text!=null&&gap<=0;
  public string Text=>Showing?current.text:null;
  public string Speaker=>Showing?current.speaker:null;
  public string Tag=>current.text!=null?current.tag:null;
  public float Remaining=>Showing?remaining:0;
  public int Pending=>pending.Count;
  public IEnumerable<string> PendingTags{get{foreach(var l in pending)yield return l.tag;}}
  public static int Words(string text)
  {
   if(string.IsNullOrWhiteSpace(text))return 0;
   int n=0;bool word=false;
   foreach(char c in text){bool w=!char.IsWhiteSpace(c);if(w&&!word)n++;word=w;}
   return n;
  }
  /// Queues a line. Returns true when it shows immediately. A line identical to the one showing or queued is ignored.
  /// tag names what the line is about (FieldOrders: "order:INDEX:brief|done") so it can be dropped once stale.
  /// urgent (time-critical combat lines) jumps the queue: it shows at once, and an interrupted ordinary line resumes
  /// afterwards; urgent lines queue only behind other urgent lines.
  public bool Say(string text,string speaker,float gapBefore=0,string tag=null,bool urgent=false)
  {
   if(string.IsNullOrWhiteSpace(text))return false;
   if(current.text==text&&current.speaker==speaker)return false;
   foreach(var l in pending)if(l.text==text&&l.speaker==speaker)return false;
   var line=new Line{text=text,speaker=speaker,tag=tag,urgent=urgent,seconds=timing.For(text),gapBefore=urgent?0:Math.Max(0,gapBefore)};
   if(current.text==null){Begin(line);return gap<=0;}
   if(urgent)
   {
    if(current.urgent){int i=0;while(i<pending.Count&&pending[i].urgent)i++;pending.Insert(i,line);return false;}
    // Interrupt: the ordinary line resumes after the urgent one (if it has anything left worth showing).
    if(Showing&&remaining>1.5f){var resume=current;resume.seconds=Math.Max(remaining,timing.minSeconds*.6f);resume.gapBefore=0;pending.Insert(0,resume);}
    else if(!Showing){var waiting=current;pending.Insert(0,waiting);}
    Begin(line);return true;
   }
   pending.Add(line);return false;
  }
  void Begin(Line line){current=line;remaining=line.seconds;gap=line.gapBefore;}
  /// Starts the next line that is not stale; clears the channel when none is left.
  bool Next()
  {
   while(pending.Count>0)
   {
    var line=pending[0];pending.RemoveAt(0);
    if(line.tag!=null&&IsStale!=null&&IsStale(line.tag))continue;
    Begin(line);return true;
   }
   current=default;return true;
  }
  /// Removes queued lines that are stale now (and the current line while it is still waiting out its gap).
  /// Returns how many were dropped. A line already on screen is left to finish.
  public int Drop(Func<string,bool> stale=null)
  {
   stale??=IsStale;if(stale==null)return 0;
   int n=pending.RemoveAll(l=>l.tag!=null&&stale(l.tag));
   if(current.text!=null&&gap>0&&current.tag!=null&&stale(current.tag)){n++;Next();}
   return n;
  }
  /// Advances the clock while playing. Returns true when the visible line changed (appeared, advanced or cleared).
  public bool Tick(float dt,bool playing)
  {
   if(!playing||current.text==null||dt<=0)return false;
   if(gap>0){gap-=dt;return gap<=0;}
   remaining-=dt;
   if(remaining>0)return false;
   return Next();
  }
  public void Clear(){pending.Clear();current=default;remaining=gap=0;}
 }
}
