from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
import sqlite3 as sql
import bcrypt
from config import Config
from models import *
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static')
app.config.from_object(Config)
app.secret_key = 'your_secret_key'
mail = Mail(app)

# Vérifie si l'extension est autorisée
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        pseudo = request.form.get('pseudo', '') 
        email = request.form.get('email', '') 
        password = request.form['password'].encode('utf-8')
        user_type = request.form['type']

        user = get_user_by_username(pseudo) if pseudo else get_user_by_email(email)
        username = pseudo if pseudo else email

        if user and bcrypt.checkpw(password, user[3]):
            if confirmation_pseudo(pseudo) or confirmation_email(email):
                session['username'] = user[0]
                update_user_points(username, 0.5, 1)
                return redirect(url_for('accueil'))
            else:
                flash('Veuillez confirmer votre email')
        else:
            flash("Mot de passe ou identifiant incorrect")
    return render_template('index.html')

@app.route('/accueil')
def accueil():
    connecte = 'username' in session
    return render_template('accueil.html', connecte=connecte)

@app.route('/accueilPublic')
def accueilPublic():
    return render_template('accueilPublic.html')

@app.route('/gestion_ressources')
def gestion_ressources():
    if 'username' not in session:
        flash('Veuillez vous connecter pour accéder à cette page')
        return redirect(url_for('connexion'))

    con = sql.connect("donnees.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM Salle")
    salles = cur.fetchall()
    cur.execute("SELECT * FROM Objet")
    objets = cur.fetchall()
    con.close()
    return render_template('gestion_ressources.html', salles=salles, objets=objets)

@app.route('/profile')
def profile():
    if 'username' in session:
        user_info = getUserInfos(session['username'])
        return render_template('profil.html', user=user_info) if user_info else ("Utilisateur non trouvé", 404)
    return redirect(url_for('connexion'))

@app.route('/modifier_profil', methods=['GET', 'POST'])
def modifier_profil():
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_info = getUserInfos(pseudonyme)

    if request.method == 'POST':
        nom = request.form.get('nom', user_info[0])
        prenom = request.form.get('prenom', user_info[1])
        age = request.form.get('age', user_info[2])
        genre = request.form.get('genre', user_info[3])
        email = request.form.get('email', user_info[4])
        date_naissance = request.form.get('dateNaissance', user_info[5])
        fonction = request.form.get('fonction', user_info[9])
        service = request.form.get('service', user_info[10])
        nouveau_mdp = request.form.get('password', '')
        photo = request.files.get('photo')

        hashed_password = bcrypt.hashpw(nouveau_mdp.encode('utf-8'), bcrypt.gensalt()) if nouveau_mdp else None

        update_user_info(pseudonyme, nom, prenom, age, genre, email, date_naissance, fonction, service, hashed_password, photo)
        flash("Profil mis à jour avec succès !")
        return redirect(url_for('profile'))

    return render_template('modifier_profil.html', user=user_info, photo_url=user_info[8])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('connexion'))

@app.route('/creation.html', methods=['GET', 'POST'])
def creer_profil():
    if request.method == 'POST':
        data = request.form
        photo = request.files.get('photo')
        hashed_password = bcrypt.hashpw(data['mot_de_passe'].encode('utf-8'), bcrypt.gensalt())
        insert_user(data['nom'], data['prenom'], data['age'], data['genre'], data['email'], data['dateNaissance'],
                    data['type'], hashed_password, photo, data['fonction'], data['service'], data['pseudonyme'])
        envoyer_email_confirmation(data['email'], data['pseudonyme'])
        return redirect(url_for('connexion'))
    return render_template('creation.html')

@app.route('/objet/<IDobjet>')
def objet(IDobjet):
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Objet WHERE ID = ?", (IDobjet,))
    objet = cursor.fetchone()
    conn.close()
    return render_template("objet.html", objet=objet) if objet else ("Objet non trouvé", 404)

