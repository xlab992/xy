import re
import base64
import urllib.parse
import requests
from bs4 import BeautifulSoup, SoupStrainer
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
    print("Errore: Le variabili d'ambiente MFP e PSW devono essere impostate.")
    sys.exit(1)

MFP_TO_USE_FOR_MPD = MFP
PSW_TO_USE_FOR_MPD = PSW

if MFP2 and PSW2: # Check if they are set and not empty strings
    MFP_TO_USE_FOR_MPD = MFP2
    PSW_TO_USE_FOR_MPD = PSW2

# Funzioni per decodificare i link MPD (riutilizzate da hat.py)
def extract_mpd_link_from_page(html_content): # Nome funzione mantenuto per compatibilità, ma ora estrae MPD/M3U8
    """Estrae il link dello stream (MPD/M3U8) da un contenuto HTML."""
    if not html_content:
        print("Errore: Contenuto HTML vuoto fornito a extract_mpd_link_from_page.")
        return None
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        iframe = soup.find('iframe')

        # Helper function per decodificare e stampare
        def decode_and_set_url(fragment, source_description):
            if not fragment: return None
            decoded_url = html.unescape(fragment)
            # Iteratively unquote
            prev_url = ""
            # Limita il numero di iterazioni per evitare loop infiniti in casi anomali
            for _ in range(5): # Tenta al massimo 5 decodifiche
                if decoded_url == prev_url:
                    break
                prev_url = decoded_url
                decoded_url = urllib.parse.unquote(prev_url)

            print(f"Link stream estratto e decodificato da {source_description}: {decoded_url}")
            # Ulteriore controllo per URL validi
            if decoded_url.startswith("http://") or decoded_url.startswith("https://"):
                return decoded_url
            else:
                print(f"URL decodificato non valido (non inizia con http/https): {decoded_url}")
                return None

        # Tentativo 1: Iframe
        if iframe and 'src' in iframe.attrs:
            src = iframe['src']
            print(f"Trovato iframe con src: {src}")

            match_chrome_ext = re.search(r'chrome-extension://[^/]+/pages/player\.html#\s*([^\s"\']+)', src)
            if match_chrome_ext:
                url = decode_and_set_url(match_chrome_ext.group(1), "iframe (chrome-extension)")
                if url: return url

            match_player_html = re.search(r'player\.html#\s*([^\s"\']+)', src)
            if match_player_html:
                url = decode_and_set_url(match_player_html.group(1), "iframe (player.html)")
                if url: return url

            print(f"Pattern specifici non trovati nell'iframe src. Provo fallback generico su iframe src: {src}")
            match_fallback_iframe = re.search(r'(https?://[^\s"\'<>]*\.(?:mpd|m3u8|m3u)(?:[^\s"\'<>{}]*)?)', src)
            if match_fallback_iframe:
                url = decode_and_set_url(match_fallback_iframe.group(1), "iframe src (fallback generico)")
                if url: return url

        # Se l'iframe non ha prodotto un URL, o non c'era un iframe, cerchiamo nell'intero HTML.
        print("Link stream non trovato nell'iframe (o iframe non presente/src mancante). Provo a cercare in tutto l'HTML.")

        match_html_chrome_ext = re.search(r'chrome-extension://[^/]+/pages/player\.html#\s*([^\s"\']+)', html_content)
        if match_html_chrome_ext:
            url = decode_and_set_url(match_html_chrome_ext.group(1), "HTML (chrome-extension)")
            if url: return url

        match_html_player_html = re.search(r'player\.html#\s*([^\s"\']+)', html_content)
        if match_html_player_html:
            url = decode_and_set_url(match_html_player_html.group(1), "HTML (player.html)")
            if url: return url

        print(f"Pattern specifici non trovati nell'HTML. Provo fallback generico su tutto l'HTML (lunghezza: {len(html_content)}).")
        match_fallback_html = re.search(r'(https?://[^\s"\'<>]*\.(?:mpd|m3u8|m3u)(?:[^\s"\'<>{}]*)?)', html_content)
        if match_fallback_html:
            url = decode_and_set_url(match_fallback_html.group(1), "HTML (fallback generico)")
            if url: return url

        print(f"Nessun link stream trovato nel contenuto HTML con nessuno dei metodi. Anteprima HTML (prime 500 char): {html_content[:500]}")
        return None
    except Exception as e:
        print(f"Errore durante l'estrazione del link stream dal contenuto HTML: {e}")
        return None

