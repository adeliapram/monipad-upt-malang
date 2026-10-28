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
        time.sleep(5) # Waktu tunggu dikurangi karena tidak perlu merender halaman dashboard penuh

        print("5. Menarik data JSON langsung dari API Internal...")
        # PENTING: Ganti URL ini dengan Request URL asli dari file getDataTotal di tab Headers
        api_url = "https://monipad.dipendajatim.go.id/monipad/index.php/main/getDataTotal" 

        # Kita perintahkan Selenium untuk menjalankan Fetch API dari dalam browser
        driver.set_script_timeout(15)
        raw_json = driver.execute_async_script(f"""
            var callback = arguments[arguments.length - 1];
            fetch('{api_url}', {{
                headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
            }})
            .then(response => response.json())
            .then(data => callback(data))
            .catch(err => callback({{error: err.toString()}}));
        """)

        if "error" in raw_json:
            raise Exception(f"Gagal mengambil JSON: {raw_json['error']}")

        print("6. Memetakan data JSON...")
        # Masuk ke objek "data" dan array "pad"
        data_pajak = raw_json.get("data", {}).get("pad", [])
        
        # Berdasarkan respons JSON Anda, "Total" ada di indeks ke-7 (NO: 8)
        data_total = data_pajak[7] if len(data_pajak) > 7 else {}
        sisahari = raw_json.get("data", {}).get("sisahari", {})

        new_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pro_sdhari_ini": data_total.get("PROSEN", "0"),
            "jml_target": data_total.get("TARGET", "0"),
            "jml_sdhari_ini": data_total.get("JUMLAH", "0"),
            "jml_hari_ini": data_total.get("HRINI", "0"),
            "jml_kurang": data_total.get("KURANG", "0"),
            
            # Jika variabel "_non" berasal dari endpoint API lain, Anda bisa biarkan 0 
            # atau melakukan fetch ke endpoint kedua dengan cara yang sama seperti di atas.
            "jml_target_non": "0", 
            "jml_sdhari_ini_non": "0", 
            
            "jml_hari_kerja": sisahari.get("JMLHRSISAKERJA", "0"),
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
