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
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root{
      --bg:#f8fafc; --surface:#ffffff; --text:#0f172a; --muted:#64748b;
      --primary:#3b82f6; --primary-2:#7c3aed;
      --border:#d6dbe6; --border-strong:#b8c0cf;
      --chip:#eef2ff; --radius:14px; --radius-sm:10px;
      --shadow:0 6px 18px rgba(2,6,23,.06);
      --shadow-hover:0 10px 26px rgba(2,6,23,.10);
      --ring: 0 0 0 3px rgba(59,130,246,.20);
    }
    html,body{background:var(--bg); color:var(--text)}
    .navbar{
      background:linear-gradient(90deg, var(--primary), var(--primary-2)); color:#fff;
      border-bottom:1px solid rgba(255,255,255,.25)
    }
    .brand{font-weight:700; letter-spacing:.2px}

    .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:20px}

    /* Cartes avec vraies bordures */
    .card{
      background:var(--surface);
      border:1.5px solid var(--border);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }
    .card:hover{transform:translateY(-1px); box-shadow:var(--shadow-hover); border-color:var(--border-strong)}

    /* Encadré image + bordure visible */
    .imgbox{
      background:#f1f5ff;
      border:1.5px solid var(--border);
      border-radius:var(--radius-sm);
      aspect-ratio:4/3; display:flex; align-items:center; justify-content:center;
    }
    .imgbox img{max-height:100%; max-width:100%; object-fit:contain;}

    /* Badges */
    .badge-cat{
      border-radius:999px; border:1px solid var(--border);
      background:var(--chip); color:#1f2937; padding:.25rem .6rem; font-size:.75rem
    }
    .badge{border-radius:999px; padding:.22rem .55rem}
    .badge-success{background:#e8f7ee; color:#15803d; border:1px solid #b9e7c7}
    .badge-info{background:#e6f9fd; color:#03697a; border:1px solid #b9eef6}
    .badge-muted{background:#f1f5f9; color:#64748b; border:1px solid #dbe3ef}

    .price{font-weight:800}

    /* Inputs & selects — bordures nettes + états focus */
    .search{
      appearance:none;
      border:2px solid var(--border);
      background:var(--surface);
      color:var(--text);
      border-radius:12px;
      padding:.62rem .9rem;
      transition:border-color .15s ease, box-shadow .15s ease;
      box-shadow:none;
    }
    .search:focus{
      outline:none;
      border-color: var(--border-strong);
      box-shadow: var(--ring);
    }
    .search::placeholder{color:var(--muted); opacity:.85}

    /* Boutons sobres avec bordures */
    .btn-outline-primary{
      border:1.5px solid var(--border);
      color:var(--text);
      background:var(--surface);
      border-radius:10px;
    }
    .btn-outline-primary:hover{
      border-color: var(--border-strong);
      background:#f5f7fb;
      color:var(--text);
    }

    /* Petite bordure pour les input-group éventuels (si tu en ajoutes plus tard) */
    .input-group .form-control{border:2px solid var(--border); border-right:0}
    .input-group .btn{border:2px solid var(--border); border-left:0}

    /* Footer count align */
    #count{color:var(--muted)}
  </style>
</head>
<body>
<nav class="navbar py-3 mb-3">
  <div class="container d-flex align-items-center justify-content-between">
    <div class="brand">📦 Bons plans E.Leclerc</div>
  </div>
</nav>

<div class="container">
  <div class="row g-2 mb-3">
    <div class="col-md-4"><input id="q" class="search w-100" placeholder="Recherche (nom, texte)…"></div>
    <div class="col-md-3"><input id="seller" class="search w-100" placeholder="Vendeur"></div>
    <div class="col-md-3">
      <select id="promo" class="search w-100">
        <option value="">Promo : toutes</option>
        <option value="percent">Seulement %</option>
        <option value="euro">Seulement €</option>
        <option value="none">Sans promo</option>
      </select>
    </div>
    <div class="col-md-2">
      <select id="cat" class="search w-100">
        <option value="">Catégorie : toutes</option>
      </select>
    </div>
  </div>

  <div id="grid" class="grid"></div>
  <div class="d-flex justify-content-end mt-2"><small id="count"></small></div>
</div>

<script>
let RAW = [];

function isPercent(txt){ return txt && /%/.test(txt); }
function isEuro(txt){ return txt && /€/.test(txt); }

function formatPromo(txt){
  if(!txt) return txt;
  const s = String(txt).trim();
  // garder si déjà préfixé par un tiret (incl. variantes unicode)
  if(/^[\-\u2212\u2013]/.test(s)) return s;
  // si contient un chiffre, préfixer d'un '-'
  if(/\d/.test(s)) return '-' + s;
  return s;
}

function badgePromo(txt){
  const f = formatPromo(txt);
  if(!f) return '<span class="badge badge-muted">—</span>';
  if(isPercent(f)) return '<span class="badge badge-success">'+f+'</span>';
  if(isEuro(f)) return '<span class="badge badge-info">'+f+'</span>';
  return '<span class="badge badge-muted">'+f+'</span>';
}

function fillCategoryFilter(){
  const select = document.getElementById('cat');
  const uniq = Array.from(new Set(RAW.map(d => d.category || 'Autre'))).sort();
  uniq.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    select.appendChild(opt);
  });
}

function render(){
  const q = document.getElementById('q').value.trim().toLowerCase();
  const seller = document.getElementById('seller').value.trim().toLowerCase();
  const promo = document.getElementById('promo').value;
  const cat = document.getElementById('cat').value;

  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const items = RAW.filter(d=>{
    const t = (d.product_name||'') + ' ' + (d.description||'') + ' ' + (d.features||'');
    const matchQ = !q || t.toLowerCase().includes(q);
    const matchSeller = !seller || (d.sold_by||'').toLowerCase().includes(seller);
    let matchPromo = true;
    if(promo==='percent') matchPromo = isPercent(d.discount_text);
    if(promo==='euro') matchPromo = isEuro(d.discount_text);
    if(promo==='none') matchPromo = !d.discount_text;
    const matchCat = !cat || (d.category||'Autre')===cat;
    return matchQ && matchSeller && matchPromo && matchCat;
  });

  items.forEach(d=>{
    const img = d.image_url ? `<img src="${d.image_url}" alt="" />` : '';
    const feat = d.features ? d.features.split('|').map(x=>x.trim()).filter(Boolean).map(x=>`<li>${x}</li>`).join('') : '';
    const link = d.page_url ? `<a class="btn btn-sm btn-outline-primary" href="${d.page_url}" target="_blank" rel="noopener">Voir le produit</a>` : '';
    const price = d.price_eur!=null ? (d.price_eur.toFixed(2)+' €') : '—';

    const card = document.createElement('div');
    card.className = 'card p-3';
    card.innerHTML = `
      <div class="imgbox mb-2">${img}</div>
      <div class="d-flex justify-content-between align-items-start">
        <h6 class="m-0" title="${d.product_name||''}">${d.product_name||'Produit'}</h6>
        <span class="badge-cat">${d.category || 'Autre'}</span>
      </div>
      <div class="d-flex justify-content-between align-items-center mb-2">
        <div class="price">${price}</div>
        <span>${badgePromo(d.discount_text)}</span>
      </div>
      <details class="mb-1"><summary>Description</summary><div class="mt-2">${d.description || '—'}</div></details>
      ${feat ? `<details class="mb-2"><summary>Caractéristiques</summary><ul class="mt-2">${feat}</ul></details>` : ''}
      <div class="d-flex justify-content-between align-items-center">
        <small class="text-muted">${(d.scraped_at||'').replace('T',' ').slice(0,19)}</small>
        ${link}
      </div>
    `;
    grid.appendChild(card);
  });

  document.getElementById('count').textContent = `${items.length} produit(s)`;
}

async function load(){
  const res = await fetch('/api/deals');
  RAW = await res.json();
  fillCategoryFilter();
  render();
}

['q','seller','promo','cat'].forEach(id=>{
  document.addEventListener('input', e => { if(e.target.id===id) render(); });
  document.addEventListener('change', e => { if(e.target.id===id) render(); });
});

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
               page_url, image_url, description, features, scraped_at, category
        FROM leclerc_deals
        ORDER BY COALESCE(price_eur, 999999) ASC
        LIMIT 5000;
    """).fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
