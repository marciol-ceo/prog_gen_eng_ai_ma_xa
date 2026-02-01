# create_bucket.py
from supabase import create_client
import os
from typing import Optional ,Dict,List,Any
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import os
# 🔑 Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def create_bucket(supabase_url: str, supabase_key: str, bucket_id: str, public: bool = False, allowed_mime_types: list = None, file_size_limit: int = None):
    """
    Crée un bucket Supabase.
    - supabase_url: URL du projet (ex: https://xyz.supabase.co)
    - supabase_key: SERVICE_ROLE key (côté serveur)
    - bucket_id: identifiant unique du bucket (ex: 'uploads')
    - public: True pour rendre les objets lisibles publiquement
    - allowed_mime_types: liste de types MIME autorisés (ex: ['image/png'])
    - file_size_limit: taille max en octets
    Retourne le dict data si succès, lève une Exception sinon.
    """
    supabase = create_client(supabase_url, supabase_key)

    options = {}
    if allowed_mime_types is not None:
        options["allowed_mime_types"] = allowed_mime_types
    if file_size_limit is not None:
        options["file_size_limit"] = file_size_limit
    options["public"] = public
    try:
         response = supabase.storage.create_bucket(bucket_id, options=options)
    except :
        return 'bucket deja existant'

    # Le client renvoie généralement un dict avec 'data' et 'error'
    if response.get("error"):
        raise RuntimeError(f"Erreur création bucket: {response['error']}")
    return response.get("data")

def normalize_folder_path(folder_path: str) -> str:
    """
    Normalise le chemin du dossier pour qu'il n'ait pas de slash initial
    et qu'il se termine sans slash.
    Exemples: "docs/reports", "/docs/reports/", "docs/reports/" -> "docs/reports"
    """
    if not folder_path:
        raise ValueError("folder_path ne peut pas être vide")
    p = folder_path.strip()
    if p.startswith("/"):
        p = p[1:]
    if p.endswith("/"):
        p = p[:-1]
    return p

def folder_exists(supabase, bucket_id: str, folder_path: str) -> bool:
    """
    Vérifie s'il existe au moins un objet avec le préfixe folder_path.
    """
    try:
        items = supabase.storage.from_(bucket_id).list(folder_path, {"limit": 1})
        # selon la version du client, list peut renvoyer dict ou tuple; on gère les deux cas
        if isinstance(items, dict):
            return bool(items.get("data"))
        # si items est une liste directe
        return bool(items)
    except Exception:
        return False

