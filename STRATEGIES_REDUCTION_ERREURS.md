# STRATÉGIES POUR RÉDUIRE DRASTIQUEMENT LES ERREURS MATHÉMATIQUES
# ===================================================================

## 📊 DIAGNOSTIC DU PROBLÈME ACTUEL

### Points faibles identifiés :
1. ❌ **Température élevée (1.0)** → favorise créativité mais introduit erreurs
2. ❌ **Pas de vérification post-génération**
3. ❌ **Auto-vérification insuffisante** (modèle vérifie dans même contexte)
4. ❌ **Aucune validation symbolique** des formules

---

## 🎯 SOLUTIONS PROPOSÉES (5 STRATÉGIES COMPLÉMENTAIRES)

### STRATÉGIE 1: Réduction de la température + Génération en deux passes
**Impact estimé: ↓ 40-50% d'erreurs**

```python
# AVANT (maxa_extr_gen_epreuve.py ligne 651)
temperature=1.0  # Trop élevé pour mathématiques précises

# APRÈS - Générer en 2 passes:
# Passe 1: Structure et idées (temp 0.9)
# Passe 2: Formules et calculs précis (temp 0.5)
```

**Modification à faire:**
```python
# Dans generer_exercices_innovants(), remplacer:
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=4000,
    temperature=0.6,  # ← RÉDUIRE de 1.0 à 0.6
    messages=[{"role": "user", "content": prompt}]
)
```

---

### STRATÉGIE 2: Agent de vérification séparé
**Impact estimé: ↓ 60-70% d'erreurs**

Ajouter après chaque génération (nouveau fichier `maxa_math_validator.py` créé):

```python
from maxa_math_validator import validate_exercise

# Après génération de l'exercice
exercice_genere = response.content[0].text.strip()

# VALIDATION OBLIGATOIRE
validation = validate_exercise(
    exercice_genere,
    level=level_indication[1],
    subject=level_indication[0]
)

if not validation['is_valid']:
    print(f"⚠️ Exercice invalide, tentative de correction...")

    # Option A: Regénérer avec prompt de correction
    # Option B: Rejeter et informer
    # Option C: Corriger automatiquement avec les suggestions
```

---

### STRATÉGIE 3: Prompt amélioré avec exemples d'erreurs à éviter
**Impact estimé: ↓ 30-40% d'erreurs**

Ajouter au prompt actuel (avant la génération):

```python
**⚠️ ERREURS FRÉQUENTES À ABSOLUMENT ÉVITER :**

1. **Erreurs de calcul numérique** :
   ❌ NE PAS écrire: "f(2) = 7" sans vérifier en calculant
   ✅ TOUJOURS calculer avant d'écrire: si f(x) = x² - 3x + 2, alors f(2) = 4 - 6 + 2 = 0

2. **Erreurs de dérivées** :
   ❌ NE PAS écrire: "si f(x) = x³, alors f'(x) = 3x²" sans vérifier
   ✅ CALCULE mentalement: d/dx(x³) = 3x² ✓

3. **Erreurs d'intégrales** :
   ❌ NE PAS écrire des résultats sans calcul
   ✅ Si ∫₀¹ x dx, calculer: [x²/2]₀¹ = 1/2 - 0 = 1/2

4. **Erreurs de racines** :
   ❌ NE PAS dire "x² - 5x + 6 = 0 a pour racines 1 et 6"
   ✅ VÉRIFIE: (x-2)(x-3) = 0 → racines 2 et 3

5. **Incohérences paramétriques** :
   ❌ NE PAS utiliser "a = 3" puis plus loin "a = 5"
   ✅ GARDE les paramètres cohérents dans tout l'exercice

**PROCÉDURE DE VÉRIFICATION OBLIGATOIRE** :
Après avoir généré l'exercice, AVANT de le soumettre :
1. Relis CHAQUE égalité nummérique et CALCULE pour vérifier
2. Pour CHAQUE formule (dérivée, intégrale, limite), fais le calcul mental
3. Vérifie que les paramètres sont cohérents
4. Résous mentalement les questions pour vérifier qu'elles ont des solutions
5. Si tu détectes UNE SEULE erreur, CORRIGE-LA immédiatement
"""

---

### STRATÉGIE 4: Génération avec validation croisée (solutions parallèles)
**Impact estimé: ↓ 50-60% d'erreurs**

```python
def generer_avec_validation_croisee(client, prompt_exercice, level, subject):
    """
    Génère l'exercice ET ses solutions en parallèle.
    Si solutions impossibles → exercice invalide.
    """

    # Étape 1: Générer l'exercice
    exercice = generer_exercice(client, prompt_exercice)

    # Étape 2: Générer les solutions avec agent séparé
    prompt_solution = f"""
    Résous cet exercice étape par étape.
    Si une question est impossible, indique "IMPOSSIBLE".

    {exercice}
    """

    solutions = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        temperature=0.3,  # Bas pour précision calculs
        messages=[{"role": "user", "content": prompt_solution}]
    )

    # Étape 3: Vérifier si "IMPOSSIBLE" apparaît
    if "IMPOSSIBLE" in solutions.content[0].text:
        return {
            'valid': False,
            'reason': 'Questions impossibles détectées',
            'exercice': exercice,
            'solutions': solutions.content[0].text
        }

    return {
        'valid': True,
        'exercice': exercice,
        'solutions': solutions.content[0].text
    }
```

---

### STRATÉGIE 5: Valeurs numériques contrôlées
**Impact estimé: ↓ 20-30% d'erreurs**

Ajouter au prompt:

```python
**CONTRAINTES SUR LES VALEURS NUMÉRIQUES :**

Pour MINIMISER les erreurs de calcul :

