
from flask import Flask, render_template, request, redirect, url_for, session, flash, redirect, url_for, flash
from flask_mail import Mail, Message
import sqlite3 as sql
import bcrypt
from config import Config
from models import *
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/images/'  # Dossier où les photos seront stockées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Vérifie si le fichier a une extension autorisée
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key'  # A changer pour la sécurité
mail = Mail(app)

# Route de Connexion
@app.route('/', methods=['POST', 'GET'])
def connexion():  # Connexion au site
    if request.method == 'POST':
        pseudo = request.form.get('pseudo', '') 
        email = request.form.get('email', '') 
        password = request.form['password'].encode('utf-8')  # Encode mdp
        user_type = request.form['type']
        
        if pseudo:
            user = get_user_by_username(pseudo)
            username = pseudo
        else:
            user = get_user_by_email(email)
            username = email

        if user and bcrypt.checkpw(password, user[3]):
            if confirmation_pseudo(pseudo):  # Vérifie si le pseudonyme a été confirmé
                session['username'] = user[0] 
                print(f"Username in session: {session.get('username')}")
                update_user_points(username, 0.5)  # Incrémente les points de 0.5 lors de la connexion

                return redirect(url_for('accueil'))  
            elif confirmation_email(email):  # Vérifie si l'email a été confirmé
                session['username'] = user[0]  # Enregistre la session de l'utilisateur
                print(f"Username in session: {session.get('username')}")
                update_user_points(username, 0.5,1)  # Incrémente les points de 0.5 lors de la connexion et de 1 pour l'acces au site
                return redirect(url_for('accueil'))  
            
            else:
                flash('Veuillez confirmer votre email')
                return render_template('index.html')
        else:
            flash("Mot de passe ou identifiant incorrect")
            return render_template('index.html') 
    else:
        return render_template('index.html')  # Formulaire par défaut pour la connexion


# Route de l'Accueil
@app.route('/accueil')
def accueil():  # Accueil accessible pour tous les utilisateurs
    connecte = 'username' in session  # Vérifie si l'utilisateur est connecté
    return render_template('accueil.html', connecte=connecte)

# Route du Profil
@app.route('/profile')
def profile():  # Redirige vers le profil privé de l'utilisateur
    if 'username' in session:
        user_info = getUserInfos(session['username'])  
        if user_info:
            return render_template('profil.html', user=user_info)  
        else:
            return "Utilisateur non trouvé", 404
    else:
        return redirect(url_for('connexion'))  

# Route de l'accueil Public pour les personnes non connectées
@app.route('/accueilPublic')
def accueilPublic():  # Page d'accueil pour les visiteurs
    return render_template('accueilPublic.html')  



@app.route("/profil/<pseudonyme>")
def profil(pseudonyme):
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Informations WHERE pseudonyme = ?", (pseudonyme,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return render_template("profil.html", user=user)
    else:
        return "Utilisateur non trouvé", 404




# Fonction d'envoi de mail de confirmation
def envoyer_email_confirmation(destinataire, nom_utilisateur):
    try:
        token = generer_token_confirmation(destinataire)
        lien_confirmation = url_for('confirmer_compte', token=token, _external=True) # _external=True pour avoir l'URL complète

        msg = Message('Confirmation de compte', sender='testgroupe3cytech@gmail.com', recipients=[destinataire])
        msg.html = render_template('email_confirmation.html', nom_utilisateur=nom_utilisateur, lien_confirmation=lien_confirmation) # Utilise un template HTML
        mail.send(msg)
        print("Email de confirmation envoyé !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")


# Route de Création de Profil
@app.route('/creation.html', methods=['GET', 'POST'])
def creer_profil(): #créer un profil
    if request.method == 'POST':
        # Récupération des informations du formulaire
        nom = request.form['nom']
        prenom = request.form['prenom']
        age = request.form['age']
        genre = request.form['genre']
        dateNaissance = request.form['dateNaissance']
        photo = request.form['photo']
        email = request.form['email']
        fonction = request.form['fonction']
        pseudonyme = request.form['pseudonyme']
        mot_de_passe = request.form['mot_de_passe']
        type_user = request.form['type']
        #points = request.form['points'] #à supprimer
        #nbAction = request.form['nbAction'] #à supprimer
        service = request.form['service']

        # Hachage du mot de passe avant insertion
        hashed_password = bcrypt.hashpw(mot_de_passe.encode('utf-8'), bcrypt.gensalt())

        # Insertion dans la base de données
        insert_user(nom, prenom, age, genre, email,	dateNaissance, type_user, hashed_password, photo, fonction, service, pseudonyme)
        envoyer_email_confirmation(email, pseudonyme)
        return redirect(url_for('connexion'))  # Redirection vers le profil

    return render_template('creation.html')  # Affichage du formulaire de création de profil


