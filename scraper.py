from datetime import datetime
import json
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://monipad.dipendajatim.go.id/monipad/"
DASHBOARD_URL = "https://monipad.dipendajatim.go.id/monipad/index.php/"

# Mengambil kredensial dari GitHub Secrets (Aman!)
USERNAME = os.environ.get("MONIPAD_USER")
PASSWORD = os.environ.get("MONIPAD_PASS")

DATA_FILE = "data.json"


def scrape_data():
  options = Options()
  options.add_argument("--headless")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--window-size=1920,1080")

  driver = webdriver.Chrome(
      service=Service(ChromeDriverManager().install()), options=options
  )

  try:
    driver.get(LOGIN_URL)
    time.sleep(3)

    # Sesuaikan name input form login MONIPAD Anda
    driver.find_element(By.NAME, "username").send_keys(USERNAME)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.TAG_NAME, "button").click()
    time.sleep(4)

    driver.get(DASHBOARD_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    def get_text_safe(selector):
      el = soup.select_one(selector)
      return el.text.strip() if el else "0"

    # Ekstraksi berdasarkan elemen XPath / ID yang Anda berikan
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "upt_hari_ini": get_text_safe("#uptHariIni div:nth-of-type(2)"),
        "upt_sd_hari_ini": get_text_safe("#uptSdHariIni div:nth-of-type(2)"),
        "pen_total": get_text_safe("#penTotal div div:nth-of-type(2)"),
        "pen_jenis": get_text_safe("#penJenis div div:nth-of-type(2)"),
    }
    return new_data
  except Exception as e:
    print(f"Error scraping: {e}")
    return None
  finally:
    driver.quit()


def main():
  current_data = scrape_data()
  if not current_data:
    return

  # Load data lama untuk perbandingan (Diff) & Log
  old_history = {"current": {}, "logs": []}
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
      old_history = json.load(f)

  old_vals = old_history.get("current", {})
  logs = old_history.get("logs", [])

  # Deteksi Perubahan (Contoh untuk pen_total)
  if "pen_total" in old_vals and "pen_total" in current_data:
    try:
      clean_old = float(
          old_vals["pen_total"]
          .replace("Rp", "")
          .replace(".", "")
          .replace(",", ".")
          .strip()
          or 0
      )
      clean_new = float(
          current_data["pen_total"]
          .replace("Rp", "")
          .replace(".", "")
          .replace(",", ".")
          .strip()
          or 0
      )

      diff = clean_new - clean_old
      if diff != 0:
        pesan = (
            f"Pendapatan Total bertambah Rp {diff:,.0f}"
            if diff > 0
            else f"Pendapatan Total berkurang Rp {abs(diff):,.0f}"
        )
        logs.insert(0, {"time": current_data["timestamp"], "message": pesan})
    except Exception:
      pass

  # Simpan struktur data baru
  final_data = {"current": current_data, "logs": logs[:50]}  # Simpan 50 log terbaru

  with open(DATA_FILE, "w") as f:
    json.dump(final_data, f, indent=4)


if __name__ == "__main__":
  main()
