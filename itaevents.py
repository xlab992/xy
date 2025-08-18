import xml.etree.ElementTree as ET
import random
import uuid
import json
import os
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus  # Add this import
import urllib.parse # Aggiunto per la logica dei loghi
import io # Aggiunto per la logica dei loghi
from PIL import Image, ImageDraw, ImageFont # Aggiunto per la logica dei loghi
from dotenv import load_dotenv
load_dotenv()

MFP = os.getenv("MFP")
PSW = os.getenv("PSW")
PZPROXY = os.getenv("PZPROXY")
# MFPRender = os.getenv("MFPRender") # Load if needed in the future
# PSWRender = os.getenv("PSWRender") # Load if needed in the future
PROXY = os.getenv("PROXY", "") # Kept as a general optional prefix

if not MFP or not PSW:
    raise ValueError("MFP and PSW environment variables must be set.")

GUARCAL = os.getenv("GUARCAL")
DADDY = os.getenv("DADDY")
# SKYSTR = os.getenv("SKYSTR") # Non più usato dalla nuova logica dei loghi

# Constants
#REFERER = "forcedtoplay.xyz"
#ORIGIN = "forcedtoplay.xyz"
#HEADER = f"&h_user-agent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F133.0.0.0+Safari%2F537.36&h_referer=https%3A%2F%2F{REFERER}%2F&h_origin=https%3A%2F%2F{ORIGIN}"
NUM_CHANNELS = 10000
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "itaevents.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

# Add a cache for logos to avoid repeated requests
LOGO_CACHE = {}

# Add a cache for logos loaded from the local file
LOCAL_LOGO_CACHE = [] # Changed to a list to store URLs directly
LOCAL_LOGO_FILE = "guardacalcio_image_links.txt"

RBT_PAGES_DIR_ITALOG = "download" # Directory dove italog si aspetta di trovare le pagine HTML
RBT_BASE_URL = "https://www.rbtv77.com"
RBT_SPORT_PATHS = {
    "calcio": "/football.html",
    "soccer": "/football.html",
    "football americano": "/american-football.html",
    "basket": "/basketball.html",
    "pallacanestro": "/basketball.html",
    "tennis": "/tennis.html",
    "motorsport": "/motorsport.html",
    "automobilismo": "/motorsport.html",
    "formula 1": "/motorsport.html",
    "f1": "/motorsport.html",
    "motogp": "/motorsport.html",
    "pallavolo": "/volleyball.html",
    "volley": "/volleyball.html",
    "fighting": "/fighting.html", # boxe, mma, wwe
    "boxe": "/fighting.html",
    "combat sport": "/fighting.html",
}

os.makedirs("logos", exist_ok=True) # Assicura che la directory dei loghi esista

def generate_text_logo(text, size=130):
    """
    Genera un'immagine quadrata con il testo specificato centrato.
    Usato come fallback quando un logo non viene trovato.
    """
    print(f"[DEBUG_LOGO] generate_text_logo: Generazione logo testuale per '{text}' con dimensione {size}x{size}")
    try:
        img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        try:
            # Prova a usare un font TrueType, altrimenti carica il default
            font_size = int(size * 0.2) # Dimensione font proporzionale alla dimensione immagine
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
            print("[DEBUG_LOGO] generate_text_logo: Font Arial non trovato, usando font di default.")

        # Calcola la dimensione del testo
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Posiziona il testo al centro
        text_x = (size - text_width) / 2
        text_y = (size - text_height) / 2
        draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font) # Testo nero
        return img
    except Exception as e:
        print(f"[!] Errore durante la generazione del logo testuale per '{text}': {e}")
        return Image.new('RGBA', (size, size), (255, 255, 255, 0)) # Restituisce un'immagine vuota in caso di errore

# Define keywords for EXCLUDING channels
EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO = ["college", "youth"]

# Dizionario per traduzione termini sportivi inglesi in italiano
SPORT_TRANSLATIONS = {
    "soccer": "calcio",
    "football": "football americano",
    "basketball": "basket",
    "tennis": "tennis",
    "swimming": "nuoto",
    "athletics": "atletica",
    "cycling": "ciclismo",
    "golf": "golf",
    "baseball": "baseball",
    "rugby": "rugby",
    "boxing": "boxe",
    "wrestling": "lotta",
    "volleyball": "pallavolo",
    "hockey": "hockey",
    "horse racing": "ippica",
    "motor sports": "automobilismo",
    "motorsports": "automobilismo",
    "gymnastics": "ginnastica",
    "martial arts": "arti marziali",
    "running": "corsa",
    "ice hockey": "hockey su ghiaccio",
    "field hockey": "hockey su prato",
    "water polo": "pallanuoto",
    "weight lifting": "sollevamento pesi",
    "weightlifting": "sollevamento pesi",
    "skiing": "sci",
    "skating": "pattinaggio",
    "ice skating": "pattinaggio su ghiaccio",
    "fencing": "scherma",
    "archery": "tiro con l'arco",
    "climbing": "arrampicata",
    "rowing": "canottaggio",
    "sailing": "vela",
    "surfing": "surf",
    "fishing": "pesca",
    "dancing": "danza",
    "chess": "scacchi",
    "snooker": "biliardo",
    "billiards": "biliardo",
    "darts": "freccette",
    "badminton": "badminton",
    "cricket": "cricket",
    "aussie rules": "football australiano",
    "australian football": "football australiano",
    "cross country": "corsa campestre",
    "biathlon": "biathlon",
    "waterpolo": "pallanuoto",
    "handball": "pallamano"
}

# Lista di User-Agent comuni (per la logica dei loghi)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]

# Headers for requests
headers = {
    "Accept": "*/*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,ru;q=0.5",
    "Priority": "u=1, i",
    "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    "Sec-Ch-UA-Mobile": "?0",
    "Sec-Ch-UA-Platform": "Windows",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Referer": RBT_BASE_URL + "/", # Aggiunto per coerenza con la logica dei loghi
    "Sec-Fetch-Storage-Access": "active"
    # User-Agent sarà impostato dinamicamente se necessario dalla logica dei loghi
}

# Remove existing M3U8 file if it exists
if os.path.exists(M3U8_OUTPUT_FILE):
    os.remove(M3U8_OUTPUT_FILE)