def decode_base64_keys(encoded_string):
    """Decodifica una stringa base64 contenente informazioni sulla chiave.
    Tenta prima di interpretare la stringa decodificata come un oggetto JSON
    con una singola coppia chiave-valore (la chiave JSON diventa key1, il valore JSON diventa key2).
    Se l'interpretazione JSON fallisce o non corrisponde al formato atteso,
    tenta di dividere la stringa decodificata usando ':' come separatore per ottenere key1 e key2.
    Restituisce (key1, key2) o (None, None) in caso di errore.
    """
    try:
        decoded_str = base64.b64decode(encoded_string).decode('utf-8')
    except Exception as e:
        print(f"Errore durante la decodifica base64 della stringa di chiavi: {e}")
        return None, None

    # Tenta prima di parsare come JSON
    try:
        data = json.loads(decoded_str)
        if isinstance(data, dict) and len(data) == 1:
            # Estrai la chiave e il valore dall'unico elemento del dizionario
            key1 = list(data.keys())[0]
            key2 = data[key1]
            return key1, key2
        else:
            # JSON valido, ma non la struttura attesa (dizionario con 1 elemento)
            print(f"Stringa decodificata '{decoded_str}' è JSON valido ma non ha la struttura attesa. Tento lo split per ':'.")
            # Prosegui con il tentativo di split
    except json.JSONDecodeError:
        # Non è un JSON valido, prosegui con il tentativo di split
        # print(f"Decodifica JSON fallita per '{decoded_str}', tento split per ':'") # Debug opzionale
        pass
    except Exception as e: # Altri errori durante l'elaborazione JSON
        print(f"Errore imprevisto durante l'elaborazione JSON di '{decoded_str}': {e}. Tento lo split per ':'.")
        pass

    # Fallback: tenta lo split con il carattere ':' (logica originale)
    if ':' in decoded_str:
        key1, key2 = decoded_str.split(':', 1)
        return key1, key2
    else:
        print(f"Stringa decodificata '{decoded_str}' non è JSON (o nel formato atteso) né contiene ':' per lo split.")
        return None, None

def generate_proxy_url(stream_url, key1, key2, stream_type):
    """Genera l'URL proxy con i parametri richiesti in base al tipo di stream (mpd o hls)."""
    # MFP_TO_USE_FOR_MPD and PSW_TO_USE_FOR_MPD are determined globally

    if stream_type == 'mpd':
        endpoint_base = f"{MFP_TO_USE_FOR_MPD}/proxy/mpd/manifest.m3u8"
        # Rimuovi il parametro ck= dall'URL MPD prima di codificarlo
        url_to_encode = stream_url.split('?ck=')[0] if '?ck=' in stream_url else stream_url
    elif stream_type == 'hls':
        endpoint_base = f"{MFP_TO_USE_FOR_MPD}/proxy/hls/manifest.m3u8" # Using MFP_TO_USE_FOR_MPD for HLS in this script's context
        url_to_encode = stream_url # Gli URL HLS non hanno 'ck' in questo contesto
    else:
        print(f"Errore: Tipo di stream non supportato '{stream_type}' in generate_proxy_url.")
        return None

    encoded_link = urllib.parse.quote(url_to_encode, safe=':/')
    proxy_url_parts = [f"{endpoint_base}?api_password={PSW_TO_USE_FOR_MPD}&d={encoded_link}"]

    # Aggiungi key_id e key solo se sono validi e se è un MPD
    if stream_type == 'mpd' and key1 and key2:
        proxy_url_parts.append(f"&key_id={key1}")
        proxy_url_parts.append(f"&key={key2}")
    return "".join(proxy_url_parts)

