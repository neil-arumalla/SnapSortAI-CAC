"""HTML for every page: plain HTML and CSS, no JavaScript, works on phones (light and dark mode)."""
from __future__ import annotations

import html
from datetime import date

import segno

import settings
import store
from finder import CATEGORIES, VALUABLES

CSS = """
:root{--bg:#f3f5fb;--surface:#fff;--ink:#0f172a;--muted:#5b6475;--line:#e4e8f1;--soft:#eef1f8;
--brand:#4f46e5;--brand2:#0ea5e9;--brand-ink:#3730a3;--warm:#f59e0b;--ok:#059669;--err:#dc2626;
--r:18px;--shadow:0 1px 2px rgba(15,23,42,.05),0 10px 30px -12px rgba(30,41,90,.18);
--grad:linear-gradient(135deg,var(--brand) 0%,#7c3aed 45%,var(--brand2) 100%)}
@media (prefers-color-scheme:dark){:root{--bg:#0b1020;--surface:#141a2e;--ink:#e8ecf7;--muted:#9aa4bd;--line:#252d48;
--soft:#1b2340;--brand-ink:#a5b4fc;--shadow:0 1px 2px rgba(0,0,0,.4),0 12px 32px -12px rgba(0,0,0,.6)}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:80px}
body{margin:0;font:16px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);
background:radial-gradient(1200px 500px at 10% -10%,rgba(79,70,229,.10),transparent 60%),
radial-gradient(900px 400px at 100% 0,rgba(14,165,233,.10),transparent 60%),var(--bg);min-height:100vh}
.wrap{max-width:1120px;margin:0 auto;padding:0 18px 40px}
a{color:var(--brand-ink);text-underline-offset:3px}code{word-break:break-all;font-size:.85em;background:var(--soft);padding:2px 6px;border-radius:6px}
h1{overflow-wrap:anywhere;font-size:clamp(1.6rem,4vw,2.4rem);line-height:1.15;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:1.15rem;margin:28px 0 12px;letter-spacing:-.01em;display:flex;align-items:center;gap:8px}
.muted{color:var(--muted)}.small{font-size:.86rem}
.top{position:sticky;top:0;z-index:10;backdrop-filter:saturate(1.6) blur(14px);-webkit-backdrop-filter:saturate(1.6) blur(14px);
background:color-mix(in srgb,var(--bg) 72%,transparent);border-bottom:1px solid var(--line)}
.top .in{max-width:1120px;margin:0 auto;padding:10px 18px;display:flex;align-items:center;gap:12px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:-.02em;color:var(--ink);text-decoration:none}
.mark{width:34px;height:34px;border-radius:11px;background:var(--grad);display:grid;place-items:center;font-size:18px;
box-shadow:0 6px 16px -6px rgba(79,70,229,.7)}
.top .sp{flex:1}.top .lang{font-size:.8rem;color:var(--muted);border:1px solid var(--line);padding:4px 10px;border-radius:999px}
.hero{position:relative;overflow:hidden;margin:22px 0 8px;padding:30px 28px;border-radius:26px;color:#fff;background:var(--grad);
box-shadow:0 24px 50px -24px rgba(79,70,229,.65)}
.hero::before,.hero::after{content:"";position:absolute;border-radius:50%;background:rgba(255,255,255,.12)}
.hero::before{width:320px;height:320px;right:-80px;top:-140px}.hero::after{width:180px;height:180px;right:120px;bottom:-110px}
.hero>*{position:relative}.hero h1{color:#fff}.hero p{margin:4px 0;color:rgba(255,255,255,.9)}.hero a{color:#fff}
.hero .eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.74rem;font-weight:700;opacity:.85}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.stat{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.25);border-radius:14px;padding:10px 16px;min-width:110px}
.stat b{display:block;font-size:1.6rem;line-height:1.1}.stat span{font-size:.8rem;opacity:.9}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;box-shadow:var(--shadow)}
.tile b{display:block;font-size:1.7rem;line-height:1.1;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.tile span{font-size:.82rem;color:var(--muted)}
.nav{position:sticky;top:58px;z-index:5;display:flex;gap:8px;overflow-x:auto;padding:10px 2px;margin:8px 0 0;scrollbar-width:none;
background:linear-gradient(var(--bg) 70%,transparent)}
.nav::-webkit-scrollbar{display:none}
.nav a{flex:none;padding:8px 14px;border:1px solid var(--line);border-radius:999px;background:var(--surface);text-decoration:none;
font-size:.88rem;color:var(--ink);box-shadow:var(--shadow);transition:transform .15s,border-color .15s}
.nav a:hover{transform:translateY(-1px);border-color:var(--brand)}.nav a b{color:var(--brand-ink);margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px}
.card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;
flex-direction:column;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s;animation:rise .45s both}
.card:hover{transform:translateY(-4px);box-shadow:0 2px 4px rgba(15,23,42,.06),0 22px 40px -16px rgba(79,70,229,.35)}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.ph{position:relative;aspect-ratio:1/1;background:linear-gradient(135deg,var(--soft),var(--surface));display:flex;align-items:center;
justify-content:center;text-align:center;color:var(--muted);font-size:.88rem}
.ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#fff}.ph .none{padding:16px}.ph .ico{display:block;font-size:2rem;margin-bottom:6px}
.num{position:absolute;top:10px;left:10px;z-index:1;font-weight:800;font-size:.95rem;padding:4px 10px;border-radius:999px;color:#fff;
background:var(--grad);box-shadow:0 6px 14px -6px rgba(79,70,229,.8)}
.new{position:absolute;top:10px;right:10px;z-index:1;font-size:.7rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
padding:4px 9px;border-radius:999px;background:var(--warm);color:#3b2300}
.body{padding:12px 14px 14px;font-size:.93rem;display:flex;flex-direction:column;gap:2px;flex:1}
.body .en{font-weight:600}.es{color:var(--muted);font-size:.86rem}.when{margin-top:auto;padding-top:8px;font-size:.78rem;color:var(--muted)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:18px 20px;margin:16px 0;box-shadow:var(--shadow)}
.panel h2{margin-top:0}
.schools{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:18px}
.schools a{display:flex;align-items:center;gap:14px;background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:18px;
text-decoration:none;color:var(--ink);box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}
.schools a:hover{transform:translateY(-4px);box-shadow:0 22px 40px -16px rgba(79,70,229,.35)}
.schools .count{flex:none;width:64px;height:64px;border-radius:18px;background:var(--grad);color:#fff;display:grid;place-items:center;
font-weight:800;font-size:1.4rem;line-height:1}.schools .count small{display:block;font-size:.6rem;font-weight:600;opacity:.9}
.schools .go{margin-left:auto;font-size:1.3rem;color:var(--brand-ink)}
.badge{display:inline-block;font-size:.72rem;font-weight:600;padding:3px 9px;border-radius:999px;background:var(--soft);color:var(--muted);margin:4px 4px 0 0}
.badge.warn{background:#fff3d6;color:#8a5300}
.btn{display:inline-flex;align-items:center;gap:6px;border:0;border-radius:12px;padding:11px 18px;font:600 1rem/1 inherit;color:#fff;cursor:pointer;
text-decoration:none;background:var(--grad);box-shadow:0 10px 20px -10px rgba(79,70,229,.8);transition:transform .15s,filter .15s}
.btn:hover{transform:translateY(-1px);filter:brightness(1.07)}.btn:active{transform:none}
.btn.secondary{background:var(--surface);color:var(--brand-ink);border:1px solid var(--line);box-shadow:none}
.btn.secondary:hover{border-color:var(--brand)}.btn.small{padding:7px 11px;font-size:.8rem;border-radius:10px}
:focus-visible{outline:3px solid var(--brand2);outline-offset:2px}
.row{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.row form{margin:0}
input[type=text]{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:12px;font-size:1rem;margin:6px 0 12px;
background:var(--surface);color:var(--ink)}
input[type=text]:focus{outline:none;border-color:var(--brand);box-shadow:0 0 0 4px rgba(79,70,229,.15)}
.drop{display:block;border:2px dashed color-mix(in srgb,var(--brand) 45%,var(--line));border-radius:16px;padding:22px;text-align:center;
background:color-mix(in srgb,var(--brand) 5%,var(--surface));margin:8px 0 12px;cursor:pointer}
.drop .ico{font-size:2.2rem;display:block}.drop strong{display:block;margin:4px 0}
input[type=file]{margin-top:10px;font-size:.95rem;max-width:100%;color:var(--muted)}
input[type=file]::file-selector-button{border:0;border-radius:10px;padding:9px 14px;margin-right:10px;font:600 .9rem inherit;color:#fff;
background:var(--grad);cursor:pointer}
.tips{list-style:none;padding:0;margin:0 0 14px;display:grid;gap:6px}.tips li::before{content:"✓";color:var(--ok);font-weight:800;margin-right:8px}
.notice,.ok,.error{border-radius:14px;padding:12px 14px;margin:14px 0;display:flex;gap:10px;align-items:flex-start}
.notice{background:color-mix(in srgb,var(--warm) 13%,var(--surface));border:1px solid color-mix(in srgb,var(--warm) 45%,transparent)}
.ok{background:color-mix(in srgb,var(--ok) 12%,var(--surface));border:1px solid color-mix(in srgb,var(--ok) 40%,transparent)}
.error{background:color-mix(in srgb,var(--err) 10%,var(--surface));border:1px solid color-mix(in srgb,var(--err) 40%,transparent);color:var(--err)}
.spin{flex:none;width:20px;height:20px;border-radius:50%;border:3px solid color-mix(in srgb,var(--warm) 30%,transparent);
border-top-color:var(--warm);animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.overview{width:100%;border-radius:14px;border:1px solid var(--line);margin:8px 0}
.qr{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}.qr .panel{text-align:center}
.qr svg{width:220px;height:auto;padding:12px;background:#fff;border-radius:16px}
table{width:100%;border-collapse:collapse}td{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:last-child td{border-bottom:0}
.foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 18px;font-size:.8rem;color:var(--muted)}
@media (max-width:560px){.hero{padding:24px 20px;border-radius:22px}.grid{grid-template-columns:repeat(2,1fr);gap:12px}.top .lang{display:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
"""

