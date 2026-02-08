
import anthropic
from dotenv import load_dotenv 
import os
import re
from maxa_supabase_ops import *
from datetime import datetime
load_dotenv()


def lire_fichier_sans_sections(chemin_fichier, 
                               motif_exclure="---SECTION---", 
                               exclure_partiel=False,
                               ignorer_casse=False,
                               encodages=("utf-8", "latin-1", "cp1252")):
    """
    Lit un fichier texte et retourne une liste des lignes filtrées.
    
    Paramètres :
    -----------
    chemin_fichier : str
        Chemin d'accès au fichier texte à lire.
    motif_exclure : str ou list[str], optionnel (défaut: "---SECTION---")
        Motif(s) à rechercher pour exclure une ligne.
    exclure_partiel : bool, optionnel (défaut: False)
        Si True, exclut les lignes contenant partiellement le motif.
        Si False, n'exclut que les lignes égales (après strip) au motif.
    ignorer_casse : bool, optionnel (défaut: False)
        Ignore la casse lors de la comparaison.
    encodages : tuple[str], optionnel (défaut: ("utf-8", "latin-1", "cp1252"))
        Liste des encodages à essayer successivement.
    
    Retourne :
    ---------
    list[str]
        Liste des lignes du fichier sans celles filtrées.
    
    Lève :
    -----
    FileNotFoundError : Si le fichier n'existe pas.
    PermissionError : Si accès refusé au fichier.
    UnicodeDecodeError : Si aucun encodage ne fonctionne.
    """
    import os
    
    # Vérification existence fichier
    if not os.path.exists(chemin_fichier):
        raise FileNotFoundError(f"Fichier non trouvé : {chemin_fichier}")
    
    if not os.path.isfile(chemin_fichier):
        raise ValueError(f"Le chemin spécifié n'est pas un fichier : {chemin_fichier}")
    
    # Normalisation du motif en liste
    motifs = [motif_exclure] if isinstance(motif_exclure, str) else motif_exclure
    
    # Tentative de lecture avec différents encodages
    contenu = None
    erreur_finale = None
    
    for enc in encodages:
        try:
            with open(chemin_fichier, 'r', encoding=enc) as f:
                contenu = f.read()
            break
        except UnicodeDecodeError as e:
            erreur_finale = e
            continue
    
    if contenu is None:
        raise UnicodeDecodeError(
            f"Aucun encodage compatible trouvé parmi {encodages}. "
            f"Dernière erreur : {erreur_finale}"
        )
    
    # Découpage en lignes et filtrage
    lignes_filtrees = []
    for ligne in contenu.split('\n'):
        ligne_nettoyee = ligne.strip()
        
        # Déterminer si la ligne doit être exclue
        exclure = False
        for motif in motifs:
            if ignorer_casse:
                motif = motif.lower()
                ligne_test = ligne_nettoyee.lower()
            else:
                ligne_test = ligne_nettoyee
            
            if exclure_partiel:
                if motif in ligne_test:
                    exclure = True
                    break
            else:
                if ligne_test == motif:
                    exclure = True
                    break
        
        if not exclure:
            lignes_filtrees.append(ligne)
    
    return lignes_filtrees



