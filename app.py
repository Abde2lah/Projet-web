from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_mail import Mail, Message
import sqlite3 as sql
import bcrypt
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
        flash("Veuillez vous connecter.")
        return redirect(url_for('connexion'))
    
    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM Salle")
    salles = cur.fetchall()
    cur.execute("SELECT * FROM Objet")
    objets = cur.fetchall()
    conn.close()

    return render_template('gestion_ressources.html', salles=salles, objets=objets)

@app.route('/ajouter_salle', methods=['GET', 'POST'])
def ajouter_salle():
    if 'username' not in session:
        flash("Veuillez vous connecter.")
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)

    if not user_type or int(user_type[0]) < 2:
        flash("Accès réservé aux administrateurs.")
        return redirect(url_for('gestion_ressources'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            numero = request.form['NumeroSalle']
            etage = request.form['Etage']
            service = request.form['Service']
            objet_ids = request.form.getlist('ObjetID')
            objet_id_str = ','.join(objet_ids) if objet_ids else None
            pseudonyme_form = request.form['pseudonyme']

            cur.execute("""
                INSERT INTO Salle (NumeroSalle, Etage, Service, ObjetID, pseudonyme)
                VALUES (?, ?, ?, ?, ?)
            """, (numero, etage, service, objet_id_str, pseudonyme_form))
            conn.commit()
            update_user_points(pseudonyme, 0.25, 0)
            increment_user_actions(pseudonyme)
            flash("Salle ajoutée avec succès.")
        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de l'ajout : {e}")
        finally:
            conn.close()

        return redirect(url_for('gestion_ressources'))

    cur.execute("SELECT pseudonyme FROM Informations")
    utilisateurs = cur.fetchall()
    cur.execute("SELECT ID, nom FROM Objet")
    objets = cur.fetchall()
    conn.close()
    return render_template('ajouter_salle.html', utilisateurs=utilisateurs, objets=objets)

@app.route('/modifier_salle/<int:NumeroSalle>', methods=['GET', 'POST'])
def modifier_salle(NumeroSalle):
    if 'username' not in session:
        flash("Connexion requise.")
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)

    if not user_type or int(user_type[0]) < 2:
        flash("Modification réservée aux administrateurs.")
        return redirect(url_for('gestion_ressources'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            etage = request.form['Etage']
            service = request.form['Service']
            objet_ids = request.form.getlist('ObjetID')
            objet_id_str = ','.join(objet_ids) if objet_ids else None
            pseudonyme_form = request.form['pseudonyme']

            cur.execute("""
                UPDATE Salle
                SET Etage = ?, Service = ?, ID = ?, pseudonyme = ?
                WHERE NumeroSalle = ?
            """, (etage, service, objet_id_str, pseudonyme_form, NumeroSalle))
            conn.commit()
            update_user_points(pseudonyme, 0.25, 0)
            increment_user_actions(pseudonyme)
            flash("Salle modifiée avec succès.")
        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de la modification : {e}")
        finally:
            conn.close()

        return redirect(url_for('gestion_ressources'))

    cur.execute("SELECT * FROM Salle WHERE NumeroSalle = ?", (NumeroSalle,))
    salle = cur.fetchone()

    cur.execute("SELECT ID, nom, marque, type FROM Objet")
    objets = cur.fetchall()

    cur.execute("SELECT pseudonyme FROM Connexion")
    utilisateurs = cur.fetchall()

    conn.close()
    return render_template('modifier_salle.html', salle=salle, objets=objets, utilisateurs=utilisateurs)

@app.route('/supprimer_salle/<int:NumeroSalle>', methods=['POST'])
def supprimer_salle(NumeroSalle):
    if 'username' not in session:
        flash("Connexion requise")
        return redirect(url_for('connexion'))
    
    pseudonyme = session['username']
    user_type = get_user_type(pseudonyme)  # ✅ ici

    if not user_type or int(user_type[0]) < 2:
        flash("Accès réservé aux administrateurs.")
        return redirect(url_for('gestion_ressources'))

    conn = sql.connect("donnees.db")
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM Salle WHERE NumeroSalle = ?", (NumeroSalle,))
        conn.commit()
        update_user_points(pseudonyme, 0.25, 0)
        increment_user_actions(pseudonyme)
        # Supprimer les références à cette salle dans la table Objet
        flash("Salle supprimée avec succès.")
    except Exception as e:
        flash(f"Erreur : {e}")
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
        sql_query += " AND (nom LIKE ? OR service LIKE ?)"
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
def afficher_rapport():
    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    cur.execute("SELECT SUM(ConsommationL), SUM(ConsommationW) FROM Objet")
    conso_l, conso_w = cur.fetchone()

    cur.execute("SELECT AVG(nbAcces) FROM Informations")
    taux_connexion = cur.fetchone()[0]

    cur.execute("SELECT service, COUNT(*) as count FROM Informations GROUP BY service ORDER BY count DESC LIMIT 5")
    services = cur.fetchall()

    conn.close()

    return render_template('rapport.html',
                        conso_l=conso_l or 0,
                        conso_w=conso_w or 0,
                        taux_connexion=taux_connexion or 0,
                        services=services)


@app.route('/rapport/pdf')
def generer_pdf():
    conn = sql.connect("donnees.db")
    cur = conn.cursor()

    # Statistiques de consommation
    cur.execute("SELECT SUM(ConsommationL), SUM(ConsommationW) FROM Objet")
    conso_l, conso_w = cur.fetchone()

    # Taux de connexion
    cur.execute("SELECT AVG(nbAcces) FROM Informations")
    taux_connexion = cur.fetchone()[0]

    # Services les plus utilisés
    cur.execute("SELECT service, COUNT(*) FROM Informations GROUP BY service ORDER BY COUNT(*) DESC LIMIT 5")
    services = cur.fetchall()

    # Utilisateurs les plus connectés
    cur.execute("SELECT nom, prenom, nbAcces FROM Informations ORDER BY nbAcces DESC LIMIT 5")
    top_connexions = cur.fetchall()

    # Utilisateurs avec le plus de points
    cur.execute("SELECT nom, prenom, points FROM Informations ORDER BY points DESC LIMIT 5")
    top_points = cur.fetchall()

    conn.close()

    # Création du PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(40, 70, 100)
    pdf.cell(0, 10, " Rapport d'utilisation de la plateforme", ln=True, align='C')

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Date de génération : {datetime.date.today()}", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(0, 10, " Consommation énergétique", ln=True, fill=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Total en litres : {conso_l or 0:.2f} L", ln=True)
    pdf.cell(0, 10, f"Total en watts : {conso_w or 0:.2f} W", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(0, 10, " Taux de connexion moyen", ln=True, fill=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"{taux_connexion or 0:.2f} connexions par utilisateur", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(0, 10, " Services les plus utilisés", ln=True, fill=True)
    pdf.set_font("Arial", "", 12)
    for service, count in services:
        pdf.cell(0, 10, f"- {service} : {count} utilisateur(s)", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(0, 10, " Utilisateurs les plus connectés", ln=True, fill=True)
    pdf.set_font("Arial", "", 12)
    for nom, prenom, acces in top_connexions:
        pdf.cell(0, 10, f"{prenom} {nom} : {acces} connexions", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(220, 235, 255)
    pdf.cell(0, 10, "Utilisateurs avec le plus de points", ln=True, fill=True)
    pdf.set_font("Arial", "", 12)
    for nom, prenom, points in top_points:
        pdf.cell(0, 10, f"{prenom} {nom} : {points} points", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Généré automatiquement via le tableau de bord - Projet CYTECH", ln=True, align='C')

    pdf.output("rapport_utilisation.pdf", "F")
    return send_file("rapport_utilisation.pdf", as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')