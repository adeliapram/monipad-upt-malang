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

        print("5. Membuka halaman dashboard UPT...")
        # Tetap buka halaman dashboard agar sesi aktif dan file jQuery bawaan web ikut dimuat
        driver.get("https://monipad.dipendajatim.go.id/monipad/index.php/main")
        
        print("Menunggu halaman stabil...")
        time.sleep(4) 

        print("6. Mengambil berbagai data JSON via Injeksi Fetch...")
        driver.set_script_timeout(15)

        # Fungsi bantuan untuk menjalankan Fetch dan mengubahnya ke JSON
        def fetch_api(kode_fetch):
            js_script = f"""
                var callback = arguments[arguments.length - 1];
                
                {kode_fetch}
                
                .then(res => res.text())
                .then(data => callback(data))
                .catch(err => callback("ERROR_AJAX"));
            """
            raw_resp = driver.execute_async_script(js_script)
            if raw_resp == "ERROR_AJAX":
                print("Ada API yang gagal ditarik.")
                return None
            return json.loads(raw_resp)

        # ==========================================
        # 1. AMBIL DATA TOTAL
        # Paste hasil "Copy as fetch" dari getDataTotal di sini (tanpa titik koma di akhir)
        # ==========================================
        script_fetch_total = """
            fetch("https://monipad.dipendajatim.go.id/...", {
              "headers": {...},
              "body": "...",
              "method": "POST"
            })
        """
        json_total = fetch_api(script_fetch_total)

        # ==========================================
        # 2. AMBIL DATA HARIAN (Opsional)
        # Paste hasil "Copy as fetch" dari getDataHarian di sini
        # ==========================================
        script_fetch_harian = """
            fetch("https://monipad.dipendajatim.go.id/...", {
              "headers": {...},
              "body": "...",
              "method": "POST"
            })
        """
        json_harian = fetch_api(script_fetch_harian)

        # Anda bisa menambahkan script_fetch_bulanan, dll dengan cara yang sama...

        # ==========================================
        # 3. GABUNGKAN SEMUA DATA
        # ==========================================
        if json_total:
            # Sesuaikan indeks [7] dengan posisi "Total" di dalam JSON pad Anda
            data_total = json_total["data"]["pad"][7] 
            data_sisahari = json_total["data"]["sisahari"]
            
            # Jika json_harian ada, Anda juga bisa mengekstrak isinya di sini
            # data_harian_tertentu = json_harian["data"][...] 

            new_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pro_sdhari_ini": data_total.get("PROSEN", "0"),
                "jml_target": data_total.get("TARGET", "0"),
                "jml_sdhari_ini": data_total.get("JUMLAH", "0"),
                "jml_hari_ini": data_total.get("HRINI", "0"),
                "jml_kurang": data_total.get("KURANG", "0"),
                
                # Anda bisa mengisi ini dari json_harian atau file fetch lainnya
                "jml_target_non": "0", 
                "jml_sdhari_ini_non": "0",
                
                "jml_hari_kerja": data_sisahari.get("JMLHRSISAKERJA", "0")
            }

            print("SUKSES! Semua data berhasil digabung:", new_data)
            return new_data
        else:
            raise Exception("Gagal menarik data utama (Total).")

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
