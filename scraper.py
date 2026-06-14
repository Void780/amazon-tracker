import requests
from bs4 import BeautifulSoup
import re

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def pulisci_prezzo(testo):
    testo = testo.replace("€", "").replace(" ", "").replace("\xa0", "").strip()
    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    elif "." in testo and len(testo.split(".")[-1]) == 3:
        testo = testo.replace(".", "")
    match = re.search(r"\d+\.?\d*", testo)
    if match:
        try:
            valore = float(match.group())
            return valore if valore > 0 else None
        except ValueError:
            return None
    return None

def ottieni_info_prodotto(url):
    try:
        risposta = session.get(url, headers=HEADERS, timeout=15)
        if risposta.status_code != 200:
            print(f"Status: {risposta.status_code}")
            return None

        if "captcha" in risposta.text.lower():
            print("Amazon ha rilevato il bot (CAPTCHA)")
            return None

        soup = BeautifulSoup(risposta.content, "html.parser")

        nome_el = soup.find("span", {"id": "productTitle"})
        nome = nome_el.get_text().strip()[:120] if nome_el else "Prodotto sconosciuto"

        prezzo = None

        for el in soup.find_all("span", {"class": "a-offscreen"}):
            p = pulisci_prezzo(el.get_text())
            if p and p > 0:
                prezzo = p
                break

        if not prezzo:
            intero = soup.find("span", {"class": "a-price-whole"})
            decimale = soup.find("span", {"class": "a-price-fraction"})
            if intero:
                try:
                    i = intero.get_text().strip().replace(".", "").replace(",", "")
                    d = decimale.get_text().strip() if decimale else "00"
                    prezzo = float(f"{i}.{d}")
                except ValueError:
                    pass

        return {"nome": nome, "prezzo": prezzo}

    except Exception as e:
        print(f"Errore: {e}")
        return None