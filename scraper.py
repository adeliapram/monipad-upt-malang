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

    print("2. Mencari kotak input username & password...")
    user_input = driver.find_element(By.ID, "login_user")
    pass_input = driver.find_element(By.ID, "login_pass")

    print("3. Mengisi kredensial dan menekan Enter...")
    user_input.send_keys(USERNAME)
    pass_input.send_keys(PASSWORD)
    pass_input.send_keys(Keys.RETURN)  # Menekan tombol Enter untuk login

    print("4. Menunggu proses login selesai...")
    time.sleep(6)

    print("5. Berpindah ke halaman dashboard...")
    driver.get(DASHBOARD_URL)
    time.sleep(5)

    print("6. Mengambil data halaman...")
    soup = BeautifulSoup(driver.page_source, "html.parser")

    def get_text_safe(selector):
      try:
        el = soup.select_one(selector)
        return el.text.strip() if el else "0"
      except Exception:
        return "0"

    new_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "upt_hari_ini": get_text_safe("#uptHariIni div:nth-of-type(2)"),
        "upt_sd_hari_ini": get_text_safe("#uptSdHariIni div:nth-of-type(2)"),
        "pen_total": get_text_safe("#penTotal div div:nth-of-type(2)"),
    }

    print("SUKSES! Data ditarik:", new_data)
    return new_data

  except Exception as e:
    print(f"GAGAL PADA STEP: {str(e)}")
    return None
  finally:
    driver.quit()


def main():
  current_data = scrape_data()
  if not current_data:
    print("Data kosong, file data.json diabaikan.")
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

  final_data = {"current": current_data, "logs": logs[:50]}

  with open(DATA_FILE, "w") as f:
    json.dump(final_data, f, indent=4)
  print("File data.json berhasil diperbarui!")


if __name__ == "__main__":
  main()