def extraire_indices_sections(liste_lignes: list) -> list:
    """
    Extrait les indices des lignes contenant des marqueurs de section
    (Exercice, Partie, Problème, etc.) via l'API Claude.
    
    Returns:
        list: Liste des indices (int) des lignes de section
    """
    import anthropic
    import json
    import os
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Conversion de la liste en texte numéroté
    texte_numerote = "\n".join([f"{i}: {ligne}" for i, ligne in enumerate(liste_lignes)])
    
    prompt = f"""Analyse ce document ligne par ligne et retourne UNIQUEMENT les indices (numéros) des lignes qui marquent le début d'une section.

    CRITÈRES D'UNE LIGNE DE SECTION :
    - Contient l'un de ces mots-clés : "Exercice", "Exo", "Partie", "Problème", "Problem", "Question", "Chapitre", "Section"
    - Généralement courte (moins de 4 phrases)
    - Souvent suivie d'un numéro (ex: "Exercice 1", "Partie A")

    DOCUMENT À ANALYSER :
    {texte_numerote}

    INSTRUCTIONS :
    1. Identifie chaque ligne qui correspond aux critères ci-dessus
    2. Retourne UNIQUEMENT un tableau JSON d'indices (nombres entiers)
    3. Format attendu : [12, 45, 78, 156]
    4. Ne retourne AUCUN texte explicatif, juste le JSON

    Réponse :"""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1000,
            temperature=0,  # Déterministe pour cohérence
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extraction de la réponse
        reponse_brute = response.content[0].text.strip()
        
        # Nettoyage (enlever éventuels backticks markdown)
        reponse_json = reponse_brute.replace("```json", "").replace("```", "").strip()
        
        # Parse du JSON
        indices = json.loads(reponse_json)
        
        print(f"✅ {len(indices)} sections détectées : {indices}")
        return indices
        
    except json.JSONDecodeError as e:
        print(f"❌ Erreur parsing JSON : {e}")
        print(f"Réponse brute : {reponse_brute}")
        return []
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []


def extraire_exercices_complets(liste_lignes: list, indices_sections: list) -> dict:
    """
    Extrait les exercices complets entre chaque indice de section.
    
    Args:
        liste_lignes: Liste de toutes les lignes du document
        indices_sections: Liste des indices de début de section
    
    Returns:
        dict: {
            'Exercice 1': ['ligne1', 'ligne2', ...],
            'Partie A': ['ligne1', 'ligne2', ...],
            ...
        }
    """
    exercices = {}
    indices_tries = sorted(indices_sections)
    
    for i, idx_debut in enumerate(indices_tries):
        # Déterminer l'indice de fin
        if i < len(indices_tries) - 1:
            idx_fin = indices_tries[i + 1] - 1
        else:
            idx_fin = len(liste_lignes) - 1
        
        # Extraire la ligne de titre
        ligne_titre = liste_lignes[idx_debut].strip()
        
        # Extraire les mots
        mots = ligne_titre.split()
        
        if len(mots) >= 2:
            premier_mot = mots[0].lower()
            deuxieme_mot = mots[1]
            
            # Vérifier si le 2ème mot contient des symboles LaTeX ou spéciaux
            # (contient $, \, {, }, ^, _, ou autres symboles non-alphanumériques)
            if re.search(r'[\$\\{}^_]|[^a-zA-Z0-9À-ÿ]', deuxieme_mot):
                # Si LaTeX/symboles détectés, utiliser le compteur (i+1)
                cle = f"{premier_mot} {i + 1}"
            else:
                # Sinon, utiliser le 2ème mot tel quel
                cle = f"{premier_mot} {deuxieme_mot}"
        elif len(mots) == 1:
            cle = f"{mots[0]} {i + 1}"
        else:
            cle = f"Section {i + 1}"
        
        # Nettoyer la clé
        cle = cle.rstrip('.,;:')
        
        # Extraire toutes les lignes de l'exercice
        contenu_exercice = liste_lignes[idx_debut:idx_fin + 1]
        
        # Stocker dans le dictionnaire
        exercices[cle] = contenu_exercice
    
    return exercices


def pipeline_extraction_exercices(liste_lignes: list) -> dict:
    """Pipeline complet : détection indices + extraction exercices (6 lignes max)"""
    import json
    import time
    
    resultat_indices = extraire_indices_sections(liste_lignes)
    indices = resultat_indices
    time.sleep(2)
    exercices = extraire_exercices_complets(liste_lignes, indices)
    return exercices,{'structure':[liste_lignes[i] for i in indices]}


def matcher_template_avec_liste(bucket_name,  api_key: str = None) -> list:
    """
    Utilise l'IA pour trouver les indices de correspondance entre template et liste originale.
    
    Args:
        template: ['Exercice n°1', 'Exercice n°2', 'Problème 1', ...]
        liste_originale: ['exercice_1', 'exercice_2', 'probleme_1', ...]
        api_key: Clé API Anthropic
    
    Returns:
        list: Indices de correspondance [0, 1, 2, ...] ou None si pas trouvé
    """
    import anthropic
    import json
    import os
    template = select_random_structure(bucket_name, "structure")
    liste_originale= list_files_in_folder(bucket_name, "")
    
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""Tu dois matcher chaque élément du TEMPLATE avec son indice correspondant dans la LISTE ORIGINALE.