def process_stream_url(stream_url):
    """Elabora un URL di stream (MPD, M3U8, M3U), estrae le chiavi (per MPD) e genera l'URL proxy."""
    if not stream_url:
        print("URL stream non fornito a process_stream_url.")
        return None

    # Parse the URL to reliably get the path component
    try:
        parsed_url = urllib.parse.urlparse(stream_url)
        path_lower = parsed_url.path.lower()
    except Exception as e:
        print(f"Errore durante il parsing dell'URL '{stream_url}': {e}")
        return None

    if path_lower.endswith(".mpd"):
        stream_type = 'mpd'
        print(f"Processando link MPD: {stream_url}")
        # Verifica se l'URL MPD contiene il parametro ck= per le chiavi
        ck_match = re.search(r'[?&]ck=([^&\s]+)', stream_url)
        if ck_match:
            encoded_keys = ck_match.group(1)
            key1, key2 = decode_base64_keys(encoded_keys)
            if not (key1 and key2): # decode_base64_keys già gestisce e stampa errori
                print(f"Parametro 'ck' trovato ma impossibile decodificare le chiavi per MPD: {stream_url}.")
                return None # Se ck è presente ma malformato, non procedere
            return generate_proxy_url(stream_url, key1, key2, stream_type)
        else:
            # Nessun parametro 'ck' trovato, genera proxy MPD senza chiavi
            print(f"Nessun parametro 'ck' trovato per {stream_url}. Genero proxy MPD senza chiavi.")
            return generate_proxy_url(stream_url, None, None, stream_type)

    elif path_lower.endswith((".m3u8", ".m3u")):
        stream_type = 'hls'
        print(f"Processando link HLS: {stream_url}")
        # Gli stream HLS in questo contesto non usano parametri ck per le chiavi nel proxy URL
        return generate_proxy_url(stream_url, None, None, stream_type)
    else:
        print(f"URL non processabile (path '{parsed_url.path}' non termina con .mpd, .m3u8, o .m3u): {stream_url}")
        return None

# Funzioni specifiche per thisnot.business
def login_to_site(url, password):
    """Effettua il login al sito con la password fornita"""
    try:
        session = requests.Session()
        # Prima richiesta per ottenere eventuali cookie
        response = session.get(url)
        response.raise_for_status()

        # Cerca il form di login e invia la password
        # Nota: questa parte potrebbe richiedere adattamenti in base al funzionamento effettivo del form
        login_data = {
            'password': password
        }

        # Assumiamo che il form faccia POST alla stessa URL
        response = session.post(url, data=login_data)
        response.raise_for_status()

        # Verifica se il login è riuscito (controlla se siamo ancora nella pagina di login)
        if "INSERIRE PASSWORD" in response.text:
            print("Login fallito. Password errata o form non trovato.")
            return None

        print("Login effettuato con successo!")
        return session
    except Exception as e:
        print(f"Errore durante il login: {e}")
        return None

