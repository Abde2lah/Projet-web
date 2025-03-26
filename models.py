import sqlite3 as sql
import bcrypt 
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import datetime
import os
from werkzeug.utils import secure_filename 

UPLOAD_FOLDER = 'static/images/'  # Dossier où les photos seront stockées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




def insert_user(nom, prenom, age, genre, email, dateNaissance, type_user, password, photo, fonction, service, pseudonyme):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()
        now = datetime.datetime.now()
        # Vérifier si une photo a été fournie, sinon mettre une image par défaut
        if not photo:
            photo = "static/images/default.png"
            filename = None
        if photo:
            filename = secure_filename(photo.filename)  # Sécurise le nom du fichier
            photo.save(os.path.join(UPLOAD_FOLDER, filename))  # Image par défaut stockée dans /static/images/
        # Insertion dans la table Informations
        cur.execute("""
            INSERT INTO Informations 
            (nom, prenom, age, genre, email, dateNaissance, type, password, photo, fonction, service, niveau, pseudonyme, points, nbAction, nbAcces) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, 0)
        """, (nom, prenom, age, genre, email, dateNaissance, type_user, password, photo, fonction, service, pseudonyme))
        # Insertion dans la table Connexion
        cur.execute("""
            INSERT INTO Connexion (pseudonyme, email, type, password, heure, confirme) 
            VALUES (?, ?, ?, ?, ?, 0)
        """, (pseudonyme, email, type_user, password, now))
        con.commit()
    except sql.Error as e:
        print(f"Database error: {e}")
        if con:
            con.rollback()
    finally:
        if con:
            con.close()


def get_user_by_username(pseudo):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM Connexion WHERE pseudonyme = ?", (pseudo,))
        user = cur.fetchone()
        return user
    except sql.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if con:
            con.close()

def get_user_by_email(email):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Connexion WHERE email = ?", (email,))
    user = cur.fetchone()
    cur.close()
    con.close()
    return user

def getUserInfos(username):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM Informations WHERE pseudonyme = ?", (username,))
        user = cur.fetchone()  # Gets only one user.
        cur.close()
        con.close()  # Closes the connection.
        if user:
            return user
        else:
            return None
    except sql.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'con' in locals() and con:
            con.close() 

def getUserInfosPublic(username):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT nom, prenom, age, fonction, service, photo FROM Informations WHERE pseudonyme = ?", (username,))
    user = cur.fetchone() #Gets only one user.
    cur.close()
    con.close() #closes the connection.
    if user:
        return user
    else:
        return None

def hash_password(password):#cryptage du mdp
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):#faire la correspondance avec le mot de passe saisi
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def generer_token_confirmation(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def verifier_token_confirmation(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
    except Exception:
        return False
    return email

def update_user(username, nom, prenom, age, genre, dateNaissance, photo, email, pseudonyme, niveau, points, nbAction):
    conn = sql.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET nom = ?, prenom = ?, age = ?, genre = ?, dateNaissance = ?, photo = ?, email = ?, pseudonyme = ?, niveau = ?, points = ?, nbAction = ?
        WHERE username = ?
    """, (nom, prenom, age, genre, dateNaissance, photo, email, pseudonyme, niveau, points, nbAction, username))
    conn.commit()
    cursor.close()
    conn.close()

def confirmation_pseudo(pseudonyme):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    if pseudonyme==None:
        return False
    cur.execute("SELECT confirme FROM Connexion WHERE pseudonyme = ?", (pseudonyme,))
    confirme=cur.fetchone()
    cur.close()
    con.close()
    if confirme is not None and confirme[0] == 1: 
        return True
    else: 
        return False

def confirmation_email(email):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    if email==None:
        return False
    cur.execute("SELECT confirme FROM Connexion WHERE email = ?", (email,))
    confirme=cur.fetchone()
    cur.close()
    con.close()
    if confirme is not None and confirme[0] == 1:
        return True
    else: 
        return False

def  insert_object(ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom,type_object, dernierReglage, consommationL, consommationW):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()
        cur.execute("INSERT INTO Objet (ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom, type, dernierReglage, consommationL, consommationW) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom,type_object, dernierReglage, consommationL, consommationW))
        con.commit()
    except sql.Error as e:
        print(f"Database error: {e}")
        if con:
            con.rollback()
    finally:
        if con:
            con.close()

def get_user_type(pseudonyme):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    if pseudonyme==None:
        return 0
    cur.execute("SELECT type FROM Informations WHERE pseudonyme = ? OR email= ?", (pseudonyme,pseudonyme))
    type_user=cur.fetchone()
    cur.close()
    con.close()
    return type_user


def update_user_points(pseudonyme, nbPoints, nbAcces):
    """ Met à jour les points et le nombre de connexions de l'utilisateur """
    if not pseudonyme:
        return

    con = sql.connect("donnees.db")
    cur = con.cursor()
    
    # Mise à jour des points et du nombre de connexions
    cur.execute("UPDATE Informations SET nbAcces = nbAcces + ?, points = points + ? WHERE pseudonyme = ? OR email = ?", 
                (nbAcces, nbPoints, pseudonyme, pseudonyme))
    con.commit()
    update_user_level(pseudonyme)  # Met à jour le niveau de l'utilisateur
    cur.close()
    con.close()

def update_user_level(pseudonyme):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    if pseudonyme==None:
        return 0
    cur.execute("SELECT points FROM Informations WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
    points=cur.fetchone()
    if points[0] >=6 and points[0] < 10:
        cur.execute("UPDATE Informations SET Niveau = 1 WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
        con.commit()
    if points[0] >=10 and points[0] < 14:
        cur.execute("UPDATE Informations SET Niveau = 2 WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
        con.commit()
    if points[0] >=14:
        cur.execute("UPDATE Informations SET Niveau = 3 WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
        con.commit()

    cur.close()
    con.close()   

def get_user_by_nom(nom):
    conn = sql.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Informations WHERE nom = ?", (nom,))
    user = cursor.fetchone()
    conn.close()
    return user


def increment_user_actions(pseudonyme):
    """Incrémente le nombre d'actions de l'utilisateur."""
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()

        cur.execute("""
            UPDATE Informations 
            SET nbAction = nbAction + 1 
            WHERE pseudonyme = ?
        """, (pseudonyme,))

        con.commit()
    except Exception as e:
        print(f"Erreur lors de l'incrémentation du nbAction : {e}")
        con.rollback()
    finally:
        cur.close()
        con.close()


def update_user_info(pseudonyme, nom, prenom, age, genre, email, date_naissance, fonction, service, password, photo):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()

        if password:
            cur.execute("""
                UPDATE Informations 
                SET nom = ?, prenom = ?, age = ?, genre = ?, email = ?, dateNaissance = ?, fonction = ?, service = ?, password = ?, photo = ?
                WHERE pseudonyme = ?
            """, (nom, prenom, age, genre, email, date_naissance, fonction, service, password, photo, pseudonyme))
        else:
            cur.execute("""
                UPDATE Informations 
                SET nom = ?, prenom = ?, age = ?, genre = ?, email = ?, dateNaissance = ?, fonction = ?, service = ?, photo = ?
                WHERE pseudonyme = ?
            """, (nom, prenom, age, genre, email, date_naissance, fonction, service, photo, pseudonyme))

        con.commit()
    except sql.Error as e:
        print(f"Erreur lors de la mise à jour du profil : {e}")
        con.rollback()
    finally:
        con.close()

