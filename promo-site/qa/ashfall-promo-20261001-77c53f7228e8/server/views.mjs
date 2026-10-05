// Server-rendered views. Editorial HTML from dist/content.json is trusted build output (raw);
// everything that originates from users or requests goes through the escaping html`` template.
import { html, raw, esc, userText } from './html.mjs';

export const TOPIC_ART = {
  world: 'tir-world-map', ward: 'ward-vanguard-hall-concept', opening: 'ashfall-nano-infirmary-awakening',
  lattice: 'ashfall-first-signal-node', build: 'build-field-pack-20261001', machines: 'outer-berms-depot-concept',
  companions: 'ashfall-companion-recovery', atlas: 'ashfall-bleached-flats-caravan', testing: 'build-ward-hill-20261001',
  general: 'ashfall-ward-hero',
};

export const NAV = [
  ['/#world', 'The World'], ['/#opening', 'Story'], ['/#lattice', 'The Lattice'], ['/#build', 'Survive & Build'],
  ['/#companions', 'Companions'], ['/#atlas', 'Atlas'], ['/#testing', 'Early testing'],
];

const fmtDate = (ms) => {
  const d = new Date(ms);
  return `${d.getUTCDate()} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getUTCMonth()]} ${d.getUTCFullYear()}, ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} UTC`;
};
export const timeTag = (ms) => html`<time datetime="${new Date(ms).toISOString()}" data-relative>${fmtDate(ms)}</time>`;

/**
 * @param {{content: any, assets: Record<string, any>, bundles: Record<string, string>, ogUrl: string, origin: string, fonts: Record<string, string>, release?: string}} site loaded dist/content.json plus runtime origin
 */
