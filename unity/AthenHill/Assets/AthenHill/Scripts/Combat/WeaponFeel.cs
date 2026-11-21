using UnityEngine;
namespace AthenHill
{
 /// Pure handling rules (Steady Hands bench, 20 Nov 2026; DESIGN.md section 10). The numbers come from the weapon's
 /// handling stats (WeaponStats sway, sideKick, recovery, scatterGrowth); these functions only shape them over time.
 ///  - Heat: each shot adds scatterGrowth; heat halves every HalfLife seconds; the shot cone is multiplied by 1 + heat.
 ///    The first shot of a string (heat 0) has exactly today's cone, so an aimed first shot is as accurate as before.
 ///  - Idle sway: a slow figure of eight (Lissajous 1:2) plus a small tremor whose share grows with the amplitude, so a
 ///    steady weapon (low sway) has almost no tremor. Visual only: it moves the held weapon, never the camera or the shot.
 public static class WeaponFeel
 {
  /// Seconds for rapid-fire heat to halve.
  public const float HalfLife=.35f;
  /// Heat cap: the cone never grows past (1 + MaxHeat) times its base.
  public const float MaxHeat=1.5f;
  /// Sway at or above this (degrees) has a full tremor; below, the tremor fades with the square of the ratio.
  public const float TremorFrom=1f;
  public static float Decay(float heat,float seconds)=>heat<=0?0:heat*Mathf.Pow(.5f,Mathf.Max(0,seconds)/HalfLife);
  /// Heat after a shot fired sinceLast seconds after the previous one.
  public static float HeatAfterShot(float heat,float sinceLast,float growth)=>Mathf.Min(MaxHeat,Decay(heat,sinceLast)+Mathf.Max(0,growth));
  public static float ScatterScale(float heat)=>1+Mathf.Clamp(heat,0,MaxHeat);
  /// Idle sway offset in degrees (x = yaw, y = pitch) at time t for amplitude degrees. Period about 3.2 s for the
  /// figure of eight; the tremor is a few Hz of layered sines.
  public static Vector2 Sway(float t,float amplitude)
  {
   if(amplitude<=0)return Vector2.zero;
   const float w=1.96f; // rad/s: 3.2 s period
   var eight=new Vector2(Mathf.Sin(w*t),Mathf.Sin(2*w*t)*.5f);
   float tremor=Mathf.Clamp01(amplitude/TremorFrom);tremor*=tremor;
   var shake=new Vector2(Mathf.Sin(t*23.1f)+.6f*Mathf.Sin(t*37.7f+1.3f),Mathf.Sin(t*19.3f+.7f)+.6f*Mathf.Sin(t*41.9f))*.06f*tremor;
   return (eight+shake)*amplitude;
  }
  /// Signed sideways kick for one shot: a random side with a magnitude between 60 and 100 percent of sideKick.
  public static float SideKick(float sideKick,float random01,float randomSign)=>sideKick<=0?0:sideKick*Mathf.Lerp(.6f,1f,Mathf.Clamp01(random01))*(randomSign<.5f?-1:1);
 }
}
