import requests
import gzip
import os
import xml.etree.ElementTree as ET
import io
import re
import json
from datetime import datetime, timedelta

# URL dei file GZIP o XML da elaborare
URLS_GZIP = [
    'https://www.open-epg.com/files/italy1.xml',
    'https://www.open-epg.com/files/italy2.xml',
    'https://www.open-epg.com/files/italy3.xml',
    'https://www.open-epg.com/files/italy4.xml'
]

# File di output finale
OUTPUT_XML_FINAL = 'epg.xml'

# URL remoto di it.xml (PlutoTV)
URL_IT_XML = 'https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/it.xml'

# File eventi locale (input per questo script)
PATH_EVENTI_INPUT = 'eventi.xml'

# File JSON degli eventi live
EVENTS_JSON_FILE = 'daddyliveSchedule.json'

# ======================================================================
# FUNZIONI ORIGINALI PER EPG STATICI
# ======================================================================

def download_and_parse_xml(url):
    """Scarica un file .xml o .gzip e restituisce l'ElementTree."""
    print(f" Tentativo di scaricare e parsare: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Prova a decomprimere come GZIP
        try:
            with gzip.open(io.BytesIO(response.content), 'rb') as f_in:
                xml_content = f_in.read()
            print(f" -> Decompresso come GZIP.")
        except (gzip.BadGzipFile, OSError):
            # Non è un file gzip, usa direttamente il contenuto
            xml_content = response.content
            print(f" -> Letto come XML semplice.")
        return ET.ElementTree(ET.fromstring(xml_content))
    except requests.exceptions.RequestException as e:
        print(f" ERRORE durante il download da {url}: {e}")
    except ET.ParseError as e:
        print(f" ERRORE nel parsing del file XML da {url}: {e}")
    return None

def clean_attribute(element, attr_name):
    """
    Pulisce un attributo specifico di un elemento XML:
    rimuove gli spazi e converte in minuscolo.
    """
    if attr_name in element.attrib:
        old_value = element.attrib[attr_name]
        new_value = old_value.replace(" ", "").lower()
        if old_value != new_value:
            # print(f" Attributo '{attr_name}' pulito: '{old_value}' -> '{new_value}'")
            element.attrib[attr_name] = new_value

# ======================================================================
# NUOVE FUNZIONI PER EPG EVENTI LIVE
# ======================================================================

def clean_text(text):
    """Pulisce il testo rimuovendo tag HTML."""
    return re.sub(r'<[^>]+>', '', str(text))

def clean_channel_id(text):
    """Rimuove caratteri speciali e spazi dal channel ID."""
    # Rimuovi prima i tag HTML
    text = clean_text(text)
    # Rimuovi tutti gli spazi
    text = re.sub(r'\s+', '', text)
    # Mantieni solo caratteri alfanumerici (rimuovi tutto il resto)
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    # Assicurati che non sia vuoto
    if not text:
        text = "unknownchannel"
    return text.lower()

def load_events_json(json_file_path):
    """Carica e filtra i dati JSON per la generazione EPG."""
    if not os.path.exists(json_file_path):
        print(f"[!] File JSON non trovato per EPG eventi: {json_file_path}")
        return {}
    
    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            json_data = json.load(file)
        print(f"[✓] Dati JSON caricati da: {json_file_path}")
        return json_data
    except json.JSONDecodeError as e:
        print(f"[!] Errore nel parsing del file JSON: {e}")
        return {}
    except Exception as e:
        print(f"[!] Errore nell'apertura del file JSON: {e}")
        return {}

def generate_epg_xml_from_events(json_data):
    """Genera il contenuto XML EPG dai dati JSON filtrati."""
    print("[i] Generazione contenuto XML EPG dagli eventi...")
    
    epg_content = []
    
    # Offset italiano (+2 ore rispetto a UTC)
    italian_offset = timedelta(hours=2)
    italian_offset_str = "+0200"
    
    # Data e ora corrente
    current_datetime_utc = datetime.utcnow()
    current_datetime_local = current_datetime_utc + italian_offset
    
    # Tiene traccia degli ID dei canali già processati
    channel_ids_processed = set()
    
    # Contatori per statistiche
    total_events = 0
    processed_events = 0
    processed_channels = 0
    
    for date_key, categories in json_data.items():
        # Estrai la data dall'intestazione
        try:
            date_str_from_key = date_key.split(' - ')[0]
            # Rimuovi suffissi ordinali (st, nd, rd, th)
            date_str_cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str_from_key)
            event_date_part = datetime.strptime(date_str_cleaned, "%A %d %B %Y").date()
            print(f"[i] Elaborazione eventi per la data: {event_date_part}")
        except ValueError as e:
            print(f"[!] Errore nel parsing della data: '{date_str_from_key}'. Errore: {e}")
            continue
        except IndexError as e:
            print(f"[!] Formato data non valido: '{date_key}'. Errore: {e}")
            continue
        
        # Salta date passate
        if event_date_part < current_datetime_local.date():
            print(f"[i] Saltati eventi del passato per la data: {event_date_part}")
            continue
        
        # Processa ogni categoria
        for category_name, events_list in categories.items():
            total_events += len(events_list)
            
            # Ordina gli eventi per orario
            try:
                sorted_events = sorted(events_list, key=lambda x: datetime.strptime(x.get("time", "00:00"), "%H:%M").time())
            except Exception as e:
                print(f"[!] Impossibile ordinare gli eventi per '{category_name}'. Errore: {e}")
                sorted_events = events_list
            
            # Processa ogni evento
            for event_info in sorted_events:
                time_str_utc = event_info.get("time", "00:00")
                event_name = clean_text(event_info.get("event", "Evento Sconosciuto"))
                event_desc = event_info.get("description", f"Trasmesso in diretta.")
                
                # Crea channel ID pulito
                channel_id = clean_channel_id(event_name)
                
                # Converti orario UTC in locale
                try:
                    event_time_utc_obj = datetime.strptime(time_str_utc, "%H:%M").time()
                    event_datetime_utc = datetime.combine(event_date_part, event_time_utc_obj)
                    event_datetime_local = event_datetime_utc + italian_offset
                except ValueError as e:
                    print(f"[!] Errore parsing orario '{time_str_utc}' per '{event_name}'. Errore: {e}")
                    continue
                
                # Salta eventi passati (più di 2 ore fa)
                if event_datetime_local < (current_datetime_local - timedelta(hours=2)):
                    continue
                
                # Verifica che ci siano canali disponibili
                channels_list = event_info.get("channels", [])
                if not channels_list:
                    print(f"[!] Nessun canale disponibile per '{event_name}'")
                    continue
                
                processed_events += 1
                
                # Processa ciascun canale
                for channel_data in channels_list:
                    if not isinstance(channel_data, dict):
                        print(f"[!] Formato canale non valido per '{event_name}'")
                        continue
                    
                    # Crea tag channel se non già processato
                    if channel_id not in channel_ids_processed:
                        channel_tag = f"""  <channel id="{channel_id}">
    <display-name>{event_name}</display-name>
  </channel>"""
                        epg_content.append(channel_tag)
                        channel_ids_processed.add(channel_id)
                        processed_channels += 1
                    
                    # Crea tag programme per l'annuncio
                    # L'annuncio inizia alle 00:00 del giorno e termina all'inizio dell'evento
                    announcement_start_local = datetime.combine(event_date_part, datetime.min.time())
                    announcement_stop_local = event_datetime_local
                    
                    announcement_title = f'Inizia alle {event_datetime_local.strftime("%H:%M")}.'
                    
                    announcement_tag = f"""  <programme start="{announcement_start_local.strftime('%Y%m%d%H%M%S')} {italian_offset_str}" stop="{announcement_stop_local.strftime('%Y%m%d%H%M%S')} {italian_offset_str}" channel="{channel_id}">
    <title lang="it">{announcement_title}</title>
    <desc lang="it">{event_name}.</desc>
    <category lang="it">Annuncio</category>
  </programme>"""
                    epg_content.append(announcement_tag)
                    
                    # Crea tag programme per l'evento principale
                    # L'evento inizia all'orario specificato e dura 2 ore
                    main_event_start_local = event_datetime_local
                    main_event_stop_local = event_datetime_local + timedelta(hours=2)
                    
                    event_tag = f"""  <programme start="{main_event_start_local.strftime('%Y%m%d%H%M%S')} {italian_offset_str}" stop="{main_event_stop_local.strftime('%Y%m%d%H%M%S')} {italian_offset_str}" channel="{channel_id}">
    <title lang="it">Trasmesso in diretta.</title>
    <desc lang="it">{event_name}</desc>
    <category lang="it">{clean_text(category_name)}</category>
  </programme>"""
                    epg_content.append(event_tag)
    
    print(f"[✓] Elaborati {processed_events}/{total_events} eventi, generati {processed_channels} canali")
    return "\n".join(epg_content)