def create_folder(bucket_id: str, folder_path: str, placeholder_name: str = ".keep", placeholder_content: bytes = b"", public: bool = False):
    """
    Crée un dossier virtuel en uploadant bucket_id/folder_path/.keep
    - bucket_id: nom du bucket
    - folder_path: chemin du dossier (ex: 'docs/reports')
    - placeholder_name: nom du fichier placeholder (par défaut '.keep')
    - placeholder_content: contenu binaire du placeholder (par défaut vide)
    Retourne le résultat de l'upload ou l'information que le dossier existe déjà.
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    folder = normalize_folder_path(folder_path)
    placeholder_path = f"{folder}/{placeholder_name}"

    # Si un objet existe déjà sous ce préfixe, on considère le dossier comme existant
    if folder_exists(supabase, bucket_id, folder):
        return {"status": "exists", "folder": folder}

    # Upload du placeholder
    # Selon la version du client, upload peut renvoyer dict {'data':..., 'error':...}
    res = supabase.storage.from_(bucket_id).upload(placeholder_path, placeholder_content, {"content-type": "application/octet-stream"})
    # Gestion simple du retour
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Erreur lors de la création du dossier: {res['error']}")
    return {"status": "created", "path": placeholder_path, "result": res}

def upload_json_dict_to_folder(
    bucket: str,
    folder: str,
    filename: Optional[str],
    data: Dict,
    overwrite: bool = False,
    make_public_url: bool = False
) -> Dict:
    """
    Sérialise `data` (dict) en JSON et upload dans `bucket/folder/filename`.
    - bucket: nom du bucket (ex: 'donnees')
    - folder: chemin du dossier virtuel (ex: 'invoices/2026' ou 'docs')
    - filename: nom du fichier (ex: 'doc.json'). Si None, génère un nom horodaté.
    - data: dictionnaire Python à stocker
    - overwrite: si True, supprime le fichier existant avant upload
    - make_public_url: si True, tente de retourner l'URL publique (nécessite bucket public)
    Retour: dict {status, path, public_url? , result}
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Variables d'environnement SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY requises")

    # normaliser dossier et nom de fichier
    folder = folder.strip().strip("/")
    if not filename:
        filename = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + ".json"
    if not filename.lower().endswith(".json"):
        filename = filename + ".json"
    path = f"{folder}/{filename}"

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # sérialisation JSON en bytes (utf-8)
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    # suppression si overwrite demandé
    if overwrite:
        try:
            # remove attend une liste de chemins
            supabase.storage.from_(bucket).remove([path])
        except Exception:
            # ignorer si le fichier n'existe pas ou si la suppression échoue silencieusement
            pass

    # upload en précisant le content-type
    file_options = {"content-type": "application/json"}
    res = supabase.storage.from_(bucket).upload(path, json_bytes, file_options)

    # gestion simple du retour selon différentes versions du client
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(f"Erreur upload: {res['error']}")

    result = {"status": "uploaded", "path": path, "result": res}

    # si demandé, récupérer l'URL publique (fonctionne si le bucket est public)
    if make_public_url:
        try:
            public_url = supabase.storage.from_(bucket).get_public_url(path)
            # get_public_url peut renvoyer dict ou string selon la version
            if isinstance(public_url, dict):
                result["public_url"] = public_url.get("publicUrl") or public_url.get("url")
            else:
                result["public_url"] = public_url
        except Exception:
            # ne pas échouer si récupération de l'URL publique impossible
            result["public_url"] = None

    return result

