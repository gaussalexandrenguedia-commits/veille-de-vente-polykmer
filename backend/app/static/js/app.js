/* App web Veille Vente — logique par page (fetch API JSON). */
const $ = (id) => document.getElementById(id);
const xaf = (n) => n == null ? "—" : Math.round(n).toLocaleString("fr-FR") + " XAF";
const num = (n) => n == null ? "—" : Math.round(n).toLocaleString("fr-FR");
const pct = (n, signed) => (signed && n > 0 ? "+" : "") + n + " %";
const dtf = (iso) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function ago(s) {
  if (s < 90) return "à l'instant";
  if (s < 3600) return "il y a " + Math.round(s / 60) + " min";
  if (s < 86400) return "il y a " + Math.round(s / 3600) + " h";
  return "il y a " + Math.round(s / 86400) + " j";
}
async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("HTTP " + r.status + " sur " + url);
  return r.json();
}
async function postJSON(url, body) {
  const r = await fetch(url, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
  return data;
}
function toast(msg, cls) {
  const t = document.createElement("div");
  t.className = "toast " + (cls || "");
  t.textContent = msg;
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4200);
}
function badge(txt, cls) { return `<span class="badge ${cls}">${esc(txt)}</span>`; }
function gravBadge(g) {
  return g === "rouge" ? badge("🔴 critique", "b-red")
    : g === "vert" ? badge("🟢 info", "b-green") : badge("🟡 attention", "b-yellow");
}
function scoreBadge(s) {
  return s > 20 ? badge("😊 +" + s, "b-green")
    : s < -20 ? badge("😞 " + s, "b-red") : badge("😐 " + s, "b-gray");
}

/* ── Dashboard ─────────────────────────────────────────── */
async function pageDashboard() {
  const prods = await getJSON("/api/v1/produits");
  const sel = $("courbeProduit");
  sel.innerHTML = prods.map((p) => `<option value="${p.sku}">${esc(p.nom)}</option>`).join("");
  sel.value = "RIZ-PARF-50KG";
  async function load() {
    const s = await getJSON("/api/v1/dashboard/summary?produit=" + sel.value);
    $("kpiReleves").textContent = num(s.releves_7j);
    $("kpiRuptures").textContent = pct(s.rupture_pct);
    $("kpiPromos").textContent = pct(s.promo_pct);
    $("kpiMomo").textContent = pct(s.momo_pct);
    const series = {};
    for (const [ville, pts] of Object.entries((s.courbe && s.courbe.series) || {}))
      series[ville] = pts.map((p) => ({ x: p.date, y: p.prix }));
    lineChart($("chartCourbe"), series, { empty: "Pas de courbe pour ce produit" });
    hbars($("chartVariations"), s.variations.map((v) =>
      ({ label: v.produit, value: v.variation_pct })), { suffix: "%" });
    const rc = (t) => t >= 20 ? "#ef4444" : t >= 10 ? "#f59e0b" : "#22c55e";
    bars($("chartRuptures"), s.ruptures.map((r) =>
      ({ label: r.produit, value: r.taux, color: rc(r.taux) })), { suffix: "%" });
    bars($("chartPromos"), s.promos_ville.map((p) =>
      ({ label: p.ville, value: p.pct })), { suffix: "%" });
    bars($("chartCouverture"), s.couverture.map((c) => ({ label: c.source, value: c.n })));
    $("listAlertes").innerHTML = s.alertes.length ? s.alertes.map((a) =>
      `<div class="alert-item">${gravBadge(a.gravite)}<span class="grow">${esc(a.titre)}</span></div>`).join("")
      : `<div class="empty">Aucune alerte active 🎉</div>`;
  }
  sel.onchange = () => load().catch((e) => toast(e.message, "err"));
  await load();
}

