-- Competitor prices table (references produits)
CREATE TABLE prix_concurrents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    produit_id INT NOT NULL,                  -- foreign key column
    concurrent_nom NVARCHAR(100),
    prix DECIMAL(10,2),
    frais_livraison DECIMAL(10,2),
    date_releve DATE,
    CONSTRAINT UQ_prix_concurrents UNIQUE (produit_id, concurrent_nom, date_releve),
    FOREIGN KEY (produit_id) REFERENCES produits(id)   -- ✅ fixed: references produits
);

-- Market signals table
CREATE TABLE signaux_marche (
    id INT IDENTITY(1,1) PRIMARY KEY,
    produit_id INT NOT NULL,
    volume_recherche INT,
    note_moyenne DECIMAL(3,2),
    date_signal DATE,
    FOREIGN KEY (produit_id) REFERENCES produits(id)   -- ✅ fixed
);