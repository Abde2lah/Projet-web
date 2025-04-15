from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_mail import Mail, Message
import sqlite3 as sql
import bcrypt
import matplotlib
matplotlib.use('Agg')  # backend pour serveur sans interface graphique
import matplotlib.pyplot as plt

import io 
from config import Config
from models import *
import os
from werkzeug.utils import secure_filename
from fpdf import FPDF
import datetime

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static')
app.config.from_object(Config)
app.secret_key = 'your_secret_key'
mail = Mail(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        pseudo = request.form.get('pseudo', '') 
        email = request.form.get('email', '') 
        password = request.form['password'].encode('utf-8')

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
        return redirect(url_for('connexion'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Cette requête récupère chaque salle avec ses objets associés (concaténés)
    cur.execute("""
        SELECT s.NumeroSalle, s.Etage, s.Service, s.pseudonyme,
        GROUP_CONCAT(o.nom, ', ') as objets
        FROM Salle s
        LEFT JOIN SalleObjet so ON s.NumeroSalle = so.SalleID
        LEFT JOIN Objet o ON so.ObjetID = o.ID
        GROUP BY s.NumeroSalle
    """)
    salles = cur.fetchall()

    cur.execute("SELECT * FROM Objet")
    objets = cur.fetchall()

    conn.close()

    return render_template("gestion_ressources.html", salles=salles, objets=objets)



@app.route('/ajouter_salle', methods=['GET', 'POST'])
def ajouter_salle():
    if 'username' not in session:
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        numero_salle = request.form['NumeroSalle']
        etage = request.form['Etage']
        service = request.form['Service']
        pseudonyme = request.form['pseudonyme']
        objet_ids = request.form.getlist('ObjetID[]')  # ✅ Correct name

        print("Objets sélectionnés :", objet_ids, type(objet_ids))  # 🧪 Debug temporaire

        conn = sql.connect("donnees.db")
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO Salle (NumeroSalle, Etage, Service, pseudonyme)
                VALUES (?, ?, ?, ?)
            """, (numero_salle, etage, service, pseudonyme))

            for objet_id in objet_ids:
                cur.execute("INSERT INTO SalleObjet (SalleID, ObjetID) VALUES (?, ?)", (numero_salle, objet_id))

            conn.commit()
            flash("Salle ajoutée avec succès.")
            return redirect(url_for('gestion_ressources'))

        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de l'ajout : {e}")
        finally:
            conn.close()

    # En GET
    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT ID, nom FROM Objet")
    objets = cur.fetchall()
    cur.execute("SELECT pseudonyme FROM Connexion")
    utilisateurs = cur.fetchall()
    conn.close()

    return render_template('ajouter_salle.html', objets=objets, utilisateurs=utilisateurs)


    return render_template('ajouter_salle.html', objets=objets, utilisateurs=utilisateurs)
@app.route('/modifier_salle/<int:NumeroSalle>', methods=['GET', 'POST'])
def modifier_salle(NumeroSalle):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    if request.method == 'POST':
        etage = request.form['Etage']
        service = request.form['Service']
        pseudonyme = request.form['pseudonyme']
        objet_ids = request.form.getlist('ObjetID[]')

        try:
            # Mise à jour de la salle
            cur.execute("""
                UPDATE Salle
                SET Etage = ?, Service = ?, pseudonyme = ?
                WHERE NumeroSalle = ?
            """, (etage, service, pseudonyme, NumeroSalle))

            # Supprimer les anciennes associations d’objets
            cur.execute("DELETE FROM SalleObjet WHERE SalleID = ?", (NumeroSalle,))

            # Ajouter les nouvelles associations
            for objet_id in objet_ids:
                cur.execute("INSERT INTO SalleObjet (SalleID, ObjetID) VALUES (?, ?)", (NumeroSalle, objet_id))

            conn.commit()
            flash("Salle modifiée avec succès.")
            return redirect(url_for('gestion_ressources'))

        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de la modification : {e}")
        finally:
            conn.close()

    # En GET : afficher les infos de la salle à modifier
    cur.execute("""
        SELECT s.NumeroSalle, s.Etage, s.Service, s.pseudonyme,
            GROUP_CONCAT(so.ObjetID) as objets
        FROM Salle s
        LEFT JOIN SalleObjet so ON s.NumeroSalle = so.SalleID
        WHERE s.NumeroSalle = ?
        GROUP BY s.NumeroSalle
    """, (NumeroSalle,))
    salle_row = cur.fetchone()

    if salle_row:
        salle = (salle_row[0], salle_row[1], salle_row[2], salle_row[4], salle_row[3])  # Reorder for template: id, étage, service, objets, user
    else:
        flash("Salle introuvable.")
        return redirect(url_for('gestion_ressources'))

    # Récupérer objets et utilisateurs
    cur.execute("SELECT ID, nom FROM Objet")
    objets = cur.fetchall()
    cur.execute("SELECT pseudonyme FROM Connexion")
    utilisateurs = cur.fetchall()

    conn.close()

    return render_template('modifier_salle.html', salle=salle, objets=objets, utilisateurs=utilisateurs)


@app.route('/supprimer_salle/<int:NumeroSalle>', methods=['POST'])
def supprimer_salle(NumeroSalle):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    try:
        # Supprimer les associations d'objets
        cur.execute("DELETE FROM SalleObjet WHERE SalleID = ?", (NumeroSalle,))

        # Supprimer la salle
        cur.execute("DELETE FROM Salle WHERE NumeroSalle = ?", (NumeroSalle,))

        conn.commit()
        flash("Salle supprimée avec succès.")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur lors de la suppression : {e}")
    finally:
        conn.close()

    return redirect(url_for('gestion_ressources'))



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
        update_user_points(pseudonyme, 0.25, 0)
        increment_user_actions(pseudonyme)
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

        # Vérification de tous les champs requis
        champs_obligatoires = ['nom', 'prenom', 'age', 'genre', 'email', 'dateNaissance',
                            'type', 'mot_de_passe', 'fonction', 'service', 'pseudonyme',
                            'niveau', 'points', 'nbAction']

        for champ in champs_obligatoires:
            if not data.get(champ):
                flash(f"Le champ '{champ}' est obligatoire.")
                return redirect(url_for('creer_profil'))

        # Hash du mot de passe
        hashed_password = bcrypt.hashpw(data['mot_de_passe'].encode('utf-8'), bcrypt.gensalt())

        try:
            insert_user(
                nom=data['nom'],
                prenom=data['prenom'],
                age=int(data['age']),
                genre=data['genre'],
                email=data['email'],
                dateNaissance=data['dateNaissance'],
                type_user=int(data['type']),
                password=hashed_password,
                photo=photo,
                fonction=data['fonction'],
                service=data['service'],
                pseudonyme=data['pseudonyme']
            )

            # Mise à jour des autres champs
            conn = sql.connect("donnees.db")
            cur = conn.cursor()
            cur.execute("""
                UPDATE Informations SET niveau = ?, points = ?, nbAction = ?
                WHERE pseudonyme = ?
            """, (
                int(data['niveau']),
                float(data['points']),
                int(data['nbAction']),
                data['pseudonyme']
            ))
            conn.commit()
            conn.close()

            envoyer_email_confirmation(data['email'], data['pseudonyme'])
            flash("Compte créé avec succès ! Veuillez confirmer votre e-mail.")
            return redirect(url_for('connexion'))

        except Exception as e:
            flash(f"Erreur lors de la création du compte : {e}")
            return redirect(url_for('creer_profil'))

    return render_template('creation.html')


@app.route('/objet/<IDobjet>')
def objet(IDobjet):
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Objet WHERE ID = ?", (IDobjet,))
    objet = cursor.fetchone()
    conn.close()
    return render_template("objet.html", objet=objet) if objet else ("Objet non trouvé", 404)

@app.route('/objet/<IDobjet>/reload', methods=['POST'])
def objet_reload(IDobjet):
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Objet WHERE ID = ?", (IDobjet,))
    objet = cursor.fetchone()
    temp_target = objet[2]

    cursor.execute("""UPDATE Objet
                    SET batterie=100, TempActuelle=? WHERE ID=?""", (temp_target, IDobjet,))
    conn.commit()

    cursor.execute("SELECT * FROM Objet WHERE ID = ?", (IDobjet,))
    objet = cursor.fetchone()
    conn.close()
    return render_template("visualiser_objet.html", objet=objet) if objet else("Objet non trouvé", 404)

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

        update_user_points(pseudonyme, 0.25, 0)
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

@app.route('/modifier_objet/<string:id>', methods=['GET', 'POST'])
def modifier_objet(id):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)

    if not user_type or int(user_type[0]) < 2:
        flash("Accès réservé aux administrateurs.")
        return redirect(url_for('gestion_ressources'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Objet WHERE ID = ?", (id,))
    objet = cur.fetchone()

    if not objet:
        conn.close()
        flash("Objet non trouvé.")
        return redirect(url_for('gestion_ressources'))

    if request.method == 'POST':
        data = request.form
        champs_requis = ['TempActuelle', 'tempcible', 'mode', 'connectivite', 'batterie',
                        'service', 'marque', 'nom', 'type', 'dernierReglage']

        # Vérification des champs manquants
        champs_vides = [champ for champ in champs_requis if not data.get(champ)]
        if champs_vides:
            flash(f"Les champs suivants sont obligatoires : {', '.join(champs_vides)}")
            conn.close()
            return render_template('modifier_objet.html', objet=data)

        try:
            cur.execute("""
                UPDATE Objet
                SET TempActuelle=?, tempcible=?, mode=?, connectivite=?, batterie=?, 
                    service=?, marque=?, nom=?, type=?, dernierReglage=?, 
                    ConsommationL=?, ConsommationW=?
                WHERE ID=?
            """, (
                data['TempActuelle'], data['tempcible'], data['mode'], data['connectivite'],
                data['batterie'], data['service'], data['marque'], data['nom'], data['type'],
                data['dernierReglage'], data.get('ConsommationL', 0), data.get('ConsommationW', 0), id
            ))
            conn.commit()
            update_user_points(pseudonyme, 0.25, 0)
            increment_user_actions(pseudonyme)
            flash("Objet modifié avec succès.")
            return redirect(url_for('gestion_ressources'))

        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de la modification : {e}")

        finally:
            conn.close()

    else:
        conn.close()
        return render_template('modifier_objet.html', objet=objet)



@app.route('/supprimer_objet/<string:id>', methods=['POST'])
def supprimer_objet(id):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)

    if not user_type or int(user_type[0]) < 2:
        flash("Suppression réservée aux administrateurs.")
        return redirect(url_for('gestion_ressources'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    try:
        # Supprimer l'objet
        cur.execute("DELETE FROM Objet WHERE ID = ?", (id,))
        conn.commit()
        update_user_points(pseudonyme, 0.25, 0)
        increment_user_actions(pseudonyme)
        flash("Objet supprimé et dissocié des salles.")
    except Exception as e:
        conn.rollback()
        flash(f"Erreur lors de la suppression : {e}")
    finally:
        conn.close()

    return redirect(url_for('gestion_ressources'))



@app.route('/utilisateurs_public')
def liste_utilisateurs_public():
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom, prenom, age, genre, email, dateNaissance, type, photo, fonction, service, niveau, pseudonyme, points 
        FROM Informations
    """)
    users = cursor.fetchall()
    conn.close()

    return render_template('utilisateurs_public.html', users=users)


@app.route('/search', methods=['GET'])
def search(): #recherche de l'accueil avec filtres

    search_query = request.args.get('search-input')
    service_filter = request.args.get('service-filter')  #filtre de service
    function_filter = request.args.get('fonction-filter') # filtre de fonction

    con = sql.connect("donnees.db")
    cur = con.cursor()

    sql_query = "SELECT nom, prenom, fonction, service, pseudonyme FROM Informations WHERE 1=1"

    params = []

    if search_query:
        sql_query += " AND (nom LIKE ? OR prenom LIKE ?)"
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])
    if service_filter:
        sql_query += " AND service = ?"
        params.append(service_filter)

    if function_filter:
        sql_query += " AND fonction = ?"
        params.append(function_filter)

    cur.execute(sql_query, params)
    results = cur.fetchall()
    con.close()

    return render_template('resultats.html', results=results, query=search_query)


