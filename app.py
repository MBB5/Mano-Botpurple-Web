"""
Site Web ManoBotPurple — Consultation publique des données du projet.

Fonctionnalités :
- Prix de vente & réparation des Baguettes et des Balais
- Recettes d'artisanat (Baguettes / Balais) avec synthèse Kits / Cristaux / Magicarium
- Calculateur de coût (kits de base, cristaux, magicarium, galyons, temps de récolte)
- Page Infos : fiches Baguettes / Balais avec filtres, images (admin), durabilité, récupération
- Tutoriel et connexion administrateur (mot de passe : variable MOT_DE_PASSE_ADMIN)

Le site lit directement les fichiers JSON du projet : aucune donnée dupliquée.
"""

import os
import re
import sys
import json
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session

# Racine du projet (Site_Web est à la racine de 7Wands)
RACINE_PROJET = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(RACINE_PROJET))

from La_Baguette_de_Mano import service_baguettes  # moteur de calcul des kits
from Le_Balais_de_Mano import service_balais

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "manobotpurple-cle-locale"

MOT_DE_PASSE_ADMIN = os.environ.get("MOT_DE_PASSE_ADMIN", "Donvale")

BAGUETTE_DATA = RACINE_PROJET / "La_Baguette_de_Mano" / "data"
BALAIS_DATA = RACINE_PROJET / "Le_Balais_de_Mano" / "data"
FICHES_PATH = Path(__file__).parent / "data" / "fiches.json"

DUREES_VALIDES = ["Très bonne", "Bonne", "Mauvaise"]


def _lire_json(chemin: Path, cle_defaut: str = "") -> dict:
    """Charge un JSON ; si cle_defaut est vide, renvoie tout le document."""
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if not cle_defaut else data.get(cle_defaut, {})
    except Exception:
        return {}


def _recherche(q: str, items: dict) -> dict:
    """Filtre un dict {nom: infos} selon une requête (insensible casse/accents)."""
    if not q:
        return items
    q_norm = service_baguettes.normaliser(q)
    resultat = {}
    for nom, infos in items.items():
        hay = service_baguettes.normaliser(nom + " " + json.dumps(infos, ensure_ascii=False))
        if q_norm in hay:
            resultat[nom] = infos
    return resultat


