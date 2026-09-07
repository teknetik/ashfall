import { CAMERA_NAMES } from './camera';
import type { Game } from './game';
import { icon } from './ui-icons';
import { ITEMS, type ItemId } from './shop';

const names = { cam_gate: 'West Gate', cam_avenue: 'Avenue', cam_hill: 'Hill Tree', cam_grid: 'Lattice Jack', cam_whompah: 'Ring Gate', cam_hero: 'Hero' };
const hotbar = [['flask', 'Water Flask'], ['medkit', 'Medkit'], ['lattice', 'Lattice Jack'], ['talk', 'Talk'], ['pack', 'Inventory'], ['notes', 'City notes']];
const debugEnabled = import.meta.env.DEV || new URLSearchParams(location.search).get('debug') === '1';
const escapeHTML = (value: unknown) => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!);

export function createUI(root: HTMLElement) {
  root.innerHTML = `
    <canvas class="world-canvas" tabindex="0" aria-label="Athen Hill city. WASD to walk, right-drag to look, E to interact."></canvas>
    <div id="play-hud" class="play-hud">
      <header class="identity"><p class="eyebrow">Free Column · Colony 07</p><h1>Athen Hill</h1><p id="location" class="scope">West Gate</p></header>
      <aside class="vitals metal-frame" aria-label="Colonist status"><div class="vital"><span class="meter" role="meter" aria-label="Vitality" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"><i></i></span><span>VIT</span></div><div class="vital nano"><span class="meter" role="meter" aria-label="Nano" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"><i></i></span><span>NANO</span></div></aside>
      <div class="objective-strip"><span class="objective-mark" aria-hidden="true">◇</span><p id="objective">Find your place in the city.</p><span id="story-progress" class="story-progress"></span></div>
      <div class="top-actions">
        <details id="inventory" class="inventory metal-frame"><summary>${icon('pack')}<span>Pack</span><span id="credits" class="credits">— cr</span></summary><div class="inventory-content"><div class="panel-caption"><span>Field inventory</span><span id="inventory-count"></span></div><ul id="inventory-items" class="inventory-items"></ul><p class="fine-print">Trade supplies at Basic General.</p></div></details>
        <details id="city-notes" class="city-notes metal-frame"><summary aria-label="City notes">${icon('notes')}</summary><div><p class="panel-caption">Your first afternoon</p><p>Meet the four colonists. Mira trades at Basic General, Torr works by the mission terminals, Vex watches the west gate, and Linn is on the hill.</p><p>The Lattice Jack stands north of the tree. The Ring Gate is to the south.</p></div></details>
        <button id="pause" class="icon-button metal-frame" aria-label="Pause exploration" title="Pause · Escape" disabled>${icon('pause')}</button>
        ${debugEnabled ? `<details class="instrumentation metal-frame"><summary>Survey</summary><p id="status" class="status" role="status">Building the city…</p><div class="camera-controls"><label for="view">View</label><select id="view"><option value="follow">Player</option>${CAMERA_NAMES.map(name => `<option value="${name}">${names[name]}</option>`).join('')}</select></div><div class="tool-actions"><button id="save" disabled>Save frame</button><button id="reset" disabled>Return to gate</button></div><p id="save-status" class="save-status" role="status">Choose a named view for a fixed capture.</p><p id="metrics" class="metrics"></p><p id="position" class="position"></p></details>` : ''}
      </div>
      <section class="chat-log metal-frame" aria-label="City conversation"><div class="panel-caption"><span>Local channel</span><span class="channel-light" aria-hidden="true"></span></div><ol id="chat-lines" role="log" aria-live="polite" aria-relevant="additions"></ol></section>
      <div class="quickbar"><nav class="hotbar metal-frame" aria-label="Quick actions">${hotbar.map(([symbol, label], index) => `<button class="hotbar-slot" data-hotbar="${index}" aria-label="${label}, quick slot ${index + 1}" aria-pressed="false" title="${index + 1} · ${label}"><span class="slot-key">${index + 1}</span>${icon(symbol)}<span class="slot-quantity" data-quantity="${symbol}"></span></button>`).join('')}</nav><p class="desktop-help"><kbd>WASD</kbd> walk <span>·</span> <kbd>Shift</kbd> run <span>·</span> Right-drag look <span>·</span> <kbd>E</kbd> interact</p></div>
      <div id="interaction-prompt" class="interaction-prompt" hidden><span class="target-bracket" aria-hidden="true"></span><button id="interact"><kbd>E</kbd><span id="interaction-label">Talk</span></button></div>
      <div id="toast" class="toast metal-frame" role="status" aria-live="polite" hidden></div>
      <nav class="touch-controls" aria-label="Movement controls"><button data-move="forward" aria-label="Walk forward">↑</button><button data-move="left" aria-label="Walk left">←</button><button data-move="back" aria-label="Walk backward">↓</button><button data-move="right" aria-label="Walk right">→</button></nav>
      <div class="touch-actions"><button id="touch-interact" aria-label="Interact with nearby target" disabled>${icon('talk')}<span>Interact</span></button><button class="touch-run" data-move="run">Run</button></div>
    </div>
    <div id="boot-message" class="boot-message metal-frame" role="status"><p class="eyebrow">Athen Hill</p><h2 id="boot-title">Arriving at West Gate</h2><p id="boot-detail">Preparing the city and its colonists…</p><span class="load-track" aria-hidden="true"></span><button id="reload" hidden>Reload city</button></div>
    <div id="modal-shade" class="modal-shade" hidden>
      <section id="pause-panel" class="game-panel pause-panel metal-frame" role="dialog" aria-modal="true" aria-labelledby="pause-title" tabindex="-1" hidden><div class="panel-title"><p class="eyebrow">Exploration paused</p><button class="icon-button" data-close aria-label="Resume exploration">${icon('close')}</button></div><h2 id="pause-title">A moment on the hill.</h2><p>The city will be here.</p><button id="resume" class="primary-action">Resume walking</button><dl class="controls-list"><dt>Move / run</dt><dd>WASD / Shift</dd><dt>Look / interact</dt><dd>Right-drag / E</dd><dt>Quick slots</dt><dd>1–6</dd><dt>Pause / close</dt><dd>Escape</dd></dl></section>
      <section id="dialogue-panel" class="game-panel dialogue-panel metal-frame" role="dialog" aria-modal="true" aria-labelledby="dialogue-speaker" aria-describedby="dialogue-text" tabindex="-1" hidden><div class="panel-title"><div><p id="dialogue-title" class="eyebrow"></p><h2 id="dialogue-speaker"></h2></div><button class="icon-button" data-close aria-label="End conversation">${icon('close')}</button></div><p id="dialogue-text" class="dialogue-text"></p><div id="dialogue-choices" class="dialogue-choices"></div><p class="panel-footnote">Local transmission <span>ESC · leave</span></p></section>
      <section id="shop-panel" class="game-panel shop-panel metal-frame" role="dialog" aria-modal="true" aria-labelledby="shop-title" tabindex="-1" hidden><div class="panel-title"><div><p class="eyebrow">Mira · Supplies & salvage</p><h2 id="shop-title">Basic General</h2></div><button class="icon-button" data-close aria-label="Leave Basic General">${icon('close')}</button></div><div class="trade-heading"><span>Field supplies</span><span id="shop-credits" class="credits"></span></div><div class="trade-table-heading" aria-hidden="true"><span>Item</span><span>Pack</span><span>Trade</span></div><div id="shop-items" class="shop-items"></div><p class="panel-footnote">Single-item trades <span>ESC · leave</span></p></section>
      <section id="grid-panel" class="game-panel grid-panel metal-frame" role="dialog" aria-modal="true" aria-labelledby="grid-title" tabindex="-1" hidden><div class="panel-title"><div><p class="eyebrow">Lattice Jack / Sector relay</p><h2 id="grid-title">Local lattice</h2></div><button class="icon-button" data-close aria-label="Leave the Lattice Jack">${icon('close')}</button></div><div id="grid-tunnel" class="grid-tunnel"><div class="tunnel-rings" aria-hidden="true"><i></i><i></i><i></i><i></i></div><p>Synchronizing your signal</p><progress id="grid-progress" max="1" value="0" aria-label="Lattice connection progress"></progress></div><div id="grid-map" hidden><div class="sector-map"><span class="map-origin">ATHEN HILL <i></i></span><div id="grid-nodes" class="grid-nodes"></div></div><p id="grid-selection" class="grid-selection">Select a sector to establish a link.</p></div><p class="panel-footnote">Three relays in range <span>ESC · disconnect</span></p></section>
    </div>`;
  return root.querySelector<HTMLCanvasElement>('canvas')!;
}

