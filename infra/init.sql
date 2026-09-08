-- Veille de vente Cameroun & CEMAC — schéma initial (v0.1)
-- Lancé automatiquement par docker-compose (volume /docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$ BEGIN
  CREATE TYPE source_type AS ENUM ('ecommerce','facebook','whatsapp','telegram','tiktok','terrain','institutionnel','manuel','api_momo');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE methode_collecte AS ENUM ('scrape','terrain','manuel','api');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE gravite AS ENUM ('rouge','jaune','vert');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Référentiels ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produits (
  id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  nom TEXT NOT NULL,
  categorie TEXT NOT NULL,
  unite TEXT NOT NULL DEFAULT 'piece',
  marques_suivies TEXT[] DEFAULT '{}',
  alias TEXT[] DEFAULT '{}',
  traceur BOOLEAN DEFAULT FALSE,
  cree_le TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS marches (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  ville TEXT NOT NULL,
  pays CHAR(2) NOT NULL DEFAULT 'CM',
  lat DOUBLE PRECISION, lon DOUBLE PRECISION,
  jours_affluence TEXT[] DEFAULT '{}',
  UNIQUE (nom, ville)
);

CREATE TABLE IF NOT EXISTS sources (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL UNIQUE,
  type source_type NOT NULL,
  url_ou_compte TEXT,
  frequence TEXT DEFAULT 'hebdo',
  statut_legal TEXT DEFAULT 'a_qualifier',
  actif BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS corridors (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL UNIQUE,
  origine TEXT NOT NULL,
  destination TEXT NOT NULL,
  distance_km INTEGER
);

-- ── Cœur : relevés & offres ───────────────────────────────────
CREATE TABLE IF NOT EXISTS releves_prix (
  id SERIAL PRIMARY KEY,
  produit_id INTEGER NOT NULL REFERENCES produits(id),
  source_id INTEGER NOT NULL REFERENCES sources(id),
  marche_id INTEGER REFERENCES marches(id),
  prix NUMERIC(14,2) NOT NULL CHECK (prix > 0),
  prix_gros NUMERIC(14,2),
  devise TEXT NOT NULL DEFAULT 'XAF',
  ville TEXT NOT NULL,
  pays CHAR(2) NOT NULL DEFAULT 'CM',
  vendeur_hash TEXT,
  marque TEXT,
  origine TEXT,
  rupture BOOLEAN DEFAULT FALSE,
  promo BOOLEAN DEFAULT FALSE,
  promo_detail TEXT,
  paiement_momo BOOLEAN DEFAULT FALSE,
  methode methode_collecte NOT NULL DEFAULT 'manuel',
  preuve_url TEXT,
  observe_le TIMESTAMPTZ NOT NULL DEFAULT now(),
  collecteur TEXT,
  cree_le TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_releves_produit_ville_date ON releves_prix (produit_id, ville, observe_le);
CREATE INDEX IF NOT EXISTS idx_releves_marche_date ON releves_prix (marche_id, observe_le);

CREATE TABLE IF NOT EXISTS offres_digitales (
  id SERIAL PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  url TEXT UNIQUE NOT NULL,
  titre TEXT NOT NULL,
  prix NUMERIC(14,2),
  ancien_prix NUMERIC(14,2),
  remise_pct NUMERIC(5,2),
  vendeur_hash TEXT,
  ville TEXT,
  engagement JSONB DEFAULT '{}',
  capture_le TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commentaires (
  id SERIAL PRIMARY KEY,
  offre_id INTEGER REFERENCES offres_digitales(id) ON DELETE SET NULL,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  texte TEXT NOT NULL,
  auteur_hash TEXT,
  langue TEXT DEFAULT 'fr',
  sentiment_score INTEGER DEFAULT 0,
  motif TEXT,
  capture_le TIMESTAMPTZ DEFAULT now()
);

-- ── Logistique & macro ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS releves_logistique (
  id SERIAL PRIMARY KEY,
  corridor_id INTEGER NOT NULL REFERENCES corridors(id),
  delai_jours NUMERIC(6,1),
  cout_tonne_xaf NUMERIC(14,2),
  indice_tracasserie INTEGER CHECK (indice_tracasserie BETWEEN 1 AND 5),
  commentaire TEXT,
  observe_le TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS indicateurs_macro (
  id SERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  indicateur TEXT NOT NULL,
  valeur NUMERIC(16,4) NOT NULL,
  periode DATE NOT NULL,
  note TEXT,
  UNIQUE (source, indicateur, periode)
);

-- ── Alertes ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alertes (
  id SERIAL PRIMARY KEY,
  type TEXT NOT NULL,
  gravite gravite NOT NULL DEFAULT 'jaune',
  titre TEXT NOT NULL,
  detail JSONB DEFAULT '{}',
  produit_id INTEGER REFERENCES produits(id),
  marche_id INTEGER REFERENCES marches(id),
  cree_le TIMESTAMPTZ DEFAULT now(),
  resolu BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_alertes_gravite_date ON alertes (gravite, cree_le) WHERE resolu = FALSE;

-- ── Seed minimal ──────────────────────────────────────────────
INSERT INTO marches (nom, ville, pays, lat, lon, jours_affluence) VALUES
  ('Marché Central', 'Douala', 'CM', 4.048, 9.704, '{sam,mer}'),
  ('Mboppi', 'Douala', 'CM', 4.058, 9.732, '{sam}'),
  ('Marché Mokolo', 'Yaoundé', 'CM', 3.873, 11.502, '{sam,mer}'),
  ('Marché Mfoundi', 'Yaoundé', 'CM', 3.866, 11.522, '{dim,sam}'),
  ('Marché A', 'Bafoussam', 'CM', 5.478, 10.417, '{sam}'),
  ('Poto-Poto', 'Brazzaville', 'CG', -4.255, 15.256, '{sam}'),
  ('Marché Central', 'NDjamena', 'TD', 12.134, 15.055, '{sam}')
ON CONFLICT DO NOTHING;

INSERT INTO sources (nom, type, url_ou_compte, frequence, statut_legal) VALUES
  ('Jumia Cameroun', 'ecommerce', 'https://www.jumia.cm', 'quotidien', 'tolere'),
  ('CoinAfrique', 'ecommerce', 'https://www.coinafrique.com', 'quotidien', 'tolere'),
  ('Glotelho', 'ecommerce', 'https://www.glotelho.cm', 'quotidien', 'tolere'),
  ('Relevés terrain Kobo', 'terrain', 'kobo:releve-prix', 'hebdo', 'autorise'),
  ('Panel Facebook', 'facebook', 'panel:50-pages', 'quotidien', 'a_qualifier'),
  ('Canaux Telegram', 'telegram', 'panel:10-canaux', 'quotidien', 'a_qualifier')
ON CONFLICT DO NOTHING;

INSERT INTO corridors (nom, origine, destination, distance_km) VALUES
  ('Douala-Bangui', 'Douala', 'Bangui', 1450),
  ('Douala-Ndjamena', 'Douala', 'NDjamena', 1850),
  ('Douala-Brazzaville', 'Douala', 'Brazzaville', 1500),
  ('Kribi-Yaoundé', 'Kribi', 'Yaoundé', 175),
  ('Ekok-Ikom (Nigeria)', 'Ekok', 'Ikom', 90)
ON CONFLICT DO NOTHING;

INSERT INTO produits (sku, nom, categorie, unite, marques_suivies, alias, traceur) VALUES
  ('RIZ-PARF-50KG', 'Riz parfumé 50 kg', 'Alimentaire', 'sac 50kg', '{Meme,Broli}', '{riz 50 kg parfume,riz parfume sac}', TRUE),
  ('HUILE-VEG-1L', 'Huile végétale 1 L', 'Alimentaire', 'bouteille 1L', '{Mayor,Diamaor}', '{huile 1l,huile vegetale litre}', TRUE),
  ('SUCRE-1KG', 'Sucre en poudre 1 kg', 'Alimentaire', 'kg', '{Sosucam}', '{sucre 1kg}', TRUE),
  ('CIMENT-50KG', 'Ciment 50 kg', 'Materiaux', 'sac 50kg', '{Cimencam,Dangote}', '{ciment sac,ciment 50}', TRUE),
  ('CONGEL-200L', 'Congélateur 200 L', 'Electromenager', 'piece', '{Hisense,Nasco}', '{congelateur 200l}', TRUE),
  ('TV-32', 'Téléviseur 32 pouces', 'Electromenager', 'piece', '{Hisense,TCL}', '{tv 32,tv 32 pouces}', FALSE),
  ('SMART-ENTRY', 'Smartphone entrée de gamme 64 Go', 'Telephonie', 'piece', '{Tecno,Itel,Redmi}', '{tecno spark,itel,redmi}', TRUE)
ON CONFLICT DO NOTHING;
