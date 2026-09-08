/* Mini-bibliothèque de graphiques SVG — zéro dépendance. */
const PALETTE = ["#38bdf8", "#22c55e", "#f59e0b", "#f472b6", "#a78bfa", "#94a3b8"];

function el(tag, attrs = {}, text = "") {
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text) n.textContent = text;
  return n;
}
function emptyMsg(div, msg) {
  div.innerHTML = "";
  const p = document.createElement("div");
  p.className = "empty"; p.textContent = msg || "Pas de données";
  div.appendChild(p);
}
function niceMax(v) {
  if (!v || v <= 0) return 10;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

/* Courbes : series = {label: [{x: "2026-09-01", y: 28500}]} */
function lineChart(div, series, opts = {}) {
  div.innerHTML = "";
  const labels = Object.keys(series).filter((k) => series[k].length);
  if (!labels.length) return emptyMsg(div, opts.empty);
  const W = 640, H = 250, P = { l: 64, r: 12, t: 12, b: 30 };
  const allY = labels.flatMap((k) => series[k].map((d) => d.y));
  const allX = [...new Set(labels.flatMap((k) => series[k].map((d) => d.x)))].sort();
  const maxY = niceMax(Math.max(...allY) * 1.08), minY = Math.min(0, Math.min(...allY) * 0.92);
  const X = (i) => P.l + (i / Math.max(allX.length - 1, 1)) * (W - P.l - P.r);
  const Y = (v) => P.t + (1 - (v - minY) / (maxY - minY || 1)) * (H - P.t - P.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}` });
  for (let g = 0; g <= 4; g++) {
    const v = minY + ((maxY - minY) * g) / 4;
    svg.appendChild(el("line", { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), class: "grid" }));
    svg.appendChild(el("text", { x: P.l - 6, y: Y(v) + 4, "text-anchor": "end" },
      v >= 1000 ? Math.round(v / 100) / 10 + "k" : Math.round(v)));
  }
  const step = Math.max(1, Math.ceil(allX.length / 6));
  allX.forEach((x, i) => {
    if (i % step === 0 || i === allX.length - 1)
      svg.appendChild(el("text", { x: X(i), y: H - 8, "text-anchor": "middle" },
        String(x).slice(5)));
  });
  labels.forEach((k, li) => {
    const c = PALETTE[li % PALETTE.length];
    const pts = series[k].map((d) => [X(allX.indexOf(d.x)), Y(d.y)]);
    const path = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    svg.appendChild(el("path", { d: path, fill: "none", stroke: c, "stroke-width": 2 }));
    series[k].forEach((d) => {
      const circ = el("circle", { cx: X(allX.indexOf(d.x)), cy: Y(d.y), r: 3, fill: c });
      const t = el("title", {}, `${k} · ${d.x} : ${Math.round(d.y).toLocaleString("fr-FR")} XAF`);
      circ.appendChild(t); svg.appendChild(circ);
    });
  });
  div.appendChild(svg);
  const leg = document.createElement("div");
  leg.className = "legend";
  leg.innerHTML = labels.map((k, i) =>
    `<span><i class="chip" style="background:${PALETTE[i % PALETTE.length]}"></i>${k}</span>`).join("");
  div.appendChild(leg);
}

/* Barres verticales : items = [{label, value, color?}] */
function bars(div, items, opts = {}) {
  div.innerHTML = "";
  if (!items.length) return emptyMsg(div, opts.empty);
  const W = 640, H = Math.max(200, 120 + items.length * 8), P = { l: 64, r: 12, t: 12, b: 44 };
  const maxV = niceMax(Math.max(...items.map((d) => d.value)));
  const bw = (W - P.l - P.r) / items.length;
  const Y = (v) => P.t + (1 - v / maxV) * (H - P.t - P.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}` });
  for (let g = 0; g <= 4; g++) {
    const v = (maxV * g) / 4;
    svg.appendChild(el("line", { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), class: "grid" }));
    svg.appendChild(el("text", { x: P.l - 6, y: Y(v) + 4, "text-anchor": "end" },
      (opts.suffix === "%" ? v.toFixed(v < 10 ? 1 : 0) + "%" : Math.round(v).toLocaleString("fr-FR"))));
  }
  items.forEach((d, i) => {
    const x = P.l + i * bw + bw * 0.2, w = bw * 0.6;
    const r = el("rect", { x: x.toFixed(1), y: Y(d.value).toFixed(1), width: w.toFixed(1),
      height: Math.max(H - P.b - Y(d.value), 2).toFixed(1), rx: 3,
      fill: d.color || PALETTE[i % PALETTE.length] });
    r.appendChild(el("title", {}, `${d.label} : ${d.value}`));
    svg.appendChild(r);
    const t = el("text", { x: (x + w / 2).toFixed(1), y: H - 26, "text-anchor": "middle" },
      d.label.length > 14 ? d.label.slice(0, 13) + "…" : d.label);
    svg.appendChild(t);
    svg.appendChild(el("text", { x: (x + w / 2).toFixed(1), y: Y(d.value) - 5,
      "text-anchor": "middle" }, opts.suffix === "%" ? d.value + "%" : String(d.value)));
  });
  div.appendChild(svg);
}

/* Barres horizontales divergentes : items = [{label, value}] (±) */
function hbars(div, items, opts = {}) {
  div.innerHTML = "";
  if (!items.length) return emptyMsg(div, opts.empty);
  const rowH = 26, W = 640, P = { l: 190, r: 60, t: 8, b: 8 };
  const H = P.t + P.b + items.length * rowH;
  const maxA = Math.max(...items.map((d) => Math.abs(d.value)), 1);
  const mid = P.l + (W - P.l - P.r) / 2, half = (W - P.l - P.r) / 2;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}` });
  svg.appendChild(el("line", { x1: mid, x2: mid, y1: 4, y2: H - 4, class: "grid" }));
  items.forEach((d, i) => {
    const y = P.t + i * rowH;
    const w = (Math.abs(d.value) / maxA) * half;
    const x = d.value >= 0 ? mid : mid - w;
    const c = Math.abs(d.value) >= 10 ? "#ef4444" : Math.abs(d.value) >= 5 ? "#f59e0b" : "#22c55e";
    svg.appendChild(el("rect", { x: x.toFixed(1), y: y + 4, width: Math.max(w, 2).toFixed(1),
      height: rowH - 10, rx: 3, fill: c }));
    const lab = el("text", { x: P.l - 8, y: y + rowH / 2 + 4, "text-anchor": "end" },
      d.label.length > 26 ? d.label.slice(0, 25) + "…" : d.label);
    lab.appendChild(el("title", {}, d.label));
    svg.appendChild(lab);
    svg.appendChild(el("text", { x: (d.value >= 0 ? x + w + 6 : x - 6).toFixed(1),
      y: y + rowH / 2 + 4, "text-anchor": d.value >= 0 ? "start" : "end" },
      (d.value > 0 ? "+" : "") + d.value + (opts.suffix || "")));
  });
  div.appendChild(svg);
}
