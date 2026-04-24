import requests
from bs4 import BeautifulSoup

url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

units = soup.find("select", id="ddlUnit")
if units:
    for option in units.find_all("option"):
        if option["value"] != "-1":
            print(f"Faculty: {option['value']} - {option.text.strip()}")
