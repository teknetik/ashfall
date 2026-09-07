using UnityEngine;
public class ProbeRotation : MonoBehaviour { void Update() { transform.Rotate(0, 45 * Time.deltaTime, 0); } }