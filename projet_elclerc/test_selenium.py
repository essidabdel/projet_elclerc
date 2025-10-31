from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("[DEBUG] lancement...")

opts = Options()

opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--start-maximized")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)

print("[DEBUG] driver ok, j'ouvre google")
driver.get("https://www.google.com")
input("Appuie Entrée pour fermer...")
driver.quit()
