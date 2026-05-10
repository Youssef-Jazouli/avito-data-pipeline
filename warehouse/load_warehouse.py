import logging
import os
import psycopg2

logging.basicConfig(
    filename="logs/warehouse.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        user=os.getenv("DB_USER", "avito_user"),
        password=os.getenv("DB_PASSWORD", "avito_pass"),
        dbname=os.getenv("DB_NAME", "avito_db")
    )

def load_bi(cur):
    cur.execute("SELECT id, titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_salles_de_bain, prix_par_m2, lien, scraped_at FROM clean.ads")
    rows = cur.fetchall()

    for row in rows:
        id_, titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_sdb, prix_par_m2, lien, scraped_at = row

        # dim_location
        cur.execute("""
            INSERT INTO bi_schema.dim_location (ville, quartier)
            VALUES (%s,%s)
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (ville, quartier))
        res = cur.fetchone()
        if not res:
            cur.execute("SELECT id FROM bi_schema.dim_location WHERE ville=%s AND quartier=%s", (ville, quartier))
            res = cur.fetchone()
        loc_id = res[0]

        # dim_features
        cur.execute("""
            INSERT INTO bi_schema.dim_features (surface_m2, nb_chambres, nb_salles_de_bain)
            VALUES (%s,%s,%s)
            RETURNING id
        """, (surface_m2, nb_chambres, nb_sdb))
        feat_id = cur.fetchone()[0]

        # dim_time
        if scraped_at:
            cur.execute("""
                INSERT INTO bi_schema.dim_time (scraped_at, jour, mois, annee, jour_semaine)
                VALUES (%s,%s,%s,%s,%s)
                RETURNING id
            """, (scraped_at, scraped_at.day, scraped_at.month, scraped_at.year,
                  scraped_at.strftime("%A")))
            time_id = cur.fetchone()[0]
        else:
            time_id = None

        # fact_annonce
        cur.execute("""
            INSERT INTO bi_schema.fact_annonce
                (titre, prix_mad, prix_par_m2, lien, dim_location_id, dim_features_id, dim_time_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (titre, prix_mad, prix_par_m2, lien, loc_id, feat_id, time_id))

def load_ml(cur):
    cur.execute("""
        INSERT INTO ml_schema.feature_store
            (titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_salles_de_bain, prix_par_m2, scraped_at)
        SELECT titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_salles_de_bain, prix_par_m2, scraped_at
        FROM clean.ads
        ON CONFLICT DO NOTHING
    """)

def clear_staging(cur):
    cur.execute("TRUNCATE TABLE staging.raw_ads RESTART IDENTITY")
    logging.info("Staging cleared.")

def load():
    conn = get_conn()
    cur = conn.cursor()

    load_bi(cur)
    conn.commit()
    print("BI schema loaded.")

    load_ml(cur)
    conn.commit()
    print("ML schema loaded.")

    clear_staging(cur)
    conn.commit()
    print("Staging cleared.")

    cur.close()
    conn.close()
    logging.info("Warehouse load complete.")

if __name__ == "__main__":
    load()