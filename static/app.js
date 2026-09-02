/* ManoBotPurple — Frontend JS */

const $ = (s) => document.querySelector(s);
const fmt = (n) => Number(n).toLocaleString('fr-FR');

// Conversion minutes -> affichage jours/heures/minutes
function duree(min) {
  min = Math.round(min);
  if (min < 60) return `${fmt(min)} min`;
  const h = Math.floor(min / 60);
  if (h < 24) {
    const m = min % 60;
    return m ? `${h} h ${fmt(m).replace('\u202f', ' ')}` : `${h} h`;
  }
  const j = Math.floor(h / 24), hRest = h % 24;
  return hRest ? `${j} j ${hRest} h` : `${j} j`;
}

// Tarif Magicarium courant (sélecteur de la page Calculateur)
function tarifCourant() {
  const sel = $('#calcul-tarif');
  return sel ? sel.value : '1691';
}

// Prix Magicarium disponibles (recettes)
const TARIFS_MAGICARIUM = [
  { id: 'defaut', nom: 'Marchand 1691', prix: 1691 },
  { id: 'gilga', nom: 'Gilga', prix: 600 },
  { id: 'soi', nom: 'Forgeron', prix: 280 },
];

// Options cochées dans le panneau Recettes du module donné ('baguettes' | 'balais')
function optionsRecettes(module) {
  const box = $(`#tarif-options-${module === 'baguettes' ? 'b' : 'bl'}`);
  if (!box) return { magicarium: true, tarifs: [TARIFS_MAGICARIUM[0]] };
  const coches = [...box.querySelectorAll('input:checked')].map(i => i.value);
  const tarifs = TARIFS_MAGICARIUM.filter(t => coches.includes(t.id));
  return { magicarium: coches.includes('magicarium'), tarifs: tarifs.length ? tarifs : [] };
}

// ===== Navigation par pages =====
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.hidden = true);
  const page = $(`#page-${name}`);
  if (page) page.hidden = false;
  document.querySelectorAll('.nav-links a').forEach(a =>
    a.classList.toggle('active', a.dataset.page === name));
  if (name === 'infos') {
    loadSession();
    loadFiches();
  }
  window.scrollTo(0, 0);
}

document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', (e) => {
    const target = a.getAttribute('href');
    if (target.startsWith('/#')) {
      e.preventDefault();
      const name = target.slice(2);
      showPage(name);
      history.replaceState(null, '', target);
    }
  });
});

function pageFromHash() {
  const h = location.hash.replace('#', '');
  return ['baguettes', 'balais', 'infos', 'tutoriel', 'calcul'].includes(h) ? h : 'accueil';
}
showPage(pageFromHash());
window.addEventListener('hashchange', () => showPage(pageFromHash()));

// ===== Onglets mini (Prix / Recettes) =====
document.querySelectorAll('.tabs-mini').forEach(tabs => {
  tabs.querySelectorAll('.mini-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.querySelectorAll('.mini-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const section = tabs.parentElement;
      section.querySelectorAll('.mini-pane').forEach(p => p.hidden = true);
      section.querySelector(`#tab-${btn.dataset.tab}`).hidden = false;
    });
  });
});

// ===== Helpers d'affichage =====
function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s ?? '';
  return d.innerHTML;
}

function prixCard(nom, info) {
  const pnj = info.pnj ?? '?', client = info.client ?? '?', coutant = info.coutant ?? info.stats ?? '?';
  return `<div class="item-card">
    <h3>${escapeHtml(nom)}</h3>
    <div class="details">💰 Coûtant : <b>${escapeHtml(coutant)}</b></div>
    <div class="details">🧑 Client : <b>${escapeHtml(client)}</b></div>
    <div class="details">🏪 PNJ : <b>${escapeHtml(pnj)}</b></div>
    ${info.date ? `<div class="meta">📅 ${escapeHtml(info.date)}</div>` : ''}
  </div>`;
}

