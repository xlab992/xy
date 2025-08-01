import re
import base64
import urllib.parse
import requests
from bs4 import BeautifulSoup
import sys
import os
import json
import time
import html
from urllib.parse import urljoin
from dotenv import load_dotenv
load_dotenv()
MFP = os.getenv("MFP")
PSW = os.getenv("PSW")
MFP2 = os.getenv("MFP2")
PSW2 = os.getenv("PSW2")
# MFPRender = os.getenv("MFPRender") # Load if needed in the future
# PSWRender = os.getenv("PSWRender") # Load if needed in the future

if not MFP or not PSW:
    raise ValueError("MFP and PSW environment variables must be set.")

MFP_TO_USE_FOR_MPD = MFP
PSW_TO_USE_FOR_MPD = PSW

if MFP2 and PSW2: # Check if they are set and not empty strings
    MFP_TO_USE_FOR_MPD = MFP2
    PSW_TO_USE_FOR_MPD = PSW2

# Funzioni dal tuo mpd_decoder.py
def extract_mpd_link_from_page(url):
    """Estrae il link MPD da una pagina HTML che contiene un iframe con player.html#"""
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe')

        if iframe and 'src' in iframe.attrs:
            src = iframe['src']
            # Cerca il pattern player.html# seguito dal link MPD
            # Modifica: usa un pattern più permissivo e poi decodifica le entità HTML
            match = re.search(r'player\.html#(https?://.+?)(?="|\'|\s|$)', src)
            if match:
                # Decodifica le entità HTML come &amp;
                mpd_url = html.unescape(match.group(1))
                return mpd_url

        # Se non troviamo il link nell'iframe, cerchiamo in tutto l'HTML
        # Modifica: usa un pattern più permissivo e poi decodifica le entità HTML
        match = re.search(r'player\.html#(https?://.+?)(?="|\'|\s|$)', response.text)
        if match:
            mpd_url = html.unescape(match.group(1))
            return mpd_url

        print(f"Nessun link MPD trovato nella pagina {url}.")
        return None
    except Exception as e:
        print(f"Errore durante l'estrazione del link MPD da {url}: {e}")
        return None

def decode_base64_keys(encoded_string):
    """Decodifica una stringa base64 e restituisce le due chiavi separate da ':'"""
    try:
        decoded = base64.b64decode(encoded_string).decode('utf-8')
        # Verifica se la stringa decodificata contiene il separatore ':'
        if ':' in decoded:
            key1, key2 = decoded.split(':', 1)
            return key1, key2
        else:
            print("La stringa decodificata non contiene il separatore ':'")
            return None, None
    except Exception as e:
        print(f"Errore durante la decodifica base64: {e}")
        return None, None

def generate_proxy_url(mpd_link, key1, key2):
    """Genera l'URL proxy con i parametri richiesti"""
    # Construct the base part of the proxy URL using the selected MFP/PSW
    proxy_base_with_auth = f"{MFP_TO_USE_FOR_MPD}/proxy/mpd/manifest.m3u8?api_password={PSW_TO_USE_FOR_MPD}"
    # Rimuovi il parametro ck= dall'URL MPD prima di codificarlo
    mpd_base = mpd_link.split('?ck=')[0] if '?ck=' in mpd_link else mpd_link

    # Codifica l'URL MPD per l'uso come parametro
    encoded_link = urllib.parse.quote(mpd_base)

    # Costruisci l'URL proxy completo
    proxy_url = f"{proxy_base_with_auth}&d={encoded_link}&key_id={key1}&key={key2}"
    return proxy_url

def process_mpd_url(mpd_url):
    """Elabora un URL MPD diretto, estrae le chiavi e genera l'URL proxy"""
    # Verifica se l'URL contiene il parametro ck= per le chiavi
    ck_match = re.search(r'[?&]ck=([^&\s]+)', mpd_url)  # Modifica qui per catturare ck= anche se non è il primo parametro

    if ck_match:
        encoded_keys = ck_match.group(1)
        key1, key2 = decode_base64_keys(encoded_keys)

        if key1 and key2:
            # Genera l'URL proxy
            proxy_url = generate_proxy_url(mpd_url, key1, key2)
            return proxy_url
        else:
            print("Impossibile decodificare le chiavi.")
            return None
    else:
        print("Nessun parametro 'ck' trovato nell'URL MPD.")
        print(f"URL MPD estratto: {mpd_url}")  # Aggiungi questa riga per debug
        return None

