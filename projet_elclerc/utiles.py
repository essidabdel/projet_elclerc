import sqlite3
import time
import re
from datetime import datetime
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ---------- XPATHS ----------
XPATH_COOKIES_ACCEPT = "//button[contains(., 'Accepter') or contains(., 'accepter') or contains(., 'J’accepte') or contains(., \"J'accepte\")]"
XPATH_MENU_BUTTON = "/html/body/app-root/ng-sidebar-container/div/div/app-navbar/div[1]/nav/app-navbar-menu-button/div"
XPATH_BONS_PLANS_BUTTON = "/html/body/app-root/ng-sidebar-container/ng-sidebar/aside/app-sidenav/div/div[1]/div[2]/div/div/div/div/div[2]/app-sidenav-sections/ul[1]/li[2]/a"

XPATH_ALL_PRODUCT_LIST = "/html/body/app-root/ng-sidebar-container/div/div/div[2]/app-template-details/div[2]/div[4]/div/div[2]/app-template-result-list/ul"
XPATH_ALL_PRODUCT_CARDS = XPATH_ALL_PRODUCT_LIST + "/li"

XPATH_PRODUCT_NAME_IN_CARD = ".//app-product-card-label/div/a"
XPATH_SOLD_BY_IN_CARD = ".//app-product-card-seller/p/span"
XPATH_SOLD_BY_BLOCK_IN_CARD = ".//app-product-card-seller"
XPATH_PROMO_BLOCK_IN_CARD = ".//app-product-promo/div/div"
XPATH_PRICE_INTEGER_PART = ".//app-product-price//div[@id='price']//div[contains(@class,'price-unit')]"
XPATH_PRICE_CENTS_PART   = ".//app-product-price//div[@id='price']//span[contains(@class,'price-cents')]"
XPATH_IMAGE_IN_CARD = ".//app-lazy-image/img"
XPATH_PAGE_LINK_IN_CARD = ".//a[@href][1]"

XPATH_NEXT_LI = "//li[contains(@class,'pagination-next')]"
XPATH_NEXT_BUTTON = XPATH_NEXT_LI + "/a"

# Fiche produit
XPATH_PRODUCT_DESCRIPTION = "/html/body/main/div/div/div[3]/section[1]/div"
XPATH_FEATURES_TBODY = "/html/body/main/div/div/div[3]/section[2]/div[1]/table/tbody"
XPATH_CATEGORY_IN_TABLE = "/html/body/main/div/div/div[3]/section[2]/div[1]/table/tbody/tr[14]/td"  # selon ton exemple


# ---------- DB ----------
class DBManager:
    def __init__(self, db_path: str = "leclerc_deals.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leclerc_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sold_by TEXT,
                product_name TEXT,
                discount_text TEXT,
                price_eur REAL,
                page_url TEXT,
                image_url TEXT,
                description TEXT,
                features TEXT,
                category TEXT,
                scraped_at TEXT
            );
        """)
        con.commit()
        con.close()

    def save_many(self, deals: List[Dict]):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        for d in deals:
            try:
                cur.execute("""
                    INSERT INTO leclerc_deals
                    (sold_by, product_name, discount_text, price_eur, page_url, image_url,
                     description, features, category, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.get("sold_by"),
                    d.get("product_name"),
                    d.get("discount_text"),
                    d.get("price_eur"),
                    d.get("page_url"),
                    d.get("image_url"),
                    d.get("description"),
                    d.get("features"),
                    d.get("category"),
                    d.get("scraped_at"),
                ))
            except sqlite3.DatabaseError:
                continue
        con.commit()
        con.close()


