import os
import json
from datetime import datetime

# ==========================================
# Configuration des dossiers
# ==========================================
DOSSIER_SOURCE = os.path.dirname(os.path.abspath(__file__))

# Nom du dossier où seront sauvegardés les 5 JSON
NOM_DOSSIER_SORTIE = "resultats_json"
DOSSIER_SORTIE = os.path.join(DOSSIER_SOURCE, NOM_DOSSIER_SORTIE)

# Créer le dossier de sortie s'il n'existe pas déjà
os.makedirs(DOSSIER_SORTIE, exist_ok=True)

# Nombre de fichiers JSON souhaités en sortie
NOMBRE_JSON = 5

# Extensions à lire
EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js", ".xml",
    ".yaml", ".yml", ".ini", ".cfg", ".log", ".sql", ".bat", ".ps1",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".dart", ".kt",
    ".gradle", ".properties"
}

resultats = []

print("=" * 70)
print("DOSSIER RACINE")
print(DOSSIER_SOURCE)
print("=" * 70)

nb_dossiers = 0

for racine, dossiers, fichiers in os.walk(DOSSIER_SOURCE):
    
    # ÉVITER DE SCANNER LE DOSSIER DE SORTIE (pour ne pas relire les JSON générés)
    if NOM_DOSSIER_SORTIE in dossiers:
        dossiers.remove(NOM_DOSSIER_SORTIE)

    nb_dossiers += 1
    print(f"\n📂 {racine}")

    for fichier in fichiers:
        chemin = os.path.join(racine, fichier)
        extension = os.path.splitext(fichier)[1].lower()
        print(f"   -> {fichier}")

        if extension not in EXTENSIONS:
            continue

        try:
            with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
                contenu = f.read()

            stat = os.stat(chemin)
            resultats.append({
                "nom": fichier,
                "extension": extension,
                "chemin_absolu": chemin,
                "chemin_relatif": os.path.relpath(chemin, DOSSIER_SOURCE),
                "dossier": os.path.relpath(racine, DOSSIER_SOURCE),
                "taille": stat.st_size,
                "date_modification": datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "contenu": contenu
            })

        except Exception as e:
            print("Erreur :", chemin)
            print(e)

# ==========================================
# Répartition et sauvegarde dans le sous-dossier
# ==========================================
total_fichiers_lus = len(resultats)

# Calcul pour diviser la liste en 5 segments de manière équilibrée
k, m = divmod(total_fichiers_lus, NOMBRE_JSON)
parties = [resultats[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(NOMBRE_JSON)]

print("\n" + "=" * 70)
print(f"GÉNÉRATION DES FICHIERS JSON DANS : {NOM_DOSSIER_SORTIE}/")
print("=" * 70)

for i, partie in enumerate(parties):
    # Ignore la création du fichier s'il est vide
    if not partie:
        continue
        
    # Sauvegarde dans le DOSSIER_SORTIE au lieu de DOSSIER_SOURCE
    nom_fichier = os.path.join(DOSSIER_SORTIE, f"contenu_global_partie_{i+1}.json")
    with open(nom_fichier, "w", encoding="utf-8") as f:
        json.dump(partie, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Fichier JSON {i+1} créé ({len(partie)} fichiers) : {nom_fichier}")

print("\n" + "=" * 70)
print("ANALYSE TERMINÉE")
print("=" * 70)
print("Nombre de dossiers parcourus :", nb_dossiers)
print("Nombre total de fichiers lus :", total_fichiers_lus)