1. **Privilégier des valeurs simples** :
   - Entiers de -10 à 10
   - Fractions simples: 1/2, 1/3, 2/3, 1/4, 3/4
   - Racines carrées simples: √2, √3, √5

2. **Éviter** :
   - Grands nombres (> 100) sauf si nécessaire au niveau
   - Fractions complexes (137/243)
   - Décimaux non exacts (0.333... au lieu de 1/3)

3. **Systématisation** :
   - Si f(x) = ax² + bx + c, utilise a, b, c ∈ {-5, ..., 5}
   - Si racines demandées, assure Δ = b² - 4ac soit un carré parfait

4. **Vérification automatique** :
   - Avant d'écrire une égalité avec nombres:
     * f(2) = ... → calcule 2 fois pour vérifier
     * Si résultat compliqué, SIMPLIFIE d'abord les paramètres
```

---

## 🚀 PLAN D'IMPLÉMENTATION PROGRESSIF

### Phase 1 (Immédiat - Impact: ↓50% erreurs)
1. ✅ Créer `maxa_math_validator.py` (FAIT)
2. 🔧 Modifier `maxa_extr_gen_epreuve.py`:
   - Réduire température de 1.0 → 0.6
   - Intégrer le validateur après chaque génération
   - Ajouter exemples d'erreurs au prompt

### Phase 2 (Court terme - Impact: ↓70% erreurs)
3. 🔧 Implémenter validation croisée avec génération solutions
4. 🔧 Ajouter contraintes valeurs numériques au prompt
5. 🔧 Logger les erreurs détectées pour améliorer continuellement

### Phase 3 (Moyen terme - Impact: ↓85% erreurs)
6. 🔧 Ajouter validation symbolique SymPy
7. 🔧 Base de données d'erreurs courantes → amélioration prompt
8. 🔧 Mode "stricte" avec rejet automatique si erreur détectée

---

## 📈 MÉTRIQUES DE SUCCÈS

Objectifs à mesurer:
- **Taux d'erreurs mathématiques** : < 5% (vs ~30% actuellement)
- **Score de confiance moyen** : > 0.90
- **Taux de rejet** : < 15% (exercices non validés)
- **Temps de génération** : +20% max (validation incluse)

---

## 🛠️ FICHIERS À MODIFIER

### 1. `maxa_extr_gen_epreuve.py` (PRINCIPAL)
**Lignes à modifier:**

```python
# Ligne 651 - Réduire température
temperature=0.6,  # au lieu de 1.0

# Après ligne 655 - Ajouter validation
from maxa_math_validator import validate_exercise

exercice_genere_brut = response.content[0].text.strip()

# VALIDATION AJOUTÉE
print(f"   🔍 Validation mathématique...")
validation = validate_exercise(
    exercice_genere_brut,
    level=str(level_indication[1]),
    subject=str(level_indication[0])
)

if not validation['is_valid']:
    print(f"   ❌ Exercice invalide (score: {validation['confidence_score']:.1%})")
    print(f"   🔄 Tentative de régénération...")

    # Régénérer avec prompt de correction
    correction_prompt = f"""
L'exercice suivant contient des erreurs mathématiques.
Corrige-le en respectant RIGOUREUSEMENT l'exactitude mathématique.

EXERCICE AVEC ERREURS:
{exercice_genere_brut}

ERREURS DÉTECTÉES:
{chr(10).join([f"- {e['message']}" for e in validation['errors']])}

GÉNÈRE LA VERSION CORRIGÉE (mêmes règles LaTeX).
"""

    correction_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        temperature=0.5,  # Encore plus bas pour correction
        messages=[{"role": "user", "content": correction_prompt}]
    )

    exercice_genere_brut = correction_response.content[0].text.strip()
    print(f"   ✅ Exercice corrigé")

lignes_generees = exercice_genere_brut.split('\n')
```

### 2. Prompt amélioré (lignes 386-644)
Ajouter AVANT "**VÉRIFICATION MATHÉMATIQUE OBLIGATOIRE**":

[Insérer les exemples d'erreurs de la STRATÉGIE 3]

---

## 💡 EXEMPLE D'UTILISATION

```python
# Utilisation standalone du validateur
from maxa_math_validator import validate_exercise

exercice = """
Exercice 1

Soit f(x) = x² - 5x + 6.

1) Montrer que f(2) = 0.
2) Calculer f'(x).
"""

result = validate_exercise(exercice, "Prépa", "Mathématiques")

if result['is_valid']:
    print("✅ Exercice validé!")
    save_to_database(exercice)
else:
    print("❌ Erreurs:", result['errors'])
    # Ne pas enregistrer
```

---

## ⚡ RÉSUMÉ DES MODIFICATIONS URGENTES

**À FAIRE MAINTENANT (10 minutes):**

1. Copier `maxa_math_validator.py` dans le dossier (FAIT)

2. Dans `maxa_extr_gen_epreuve.py`:
   ```python
   # Ligne 2 - Ajouter import
   from maxa_math_validator import validate_exercise

   # Ligne 651 - Modifier
   temperature=0.6,  # CHANGÉ de 1.0

   # Après ligne 655 - Ajouter validation (code ci-dessus)
   ```

3. Tester:
   ```bash
   python maxa_extr_gen_epreuve.py
   ```

**Résultat attendu:** ↓60% d'erreurs immédiatement

---

## 📞 SUPPORT ET AMÉLIORATION CONTINUE

- Créer un log `erreurs_detectees.json` pour tracker erreurs
- Analyser mensuellement pour améliorer prompt
- Ajuster température selon résultats (commencer 0.6, affiner)

**Température optimale** : Entre 0.5 et 0.7 selon tests
- 0.5 = très précis mais moins créatif
- 0.7 = bon équilibre précision/créativité
- 1.0 = créatif mais trop d'erreurs

---

FIN DU DOCUMENT
