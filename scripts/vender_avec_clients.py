import pyodbc
from datetime import datetime

# Connexion à la base de données
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\SQLEXPRESS;'
    'DATABASE=BaseInventaire;'
    'Trusted_Connection=yes;'
)

cursor = conn.cursor()

def ensure_date_in_dim_temps(date_obj):
    """S'assure que la date existe dans dim_temps (insère si manquante)."""
    cursor.execute("SELECT 1 FROM dim_temps WHERE date_complete = ?", (date_obj,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO dim_temps (date_complete, annee, trimestre, mois, nom_mois, jour_mois, jour_semaine, nom_jour, est_weekend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_obj,
            date_obj.year,
            (date_obj.month - 1) // 3 + 1,
            date_obj.month,
            date_obj.strftime('%B'),
            date_obj.day,
            date_obj.isoweekday(),
            date_obj.strftime('%A'),
            1 if date_obj.weekday() >= 5 else 0
        ))

try:
    # --- Informations client (dim_client) ---
    print("Informations client :")
    client_id = input("ID client (ou laissez vide pour un nouveau client) : ").strip()
    
    if client_id == "":
        # Créer un nouveau client
        code_client = input("Code client (unique) : ")
        nom_complet = input("Nom complet : ")
        email = input("Email : ")
        segment = input("Segment (ex: particulier, professionnel) : ")
        pays = input("Pays : ")
        cursor.execute("""
            INSERT INTO dim_client (code_client, nom_complet, email, segment, date_acquisition, pays)
            OUTPUT INSERTED.client_id
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code_client, nom_complet, email, segment, datetime.now().date(), pays))
        client_id = cursor.fetchone()[0]
        print(f"Nouveau client créé avec l'ID : {client_id}")
    else:
        client_id = int(client_id)
        cursor.execute("SELECT client_id FROM dim_client WHERE client_id = ?", (client_id,))
        if not cursor.fetchone():
            print(f"L'ID client {client_id} n'existe pas.")
            exit(1)

    # --- Produit et quantité ---
    product_id = int(input("ID du produit : "))
    quantity_sold = int(input("Quantité vendue : "))

    # Vérifier le stock actuel depuis mouvements_stock
    cursor.execute("""
        SELECT COALESCE(SUM(quantite_variation), 0)
        FROM mouvements_stock
        WHERE id_produit = ?
    """, (product_id,))
    current_stock = cursor.fetchone()[0]

    if current_stock < quantity_sold:
        print(f"Stock insuffisant ! Stock actuel : {current_stock}")
    else:
        sale_date = datetime.now().date()
        
        # S'assurer que la date existe dans dim_temps
        ensure_date_in_dim_temps(sale_date)
        
        # Récupérer le prix unitaire du produit
        cursor.execute("SELECT prix_unitaire FROM produits WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            print(f"Produit ID {product_id} introuvable.")
            exit(1)
        unit_price = float(row[0])
        
        # --- Insertion dans la table fait_ventes ---
        cursor.execute("""
            INSERT INTO fait_ventes (produit_id, client_id, date_complete, quantite_vendue, prix_unitaire)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, client_id, sale_date, quantity_sold, unit_price))
        
        # --- Insertion du mouvement de stock (vente) ---
        cursor.execute("""
            INSERT INTO mouvements_stock (id_produit, quantite_variation, type_mouvement)
            VALUES (?, ?, 'VENTE')
        """, (product_id, -quantity_sold))
        
        conn.commit()
        print(f"Vente enregistrée. Nouveau stock : {current_stock - quantity_sold}")

except Exception as e:
    conn.rollback()
    print(f"Erreur : {e}")

finally:
    cursor.close()
    conn.close()