TEMPLATE (ce qu'on cherche) :
{template}

LISTE ORIGINALE (avec indices) :
{list(enumerate(liste_originale))}

TÂCHE : Pour chaque élément du template, trouve l'indice dans la liste originale qui correspond.

Exemples de correspondances :
- "Exercice n°1" correspond à "exercice_1" (indice 0)
- "Exercice $\\mathbf{{n}}^{{\\circ}} \\mathbf{{2}}$" correspond à "exercice_2" (indice 1)
- "Problème 1" correspond à "probleme_1" ou "problème_1"

Ignore les différences de :
- Formatage LaTeX ($, \\mathbf, etc.)
- Majuscules/minuscules
- Accents (e vs é)
- Underscores vs espaces

Retourne UNIQUEMENT un JSON :
{{
  "indices": [0, 1, 2,  ...],
  "correspondances": [
    {{"template": "Exercice n°1", "original": "exercice_1", "indice": 0}},
    ...
  ]
}}

Si un élément du template n'a pas de correspondance, mets null."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    
    resultat = json.loads(response.content[0].text.strip().replace("```json", "").replace("```", "").strip())
    
    
    return [liste_originale[i] for i in resultat['indices'] if i is not None ]


def former_exercices_aleatoires(bucket_name: str) -> list:
    """
    Forme une liste d'exercices aléatoires en sélectionnant un exercice au hasard
    dans chaque fichier stocké dans le bucket Supabase spécifié.
    
    Args:
        bucket_name (str): Le nom du bucket Supabase contenant les fichiers d'exercices.
    
    Returns:
        list: Une liste d'exercices aléatoires extraits des fichiers du bucket.
    """
    import random
    import time
    indices = matcher_template_avec_liste(bucket_name)

    liste_exo =[]
    for i in indices:
        
        name = random.choice(list_files_in_folder(bucket_name, i)[1:] )
        texte = fetch_json_from_bucket(bucket_name,i ,name)
        liste_exo.append({i:texte})
    return liste_exo
 

def generer_exercices_innovants(
    bucket_name: str, 
    api_key: str = None,
    texte_entete: str = None,
    logo_gauche: str = None,
    logo_droit: str = None,
    titre_document: str = "Devoir de Mathématiques",
    level_indication: list = ['mathématiques','Bac+1 à CPGE'],
    indication_exemple: set = {'suite définie par récurrence → fonction définie par une équation fonctionnelle',
                              'fonction exponentielle → fonction trigonométrique ou rationnelle',
                              'probabilités discrètes → variable aléatoire continue avec densité simple',
                              'calcul formel direct → raisonnement par encadrement ou variation'},
    sous_titre: str = None,
    generer_latex: bool = True
) -> dict:
    """
    Génère des exercices VRAIMENT nouveaux et innovants, avec option de compilation LaTeX.
    
    Args:
        bucket_name : nom du bucket du concours
        api_key: Clé API Anthropic
        texte_entete: Texte personnalisé pour l'en-tête (ex: "Lycée XYZ - Classe de Terminale")
        logo_gauche: Chemin vers le logo gauche (ex: "logo_lycee.png")
        logo_droit: Chemin vers le logo droit (ex: "logo_academie.png")
        titre_document: Titre principal du document
        sous_titre: Sous-titre optionnel (ex: "Durée: 2h - Calculatrice autorisée")
        generer_latex: Si True, génère le code LaTeX complet
    
    Returns:
        dict: {
            'exercices': [...],  # Liste des exercices générés
            'latex': str,        # Code LaTeX complet (si generer_latex=True)
            'metadata': {...}    # Métadonnées (tokens, date, etc.)
        }
    """
    liste_exercices = former_exercices_aleatoires(bucket_name)
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Clé API manquante")
    
    client = anthropic.Anthropic(api_key=api_key)
    exercices_generes = []
    total_tokens_input = 0
    total_tokens_output = 0
    
    # Génération des exercices avec le prompt original (inchangé)
    for i, dict_exo in enumerate(liste_exercices, 1):
        cle_exo = list(dict_exo.keys())[0]
        contenu_original = dict_exo[cle_exo]
        
        print(f"\n🎨 Création innovante {i}/{len(liste_exercices)}: {cle_exo}")
        
        texte_exercice = "\n".join(contenu_original)
        
 
        prompt = rf"""Tu es un concepteur d'exercices "{str(level_indication[0])}" créatif et rigoureux, spécialisé dans la conception de sujets de niveau  "{str(level_indication[1])}", dans l'esprit des concours d'ingénieurs.

EXERCICE DE RÉFÉRENCE (POUR INSPIRATION UNIQUEMENT) :
{texte_exercice}

# 🎯 MISSION :
Créer un NOUVEL exercice TOTALEMENT DIFFÉRENT, de niveau "{str(level_indication[1])}", destiné à évaluer des compétences fondamentales solides en "{str(level_indication[0])}".

---

**CE QUE TU DOIS CONSERVER :**
1. Le niveau de difficulté académique : **"{str(level_indication[1])}"**, sans dépasser ce cadre
2. Le domaine "{str(level_indication[0])}" général (analyse, algèbre, probabilités, selon le cas)
3. La rigueur, la clarté et la qualité attendues d'un exercice de concours ou de contrôle exigeant
4. Environ le même nombre de questions (±2 acceptable)

---

**CE QUE TU DOIS CHANGER RADICALEMENT :**
1. ❌ AUCUNE reformulation : l'exercice doit être entièrement nouveau
2. ❌ PAS les mêmes objets "{str(level_indication[0])}" :
   - si l'original utilise ln(x), utiliser une autre fonction
   - si l'original traite une suite, préférer une fonction, une intégrale ou une équation
3. ❌ PAS le même contexte "{str(level_indication[0])}"
4. ❌ PAS la même structure de questions : changer l'ordre, la progression logique et les types de raisonnements
5. ✅ INVENTER un nouveau problème qui teste LES MÊMES COMPÉTENCES FONDAMENTALES mais par une approche différente

---

**EXEMPLES DE TRANSFORMATION CRÉATIVE (ADAPTÉS AU NIVEAU "{str(level_indication[1])}") :**
f"{{ ' -'.join(indication_exemple) }}"

---

**DIRECTIVES DE CRÉATIVITÉ :**
- Changer les objets "{str(level_indication[0])}" (fonctions, suites, variables, paramètres)
- Changer l'angle d'attaque (direct vs indirect, analytique vs graphique)
- Varier les techniques utilisées tout en restant STRICTEMENT dans le programme "{str(level_indication[1])}"
- Utiliser des contextes sobres mais originaux si pertinent
- Varier naturellement la longueur et la difficulté des sous-questions

---

**FORMAT LATEX STRICT - RESPECTE EXACTEMENT :**

1. **Titre de l'exercice** (une seule ligne):
   {cle_exo.replace('exercice', 'Exercice')}

2. **Paragraphe introductif** (optionnel, 1-3 lignes):
   Texte normal sans balises spéciales.
   Formules mathématiques inline : $expression$
   Formules mathématiques display : \[expression\]

3. **Questions principales** (numérotation obligatoire):
   1. Première question avec formules inline $x^2$ ou display \[\int_0^1 f(x)\,dx\]
   2. Deuxième question...
   3. Troisième question...

4. **Sous-questions** (sous une question principale):
   a) Première sous-question
   b) Deuxième sous-question

**RÈGLES LATEX ABSOLUES (AUCUNE EXCEPTION) :**

✅ AUTORISÉ:
- Formules inline: $f(x) = x^2$, $\ln(x)$, $e^x$
- Formules display: \[\int_0^1 f(x)\,dx\]
- Systèmes d'équations: \[\begin{{cases}} x + y = 1 \\ x - y = 0 \end{{cases}}\]
- Matrices avec parenthèses: \[\begin{{pmatrix}} a & b \\ c & d \end{{pmatrix}}\]
- Matrices avec crochets: \[\begin{{bmatrix}} 1 & 2 \\ 3 & 4 \end{{bmatrix}}\]
- Déterminants: \[\begin{{vmatrix}} a & b \\ c & d \end{{vmatrix}}\]
- Vecteurs colonnes: \[\begin{{pmatrix}} x \\ y \\ z \end{{pmatrix}}\]
- Fractions: $\frac{{a}}{{b}}$ ou \[\frac{{a}}{{b}}\]
- Dérivées: $f'(x)$, $\frac{{df}}{{dx}}$
- Intégrales: $\int_a^b f(x)\,dx$, $\displaystyle\int_a^b$
- Symboles: $\in$, $\subset$, $\forall$, $\exists$, $\to$, $\mathbb{{R}}$, $\mathbb{{N}}$, $\mathbb{{C}}$
- Indices/Exposants: $x_n$, $a^2$, $u_{{n+1}}$
- Racines: $\sqrt{{x}}$, $\sqrt[n]{{x}}$
- Limites: $\lim_{{x \to 0}}$, $\displaystyle\lim_{{n \to +\infty}}$

❌ STRICTEMENT INTERDIT:
- Markdown: *, **, _, ~~, #, ##, ###
- Gras/Italique LaTeX: \textbf{{}}, \textit{{}}, \emph{{}}, \bf, \it
- Mise en forme: \underline{{}}, \section{{}}, \subsection{{}}, \title{{}}
- Espacements manuels: \vspace{{}}, \hspace{{}}, \newline, \\\\
- Balises HTML: <b>, <i>, <u>, <strong>
- Caractères spéciaux non échappés: &, %, $, #, _, {{, }}
- Formules sans délimiteurs: écrire x^2 au lieu de $x^2$
- Double backslash en fin de ligne normale (sauf dans cases ou tableaux)

**FORMAT DES FORMULES:**
- Formules courtes (< 5 caractères): inline $x$, $f(x)$, $a+b$
- Formules moyennes: inline $\int_0^1 f(x)\,dx$
- Formules longues ou importantes: display \[\int_0^1 f(x)\,dx = \frac{{1}}{{2}}\]

**SYSTÈMES D'ÉQUATIONS - FORMAT OBLIGATOIRE:**
TOUJOURS en display mode avec cases. Séparer les équations avec \\\\
Exemple correct:
\[\begin{{cases}}
x + y = 1 \\
x - y = 0 \\
2x + 3y = 5
\end{{cases}}\]

**MATRICES - FORMAT OBLIGATOIRE:**
TOUJOURS en display mode. Utiliser & pour séparer les colonnes, \\\\ pour les lignes.
- Matrices avec parenthèses (pmatrix):
\[\begin{{pmatrix}}
1 & 2 & 3 \\
4 & 5 & 6 \\
7 & 8 & 9
\end{{pmatrix}}\]

- Matrices avec crochets (bmatrix):
\[A = \begin{{bmatrix}}
a_{{11}} & a_{{12}} \\
a_{{21}} & a_{{22}}
\end{{bmatrix}}\]

- Déterminants (vmatrix):
\[\det(A) = \begin{{vmatrix}}
a & b \\
c & d
\end{{vmatrix}} = ad - bc\]

- Vecteurs colonnes:
\[\vec{{v}} = \begin{{pmatrix}}
x \\
y \\
z
\end{{pmatrix}}\]

**IMPORTANT POUR MATRICES ET SYSTÈMES:**
- Ne JAMAIS mettre de matrices ou systèmes en inline mode ($...$)
- TOUJOURS utiliser display mode (\[...\])
- Utiliser & pour aligner les colonnes
- Utiliser \\\\ pour séparer les lignes (deux backslashes)
- Bien fermer avec \end{{pmatrix}}, \end{{bmatrix}}, \end{{vmatrix}}, ou \end{{cases}}

**EXEMPLES DE STRUCTURES CORRECTES:**

Exemple 1 - Analyse:
Exercice 1

Soit f la fonction définie sur $\mathbb{{R}}$ par $f(x) = x^2 - 3x + 2$.

1. Déterminer les racines de f et dresser le tableau de variations.
2. Calculer l'aire sous la courbe entre les deux racines:
\[A = \int_{{x_1}}^{{x_2}} f(x)\,dx\]
3. Étudier la fonction composée $g = f \circ f$.
   a) Montrer que g est paire.
   b) Calculer $g'(0)$.

Exemple 2 - Algèbre linéaire:
Exercice 2

Soit A la matrice définie par:
\[A = \begin{{bmatrix}}
1 & 2 & -1 \\
0 & 3 & 2 \\
-1 & 1 & 4
\end{{bmatrix}}\]

1. Calculer le déterminant de A:
\[\det(A) = \begin{{vmatrix}}
1 & 2 & -1 \\
0 & 3 & 2 \\
-1 & 1 & 4
\end{{vmatrix}}\]
2. Résoudre le système linéaire suivant:
\[\begin{{cases}}
x + 2y - z = 3 \\
3y + 2z = 5 \\
-x + y + 4z = 1
\end{{cases}}\]
3. Déterminer les valeurs propres de A.

**VALIDATION FINALE:**
- Chaque question commence par "1. ", "2. ", "3. "
- Chaque sous-question commence par "a) ", "b) ", "c) "
- Toutes les formules sont entre $...$ ou \[...\]
- Aucun caractère markdown (*, **, #)
- Aucune commande LaTeX de mise en forme (\textbf, \textit, etc.)
- Le titre n'a PAS de contenu sur la même ligne

---

**CRITÈRE DE SUCCÈS :**
Un étudiant de niveau "{str(level_indication[1])}" ne doit PAS penser :
"c'est juste l'exercice original reformulé",
mais plutôt :
"voici un nouvel exercice exigeant et intelligemment conçu".

Le LaTeX généré doit compiler SANS AUCUNE ERREUR dans l'app mobile.

---

GÉNÈRE MAINTENANT L'EXERCICE (UNIQUEMENT L'ÉNONCÉ, AUCUNE SOLUTION).
"""

        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4000,
                temperature=1.0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            exercice_genere_brut = response.content[0].text.strip()
            lignes_generees = exercice_genere_brut.split('\n')
            
            total_tokens_input += response.usage.input_tokens
            total_tokens_output += response.usage.output_tokens
            
            resultat = {
                cle_exo: {
                    'original': contenu_original,
                    'genere': lignes_generees,
                    'tokens': {
                        'input': response.usage.input_tokens,
                        'output': response.usage.output_tokens
                    }
                }
            }
            
            exercices_generes.append(resultat)
            
            print(f"   ✅ Créé: {len(lignes_generees)} lignes (innovant)")
            print(f"   📊 Tokens: {response.usage.input_tokens} → {response.usage.output_tokens}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            exercices_generes.append({
                cle_exo: {
                    'original': contenu_original,
                    'genere': None,
                    'erreur': str(e)
                }
            })
    
    # Génération du code LaTeX complet
    latex_code = None
    if generer_latex:
        latex_code = _generer_document_latex(
            exercices_generes,
            texte_entete=texte_entete,
            logo_gauche=logo_gauche,
            logo_droit=logo_droit,
            titre_document=titre_document,
            sous_titre=sous_titre
        )
    
    return {
        'exercices': exercices_generes,
        'latex': latex_code,
        'metadata': {
            'date_generation': datetime.now().isoformat(),
            'nombre_exercices': len(exercices_generes),
            'tokens_total': {
                'input': total_tokens_input,
                'output': total_tokens_output,
                'total': total_tokens_input + total_tokens_output
            }
        }
    }