ICONS = {"bottle": "🥤", "lunchbox": "🍱", "bag": "🎒", "clothing": "🧥", "hat": "🧢", "gloves_scarf": "🧣", "shoes": "👟",
         "eyewear": "🕶️", "keys": "🔑", "jewelry_watch": "⌚", "electronics": "📱", "wallet_id": "👛",
         "school_supplies": "📚", "sports": "⚽", "other": "📦"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def layout(title: str, body: str, refresh: int | None = None) -> str:
    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    top = ('<header class="top"><div class="in"><a class="logo" href="/"><span class="mark">🔎</span>SnapSortAI</a>'
           '<span class="sp"></span><span class="lang">English · Español</span></div></header>')
    foot = ('<footer class="foot"><span>🔒 Names on items are blurred</span><span>💎 Valuables are never pictured</span>'
            '<span>🏫 Only cropped items are public, never the whole photo</span></footer>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="theme-color" content="#4f46e5">'
            f'<meta name="robots" content="noindex">{meta}<title>{esc(title)}</title>'
            f'<style>{CSS}</style></head><body>{top}<main class="wrap">{body}{foot}</main></body></html>')


def hero(eyebrow: str, title: str, lines: list[str], stats: list[tuple] = ()) -> str:
    """The gradient banner at the top of a page. `lines` and stat labels are trusted HTML."""
    tiles = "".join(f'<div class="stat"><b>{value}</b><span>{label}</span></div>' for value, label in stats)
    return (f'<section class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1>'
            + "".join(f"<p>{line}</p>" for line in lines)
            + (f'<div class="stats">{tiles}</div>' if stats else "") + "</section>")


NEW_DAYS = 3  # items found this recently get a "New" badge


def is_new(item: dict) -> bool:
    return (date.today() - date.fromisoformat(item["found"][:10])).days < NEW_DAYS


def short_date(iso: str) -> tuple[str, str]:
    d = date.fromisoformat(iso[:10])
    en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.month - 1]
    es = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][d.month - 1]
    return f"{en} {d.day}", f"{d.day} {es}"