# ROUTE DE RECHERCHE D'OBJETS
@app.route('/search_objets', methods=['GET'])
def search_objets():
    search_query = request.args.get('search-input')
    service_filter = request.args.get('service-filter')
    type_filter = request.args.get('type-filter')
    marque_filter = request.args.get('marque-filter')

    con = sql.connect("donnees.db")
    cur = con.cursor()

    sql_query = "SELECT * FROM Objet WHERE 1=1"
    params = []

    if search_query:
        sql_query += " AND (ID LIKE ? OR nom LIKE ?)"
        params.extend(['%' + search_query + '%'] * 2)
    if service_filter:
        sql_query += " AND service = ?"
        params.append(service_filter)
    if type_filter:
        sql_query += " AND type = ?"
        params.append(type_filter)
    if marque_filter:
        sql_query += " AND marque = ?"
        params.append(marque_filter)

    cur.execute(sql_query, params)
    results = cur.fetchall()
    con.close()

    # Mise à jour des points uniquement si résultat non vide et utilisateur connecté
    if 'username' in session and results:
        pseudonyme = session['username']
        update_user_points(pseudonyme, 1, 1)

    return render_template('resultats-objets.html', results=results, query=search_query)

@app.route('/supprimer_utilisateur/<string:pseudonyme>', methods=['POST'])
def supprimer_utilisateur(pseudonyme):
    if 'username' not in session:
        flash("Connexion requise.")
        return redirect(url_for('connexion'))

    user_type = get_user_type(session['username'])
    if not user_type or int(user_type[0]) < 3:
        flash("Seuls les administrateurs peuvent supprimer des utilisateurs.")
        return redirect(url_for('liste_utilisateurs'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM Informations WHERE pseudonyme = ?", (pseudonyme,))
        cur.execute("DELETE FROM Connexion WHERE pseudonyme = ?", (pseudonyme,))
        conn.commit()
        flash("Utilisateur supprimé avec succès.")
    except Exception as e:
        flash(f"Erreur lors de la suppression : {e}")
    finally:
        conn.close()

    return redirect(url_for('liste_utilisateurs'))


@app.context_processor
def inject_user_type():
    def get_user_type_safe(pseudo):
        result = get_user_type(pseudo)
        return int(result[0]) if result else 0
    return dict(get_user_type=get_user_type_safe)


@app.route('/rapport')
def rapport():
    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Données brutes
    cur.execute("SELECT SUM(ConsommationL), SUM(ConsommationW) FROM Objet")
    conso_l, conso_w = cur.fetchone()

    cur.execute("SELECT AVG(nbAcces) FROM Informations")
    taux_connexion = cur.fetchone()[0]

    cur.execute("SELECT service, COUNT(*) FROM Informations GROUP BY service ORDER BY COUNT(*) DESC LIMIT 5")
    services = cur.fetchall()

    cur.execute("SELECT nom, prenom, nbAcces FROM Informations")
    connexions = cur.fetchall()

    cur.execute("SELECT nom, prenom, nbAction FROM Informations")
    actions = cur.fetchall()

    conn.close()

    # 🎨 Diagramme camembert des connexions
    fig1, ax1 = plt.subplots()
    labels1 = [f"{prenom} {nom}" for nom, prenom, _ in connexions]
    sizes1 = [nb for _, _, nb in connexions]
    ax1.pie(sizes1, labels=labels1, autopct='%1.1f%%', startangle=140)
    ax1.set_title("Répartition des connexions par utilisateur")
    img_connexions = fig_to_base64(fig1)

    # 📊 Barres objets par service
    fig2, ax2 = plt.subplots()
    services_labels = [s[0] for s in services]
    service_counts = [s[1] for s in services]
    ax2.bar(services_labels, service_counts)
    ax2.set_title("Top 5 services les plus utilisés")
    img_services = fig_to_base64(fig2)

    # 📊 Barres des actions par utilisateur
    fig3, ax3 = plt.subplots()
    labels3 = [f"{prenom} {nom}" for nom, prenom, _ in actions]
    actions_counts = [nb for _, _, nb in actions]
    ax3.barh(labels3, actions_counts)
    ax3.set_title("Nombre d’actions par utilisateur")
    img_actions = fig_to_base64(fig3)

    return render_template("rapport.html",
        date=datetime.date.today(),
        conso_l=conso_l,
        conso_w=conso_w,
        taux_connexion=taux_connexion,
        services=services,
        img_connexions=img_connexions,
        img_services=img_services,
        img_actions=img_actions
    )


@app.route('/visualiser_objet/<id>', methods=['GET','POST'])
def visualiser_objet(id):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)


    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Objet WHERE ID = ?", (id,))
    objet = cur.fetchone()

    if not objet:
        conn.close()
        flash("Objet non trouvé.")
        return redirect(url_for('gestion_ressources'))

    if request.method == 'POST':
        data = request.form
        champs_requis = ['TempActuelle', 'tempcible', 'mode', 'connectivite', 'batterie',
                        'service', 'marque', 'nom', 'type', 'dernierReglage']

        # Vérification des champs manquants
        champs_vides = [champ for champ in champs_requis if not data.get(champ)]
        if champs_vides:
            flash(f"Les champs suivants sont obligatoires : {', '.join(champs_vides)}")
            conn.close()
            return render_template('modifier_objet.html', objet=data)

        try:
            cur.execute("""
                UPDATE Objet
                SET TempActuelle=?, tempcible=?, mode=?, connectivite=?, batterie=?, 
                    service=?, marque=?, nom=?, type=?, dernierReglage=?, 
                    ConsommationL=?, ConsommationW=?
                WHERE ID=?
            """, (
                data['TempActuelle'], data['tempcible'], data['mode'], data['connectivite'],
                data['batterie'], data['service'], data['marque'], data['nom'], data['type'],
                data['dernierReglage'], data.get('ConsommationL', 0), data.get('ConsommationW', 0), id
            ))
            conn.commit()
            update_user_points(pseudonyme, 0.25, 0)
            increment_user_actions(pseudonyme)
            flash("Objet modifié avec succès.")
            return redirect(url_for('gestion_ressources'))

        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de la modification : {e}")

        finally:
            conn.close()

    else:
        conn.close()
        return render_template('visualiser_objet.html', objet=objet)
    
@app.route('/visualiser_salle/<int:NumeroSalle>')
def visualiser_salle(NumeroSalle):
    if 'username' not in session:
        flash("Connexion requise.")
        return redirect(url_for('connexion'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Récupère la salle
    cur.execute("""
        SELECT NumeroSalle, Etage, Service, pseudonyme
        FROM Salle
        WHERE NumeroSalle = ?
    """, (NumeroSalle,))
    salle = cur.fetchone()

    if not salle:
        flash("Salle introuvable.")
        conn.close()
        return redirect(url_for('gestion_ressources'))

    # Récupère les objets associés
    cur.execute("""
        SELECT o.nom, o.type, o.service, o.marque
        FROM SalleObjet so
        JOIN Objet o ON so.ObjetID = o.ID
        WHERE so.SalleID = ?
    """, (NumeroSalle,))
    objets = cur.fetchall()

    conn.close()

    return render_template("visualiser_salle.html", salle=salle, objets=objets)



@app.route('/rapport/pdf')
def generer_pdf():
    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Données de base
    cur.execute("SELECT SUM(ConsommationL), SUM(ConsommationW) FROM Objet")
    conso_l, conso_w = cur.fetchone()

    cur.execute("SELECT AVG(nbAcces) FROM Informations")
    taux_connexion = cur.fetchone()[0]

    cur.execute("SELECT service, COUNT(*) FROM Informations GROUP BY service ORDER BY COUNT(*) DESC LIMIT 5")
    services = cur.fetchall()

    cur.execute("SELECT nom, prenom, nbAcces FROM Informations")
    connexions = cur.fetchall()

    cur.execute("SELECT nom, prenom, nbAction FROM Informations")
    actions = cur.fetchall()

    conn.close()

    # 🎨 Graphique 1 – Connexions (camembert)
    fig1, ax1 = plt.subplots()
    labels1 = [f"{prenom} {nom}" for nom, prenom, _ in connexions]
    sizes1 = [nb for _, _, nb in connexions]
    ax1.pie(sizes1, labels=labels1, autopct='%1.1f%%', startangle=140)
    ax1.set_title("Répartition des connexions par utilisateur")
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format='png', bbox_inches='tight')
    buf1.seek(0)
    plt.close(fig1)

    # 📊 Graphique 2 – Services (barres)
    fig2, ax2 = plt.subplots()
    service_labels = [s[0] for s in services]
    service_counts = [s[1] for s in services]
    ax2.bar(service_labels, service_counts)
    ax2.set_title("Top 5 services les plus utilisés")
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png', bbox_inches='tight')
    buf2.seek(0)
    plt.close(fig2)

    # 📊 Graphique 3 – Actions par utilisateur
    fig3, ax3 = plt.subplots()
    action_labels = [f"{prenom} {nom}" for nom, prenom, _ in actions]
    action_counts = [nb for _, _, nb in actions]
    ax3.barh(action_labels, action_counts)
    ax3.set_title("Nombre d’actions par utilisateur")
    buf3 = io.BytesIO()
    fig3.savefig(buf3, format='png', bbox_inches='tight')
    buf3.seek(0)
    plt.close(fig3)

    # 📝 Création PDF
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Rapport d'utilisation de la plateforme", ln=True, align='C')

    pdf.set_font("Arial", "", 12)
    pdf.ln(8)
    pdf.cell(0, 10, f"Date : {datetime.date.today()}", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Consommation énergétique", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"- Eau : {conso_l or 0:.2f} L", ln=True)
    pdf.cell(0, 10, f"- Énergie : {conso_w or 0:.2f} W", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Taux de connexion moyen", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"{taux_connexion or 0:.2f} connexions/utilisateur", ln=True)

    # 📎 Ajout des graphiques
    for buf in [buf1, buf2, buf3]:
        pdf.ln(10)
        img_path = f"/tmp/graph_{datetime.datetime.now().timestamp()}.png"
        with open(img_path, 'wb') as f:
            f.write(buf.read())
        pdf.image(img_path, w=180)
        buf.close()

    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Généré automatiquement par la plateforme - Projet CYTECH", ln=True, align='C')

    filename = "rapport_utilisation.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)


@app.route('/objet/<id>/demande_suppression', methods=['POST'])
def demande_suppression_objet(id):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    message = request.form.get('message', '')
    pseudonyme = session['username']

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Vérifie si une demande est déjà en attente
    cur.execute("SELECT COUNT(*) FROM DemandeSuppression WHERE objet_id=? AND statut='en attente'", (id,))
    if cur.fetchone()[0] > 0:
        flash("❗ Une demande est déjà en cours pour cet objet.")
    else:
        cur.execute("""
            INSERT INTO DemandeSuppression (objet_id, pseudonyme, message)
            VALUES (?, ?, ?)
        """, (id, pseudonyme, message))
        conn.commit()
        flash("✅ Demande de suppression envoyée.")

    conn.close()
    return redirect(url_for('gestion_ressources'))


@app.route('/admin/demandes')
def voir_demandes():
    if not est_admin():
        flash("Accès réservé à l’administrateur.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, o.nom, d.pseudonyme, d.message, d.statut, d.date_creation
        FROM DemandeSuppression d
        JOIN Objet o ON d.objet_id = o.ID
        ORDER BY d.date_creation DESC
    """)
    demandes = cur.fetchall()
    conn.close()

    return render_template("admin_demandes.html", demandes=demandes)




@app.route('/demande_upgrade', methods=['GET', 'POST'])
def demande_upgrade():
    if 'username' not in session:
        flash("Connexion requise.")
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)[0]

    if user_type == 3:
        flash("Tu es déjà administrateur 👑")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Vérifie s’il y a déjà une demande en attente
    cur.execute("SELECT COUNT(*) FROM DemandeUpgrade WHERE pseudonyme=? AND statut='en attente'", (pseudonyme,))
    if cur.fetchone()[0] > 0:
        flash("❗ Une demande est déjà en attente.")
        conn.close()
        return redirect(url_for('accueil'))

    if request.method == 'POST':
        message = request.form.get('message', '')
        niveau_suivant = user_type + 1  # 1 → 2, 2 → 3

        cur.execute("""
            INSERT INTO DemandeUpgrade (pseudonyme, niveau_actuel, niveau_demande, message)
            VALUES (?, ?, ?, ?)
        """, (pseudonyme, user_type, niveau_suivant, message))

        conn.commit()
        flash("✅ Demande de promotion envoyée. En attente de validation.")
        conn.close()
        return redirect(url_for('accueil'))

    conn.close()
    return render_template('demande_upgrade.html', user_type=user_type)

@app.route('/admin/demandes_upgrade')
def voir_demandes_upgrade():
    if not est_admin():
        flash("Accès refusé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM DemandeUpgrade ORDER BY date_creation DESC")
    demandes = cur.fetchall()
    conn.close()

    return redirect(url_for('admin_dashboard'))




@app.route('/demande_creation_salle', methods=['GET', 'POST'])
def demande_creation_salle():
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)[0]

    if user_type >= 3:
        flash("Tu peux créer directement une salle.")
        return redirect(url_for('ajouter_salle'))

    if request.method == 'POST':
        numero_salle = request.form.get('numero_salle')
        etage = request.form.get('etage')
        service = request.form.get('service')
        message = request.form.get('message')

        conn = sql.connect("donnees.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO DemandeCreationSalle (pseudonyme, numero_salle, etage, service, message)
            VALUES (?, ?, ?, ?, ?)
        """, (pseudonyme, numero_salle, etage, service, message))

        conn.commit()
        conn.close()
        flash("✅ Demande de création de salle envoyée à l'administrateur.")
        return redirect(url_for('gestion_ressources'))

    return render_template('demande_creation_salle.html')

@app.route('/admin/demandes_salle')
def demandes_creation_salle():
    if not est_admin():
        flash("Accès réservé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM DemandeCreationSalle ORDER BY date_creation DESC")
    demandes = cur.fetchall()
    conn.close()
    return redirect(url_for('admin_dashboard'))



@app.route('/demande_creation_objet', methods=['GET', 'POST'])
def demande_creation_objet():
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)[0]

    if user_type >= 2:
        flash("Tu as déjà accès à la création directe d’objets.")
        return redirect(url_for('creer_objet'))

    if request.method == 'POST':
        nom = request.form['nom']
        type_objet = request.form['type']
        service = request.form['service']
        message = request.form.get('message', '')

        conn = sql.connect("donnees.db")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO DemandeCreationObjet (pseudonyme, nom, type, service, message)
            VALUES (?, ?, ?, ?, ?)
        """, (pseudonyme, nom, type_objet, service, message))

        conn.commit()
        conn.close()
        flash("✅ Demande envoyée à l’administrateur.")
        return redirect(url_for('gestion_ressources'))

    return render_template('demande_creation_objet.html')

@app.route('/admin/demandes_objet')
def demandes_creation_objet():
    if not est_admin():
        flash("Accès réservé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM DemandeCreationObjet ORDER BY date_creation DESC")
    demandes = cur.fetchall()
    conn.close()
    return render_template("admin_demandes_objet.html", demandes=demandes)



@app.route('/salle/<int:NumeroSalle>/demande_suppression', methods=['POST'])
def demande_suppression_salle(NumeroSalle):
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    message = request.form.get('message', '')

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Vérifie s'il y a déjà une demande
    cur.execute("""
        SELECT COUNT(*) FROM DemandeSuppressionSalle
        WHERE NumeroSalle = ? AND statut = 'en attente'
    """, (NumeroSalle,))
    if cur.fetchone()[0] > 0:
        flash("❗ Une demande pour cette salle est déjà en attente.")
    else:
        cur.execute("""
            INSERT INTO DemandeSuppressionSalle (NumeroSalle, pseudonyme, message)
            VALUES (?, ?, ?)
        """, (NumeroSalle, pseudonyme, message))
        conn.commit()
        flash("✅ Demande de suppression envoyée à l'administrateur.")

    conn.close()
    return redirect(url_for('gestion_ressources'))

@app.route('/admin/demandes_suppression_salle')
def voir_demandes_suppression_salle():
    if not est_admin():
        flash("Accès réservé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, s.NumeroSalle, d.pseudonyme, d.message, d.statut, d.date_creation
        FROM DemandeSuppressionSalle d
        JOIN Salle s ON d.NumeroSalle = s.NumeroSalle
        ORDER BY d.date_creation DESC
    """)
    demandes = cur.fetchall()
    conn.close()
    return redirect(url_for('admin_dashboard'))




@app.route('/admin/dashboard')
def admin_dashboard():
    if not est_admin():
        flash("Accès refusé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    blocs = []

    def ajouter_bloc(query, headers, title, endpoint_type, statut_index):
        cur.execute(query)
        demandes = cur.fetchall()
        blocs.append({
            "title": title,
            "headers": headers,
            "demandes": demandes,
            "type": endpoint_type,
            "statut_index": statut_index
        })

        ajouter_bloc(
        """
        SELECT d.id, o.nom, d.pseudonyme, d.message, d.statut, d.date_creation
        FROM DemandeSuppression d
        JOIN Objet o ON d.objet_id = o.ID
        ORDER BY d.date_creation DESC
        """,
        ["ID", "Objet", "Utilisateur", "Message", "Statut", "Date"],
        "🗃️ Suppression d'objet",
        "demande",
        4
    )


    ajouter_bloc(
        "SELECT id, pseudonyme, message, statut, date_creation FROM DemandeRole",
        ["ID", "Utilisateur", "Message", "Statut", "Date"],
        "👑 Rôles",
        "role",
        3
    )

    ajouter_bloc(
        "SELECT id, pseudonyme, niveau_actuel, niveau_demande, message, statut, date_creation FROM DemandeUpgrade",
        ["ID", "Utilisateur", "De", "Vers", "Message", "Statut", "Date"],
        "📈 Évolutions",
        "upgrade",
        5
    )

    ajouter_bloc(
        "SELECT id, pseudonyme, numero_salle, etage, service, message, statut, date_creation FROM DemandeCreationSalle",
        ["ID", "Utilisateur", "Salle", "Étage", "Service", "Message", "Statut", "Date"],
        "🏗️ Création de salle",
        "demande_salle",
        6
    )

    ajouter_bloc(
        "SELECT d.id, s.NumeroSalle, d.pseudonyme, d.message, d.statut, d.date_creation FROM DemandeSuppressionSalle d JOIN Salle s ON d.NumeroSalle = s.NumeroSalle",
        ["ID", "Salle", "Utilisateur", "Message", "Statut", "Date"],
        "🧯 Suppression de salle",
        "suppression_salle",
        4
    )

    ajouter_bloc(
        "SELECT id, pseudonyme, nom, type, service, message, statut, date_creation FROM DemandeCreationObjet",
        ["ID", "Utilisateur", "Nom", "Type", "Service", "Message", "Statut", "Date"],
        "📦 Création d'objet",
        "objet",
        6
    )

    conn.close()
    return render_template("dashboard.html", blocs=blocs)


@app.route('/admin/valider_<type>/<int:id>')
def valider_type(type, id):
    if not est_admin():
        flash("Accès refusé.")
        return redirect(url_for('accueil'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    try:
        if type == "demande":
            cur.execute("SELECT objet_id FROM DemandeSuppression WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                objet_id = row[0]
                cur.execute("DELETE FROM Objet WHERE ID = ?", (objet_id,))
                cur.execute("UPDATE DemandeSuppression SET statut = 'validée' WHERE id = ?", (id,))
                flash("✅ Objet supprimé et demande validée.")
            else:
                flash("❌ Demande introuvable.")

        elif type == "role":
            cur.execute("SELECT pseudonyme FROM DemandeRole WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                pseudo = row[0]
                cur.execute("UPDATE Connexion SET type = 3 WHERE pseudonyme = ?", (pseudo,))
                cur.execute("UPDATE DemandeRole SET statut = 'validée' WHERE id = ?", (id,))
                flash(f"🎉 {pseudo} est désormais administrateur !")
            else:
                flash("❌ Demande introuvable.")

        elif type == "upgrade":
            cur.execute("SELECT pseudonyme FROM DemandeUpgrade WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                pseudo = row[0]
                # On récupère le niveau actuel depuis Connexion
                cur.execute("SELECT type FROM Informations WHERE pseudonyme = ?", (pseudo,))
                niveau_actuel = cur.fetchone()[0]
                niveau_suivant = niveau_actuel + 1 if niveau_actuel < 3 else 3  # Pas au-delà de 3 car les admins sont max

                cur.execute("UPDATE Informations SET type = ? WHERE pseudonyme = ?", (niveau_suivant, pseudo))
                cur.execute("UPDATE DemandeUpgrade SET statut = 'validée' WHERE id = ?", (id,))
                flash(f"✅ {pseudo} a été promu au niveau {niveau_suivant}.")
            else:
                flash("❌ Demande introuvable.")


        elif type == "demande_salle":
            cur.execute("SELECT numero_salle, etage, service, pseudonyme FROM DemandeCreationSalle WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                numero, etage, service, pseudo = row
                cur.execute("INSERT INTO Salle (NumeroSalle, Etage, Service, pseudonyme) VALUES (?, ?, ?, ?)",
                            (numero, etage, service, pseudo))
                cur.execute("UPDATE DemandeCreationSalle SET statut = 'validée' WHERE id = ?", (id,))
                flash("✅ Salle créée et demande validée.")
            else:
                flash("❌ Demande introuvable.")

        elif type == "suppression_salle":
            cur.execute("SELECT NumeroSalle FROM DemandeSuppressionSalle WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                numero_salle = row[0]
                cur.execute("DELETE FROM SalleObjet WHERE SalleID = ?", (numero_salle,))
                cur.execute("DELETE FROM Salle WHERE NumeroSalle = ?", (numero_salle,))
                cur.execute("UPDATE DemandeSuppressionSalle SET statut = 'validée' WHERE id = ?", (id,))
                flash("✅ Salle supprimée et demande validée.")
            else:
                flash("❌ Demande introuvable.")

        elif type == "objet":
            cur.execute("SELECT nom, type, service, pseudonyme FROM DemandeCreationObjet WHERE id = ?", (id,))
            row = cur.fetchone()
            if row:
                nom, type_objet, service, pseudo = row
                cur.execute("""
                    INSERT INTO Objet (ID, TempActuelle, tempcible, mode, connectivite, batterie,
                    service, marque, nom, type, dernierReglage, ConsommationL, ConsommationW)
                    VALUES (?, 0, 0, 'auto', 'wifi', 100, ?, 'standard', ?, ?, DATE(), 0, 0)
                """, (id, service, nom, type_objet))
                cur.execute("UPDATE DemandeCreationObjet SET statut = 'validée' WHERE id = ?", (id,))
                flash("✅ Objet créé avec succès.")
            else:
                flash("❌ Demande introuvable.")

        else:
            flash("❌ Type de demande inconnu.")

        conn.commit()
    except Exception as e:
        flash(f"❌ Erreur : {str(e)}")
    finally:
        conn.close()

    return redirect(url_for('admin_dashboard'))



@app.route('/admin/refuser_<type>/<int:id>')
def refuser_type(type, id):
    if not est_admin():
        flash("Accès refusé.")
        return redirect(url_for('accueil'))

    table_map = {
        "demande": "DemandeSuppression",
        "role": "DemandeRole",
        "upgrade": "DemandeUpgrade",
        "demande_salle": "DemandeCreationSalle",
        "suppression_salle": "DemandeSuppressionSalle",
        "objet": "DemandeCreationObjet"
    }

    table = table_map.get(type)

    if not table:
        flash("❌ Type de demande inconnu.")
        return redirect(url_for('admin_dashboard'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET statut = 'refusée' WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("🚫 Demande refusée.")
    return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')