def load_local_logos():
    """Loads logo links from the local file into a cache."""
    if not LOCAL_LOGO_CACHE: # Load only once
        try:
            with open(LOCAL_LOGO_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line: # Add non-empty lines to the list
                        LOCAL_LOGO_CACHE.append(line)
            print(f"Caricati {len(LOCAL_LOGO_CACHE)} loghi dal file locale: {LOCAL_LOGO_FILE}")
        except FileNotFoundError:
            print(f"File locale dei loghi non trovato: {LOCAL_LOGO_FILE}. Procedo con lo scraping web.")
        except Exception as e:
            print(f"Errore durante il caricamento del file locale dei loghi {LOCAL_LOGO_FILE}: {e}")

def get_github_logo_url(local_path):
    nomegithub = os.getenv("NOMEGITHUB")
    nomerepo = os.getenv("NOMEREPO")
    filename = os.path.basename(local_path)
    filename_encoded = urllib.parse.quote(filename)
    return f"https://github.com/{nomegithub}/{nomerepo}/raw/branch/main/logos/{filename_encoded}"


def create_logo_from_urls(team1_original, team2_original, logo1_url, logo2_url, event_name_for_single_logo="event_logo"):
    """
    Scarica i loghi dagli URL, li combina se sono due, o salva il singolo.
    Restituisce il percorso locale del file logo salvato.
    """
    try:
        img1 = None
        img2 = None

        # Processa il primo logo
        if logo1_url and logo1_url.startswith("textlogo:"):
            team1_text = logo1_url.replace("textlogo:", "")
            img1 = generate_text_logo(team1_text, size=130) # Usa la dimensione standard del logo team
        elif logo1_url:
            img1_content = requests.get(logo1_url, timeout=10).content
            img1 = Image.open(io.BytesIO(img1_content)).convert('RGBA')

        # Processa il secondo logo
        if logo2_url and logo2_url.startswith("textlogo:"):
            team2_text = logo2_url.replace("textlogo:", "")
            img2 = generate_text_logo(team2_text, size=130) # Usa la dimensione standard del logo team
        elif logo2_url:
            img2_content = requests.get(logo2_url, timeout=10).content
            img2 = Image.open(io.BytesIO(img2_content)).convert('RGBA')

        if team1_original and team2_original and logo1_url and logo2_url: # Due loghi da combinare
            vs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vs.png")

            print(f"[DEBUG_LOGO] create_logo_from_urls: Dimensioni originali - Logo1: {img1.size}, Logo2: {img2.size}")
            # Dimensioni fisse e bilanciate
            final_size = 400
            team_logo_size = 130  # Dimensione fissa per i team
            vs_size = 90  # Dimensione fissa più piccola per VS

            print(f"Dimensioni usate: Teams={team_logo_size}x{team_logo_size}, VS={vs_size}x{vs_size}")

            print(f"[DEBUG_LOGO] create_logo_from_urls: Ridimensionamento loghi team a {team_logo_size}x{team_logo_size}")
            # Assicurati che img1 e img2 siano oggetti Image prima di ridimensionare
            if not isinstance(img1, Image.Image) or not isinstance(img2, Image.Image):
                 print("[!] Errore: Immagini non valide per la combinazione.")
                 return None
            img1 = img1.resize((team_logo_size, team_logo_size), Image.Resampling.LANCZOS)
            img2 = img2.resize((team_logo_size, team_logo_size), Image.Resampling.LANCZOS)

            # Carica e ridimensiona l'immagine VS
            if os.path.exists(vs_path):
                vs_img = Image.open(vs_path).convert('RGBA')
                vs_img = vs_img.resize((vs_size, vs_size), Image.Resampling.LANCZOS)
                print(f"[DEBUG_LOGO] create_logo_from_urls: Immagine VS ridimensionata a {vs_img.size}")
            else:  # Se non trova vs.png crea una di fallback
                vs_img = Image.new('RGBA', (vs_size, vs_size), (255, 255, 255, 0))
                draw = ImageDraw.Draw(vs_img)
                try:
                    font = ImageFont.truetype("arial.ttf", 25)
                except IOError:
                    font = ImageFont.load_default()

                text_bbox = draw.textbbox((0, 0), "VS", font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (vs_size - text_width) / 2
                text_y = (vs_size - text_height) / 2
                draw.text((text_x, text_y), "VS", fill=(400, 0, 0), font=font)
                print(f"[DEBUG_LOGO] create_logo_from_urls: Immagine VS di fallback creata.")

            # Crea l'immagine quadrata finale
            combined = Image.new('RGBA', (final_size, final_size), (255, 255, 255, 0))

            # Calcola le posizioni per centrare tutto orizzontalmente
            spacing = 20
            total_content_width = team_logo_size + vs_size + team_logo_size + (2 * spacing)
            start_x = (final_size - total_content_width) // 2

            # Posizioni X
            img1_x = start_x
            vs_x = start_x + team_logo_size + spacing
            img2_x = vs_x + vs_size + spacing

            # Posizioni Y (centrate verticalmente)
            img1_y = (final_size - team_logo_size) // 2
            img2_y = (final_size - team_logo_size) // 2
            vs_y = (final_size - vs_size) // 2

            # Incolla le immagini
            combined.paste(img1, (img1_x, img1_y), img1)
            combined.paste(vs_img, (vs_x, vs_y), vs_img)
            combined.paste(img2, (img2_x, img2_y), img2)

            # Salva l'immagine
            clean_team1 = re.sub(r'[\\/*?:"<>|]', "", team1_original)
            clean_team2 = re.sub(r'[\\/*?:"<>|]', "", team2_original)
            output_filename = f"{clean_team1}_vs_{clean_team2}.png"
            output_path = os.path.join("logos", output_filename)
            print(f"[DEBUG_LOGO] create_logo_from_urls: Salvataggio logo combinato in: {output_path}")
            combined.save(output_path)
            return output_path

        elif logo1_url: # Un solo logo
            if not isinstance(img1, Image.Image):
                 print("[!] Errore: Immagine singola non valida.")
                 return None
            print(f"[DEBUG_LOGO] create_logo_from_urls: Gestione logo singolo da URL: {logo1_url}")
            # img_content già scaricato/generato come img1
            # Tentativo di aprire l'immagine per ottenere le dimensioni originali
            """ # Commentato perché img1 è già un oggetto Image
                single_img = Image.open(io.BytesIO(img_content))
                print(f"[DEBUG_LOGO] create_logo_from_urls: Dimensioni logo singolo originale: {single_img.size}")
            except Exception as img_err:
                print(f"[DEBUG_LOGO] create_logo_from_urls: Impossibile leggere le dimensioni del logo singolo: {img_err}")
            """
            clean_event_name = re.sub(r'[^\w\s-]', '', event_name_for_single_logo).strip().replace(' ', '_')
            file_ext = logo1_url.split('.')[-1] if '.' in logo1_url.split('/')[-1] else 'png'
            output_path = os.path.join("logos", f"{clean_event_name}_single.{file_ext}")
            print(f"[DEBUG_LOGO] create_logo_from_urls: Salvataggio logo singolo (generato/scaricato) in: {output_path}")
            img1.save(output_path)
            return output_path

    except Exception as e:
        print(f"Errore creazione logo da URLs ({logo1_url}, {logo2_url}): {e}")
    return None

def _search_bing_fallback(event_name):
    """
    Cerca un logo per l'evento specificato utilizzando un motore di ricerca
    Restituisce l'URL dell'immagine trovata o None se non trovata
    """
    try:
        # Pulizia nome evento
        clean_event_name = re.sub(r'\s*\(\d{1,2}:\d{2}\)\s*$', '', event_name)
        if ':' in clean_event_name:
            clean_event_name = clean_event_name.split(':', 1)[1].strip()
        # This function is commented out as per user request.
        print(f"[DEBUG_LOGO] _search_bing_fallback: Ricerca logo generica per: '{clean_event_name}'")
        # print(f"[🔍] Ricerca logo generica per: {clean_event_name}") # Log ridotto
        search_query = urllib.parse.quote(f"{clean_event_name} logo")
        search_url = f"https://www.bing.com/images/search?q={search_query}&qft=+filterui:photo-transparent+filterui:aspect-square+filterui:imagesize-large" # Aggiunto filtro per immagini grandi

        current_headers = headers.copy()
        current_headers["User-Agent"] = random.choice(USER_AGENTS)

        response = requests.get(search_url, headers=current_headers, timeout=10)
        if response.status_code == 200:
            match = re.search(r'"contentUrl":"(https?://[^"]+\.(?:png|jpg|jpeg|svg))"', response.text)
            if match:
                print(f"[DEBUG_LOGO] _search_bing_fallback: Logo trovato con Bing: {match.group(1)}")
                return match.group(1)
            print(f"[DEBUG_LOGO] _search_bing_fallback: Nessun logo trovato con Bing per '{clean_event_name}'.")
        return None
    except Exception as e:
        print(f"[!] Errore nella ricerca del logo Bing: {str(e)}")
        # This function is commented out as per user request.
        return None

def search_team_logo(team_name):
    """
    Funzione dedicata alla ricerca del logo di una singola squadra (attualmente non usata direttamente dalla logica principale).
    """
    try:
        # This function is commented out as per user request.
        print(f"[DEBUG_LOGO] search_team_logo: Inizio ricerca logo per squadra: '{team_name}'")
        search_query = urllib.parse.quote(f"{team_name} logo")
        search_url = f"https://www.bing.com/images/search?q={search_query}&qft=+filterui:photo-transparent+filterui:aspect-square&form=IRFLTR"

        current_headers = headers.copy() # Usa gli header globali come base
        current_headers["User-Agent"] = random.choice(USER_AGENTS) # Scegli un User-Agent a caso

        response = requests.get(search_url, headers=current_headers, timeout=10)

        if response.status_code == 200:
            patterns = [
                r'"contentUrl":"(https?://[^"]+\.(?:png|jpg|jpeg|svg))"',
                # Pattern per murl, a volte codificato in HTML
                r'murl&quot;:&quot;(https?://[^&]+)&quot;',
                r'"murl":"(https?://[^"]+)"'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    for match_url in matches:
                        # Preferisci PNG o SVG se disponibili
                        if any(ext in match_url.lower() for ext in ['.png', '.svg', '.jpg', '.jpeg']):
                            print(f"[DEBUG_LOGO] search_team_logo: Logo trovato per '{team_name}': {match_url} (formato preferito)")
                            return match_url
                    # Fallback al primo match se nessun formato preferito trovato
                    print(f"[DEBUG_LOGO] search_team_logo: Logo trovato per '{team_name}': {matches[0]} (fallback al primo)")

                    return matches[0] # Fallback al primo match se nessun formato preferito trovato
        print(f"[DEBUG_LOGO] search_team_logo: Nessun logo trovato per '{team_name}'.")
    except Exception as e:
        print(f"[!] Errore nella ricerca del logo per '{team_name}': {e}")
        # This function is commented out as per user request.
    return None

def _get_rbtv77_local_page_path(sport_key, event_name):
    """Determina il percorso del file HTML locale di rbtv77.com per lo sport specificato."""
    normalized_sport_key = sport_key.lower()
    if normalized_sport_key in RBT_SPORT_PATHS:
        filename_base = RBT_SPORT_PATHS[normalized_sport_key].strip('/').replace('.html', '').replace('/', '_')
        return os.path.join(RBT_PAGES_DIR_ITALOG, f"rbtv77_{filename_base}.html")
    for dict_key, path_segment in RBT_SPORT_PATHS.items():
        if dict_key in normalized_sport_key or normalized_sport_key in dict_key:
            filename_base = path_segment.strip('/').replace('.html', '').replace('/', '_')
            return os.path.join(RBT_PAGES_DIR_ITALOG, f"rbtv77_{filename_base}.html")
    event_name_lower = event_name.lower()
    for keyword, path_segment in RBT_SPORT_PATHS.items():
        if keyword in event_name_lower:
            filename_base = path_segment.strip('/').replace('.html', '').replace('/', '_')
            return os.path.join(RBT_PAGES_DIR_ITALOG, f"rbtv77_{filename_base}.html")
    return None

def _parse_rbtv77_html_content(html_content, event_name, team1_norm, team2_norm, team1_original=None, team2_original=None):
    """Analizza l'HTML di rbtv77.com per trovare loghi corrispondenti."""
    print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Inizio parsing per evento: '{event_name}'. Team Originali: '{team1_original}' vs '{team2_original}'. Team Normalizzati: '{team1_norm}' vs '{team2_norm}'.")
    soup = BeautifulSoup(html_content, 'html.parser')
    event_containers = soup.find_all('div', class_='PefrsX') # Contenitore principale dell'evento
    print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Trovati {len(event_containers)} contenitori di eventi con classe 'PefrsX'.")
    for container in event_containers:
        team_divs = container.find('div', class_='_484Pxk')
        if not team_divs: continue
        side_a_div = team_divs.find('div', class_='ao9NcA')
        side_b_div = team_divs.find('div', class_='MzXghE')
        def extract_side_data(side_div):
            if not side_div: return None, None
            name_span = side_div.find('span', class_='iXmXJT')
            name = name_span.text.strip() if name_span else ""
            logo_img = side_div.find('img', class_='r-logo')
            logo_url = logo_img['origin-src'] if logo_img and logo_img.get('origin-src') else \
                       (logo_img['src'] if logo_img and logo_img.get('src') else None)
            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Estratto lato: Nome='{name}', Logo URL='{logo_url}'")
            return name.lower(), logo_url
        name_a, logo_a_url = extract_side_data(side_a_div)
        name_b, logo_b_url = extract_side_data(side_b_div)
        if team1_norm and team2_norm:
            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Evento VS. Nomi normalizzati HTML: '{name_a}' vs '{name_b}'. Nomi normalizzati input: '{team1_norm}' vs '{team2_norm}'")
            def get_search_terms(original_name_from_event, normalized_name_from_event):
                terms = set()
                if original_name_from_event:
                    name_lower = original_name_from_event.lower()
                    terms.add(name_lower)
                    name_for_base_extraction = re.sub(r'\s+[A-Z]\.?$', '', original_name_from_event, flags=re.IGNORECASE).strip()
                    if name_for_base_extraction:
                        base_term = name_for_base_extraction.split(' ')[0].lower()
                        if base_term: terms.add(base_term)
                    if '.' in name_lower:
                        parts_before_dot = name_lower.split('.')[0].strip()
                        if parts_before_dot:
                            terms.add(parts_before_dot)
                            terms.add(parts_before_dot.split(' ')[0])
                if normalized_name_from_event:
                    norm_lower = normalized_name_from_event.lower()
                    terms.add(norm_lower)
                    if ' ' in norm_lower: terms.add(norm_lower.split(' ')[0])
                terms.discard('')
                return list(terms)
            team1_search_terms = get_search_terms(team1_original, team1_norm)
            # Aggiungi il nome normalizzato del sito come termine di ricerca
            #if name_a: team1_search_terms.append(name_a)
            #if name_b: team1_search_terms.append(name_b)
            team1_search_terms = list(set(term for term in team1_search_terms if term)) # Rimuovi duplicati e vuoti

            team2_search_terms = get_search_terms(team2_original, team2_norm)
            # Aggiungi il nome normalizzato del sito come termine di ricerca
            #if name_a: team2_search_terms.append(name_a)
            #if name_b: team2_search_terms.append(name_b)
            team2_search_terms = list(set(term for term in team2_search_terms if term)) # Rimuovi duplicati e vuoti

            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Termini di ricerca per Team1 ({team1_original if team1_original else team1_norm}): {team1_search_terms}")
            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Termini di ricerca per Team2 ({team2_original if team2_original else team2_norm}): {team2_search_terms}")

            name_a_parts = name_a.lower().split()
            name_b_parts = name_b.lower().split()
            match1 = any(t1_term in name_a.lower() or (name_a_parts and t1_term in name_a_parts[-1]) for t1_term in team1_search_terms) and \
                     any(t2_term in name_b.lower() or (name_b_parts and t2_term in name_b_parts[-1]) for t2_term in team2_search_terms)
            match2 = any(t1_term in name_b.lower() or (name_b_parts and t1_term in name_b_parts[-1]) for t1_term in team1_search_terms) and \
                     any(t2_term in name_a.lower() or (name_a_parts and t2_term in name_a_parts[-1]) for t2_term in team2_search_terms)
            if match1 and logo_a_url and logo_b_url:
                print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza trovata su RBTv77: {name_a} vs {name_b}. Loghi: {logo_a_url}, {logo_b_url}")
                return logo_a_url, logo_b_url
            if match2 and logo_a_url and logo_b_url:
                print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza trovata su RBTv77 (invertita): {name_b} vs {name_a}. Loghi: {logo_b_url}, {logo_a_url}")
                return logo_b_url, logo_a_url

            # Nuova logica: cerca corrispondenza parziale per team1 e team2 nei nomi trovati
            match_partial_a = any(term in name_a.lower() for term in team1_search_terms) and any(term in name_b.lower() for term in team2_search_terms)
            match_partial_b = any(term in name_b.lower() for term in team1_search_terms) and any(term in name_a.lower() for term in team2_search_terms)
            if match_partial_a and logo_a_url and logo_b_url:
                print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza parziale trovata su RBTv77: {name_a} vs {name_b}. Loghi: {logo_a_url}, {logo_b_url}")
                return logo_a_url, logo_b_url
            if match_partial_b and logo_a_url and logo_b_url:
                print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza parziale trovata su RBTv77 (invertita): {name_b} vs {name_a}. Loghi: {logo_b_url}, {logo_a_url}")
                return logo_b_url, logo_a_url
        event_title_div = container.find('div', class_='lqdQi3')
        event_title_on_site = event_title_div.text.lower() if event_title_div else ""
        cleaned_event_name_for_search = re.sub(r'\s*\(\d{1,2}:\d{2}\)\s*$', '', event_name).lower()
        if ':' in cleaned_event_name_for_search:
            cleaned_event_name_for_search = cleaned_event_name_for_search.split(':', 1)[1].strip()
        simplified_event_name = ' '.join(normalize_team_name(cleaned_event_name_for_search).lower().split())
        search_terms_generic = []
        if team1_original: search_terms_generic.extend(get_search_terms(team1_original, team1_norm))
        if team2_original: search_terms_generic.extend(get_search_terms(team2_original, team2_norm))
        if not search_terms_generic and simplified_event_name:
            search_terms_generic.extend(get_search_terms(None, simplified_event_name))
        name_a_last_word_generic = name_a.lower().split()[-1] if name_a else ""
        name_b_last_word_generic = name_b.lower().split()[-1] if name_b else ""
        if search_terms_generic and any(term in name_a.lower() or term in name_a_last_word_generic or \
                                        # Aggiunto controllo per nome intero o ultima parola
                                        term in name_b.lower() or term in name_b_last_word_generic or \
                                        term in event_title_on_site.lower() for term in search_terms_generic) and logo_a_url:
            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza evento singolo/generico trovata su RBTv77: {event_name} -> {name_a} (logo: {logo_a_url})")
            if name_b and logo_b_url: return logo_a_url, logo_b_url
            return logo_a_url, None
    print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Nessuna corrispondenza trovata per '{event_name}'.")
    return None, None

def _scrape_rbtv77(event_name, sport_key, team1_original, team2_original, team1_norm, team2_norm, cache_key):
    """Legge un file HTML locale di RBTv77 e cerca i loghi."""
    local_html_path = _get_rbtv77_local_page_path(sport_key, event_name)
    print(f"[DEBUG_LOGO] _scrape_rbtv77: Tentativo di scraping RBTv77 per '{event_name}', sport '{sport_key}'. Percorso HTML locale: '{local_html_path}'")
    if not local_html_path or not os.path.exists(local_html_path): # print(f"File HTML locale RBTv77 non trovato per sport: {sport_key} / evento: {event_name} (atteso in {local_html_path})")
        return None
    try:
        with open(local_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logo1_src_url, logo2_src_url = _parse_rbtv77_html_content(
            html_content, event_name,
            team1_norm, team2_norm,
            team1_original, team2_original)
        local_logo_path = None
        print(f"[DEBUG_LOGO] _scrape_rbtv77: Risultati parsing RBTv77 per '{event_name}': logo1='{logo1_src_url}', logo2='{logo2_src_url}'")
        if logo1_src_url and logo2_src_url and team1_original and team2_original:
            print(f"[DEBUG_LOGO] _scrape_rbtv77: Trovato coppia loghi da RBTv77 per {team1_original} vs {team2_original}. Creazione logo combinato.")
            local_logo_path = create_logo_from_urls(team1_original, team2_original, logo1_src_url, logo2_src_url)
        elif logo1_src_url:
            print(f"[DEBUG_LOGO] _scrape_rbtv77: URL logo singolo trovato nel file locale RBTv77 per {event_name}: {logo1_src_url}")
            single_logo_name_base = team1_original if team1_original else event_name
            local_logo_path = create_logo_from_urls(None, None, logo1_src_url, None, event_name_for_single_logo=single_logo_name_base)
        if local_logo_path:
            github_logo_url = get_github_logo_url(local_logo_path)
            print(f"[DEBUG_LOGO] _scrape_rbtv77: Logo creato/trovato da RBTv77 per '{event_name}'. URL GitHub: {github_logo_url}")
            if github_logo_url and cache_key: LOGO_CACHE[cache_key] = github_logo_url
            elif github_logo_url: LOGO_CACHE[event_name] = github_logo_url
            return github_logo_url
    except Exception as e:
        print(f"Errore durante l'elaborazione del file locale RBTv77 {local_html_path}: {e}")
    return None

def get_dynamic_logo(event_name, sport_key):
    """
    Cerca il logo per un evento seguendo una priorità rigorosa:
    1. Cache in memoria (LOGO_CACHE)
    2. File locale (guardacalcio_image_links.txt) - solo se trova ENTRAMBI i team con nome ESATTO
    3. Analisi file HTML locali RBTv77 - solo se trova ENTRAMBI i team con nome ESATTO
    4. Per eventi singoli (senza "vs"): Ricerca con Bing Image Search
    5. Logo di default statico per tutti gli altri casi
    """ # Removed step 6 from docstring
    print(f"[DEBUG_LOGO] get_dynamic_logo: Inizio ricerca logo per evento: '{event_name}', sport: '{sport_key}'")
    event_parts = event_name.split(':', 1)
    teams_string = event_parts[1].strip() if len(event_parts) > 1 else event_parts[0].strip()

    # Cerca pattern VS standard
    teams_match = re.search(r'([^:]+?)\s+vs\s+([^:]+?)(?:\s+[-|]|$)', teams_string, re.IGNORECASE)
    if not teams_match:
        teams_match = re.search(r'([^:]+?)\s+-\s+([^:]+?)(?:\s+[-|]|$)', teams_string, re.IGNORECASE)

    cache_key = None
    team1 = None
    team2 = None
    is_vs_event = False

    if teams_match:
        team1 = teams_match.group(1).strip()
        team2 = teams_match.group(2).strip()
        cache_key = f"{team1} vs {team2}"
        is_vs_event = True

        if cache_key in LOGO_CACHE:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato in cache: VS event '{cache_key}'")
            return LOGO_CACHE[cache_key]
    else:
        # Evento singolo (senza vs)
        clean_event_name_for_cache = re.sub(r'\s*\(\d{1,2}:\d{2}\)\s*$', '', event_name)
        if ':' in clean_event_name_for_cache:
            clean_event_name_for_cache = clean_event_name_for_cache.split(':', 1)[1].strip()
        cache_key = clean_event_name_for_cache
        is_vs_event = False

        if cache_key in LOGO_CACHE:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato in cache: evento singolo '{cache_key}'")
            return LOGO_CACHE[cache_key]

    # SOLO per eventi VS: controllo file locale con corrispondenza ESATTA
    load_local_logos()
    # Modificato il log per chiarezza
    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo file locale (corrispondenza esatta VS) per: {is_vs_event}, team1: {team1}, team2: {team2}")
    if LOCAL_LOGO_CACHE and is_vs_event and team1 and team2:
        team1_normalized = team1.lower().replace(" ", "-")
        team2_normalized = team2.lower().replace(" ", "-")

        for logo_url in LOCAL_LOGO_CACHE:
            logo_url_lower = logo_url.lower()
            # Deve contenere ENTRAMBI i team normalizzati con corrispondenza ESATTA
            if (team1_normalized in logo_url_lower and
                team2_normalized in logo_url_lower):
                # Verifica aggiuntiva: il nome del file deve contenere esattamente i team
                filename = logo_url.split('/')[-1].lower()
                if (team1_normalized in filename and team2_normalized in filename):
                    print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato in file locale: logo combinato per '{cache_key}' -> {logo_url}")
                    if cache_key:
                        LOGO_CACHE[cache_key] = logo_url
                    return logo_url

    # SOLO per eventi VS: controllo RBTv77 con corrispondenza ESATTA
    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo RBTv77 per VS event: {is_vs_event}, team1: {team1}, team2: {team2}")
    if is_vs_event and team1 and team2:
        team1_normalized = normalize_team_name(team1)
        team2_normalized = normalize_team_name(team2)

        # Normalizzazioni speciali
        if "bayern" in team1.lower():
            team1_normalized = "Bayern"
        if "bayern" in team2.lower():
            team2_normalized = "Bayern"
        if "internazionale" in team1.lower() or "inter" in team1.lower():
            team1_normalized = "Inter"
        if "internazionale" in team2.lower() or "inter" in team2.lower():
            team2_normalized = "Inter"

        rbtv77_logo = _scrape_rbtv77(event_name, sport_key, team1, team2, team1_normalized, team2_normalized, cache_key)
        if rbtv77_logo:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato da RBTv77: logo combinato per '{cache_key}' -> {rbtv77_logo}")
            return rbtv77_logo
    # Removed the fallback logic for searching/generating individual team logos
    # as per user request to only use logos found in the HTML pages.
    # if is_vs_event and team1 and team2:
    #     print(f"[DEBUG_LOGO] get_dynamic_logo: Nessun logo combinato trovato per '{cache_key}'. Tentativo ricerca loghi singoli o generazione testuale.")
    #     logo1_url = search_team_logo(team1)
    #     if not logo1_url:
    #         print(f"[DEBUG_LOGO] get_dynamic_logo: Logo singolo non trovato per '{team1}'. Generazione logo testuale.")
    #         logo1_url = f"textlogo:{team1}" # Usa lo schema speciale per logo testuale
    #
    #     logo2_url = search_team_logo(team2)
    #     if not logo2_url:
    #         print(f"[DEBUG_LOGO] get_dynamic_logo: Logo singolo non trovato per '{team2}'. Generazione logo testuale.")
    #         logo2_url = f"textlogo:{team2}" # Usa lo schema speciale per logo testuale
    #
    #     # Se almeno uno dei loghi è stato trovato o generato, crea il logo combinato
    #     if logo1_url or logo2_url:
    #         print(f"[DEBUG_LOGO] get_dynamic_logo: Creazione logo combinato con loghi singoli/testuali per '{cache_key}'. Logo1: '{logo1_url}', Logo2: '{logo2_url}'")
    #         local_logo_path = create_logo_from_urls(team1, team2, logo1_url, logo2_url)
    #         if local_logo_path:
    #             github_logo_url = get_github_logo_url(local_logo_path)
    #             print(f"[DEBUG_LOGO] get_dynamic_logo: Logo combinato creato/trovato (singoli/testuali) per '{cache_key}'. URL GitHub: {github_logo_url}")
    #             if cache_key:
    #                 LOGO_CACHE[cache_key] = github_logo_url
    #             return github_logo_url
    #         else:
    #              print(f"[DEBUG_LOGO] get_dynamic_logo: Fallita la creazione del logo combinato con loghi singoli/testuali per '{cache_key}'.")

    # Ricerca Bing SOLO per eventi singoli (senza vs)
    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo Bing per evento singolo: {not is_vs_event}")
    if not is_vs_event:
        print(f"[DEBUG_LOGO] get_dynamic_logo: Evento singolo rilevato, tentativo Bing per: {event_name}")
        try:
            logo_result = None # Removed call to _search_bing_fallback(event_name)
            if logo_result:
                print(f"[DEBUG_LOGO] get_dynamic_logo: Logo trovato con Bing per evento singolo '{cache_key}': {logo_result}")
                if cache_key:
                    LOGO_CACHE[cache_key] = logo_result
                return logo_result
        except Exception as e:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Errore durante il fallback a Bing per {event_name}: {e}")

    # Logo di default statico per tutti gli altri casi
    print(f"[DEBUG_LOGO] get_dynamic_logo: Nessun logo specifico trovato per '{event_name}', uso logo di default statico.")
    if cache_key:
        LOGO_CACHE[cache_key] = LOGO
    return LOGO

def normalize_team_name(team_name):
    words_to_remove = ["calcio", "fc", "club", "united", "city", "ac", "sc", "sport", "team", "ssc", "as", "cf", "uc", "us", "gs", "ss", "rl", "rc"]
    name_no_punctuation = re.sub(r'[^\w\s]', '', team_name)
    normalized_name = ' '.join(word for word in name_no_punctuation.split() if word.lower() not in words_to_remove)
    return normalized_name.strip()

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_stream_link(dlhd_id, event_name="", channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {event_name} on {channel_name}...")

    # Verifica se è un canale Tennis Stream
    #if channel_name and "Tennis Stream" in channel_name:
    #    print(f"Canale Tennis Stream rilevato, utilizzo link fisso per: {event_name}")
    #    return "https://daddylive.dad/embed/stream-576.php"

    # Restituisci direttamente l'URL senza fare richieste HTTP
    return f"https://thedaddy.click/stream/stream-{dlhd_id}.php"


def clean_group_title(sport_key):
    """Clean the sport key to create a proper group-title"""
    # More robust HTML tag removal
    import re
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip()

    # If empty after cleaning, return original key
    if not clean_key:
        clean_key = sport_key.strip()

    # Convert to title case to standardize
    return clean_key.title()

def translate_sport_to_italian(sport_key):
    """Traduce i termini sportivi inglesi in italiano"""
    # Pulisce il termine dai tag HTML
    clean_key = re.sub(r'<[^>]+>', '', sport_key).strip().lower()

    # Cerca la traduzione nel dizionario
    if clean_key in SPORT_TRANSLATIONS:
        translated = SPORT_TRANSLATIONS[clean_key]
        # Mantieni la formattazione originale (maiuscole/minuscole)
        return translated.title()

    # Se non trova traduzione, restituisce il termine originale pulito
    return clean_group_title(sport_key)

def should_include_channel(channel_name, event_name, sport_key):
    """Controlla se il canale deve essere incluso. Esclude se una keyword è trovata."""
    combined_text = (str(channel_name) + " " + str(event_name) + " " + str(sport_key)).lower()

    for keyword in EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO:
        if keyword.lower() in combined_text:
            print(f"Canale escluso (keyword: '{keyword}'): {channel_name} | {event_name}")
            return False
    return True

def process_events():
    # Fetch JSON schedule
    # fetcher.fetchHTML(DADDY_JSON_FILE, "https://daddylive.dad/schedule/schedule-generated.json")

    # Load JSON data
    dadjson = loadJSON(DADDY_JSON_FILE)

    # Counters
    total_events = 0
    skipped_events = 0
    excluded_by_keyword_filter = 0
    included_channels_count = 0

    # Define categories to exclude
    excluded_categories = [
        "TV Shows", "Cricket", "Aussie rules", "Snooker", "Baseball",
        "Biathlon", "Cross Country", "Horse Racing", "Ice Hockey",
        "Waterpolo", "Golf", "Darts", "Cycling", "Badminton", "Handball", "Equestrian", "Lacrosse", "Floorball"
    ]

    # First pass to gather category statistics
    category_stats = {}
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                if clean_sport_key not in category_stats:
                    category_stats[clean_sport_key] = 0
                category_stats[clean_sport_key] += len(sport_events)
        except (KeyError, TypeError):
            pass

    # Print category statistics
    print("\n=== Available Categories ===")
    for category, count in sorted(category_stats.items()):
        excluded = "EXCLUDED" if category in excluded_categories else ""
        print(f"{category}: {count} events {excluded}")
    print("===========================\n")

    # Generate unique IDs for channels
    unique_ids = generate_unique_ids(NUM_CHANNELS)

    # Open M3U8 file with header
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Second pass to process events
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                total_events += len(sport_events)

                # Skip only exact category matches
                if clean_sport_key in excluded_categories:
                    skipped_events += len(sport_events)
                    continue

                for game in sport_events:
                    for channel in game.get("channels", []):
                        try:
                            # Clean and format day
                            clean_day = day.replace(" - Schedule Time UK GMT", "")
                            # Rimuovi completamente i suffissi ordinali (st, nd, rd, th)
                            clean_day = clean_day.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
                            # Rimuovi anche i suffissi attaccati al numero (1st, 2nd, 3rd, etc.)
                            import re
                            clean_day = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_day)

                            print(f"Original day: '{day}'")
                            print(f"Clean day after processing: '{clean_day}'")

                            day_parts = clean_day.split()
                            print(f"Day parts: {day_parts}")  # Debug per vedere i componenti della data

                            # Handle various date formats with better validation
                            day_num = None
                            month_name = None
                            year = None

                            if len(day_parts) >= 4:  # Standard format: Weekday Month Day Year
                                weekday = day_parts[0]
                                # Verifica se il secondo elemento contiene lettere (è il mese) o numeri (è il giorno)
                                if any(c.isalpha() for c in day_parts[1]):
                                    # Formato: Weekday Month Day Year
                                    month_name = day_parts[1]
                                    day_num = day_parts[2]
                                elif any(c.isalpha() for c in day_parts[2]):
                                    # Formato: Weekday Day Month Year
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                else:
                                    # Se non riusciamo a determinare, assumiamo il formato più comune
                                    day_num = day_parts[1]
                                    month_name = day_parts[2]
                                year = day_parts[3]
                                print(f"Parsed date components: weekday={weekday}, day={day_num}, month={month_name}, year={year}")
                            elif len(day_parts) == 3:
                                # Format could be: "Weekday Day Year" (missing month) or "Day Month Year"
                                if day_parts[0].lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                                    # It's "Weekday Day Year" format (missing month)
                                    day_num = day_parts[1]
                                    # Get current month for Rome timezone
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                    month_name = current_month
                                    year = day_parts[2]
                                else:
                                    # Assume Day Month Year
                                    day_num = day_parts[0]
                                    month_name = day_parts[1]
                                    year = day_parts[2]
                            else:
                                # Use current date from Rome timezone
                                rome_tz = pytz.timezone('Europe/Rome')
                                now = datetime.datetime.now(rome_tz)
                                day_num = now.strftime('%d')
                                month_name = now.strftime('%B')
                                year = now.strftime('%Y')
                                print(f"Using current Rome date for: {clean_day}")

                            # Validate day_num - ensure it's a number and extract only digits
                            if day_num:
                                # Extract only digits from day_num
                                day_num_digits = re.sub(r'[^0-9]', '', str(day_num))
                                if day_num_digits:
                                    day_num = day_num_digits
                                else:
                                    # If no digits found, use current day
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Warning: Invalid day number '{day_num}', using current day: {day_num}")
                            else:
                                # If day_num is None, use current day
                                rome_tz = pytz.timezone('Europe/Rome')
                                day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                print(f"Warning: Missing day number, using current day: {day_num}")

                            # Get time from game data
                            time_str = game.get("time", "00:00")

                            # Converti l'orario da UK a CET (aggiungi 2 ore invece di 1)
                            time_parts = time_str.split(":")
                            if len(time_parts) == 2:
                                hour = int(time_parts[0])
                                minute = time_parts[1]
                                # Aggiungi due ore all'orario UK
                                hour_cet = (hour + 2) % 24
                                # Assicura che l'ora abbia due cifre
                                hour_cet_str = f"{hour_cet:02d}"
                                # Nuovo time_str con orario CET
                                time_str_cet = f"{hour_cet_str}:{minute}"
                            else:
                                # Se il formato dell'orario non è corretto, mantieni l'originale
                                time_str_cet = time_str

                            # Convert month name to number
                            month_map = {
                                "January": "01", "February": "02", "March": "03", "April": "04",
                                "May": "05", "June": "06", "July": "07", "August": "08",
                                "September": "09", "October": "10", "November": "11", "December": "12"
                            }

                            # Aggiungi controllo per il mese
                            if not month_name or month_name not in month_map:
                                print(f"Warning: Invalid month name '{month_name}', using current month")
                                rome_tz = pytz.timezone('Europe/Rome')
                                current_month = datetime.datetime.now(rome_tz).strftime('%B')
                                month_name = current_month

                            month_num = month_map.get(month_name, "01")  # Default to January if not found

                            # Ensure day has leading zero if needed
                            if len(str(day_num)) == 1:
                                day_num = f"0{day_num}"

                            # Create formatted date time
                            year_short = str(year)[-2:]  # Extract last two digits of year
                            formatted_date_time = f"{day_num}/{month_num}/{year_short} - {time_str_cet}"

                            # Also create proper datetime objects for EPG
                            # Make sure we're using clean numbers for the date components
                            try:
                                # Ensure all date components are valid
                                if not day_num or day_num == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    day_num = datetime.datetime.now(rome_tz).strftime('%d')
                                    print(f"Using current day as fallback: {day_num}")

                                if not month_num or month_num == "":
                                    month_num = "01"  # Default to January
                                    print(f"Using January as fallback month")

                                if not year or year == "":
                                    rome_tz = pytz.timezone('Europe/Rome')
                                    year = datetime.datetime.now(rome_tz).strftime('%Y')
                                    print(f"Using current year as fallback: {year}")

                                if not time_str or time_str == "":
                                    time_str = "00:00"
                                    print(f"Using 00:00 as fallback time")

                                # Ensure day_num has proper format (1-31)
                                try:
                                    day_int = int(day_num)
                                    if day_int < 1 or day_int > 31:
                                        day_num = "01"  # Default to first day of month
                                        print(f"Day number out of range, using 01 as fallback")
                                except ValueError:
                                    day_num = "01"  # Default to first day of month
                                    print(f"Invalid day number format, using 01 as fallback")

                                # Ensure day has leading zero if needed
                                if len(str(day_num)) == 1:
                                    day_num = f"0{day_num}"

                                date_str = f"{year}-{month_num}-{day_num} {time_str}:00"
                                print(f"Attempting to parse date: '{date_str}'")
                                start_date_utc = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

                                # Convert to Amsterdam timezone
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                start_date_amsterdam = start_date_utc.replace(tzinfo=pytz.UTC).astimezone(amsterdam_timezone)

                                # Format for EPG
                                mStartTime = start_date_amsterdam.strftime("%Y%m%d%H%M%S")
                                mStopTime = (start_date_amsterdam + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")
                            except ValueError as e:
                                # Definisci date_str qui se non è già definita
                                error_msg = str(e)
                                if 'date_str' not in locals():
                                    date_str = f"Error with: {year}-{month_num}-{day_num} {time_str}:00"

                                print(f"Date parsing error: {error_msg} for date string '{date_str}'")
                                # Use current time as fallback
                                amsterdam_timezone = pytz.timezone("Europe/Amsterdam")
                                now = datetime.datetime.now(amsterdam_timezone)
                                mStartTime = now.strftime("%Y%m%d%H%M%S")
                                mStopTime = (now + datetime.timedelta(days=2)).strftime("%Y%m%d%H%M%S")

                            # Build channel name with new date format
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channelName = formatted_date_time + "  " + channel["channel_name"]
                            else:
                                channelName = formatted_date_time + "  " + str(channel)

                            # Extract event name for the tvg-id
                            event_name_short = game["event"].split(":")[0].strip() if ":" in game["event"] else game["event"].strip()
                            event_details = game["event"]  # Keep the full event details for tvg-name

                        except Exception as e:
                            print(f"Error processing date '{day}': {e}")
                            print(f"Game time: {game.get('time', 'No time found')}")
                            continue

                        # Check if channel should be included based on keywords
                        if should_include_channel(channelName, event_details, clean_sport_key):
                            # Process channel information
                            if isinstance(channel, dict) and "channel_id" in channel:
                                channelID = f"{channel['channel_id']}"
                            else:
                                # Generate a fallback ID
                                channelID = str(uuid.uuid4())

                            # Around line 353 where you access channel["channel_name"]
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channel_name_str = channel["channel_name"]
                            else:
                                channel_name_str = str(channel)
                            stream_url_dynamic = get_stream_link(channelID, event_details, channel_name_str)

                            if stream_url_dynamic:
                                # Around line 361 where you access channel["channel_name"] again
                                if isinstance(channel, dict) and "channel_name" in channel:
                                    channel_name_str = channel["channel_name"]
                                else:
                                    channel_name_str = str(channel)

                                with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file:
                                    # Estrai l'orario dal formatted_date_time
                                    time_only = time_str_cet if time_str_cet else "00:00"

                                    # Crea il nuovo formato per tvg-name con l'orario all'inizio e la data alla fine
                                    tvg_name = f"{time_only} {event_details} - {day_num}/{month_num}/{year_short}"

                                    # Get dynamic logo for this event
                                    event_logo = get_dynamic_logo(game["event"], clean_sport_key)

                                    italian_sport_key = translate_sport_to_italian(clean_sport_key)
                                    file.write(f'#EXTINF:-1 tvg-id="{event_name_short} - {event_details.split(":", 1)[1].strip() if ":" in event_details else event_details}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{italian_sport_key}", {channel_name_str}\n')
                                    # New stream URL format
                                    #file.write(f"{PROXY}{MFP}/extractor/video?host=DLHD&redirect_stream=true&api_password={PSW}&d={stream_url_dynamic}\n\n")
                                    #file.write(f"{PZPROXY}/proxy/m3u?url={stream_url_dynamic}\n\n")
                                    file.write(f"{MFP}/proxy/hls/manifest.m3u8?api_password={PSW}&d={stream_url_dynamic}\n\n") 
                                included_channels_count += 1

                            else:
                            # Il log del motivo dell'esclusione è già in should_include_channel
                                excluded_by_keyword_filter += 1

                        else:
                            print(f"Skipping channel (no keyword match): {clean_group_title(sport_key)} - {event_details} - {channelName}")

        except KeyError as e:
            print(f"KeyError: {e} - Key may not exist in JSON structure")

    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Total events found: {total_events}")
    print(f"Events skipped due to category filters: {skipped_events}")
    print(f"Channels excluded by keyword filter in channel info: {excluded_by_keyword_filter}")
    print(f"Channels included in M3U8 (passed all filters and stream found): {included_channels_count}")
    print(f"Keywords used for channel info exclusion: {EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO}")
    print(f"===========================\n")

    return included_channels_count


def main():
    # Process events and generate M3U8
    total_included_channels = process_events()

    # Verify if any valid channels were created
    if total_included_channels == 0:
        print("No valid channels found or all channels were excluded by filters.")
    else:
        print(f"M3U8 generated with {total_included_channels} channels.")

if __name__ == "__main__":
    main()