function syntheseRecette(a, opts) {
  const lignes = [];
  lignes.push(`📦 Kits de base : <b>${fmt(a.kits_base)}</b> · ☀️ Cristaux : <b>${fmt(a.cristaux_extra)}</b>`);
  lignes.push(`💰 Montant total des kits : <b>${fmt(a.cout_kits)} G</b>`);
  if (opts.magicarium) {
    lignes.push(`🔮 Magicarium : <b>${fmt(a.magicarium)}</b>`);
  }
  for (const t of opts.tarifs) {
    lignes.push(`<span class="tarif-line"><span class="tarif-nom">💰 ${t.nom}</span><b style="color:var(--gold)">${fmt(a.cout_kits + a.magicarium * t.prix)} G</b></span>`);
  }
  const tarif = opts.tarifs.length === 1 ? opts.tarifs[0] : TARIFS_MAGICARIUM[0];
  lignes.push(`💰 <b style="color:var(--gold)">TOTAL (${tarif.nom}) : ${fmt(a.cout_kits + a.magicarium * tarif.prix)} G</b>`);
  lignes.push(`⏱️ Récolte : <b>${duree(a.temps_recolte_minutes)}</b>`);
  return `<div class="synthese">${lignes.join('<br>')}</div>`;
}

function recetteCard(nom, r, opts) {
    let synthese = '';
    if (r.analyse && (r.analyse.kits_base > 0 || r.analyse.cristaux_extra > 0 || r.analyse.magicarium > 0)) {
      synthese = syntheseRecette(r.analyse, opts);
    }
  return `<div class="item-card">
    <h3>${escapeHtml(nom)}</h3>
    ${r.ingredients ? `<div class="details" style="white-space:pre-line">${escapeHtml(r.ingredients)}</div>` : ''}
    ${r.details ? `<div class="meta">${escapeHtml(r.details)}</div>` : ''}
    ${synthese}
  </div>`;
}

function vide(msg = 'Aucun résultat') {
  return `<div class="empty">${msg}</div>`;
}

// ===== Chargement des données =====
async function loadPrix(module, q = '') {
  const data = await fetch(`/api/prix/${module}?q=${encodeURIComponent(q)}`).then(r => r.json());
  const vente = Object.entries(data.vente || {}).map(([n, i]) => prixCard(n, i)).join('') || vide();
  const repa = Object.entries(data.reparation || {}).map(([n, i]) => prixCard(n, i)).join('') || vide();
  if (module === 'baguettes') {
    $('#vente-baguettes').innerHTML = vente;
    $('#repa-baguettes').innerHTML = repa;
  } else {
    $('#vente-balais').innerHTML = vente;
    $('#repa-balais').innerHTML = repa;
  }
}

async function loadRecettes(module, q = '') {
  const data = await fetch(`/api/recettes/${module}?q=${encodeURIComponent(q)}`).then(r => r.json());
  const opts = optionsRecettes(module);
  const html = Object.entries(data).map(([n, r]) => recetteCard(n, r, opts)).join('') || vide();
  if (module === 'baguettes') $('#recettes-baguettes').innerHTML = html;
  else $('#recettes-balais').innerHTML = html;
}



// ===== Debounced search =====
let timers = {};
function debounce(key, fn, delay = 250) {
  clearTimeout(timers[key]);
  timers[key] = setTimeout(fn, delay);
}

$('#search-baguettes').addEventListener('input', (e) => debounce('b', () => {
  loadPrix('baguettes', e.target.value);
  loadRecettes('baguettes', e.target.value);
}));
$('#search-balais').addEventListener('input', (e) => debounce('bl', () => {
  loadPrix('balais', e.target.value);
  loadRecettes('balais', e.target.value);
}));