/* ── Prix ──────────────────────────────────────────────── */
async function pagePrix() {
  const prods = await getJSON("/api/v1/produits");
  const sel = $("prixProduit");
  sel.innerHTML = prods.map((p) => `<option value="${p.sku}">${esc(p.nom)}</option>`).join("");
  sel.value = "RIZ-PARF-50KG";
  async function load() {
    const jours = $("prixJours").value;
    const c = await getJSON(`/api/v1/dashboard/courbe?produit=${sel.value}&jours=${jours}`);
    $("prixNom").textContent = c.produit + " (" + c.unite + ")";
    const series = {};
    for (const [ville, pts] of Object.entries(c.series))
      series[ville] = pts.map((p) => ({ x: p.date, y: p.prix }));
    lineChart($("chartPrix"), series, { empty: "Pas de données" });
    const all = Object.values(c.series).flat().map((p) => p.prix);
    const vars = await getJSON("/api/v1/kpi/variations?seuil=0");
    const v = vars.find((x) => x.sku === c.sku);
    if (all.length) {
      const med = all.slice().sort((a, b) => a - b)[Math.floor(all.length / 2)];
      $("prixStats").innerHTML =
        `<div class="kpi"><span class="kpi-label">Médiane</span><span class="kpi-val">${xaf(med)}</span></div>` +
        `<div class="kpi"><span class="kpi-label">Min / Max</span><span class="kpi-val">${xaf(Math.min(...all))} / ${xaf(Math.max(...all))}</span></div>` +
        `<div class="kpi"><span class="kpi-label">Variation 7 j</span><span class="kpi-val ${v && Math.abs(v.variation_pct) >= 10 ? "danger" : ""}">${v ? pct(v.variation_pct, true) : "—"}</span></div>` +
        `<div class="kpi"><span class="kpi-label">Villes suivies</span><span class="kpi-val">${Object.keys(c.series).length}</span></div>`;
    } else $("prixStats").innerHTML = "";
    const rel = await getJSON(`/api/v1/prix?produit=${sel.value}&jours=${jours}`);
    $("tablePrix").innerHTML = rel.serie.slice(-50).reverse().map((r) =>
      `<tr><td>${dtf(r.observe_le)}</td><td>${esc(r.ville)}</td><td class="num">${xaf(r.prix)}</td>` +
      `<td>${esc(r.collecteur || "")}</td><td>${badge(r.methode, "b-blue")}</td>` +
      `<td>${esc(r.marque || "")}</td><td>${r.promo ? badge("PROMO", "b-green") : ""}</td></tr>`).join("")
      || `<tr><td colspan="7" class="muted">Aucun relevé</td></tr>`;
  }
  sel.onchange = $("prixJours").onchange = () => load().catch((e) => toast(e.message, "err"));
  await load();
}

/* ── Alertes ───────────────────────────────────────────── */
async function pageAlertes() {
  async function load() {
    const g = $("filtreGravite").value;
    const list = await getJSON("/api/v1/kpi/alertes" + (g ? "?gravite=" + g : ""));
    $("nbAlertes").textContent = list.length;
    $("listAlertesFull").innerHTML = list.length ? list.map((a) =>
      `<div class="alert-item">${gravBadge(a.gravite)}<span class="grow"><b>${esc(a.type)}</b> — ${esc(a.titre)}</span>` +
      `<button class="btn small" data-id="${a.id}">✓ Résoudre</button></div>`).join("")
      : `<div class="empty">Aucune alerte 🎉</div>`;
    document.querySelectorAll("#listAlertesFull button").forEach((b) =>
      b.onclick = async () => {
        try { await postJSON(`/api/v1/kpi/alertes/${b.dataset.id}/resoudre`); toast("Alerte résolue", "ok"); load(); navBadge(); }
        catch (e) { toast(e.message, "err"); }
      });
  }
  $("filtreGravite").onchange = load;
  $("btnGenerer").onclick = async () => {
    try {
      const r = await postJSON("/api/v1/kpi/alertes/generer?seuil=" + $("seuilGenerer").value);
      toast(r.nouvelles_alertes + " nouvelle(s) alerte(s)", r.nouvelles_alertes ? "" : "ok");
      load(); navBadge();
    } catch (e) { toast(e.message, "err"); }
  };
  await load();
}

