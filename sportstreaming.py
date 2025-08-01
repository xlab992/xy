import requests
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# 1. Configurazione esclusione canali
EXCLUDED_TEMP_CHANNELS = set(list(range(25, 30)) + [32, 34] + list(range(35, 41)))

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

base_url = "https://www.sportstreaming.net/"
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Origin": "https://www.sportstreaming.net",
    "Referer": "https://www.sportstreaming.net/"
}

PROXY_STREAM_PREFIX = os.getenv("PROXYMFP")

# 4. Implementazione completa formattazione date
def format_event_date(date_text):
    if not date_text:
        return "Data non disponibile"
    
    date_text = date_text.lower().strip()
    day, month_name, year = None, None, None
    
    try:
        # Estrazione giorno, mese e anno
        date_parts = re.findall(r'\d+|[^\W\d]+', date_text)
        day = int(date_parts[0])
        month_name = date_parts[1]
        year = int(date_parts[2]) if len(date_parts) > 2 else datetime.datetime.now().year
    except (IndexError, ValueError):
        return "Formato data non valido"
    
    # 5. Mappa mesi italiani completa
    ITALIAN_MONTHS_MAP = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3,
        'aprile': 4, 'maggio': 5, 'giugno': 6,
        'luglio': 7, 'agosto': 8, 'settembre': 9,
        'ottobre': 10, 'novembre': 11, 'dicembre': 12,
        'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
        'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
    }
    
    month = ITALIAN_MONTHS_MAP.get(month_name, None)
    if not month:
        return "Mese non valido"
    
    return f"{year}-{month:02d}-{day:02d}"

def find_event_pages():
    try:
        event_links = []
        seen_links = set()
        
        # Scraping della pagina principale
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trovare tutti i link agli eventi
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/live-' in href and href not in seen_links:
                full_url = f"https://www.sportstreaming.net{href}"
                event_links.append(full_url)
                seen_links.add(full_url)
        
        # Aggiungi canali live-temp (escludendo quelli specificati)
        for i in range(1, 41):
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

def get_event_details(event_url):
    try:
        response = requests.get(event_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estrazione URL dello stream
        stream_element = soup.find('div', class_='stream-player')
        stream_url = stream_element.find('iframe')['src'] if stream_element else None
        
        # Estrazione data evento
        date_element = soup.find('span', class_='event-date')
        date_text = date_element.text.strip() if date_element else None
        formatted_date = format_event_date(date_text) if date_text else "Data non disponibile"
        
        # Estrazione titolo evento
        title_element = soup.find('h1', class_='event-title')
        event_title = title_element.text.strip() if title_element else "Evento sconosciuto"
        
        # Estrazione informazioni lega
        league_element = soup.find('div', class_='league-info')
        league_info = league_element.text.strip() if league_element else "Evento"
        
        return stream_url, formatted_date, event_title, league_info
    
    except Exception as e:
        print(f"Errore durante l'analisi di {event_url}: {e}")
        return None, None, None, None

def generate_clean_tvg_id(name_input):
    if not name_input or name_input.lower() in ["unknown event", "event"]:
        print(f"DEBUG: name_input '{name_input}' è sconosciuto/evento, ritorno 'unknown-event'")
        return "unknown-event"
    
    s = name_input.lower().strip()
    print(f"DEBUG: generate_clean_tvg_id chiamato con name_input='{name_input}', s='{s}'")
    
    # Controllo mappatura personalizzata
    for keyword, tvg_id_map_val in TVG_ID_MAPPING.items():
        if keyword in s:
            print(f"DEBUG: Parola chiave '{keyword}' trovata in '{s}'. Ritorno '{tvg_id_map_val}'")
            return tvg_id_map_val
    print(f"DEBUG: Nessuna parola chiave da TVG_ID_MAPPING trovata in '{s}'.")

    # Pulizia standard
    cleaned_s = re.sub(r'[\s\W_]+', '-', s)
    cleaned_s = re.sub(r'^-+|-+$', '', cleaned_s)
    result = cleaned_s if cleaned_s else "unknown-event"
    print(f"DEBUG: Pulizia standard. Ritorno '{result}'")
    return result

def update_m3u_file(video_streams, m3u_file="sportstreaming_playlist.m3u8"):
    REPO_PATH = os.getenv('GITHUB_WORKSPACE', '.')
    file_path = os.path.join(REPO_PATH, m3u_file)

    # Aggiunta per debug: Stampa TVG_ID_MAPPING per conferma
    print(f"DEBUG: TVG_ID_MAPPING in uso: {TVG_ID_MAPPING}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        perma_count = 1

        for event_url, stream_url, formatted_date, event_title, league_info in video_streams:
            if not stream_url:
                continue

            # Gestione immagini
            if "live-temp-" in event_url:
                image_url = TEMP_CHANNEL_LOGO
            elif "perma" in event_url.lower():
                image_url = f"https://sportstreaming.net/assets/img/live/perma/live{perma_count}.png"
                perma_count += 1
            else:
                match = re.search(r'live-(\d+)', event_url)
                image_url = f"https://sportstreaming.net/assets/img/live/standard/live{match.group(1)}.png" if match else "https://sportstreaming.net/assets/img/live/standard/live1.png"

            display_name = f"{league_info}: {event_title}" if ("perma" in event_url.lower() and league_info != "Event") else event_title
            print(f"DEBUG: display_name per tvg_id: '{display_name}' (da event_title: '{event_title}', league_info: '{league_info}')") # AGGIUNTA PER DEBUG
            tvg_id = generate_clean_tvg_id(display_name)

            # Costruzione URL finale
            encoded_ua = quote_plus(headers["User-Agent"])
            encoded_referer = quote_plus(headers["Referer"])
            encoded_origin = quote_plus(headers["Origin"])
            final_stream_url = f"{PROXY_STREAM_PREFIX}{stream_url}&h_user-agent={encoded_ua}&h_referer={encoded_referer}&h_origin={encoded_origin}"

            # Scrittura entry M3U
            f.write(f'#EXTINF:-1 group-title="SportStreaming" tvg-logo="{image_url}" tvg-id="{tvg_id}" tvg-name="{display_name}",{display_name} | {formatted_date}\n')
            f.write(f"{final_stream_url}\n\n")

    print(f"✅ Playlist generata correttamente: {file_path}")

if __name__ == "__main__":
    print("🚀 Avvio generazione playlist...")
    event_pages = find_event_pages()
    
    if not event_pages:
        print("❌ Nessuna pagina evento trovata")
    else:
        print(f"📡 Trovati {len(event_pages)} eventi")
        video_streams = []
        
        for event_url in event_pages:
            print(f"🔍 Analisi: {event_url}")
            stream_url, formatted_date, event_title, league_info = get_event_details(event_url)
            
            if stream_url:
                video_streams.append((event_url, stream_url, formatted_date, event_title, league_info))
                print(f"✅ Aggiunto: {event_title}")
            else:
                print(f"⚠️ Flusso non trovato per: {event_url}")
        
        if video_streams:
            update_m3u_file(video_streams)
            print(f"🎉 Generati {len(video_streams)} canali")
        else:
            print("❌ Nessun flusso valido trovato")
