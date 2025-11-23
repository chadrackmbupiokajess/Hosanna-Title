import requests
import xml.etree.ElementTree as ET
import time
import os
import tkinter as tk
from tkinter import simpledialog, messagebox

# ==============================================================================
# --- CONFIGURATION ---
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    # L'adresse IP sera demandée à l'utilisateur au démarrage
    "VMIX_URL": "", # Sera rempli par l'utilisateur
    
    # --- Entrées Titres (Utiliser deux entrées séparées) ---
    "NOW_PLAYING_INPUT": "TitreEnCours",  # Nom/Numéro de l'entrée pour "En Cours"
    "NOW_PLAYING_OVERLAY_CHANNEL": 1,     # Canal d'overlay pour "En Cours"

    "NEXT_UP_INPUT": "TitreASuivre",      # Nom/Numéro de l'entrée pour "À Suivre"
    "NEXT_UP_OVERLAY_CHANNEL": 2,         # Canal d'overlay pour "À Suivre"
    
    # --- Noms des champs (doivent exister dans votre modèle de titre) ---
    "TEXT_FIELD": "Headline.Text",        # Champ de texte principal
    "IMAGE_FIELD": "Image.Source",        # Champ image

    # --- Fichiers images ---
    "NOW_PLAYING_IMAGE_PATH": os.path.join(BASE_DIR, "en cours.png"),
    "NEXT_UP_IMAGE_PATH": os.path.join(BASE_DIR, "a suivre.png"),

    # --- Fichiers pour les titres (pour écriture automatique) ---
    # Ces fichiers seront mis à jour automatiquement par le script
    "CURRENT_TITLE_FILE": os.path.join(BASE_DIR, "titre_actuel.txt"),
    "NEXT_TITLE_FILE": os.path.join(BASE_DIR, "titre_suivant.txt"),

    # --- Temporisation (en secondes) ---
    "SHOW_NOW_PLAYING_FOR": 8,
    "SHOW_NEXT_UP_WHEN_REMAINING": 15,
    "SHOW_NEXT_UP_FOR": 6,

    # --- Transitions ---
    "OVERLAY_TRANSITION_TYPE": "Fade",
    "OVERLAY_TRANSITION_DURATION": 500,

    # --- Formatage du texte ---
    "MAX_TITLE_LENGTH": 27, # Longueur maximale du titre avant troncature avec "..."
}
# ==============================================================================
# --- FIN DE LA CONFIGURATION ---
# ==============================================================================