// ===== Calculateur =====
$('#calcul-btn').addEventListener('click', async () => {
  const texte = $('#calcul-input').value;
  const res = await fetch('/api/calcul', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texte, tarif: tarifCourant() }),
  }).then(r => r.json());

  $('#calcul-result').innerHTML = res.kits_base === 0 && res.cristaux_extra === 0 && res.magicarium === 0
    ? vide('Aucun composant reconnu. Utilisez le format "• 4x Kits d\'Excellence".')
    : `<div class="item-card">
        <h3>🧮 Résultat du calcul</h3>
        <div class="synthese" style="font-size:1em">
          📦 Kits de base : <b>${fmt(res.kits_base)}</b><br>
          ☀️ Cristaux Solaires (hors kit) : <b>${fmt(res.cristaux_extra)}</b><br>
          🔮 Magicarium : <b>${fmt(res.magicarium)}</b> × ${fmt(res.tarif_magicarium ?? 1691)}<br><br>
          💰 Coût kits : <b>${fmt(res.cout_kits)} Galyons</b><br>
          💰 Coût Magicarium : <b>${fmt(res.cout_magicarium)} Galyons</b><br>
          💰 <b style="color:var(--gold)">TOTAL : ${fmt(res.cout_total)} Galyons</b><br><br>
          ⏱️ Temps de récolte estimé : <b>${duree(res.temps_recolte_minutes)}</b>
        </div>
      </div>`;
});

// ===== Init =====
document.querySelectorAll('.tarif-options').forEach(box => {
  const maj = () => box.querySelectorAll('label').forEach(l =>
    l.classList.toggle('on', l.querySelector('input').checked));
  maj();
  box.addEventListener('change', () => {
    maj();
    const mod = box.id === 'tarif-options-b' ? 'baguettes' : 'balais';
    loadRecettes(mod, $(`#search-${mod}`).value);
  });
});

loadPrix('baguettes');
loadRecettes('baguettes');
loadPrix('balais');
loadRecettes('balais');

// ===== Page Infos : fiches + filtres + admin =====
let FICHES = [];
let isAdmin = false;
let fichesLoaded = false;

async function loadSession() {
  try {
    const s = await fetch('/api/session').then(r => r.json());
    setAdmin(!!s.admin);
  } catch (e) {
    setAdmin(false);
  }
}

function setAdmin(val) {
  isAdmin = !!val;
  const loginBtn = $('#admin-login-btn');
  const logoutBtn = $('#admin-logout-btn');
  const status = $('#admin-status');
  const loginBox = $('#admin-login-box');
  const floatingPanel = $('#admin-floating-panel');
  const floatingEditor = $('#admin-floating-editor');
  const floatingLogin = $('#admin-floating-login');

  if (loginBtn) loginBtn.hidden = isAdmin;
  if (logoutBtn) logoutBtn.hidden = !isAdmin;
  if (status) status.textContent = isAdmin ? '🟢 Connecté en tant qu\'administrateur' : '';
  if (loginBox) loginBox.hidden = true;
  if (floatingPanel) floatingPanel.hidden = !isAdmin && !floatingPanel.dataset.open;
  if (floatingLogin) floatingLogin.hidden = isAdmin;
  if (floatingEditor) floatingEditor.hidden = !isAdmin;
  if (fichesLoaded) renderFiches();
  if (isAdmin) populateAdminEditor();
}

