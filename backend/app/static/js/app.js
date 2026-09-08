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

async function fillVilles(datalistId) {
  try {
    const villes = await getJSON("/api/v1/villes");
    const dl = $(datalistId);
    if (dl) dl.innerHTML = villes.map((v) => `<option value="${v.ville}">${v.pays}</option>`).join("");
  } catch (e) { /* silencieux */ }
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
  fillVilles("dlVilles");
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

/* ── Agent IA ──────────────────────────────────────────── */
function mdLite(s) {
  return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^- (.+)$/gm, "• $1").replace(/\n/g, "<br>");
}
async function pageIA() {
  async function statut() {
    const st = await getJSON("/api/v1/ai/statut");
    $("iaStatus").textContent = st.ia_disponible
      ? `🤖 Agent IA — Gemini connecté (${st.nb_cles} clés)` : "🤖 Agent IA — mode heuristique offline";
    $("iaDetail").textContent = st.ia_disponible
      ? `Modèles : ${st.modeles.join(" → ")} · clés ${st.cles.join(", ")}`
      : "Aucune clé GEMINI_API_KEYS : parser/scoreur/messages en heuristique, vision et rapport enrichi indisponibles.";
  }
  fillVilles("dlVilles");
  await statut();
  $("btnTestIA").onclick = async () => {
    try {
      const r = await postJSON("/api/v1/ai/test");
      toast(r.ok ? `Gemini OK (${r.latence_ms} ms)` : "Échec : " + r.erreur, r.ok ? "ok" : "err");
    } catch (e) { toast(e.message, "err"); }
  };
  const prods = await getJSON("/api/v1/produits");
  $("iaProduit").innerHTML = prods.map((p) => `<option value="${p.sku}">${esc(p.nom)}</option>`).join("");
  $("formParse").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await postJSON("/api/v1/ai/parser-annonce", { texte: $("iaTexte").value });
      const out = $("iaParseOut");
      out.hidden = false;
      out.textContent = JSON.stringify(r, null, 2);
    } catch (err) { toast(err.message, "err"); }
  };
  $("formScore").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await postJSON("/api/v1/ai/scorer", { produit: $("iaProduit").value,
        prix: parseFloat($("iaPrix").value), ville: $("iaVille").value || null,
        texte: $("iaTexteScore").value });
      const vc = r.verdict === "prioritaire" ? "b-green" : r.verdict === "suspect" ? "b-red" : r.verdict === "interessant" ? "b-yellow" : "b-gray";
      $("iaScoreOut").innerHTML = `<div class="kpis small">
        <div class="kpi"><span class="kpi-label">Score</span><span class="kpi-val">${r.score}/100</span></div>
        <div class="kpi"><span class="kpi-label">Verdict</span><span class="kpi-val">${badge(r.verdict, vc)}</span></div>
        <div class="kpi"><span class="kpi-label">Écart marché</span><span class="kpi-val">${pct(r.ecart_pct, true)}</span></div>
        <div class="kpi"><span class="kpi-label">Médiane</span><span class="kpi-val">${xaf(r.mediane_marche)}</span></div></div>
        <div class="muted">${r.fraude_suspectee ? "🚨 " : "✓ "}${r.raisons.map(esc).join(" · ")} <i>(${esc(r.source)})</i></div>`;
    } catch (err) { toast(err.message, "err"); }
  };
  $("formVision").onsubmit = async (e) => {
    e.preventDefault();
    const f = $("iaImage").files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f); fd.append("titre", $("iaTitre").value);
    try {
      const r = await fetch("/api/v1/ai/analyser-image", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
      const out = $("iaVisionOut");
      out.hidden = false;
      out.textContent = JSON.stringify(data, null, 2);
    } catch (err) { toast(err.message, "err"); }
  };
  $("formMsg").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await postJSON("/api/v1/ai/message-vendeur", { produit: $("iaMProduit").value,
        prix: parseFloat($("iaMPrix").value), ville: $("iaMVille").value,
        phone: $("iaMPhone").value || null,
        prix_propose: $("iaMPropose").value ? parseFloat($("iaMPropose").value) : null });
      $("iaMsgOut").innerHTML = `<div class="comment">${esc(r.message)}
        <div class="meta"><i>(${esc(r.source)})</i>
        ${r.wa_link ? `<a class="btn small primary" target="_blank" rel="noopener" href="${esc(r.wa_link)}">💬 Ouvrir WhatsApp</a>` : ""}</div></div>`;
    } catch (err) { toast(err.message, "err"); }
  };
  $("btnRapport").onclick = async () => {
    try {
      const r = await getJSON("/api/v1/ai/rapport-jour");
      $("iaRapportOut").innerHTML = mdLite(r.rapport) + `<div class="meta"><i>source : ${esc(r.source)}</i></div>`;
    } catch (e) { toast(e.message, "err"); }
  };
}

