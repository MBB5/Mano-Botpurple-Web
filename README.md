# Site Web ManoBotPurple

Site Flask qui expose les fonctionnalités du projet 7Wands (prix, recettes,
calculs kits/cristaux/magicarium, fiches baguettes/balais) et permet la
recherche publique. Il lit **directement** les fichiers JSON des modules — aucune
donnée dupliquée.

## Lancement

```powershell
cd Site_Web
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

Puis ouvrir http://localhost:5000

## Pages

- **Accueil** : statistiques globales (nb de recettes, prix)
- **Baguettes / Balais** : recherche + onglets Prix (vente / réparation) et Recettes
  (avec synthèse Kits / Cristaux / Magicarium calculée par `service_baguettes`)
- **Infos** : fiches baguettes/balais (image admin, récupération, durabilité) + filtres
- **Tutoriel** : guide du site
- **Calculateur** : colle une liste d'ingrédients et obtient le coût total

## API JSON

| Route | Description |
|---|---|
| `GET /api/prix/<baguettes\|balais>?q=` | Prix de vente + réparation |
| `GET /api/recettes/<baguettes\|balais>?q=` | Recettes + analyse des composants |
| `GET /api/fiches` | Fiches baguettes/balais |
| `POST /api/fiches` | MAJ fiche (admin) |
| `POST /api/login` / `POST /api/logout` / `GET /api/session` | Session admin |
| `POST /api/calcul {"texte": ...}` | Calculateur de coût |

## Déploiement

Compatible Railway / Render / VPS : `PORT` est lu depuis l'environnement.
Pour Railway, ajouter un `Procfile` :

```
web: python app.py
```
# Mano-Botpurple-Web