def _generer_document_latex(
    exercices: list,
    texte_entete: str = None,
    logo_gauche: str = None,
    logo_droit: str = None,
    titre_document: str = "Devoir de Mathématiques",
    sous_titre: str = None
) -> str:
    """
    Génère le code LaTeX complet pour le document d'exercices.
    
    Args:
        exercices: Liste des exercices générés
        texte_entete: Texte de l'en-tête
        logo_gauche: Chemin du logo gauche
        logo_droit: Chemin du logo droit
        titre_document: Titre principal
        sous_titre: Sous-titre optionnel
    
    Returns:
        str: Code LaTeX complet
    """
    
    # Préambule LaTeX
    preambule = r"""\documentclass[11pt,a4paper]{article}

% Packages essentiels
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{fancyhdr}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{tikz}

% Configuration de la page
\geometry{
    a4paper,
    top=2.5cm,
    bottom=2.5cm,
    left=2cm,
    right=2cm,
    headheight=60pt
}

% Styles de page
\fancypagestyle{firstpage}{
    \fancyhf{}
"""
    
    # En-tête UNIQUEMENT pour la première page
    if texte_entete:
        preambule += r"""    \fancyhead[L]{"""
        # Remplacer le logo par du texte "MAXA Gen Engine"
        preambule += r"\textbf{\large MAXA Gen Engine}"
        preambule += r"""}
    \fancyhead[C]{"""
        # Gérer les \\ dans le texte d'en-tête en utilisant une structure appropriée
        # Remplacer \\ par \newline dans un environnement qui le supporte
        texte_entete_clean = texte_entete.replace('\\\\', '\\newline ')
        preambule += rf"\begin{{tabular}}{{c}}\textbf{{{texte_entete_clean}}}\end{{tabular}}"
        preambule += r"""}
    \fancyhead[R]{}
"""
    
    preambule += r"""    \fancyfoot[C]{\thepage}
    \renewcommand{\headrulewidth}{0.4pt}
    \renewcommand{\footrulewidth}{0.4pt}
}

% Style pour les autres pages (sans en-tête avec logos)
\fancypagestyle{otherpage}{
    \fancyhf{}
    \fancyfoot[C]{\thepage}
    \renewcommand{\headrulewidth}{0pt}
    \renewcommand{\footrulewidth}{0.4pt}
}

% Style par défaut
\pagestyle{otherpage}

% Environnements personnalisés
\newtheoremstyle{exercice}
  {10pt}{10pt}{\normalfont}{}{\bfseries}{.}{.5em}{}
\theoremstyle{exercice}
\newtheorem{exercice}{Exercice}

% Configuration des listes pour questions sur une ligne
\setlist[enumerate,1]{
    label=\textbf{\arabic*.},
    leftmargin=*,
    itemsep=8pt,
    parsep=4pt,
    topsep=8pt
}

\setlist[enumerate,2]{
    label=\textbf{\alph*)},
    leftmargin=*,
    itemsep=6pt,
    parsep=3pt
}

\begin{document}

% Appliquer le style de première page
\thispagestyle{firstpage}

"""
    
    # Titre du document
    titre = r"""
\begin{center}
    {\LARGE\bfseries """ + titre_document + r"""}
"""
    if sous_titre:
        titre += r"""    
    \vspace{0.3cm}
    
    {\large """ + sous_titre + r"""}
"""
    titre += r"""    
    \vspace{0.5cm}
    
    \hrule
    \vspace{1cm}
\end{center}

"""
    
    # Corps du document avec les exercices
    corps = ""
    for i, dict_exo in enumerate(exercices, 1):
        cle_exo = list(dict_exo.keys())[0]
        exo_data = dict_exo[cle_exo]
        
        if exo_data.get('genere'):
            # Début de l'exercice
            corps += f"\\begin{{exercice}}\n"
            
            # Parser et formater le contenu de l'exercice
            contenu_formate = _formater_exercice_latex(exo_data['genere'])
            corps += contenu_formate
            
            corps += "\\end{exercice}\n"
            
            # Espacement entre exercices
            if i < len(exercices):
                corps += "\n\\vspace{1.5cm}\n\n"
    
    # Fin du document
    fin = r"""
\end{document}
"""
    
    return preambule + titre + corps + fin