def extract_event_links(session, main_url):
    """Estrae tutti i link agli eventi dalla pagina principale dopo il login"""
    try:
        response = session.get(main_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        event_links = []
        event_info = []

        # Cerca tutte le categorie (card con header)
        categories = soup.find_all('div', class_='card-header')

        for category in categories:
            category_name = category.text.strip()
            print(f"\nCategoria trovata: {category_name}")

            # Trova il div card-body associato a questa categoria
            card_body = category.find_next('div', class_='card-body')
            if not card_body:
                continue

            # Trova tutti i titoli degli eventi in questa categoria
            titles = card_body.find_all('b', class_='title')
            for title in titles:
                event_title = title.text.strip()
                print(f"Evento: {event_title}")

                # Trova la data associata a questo evento
                date_elem = title.find_next('b', class_='date')
                event_date = date_elem.text.strip() if date_elem else ""

                # Trova tutti i link player.php in questo evento
                parent_div = title.find_parent('div', class_='card-body')
                links = parent_div.find_all('a', href=lambda href: href and 'player.php' in href)

                for link in links:
                    href = link.get('href')
                    if href.startswith('/'):
                        href = urljoin(main_url, href)

                    # Estrai il nome del canale
                    channel_name = link.text.strip()

                    # Estrai il nome dell'evento
                    event_text = link.find_previous('b')
                    event_name = event_text.text.strip() if event_text else ""

                    # Estrai la bandiera/lingua
                    flag = link.find_previous('i', class_=lambda c: c and c.startswith('flag-'))
                    language = flag.get('class')[1].replace('flag-', '') if flag and len(flag.get('class')) > 1 else ""

                    event_links.append(href)
                    event_info.append({
                        'category': category_name,
                        'title': event_title,
                        'date': event_date,
                        'event': event_name,
                        'channel': channel_name,
                        'language': language,
                        'url': href
                    })

        return event_links, event_info
    except Exception as e:
        print(f"Errore durante l'estrazione dei link degli eventi: {e}")
        return [], []

def process_event_page(session, url, event_info):
    """Processa una pagina di evento e restituisce l'URL proxy"""
    try:
        print(f"\nProcessando l'evento: {event_info['event']} su {event_info['channel']} (URL: {url})")

        response = session.get(url)
        response.raise_for_status()

        html_text = response.text
        if not html_text:
            print(f"Contenuto HTML vuoto ricevuto da {url}")
            return None
        stream_url = extract_mpd_link_from_page(response.text) # La funzione ora estrae URL generici di stream
        if not stream_url:
            print(f"Nessun link stream (MPD/M3U8) trovato in {url}")
            return None

        print(f"Link stream trovato: {stream_url}")

        # Processa l'URL stream per ottenere l'URL proxy
        proxy_url = process_stream_url(stream_url)
        if proxy_url:
            print(f"URL proxy generato: {proxy_url}")
            return proxy_url
        else:
            print(f"Impossibile generare l'URL proxy per lo stream: {stream_url} (originato da {url})")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Errore di rete durante il processing della pagina evento {url}: {e}")
        return None
    except Exception as e:
        print(f"Errore generico durante il processing della pagina evento {url}: {e}")
        return None

# Nuova mappa di associazione basata sull'ID della pagina evento
page_id_to_tvg_info = {
    "Sport251_IT": {"tvg_id": "skysport251.it", "tvg_name": "Sky Sport 251"},
    "Sport252_IT": {"tvg_id": "skysport252.it", "tvg_name": "Sky Sport 252"},
    "Sport253_IT": {"tvg_id": "skysport253.it", "tvg_name": "Sky Sport 253"},
    "Sport254_IT": {"tvg_id": "skysport254.it", "tvg_name": "Sky Sport 254"},
    "Sport255_IT": {"tvg_id": "skysport255.it", "tvg_name": "Sky Sport 255"},
    "Sport256_IT": {"tvg_id": "skysport256.it", "tvg_name": "Sky Sport 256"},
    "Sport257_IT": {"tvg_id": "skysport257.it", "tvg_name": "Sky Sport 257"},
    "Sport258_IT": {"tvg_id": "skysport258.it", "tvg_name": "Sky Sport 258"},
    "Sport259_IT": {"tvg_id": "skysport259.it", "tvg_name": "Sky Sport 259"},
    "SportUno_IT": {"tvg_id": "skysportuno.it", "tvg_name": "Sky Sport UNO"},
    "Sport24_IT":  {"tvg_id": "skysport24.it", "tvg_name": "Sky Sport 24"},
    "SportF1_IT":  {"tvg_id": "skysportf1.it", "tvg_name": "Sky Sport F1"},
    "Eurosport2_IT": {"tvg_id": "eurosport2.it", "tvg_name": "Eurosport 2"},
    "Eurosport1_IT": {"tvg_id": "eurosport1.it", "tvg_name": "Eurosport 1"},
    "SportNBA_IT": {"tvg_id": "skysportnba.it", "tvg_name": "Sky Sport NBA"},
    "Dazn": {"tvg_id": "dazn1.it", "tvg_name": "Dazn 1"}
}

def get_channel_info(page_url_key, original_channel_name, event_info_dict):
    """Ottiene le informazioni del canale in base al nome"""
    # Estrai l'ID effettivo della pagina dall'URL completo
    # es. da "https://thisnot.business/player.php?id=Sport251_IT" a "Sport251_IT"
    page_id_match = re.search(r'id=([^&]+)', page_url_key)
    actual_page_id = page_id_match.group(1) if page_id_match else original_channel_name

    tvg_id_val = actual_page_id  # Default per tvg-id se non associato
    tvg_name_for_extinf_tag = original_channel_name # Default per il tag tvg-name=""
    display_name_after_comma = original_channel_name # Default per il nome visualizzato
    logo_url = "https://thisnot.business/loghi/logoaaa.png" # Default per canali non associati

    if actual_page_id in page_id_to_tvg_info:
        info = page_id_to_tvg_info[actual_page_id]
        tvg_id_val = info["tvg_id"]
        tvg_name_for_extinf_tag = info["tvg_name"]
        display_name_after_comma = info["tvg_name"]
        logo_url = "https://thisnot.business/loghi/logo.png"
    else:
        # Per canali non associati, il tvg-name nel tag EXTINF è la descrizione dell'evento
        tvg_name_for_extinf_tag = f"{event_info_dict.get('title', '')} {event_info_dict.get('date', '')} {event_info_dict.get('event', '')}".strip().replace('"', "'") # Evita virgolette nel tag
        # Il nome visualizzato rimane l'original_channel_name
        display_name_after_comma = original_channel_name

    group_title_val = "Sport;ThisNot"
    suffix_val = "(TN)"

    return {
        "tvg_id": tvg_id_val,
        "tvg_name_extinf": tvg_name_for_extinf_tag,
        "tvg_name_display": display_name_after_comma,
        "tvg_logo": logo_url,
        "group_title": group_title_val,
        "suffix": suffix_val
    }

def create_m3u_entry(page_id_key, original_channel_name, proxy_url, event_info_dict):
    """Crea una voce M3U per il canale"""
    channel_meta = get_channel_info(page_id_key, original_channel_name, event_info_dict)

    extinf_line = (
        f'#EXTINF:-1 tvg-id="{channel_meta["tvg_id"]}" '
        f'tvg-name="{channel_meta["tvg_name_extinf"]}" '
        f'tvg-logo="{channel_meta["tvg_logo"]}" '
        f'group-title="{channel_meta["group_title"]}", '
        f'{channel_meta["tvg_name_display"]} {channel_meta["suffix"]}'
    )
    return f"{extinf_line}\n{proxy_url}\n\n"

def create_m3u_playlist(items_for_m3u, m3u_file):
    """Crea una nuova playlist M3U con i canali"""
    try:
        # Crea il file M3U con l'intestazione
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write("# Playlist generata da ThisNotBusiness\n")

            # Aggiungi tutti i canali
            for item_data in items_for_m3u:
                entry = create_m3u_entry(
                    item_data['page_id_key'],
                    item_data['original_channel_name'],
                    item_data['proxy_url'],
                    item_data['event_info_dict']
                )
                f.write(entry)

        print(f"Creata playlist M3U con {len(items_for_m3u)} canali: {m3u_file}")
        return True
    except Exception as e:
        print(f"Errore durante la creazione del file M3U {m3u_file}: {e}")
        return False

def main():
    # URL principale da cui iniziare
    main_url = "https://thisnot.business"
    password = "2025"  # Password per accedere al sito

    # Effettua il login
    print(f"Effettuando il login a {main_url} con password {password}...")
    session = login_to_site(main_url, password)
    if not session:
        print("Login fallito. Impossibile continuare.")
        return

    # Estrai tutti i link agli eventi
    print(f"Estraendo i link degli eventi da {main_url}...")
    event_links, event_info = extract_event_links(session, main_url)
    print(f"Trovati {len(event_links)} link a eventi.")

    # Processa ogni evento
    results_for_m3u = {} # Per M3U, chiave: cat_event_canale
    # Mappa per il report: event_page_url -> proxy_url (se successo)
    page_url_to_proxy_map = {}

    for i, (original_url_from_event_links, original_info_from_event_info_list) in enumerate(zip(event_links, event_info)):
        # current_page_url dovrebbe essere identico a original_info_from_event_info_list['url']
        current_page_url = original_info_from_event_info_list['url']

        print(f"Processando {i+1}/{len(event_links)}: {current_page_url}")

        # Passa l'original_info_from_event_info_list che corrisponde all'URL corrente
        proxy_url = process_event_page(session, current_page_url, original_info_from_event_info_list)

        if proxy_url:
            # Popola la mappa per il report
            page_url_to_proxy_map[current_page_url] = proxy_url

            # Per M3U/TXT/JSON, usa l'URL univoco della pagina evento come chiave.
            # Questo assicura che ogni pagina evento elaborata con successo
            # che produce un URL proxy valido sia inclusa negli output.
            # Non ci saranno sovrascritture basate su categoria/evento/canale duplicati.
            results_for_m3u[current_page_url] = {
                'proxy_url': proxy_url,
                'info': original_info_from_event_info_list
            }
            print(f"Generato URL proxy per {original_info_from_event_info_list['event']} su {original_info_from_event_info_list['channel']}")
        # Il messaggio di errore specifico viene già stampato da process_event_page o process_stream_url

        # Aggiungi un piccolo ritardo per evitare di sovraccaricare il server
        time.sleep(1)

    # Salva i risultati in un file
    output_file = "thisnot_business_channels.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for _key, data in results_for_m3u.items(): # Usa results_for_m3u
            info = data['info']
            f.write(f"{info['category']} - {info['event']} - {info['channel']}: {data['proxy_url']}\n")

    # Salva anche in formato JSON per un uso più facile
    json_output_file = "thisnot_business_channels.json"
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(results_for_m3u, f, indent=2, ensure_ascii=False) # Usa results_for_m3u

    print(f"\nCompletato! Trovati {len(results_for_m3u)} URL proxy validi (uno per pagina evento processata con successo).")
    print(f"I risultati sono stati salvati in {output_file} e {json_output_file}")

    # Creazione del file di report sullo stato dell'estrazione per ogni link evento
    report_file = "thisnot_business_extraction_report.txt"

    with open(report_file, 'w', encoding='utf-8') as f_report:
        f_report.write("Report Estrazione Link da thisnot.business\n")
        f_report.write("===========================================\n\n")

        for single_event_info in event_info: # event_info è la lista di dizionari originali
            event_page_url = single_event_info['url']

            if event_page_url in page_url_to_proxy_map:
                retrieved_proxy_url = page_url_to_proxy_map[event_page_url]
                status_message = f"OK - Proxy generato: {retrieved_proxy_url}"
            else:
                status_message = "FALLITO - Nessun proxy generato (Stream non trovato o non processabile)"

            f_report.write(f"Pagina Evento: {event_page_url}\n")
            f_report.write(f"  Dettagli: Categoria='{single_event_info.get('category', 'N/A')}', Evento='{single_event_info.get('event', 'N/A')}', Canale='{single_event_info.get('channel', 'N/A')}'\n")
            f_report.write(f"  Stato Estrazione: {status_message}\n\n")
    print(f"Il report di estrazione è stato salvato in {report_file}")

    # Prepara i dati per il file M3U
    items_for_m3u = []
    for page_url_key, data_item in results_for_m3u.items(): # Usa results_for_m3u
        event_details = data_item['info']
        proxy_link = data_item['proxy_url']
        items_for_m3u.append({
            'page_id_key': page_url_key, # URL completo della pagina evento
            'original_channel_name': event_details['channel'], # Nome canale originale da 'info'
            'proxy_url': proxy_link,
            'event_info_dict': event_details  # Dizionario completo event_info
        })

    # Crea la playlist M3U
    m3u_file = "this.m3u8"
    print(f"\nCreando la playlist M3U: {m3u_file}...")
    if create_m3u_playlist(items_for_m3u, m3u_file):
        print(f"Playlist M3U creata con successo!")
    else:
        print(f"Errore durante la creazione della playlist M3U.")

if __name__ == "__main__":
    main()