async function populateAdminEditor() {
  const moduleSelect = $('#admin-module-select');
  const kindSelect = $('#admin-kind-select');
  const itemSelect = $('#admin-item-select');
  const form = $('#admin-edit-form');
  if (!moduleSelect || !kindSelect || !itemSelect || !form) return;

  const module = moduleSelect.value;
  const kind = kindSelect.value;

  let items = {};
  if (kind === 'prix') {
    const data = await fetch(`/api/prix/${module}`).then(r => r.json());
    const vente = data.vente || {};
    const rep = data.reparation || {};
    items = { ...vente, ...rep };
  } else {
    const data = await fetch(`/api/recettes/${module}`).then(r => r.json());
    items = data || {};
  }

  const names = Object.keys(items);
  const current = itemSelect.value || names[0] || '';
  itemSelect.innerHTML = names.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
  itemSelect.value = names.includes(current) ? current : (names[0] || '');

  if (!names.length) {
    form.innerHTML = '<div class="empty">Aucune donnée à modifier dans ce module.</div>';
    return;
  }

  if (kind === 'prix') {
    const entry = (await fetch(`/api/prix/${module}`).then(r => r.json()));
    const vente = entry.vente || {};
    const rep = entry.reparation || {};
    const selected = vente[itemSelect.value] || rep[itemSelect.value] || {};
    const category = Object.prototype.hasOwnProperty.call(vente, itemSelect.value) ? 'vente' : 'repa';
    form.innerHTML = `
      <label>Catégorie
        <select id="admin-price-category">
          <option value="vente" ${category === 'vente' ? 'selected' : ''}>Vente</option>
          <option value="repa" ${category === 'repa' ? 'selected' : ''}>Réparation</option>
        </select>
      </label>
      <label>Coûtant
        <input id="admin-price-coutant" type="text" value="${escapeHtml(selected.coutant || '')}">
      </label>
      <label>Client
        <input id="admin-price-client" type="text" value="${escapeHtml(selected.client || '')}">
      </label>
      <label>PNJ
        <input id="admin-price-pnj" type="text" value="${escapeHtml(selected.pnj || '')}">
      </label>
    `;
    return;
  }

  const recipe = (await fetch(`/api/recettes/${module}`).then(r => r.json()))[itemSelect.value] || {};
  form.innerHTML = `
    <label>Ingrédients
      <textarea id="admin-recipe-ingredients">${escapeHtml(recipe.ingredients || '')}</textarea>
    </label>
    <label>Détails
      <textarea id="admin-recipe-details">${escapeHtml(recipe.details || '')}</textarea>
    </label>
    <label>Date
      <input id="admin-recipe-date" type="text" value="${escapeHtml(recipe.date || '')}">
    </label>
  `;
}

async function loadFiches(force = false) {
  if (fichesLoaded && !force) return;
  const data = await fetch('/api/fiches').then(r => r.json());
  FICHES = [
    ...Object.entries(data.baguettes || {}).map(([nom, i]) => ({ nom, ...i })),
    ...Object.entries(data.balais || {}).map(([nom, i]) => ({ nom, ...i })),
  ];
  fichesLoaded = true;
  renderFiches();
}

function filtresFiches() {
  const num = (id) => { const v = $(id).value; return v === '' ? null : Number(v); };
  return {
    q: $('#fiche-search').value.trim().toLowerCase(),
    type: $('#filtre-type').value,
    duree: $('#filtre-duree').value,
    coutMin: num('#filtre-coutant-min'), coutMax: num('#filtre-coutant-max'),
    venteMin: num('#filtre-vente-min'), venteMax: num('#filtre-vente-max'),
    recMin: num('#filtre-recup-min'), recMax: num('#filtre-recup-max'),
  };
}

function renderFiches() {
  const f = filtresFiches();
  const items = FICHES.filter(it => {
    if (f.q && !it.nom.toLowerCase().includes(f.q)) return false;
    if (f.type && it.type !== f.type) return false;
    if (f.duree && (it.duree || '') !== f.duree) return false;
    if (f.coutMin !== null && !(it.prix_coutant >= f.coutMin)) return false;
    if (f.coutMax !== null && !(it.prix_coutant <= f.coutMax)) return false;
    if (f.venteMin !== null && !(it.prix_vente >= f.venteMin)) return false;
    if (f.venteMax !== null && !(it.prix_vente <= f.venteMax)) return false;
    if (f.recMin !== null && !(it.recuperation >= f.recMin)) return false;
    if (f.recMax !== null && !(it.recuperation <= f.recMax)) return false;
    return true;
  });
  $('#fiches-grid').innerHTML = items.map(ficheCard).join('') || vide('Aucune fiche ne correspond aux filtres');
  if (isAdmin) bindFicheAdmin();
}

