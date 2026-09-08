-- Migration 003 — table des deals (Postgres prod).
-- SQLite démo : créée automatiquement au démarrage (create_all).
-- Appliquer : psql $DATABASE_URL -f infra/migrations/003_opportunites.sql

CREATE TABLE IF NOT EXISTS opportunites (
  id SERIAL PRIMARY KEY,
  titre TEXT NOT NULL,
  produit_id INTEGER REFERENCES produits(id),
  source_id INTEGER REFERENCES sources(id),
  prix NUMERIC(14,2),
  mediane_ref NUMERIC(14,2),
  ecart_pct NUMERIC(7,2),
  score INTEGER DEFAULT 0,
  verdict TEXT DEFAULT 'marche',
  ville TEXT DEFAULT '',
  pays CHAR(2) DEFAULT 'CM',
  preuve_url TEXT,
  phone TEXT,
  statut TEXT DEFAULT 'nouveau',
  notes TEXT DEFAULT '',
  meta JSONB DEFAULT '{}',
  cree_le TIMESTAMPTZ DEFAULT now(),
  maj_le TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_deals_statut ON opportunites (statut, score DESC);
CREATE INDEX IF NOT EXISTS idx_deals_produit ON opportunites (produit_id);