/* ── Sniper ────────────────────────────────────────────── */
async function pageSniper() {
  const st = await getJSON("/api/v1/sniper/status");
  if (!st.available) { $("sniperOnboard").hidden = false; return; }
  $("sniperStats").hidden = false;
  $("snWatches").textContent = st.watches.length;
  $("snSignaux").textContent = st.signaux_24h;
  $("snCooldowns").textContent = st.cooldowns_actifs;
  $("snConfig").textContent = st.config_connue ? "oui" : "non";
  $("watchGrid").innerHTML = st.watches.map((w) => {
    const frais = w.interval ? w.updated_ago_s < w.interval * 2 + 60 : w.updated_ago_s < 900;
    const stock = w.stock === true ? badge("✅ en stock", "b-green")
      : w.stock === false ? badge("⛔ rupture", "b-red") : badge("stock ?", "b-gray");
    return `<div class="watch-card">
      <h3>${esc(w.name)}</h3>
      <div class="muted">${badge(w.tier, "b-blue")} ${esc(w.ville)} ${w.interval ? "· toutes les " + w.interval + " s" : ""}</div>
      <div class="watch-price">${xaf(w.price)}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0">${stock}
        ${w.zone_ok ? badge("🎯 zone", "b-green") : ""}${w.selector_used ? badge("🩹 " + w.selector_used, "b-gray") : ""}
        ${w.seller_phone ? badge("☎️ tél", "b-green") : ""}</div>
      <div class="muted">${frais ? "🟢" : "🟠"} dernière obs. ${ago(w.updated_ago_s)}</div>
      <div style="margin-top:8px"><button class="btn small" data-w="${esc(w.id)}">Sélecteurs</button>
      <div id="sel-${esc(w.id)}" style="margin-top:6px"></div></div>
    </div>`;
  }).join("");
  document.querySelectorAll("#watchGrid button").forEach((b) =>
    b.onclick = async () => {
      const box = $("sel-" + b.dataset.w);
      if (box.dataset.done) { box.innerHTML = ""; delete box.dataset.done; return; }
      const rows = await getJSON("/api/v1/sniper/selectors/" + b.dataset.w);
      box.dataset.done = "1";
      box.innerHTML = rows.length ? rows.map((r) => {
        const tot = r.ok + r.fail, pc = tot ? Math.round((r.ok / tot) * 100) : 0;
        return `<div class="muted">${esc(r.selector)} — ${r.ok} ok / ${r.fail} ko</div><div class="selbar"><i style="width:${pc}%"></i></div>`;
      }).join("") : `<span class="muted">aucune stat sélecteur</span>`;
    });
}

/* ── Social ────────────────────────────────────────────── */
async function pageSocial() {
  async function load() {
    const s = await getJSON("/api/v1/social/resume?jours=14");
    $("soVolume").textContent = num(s.volume);
    const sc = $("soScore");
    sc.textContent = (s.score_moyen > 0 ? "+" : "") + s.score_moyen;
    sc.className = "kpi-val " + (s.score_moyen < -20 ? "danger" : s.score_moyen > 20 ? "ok" : "warn");
    $("soNeg").textContent = num(s.negatifs);
    $("soPos").textContent = num(s.positifs);
    lineChart($("chartSentiment"), { "Score moyen": s.timeline.map((t) => ({ x: t.date, y: t.score })) },
      { empty: "Pas de commentaires" });
    bars($("chartMotifs"), s.motifs.map((m, i) => ({ label: m.label, value: m.n })), {});
    $("listComments").innerHTML = s.derniers.length ? s.derniers.map((c) =>
      `<div class="comment">${esc(c.texte)}
       <div class="meta">${scoreBadge(c.score)}<span>${esc(c.source)}</span>
       ${c.motif ? badge(c.motif, "b-yellow") : ""}<span>${esc(c.langue)} · ${dtf(c.date)}</span></div></div>`).join("")
      : `<div class="empty">Aucun commentaire</div>`;
  }
  $("formComment").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await postJSON("/api/v1/social/commentaires",
        { source: $("cSource").value, texte: $("cTexte").value });
      $("cResult").textContent = `→ score ${r.score}, motif ${r.motif || "—"}`;
      $("cTexte").value = "";
      toast("Commentaire analysé et enregistré", "ok");
      load();
    } catch (err) { toast(err.message, "err"); }
  };
  await load();
}