function ficheCard(it) {
  const img = it.image
    ? `<img src="${escapeHtml(it.image)}" alt="" style="max-width:100%;border-radius:8px;margin-bottom:8px">`
    : `<div class="img-placeholder">🖼️ Pas d'image</div>`;
  const adminZone = isAdmin ? `
    <div class="admin-zone" style="margin-top:8px;display:flex;flex-direction:column;gap:6px">
      <input type="file" accept="image/*" data-fiche="${escapeHtml(it.nom)}" class="fiche-image-input" style="font-size:0.75rem">
      <label style="font-size:0.8rem">♻️ Récupération
        <input type="number" min="1" value="${escapeHtml(String(it.recuperation ?? 1))}" data-fiche-rec="${escapeHtml(it.nom)}" style="width:70px">
      </label>
      <label style="font-size:0.8rem">🛡️ Durabilité
        <select data-fiche-duree="${escapeHtml(it.nom)}">
          <option value="" ${!it.duree ? 'selected' : ''}>Non renseignée</option>
          <option ${it.duree === 'Très bonne' ? 'selected' : ''}>Très bonne</option>
          <option ${it.duree === 'Bonne' ? 'selected' : ''}>Bonne</option>
          <option ${it.duree === 'Mauvaise' ? 'selected' : ''}>Mauvaise</option>
        </select>
      </label>
      <button class="btn-primary fiche-save-btn" data-fiche-save="${escapeHtml(it.nom)}" style="font-size:0.8rem">💾 Enregistrer</button>
    </div>` : '';
  return `<div class="item-card">
    <h3>${escapeHtml(it.nom)} <span class="meta">(${escapeHtml(it.type)})</span></h3>
    ${img}
    <div class="details">💰 Coûtant : <b>${it.prix_coutant != null ? fmt(it.prix_coutant) + ' G' : escapeHtml(it.coutant || '?')}</b></div>
    <div class="details">🏪 Vente PNJ : <b>${it.prix_vente != null ? fmt(it.prix_vente) + ' G' : escapeHtml(it.pnj || '?')}</b></div>
    <div class="details">♻️ Récupération : <b>${escapeHtml(String(it.recuperation ?? 1))}</b></div>
    <div class="details">🛡️ Durabilité : <b>${escapeHtml(it.duree || 'Non renseignée')}</b></div>
    ${adminZone}
  </div>`;
}

function bindFicheAdmin() {
  document.querySelectorAll('.fiche-image-input').forEach(inp => {
    inp.addEventListener('change', async () => {
      const file = inp.files[0];
      if (!file) return;
      if (file.size > 2 * 1024 * 1024) { alert('Image trop lourde (max 2 Mo).'); return; }
      const dataUrl = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result); r.onerror = rej;
        r.readAsDataURL(file);
      });
      const resp = await fetch('/api/fiches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom: inp.dataset.fiche, image: dataUrl }),
      });
      if (resp.ok) loadFiches(true);
      else alert('Erreur : connexion administrateur requise.');
    });
  });
  document.querySelectorAll('.fiche-save-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const nom = btn.dataset.ficheSave;
      const rec = document.querySelector(`[data-fiche-rec="${CSS.escape(nom)}"]`);
      const dur = document.querySelector(`[data-fiche-duree="${CSS.escape(nom)}"]`);
      const body = { nom };
      if (rec) body.recuperation = rec.value;
      if (dur) body.duree = dur.value;
      const resp = await fetch('/api/fiches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (resp.ok) loadFiches(true);
      else alert('Erreur : connexion administrateur requise.');
    });
  });
}

