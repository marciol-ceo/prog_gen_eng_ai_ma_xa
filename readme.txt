## For sure Système de Génération d'Épreuves IA (FastAPI)

Ce projet est une API robuste permettant d'automatiser la création d'épreuves scolaires et de concours (Mathématiques, CPGE, etc.). Il intègre la gestion du stockage via Supabase, l'extraction de texte par OCR via Mathpix, et un moteur de génération de documents au format LaTeX.

### 🚀 Fonctionnalités

Gestion de Stockage (Supabase) : Création, listing et suppression de buckets. Organisation des exercices en dossiers.

Extraction OCR : Conversion de fichiers PDF ou images en texte exploitable, avec support des formules mathématiques.

Génération d'Épreuves : Création intelligente de devoirs avec en-têtes personnalisés, logos et transformation pédagogique des énoncés.

Export LaTeX : Téléchargement direct des fichiers .tex générés pour une compilation et une impression de haute qualité.

### 📋 Prérequis

Python : 3.10.19 (voir runtime.txt)

Supabase : Un compte et un projet actif (URL et Clé API).

Mathpix : Clés API pour le traitement OCR des documents mathématiques.

### 🛠️ Installation

Cloner le projet :

git clone <url-du-repo>
cd <nom-du-projet>


Installer les dépendances :

pip install -r requirements.txt


### 🖥️ Utilisation

Pour lancer l'API en mode développement :

uvicorn main:app --reload


L'API sera accessible sur http://127.0.0.1:8000.

### 📖 Documentation API

Une fois le serveur lancé, vous pouvez accéder à la documentation interactive pour tester les points d'accès :

Swagger UI : http://127.0.0.1:8000/docs

ReDoc : http://127.0.0.1:8000/redoc

Points d'accès principaux

Méthode

Endpoint

Description

GET

/buckets/

Liste tous les buckets disponibles.

POST

/buckets/upload-exercises

Upload des textes d'exercices vers Supabase.

POST

/ocr/process-pdf

Extrait le texte d'un PDF via OCR.

POST

/exams/generate

Génère une épreuve innovante (JSON/LaTeX).

POST

/exams/download-latex

Télécharge le fichier .tex généré.

### 📂 Structure du Projet

.
├── main.py              # Application FastAPI principale
├── runtime.txt          # Version de Python spécifiée
├── requirements.txt     # Liste des dépendances
├── .env                 # Variables d'environnement (non suivi par Git)
├── latex/               # Dossier de stockage local des épreuves
├── maxa_supabase_ops.py # Opérations liées à Supabase
├── maxa_extr_gen_epreuve.py # Logique de génération et upload
└── extrat_info_pdf.py   # Gestion de l'OCR et Mathpix


📄 Licence

Ce projet est la propriété de [Votre Nom/Organisation]. Toute reproduction ou utilisation commerciale sans autorisation est interdite.
