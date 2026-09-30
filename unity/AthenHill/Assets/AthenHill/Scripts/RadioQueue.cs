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
  public struct Line{public string text,speaker;public float seconds,gapBefore;}
  [Serializable]public class Timing
  {
   [UnityEngine.Tooltip("Seconds every radio line stays up, plus Seconds Per Word.")]
   [UnityEngine.Min(0)]public float baseSeconds=2.5f;
   [UnityEngine.Tooltip("Reading time per word (0.3 s ≈ 200 words a minute).")]
   [UnityEngine.Min(0)]public float secondsPerWord=.3f;
   [UnityEngine.Min(.5f)]public float minSeconds=5,maxSeconds=24;
   public float For(string text)=>Math.Min(maxSeconds,Math.Max(minSeconds,baseSeconds+secondsPerWord*Words(text)));
  }
  readonly Queue<Line> pending=new Queue<Line>();
  Line current;float remaining,gap;
  public Timing timing=new Timing();
  public bool Showing=>current.text!=null&&gap<=0;
  public string Text=>Showing?current.text:null;
  public string Speaker=>Showing?current.speaker:null;
  public float Remaining=>Showing?remaining:0;
  public int Pending=>pending.Count;
  public static int Words(string text)
  {
   if(string.IsNullOrWhiteSpace(text))return 0;
   int n=0;bool word=false;
   foreach(char c in text){bool w=!char.IsWhiteSpace(c);if(w&&!word)n++;word=w;}
   return n;
  }
  /// Queues a line. Returns true when it shows immediately. A line identical to the one showing or queued is ignored.
  public bool Say(string text,string speaker,float gapBefore=0)
  {
   if(string.IsNullOrWhiteSpace(text))return false;
   if(current.text==text&&current.speaker==speaker)return false;
   foreach(var l in pending)if(l.text==text&&l.speaker==speaker)return false;
   var line=new Line{text=text,speaker=speaker,seconds=timing.For(text),gapBefore=Math.Max(0,gapBefore)};
   if(current.text==null){Begin(line);return gap<=0;}
   pending.Enqueue(line);return false;
  }
  void Begin(Line line){current=line;remaining=line.seconds;gap=line.gapBefore;}
  /// Advances the clock while playing. Returns true when the visible line changed (appeared, advanced or cleared).
  public bool Tick(float dt,bool playing)
  {
   if(!playing||current.text==null||dt<=0)return false;
   if(gap>0){gap-=dt;return gap<=0;}
   remaining-=dt;
   if(remaining>0)return false;
   if(pending.Count>0){Begin(pending.Dequeue());return true;}
   current=default;return true;
  }
  public void Clear(){pending.Clear();current=default;remaining=gap=0;}
 }
}
