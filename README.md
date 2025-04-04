# Projet Web - Gestion des ressources médicales pour un hôpital connecté

## 1.  Contenu du projet

Ce projet est une application web de **gestion de ressources médicales**. Elle permet de :

- Créer, modifier et supprimer des **salles** et **objets médicaux** (ex : appareils, équipements)
- Gérer des utilisateurs selon leur **niveau d’accès** (invité, utilisateurs simples, complexes et administrateurs)
- Consulter les profils, confirmer un compte via email pour l'inscription, pouvoir savoir qui est practicien dans quel domaine
- Visualiser et interagir avec les objets et les utilisateurs dans une interface simple et claire

## 2. 🎯 Objectif du projet

L’objectif est de développer une plateforme pour :

- Créer, modifier et supprimer des **salles** et **objets médicaux** (ex : appareils, équipements)
- Gérer des utilisateurs selon leur **niveau d’accès** (invité, utilisateurs simples, complexes et administrateurs)
- Consulter les profils, confirmer un compte via email pour l'inscription, pouvoir savoir qui est practicien dans quel domaine
- Visualiser et interagir avec les objets et les utilisateurs dans une interface simple et claire


## 3.  Groupe de travail

Projet réalisé par :

- Abdellah DJEDIDI
- Charf-Eddine CHAKROUN 
- Melina GARUFI, 
- Nathan LE NESTOUR,
- Rayane SAIL

## 4.  Fichiers principaux

Le projet est constitué de : 
- `app.py` → le fichier principal contenant les routes Flask 
- `models.py` → les fonctions de manipulation des données SQLite, d'email, d'insertion et de mise à jour de base de données
- `BDD.txt` → structure de la base de données donnees.db
- `templates/` → tous les fichiers HTML reliés aux routes des fonctions flask
- `static/` → dossier contenant le fichier styles.css pour le rendu des pages html et les images de photo de profil.
- `config.py` → configuration Flask (clé secrète, email)
- `migrate.py`→ fichier python permettant de manipuler certaines parties de la base de données, insérer des tables ou des colonnes
-- `test.txt` → fichier servant à stocker les fonctions lors du nettoyage du code
- `README.md` → ce fichier

## 5.  Compilation & Lancement

Ce projet a été majoritairement fait sur Linux. Pour pouvoir lancer le site web, il faut d'abord se prémunir du code situé dans le dépot https://github.com/Abde2lah/Projet-web/
Il faut avant toute chose créer un environnement virtuel venv dans lesquelle on manipulera les variables

Sous linux : `python3 -m venv venv` 
Si un problème est lié au venv, la commande `rm -rf venv` permettra de supprimer le venv pour en créer un nouveau.

Pour activer le venv, on effectue `source venv/bin/activate`.

Enfin, on peut executer le code avec `python app.py`.


## 6. Bibliothèque

La conception de ce site a été faite grâce à plusieurs bibliothèques : 
- `flask` → pour la gestion des routes et le rendu 
- `flask_mail` → pour la confirmation de l'inscrption par mail.
- `sqlite3` →  pour la gestion de la base de données
- `bcrypt` → 
- `os` → 
- `werkzeug` → pour la gestion des photos de profil dans un dossier sécurié



