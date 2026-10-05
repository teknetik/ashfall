import { chromium } from '../../app/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const OUT = path.dirname(new URL(import.meta.url).pathname);
const BASE = 'https://ashfall.teknetik.co';
const PORT = 3188;
const id = crypto.randomBytes(7).toString('hex');
const users = [0, 1].map((n) => ({ username: `qa${n}${id}`, password: `Q!${crypto.randomBytes(28).toString('base64url')}` }));
const errors = [];
const results = [];
const browser = await chromium.launch({ args: [`--host-resolver-rules=MAP ashfall.teknetik.co:443 127.0.0.1:${PORT}`] });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true, reducedMotion: 'reduce' });
const page = await context.newPage();
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
async function check(name, fn) { try { const detail = await fn(); results.push({ name, pass: true, detail: detail || 'ok' }); console.log('PASS', name, detail || ''); } catch(e) { results.push({ name, pass: false, error: String(e?.stack || e).split('\n').slice(0, 4).join(' | ') }); console.log('FAIL', name, String(e?.message || e)); } }
const goto = async p => { const r = await page.goto(`${BASE}${p}`, { waitUntil: 'networkidle' }); assert.equal(r.status(), 200, p); };
const marker = `QA idea ${id} <img src=x onerror=alert(1)> & 'quoted'`;
const edited = `QA edited ${id} <script>alert(1)</script> & text`;
const reply = `QA comment ${id} — recovery and repair matter.`;
let postId;
try {
  await check('desktop/tablet/mobile pages and screenshots, labels, images', async () => {
    const summary = [];
    for (const [name, width, height] of [['desktop',1440,900],['tablet',820,1180],['mobile',390,844]]) {
      await page.setViewportSize({ width, height });
      for (const route of ['/', '/gallery', '/discuss', '/about', '/privacy']) {
        await goto(route);
        const v = await page.evaluate(() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth, images: [...document.querySelectorAll('img:not(.lightbox img)')].map(i => ({alt: i.getAttribute('alt'), src: i.currentSrc || i.src})), labels: [...document.querySelectorAll('.fig__badge')].map(el => el.textContent.trim())}));
        assert.ok(v.scroll <= v.client, `${name} ${route} horizontal overflow ${v.scroll}/${v.client}`);
        assert.ok(v.images.every(i => i.alt !== null), `${name} ${route} image alt`);
        assert.ok(v.labels.every(x => /concept|in build|work-in-progress build/i.test(x)), `${name} ${route} image label: ${v.labels.join(', ')}`);
        if (route === '/' || route === '/gallery') {
          if (route === '/gallery') {
            for (const img of await page.locator('.gallery img').all()) await img.scrollIntoViewIfNeeded();
            await page.waitForFunction(() => [...document.querySelectorAll('.gallery img')].every(i => i.complete && i.naturalWidth > 0));
            await page.evaluate(() => window.scrollTo(0, 0));
          }
          await page.screenshot({ path: path.join(OUT, `${name}-${route === '/' ? 'home' : 'gallery'}.png`), fullPage: route === '/gallery' });
        }
        summary.push(`${name}:${route}:${v.images.length}img`);
      }
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await goto('/gallery');
    const imageResults = await page.evaluate(async () => {
      const urls = [...new Set([...document.querySelectorAll('picture source')].flatMap(el => (el.getAttribute('srcset') || '').split(',').map(s => s.trim().split(/\s+/)[0])).concat([...document.querySelectorAll('picture img')].map(el => el.getAttribute('src'))).filter(Boolean))];
      return Promise.all(urls.map(async url => {
        const response = await fetch(url); const b = await response.blob(); const i = new Image(); i.src = url;
        try { await i.decode(); return { url, status: response.status, bytes: b.size, width: i.naturalWidth, height: i.naturalHeight }; }
        catch(e) { return { url, status: response.status, bytes: b.size, width: 0, height: 0 }; }
      }));
    });
    fs.writeFileSync(path.join(OUT, 'image-results.json'), JSON.stringify(imageResults, null, 2));
    assert.ok(imageResults.length >= 20, `gallery variants count ${imageResults.length}`);
    assert.ok(imageResults.every(i => i.status === 200 && i.bytes > 0 && i.width > 0 && i.height > 0), 'all art decodes');
    return `${summary.length} page-size combinations; ${imageResults.length} served/decoded art variants`;
  });
  await check('menu/gallery keyboard and reduced motion', async () => {
    await page.setViewportSize({width:390,height:844}); await goto('/');
    const menu = page.locator('.site-header .menu-btn'); await menu.click();
    assert.equal(await menu.getAttribute('aria-expanded'),'true');
    await page.keyboard.press('Escape'); assert.equal(await menu.getAttribute('aria-expanded'),'false');
    await goto('/gallery'); await page.locator('.filters button[data-filter="concept"]').click();
    assert.ok(await page.locator('.gallery .fig:not([hidden])').count() > 0);
    const first = page.locator('.gallery a[data-lightbox]').first(); await first.focus(); await page.keyboard.press('Enter');
    assert.ok(await page.locator('.lightbox').isVisible()); await page.keyboard.press('ArrowRight'); await page.keyboard.press('Escape');
    assert.ok(await page.locator('.lightbox').isHidden());
    await goto('/'); const motion = await page.evaluate(() => ({all:document.querySelectorAll('.reveal').length,shown:document.querySelectorAll('.reveal.is-in').length}));
    assert.equal(motion.all,motion.shown);
    await page.setViewportSize({width:1440,height:900});
    return 'Escape/arrow keyboard and reduced-motion static reveals';
  });
  await check('anonymous post refused; CSRF and Origin rejected', async () => {
    const anon = await browser.newContext({ignoreHTTPSErrors:true});
    const r = await anon.request.post(`https://127.0.0.1:${PORT}/discuss/world/posts`, { headers: {'Host':'ashfall.teknetik.co','Origin':BASE,'Content-Type':'application/x-www-form-urlencoded'}, data:'type=idea&body=unauthorized' });
    assert.equal(r.status(),403); await anon.close();
    await goto('/join');
    const csrf = await page.locator('form[action="/join"] input[name="_csrf"]').inputValue();
    const cookies = await context.cookies(BASE);
    const cookie = cookies.map(c=>`${c.name}=${c.value}`).join('; ');
    const body = new URLSearchParams({_csrf:csrf,username:users[0].username,password:users[0].password,confirm:users[0].password,privacy:'yes'}).toString();
    const badOrigin = await context.request.post(`https://127.0.0.1:${PORT}/join`, {headers:{'Host':'ashfall.teknetik.co','Origin':'https://evil.example','Cookie':cookie,'Content-Type':'application/x-www-form-urlencoded'},data:body,maxRedirects:0});
    assert.equal(badOrigin.status(),403);
    const noCsrf = await context.request.post(`https://127.0.0.1:${PORT}/join`, {headers:{'Host':'ashfall.teknetik.co','Origin':BASE,'Cookie':cookie,'Content-Type':'application/x-www-form-urlencoded'},data:body.replace(`_csrf=${encodeURIComponent(csrf)}`, '_csrf=wrong'),maxRedirects:0});
    assert.equal(noCsrf.status(),403);
    return 'anonymous 403, foreign Origin 403, invalid token 403';
  });
  await check('signup, post XSS text, edit, malformed input', async () => {
    await goto('/join'); await page.fill('#username',users[0].username); await page.fill('#password',users[0].password); await page.fill('#confirm',users[0].password); await page.check('#privacy');
    await Promise.all([page.waitForURL(/\/discuss/), page.locator('form[action="/join"] button[type="submit"]').click()]);
    const session = (await context.cookies(BASE)).find(c=>c.name==='__Host-ashfall_session');
    assert.ok(session?.secure && session.httpOnly && session.sameSite==='Lax');
    await goto('/discuss/world'); await page.locator('#composer input[name="type"][value="idea"]').check(); await page.fill('#body',marker);
    await Promise.all([page.waitForURL(/done=posted/),page.locator('#composer button[type="submit"]').click()]);
    const post = page.locator('.post', {hasText:marker}); assert.equal(await post.count(),1);
    postId = Number((await post.getAttribute('id')).split('-')[1]);
    assert.equal(await post.locator('img,script').count(),0);
    await page.reload({waitUntil:'networkidle'}); assert.equal(await page.locator(`#post-${postId}`).count(),1);
    await page.locator(`#post-${postId} a[href$="/edit"]`).click();
    await page.fill('textarea[name="body"]', edited); await Promise.all([page.waitForURL(/done=edited/),page.locator('form[action$="/edit"] button[type="submit"]').click()]);
    assert.equal(await page.locator(`#post-${postId} script`).count(),0);
    assert.ok((await page.locator(`#post-${postId}`).innerText()).includes(edited));
    const form = page.locator('#composer');
    await form.locator('input[name="type"][value="idea"]').check(); await form.locator('#body').fill('tiny');
    const invalid = await form.evaluate(async el => { const fields = new FormData(el); const r = await fetch(el.action,{method:'POST',body:new URLSearchParams(fields),headers:{'Content-Type':'application/x-www-form-urlencoded'}}); return r.status; });
    assert.equal(invalid,400);
    await page.locator(`#post-${postId} details`).first().locator('summary').click();
    await page.fill(`#reply-${postId}`,reply);
    await Promise.all([page.waitForURL(/done=replied/),page.locator(`#post-${postId} form[action="/discuss/world/posts"] button`).click()]);
    assert.ok((await page.locator(`#post-${postId} .post--reply`).innerText()).includes(reply));
    return `idea #${postId}, comment, escaped, edited, invalid body 400`;
  });
  await check('second user cannot edit/delete first user post', async () => {
    const ctx2 = await browser.newContext({viewport:{width:1280,height:800},ignoreHTTPSErrors:true}); const p2 = await ctx2.newPage();
    await p2.goto(`${BASE}/join`); await p2.fill('#username',users[1].username); await p2.fill('#password',users[1].password); await p2.fill('#confirm',users[1].password); await p2.check('#privacy');
    await Promise.all([p2.waitForURL(/\/discuss/),p2.locator('form[action="/join"] button[type="submit"]').click()]);
    let r = await p2.goto(`${BASE}/posts/${postId}/edit`); assert.equal(r.status(),403);
    const token = await p2.locator('form[action="/logout"] input[name="_csrf"]').first().inputValue();
    const cookie = (await ctx2.cookies(BASE)).map(c=>`${c.name}=${c.value}`).join('; ');
    const req = async (url, body) => ctx2.request.post(`https://127.0.0.1:${PORT}${url}`,{headers:{'Host':'ashfall.teknetik.co','Origin':BASE,'Cookie':cookie,'Content-Type':'application/x-www-form-urlencoded'},data:new URLSearchParams({_csrf:token,...body}).toString(),maxRedirects:0});
    r = await req(`/posts/${postId}/edit`,{body:'Adversary edit'}); assert.equal(r.status(),403);
    r = await req(`/posts/${postId}/delete`,{}); assert.equal(r.status(),403);
    await ctx2.close(); return 'GET edit 403, POST edit 403, POST delete 403';
  });
  await check('service restart persists account, session, edited post', async () => {
    const before = await page.goto(`${BASE}/api/health`); const a=await before.json();
    execFileSync('systemctl',['--user','restart','ashfall-promo-qa'],{stdio:'pipe'});
    let health;
    for(let i=0;i<30;i++) { try { const r=await page.goto(`${BASE}/api/health`,{timeout:3000}); if(r.status()===200) { health=await r.json(); if(health.uptimeS< a.uptimeS) break; } } catch {} await new Promise(resolve=>setTimeout(resolve,500)); }
    assert.ok(health && health.uptimeS < a.uptimeS, `uptime before ${a.uptimeS}, after ${health?.uptimeS}`);
    await goto('/discuss/world'); assert.ok((await page.locator(`#post-${postId}`).innerText()).includes(edited));
    assert.ok((await page.locator(`#post-${postId} .post--reply`).innerText()).includes(reply));
    await goto('/account'); assert.ok((await page.locator('main').innerText()).includes(users[0].username));
    return `before uptime ${a.uptimeS}s, after ${health.uptimeS}s, same account/session/post`;
  });
  await check('owner delete, logout/login and persistent deletion', async () => {
    await goto('/discuss/world');
    page.once('dialog', dialog => dialog.accept());
    const deleteResponse = await Promise.all([page.waitForResponse(r => r.url().includes(`/posts/${postId}/delete`)), page.locator(`#post-${postId} form[action="/posts/${postId}/delete"] button`).click()]);
    assert.equal(deleteResponse[0].status(),303,`owner delete response ${deleteResponse[0].status()}`);
    await page.waitForURL(/done=deleted/);
    await page.reload({waitUntil:'networkidle'});
    assert.ok(!(await page.locator('main').innerText()).includes(edited));
    await goto('/account'); await Promise.all([page.waitForURL(/signedout/),page.locator('form[action="/logout"] button').first().click()]);
    await goto('/login'); await page.fill('#username',users[0].username); await page.fill('#password',users[0].password);
    await Promise.all([page.waitForURL(/\/discuss/),page.locator('form[action="/login"] button[type="submit"]').click()]);
    await goto('/discuss/world'); assert.ok(!(await page.locator('main').innerText()).includes(edited));
    return 'owner delete retained across reload and logout/new login';
  });
  assert.ok(errors.every(e => e.includes('400 (Bad Request)')),`unexpected browser console errors: ${errors.join('; ')}`);
} finally {
  await context.close(); await browser.close();
  fs.writeFileSync(path.join(OUT,'results.json'),JSON.stringify({candidate:'20261001-77c53f7228e8',results,consoleErrors:errors},null,2));
  console.log(`RESULT ${results.filter(x=>x.pass).length}/${results.length}; console errors ${errors.length}`);
}
if(results.some(x=>!x.pass))process.exitCode=1;
