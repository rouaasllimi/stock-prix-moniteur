# low_stock_alert.py
import pyodbc
import pandas as pd
from datetime import date
import smtplib
from email.message import EmailMessage   
import os

# Configuration
CONN_STR = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=_____;'
    'DATABASE=BaseInventaire;'
    'Trusted_Connection=yes;'
)

# Paramètres email 
ENABLE_EMAIL = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "_____@gmail.com"
EMAIL_PASSWORD = "*******"
EMAIL_RECIPIENT = "_____@gmail.com"

# Nom du fichier CSV avec la date du jour
CSV_FILENAME = f"alertes_stock_prix_{date.today()}.csv"

# Fonctions

def obtenir_stock_actuel():
    """Retourne un dictionnaire {id_produit: stock_actuel} depuis mouvements_stock."""
    conn = pyodbc.connect(CONN_STR)
    query = """
        SELECT id_produit, COALESCE(SUM(quantite_variation), 0) AS stock_actuel
        FROM mouvements_stock
        GROUP BY id_produit
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return dict(zip(df['id_produit'], df['stock_actuel']))

def obtenir_produits_avec_seuil():
    """Retourne un DataFrame avec id, nom, seuil_reapprovisionnement, prix_unitaire."""
    conn = pyodbc.connect(CONN_STR)
    query = "SELECT id, nom, seuil_reapprovisionnement, prix_unitaire FROM produits"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def obtenir_derniers_prix_concurrents():
    """Retourne un DataFrame avec le dernier prix par produit depuis prix_concurrents."""
    conn = pyodbc.connect(CONN_STR)
    query = """
        WITH ranked AS (
            SELECT 
                produit_id,
                concurrent_nom,
                prix,
                date_releve,
                ROW_NUMBER() OVER (PARTITION BY produit_id ORDER BY date_releve DESC) as rn
            FROM prix_concurrents
        )
        SELECT produit_id, concurrent_nom, prix, date_releve
        FROM ranked
        WHERE rn = 1
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def classer_stock(actuel, seuil):
    """Retourne 'En rupture', 'Stock faible' ou 'OK'."""
    if actuel <= 0:
        return "En rupture"
    elif actuel < seuil:
        return "Stock faible"
    else:
        return "OK"

def evaluer_risque_prix(prix_propre, prix_concurrent):
    """Retourne (niveau_risque, message) basé sur le prix concurrent."""
    if prix_concurrent is None or prix_propre is None:
        return "N/A", "Pas de prix concurrent"
    if prix_concurrent < prix_propre * 0.7:
        return "Critique", f"Concurrent {prix_concurrent:.2f}€ ( -{int((1 - prix_concurrent/prix_propre)*100)}% )"
    elif prix_concurrent < prix_propre * 0.85:
        return "Élevé", f"Concurrent {prix_concurrent:.2f}€ ( -{int((1 - prix_concurrent/prix_propre)*100)}% )"
    elif prix_concurrent < prix_propre:
        return "Modéré", f"Concurrent {prix_concurrent:.2f}€ ( -{int((1 - prix_concurrent/prix_propre)*100)}% )"
    else:
        return "OK", f"Prix concurrent plus haut ({prix_concurrent:.2f}€)"

def exporter_csv(df, nom_fichier):
    """Sauvegarde le DataFrame en CSV."""
    df.to_csv(nom_fichier, index=False, encoding='utf-8-sig')
    print(f"CSV exporté : {nom_fichier}")

