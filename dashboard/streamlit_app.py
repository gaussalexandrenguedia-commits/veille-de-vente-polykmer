"""Dashboard MVP — Veille de vente Cameroun & CEMAC.

Source : data/samples/prix_exemple.csv par défaut.
Si API_URL est défini (ex. http://localhost:8000), tente de charger les KPIs live.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Veille Vente CM & CEMAC", page_icon="📊", layout="wide")

RACINE = Path(__file__).resolve().parents[1]
CSV_DEFAUT = RACINE / "data" / "samples" / "prix_exemple.csv"
API_URL = os.getenv("API_URL", "")

st.title("📊 Veille de vente — Cameroun & CEMAC")
st.caption("Prix • Promos • Ruptures • Concurrence • Sentiment — MVP v0.1 (données d'exemple)")


@st.cache_data
def charger_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return df


# ── Chargement ────────────────────────────────────────────────
st.sidebar.header("Source de données")
chemin = st.sidebar.text_input("Fichier CSV", str(CSV_DEFAUT))
try:
    df = charger_csv(chemin)
    st.sidebar.success(f"{len(df)} relevés chargés")
except Exception as e:  # noqa: BLE001
    st.error(f"Impossible de charger {chemin} : {e}")
    st.stop()

# ── Filtres ───────────────────────────────────────────────────
st.sidebar.header("Filtres")
cats = sorted(df["categorie"].unique())
cat = st.sidebar.multiselect("Catégories", cats, default=cats)
villes = sorted(df["ville"].unique())
ville = st.sidebar.multiselect("Villes", villes, default=villes)
produits = sorted(df["produit"].unique())
produit_sel = st.sidebar.selectbox("Produit (courbe)", produits,
                                   index=produits.index("Riz parfumé 50 kg") if "Riz parfumé 50 kg" in produits else 0)

f = df[df["categorie"].isin(cat) & df["ville"].isin(ville)].copy()
if f.empty:
    st.warning("Aucune donnée avec ces filtres.")
    st.stop()

# ── KPIs tête ─────────────────────────────────────────────────
def med_ponderee(g: pd.DataFrame) -> float:
    poids = {"terrain": 2, "scrape": 1, "manuel": 1, "api": 1.5}
    pool = []
    for _, r in g.iterrows():
        pool.extend([r["prix"]] * int(poids.get(r["methode"], 1)))
    return float(pd.Series(pool).median()) if pool else float("nan")

max_date = f["date"].max()
s_cur = f[f["date"] > max_date - pd.Timedelta(days=7)]
s_prev = f[(f["date"] <= max_date - pd.Timedelta(days=7)) & (f["date"] > max_date - pd.Timedelta(days=14))]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Relevés (7 j)", len(s_cur))
taux_rupt = s_cur["rupture"].mean() * 100 if len(s_cur) else 0
c2.metric("Ruptures (7 j)", f"{taux_rupt:.1f} %")
taux_promo = s_cur["promo"].mean() * 100 if len(s_cur) else 0
c3.metric("Offres en promo (7 j)", f"{taux_promo:.1f} %")
taux_momo = s_cur["paiement_momo"].mean() * 100 if len(s_cur) else 0
c4.metric("Mentions Mobile Money", f"{taux_momo:.0f} %")

# ── Courbe produit ────────────────────────────────────────────
st.subheader(f"Évolution du prix — {produit_sel}")
d = f[(f["produit"] == produit_sel) & (f["rupture"] == 0)]
if d.empty:
    st.info("Pas de relevés pour ce produit avec ces filtres.")
else:
    med = d.groupby(["date", "ville"])["prix"].median().reset_index()
    fig = px.line(med, x="date", y="prix", color="ville", markers=True,
                  labels={"prix": "Prix médian (XAF)", "date": ""})
    st.plotly_chart(fig, use_container_width=True)

# ── Variations & ruptures ─────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("Variations 7 j vs 7 j précédents (médiane pondérée)")
    rows = []
    for (sku, prod), g in f.groupby(["sku", "produit"]):
        g = g[g["rupture"] == 0]
        cur = g[g["date"] > max_date - pd.Timedelta(days=7)]
        prev = g[(g["date"] <= max_date - pd.Timedelta(days=7)) & (g["date"] > max_date - pd.Timedelta(days=14))]
        m_cur, m_prev = med_ponderee(cur), med_ponderee(prev)
        if pd.notna(m_cur) and pd.notna(m_prev) and m_prev:
            rows.append({"Produit": prod, "Médiane (XAF)": round(m_cur),
                         "Variation %": round((m_cur - m_prev) / m_prev * 100, 1),
                         "n": len(cur)})
    var = pd.DataFrame(rows).sort_values("Variation %", key=abs, ascending=False) if rows else pd.DataFrame()
    if not var.empty:
        st.dataframe(var.style.format({"Médiane (XAF)": "{:,.0f}", "Variation %": "{:+.1f} %"})
                     .map(lambda v: "color: red" if isinstance(v, (int, float)) and abs(v) >= 10 else None,
                            subset=["Variation %"]),
                     use_container_width=True, hide_index=True)
        alertes = var[abs(var["Variation %"]) >= 10]
        for _, r in alertes.iterrows():
            st.error(f"🔴 {r['Produit']} : {r['Variation %']:+.1f} % en 7 j ({r['Médiane (XAF)']:,.0f} XAF)")
    else:
        st.info("Pas assez d'historique pour calculer les variations.")

with col2:
    st.subheader("Ruptures par produit (7 j)")
    r = s_cur.groupby("produit")["rupture"].mean().mul(100).round(1).sort_values(ascending=False)
    if not r.empty:
        fig2 = px.bar(r, labels={"value": "% ruptures", "produit": ""}, color=r,
                      color_continuous_scale=["green", "orange", "red"])
        st.plotly_chart(fig2, use_container_width=True)

# ── Promos & marchés ──────────────────────────────────────────
col3, col4 = st.columns(2)
with col3:
    st.subheader("Promos par ville (7 j)")
    p = s_cur.groupby("ville")["promo"].mean().mul(100).round(1)
    st.plotly_chart(px.bar(p, labels={"value": "% promos"}), use_container_width=True)
with col4:
    st.subheader("Couverture : relevés par source (7 j)")
    s = s_cur.groupby("source").size().sort_values(ascending=False)
    st.plotly_chart(px.bar(s, labels={"value": "relevés"}), use_container_width=True)

# ── Détail ────────────────────────────────────────────────────
st.subheader("Derniers relevés")
st.dataframe(f.sort_values("date", ascending=False).head(100), use_container_width=True, hide_index=True)

st.divider()
st.caption("MVP v0.1 — Branchez l'API (`API_URL`) et Postgres pour passer des CSV aux données live. Voir README + docs/03-ARCHITECTURE.md")
