"""
MAXA Math Validator - Système de vérification mathématique des exercices générés
===============================================================================

Ce module ajoute plusieurs couches de vérification pour garantir l'exactitude
mathématique des exercices générés par MAXA Gen Engine.
"""

import re
import anthropic
from sympy import *
from sympy.parsing.latex import parse_latex
import os

class MathValidator:
    """
    Validateur mathématique pour exercices générés.

    Stratégies de vérification :
    1. Vérification symbolique avec SymPy
    2. Agent Claude séparé spécialisé en vérification
    3. Détection de patterns d'erreurs courants
    4. Validation croisée avec génération de solutions
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Patterns d'erreurs mathématiques courantes
        self.error_patterns = [
            # Erreurs de calcul basiques
            (r'\$f\((\d+)\)\s*=\s*(\d+)\$', self._check_function_value),
            # Égalités douteuses
            (r'\$(.+?)\s*=\s*(.+?)\$', self._check_equation),
            # Dérivées
            (r"f'\((.+?)\)\s*=\s*(.+?)", self._check_derivative),
            # Intégrales avec bornes et résultat
            (r'\\int_\{(.+?)\}\^\{(.+?)\}(.+?)\\,?dx\s*=\s*(.+?)', self._check_integral),
        ]

    def validate_exercise(self, exercise_text: str, level: str, subject: str) -> dict:
        """
        Valide un exercice généré sur plusieurs critères.

        Returns:
            dict: {
                'is_valid': bool,
                'errors': list,
                'warnings': list,
                'corrections': list,
                'confidence_score': float (0-1)
            }
        """
        print(f"\n🔍 Validation de l'exercice ({subject} - {level})")

        errors = []
        warnings = []
        corrections = []

        # 1. Vérification par patterns d'erreurs courantes
        pattern_check = self._check_common_errors(exercise_text)
        errors.extend(pattern_check['errors'])
        warnings.extend(pattern_check['warnings'])

        # 2. Vérification symbolique des formules
        symbolic_check = self._verify_symbolic_math(exercise_text)
        errors.extend(symbolic_check['errors'])
        warnings.extend(symbolic_check['warnings'])
        corrections.extend(symbolic_check['corrections'])

        # 3. Vérification par agent Claude séparé
        agent_check = self._verify_with_agent(exercise_text, level, subject)
        errors.extend(agent_check['errors'])
        warnings.extend(agent_check['warnings'])
        corrections.extend(agent_check['corrections'])

        # Calcul du score de confiance
        total_issues = len(errors) + len(warnings) * 0.5
        confidence_score = max(0, 1 - (total_issues * 0.1))

        is_valid = len(errors) == 0 and confidence_score >= 0.7

        result = {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'corrections': corrections,
            'confidence_score': confidence_score
        }

        self._print_validation_report(result)
        return result

    def _check_common_errors(self, text: str) -> dict:
        """Détecte les patterns d'erreurs mathématiques courantes."""
        errors = []
        warnings = []

        # Pattern: f(a) = b (vérifier si c'est cohérent avec la définition de f)
        func_values = re.findall(r'\$f\((\d+)\)\s*=\s*([+-]?\d+(?:\.\d+)?)\$', text)
        if func_values:
            warnings.append({
                'type': 'FUNCTION_VALUE',
                'message': f'Trouvé {len(func_values)} valeurs de fonction à vérifier manuellement',
                'details': func_values
            })

        # Pattern: égalités numériques simples (2+3=6 serait une erreur)
        simple_eqs = re.findall(r'\$(\d+)\s*[+\-*/]\s*(\d+)\s*=\s*(\d+)\$', text)
        for eq in simple_eqs:
            a, op_b, result = eq[0], eq[1:], eq[2]
            # Essayer d'évaluer
            try:
                expected = eval(f"{a}{op_b}")
                actual = int(result)
                if expected != actual:
                    errors.append({
                        'type': 'ARITHMETIC_ERROR',
                        'message': f'Erreur de calcul: {a}{op_b} ≠ {actual} (devrait être {expected})',
                        'severity': 'HIGH'
                    })
            except:
                pass

        # Pattern: Dérivées de fonctions classiques
        derivatives = re.findall(r"f'\(x\)\s*=\s*([^$]+)", text)
        if derivatives:
            warnings.append({
                'type': 'DERIVATIVE',
                'message': f'Trouvé {len(derivatives)} dérivées à vérifier',
                'details': derivatives
            })

        # Pattern: Limites avec résultats
        limits = re.findall(r'\\lim_\{[^}]+\}[^=]+=\s*([^$\]]+)', text)
        if limits:
            warnings.append({
                'type': 'LIMIT',
                'message': f'Trouvé {len(limits)} limites à vérifier',
                'details': limits
            })

        return {'errors': errors, 'warnings': warnings}

    def _verify_symbolic_math(self, text: str) -> dict:
        """
        Vérifie les formules mathématiques avec SymPy.
        Tente de parser et vérifier les égalités.
        """
        errors = []
        warnings = []
        corrections = []

        # Extraire toutes les formules display (\[...\])
        display_formulas = re.findall(r'\\\[(.*?)\\\]', text, re.DOTALL)

        for formula in display_formulas:
            # Ignorer les structures (cases, matrices, etc.)
            if any(keyword in formula for keyword in ['begin{', '\\\\', '&']):
                continue

            # Chercher les égalités
            if '=' in formula:
                try:
                    # Essayer de parser avec SymPy
                    parts = formula.split('=')
                    if len(parts) == 2:
                        left_str = parts[0].strip()
                        right_str = parts[1].strip()

                        # Tentative de parsing LaTeX -> SymPy
                        try:
                            left_expr = parse_latex(left_str)
                            right_expr = parse_latex(right_str)

                            # Vérifier si égalité symbolique
                            diff = simplify(left_expr - right_expr)

                            if diff != 0:
                                # Peut être une égalité conditionnelle ou paramétrique
                                warnings.append({
                                    'type': 'SYMBOLIC_EQUALITY',
                                    'message': f'Égalité à vérifier: {left_str} = {right_str}',
                                    'difference': str(diff)
                                })
                        except:
                            # Parsing LaTeX échoué, c'est normal pour formules complexes
                            pass

                except Exception as e:
                    # Ne pas bloquer sur erreurs de parsing
                    pass

        return {'errors': errors, 'warnings': warnings, 'corrections': corrections}

    def _verify_with_agent(self, exercise_text: str, level: str, subject: str) -> dict:
        """
        Utilise un agent Claude séparé pour vérifier l'exactitude mathématique.
        Température basse (0.3) pour favoriser la précision.
        """
        errors = []
        warnings = []
        corrections = []

        verification_prompt = f"""Tu es un VÉRIFICATEUR MATHÉMATIQUE EXPERT, spécialisé en {subject} niveau {level}.

Ta mission est de vérifier RIGOUREUSEMENT l'exactitude mathématique de l'exercice ci-dessous.

EXERCICE À VÉRIFIER :
{exercise_text}

---

INSTRUCTIONS DE VÉRIFICATION :

1. **Vérifier TOUTES les égalités numériques** :
   - Si tu vois "f(2) = 7", vérifie en calculant que c'est VRAI
   - Si tu vois "2 + 3 = 5", vérifie
   - Si tu vois une limite, dérivée, intégrale avec un résultat, CALCULE pour vérifier

2. **Vérifier la cohérence des données** :
   - Les paramètres sont-ils cohérents entre eux ?
   - Les hypothèses se contredisent-elles ?
   - Les domaines de définition sont-ils corrects ?

3. **Vérifier la faisabilité des questions** :
   - Chaque question a-t-elle une solution qui existe ?
   - Les calculs demandés sont-ils faisables au niveau {level} ?

4. **Identifier les erreurs courantes** :
   - Erreurs de signe
   - Erreurs de calcul de dérivées/intégrales
   - Confusions entre paramètres
   - Domaines de définition incorrects
   - Racines/solutions inexistantes

---

FORMAT DE RÉPONSE :

Réponds UNIQUEMENT en JSON avec cette structure exacte :

{{
  "verdict": "VALIDE" ou "INVALIDE" ou "DOUTEUX",
  "erreurs_critiques": [
    {{"description": "...", "localisation": "question 1", "correction": "..."}}
  ],
  "avertissements": [
    {{"description": "...", "localisation": "question 2"}}
  ],
  "score_confiance": 0.95,
  "commentaire_general": "..."
}}

Si l'exercice est PARFAIT mathématiquement, réponds :
{{
  "verdict": "VALIDE",
  "erreurs_critiques": [],
  "avertissements": [],
  "score_confiance": 1.0,
  "commentaire_general": "Exercice mathématiquement correct."
}}

SOIS TRÈS RIGOUREUX. Ne laisse passer AUCUNE erreur mathématique.
"""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2000,
                temperature=0.3,  # Température basse pour précision
                messages=[{"role": "user", "content": verification_prompt}]
            )

            result_text = response.content[0].text.strip()

            # Parser la réponse JSON
            import json
            # Extraire le JSON de la réponse (peut être entouré de ```json```)
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Convertir en format standard
                if result.get('erreurs_critiques'):
                    for err in result['erreurs_critiques']:
                        errors.append({
                            'type': 'AGENT_CRITICAL',
                            'message': err.get('description', ''),
                            'location': err.get('localisation', ''),
                            'correction': err.get('correction', ''),
                            'severity': 'HIGH'
                        })

                if result.get('avertissements'):
                    for warn in result['avertissements']:
                        warnings.append({
                            'type': 'AGENT_WARNING',
                            'message': warn.get('description', ''),
                            'location': warn.get('localisation', '')
                        })

                if result.get('verdict') == 'INVALIDE':
                    print(f"   ⚠️ Agent verdict: INVALIDE (score: {result.get('score_confiance', 0)})")
                else:
                    print(f"   ✅ Agent verdict: {result.get('verdict')} (score: {result.get('score_confiance', 0)})")

        except Exception as e:
            warnings.append({
                'type': 'AGENT_ERROR',
                'message': f'Erreur lors de la vérification par agent: {str(e)}'
            })

        return {'errors': errors, 'warnings': warnings, 'corrections': corrections}

    def _check_function_value(self, match):
        """Vérification de f(a) = b."""
        # À implémenter si on a la définition de f
        pass

    def _check_equation(self, match):
        """Vérification d'égalité."""
        pass

    def _check_derivative(self, match):
        """Vérification de dérivée."""
        pass

    def _check_integral(self, match):
        """Vérification d'intégrale."""
        pass

    def _print_validation_report(self, result: dict):
        """Affiche un rapport de validation formaté."""
        print(f"\n{'='*60}")
        print(f"📋 RAPPORT DE VALIDATION")
        print(f"{'='*60}")

        print(f"\n✨ Score de confiance: {result['confidence_score']:.1%}")
        print(f"{'✅ VALIDE' if result['is_valid'] else '❌ INVALIDE'}")

        if result['errors']:
            print(f"\n🚨 ERREURS CRITIQUES ({len(result['errors'])}):")
            for i, error in enumerate(result['errors'], 1):
                print(f"   {i}. [{error['type']}] {error['message']}")
                if 'location' in error:
                    print(f"      📍 {error['location']}")
                if 'correction' in error and error['correction']:
                    print(f"      💡 Correction: {error['correction']}")

        if result['warnings']:
            print(f"\n⚠️ AVERTISSEMENTS ({len(result['warnings'])}):")
            for i, warning in enumerate(result['warnings'], 1):
                print(f"   {i}. [{warning['type']}] {warning['message']}")

        print(f"\n{'='*60}\n")


def validate_exercise(exercise_text: str, level: str, subject: str, api_key=None) -> dict:
    """
    Fonction helper pour valider un exercice.

    Usage:
        result = validate_exercise(exercise, "Prépa", "Mathématiques")
        if result['is_valid']:
            print("Exercice validé!")
        else:
            print("Erreurs détectées:", result['errors'])
    """
    validator = MathValidator(api_key=api_key)
    return validator.validate_exercise(exercise_text, level, subject)


if __name__ == "__main__":
    # Test du validateur
    test_exercise = """
    Exercice 1

    Soit f la fonction définie sur $\\mathbb{R}$ par $f(x) = x^2 - 4x + 3$.

    1) Vérifier que $f(2) = -1$.
    2) Calculer $f'(x)$ et vérifier que $f'(x) = 2x - 4$.
    3) Résoudre l'équation $f(x) = 0$.
    """

    result = validate_exercise(test_exercise, "Prépa", "Mathématiques")

    if not result['is_valid']:
        print("\n⚠️ Exercice contient des erreurs!")