def qr_svg(url: str) -> str:
    return segno.make(url, error="m").svg_inline(scale=6, border=2)


def message_page(title: str, text: str) -> str:
    return layout(title, hero("SnapSortAI", esc(title), [])
                  + f'<p class="panel">{esc(text)}</p><p><a class="btn secondary" href="/">&larr; Back to the start</a></p>')


# ---------------------------------------------------------------------------
# Public pages (families and students)
# ---------------------------------------------------------------------------
def home_page() -> str:
    counts = {s: len(store.public_items(s)) for s in settings.SCHOOLS}
    links = "".join(
        f'<a href="/{s}"><span class="count">{counts[s]}<small>items</small></span>'
        f'<span><strong>{esc(n)}</strong><br><span class="muted small">{counts[s]} items / artículos</span></span>'
        f'<span class="go">&rarr;</span></a>'
        for s, n in settings.SCHOOLS.items())
    top = hero("Objetos perdidos", "Lost something at school? Let&rsquo;s find it.",
               ["Browse photos of everything in your school&rsquo;s lost &amp; found, from home.",
                "Mira desde casa todo lo que hay en objetos perdidos de tu escuela."],
               [(sum(counts.values()), "items waiting / artículos"), (len(counts), "schools / escuelas")])
    return layout("SnapSortAI", top + '<h2>🏫 Choose your school / Elige tu escuela</h2>'
                                        f'<div class="schools">{links}</div>')


