-- Staging schema
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.raw_ads (
    id SERIAL PRIMARY KEY,
    titre TEXT,
    prix TEXT,
    localisation TEXT,
    surface TEXT,
    chambres TEXT,
    salles_de_bain TEXT,
    lien TEXT UNIQUE,
    scraped_at TIMESTAMP DEFAULT NOW()
);

-- Clean schema
CREATE SCHEMA IF NOT EXISTS clean;

CREATE TABLE IF NOT EXISTS clean.ads (
    id SERIAL PRIMARY KEY,
    titre TEXT,
    prix_mad NUMERIC,
    ville TEXT,
    quartier TEXT,
    surface_m2 NUMERIC,
    nb_chambres INTEGER,
    nb_salles_de_bain INTEGER,
    prix_par_m2 NUMERIC,
    lien TEXT UNIQUE,
    scraped_at TIMESTAMP
);

-- BI schema
CREATE SCHEMA IF NOT EXISTS bi_schema;

CREATE TABLE IF NOT EXISTS bi_schema.dim_location (
    id SERIAL PRIMARY KEY,
    ville TEXT,
    quartier TEXT
);

CREATE TABLE IF NOT EXISTS bi_schema.dim_features (
    id SERIAL PRIMARY KEY,
    surface_m2 NUMERIC,
    nb_chambres INTEGER,
    nb_salles_de_bain INTEGER
);

CREATE TABLE IF NOT EXISTS bi_schema.dim_time (
    id SERIAL PRIMARY KEY,
    scraped_at TIMESTAMP,
    jour INTEGER,
    mois INTEGER,
    annee INTEGER,
    jour_semaine TEXT
);

CREATE TABLE IF NOT EXISTS bi_schema.fact_annonce (
    id SERIAL PRIMARY KEY,
    titre TEXT,
    prix_mad NUMERIC,
    prix_par_m2 NUMERIC,
    lien TEXT,
    dim_location_id INTEGER REFERENCES bi_schema.dim_location(id),
    dim_features_id INTEGER REFERENCES bi_schema.dim_features(id),
    dim_time_id INTEGER REFERENCES bi_schema.dim_time(id)
);

-- ML schema
CREATE SCHEMA IF NOT EXISTS ml_schema;

CREATE TABLE IF NOT EXISTS ml_schema.feature_store (
    id SERIAL PRIMARY KEY,
    titre TEXT,
    prix_mad NUMERIC,
    ville TEXT,
    quartier TEXT,
    surface_m2 NUMERIC,
    nb_chambres INTEGER,
    nb_salles_de_bain INTEGER,
    prix_par_m2 NUMERIC,
    scraped_at TIMESTAMP
);