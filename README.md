Projet : Bons plans E.Leclerc
=============================

Ce dépôt contient un petit scraper Selenium et une interface web légère pour afficher des "bons plans" extraits depuis le site e.leclerc. Le but est pédagogique : rassembler des offres, les stocker dans une base SQLite et les présenter via une page web réactive.

Contenu principal
-----------------
- `utiles.py`  : classes principales — `LeclercScraper` (Selenium) et `DBManager` (SQLite).
- `front.py`   : serveur Flask simple et template HTML/CSS/JS pour afficher les deals.
- `app.py`     : point d'entrée (si différent de `front.py` dans ce dépôt).
- `test_selenium.py` : script de test / exemple (si présent).
- `leclerc.ipynb` : carnet Jupyter avec expérimentations.
- `leclerc_deals.db` : base SQLite (générée après exécution du scraper).

Prérequis
---------
- Python 3.8+ (recommandé)
- Google Chrome installé (ou Chromium compatible)
- Packages Python : Flask, selenium, webdriver-manager

Installation rapide (PowerShell)
-------------------------------
# Option recommandée : créer et activer un environnement virtuel
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install flask selenium webdriver-manager

Lancer l'interface web
----------------------
Exécuter le serveur Flask intégré (ex. depuis la racine du dépôt) :

python app.py

Par défaut, l'application écoute sur `http://127.0.0.1:5000/`. La page affiche les deals présents dans `leclerc_deals.db`.

