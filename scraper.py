from datetime import datetime
import json
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
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
    print("Membuka halaman login...")
    driver.get(LOGIN_URL)

    # Tunggu maksimal 10 detik sampai elemen input 'login_user' benar-benar muncul di layar
    print("Menunggu elemen form login siap...")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(
        EC.presence_of_element_located((By.ID, "login_user"))
    )
    password_field = driver.find_element(By.ID, "login_pass")

    print("Mengisi form login...")
    username_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD)

    # Cari dan klik tombol login
    print("Mengklik tombol login...")
    try:
      submit_btn = wait.until(
          EC.element_to_be_clickable(
              (
                  By.XPATH,
                  '//button[@type="submit"] | //input[@type="submit"] |'
                  ' //button',
              )
          )
      )
      submit_btn.click()
    except Exception:
      # Fallback klik via javascript jika tombol tertutup elemen lain
      submit_btn = driver.find_element(By.TAG_NAME, "button")
      driver.execute_script("arguments[0].click();", submit_btn)

    print("Menunggu proses login & masuk ke dashboard...")
    time.sleep(5)

    # Masuk ke halaman dashboard
    driver.get(DASHBOARD_URL)
    time.sleep(5)

    print("URL saat ini:", driver.current_url)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    def get_text_safe(selector):
      try:
        el = soup.select_one(selector)
        return el.text.strip() if el else "0"
      except Exception:
        return "0"

    # Mengambil data sesuai elemen XPath / ID yang Anda berikan
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "upt_hari_ini": get_text_safe("#uptHariIni div:nth-of-type(2)"),
        "upt_sd_hari_ini": get_text_safe("#uptSdHariIni div:nth-of-type(2)"),
        "pen_total": get_text_safe("#penTotal div div:nth-of-type(2)"),
    }

    print("Data yang berhasil diekstrak:", new_data)
    return new_data

  except Exception as e:
    print(f"Terjadi error saat scraping: {e}")
    return None
  finally:
    driver.quit()


def main():
  current_data = scrape_data()
  if not current_data or current_data.get("upt_hari_ini") == "0":
    print("Peringatan: Data kosong atau gagal ditarik.")

  # Load data lama jika ada
  old_history = {"current": {}, "logs": []}
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        old_history = json.load(f)
    except Exception:
      pass

  old_vals = old_history.get("current", {})
  logs = old_history.get("logs", [])

  # Cek perubahan untuk log notifikasi
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

  # Simpan ke data.json
  final_data = {"current": current_data, "logs": logs[:50]}

  with open(DATA_FILE, "w") as f:
    json.dump(final_data, f, indent=4)
  print("File data.json berhasil disimpan!")


if __name__ == "__main__":
  main()
