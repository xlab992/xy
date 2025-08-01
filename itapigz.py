import xml.etree.ElementTree as ET
import random
import uuid
import fetcher
import json
import os
import datetime
import pytz
import requests
import html # Aggiunto per l'unescaping dell'HTML
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus  # Add this import
import urllib.parse
import io
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import concurrent.futures
load_dotenv()

PZPROXY = os.getenv("PZPROXY")
# MFP = os.getenv("MFP") # Not used in this script for stream construction
# PSW = os.getenv("PSW") # Not used in this script
# MFPRender = os.getenv("MFPRender") # Load if needed in the future
# PSWRender = os.getenv("PSWRender") # Load if needed in the future
GUARCAL = os.getenv("GUARCAL")
DADDY = os.getenv("DADDY")

RBT_PAGES_DIR_ITALOG = "download" # Directory dove italog si aspetta di trovare le pagine HTML
# Dovrai impostare questo URL all'effettivo percorso raw della tua cartella 'download' su Git
RBT_GIT_HTML_BASE_URL = os.getenv("RBT_GIT_HTML_BASE_URL", "https://raw.githubusercontent.com/ciccioxm3/OMGTV/main/download/") # Esempio, da configurare
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

# Constants
#REFERER = "forcedtoplay.xyz"
#ORIGIN = "forcedtoplay.xyz"
#HEADER = f"&h_user-agent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F133.0.0.0+Safari%2F537.36&h_referer=https%3A%2F%2F{REFERER}%2F&h_origin=https%3A%2F%2F{ORIGIN}"
NUM_CHANNELS = 10000
DADDY_LIVE_CHANNELS_URL = 'https://daddylive.dad/24-7-channels.php' # From 247m3u.py
DADDY_JSON_FILE = "daddyliveSchedule.json"
M3U8_OUTPUT_FILE = "itapigz.m3u8"
LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddsport.png"

# Base URLs for the standard stream checking mechanism (from lista.py)
NEW_KSO_BASE_URLS = [
    "https://new.newkso.ru/wind/",
    "https://new.newkso.ru/ddy6/",
    "https://new.newkso.ru/zeko/",
    "https://new.newkso.ru/nfs/",
    "https://new.newkso.ru/dokko1/",
]
WIKIHZ_TENNIS_BASE_URL = "https://new.newkso.ru/wikihz/"
# Add a cache for logos to avoid repeated requests
LOGO_CACHE = {}

# Add a cache for logos loaded from the local file
LOCAL_LOGO_CACHE = [] # Changed to a list to store URLs directly
LOCAL_LOGO_FILE = "guardacalcio_image_links.txt"
HTTP_REQUEST_TIMEOUT = 10 # Standard timeout for HTTP requests
STREAM_LOCATION_CACHE = {} # Cache for pre-fetched stream locations: dlhd_id -> raw_m3u8_url

# --- Globals for Indexed Stream Paths ---
INDEXED_KSO_PATHS = {} # Stores {stream_id: (base_url, path_segment_from_index)}
INDEXED_TENNIS_PATHS = {} # Stores {tennis_id: path_segment_from_index}
# --- End Globals for Indexed Stream Paths ---

EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO = ["youth", "college"]


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

# --- Constants from 247m3u.py ---
STATIC_LOGOS_247 = {
    "sky uno": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-uno-it.png",
    "rai 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/rai-1-it.png",
    "rai 2": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/rai-2-it.png",
    "rai 3": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/rai-3-it.png",
    "eurosport 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/spain/eurosport-1-es.png",
    "eurosport 2": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/spain/eurosport-2-es.png",
    "italia 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/italia1-it.png",
    "la7": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/la7-it.png",
    "la7d": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/la7d-it.png",
    "rai sport": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/rai-sport-it.png",
    "rai premium": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/rai-premium-it.png",
    "sky sports golf": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-golf-it.png",
    "sky sport motogp": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-motogp-it.png",
    "sky sport tennis": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-tennis-it.png",
    "sky sport f1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-f1-it.png",
    "sky sport football": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-football-it.png",
    "sky sport uno": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-uno-it.png",
    "sky sport arena": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-arena-it.png",
    "sky cinema collection": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-collection-it.png",
    "sky cinema uno": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-uno-it.png",
    "sky cinema action": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-action-it.png",
    "sky cinema comedy": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-comedy-it.png",
    "sky cinema uno +24": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-uno-plus24-it.png",
    "sky cinema romance": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-romance-it.png",
    "sky cinema family": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-family-it.png",
    "sky cinema due +24": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-due-plus24-it.png",
    "sky cinema drama": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-drama-it.png",
    "sky cinema suspense": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-cinema-suspense-it.png",
    "sky sport 24": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-24-it.png",
    "sky sport calcio": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-sport-calcio-it.png",
    "sky sport": "https://play-lh.googleusercontent.com/u7UNH06SU4KsMM4ZGWr7wghkJYN75PNCEMxnIYULpA__VPg8zfEOYMIAhUaIdmZnqw=w480-h960-rw",
    "sky calcio 1": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-1-alt-de.png",
    "sky calcio 2": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-2-alt-de.png",
    "sky calcio 3": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-3-alt-de.png",
    "sky calcio 4": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-4-alt-de.png",
    "sky calcio 5": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-5-alt-de.png",
    "sky calcio 6": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-6-alt-de.png",
    "sky calcio 7": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/germany/sky-select-7-alt-de.png",
    "sky serie": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/sky-serie-it.png",
    "20 mediaset": "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/italy/20-it.png",
    "dazn 1": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/DAZN_1_Logo.svg/774px-DAZN_1_Logo.svg.png"
}
STATIC_TVG_IDS_247 = {
    "sky uno": "skyuno.it", "rai 1": "rai1.it", "rai 2": "rai2.it", "rai 3": "rai3.it",
    "eurosport 1": "eurosport1.it", "eurosport 2": "eurosport2.it", "italia 1": "italia1.it",
    "la7": "la7.it", "la7d": "la7d.it", "rai sport": "raisport.it", "rai premium": "raipremium.it",
    "sky sports golf": "skysportgolf.it", "sky sport motogp": "skysportmotogp.it",
    "sky sport tennis": "skysporttennis.it", "sky sport f1": "skysportf1.it",
    "sky sport football": "skysportmax.it", "sky sport uno": "skysportuno.it",
    "sky sport arena": "skysportarena.it", "sky cinema collection": "skycinemacollectionhd.it",
    "sky cinema uno": "skycinemauno.it", "sky cinema action": "skycinemaaction.it",
    "sky cinema comedy": "skycinemacomedy.it", "sky cinema uno +24": "skycinemauno+24.it",
    "sky cinema romance": "skycinemaromance.it", "sky cinema family": "skycinemafamily.it",
    "sky cinema due +24": "skycinemadue+24.it", "sky cinema drama": "skycinemadrama.it",
    "sky cinema suspense": "skycinemasuspense.it", "sky sport 24": "skysport24.it",
    "sky sport calcio": "skysportcalcio.it", "sky calcio 1": "skysport251.it",
    "sky calcio 2": "skysport252.it", "sky calcio 3": "skysport253.it",
    "sky calcio 4": "skysport254.it", "sky calcio 5": "skysport255.it",
    "sky calcio 6": "skysport256.it", "sky calcio 7": "skysport257.it",
    "sky serie": "skyserie.it", "20 mediaset": "20mediasethd.it", "dazn 1": "dazn1.it",
}
STATIC_CATEGORIES_247 = {
    "sky uno": "Sky", "rai 1": "Rai Tv", "rai 2": "Rai Tv", "rai 3": "Rai Tv",
    "eurosport 1": "Sport", "eurosport 2": "Sport", "italia 1": "Mediaset", "la7": "Tv Italia",
    "la7d": "Tv Italia", "rai sport": "Sport", "rai premium": "Rai Tv", "sky sports golf": "Sport",
    "sky sport motogp": "Sport", "sky sport tennis": "Sport", "sky sport f1": "Sport",
    "sky sport football": "Sport", "sky sport uno": "Sport", "sky sport arena": "Sport",
    "sky cinema collection": "Sky", "sky cinema uno": "Sky", "sky cinema action": "Sky",
    "sky cinema comedy": "Sky", "sky cinema uno +24": "Sky", "sky cinema romance": "Sky",
    "sky cinema family": "Sky", "sky cinema due +24": "Sky", "sky cinema drama": "Sky",
    "sky cinema suspense": "Sky", "sky sport 24": "Sport", "sky sport calcio": "Sport",
    "sky calcio 1": "Sport", "sky calcio 2": "Sport", "sky calcio 3": "Sport",
    "sky calcio 4": "Sport", "sky calcio 5": "Sport", "sky calcio 6": "Sport",
    "sky calcio 7": "Sport", "sky serie": "Sky", "20 mediaset": "Mediaset", "dazn 1": "Sport",
}
DEFAULT_247_LOGO = "https://raw.githubusercontent.com/cribbiox/eventi/refs/heads/main/ddlive.png"
DEFAULT_247_GROUP = "24/7 Channels (IT)"
# --- End of Constants from 247m3u.py ---

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
    "Sec-Fetch-Storage-Access": "active",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}


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