class VmixTitleController:
    def __init__(self, config):
        self.config = config
        self.api_url = config["VMIX_URL"]
        
        if not self.api_url:
            raise ValueError("L'URL de vMix n'a pas été configurée. Veuillez fournir l'adresse IP.")

        # État
        self.last_title = "" 
        self.now_playing_shown = False
        self.next_up_shown = False
        self.song_start_time = None
        self.next_up_start_time = None

        self._setup_transitions()

    def _setup_transitions(self):
        """Configure les transitions pour les deux canaux d'overlay."""
        channels = [self.config["NOW_PLAYING_OVERLAY_CHANNEL"], self.config["NEXT_UP_OVERLAY_CHANNEL"]]
        ttype = self.config['OVERLAY_TRANSITION_TYPE']
        duration = self.config['OVERLAY_TRANSITION_DURATION']
        
        for channel in set(channels): # set() pour éviter de configurer deux fois le même canal
            print(f"Configuration de la transition pour le canal {channel} : {ttype}, {duration}ms.")
            self._send_vmix_request({'Function': 'SetOverlayTransition', 'Value': channel, 'Type': ttype})
            self._send_vmix_request({'Function': 'SetOverlayTransitionDuration', 'Value': channel, 'Duration': duration})

    def _send_vmix_request(self, params):
        try:
            requests.get(self.api_url, params=params, timeout=0.5)
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à vMix : {e}")

    def _update_title(self, input_name, text="", image_path=""):
        """Met à jour le texte et l'image d'une entrée titre spécifique."""
        # Mettre à jour le texte
        self._send_vmix_request({
            'Function': 'SetText', 'Input': input_name,
            'SelectedName': self.config["TEXT_FIELD"], 'Value': text
        })
        # Mettre à jour l'image
        self._send_vmix_request({
            'Function': 'SetImage', 'Input': input_name,
            'SelectedName': self.config["IMAGE_FIELD"], 'Value': image_path
        })

    def _toggle_overlay(self, channel, action="In", input_name=""):
        """Affiche ou masque un overlay sur un canal spécifique."""
        function = f"OverlayInput{channel}{action}"
        self._send_vmix_request({'Function': function, 'Input': input_name})

    def reset_state(self):
        """Réinitialise l'état en masquant tous les overlays."""
        if self.now_playing_shown:
            self._toggle_overlay(self.config["NOW_PLAYING_OVERLAY_CHANNEL"], "Out", self.config["NOW_PLAYING_INPUT"])
        if self.next_up_shown:
            self._toggle_overlay(self.config["NEXT_UP_OVERLAY_CHANNEL"], "Out", self.config["NEXT_UP_INPUT"])
        
        self.last_title = ""
        self.now_playing_shown = False
        self.next_up_shown = False
        self.song_start_time = None
        self.next_up_start_time = None

    def _write_title_to_file(self, file_path, content):
        """Écrit le contenu dans un fichier texte."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Erreur lors de l'écriture dans le fichier {file_path}: {e}")

    def _format_title_for_display(self, title_text):
        """Tronque le titre à MAX_TITLE_LENGTH et ajoute '...' si nécessaire."""
        max_len = self.config["MAX_TITLE_LENGTH"]
        if len(title_text) > max_len:
            return title_text[:max_len - 3] + "..."
        return title_text

    def _get_videolist_status(self):
        """Récupère et parse l'état de la VideoList depuis vMix."""
        try:
            res = requests.get(self.api_url, timeout=0.5)
            res.raise_for_status()
            root = ET.fromstring(res.text)

            for input_el in root.findall(".//input"):
                if input_el.attrib.get("type") == "VideoList" and input_el.attrib.get("state") == "Running":
                    list_items = input_el.find("list")
                    items = list_items.findall("item") if list_items is not None else []
                    
                    current_item_text = ""
                    next_item_text = ""
                    for i, item in enumerate(items):
                        if item.attrib.get("selected") == "true":
                            current_item_text = item.text.split("\\")[-1].split(".")[0] 
                            if i + 1 < len(items):
                                next_item_text = items[i + 1].text.split("\\")[-1].split(".")[0] 
                            break
                    
                    return {
                        "title": input_el.attrib.get("title"), 
                        "position": int(input_el.attrib.get("position")),
                        "duration": int(input_el.attrib.get("duration")),
                        "current_item": current_item_text, 
                        "next_item": next_item_text        
                    }
            return None
        except (requests.exceptions.RequestException, ET.ParseError) as e:
            print(f"Erreur lors de la récupération des données vMix : {e}")
            return None

    def process_videolist(self, status):
        if status["title"] != self.last_title:
            self.reset_state()
            self.last_title = status["title"]
            self.song_start_time = time.time()
            self._write_title_to_file(self.config["CURRENT_TITLE_FILE"], status["current_item"])
            self._write_title_to_file(self.config["NEXT_TITLE_FILE"], status["next_item"])


        elapsed = time.time() - self.song_start_time
        remaining = (status["duration"] - status["position"]) / 1000

        display_current_item = self._format_title_for_display(status["current_item"])
        display_next_item = self._format_title_for_display(status["next_item"])

        if not self.now_playing_shown and elapsed < self.config["SHOW_NOW_PLAYING_FOR"]:
            self._update_title(self.config["NOW_PLAYING_INPUT"], text=display_current_item, image_path=self.config["NOW_PLAYING_IMAGE_PATH"])
            self._toggle_overlay(self.config["NOW_PLAYING_OVERLAY_CHANNEL"], "In", self.config["NOW_PLAYING_INPUT"])
            self.now_playing_shown = True
        elif self.now_playing_shown and elapsed > self.config["SHOW_NOW_PLAYING_FOR"]:
            self._toggle_overlay(self.config["NOW_PLAYING_OVERLAY_CHANNEL"], "Out", self.config["NOW_PLAYING_INPUT"])
            self.now_playing_shown = False 

        if not self.next_up_shown and remaining < self.config["SHOW_NEXT_UP_WHEN_REMAINING"] and status["next_item"]:
            self._update_title(self.config["NEXT_UP_INPUT"], text=f"À suivre : {display_next_item}", image_path=self.config["NEXT_UP_IMAGE_PATH"])
            self._toggle_overlay(self.config["NEXT_UP_OVERLAY_CHANNEL"], "In", self.config["NEXT_UP_INPUT"])
            self.next_up_shown = True
            self.next_up_start_time = time.time()

        if self.next_up_shown and self.next_up_start_time and (time.time() - self.next_up_start_time >= self.config["SHOW_NEXT_UP_FOR"]):
            self._toggle_overlay(self.config["NEXT_UP_OVERLAY_CHANNEL"], "Out", self.config["NEXT_UP_INPUT"])
            self.next_up_shown = False

    def run(self):
        print("Démarrage du script (version avec titres automatiques, fichiers mis à jour et troncature)...")
        while True:
            videolist_status = self._get_videolist_status()
            if videolist_status:
                self.process_videolist(videolist_status)
            else:
                self.reset_state()
            time.sleep(1)

def get_vmix_ip_from_user():
    """Affiche une fenêtre Tkinter pour demander l'adresse IP de vMix."""
    root = tk.Tk()
    root.withdraw() # Cache la fenêtre principale de Tkinter

    ip_address = None
    while not ip_address:
        ip_address = simpledialog.askstring(
            "Configuration vMix", 
            "Veuillez entrer l'adresse IP de vMix (ex: 192.168.1.193):",
            parent=root
        )
        if ip_address is None: # L'utilisateur a cliqué sur Annuler
            messagebox.showinfo("Annulation", "Le script a été annulé par l'utilisateur.")
            return None
        if not ip_address.strip():
            messagebox.showerror("Erreur", "L'adresse IP ne peut pas être vide. Veuillez réessayer.")
            ip_address = None # Réinitialise pour redemander

    root.destroy()
    return ip_address.strip()

if __name__ == "__main__":
    vmix_ip = get_vmix_ip_from_user()
    if vmix_ip:
        CONFIG["VMIX_URL"] = f"http://{vmix_ip}:8088/api/"
        try:
            controller = VmixTitleController(CONFIG)
            controller.run()
        except ValueError as e:
            messagebox.showerror("Erreur de configuration", str(e))
        except Exception as e:
            messagebox.showerror("Erreur inattendue", f"Une erreur est survenue : {e}")
    else:
        print("Le script n'a pas pu démarrer sans l'adresse IP de vMix.")
