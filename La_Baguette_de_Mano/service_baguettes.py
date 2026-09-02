"""
Service métier pour La Baguette de Mano.
Gère les prix de vente/réparation des baguettes, ainsi que les recettes d'artisanat et kits.
Calcule automatiquement les Kits de base, Cristaux Solaires (hors kit de base) et Magicarium requis.
"""

import json
import os
import re
import unicodedata
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

PRIX_FILE = os.path.join(DATA_DIR, 'prix_baguettes.json')
RECETTES_FILE = os.path.join(DATA_DIR, 'recettes_baguettes.json')

ORDRE_KITS = [
    "Kit de Base",
    "Kit de baguette simple",
    "Kit Renforcé",
    "Kit Magistral",
    "Kit d'Excellence",
    "Kit d'Exception",
    "Guide des Kits"
]

TARIF_KIT_DEFAUT = 3200.0


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
    """Retourne Prixdeventesbaguettes ou Prixderepabaguettes."""
    return 'Prixdeventesbaguettes' if 'vent' in str(type_action).lower() else 'Prixderepabaguettes'


def charger_prix() -> dict:
    cles_requises = ["Prixdeventesbaguettes", "Prixderepabaguettes"]
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
    cle = "Recettesbaguettes"
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


def ajouter_prix_baguette(nom: str, type_action: str, stats: str) -> tuple[bool, str]:
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


def supprimer_prix_baguette(nom: str, type_action: str) -> tuple[bool, str]:
    cle = get_prix_cle(type_action)
    data = charger_prix()
    cle_trouvee = trouver_cle(data.get(cle, {}), nom)
    if not cle_trouvee:
        return False, nom
    del data[cle][cle_trouvee]
    sauvegarder_prix(data)
    return True, cle_trouvee


def ajouter_recette_baguette(nom: str, ingredients: str, details: str = "") -> tuple[bool, str]:
    nom_propre = re.sub(r'\s+', ' ', nom.strip())
    if not nom_propre:
        return False, "Nom invalide"
    data = charger_recettes()
    data['Recettesbaguettes'][nom_propre] = {
        "ingredients": ingredients.strip(),
        "details": details.strip(),
        "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
    }
    sauvegarder_recettes(data)
    return True, nom_propre


def supprimer_recette_baguette(nom: str) -> tuple[bool, str]:
    data = charger_recettes()
    cle_trouvee = trouver_cle(data.get('Recettesbaguettes', {}), nom)
    if not cle_trouvee:
        return False, nom
    del data['Recettesbaguettes'][cle_trouvee]
    sauvegarder_recettes(data)
    return True, cle_trouvee


def lister_recettes_ordonnees() -> list[tuple[str, str]]:
    """Retourne la liste des recettes de baguettes et kits ordonnés."""
    data = charger_recettes()
    b_dict = data.get('Recettesbaguettes', {})

    kits = []
    for k in ORDRE_KITS:
        if k in b_dict:
            kits.append((k, "📦 Kit"))
    for k in b_dict.keys():
        if ("kit" in k.lower() or "guide" in k.lower()) and k not in ORDRE_KITS:
            kits.append((k, "📦 Kit"))

    baguettes = []
    for k in sorted(b_dict.keys()):
        if "kit" not in k.lower() and "guide" not in k.lower():
            baguettes.append((k, "🪄 Baguette"))

    return kits + baguettes


# ===== Moteur d'analyse Cristaux Solaires & Magicarium =====

# Ratios élémentaires des paliers de kits (hors kit de base)
RATIOS_KITS = {
    "kit de base": {"kits_base": 1.0, "cristaux_extra": 0.0, "magicarium": 0.0},
    "kit de baguette simple": {"kits_base": 1.0, "cristaux_extra": 0.0, "magicarium": 0.0},
    "kit renforce": {"kits_base": 7.0, "cristaux_extra": 1.0, "magicarium": 12.0},
    "kit magistral": {"kits_base": 70.0, "cristaux_extra": 10.0, "magicarium": 120.0},
    "kit d excellence": {"kits_base": 700.0, "cristaux_extra": 100.0, "magicarium": 1200.0},
    "kit d exception": {"kits_base": 7000.0, "cristaux_extra": 1000.0, "magicarium": 12000.0},
}