/* ── Relevés ───────────────────────────────────────────── */
async function pageReleves() {
  const [prods, sources] = await Promise.all([
    getJSON("/api/v1/produits"), getJSON("/api/v1/sources")]);
  $("dlProduits").innerHTML = prods.map((p) =>
    `<option value="${p.sku}">${esc(p.nom)}</option>`).join("");
  $("rSource").innerHTML = sources.map((s) => `<option>${esc(s.nom)}</option>`).join("");
  $("rSource").value = "Relevés terrain Kobo";
  async function loadTable() {
    const rows = await getJSON("/api/v1/releves/recent?limit=60");
    $("tableReleves").innerHTML = rows.map((r) =>
      `<tr><td>${dtf(r.date)}</td><td>${esc(r.produit)}</td><td>${esc(r.ville)}</td>` +
      `<td class="num">${xaf(r.prix)}</td><td>${esc(r.source)}</td>` +
      `<td>${badge(r.methode, "b-blue")}</td>` +
      `<td>${r.rupture ? badge("RUPTURE", "b-red") : ""} ${r.promo ? badge("PROMO", "b-green") : ""}</td></tr>`).join("");
  }
  $("formReleve").onsubmit = async (e) => {
    e.preventDefault();
    const body = { produit: $("rProduit").value, source: $("rSource").value,
      ville: $("rVille").value, marche: $("rMarche").value || null,
      prix: parseFloat($("rPrix").value),
      prix_gros: $("rPrixGros").value ? parseFloat($("rPrixGros").value) : null,
      marque: $("rMarque").value || null, origine: $("rOrigine").value || null,
      promo: $("rPromo").checked, promo_detail: $("rPromoDetail").value || null,
      paiement_momo: $("rMomo").checked, rupture: $("rRupture").checked,
      methode: "manuel", collecteur: "webapp" };
    try {
      const r = await postJSON("/api/v1/releves", body);
      toast(`Relevé #${r.id} enregistré (${r.produit_nom})`, "ok");
      $("rPrix").value = ""; $("rPrixGros").value = "";
      loadTable();
    } catch (err) { toast(err.message, "err"); }
  };
  await loadTable();
}

/* ── Référentiels ──────────────────────────────────────── */
async function pageReferentiels() {
  document.querySelectorAll(".tab").forEach((t) =>
    t.onclick = () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("on"));
      t.classList.add("on");
      ["produits", "marches", "sources"].forEach((k) => $("tab-" + k).hidden = k !== t.dataset.tab);
    });
  const [prods, marches, sources] = await Promise.all([
    getJSON("/api/v1/produits"), getJSON("/api/v1/marches"), getJSON("/api/v1/sources")]);
  $("tableProduits").innerHTML = prods.map((p) =>
    `<tr><td><code>${esc(p.sku)}</code></td><td>${esc(p.nom)}</td><td>${esc(p.categorie)}</td>` +
    `<td>${esc(p.unite)}</td><td class="muted">${esc((p.marques_suivies || []).join(", "))}</td>` +
    `<td>${p.traceur ? "⭐" : ""}</td></tr>`).join("");
  const drapeaux = { CM: "🇨🇲", CG: "🇨🇬", GA: "🇬🇦", TD: "🇹🇩", CF: "🇨🇫", GQ: "🇬🇶" };
  $("tableMarches").innerHTML = marches.map((m) =>
    `<tr><td>${esc(m.nom)}</td><td>${esc(m.ville)}</td><td>${drapeaux[m.pays] || ""} ${esc(m.pays)}</td>` +
    `<td class="muted">${m.lat != null ? m.lat.toFixed(2) + ", " + m.lon.toFixed(2) : "—"}</td></tr>`).join("");
  $("tableSources").innerHTML = sources.map((s) =>
    `<tr><td>${esc(s.nom)}</td><td>${badge(s.type, "b-blue")}</td>` +
    `<td>${esc(s.frequence)}</td><td>${s.actif ? "✅" : "⏸️"}</td></tr>`).join("");
}

/* ── Commun : badge alertes + horloge ──────────────────── */
async function navBadge() {
  try {
    const rouges = await getJSON("/api/v1/kpi/alertes?gravite=rouge");
    const b = $("navAlertBadge");
    if (rouges.length) { b.textContent = rouges.length; b.hidden = false; }
    else b.hidden = true;
  } catch (e) { /* silencieux */ }
}
function clock() {
  const c = $("clock");
  if (c) c.textContent = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

document.addEventListener("DOMContentLoaded", async () => {
  clock(); setInterval(clock, 30000); navBadge();
  const page = document.body.dataset.page;
  const fn = { dashboard: pageDashboard, prix: pagePrix, alertes: pageAlertes,
    sniper: pageSniper, social: pageSocial, releves: pageReleves,
    referentiels: pageReferentiels }[page];
  if (fn) try { await fn(); } catch (e) { toast("Erreur : " + e.message, "err"); }
});
