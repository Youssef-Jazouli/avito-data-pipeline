import logging
import os
import re
import psycopg2

logging.basicConfig(
    filename="logs/clean.log",
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

def parse_price(prix_str):
    if not prix_str:
        return None
    digits = re.sub(r"[^\d]", "", prix_str)
    return float(digits) if digits else None

def parse_surface(s):
    if not s:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", s.replace(",", "."))
    return float(m.group(1)) if m else None

def parse_int(s):
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None

def parse_location(loc):
    ville, quartier = "", ""
    if not loc:
        return ville, quartier
    loc = re.sub(r"dans\s+", "", loc, flags=re.IGNORECASE).strip()
    # Remove "Appartements " prefix
    loc = re.sub(r"^appartements\s+", "", loc, flags=re.IGNORECASE).strip()
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        ville, quartier = parts[0], parts[1]
    elif len(parts) == 1:
        ville = parts[0]
    return ville.title(), quartier.title()

def clean():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, titre, prix, localisation, surface, chambres, salles_de_bain, lien, scraped_at FROM staging.raw_ads")
    rows = cur.fetchall()

    inserted = 0
    skipped = 0

    for row in rows:
        id_, titre, prix, localisation, surface, chambres, sdb, lien, scraped_at = row

        prix_mad = parse_price(prix)
        surface_m2 = parse_surface(surface)
        nb_chambres = parse_int(chambres)
        nb_sdb = parse_int(sdb)
        ville, quartier = parse_location(localisation)

        # Drop rows missing critical fields
        if not prix_mad or not surface_m2:
            skipped += 1
            continue

        # Outlier filter
        if prix_mad < 50000 or prix_mad > 100_000_000:
            skipped += 1
            continue
        if surface_m2 < 10 or surface_m2 > 2000:
            skipped += 1
            continue

        prix_par_m2 = round(prix_mad / surface_m2, 2)

        try:
            cur.execute("""
                INSERT INTO clean.ads
                    (titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_salles_de_bain, prix_par_m2, lien, scraped_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (lien) DO NOTHING
            """, (titre, prix_mad, ville, quartier, surface_m2, nb_chambres, nb_sdb, prix_par_m2, lien, scraped_at))
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            logging.warning(f"Insert error: {e}")
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()
    logging.info(f"Clean: {inserted} inserted, {skipped} skipped")
    print(f"Clean done: {inserted} inserted, {skipped} skipped")

if __name__ == "__main__":
    clean()