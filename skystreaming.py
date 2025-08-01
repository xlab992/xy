import requests
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
load_dotenv()

# URL di partenza (homepage o pagina con elenco eventi)
base_url = "https://www.sportstreaming.net/"
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Origin": "https://www.sportstreaming.net",
    "Referer": "https://www.sportstreaming.net/"
}

# Prefisso per il proxy dello stream
MFP = os.getenv("MFP")
PSW = os.getenv("PSW")
# MFPRender = os.getenv("MFPRender") # Load if needed in the future
# PSWRender = os.getenv("PSWRender") # Load if needed in the future

if not MFP or not PSW:
    raise ValueError("MFP and PSW environment variables must be set.")

# --- INIZIO MODIFICHE RICHIESTE ---

# 1. Esclusione canali live-temp specifici
# Escludere: 25-30 (compresi), 32, 34, 35-40 (compresi)
EXCLUDED_TEMP_CHANNELS = set(list(range(25, 31)) + [32, 34] + list(range(35, 41)))

# 2. Mappatura completa tvg-id
TVG_ID_MAPPING = {
    'golf': 'skysportgolf.it',
    'sport uno': 'skysportuno.it',
    'sport calcio': 'skysportcalcio.it',
    'sport max': 'skysportmax.it',
    'sport arena': 'skysportarena.it',
    'cinema uno': 'skycinemauno.it',
    'cinema due': 'skycinemadue.it',
    'cinema collection': 'skycinemacollection.it',
    'cinema action': 'skycinemaaction.it',
    'cinema family': 'skycinemafamily.it',
    'cinema romance': 'skycinemaromance.it',
    'cinema comedy': 'skycinemacomedy.it',
    'cinema drama': 'skycinemadrama.it',
    'uno': 'skyuno.it',
    'atlantic': 'skyatlantic.it',
    'serie': 'skyserie.it',
    'investigation': 'skyinvestigation.it',
    'comedy central': 'comedycentral.it',
    'arte': 'skyarte.it',
    'documentaries': 'skydocumentaries.it',
    'nature': 'skynature.it'
}

# 3. Immagine per live-temp
TEMP_CHANNEL_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/Sky_italia_2018.png/500px-Sky_italia_2018.png"

# --- FINE MODIFICHE RICHIESTE ---

# Funzione helper per formattare la data dell'evento
def format_event_date(date_text):
    if not date_text:
        return ""
    match = re.search(
        r'(?:[a-zA-Zì]+\s+)?(\d{1,2})\s+([a-zA-Z]+)\s+(?:ore\s+)?(\d{1,2}:\d{2})',
        date_text,
        re.IGNORECASE
    )
    if match:
        day = match.group(1).zfill(2)
        month_name = match.group(2).lower()
        time = match.group(3)
        month_number = ITALIAN_MONTHS_MAP.get(month_name)
        if month_number:
            return f"{time} {day}/{month_number}"
    return ""


# Mappa dei mesi italiani per la formattazione della data
ITALIAN_MONTHS_MAP = {
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
}

# Funzione per trovare i link alle pagine evento
def find_event_pages():
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        event_links = []
        seen_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if re.match(r'/live-(perma-)?\d+', href):
                full_url = base_url + href.lstrip('/')
                if full_url not in seen_links:
                    event_links.append(full_url)
                    seen_links.add(full_url)
            elif re.match(r'https://www\.sportstreaming\.net/live-(perma-)?\d+', href):
                if href not in seen_links:
                    event_links.append(href)
                    seen_links.add(href)

        # Aggiungi i canali live-temp-1 fino a live-temp-40
        for i in range(1, 41):
            # Modifica: Esclusione canali specifici
            if i in EXCLUDED_TEMP_CHANNELS:
                continue
            temp_url = f"https://sportstreaming.net/live-temp-{i}"
            if temp_url not in seen_links:
                event_links.append(temp_url)
                seen_links.add(temp_url)

        return event_links

    except requests.RequestException as e:
        print(f"Errore durante la ricerca delle pagine evento: {e}")
        return []

