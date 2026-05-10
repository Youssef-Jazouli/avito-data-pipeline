import time
import csv
import logging
import os

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    filename="logs/avito_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def main():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    url = (
        "https://www.avito.ma/fr/maroc/appartements-%C3%A0_vendre"
        "?price=100000-&rooms=1&bathrooms=1&has_price=true&size=20-"
    )

    driver.get(url)

    results = []
    seen_links = set()

    for page in range(40):
        logging.info(f"Scraping page {page + 1}")

        for _ in range(3):
            driver.execute_script("window.scrollBy(0,1000);")
            time.sleep(1)

        cards = driver.find_elements(By.XPATH, "//a[contains(@href,'/appartements/')]")
        page_ads_count = 0

        for card in cards:
            try:
                lien = card.get_attribute("href")
                if not lien or lien in seen_links:
                    continue
                seen_links.add(lien)

                try:
                    titre = card.find_element(By.XPATH, ".//p[@title]").text
                except:
                    titre = card.text.split("\n")[0]

                try:
                    localisation = card.find_element(
                        By.XPATH, ".//p[contains(text(),'dans')]"
                    ).text
                except:
                    localisation = ""

                try:
                    prix = card.find_element(
                        By.XPATH, ".//span[contains(@class,'3286ebc5-2')]"
                    ).text
                except:
                    prix = ""

                surface = chambres = salles_de_bain = ""
                for line in card.text.lower().split("\n"):
                    if "m²" in line:
                        surface = line
                    elif "chambre" in line:
                        chambres = line
                    elif "sdb" in line or "bain" in line:
                        salles_de_bain = line

                results.append({
                    "titre": titre,
                    "prix": prix,
                    "localisation": localisation,
                    "surface": surface,
                    "chambres": chambres,
                    "salles_de_bain": salles_de_bain,
                    "lien": lien
                })
                page_ads_count += 1

            except Exception as e:
                error_msg = str(e).split('\n')[0]
                logging.warning(f"Error on page {page+1}: {error_msg}")
                if "invalid session id" in error_msg:
                    logging.error("Browser session lost.")
                    break

        logging.info(f"Page {page + 1}: {page_ads_count} ads extracted.")

        try:
            next_btn = driver.find_elements(By.XPATH, "//a[contains(@href,'?o=')]")[-1]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
            next_btn.click()
            time.sleep(3)
        except:
            logging.info("Last page reached")
            break

    driver.quit()

    if results:
        with open("data/avito_raw.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["titre","prix","localisation","surface","chambres","salles_de_bain","lien"])
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Scraping done. Total: {len(results)} rows")
        print(f"Scraping done: {len(results)} rows")
    else:
        logging.warning("No data collected.")
        print("No data collected")