# Nuove funzioni per l'estrazione da pagine Hattrick
def extract_channel_links(main_url):
    """Estrae tutti i link ai canali dalla pagina principale"""
    try:
        response = requests.get(main_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        channel_links = []

        # Cerca tutti i link nei pulsanti
        buttons = soup.find_all('button', class_='btn')
        for button in buttons:
            a_tag = button.find('a')
            if a_tag and 'href' in a_tag.attrs:
                href = a_tag['href'].strip()
                # Rimuovi eventuali spazi e apici
                href = re.sub(r'[`\'"]', '', href).strip()
                if href.startswith('http'):
                    channel_links.append(href)
                elif href:
                    # Costruisci URL completo se è relativo
                    channel_links.append(urljoin(main_url, href))

        return channel_links
    except Exception as e:
        print(f"Errore durante l'estrazione dei link dei canali: {e}")
        return []

def extract_clappr_keys(url):
    """Estrae il link MPD e le chiavi dal player Clappr"""
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Cerca il source MPD
        mpd_match = re.search(r'source:\s*[\'"]([^\'"\s]+\.mpd)[\'"]', response.text)
        if not mpd_match:
            print(f"Nessun link MPD trovato nella pagina Clappr {url}")
            return None, None, None

        mpd_link = mpd_match.group(1).strip()

        # Cerca le clearKeys
        keys_match = re.search(r'clearKeys:\s*{\s*[\'"]([^\'"]+)[\'"]:\s*[\'"]([^\'"]+)[\'"]', response.text)
        if not keys_match:
            print(f"Nessuna chiave trovata nella pagina Clappr {url}")
            return mpd_link, None, None

        key_id = keys_match.group(1).strip()
        key = keys_match.group(2).strip()

        return mpd_link, key_id, key
    except Exception as e:
        print(f"Errore durante l'estrazione delle chiavi Clappr da {url}: {e}")
        return None, None, None

def process_channel_page(url):
    """Processa una pagina di canale e restituisce l'URL proxy"""
    channel_name = url.split('/')[-1].replace('.htm', '')
    print(f"\nProcessando il canale: {channel_name}")

    if 'hd.htm' in url.lower():
        print(f"Canale HD rilevato: {url}")
        # Usa il metodo di decodifica base64
        mpd_url = extract_mpd_link_from_page(url)
        if mpd_url:
            proxy_url = process_mpd_url(mpd_url)
            return channel_name, proxy_url
    else:
        print(f"Canale standard rilevato: {url}")
        # Usa il metodo di estrazione diretta da Clappr
        mpd_link, key_id, key = extract_clappr_keys(url)
        if mpd_link and key_id and key:
            proxy_url = generate_proxy_url(mpd_link, key_id, key)
            return channel_name, proxy_url

    return channel_name, None

# Definizione delle associazioni tra nomi dei canali e tvg-name
channel_associations = {
    "euro1": "EuroSport 1",
    "skyuno": "Sky UNO",
    "skyunohd": "Sky UNO",
    "tennis": "Sky Sport Tennis",
    "tennishd": "Sky Sport Tennis",
    "dazn1hd": "DAZN 1",
    "motogp": "Sky Sport MotoGP",
    "motogphd": "Sky Sport MotoGP",
    "f1": "Sky Sport F1",
    "f1hd": "Sky Sport F1",
    "max": "Sky Sport Football",
    "maxhd": "Sky Sport Football",
    "arena": "Sky Sport Arena",
    "arenahd": "Sky Sport Arena",
    "calcio": "Sky Sport Calcio",
    "calciohd": "Sky Sport Calcio",
    "uno": "Sky Sport UNO",
    "unohd": "Sky Sport UNO",
    "sport24hd": "Sky Sport 24",
    "live12hd": "skysport252.it",
    "live12": "skysport252.it",
    "live13hd": "skysport253.it",
    "live13": "skysport253.it",
    "live16hd": "skysport256.it",
    "live16": "skysport256.it"
}

# Definizione delle associazioni tra tvg-name e tvg-id
tvg_id_associations = {
    "EuroSport 1": "eurosport1.it",
    "Sky UNO": "skyuno.it",
    "Sky Sport Tennis": "skysporttennis.it",
    "DAZN 1": "dazn1.it",
    "Sky Sport MotoGP": "skysportmotogp.it",
    "Sky Sport F1": "skysportf1.it",
    "Sky Sport Football": "skysportmax.it",
    "Sky Sport Arena": "skysportarena.it",
    "Sky Sport Calcio": "skysportcalcio.it",
    "Sky Sport UNO": "skysportuno.it",
    "Sky Sport 24": "skysport24.it"
}

# Definizione delle associazioni tra tvg-name e group-title
group_title_associations = {
    "EuroSport 1": "Sport",
    "Sky UNO": "Sky",
    "Sky Sport Tennis": "Sport",
    "DAZN 1": "Sport",
    "Sky Sport MotoGP": "Sport",
    "Sky Sport F1": "Sport",
    "Sky Sport Football": "Sport",
    "Sky Sport Arena": "Sport",
    "Sky Sport Calcio": "Sport",
    "Sky Sport UNO": "Sport",
    "Sky Sport 24": "Sport"
}

# Definizione delle associazioni tra tvg-name e logo
logo_associations = {
    "EuroSport 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/spain/eurosport-1-es.png",
    "Sky UNO": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-uno-it.png",
    "Sky Sport Tennis": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-tennis-it.png",
    "DAZN 1": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/DAZN_1_Logo.svg/774px-DAZN_1_Logo.svg.png",
    "Sky Sport MotoGP": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-motogp-it.png",
    "Sky Sport F1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-f1-it.png",
    "Sky Sport Football": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-football-it.png",
    "Sky Sport Arena": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-arena-it.png",
    "Sky Sport Calcio": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-calcio-it.png",
    "Sky Sport UNO": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-uno-it.png",
    "Sky Sport 24": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-24-it.png"
}

def get_channel_info(channel_name):
    """Ottiene le informazioni del canale in base al nome"""
    # Determina il tvg-name
    tvg_name = None
    if channel_name in channel_associations:
        tvg_name = channel_associations[channel_name]

    # Se non troviamo un'associazione, usiamo il nome del canale
    if not tvg_name:
        tvg_name = channel_name

    # Determina il tvg-id
    tvg_id = tvg_id_associations.get(tvg_name, "")

    # Determina il group-title
    group_title = group_title_associations.get(tvg_name, "Altro")

    # Determina il logo
    logo = logo_associations.get(tvg_name, "")

    # Determina il suffisso in base al nome del canale
    suffix = "(Hd)" if "hd" in channel_name.lower() else "(H)"

    return {
        "tvg_id": tvg_id,
        "tvg_name": tvg_name,
        "tvg_logo": logo,
        "group_title": group_title,
        "suffix": suffix
    }

def create_m3u_entry(channel_name, proxy_url):
    """Crea una voce M3U per il canale"""
    info = get_channel_info(channel_name)

    # Crea la riga EXTINF
    extinf = f'#EXTINF:-1 tvg-id="{info["tvg_id"]}" tvg-name="{info["tvg_name"]} " tvg-logo="{info["tvg_logo"]}" group-title="{info["group_title"]}", {info["tvg_name"]} {info["suffix"]}'

    return f"{extinf}\n{proxy_url}\n\n"

def create_m3u_playlist(channels, m3u_file):
    """Crea una nuova playlist M3U con i canali"""
    try:
        # Crea il file M3U con l'intestazione
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write("# Playlist generata da Hattrick\n")

            # Aggiungi tutti i canali
            for channel_name, proxy_url in channels.items():
                entry = create_m3u_entry(channel_name, proxy_url)
                f.write(entry)

        print(f"Creata playlist M3U con {len(channels)} canali: {m3u_file}")
        return True
    except Exception as e:
        print(f"Errore durante la creazione del file M3U {m3u_file}: {e}")
        return False

def main():
    # URL principale da cui iniziare
    main_url = "https://hattrick.ws/"

    # Estrai tutti i link ai canali
    print(f"Estraendo i link dei canali da {main_url}...")
    channel_links = extract_channel_links(main_url)
    print(f"Trovati {len(channel_links)} link a canali.")

    # Processa ogni canale
    results = {}
    for i, url in enumerate(channel_links):
        print(f"Processando {i+1}/{len(channel_links)}: {url}")
        channel_name, proxy_url = process_channel_page(url)
        if proxy_url:
            results[channel_name] = proxy_url
            print(f"Generato URL proxy per {channel_name}")
        else:
            print(f"Impossibile generare URL proxy per {channel_name}")

        # Aggiungi un piccolo ritardo per evitare di sovraccaricare il server
        time.sleep(1)

    # Salva i risultati in un file
    output_file = "hattrick_channels.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for channel, url in results.items():
            f.write(f"{channel}: {url}\n")

    # Salva anche in formato JSON per un uso più facile
    json_output_file = "hattrick_channels.json"
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nCompletato! Trovati {len(results)} canali con URL proxy validi.")
    print(f"I risultati sono stati salvati in {output_file} e {json_output_file}")

    # Crea la playlist M3U
    m3u_file = "hat.m3u8"
    print(f"\nCreando la playlist M3U: {m3u_file}...")
    if create_m3u_playlist(results, m3u_file):
        print(f"Playlist M3U creata con successo!")
    else:
        print(f"Errore durante la creazione della playlist M3U.")

if __name__ == "__main__":
    main()
