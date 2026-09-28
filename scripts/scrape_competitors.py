# scrape_competitors.py
import pyodbc
from datetime import date
import random

# Connexion à la base SQL Server
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\SQLEXPRESS;'
    'DATABASE=BaseInventaire;'
    'Trusted_Connection=yes;'
)
curseur = conn.cursor()

def obtenir_tous_produits():
    """Récupère tous les produits de la table produits (id et nom)."""
    curseur.execute("SELECT id, nom FROM produits")
    return curseur.fetchall()

def generer_prix_simule(nom_produit):
    """
    Simule un prix concurrent.
    À remplacer par un vrai scraping plus tard si nécessaire.
    """
    return round(random.uniform(5, 200), 2)

def inserer_prix_concurrent(produit_id, nom_concurrent, prix, frais_livraison=0.0):
    """Insère ou met à jour le prix concurrent du jour."""
    aujourdhui = date.today()
    try:
        curseur.execute("""
            INSERT INTO prix_concurrents (produit_id, concurrent_nom, prix, frais_livraison, date_releve)
            VALUES (?, ?, ?, ?, ?)
        """, (produit_id, nom_concurrent, prix, frais_livraison, aujourdhui))
        conn.commit()
        print(f"Insertion : produit {produit_id} | {nom_concurrent} | {prix} €")
    except pyodbc.IntegrityError:
        # Mise à jour si déjà présent aujourd'hui
        curseur.execute("""
            UPDATE prix_concurrents
            SET prix = ?, frais_livraison = ?
            WHERE produit_id = ? AND concurrent_nom = ? AND date_releve = ?
        """, (prix, frais_livraison, produit_id, nom_concurrent, aujourdhui))
        conn.commit()
        print(f"Mise à jour : produit {produit_id} | {nom_concurrent} | {prix} €")

def main():
    print("Début de la simulation des prix concurrents...")
    produits = obtenir_tous_produits()

    concurrents = ["Amazon", "Cdiscount", "Fnac"]

    for id_produit, nom_produit in produits:
        for concurrent in concurrents:
            prix = generer_prix_simule(nom_produit)
            # Frais de livraison gratuits si prix > 50€
            frais = 0.0 if prix > 50 else 4.99
            inserer_prix_concurrent(id_produit, concurrent, prix, frais)

    print("Simulation terminée. Vérifiez la table prix_concurrents.")

if __name__ == "__main__":
    main()