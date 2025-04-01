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
