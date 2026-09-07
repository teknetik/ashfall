// Snapshot authored source data once for the Unity ScriptableObject importer.
// Gameplay is implemented independently in C#; this does not ship a TS runtime.
const fs=require('fs');const ts=require('typescript');
function data(path,extra=''){const exports={};new Function('exports','require',ts.transpileModule(fs.readFileSync(path,'utf8')+extra,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText)(exports,require);return exports;}
const npc=data('src/npc.ts'),dialogue=data('src/dialogue.ts'),shop=data('src/shop.ts'),travel=data('src/travel.ts','\nexport const handoverNodes=NODES;');
const result={catalog:{startingCredits:25,items:Object.values(shop.ITEMS).map(x=>({...x,startingQuantity:x.id==='scrap_coil'?1:0})),destinations:travel.handoverNodes},npcs:npc.NPC_DEFINITIONS.map(n=>({...n,displayName:n.name,nodes:['greeting',...({npc_torr:['slab'],npc_vex:['gate'],npc_linn:['hill']}[n.id]||[])].map(id=>({id,...dialogue.getDialogue(n.id,id)}))})),walkers:npc.AMBIENT_WALKERS};
fs.writeFileSync('unity/AthenHill/Assets/AthenHill/Data/source-content.json',JSON.stringify(result,null,2)+'\n');
