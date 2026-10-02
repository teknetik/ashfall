using System;
using UnityEngine;
namespace AthenHill
{
 /// Visible armour on the player colonist (2 Oct 2026): each entry names an equipment item and the model shown while it
 /// is equipped in its slot (the Warden plate carrier on the chest). The field vest the colonist starts with has no
 /// model; the suit is the vest. Driven by the character model's Changed event, so the inventory's equip/unequip shows
 /// and hides the piece at once.
 [DisallowMultipleComponent]
 public class PlayerArmourVisuals:MonoBehaviour
 {
  [Serializable]public class Piece
  {
   [Tooltip("Catalog item id (CharacterCatalog equipment entry).")]public string itemId;
   [Tooltip("Equipment slot the item sits in when worn (armour_chest).")]public string slot="armour_chest";
   [Tooltip("Model under the colonist's bones, shown only while the item is equipped.")]public GameObject model;
  }
  public PlayerCombat combat;
  public Piece[] pieces=new Piece[0];
  CharacterModel bound;
  void Start(){Apply();}
  void OnDestroy(){Unbind();}
  void Unbind(){if(bound!=null)bound.Changed-=Apply;bound=null;}
  void Update()
  {
   var character=combat?combat.Character:null;
   if(character==bound)return;
   Unbind();bound=character;
   if(bound!=null)bound.Changed+=Apply;
   Apply();
  }
  /// Shows each piece exactly when its item is equipped in its slot; everything is hidden with no character bound.
  public void Apply()
  {
   foreach(var p in pieces)
   {
    if(p==null||!p.model)continue;
    bool worn=bound!=null&&!string.IsNullOrEmpty(p.itemId)&&bound.Equipped(p.slot)==p.itemId;
    if(p.model.activeSelf!=worn)p.model.SetActive(worn);
   }
  }
  /// Worn piece item ids, for QA snapshots.
  public string[] Worn()
  {
   var list=new System.Collections.Generic.List<string>();
   foreach(var p in pieces)if(p!=null&&p.model&&p.model.activeSelf)list.Add(p.itemId);
   return list.ToArray();
  }
 }
}