def _ecrire_json(chemin: Path, data: dict):
    """Écrit un JSON avec encodage UTF-8 et indentation lisible."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _chemin_module(module: str, type_data: str) -> Path:
    if type_data == "prix":
        if module == "baguettes":
            return BAGUETTE_DATA / "prix_baguettes.json"
        if module == "balais":
            return BALAIS_DATA / "prix_balais.json"
        raise ValueError("module inconnu")
    if type_data == "recettes":
        if module == "baguettes":
            return BAGUETTE_DATA / "recettes_baguettes.json"
        if module == "balais":
            return BALAIS_DATA / "recettes_balais.json"
        raise ValueError("module inconnu")
    raise ValueError("type de donnée inconnu")


# ---------------------------------------------------------------- Pages
@app.route("/")
def accueil():
    prix_b = _lire_json(BAGUETTE_DATA / "prix_baguettes.json", "")
    rec_b = _lire_json(BAGUETTE_DATA / "recettes_baguettes.json", "Recettesbaguettes")
    prix_bal = _lire_json(BALAIS_DATA / "prix_balais.json", "")
    rec_bal = _lire_json(BALAIS_DATA / "recettes_balais.json", "Recettesbalais")
    stats = {
        "ventes_baguettes": len(prix_b.get("Prixdeventesbaguettes", {})),
        "repas_baguettes": len(prix_b.get("Prixderepabaguettes", {})),
        "recettes_baguettes": len(rec_b),
        "ventes_balais": len(prix_bal.get("Prixdeventesbalais", {})),
        "repas_balais": len(prix_bal.get("Prixderepabalais", {})),
        "recettes_balais": len(rec_bal),
        "total_baguettes": len(prix_b.get("Prixdeventesbaguettes", {})),
        "total_balais": len(prix_bal.get("Prixdeventesbalais", {})),
    }
    return render_template("index.html", stats=stats)


# ---------------------------------------------------------------- API JSON
@app.route("/api/prix/<module>")
def api_prix(module: str):
    q = request.args.get("q", "").strip()
    if module == "baguettes":
        data = _lire_json(BAGUETTE_DATA / "prix_baguettes.json", "")
        vente = _recherche(q, data.get("Prixdeventesbaguettes", {}))
        repa = _recherche(q, data.get("Prixderepabaguettes", {}))
    elif module == "balais":
        data = _lire_json(BALAIS_DATA / "prix_balais.json", "")
        vente = _recherche(q, data.get("Prixdeventesbalais", {}))
        repa = _recherche(q, data.get("Prixderepabalais", {}))
    else:
        return jsonify({"erreur": "module inconnu"}), 404
    return jsonify({"vente": vente, "reparation": repa})


@app.route("/api/recettes/<module>")
def api_recettes(module: str):
    q = request.args.get("q", "").strip()
    if module == "baguettes":
        items = _lire_json(BAGUETTE_DATA / "recettes_baguettes.json", "Recettesbaguettes")
    elif module == "balais":
        items = _lire_json(BALAIS_DATA / "recettes_balais.json", "Recettesbalais")
    else:
        return jsonify({"erreur": "module inconnu"}), 404

    items = _recherche(q, items)
    resultat = {}
    for nom, info in items.items():
        if not isinstance(info, dict):
            info = {"ingredients": str(info), "details": ""}
        ingr = info.get("ingredients") or ""
        tarif_m = service_baguettes.resoudre_tarif_magicarium(request.args.get("tarif"))
        analyse = service_baguettes.analyser_composants_recette(ingr, tarif_m) if module == "baguettes" else None
        resultat[nom] = {
            "ingredients": ingr,
            "details": info.get("details", ""),
            "date": info.get("date", ""),
            "analyse": analyse,
        }
    return jsonify(resultat)


# ---------------------------------------------------------------- Fiches / Admin
def _prix_valeur(texte: str):
    """Extrait le premier montant en galyons d'un texte du type '52 500 G.'"""
    if not texte:
        return None
    m = re.search(r"([\d\s\u202f\u00a0.,]+)\s*G\b", str(texte))
    if not m:
        return None
    nombre = re.sub(r"[^\d]", "", m.group(1))
    return int(nombre) if nombre else None


