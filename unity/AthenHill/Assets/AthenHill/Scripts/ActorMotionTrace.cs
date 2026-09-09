using System.Collections.Generic;
using UnityEngine;

namespace AthenHill
{
    // Explicitly started by the existing development QA bridge; release builds cannot record.
    public static class ActorMotionTrace
    {
        static PlayerMotor target;
        static readonly List<object> frames=new List<object>();
        public static void Begin(PlayerMotor player)
        {
            if(!Debug.isDebugBuild&&!Application.isEditor)return;
            frames.Clear();target=player;
        }
        public static object End()
        {
            target=null;
            var result=frames.ToArray();frames.Clear();return result;
        }
        public static void Sample(PlayerMotor player)
        {
            if(target!=player || (!Debug.isDebugBuild&&!Application.isEditor) || frames.Count>=30000)return;
            var a=player.actor;
            frames.Add(new{
                time=Time.fixedTime,dt=Time.fixedDeltaTime,
                position=new[]{player.transform.position.x,player.transform.position.y,player.transform.position.z},
                player.Grounded,player.Speed,player.VerticalSpeed,player.JumpStarted,player.Blocked,player.Talking,
                phase=a?a.AirPhase.ToString():null,clip=a?a.CurrentClip:null,
                clipTime=a&&a.animationSource&&a.animationSource[a.CurrentClip]!=null?a.animationSource[a.CurrentClip].time:0,
                airTime=a?a.AirTime:0,impactSpeed=a?a.ImpactSpeed:0,
                visualForward=new[]{player.visual.forward.x,player.visual.forward.y,player.visual.forward.z}
            });
        }
    }
}