def list_buckets() -> List[Dict[str, Any]]:
    """
    Retourne la liste des buckets du projet Supabase sous forme de liste de dicts.
    Ex: [{"name": "donnees", "public": False, "created_at": "2024-01-01T..."} , ...]
    Lève RuntimeError en cas d'erreur.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Variables d'environnement SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY requises")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Certaines versions du client exposent différentes méthodes/retours.
    # On essaie plusieurs variantes et on normalise le résultat.
    raw = None
    try:
        # tentative 1 : méthode courante (snake_case)
        raw = supabase.storage.list_buckets()
    except Exception:
        try:
            # tentative 2 : autre nom possible
            raw = supabase.storage.listBuckets()
        except Exception:
            # tentative 3 : appel générique via RPC si nécessaire (peu probable)
            raw = None

    if raw is None:
        raise RuntimeError("Impossible d'interroger l'API Storage. Vérifie la version du SDK et les clés.")

    # Normaliser différents formats de réponse
    buckets = []
    # Cas : dict { "data": [...], "error": ... }
    if isinstance(raw, dict) and raw.get("data") is not None:
        data = raw.get("data") or []
    # Cas : tuple (data, error) ou (data,)
    elif isinstance(raw, (list, tuple)) and len(raw) > 0 and isinstance(raw[0], (list, dict)):
        data = raw[0]
    # Cas : raw est directement la liste des buckets
    elif isinstance(raw, list):
        data = raw
    else:
        # fallback : essayer d'extraire un attribut 'buckets' ou 'data'
        data = getattr(raw, "data", None) or getattr(raw, "buckets", None) or []

    for item in data or []:
        # item peut être un dict ou un objet; on tente d'extraire les champs usuels
        if isinstance(item, dict):
            name = item.get("name") or item.get("id") or item.get("bucket")
            public = item.get("public") if "public" in item else item.get("is_public")
            created_at = item.get("created_at") or item.get("createdAt")
        else:
            # objet avec attributs
            name = getattr(item, "name", None) or getattr(item, "id", None)
            public = getattr(item, "public", None) or getattr(item, "is_public", None)
            created_at = getattr(item, "created_at", None) or getattr(item, "createdAt", None)

        buckets.append({
            "name": name,
            "public": public,
            "created_at": created_at
        })

    return buckets

def _normalize_folder(folder: Optional[str]) -> str:
    f = (folder or "").strip()
    if f.startswith("/"):
        f = f[1:]
    if f.endswith("/"):
        f = f[:-1]
    return f

def _extract_items(raw) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, dict) and raw.get("data") is not None:
        return raw.get("data") or []
    if isinstance(raw, (list, tuple)) and len(raw) > 0 and isinstance(raw[0], (list, dict)):
        return raw[0]
    if isinstance(raw, list):
        return raw
    data = getattr(raw, "data", None) or getattr(raw, "files", None) or []
    return data or []

def list_files_in_folder(
    bucket: str,
    folder: Optional[str] = "",
    recursive: bool = False,
    page_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Liste les fichiers dans `bucket/folder`.
    - bucket: nom du bucket (ex: 'donnees')
    - folder: chemin du dossier virtuel (ex: 'docs/2026' ou '')
    - recursive: si True, inclut les fichiers dans les sous-dossiers
    - page_size: taille de page pour la pagination
    Retour: liste de dicts { name, path, size, content_type, updated_at }
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY requis")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    prefix = _normalize_folder(folder)
    path_for_list = prefix if prefix else ""
    
    all_items: List[Dict[str, Any]] = []
    offset = 0
    normalized_items = []
    while True:
        try:
            options = {"limit": page_size, "offset": offset}
            raw = supabase.storage.from_(bucket).list(path_for_list, options)
        except TypeError:
            raw = supabase.storage.from_(bucket).list(path_for_list, {"limit": page_size, "offset": offset})
        except Exception as e:
            raise RuntimeError(f"Erreur lors du list: {e}")
        #print(raw)

        for it in raw:
            if isinstance(it, dict):
                name = it.get("name") 
                
                normalized_items.append(name)

        if not raw or len(raw) < page_size:
            break
        offset += page_size

    return normalized_items

def fetch_json_from_bucket(
    bucket: str,
    folder: Optional[str],
    filename: str,
    encoding: str = "utf-8"
) -> Dict:
    """
    Récupère `bucket/folder/filename` depuis Supabase Storage, parse le JSON et retourne un dict.
    - bucket: nom du bucket (ex: 'donnees')
    - folder: chemin du dossier virtuel (ex: 'docs/2026') ou ''/None pour la racine
    - filename: nom du fichier (ex: 'client_dupont.json')
    - encoding: encodage pour décoder les bytes (par défaut 'utf-8')
    Lève RuntimeError en cas d'erreur (fichier introuvable, JSON invalide, problème réseau).
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis en variables d'environnement")

    # normaliser le chemin
    folder = (folder or "").strip().strip("/")
    path = f"{folder}/{filename}" if folder else filename

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        raw = supabase.storage.from_(bucket).download(path)
    except Exception as e:
        # Erreur levée par le SDK (ex: bucket inexistant, permissions)
        raise RuntimeError(f"Erreur lors du téléchargement depuis Supabase: {e}")

    # Le SDK peut renvoyer plusieurs formats : bytes, dict {'data': bytes, 'error': ...}, tuple (data, error)
    file_bytes = None
    # cas dict { 'data': ..., 'error': ... }
    if isinstance(raw, dict) and raw.get("data") is not None:
        file_bytes = raw.get("data")
        error = raw.get("error")
        if error:
            raise RuntimeError(f"Erreur Supabase lors du download: {error}")
    # cas tuple (data, error)
    elif isinstance(raw, (list, tuple)) and len(raw) >= 1:
        # si second élément est une erreur
        data_candidate = raw[0]
        error_candidate = raw[1] if len(raw) > 1 else None
        if error_candidate:
            raise RuntimeError(f"Erreur Supabase lors du download: {error_candidate}")
        file_bytes = data_candidate
    # cas bytes direct
    elif isinstance(raw, (bytes, bytearray)):
        file_bytes = bytes(raw)
    # cas objet avec attribut 'data'
    else:
        file_bytes = getattr(raw, "data", None) or getattr(raw, "content", None)

    if not file_bytes:
        raise RuntimeError(f"Fichier introuvable ou contenu vide: {path}")

    # Si file_bytes est un objet file-like, essayer à lire
    try:
        if hasattr(file_bytes, "read"):
            file_bytes = file_bytes.read()
    except Exception:
        pass

    # Décoder et parser JSON
    try:
        text = file_bytes.decode(encoding) if isinstance(file_bytes, (bytes, bytearray)) else str(file_bytes)
    except Exception as e:
        raise RuntimeError(f"Impossible de décoder le contenu du fichier {path}: {e}")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON invalide dans le fichier {path}: {e}")

    return data




