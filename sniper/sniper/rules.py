"""Moteur de règles : baisses de prix, seuils, stock, mots-clés, nouveautés.

Entrée : watch (dict YAML), obs (observation courante), prev (obs précédente ou None).
Sortie : liste de Signal. Pur, synchrone, testable sans réseau.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Signal:
    watch_id: str
    rule: str
    title: str
    severity: str = "jaune"          # rouge | jaune | vert
    detail: dict = field(default_factory=dict)
    dedup_sig: str = ""              # signature de déduplication
    cooldown_key: str = ""           # clé de cooldown


def _fmt(p: float | None) -> str:
    return f"{p:,.0f} XAF".replace(",", " ") if p is not None else "n/a"


def evaluate(watch: dict, obs: dict, prev: dict | None) -> list[Signal]:
    wid = watch["id"]
    out: list[Signal] = []
    price, p_prev = obs.get("price"), (prev or {}).get("price")
    stock, s_prev = obs.get("stock"), (prev or {}).get("stock")
    text = obs.get("text", "") or ""
    items, i_prev = obs.get("items"), (prev or {}).get("items")

    for r in watch.get("rules", []):
        t = r.get("type")
        sev = r.get("severity", "jaune")

        if t == "drop_pct" and price and p_prev:
            drop = (p_prev - price) / p_prev * 100
            if drop >= float(r["value"]):
                out.append(Signal(wid, "drop_pct",
                    f"📉 Baisse {drop:.1f} % : {_fmt(p_prev)} → {_fmt(price)}",
                    severity="rouge" if drop >= 15 else sev,
                    detail={"prix_avant": p_prev, "prix": price, "drop_pct": round(drop, 2)},
                    dedup_sig=f"{wid}:drop:{int(price)}",
                    cooldown_key=f"{wid}:drop_pct"))

        elif t == "below" and price is not None and price < float(r["value"]):
            out.append(Signal(wid, "below",
                f"🎯 Sous le seuil : {_fmt(price)} < {_fmt(float(r['value']))}",
                severity=r.get("severity", "rouge"),
                detail={"prix": price, "seuil": float(r["value"])},
                dedup_sig=f"{wid}:below:{r['value']}",
                cooldown_key=f"{wid}:below"))

        elif t == "above" and price is not None and price > float(r["value"]):
            out.append(Signal(wid, "above",
                f"📈 Au-dessus du seuil : {_fmt(price)} > {_fmt(float(r['value']))}",
                severity=sev,
                detail={"prix": price, "seuil": float(r["value"])},
                dedup_sig=f"{wid}:above:{r['value']}",
                cooldown_key=f"{wid}:above"))

        elif t == "back_in_stock" and stock is True and s_prev is False:
            out.append(Signal(wid, "back_in_stock",
                f"✅ Retour en stock{f' — {_fmt(price)}' if price else ''}",
                severity=r.get("severity", "rouge"),
                detail={"prix": price},
                dedup_sig=f"{wid}:bis:{int(price or 0)}",
                cooldown_key=f"{wid}:back_in_stock"))

        elif t == "stock_changed" and stock is not None and s_prev is not None and stock != s_prev:
            out.append(Signal(wid, "stock_changed",
                f"📦 Stock : {'disponible' if stock else 'RUPTURE'}",
                severity="rouge" if stock is False else sev,
                detail={"stock": stock}, dedup_sig=f"{wid}:stock:{stock}",
                cooldown_key=f"{wid}:stock_changed"))

        elif t == "keyword" and text:
            m = re.search(r.get("pattern", ""), text, re.I | re.S)
            if m:
                extrait = re.sub(r"\s+", " ", m.group(0))[:120]
                out.append(Signal(wid, "keyword",
                    f"🔎 Mot-clé « {r.get('pattern')} » détecté : …{extrait}…",
                    severity=sev, detail={"pattern": r.get("pattern"), "extrait": extrait},
                    dedup_sig=f"{wid}:kw:{r.get('pattern')}:{abs(hash(extrait)) % 10**8}",
                    cooldown_key=f"{wid}:keyword"))

        elif t == "new_items" and items is not None:
            anciens = set(i_prev or [])
            nouveaux = [i for i in items if i not in anciens]
            if prev is not None:  # 1er passage = amorçage, pas d'alerte
                for nid in nouveaux[:5]:
                    out.append(Signal(wid, "new_item", f"🆕 Nouvel item : {nid}",
                        severity=sev, detail={"item_id": nid},
                        dedup_sig=f"{wid}:new:{nid}", cooldown_key=f"{wid}:new_items"))
                if len(nouveaux) > 5:
                    out.append(Signal(wid, "new_items",
                        f"🆕 +{len(nouveaux) - 5} autres nouveaux items",
                        severity="vert", detail={"count": len(nouveaux)},
                        dedup_sig=f"{wid}:newbatch:{len(nouveaux)}",
                        cooldown_key=f"{wid}:new_items"))

        elif t == "changed" and prev is not None and obs.get("hash") != (prev.get("hash")):
            out.append(Signal(wid, "changed", "🔄 Contenu modifié",
                severity=sev, detail={"hash": obs.get("hash")},
                dedup_sig=f"{wid}:chg:{obs.get('hash')}",
                cooldown_key=f"{wid}:changed"))

    return out
