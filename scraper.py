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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "https://monipad.dipendajatim.go.id/monipad/"
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
    print("1. Membuka halaman utama login...")
    driver.get(LOGIN_URL)

    print("2. Menunggu form login muncul...")
    wait = WebDriverWait(driver, 15)
    user_input = wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="login_user"]'))
    )
    pass_input = driver.find_element(By.XPATH, '//*[@id="login_pass"]')

    print("3. Mengisi kredensial...")
    user_input.send_keys(USERNAME)
    pass_input.send_keys(PASSWORD)
    pass_input.send_keys(Keys.RETURN)

    print("4. Menunggu proses login selesai...")
    time.sleep(7)

    print("5. Membuka halaman dashboard...")
    driver.get(DASHBOARD_URL)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    def get_text_safe(selector):
      try:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else "0"
      except Exception:
        return "0"

    # Menarik data persis berdasarkan ID dari struktur HTML Monipad
    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # Kartu 1: Total S/D Hari Ini
        "pro_sdhari_ini": get_text_safe("#pro_sdhari_ini"),
        "jml_target": get_text_safe("#jml_target"),
        "jml_sdhari_ini": get_text_safe("#jml_sdhari_ini"),
        "jml_hari_ini": get_text_safe("#jml_hari_ini"),
        "jml_kurang": get_text_safe("#jml_kurang"),
        "jml_target_non": get_text_safe("#jml_target_non"),
        "jml_sdhari_ini_non": get_text_safe("#jml_sdhari_ini_non"),
        "jml_hari_kerja": get_text_safe("#jml_hari_kerja"),
        # Kartu 2: Per Jenis Penerimaan S/D Hari Ini (Persentase & Nominal)
        "pro_pkb": get_text_safe("#pro_pkb"),
        "prg_pkb": get_text_safe("#prg_pkb"),
        "pro_bbn": get_text_safe("#pro_bbn"),
        "prg_bbn": get_text_safe("#prg_bbn"),
        "pro_pbb": get_text_safe("#pro_pbb"),
        "prg_pbb": get_text_safe("#prg_pbb"),
        "pro_pap": get_text_safe("#pro_pap"),
        "prg_pap": get_text_safe("#prg_pap"),
        "pro_prk": get_text_safe("#pro_prk"),
        "prg_prk": get_text_safe("#prg_prk"),
        "pro_rju": get_text_safe("#pro_rju"),
        "prg_rju": get_text_safe("#prg_rju"),
        "pro_pll": get_text_safe("#pro_pll"),
        "prg_pll": get_text_safe("#prg_pll"),
        "pro_mblb": get_text_safe("#pro_mblb"),
        "prg_mblb": get_text_safe("#prg_mblb"),
    }

    print("SUKSES! Data berhasil ditarik:", new_data)
    return new_data

  except Exception as e:
    print(f"GAGAL SAAT SCRAPING: {str(e)}")
    return None
  finally:
    driver.quit()


def main():
  current_data = scrape_data()
  if not current_data:
    print("Gagal mengambil data dari web.")
    return

  # Load data lama dengan pengamanan ekstra agar tidak NoneType error
  old_history = {"current": {}, "logs": []}
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        content = f.read()
        if content.strip():
          old_history = json.loads(content)
          if not isinstance(old_history, dict):
            old_history = {"current": {}, "logs": []}
    except Exception:
      old_history = {"current": {}, "logs": []}

  old_vals = old_history.get("current")
  if not isinstance(old_vals, dict):
    old_vals = {}

  logs = old_history.get("logs")
  if not isinstance(logs, list):
    logs = []

  # Deteksi perubahan untuk log notifikasi
  if "upt_pen_total" in old_vals and "upt_pen_total" in current_data:
    try:
      clean_old = float(
          str(old_vals["upt_pen_total"])
          .replace("Rp", "")
          .replace(".", "")
          .replace(",", ".")
          .strip()
          or 0
      )
      clean_new = float(
          str(current_data["upt_pen_total"])
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
  print("File data.json berhasil diperbarui dengan aman!")


if __name__ == "__main__":
  main()
