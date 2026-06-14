import requests
from bs4 import BeautifulSoup
import re

# Headers per simulare un browser reale ed evitare il blocco di Amazon
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def ottieni_info_prodotto(url):
    """Scarica la pagina Amazon e restituisce nome e prezzo del prodotto."""
    try:
        risposta = requests.get(url, headers=HEADERS, timeout=10)

        if risposta.status_code != 200:
            print(f"Status code: {risposta.status_code}")
            return None

        soup = BeautifulSoup(risposta.content, "html.parser")

        # --- Nome prodotto ---
        nome_el = soup.find("span", {"id": "productTitle"})
        nome = nome_el.get_text().strip() if nome_el else "Prodotto sconosciuto"
        nome = nome[:120]  # Tronca se troppo lungo

        # --- Prezzo ---
        prezzo = None
        
        # Diciamo al bot di cercare SOLO nei div principali del prezzo per evitare le rate
        contenitori_prezzo = [
            soup.find("div", {"id": "corePriceDisplay_desktop_feature_div"}),
            soup.find("div", {"id": "corePrice_feature_div"}),
            soup.find("div", {"id": "corePrice_desktop"}),
            soup  # Fallback: cerca in tutta la pagina se non trova i div principali
        ]

        for contenitore in contenitori_prezzo:
            if not contenitore:
                continue
                
            # Cerchiamo prima la classe a-offscreen (solitamente ha il prezzo intero)
            el_prezzo = contenitore.find("span", {"class": "a-offscreen"})
            if not el_prezzo:
                # Fallback sulla classe a-price-whole
                el_prezzo = contenitore.find("span", {"class": "a-price-whole"})
                
            if el_prezzo:
                testo = el_prezzo.get_text().strip()
                # Pulisce simboli di valuta, spazi e formatta i numeri (es. "1.299,99€" → "1299.99")
                testo = testo.replace("€", "").replace(" ", "")
                testo = testo.replace(".", "").replace(",", ".")
                
                match = re.search(r"\d+\.?\d*", testo)
                if match:
                    try:
                        prezzo = float(match.group())
                        # Se ha trovato un prezzo reale (maggiore di 0), si ferma!
                        if prezzo > 0:
                            break
                    except ValueError:
                        continue
            
            # Se ha trovato il prezzo nel contenitore giusto, ferma il ciclo generale
            if prezzo:
                break

        return {"nome": nome, "prezzo": prezzo}

    except requests.RequestException as e:
        print(f"Errore di rete: {e}")
        return None
    except Exception as e:
        print(f"Errore generico: {e}")
        return None