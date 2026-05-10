import csv
import logging
import os
import psycopg2
from datetime import datetime

logging.basicConfig(
    filename="logs/staging.log",
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

def load():
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    with open("data/avito_raw.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cur.execute("""
                    INSERT INTO staging.raw_ads
                        (titre, prix, localisation, surface, chambres, salles_de_bain, lien, scraped_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (lien) DO NOTHING
                """, (
                    row["titre"], row["prix"], row["localisation"],
                    row["surface"], row["chambres"], row["salles_de_bain"],
                    row["lien"], datetime.now()
                ))
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                logging.warning(f"Row skipped: {e}")

    conn.commit()
    cur.close()
    conn.close()
    logging.info(f"Staging: {inserted} inserted, {skipped} skipped")
    print(f"Staging done: {inserted} inserted, {skipped} skipped")

if __name__ == "__main__":
    load()