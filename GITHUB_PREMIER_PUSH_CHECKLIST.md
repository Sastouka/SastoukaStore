# SastoukaStore — contrôle avant premier push GitHub

Date : 2026-10-07 00:09:27

## Contrôle effectué

- `.gitignore` vérifié
- fichiers locaux sensibles recherchés
- recherche de secrets évidents dans les fichiers texte
- vérification de Git

## Fichiers à ne jamais publier

```text
.env
secret.json
data/*.db
data/*.sqlite
data/*.sqlite3
protected_data/
_PATCH_BACKUPS/
```

## Vérification avant staging

```powershell
git status --short
git ls-files .env secret.json data/chariow.db
```

La deuxième commande ne doit retourner aucun fichier sensible.

## Premier commit

```powershell
git init
git add .
git status
git commit -m "Initial commit - SastoukaStore"
git branch -M main
```

Puis, après création du dépôt GitHub :

```powershell
git remote add origin https://github.com/Sastouka/NOM-DU-DEPOT.git
git push -u origin main
```

## Sécurité

Ne jamais publier les vrais identifiants PayPal, mots de passe,
clés API, clés privées ou fichiers `.env`.

### Résultat du pré-flight

- `.gitignore` : À compléter
- fichiers sensibles locaux détectés : oui
- motifs de secrets dans le code : oui — revue nécessaire
- Git : OK
