using UnityEngine;
namespace AthenHill
{
    [DisallowMultipleComponent]
    public class ActorAnimation : MonoBehaviour
    {
        public Animation animationSource;
        [Tooltip("Optional Humanoid controller with idle, walk and run states. Existing legacy actors continue using Animation.")]
        public Animator humanoidAnimator;
        public AnimationClip idle, walk, run, talk;
        [Header("Grounded jump presentation")]
        public AnimationClip jumpTakeoff, jumpAirborne, jumpFall, jumpLanding, jumpLandingMoving;
        [Min(.01f)] public float takeoffSeconds = .12f, landingSeconds = .24f;
        [Range(0,1)] public float idlePhase;
        [Min(.01f)] public float walkStrideSpeed=1.503112134f, runStrideSpeed=3.610416400f;
        [Min(0)] public float blendSeconds=.15f;
        public string CurrentClip {get;private set;} = "idle";
        public ActorAirPhase AirPhase => air.Phase;
        public float AirTime => air.AirTime;
        public float ImpactSpeed => air.ImpactSpeed;
        readonly ActorAirMotion air = new ActorAirMotion();
        AnimationClip previousClip;
        bool previousGait;
        bool initialized;
        void Awake()
        {
            Initialize();
        }
        void Initialize()
        {
            if(initialized)return;
            initialized=true;
            if(humanoidAnimator){SetMotion(0,false,false);return;}
            if(!animationSource) animationSource=GetComponentInChildren<Animation>();
            if(!animationSource)return;
            foreach(var clip in new[]{idle,walk,run,talk})
            {
                if(!clip) continue;
                animationSource.AddClip(clip,clip.name);
                animationSource[clip.name].wrapMode=WrapMode.Loop;
            }
            foreach(var clip in new[]{jumpTakeoff,jumpAirborne,jumpFall,jumpLanding,jumpLandingMoving})
            {
                if(!clip)continue;
                animationSource.AddClip(clip,clip.name);
                animationSource[clip.name].wrapMode=WrapMode.ClampForever;
            }
            SetMotion(0,false,false);
            if(idle && animationSource[idle.name]!=null)
                animationSource[idle.name].normalizedTime=idlePhase;
        }
        public void SetMotion(float speed,bool running,bool talking)
        {
            if(humanoidAnimator)
            {
                string state=talking||speed<=.05f?"idle":running?"run":"walk";
                humanoidAnimator.speed=speed>.05f?speed/(running?runStrideSpeed:walkStrideSpeed):1;
                if(CurrentClip!=state)humanoidAnimator.CrossFadeInFixedTime(state,blendSeconds);
                CurrentClip=state;return;
            }
            var clip=talking?talk:speed>.05f?(running?run:walk):idle;
            PlayLegacy(clip,talking||speed<=.05f?1:speed/Mathf.Max(.01f,running?runStrideSpeed:walkStrideSpeed),!talking&&speed>.05f,false);
        }

        public void SetGroundMotion(float speed, bool running, bool talking, bool grounded,
            float verticalSpeed, bool jumpAccepted, float dt)
        {
            Initialize();
            var oldPhase=air.Phase;
            bool movingLanding=speed>.5f&&jumpLandingMoving;
            float recovery=movingLanding?landingSeconds/Mathf.Max(.5f,speed/runStrideSpeed):landingSeconds;
            air.Step(grounded,jumpAccepted,verticalSpeed,dt,takeoffSeconds,recovery);
            AnimationClip clip=null;
            switch(air.Phase)
            {
                case ActorAirPhase.Takeoff:clip=jumpTakeoff;break;
                case ActorAirPhase.Rising:clip=jumpAirborne;break;
                case ActorAirPhase.Falling:clip=jumpFall?jumpFall:jumpAirborne;break;
                case ActorAirPhase.Landing:clip=movingLanding?jumpLandingMoving:jumpLanding;break;
            }
            if(!clip){SetMotion(speed,running,talking);return;}
            float rate=air.Phase==ActorAirPhase.Takeoff?clip.length/Mathf.Max(.01f,takeoffSeconds):
                air.Phase==ActorAirPhase.Landing?clip.length/Mathf.Max(.01f,recovery):1;
            PlayLegacy(clip,rate,false,jumpAccepted||oldPhase!=air.Phase);
        }

        public void ResetGroundMotion()
        {
            air.Reset();
            previousClip=null;
            previousGait=false;
            if(animationSource)animationSource.Stop();
            SetMotion(0,false,false);
        }

        void PlayLegacy(AnimationClip clip,float rate,bool gait,bool restart)
        {
            if(!animationSource || !clip || animationSource[clip.name]==null)return;
            var state=animationSource[clip.name];
            if(previousClip!=clip || restart || !animationSource.IsPlaying(clip.name))
            {
                // Walk/run use the same footfall phase, so changing speed does not swap the support foot.
                float phase=gait&&previousGait&&previousClip&&animationSource[previousClip.name]!=null?
                    Mathf.Repeat(animationSource[previousClip.name].normalizedTime,1):0;
                if(gait&&previousClip==jumpLandingMoving&&run)
                    phase=Mathf.Repeat(animationSource[previousClip.name].time/run.length,1);
                state.normalizedTime=phase;
                float fade=(clip==jumpTakeoff||clip==jumpLanding||clip==jumpLandingMoving)?Mathf.Min(blendSeconds,.065f):blendSeconds;
                animationSource.CrossFade(clip.name,fade);
            }
            state.speed=rate;
            CurrentClip=clip.name;
            previousClip=clip;
            previousGait=gait;
        }
    }
}
