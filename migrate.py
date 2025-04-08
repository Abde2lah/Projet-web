import sqlite3

def add_nbAcces_column():
    con = sqlite3.connect("donnees.db")
    cur = con.cursor()

    # Vérifier si la colonne existe déjà
    cur.execute("PRAGMA table_info(Informations);")
    columns = [column[1] for column in cur.fetchall()]

    if "nbAcces" not in columns:
        cur.execute("ALTER TABLE Informations ADD COLUMN nbAcces INTEGER DEFAULT 0;")
        con.commit()
        print("Colonne 'nbAcces' ajoutée avec succès.")
    else:
        print("La colonne 'nbAcces' existe déjà.")

    con.close()

add_nbAcces_column()

import sqlite3

# Fonction pour vérifier si la table existe déjà
def table_exists(cursor, table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    result = cursor.fetchone()
    return result is not None

# Fonction pour créer la table Salle
def create_salle_table():
    # Connexion à la base de données (changez le chemin si nécessaire)
    conn = sqlite3.connect('donnees.db')
    cursor = conn.cursor()

    # Vérification si la table Salle existe déjà
    if table_exists(cursor, 'Salle'):
        print("La table 'Salle' existe déjà.")
    else:
        # Requête SQL pour créer la table Salle
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS Salle (
            NumeroSalle INT PRIMARY KEY,
            Etage INT, 
            Service VARCHAR(255),
            ObjetID INT,
            pseudonyme VARCHAR(50),
            FOREIGN KEY (ObjetID) REFERENCES Objet(ID),
            FOREIGN KEY (pseudonyme) REFERENCES Connexion(pseudonyme)
        );
        '''
        try:
            # Exécution de la requête SQL
            cursor.execute(create_table_sql)
            # Validation des changements
            conn.commit()
            print("Table 'Salle' créée avec succès.")
        except sqlite3.Error as e:
            print(f"Erreur lors de la création de la table 'Salle': {e}")
    
    # Fermeture de la connexion à la base de données
    cursor.close()
    conn.close()


def afficher_colonnes(Salle, db_path='donnees.db'):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA table_info({Salle})")
        colonnes = cursor.fetchall()

        print(f"Colonnes de la table '{Salle}' :")
        for colonne in colonnes:
            cid, nom, type_, notnull, dflt_value, pk = colonne
            print(f" - {nom} ({type_}) {'[PK]' if pk else ''}")
    
    except sqlite3.Error as e:
        print(f"Erreur SQLite : {e}")
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    afficher_colonnes("Salle")





# Exécution de la fonction pour créer la table
if __name__ == "__main__":
    create_salle_table()