def catalog_page(school: str) -> str:
    name = settings.SCHOOLS[school]
    items = store.public_items(school)
    nav, sections = [], []
    for cat, (en, es) in CATEGORIES.items():
        group = [i for i in items if i["category"] == cat]
        if not group:
            continue
        nav.append(f'<a href="#{cat}">{ICONS[cat]} {en}<b>{len(group)}</b></a>')
        cards = []
        for i in group:
            if store.public_photo_ok(i):
                ph = f'<img src="/{school}/img/{i["no"]}.jpg" alt="{esc(i["en"])}" loading="lazy">'
            else:
                ph = f'<span class="none"><span class="ico">{ICONS[cat]}</span>Ask at the front office<br>Pregunta en la oficina</span>'
            new = '<div class="new">New · Nuevo</div>' if is_new(i) else ""
            en_date, es_date = short_date(i["found"])
            es_line = f'<div class="es">{esc(i["es"])}</div>' if i.get("es") else ""
            pile = (f'<div class="small muted">About {i["count"]} items / Aprox. {i["count"]}</div>'
                    if i.get("pile") and i.get("count", 1) > 1 else "")
            cards.append(f'<div class="card"><div class="ph"><div class="num">#{i["no"]}</div>{new}{ph}</div><div class="body">'
                         f'<div class="en">{esc(i["en"])}</div>{es_line}{pile}'
                         f'<div class="when">📅 Found {en_date} · Encontrado el {es_date}</div></div></div>')
        sections.append(f'<h2 id="{cat}">{ICONS[cat]} {en} <span class="muted small">/ {es}</span></h2>'
                        f'<div class="grid">{"".join(cards)}</div>')
    fresh = sum(1 for i in items if is_new(i))
    top = hero('<a href="/">&larr; All schools / Todas las escuelas</a>', esc(name),
               ["Recognize something? Tell the front office the item number.",
                "¿Reconoces algo? Dile el número a la oficina principal."],
               [(len(items), "items / artículos"), (len(nav), "categories / categorías"), (fresh, f"new in {NEW_DAYS} days / nuevos")])
    body = (top + f'<nav class="nav">{"".join(nav)}</nav>'
            + ("".join(sections) if items else
               '<div class="panel" style="text-align:center"><div style="font-size:2.5rem">🎉</div>'
               'No items right now. / No hay artículos por ahora.</div>')
            + f'<div class="panel">Items not claimed within {settings.DAYS_LISTED} days are donated. / '
              f'Los artículos que no se reclamen en {settings.DAYS_LISTED} días se donan.</div>')
    return layout(f"SnapSortAI · {name}", body)


def qr_page(base: str) -> str:
    blocks = "".join(
        f'<div class="panel"><h2 style="justify-content:center">🏫 {esc(n)}</h2>{qr_svg(f"{base}/{s}")}'
        f'<p class="small muted"><code>{esc(base)}/{esc(s)}</code></p></div>'
        for s, n in settings.SCHOOLS.items())
    return layout("SnapSortAI QR codes",
                  hero("📱 Point your phone camera here", "Scan to see lost &amp; found items",
                       ["Escanea para ver los objetos perdidos"])
                  + f'<div class="qr">{blocks}</div>')


