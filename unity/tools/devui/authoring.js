/* OpenAI authoring is local-server-only. This file never receives a credential. */
let authoringConfig = null, authoringJobs = [], authoringPolling = false;
const authoringBriefs = new Map();
let pendingAuthoringJob = null;
let creativeMode = 'ideas', creativeBrief = '', creativeSpeech = '', creativeDirection = 'Natural, grounded delivery. A working resident of Ward, with a warm, practical tone.', creativeVoice = 'cedar', reviewedJob = null;
const authoringLabels = {item_text:'Item copy', ideas:'Ideas', icon:'Item illustration', voice:'Character voice'};
const assetUrl = value => /^\/api\/ai\/assets\/[0-9a-f]{32}\.(png|wav)$/.test(value||'') ? value : '';
const timeLabel = value => new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
const provenanceLink = job => `<a href="/api/ai/assets/${esc(job.id)}.json" download>Generation record</a>`;
const activeAuthoring = () => authoringConfig?.activeJob;
function authoringStatus(){return authoringConfig?.configured ? 'OpenAI key found · held by local server' : 'OpenAI key unavailable · configure the root .env';}
async function refreshAuthoring(){
  if(authoringPolling)return;
  authoringPolling=true;
  try{
    const response=await api('ai');authoringConfig=response.config;authoringJobs=response.jobs;
    const finished=authoringJobs.find(job=>job.id===pendingAuthoringJob);
    if(finished&&!['queued','running'].includes(finished.status)){
      pendingAuthoringJob=null;
      notice(finished.status==='complete'?'OpenAI draft ready for review. Nothing has been applied.':finished.error||'Authoring request stopped.');
    }
    if(tab==='items')updateItemAuthoring();
    if(tab==='creative')updateCreativeResults();
  }catch(e){if(tab==='creative'||tab==='items')notice('Authoring unavailable: '+e.message);}
  finally{authoringPolling=false;}
}
window.authoringInit=async()=>{await refreshAuthoring();setInterval(refreshAuthoring,1800);};
async function generateAuthoring(body){
  try{
    const response=await api('ai/generate',body);
    reviewedJob=response.job.id;pendingAuthoringJob=response.job.id;
    notice('OpenAI is generating a draft. You can keep editing while it runs.');
    await refreshAuthoring();
  }catch(e){notice(e.message);}
}
async function cancelAuthoring(id){try{await api('ai/cancel',{id});await refreshAuthoring();notice('Cancelled locally. An in-flight API request may still finish and incur a charge.');}catch(e){notice(e.message);}}
function jobStatus(job){
  if(!job)return '';
  if(job.status==='complete')return `<span class="job-state complete">Ready for review</span>`;
  if(job.status==='queued'||job.status==='running')return `<span class="job-state" role="status">Generating ${esc(authoringLabels[job.kind].toLowerCase())}…</span><button data-cancel-ai="${esc(job.id)}">Cancel request</button>`;
  return `<span class="job-state failed">${esc(job.status)}</span><p>${esc(job.error)}</p>`;
}
function attachCancel(container){container.querySelectorAll('[data-cancel-ai]').forEach(button=>button.onclick=()=>cancelAuthoring(button.dataset.cancelAi));}
function generationFooter(job){return `<div class="generation-meta"><span>${esc(job.model)} · ${esc(timeLabel(job.createdUtc))}</span>${provenanceLink(job)}</div>`;}
function currentItem(){return tab==='items' ? work.items[selection] : null;}
window.mountItemAuthoring=item=>{
  const panel=document.createElement('section');panel.className='authoring-panel';panel.id='itemAuthoring';panel.setAttribute('aria-label','OpenAI item authoring');
  panel.innerHTML=`<div class="authoring-heading"><h3>Develop this item</h3><span id="itemAiConnection">${esc(authoringStatus())}</span></div><p>Write a direction, generate a proposal, then choose what to keep.</p><label>Creative brief<textarea id="itemAiBrief" rows="3" maxlength="6000" placeholder="e.g. A repaired military servo, rebuilt for a courier’s leg implant. Practical and a little improvised.">${esc(authoringBriefs.get(item.id)||'')}</textarea></label><div class="row"><button id="generateItemCopy" class="primary">Suggest name & description</button><button id="generateItemIcon">Generate item illustration</button></div><small>Uses the OpenAI API. Your brief, selected item and setting reference are sent to OpenAI. API billing is separate from Codex usage.</small><div id="itemAiResults" aria-live="polite"></div>`;
  $('#editor').append(panel);
  mountItemEquipment(item,panel);
  const jumps=document.createElement('div');jumps.className='item-section-nav';jumps.setAttribute('role','group');jumps.setAttribute('aria-label','Item sections');
  jumps.innerHTML='<button data-item-section=".form">Metadata</button><button data-item-section=".equipment-authoring">Equipment & sockets</button><button data-item-section="#itemAuthoring">OpenAI authoring</button>';
  $('#editor').prepend(jumps);jumps.querySelectorAll('[data-item-section]').forEach(button=>button.onclick=()=>$('#editor').querySelector(button.dataset.itemSection)?.scrollIntoView({block:'start'}));
  $('#itemAiBrief').oninput=e=>authoringBriefs.set(item.id,e.target.value);
  const brief=()=>authoringBriefs.get(item.id)?.trim()||`Develop ${item.name} for Ashfall, using its existing role and stats.`;
  $('#generateItemCopy').onclick=()=>generateAuthoring({kind:'item_text',prompt:brief(),item:structuredClone(item)});
  $('#generateItemIcon').onclick=()=>generateAuthoring({kind:'icon',prompt:brief(),item:structuredClone(item)});
  if(item.iconAsset){const preview=document.createElement('div');preview.className='selected-item-art';preview.innerHTML=`<img src="${esc(assetUrl(item.iconAsset))}" alt="Draft illustration for ${esc(item.name)}"><div><strong>Selected draft illustration</strong><p>1024 px source retained. Import into Unity after visual review.</p><a href="${esc(assetUrl(item.iconAsset))}" download="${esc(item.id)}.png">Download PNG</a></div>`;$('#editor').prepend(preview);}
  mountUnityItemPicker();updateItemAuthoring(true);
};
function mountUnityItemPicker(){
  if(!unityCraft?.items?.length||$('#unityItemPicker'))return;
  const panel=document.createElement('div');panel.id='unityItemPicker';panel.className='unity-item-picker';
  panel.innerHTML=`<label>Start from Unity catalogue<select id="unityItemSource">${unityCraft.items.map(x=>`<option value="${esc(x.id)}">${esc(x.name)} · ${esc(x.id)}</option>`).join('')}</select></label><button id="copyUnityItem">Copy into draft</button><small>Copies the exported snapshot. Existing draft IDs are selected, never overwritten.</small>`;
  $('#view .list').append(panel);
  $('#copyUnityItem').onclick=()=>{
    const id=$('#unityItemSource').value,existing=work.items.findIndex(x=>x.id===id);
    if(existing>=0){selection=existing;render();notice('Existing draft selected; no fields overwritten.');return;}
    const source=unityCraft.items.find(x=>x.id===id);if(!source)return;
    work.items.push({id:source.id,name:source.name,category:source.tags?.includes('weapon')?'Weapon':'Item',subtype:'',tier:1,rarity:source.rarity||'Common',weightKg:source.weightKg||0,stack:Math.max(1,source.maxStack||20),tags:source.tags||[],stats:{},description:source.description||'',buyPrice:source.buyPrice||0,sellPrice:source.sellPrice||0});
    const equipment=equipmentFromUnity(id);if(equipment)work.items[work.items.length-1].equipment=equipment;
    selection=work.items.length-1;dirty=true;render();notice('Copied the Unity export to a local draft. Unity assets remain unchanged.');
  };
}
// Keep comparison text current while editing without rebuilding the proposal or
// resetting the user's field choices.
window.refreshItemCopyReview=()=>{
  const item=currentItem();if(!item)return;
  document.querySelectorAll('[data-current-field]').forEach(node=>{
    const key=node.dataset.currentField,label=key==='designNotes'?'design notes':key;
    node.textContent=item[key]||'No '+label;
  });
};
let lastItemReviewKey='';
function updateItemAuthoring(force=false){
  const panel=$('#itemAiResults'),item=currentItem();if(!panel||!item)return;
  $('#itemAiConnection').textContent=authoringStatus();
  const blocked=!authoringConfig?.configured||!!activeAuthoring();
  $('#generateItemCopy').disabled=blocked;$('#generateItemIcon').disabled=blocked;
  const jobs=authoringJobs.filter(x=>x.item?.id===item.id);
  const job=jobs.find(x=>x.id===reviewedJob)||jobs[0];
  const key=item.id+':'+(job?.id||'')+':'+(job?.status||'');
  if(!force&&key===lastItemReviewKey)return;lastItemReviewKey=key;
  if(!job){panel.innerHTML='<p class="empty-copy">Proposals appear here. Nothing is applied automatically.</p>';return;}
  panel.innerHTML=`<div class="review-title"><h4>${esc(authoringLabels[job.kind])}</h4>${jobStatus(job)}</div>`;
  if(job.status==='complete'&&job.kind==='item_text'){
    panel.innerHTML+=`<div class="proposal-grid"><div class="proposal-label">Use</div><div class="proposal-label">Current draft</div><div class="proposal-label">OpenAI proposal</div>${[['name','Name',false],['description','Description',true],['designNotes','Design notes',true]].map(([key,label,checked])=>`<label class="review-check"><input type="checkbox" data-apply-field="${key}" ${checked?'checked':''}><span>${label}</span></label><div class="before-copy" data-current-field="${key}">${esc(item[key]||'No '+label.toLowerCase())}</div><div class="after-copy">${esc(job.result[key])}</div>`).join('')}</div><button id="applyItemCopy" class="primary">Apply selected fields to draft</button><p class="review-note">Stable ID, stats, prices and gameplay references are retained.</p>`;
  }else if(job.status==='complete'&&job.kind==='icon'){
    panel.innerHTML+=`<div class="illustration-review"><img src="${esc(assetUrl(job.asset?.url))}" alt="Generated illustration proposal for ${esc(item.name)}"><div><h4>Illustration proposal</h4><p>Check the silhouette at inventory size and inspect the full PNG for fused parts or misleading detail.</p><div class="icon-scale"><img src="${esc(assetUrl(job.asset?.url))}" alt="Same illustration at 56 pixels"><span>56 px inventory size</span></div><button id="applyItemIcon" class="primary">Use in draft</button> <a href="${esc(assetUrl(job.asset?.url))}" download="${esc(item.id)}.png">Download PNG</a></div></div>`;

  }
  panel.innerHTML+=generationFooter(job);
  // Bind review actions after the complete markup is installed.
  if(job.status==='complete'&&job.kind==='item_text')$('#applyItemCopy').onclick=()=>{
    const target=currentItem();if(target?.id!==job.item.id)return;
    const chosen=[...panel.querySelectorAll('[data-apply-field]:checked')].map(x=>x.dataset.applyField);
    if(!chosen.length){notice('Choose at least one field to apply.');return;}
    chosen.forEach(field=>target[field]=job.result[field]);target.aiProvenance=[...new Set([...(target.aiProvenance||[]),job.id])].slice(-32);dirty=true;render();notice('Selected copy applied to the unsaved draft. Save draft when ready.');
  };
  if(job.status==='complete'&&job.kind==='icon')$('#applyItemIcon').onclick=()=>{const target=currentItem();if(target?.id!==job.item.id)return;target.iconAsset=job.asset.url;target.aiProvenance=[...new Set([...(target.aiProvenance||[]),job.id])].slice(-32);dirty=true;render();notice('Illustration attached to the draft. Import the PNG into Unity when accepted.');};
  if(jobs.length>1){const history=document.createElement('label');history.className='review-history';history.innerHTML=`Previous proposals<select>${jobs.map(x=>`<option value="${esc(x.id)}" ${x.id===job.id?'selected':''}>${esc(authoringLabels[x.kind])} · ${esc(timeLabel(x.createdUtc))} · ${esc(x.status)}</option>`).join('')}</select>`;history.querySelector('select').onchange=e=>{reviewedJob=e.target.value;updateItemAuthoring(true);};panel.append(history);}
  attachCancel(panel);
}
window.creativeDesk=()=>{
  wrap('Creative desk',`<div class="creative-layout"><section class="creative-compose"><h3>Develop Ward’s next detail</h3><p>Explore item concepts, write a character’s lines, or audition a voice. Keep the result that serves the game.</p><div class="mode-tabs" role="group" aria-label="Authoring mode"><button data-creative-mode="ideas" aria-pressed="${creativeMode==='ideas'}">Ideas & writing</button><button data-creative-mode="voice" aria-pressed="${creativeMode==='voice'}">Character voice</button></div><label>${creativeMode==='voice'?'Character / scene brief':'Creative brief'}<textarea id="creativeBrief" rows="5" maxlength="6000" placeholder="e.g. Three industrial leg implants with distinct silhouettes, each with three augmentation options and a clear tradeoff.">${esc(creativeBrief)}</textarea></label>${creativeMode==='voice'?`<label>Dialogue to speak<textarea id="creativeSpeech" rows="6" maxlength="4096" placeholder="Paste the approved dialogue line here. Existing dialogue is never replaced.">${esc(creativeSpeech)}</textarea></label><div class="row"><label>Built-in voice<select id="creativeVoice">${(authoringConfig?.voices||['cedar']).map(v=>`<option value="${esc(v)}" ${v===creativeVoice?'selected':''}>${esc(v)}</option>`).join('')}</select></label></div><label>Performance direction<textarea id="creativeDirection" rows="3" maxlength="1500">${esc(creativeDirection)}</textarea></label><p class="review-note">AI-generated voice. Use this disclosure in the game’s credits when shipping it.</p>`:''}<button id="generateCreative" class="primary">${creativeMode==='voice'?'Generate voice audition':'Generate ideas'}</button><p id="creativeConnection" class="review-note">${esc(authoringStatus())}</p><details><summary>Models & what is sent</summary><p>OpenAI API usage is billed separately from Codex. Text requests send your brief and the local lore reference. Voice sends only the entered dialogue and performance direction. No source code or credentials are sent as prompt content.</p><dl>${Object.entries(authoringConfig?.models||{}).map(([key,value])=>`<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join('')}</dl><p>Models can be configured through the server environment. Requests run once; failures are never retried automatically.</p></details></section><section class="creative-results"><div class="authoring-heading"><h3>Generation journal</h3><small id="generationCount">Local drafts · ${authoringJobs.length} records</small></div><div id="creativeJournal"></div><div id="creativeReview" aria-live="polite"></div></section></div>`);
  $('#creativeBrief').oninput=e=>creativeBrief=e.target.value;
  if($('#creativeSpeech'))$('#creativeSpeech').oninput=e=>creativeSpeech=e.target.value;
  if($('#creativeDirection'))$('#creativeDirection').oninput=e=>creativeDirection=e.target.value;
  if($('#creativeVoice'))$('#creativeVoice').onchange=e=>creativeVoice=e.target.value;
  document.querySelectorAll('[data-creative-mode]').forEach(b=>b.onclick=()=>{creativeMode=b.dataset.creativeMode;render();});
  $('#generateCreative').onclick=()=>generateAuthoring({kind:creativeMode==='voice'?'voice':'ideas',prompt:creativeBrief.trim()||(creativeMode==='voice'?'Character voice audition':'Suggest grounded equipment concepts for Ward.'),...(creativeMode==='voice'?{speech:creativeSpeech,voice:creativeVoice,direction:creativeDirection}:{})});
  updateCreativeResults(true);
};
let lastCreativeKey='';
function updateCreativeResults(force=false){
  const journal=$('#creativeJournal'),review=$('#creativeReview');if(!journal||!review)return;
  if($('#generationCount'))$('#generationCount').textContent=`Local drafts · ${authoringJobs.length} records`;
  $('#generateCreative').disabled=!authoringConfig?.configured||!!activeAuthoring();$('#creativeConnection').textContent=authoringStatus();
  const job=authoringJobs.find(x=>x.id===reviewedJob)||authoringJobs[0];
  const key=authoringJobs.map(x=>x.id+':'+x.status).join(',')+'|'+(job?.id||'');if(!force&&key===lastCreativeKey)return;lastCreativeKey=key;
  journal.innerHTML=authoringJobs.length?authoringJobs.slice(0,15).map(x=>`<button class="journal-row ${job?.id===x.id?'selected':''}" data-review-job="${esc(x.id)}"><span>${esc(authoringLabels[x.kind])}${x.item?' · '+esc(x.item.name):''}</span><small>${esc(timeLabel(x.createdUtc))} · ${esc(x.status)}</small></button>`).join(''):'<p class="empty-copy">Your first generation will appear here, with its prompt and model record.</p>';
  journal.querySelectorAll('[data-review-job]').forEach(b=>b.onclick=()=>{reviewedJob=b.dataset.reviewJob;updateCreativeResults(true);});
  if(!job){review.innerHTML='';return;}
  review.innerHTML=`<div class="review-title"><h4>${esc(authoringLabels[job.kind])}</h4>${jobStatus(job)}</div><p class="brief-quote">${esc(job.prompt)}</p>`;
  if(job.status==='complete'){
    if(job.kind==='ideas')review.innerHTML+=`<div class="generated-writing">${esc(job.result)}</div><button id="copyIdeas">Copy text</button>`;
    if(job.kind==='item_text')review.innerHTML+=`<h3>${esc(job.result.name)}</h3><p>${esc(job.result.description)}</p><p class="review-note">${esc(job.result.designNotes)}</p><button id="openJobItem">Review in Items</button>`;
    if(job.kind==='icon')review.innerHTML+=`<img class="journal-image" src="${esc(assetUrl(job.asset?.url))}" alt="Generated item illustration"><button id="openJobItem">Review in Items</button>`;
    if(job.kind==='voice')review.innerHTML+=`<p class="generated-writing">${esc(job.result.speech)}</p><audio controls preload="metadata" src="${esc(assetUrl(job.asset?.url))}" aria-label="AI-generated voice audition"></audio><p class="review-note">AI-generated voice · ${esc(job.result.voice)}</p><a href="${esc(assetUrl(job.asset?.url))}" download="ashfall-voice-${esc(job.id)}.wav">Download WAV for Unity</a>`;
  }
  review.innerHTML+=generationFooter(job);
  if($('#copyIdeas'))$('#copyIdeas').onclick=async()=>{try{await navigator.clipboard.writeText(job.result);notice('Ideas copied.');}catch(e){notice('Clipboard unavailable. Select and copy the text directly.');}};
  if($('#openJobItem'))$('#openJobItem').onclick=()=>{const index=work.items.findIndex(x=>x.id===job.item.id);if(index<0){notice('The original item draft is no longer present. Recreate or import it to apply this proposal.');return;}tab='items';selection=index;render();};
  attachCancel(review);
}

const fallbackCharacterSlots=['implant_head','implant_arms','implant_wrist','implant_hand','implant_chest','implant_waist','implant_legs','implant_feet','armour_head','armour_arms','armour_hands','armour_chest','armour_legs','armour_feet','storage'];
const fallbackCharacterStats=['strength','agility','endurance','intellect','perception','resolve','health','stamina','nano','carryCapacity','storageCapacity','packSlots','movementSpeed','armour','physicalResistance','energyResistance','thermalResistance','radiationResistance','toxinResistance','nanoResistance','criticalChance','healingEfficiency','staminaRegeneration','nanoRegeneration','meleeDamage','rangedDamage','accuracy','recoilControl','nanoStability','suppressionResistance'];
const socketTypes=['implant','armour_plate','armour_lining','armour_motor','armour_utility'];
const implantSockets=()=>[1,2,3].map(n=>({id:'augmentation_'+n,label:'Augmentation '+n,type:'implant'}));
const prettyId=id=>id.replaceAll('_',' ').replace(/([a-z])([A-Z])/g,'$1 $2').replace(/^./,v=>v.toUpperCase());
function equipmentFromUnity(id){
  const host=unityCraft?.character?.equipment?.find(x=>x.itemId===id);
  const mod=unityCraft?.character?.modifications?.find(x=>x.itemId===id);
  if(host){const kind=host.slots?.some(x=>x.startsWith('implant_'))?'implant':'armour';return {kind,slots:host.slots||[],socketTypes:[],modificationSockets:kind==='implant'?implantSockets():host.modificationSockets||[],modifiers:host.modifiers||[]};}
  if(mod)return {kind:mod.socketTypes?.includes('implant')?'augmentation':'armour_mod',slots:mod.slots||[],socketTypes:mod.socketTypes||[],modificationSockets:[],modifiers:mod.modifiers||[]};
  return null;
}
function mountItemEquipment(item,anchor){
  const section=document.createElement('section');section.className='equipment-authoring';
  const eq=item.equipment,kind=eq?.kind||'none',isModule=['augmentation','armour_mod'].includes(kind);
  const slots=unityCraft?.character?.slots?.length?unityCraft.character.slots:fallbackCharacterSlots.map(id=>({id,label:prettyId(id)}));
  const stats=unityCraft?.character?.stats?.length?unityCraft.character.stats:fallbackCharacterStats.map(id=>({id,label:prettyId(id)}));
  section.innerHTML=`<h4>Equipment & augmentation</h4><label>Item role<select id="equipmentKind"><option value="none">Ordinary item</option>${[['implant','Implant host · 3 augmentations'],['armour','Armour host · component sockets'],['augmentation','Implant augmentation'],['armour_mod','Armour component']].map(([id,label])=>`<option value="${id}" ${kind===id?'selected':''}>${label}</option>`).join('')}</select></label>${eq?`<div class="equipment-columns"><div><h4>${isModule?'Compatible body slots':'Equips to'}</h4><div class="equipment-slot-list">${slots.filter(x=>kind==='implant'||kind==='augmentation'?x.id.startsWith('implant_'):x.id.startsWith('armour_')||x.id==='storage').map(x=>`<label class="inline-check"><input type="checkbox" data-equip-slot="${esc(x.id)}" ${eq.slots.includes(x.id)?'checked':''}><span>${esc(x.label)}</span></label>`).join('')}</div>${isModule?'<small>Leave body slots empty to allow any matching socket type.</small>':''}</div><div><h4>${isModule?'Fits socket types':'Available sockets'}</h4>${isModule?socketTypes.filter(x=>kind==='augmentation'?x==='implant':x!=='implant').map(x=>`<label class="inline-check"><input type="checkbox" data-socket-type="${x}" ${eq.socketTypes.includes(x)?'checked':''}><span>${esc(prettyId(x))}</span></label>`).join(''):kind==='implant'?`<ol class="implant-socket-list">${eq.modificationSockets.map(x=>`<li>${esc(x.label)} <small>Implant augmentation</small></li>`).join('')}</ol><small>Every implant has exactly three augmentation sockets.</small>`:`<div id="armourSockets">${eq.modificationSockets.map((x,i)=>`<div class="socket-author-row"><label>Socket ID<input data-socket-id="${i}" value="${esc(x.id)}" maxlength="64"></label><label>Label<input data-socket-label="${i}" value="${esc(x.label)}" maxlength="80"></label><label>Type<select data-socket-kind="${i}">${socketTypes.filter(t=>t!=='implant').map(t=>`<option value="${t}" ${t===x.type?'selected':''}>${esc(prettyId(t))}</option>`).join('')}</select></label><button data-remove-socket="${i}">Remove socket</button></div>`).join('')}</div><button id="addArmourSocket" ${eq.modificationSockets.length>=8?'disabled':''}>Add armour socket</button>`}</div></div><h4>Effects</h4><p class="review-note">Flat bonuses apply before percentage bonuses. These are proposed balance values until authored in Unity.</p><div class="effect-head"><span>Stat</span><span>Flat bonus</span><span>Percent bonus</span><span></span></div>${eq.modifiers.map((m,i)=>`<div class="effect-author-row"><label><span class="sr-only">Stat ${i+1}</span><input list="characterStats" data-effect-stat="${i}" value="${esc(m.stat)}"></label><label><span class="sr-only">Flat bonus ${i+1}</span><input type="number" step="0.01" data-effect-flat="${i}" value="${m.flat}"></label><label><span class="sr-only">Percent bonus ${i+1}</span><input type="number" min="-100" max="10000" step="0.1" data-effect-percent="${i}" value="${Number((m.percent*100).toFixed(4))}"></label><button data-remove-effect="${i}" aria-label="Remove effect ${i+1}">Remove</button></div>`).join('')}<datalist id="characterStats">${stats.map(x=>`<option value="${esc(x.id)}">${esc(x.label)}</option>`).join('')}</datalist><button id="addEquipmentEffect" ${eq.modifiers.length>=32?'disabled':''}>Add effect</button>`:'<p class="review-note">Choose a role to author implant sockets, armour components and compatible body slots.</p>'}`;
  anchor.before(section);
  $('#equipmentKind').onchange=e=>{
    const kind=e.target.value;if(kind==='none')delete item.equipment;
    else item.equipment={kind,slots:[],socketTypes:kind==='augmentation'?['implant']:kind==='armour_mod'?['armour_plate']:[],modificationSockets:kind==='implant'?implantSockets():[],modifiers:[]};
    dirty=true;render();notice('Equipment role changed in the unsaved draft.');
  };
  if(!eq)return;
  const edited=()=>draftEdited('Unsaved equipment definition.');
  section.querySelectorAll('[data-equip-slot]').forEach(el=>el.onchange=()=>{eq.slots=[...section.querySelectorAll('[data-equip-slot]:checked')].map(x=>x.dataset.equipSlot);edited();});
  section.querySelectorAll('[data-socket-type]').forEach(el=>el.onchange=()=>{eq.socketTypes=[...section.querySelectorAll('[data-socket-type]:checked')].map(x=>x.dataset.socketType);edited();});
  for(const field of ['id','label','kind'])section.querySelectorAll(`[data-socket-${field}]`).forEach(el=>el.onchange=()=>{eq.modificationSockets[Number(el.dataset['socket'+field[0].toUpperCase()+field.slice(1)])][field==='kind'?'type':field]=el.value;edited();});
  section.querySelectorAll('[data-remove-socket]').forEach(el=>el.onclick=()=>{eq.modificationSockets.splice(Number(el.dataset.removeSocket),1);dirty=true;render();});
  if($('#addArmourSocket'))$('#addArmourSocket').onclick=()=>{let index=eq.modificationSockets.length+1;while(eq.modificationSockets.some(x=>x.id==='component_'+index))index++;eq.modificationSockets.push({id:'component_'+index,label:'Component '+index,type:'armour_plate'});dirty=true;render();};
  for(const field of ['stat','flat','percent'])section.querySelectorAll(`[data-effect-${field}]`).forEach(el=>el.onchange=()=>{eq.modifiers[Number(el.dataset['effect'+field[0].toUpperCase()+field.slice(1)])][field]=field==='stat'?el.value:Number(el.value)/(field==='percent'?100:1);edited();});
  section.querySelectorAll('[data-remove-effect]').forEach(el=>el.onclick=()=>{eq.modifiers.splice(Number(el.dataset.removeEffect),1);dirty=true;render();});
  $('#addEquipmentEffect').onclick=()=>{eq.modifiers.push({stat:kind==='armour_mod'?'armour':'movementSpeed',flat:0,percent:0});dirty=true;render();};
}
