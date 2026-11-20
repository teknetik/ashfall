using UnityEngine;

namespace AthenHill
{
    /// QA read-out for the weapon-driven first-person rifle hands (20 Nov 2026, rifle_hands_20261120): whether the rifle
    /// view model is weapon-driven, which grip points the arm IKs hold, and how far each hand is from its grip point
    /// (bones as left by the previous frame's LateUpdate). Read by NativeQa's snapshot (combat.rifleHands).
    public static class RifleHandsQa
    {
        public static object State(PlayerCombat combat)
        {
            var vm=combat?combat.rifleViewModel:null;
            if(!vm)return new{available=false};
            SupportHandIK right=null,left=null;
            foreach(var ik in vm.GetComponentsInChildren<SupportHandIK>(true))
            {
                if(!ik.upper)continue;
                if(ik.upper.name=="RightArm")right=ik;else if(ik.upper.name=="LeftArm")left=ik;
            }
            float Err(SupportHandIK k)=>k&&k.hand&&k.rifleGrip?Vector3.Distance(k.hand.position,k.rifleGrip.position)*100f:-1f;
            var arms=vm.GetComponent<ViewModelArmsRig>();
            return new
            {
                available=true,
                visible=vm.Visible,
                aim=vm.AimBlend,
                weaponDriven=arms&&arms.arms&&arms.arms!=vm.rig,
                shootingGrip=right&&right.rifleGrip?right.rifleGrip.name:null,
                supportGrip=left&&left.rifleGrip?left.rifleGrip.name:null,
                rightErrCm=Err(right),
                leftErrCm=Err(left)
            };
        }
    }
}
