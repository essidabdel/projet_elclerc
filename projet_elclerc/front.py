"""front.py — interface web pour afficher les bons plans E.Leclerc.
Fichier minimal : route principale et API simple qui renvoie les deals depuis SQLite.
"""
import sqlite3
from flask import Flask, jsonify, render_template_string

DB_PATH = "leclerc_deals.db"
app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="fr" data-theme="light">
<head>
  <meta charset="utf-8">
  <title>Bons plans E.Leclerc — Cartes produits</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- Bootstrap CSS (grid/utilitaires) -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">

  <style>
    :root{
      --bg: #f6f8fb;
      --surface: #ffffff;
      --text: #0f172a;
      --muted: #5b6476;
      --primary: #3b82f6;
      --primary-2: #7c3aed;
      --ring: rgba(59,130,246,.25);
      --chip: #eef2ff;
      --success:#16a34a;
      --info:#06b6d4;
      --warn:#f59e0b;
      --radius: 16px;
      --shadow: 0 10px 30px rgba(2,6,23,.08);
      --shadow-strong: 0 20px 40px rgba(2,6,23,.10);
      --card-border: #e6e9ef;
      --skeleton: linear-gradient(90deg,#eceff5, #f6f8fb 25%, #eceff5 50%);
    }
    [data-theme="dark"]{
      --bg:#0f172a; --surface:#0b1220; --text:#e5e7eb; --muted:#9aa4b2;
      --primary:#60a5fa; --primary-2:#a78bfa; --ring: rgba(96,165,250,.3);
      --chip:#1f2937; --success:#22c55e; --info:#22d3ee; --warn:#fbbf24;
      --card-border:#1f2937; --skeleton: linear-gradient(90deg,#111827,#0f172a 25%,#111827 50%);
    }

    html,body{background:var(--bg); color:var(--text)}
    .navbar{background:linear-gradient(90deg, var(--primary), var(--primary-2)); color:#fff}
    .navbar .brand{font-weight:700; letter-spacing:.3px}
    .card{
      background:var(--surface); border:1px solid var(--card-border); border-radius:var(--radius);
      box-shadow:var(--shadow); transition:transform .2s ease, box-shadow .2s ease, border-color .2s;
    }
    .card:hover{ transform:translateY(-2px) scale(1.01); box-shadow:var(--shadow-strong); border-color:transparent; }
    .toolbar{position:sticky; top:0; z-index:10; padding:12px 16px; border-radius:var(--radius); background:var(--surface);
      border:1px solid var(--card-border); box-shadow:var(--shadow)}
    .chip{background:var(--chip); color:var(--text); padding:.35rem .6rem; border-radius:999px; font-size:.8rem; border:1px solid var(--card-border)}
    .btn-soft{
      background:var(--surface); color:var(--text); border:1px solid var(--card-border);
      border-radius:12px; padding:.55rem .9rem; transition:.2s; box-shadow:var(--shadow)
    }
    .btn-soft:hover{box-shadow:var(--shadow-strong); transform:translateY(-1px);}
    .btn-primary{
      background:linear-gradient(90deg, var(--primary), var(--primary-2)); border:none; color:#fff;
      border-radius:12px; padding:.55rem 1rem; box-shadow:var(--shadow)
    }
    .search{border:1px solid var(--card-border); background:var(--surface); color:var(--text); border-radius:12px; padding:.6rem .9rem}
    .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px}
    .imgbox{
      background:var(--bg); border-radius:12px; display:flex; align-items:center; justify-content:center;
      aspect-ratio: 4/3; overflow:hidden; border:1px solid var(--card-border)
    }
    .imgbox img{max-height:100%; max-width:100%; object-fit:contain; filter:saturate(110%); transition:transform .25s ease}
    .card:hover .imgbox img{transform:scale(1.03)}
    .badge{font-weight:600; border-radius:999px}
    .badge-success{background:rgba(22,163,74,.12); color:var(--success); border:1px solid rgba(22,163,74,.25)}
    .badge-info{background:rgba(6,182,212,.12); color:var(--info); border:1px solid rgba(6,182,212,.25)}
    .badge-muted{background:transparent; color:var(--muted); border:1px dashed var(--card-border)}
    .price{font-weight:800; font-size:1.15rem}
    details summary{cursor:pointer; color:var(--primary)}
    details{border-top:1px dashed var(--card-border); padding-top:.5rem; margin-top:.5rem}
    .muted{color:var(--muted)}
    .pill{padding:.15rem .5rem; border-radius:999px; border:1px solid var(--card-border); color:var(--muted); font-size:.72rem}
    .count{font-weight:700}
    /* Skeletons */
    .skeleton{ background:var(--skeleton); background-size:200% 100%; animation:shine 1.1s linear infinite; border-radius:12px }
    @keyframes shine{ to{ background-position-x:-200%; } }
    .skeleton.line{height:14px; margin:6px 0}
    .skeleton.thumb{height:180px}
    /* Modal quickview */
    .modal-backdrop{backdrop-filter: blur(3px);}
    .kbd{font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background:var(--chip); border:1px solid var(--card-border); padding:.1rem .35rem; border-radius:6px}
    .theme-toggle{border:1px solid var(--card-border)}
  </style>
</head>
<body>
<nav class="navbar py-3 mb-3">
  <div class="container d-flex align-items-center justify-content-between">
    <div class="brand">📦 Bons plans E.Leclerc</div>
    <div class="d-flex align-items-center gap-2">
      <button id="refresh" class="btn-soft">🔄 Recharger</button>
      <button id="themeBtn" class="btn-soft theme-toggle" title="Thème (T)">🌓 Thème</button>
    </div>
  </div>
</nav>

<div class="container">
  <div class="toolbar mb-4">
    <div class="row g-2 align-items-center">
      <div class="col-md-5">
        <input id="q" class="search w-100" placeholder="Rechercher (produit, description, caractéristiques)…  ⌕">
      </div>
      <div class="col-md-3">
        <input id="seller" class="search w-100" placeholder="Filtrer vendeur">
      </div>
      <div class="col-md-2">
        <select id="promo" class="search w-100">
          <option value="">Promo : toutes</option>
          <option value="percent">Seulement %</option>
          <option value="euro">Seulement €</option>
          <option value="none">Sans promo</option>
        </select>
      </div>
      <div class="col-md-2 d-flex justify-content-end">
        <span class="pill">Total: <span id="count" class="count">0</span></span>
      </div>
    </div>
  </div>

  <div id="grid" class="grid">
    <!-- skeletons -->
    {% for _ in range(8) %}
    <div class="card p-3">
      <div class="imgbox skeleton thumb"></div>
      <div class="skeleton line" style="width:80%"></div>
      <div class="skeleton line" style="width:50%"></div>
      <div class="skeleton line" style="width:60%"></div>
    </div>
    {% endfor %}
  </div>

  <div class="d-flex justify-content-center my-4">
    <button id="toTop" class="btn-primary" style="display:none">↑ Remonter en haut</button>
  </div>
</div>

<!-- Modal -->
<div class="modal fade" id="quickModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content" style="background:var(--surface); color:var(--text); border:1px solid var(--card-border)">
      <div class="modal-header">
        <h6 class="modal-title" id="modalTitle"></h6>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" style="filter: invert(var(--invert,0))"></button>
      </div>
      <div class="modal-body">
        <div class="row g-3">
          <div class="col-md-5">
            <div class="imgbox" style="aspect-ratio:1/1"><img id="modalImg" alt=""></div>
          </div>
          <div class="col-md-7">
            <div class="d-flex align-items-center justify-content-between mb-2">
              <div class="price" id="modalPrice"></div>
              <span class="chip" id="modalSeller"></span>
            </div>
            <div class="mb-2"><span class="badge" id="modalPromo"></span></div>
            <details open>
              <summary>Description</summary>
              <div id="modalDesc" class="mt-2"></div>
            </details>
            <details class="mt-2" id="modalFeatWrap" style="display:none">
              <summary>Caractéristiques</summary>
              <ul id="modalFeat" class="mt-2"></ul>
            </details>
          </div>
        </div>
      </div>
      <div class="modal-footer d-flex justify-content-between">
        <small class="muted">Astuce : appuie <span class="kbd">Espace</span> pour aperçu rapide</small>
        <a id="modalLink" class="btn-primary" target="_blank" rel="noopener">Voir le produit</a>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
let RAW = [];
let dtTheme = 'light';
const grid = document.getElementById('grid');
const countEl = document.getElementById('count');
const toTop = document.getElementById('toTop');
const quickModal = new bootstrap.Modal(document.getElementById('quickModal'));

function setTheme(t){
  document.documentElement.setAttribute('data-theme', t);
  dtTheme = t;
}
document.getElementById('themeBtn').onclick=()=> setTheme(dtTheme==='light'?'dark':'light');
document.addEventListener('keydown', e=>{
  if(e.key.toLowerCase()==='t') setTheme(dtTheme==='light'?'dark':'light');
});

function isPercent(txt){ return txt && /%/.test(txt); }
function isEuro(txt){ return txt && /€/.test(txt); }

function badgeForPromo(txt){
  if(!txt) return '<span class="badge badge-muted">—</span>';
  if(isPercent(txt)) return '<span class="badge badge-success">'+txt+'</span>';
  if(isEuro(txt)) return '<span class="badge badge-info">'+txt+'</span>';
  return '<span class="badge badge-muted">'+txt+'</span>';
}

function render(){
  const q = document.getElementById('q').value.trim().toLowerCase();
  const seller = document.getElementById('seller').value.trim().toLowerCase();
  const promo = document.getElementById('promo').value;

  grid.innerHTML = '';
  const items = RAW.filter(d=>{
    const matchQ = !q
      || (d.product_name||'').toLowerCase().includes(q)
      || (d.description||'').toLowerCase().includes(q)
      || (d.features||'').toLowerCase().includes(q);
    const matchSeller = !seller || (d.sold_by||'').toLowerCase().includes(seller);
    let matchPromo = true;
    if(promo==='percent') matchPromo = isPercent(d.discount_text);
    if(promo==='euro') matchPromo = isEuro(d.discount_text);
    if(promo==='none') matchPromo = !d.discount_text;
    return matchQ && matchSeller && matchPromo;
  });

  countEl.textContent = items.length;

  // Fade-in on scroll
  const obs = new IntersectionObserver((entries)=>{
    entries.forEach(ent=>{
      if(ent.isIntersecting){ ent.target.style.opacity=1; ent.target.style.transform='translateY(0)'; obs.unobserve(ent.target); }
    });
  }, {rootMargin:'80px'});

  items.forEach(d=>{
    const card = document.createElement('div');
    card.className = 'card p-3';
    card.style.opacity = 0;
    card.style.transform = 'translateY(8px)';
    const img = d.image_url ? `<img src="${d.image_url}" alt="img">` : '';
    const sellerChip = `<span class="chip">${d.sold_by || '—'}</span>`;
    const promoBadge = badgeForPromo(d.discount_text);
    const price = d.price_eur!=null ? (d.price_eur.toFixed(2)+' €') : '—';
    const features = d.features ? d.features.split('|').map(x=>x.trim()).filter(Boolean).map(x=>`<li>${x}</li>`).join('') : '';
    const link = d.page_url ? `<a class="btn-soft" href="${d.page_url}" target="_blank" rel="noopener">Voir le produit</a>` : '';

    card.innerHTML = `
      <div class="imgbox mb-2">${img}</div>
      <div class="d-flex justify-content-between align-items-start mb-1">
        <h6 class="m-0" title="${d.product_name||''}">${d.product_name||'Produit'}</h6>
        ${promoBadge}
      </div>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div class="price">${price}</div>
        ${sellerChip}
      </div>
      <details class="mb-1">
        <summary>Description</summary>
        <div class="mt-2">${d.description || '—'}</div>
      </details>
      ${features ? `<details class="mb-2"><summary>Caractéristiques</summary><ul class="mt-2">${features}</ul></details>` : ''}
      <div class="d-flex justify-content-between align-items-center">
        <small class="muted">${(d.scraped_at||'').replace('T',' ').slice(0,19)}</small>
        <div class="d-flex gap-2">
          ${link}
          <button class="btn-soft" data-quick>👁︎ Aperçu</button>
        </div>
      </div>
    `;
  // quick view
    card.querySelector('[data-quick]').onclick=()=> openQuick(d);
    grid.appendChild(card);
    obs.observe(card);
  });

  toTop.style.display = items.length>12 ? 'block':'none';
}

function openQuick(d){
  document.getElementById('modalTitle').textContent = d.product_name || 'Produit';
  document.getElementById('modalPrice').textContent = d.price_eur!=null ? (d.price_eur.toFixed(2)+' €') : '—';
  document.getElementById('modalSeller').textContent = d.sold_by || '—';
  document.getElementById('modalPromo').innerHTML = badgeForPromo(d.discount_text);
  document.getElementById('modalImg').src = d.image_url || '';
  document.getElementById('modalDesc').textContent = d.description || '—';
  const wrap = document.getElementById('modalFeatWrap');
  const ul = document.getElementById('modalFeat'); ul.innerHTML='';
  if(d.features){
    d.features.split('|').map(x=>x.trim()).filter(Boolean).forEach(x=>{
      const li = document.createElement('li'); li.textContent = x; ul.appendChild(li);
    });
    wrap.style.display='';
  }else wrap.style.display='none';
  const link = document.getElementById('modalLink');
  if(d.page_url){ link.href=d.page_url; link.style.display=''; } else { link.style.display='none'; }
  quickModal.show();
}
document.addEventListener('keydown', e=>{ if(e.code==='Space' && RAW[0]){ e.preventDefault(); openQuick(RAW[0]); } });

async function load(){
  const res = await fetch('/api/deals');
  RAW = await res.json();
  render();
}
document.getElementById('refresh').onclick=load;
document.getElementById('q').addEventListener('input', render);
document.getElementById('seller').addEventListener('input', render);
document.getElementById('promo').addEventListener('change', render);
toTop.onclick=()=> window.scrollTo({top:0, behavior:'smooth'});

load();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/deals")
def api_deals():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT sold_by, product_name, discount_text, price_eur,
               page_url, image_url, description, features, scraped_at
        FROM leclerc_deals
        ORDER BY COALESCE(price_eur, 999999) ASC
        LIMIT 2000;
    """).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