export function createViews(site) {
  const { content, assets, bundles, ogUrl } = site;
  const meta = content.meta;
  const topicsBySlug = Object.fromEntries(content.topics.map((t) => [t.slug, t]));

  const picture = (a, sizes, cls = '', eager = false) => {
    const v = a.variants;
    const set = (f) => v.map((x) => `${x[f]} ${x.width}w`).join(', ');
    return raw(`<picture><source type="image/avif" srcset="${set('avif')}" sizes="${sizes}"><source type="image/webp" srcset="${set('webp')}" sizes="${sizes}"><img src="${eager ? v.at(-1).jpg : v[0].jpg}" srcset="${set('jpg')}" sizes="${sizes}" width="${v.at(-1).width}" height="${v.at(-1).height}" alt="${esc(a.alt)}" ${eager ? 'fetchpriority="high"' : 'loading="lazy" decoding="async"'}${cls ? ` class="${cls}"` : ''}></picture>`);
  };
  const badge = (a) => html`<span class="badge badge--${a.kind}">${a.label}</span>`;

  /**
   * @param {{title?: string, description?: string, path: string, body: any, user?: any, csrf?: string, solidHeader?: boolean, noindex?: boolean, active?: string, flash?: any}} p
   */
  function layout(p) {
    const title = p.title ? `${p.title} — Ashfall` : meta['title tag'];
    const desc = p.description || meta['meta description'];
    const canonical = `${site.origin}${p.path}`;
    const user = p.user;
    const authBlock = user
      ? html`<span class="header-user">Signed in as <a href="/account">${user.username}</a></span>
        <form method="post" action="/logout" class="header-logout"><input type="hidden" name="_csrf" value="${p.csrf}"><button class="btn btn--ghost btn--small" type="submit">Sign out</button></form>`
      : html`<a class="btn btn--ghost btn--small" href="/login">Sign in</a>`;
    const navItems = NAV.map(([href, label]) => html`<li><a href="${href}">${label}</a></li>`);
    return html`<!doctype html>
<html lang="en-GB" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${title}</title>
<meta name="description" content="${desc}">
<link rel="canonical" href="${canonical}">
${p.noindex ? raw('<meta name="robots" content="noindex">') : ''}
<meta name="theme-color" content="#14110e">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ashfall">
<meta property="og:title" content="${p.title ? title : meta['og title']}">
<meta property="og:description" content="${p.description || meta['og description']}">
<meta property="og:url" content="${canonical}">
<meta property="og:image" content="${site.origin}${ogUrl}">
<meta property="og:image:alt" content="${assets['ashfall-ward-hero'].alt}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="${site.fonts['fraunces.woff2']}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="${bundles['site.css']}">
<script src="${bundles['site.js']}" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header${p.solidHeader ? ' site-header--solid' : ''}">
  <div class="site-header__inner">
    <a class="wordmark" href="/"><span class="wordmark__mark" aria-hidden="true"></span>Ashfall</a>
    <nav class="nav" aria-label="Primary"><ul>${navItems}</ul></nav>
    <div class="header-actions">
      <a class="btn btn--small header-discuss" href="/discuss"${p.active === 'discuss' ? raw(' aria-current="page"') : ''}>Discuss</a>
      ${authBlock}
      <button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-menu">Menu</button>
    </div>
  </div>
</header>
<div class="menu" id="site-menu" hidden role="dialog" aria-modal="true" aria-label="Site menu">
  <div class="menu__top"><a class="wordmark" href="/"><span class="wordmark__mark" aria-hidden="true"></span>Ashfall</a><button class="menu-btn menu__close" type="button">Close <span aria-hidden="true">×</span></button></div>
  <nav aria-label="Menu"><ul>${navItems}<li><a href="/gallery">Gallery</a></li><li><a href="/discuss">Discuss</a></li></ul></nav>
  <div class="menu__foot">${user ? html`<span>Signed in as <a href="/account">${user.username}</a></span>` : html`<a class="btn" href="/join">Create an account</a><a class="btn btn--ghost" href="/login">Sign in</a>`}<a class="btn btn--ghost" href="/discuss">Discuss</a></div>
</div>
<main id="main" tabindex="-1">
${p.flash ? html`<div class="toast">${p.flash}</div>` : ''}
${p.body}
</main>
<footer class="site-footer">
  <div class="site-footer__inner">
    <div>
      <a class="wordmark" href="/"><span class="wordmark__mark" aria-hidden="true"></span>Ashfall</a>
      <p>${meta['footer status line']}</p>
    </div>
    <nav aria-label="Footer">
      <ul><li><a href="/gallery">Gallery</a></li><li><a href="/discuss">Discuss</a></li><li><a href="/about">About</a></li><li><a href="/privacy">Privacy</a></li></ul>
      <small>Art on this site is concept art unless marked “In build”. © Teknetik.</small>
    </nav>
  </div>
</footer>
</body>
</html>`;
  }

  const discussLink = (slug, counts) => {
    const c = counts[slug] || { likes: 0, ideas: 0, feedback: 0 };
    const t = topicsBySlug[slug];
    return html`<p class="discuss-this"><a class="btn btn--ghost" href="/discuss/${slug}">Discuss “${t.title}”</a> <span class="counts"><span>${c.likes} like${c.likes === 1 ? '' : 's'}</span><span>${c.ideas} idea${c.ideas === 1 ? '' : 's'}</span><span>${c.feedback} feedback</span></span></p>`;
  };

  const postSnippet = (p) => html`<article class="post post--${p.type}">
    <div class="post__meta"><span class="badge badge--${p.type === 'idea' ? 'concept' : 'planned'}">${p.type === 'idea' ? 'Idea' : 'Feedback'}</span><span class="post__author">${p.username || 'deleted account'}</span>${timeTag(p.created_at)}<a href="/discuss/${p.topic}#post-${p.id}">in ${topicsBySlug[p.topic]?.title || p.topic}</a></div>
    <div class="post__body">${userText(p.body.length > 280 ? `${p.body.slice(0, 277)}…` : p.body)}</div>
  </article>`;

  function home({ user, csrf, counts, recent, flashCode }) {
    const heroA = assets['ashfall-ward-hero'];
    const h = content.hero;
    const chapters = content.chapters.map((c) => html`
<section id="${c.id}" class="section chapter ${c.parchment ? 'parchment' : c.number % 2 ? 'section--dark' : 'section--alt'}${c.sub ? ' chapter--sub' : ''}" aria-labelledby="${c.id}-h">
  ${c.leadHtml ? raw(`<div class="chapter__lead">${c.leadHtml}</div>`) : ''}
  <div class="chapter__grid">
    <header class="chapter__head reveal">
      ${c.number ? html`<p class="chapter__num">Chapter ${String(c.number).padStart(2, '0')}</p>` : ''}
      ${c.kicker ? html`<p class="kicker">${c.kicker}</p>` : ''}
      <h2 id="${c.id}-h">${raw(c.titleHtml)}</h2>
      ${c.standfirstHtml ? raw(`<p class="standfirst">${c.standfirstHtml}</p>`) : ''}
    </header>
    ${raw(c.railHtml)}
    <div class="prose">
      ${raw(c.bodyHtml)}
      ${c.id === 'jacks' || c.id === 'companions' ? '' : discussLink(c.topic, counts)}
      ${c.id === 'jacks' ? discussLink('companions', counts) : ''}
    </div>
  </div>
</section>`);
    const at = content.atlas;
    const map = assets['tir-world-map'];
    const body = html`
<section class="hero" aria-labelledby="hero-h">
  <div class="hero__art">${picture(heroA, '100vw', '', true)}</div>
  <div class="hero__inner">
    <div class="hero__text">
      <p class="kicker">${h.kicker}</p>
      <h1 id="hero-h">${h.title}</h1>
      <p class="hero__premise">${h.premise}</p>
      <p class="hero__boot" data-text="${h.boot}"><span class="hero__boot-text" aria-hidden="true">${h.boot}</span><span class="visually-hidden">${h.boot}</span></p>
      <div class="hero__ctas"><a class="btn" href="#world">${h.ctaPrimary}</a><a class="btn btn--ghost" href="/discuss">${h.ctaSecondary}</a></div>
    </div>
  </div>
  <div class="hero__badge">${badge(heroA)}</div>
</section>
${chapters}
<section id="atlas" class="section section--dark atlas" aria-labelledby="atlas-h">
  <div class="atlas__head reveal">
    <p class="chapter__num">Chapter 08</p>
    <p class="kicker">${at.kicker}</p>
    <h2 id="atlas-h">${at.title}</h2>
    <p class="standfirst">${raw(at.introHtml)}</p>
  </div>
  <div class="atlas__layout">
    <div class="atlas__map">
      <figure class="fig" data-asset="tir-world-map">
        <div class="mapwrap">
          <a class="fig__link" href="${map.variants.at(-1).jpg}" data-lightbox="atlas-map" aria-label="Enlarge image: ${map.title}">${picture(map, '(min-width: 1024px) 700px, 100vw')}</a>
          <nav class="spots" aria-label="Regions on the map">${raw(at.spots)}</nav>
        </div>
        <div class="fig__badge">${badge(map)}</div>
        <figcaption><span class="fig__title">${map.title}.</span> ${at.mapCaption} ${map.caption}</figcaption>
      </figure>
    </div>
    <div class="atlas__regions">${raw(at.regionsHtml)}</div>
  </div>
  <div class="atlas__between prose">${raw(at.betweenHtml)}${discussLink('atlas', counts)}</div>
</section>
<section id="testing" class="section section--alt" aria-labelledby="testing-h">
  <div class="testing__grid">
    <div class="prose">
      <p class="chapter__num">Chapter 09</p>
      <p class="kicker">${content.testing.kicker}</p>
      <h2 id="testing-h">${raw(content.testing.titleHtml)}</h2>
      ${raw(content.testing.bodyHtml)}
      ${discussLink('testing', counts)}
    </div>
    ${raw(content.testing.figuresHtml)}
  </div>
</section>
<section id="voices" class="section section--dark" aria-labelledby="voices-h">
  <div class="teaser">
    <p class="kicker">Discussion</p>
    <h2 id="voices-h">${content.discuss['teaser heading']}</h2>
    ${recent.length ? html`<div class="teaser__list">${recent.map(postSnippet)}</div>` : html`<p class="lede">${content.discuss['teaser empty state']}</p>`}
    <p><a class="btn" href="/discuss">${content.discuss.cta}</a> ${user ? '' : html`<a class="btn btn--ghost" href="/join">Create an account</a>`}</p>
  </div>
</section>`;
    return layout({ path: '/', body, user, csrf, flash: flash(flashCode) });
  }

  function gallery({ user, csrf }) {
    const order = ['ashfall-ward-hero', 'tir-world-map', 'ward-vanguard-hall-concept', 'ashfall-nano-infirmary-awakening', 'ashfall-first-signal-node', 'outer-berms-depot-concept', 'ashfall-companion-recovery', 'ashfall-bleached-flats-caravan', 'ashfall-verdant-fold-station', 'build-ward-hill-20261001', 'build-field-pack-20261001'];
    const intros = content.galleryIntros;
    const items = order.map((id) => {
      const a = assets[id];
      const filters = [a.kind === 'build' ? 'build' : 'concept', a.planned ? 'planned' : ''].filter(Boolean).join(' ');
      return html`<figure class="fig${id === 'tir-world-map' ? ' fig--map' : ''}" data-filters="${filters}" data-asset="${id}">
        <a class="fig__link" href="${a.variants.at(-1).jpg}" data-lightbox="gallery" aria-label="Enlarge image: ${a.title}">${picture(a, id === 'tir-world-map' ? '(min-width: 1024px) 66vw, 100vw' : '(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw')}</a>
        <div class="fig__badge">${badge(a)}</div>
        <figcaption><span class="fig__title">${a.title}.</span> ${a.caption}</figcaption>
      </figure>`;
    });
    const body = html`<div class="page"><div class="page__inner page__inner--wide">
      <p class="kicker">Gallery</p>
      <h1>Art of Ashfall</h1>
      <p class="lede">Every image is labelled. Concept art explores the look and mood of Tir; “In build” captures come from the current development build and are dated.</p>
      <div class="filters" role="group" aria-label="Filter images" hidden>
        <button type="button" data-filter="all" aria-pressed="true" data-intro="">All</button>
        <button type="button" data-filter="concept" aria-pressed="false" data-intro="${intros['concept art'] || ''}">Concept art</button>
        <button type="button" data-filter="planned" aria-pressed="false" data-intro="${intros['planned regions'] || ''}">Planned regions</button>
        <button type="button" data-filter="build" aria-pressed="false" data-intro="${intros['in build'] || ''}">In build</button>
      </div>
      <p class="filter-intro" aria-live="polite"></p>
      <div class="gallery">${items}</div>
    </div></div>`;
    return layout({ title: 'Gallery', path: '/gallery', body, user, csrf, solidHeader: true, description: 'Concept art and dated development-build captures for Ashfall, each clearly labelled.' });
  }

  function about({ user, csrf }) {
    const body = html`<div class="page"><div class="page__inner prose">
      <p class="kicker">About</p><h1>${content.aboutTitle}</h1>
      ${raw(content.aboutHtml)}
      <h2 id="faq">Questions from early testers</h2>
      <div class="faq">${content.faq.map((f) => html`<details><summary>${f.q}</summary><div>${raw(f.aHtml)}</div></details>`)}</div>
    </div></div>`;
    return layout({ title: 'About', path: '/about', body, user, csrf, solidHeader: true });
  }

  function privacy({ user, csrf, sessionDays }) {
    const body = html`<div class="page"><div class="page__inner prose">
      <p class="kicker">Privacy</p><h1>Privacy</h1>
      <p class="lede">Reading this site does not require an account, and reading sets no cookies.</p>
      <h2>If you create an account, we store</h2>
      <ul>
        <li>Your chosen username (shown publicly next to your posts).</li>
        <li>A salted scrypt hash of your password. We never store or see the password itself, and passwords are never written to logs.</li>
        <li>The date your account was created and when your password was last set.</li>
        <li>Your role (member or moderator) and whether the account is suspended.</li>
        <li>Your sign-in sessions: a random session identifier (stored only as a one-way hash), when it was created, when it was last used, and when it expires (at most ${sessionDays} days after sign-in).</li>
      </ul>
      <p>We don't ask for your email address, real name, phone number or location.</p>
      <h2>If you post, we store</h2>
      <ul>
        <li>What you wrote, the topic and post type (idea, feedback or reply), any feedback tag you chose, when you posted and when you last edited it.</li>
        <li>Which topics and posts you liked, and when.</li>
        <li>Reports you make about other posts (the reason you chose and when).</li>
      </ul>
      <p>Posts, usernames and like counts are public. Who liked what is not shown publicly.</p>
      <h2>Operational data</h2>
      <p>To protect the site from abuse, the server keeps rate-limit counters in memory, keyed by network address and username. They expire within 24 hours and are discarded whenever the service restarts; they are never written to the database. The server log records each request's method, path (without query string), response status and duration. It does not record your network address, username, passwords, cookies or what you post. Logs are kept by the host's system journal under its normal rotation.</p>
      <p>Moderators can see reports and the original text of posts they have removed. Moderation actions (remove, restore, lock, suspend) are recorded with the moderator and the reason.</p>
      <h2>Cookies</h2>
      <ul>
        <li><strong>Session cookie</strong> (<code>__Host-ashfall_session</code>): set only when you sign in; keeps you signed in. Secure, HttpOnly, limited to this site.</li>
        <li><strong>Form security cookie</strong> (<code>__Host-ashfall_csrf</code>): set only when you open the sign-in or join page; protects those forms from cross-site forgery. It expires when you close your browser.</li>
      </ul>
      <p>There are no advertising, analytics or tracking cookies, no third-party scripts, fonts or embeds. Everything on this site is served from this site.</p>
      <h2>Deleting your data</h2>
      <p>You can edit or delete your own posts at any time. You can delete your account from your <a href="/account">account page</a>. Deleting your account immediately removes your username, password hash, sessions, likes and reports, and erases the text of all your posts. Where other people replied to one of your posts, an empty “deleted” placeholder remains so their replies still make sense; it carries no text and no username.</p>
      <p>Database backups are taken daily for disaster recovery and kept for a limited period (up to about a month). Data you delete disappears from backups as they expire.</p>
      <p>Moderators may remove posts that break the discussion rules.</p>
      <h2>Contact</h2>
      <p>The easiest way to reach the people running this site is to post in <a href="/discuss/general">General feedback</a>. Please do not post personal information there.</p>
    </div></div>`;
    return layout({ title: 'Privacy', path: '/privacy', body, user, csrf, solidHeader: true, description: 'What the Ashfall site stores, why, and how to delete it.' });
  }

  const topicThumb = (slug) => {
    const a = assets[TOPIC_ART[slug]];
    const v = a.variants[0];
    return { a, html: raw(`<img src="${v.jpg}" width="${v.width}" height="${v.height}" alt="" loading="lazy" decoding="async">`) };
  };

  function discussIndex({ user, csrf, counts, flashCode }) {
    const cards = content.topics.map((t) => {
      const c = counts[t.slug] || { likes: 0, ideas: 0, feedback: 0, locked: 0 };
      const th = topicThumb(t.slug);
      return html`<a class="topic-card" href="/discuss/${t.slug}">${th.html}<div><p class="topic-card__title">${t.title}${c.locked ? ' (locked)' : ''}</p><p class="topic-card__prompt">${t.prompt}</p><p class="counts"><span>${c.likes} likes</span><span>${c.ideas} ideas</span><span>${c.feedback} feedback</span><span class="badge badge--${th.a.kind}">${th.a.label}</span></p></div></a>`;
    });
    const body = html`<div class="page"><div class="page__inner page__inner--wide">
      ${flash(flashCode)}
      <p class="kicker">Early-tester discussion</p>
      <h1>Discuss Ashfall</h1>
      <p class="lede">One thread per chapter, plus general feedback. Reading is open to everyone; ${user ? html`you're signed in as <strong>${user.username}</strong>.` : html`<a href="/join">create an account</a> or <a href="/login">sign in</a> to post.`}</p>
      <div class="notice"><p class="kicker">Discussion rules</p>${raw(content.rulesHtml)}</div>
      <div class="topics">${cards}</div>
    </div></div>`;
    return layout({ title: 'Discuss', path: '/discuss', body, user, csrf, solidHeader: true, active: 'discuss', description: 'Early-tester discussion threads for Ashfall: ideas, feedback and likes for each part of the design.' });
  }

  const FLASH = {
    posted: ['ok', 'Posted. Thank you.'], replied: ['ok', 'Reply posted.'], deleted: ['ok', 'Post deleted.'], edited: ['ok', 'Post updated.'],
    liked: ['ok', 'Noted — you like this direction.'], unliked: ['ok', 'Like removed.'], reported: ['ok', 'Report sent to the moderators. Thank you.'],
    welcome: ['ok', 'Account created. Welcome to the discussion.'], signedin: ['ok', 'Signed in.'], signedout: ['ok', 'Signed out.'],
    password: ['ok', 'Password changed. Other sessions were signed out.'], locked: ['warn', 'This topic is locked by a moderator. Reading is still open.'],
    removed: ['ok', 'Post removed.'], restored: ['ok', 'Post restored.'], suspended: ['ok', 'User suspended.'], unsuspended: ['ok', 'User reinstated.'],
    resolved: ['ok', 'Report resolved.'], topiclocked: ['ok', 'Topic locked.'], topicunlocked: ['ok', 'Topic unlocked.'], accountdeleted: ['ok', 'Your account and its data were deleted.'],
  };
  const flash = (code) => {
    const f = FLASH[code];
    return f ? html`<div class="notice notice--${f[0]}" role="status"><p class="lattice-line">${f[0] === 'ok' ? 'SIGNAL ACKNOWLEDGED · ' : ''}${f[1]}</p></div>` : '';
  };
  const errorNotice = (msg) => (msg ? html`<div class="notice notice--error" role="alert"><p>${msg}</p></div>` : '');

  const likeIcon = raw('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4.2" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/></g></svg>');

  function postHtml(p, ctx) {
    const { user, csrf, topic, locked, replies, likedPosts } = ctx;
    const isOwner = user && p.user_id === user.id;
    const isMod = user && user.role === 'moderator';
    if (p.deleted_at) {
      return html`<article class="post post--${p.type} post--removed" id="post-${p.id}"><p class="post__meta">Deleted by its author.</p>${replies && replies.length ? html`<div class="post__replies">${replies.map((r) => postHtml(r, { ...ctx, replies: null }))}</div>` : ''}</article>`;
    }
    const removed = !!p.removed_at;
    const typeLabel = { idea: 'Idea', feedback: 'Feedback', reply: 'Reply' }[p.type];
    const badgeKind = { idea: 'concept', feedback: 'planned', reply: 'exploring' }[p.type];
    const canAct = user && user.status === 'active' && !locked;
    return html`<article class="post post--${p.type}${removed ? ' post--removed' : ''}" id="post-${p.id}" aria-labelledby="post-${p.id}-meta">
      <div class="post__meta" id="post-${p.id}-meta"><span class="badge badge--${badgeKind}">${typeLabel}</span>${p.tag ? html`<span class="badge badge--exploring">${p.tag}</span>` : ''}<span class="post__author">${p.username || 'deleted account'}</span>${p.author_role === 'moderator' ? html`<span class="badge badge--build">Moderator</span>` : ''}${timeTag(p.created_at)}${p.edited_at ? html`<span>(edited)</span>` : ''}</div>
      ${removed ? html`<p class="post__body"><em>Removed by moderator.</em></p>` : html`<div class="post__body">${userText(p.body)}</div>`}
      ${removed ? '' : html`<div class="post__actions">
        ${p.type !== 'reply' ? (canAct && !isOwner
          ? html`<form method="post" action="/posts/${p.id}/like"><input type="hidden" name="_csrf" value="${csrf}"><button class="post-like" type="submit" aria-pressed="${likedPosts.has(p.id) ? 'true' : 'false'}">${likeIcon}<span>${p.likes}</span><span class="visually-hidden"> likes — ${likedPosts.has(p.id) ? 'remove your like' : 'like this post'}</span></button></form>`
          : html`<span class="counts"><span>${p.likes} like${p.likes === 1 ? '' : 's'}</span></span>`) : ''}
        ${canAct && p.type !== 'reply' ? html`<details><summary>Reply</summary>
          <form method="post" action="/discuss/${topic}/posts" class="form form--wide">
            <input type="hidden" name="_csrf" value="${csrf}"><input type="hidden" name="type" value="reply"><input type="hidden" name="parent" value="${p.id}">
            <div class="field"><label for="reply-${p.id}">Your reply to ${p.username || 'this post'}</label><textarea id="reply-${p.id}" name="body" required minlength="2" maxlength="2000" rows="3"></textarea></div>
            <div><button class="btn btn--small" type="submit">Post reply</button></div>
          </form></details>` : ''}
        ${isOwner ? html`<a class="linkbtn" href="/posts/${p.id}/edit">Edit</a>
          <form method="post" action="/posts/${p.id}/delete" data-confirm="Delete this post? This cannot be undone."><input type="hidden" name="_csrf" value="${csrf}"><button class="linkbtn linkbtn--danger" type="submit">Delete</button></form>` : ''}
        ${user && !isOwner && user.status === 'active' ? html`<details><summary>Report</summary>
          <form method="post" action="/posts/${p.id}/report" class="form">
            <input type="hidden" name="_csrf" value="${csrf}">
            <div class="field"><label for="rr-${p.id}">Reason</label><select id="rr-${p.id}" name="reason"><option value="spam">Spam</option><option value="abuse">Harassment or abuse</option><option value="personal">Personal information</option><option value="spoiler">Unmarked spoilers</option><option value="other">Something else</option></select></div>
            <div><button class="btn btn--small btn--ghost" type="submit">Send report</button></div>
          </form></details>` : ''}
        ${isMod ? html`<details><summary>Moderate</summary>
          <form method="post" action="/moderation/posts/${p.id}/remove" class="form"><input type="hidden" name="_csrf" value="${csrf}">
            <div class="field"><label for="mr-${p.id}">Reason for removal</label><input id="mr-${p.id}" type="text" name="reason" required maxlength="200"></div>
            <div><button class="btn btn--small btn--danger" type="submit">Remove</button></div></form></details>` : ''}
      </div>`}
      ${isMod && removed ? html`<div class="post__actions"><p class="hint">Removed: ${p.removed_reason || 'no reason given'}. Original text is visible in the moderation queue.</p><form method="post" action="/moderation/posts/${p.id}/restore"><input type="hidden" name="_csrf" value="${csrf}"><button class="linkbtn" type="submit">Restore</button></form></div>` : ''}
      ${replies && replies.length ? html`<div class="post__replies">${replies.map((r) => postHtml(r, { ...ctx, replies: null }))}</div>` : ''}
    </article>`;
  }

  function topicPage({ user, csrf, slug, posts, repliesByParent, counts, likedTopic, likedPosts, sort, page, hasMore, flashCode, error, form }) {
    const t = topicsBySlug[slug];
    const c = counts;
    const th = assets[TOPIC_ART[slug]];
    const locked = !!c.locked;
    const canPost = user && user.status === 'active' && !locked;
    const typeVal = form?.type || 'idea';
    const composer = !user
      ? html`<div class="composer"><p><strong>Sign in or create an account to post.</strong> Reading is open to everyone.</p><p><a class="btn" href="/join?next=/discuss/${slug}">Create an account</a> <a class="btn btn--ghost" href="/login?next=/discuss/${slug}">Sign in</a></p></div>`
      : locked ? html`<div class="notice notice--warn"><p>This topic is locked by a moderator. Reading is still open.</p></div>`
        : user.status !== 'active' ? html`<div class="notice notice--warn"><p>Your account is suspended, so you can't post.</p></div>`
          : html`<form class="composer form form--wide" method="post" action="/discuss/${slug}/posts" id="composer" novalidate>
        <h2>Add to “${t.title}”</h2>
        <input type="hidden" name="_csrf" value="${csrf}">
        <fieldset class="seg"><legend class="visually-hidden">Post type</legend>
          <label><input type="radio" name="type" value="idea"${typeVal === 'idea' ? raw(' checked') : ''}> Idea</label>
          <label><input type="radio" name="type" value="feedback"${typeVal === 'feedback' ? raw(' checked') : ''}> Feedback</label>
        </fieldset>
        <p class="hint" id="composer-hint">Idea: what would you add or change? Feedback: what works or doesn't? Plain text, 10–2000 characters.</p>
        <div class="field composer__tag"><label for="tag">Feedback about (optional)</label><select id="tag" name="tag"><option value="">—</option>${['story', 'mechanics', 'art', 'build'].map((x) => html`<option value="${x}"${form?.tag === x ? raw(' selected') : ''}>${x[0].toUpperCase() + x.slice(1)}</option>`)}</select></div>
        <div class="field"><label for="body">Your post</label><textarea id="body" name="body" required minlength="10" maxlength="2000" rows="5" aria-describedby="composer-hint${error ? ' body-error' : ''}"${error ? raw(' aria-invalid="true"') : ''}>${form?.body || ''}</textarea>${error ? html`<p class="field-error" id="body-error">${error}</p>` : ''}</div>
        <div><button class="btn" type="submit">Post</button></div>
      </form>`;
    const likeBlock = html`<div class="like-form">${canPost
      ? html`<form method="post" action="/discuss/${slug}/like"><input type="hidden" name="_csrf" value="${csrf}"><button class="like-btn" type="submit" aria-pressed="${likedTopic ? 'true' : 'false'}">${likeIcon}<span>I like this direction</span></button></form>`
      : ''}<span class="counts"><span>${c.likes} like${c.likes === 1 ? '' : 's'}</span><span>${c.ideas} ideas</span><span>${c.feedback} feedback</span></span></div>`;
    const ctx = { user, csrf, topic: slug, locked, likedPosts };
    const list = posts.length
      ? posts.map((p) => postHtml(p, { ...ctx, replies: repliesByParent.get(p.id) || [] }))
      : html`<div class="empty">${picture(th, '12rem')}<div><p><strong>No posts yet.</strong> ${t.prompt}</p><p>${user ? 'Be the first to add an idea or some feedback.' : html`<a href="/join?next=/discuss/${slug}">Create an account</a> to be the first.`}</p><span class="badge badge--${th.kind}">${th.label}</span></div></div>`;
    const isMod = user && user.role === 'moderator';
    const body = html`<div class="page"><div class="page__inner">
      <p class="crumbs"><a href="/discuss">All topics</a> /</p>
      ${flash(flashCode)}
      <div class="topic-head">
        <div><p class="kicker">Topic</p><h1>${t.title}</h1><p class="lede">${t.prompt}</p>${likeBlock}
        ${slug !== 'general' && slug !== 'testing' ? html`<p><a href="/#${slug === 'build' ? 'build' : slug}">Read the chapter</a></p>` : slug === 'testing' ? html`<p><a href="/#testing">Read the early-testing status</a></p>` : ''}
        ${isMod ? html`<form method="post" action="/moderation/topics/${slug}/${locked ? 'unlock' : 'lock'}"><input type="hidden" name="_csrf" value="${csrf}"><button class="btn btn--small btn--ghost" type="submit">${locked ? 'Unlock topic' : 'Lock topic'}</button></form>` : ''}</div>
        <figure class="fig" data-asset="${th.id}">${picture(th, '16rem')}<div class="fig__badge">${badge(th)}</div></figure>
      </div>
      ${composer}
      <h2 class="visually-hidden">Posts</h2>
      <div class="sort">Sort: <a href="/discuss/${slug}?sort=new"${sort === 'new' ? raw(' aria-current="true"') : ''}>Newest</a> <a href="/discuss/${slug}?sort=liked"${sort === 'liked' ? raw(' aria-current="true"') : ''}>Most liked ideas</a></div>
      <div class="posts">${list}</div>
      ${hasMore ? html`<p><a class="btn btn--ghost" href="/discuss/${slug}?sort=${sort}&amp;page=${page + 1}#post-more">Load more</a></p>` : ''}
      <span id="post-more"></span>
    </div></div>`;
    return layout({ title: t.title, path: `/discuss/${slug}`, body, user, csrf, solidHeader: true, active: 'discuss', description: `Early-tester discussion: ${t.prompt}` });
  }

  /** @param {{mode: string, user: any, csrf: string, error?: string, fieldErrors?: Record<string, string>, values?: Record<string, any>, next?: string, inviteRequired?: boolean, signupEnabled?: boolean}} o */
  function authForm({ mode, user, csrf, error, fieldErrors = {}, values = {}, next = '', inviteRequired = false, signupEnabled = true }) {
    const isJoin = mode === 'join';
    const fe = (name) => (fieldErrors[name] ? html`<p class="field-error" id="${name}-error">${fieldErrors[name]}</p>` : '');
    const inv = (name) => (fieldErrors[name] ? raw(` aria-invalid="true" aria-describedby="${name}-error${name === 'password' ? ' password-hint' : ''}"`) : name === 'password' && isJoin ? raw(' aria-describedby="password-hint"') : '');
    const body = !isJoin || signupEnabled ? html`<div class="page"><div class="page__inner">
      <p class="kicker">${isJoin ? 'Join the discussion' : 'Welcome back'}</p>
      <h1>${isJoin ? 'Create an account' : 'Sign in'}</h1>
      <p class="lede">${isJoin ? 'An account lets you post ideas and feedback. We only ask for a username and a password — no email.' : 'Sign in to post, reply and like.'}</p>
      ${errorNotice(error)}
      <form class="form" method="post" action="${isJoin ? '/join' : '/login'}" novalidate>
        <input type="hidden" name="_csrf" value="${csrf}">
        <input type="hidden" name="next" value="${next}">
        <div class="field"><label for="username">Username</label>
          <input id="username" name="username" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" required minlength="3" maxlength="24" ${isJoin ? raw('pattern="[a-z0-9_-]{3,24}"') : ''} value="${values.username || ''}"${inv('username')}>
          ${isJoin ? html`<p class="hint">3–24 characters: lowercase letters, numbers, - and _. Shown publicly next to your posts.</p>` : ''}${fe('username')}</div>
        <div class="field"><label for="password">Password</label>
          <div class="pw"><input id="password" name="password" type="password" autocomplete="${isJoin ? 'new-password' : 'current-password'}" required ${isJoin ? raw('minlength="10"') : ''} maxlength="200"${inv('password')}></div>
          ${isJoin ? html`<p class="hint" id="password-hint">At least 10 characters. A few unrelated words make a good password. Use one you don't use anywhere else.</p>` : ''}${fe('password')}</div>
        ${isJoin ? html`<div class="field"><label for="confirm">Confirm password</label><div class="pw"><input id="confirm" name="confirm" type="password" autocomplete="new-password" required maxlength="200"${inv('confirm')}></div>${fe('confirm')}</div>
          ${inviteRequired ? html`<div class="field"><label for="invite">Invite code</label><input id="invite" name="invite" type="text" autocomplete="off" required maxlength="100"${inv('invite')}><p class="hint">Signup is currently limited to invited testers.</p>${fe('invite')}</div>` : ''}
          <div class="field"><div class="check"><input id="privacy" name="privacy" type="checkbox" value="yes" required${values.privacy ? raw(' checked') : ''}${inv('privacy')}><label for="privacy">I've read the <a href="/privacy" target="_blank" rel="noopener">privacy notice</a>.</label></div>${fe('privacy')}</div>
          <div class="visually-hidden" aria-hidden="true"><label for="website">Leave this empty</label><input id="website" name="website" type="text" tabindex="-1" autocomplete="off"></div>` : ''}
        <div><button class="btn" type="submit">${isJoin ? 'Create account' : 'Sign in'}</button></div>
      </form>
      <p>${isJoin ? html`Already have an account? <a href="/login${next ? `?next=${encodeURIComponent(next)}` : ''}">Sign in</a>.` : html`New here? <a href="/join${next ? `?next=${encodeURIComponent(next)}` : ''}">Create an account</a>. Forgotten passwords can't be recovered by email (we don't store one); ask a moderator in General feedback from a new account.`}</p>
    </div></div>` : html`<div class="page"><div class="page__inner"><h1>Signup is closed</h1><p class="lede">New accounts are not being accepted right now. Reading is still open to everyone.</p></div></div>`;
    return layout({ title: isJoin ? 'Create an account' : 'Sign in', path: isJoin ? '/join' : '/login', body, user, csrf, solidHeader: true, noindex: true });
  }

  /** @param {{user: any, csrf: string, posts: any[], flashCode?: string, error?: string, fieldErrors?: Record<string, string>}} o */
  function account({ user, csrf, posts, flashCode, error, fieldErrors = {} }) {
    const fe = (name) => (fieldErrors[name] ? html`<p class="field-error" id="${name}-error">${fieldErrors[name]}</p>` : '');
    const body = html`<div class="page"><div class="page__inner">
      ${flash(flashCode)}${errorNotice(error)}
      <p class="kicker">Account</p><h1>${user.username}</h1>
      <p>Member since ${timeTag(user.created_at)}.${user.role === 'moderator' ? html` You are a moderator — <a href="/moderation">open the moderation queue</a>.` : ''}</p>
      <h2>Your posts</h2>
      ${posts.length ? html`<ul>${posts.map((p) => html`<li><a href="/discuss/${p.topic}#post-${p.id}">${topicsBySlug[p.topic]?.title || p.topic}</a> · ${p.type} · ${timeTag(p.created_at)}${p.removed_at ? ' · removed by moderator' : ''}<br><span class="hint">${p.body.length > 120 ? `${p.body.slice(0, 117)}…` : p.body}</span></li>`)}</ul>` : html`<p>You haven't posted yet. <a href="/discuss">Browse the topics</a>.</p>`}
      <h2>Change password</h2>
      <form class="form" method="post" action="/account/password" novalidate>
        <input type="hidden" name="_csrf" value="${csrf}">
        <input type="text" name="username" value="${user.username}" autocomplete="username" hidden>
        <div class="field"><label for="current">Current password</label><div class="pw"><input id="current" name="current" type="password" autocomplete="current-password" required maxlength="200"></div>${fe('current')}</div>
        <div class="field"><label for="password">New password</label><div class="pw"><input id="password" name="password" type="password" autocomplete="new-password" required minlength="10" maxlength="200"></div>${fe('password')}</div>
        <div class="field"><label for="confirm">Confirm new password</label><div class="pw"><input id="confirm" name="confirm" type="password" autocomplete="new-password" required maxlength="200"></div>${fe('confirm')}</div>
        <div><button class="btn" type="submit">Change password</button></div>
      </form>
      <h2>Delete your account</h2>
      <p>This removes your username, password hash, sessions, likes and reports, and erases the text of all your posts. Where someone replied to one of your posts, an empty “deleted” placeholder stays so their replies still make sense. This cannot be undone.</p>
      <form class="form" method="post" action="/account/delete" data-confirm="Delete your account and erase all your posts? This cannot be undone." novalidate>
        <input type="hidden" name="_csrf" value="${csrf}">
        <div class="field"><label for="del-pw">Your password (to confirm)</label><div class="pw"><input id="del-pw" name="password" type="password" autocomplete="current-password" required maxlength="200"></div>${fe('delete')}</div>
        <div><button class="btn btn--danger" type="submit">Delete my account</button></div>
      </form>
    </div></div>`;
    return layout({ title: 'Your account', path: '/account', body, user, csrf, solidHeader: true, noindex: true });
  }

  /** @param {{user: any, csrf: string, post: any, error?: string}} o */
  function editPost({ user, csrf, post, error }) {
    const body = html`<div class="page"><div class="page__inner">
      <p class="crumbs"><a href="/discuss/${post.topic}#post-${post.id}">Back to the topic</a></p>
      <h1>Edit your post</h1>
      <form class="form form--wide" method="post" action="/posts/${post.id}/edit" novalidate>
        <input type="hidden" name="_csrf" value="${csrf}">
        <div class="field"><label for="body">Your post</label><textarea id="body" name="body" required maxlength="2000" rows="8"${error ? raw(' aria-invalid="true" aria-describedby="body-error"') : ''}>${post.body}</textarea>${error ? html`<p class="field-error" id="body-error">${error}</p>` : ''}</div>
        <div><button class="btn" type="submit">Save changes</button> <a href="/discuss/${post.topic}#post-${post.id}">Cancel</a></div>
      </form>
    </div></div>`;
    return layout({ title: 'Edit post', path: `/posts/${post.id}/edit`, body, user, csrf, solidHeader: true, noindex: true });
  }

  function moderation({ user, csrf, reports, removed, recent, users, flashCode }) {
    const postCell = (p) => html`<a href="/discuss/${p.topic}#post-${p.id}">#${p.id}</a> in ${p.topic} by ${p.username || 'deleted'}<br><span class="hint">${p.body.length > 200 ? `${p.body.slice(0, 197)}…` : p.body}</span>`;
    const body = html`<div class="page"><div class="page__inner page__inner--wide">
      ${flash(flashCode)}
      <p class="kicker">Moderators only</p><h1>Moderation</h1>
      <h2>Open reports (${reports.length})</h2>
      ${reports.length ? html`<div class="table-wrap"><table class="mod-table"><thead><tr><th>Post</th><th>Reason</th><th>Reported</th><th>Actions</th></tr></thead><tbody>${reports.map((r) => html`<tr><td>${postCell(r)}</td><td>${r.reason}${r.report_count > 1 ? ` (${r.report_count} reports)` : ''}</td><td>${timeTag(r.reported_at)}</td><td>
        ${r.removed_at ? html`<span>Already removed.</span>` : html`<form method="post" action="/moderation/posts/${r.id}/remove"><input type="hidden" name="_csrf" value="${csrf}"><label class="visually-hidden" for="rm-${r.id}">Reason</label><input id="rm-${r.id}" type="text" name="reason" required maxlength="200" placeholder="Reason"><button class="btn btn--small btn--danger" type="submit">Remove</button></form>`}
        <form method="post" action="/moderation/posts/${r.id}/resolve"><input type="hidden" name="_csrf" value="${csrf}"><button class="btn btn--small btn--ghost" type="submit">Dismiss reports</button></form></td></tr>`)}</tbody></table></div>` : html`<p>No open reports.</p>`}
      <h2>Recent posts</h2>
      ${recent.length ? html`<div class="table-wrap"><table class="mod-table"><thead><tr><th>Post</th><th>Posted</th><th>Actions</th></tr></thead><tbody>${recent.map((p) => html`<tr><td>${postCell(p)}</td><td>${timeTag(p.created_at)}</td><td>${p.removed_at ? html`<form method="post" action="/moderation/posts/${p.id}/restore"><input type="hidden" name="_csrf" value="${csrf}"><button class="btn btn--small btn--ghost" type="submit">Restore</button></form>` : html`<form method="post" action="/moderation/posts/${p.id}/remove"><input type="hidden" name="_csrf" value="${csrf}"><label class="visually-hidden" for="rr-${p.id}">Reason</label><input id="rr-${p.id}" type="text" name="reason" required maxlength="200" placeholder="Reason"><button class="btn btn--small btn--danger" type="submit">Remove</button></form>`}</td></tr>`)}</tbody></table></div>` : html`<p>No posts yet.</p>`}
      <h2>Removed posts</h2>
      ${removed.length ? html`<div class="table-wrap"><table class="mod-table"><thead><tr><th>Post (original text)</th><th>Reason</th><th>Actions</th></tr></thead><tbody>${removed.map((p) => html`<tr><td>${postCell(p)}</td><td>${p.removed_reason || ''}</td><td><form method="post" action="/moderation/posts/${p.id}/restore"><input type="hidden" name="_csrf" value="${csrf}"><button class="btn btn--small btn--ghost" type="submit">Restore</button></form></td></tr>`)}</tbody></table></div>` : html`<p>Nothing removed.</p>`}
      <h2>Members</h2>
      <div class="table-wrap"><table class="mod-table"><thead><tr><th>Username</th><th>Joined</th><th>Posts</th><th>Status</th><th>Actions</th></tr></thead><tbody>${users.map((u) => html`<tr><td>${u.username}${u.role === 'moderator' ? ' (moderator)' : ''}</td><td>${timeTag(u.created_at)}</td><td>${u.posts}</td><td>${u.status}</td><td>${u.role === 'moderator' ? '' : html`<form method="post" action="/moderation/users/${u.id}/${u.status === 'active' ? 'suspend' : 'unsuspend'}"><input type="hidden" name="_csrf" value="${csrf}"><button class="btn btn--small ${u.status === 'active' ? 'btn--danger' : 'btn--ghost'}" type="submit">${u.status === 'active' ? 'Suspend' : 'Reinstate'}</button></form>`}</td></tr>`)}</tbody></table></div>
    </div></div>`;
    return layout({ title: 'Moderation', path: '/moderation', body, user, csrf, solidHeader: true, noindex: true });
  }

  function errorPage({ status, title, message, user, csrf }) {
    const body = html`<div class="page"><div class="page__inner"><p class="kicker lattice-line">SIGNAL LOST · ${status}</p><h1>${title}</h1><p class="lede">${message}</p><p><a class="btn" href="/">Back to the start</a> <a class="btn btn--ghost" href="/discuss">Discussion</a></p></div></div>`;
    return layout({ title, path: '/', body, user, csrf, solidHeader: true, noindex: true });
  }

  return { layout, home, gallery, about, privacy, discussIndex, topicPage, authForm, account, editPost, moderation, errorPage, topicsBySlug };
}
