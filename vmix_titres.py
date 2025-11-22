import requests
import xml.etree.ElementTree as ET
import time

# ==============================================================================
# --- CONFIGURATION ---
# Modifiez les valeurs ci-dessous pour adapter le script à votre projet vMix
# ==============================================================================
CONFIG = {
    # Adresse IP et port de vMix
    "VMIX_URL": "http://192.168.209.241:8088/api/",
    
    # Nom ou numéro de l'entrée Titre à utiliser
    "TITLE_INPUT": "TitreMusique",
    
    # Numéro du canal d'Overlay (1, 2, 3, 4, etc.)
    "OVERLAY_CHANNEL": 2,
    
    # Noms des champs de texte (souvent "Headline.Text" ou "Description.Text")
    "NOW_PLAYING_FIELD": "Headline.Text",   # Pour le titre en cours
    "NEXT_UP_FIELD": "Description.Text"     # Pour le titre "À suivre"
}
# ==============================================================================
# --- FIN DE LA CONFIGURATION ---
# ==============================================================================

# Variables d’état (ne pas modifier)
last_title = ""
overlay_displayed = False
next_overlay_displayed = False
start_time = None
next_overlay_start = None

# --- Fonctions vMix (utilisent maintenant la CONFIG) ---

def update_gt_text(zone1="", zone2=""):
    """Met à jour les deux zones de texte du titre."""
    requests.get(CONFIG["VMIX_URL"], params={
        'Function': 'SetText',
        'Input': CONFIG["TITLE_INPUT"],
        'SelectedName': CONFIG["NOW_PLAYING_FIELD"],
        'Value': zone1
    })

    requests.get(CONFIG["VMIX_URL"], params={
        'Function': 'SetText',
        'Input': CONFIG["TITLE_INPUT"],
        'SelectedName': CONFIG["NEXT_UP_FIELD"],
        'Value': zone2
    })

def show_overlay():
    """Affiche le titre sur le canal d'overlay configuré."""
    function_name = f"OverlayInput{CONFIG['OVERLAY_CHANNEL']}In"
    requests.get(CONFIG["VMIX_URL"], params={'Function': function_name, 'Input': CONFIG["TITLE_INPUT"]})

def hide_overlay():
    """Masque le titre du canal d'overlay configuré."""
    function_name = f"OverlayInput{CONFIG['OVERLAY_CHANNEL']}Out"
    requests.get(CONFIG["VMIX_URL"], params={'Function': function_name, 'Input': CONFIG["TITLE_INPUT"]})

# --- Boucle Principale (Logique originale conservée) ---

def main_loop():
    global last_title, overlay_displayed, next_overlay_displayed, start_time, next_overlay_start
    print("Démarrage du script (version améliorée)...")

    while True:
        try:
            res = requests.get(CONFIG["VMIX_URL"])
            res.raise_for_status()
            root = ET.fromstring(res.text)

            videolist_found = False
            for input_el in root.findall(".//input"):
                if input_el.attrib.get("type") == "VideoList" and input_el.attrib.get("state") == "Running":
                    videolist_found = True
                    title = input_el.attrib.get("title")
                    position = int(input_el.attrib.get("position"))
                    duration = int(input_el.attrib.get("duration"))
                    list_items = input_el.find("list")

                    current_item = ""
                    next_item = ""
                    if list_items is not None:
                        items = list_items.findall("item")
                        for i in range(len(items)):
                            if items[i].attrib.get("selected") == "true":
                                current_item = items[i].text.split("\\")[-1].split(".")[0]
                                if i + 1 < len(items):
                                    next_item = items[i + 1].text.split("\\")[-1].split(".")[0]
                                break

                    if title != last_title:
                        last_title = title
                        overlay_displayed = False
                        next_overlay_displayed = False
                        start_time = time.time()
                        next_overlay_start = None

                    elapsed = time.time() - start_time if start_time else 0
                    remaining = (duration - position) / 1000

                    if not overlay_displayed and elapsed < 4:
                        update_gt_text(f"{current_item}", "")
                        show_overlay()
                        overlay_displayed = True

                    if overlay_displayed and elapsed > 8:
                        hide_overlay()

                    if not next_overlay_displayed and remaining < 10 and next_item:
                        update_gt_text("", f"À suivre : {next_item}")
                        show_overlay()
                        next_overlay_displayed = True
                        next_overlay_start = time.time()

                    if next_overlay_displayed and next_overlay_start and (time.time() - next_overlay_start >= 6):
                        hide_overlay()
                        next_overlay_displayed = False

                    break # Sortir de la boucle for après avoir trouvé la VideoList
            
            if not videolist_found:
                if overlay_displayed or next_overlay_displayed:
                    hide_overlay()
                last_title = ""
                overlay_displayed = False
                next_overlay_displayed = False
                start_time = None
                next_overlay_start = None

        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(1)

if __name__ == "__main__":
    main_loop()