def _formater_exercice_latex(lignes: list) -> str:
    """
    Formate intelligemment les lignes d'un exercice pour LaTeX.
    Chaque question numérotée est sur sa propre ligne.
    
    Args:
        lignes: Liste des lignes brutes de l'exercice
    
    Returns:
        str: Contenu formaté en LaTeX
    """
    import re
    
    contenu = ""
    dans_enumerate = False
    dans_sous_enumerate = False
    
    for ligne in lignes:
        ligne = ligne.strip()
        
        # Ignorer les lignes vides et les commentaires
        if not ligne or ligne.startswith('#'):
            continue
        
        # Détecter le titre de l'exercice (généralement la première ligne)
        if ligne.lower().startswith('exercice') and not dans_enumerate:
            # Nettoyer le titre (enlever les balises markdown, etc.)
            titre_clean = re.sub(r'[*#]+', '', ligne).strip()
            contenu += f"\\textbf{{{titre_clean}}}\n\n"
            continue
        
        # Détecter une question principale (1., 2., 3., etc.)
        match_question = re.match(r'^(\d+)\.\s*(.*)', ligne)
        if match_question:
            # Fermer sous-enumerate si ouvert
            if dans_sous_enumerate:
                contenu += "\\end{enumerate}\n"
                dans_sous_enumerate = False
            
            # Ouvrir enumerate si pas encore fait
            if not dans_enumerate:
                contenu += "\\begin{enumerate}\n"
                dans_enumerate = True
            
            question_text = match_question.group(2).strip()
            contenu += f"\\item {question_text}\n"
            continue
        
        # Détecter une sous-question (a), b), (i), etc.)
        match_sous_question = re.match(r'^[\(]?([a-z]|[ivxlcdm]+)[\)]\s*(.*)', ligne, re.IGNORECASE)
        if match_sous_question and dans_enumerate:
            # Ouvrir sous-enumerate si pas encore fait
            if not dans_sous_enumerate:
                contenu += "\\begin{enumerate}\n"
                dans_sous_enumerate = True
            
            sous_question_text = match_sous_question.group(2).strip()
            contenu += f"\\item {sous_question_text}\n"
            continue
        
        # Ligne de texte normale (paragraphe)
        if ligne:
            # Si on est dans une liste, c'est la suite de la question précédente
            if dans_enumerate or dans_sous_enumerate:
                contenu += f"{ligne}\n"
            else:
                # Sinon c'est un paragraphe introductif
                contenu += f"{ligne}\n\n"
    
    # Fermer les environnements ouverts
    if dans_sous_enumerate:
        contenu += "\\end{enumerate}\n"
    if dans_enumerate:
        contenu += "\\end{enumerate}\n"
    
    return contenu


