import requests
from bs4 import BeautifulSoup
import time
import json
import re

BASE_URL = "https://www.acibadem.edu.tr"

def scrape_page(url):
    try:
        response = requests.get(url, timeout=10)
        time.sleep(2)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        else:
            print(f"Error: {url} - {response.status_code}")
            return None
    except Exception as e:
        print(f"Request Error: {e}")
        return None

def scrape_homepage():
    soup = scrape_page(BASE_URL)
    data = {"homepage_titles": []}
    if soup:
        titles = soup.find_all("h2")
        for t in titles:
            data["homepage_titles"].append(t.get_text(strip=True))
    return data

def scrape_contact():
    data = {
        "contact_info": {
            "campus": "Kerem Aydınlar Kampüsü",
            "address": "Kayışdağı cad. No:32 Ataşehir/İstanbul",
            "phone": "+90 0216 500 44 44",
            "email": "info@acibadem.edu.tr",
            "bilgisayar_muhendisligi_bolum_baskani": "Prof. Dr. Ahmet Bulut",
            "bilgisayar_muhendisligi_akademik_kadro": [
                "Prof. Dr. Ahmet Bulut",
                "Dr. Öğr. Üyesi Mehmet Serkan Apaydın",
                "Öğr. Gör. Dr. Mahsa Zıraksıma",
                "Öğr. Gör. Dr. Seda Nilgün Dumlu",
                "Öğr. Gör. Dr. Sultan Sütlü",
                "Öğr. Gör. Cengiz Riva",
                "Arş. Gör. Gülnaz Yükselen",
                "Arş. Gör. Seher Zeynep Sonkaya",
                "Prof. Dr. Nurettin Cenk Turgay",
                "Dr. Öğr. Üyesi Onur Güzey",
                "Dr. Öğr. Üyesi Özgür Doğan Şahin"
            ]
        }
    }
    return data

def scrape_faculties():
    url = BASE_URL + "/akademik"
    soup = scrape_page(url)
    data = {"faculties": []}
    if soup:
        faculties = soup.find_all("h5")
        for f in faculties:
            data["faculties"].append(f.get_text(strip=True))
    return data

def scrape_deans():
    """
    Scrape dean information from faculty pages.
    This is a template function - it tries to find dean info from academic pages.
    """
    data = {"deans": {}}
    

    faculty_urls = {
        "Tıp Fakültesi": f"{BASE_URL}/akademik/tip-fakultesi",
        "Sağlık Bilimleri Fakültesi": f"{BASE_URL}/akademik/saglik-bilimleri-fakultesi",
        "Eczacılık Fakültesi": f"{BASE_URL}/akademik/eczacilik-fakultesi",
        "Mühendislik ve Doğa Bilimleri Fakültesi": f"{BASE_URL}/akademik/muhendislik-ve-doga-bilimleri-fakultesi",
        "İnsan ve Toplum Bilimleri Fakültesi": f"{BASE_URL}/akademik/insan-ve-toplum-bilimleri-fakultesi",
    }
    
    for faculty_name, faculty_url in faculty_urls.items():
        try:
            soup = scrape_page(faculty_url)
            if soup:
                text = soup.get_text()
                dean_pattern = r'(?:Prof\.\s*Dr\.|Doç\.\s*Dr\.|Dr\.)\s+([A-Za-zçğıöşüÇĞİÖŞÜ\s]+?)(?:\n|<|$|,)'
                matches = re.findall(dean_pattern, text)
                if matches:
                    data["deans"][faculty_name] = matches[0].strip()
        except Exception as e:
            print(f"Error scraping dean info for {faculty_name}: {e}")
    
    return data

def main():
    all_data = {}
    all_data.update(scrape_homepage())
    all_data.update(scrape_contact())
    all_data.update(scrape_faculties())
    all_data.update(scrape_deans())

    with open("acibadem_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print("Scraping completed. Data saved into acibadem_data.json file.")

if __name__ == "__main__":
    main()