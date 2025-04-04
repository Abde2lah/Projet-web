import sqlite3 as sql
import bcrypt 
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import datetime
import os
from werkzeug.utils import secure_filename 

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def insert_user(nom, prenom, age, genre, email, dateNaissance, type_user, password, photo, fonction, service, pseudonyme):
    try:
        con = sql.connect("donnees.db")
        cur = con.cursor()
        now = datetime.datetime.now()

        if not photo or not hasattr(photo, 'filename') or not allowed_file(photo.filename):
            photo_path = "/static/images/default.png"
        else:
            filename = secure_filename(photo.filename)
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            photo.save(full_path)
            photo_path = f"/static/images/{filename}"

        cur.execute("""
            INSERT INTO Informations 
            (nom, prenom, age, genre, email, dateNaissance, type, password, photo, fonction, service, niveau, pseudonyme, points, nbAction, nbAcces) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, 0)
        """, (nom, prenom, age, genre, email, dateNaissance, type_user, password, photo_path, fonction, service, pseudonyme))

        cur.execute("""
            INSERT INTO Connexion (pseudonyme, email, type, password, heure, confirme) 
            VALUES (?, ?, ?, ?, ?, 0)
        """, (pseudonyme, email, type_user, password, now))

        con.commit()
    except sql.Error as e:
        print(f"Database error: {e}")
        con.rollback()
    finally:
        con.close()

def get_user_by_username(pseudo):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Connexion WHERE pseudonyme = ?", (pseudo,))
    user = cur.fetchone()
    con.close()
    return user

def get_user_by_email(email):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Connexion WHERE email = ?", (email,))
    user = cur.fetchone()
    con.close()
    return user

def getUserInfos(username):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Informations WHERE pseudonyme = ?", (username,))
    user = cur.fetchone()
    con.close()
    return user

def getUserInfosPublic(username):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT nom, prenom, age, fonction, service, photo FROM Informations WHERE pseudonyme = ?", (username,))
    user = cur.fetchone()
    con.close()
    return user

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):
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
    con = sql.connect('donnees.db')
    cur = con.cursor()
    cur.execute("""
        UPDATE Informations SET nom = ?, prenom = ?, age = ?, genre = ?, dateNaissance = ?, photo = ?, email = ?, pseudonyme = ?, niveau = ?, points = ?, nbAction = ?
        WHERE pseudonyme = ?
    """, (nom, prenom, age, genre, dateNaissance, photo, email, pseudonyme, niveau, points, nbAction, username))
    con.commit()
    con.close()

def update_user_info(pseudonyme, nom, prenom, age, genre, email, date_naissance, fonction, service, password, photo):
    con = sql.connect("donnees.db")
    cur = con.cursor()

    photo_to_save = None
    if photo and hasattr(photo, 'filename') and allowed_file(photo.filename):
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(photo_path)
        photo_to_save = '/static/images/' + filename

    if password:
        cur.execute("""
            UPDATE Informations 
            SET nom = ?, prenom = ?, age = ?, genre = ?, email = ?, dateNaissance = ?, fonction = ?, service = ?, password = ?, photo = COALESCE(?, photo)
            WHERE pseudonyme = ?
        """, (nom, prenom, age, genre, email, date_naissance, fonction, service, password, photo_to_save, pseudonyme))
    else:
        cur.execute("""
            UPDATE Informations 
            SET nom = ?, prenom = ?, age = ?, genre = ?, email = ?, dateNaissance = ?, fonction = ?, service = ?, photo = COALESCE(?, photo)
            WHERE pseudonyme = ?
        """, (nom, prenom, age, genre, email, date_naissance, fonction, service, photo_to_save, pseudonyme))

    con.commit()
    con.close()

def confirmation_pseudo(pseudonyme):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    cur.execute("SELECT confirme FROM Connexion WHERE pseudonyme = ?", (pseudonyme,))
    confirme = cur.fetchone()
    con.close()
    return confirme is not None and confirme[0] == 1

def confirmation_email(email):
    con = sql.connect("donnees.db")
    cur= con.cursor()
    cur.execute("SELECT confirme FROM Connexion WHERE email = ?", (email,))
    confirme = cur.fetchone()
    con.close()
    return confirme is not None and confirme[0] == 1

def insert_object(ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom, type_object, dernierReglage, consommationL, consommationW):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("""
        INSERT INTO Objet (ID, TempActuelle, tempcible, mode, connectivite, batterie, service, marque, nom, type, dernierReglage, ConsommationL, ConsommationW)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom, type_object, dernierReglage, consommationL, consommationW))
    con.commit()
    con.close()

def get_user_type(pseudonyme):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT type FROM Informations WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
    result = cur.fetchone()
    con.close()
    return result

def update_user_points(pseudonyme, nbPoints, nbAcces):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("""
        UPDATE Informations SET nbAcces = nbAcces + ?, points = points + ? WHERE pseudonyme = ? OR email = ?
    """, (nbAcces, nbPoints, pseudonyme, pseudonyme))
    con.commit()
    update_user_level(pseudonyme)
    con.close()

def update_user_level(pseudonyme):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT points FROM Informations WHERE pseudonyme = ? OR email = ?", (pseudonyme, pseudonyme))
    points = cur.fetchone()
    if not points:
        return

    level = 0
    if 6 <= points[0] < 10:
        level = 1
    elif 10 <= points[0] < 14:
        level = 2
    elif points[0] >= 14:
        level = 3

    cur.execute("UPDATE Informations SET niveau = ? WHERE pseudonyme = ? OR email = ?", (level, pseudonyme, pseudonyme))
    con.commit()
    con.close()

def increment_user_actions(pseudonyme):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("UPDATE Informations SET nbAction = nbAction + 1 WHERE pseudonyme = ?", (pseudonyme,))
    con.commit()
    con.close()

def get_user_by_nom(nom):
    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Informations WHERE nom = ?", (nom,))
    user = cur.fetchone()
    con.close()
    return user