/* ── Deals ─────────────────────────────────────────────── */
function verdictBadge(v) {
  return v === "prioritaire" ? badge("🔥 prioritaire", "b-green")
    : v === "interessant" ? badge("👍 intéressant", "b-yellow")
    : v === "sans_ref" ? badge("sans réf", "b-gray")
    : v === "suspect" ? badge("🚨 suspect", "b-red") : badge(v, "b-gray");
}
function statutBadge(s) {
  return s === "nouveau" ? badge("🆕 nouveau", "b-blue")
    : s === "contacte" ? badge("💬 contacté", "b-yellow")
    : s === "conclu" ? badge("✅ conclu", "b-green") : badge("🗑 abandonné", "b-gray");
}
async function pageDeals() {
  fillVilles("dlVilles");
  const prods = await getJSON("/api/v1/produits");
  $("dmProduit").innerHTML = `<option value="">— sans produit —</option>` +
    prods.map((p) => `<option value="${p.sku}">${esc(p.nom)}</option>`).join("");
  try { $("cKey").value = localStorage.getItem("api_key") || ""; } catch (e) {}
  async function load() {
    const st = $("fStatut").value, vd = $("fVerdict").value;
    const d = await getJSON("/api/v1/deals" + (st || vd ? "?" + new URLSearchParams({ ...(st ? { statut: st } : {}), ...(vd ? { verdict: vd } : {}) }) : ""));
    $("dNouveaux").textContent = d.par_statut.nouveau || 0;
    $("dContactes").textContent = d.par_statut.contacte || 0;
    $("dConclus").textContent = d.par_statut.conclu || 0;
    $("dEco").textContent = xaf(d.economie_potentielle);
    $("tableDeals").innerHTML = d.items.length ? d.items.map((r) => {
      const ec = r.ecart_pct == null ? badge("—", "b-gray")
        : badge(pct(r.ecart_pct, true), r.ecart_pct <= -20 ? "b-green" : r.ecart_pct <= -10 ? "b-yellow" : "b-gray");
      const prix = r.prix == null ? "—" : `<b class="num">${xaf(r.prix)}</b>` +
        (r.mediane_ref ? ` <span class="muted">/ ${xaf(r.mediane_ref)}</span>` : "");
      let act = "";
      if (r.statut === "nouveau" || r.statut === "contacte") {
        act += `<button class="btn small primary" data-a="contacte" data-id="${r.id}" data-u="${esc(r.preuve_url || "")}" data-p="${esc(r.phone || "")}">💬 Contacter</button> `;
        act += `<button class="btn small" data-a="conclu" data-id="${r.id}">✅</button> `;
        act += `<button class="btn small" data-a="abandonne" data-id="${r.id}">🗑</button>`;
      } else act = `<button class="btn small" data-a="nouveau" data-id="${r.id}">↩ Rouvrir</button>`;
      return `<tr><td><b class="num">${r.score}</b> ${verdictBadge(r.verdict)}</td>
        <td>${esc(r.titre)}<br><span class="muted">${esc(r.produit || "")} · ${esc(r.ville || "")}${r.phone ? " · ☎ " + esc(r.phone) : ""}</span></td>
        <td>${prix} ${ec}</td><td class="muted">${esc(r.source || "")}</td>
        <td>${statutBadge(r.statut)}</td><td style="white-space:normal">${act}</td></tr>`;
    }).join("") : `<tr><td colspan="6"><div class="empty">Aucun deal — lancez une collecte ou collez une annonce ⬇</div></td></tr>`;
    document.querySelectorAll("#tableDeals button").forEach((b) =>
      b.onclick = async () => {
        try {
          await fetch(`/api/v1/deals/${b.dataset.id}`, { method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ statut: b.dataset.a }) }).then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
          if (b.dataset.a === "contacte") {
            const url = b.dataset.p ? "https://wa.me/237" + b.dataset.p.replace(/\D/g, "").slice(-9) : b.dataset.u;
            if (url) window.open(url, "_blank");
          }
          toast("Deal → " + b.dataset.a, "ok");
          load();
        } catch (e) { toast(e.message, "err"); }
      });
  }
  $("fStatut").onchange = $("fVerdict").onchange = load;
  $("formDealTexte").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await postJSON("/api/v1/deals/depuis-texte",
        { texte: $("dtTexte").value, url: $("dtUrl").value || null });
      $("dtOut").textContent = `→ deal #${r.deal.id} · score ${r.deal.score} · ${r.deal.verdict} · ${r.parse.ville || "?"} · ${r.parse.prix || "?"} XAF`;
      $("dtTexte").value = ""; $("dtUrl").value = "";
      toast("Deal créé depuis le texte", "ok");
      load();
    } catch (err) { toast(err.message, "err"); }
  };
  $("formDealManuel").onsubmit = async (e) => {
    e.preventDefault();
    const v = $("dmUrl").value.trim();
    const isPhone = /^[\d\s+.]{9,14}$/.test(v);
    try {
      await postJSON("/api/v1/deals", { produit: $("dmProduit").value || null,
        prix: parseFloat($("dmPrix").value), ville: $("dmVille").value,
        preuve_url: v && !isPhone ? v : null, phone: v && isPhone ? v : null });
      toast("Deal créé", "ok");
      load();
    } catch (err) { toast(err.message, "err"); }
  };
  $("btnCollecter").onclick = async () => {
    const key = $("cKey").value;
    try { localStorage.setItem("api_key", key); } catch (e) {}
    $("jobStatus").textContent = "lancement…";
    try {
      const r = await fetch("/api/v1/collecte/lancer", { method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": key },
        body: JSON.stringify({ site: $("cSite").value, query: $("cQuery").value,
          ville: $("cVille").value, max_pages: 1 }) });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
      $("jobStatus").textContent = `job ${data.job} en cours… (actualisation auto)`;
      const timer = setInterval(async () => {
        try {
          const j = await getJSON("/api/v1/collecte/jobs/" + data.job);
          if (j.status === "termine") {
            clearInterval(timer);
            const res = j.resultat || {};
            $("jobStatus").textContent = `✅ ${res.offres_inserees || 0} offres, ${res.releves_prix_crees || 0} relevés, ${(res.deals_crees || []).length} deals`;
            toast("Collecte terminée", "ok");
            load();
          } else if (j.status === "erreur") {
            clearInterval(timer);
            $("jobStatus").textContent = "❌ " + (j.erreur || "erreur");
          } else $("jobStatus").textContent = `job ${data.job} : ${j.status}…`;
        } catch (e) { clearInterval(timer); }
      }, 5000);
    } catch (e) { toast(e.message, "err"); $("jobStatus").textContent = ""; }
  };
  await load();
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
    sniper: pageSniper, social: pageSocial, releves: pageReleves, ia: pageIA, deals: pageDeals,
    referentiels: pageReferentiels }[page];
  if (fn) try { await fn(); } catch (e) { toast("Erreur : " + e.message, "err"); }
});
