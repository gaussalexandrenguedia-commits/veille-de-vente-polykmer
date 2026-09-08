"""Tests webapp : compat SQLite (StringArray) + seed démo idempotent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import Commentaire, Produit, RelevePrix  # noqa: E402
from app.seed import seed_all  # noqa: E402


def _session(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng)()


def test_stringarray_sqlite_roundtrip(tmp_path):
    s = _session(tmp_path)
    s.add(Produit(sku="X", nom="x", categorie="c", unite="u",
                  marques_suivies=["a", "b"], alias=["z"]))
    s.commit()
    p = s.query(Produit).filter_by(sku="X").first()
    assert p.marques_suivies == ["a", "b"]
    assert p.alias == ["z"]


def test_seed_idempotent(tmp_path):
    s = _session(tmp_path)
    r1 = seed_all(s)
    assert r1["status"] == "seeded"
    assert r1["releves"] > 500
    assert s.query(Commentaire).count() >= 20
    assert s.query(RelevePrix).count() == r1["releves"]
    r2 = seed_all(s)
    assert r2["status"] == "exists"
    assert s.query(RelevePrix).count() == r1["releves"]