export function bindUI(root: HTMLElement, game: Game) {
  const el = <T extends HTMLElement>(id: string) => root.querySelector<T>(`#${id}`)!;
  const optional = <T extends HTMLElement>(id: string) => root.querySelector<T>(`#${id}`);
  const inventory = el<HTMLDetailsElement>('inventory');
  const notes = el<HTMLDetailsElement>('city-notes');
  const hud = el('play-hud');
  const pause = el<HTMLButtonElement>('pause');
  const shade = el('modal-shade');
  let activeDialog: HTMLElement | null = null;
  let previousState = '';
  let previousDialogue = '';
  let previousShop = '';
  let previousGrid = '';
  let lastLogId: unknown = null;
  let saving = false;

  const replacePreservingFocus = (container: HTMLElement, html: string) => {
    const focused = container.contains(document.activeElement) ? (document.activeElement as HTMLElement).dataset.focusKey : undefined;
    container.innerHTML = html;
    if (focused) {
      const replacement = container.querySelector<HTMLElement>(`[data-focus-key="${CSS.escape(focused)}"]`);
      const target = replacement && !replacement.matches(':disabled') ? replacement :
        container.querySelector<HTMLElement>('button:not(:disabled)') ?? container.closest<HTMLElement>('[role="dialog"]');
      target?.focus({ preventScroll: true });
    }
  };
  const restoreCanvas = () => { if (game.state === 'play') game.canvas.focus({ preventScroll: true }); };
  const close = () => { if (game.state === 'paused') game.pause(false); else game.closeOverlay(); restoreCanvas(); };
  const selectHotbar = (slot: number) => {
    if (game.state !== 'play') return;
    game.selectHotbar(slot);
    if (slot === 4) { inventory.open = !inventory.open; notes.open = false; }
    if (slot === 5) { notes.open = !notes.open; inventory.open = false; }
    restoreCanvas();
  };

  const update = () => {
    const state = game.state;
    const ready = state !== 'boot' && state !== 'error';
    const playing = state === 'play';
    root.dataset.state = state;
    el('boot-message').hidden = ready;
    hud.hidden = !ready;
    el('boot-title').textContent = state === 'error' ? 'Connection interrupted' : 'Arriving at West Gate';
    el('boot-detail').textContent = state === 'error' ? game.error : 'Preparing the city and its colonists…';
    el('reload').hidden = state !== 'error';
    el('location').textContent = game.locationLabel;
    pause.disabled = !playing;
    const snapshot = game.shop.snapshot;
    const credits = `${snapshot.credits.toLocaleString()} cr`;
    el('credits').textContent = credits;
    el('shop-credits').textContent = credits;
    el('inventory-count').textContent = `${snapshot.items.reduce((sum, item) => sum + item.quantity, 0)} items`;
    const shopSignature = JSON.stringify(snapshot);
    if (shopSignature !== previousShop) {
      previousShop = shopSignature;
      el('inventory-items').innerHTML = snapshot.items.map(item => `<li>${icon(item.icon)}<span>${escapeHTML(item.name)}</span><strong>×${item.quantity}</strong></li>`).join('');
      replacePreservingFocus(el('shop-items'), snapshot.items.map(item => `<div class="trade-row"><span class="item-art">${icon(item.icon)}</span><div class="item-copy"><h3>${escapeHTML(item.name)}</h3><p>${escapeHTML(item.description)}</p></div><span class="trade-quantity" aria-label="${item.quantity} in your pack">×${item.quantity}</span><div class="trade-actions"><button data-buy="${item.id}" data-focus-key="buy-${item.id}" ${item.buyPrice > snapshot.credits ? 'disabled' : ''} aria-label="Buy ${escapeHTML(item.name)} for ${item.buyPrice} credits">Buy <span>${item.buyPrice} cr</span></button><button data-sell="${item.id}" data-focus-key="sell-${item.id}" ${item.quantity < 1 ? 'disabled' : ''} aria-label="Sell ${escapeHTML(item.name)} for ${item.sellPrice} credits">Sell <span>${item.sellPrice} cr</span></button></div></div>`).join(''));
      for (const item of snapshot.items) {
        const quantity = root.querySelector<HTMLElement>(`[data-quantity="${item.icon}"]`);
        if (quantity) quantity.textContent = String(item.quantity);
      }
    }
    el('objective').textContent = game.story.objective;
    el('story-progress').textContent = game.story.complete ? 'SETTLED IN' : `${game.story.spokenCount}/4 contacts`;
    el('story-progress').dataset.complete = String(game.story.complete);
    root.querySelectorAll<HTMLButtonElement>('[data-hotbar]').forEach(button => {
      button.disabled = !playing;
      button.setAttribute('aria-pressed', String(Number(button.dataset.hotbar) === game.selectedHotbar));
    });
    const recentLogs = game.logs.slice(-5);
    if (recentLogs.at(-1)?.id !== lastLogId) {
      lastLogId = recentLogs.at(-1)?.id;
      const log = el('chat-lines');
      log.innerHTML = recentLogs.map(entry => `<li><span>${escapeHTML(entry.speaker)}:</span> ${escapeHTML(entry.text)}</li>`).join('');
      log.scrollTop = log.scrollHeight;
    }
    el('toast').hidden = !game.toast || !ready;
    el('toast').textContent = game.toast;
    const nearby = playing ? game.nearbyInteraction : null;
    el('interaction-prompt').hidden = !nearby;
    el('interaction-label').textContent = nearby?.label ?? '';
    el<HTMLButtonElement>('touch-interact').disabled = !nearby;
    el<HTMLButtonElement>('touch-interact').setAttribute('aria-label', nearby?.label ?? 'No nearby interaction');
    root.querySelectorAll<HTMLButtonElement>('[data-move]').forEach(button => { button.disabled = !playing; });
    const dialogue = game.dialogue;
    const dialogueSignature = JSON.stringify(dialogue);
    if (dialogue && dialogueSignature !== previousDialogue) {
      el('dialogue-speaker').textContent = dialogue.speaker;
      el('dialogue-title').textContent = dialogue.title;
      el('dialogue-text').textContent = dialogue.text;
      replacePreservingFocus(el('dialogue-choices'), dialogue.choices.map((choice, index) => `<button data-choice="${escapeHTML(choice.id)}" data-focus-key="choice-${escapeHTML(choice.id)}"><span class="choice-index">0${index + 1}</span><span>${escapeHTML(choice.label)}</span><span aria-hidden="true">›</span></button>`).join(''));
    }
    previousDialogue = dialogueSignature;
    const grid = game.grid;
    if (grid) {
      el('grid-tunnel').hidden = grid.phase !== 'tunnel';
      el('grid-map').hidden = grid.phase !== 'map';
      el<HTMLProgressElement>('grid-progress').value = grid.progress;
      const signature = JSON.stringify([grid.nodes, grid.selectedNode]);
      if (signature !== previousGrid) {
        previousGrid = signature;
        replacePreservingFocus(el('grid-nodes'), grid.nodes.map((node, index) => `<button data-node="${escapeHTML(node.id)}" data-focus-key="node-${escapeHTML(node.id)}" aria-pressed="${grid.selectedNode === node.id}"><span class="node-dot" aria-hidden="true"></span><span class="node-number">0${index + 1}</span><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.description)}</small></button>`).join(''));
        const chosen = grid.nodes.find(node => node.id === grid.selectedNode);
        el('grid-selection').textContent = chosen ? `Link established · ${chosen.name}` : 'Select a sector to establish a link.';
      }
    }
    const panelId = state === 'paused' ? 'pause-panel' : state === 'dialogue' ? 'dialogue-panel' : state === 'shop' ? 'shop-panel' : state === 'grid' ? 'grid-panel' : null;
    activeDialog = panelId ? el(panelId) : null;
    shade.hidden = !activeDialog;
    shade.querySelectorAll<HTMLElement>('.game-panel').forEach(panel => { panel.hidden = panel !== activeDialog; });
    hud.inert = Boolean(activeDialog);
    game.canvas.inert = Boolean(activeDialog);
    if (previousState !== state) {
      if (activeDialog) {
        inventory.open = false;
        notes.open = false;
        game.input.clear();
        const first = activeDialog.querySelector<HTMLElement>('#resume, [data-choice], [data-buy]:not(:disabled), [data-node]') ?? activeDialog.querySelector<HTMLElement>('button') ?? activeDialog;
        first.focus({ preventScroll: true });
      } else if (ready && previousState !== 'boot') restoreCanvas();
      previousState = state;
    }
    if (debugEnabled) {
      const status = el('status');
      status.textContent = state === 'error' ? game.error : ready ? `City ready · ${state}` : 'Building the city…';
      status.dataset.state = state;
      el('metrics').textContent = `${Math.round(game.metrics.fps)} fps · ${game.metrics.draws} draws · ${game.metrics.tris.toLocaleString()} tris`;
      const player = game.player?.snapshot;
      el('position').textContent = player ? `x ${player.x.toFixed(1)} · y ${player.y.toFixed(2)} · z ${player.z.toFixed(1)} · ${player.grounded ? 'grounded' : 'falling'}` : '';
      const select = el<HTMLSelectElement>('view');
      const active = game.cameras.active.name;
      select.value = CAMERA_NAMES.includes(active as typeof CAMERA_NAMES[number]) ? active : 'follow';
      select.disabled = !playing;
      el<HTMLButtonElement>('save').disabled = !playing || saving || select.value === 'follow';
      el<HTMLButtonElement>('reset').disabled = !playing;
    }
  };
  root.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || !activeDialog) return;
    const focusable = [...activeDialog.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), [tabindex="0"]')].filter(node => !node.closest('[hidden]'));
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first) { event.preventDefault(); activeDialog.focus(); return; }
    if (event.shiftKey && (document.activeElement === first || !activeDialog.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && (document.activeElement === last || !activeDialog.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
  });
  root.addEventListener('click', event => {
    const button = (event.target as Element).closest<HTMLButtonElement>('button');
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-close')) close();
    else if (button.dataset.choice) game.chooseDialogue(button.dataset.choice);
    else if (button.dataset.buy && Object.hasOwn(ITEMS, button.dataset.buy)) game.buyItem(button.dataset.buy as ItemId);
    else if (button.dataset.sell && Object.hasOwn(ITEMS, button.dataset.sell)) game.sellItem(button.dataset.sell as ItemId);
    else if (button.dataset.node) game.selectGridNode(button.dataset.node);
    else if (button.dataset.hotbar !== undefined) {
      selectHotbar(Number(button.dataset.hotbar));
    }
    update();
  });
  pause.addEventListener('click', () => game.pause(true));
  el('resume').addEventListener('click', () => { game.pause(false); restoreCanvas(); });
  el('interact').addEventListener('click', () => game.interact());
  el('touch-interact').addEventListener('click', () => game.interact());
  el('reload').addEventListener('click', () => location.reload());
  optional<HTMLSelectElement>('view')?.addEventListener('change', event => { game.selectCamera((event.target as HTMLSelectElement).value); restoreCanvas(); });
  optional('reset')?.addEventListener('click', () => { game.reset(); restoreCanvas(); });
  optional('save')?.addEventListener('click', async () => {
    saving = true;
    const saved = el('save-status');
    saved.textContent = 'Saving frame…';
    update();
    try {
      const path = await game.shot(el<HTMLSelectElement>('view').value);
      saved.textContent = path.startsWith('download:') ? `Downloaded ${path.slice(9)}` : `Saved ${path}`;
    } catch (error) { saved.textContent = error instanceof Error ? error.message : 'Frame could not be saved.'; }
    finally { saving = false; update(); }
  });
  game.input.bindTouch(root);
  // Numeric keys and pointer buttons share one presentation/action path.
  game.input.onHotbar = selectHotbar;
  game.onUpdate = update;
  update();
}

export function showBootError(root: HTMLElement, error: unknown) {
  const message = error instanceof Error ? error.message : 'The renderer could not start.';
  root.dataset.state = 'error';
  root.querySelector<HTMLElement>('#play-hud')!.hidden = true;
  root.querySelector<HTMLElement>('#boot-message')!.hidden = false;
  root.querySelector<HTMLElement>('#boot-title')!.textContent = 'Connection interrupted';
  root.querySelector<HTMLElement>('#boot-detail')!.textContent = message;
  const reload = root.querySelector<HTMLButtonElement>('#reload')!;
  reload.hidden = false;
  reload.onclick = () => location.reload();
}