@app.route('/modifier_profil', methods=['GET', 'POST'])
def modifier_profil():
    if 'username' not in session:
        return redirect(url_for('connexion'))

    pseudonyme = session['username']
    user_info = getUserInfos(pseudonyme)  # Récupération des infos actuelles

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

        # Gestion de la photo (conserve l'ancienne si pas de nouvelle)
        photo_filename = user_info[8]  
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(f"{pseudonyme}_{photo.filename}")
                photo_filename = f"static/images/{filename}"  

        # Hash du mot de passe si modifié
        hashed_password = bcrypt.hashpw(nouveau_mdp.encode('utf-8'), bcrypt.gensalt()) if nouveau_mdp else None

        # Mise à jour en base de données
        update_user_info(pseudonyme, nom, prenom, age, genre, email, date_naissance, fonction, service, hashed_password, photo_filename)

        flash("Profil mis à jour avec succès !")
        return redirect(url_for('profile'))

    return render_template('modifier_profil.html', user=user_info)


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        flash('Aucun fichier sélectionné')
        return redirect(request.url)

    file = request.files['photo']

    if file.filename == '':
        flash('Nom de fichier vide')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Sécurise le nom du fichier
        filepath = os.path.join(UPLOAD_FOLDER, filename)  # Chemin complet
        file.save(filepath)  # Sauvegarde du fichier

        flash('Photo de profil mise à jour !')
        return redirect(url_for('profil', pseudonyme=session['username']))  # Redirige vers le profil

    flash('Type de fichier non autorisé')
    return redirect(request.url)



# Route de Déconnexion
@app.route('/logout')
def logout():
    session.pop('username', None)  # Supprime la session de l'utilisateur
    return redirect(url_for('connexion'))  # Redirige vers la page de connexion


# Route d'Édition du Profil
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' in session:
        user_info = getUserInfos(session['username'])  # Get user info

        if request.method == 'POST':
            # Récupération des nouvelles informations du formulaire
            nom = request.form['nom']
            prenom = request.form['prenom']
            age = request.form['age']
            genre = request.form['genre']
            dateNaissance = request.form['dateNaissance']
            photo = request.form['photo']
            email = request.form['email']
            pseudonyme = request.form['pseudonyme']
            #niveau = request.form['niveau']
            #points = request.form['points']
            #nbAction = request.form['nbAction']

            # Mise à jour des informations de l'utilisateur dans la base de données
            update_user(session['username'], nom, prenom, age, genre, dateNaissance, photo, email, pseudonyme, niveau, points, nbAction)

            return redirect(url_for('profile'))  # Redirige vers la page de profil après modification

        return render_template('edit_profile.html', user=user_info)  # Affiche le formulaire d'édition avec les données actuelles
    else:
        return redirect(url_for('connexion'))  # Redirige vers la page de connexion si l'utilisateur n'est pas connecté

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
    
@app.route('/accueil_objets')
def accueil_objets():#portail des objets connectés
    if 'username' in session:
        return render_template('accueil_objets.html')
    else:
        flash('Veuillez vous connecter pour accéder à cette page')
        return redirect(url_for('connexion'))
    

@app.route('/search_objets', methods=['GET'])
def search_objets():#fonction de recherche des objets
    search_query = request.args.get('search-input')
    service_filter = request.args.get('service-filter')  #filtre de service
    type_filter = request.args.get('type-filter') # filtre de type
    marque_filter = request.args.get('marque-filter') #filtre de marque

    con = sql.connect("donnees.db")
    cur = con.cursor()

    sql_query = "SELECT * FROM Objet WHERE 1=1" #technique pour ajouter une condition

    params = []

    if search_query:
        sql_query += " AND (ID LIKE ? OR nom LIKE ?)"
        params.extend(['%' + search_query + '%'], ['%' + search_query + '%'])

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
    pseudonyme = session['username']
    update_user_points(pseudonyme, 1,1)
    con.close()

    return render_template('resultats-objets.html', results=results, query=search_query)

@app.route('/ajout-objet.html', methods=['POST', 'GET'])
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
        # Récupération des informations du formulaire
        ID = request.form['ID']
        tempActuelle = request.form['tempActuelle']
        tempCible = request.form['tempCible']
        mode = request.form['mode']
        connectivite = request.form['connectivite']
        batterie = request.form['batterie']
        service = request.form['service']
        marque = request.form['marque']
        nom = request.form['nom']
        type_object = request.form['type']
        dernierReglage = request.form['dernierReglage']
        consommationL = request.form['ConsommationL']
        consommationW = request.form['ConsommationW']

        # Insérer l'objet dans la BDD
        insert_object(ID, tempActuelle, tempCible, mode, connectivite, batterie, service, marque, nom, type_object, dernierReglage, consommationL, consommationW)

        # Mettre à jour les points et les actions de l'utilisateur
        update_user_points(pseudonyme, 2)
        increment_user_actions(pseudonyme)  # 🔥 Ajout du compteur d'actions

        flash("Objet ajouté avec succès !")
        return redirect(url_for('accueil_objets'))

    return render_template('ajout-objet.html')

@app.route('/profil/<string:pseudonyme>')
def profilPublic(pseudonyme): #fonction permettant d'afficher le profil publique
    # Récupère les informations du profil à partir de l'ID
    user_profile = getUserInfosPublic(pseudonyme)
    if user_profile:
        return render_template('profilPublic.html', profile=user_profile)
    else:
        return "Profil non trouvé"

@app.route('/confirmer/<token>')
def confirmer_compte(token):#fonction qui permet de générer le token de confirmation et met à jour la base de donnée pour la confirmation
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
    else:
        
        return redirect(url_for('creer_profil'))
    
@app.route("/utilisateurs")
def liste_utilisateurs():
    conn = sql.connect("donnees.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom, prenom, age, genre, email, dateNaissance, type, 
        photo, fonction, service, niveau, pseudonyme, 
        points, nbAction, nbAcces 
        FROM Informations
    """)  # Vérifie bien que nbAcces est inclus !
    users = cursor.fetchall()
    conn.close()

    return render_template("utilisateurs.html", users=users)



if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')
