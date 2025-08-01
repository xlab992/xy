import os
from dotenv import load_dotenv
from pathlib import Path

def update_proxy_links(input_m3u8_filepath, output_m3u8_filepath, env_filepath):
    """
    Legge un file M3U8 di input, sostituisce un placeholder con un URL base dal file .env
    e scrive il risultato in un file M3U8 di output.
    """
    # Carica le variabili dal file .env specificato
    load_dotenv(dotenv_path=env_filepath)

    # Carica le configurazioni MFP/PSW primarie e secondarie
    mfp = os.getenv("MFP")
    psw = os.getenv("PSW")
    mfp2 = os.getenv("MFP2")
    psw2 = os.getenv("PSW2")

    # Validazione delle variabili d'ambiente necessarie
    if not mfp or not psw:
        print(f"Errore: Le variabili MFP e PSW devono essere impostate nel file {env_filepath}")
        return

    # Determina quali MFP/PSW utilizzare
    mfp_to_use = mfp
    psw_to_use = psw
    if mfp2 and psw2:  # Se MFP2 e PSW2 sono impostati e non vuoti
        print("Utilizzo MFP2 e PSW2 per i link MPD.")
        mfp_to_use = mfp2
        psw_to_use = psw2
    else:
        print("Utilizzo MFP e PSW primari per i link MPD.")

    # Costruisci la stringa di sostituzione per il placeholder
    # Il placeholder {PROXYMFPMPD} sarà sostituito da questa stringa base.
    # La parte "&d=..." ecc. è già presente nel file FILEmpd.m3u8.
    replacement_string = f"{mfp_to_use}/proxy/mpd/manifest.m3u8?api_password={psw_to_use}"
    print(f"Stringa di sostituzione per {{PROXYMFPMPD}}: {replacement_string}")

    # Configurazione per le sostituzioni
    placeholder = "{PROXYMFPMPD}" # Placeholder da cercare nel file di input
    lines_to_write = []
    updated_count = 0
    m3u8_path = Path(input_m3u8_filepath)

    try:
        with open(m3u8_path, 'r', encoding='utf-8') as f:
            lines = f.readlines() # Legge dal file di input

        for line_number, original_line in enumerate(lines, 1):
            stripped_line = original_line.strip()
            processed_line = original_line

            # Salta le righe vuote o le direttive M3U che non sono URL di stream
            if not stripped_line or stripped_line.startswith("#EXTM3U") or stripped_line.startswith("#EXTINF:"):
                lines_to_write.append(original_line)
                continue

            # Sostituisci il placeholder se presente
            if placeholder in stripped_line:
                # Sostituisce il placeholder con la stringa di base del proxy costruita
                # es. {PROXYMFPMPD}&d=... diventa https://server/proxy...?api_password=xxx&d=...
                modified_content = stripped_line.replace(placeholder, replacement_string)
                if modified_content != stripped_line:
                    processed_line = modified_content + '\n'
                    updated_count += 1

            lines_to_write.append(processed_line)

        # Scrivi le modifiche nel file di output, sovrascrivendolo
        with open(output_m3u8_filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines_to_write)

        if updated_count > 0:
            print(f"File {Path(output_m3u8_filepath).name} creato/aggiornato con successo. {updated_count} placeholder sostituiti.")
        else:
            print(f"Nessun placeholder '{placeholder}' da aggiornare trovato in {m3u8_path.name}.")

    except FileNotFoundError:
        print(f"Errore: Il file {m3u8_path} non è stato trovato.")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")

if __name__ == "__main__":
    import sys
    
    # Definisci i percorsi relativi allo script
    script_dir = Path(__file__).resolve().parent
    
    # File di input fisso
    input_m3u8_file = script_dir / "FILEmpd.m3u8" # Nome del file di input come specificato
    
    # File di output (può essere specificato come argomento o default a "mpd.m3u8")
    output_m3u8_filename = sys.argv[1] if len(sys.argv) > 1 else "mpd.m3u8"
    output_m3u8_file = script_dir / output_m3u8_filename
    env_file = script_dir / ".env"      # Assumendo che .env sia nella stessa cartella

    update_proxy_links(input_m3u8_file, output_m3u8_file, env_file)