def get_github_logo_url(local_path):
    nomegithub = os.getenv("NOMEGITHUB")
    nomerepo = os.getenv("NOMEREPO")
    filename = os.path.basename(local_path)
    filename_encoded = urllib.parse.quote(filename)
    return f"https://git.pizzapi.uk/{nomegithub}/{nomerepo}/raw/branch/main/logos/{filename_encoded}"


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
            vs_size = 60  # Dimensione fissa più piccola per VS

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
                draw.text((text_x, text_y), "VS", fill=(200, 0, 0), font=font)
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
        search_query = urllib.parse.quote(f"{clean_event_name} logo")
        search_url = f"https://www.bing.com/images/search?q={search_query}&qft=+filterui:photo-transparent+filterui:aspect-square+filterui:imagesize-large"

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

        current_headers = headers.copy() 
        current_headers["User-Agent"] = random.choice(USER_AGENTS) 

        response = requests.get(search_url, headers=current_headers, timeout=10)

        if response.status_code == 200:
            patterns = [
                r'"contentUrl":"(https?://[^"]+\.(?:png|jpg|jpeg|svg))"',
                r'murl&quot;:&quot;(https?://[^&]+)&quot;',
                r'"murl":"(https?://[^"]+)"'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    for match_url in matches:
                        if any(ext in match_url.lower() for ext in ['.png', '.svg', '.jpg', '.jpeg']):
                            print(f"[DEBUG_LOGO] search_team_logo: Logo trovato per '{team_name}': {match_url} (formato preferito)")
                            return match_url
                    print(f"[DEBUG_LOGO] search_team_logo: Logo trovato per '{team_name}': {matches[0]} (fallback al primo)")
                    return matches[0] 
        print(f"[DEBUG_LOGO] search_team_logo: Nessun logo trovato per '{team_name}'.")
    except Exception as e:
        print(f"[!] Errore nella ricerca del logo per '{team_name}': {e}")
    return None

def download_rbtv77_html_files(base_git_url, sport_paths_dict, local_dir):
    """
    Downloads RBTv77 HTML files from a raw Git URL to a local directory.
    Overwrites existing files.
    """
    if not base_git_url or base_git_url == "https://raw.githubusercontent.com/tuo_utente/tuo_repo/main/download/":
         print("[AVVISO_LOGO] RBT_GIT_HTML_BASE_URL non configurato correttamente. Salto il download dei file RBTv77.")
         return

    print(f"\nDownloading RBTv77 HTML files from {base_git_url} to {local_dir}...")
    os.makedirs(local_dir, exist_ok=True) # Ensure local directory exists

    # Ensure base_git_url ends with a slash
    base_git_url = base_git_url if base_git_url.endswith('/') else base_git_url + '/'

    download_count = 0
    for sport_key, path_segment in sport_paths_dict.items():
        # Construct the remote filename based on the path segment
        filename = f"rbtv77_{path_segment.strip('/').replace('.html', '').replace('/', '_')}.html"
        remote_url = f"{base_git_url}{filename}"
        local_path = os.path.join(local_dir, filename)

        try:
            print(f"  Downloading {remote_url}...")
            time.sleep(0.5) # Add a small delay to avoid hitting rate limits
            response = requests.get(remote_url, headers=headers, timeout=HTTP_REQUEST_TIMEOUT)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"  Successfully downloaded and saved {filename}")
            download_count += 1

        except requests.exceptions.RequestException as e_req:
            print(f"  Error downloading {remote_url}: {e_req}")
        except Exception as e_gen:
            print(f"  Generic error saving {local_path}: {e_gen}")

    print(f"Finished downloading RBTv77 HTML files. Downloaded {download_count} files.")

def _get_rbtv77_local_page_path(sport_key, event_name):
    """Determina il percorso del file HTML locale di rbtv77.com per lo sport specificato,
    assumendo che sia stato scaricato in RBT_PAGES_DIR_ITALOG."""
    # Questa funzione ora costruisce un percorso locale, non un URL remoto.
    # RBT_GIT_HTML_BASE_URL non è più usato qui.

    normalized_sport_key = sport_key.lower()
    filename_base = None

    if normalized_sport_key in RBT_SPORT_PATHS:
        filename_base = RBT_SPORT_PATHS[normalized_sport_key].strip('/').replace('.html', '').replace('/', '_')
    else:
        for dict_key, path_segment in RBT_SPORT_PATHS.items():
            if dict_key in normalized_sport_key or normalized_sport_key in dict_key:
                filename_base = path_segment.strip('/').replace('.html', '').replace('/', '_')
                break
        if not filename_base: # Fallback basato sul nome dell'evento se lo sport non mappa direttamente
            event_name_lower = event_name.lower()
            for keyword, path_segment in RBT_SPORT_PATHS.items():
                if keyword in event_name_lower:
                    filename_base = path_segment.strip('/').replace('.html', '').replace('/', '_')
                    break
    if filename_base:

        return os.path.join(RBT_PAGES_DIR_ITALOG, f"rbtv77_{filename_base}.html")

    return None # Nessun file HTML corrispondente trovato

