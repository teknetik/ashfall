using UnityEngine;

namespace AthenHill
{
    // CharacterController has no Rigidbody interpolation. Keep its simulation pose
    // authoritative, and present the last two completed steps at render cadence.
    public sealed class PlayerRenderPose
    {
        Vector3 previousPosition, position;
        Quaternion previousRotation = Quaternion.identity, rotation = Quaternion.identity;
        public Quaternion SimulationRotation => rotation;

        public void Reset(Vector3 newPosition, Quaternion newRotation)
        {
            previousPosition = position = newPosition;
            previousRotation = rotation = newRotation;
        }

        public void Record(Vector3 newPosition, Quaternion newRotation)
        {
            previousPosition = position;
            previousRotation = rotation;
            position = newPosition;
            rotation = newRotation;
        }

        public static float Fraction(double renderTime, double fixedTime, float fixedStep)
        {
            return fixedStep > 0 ? Mathf.Clamp01((float)((renderTime - fixedTime) / fixedStep)) : 1;
        }

        public Vector3 Position(float fraction) => Vector3.Lerp(previousPosition, position, fraction);
        public Quaternion Rotation(float fraction) => Quaternion.Slerp(previousRotation, rotation, fraction);
    }
}
