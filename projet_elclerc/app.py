from utiles import LeclercScraper, DBManager

def pipeline(max_pages: int = 5):
    db = DBManager()
    scraper = LeclercScraper(headless=False)

    try:
        scraper.open_homepage()
        scraper.go_to_bons_plans()

        page_count = 0
        while page_count < max_pages:
            deals = scraper.scrape_current_page()
            db.save_many(deals)
            print(f"[INFO] page {page_count+1}: {len(deals)} produits insérés")

            page_count += 1
            moved = scraper.go_next_page()
            if not moved:
                break

        print("[INFO] pipeline terminé normalement")

    except Exception as e:
        print("[ERROR] pipeline interrompu:", repr(e))

    finally:
        scraper.close()
        print("[DONE] Fin du scraping.")

if __name__ == "__main__":
    pipeline(max_pages=5)
