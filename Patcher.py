from pathlib import Path
from datetime import datetime
import re
import shutil
import py_compile
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / "_PATCH_BACKUPS"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = BACKUP_ROOT / f"GITHUB_SECURITY_V3_{STAMP}"

def backup(path: Path):
    if not path.exists():
        return
    rel = path.relative_to(ROOT)
    dst = BACKUP_DIR / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    print(f"[BACKUP] {rel}")

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")

def patch_admin_auth() -> bool:
    path = ROOT / "admin_auth.py"
    if not path.exists():
        print("[ERREUR] admin_auth.py introuvable.")
        return False

    backup(path)
    text = read_text(path)
    original = text

    # Supprime complètement les anciens symboles de fallback.
    text = text.replace("FALLBACK_ADMIN_SALT", '""')
    text = text.replace("FALLBACK_ADMIN_HASH", '""')
    text = text.replace("FALLBACK_ADMIN_PASSWORD", '""')

    # Normalise les variables d'authentification sur les variables d'environnement.
    text = re.sub(
        r'ADMIN_SALT\s*=\s*os\.getenv\(\s*[\'"]SASTOUKASTORE_ADMIN_SALT[\'"]\s*,\s*""\s*\)',
        'ADMIN_SALT = os.getenv("SASTOUKASTORE_ADMIN_SALT", "").strip()',
        text,
    )
    text = re.sub(
        r'ADMIN_HASH\s*=\s*os\.getenv\(\s*[\'"]CHARIOW_ADMIN_HASH[\'"]\s*,\s*""\s*\)',
        'ADMIN_HASH = os.getenv("CHARIOW_ADMIN_HASH", "").strip()',
        text,
    )

    # Évite qu'un ancien mécanisme de valeur de secours réintroduise un secret.
    text = re.sub(
        r'ADMIN_SALT\s*=\s*ADMIN_SALT\s+or\s*[\'"][^\'"]*[\'"]',
        'ADMIN_SALT = ADMIN_SALT or ""',
        text,
    )
    text = re.sub(
        r'ADMIN_HASH\s*=\s*ADMIN_HASH\s+or\s*[\'"][^\'"]*[\'"]',
        'ADMIN_HASH = ADMIN_HASH or ""',
        text,
    )

    if text != original:
        write_text(path, text)
        print("[WRITE] admin_auth.py : références de fallback supprimées.")
    else:
        print("[OK] Aucun remplacement supplémentaire nécessaire.")

    try:
        py_compile.compile(str(path), doraise=True)
        print("[CHECK] Syntaxe OK : admin_auth.py")
    except Exception as exc:
        print("[ERREUR] Syntaxe KO : admin_auth.py")
        print(exc)
        print(f"[BACKUP] Sauvegarde disponible : {BACKUP_DIR}")
        return False

    remaining = []
    for token in ("FALLBACK_ADMIN_PASSWORD", "FALLBACK_ADMIN_SALT", "FALLBACK_ADMIN_HASH"):
        if token in read_text(path):
            remaining.append(token)

    if remaining:
        print("[ATTENTION] Références restantes :")
        for item in remaining:
            print(f"  - {item}")
        return False

    print("[CHECK] Aucun identifiant de secours connu restant dans admin_auth.py.")
    return True

def check_gitignore() -> bool:
    path = ROOT / ".gitignore"
    required = [
        ".env",
        ".env.*",
        "!.env.example",
        "secret.json",
        "data/*.db",
        "data/*.sqlite",
        "data/*.sqlite3",
        "protected_data/",
        "_PATCH_BACKUPS/",
        ".venv/",
        "venv/",
        "env/",
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        "*.log",
        "instance/",
        "Thumbs.db",
        ".DS_Store",
    ]

    if not path.exists():
        print("[ERREUR] .gitignore introuvable.")
        return False

    lines = {x.strip() for x in read_text(path).splitlines() if x.strip()}
    missing = [x for x in required if x not in lines]

    if missing:
        print("[ATTENTION] Règles .gitignore absentes :")
        for item in missing:
            print(f"  - {item}")
        return False

    print("[CHECK] .gitignore : règles de sécurité complètes.")
    return True

def check_gitignore_behavior():
    checks = [
        ".env",
        "secret.json",
        "data/chariow.db",
        "protected_data/pdfs/test.pdf",
        "_PATCH_BACKUPS/test.txt",
        ".env.example",
    ]

    print("[GIT CHECK] Vérification avec git check-ignore :")
    for item in checks:
        try:
            p = subprocess.run(
                ["git", "check-ignore", "-q", item],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            state = "IGNORÉ" if p.returncode == 0 else "NON IGNORÉ"
            note = " (doit être NON IGNORÉ)" if item == ".env.example" else ""
            print(f"  - {item:<35} {state}{note}")
        except Exception as exc:
            print(f"  - {item:<35} ERREUR : {exc}")

def main():
    print("=" * 96)
    print("PATCHER - SASTOUKASTORE / GITHUB SECURITY V3")
    print("=" * 96)
    print(f"[DOSSIER] {ROOT}")
    print()

    if not (ROOT / ".gitignore").exists():
        print("[STOP] .gitignore introuvable dans la racine.")
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ok_ignore = check_gitignore()

    print()
    ok_auth = patch_admin_auth()

    print()
    check_gitignore_behavior()

    print()
    print("=" * 96)

    if ok_ignore and ok_auth:
        print("GITHUB SECURITY V3 : CONTRÔLE PROPRE")
        print("=" * 96)
        print("[OK] .gitignore valide.")
        print("[OK] admin_auth.py n'utilise plus les identifiants de secours connus.")
        print("[SUITE] Contrôle final puis git init / git add .")
    else:
        print("GITHUB SECURITY V3 : ACTION REQUISE")
        print("=" * 96)
        print("[ATTENTION] Corriger les éléments signalés avant le premier push.")

    print(f"[BACKUP] {BACKUP_DIR}")
    return 0 if (ok_ignore and ok_auth) else 1

if __name__ == "__main__":
    raise SystemExit(main())
