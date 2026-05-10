# Avito Data Pipeline

A fully automated, Dockerized data pipeline that scrapes Moroccan real-estate listings from **Avito.ma**, stores them in PostgreSQL, and loads cleaned data into a BI-ready star schema and an ML feature store.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Database Schemas](#database-schemas)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Pipeline Steps](#pipeline-steps)
- [Logs](#logs)
- [Data Fields](#data-fields)
- [Tech Stack](#tech-stack)

---

## Overview

This pipeline runs four sequential steps end-to-end:

1. **Scrape** — Crawls up to 40 pages of apartment listings on `avito.ma` using Selenium.
2. **Stage** — Loads raw CSV data as-is into a PostgreSQL staging table.
3. **Clean** — Parses, validates, filters outliers, and loads structured data into a clean schema.
4. **Warehouse** — Populates a star schema for BI dashboards and a flat feature store for ML models.

Each step retries up to 3 times on failure before halting the pipeline.

---

## Architecture

```
avito.ma (website)
      │
      ▼
 [ Scraper ]  ──► data/avito_raw.csv
      │
      ▼
 [ Staging ]  ──► staging.raw_ads         (raw text, deduped by URL)
      │
      ▼
 [ Cleaning ] ──► clean.ads               (parsed, validated, outliers removed)
      │
      ├──► [ BI Warehouse ]
      │         bi_schema.dim_location
      │         bi_schema.dim_features
      │         bi_schema.dim_time
      │         bi_schema.fact_annonce
      │
      └──► [ ML Feature Store ]
                ml_schema.feature_store
```

---

## Project Structure

```
avito-data-pipeline/
├── data/
│   └── avito_raw.csv          # Raw scrape output
├── logs/
│   ├── pipeline.log           # Master pipeline log
│   ├── staging.log            # Staging step log
│   ├── clean.log              # Cleaning step log
│   └── warehouse.log          # Warehouse step log
├── scraper/
│   └── scraper.py             # Selenium-based web scraper
├── staging/
│   └── load_staging.py        # CSV → staging.raw_ads loader
├── clean/
│   └── clean_data.py          # Data parsing, validation, deduplication
├── warehouse/
│   └── load_warehouse.py      # Star schema + ML feature store loader
├── pipeline/
│   └── run_pipeline.py        # Orchestrator with retry logic
├── init.sql                   # PostgreSQL schema initialization
├── Dockerfile                 # Python 3.11 + Chromium image
├── docker-compose.yml         # Multi-service setup (db + pipeline)
└── requirements.txt           # Python dependencies
```

---

## Database Schemas

### `staging.raw_ads` — Raw landing zone

| Column          | Type      | Description                    |
|-----------------|-----------|--------------------------------|
| id              | SERIAL    | Auto-increment PK              |
| titre           | TEXT      | Listing title                  |
| prix            | TEXT      | Raw price string               |
| localisation    | TEXT      | Raw location string            |
| surface         | TEXT      | Raw surface string             |
| chambres        | TEXT      | Raw bedroom count string       |
| salles_de_bain  | TEXT      | Raw bathroom count string      |
| lien            | TEXT      | Listing URL (unique constraint)|
| scraped_at      | TIMESTAMP | Ingestion timestamp            |

### `clean.ads` — Validated & parsed data

| Column              | Type    | Description                    |
|---------------------|---------|--------------------------------|
| id                  | SERIAL  | PK                             |
| titre               | TEXT    | Listing title                  |
| prix_mad            | NUMERIC | Price in MAD                   |
| ville               | TEXT    | City (parsed from localisation)|
| quartier            | TEXT    | District                       |
| surface_m2          | NUMERIC | Area in m²                     |
| nb_chambres         | INTEGER | Number of bedrooms             |
| nb_salles_de_bain   | INTEGER | Number of bathrooms            |
| prix_par_m2         | NUMERIC | Price per m²                   |
| lien                | TEXT    | URL (unique constraint)        |
| scraped_at          | TIMESTAMP | Original scrape timestamp    |

### `bi_schema` — Star schema for BI

- **`dim_location`** — `ville`, `quartier`
- **`dim_features`** — `surface_m2`, `nb_chambres`, `nb_salles_de_bain`
- **`dim_time`** — `scraped_at`, `jour`, `mois`, `annee`, `jour_semaine`
- **`fact_annonce`** — `titre`, `prix_mad`, `prix_par_m2`, `lien` + FK refs to all dimensions

### `ml_schema.feature_store` — Flat table for ML

Contains the same numeric and categorical fields as `clean.ads` in a single flat table, ready for model training.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- No local Python or browser installation needed — everything runs inside containers.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/avito-data-pipeline.git
cd avito-data-pipeline
```

### 2. Configure environment variables

Create a `.env` file at the project root:

```env
DB_USER=avito_user
DB_PASSWORD=avito_pass
DB_NAME=avito_db
```

### 3. Build and run

```bash
docker-compose up --build
```

Docker Compose will:
- Spin up a PostgreSQL 15 container and apply `init.sql`.
- Build the pipeline image (Python 3.11 + Chromium).
- Run the full pipeline once the database is healthy.

### 4. View logs

```bash
# Live pipeline output
docker-compose logs -f pipeline

# Or check log files
cat logs/pipeline.log
```

---

## Configuration

All database credentials are supplied through environment variables. Defaults (for local dev without Docker):

| Variable     | Default       |
|--------------|---------------|
| DB_HOST      | localhost     |
| DB_PORT      | 5432          |
| DB_USER      | avito_user    |
| DB_PASSWORD  | avito_pass    |
| DB_NAME      | avito_db      |

The scraper targets apartments for sale on Avito.ma filtered by:
- Price ≥ 100,000 MAD
- At least 1 bedroom and 1 bathroom
- Surface ≥ 20 m²
- Up to 40 pages (~40 listings/page)

---

## Pipeline Steps

### 1. Scraper (`scraper/scraper.py`)

- Uses **Selenium** with headless Chromium.
- Scrolls each page 3 times to trigger lazy-loaded content.
- Deduplicates listings by URL within a session.
- Extracts: title, price, location, surface, bedrooms, bathrooms, URL.
- Saves results to `data/avito_raw.csv`.

### 2. Staging (`staging/load_staging.py`)

- Reads `avito_raw.csv` and bulk-inserts rows into `staging.raw_ads`.
- Skips duplicate URLs (`ON CONFLICT DO NOTHING`).
- Timestamps every row at insertion time.

### 3. Cleaning (`clean/clean_data.py`)

- Reads all rows from `staging.raw_ads`.
- Parses price (strips non-numeric characters → float MAD).
- Parses surface (regex for numeric value → float m²).
- Parses bedrooms and bathrooms (→ integer).
- Parses location (splits city and district, title-cases both).
- Drops rows where price or surface is missing.
- Drops outliers:
  - Price outside **50,000 – 100,000,000 MAD**
  - Surface outside **10 – 2,000 m²**
- Computes `prix_par_m2 = prix_mad / surface_m2`.
- Inserts into `clean.ads`, skipping duplicates by URL.

### 4. Warehouse (`warehouse/load_warehouse.py`)

- **BI schema**: for each clean ad, upserts dimension records (location, features, time) and inserts a fact row.
- **ML schema**: bulk-inserts all clean ads into `ml_schema.feature_store` as a flat table.
- **Truncates** `staging.raw_ads` after a successful warehouse load.

### Orchestrator (`pipeline/run_pipeline.py`)

- Runs steps in order: Scrape → Stage → Clean → Warehouse.
- Each step has **3 automatic retries** with a 5-second delay between attempts.
- Logs to both `logs/pipeline.log` and stdout (visible via `docker-compose logs`).
- Exits with code `1` on unrecoverable failure.

---

## Logs

| File                  | Contents                              |
|-----------------------|---------------------------------------|
| `logs/pipeline.log`   | Master log — all steps, retry events |
| `logs/staging.log`    | Rows inserted / skipped in staging    |
| `logs/clean.log`      | Rows inserted / skipped after cleaning|
| `logs/warehouse.log`  | BI and ML load completion             |
| `logs/avito_scraper.log` | Per-page scraping progress         |

Logs are mounted as a Docker volume (`./logs:/app/logs`) so they persist on the host.

---

## Data Fields

Fields scraped from each listing:

| Field           | Description                        |
|-----------------|------------------------------------|
| titre           | Listing headline                   |
| prix            | Advertised price (string)          |
| localisation    | City / district text               |
| surface         | Area string (e.g. "85 m²")         |
| chambres        | Bedroom count string               |
| salles_de_bain  | Bathroom count string              |
| lien            | Full URL of the listing            |

---

## Tech Stack

| Component     | Technology                        |
|---------------|-----------------------------------|
| Scraping      | Python 3.11, Selenium 4, Chromium |
| Database      | PostgreSQL 15                     |
| DB Driver     | psycopg2-binary                   |
| Data          | pandas, numpy                     |
| Config        | python-dotenv                     |
| Containerization | Docker, Docker Compose         |