def _parse_rbtv77_html_content(html_content, event_name, team1_norm, team2_norm, team1_original=None, team2_original=None):
    """Analizza l'HTML di rbtv77.com per trovare loghi corrispondenti."""
    print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Inizio parsing per evento: '{event_name}'. Team Originali: '{team1_original}' vs '{team2_original}'. Team Normalizzati: '{team1_norm}' vs '{team2_norm}'.")
    # Stampa i primi 1000 caratteri dell'HTML ricevuto per il debug
    print(f"[DEBUG_HTML_CONTENT] Primi 1000 caratteri di html_content prima dell'unescaping:\n{html_content[:1000]}\n")

    processed_html_content = html_content
    try:
        # Tenta prima di decodificare gli escape unicode (es. \u003c)
        if '\\u' in processed_html_content: # Controllo generico per escape unicode
            import codecs
            try:
                processed_html_content = codecs.decode(processed_html_content, 'unicode_escape')
                print("[DEBUG_HTML_CONTENT] Tentativo di unescape unicode effettuato con codecs.decode.")
            except Exception as e_unicode:
                print(f"[DEBUG_HTML_CONTENT] Errore durante unescape unicode con codecs: {e_unicode}. Provo con html.unescape.")
                # Fallback a html.unescape se codecs.decode fallisce o non è il tipo giusto di escape
                processed_html_content = html.unescape(html_content)
        else:
            # Se non ci sono probabili escape unicode, usa html.unescape per entità come &lt;, &amp;
            processed_html_content = html.unescape(html_content)
        print(f"[DEBUG_HTML_CONTENT] Primi 1000 caratteri di processed_html_content dopo l'unescaping:\n{processed_html_content[:1000]}\n")
        soup = BeautifulSoup(processed_html_content, 'html.parser')
    except Exception as e_bs_init:
        print(f"[!] Errore durante la pre-elaborazione HTML o l'inizializzazione di BeautifulSoup: {e_bs_init}")
        return None, None

    event_containers = soup.find_all('div', class_='PefrsX') 
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
                       (logo_img['src'] if logo_img and logo_img.get('src') else None) # Changed from logo_img.src to logo_img.get('src')
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
            team1_search_terms = list(set(term for term in team1_search_terms if term))

            team2_search_terms = get_search_terms(team2_original, team2_norm)
            team2_search_terms = list(set(term for term in team2_search_terms if term))

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
                                        term in name_b.lower() or term in name_b_last_word_generic or \
                                        term in event_title_on_site.lower() for term in search_terms_generic) and logo_a_url:
            print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Corrispondenza evento singolo/generico trovata su RBTv77: {event_name} -> {name_a} (logo: {logo_a_url})")
            if name_b and logo_b_url: return logo_a_url, logo_b_url
            return logo_a_url, None
    print(f"[DEBUG_LOGO] _parse_rbtv77_html_content: Nessuna corrispondenza trovata per '{event_name}'.")
    return None, None

