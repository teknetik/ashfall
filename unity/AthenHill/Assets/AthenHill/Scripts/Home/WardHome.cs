using UnityEngine;
namespace AthenHill
{
 /// The player's home (5 Oct 2026): the converted container on the south wall (prefab WallHomeP). Linn leases it
 /// (dialogue action "lease_home", the price below); once leased the door opens for the player, the locker opens the
 /// stash window and the bunk the rest window. Story flags (saved): home_asked, home_leased, home_stored, home_rested.
 public class WardHome:MonoBehaviour
 {
  public const string AskedFlag="home_asked",LeasedFlag="home_leased",StoredFlag="home_stored",RestedFlag="home_rested";
  public GameSession session;
  public string displayName="Container home";
  [Tooltip("Credits Linn takes for the lease (her line names forty; change both together).")]
  [Min(0)]public int leasePrice=40;
  [Tooltip("Item stacks the locker holds (no weight limit).")]
  [Min(1)]public int lockerSlots=60;
  [Tooltip("Brann's workbench may use parts stored in the locker once the pack runs short (the pack is always used first).")]
  public bool lockerFeedsBench=true;
  public HomeDoor door;
  [Tooltip("E · Open the locker (stash window). Enabled once leased.")]
  public WorldInteractable locker;
  [Tooltip("E · Rest on the bunk (rest window). Enabled once leased.")]
  public WorldInteractable bunk;
  [Tooltip("Journal marker target for the locker.")]
  public Transform lockerPoint;
  [Tooltip("Floor point (and facing) where the player stands after resting, and where Continue starts once rested.")]
  public Transform wakePoint;
  public bool Leased=>session&&session.HasFlag(LeasedFlag);
  bool shown=true;
  void Start()
  {
   if(!session)session=FindAnyObjectByType<GameSession>();
   if(locker)locker.Used+=OpenLocker;
   if(bunk)bunk.Used+=OpenBunk;
   Sync(true);
  }
  void OnDestroy(){if(locker)locker.Used-=OpenLocker;if(bunk)bunk.Used-=OpenBunk;}
  void OpenLocker(){if(session)session.OpenStash(this);}
  void OpenBunk(){if(session)session.OpenRest(this);}
  void Update()=>Sync(false);
  void Sync(bool force)
  {
   bool leased=Leased;
   if(door)door.Locked=!leased;
   if(!force&&leased==shown)return;
   shown=leased;
   if(locker)locker.enabled=leased;
   if(bunk)bunk.enabled=leased;
  }
 }
}