# ---------------------------------------------------------------------------
# Staff page (the school's secret upload link)
# ---------------------------------------------------------------------------
def _item_card(school: str, key: str, i: dict) -> str:
    valuable = i["category"] in VALUABLES
    ph = (f'<img src="/upload/{key}/img/{i["no"]}.jpg" alt="Item {i["no"]}" loading="lazy">'
          if i.get("has_crop") else f'<span class="none"><span class="ico">{ICONS.get(i["category"], "📦")}</span>No picture</span>')
    badges = []
    if valuable:
        badges.append('<span class="badge warn">Valuable: no picture on the public page</span>')
    elif i.get("why_hidden") == "name label":
        badges.append('<span class="badge warn">Picture hidden: a name may show</span>')
    elif i.get("why_hidden") == "hidden by staff":
        badges.append('<span class="badge">Picture hidden by you</span>')
    if i.get("names_blurred"):
        badges.append('<span class="badge">Name blurred</span>')
    if i.get("why_hidden") == "added by hand":
        badges.append('<span class="badge">Added by hand</span>')
    if i.get("pile") and i.get("count", 1) > 1:
        badges.append(f'<span class="badge">About {i["count"]} items</span>')

    def button(action: str, label: str, primary: bool = False) -> str:
        cls = "btn small" if primary else "btn small secondary"
        return (f'<form method="post" action="/upload/{key}/item/{i["no"]}/{action}">'
                f'<button class="{cls}" type="submit">{label}</button></form>')

    buttons = [button("picked-up", "✓ Picked up", primary=True)]
    if i.get("has_crop") and not valuable:
        buttons.append(button("hide-photo", "Hide picture") if i.get("show_photo") else button("show-photo", "Show picture"))
    buttons.append(button("remove", "Remove"))
    return (f'<div class="card" id="i{i["no"]}"><div class="ph"><div class="num">#{i["no"]}</div>{ph}</div><div class="body">'
            f'<div class="en">{esc(i["en"])}</div><div>{"".join(badges)}</div>'
            f'<div class="row">{"".join(buttons)}</div></div></div>')


def staff_page(school: str, key: str, message: str = "", error: str = "") -> str:
    name = settings.SCHOOLS[school]
    data = store.load(school)
    uploads = sorted(data["uploads"].values(), key=lambda u: u.get("ts", 0), reverse=True)
    processing = [u for u in uploads if u["status"] == "processing"]
    latest = next((u for u in uploads if u["status"] in ("done", "failed")), None)
    listed = sorted((i for i in data["items"] if i["status"] == "listed" and not store.expired(i)), key=lambda i: -i["no"])
    to_donate = [i for i in data["items"] if i["status"] == "listed" and store.expired(i)]
    history = sorted((i for i in data["items"] if i["status"] in ("picked_up", "removed")),
                     key=lambda i: i.get("status_at", ""), reverse=True)[:15]

    week_ago = (date.today().toordinal() - 7)
    claimed = sum(1 for i in data["items"] if i["status"] == "picked_up"
                  and date.fromisoformat(i.get("status_at", "1970-01-01")[:10]).toordinal() >= week_ago)
    parts = [hero("🔐 Front office", f'{esc(name)}: staff page',
                  ["Snap a photo of the lost &amp; found shelf. AI finds every item, blurs names and posts it for families."]),
             '<div class="tiles">'
             f'<div class="tile"><b>{len(listed)}</b><span>on the public page</span></div>'
             f'<div class="tile"><b>{claimed}</b><span>picked up this week</span></div>'
             f'<div class="tile"><b>{len(to_donate)}</b><span>ready to donate</span></div></div>',
             '<p class="notice"><span>🔒</span><span><strong>Keep this link private.</strong> Anyone who has it can upload '
             'for your school. Bookmark it; don&rsquo;t forward or post it.</span></p>']
    if error:
        parts.append(f'<p class="error"><span>⚠️</span><span>{esc(error)}</span></p>')
    elif message:
        parts.append(f'<p class="ok"><span>✅</span><span>{esc(message)}</span></p>')
    if processing:
        parts.append('<p class="notice"><span class="spin"></span><span><strong>Finding items&hellip;</strong> '
                     'about a minute per photo. This page refreshes by itself.</span></p>')

    parts.append(
        f'<form class="panel" method="post" action="/upload/{key}" enctype="multipart/form-data">'
        f'<h2>📸 Upload lost &amp; found photos</h2>'
        f'<label class="drop"><span class="ico">🖼️</span><strong>Take a photo or choose from your library</strong>'
        f'<span class="small muted">Up to {settings.MAX_PHOTOS_PER_UPLOAD} photos at a time</span><br>'
        f'<input type="file" name="photos" accept="image/*" multiple required></label>'
        f'<ul class="tips small muted"><li>One shelf or table per photo, in good light.</li>'
        f'<li>Spread out piles so each item shows.</li><li>Keep students and faces out of the picture.</li></ul>'
        f'<button class="btn" type="submit">✨ Upload and find items</button></form>')

    if latest:
        if latest["status"] == "failed":
            parts.append(f'<div class="panel"><h2>Last upload</h2><p class="error">{esc(latest["message"])}</p></div>')
        else:
            pics = "".join(f'<img class="overview" src="/upload/{key}/overview/{esc(o)}" alt="Your photo with numbered boxes">'
                           for o in latest["overviews"])
            note = f'<p class="small muted">{esc(latest["message"])}</p>' if latest.get("message") else ""
            parts.append(f'<div class="panel"><h2>Last upload: {len(latest["items"])} items found</h2>{pics}'
                         f'<p><strong>Anything without a box was missed.</strong> Add it below.</p>{note}</div>')

    parts.append(
        f'<form class="panel" method="post" action="/upload/{key}/add"><h2>✍️ Add an item the AI missed</h2>'
        f'<input type="text" name="description" maxlength="160" placeholder="Pile of about 12 keys" required>'
        f'<button class="btn secondary" type="submit">+ Add</button>'
        f'<p class="small muted">It&rsquo;s listed without a picture.</p></form>')

    parts.append(f'<h2>🗂️ On the public page now ({len(listed)})</h2>')
    parts.append(f'<div class="grid">{"".join(_item_card(school, key, i) for i in listed)}</div>' if listed
                 else '<p class="panel">Nothing listed yet. Upload a photo above.</p>')

    if to_donate:
        rows = "".join(
            f'<tr><td>#{i["no"]}</td><td>{esc(i["en"])}</td><td><form method="post" action="/upload/{key}/item/{i["no"]}/remove">'
            f'<button class="btn small secondary" type="submit">Donated</button></form></td></tr>' for i in to_donate)
        parts.append(f'<h2>💝 Over {settings.DAYS_LISTED} days: ready to donate</h2>'
                     f'<div class="panel"><table>{rows}</table></div>')
    if history:
        rows = "".join(
            f'<tr><td>#{i["no"]}</td><td>{esc(i["en"])}</td>'
            f'<td>{"Picked up" if i["status"] == "picked_up" else "Removed"}</td>'
            f'<td><form method="post" action="/upload/{key}/item/{i["no"]}/undo">'
            f'<button class="btn small secondary" type="submit">Undo</button></form></td></tr>' for i in history)
        parts.append(f'<h2>🕘 Recently picked up or removed</h2><div class="panel"><table>{rows}</table></div>')
    parts.append(f'<p><a class="btn secondary" href="/{school}">👀 See the public page</a></p>')
    return layout(f"Staff · {name}", "".join(parts), refresh=4 if processing else None)


