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
# Contoh endpoint API untuk data total yang Anda temukan di Network Inspect
API_URL = "https://monipad.dipendajatim.go.id/monipad/index.php/main/getDataTotal" # Sesuaikan endpoint utamanya

USERNAME = os.environ.get("MONIPAD_USER")
PASSWORD = os.environ.get("MONIPAD_PASS")

DATA_FILE = "data.json"

def scrape_data():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print("1. Membuka halaman login...")
        driver.get(LOGIN_URL)

        print("2. Menunggu form login muncul...")
        wait = WebDriverWait(driver, 15)
        user_input = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="login_user"]')))
        pass_input = driver.find_element(By.XPATH, '//*[@id="login_pass"]')

        print("3. Mengisi kredensial...")
        user_input.send_keys(USERNAME)
        pass_input.send_keys(PASSWORD)
        pass_input.send_keys(Keys.RETURN)

        print("4. Menunggu proses login selesai...")
        time.sleep(7)

        print("5. Mengambil data langsung dari Endpoint API...")
        driver.get("https://monipad.dipendajatim.go.id/monipad/index.php/main/getDataTotal")
        time.sleep(3)
        
        # Mengambil elemen pre atau body untuk memastikan bersih dari tag HTML
        body_element = driver.find_element(By.TAG_NAME, "body")
        raw_text = body_element.text.strip()
        
        # Jika teks terbungkus tag HTML pre, ambil teks dalamnya
        try:
            pre_element = driver.find_element(By.TAG_NAME, "pre")
            if pre_element:
                raw_text = pre_element.text.strip()
        except:
            pass

        print(f"DEBUG MENTAH API: {raw_text[:100]}...") # Cek isi data di log GitHub
        api_json = json.loads(raw_text)

    except Exception as e:
        print(f"GAGAL SAAT MENGAMBIL API: {str(e)}")
        return None
    finally:
        driver.quit()

def main():
    current_data = scrape_data()
    if not current_data:
        print("Gagal total mendapatkan data.")
        return

    old_history = {"current": {}, "logs": []}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                content = f.read()
                if content.strip():
                    old_history = json.loads(content)
        except Exception:
            pass

    old_vals = old_history.get("current", {})
    logs = old_history.get("logs", [])

    # Deteksi perubahan untuk log notifikasi
    if "jml_sdhari_ini" in old_vals and "jml_sdhari_ini" in current_data:
        try:
            clean_old = float(str(old_vals["jml_sdhari_ini"]).replace(".", "").replace(",", ".").replace("Rp", "").strip() or 0)
            clean_new = float(str(current_data["jml_sdhari_ini"]).replace(".", "").replace(",", ".").replace("Rp", "").strip() or 0)
            
            diff = clean_new - clean_old
            if diff != 0:
                pesan = f"Realisasi S/D Hari Ini bertambah Rp {diff:,.0f}" if diff > 0 else f"Realisasi S/D Hari Ini berkurang Rp {abs(diff):,.0f}"
                logs.insert(0, {"time": current_data["timestamp"], "message": pesan})
        except Exception:
            pass

    final_data = {
        "current": current_data,
        "logs": logs[:50]
    }

    with open(DATA_FILE, "w") as f:
        json.dump(final_data, f, indent=4)
    print("File data.json berhasil diperbarui!")

if __name__ == "__main__":
    main()
