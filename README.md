# For Sure Système de Génération d'Épreuves IA (FastAPI)

Ce projet est une API puissante conçue pour automatiser la création d'épreuves académiques, de devoirs surveillés et de concours (particulièrement pour les mathématiques et les CPGE). Il combine la gestion de stockage cloud avec Supabase, l'extraction de texte mathématique par OCR via Mathpix, et un moteur de rendu LaTeX.

## 🚀 Fonctionnalités principales

Gestion du Stockage (Supabase) : Création, énumération (listing) et suppression de buckets. Organisation structurée des exercices.

Traitement OCR Avancé : Conversion de documents PDF complexes en texte exploitable grâce à l'API Mathpix, préservant les formules LaTeX.

Moteur de Génération d'Épreuves : Création intelligente de sujets avec en-têtes personnalisés, logos institutionnels et consignes spécifiques.

Export et Téléchargement : Génération de fichiers .tex prêts pour la compilation et téléchargement direct via l'API.

## 📋 Prérequis

Python : 3.10.19 (voir le fichier runtime.txt)

Environnement : Un compte Supabase (URL et Clé API) et un compte Mathpix (App ID et App Key).

## 🛠️ Installation et Configuration

Cloner le dépôt :

git clone <url-du-depot>
cd <nom-du-projet>


Installer les dépendances :

pip install -r requirements.txt


Version de Python :
Assurez-vous que votre environnement utilise la version spécifiée dans runtime.txt :
python-3.10.19

## 🖥️ Exécution

Lancez le serveur de développement Uvicorn :

uvicorn main:app --reload


L'API sera disponible par défaut sur http://127.0.0.1:8000.

## 📖 Documentation de l'API

L'API génère automatiquement sa propre documentation interactive :

Swagger UI (Interactif) : http://127.0.0.1:8000/docs

ReDoc : http://127.0.0.1:8000/redoc

Points d'accès (Endpoints) notables

Méthode

Endpoint

Description

GET

/buckets/

Liste tous les espaces de stockage (buckets).

POST

/buckets/upload-exercises

Extrait et upload des exercices vers Supabase.

POST

/ocr/process-pdf

Traite un PDF via OCR et retourne le texte LaTeX.

POST

/exams/generate

Assemble une épreuve à partir d'un bucket.

POST

/exams/download-latex

Génère et renvoie le fichier .tex pour téléchargement.

## 📂 Structure des fichiers

.
├── main.py                    # Point d'entrée principal de l'API FastAPI
├── runtime.txt                # Spécification de la version Python
├── requirements.txt           # Liste des dépendances Python
├── .env                       # Variables de configuration (clés API)
├── temp_latex/                # Dossier temporaire pour les fichiers générés
├── maxa_supabase_ops.py       # Fonctions de gestion Supabase
├── maxa_extr_gen_epreuve.py   # Logique métier de génération et d'upload
└── extrat_info_pdf.py         # Intégration de l'OCR Mathpix


⚖️ Licence

Ce projet est la propriété de [Votre Organisation/Nom]. Toute utilisation ou reproduction non autorisée est strictement interdite.