# ---------------------------------------------------------------------------
# Owner page (you)
# ---------------------------------------------------------------------------
def owner_page(token: str, base: str, message: str = "") -> str:
    tokens = store.links()["schools"]
    rows = []
    for s, n in settings.SCHOOLS.items():
        public = f"{base}/{s}"
        upload = f"{base}/upload/{s}-{tokens[s]}"
        rows.append(
            f'<div class="panel"><h2>🏫 {esc(n)}</h2>'
            f'<p><strong>Public page</strong> ({len(store.public_items(s))} items)<br>'
            f'<a href="{esc(public)}"><code>{esc(public)}</code></a></p>'
            f'<p><strong>Staff upload link</strong>: send only to this school&rsquo;s front office<br>'
            f'<a href="{esc(upload)}"><code>{esc(upload)}</code></a></p>'
            f'<div class="row"><form method="post" action="/owner/{token}/rotate/{s}">'
            f'<button class="btn small secondary" type="submit">Make a new upload link (old one stops working)</button></form></div>'
            f'<form class="row" method="post" action="/owner/{token}/reset/{s}">'
            f'<label class="small"><input type="checkbox" name="confirm" value="yes" required> Delete all of this school&rsquo;s items</label>'
            f'<button class="btn small secondary" type="submit">Reset for a new demo</button></form></div>')
    body = ([hero("👑 Owner", "SnapSortAI: owner page", ["Every school&rsquo;s links in one place."]),
             '<p class="notice"><span>🙈</span><span><strong>Don&rsquo;t show this page on a projector.</strong> It has every '
             f'school&rsquo;s secret upload link. To show QR codes on screen, open <a href="/qr">the QR page</a> instead.</span></p>']
            + ([f'<p class="ok"><span>✅</span><span>{esc(message)}</span></p>'] if message else [])
            + rows
            + ['<p class="small muted">These addresses change every time you restart the demo, '
               'so send fresh links after each restart.</p>'])
    return layout("Owner · SnapSortAI", "".join(body))