def _ensure_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def bucket_exists(supabase, bucket: str) -> bool:
    raw = supabase.storage.list_buckets()
    data = raw.get("data") if isinstance(raw, dict) else raw
    if not data:
        return False
    names = [b.get("name") if isinstance(b, dict) else getattr(b, "name", None) for b in data]
    return bucket in names

def create_folder_if_not_exists(supabase, bucket: str, folder: str):
    folder = folder.strip().strip("/")
    try:
        items = supabase.storage.from_(bucket).list(folder, {"limit": 1})
        if isinstance(items, dict) and items.get("data"):
            return {"status": "exists", "folder": folder}
        if items:
            return {"status": "exists", "folder": folder}
    except Exception:
        pass
    # créer un placeholder
    placeholder_path = f"{folder}/.keep"
    supabase.storage.from_(bucket).upload(placeholder_path, b"", {"content-type": "application/octet-stream"})
    return {"status": "created", "folder": folder}


def upload_exercices(bucket: str, liste_exo_epreuve: List[Dict]) -> List[Dict]:
    """
    Pour chaque dict de liste_exo_epreuve :
    - crée un dossier avec le nom de chaque clé
    - insère le contenu du dict dans un fichier JSON dans ce dossier
    - ajoute un timestamp (jour-heure-minute-seconde) au nom du fichier pour éviter les doublons
    """
    import time
    supabase = _ensure_client()
    if not bucket_exists(supabase, bucket):
        raise RuntimeError(f"Bucket '{bucket}' inexistant")

    results = []
    for idx, exo_dict in enumerate(liste_exo_epreuve, start=1):
        for key, value in exo_dict.items():
            folder_name = key.strip().replace(" ", "_")  # normaliser le nom du dossier
            create_folder_if_not_exists(supabase, bucket, folder_name)

            # Générer un timestamp unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            time.sleep(1)  # pour éviter les collisions si très rapide
            # nom du fichier : exoX_YYYYMMDD_HHMMSS.json
            filename = f"{key.replace(' ', '_')}_{timestamp}.json"
            path = f"{folder_name}/{filename}"

            json_bytes = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
            res = supabase.storage.from_(bucket).upload(path, json_bytes, {"content-type": "application/json"})
            if isinstance(res, dict) and res.get("error"):
                results.append({
                    "status": "error",
                    "folder": folder_name,
                    "file": filename,
                    "error": res.get("error")
                })
            else:
                results.append({
                    "status": "uploaded",
                    "folder": folder_name,
                    "file": filename
                })
    return results




