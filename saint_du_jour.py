from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont
from utils.app_utils import get_font
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class InkiPy-SaintDuJour(BasePlugin):
    """
    Plugin InkyPi pour afficher le saint du jour depuis Nominis,
    avec une synthèse IA dans le style de Paul Claudel.
    """

    def __init__(self):
        super().__init__()
        self._last_fetch = None
        self._saint_cache = None

    def synthese_ia(self, texte, nom_saint="Un saint"):
        """
        Génère une synthèse avec Mistral ou OpenAI, dans le style de Paul Claudel.
        """
        # Récupérer les clés API depuis les settings ou les variables d'environnement
        mistral_api_key = self.settings.get("mistral_api_key", "") or os.getenv("MISTRAL_API_KEY", "")
        openai_api_key = self.settings.get("openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
        use_openai = self.settings.get("use_openai", False) in [True, "True", "true", 1]

        prompt = f"""
        Résume la vie de **{nom_saint}** en 5-6 phrases claires dans le style de Paul Claudel,
        en mettant en avant :
        - Son époque et son origine
        - Ses actions ou miracles principaux
        - Sa signification spirituelle ou son héritage
        - Un fait marquant

        Biographie : {texte[:2000]}...
        """

        headers = {"Content-Type": "application/json"}

        if use_openai and openai_api_key:
            headers["Authorization"] = f"Bearer {openai_api_key}"
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            api_url = "https://api.openai.com/v1/chat/completions"
        else:
            if not mistral_api_key:
                logger.warning("⚠️ Aucune clé API configurée. Utilisation de la biographie brute.")
                return f"**{nom_saint}** : {texte[:200]}..."
            headers["Authorization"] = f"Bearer {mistral_api_key}"
            payload = {
                "model": "mistral-small",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            api_url = "https://api.mistral.ai/v1/chat/completions"

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"❌ Erreur API IA : {e}")
            return f"**{nom_saint}** : {texte[:200]}..."  # Fallback

    def draw_saint_icon(self, draw, x, y, size=30):
        """Dessine une icône de saint avec PIL (couronne + personne)."""
        # Couronne (cercle + pointes)
        crown_y = y - size * 0.3
        draw.ellipse(
            [(x - size//2, crown_y - size//2), (x + size//2, crown_y + size//2)],
            outline="black", width=2
        )
        # Pointes de la couronne
        points = [
            (x - size//3, crown_y - size//2), (x - size//4, crown_y - size//2 - 5),
            (x, crown_y - size//2 - 7),
            (x + size//4, crown_y - size//2 - 5), (x + size//3, crown_y - size//2)
        ]
        draw.line(points, fill="black", width=2)

        # Tête
        head_size = size // 2
        draw.ellipse(
            [(x - head_size//2, y - head_size//2), (x + head_size//2, y + head_size//2)],
            outline="black", width=2
        )

        # Corps (robe)
        body_y = y + head_size//2
        draw.line([(x, body_y), (x, body_y + size//2)], fill="black", width=2)
        draw.line([(x - size//4, body_y + size//3), (x + size//4, body_y + size//3)], fill="black", width=2)

    def get_saint_du_jour(self):
        """
        Récupère le saint du jour depuis nominis.cef.fr.
        Utilise un cache pour éviter les requêtes répétées.
        """
        if self._last_fetch and (datetime.now() - self._last_fetch) < timedelta(hours=1):
            return self._saint_cache

        url = "https://nominis.cef.fr/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            saint_h2 = soup.find("h2")
            if not saint_h2:
                logger.error("Aucun saint trouvé sur Nominis")
                return None

            saint_nom = saint_h2.get_text(strip=True)

            biographie_paragraphes = []
            current = saint_h2.find_next()
            while current:
                if current.name in ["h1", "h2", "h4", "h5", "h6"]:
                    break
                if current.name == "p":
                    texte = current.get_text(strip=True)
                    if texte and len(texte) > 10:
                        biographie_paragraphes.append(texte)
                current = current.find_next()

            biographie = " ".join(biographie_paragraphes)
            if not biographie:
                logger.error("Aucune biographie trouvée")
                return None

            self._saint_cache = {
                "nom": saint_nom,
                "biographie": biographie,
                "date": datetime.now().strftime("%d/%m/%Y")
            }
            self._last_fetch = datetime.now()
            return self._saint_cache

        except requests.RequestException as e:
            logger.error(f"Erreur réseau: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return None

    def generate_image(self, settings, device_config):
        """
        Génère l'image avec :
        - Icône du saint à gauche
        - Synthèse IA (style Paul Claudel) à droite
        """
        self.settings = settings  # Stocker les settings pour synthese_ia

        # Paramètres configurables
        max_length = int(settings.get("max_length", 300))  # Plus long car synthèse IA
        font_size_ratio = float(settings.get("font_size_ratio", 0.05))  # Un peu plus petit
        show_date = settings.get("show_date", True) in [True, "True", "true", 1]
        use_ia = settings.get("use_ia", True) in [True, "True", "true", 1]

        # Récupérer le saint du jour
        saint = self.get_saint_du_jour()

        # Texte à afficher
        if saint:
            if use_ia:
                # Utiliser la synthèse IA
                synthese = self.synthese_ia(saint["biographie"], saint["nom"])
                if not synthese:
                    synthese = f"Saint {saint['nom']}: {saint['biographie'][:max_length]}..."
                text = synthese
            else:
                # Fallback : biographie brute
                biographie = saint["biographie"]
                if len(biographie) > max_length:
                    biographie = biographie[:max_length] + "..."
                text = f"Saint {saint['nom']}: {biographie}"

            if show_date:
                text = f"{saint['date']}\n{text}"
        else:
            text = "Saint du jour:\nIndisponible"

        # Configuration de l'écran
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        width, height = dimensions

        # Créer l'image
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        font_size = int(width * font_size_ratio)
        font = get_font("Jost", font_size)

        # Dessiner l'icône du saint en haut à gauche
        self.draw_saint_icon(draw, 20, 30, size=25)

        # Dessiner le texte (à droite de l'icône)
        lines = text.split("\n")
        y = 15  # Marge supérieure
        x_start = 50  # Décalage pour éviter l'icône
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = x_start + (width - x_start - text_width) // 2
            draw.text((x, y), line, fill="black", font=font)
            y += (bbox[3] - bbox[1]) + 5

        logger.debug(f"Image générée: {width}x{height}")
        return imagetu 