async function loginAdmin(password) {
  const resp = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mot_de_passe: password }),
  });

  const adminPassword = $('#admin-password');
  const loginError = $('#admin-login-error');
  const floatingError = $('#admin-floating-error');

  if (resp.ok) {
    if (adminPassword) adminPassword.value = '';
    if (loginError) loginError.textContent = '';
    if (floatingError) floatingError.textContent = '';
    setAdmin(true);
    return true;
  }

  const err = await resp.json().catch(() => ({}));
  const msg = err.erreur || 'Mot de passe incorrect';
  if (loginError) loginError.textContent = msg;
  if (floatingError) floatingError.textContent = msg;
  return false;
}

async function logoutAdmin() {
  await fetch('/api/logout', { method: 'POST' });
  setAdmin(false);
}

$('#admin-login-btn').addEventListener('click', () => {
  $('#admin-login-box').hidden = !$('#admin-login-box').hidden;
  $('#admin-password').focus();
});

$('#admin-login-confirm').addEventListener('click', async () => {
  await loginAdmin($('#admin-password').value);
});

$('#admin-logout-btn').addEventListener('click', async () => {
  await logoutAdmin();
});

$('#admin-floating-toggle').addEventListener('click', () => {
  const panel = $('#admin-floating-panel');
  if (!panel) return;
  panel.hidden = !panel.hidden;
  panel.dataset.open = String(!panel.hidden);
  if (!panel.hidden && !isAdmin) {
    $('#admin-floating-password').focus();
  }
});

$('#admin-floating-login-btn').addEventListener('click', async () => {
  const ok = await loginAdmin($('#admin-floating-password').value);
  if (ok) {
    $('#admin-floating-password').value = '';
  }
});

$('#admin-floating-logout-btn').addEventListener('click', async () => {
  await logoutAdmin();
  $('#admin-floating-panel').hidden = false;
});

$('#admin-floating-password').addEventListener('keydown', async (e) => {
  if (e.key === 'Enter') {
    await loginAdmin($('#admin-floating-password').value);
  }
});

$('#admin-module-select').addEventListener('change', populateAdminEditor);
$('#admin-kind-select').addEventListener('change', populateAdminEditor);
$('#admin-item-select').addEventListener('change', populateAdminEditor);

$('#admin-save-btn').addEventListener('click', async () => {
  const module = $('#admin-module-select').value;
  const kind = $('#admin-kind-select').value;
  const nom = $('#admin-item-select').value;
  if (!nom) return;

  if (kind === 'prix') {
    const category = $('#admin-price-category').value;
    const payload = {
      nom,
      categorie: category,
      coutant: $('#admin-price-coutant').value,
      client: $('#admin-price-client').value,
      pnj: $('#admin-price-pnj').value,
    };
    const resp = await fetch(`/api/prix/${module}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) { alert('Erreur de sauvegarde du prix'); return; }
  } else {
    const payload = {
      nom,
      ingredients: $('#admin-recipe-ingredients').value,
      details: $('#admin-recipe-details').value,
      date: $('#admin-recipe-date').value,
    };
    const resp = await fetch(`/api/recettes/${module}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) { alert('Erreur de sauvegarde de la recette'); return; }
  }

  await populateAdminEditor();
  if (module === 'baguettes') { loadPrix('baguettes'); loadRecettes('baguettes'); }
  else { loadPrix('balais'); loadRecettes('balais'); }
  alert('Modifications enregistrées.');
});

// Filtres fiches : re-render à chaque changement
['fiche-search', 'filtre-type', 'filtre-duree', 'filtre-coutant-min', 'filtre-coutant-max',
 'filtre-vente-min', 'filtre-vente-max', 'filtre-recup-min', 'filtre-recup-max'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener(id === 'fiche-search' ? 'input' : 'change', () => renderFiches());
});

if (pageFromHash() === 'infos') { loadSession(); loadFiches(); }

window.addEventListener('load', () => {
  loadSession();
  const panel = $('#admin-floating-panel');
  if (panel) panel.hidden = true;
});