def generate_events_epg(json_file_path, output_file_path=None):
    """
    Funzione principale per generare l'EPG XML degli eventi.
    Se output_file_path è None, restituisce il contenuto come stringa.
    Altrimenti, salva il contenuto nel file specificato.
    """
    print(f"[i] Inizio generazione EPG XML da: {json_file_path}")
    
    # Carica e filtra i dati JSON
    json_data = load_events_json(json_file_path)
    if not json_data:
        print("[!] Nessun dato valido trovato nel file JSON.")
        return None
    
    print(f"[i] Dati caricati per {len(json_data)} date")
    
    # Genera il contenuto XML EPG
    epg_content = generate_epg_xml_from_events(json_data)
    
    # Salva su file o restituisci come stringa
    if output_file_path:
        try:
            with open(output_file_path, "w", encoding="utf-8") as file:
                file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                file.write('<tv>\n')
                file.write(epg_content)
                file.write('\n</tv>')
            print(f"[✓] File EPG XML degli eventi salvato con successo: {output_file_path}")
            return True
        except Exception as e:
            print(f"[!] Errore nel salvataggio del file EPG XML: {e}")
            return False
    else:
        return epg_content

# ======================================================================
# FUNZIONE PRINCIPALE MODIFICATA
# ======================================================================

def merge_epg_data(include_events=True):
    """
    Funzione principale per unire i dati EPG da varie fonti,
    inclusi gli eventi live.
    
    Args:
        include_events: Se True, include anche gli EPG degli eventi.
    """
    print("Avvio del processo di unione EPG...")
    
    # Crea elemento root per l'EPG finale
    root_finale = ET.Element('tv')
    tree_finale = ET.ElementTree(root_finale)
    
    # Processare ogni URL GZIP da open-epg.com
    print("\nElaborazione degli URL GZIP da open-epg.com...")
    for url in URLS_GZIP:
        tree = download_and_parse_xml(url)
        if tree is not None:
            root = tree.getroot()
            for element in root: # Aggiunge tutti gli elementi principali (canali e programmi)
                root_finale.append(element)
            print(f" -> Dati da {url} aggiunti con successo.")
        else:
            print(f" -> Fallimento nell'elaborazione di {url}.")
    
    # Aggiungere programmi da eventi.xml (file locale)
    print(f"\nElaborazione dei programmi dal file locale: {PATH_EVENTI_INPUT}...")
    if os.path.exists(PATH_EVENTI_INPUT):
        try:
            tree_eventi = ET.parse(PATH_EVENTI_INPUT)
            root_eventi = tree_eventi.getroot()
            program_count = 0
            for programme in root_eventi.findall(".//programme"): # Aggiunge solo i programmi
                root_finale.append(programme)
                program_count += 1
            print(f" -> {program_count} programmi da {PATH_EVENTI_INPUT} aggiunti con successo.")
        except ET.ParseError as e:
            print(f" ERRORE nel parsing del file {PATH_EVENTI_INPUT}: {e}")
    else:
        print(f" ATTENZIONE: File non trovato: {PATH_EVENTI_INPUT}")
    
    # Aggiungere programmi da it.xml (URL remoto PlutoTV)
    print(f"\nElaborazione dei programmi da PlutoTV (remoto): {URL_IT_XML}...")
    tree_it = download_and_parse_xml(URL_IT_XML)
    if tree_it is not None:
        root_it = tree_it.getroot()
        program_count = 0
        for programme in root_it.findall(".//programme"): # Aggiunge solo i programmi
            root_finale.append(programme)
            program_count +=1
        print(f" -> {program_count} programmi da {URL_IT_XML} aggiunti con successo.")
    else:
        print(f" Fallimento nell'elaborazione di {URL_IT_XML}.")
    
    # NUOVA FUNZIONALITÀ: Aggiungere EPG per eventi live
    if include_events:
        print(f"\nGenerazione EPG per eventi live da {EVENTS_JSON_FILE}...")
        
        # Carica e processa i dati JSON degli eventi
        if os.path.exists(EVENTS_JSON_FILE):
            # Genera XML per gli eventi
            events_content = generate_events_epg(EVENTS_JSON_FILE)
            
            if events_content:
                # Parsa il contenuto XML degli eventi
                try:
                    # Wrappa il contenuto in un tag root temporaneo per il parsing
                    temp_xml = f'<tv>\n{events_content}\n</tv>'
                    events_root = ET.fromstring(temp_xml)
                    
                    # Aggiungi i canali e i programmi al root finale
                    channel_count = 0
                    program_count = 0
                    
                    for channel in events_root.findall(".//channel"):
                        root_finale.append(channel)
                        channel_count += 1
                    
                    for programme in events_root.findall(".//programme"):
                        root_finale.append(programme)
                        program_count += 1
                    
                    print(f" -> Aggiunti {channel_count} canali e {program_count} programmi dagli eventi live.")
                except ET.ParseError as e:
                    print(f" ERRORE nel parsing dell'XML degli eventi: {e}")
            else:
                print(" ERRORE nella generazione EPG per eventi live.")
        else:
            print(f" ATTENZIONE: File JSON eventi non trovato: {EVENTS_JSON_FILE}")
    
    # Pulire gli ID dei canali
    print("\nPulizia degli ID dei canali...")
    channel_cleaned_count = 0
    for channel in root_finale.findall(".//channel"):
        clean_attribute(channel, 'id')
        channel_cleaned_count +=1
    print(f" -> ID puliti per {channel_cleaned_count} canali.")
    
    # Pulire gli attributi 'channel' nei programmi
    print("\nPulizia degli attributi 'channel' nei programmi...")
    programme_channel_cleaned_count = 0
    for programme in root_finale.findall(".//programme"):
        clean_attribute(programme, 'channel')
        programme_channel_cleaned_count +=1
    print(f" -> Attributi 'channel' puliti per {programme_channel_cleaned_count} programmi.")
    
    # Salvare il file XML finale
    print(f"\nSalvataggio del file XML finale in: {OUTPUT_XML_FINAL}...")
    try:
        with open(OUTPUT_XML_FINAL, 'wb') as f_out: # 'wb' per scrivere bytes (necessario per xml_declaration)
            tree_finale.write(f_out, encoding='utf-8', xml_declaration=True)
        print(f"✅ File XML combinato salvato con successo in: {OUTPUT_XML_FINAL}")
    except IOError as e:
        print(f"ERRORE: Impossibile scrivere il file EPG finale '{OUTPUT_XML_FINAL}': {e}")
    except Exception as e:
        print(f"ERRORE: Si è verificato un errore imprevisto durante il salvataggio del file EPG: {e}")

# ======================================================================
# PUNTO DI INGRESSO
# ======================================================================

if __name__ == "__main__":
    # Assicurati che lo script sia eseguito dalla directory corretta
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir) # Cambia la directory di lavoro corrente a quella dello script
    print(f"Directory di lavoro impostata su: {script_dir}")
    
    # Esegui la funzione principale
    merge_epg_data(include_events=True)