def delete_bucket(bucket_name: str, force: bool = False) -> dict:
    """
    Supprime un bucket Supabase.
    
    Args:
        bucket_name: Nom du bucket à supprimer
        force: Si True, vide le bucket avant de le supprimer (récursivement)
    
    Retourne dict {status, bucket, error?}
    """
    supabase = _ensure_client()
    
    def list_all_files_recursively(bucket, path=""):
        """Liste tous les fichiers récursivement dans un bucket."""
        all_files = []
        
        try:
            # Lister les éléments au niveau actuel
            items = supabase.storage.from_(bucket).list(path)
            
            if not items:
                return all_files
            
            for item in items:
                item_name = item.get('name')
                item_id = item.get('id')
                
                # Construire le chemin complet
                if path:
                    full_path = f"{path}/{item_name}"
                else:
                    full_path = item_name
                
                # Si c'est un dossier (pas de 'id' ou metadata indique un folder)
                # On descend récursivement
                if item_id is None or item.get('metadata') is None:
                    # C'est un dossier, on descend
                    all_files.extend(list_all_files_recursively(bucket, full_path))
                else:
                    # C'est un fichier
                    all_files.append(full_path)
        
        except Exception as e:
            print(f"⚠️ Erreur lors du listing de '{path}': {e}")
        
        return all_files
    
    try:
        # Si force=True, on vide d'abord le bucket
        if force:
            try:
                print(f"🔍 Recherche récursive des fichiers dans '{bucket_name}'...")
                
                # Lister TOUS les fichiers récursivement
                all_files = list_all_files_recursively(bucket_name)
                
                if all_files and len(all_files) > 0:
                    print(f"📁 {len(all_files)} fichier(s) trouvé(s)")
                    
                    # Supprimer par lots de 100 (limite API Supabase)
                    batch_size = 100
                    for i in range(0, len(all_files), batch_size):
                        batch = all_files[i:i + batch_size]
                        try:
                            supabase.storage.from_(bucket_name).remove(batch)
                            print(f"✓ Lot {i//batch_size + 1}: {len(batch)} fichier(s) supprimé(s)")
                        except Exception as batch_error:
                            print(f"⚠️ Erreur lot {i//batch_size + 1}: {batch_error}")
                    
                    print(f"✅ Total: {len(all_files)} fichier(s) supprimé(s) du bucket '{bucket_name}'")
                else:
                    print(f"ℹ️ Aucun fichier trouvé dans '{bucket_name}'")
                    
            except Exception as e:
                return {
                    "status": "error", 
                    "bucket": bucket_name, 
                    "error": f"Impossible de vider le bucket: {str(e)}"
                }
        
        # Supprimer le bucket (maintenant vide)
        print(f"🗑️ Suppression du bucket '{bucket_name}'...")
        res = supabase.storage.delete_bucket(bucket_name)
        
        # Vérifier les erreurs dans la réponse
        if isinstance(res, dict) and res.get("error"):
            return {
                "status": "error", 
                "bucket": bucket_name, 
                "error": res.get("error")
            }
        
        print(f"✅ Bucket '{bucket_name}' supprimé avec succès!")
        return {
            "status": "deleted", 
            "bucket": bucket_name, 
            "message": f"Bucket '{bucket_name}' supprimé avec succès"
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Message d'aide si le bucket n'est pas vide
        if "not empty" in error_msg.lower() or "must be empty" in error_msg.lower():
            return {
                "status": "error",
                "bucket": bucket_name,
                "error": f"Le bucket contient encore des fichiers. Réessayez avec force=True"
            }
        
        return {
            "status": "error", 
            "bucket": bucket_name, 
            "error": error_msg
        }
    


def list_folders(bucket: str, folder: str = "") -> List[Dict]:
    """
    Liste les dossiers disponibles dans un répertoire d'un bucket Supabase.
    - bucket: nom du bucket (ex: 'donnees')
    - folder: chemin du répertoire (ex: 'docs') ou '' pour la racine
    Retour: liste de dicts {name, id, created_at}
    """
    supabase = _ensure_client()
    prefix = folder.strip().strip("/") if folder else ""

    try:
        raw = supabase.storage.from_(bucket).list(prefix, {"limit": 100})
    except Exception as e:
        raise RuntimeError(f"Erreur lors du list: {e}")

    # Normaliser la réponse
    items = []
    if isinstance(raw, dict) and raw.get("data"):
        data = raw["data"]
    elif isinstance(raw, list):
        data = raw
    else:
        data = getattr(raw, "data", []) or []

    for it in data:
        # Selon le SDK, un dossier est identifié par "id" et "name" sans extension
        if isinstance(it, dict):
            # Certains SDK renvoient "metadata": None pour les dossiers
            if it.get("metadata") is None:
                items.append(it.get("name"))
        else:
            # fallback si c'est un objet
            if getattr(it, "metadata", None) is None:
                items.append( getattr(it, "name", None))

    return items

def select_random_structure(bucket_name ,folder_name):
    import random
    return fetch_json_from_bucket(bucket_name, folder_name, random.choice(list_files_in_folder(bucket_name, folder_name)[1:]))




