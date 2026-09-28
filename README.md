# Suivi des stocks et des prix concurrents

Outil Python + SQL Server qui suit le stock, enregistre les ventes, relève les prix des concurrents et génère un rapport quotidien d'alertes (CSV, email optionnel).

## Fichiers

| Fichier | Rôle |
|---------|------|
| `creation_des_tables.sql` | Crée `prix_concurrents` et `signaux_marche` |
| `scrape_competitors.py` | Relève les prix concurrents (simulés) |
| `low_stock_alert.py` | Génère les alertes et exporte le CSV |
| `vender_avec_clients.py` | Enregistre une vente (interactif) |
| `mise_a_jour.bat` | Lance le scraping puis les alertes |

## Prérequis

- Windows, Python 3.9+, SQL Server Express (`localhost\SQLEXPRESS`)
- ODBC Driver 17 for SQL Server
- `pip install pyodbc pandas`

## Base de données

Créer la base `BaseInventaire` avec les tables `produits`, `mouvements_stock`, `dim_client`, `dim_temps`, `fait_ventes`, puis exécuter `creation_des_tables.sql`.

## Utilisation

```bat
setx PROJECT_ROOT "C:\chemin\du\projet"
mise_a_jour.bat
```

Ou séparément :

```bash
python scrape_competitors.py
python low_stock_alert.py
python vender_avec_clients.py
```

Le rapport est exporté dans `alertes_stock_prix_AAAA-MM-JJ.csv`.


## Email

Mettre `ENABLE_EMAIL = True` dans `low_stock_alert.py` et renseigner les paramètres SMTP (mot de passe d'application Gmail recommandé).

## Limites

- Les prix concurrents sont **aléatoires** (`generer_prix_simule`) : à remplacer par un vrai scraping.
- `mise_a_jour.bat` nécessite la variable `PROJECT_ROOT`.