@app.route("/api/fiches")
def api_fiches():
    """Liste complète des baguettes et balais avec leurs fiches."""
    fiches = _lire_json(FICHES_PATH, "")
    prix_b = _lire_json(BAGUETTE_DATA / "prix_baguettes.json", "")
    prix_bal = _lire_json(BALAIS_DATA / "prix_balais.json", "")

    def pack(prix_doc, cle, type_item):
        items = {}
        for src in (prix_doc.get("Prixdeventes" + cle, {}), prix_doc.get("Prixderepa" + cle, {})):
            for nom, info in src.items():
                fiche = fiches.get(nom, {})
                items[nom] = {
                    "type": type_item,
                    "coutant": info.get("coutant", ""),
                    "client": info.get("client", ""),
                    "pnj": info.get("pnj", ""),
                    "prix_vente": _prix_valeur(info.get("pnj", "")),
                    "prix_coutant": _prix_valeur(info.get("coutant", "")),
                    "image": fiche.get("image", ""),
                    "recuperation": fiche.get("recuperation", 1),
                    "duree": fiche.get("duree", ""),
                }
        return items

    return jsonify({
        "baguettes": pack(prix_b, "baguettes", "Baguette"),
        "balais": pack(prix_bal, "balais", "Balais"),
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.get_json(silent=True) or {}
    if body.get("mot_de_passe") == MOT_DE_PASSE_ADMIN:
        session["admin"] = True
        return jsonify({"admin": True})
    return jsonify({"admin": False, "erreur": "Mot de passe incorrect"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("admin", None)
    return jsonify({"admin": False})


@app.route("/api/session")
def api_session():
    return jsonify({"admin": bool(session.get("admin"))})


@app.route("/api/prix/<module>", methods=["POST"])
def api_prix_post(module: str):
    """Réservé admin : met à jour un prix de vente ou de réparation."""
    if not session.get("admin"):
        return jsonify({"erreur": "Connexion administrateur requise"}), 403

    body = request.get_json(silent=True) or {}
    nom = (body.get("nom") or "").strip()
    if not nom:
        return jsonify({"erreur": "Nom manquant"}), 400

    categorie = (body.get("categorie") or "vente").strip().lower()
    if module == "baguettes":
        data = _lire_json(BAGUETTE_DATA / "prix_baguettes.json", "")
        if categorie == "repa":
            section = "Prixderepabaguettes"
        else:
            section = "Prixdeventesbaguettes"
    elif module == "balais":
        data = _lire_json(BALAIS_DATA / "prix_balais.json", "")
        if categorie == "repa":
            section = "Prixderepabalais"
        else:
            section = "Prixdeventesbalais"
    else:
        return jsonify({"erreur": "module inconnu"}), 404

    items = data.setdefault(section, {})
    item = items.setdefault(nom, {})
    for cle in ["coutant", "client", "pnj"]:
        if cle in body:
            item[cle] = (body.get(cle) or "").strip()
    items[nom] = item
    _ecrire_json(_chemin_module(module, "prix"), data)
    return jsonify({"ok": True, "module": module, "categorie": categorie, "nom": nom, "item": item})


@app.route("/api/recettes/<module>", methods=["POST"])
def api_recettes_post(module: str):
    """Réservé admin : met à jour une recette."""
    if not session.get("admin"):
        return jsonify({"erreur": "Connexion administrateur requise"}), 403

    body = request.get_json(silent=True) or {}
    nom = (body.get("nom") or "").strip()
    if not nom:
        return jsonify({"erreur": "Nom manquant"}), 400

    if module == "baguettes":
        data = _lire_json(BAGUETTE_DATA / "recettes_baguettes.json", "")
        section = "Recettesbaguettes"
    elif module == "balais":
        data = _lire_json(BALAIS_DATA / "recettes_balais.json", "")
        section = "Recettesbalais"
    else:
        return jsonify({"erreur": "module inconnu"}), 404

    items = data.setdefault(section, {})
    item = items.setdefault(nom, {})
    if "ingredients" in body:
        item["ingredients"] = (body.get("ingredients") or "").strip()
    if "details" in body:
        item["details"] = (body.get("details") or "").strip()
    if "date" in body:
        item["date"] = (body.get("date") or "").strip()
    items[nom] = item
    _ecrire_json(_chemin_module(module, "recettes"), data)
    return jsonify({"ok": True, "module": module, "nom": nom, "item": item})


@app.route("/api/fiches", methods=["POST"])
def api_fiches_post():
    """Réservé admin : met à jour l'image / récupération / durabilité d'une fiche."""
    if not session.get("admin"):
        return jsonify({"erreur": "Connexion administrateur requise"}), 403
    body = request.get_json(silent=True) or {}
    nom = (body.get("nom") or "").strip()
    if not nom:
        return jsonify({"erreur": "Nom manquant"}), 400
    fiches = _lire_json(FICHES_PATH, "")
    fiche = fiches.get(nom, {})
    if "image" in body:
        fiche["image"] = (body.get("image") or "").strip()
    if "recuperation" in body:
        try:
            fiche["recuperation"] = max(1, int(body.get("recuperation")))
        except (TypeError, ValueError):
            pass
    if "duree" in body:
        duree = (body.get("duree") or "").strip()
        fiche["duree"] = duree if duree in DUREES_VALIDES else ""
    fiches[nom] = fiche
    FICHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FICHES_PATH, "w", encoding="utf-8") as f:
        json.dump(fiches, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "nom": nom, "fiche": fiche})


@app.route("/api/calcul", methods=["POST"])
def api_calcul():
    """Calculateur de coût : réutilise le moteur du bot."""
    body = request.get_json(silent=True) or {}
    texte = body.get("texte", "")
    tarif_m = service_baguettes.resoudre_tarif_magicarium(body.get("tarif"))
    analyse = service_baguettes.analyser_composants_recette(texte, tarif_m)
    return jsonify(analyse)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
