# SastoukaStore

SastoukaStore est une boutique Flask/PWA dédiée à la vente de supports PDF numériques.

## Fonctionnalités

- Catalogue public de livres et supports PDF.
- Recherche de livres dans le catalogue.
- Filtrage par catégorie.
- Aperçu PDF avant achat.
- Panier numérique sans gestion de livraison.
- Parcours d'achats et suivi côté client.
- Interface d'administration pour gérer les livres et les achats.
- Gestion des couvertures et fichiers PDF locaux.
- Paiement PayPal selon la configuration actuelle du projet.
- Application PWA responsive.

## Architecture

```text
SastoukaStore/
├── app.py
├── admin_auth.py
├── admin_catalog.py
├── admin_orders.py
├── digital_orders.py
├── download_access.py
├── payment_service.py
├── payments.py
├── db_migrations.py
├── order_engine_v3.py
├── phone_utils.py
├── templates/
├── static/
├── data/
│   └── chariow.db
├── protected_data/
│   └── pdfs/
├── .env.example
├── requirements.txt
└── README.md
```

## Prérequis

Python 3.12 est recommandé pour l'environnement actuellement utilisé par le projet.

## Installation locale

### 1. Créer l'environnement virtuel

Windows PowerShell :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Installer les dépendances

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Préparer la configuration

Copiez :

```text
.env.example
```

vers :

```text
.env
```

Puis renseignez les valeurs réelles.

Exemple :

```powershell
Copy-Item .env.example .env
```

Ne publiez jamais `.env`.

## Clé Flask

La variable suivante est utilisée par l'application :

```text
CHARIOW_SECRET_KEY
```

Utilisez une valeur longue, aléatoire et unique.

## Compte administrateur

La configuration actuelle de `admin_auth.py` utilise notamment :

```text
SASTOUKASTORE_ADMIN_USER
SASTOUKASTORE_ADMIN_SALT
CHARIOW_ADMIN_HASH
```

Le hash administrateur est calculé à partir de :

```text
SHA256(SASTOUKASTORE_ADMIN_SALT + mot_de_passe)
```

Ne mettez jamais un mot de passe administrateur en clair dans GitHub.

## PayPal

La version actuelle du projet utilise encore :

```text
secret.json
```

pour charger les identifiants PayPal.

**Ne publiez jamais `secret.json`.**

Avant de publier le dépôt, vérifiez que ce fichier ne contient aucun secret dans l'historique Git. Une fois un secret publié, le supprimer du fichier ne suffit pas à le considérer comme sûr : il faut aussi le révoquer/renouveler côté fournisseur.

## Lancement local

```powershell
python app.py
```

Puis ouvrez :

```text
http://127.0.0.1:5000
```

Pour tester depuis un téléphone connecté au même réseau :

```text
http://IP_DU_PC:5000
```

## Données locales

La base SQLite est stockée dans :

```text
data/chariow.db
```

Les fichiers PDF protégés sont stockés dans :

```text
protected_data/pdfs/
```

Ces données locales ne doivent pas être poussées sur un dépôt public.

## Dépôt GitHub

Le dépôt recommandé est :

```text
https://github.com/Sastouka/SastoukaStore
```

Initialisation :

```powershell
git init
git add .
git status
git commit -m "Initial public release of SastoukaStore"
git branch -M main
git remote add origin https://github.com/Sastouka/SastoukaStore.git
git push -u origin main
```

Avant le premier `git push`, vérifiez impérativement :

```powershell
git status
git ls-files .env secret.json data protected_data
```

Les fichiers contenant des secrets, la base SQLite et les PDF privés ne doivent pas apparaître comme fichiers suivis.

## Sécurité avant publication

À contrôler avant le premier push :

- `.env` ne doit pas être versionné.
- `secret.json` ne doit pas être versionné.
- `data/chariow.db` ne doit pas être versionné.
- `protected_data/` ne doit pas être versionné.
- Les dossiers `_PATCH_BACKUPS/` ne doivent pas être versionnés.
- Les mots de passe, hashes sensibles et tokens réels ne doivent pas apparaître dans le code source public.
- Les anciennes sauvegardes contenant des secrets ne doivent pas être publiées.

## Dépendances principales

- Flask
- python-dotenv
- Requests
- Pillow
- OpenPyXL
- PyMuPDF

SQLite est fourni avec Python et ne nécessite pas de paquet séparé.

## Licence

Ajoutez la licence correspondant à votre choix avant publication du dépôt public.

---

SastoukaStore  
Le savoir en 1 clic.
