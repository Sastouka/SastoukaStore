from pathlib import Path
from datetime import datetime
import shutil
import sys

ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / "_PATCH_BACKUPS"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = BACKUP_ROOT / f"RENDER_BLUEPRINT_FINAL_{STAMP}"

def backup(path: Path):
    if not path.exists():
        return
    dst = BACKUP_DIR / path.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    print(f"[BACKUP] {path.relative_to(ROOT)}")

def main():
    print("=" * 96)
    print("PATCHER - SASTOUKASTORE / RENDER BLUEPRINT FINAL V1")
    print("=" * 96)
    print(f"[DOSSIER] {ROOT}")
    print()

    path = ROOT / "render.yaml"
    if not path.exists():
        print("[ERREUR] render.yaml introuvable.")
        return 1

    backup(path)

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
    path.write_text(content, encoding="utf-8")
    print("[WRITE] render.yaml")
    print("[CHECK] name: sastoukastore")
    print("[CHECK] runtime: python")
    print("[CHECK] plan: free")
    print("[CHECK] branch: main")
    print("[CHECK] region: frankfurt")
    print("[CHECK] buildCommand: pip install -r requirements.txt")
    print("[CHECK] startCommand: gunicorn app:app")
    print("[CHECK] autoDeployTrigger: commit")
    print()
    print("=" * 96)
    print("RENDER BLUEPRINT FINAL V1 : TERMINE")
    print("=" * 96)
    print("[OK] Blueprint Render complet.")
    print("[INFO] Frankfurt choisi comme région de déploiement.")
    print("[SUITE] Tester localement, puis commit/push.")
    print(f"[BACKUP] {BACKUP_DIR}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