@app.route('/profil/<pseudonyme>')
def profil(pseudonyme):
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Informations WHERE pseudonyme = ?", (pseudonyme,))
    user = cursor.fetchone()
    conn.close()
    return render_template("profil.html", user=user) if user else ("Utilisateur non trouvé", 404)

@app.route('/profilPublic/<string:pseudonyme>')
def profilPublic(pseudonyme):
    user_profile = getUserInfosPublic(pseudonyme)
    return render_template('profilPublic.html', profile=user_profile) if user_profile else "Profil non trouvé"

@app.route('/confirmer/<token>')
def confirmer_compte(token):
    email = verifier_token_confirmation(token)
    if email:
        try:
            con = sql.connect("donnees.db")
            cur = con.cursor()
            cur.execute("UPDATE Connexion SET confirme = 1 WHERE email = ?", (email,))
            con.commit()
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la base de données : {e}")
        finally:
            con.close()
        return redirect(url_for('connexion'))
    return redirect(url_for('creer_profil'))

@app.route('/ajout-objet.html', methods=['GET', 'POST'])
def creer_objet():
    if "username" not in session:
        flash("Veuillez vous connecter.")
        return redirect(url_for("connexion"))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)
    if user_type[0] < 2:
        flash('Accès non autorisé')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        data = request.form
        insert_object(data['ID'], data['tempActuelle'], data['tempCible'], data['mode'], data['connectivite'],
                      data['batterie'], data['service'], data['marque'], data['nom'], data['type'],
                      data['dernierReglage'], data['ConsommationL'], data['ConsommationW'])

        update_user_points(pseudonyme, 2, 0)
        increment_user_actions(pseudonyme)

        flash("Objet ajouté avec succès !")
        return redirect(url_for('gestion_ressources'))

    return render_template('ajout-objet.html')

@app.route("/utilisateurs")
def liste_utilisateurs():
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nom, prenom, age, genre, email, dateNaissance, type, photo, fonction, service, niveau, pseudonyme, points, nbAction, nbAcces FROM Informations")
    users = cursor.fetchall()
    conn.close()
    return render_template("utilisateurs.html", users=users)

@app.route('/ajouter_salle', methods=['GET', 'POST'])
def ajouter_salle():
    if 'username' not in session:
        flash("Veuillez vous connecter.")
        return redirect(url_for('connexion'))

    conn = sql.connect("donnees.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        numero = request.form['NumeroSalle']
        etage = request.form['Etage']
        service = request.form['Service']
        objet_id = request.form['ObjetID']
        pseudonyme = request.form['pseudonyme']

        cursor.execute("""
            INSERT INTO Salle (NumeroSalle, Etage, Service, ObjetID, pseudonyme)
            VALUES (?, ?, ?, ?, ?)
        """, (numero, etage, service, objet_id, pseudonyme))
        conn.commit()
        conn.close()
        flash("Salle ajoutée avec succès.")
        return redirect(url_for('gestion_ressources'))

    cursor.execute("SELECT pseudonyme FROM Informations")
    utilisateurs = cursor.fetchall()
    cursor.execute("SELECT ID, nom FROM Objet")
    objets = cursor.fetchall()
    conn.close()
    return render_template('ajouter_salle.html', utilisateurs=utilisateurs, objets=objets)

@app.route('/supprimer_salle/<int:id>', methods=['POST'])
def supprimer_salle(id):
    if 'username' not in session:
        flash("Connexion requise")
        return redirect(url_for('connexion'))

    con = sql.connect("donnees.db")
    cur = con.cursor()
    try:
        cur.execute("DELETE FROM Salle WHERE ID = ?", (id,))
        con.commit()
        flash("Salle supprimée avec succès.")
    except Exception as e:
        flash(f"Erreur : {e}")
    finally:
        con.close()

    return redirect(url_for('gestion_ressources'))


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')