# Funzione per estrarre il flusso video e i dettagli dell'evento dalla pagina evento
def get_event_details(event_url):
    try:
        response = requests.get(event_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        stream_url = None
        element = None
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src and ("stream" in src.lower() or re.search(r'\.(m3u8|mp4|ts|html|php)', src, re.IGNORECASE)):
                stream_url = src
                element = iframe
                break

        if not stream_url:
            for embed in soup.find_all('embed'):
                src = embed.get('src')
                if src and ("stream" in src.lower() or re.search(r'\.(m3u8|mp4|ts|html|php)', src, re.IGNORECASE)):
                    stream_url = src
                    element = embed
                    break

        if not stream_url:
            for video in soup.find_all('video'):
                src = video.get('src')
                if src and ("stream" in src.lower() or re.search(r'\.(m3u8|mp4|ts)', src, re.IGNORECASE)):
                    stream_url = src
                    element = video
                    break
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src and ("stream" in src.lower() or re.search(r'\.(m3u8|mp4|ts)', src, re.IGNORECASE)):
                        stream_url = src
                        element = source
                        break

        # Estrai data e ora formattate
        formatted_date = ""
        date_span = soup.find('span', class_='uk-text-meta uk-text-small')
        if date_span:
            date_text = date_span.get_text(strip=True)
            formatted_date = format_event_date(date_text)

        # Estrai il titolo dell'evento dal tag <title>
        event_title_from_html = "Unknown Event"
        title_tag = soup.find('title')
        if title_tag:
            event_title_from_html = title_tag.get_text(strip=True)
            event_title_from_html = re.sub(r'\s*\|\s*Sport Streaming\s*$', '', event_title_from_html, flags=re.IGNORECASE).strip()

        # Estrai informazioni sulla lega/competizione
        league_info = "Event" # Default
        is_perma_channel = "perma" in event_url.lower()

        if is_perma_channel:
            if event_title_from_html and event_title_from_html != "Unknown Event":
                league_info = event_title_from_html
            # Se il titolo del canale perma non è stato trovato, league_info resta "Event"
        else:
            # Per canali non-perma (eventi specifici), cerca lo span della lega/competizione
            league_spans = soup.find_all(
                lambda tag: tag.name == 'span' and \
                            'uk-text-small' in tag.get('class', []) and \
                            'uk-text-meta' not in tag.get('class', []) # Escludi lo span della data
            )
            if league_spans:
                # Prendi il testo del primo span corrispondente, pulito
                league_info = ' '.join(league_spans[0].get_text(strip=True).split())
            # Se lo span non viene trovato per un evento non-perma, league_info resta "Event"

        return stream_url, formatted_date, event_title_from_html, league_info

    except requests.RequestException as e:
        print(f"Errore durante l'accesso a {event_url}: {e}")
        return None, "", "Unknown Event", "Event"

# Funzione per generare tvg-id pulito e mappato
def generate_clean_tvg_id(name_input):
    if not name_input or name_input.lower() in ["unknown event", "event", "live temp"]: # Aggiunto "live temp" per genericità
        return "unknown-event"
    
    s = name_input.lower().strip()
    
    # Controllo mappatura personalizzata
    for keyword, tvg_id_map_val in TVG_ID_MAPPING.items():
        if keyword in s:
            return tvg_id_map_val
    
    # Pulizia standard se nessuna mappatura trovata
    cleaned_s = re.sub(r'[\s\W_]+', '-', s) # Sostituisce spazi e non alfanumerici con '-'
    cleaned_s = re.sub(r'^-+|-+$', '', cleaned_s) # Rimuove trattini iniziali/finali
    
    # Fallback se la stringa pulita è vuota
    return cleaned_s if cleaned_s else "unknown-event"


# Funzione per aggiornare il file M3U8
def update_m3u_file(video_streams, m3u_file="sportstreaming_playlist.m3u8"):
    REPO_PATH = os.getenv('GITHUB_WORKSPACE', '.')
    file_path = os.path.join(REPO_PATH, m3u_file)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        perma_count = 1

        for event_url, stream_url, formatted_date, event_title, league_info in video_streams:
            if not stream_url:
                continue

            # Modifica: Gestione immagine per live-temp, perma, e standard
            if "live-temp-" in event_url:
                image_url = TEMP_CHANNEL_LOGO
            elif "perma" in event_url.lower():
                image_url = f"https://sportstreaming.net/assets/img/live/perma/live{perma_count}.png"
                perma_count += 1
            else:
                match = re.search(r'live-(\d+)', event_url)
                if match:
                    live_number = match.group(1)
                    image_url = f"https://sportstreaming.net/assets/img/live/standard/live{live_number}.png"
                else:
                    image_url = "https://sportstreaming.net/assets/img/live/standard/live1.png" # Fallback per standard

            # Modifica: Logica per display_name (usato per tvg-id e tvg-name)
            # Se è un canale "perma" e league_info non è il default "Event", usa league_info.
            # Altrimenti (canali non-perma o perma con league_info generico), usa event_title.
            # Per i canali live-temp, event_title sarà tipicamente "Live Temp X" o "Unknown Event".
            display_name = league_info if ("perma" in event_url.lower() and league_info != "Event") else event_title
            
            tvg_id = generate_clean_tvg_id(display_name)

            # Codifica gli header per l'URL
            encoded_ua = quote_plus(headers["User-Agent"])
            encoded_referer = quote_plus(headers["Referer"])
            encoded_origin = quote_plus(headers["Origin"])
            # Costruisci l'URL finale con il proxy e gli header
            # stream_url qui è l'URL originale dello stream (es. https://xuione.sportstreaming.net/...)
            # New stream URL format
            proxy_stream_prefix_value = f"{MFP}/proxy/hls/manifest.m3u8?api_password={PSW}&d="
            final_stream_url = f"{proxy_stream_prefix_value}{stream_url}&h_user-agent={encoded_ua}&h_referer={encoded_referer}&h_origin={encoded_origin}"
            f.write(f"#EXTINF:-1 group-title=\"SportStreaming\" tvg-logo=\"{image_url}\" tvg-id=\"{tvg_id}\" tvg-name=\"{display_name}\",{display_name} (SpS)\n")
            f.write(f"{final_stream_url}\n")
            f.write("\n") # Aggiungi una riga vuota dopo ogni canale


    print(f"File M3U8 aggiornato con successo: {file_path}")

# Esegui lo script
if __name__ == "__main__":
    event_pages = find_event_pages()
    if not event_pages:
        print("Nessuna pagina evento trovata.")
    else:
        video_streams = []
        for event_url in event_pages:
            print(f"Analizzo: {event_url}")
            stream_url, formatted_date, event_title, league_info = get_event_details(event_url)
            if stream_url:
                video_streams.append((event_url, stream_url, formatted_date, event_title, league_info))
            else:
                print(f"Nessun flusso trovato per {event_url}")

        if video_streams:
            update_m3u_file(video_streams)
        else:
            print("Nessun flusso video trovato in tutte le pagine evento.")
