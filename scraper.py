from datetime import datetime
import json
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://monipad.dipendajatim.go.id/monipad/index.php/login"
DASHBOARD_URL = "https://monipad.dipendajatim.go.id/monipad/index.php/"

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
    print("1. Membuka halaman login...")
    driver.get(LOGIN_URL)
    time.sleep(3)

    print("2. Mengisi form login...")
    driver.find_element(By.ID, "login_user").send_keys(USERNAME)
    driver.find_element(By.ID, "login_pass").send_keys(PASSWORD)
    driver.find_element(By.ID, "login_pass").send_keys(Keys.RETURN)
    time.sleep(6)

    print("3. Membuka halaman dashboard...")
    driver.get(DASHBOARD_URL)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    def get_text_safe(selector):
      try:
        el = soup.select_one(selector)
        return el.text.strip() if el else "0"
      except Exception:
        return "0"

    # MENARIK SEMUA DATA SEKALIGUS DARI HALAMAN MONIPAD (Badan & UPT)
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Menu Monipad UPT
        "upt_hari_ini": get_text_safe("#uptHariIni div[class*='inner']"),
        "upt_sd_hari_ini": get_text_safe("#uptSdHariIni div[class*='inner']"),
        "upt_hit_target": get_text_safe("#hitTarget div div:nth-of-type(2)"),
        "upt_pen_target": get_text_safe("#penTarget div div:nth-of-type(2)"),
        "upt_pen_total": get_text_safe("#penTotal div div:nth-of-type(2)"),
        "upt_pen_jenis": get_text_safe("#penJenis div div:nth-of-type(2)"),
        "upt_pen_periode": get_text_safe(
            "#penTanggalPeriode div div:nth-of-type(2)"
        ),
        # Menu Monipad Badan (Tambahkan selector jika diperlukan)
        "badan_pen_total": get_text_safe("#penTotal div div:nth-of-type(2)"),
        "badan_pen_jenis": get_text_safe("#penJenis div div:nth-of-type(2)"),
        "badan_pen_target": get_text_safe("#penTarget div"),
    }

    print("SUKSES! Semua data berhasil ditarik:", new_data)
    return new_data

  except Exception as e:
    print(f"GAGAL SAAT SCRAPING: {str(e)}")
    return None
  finally:
    driver.quit()


def main():
  current_data = scrape_data()
  if not current_data:
    return

  old_history = {"current": {}, "logs": []}
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        old_history = json.load(f)
    except Exception:
      pass

  old_vals = old_history.get("current", {})
  logs = old_history.get("logs", [])

  # Deteksi perubahan untuk log notifikasi (contoh pada upt_pen_total)
  if "upt_pen_total" in old_vals and "upt_pen_total" in current_data:
    try:
      clean_old = float(
          old_vals["upt_pen_total"]
          .replace("Rp", "")
          .replace(".", "")
          .replace(",", ".")
          .strip()
          or 0
      )
      clean_new = float(
          current_data["upt_pen_total"]
          .replace("Rp", "")
          .replace(".", "")
          .replace(",", ".")
          .strip()
          or 0
      )

      diff = clean_new - clean_old
      if diff != 0:
        pesan = (
            f"Pendapatan UPT bertambah Rp {diff:,.0f}"
            if diff > 0
            else f"Pendapatan UPT berkurang Rp {abs(diff):,.0f}"
        )
        logs.insert(0, {"time": current_data["timestamp"], "message": pesan})
    except Exception:
      pass

  final_data = {"current": current_data, "logs": logs[:50]}

  with open(DATA_FILE, "w") as f:
    json.dump(final_data, f, indent=4)
  print("File data.json berhasil diperbarui!")


if __name__ == "__main__":
  main()