# Constantes économiques et de récolte
TARIF_MAGICARIUM_DEFAUT = 1691.0
TARIFS_MAGICARIUM = {
    "defaut": {"label": "Prix par défaut", "tarif": 1691.0},
    "gilga": {"label": "Prix Gilga", "tarif": 600.0},
    "soi": {"label": "Prix Forgeron (moi-même)", "tarif": 280.0},
}
TEMPS_RECOLTE_PAR_KIT_MINUTES = 19.0


def resoudre_tarif_magicarium(cle: str | None) -> float:
    """Retourne le tarif du Magicarium selon l'option choisie (défaut, gilga, soi)."""
    if cle and str(cle).lower() in TARIFS_MAGICARIUM:
        return TARIFS_MAGICARIUM[str(cle).lower()]["tarif"]
    return TARIF_MAGICARIUM_DEFAUT


def _extraire_nombre(texte: str) -> float | None:
    if not texte:
        return None
    t = str(texte).replace('\u202f', ' ').replace('\xa0', ' ').replace(',', '.')
    m = re.search(r'\d[\d ]*(?:\.\d+)?', t)
    if not m:
        return None
    try:
        return float(m.group(0).replace(' ', ''))
    except ValueError:
        return None


def _parser_ligne_composant(ligne: str) -> tuple[float, str] | None:
    texte = ligne.strip().lstrip('•-*·–—').strip()
    if not texte or texte.startswith('('):
        return None
    texte = re.sub(r'\s*\([^)]*\)\s*$', '', texte).strip()

    correspondance = re.match(r'^(\d[\d  \xa0]*?)\s*[x×]\s*(.+)$', texte)
    if not correspondance:
        correspondance = re.match(r'^(\d[\d  \xa0]*?)\s+(\D.+)$', texte)
    if not correspondance:
        return None

    quantite = _extraire_nombre(correspondance.group(1))
    nom = re.sub(r'\s+additionnels?$', '', correspondance.group(2).strip(), flags=re.IGNORECASE)
    if not quantite or not nom:
        return None
    return quantite, nom


def analyser_composants_recette(texte_ingredients: str, tarif_magicarium: float | None = None) -> dict:
    """
    Analyse le texte des ingrédients d'une recette et calcule :
    (tarif_magicarium : optionnel, sinon TARIF_MAGICARIUM_DEFAUT)
    - Nombre total de Kits de base
    - Nombre total de Cristaux Solaires additionnels (hors kit de base)
    - Nombre total de Magicarium additionnel
    - Coût estimé des kits en Galyons (3 200 G/u)
    - Coût estimé du Magicarium en Galyons (509 G/u)
    - Coût total estimé (Kits + Magicarium)
    - Temps estimé de récolte (19 minutes / kit de base)
    """
    total_kits_base = 0.0
    total_cristaux_extra = 0.0
    total_magicarium = 0.0

    if not texte_ingredients:
        return {
            "kits_base": 0.0,
            "cristaux_extra": 0.0,
            "magicarium": 0.0,
            "cout_kits": 0.0,
            "cout_magicarium": 0.0,
            "cout_total": 0.0,
            "tarif_magicarium": TARIF_MAGICARIUM_DEFAUT if tarif_magicarium is None else float(tarif_magicarium),
            "temps_recolte_minutes": 0.0
        }

    lignes = str(texte_ingredients).splitlines()
    for ligne in lignes:
        parsed = _parser_ligne_composant(ligne)
        if not parsed:
            continue
        qte, nom_ingr = parsed
        sing = singulariser(nom_ingr)

        if sing in RATIOS_KITS:
            r = RATIOS_KITS[sing]
            total_kits_base += qte * r["kits_base"]
            total_cristaux_extra += qte * r["cristaux_extra"]
            total_magicarium += qte * r["magicarium"]
        elif "cristal solaire" in sing:
            total_cristaux_extra += qte
        elif "magicarium" in sing:
            total_magicarium += qte

    tarif_m = TARIF_MAGICARIUM_DEFAUT if tarif_magicarium is None else float(tarif_magicarium)
    cout_kits = total_kits_base * TARIF_KIT_DEFAUT
    cout_magicarium = total_magicarium * tarif_m
    cout_total = cout_kits + cout_magicarium
    temps_recolte = total_kits_base * TEMPS_RECOLTE_PAR_KIT_MINUTES

    return {
        "kits_base": total_kits_base,
        "cristaux_extra": total_cristaux_extra,
        "magicarium": total_magicarium,
        "tarif_magicarium": tarif_m,
        "cout_kits": cout_kits,
        "cout_magicarium": cout_magicarium,
        "cout_total": cout_total,
        "temps_recolte_minutes": temps_recolte
    }

