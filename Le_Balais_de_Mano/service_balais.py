"""
Service métier pour Le Balais de Mano.
Gère les prix de vente/réparation des balais, ainsi que leurs recettes de fabrication.
"""

import json
import os
import re
import unicodedata
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

PRIX_FILE = os.path.join(DATA_DIR, 'prix_balais.json')
RECETTES_FILE = os.path.join(DATA_DIR, 'recettes_balais.json')


def normaliser(texte: str) -> str:
    """Minuscules + accents ignorés pour comparaison."""
    if not texte:
        return ''
    n = unicodedata.normalize('NFD', str(texte))
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')
    n = n.lower().strip()
    return re.sub(r'\s+', ' ', n)


def singulariser(texte: str) -> str:
    """Forme comparable d'un nom : sans casse, accents, ponctuation ni pluriel."""
    base = re.sub(r"[^\w\s]", ' ', normaliser(texte))
    mots = []
    for mot in base.split():
        if len(mot) > 5 and mot.endswith('eaux'):
            mot = mot[:-1]
        elif len(mot) > 4 and mot.endswith('aux'):
            mot = mot[:-3] + 'al'
        elif len(mot) > 3 and mot.endswith('s') and not mot.endswith('ss'):
            mot = mot[:-1]
        mots.append(mot)
    return ' '.join(mots)


def trouver_cle(dico: dict, nom: str, partiel: bool = True):
    """Cherche une clé dans un dictionnaire sans tenir compte de la casse/accents/pluriel."""
    if not nom or not dico:
        return None
    if nom in dico:
        return nom

    nom_norm = normaliser(nom)
    for cle in dico:
        if normaliser(cle) == nom_norm:
            return cle

    nom_sing = singulariser(nom)
    for cle in dico:
        if singulariser(cle) == nom_sing:
            return cle

    if not partiel:
        return None

    candidats = [cle for cle in dico
                 if nom_sing and (nom_sing in singulariser(cle) or singulariser(cle) in nom_sing)]
    if candidats:
        return min(candidats, key=len)
    return None


def get_prix_cle(type_action: str) -> str:
    """Retourne Prixdeventesbalais ou Prixderepabalais."""
    return 'Prixdeventesbalais' if 'vent' in str(type_action).lower() else 'Prixderepabalais'


def charger_prix() -> dict:
    cles_requises = ["Prixdeventesbalais", "Prixderepabalais"]
    data = {}
    if os.path.exists(PRIX_FILE):
        try:
            with open(PRIX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Erreur chargement {PRIX_FILE}: {e}")
            data = {}

    modifie = False
    for k in cles_requises:
        if k not in data or not isinstance(data[k], dict):
            data[k] = {}
            modifie = True

    if modifie or not os.path.exists(PRIX_FILE):
        sauvegarder_prix(data)

    return data


def sauvegarder_prix(data: dict):
    try:
        with open(PRIX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde {PRIX_FILE}: {e}")


def charger_recettes() -> dict:
    cle = "Recettesbalais"
    data = {}
    if os.path.exists(RECETTES_FILE):
        try:
            with open(RECETTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Erreur chargement {RECETTES_FILE}: {e}")
            data = {}

    if cle not in data or not isinstance(data[cle], dict):
        data[cle] = {}
        sauvegarder_recettes(data)

    return data


def sauvegarder_recettes(data: dict):
    try:
        with open(RECETTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde {RECETTES_FILE}: {e}")


def ajouter_prix_balai(nom: str, type_action: str, stats: str) -> tuple[bool, str]:
    nom_propre = re.sub(r'\s+', ' ', nom.strip())
    if not nom_propre:
        return False, "Nom invalide"
    cle = get_prix_cle(type_action)
    data = charger_prix()
    data[cle][nom_propre] = {
        "stats": stats.strip() if stats.strip() else "Aucun détail renseigné",
        "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
    }
    sauvegarder_prix(data)
    return True, nom_propre


def supprimer_prix_balai(nom: str, type_action: str) -> tuple[bool, str]:
    cle = get_prix_cle(type_action)
    data = charger_prix()
    cle_trouvee = trouver_cle(data.get(cle, {}), nom)
    if not cle_trouvee:
        return False, nom
    del data[cle][cle_trouvee]
    sauvegarder_prix(data)
    return True, cle_trouvee


def ajouter_recette_balai(nom: str, ingredients: str, details: str = "") -> tuple[bool, str]:
    nom_propre = re.sub(r'\s+', ' ', nom.strip())
    if not nom_propre:
        return False, "Nom invalide"
    data = charger_recettes()
    data['Recettesbalais'][nom_propre] = {
        "ingredients": ingredients.strip(),
        "details": details.strip(),
        "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
    }
    sauvegarder_recettes(data)
    return True, nom_propre


def supprimer_recette_balai(nom: str) -> tuple[bool, str]:
    data = charger_recettes()
    cle_trouvee = trouver_cle(data.get('Recettesbalais', {}), nom)
    if not cle_trouvee:
        return False, nom
    del data['Recettesbalais'][cle_trouvee]
    sauvegarder_recettes(data)
    return True, cle_trouvee


def lister_recettes_ordonnees() -> list[tuple[str, str]]:
    """Retourne la liste des recettes de balais."""
    data = charger_recettes()
    balais_dict = data.get('Recettesbalais', {})
    return [(k, "🧹 Balais") for k in sorted(balais_dict.keys())]


def extraire_bois_argentciel(texte_ingredients: str) -> float:
    """
    Retourne la quantité totale de Bois d'Argentciel mentionnée
    directement dans le texte des ingrédients (sans tenir compte des ratios de kits).
    """
    if not texte_ingredients:
        return 0.0
    total = 0.0
    for ligne in str(texte_ingredients).splitlines():
        texte = ligne.strip().lstrip('•-*·–—').strip()
        if not texte:
            continue
        if 'argentciel' not in normaliser(texte):
            continue
        # Formats acceptés : "Nx ...", "N x ..." ou "N × ..."
        m = re.match(r'^(\d[\d\s\xa0\u202f]*)[x×]', texte, re.IGNORECASE)
        if not m:
            m = re.match(r'^(\d[\d\s\xa0\u202f]+)', texte)
        if m:
            try:
                qte = float(re.sub(r'[\s\xa0\u202f]', '', m.group(1)))
                total += qte
            except ValueError:
                pass
    return total