def envoyer_email_alerte(nom_fichier_csv, table_html, texte_resume):
    """Envoie un email avec pièce jointe CSV et tableau HTML."""
    if not ENABLE_EMAIL:
        return

    msg = EmailMessage()
    msg['Subject'] = f"Alertes stock & prix - {date.today()}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECIPIENT

    # Corps du message (HTML)
    corps = f"""
    <h2>Rapport quotidien des alertes</h2>
    <p>{texte_resume}</p>
    <h3>Détail des alertes</h3>
    {table_html}
    <p>Fichier CSV attaché.</p>
    """
    msg.set_content(corps, subtype='html')

    # Attacher le fichier CSV
    with open(nom_fichier_csv, 'rb') as f:
        donnees_fichier = f.read()
        nom_fichier = os.path.basename(nom_fichier_csv)
    msg.add_attachment(donnees_fichier, maintype='application', subtype='octet-stream', filename=nom_fichier)

    # Envoi
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as serveur:
            serveur.starttls()
            serveur.login(EMAIL_SENDER, EMAIL_PASSWORD)
            serveur.send_message(msg)
        print("Email envoyé avec succès.")
    except Exception as e:
        print(f"Erreur envoi email : {e}")

def main():
    print("=== Gestion des alertes stock et prix ===")
    
    # 1. Récupération des données
    stock_dict = obtenir_stock_actuel()
    produits_df = obtenir_produits_avec_seuil()
    concurrents_df = obtenir_derniers_prix_concurrents()
    
    # 2. Pour chaque produit, calcul du statut stock et du risque prix
    resultats = []
    for _, ligne in produits_df.iterrows():
        prod_id = ligne['id']
        prod_nom = ligne['nom']
        seuil = ligne['seuil_reapprovisionnement']
        prix_propre = ligne['prix_unitaire']
        
        actuel = stock_dict.get(prod_id, 0)
        statut_stock = classer_stock(actuel, seuil)
        
        lignes_conc = concurrents_df[concurrents_df['produit_id'] == prod_id]
        if not lignes_conc.empty:
            nom_conc = lignes_conc.iloc[0]['concurrent_nom']
            prix_conc = lignes_conc.iloc[0]['prix']
            niveau_risque, msg_risque = evaluer_risque_prix(prix_propre, prix_conc)
        else:
            nom_conc = None
            prix_conc = None
            niveau_risque, msg_risque = "N/A", "Aucun prix concurrent"
        
        resultats.append({
            'id_produit': prod_id,
            'produit_nom': prod_nom,
            'stock_actuel': actuel,
            'seuil_reapprovisionnement': seuil,
            'statut_stock': statut_stock,
            'prix_vente': prix_propre,
            'concurrent_nom': nom_conc if nom_conc else '',
            'prix_concurrent': prix_conc if prix_conc else '',
            'risque_prix': niveau_risque,
            'detail_risque': msg_risque
        })
    
    # 3. Création du DataFrame et filtrage des alertes
    alertes_df = pd.DataFrame(resultats)
    alertes_df = alertes_df[
        (alertes_df['statut_stock'].isin(['Stock faible', 'En rupture'])) |
        (alertes_df['risque_prix'].isin(['Critique', 'Élevé']))
    ]
    
    # 4. Export CSV
    exporter_csv(alertes_df, CSV_FILENAME)
    
    # 5. Affichage résumé
    nb_stock_faible = len(alertes_df[alertes_df['statut_stock'].isin(['Stock faible', 'En rupture'])])
    nb_risque_prix = len(alertes_df[alertes_df['risque_prix'].isin(['Critique', 'Élevé'])])
    print(f"\nRésumé : {nb_stock_faible} produits avec stock faible/rupture")
    print(f"         {nb_risque_prix} produits avec risque prix élevé")
    print(f"         Total alertes : {len(alertes_df)}")
    
    # 6. Envoi email 
    if ENABLE_EMAIL and len(alertes_df) > 0:
        table_html = alertes_df.to_html(classes='table', index=False)
        resume = f"{nb_stock_faible} alertes stock, {nb_risque_prix} alertes prix."
        envoyer_email_alerte(CSV_FILENAME, table_html, resume)
    elif ENABLE_EMAIL:
        print("Aucune alerte – email non envoyé.")

if __name__ == "__main__":
    main()