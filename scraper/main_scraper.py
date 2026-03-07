import requests
from bs4 import BeautifulSoup
import time
import json

BASE_URL = "https://www.acibadem.edu.tr"

def scrape_page(url):
    try:
        response = requests.get(url)
        time.sleep(2)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            return soup
        else:
            print(f"Hata: {url} - {response.status_code}")
            return None
    except Exception as e:
        print(f"İstek hatası: {e}")
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
    url = BASE_URL + "/iletisim"
    soup = scrape_page(url)
    data = {"contact_info": []}
    if soup:
        contact_blocks = soup.find_all("div", class_="contact-info")
        for block in contact_blocks:
            data["contact_info"].append(block.get_text(strip=True))
    return data

def scrape_faculties():
    url = BASE_URL + "/fakulteler"
    soup = scrape_page(url)
    data = {"faculties": []}
    if soup:
        faculties = soup.find_all("div", class_="faculty-card")
        for f in faculties:
            data["faculties"].append(f.get_text(strip=True))
    return data

def main():
    all_data = {}
    all_data.update(scrape_homepage())
    all_data.update(scrape_contact())
    all_data.update(scrape_faculties())

    with open("acibadem_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print("Scraping tamamlandı. Veriler acibadem_data.json dosyasına kaydedildi.")

if __name__ == "__main__":
    main()