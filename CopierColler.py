import os
import shutil
import sys


def trouver_nom_copie(dossier_parent, nom_original):
    numero = 1

    while True:
        nouveau_nom = f"{nom_original}_{numero:02d}"
        nouveau_dossier = os.path.join(dossier_parent, nouveau_nom)

        if not os.path.exists(nouveau_dossier):
            return nouveau_dossier

        numero += 1


def main():
    # Dossier dans lequel se trouve ce patcher.py
    dossier_source = os.path.dirname(os.path.abspath(__file__))

    # Nom du dossier contenant patcher.py
    nom_original = os.path.basename(dossier_source)

    # Dossier parent
    dossier_parent = os.path.dirname(dossier_source)

    # Cherche automatiquement le prochain numéro disponible
    dossier_destination = trouver_nom_copie(
        dossier_parent,
        nom_original
    )

    print()
    print("=" * 60)
    print("      COPIE DU PROJET")
    print("=" * 60)
    print()
    print(f"Source      : {dossier_source}")
    print(f"Destination : {dossier_destination}")
    print()

    try:
        # Copie complète du dossier
        shutil.copytree(
            dossier_source,
            dossier_destination
        )

        print("Copie terminée avec succès !")
        print()
        print(f"Nouveau dossier :")
        print(dossier_destination)
        print()

    except Exception as e:
        print("ERREUR pendant la copie :")
        print(str(e))
        print()

        sys.exit(1)

    print("=" * 60)
    print("Appuyez sur Entrée pour fermer...")
    input()


if __name__ == "__main__":
    main()

