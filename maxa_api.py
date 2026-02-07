import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Importation de vos modules personnalisés (assurez-vous qu'ils sont dans le même répertoire ou le PYTHONPATH)
from maxa_supabase_ops import (
    create_bucket,  
    list_folders, 
    list_buckets,
    list_files_in_folder, 
    delete_bucket
)
from maxa_extr_gen_epreuve import generer_exercices_innovants, sauvegarder_latex,upload_exercice_in_bucket
from extrat_info_pdf import MathpixLoader

# Chargement des variables d'environnement
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = FastAPI(
    title="Système de Génération d'Épreuves IA",
    description="API permettant de gérer des exercices sur Supabase, d'extraire du texte via OCR et de générer des épreuves LaTeX innovantes.",
    version="1.0.0"
)

# --- MODÈLES DE DONNÉES (SCHEMAS) ---

class BucketCreate(BaseModel):
    bucket_name: str
    public: bool = True
    file_size_limit: int = 1000000
    allowed_mime_types: List[str] = ["image/png", "image/jpeg", "application/pdf", "application/json",'application/octet-stream']

class ExerciseUploadRequest(BaseModel):
    # Changement ici : content_file est maintenant une liste de chaînes (textes bruts d'exercices)
    content_file: List[str] = Field(..., description="Liste des textes d'exercices à extraire et uploader")
    bucket_name: str = Field("issea-bucket", description="Nom du bucket de destination")

class GenerationRequest(BaseModel):
    bucket_name: str
    texte_entete: str = "MAXA GEN ENGINE \\ Prepa-Concours \\Année 2025-2026"
    level_indication: List[str] = ["mathématiques", "Bac+1 à CPGE"]
    indication_exemple: Dict[str, str] = {
        "suite définie par récurrence": "fonction définie par une équation fonctionnelle",
        "fonction exponentielle": "fonction trigonométrique ou rationnelle"
    }
    titre_document: str = "Concours blanc"
    sous_titre: Optional[str] = "Durée: 3h - Calculatrice autorisée"
    generer_latex: bool = True
    logo_gauche: Optional[str] = 'icon_app.png'
    logo_droit: Optional[str] = None

class SaveLatexRequest(BaseModel):
    content: dict
    filename: str

# --- POINTS D'ACCÈS (ENDPOINTS) ---

@app.get("/", tags=["Général"])
async def root():
    return {"message": "Bienvenue sur l'API de Génération d'Épreuves IA"}

# --- GESTION SUPABASE ---

@app.post("/buckets/", tags=["Supabase Storage"])
async def api_create_bucket(config: BucketCreate):
    """Crée un nouvel espace de stockage (bucket) dans Supabase."""
    try:
        result = create_bucket(
            SUPABASE_URL, 
            SUPABASE_KEY, 
            config.bucket_name, 
            public=config.public,
            allowed_mime_types=config.allowed_mime_types,
            file_size_limit=config.file_size_limit
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/buckets/upload-exercises", tags=["Supabase Storage"])
async def api_upload_exercises(req: ExerciseUploadRequest):
    """
    Upload des exercices extraits dans le bucket spécifié.
    La fonction traite chaque texte, extrait la structure et upload sur Supabase.
    """
    try:
        # Appel de votre fonction mise à jour
        # La fonction retourne None selon votre implémentation
        upload_exercice_in_bucket(
            content_file=req.content_file, 
            bucket=req.bucket_name
        )
        return {
            "status": "success", 
            "message": f"{len(req.content_file)} blocs d'exercices envoyés pour traitement et upload dans le bucket {req.bucket_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/buckets/", tags=["Supabase Storage"])
async def api_list_buckets():
    """Liste tous les espaces de stockage (buckets) disponibles."""
    try:
        buckets = list_buckets()
        return {"status": "success", "buckets": buckets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

 
@app.get("/buckets/{bucket_name}/folders", tags=["Supabase Storage"])
async def api_list_folders(bucket_name: str, folder: str = ""):
    """Liste les dossiers présents dans un bucket donné."""
    try:
        folders = list_folders(bucket_name, folder=folder)
        return {"bucket": bucket_name, "folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/buckets/{bucket_name}/files", tags=["Supabase Storage"])
async def api_list_files(bucket_name: str, folder_name: str):
    """Affiche les fichiers contenus dans un dossier précis du bucket."""
    try:
        files = list_files_in_folder(bucket_name, folder_name)
        return {"bucket": bucket_name, "folder": folder_name, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/buckets/{bucket_name}", tags=["Supabase Storage"])
async def api_delete_bucket(bucket_name: str, force: bool = True):
    """Supprime un bucket et tout son contenu."""
    try:
        delete_bucket(bucket_name, force=force)
        return {"status": "success", "message": f"Bucket {bucket_name} supprimé."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- OCR & TRAITEMENT PDF ---

@app.post("/ocr/process-pdf", tags=["OCR & Extraction"])
async def process_pdf(file: UploadFile = File(...)):
    """
    Télécharge un PDF, applique l'OCR Mathpix et retourne le texte extrait.
    """
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        full_text, pages_texts = MathpixLoader(pdf_path=temp_path)
        
        # Nettoyage du fichier temporaire
        os.remove(temp_path)
        
        return {
            "filename": file.filename,
            "full_text": full_text,
            "pages_count": len(pages_texts)
        }
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

# --- GÉNÉRATION D'ÉPREUVES ---

@app.post("/exams/generate", tags=["Génération"])
async def generate_exam(req: GenerationRequest):
    """
    Génère une épreuve innovante en se basant sur les exercices d'un bucket.
    """
    try:
        resultat = generer_exercices_innovants(
            bucket_name=req.bucket_name,
            texte_entete=req.texte_entete,
            logo_gauche=req.logo_gauche,
            level_indication=req.level_indication,
            indication_exemple=req.indication_exemple,
            logo_droit=req.logo_droit,
            titre_document=req.titre_document,
            sous_titre=req.sous_titre,
            generer_latex=req.generer_latex
        )
        return {"status": "success", "result": resultat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/exams/save-latex", tags=["Génération"])
async def save_latex_file(req: SaveLatexRequest):
    """Sauvegarde localement le contenu LaTeX généré dans un fichier .tex."""
    try:
        os.makedirs("latex", exist_ok=True)
        path = f"latex/{req.filename}"
        if not path.endswith(".tex"):
            path += ".tex"
            
        a,b = sauvegarder_latex(req.content, path)
        return {"status": "success", "path": path,'latex_content': b}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)