# ---------- SCRAPER ----------
class LeclercScraper:
    def __init__(self, headless: bool = False):
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--start-maximized")
        opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/128.0.0.0 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, 10)

    # --- navigation ---
    def open_homepage(self):
        self.driver.get("https://www.e.leclerc/")
        self._accept_cookies_if_present()
        self.wait.until(EC.presence_of_element_located((By.XPATH, XPATH_MENU_BUTTON)))

    def _accept_cookies_if_present(self):
        try:
            btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_COOKIES_ACCEPT)))
            btn.click()
            time.sleep(0.5)
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
            pass

    def go_to_bons_plans(self):
        self.driver.find_element(By.XPATH, XPATH_MENU_BUTTON).click()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BONS_PLANS_BUTTON))).click()
        self.wait.until(EC.presence_of_element_located((By.XPATH, XPATH_ALL_PRODUCT_LIST)))
        self.wait.until(EC.presence_of_all_elements_located((By.XPATH, XPATH_ALL_PRODUCT_CARDS)))

    # --- page listing ---
    def scrape_current_page(self) -> List[Dict]:
        cards = self.driver.find_elements(By.XPATH, XPATH_ALL_PRODUCT_CARDS)
        deals = []
        for card in cards:
            try:
                data = self._extract_card_data(card)
                details = self._fetch_details(data.get("page_url"))
                data.update(details)
                data["scraped_at"] = datetime.utcnow().isoformat()
                deals.append(data)
            except Exception:
                continue
        return deals

    # --- extract helpers ---
    def _clean_sold_by(self, txt: str) -> Optional[str]:
        if not txt:
            return None
        line = txt.strip().splitlines()[0].strip()
        line = re.sub(r"^\s*vendu(\s+et\s+expédié)?\s+par\s*:?\s*", "", line, flags=re.IGNORECASE)
        line = line.strip(" :-\u00A0").strip()
        return line or None

    def _extract_sold_by(self, card) -> Optional[str]:
        try:
            txt = card.find_element(By.XPATH, XPATH_SOLD_BY_IN_CARD).text
            cleaned = self._clean_sold_by(txt)
            if cleaned:
                return cleaned
        except NoSuchElementException:
            pass
        try:
            txt2 = card.find_element(By.XPATH, XPATH_SOLD_BY_BLOCK_IN_CARD).text
            return self._clean_sold_by(txt2)
        except NoSuchElementException:
            return None

    def _extract_card_data(self, card) -> Dict:
        try:
            product_name = card.find_element(By.XPATH, XPATH_PRODUCT_NAME_IN_CARD).text.strip()
        except NoSuchElementException:
            product_name = None

        sold_by = self._extract_sold_by(card)
        discount_text = self._extract_promo(card)
        price_eur = self._extract_price(card)

        try:
            img = card.find_element(By.XPATH, XPATH_IMAGE_IN_CARD)
            image_url = img.get_attribute("data-src") or img.get_attribute("src")
        except NoSuchElementException:
            image_url = None

        page_url = None
        try:
            a = card.find_element(By.XPATH, XPATH_PAGE_LINK_IN_CARD)
            href = a.get_attribute("href")
            if href and not href.strip().lower().startswith("javascript"):
                page_url = href
        except NoSuchElementException:
            page_url = None

        return {
            "sold_by": sold_by,
            "product_name": product_name,
            "discount_text": discount_text,
            "price_eur": price_eur,
            "page_url": page_url,
            "image_url": image_url,
            "description": None,
            "features": None,
            "category": None,
        }

    def _extract_promo(self, card) -> Optional[str]:
        try:
            raw = card.find_element(By.XPATH, XPATH_PROMO_BLOCK_IN_CARD).text.strip()
            cleaned = " ".join(raw.split())
            return cleaned or None
        except NoSuchElementException:
            return None

    def _extract_price(self, card) -> Optional[float]:
        try:
            euros_txt = card.find_element(By.XPATH, XPATH_PRICE_INTEGER_PART).text.strip()
        except NoSuchElementException:
            euros_txt = ""
        try:
            cents_txt = card.find_element(By.XPATH, XPATH_PRICE_CENTS_PART).text.strip()
        except NoSuchElementException:
            cents_txt = ""
        euros_txt = euros_txt.replace("€", "").replace(" ", "")
        cents_txt = cents_txt.replace("€", "").replace(" ", "")
        if cents_txt.startswith(","): cents_txt = cents_txt[1:]
        if cents_txt == "": cents_txt = "00"
        if euros_txt == "": return None
        try:
            return float(f"{euros_txt}.{cents_txt}")
        except ValueError:
            return None

    # --- fiche produit ---
    def _fetch_details(self, page_url: Optional[str]) -> Dict[str, Optional[str]]:
        if not page_url:
            return {"description": None, "features": None, "category": None}

        main = self.driver.current_window_handle
        try:
            self.driver.switch_to.new_window('tab')
            self.driver.get(page_url)

            # description
            description = None
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, XPATH_PRODUCT_DESCRIPTION)))
                description = self.driver.find_element(By.XPATH, XPATH_PRODUCT_DESCRIPTION).text.strip() or None
            except TimeoutException:
                description = None

            # caractéristiques (table <tbody> ; concat "Label: valeur")
            features = self._extract_features_table()

            # catégorie (cellule précise fournie) + fallback par libellé "Catégorie"
            category = self._extract_category_from_table_specific() or self._extract_category_from_table_by_label()

            return {"description": description, "features": features, "category": category}
        except WebDriverException:
            return {"description": None, "features": None, "category": None}
        finally:
            try:
                self.driver.close()
                self.driver.switch_to.window(main)
            except Exception:
                pass

    def _extract_features_table(self) -> Optional[str]:
        """Parcourt le tbody et retourne 'Label: Valeur' séparés par ' | '."""
        try:
            tbody = self.driver.find_element(By.XPATH, XPATH_FEATURES_TBODY)
            rows = tbody.find_elements(By.XPATH, "./tr")
            pairs = []
            for tr in rows:
                try:
                    key = tr.find_element(By.XPATH, "./th").text.strip()
                    val = tr.find_element(By.XPATH, "./td").text.strip()
                    if key or val:
                        pairs.append(f"{key}: {val}".strip(": ").strip())
                except NoSuchElementException:
                    continue
            return " | ".join(pairs) if pairs else None
        except NoSuchElementException:
            return None

    def _extract_category_from_table_specific(self) -> Optional[str]:
        """Catégorie via la cellule exacte transmise (/tr[14]/td)."""
        try:
            val = self.driver.find_element(By.XPATH, XPATH_CATEGORY_IN_TABLE).text.strip()
            return val or None
        except NoSuchElementException:
            return None

    def _extract_category_from_table_by_label(self) -> Optional[str]:
        """Fallback: cherche une ligne dont le <th> contient 'Catégorie'/'Catégories'."""
        try:
            tbody = self.driver.find_element(By.XPATH, XPATH_FEATURES_TBODY)
            rows = tbody.find_elements(By.XPATH, "./tr")
            for tr in rows:
                try:
                    key = tr.find_element(By.XPATH, "./th").text.strip().lower()
                    if "catégori" in key:  # couvre 'Catégorie', 'Catégories'
                        val = tr.find_element(By.XPATH, "./td").text.strip()
                        if val:
                            return val
                except NoSuchElementException:
                    continue
            return None
        except NoSuchElementException:
            return None

    # --- pagination ---
    def go_next_page(self) -> bool:
        try:
            first_before = self.driver.find_element(By.XPATH, XPATH_ALL_PRODUCT_CARDS + "[1]").text[:60]
        except NoSuchElementException:
            first_before = ""

        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)

        try:
            next_li = self.driver.find_element(By.XPATH, XPATH_NEXT_LI)
        except NoSuchElementException:
            return False

        li_class = (next_li.get_attribute("class") or "").lower()
        if "disabled" in li_class:
            return False

        try:
            next_a = next_li.find_element(By.XPATH, "./a")
        except NoSuchElementException:
            return False

        self.driver.execute_script("arguments[0].scrollIntoView()", next_a)
        time.sleep(0.2)
        self.driver.execute_script("arguments[0].click()", next_a)

        try:
            WebDriverWait(self.driver, 12).until(
                lambda d: d.find_element(By.XPATH, XPATH_ALL_PRODUCT_CARDS + "[1]").text[:60] != first_before
            )
        except TimeoutException:
            return False

        try:
            self.wait.until(EC.presence_of_all_elements_located((By.XPATH, XPATH_ALL_PRODUCT_CARDS)))
        except TimeoutException:
            return False

        return True

    def close(self):
        self.driver.quit()
