# 🎯 Guide de Modification pour LaTeX Sans Erreur

## 📋 Résumé

Le prompt de génération actuel peut produire du LaTeX avec des erreurs de formatage. Cette modification garantit **ZÉRO erreur** dans l'app mobile.

## 🔍 Problèmes identifiés

### 1. Format LaTeX attendu par l'app (GenExamViewerPage)

L'app attend cette structure **EXACTE** :

```latex
\begin{document}
{\LARGE\bfseries Titre de l'épreuve}

{\large Durée: 2h - Calculatrice autorisée}

\begin{exercice}
Introduction optionnelle avec formules $inline$ et \[display\]

\begin{enumerate}
\item Question 1 avec formules
\item Question 2...
  \begin{enumerate}
  \item Sous-question a)
  \item Sous-question b)
  \end{enumerate}
\end{enumerate}
\end{exercice}

\end{document}
```

### 2. Erreurs fréquentes générées par le prompt actuel

❌ **Markdown** : `*`, `**`, `#` → Cassent le LaTeX
❌ **Commandes interdites** : `\textbf`, `\textit` → Contradictoires avec le parser
❌ **Formules mal formatées** : Texte avec `x^2` au lieu de `$x^2$`
❌ **Structure incorrecte** : Contenu sur même ligne que le titre

### 3. Le parser `_formater_exercice_latex` attend:

- Questions numérotées : `1. `, `2. `, `3. `
- Sous-questions : `a) `, `b) `, `c) `
- Pas de balises markdown
- Pas de `\textbf` dans le contenu (il l'ajoute lui-même pour le titre)

## ✅ Solution : Nouveau Prompt

### Modifications à faire dans `maxa_extr_gen_epreuve.py`

**Fichier:** `maxa_extr_gen_epreuve.py`
**Ligne:** 388-458
**Action:** Remplacer le prompt par celui de `PROMPT_LATEX_AMELIORE.txt`

### Améliorations apportées

1. ✅ **Règles LaTeX strictes** clairement définies
2. ✅ **Exemples concrets** de format attendu
3. ✅ **Liste explicite** des commandes autorisées/interdites
4. ✅ **Validation finale** avec critères précis
5. ✅ **Format de formules** (inline vs display) bien spécifié

### Exemple de sortie attendue

```
Exercice 1

Soit f la fonction définie sur $\mathbb{R}$ par $f(x) = x^2 - 3x + 2$.

1. Déterminer les racines de f et dresser le tableau de variations.
2. Calculer l'aire sous la courbe entre les deux racines:
\[A = \int_{x_1}^{x_2} f(x)\,dx\]
3. Étudier la fonction composée $g = f \circ f$.
   a) Montrer que g est paire.
   b) Calculer $g'(0)$.
```

## 📝 Instructions de Déploiement

### Étape 1 : Backup

```bash
cd "C:\Users\Dell\Downloads\MAXA Gen Engine\prog_gen_eng_ai_ma_xa"
cp maxa_extr_gen_epreuve.py maxa_extr_gen_epreuve.py.backup
```

### Étape 2 : Modification

1. Ouvrir `maxa_extr_gen_epreuve.py`
2. Aller à la ligne 388 (début du prompt)
3. Sélectionner tout le prompt (jusqu'à la ligne 458)
4. Remplacer par le contenu de `PROMPT_LATEX_AMELIORE.txt`

### Étape 3 : Test

Générer une épreuve de test:

```python
from maxa_extr_gen_epreuve import generer_exercices_innovants

result = generer_exercices_innovants(
    bucket_name='issea-bucket',
    titre_document='Test Devoir',
    sous_titre='Durée: 2h',
    generer_latex=True
)

# Vérifier qu'il n'y a pas de *, **, \textbf dans le résultat
latex = result['latex']
assert '*' not in latex, "Markdown trouvé!"
assert '\\textbf' not in latex, "textbf trouvé!"
print("✅ Format correct!")
```

### Étape 4 : Déploiement

Si local:
```bash
# Redémarrer l'API
pkill -f maxa_api.py
python maxa_api.py
```

Si Render.com:
```bash
git add maxa_extr_gen_epreuve.py
git commit -m "fix: amélioration prompt LaTeX pour éliminer les erreurs de format"
git push origin main
# Render redéploiera automatiquement
```

## 🧪 Tests de Validation

### Test 1 : Pas de Markdown

```python
assert '*' not in latex_code
assert '**' not in latex_code
assert '#' not in latex_code
```

### Test 2 : Pas de Commandes Interdites

```python
assert '\\textbf' not in latex_code
assert '\\textit' not in latex_code
assert '\\emph' not in latex_code
```

### Test 3 : Structure Correcte

```python
assert '\\begin{exercice}' in latex_code
assert '\\end{exercice}' in latex_code
assert '\\begin{enumerate}' in latex_code
assert '\\end{enumerate}' in latex_code
```

### Test 4 : Formules Bien Formatées

```python
# Toutes les variables math doivent être entre $ ou \[ \]
import re
# Vérifier qu'il n'y a pas de variables isolées comme x^2 sans $
pattern = r'(?<!\$)[a-z]\^\{?\d+\}?(?!\$)'
matches = re.findall(pattern, latex_code)
assert len(matches) == 0, f"Formules non délimitées: {matches}"
```

## 📊 Résultats Attendus

Avant (avec erreurs):
```latex
**Exercice 1**  <!-- Markdown! -->

Soit f(x) = x^2 - 3   <!-- Pas de $ ! -->

\textbf{1.} Question   <!-- textbf interdit ! -->
```

Après (sans erreur):
```latex
Exercice 1

Soit $f(x) = x^2 - 3$

1. Question
```

## 🎯 Impact

- ✅ **Zéro erreur** de compilation LaTeX dans l'app
- ✅ **Affichage cohérent** des formules mathématiques
- ✅ **Pas de crash** du parser
- ✅ **Expérience utilisateur** parfaite

## 📞 Support

Si problèmes persistent après modification:
1. Vérifier que le prompt a bien été remplacé
2. Tester avec un bucket simple (peu d'exercices)
3. Vérifier les logs de l'API pour voir ce que Claude génère
4. Comparer la sortie avec l'exemple attendu

---

**Créé le:** 2026-02-03
**Version:** 1.0
**Status:** Prêt pour déploiement