def sauvegarder_latex(
    resultat_generation: dict,
    nom_fichier: str = "exercices_generes.tex"
) -> str:
    """
    Sauvegarde le code LaTeX dans un fichier.
    
    Args:
        resultat_generation: Résultat de generer_exercices_innovants()
        nom_fichier: Nom du fichier de sortie
    
    Returns:
        str: Chemin du fichier créé
    """
    if not resultat_generation.get('latex'):
        raise ValueError("Aucun code LaTeX à sauvegarder. Vérifiez que generer_latex=True")
    
    with open(nom_fichier, 'w', encoding='utf-8') as f:
        f.write(resultat_generation['latex'])
    
    print(f"\n📄 Fichier LaTeX sauvegardé: {nom_fichier}")
    return nom_fichier,resultat_generation['latex']



def upload_exercice_in_bucket(content_file :list ,
                              bucket: str ='issea-bucket'):
    ''' Upload des exercices extraits dans le bucket spécifié '''
    
    liste_exo_epreuve_indice = [pipeline_extraction_exercices(i.split('\n')) for i in content_file]
    liste_exo_epreuve = [x[0] for x in liste_exo_epreuve_indice]
    list_structure = [x[1] for x in liste_exo_epreuve_indice]

    upload_exercices(bucket=bucket,liste_exo_epreuve=liste_exo_epreuve)
    upload_exercices(bucket=bucket,liste_exo_epreuve=list_structure)
    return None




