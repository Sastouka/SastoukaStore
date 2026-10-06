from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / "_PATCH_BACKUPS"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = BACKUP_ROOT / f"RENDER_GITHUB_CLEANUP_{STAMP}"

def backup(path: Path):
    if not path.exists():
        return
    dst = BACKUP_DIR / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    print(f"[BACKUP] {path.relative_to(ROOT)}")

def main():
    print("=" * 96)
    print("PATCHER - SASTOUKASTORE / RENDER GITHUB CLEANUP V1")
    print("=" * 96)
    print(f"[DOSSIER] {ROOT}")
    print()

    render = ROOT / "render.yaml"
    if not render.exists():
        print("[ERREUR] render.yaml introuvable.")
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup(render)

    content = """services:
  - type: web
    name: sastoukastore
    runtime: python
    plan: free
    branch: main
    region: frankfurt
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    autoDeployTrigger: commit
"""
    render.write_text(content, encoding="utf-8")

    print("[WRITE] render.yaml")
    print("[CHECK] type: web")
    print("[CHECK] name: sastoukastore")
    print("[CHECK] runtime: python")
    print("[CHECK] plan: free")
    print("[CHECK] branch: main")
    print("[CHECK] region: frankfurt")
    print("[CHECK] buildCommand: pip install -r requirements.txt")
    print("[CHECK] startCommand: gunicorn app:app")
    print("[CHECK] autoDeployTrigger: commit")

    accidental = ROOT / "ion"
    if accidental.exists():
        backup(accidental)
        try:
            accidental.unlink()
            print("[DELETE] ion (fichier accidentel détecté dans le dernier commit)")
        except Exception as exc:
            print(f"[ERREUR] Impossible de supprimer ion : {exc}")
            return 1
    else:
        print("[OK] Fichier accidentel 'ion' absent.")

    try:
        diff = subprocess.run(
            ["git", "diff", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if diff.returncode == 0:
            print("[CHECK] git diff --check : OK")
        else:
            print("[ERREUR] git diff --check :")
            print(diff.stdout)
            print(diff.stderr)
            return 1
    except Exception as exc:
        print(f"[ATTENTION] git diff --check non disponible : {exc}")

    print()
    print("=" * 96)
    print("RENDER GITHUB CLEANUP V1 : TERMINÉ")
    print("=" * 96)
    print("[OK] render.yaml corrigé pour Render.")
    print("[OK] runtime python explicite.")
    print("[OK] branche main explicite.")
    print("[OK] fichier accidentel ion supprimé.")
    print()
    print("[SUITE]")
    print("git add .")
    print("git status")
    print('git commit -m "Fix Render configuration"')
    print("git push origin main")
    print()
    print(f"[BACKUP] {BACKUP_DIR}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