def _scrape_rbtv77(event_name, sport_key, team1_original, team2_original, team1_norm, team2_norm, cache_key):
    """Legge un file HTML locale di RBTv77 (precedentemente scaricato) e cerca i loghi."""
    local_html_path = _get_rbtv77_local_page_path(sport_key, event_name)
    print(f"[DEBUG_LOGO] _scrape_rbtv77: Tentativo di scraping RBTv77 per '{event_name}', sport '{sport_key}'. Percorso HTML locale: '{local_html_path}'")

    if not local_html_path:
        print(f"[DEBUG_LOGO] _scrape_rbtv77: Nessun percorso HTML locale determinato per sport '{sport_key}' ed evento '{event_name}'.")
        return None

    if not os.path.exists(local_html_path):
        print(f"[DEBUG_LOGO] _scrape_rbtv77: File HTML locale RBTv77 non trovato: '{local_html_path}'")
        return None
    try:
        with open(local_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            logo1_src_url, logo2_src_url = _parse_rbtv77_html_content(
                html_content, event_name,
                team1_norm, team2_norm,
                team1_original, team2_original)
            local_logo_path = None # Percorso locale dove il logo combinato/singolo viene salvato
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

def normalize_team_name(team_name):
    words_to_remove = ["calcio", "fc", "club", "united", "city", "ac", "sc", "sport", "team", "ssc", "as", "cf", "uc", "us", "gs", "ss", "rl", "rc"]
    name_no_punctuation = re.sub(r'[^\w\s]', '', team_name)
    normalized_name = ' '.join(word for word in name_no_punctuation.split() if word.lower() not in words_to_remove)
    return normalized_name.strip()

def get_dynamic_logo(event_name, sport_key):
    """
    Cerca il logo per un evento seguendo una priorità rigorosa:
    1. Cache in memoria (LOGO_CACHE)
    2. File locale (guardacalcio_image_links.txt) - solo se trova ENTRAMBI i team con nome ESATTO
    3. Analisi file HTML locali RBTv77 - solo se trova ENTRAMBI i team con nome ESATTO
    4. Per eventi singoli (senza "vs"): Ricerca con Bing Image Search (attualmente disabilitata)
    5. Logo di default statico per tutti gli altri casi
    """
    print(f"[DEBUG_LOGO] get_dynamic_logo: Inizio ricerca logo per evento: '{event_name}', sport: '{sport_key}'")
    event_parts = event_name.split(':', 1)
    teams_string = event_parts[1].strip() if len(event_parts) > 1 else event_parts[0].strip()

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
        clean_event_name_for_cache = re.sub(r'\s*\(\d{1,2}:\d{2}\)\s*$', '', event_name)
        if ':' in clean_event_name_for_cache:
            clean_event_name_for_cache = clean_event_name_for_cache.split(':', 1)[1].strip()
        cache_key = clean_event_name_for_cache
        is_vs_event = False

        if cache_key in LOGO_CACHE:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato in cache: evento singolo '{cache_key}'")
            return LOGO_CACHE[cache_key]

    load_local_logos()
    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo file locale (corrispondenza esatta VS) per: {is_vs_event}, team1: {team1}, team2: {team2}")
    if LOCAL_LOGO_CACHE and is_vs_event and team1 and team2:
        team1_normalized_local = team1.lower().replace(" ", "-")
        team2_normalized_local = team2.lower().replace(" ", "-")

        for logo_url_local in LOCAL_LOGO_CACHE:
            logo_url_lower = logo_url_local.lower()
            filename = logo_url_local.split('/')[-1].lower()
            if (team1_normalized_local in filename and team2_normalized_local in filename):
                print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato in file locale: logo combinato per '{cache_key}' -> {logo_url_local}")
                if cache_key:
                    LOGO_CACHE[cache_key] = logo_url_local
                return logo_url_local

    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo RBTv77 per VS event: {is_vs_event}, team1: {team1}, team2: {team2}")
    if is_vs_event and team1 and team2:
        team1_normalized_rbt = normalize_team_name(team1)
        team2_normalized_rbt = normalize_team_name(team2)

        if "bayern" in team1.lower(): team1_normalized_rbt = "Bayern"
        if "bayern" in team2.lower(): team2_normalized_rbt = "Bayern"
        if "internazionale" in team1.lower() or "inter" in team1.lower(): team1_normalized_rbt = "Inter"
        if "internazionale" in team2.lower() or "inter" in team2.lower(): team2_normalized_rbt = "Inter"

        rbtv77_logo = _scrape_rbtv77(event_name, sport_key, team1, team2, team1_normalized_rbt, team2_normalized_rbt, cache_key)
        if rbtv77_logo:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Trovato da RBTv77: logo combinato per '{cache_key}' -> {rbtv77_logo}")
            return rbtv77_logo

    print(f"[DEBUG_LOGO] get_dynamic_logo: Controllo Bing per evento singolo: {not is_vs_event}")
    if not is_vs_event: # Logica Bing (attualmente disabilitata nel flusso)
        print(f"[DEBUG_LOGO] get_dynamic_logo: Evento singolo rilevato, tentativo Bing per: {event_name}")
        try:
            logo_result = None # Chiamata a _search_bing_fallback(event_name) rimossa come da italog.py
            if logo_result:
                print(f"[DEBUG_LOGO] get_dynamic_logo: Logo trovato con Bing per evento singolo '{cache_key}': {logo_result}")
                if cache_key:
                    LOGO_CACHE[cache_key] = logo_result
                return logo_result
        except Exception as e:
            print(f"[DEBUG_LOGO] get_dynamic_logo: Errore durante il fallback a Bing per {event_name}: {e}")

    print(f"[DEBUG_LOGO] get_dynamic_logo: Nessun logo specifico trovato per '{event_name}', uso logo di default statico.")
    if cache_key:
        LOGO_CACHE[cache_key] = LOGO # LOGO è la costante definita globalmente
    return LOGO

def generate_unique_ids(count, seed=42):
    random.seed(seed)
    return [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(count)]

def loadJSON(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

# Modify the existing get_stream_link function to use the new logic
def get_stream_link(dlhd_id, event_name="", channel_name="", max_retries=3):
    print(f"Getting stream link for channel ID: {dlhd_id} - {event_name} on {channel_name}...")

    raw_m3u8_url_found = None
    daddy_headers_str = "&h_user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    attempted_urls_for_id_live = [] # Initialize here for all live discovery paths

    # 1. Check pre-fetched cache first
    raw_m3u8_url_found = STREAM_LOCATION_CACHE.get(dlhd_id)

    if raw_m3u8_url_found:
        print(f"[✓] Stream for ID {dlhd_id} found in pre-fetch cache: {raw_m3u8_url_found}")
    else: # Not in pre-fetch cache
        if not dlhd_id.startswith(str(uuid.uuid4())[:5]): # Avoid live discovery for generated UUIDs if they are identifiable
            print(f"[!] ID {dlhd_id} not in pre-fetch cache or is a UUID. Attempting live discovery...")
            # Fallback to original discovery logic
            is_tennis_channel = channel_name and ("Tennis Stream" in channel_name or "Tennis Channel" in channel_name)
            should_try_tennis_url = is_tennis_channel or \
                                    (dlhd_id.startswith("15") and len(dlhd_id) == 4)

            if should_try_tennis_url:
                if not is_tennis_channel and dlhd_id.startswith("15") and len(dlhd_id) == 4:
                    print(f"[INFO] Channel ID {dlhd_id} matches 15xx pattern. Attempting tennis-specific URL (live).")
                if len(dlhd_id) >= 2:
                    # Modifica per rimuovere lo zero iniziale se il numero è < 10
                    last_digits_str = dlhd_id[-2:]
                    try:
                        last_digits_int = int(last_digits_str)
                        tennis_stream_path = f"wikiten{last_digits_int}/mono.m3u8" # Es. wikiten5/mono.m3u8
                    except ValueError: # Fallback se non è un numero, anche se zfill(2) dovrebbe prevenirlo
                        tennis_stream_path = f"wikiten{last_digits_str.zfill(2)}/mono.m3u8" # Es. wikiten05/mono.m3u8
                    candidate_url_tennis = f"{WIKIHZ_TENNIS_BASE_URL.rstrip('/')}/{tennis_stream_path.lstrip('/')}"
                    attempted_urls_for_id_live.append(candidate_url_tennis)
                    try:
                        response = requests.get(candidate_url_tennis, stream=True, timeout=HTTP_REQUEST_TIMEOUT) # Changed candidate_url to candidate_url_tennis
                        if response.status_code == 200:
                            print(f"[✓] Stream TENNIS (or 15xx ID) found for channel ID {dlhd_id} at: {candidate_url_tennis} (live discovery)")
                            raw_m3u8_url_found = candidate_url_tennis # Changed candidate_url to candidate_url_tennis
                        response.close()
                    except requests.exceptions.RequestException: pass
                else:
                    print(f"[WARN] Channel ID {dlhd_id} is too short for tennis logic (live discovery).")

            if not raw_m3u8_url_found: # Only if tennis check failed or wasn't applicable
                for base_url in NEW_KSO_BASE_URLS:
                    stream_path = f"premium{dlhd_id}/mono.m3u8"
                    candidate_url_kso = f"{base_url.rstrip('/')}/{stream_path.lstrip('/')}"
                    attempted_urls_for_id_live.append(candidate_url_kso)
                    try:
                        response = requests.get(candidate_url_kso, stream=True, timeout=HTTP_REQUEST_TIMEOUT)
                        if response.status_code == 200:
                            print(f"[✓] Stream found for channel ID {dlhd_id} at: {candidate_url_kso} (live discovery)")
                            raw_m3u8_url_found = candidate_url_kso # Changed candidate_url to candidate_url_kso
                            response.close(); break
                        response.close()
                    except requests.exceptions.RequestException: pass

            if raw_m3u8_url_found:
                STREAM_LOCATION_CACHE[dlhd_id] = raw_m3u8_url_found # Cache it if found via fallback live discovery
            else:
                print(f"[✗] No stream found for channel ID {dlhd_id} after live discovery.")
                return None
        else: # ID was likely a UUID, and not found in cache.
            print(f"[✗] ID {dlhd_id} (likely UUID) not found in cache and skipped live discovery.")
            return None

    # Apply proxy and headers if raw_m3u8_url_found is not None
    if raw_m3u8_url_found:
        url_with_headers = raw_m3u8_url_found + daddy_headers_str
        # get_stream_link will now consistently return the url with daddy_headers_str.
        return url_with_headers

    return None # Should be caught earlier if raw_m3u8_url_found was None

# --- Functions for Fetching and Parsing Index Pages ---
def fetch_and_parse_single_index_page(base_url, stream_type, http_headers):
    """
    Fetches and parses a single index page (e.g., a KSO base URL or WIKIHZ base URL).
    Populates INDEXED_KSO_PATHS or INDEXED_TENNIS_PATHS.
    stream_type: 'kso' or 'tennis'
    """
    print(f"Fetching index page: {base_url} for type: {stream_type}")
    try:
        response = requests.get(base_url, headers=http_headers, timeout=HTTP_REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)

        count_added = 0
        for link in links:
            href = link.get('href')
            if not href or href == "../" or href == "..": # Ignore irrelevant links
                continue

            path_segment_from_index = href.strip('/') # e.g., "premium123" or "wikiten5"

            if stream_type == 'kso':
                match = re.fullmatch(r'premium(\d+)', path_segment_from_index)
                if match:
                    stream_id = match.group(1)
                    # Store the first base_url where this stream_id is found
                    if stream_id not in INDEXED_KSO_PATHS:
                        INDEXED_KSO_PATHS[stream_id] = (base_url, href) # Store original href with slashes if present
                        count_added +=1
            elif stream_type == 'tennis':
                match = re.fullmatch(r'wikiten(\d+)', path_segment_from_index)
                if match:
                    # For tennis, the ID is the numeric part, e.g., '5' from 'wikiten5'
                    tennis_short_id = match.group(1)
                    if tennis_short_id not in INDEXED_TENNIS_PATHS:
                        INDEXED_TENNIS_PATHS[tennis_short_id] = href # Store original href
                        count_added += 1
        if count_added > 0:
            print(f"  Added {count_added} unique stream paths from {base_url}")

    except requests.exceptions.RequestException as e_req:
        print(f"  Error fetching or parsing index page {base_url}: {e_req}")
    except Exception as e_gen:
        print(f"  Generic error processing index page {base_url}: {e_gen}")

def fetch_all_index_pages():
    """Calls fetch_and_parse_single_index_page for all relevant base URLs."""
    print("\nFetching and parsing all index pages for stream discovery...")

    # For KSO streams (iterate through each defined base URL)
    for kso_base_url in NEW_KSO_BASE_URLS:
        fetch_and_parse_single_index_page(kso_base_url, 'kso', headers) # Assuming 'headers' is global

    # For Tennis streams (single base URL)
    fetch_and_parse_single_index_page(WIKIHZ_TENNIS_BASE_URL, 'tennis', headers)

    print("Finished fetching and parsing index pages.")
    print(f"  Total unique KSO stream IDs found in indices: {len(INDEXED_KSO_PATHS)}")
    print(f"  Total unique Tennis stream IDs found in index: {len(INDEXED_TENNIS_PATHS)}")
    # print(f"DEBUG KSO Index: {INDEXED_KSO_PATHS}") # Optional: for debugging
    # print(f"DEBUG Tennis Index: {INDEXED_TENNIS_PATHS}") # Optional: for debugging
# --- End of Index Page Functions ---


def _discover_single_id_location(id_info_tuple):
    """
    Worker for pre-caching. Finds the raw m3u8 URL for a single dlhd_id.
    id_info_tuple: (dlhd_id, channel_name_for_tennis_logic)
    Returns: (dlhd_id, found_raw_url) or (dlhd_id, None)
    """
    dlhd_id, channel_name_for_tennis_logic = id_info_tuple
    raw_m3u8_url = None
    attempted_urls_for_id_precaching = []

    # --- 1. Try Tennis URL Logic (using index first, then direct if needed) ---
    is_tennis_channel = channel_name_for_tennis_logic and \
                             ("Tennis Stream" in channel_name_for_tennis_logic or \
                              "Tennis Channel" in channel_name_for_tennis_logic)

    # Determine the potential short ID for tennis lookup (e.g., "5" from "wikiten5")
    # This could be the dlhd_id itself if it's short, or derived from it.
    potential_tennis_short_id = None
    if dlhd_id.isdigit(): # If dlhd_id is purely numeric
        if len(dlhd_id) <= 2: # e.g. "5", "12"
            potential_tennis_short_id = dlhd_id
        elif len(dlhd_id) > 2 : # e.g. "1505" -> try "05" -> "5"
            potential_tennis_short_id = dlhd_id[-2:].lstrip('0') if len(dlhd_id[-2:]) > 0 else dlhd_id[-1:]

    tennis_path_segment_from_index = None
    if potential_tennis_short_id and potential_tennis_short_id in INDEXED_TENNIS_PATHS:
        tennis_path_segment_from_index = INDEXED_TENNIS_PATHS[potential_tennis_short_id]

    if tennis_path_segment_from_index:
        # Path found in index, construct URL and verify
        # tennis_path_segment_from_index includes "wikitenX", ensure no double "wikitenX"
        candidate_url_tennis = f"{WIKIHZ_TENNIS_BASE_URL.rstrip('/')}/{tennis_path_segment_from_index.strip('/')}/mono.m3u8"
        attempted_urls_for_id_precaching.append(f"[TENNIS_INDEX] {candidate_url_tennis}")
        try:
            response = requests.get(candidate_url_tennis, stream=True, timeout=HTTP_REQUEST_TIMEOUT)
            if response.status_code == 200:
                raw_m3u8_url = candidate_url_tennis
            response.close()
        except requests.exceptions.RequestException: pass

    # Fallback to original tennis logic if not found via index or if index check failed,
    # and if it's a likely tennis channel by name or ID pattern.
    if not raw_m3u8_url and (is_tennis_channel or (dlhd_id.startswith("15") and len(dlhd_id) == 4)):
        # This part of the original logic tries to guess the path based on dlhd_id's last digits
        # This might be redundant if the index is comprehensive, but keep as fallback.
        guessed_tennis_short_id_str = dlhd_id[-2:] # e.g. "05" from "1505"
        try:
            guessed_tennis_short_id_int = int(guessed_tennis_short_id_str) # Convert to int to remove leading zero for path
            tennis_stream_path_guessed = f"wikiten{guessed_tennis_short_id_int}/mono.m3u8"
        except ValueError: # Fallback if not purely numeric
            try:
                # Try with zfill if original was like "5" -> "05"
                tennis_stream_path_guessed = f"wikiten{guessed_tennis_short_id_str.zfill(2)}/mono.m3u8"
            except: # Ultimate fallback, probably won't work
                tennis_stream_path_guessed = f"wikiten{guessed_tennis_short_id_str}/mono.m3u8"

        candidate_url_tennis_direct = f"{WIKIHZ_TENNIS_BASE_URL.rstrip('/')}/{tennis_stream_path_guessed.lstrip('/')}"
        # Avoid re-attempt if index already tried this exact URL (unlikely to be exact match here due to path construction)
        is_already_attempted = any(candidate_url_tennis_direct in url for url in attempted_urls_for_id_precaching if "[TENNIS_INDEX]" in url)
        if not is_already_attempted:
             attempted_urls_for_id_precaching.append(f"[TENNIS_DIRECT_GUESS] {candidate_url_tennis_direct}")
             try:
                 response = requests.get(candidate_url_tennis_direct, stream=True, timeout=HTTP_REQUEST_TIMEOUT)
                 if response.status_code == 200:
                     raw_m3u8_url = candidate_url_tennis_direct
                 response.close()
             except requests.exceptions.RequestException: pass

    # --- 2. Try Standard KSO Base URLs Logic (using index first, then direct) ---
    if not raw_m3u8_url:
        indexed_kso_info = INDEXED_KSO_PATHS.get(dlhd_id) # dlhd_id is the key like "123"
        if indexed_kso_info:
            kso_base_url_from_index, kso_path_segment_from_index = indexed_kso_info
            # kso_path_segment_from_index is like "premium123/" or "premium123"
            candidate_url_kso_indexed = f"{kso_base_url_from_index.rstrip('/')}/{kso_path_segment_from_index.strip('/')}/mono.m3u8"
            attempted_urls_for_id_precaching.append(f"[KSO_INDEX] {candidate_url_kso_indexed}")
            try:
                response = requests.get(candidate_url_kso_indexed, stream=True, timeout=HTTP_REQUEST_TIMEOUT)
                if response.status_code == 200:
                    raw_m3u8_url = candidate_url_kso_indexed
                response.close()
            except requests.exceptions.RequestException: pass

        # Fallback to original KSO direct attempts if not found via index or if index check failed
        if not raw_m3u8_url:
            for base_url_kso_fallback in NEW_KSO_BASE_URLS:
                stream_path_direct = f"premium{dlhd_id}/mono.m3u8"
                candidate_url_kso_direct = f"{base_url_kso_fallback.rstrip('/')}/{stream_path_direct.lstrip('/')}"

                # Avoid re-attempting if this exact URL was already tried via index
                is_already_attempted_via_index = False
                if indexed_kso_info:
                    # Reconstruct the URL that would have been tried from index to compare
                    idx_base, idx_path = indexed_kso_info
                    if idx_base == base_url_kso_fallback and f"{idx_path.strip('/')}/mono.m3u8" == stream_path_direct:
                         is_already_attempted_via_index = True

                if not is_already_attempted_via_index:
                    attempted_urls_for_id_precaching.append(f"[KSO_DIRECT_GUESS] {candidate_url_kso_direct}")
                    try:
                        response = requests.get(candidate_url_kso_direct, stream=True, timeout=HTTP_REQUEST_TIMEOUT)
                        if response.status_code == 200:
                            raw_m3u8_url = candidate_url_kso_direct
                            response.close(); break # Found with this fallback base_url
                        response.close()
                    except requests.exceptions.RequestException: pass

    if not raw_m3u8_url:
        # This print will help confirm if we are reaching this point for all IDs
        # print(f"  [DEBUG _discover_single_id_location] ID {dlhd_id} - No raw_m3u8_url found. Attempted: {attempted_urls_for_id_precaching}")
        return (dlhd_id, None) # Ensure a tuple is always returned
    return (dlhd_id, raw_m3u8_url) # Return the found URL with the ID

def populate_stream_location_cache(ids_to_probe_with_names):
    """
    Populates STREAM_LOCATION_CACHE by discovering stream URLs for given IDs in parallel.
    ids_to_probe_with_names: list of (dlhd_id, channel_name_for_tennis_logic) tuples
    """
    if not ids_to_probe_with_names:
        print("No unique IDs provided for cache population.")
        return

    print(f"Pre-populating stream location cache for {len(ids_to_probe_with_names)} unique IDs...")

    MAX_CACHE_WORKERS = 20 # Adjust as needed, can be higher for I/O bound tasks
    processed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CACHE_WORKERS) as executor:
        future_to_id_info = {executor.submit(_discover_single_id_location, id_info): id_info for id_info in ids_to_probe_with_names}
        for future in concurrent.futures.as_completed(future_to_id_info):
            id_info_tuple = future_to_id_info[future]
            original_dlhd_id = id_info_tuple[0]
            processed_count += 1
            try:
                discovered_id, found_url = future.result()
                if found_url:
                    STREAM_LOCATION_CACHE[discovered_id] = found_url
                    # Optional: print(f"  [CACHE POPULATED] ID {discovered_id} found at {found_url} ({processed_count}/{len(ids_to_probe_with_names)})")
                # else:
                    # Optional: print(f"  [CACHE POPULATE FAILED] ID {discovered_id} not found by pre-fetcher. ({processed_count}/{len(ids_to_probe_with_names)})")
            except Exception as exc:
                print(f"  [CACHE POPULATE ERROR] ID {original_dlhd_id} generated an exception: {exc} ({processed_count}/{len(ids_to_probe_with_names)})")
    print(f"Stream location cache populated. Found locations for {len(STREAM_LOCATION_CACHE)} out of {len(ids_to_probe_with_names)} unique IDs.")

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

def should_include_channel(channel_name, event_name, sport_key):
    """Check if channel should be included based on keywords"""
    combined_text = (channel_name + " " + event_name + " " + sport_key).lower()

    # Check if any exclusion keyword is present in the combined text
    for keyword in EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO:
        if keyword.lower() in combined_text:
            return False  # Exclude the channel if keyword is found

    return True  # Include the channel if no exclusion keywords are found

def fetch_stream_details_worker(task_args):
    """
    Worker function to fetch stream link and prepare M3U8 line data.
    task_args is a tuple containing:
    (channelID, event_details, channel_name_str_for_get_link,
     tvg_id_val, tvg_name, event_logo, italian_sport_key, channel_name_str_for_extinf)
    """
    channelID, event_details, channel_name_str_for_get_link, \
    tvg_id_val, tvg_name, event_logo, italian_sport_key, \
    channel_name_str_for_extinf = task_args

    stream_url_dynamic_with_headers = get_stream_link(channelID, event_details, channel_name_str_for_get_link)

    if stream_url_dynamic_with_headers:
        # Estrai l'URL grezzo prima degli header aggiunti (se presenti)
        raw_stream_url_part = stream_url_dynamic_with_headers.split("&h_user-agent=")[0]
        return (channelID, raw_stream_url_part, tvg_id_val, tvg_name, event_logo,
                italian_sport_key, channel_name_str_for_extinf)
    return None

def fetch_and_parse_247_channels():
    """Fetches and parses 24/7 channel data from daddylive.dad."""
    all_247_channels_info = []
    try:
        print(f'Downloading {DADDY_LIVE_CHANNELS_URL} for 24/7 channels...')
        response = requests.get(DADDY_LIVE_CHANNELS_URL, headers=headers, timeout=HTTP_REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)

        for link in links:
            if "italy" in link.text.lower():  # Filter for "Italy"
                href = link['href']
                match_re = re.search(r'stream-(\d+)\.php', href)
                if match_re:
                    stream_number = match_re.group(1)
                    original_stream_name = link.text.strip()

                    # Clean channel name as in 247m3u.py
                    stream_name_cleaned = original_stream_name
                    replacements = {
                        "Italy": "", "ITALY": "",
                        "(251)": "", "(252)": "", "(253)": "", "(254)": "",
                        "(255)": "", "(256)": "", "(257)": "",
                        "HD+": "", "8": "" # "8" was in 247m3u.py, check if still needed
                    }
                    for old, new in replacements.items():
                        stream_name_cleaned = stream_name_cleaned.replace(old, new)
                    stream_name_cleaned = stream_name_cleaned.strip()

                    # If cleaning results in an empty name, use a placeholder or original
                    if not stream_name_cleaned:
                        stream_name_cleaned = f"Channel {stream_number}"

                    all_247_channels_info.append({
                        'id': stream_number,
                        'name': stream_name_cleaned,
                        'original_name': original_stream_name
                    })
        print(f"Found {len(all_247_channels_info)} potential 24/7 'Italy' channels from HTML page.")
    except requests.exceptions.RequestException as e_req:
        print(f'Error downloading or parsing 24/7 channels page: {e_req}')
    except Exception as e_gen:
        print(f'Generic error in fetch_and_parse_247_channels: {e_gen}')
    return all_247_channels_info

def prepare_247_channel_tasks(parsed_247_channels_list):
    """Prepares task arguments for 24/7 channels for the ThreadPoolExecutor."""
    tasks = []
    processed_247_ids_in_this_batch = set() # To avoid duplicates from the 24/7 list itself
    # Add DAZN 1 manually first
    dazn1_id = "877"
    dazn1_name = "DAZN 1"
    dazn1_original_name = "DAZN 1" # For get_stream_link context
    dazn1_logo = STATIC_LOGOS_247.get(dazn1_name.lower(), DEFAULT_247_LOGO)
    dazn1_tvg_id = STATIC_TVG_IDS_247.get(dazn1_name.lower(), dazn1_name)
    dazn1_group = STATIC_CATEGORIES_247.get(dazn1_name.lower(), DEFAULT_247_GROUP)
    tasks.append((
        dazn1_id, dazn1_name, dazn1_original_name, dazn1_tvg_id, dazn1_name,
        dazn1_logo, dazn1_group, f"{dazn1_name} (D)" # Changed suffix here
    ))
    processed_247_ids_in_this_batch.add(dazn1_id)
    for ch_info in parsed_247_channels_list:
        channel_id = ch_info['id']
        if channel_id not in processed_247_ids_in_this_batch: # Removed check against event_channel_ids_to_skip
            channel_name = ch_info['name']
            original_channel_name = ch_info['original_name']
            tvg_logo = STATIC_LOGOS_247.get(channel_name.lower().strip(), DEFAULT_247_LOGO)
            tvg_id = STATIC_TVG_IDS_247.get(channel_name.lower().strip(), channel_name)
            group_title = STATIC_CATEGORIES_247.get(channel_name.lower().strip(), DEFAULT_247_GROUP)
            tasks.append((
                channel_id, channel_name, original_channel_name, tvg_id, channel_name,
                tvg_logo, group_title, f"{channel_name} (D)" # Changed suffix here
            ))
            processed_247_ids_in_this_batch.add(channel_id)
        elif channel_id in processed_247_ids_in_this_batch:
            print(f"Skipping 24/7 channel {ch_info['name']} (ID: {channel_id}) as it was already added in this 24/7 batch.")
    return tasks

def generate_m3u_playlist():
    # Inizializza unique_ids_for_precaching qui, prima del suo primo utilizzo.
    unique_ids_for_precaching = {}
    dadjson = loadJSON(DADDY_JSON_FILE)
    for day, day_data in dadjson.items():
        try:
            for sport_key, sport_events in day_data.items():
                for game in sport_events:
                    for channel_data_item in game.get("channels", []):
                        channel_id_str = None
                        channel_name_for_tennis = ""

                        if isinstance(channel_data_item, dict):
                            if "channel_id" in channel_data_item:
                                channel_id_str = str(channel_data_item['channel_id'])
                            if "channel_name" in channel_data_item:
                                channel_name_for_tennis = channel_data_item["channel_name"]
                            # else, channel_name_for_tennis remains empty
                        elif isinstance(channel_data_item, str) and channel_data_item.isdigit():
                            channel_id_str = channel_data_item
                            # channel_name_for_tennis remains empty

                        if channel_id_str:
                            if channel_id_str not in unique_ids_for_precaching:
                                unique_ids_for_precaching[channel_id_str] = channel_name_for_tennis
                            # If already present, we could update channel_name_for_tennis if the new one is more specific,
                            # but for simplicity, first encountered name is fine for the heuristic.
        except (KeyError, TypeError) as e:
            print(f"KeyError/TypeError during ID collection for pre-caching: {e}")
            pass

    # Fetch and parse index pages ONCE before starting any stream discovery
    fetch_all_index_pages()

    # unique_ids_for_precaching era inizializzata qui, spostata sopra.
    print("Collecting unique channel IDs for pre-caching (Events)...")
    print("Collecting unique channel IDs for pre-caching (24/7 Channels)...")
    parsed_247_channels_data = fetch_and_parse_247_channels()
    for ch_info in parsed_247_channels_data:
        ch_id = ch_info['id']
        ch_name_for_tennis_logic = ch_info.get('original_name', ch_info['name']) # Use original name for more context
        if ch_id not in unique_ids_for_precaching:
            unique_ids_for_precaching[ch_id] = ch_name_for_tennis_logic

    # Add DAZN1 ID for pre-caching
    dazn1_id_static = "877"
    dazn1_name_static = "DAZN 1"
    if dazn1_id_static not in unique_ids_for_precaching:
        unique_ids_for_precaching[dazn1_id_static] = dazn1_name_static

    ids_to_probe_tuples = [(id_val, name_val) for id_val, name_val in unique_ids_for_precaching.items()]
    populate_stream_location_cache(ids_to_probe_tuples)

    # Remove existing M3U8 file if it exists and write header
    if os.path.exists(M3U8_OUTPUT_FILE):
        os.remove(M3U8_OUTPUT_FILE)
    with open(M3U8_OUTPUT_FILE, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')

    # Counters
    total_events_in_json = 0
    skipped_events_by_category_filter = 0

    # Define categories to exclude for events
    excluded_categories = [
        "TV Shows", "Cricket", "Aussie rules", "Snooker", "Baseball",
        "Biathlon", "Cross Country", "Horse Racing", "Ice Hockey",
        "Waterpolo", "Golf", "Darts", "Badminton", "Handball", "Squash"
    ]

    # Initialize counters and task list for events before the loop
    processed_event_channels_count = 0
    excluded_event_channels_by_keyword = 0
    tasks_for_workers = [] 

    # First pass to gather category statistics
    category_stats = {} # For events
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

    # Generate unique IDs for channels (if needed for fallback, though IDs from JSON/HTML are primary)
    # unique_ids_fallback = generate_unique_ids(NUM_CHANNELS) # This seems unused if IDs are from source

    # 4. Process and write 24/7 channels FIRST
    print("\nProcessing 24/7 Channels...")
    tasks_247 = prepare_247_channel_tasks(parsed_247_channels_data) # No longer pass event_channel_ids_processed_and_written

    processed_247_channels_count = 0
    MAX_WORKERS = 10 # Define MAX_WORKERS here or make it a global constant
    if tasks_247:
        print(f"Fetching stream details for {len(tasks_247)} 24/7 channels...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results_247 = list(executor.map(fetch_stream_details_worker, tasks_247))

        with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file: # Append 24/7 channels
            for result_item in results_247:
                if result_item:
                    # Il secondo elemento è l'URL grezzo dello stream
                    _, raw_stream_url_247, tvg_id_val, tvg_name, event_logo, \
                    group_title_val, channel_name_str_for_extinf_247 = result_item

                    # URL-encode il raw_stream_url_247 per l'uso sicuro in un parametro query
                    safe_raw_url_247 = urllib.parse.quote_plus(raw_stream_url_247)
                    new_final_url_247 = f"{PZPROXY}/proxy?url={safe_raw_url_247}"

                    file.write(f'#EXTINF:-1 tvg-id="{tvg_id_val}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{group_title_val}",{channel_name_str_for_extinf_247}\n')
                    file.write(f"{new_final_url_247}\n\n")
                    processed_247_channels_count += 1
        print(f"Finished processing 24/7 channels. Added {processed_247_channels_count} 24/7 channels.")
    else:
        print("No 24/7 channel tasks to process.")

    print("\nProcessing Event Channels from JSON...")
    for day, day_data in dadjson.items():
        try:
            # day_data is a dict where keys are sport_keys and values are lists of events
            for sport_key, sport_events in day_data.items():
                clean_sport_key = sport_key.replace("</span>", "").replace("<span>", "").strip()
                total_events_in_json += len(sport_events)

                # Skip only exact category matches
                if clean_sport_key in excluded_categories:
                    skipped_events_by_category_filter += len(sport_events)
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

                        # Derive channelID and channel_name for get_stream_link arguments
                        channelID_for_task = None
                        channel_name_for_get_link_arg = "" # For tennis heuristic in get_stream_link

                        if isinstance(channel, dict):
                            if "channel_id" in channel:
                                channelID_for_task = str(channel['channel_id'])
                            if "channel_name" in channel:
                                channel_name_for_get_link_arg = channel["channel_name"]
                            else: # dict but no channel_name
                                channel_name_for_get_link_arg = str(channel) # Fallback
                        elif isinstance(channel, str): # channel is a string
                            if channel.isdigit(): # Assume it's an ID
                                channelID_for_task = channel
                                channel_name_for_get_link_arg = f"Channel {channel}" # Placeholder name
                            else: # Assume it's a name, no ID from this structure
                                channel_name_for_get_link_arg = channel
                                # channelID_for_task remains None

                        if not channelID_for_task: # If no usable ID, generate UUID as per original logic
                            channelID_for_task = str(uuid.uuid4())
                            print(f"  Generated UUID {channelID_for_task} as fallback ID for channel: {channel}")

                        # Check if channel should be included based on keywords
                        if should_include_channel(channelName, event_details, clean_sport_key):
                            # channel_name_str_for_extinf is what appears after the comma in #EXTINF
                            # channel_name_str_for_extinf è quello che appare dopo la virgola in #EXTINF
                            if isinstance(channel, dict) and "channel_name" in channel:
                                channel_name_str_for_extinf = channel["channel_name"]
                            else:
                                channel_name_str_for_get_link = str(channel)
                                channel_name_str_for_extinf = str(channel)

                            time_only = time_str_cet if time_str_cet else "00:00"
                            tvg_name = f"{time_only} {event_details} - {day_num}/{month_num}/{year_short}"
                            event_logo = get_dynamic_logo(game["event"], clean_sport_key) # Usa la nuova funzione get_dynamic_logo
                            italian_sport_key = translate_sport_to_italian(clean_sport_key)
                            tvg_id_val = f"{event_name_short} - {event_details.split(':', 1)[1].strip() if ':' in event_details else event_details}"

                            tasks_for_workers.append((
                                channelID_for_task, event_details, channel_name_for_get_link_arg, # Use derived ID and name for get_stream_link
                                tvg_id_val, tvg_name, event_logo, italian_sport_key,
                                channel_name_str_for_extinf
                            ))
                        else:
                            excluded_event_channels_by_keyword +=1

        except KeyError as e:
            print(f"KeyError: {e} - Key may not exist in JSON structure")


    MAX_WORKERS = 10
    if tasks_for_workers:
        event_channel_ids_processed_and_written = set() # Store IDs of events written to M3U
        print(f"Fetching stream details for {len(tasks_for_workers)} event channels...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            event_results = list(executor.map(fetch_stream_details_worker, tasks_for_workers))

        with open(M3U8_OUTPUT_FILE, 'a', encoding='utf-8') as file: # Append event channels
            for result_item in event_results:
                if result_item:
                    original_channel_id, raw_stream_url, tvg_id_val, tvg_name, event_logo, \
                    italian_sport_key, channel_name_str_for_extinf = result_item

                    event_channel_ids_processed_and_written.add(original_channel_id) # Populate the set
                    
                    # URL-encode il raw_stream_url per l'uso sicuro in un parametro query
                    safe_raw_url = urllib.parse.quote_plus(raw_stream_url)
                    new_final_url = f"{PZPROXY}/proxy?url={safe_raw_url}"

                    file.write(f'#EXTINF:-1 tvg-id="{tvg_id_val}" tvg-name="{tvg_name}" tvg-logo="{event_logo}" group-title="{italian_sport_key}",{channel_name_str_for_extinf}\n')
                    file.write(f"{new_final_url}\n\n")
                    processed_event_channels_count += 1
        print(f"Finished processing event channels. Added {processed_event_channels_count} event channels.")
    else:
        event_channel_ids_processed_and_written = set() # Initialize empty if no event tasks
        print("No event channel tasks to process.")


    print(f"\n=== Processing Summary ===")
    print(f"Total events found in JSON: {total_events_in_json}")
    print(f"Events skipped due to category filters: {skipped_events_by_category_filter}")
    print(f"Event channels included in M3U8: {processed_event_channels_count}")
    print(f"Event channels excluded by keyword filter: {excluded_event_channels_by_keyword}")
    print(f"Keywords used for event channel exclusion: {EXCLUDE_KEYWORDS_FROM_CHANNEL_INFO}")
    print(f"---")
    print(f"24/7 channels (incl. DAZN1) processed for M3U8: {processed_247_channels_count}")
    total_channels_in_m3u8 = processed_event_channels_count + processed_247_channels_count
    print(f"---")
    print(f"Total channels in M3U8 ({M3U8_OUTPUT_FILE}): {total_channels_in_m3u8}")
    print(f"===========================\n")
    return total_channels_in_m3u8

def main():
    # Process events and generate M3U8
    download_rbtv77_html_files(RBT_GIT_HTML_BASE_URL, RBT_SPORT_PATHS, RBT_PAGES_DIR_ITALOG)

    total_processed_channels = generate_m3u_playlist()

    # Verify if any valid channels were created
    if total_processed_channels == 0:
        print(f"No valid channels found from events or 24/7 sources for {M3U8_OUTPUT_FILE}.")
    else:
        print(f"{M3U8_OUTPUT_FILE} generated with a total of {total_processed_channels} channels.")

if __name__ == "__main__":
    main()
