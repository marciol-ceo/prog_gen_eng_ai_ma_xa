import os
import time
import json
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()  # charge .env si présent

BASE = "https://api.mathpix.com/v3"

def _get_keys(app_id: Optional[str], app_key: Optional[str]):
    app_id = app_id or os.getenv("MATHPIX_APP_ID") or os.getenv("APP_ID")
    app_key = app_key or os.getenv("MATHPIX_APP_KEY") or os.getenv("APP_KEY")
    if not app_id or not app_key:
        raise ValueError("Clés API manquantes. Définir MATHPIX_APP_ID et MATHPIX_APP_KEY.")
    return app_id, app_key

def submit_pdf(pdf_path: str,
               app_id: Optional[str] = None,
               app_key: Optional[str] = None,
               options: Optional[dict] = None,
               timeout: int = 300) -> str:
    """
    Soumet un PDF et retourne le pdf_id (async).
    """
    app_id, app_key = _get_keys(app_id, app_key)
    if options is None:
        options = {
            "conversion_formats": {"docx": True, "tex.zip": True},
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True
        }
    headers = {"app_id": app_id, "app_key": app_key}
    data = {"options_json": json.dumps(options)}
    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        resp = requests.post(f"{BASE}/pdf", headers=headers, data=data, files=files, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()
    if "pdf_id" not in j:
        raise RuntimeError(f"Réponse inattendue: {j}")
    return j["pdf_id"]

def poll_pdf_status(pdf_id: str,
                    app_id: Optional[str] = None,
                    app_key: Optional[str] = None,
                    poll_interval: int = 3,
                    timeout: int = 600) -> dict:
    """
    Poll la ressource /v3/pdf/{pdf_id} jusqu'à status completed ou error.
    Retourne le JSON final de status.
    """
    app_id, app_key = _get_keys(app_id, app_key)
    headers = {"app_id": app_id, "app_key": app_key}
    start = time.time()
    while True:
        resp = requests.get(f"{BASE}/pdf/{pdf_id}", headers=headers)
        resp.raise_for_status()
        status_j = resp.json()
        status = status_j.get("status")
        if status in ("completed", "error"):
            return status_j
        if time.time() - start > timeout:
            raise TimeoutError("Timeout pendant le polling du PDF.")
        time.sleep(poll_interval)

def download_conversion(pdf_id: str,
                        ext: str,
                        dest_path: str,
                        app_id: Optional[str] = None,
                        app_key: Optional[str] = None,
                        timeout: int = 120):
    """
    Télécharge la conversion : ext par exemple 'mmd', 'lines.json', 'docx', 'tex.zip', 'html'.
    Sauve en dest_path.
    """
    app_id, app_key = _get_keys(app_id, app_key)
    headers = {"app_id": app_id, "app_key": app_key}
    url = f"{BASE}/pdf/{pdf_id}.{ext}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    mode = "wb" if isinstance(resp.content, (bytes, bytearray)) else "w"
    with open(dest_path, mode) as f:
        if mode == "wb":
            f.write(resp.content)
        else:
            f.write(resp.text)

import json
from pathlib import Path
from typing import Tuple, List, Dict

def extract_text_from_lines_json(lines_json_path: str) -> Tuple[str, List[str]]:
    """
    Lit un fichier lines.json (format Mathpix) et retourne:
      - full_text: texte concaténé de tout le document (pages séparées par deux sauts de ligne)
      - pages: liste de chaînes, une par page (ligne par ligne concaténées dans l'ordre)
    Comportement:
      - Utilise "text" puis "text_display" pour chaque ligne.
      - Nettoie les retours à la ligne internes et les espaces superflus.
      - Si le fichier n'a pas de clé 'pages', renvoie le texte brut trouvé dans la racine si présent.
    """
    p = Path(lines_json_path)
    if not p.exists():
        raise FileNotFoundError(f"{lines_json_path} introuvable")

    with p.open("r", encoding="utf-8") as f:
        j = json.load(f)

    pages_data = j.get("pages")
    pages_texts: List[str] = []

    if isinstance(pages_data, list) and pages_data:
        for page in pages_data:
            lines = page.get("lines", [])
            page_lines: List[str] = []
            for line in lines:
                txt = line.get("text") or line.get("text_display") or ""
                txt = txt.replace("\n", " ").strip()
                if txt:
                    page_lines.append(txt)
            pages_texts.append("\n".join(page_lines).strip())
    else:
        # Fallback: tenter de récupérer un champ texte global
        fallback_text = j.get("text") or j.get("full_text") or j.get("markdown") or ""
        if fallback_text:
            # découper par pages si possible via séparateurs connus
            possible_pages = [p.strip() for p in fallback_text.split("\f") if p.strip()]
            if len(possible_pages) > 1:
                pages_texts = possible_pages
            else:
                pages_texts = [fallback_text.strip()]

    # full_text: concatène les pages avec deux sauts de ligne comme séparateur
    full_text = "\n\n".join([pt for pt in pages_texts if pt]).strip()

    return full_text, pages_texts


def extract_text_from_mmd(mmd_path: str) -> str:
    """
    Lit un fichier .mmd (Mathpix Markdown) et retourne son contenu texte brut.
    """
    with open(mmd_path, "r", encoding="utf-8") as f:
        return f.read()

def MathpixLoader(pdf_path):
    pdf_id = submit_pdf(pdf_path)                     # envoie -> pdf_id
    status = poll_pdf_status(pdf_id)                   # attend la fin
    download_conversion(pdf_id, "lines.json", "res.lines.json")  # télécharge lines.json
    full_text, pages_texts = extract_text_from_lines_json("res.lines.json")        # texte concaténé
    return full_text, pages_texts