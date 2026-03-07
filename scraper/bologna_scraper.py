from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_bologna_data():
    # Chrome'u arka planda (headless) çalıştırmak için ayarlar
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') 
    
    # WebDriver'ı başlat
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # PDF'te belirtilen Bilgisayar Mühendisliği Bologna sayfası
    url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246#"
    
    print(f"Sayfa yükleniyor: {url}")
    driver.get(url)
    
    # JavaScript'in tabloyu ve içerikleri yüklemesi için ZORUNLU bekleme süresi
    time.sleep(5) 
    
    bologna_data = []
    
    try:
        # Örnek: Sayfadaki tüm ders tablolarını veya satırlarını bulma
        # Not: A'nın sayfaya sağ tıklayıp "İncele" diyerek doğru class veya id'leri bulması gerekecek.
        # Bu örnekte rastgele bir CSS seçici kullanılmıştır.
        course_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        for row in course_rows:
            # Satırdaki hücreleri al
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > 2:
                course_code = cells[0].text.strip()
                course_name = cells[1].text.strip()
                course_ects = cells[2].text.strip()
                
                if course_code and course_name:
                    bologna_data.append({
                        "kodu": course_code,
                        "adi": course_name,
                        "akts": course_ects
                    })
                    
    except Exception as e:
        print(f"Veri çekerken bir hata oluştu: {e}")
        
    finally:
        driver.quit() # Tarayıcıyı mutlaka kapat

    # Verileri kaydet
    with open("bologna_data.json", "w", encoding="utf-8") as f:
        json.dump(bologna_data, f, ensure_ascii=False, indent=4)
        
    print(f"Toplam {len(bologna_data)} ders bologna_data.json dosyasına kaydedildi.")

if __name__ == "__main__":
    scrape_bologna_data()