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
        [Min(.01f)] public float walkStrideSpeed=1.503112134f, runStrideSpeed=3.610416400f;
        [Min(0)] public float blendSeconds=.15f;
        public string CurrentClip {get;private set;} = "idle";
        void Awake()
        {
            if(humanoidAnimator){SetMotion(0,false,false);return;}
            if(!animationSource) animationSource=GetComponentInChildren<Animation>();
            foreach(var clip in new[]{idle,walk,run,talk})
            {
                if(!clip) continue;
                animationSource.AddClip(clip,clip.name);
                animationSource[clip.name].wrapMode=WrapMode.Loop;
            }
            SetMotion(0,false,false);
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
            if(!animationSource) return;
            var clip=talking?talk:speed>.05f?(running?run:walk):idle;
            if(!clip || animationSource[clip.name]==null) return;
            CurrentClip=clip.name;
            animationSource[clip.name].speed=talking||speed<=.05f?1:speed/(running?runStrideSpeed:walkStrideSpeed);
            if(!animationSource.IsPlaying(clip.name)) animationSource.CrossFade(clip.name,blendSeconds);
        }
    }
}
