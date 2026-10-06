# -*- coding: utf-8 -*-
"""
SastoukaStore — BUILD WINDOWS ONEFILE INDEPENDANT V2

Résultat :
    dist\SastoukaStore.exe

À côté de SastoukaStore.exe, le premier lancement crée uniquement :
    SastoukaStore_DATA\

Le code/templates/static sont embarqués dans l'EXE et extraits temporairement
dans %TEMP% pendant l'exécution. Les données modifiables sont synchronisées
dans SastoukaStore_DATA.

Identifiant initial : SastoukaStore
Mot de passe initial : SastoukaStore123456
"""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "SastoukaStore"
ENTRY = ROOT / "app.py"
ICON_PNG = Path(r"C:\Users\hp\Downloads\iconsastoukastore.png")

BUILD_DIR = ROOT / "_build_sastoukastore_onefile_v2"
DIST_DIR = ROOT / "dist"
PAYLOAD = BUILD_DIR / "sastoukastore_payload.zip"
LAUNCHER = BUILD_DIR / "sastoukastore_launcher.py"
ICO = BUILD_DIR / "sastoukastore.ico"

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "_PATCH_BACKUPS", "build", "dist",
    "_build_sastoukastore_onefile_v2", "node_modules"
}
EXCLUDED_FILES = {
    ".env", ".env.local", ".env.production",
    "Build_windows.py",
    "Build_windows_SastoukaStore_OneFile_VIP.py",
    "Build_windows_SastoukaStore_OneFile_Independent.py",
    "Build_windows_SastoukaStore_OneFile_Independent_v2.py",
}

LAUNCHER_B64 = 'IyAtKi0gY29kaW5nOiB1dGYtOCAtKi0KZnJvbSBfX2Z1dHVyZV9fIGltcG9ydCBhbm5vdGF0aW9ucwppbXBvcnQgaGFzaGxpYiwgb3MsIHNlY3JldHMsIHNodXRpbCwgc3lzLCB0ZW1wZmlsZSwgemlwZmlsZQpmcm9tIHBhdGhsaWIgaW1wb3J0IFBhdGgKCkFQUF9OQU1FID0gIkNIQVJJT1ciCkRBVEFfRElSX05BTUUgPSAiQ0hBUklPV19EQVRBIgpQQVlMT0FEX05BTUUgPSAiY2hhcmlvd19wYXlsb2FkLnppcCIKRU5WX05BTUUgPSAiLmVudiIKCk1VVEFCTEVfRElSUyA9ICgKICAgICJkYXRhIiwKICAgICJzdGF0aWMvdXBsb2FkcyIsCiAgICAicHJvdGVjdGVkX2RhdGEiLAogICAgImJhY2t1cHMiLAogICAgImV4cG9ydHMiLAogICAgImxvZ3MiLAogICAgIkNvbmZpZyIsCikKCmRlZiBleGVfZGlyKCk6CiAgICByZXR1cm4gUGF0aChzeXMuZXhlY3V0YWJsZSkucmVzb2x2ZSgpLnBhcmVudAoKZGVmIGJ1bmRsZV9kaXIoKToKICAgIG1laXBhc3MgPSBnZXRhdHRyKHN5cywgIl9NRUlQQVNTIiwgTm9uZSkKICAgIHJldHVybiBQYXRoKG1laXBhc3MpIGlmIG1laXBhc3MgZWxzZSBQYXRoKF9fZmlsZV9fKS5yZXNvbHZlKCkucGFyZW50CgpkZWYgcGVyc2lzdGVudF9kaXIoKToKICAgIHRhcmdldCA9IGV4ZV9kaXIoKSAvIERBVEFfRElSX05BTUUKICAgIHRyeToKICAgICAgICB0YXJnZXQubWtkaXIocGFyZW50cz1UcnVlLCBleGlzdF9vaz1UcnVlKQogICAgICAgIHByb2JlID0gdGFyZ2V0IC8gIi53cml0ZV90ZXN0IgogICAgICAgIHByb2JlLndyaXRlX3RleHQoIm9rIiwgZW5jb2Rpbmc9InV0Zi04IikKICAgICAgICBwcm9iZS51bmxpbmsobWlzc2luZ19vaz1UcnVlKQogICAgICAgIHJldHVybiB0YXJnZXQKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgcm9vdCA9IFBhdGgob3MuZW52aXJvbi5nZXQoIkxPQ0FMQVBQREFUQSIsIFBhdGguaG9tZSgpKSkKICAgICAgICB0YXJnZXQgPSByb290IC8gQVBQX05BTUUgLyBEQVRBX0RJUl9OQU1FCiAgICAgICAgdGFyZ2V0Lm1rZGlyKHBhcmVudHM9VHJ1ZSwgZXhpc3Rfb2s9VHJ1ZSkKICAgICAgICByZXR1cm4gdGFyZ2V0CgpkZWYgcmVtb3ZlX3RyZWUocGF0aCk6CiAgICBpZiBwYXRoLmV4aXN0cygpOgogICAgICAgIHNodXRpbC5ybXRyZWUocGF0aCwgaWdub3JlX2Vycm9ycz1UcnVlKQoKZGVmIGNvcHlfdHJlZShzcmMsIGRzdCk6CiAgICBpZiBub3Qgc3JjLmV4aXN0cygpOgogICAgICAgIHJldHVybgogICAgZHN0LnBhcmVudC5ta2RpcihwYXJlbnRzPVRydWUsIGV4aXN0X29rPVRydWUpCiAgICByZW1vdmVfdHJlZShkc3QpCiAgICBzaHV0aWwuY29weXRyZWUoc3JjLCBkc3QpCgpkZWYgc2VlZF9wZXJzaXN0ZW50X2RhdGEocnVudGltZSwgcGVyc2lzdGVudCk6CiAgICBmb3IgcmVsIGluIE1VVEFCTEVfRElSUzoKICAgICAgICBzcmMgPSBydW50aW1lIC8gcmVsCiAgICAgICAgZHN0ID0gcGVyc2lzdGVudCAvIHJlbAogICAgICAgIGlmIHNyYy5leGlzdHMoKSBhbmQgbm90IGRzdC5leGlzdHMoKToKICAgICAgICAgICAgY29weV90cmVlKHNyYywgZHN0KQoKZGVmIHN5bmNfZnJvbV9wZXJzaXN0ZW50KHBlcnNpc3RlbnQsIHJ1bnRpbWUpOgogICAgZm9yIHJlbCBpbiBNVVRBQkxFX0RJUlM6CiAgICAgICAgc3JjID0gcGVyc2lzdGVudCAvIHJlbAogICAgICAgIGRzdCA9IHJ1bnRpbWUgLyByZWwKICAgICAgICBpZiBzcmMuZXhpc3RzKCk6CiAgICAgICAgICAgIGNvcHlfdHJlZShzcmMsIGRzdCkKCmRlZiBzeW5jX3RvX3BlcnNpc3RlbnQocnVudGltZSwgcGVyc2lzdGVudCk6CiAgICBmb3IgcmVsIGluIE1VVEFCTEVfRElSUzoKICAgICAgICBzcmMgPSBydW50aW1lIC8gcmVsCiAgICAgICAgZHN0ID0gcGVyc2lzdGVudCAvIHJlbAogICAgICAgIGlmIHNyYy5leGlzdHMoKToKICAgICAgICAgICAgY29weV90cmVlKHNyYywgZHN0KQoKZGVmIGVuc3VyZV9jcmVkZW50aWFscyhwZXJzaXN0ZW50KToKICAgIGVudl9wYXRoID0gcGVyc2lzdGVudCAvIEVOVl9OQU1FCiAgICBpZiBub3QgZW52X3BhdGguZXhpc3RzKCk6CiAgICAgICAgdXNlcm5hbWUgPSAiQ2hhcmlvdyIKICAgICAgICBwYXNzd29yZCA9ICJDaGFyaW93MTIzNDU2IgogICAgICAgIHNhbHQgPSBzZWNyZXRzLnRva2VuX2hleCgxNikKICAgICAgICBwd2RfaGFzaCA9IGhhc2hsaWIuc2hhMjU2KChzYWx0ICsgcGFzc3dvcmQpLmVuY29kZSgidXRmLTgiKSkuaGV4ZGlnZXN0KCkKICAgICAgICBlbnZfcGF0aC53cml0ZV90ZXh0KAogICAgICAgICAgICBmJ0NIQVJJT1dfQURNSU5fVVNFUj0ie3VzZXJuYW1lfSJcbicKICAgICAgICAgICAgZidDSEFSSU9XX0FETUlOX1NBTFQ9IntzYWx0fSJcbicKICAgICAgICAgICAgZidDSEFSSU9XX0FETUlOX0hBU0g9Intwd2RfaGFzaH0iXG4nCiAgICAgICAgICAgIGYnQ0hBUklPV19ET1dOTE9BRF9LRVlfU0VDUkVUPSJ7c2VjcmV0cy50b2tlbl9oZXgoMzIpfSJcbicKICAgICAgICAgICAgZidDSEFSSU9XX1NFQ1JFVF9LRVk9IntzZWNyZXRzLnRva2VuX2hleCgzMil9IlxuJwogICAgICAgICAgICAnRkxBU0tfREVCVUc9IjAiXG4nLAogICAgICAgICAgICBlbmNvZGluZz0idXRmLTgiLAogICAgICAgICkKCiAgICB2YWx1ZXMgPSB7fQogICAgZm9yIGxpbmUgaW4gZW52X3BhdGgucmVhZF90ZXh0KGVuY29kaW5nPSJ1dGYtOCIsIGVycm9ycz0iaWdub3JlIikuc3BsaXRsaW5lcygpOgogICAgICAgIGxpbmUgPSBsaW5lLnN0cmlwKCkKICAgICAgICBpZiBub3QgbGluZSBvciBsaW5lLnN0YXJ0c3dpdGgoIiMiKSBvciAiPSIgbm90IGluIGxpbmU6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgaywgdiA9IGxpbmUuc3BsaXQoIj0iLCAxKQogICAgICAgIHZhbHVlc1trLnN0cmlwKCldID0gdi5zdHJpcCgpLnN0cmlwKCciJykuc3RyaXAoIiciKQoKICAgIHZhbHVlcy5zZXRkZWZhdWx0KCJDSEFSSU9XX0FETUlOX1VTRVIiLCAiQ2hhcmlvdyIpCiAgICB2YWx1ZXMuc2V0ZGVmYXVsdCgiQ0hBUklPV19BRE1JTl9TQUxUIiwgIiIpCiAgICB2YWx1ZXMuc2V0ZGVmYXVsdCgiQ0hBUklPV19BRE1JTl9IQVNIIiwgIiIpCiAgICB2YWx1ZXMuc2V0ZGVmYXVsdCgiQ0hBUklPV19ET1dOTE9BRF9LRVlfU0VDUkVUIiwgc2VjcmV0cy50b2tlbl9oZXgoMzIpKQogICAgdmFsdWVzLnNldGRlZmF1bHQoIkNIQVJJT1dfU0VDUkVUX0tFWSIsIHNlY3JldHMudG9rZW5faGV4KDMyKSkKICAgIHZhbHVlc1siRkxBU0tfREVCVUciXSA9ICIwIgoKICAgIGVudl9wYXRoLndyaXRlX3RleHQoCiAgICAgICAgIlxuIi5qb2luKGYne2t9PSJ7dn0iJyBmb3IgaywgdiBpbiB2YWx1ZXMuaXRlbXMoKSkgKyAiXG4iLAogICAgICAgIGVuY29kaW5nPSJ1dGYtOCIsCiAgICApCiAgICBmb3IgaywgdiBpbiB2YWx1ZXMuaXRlbXMoKToKICAgICAgICBvcy5lbnZpcm9uW2tdID0gdgogICAgb3MuZW52aXJvblsiQ0hBUklPV19EQVRBX1JPT1QiXSA9IHN0cihwZXJzaXN0ZW50KQogICAgcmV0dXJuIGVudl9wYXRoCgpkZWYgZXh0cmFjdF9wYXlsb2FkX3RvX3RlbXAoKToKICAgIHBheWxvYWQgPSBidW5kbGVfZGlyKCkgLyBQQVlMT0FEX05BTUUKICAgIGlmIG5vdCBwYXlsb2FkLmV4aXN0cygpOgogICAgICAgIHJhaXNlIEZpbGVOb3RGb3VuZEVycm9yKGYiUGF5bG9hZCBpbnRyb3V2YWJsZSBkYW5zIENIQVJJT1cuZXhlIDoge3BheWxvYWR9IikKICAgIHJ1bnRpbWUgPSBQYXRoKHRlbXBmaWxlLm1rZHRlbXAocHJlZml4PSJDSEFSSU9XXyIpKQogICAgd2l0aCB6aXBmaWxlLlppcEZpbGUocGF5bG9hZCwgInIiKSBhcyB6ZjoKICAgICAgICB6Zi5leHRyYWN0YWxsKHJ1bnRpbWUpCiAgICByZXR1cm4gcnVudGltZQoKZGVmIG1haW4oKToKICAgIHBlcnNpc3RlbnQgPSBwZXJzaXN0ZW50X2RpcigpCiAgICBydW50aW1lID0gZXh0cmFjdF9wYXlsb2FkX3RvX3RlbXAoKQogICAgdHJ5OgogICAgICAgIHNlZWRfcGVyc2lzdGVudF9kYXRhKHJ1bnRpbWUsIHBlcnNpc3RlbnQpCiAgICAgICAgc3luY19mcm9tX3BlcnNpc3RlbnQocGVyc2lzdGVudCwgcnVudGltZSkKICAgICAgICBlbnZfcGF0aCA9IGVuc3VyZV9jcmVkZW50aWFscyhwZXJzaXN0ZW50KQoKICAgICAgICAjIGxvYWRfZG90ZW52KCkgZGVzIHZlcnNpb25zIGFjdHVlbGxlcyB0cm91dmVyYSBjZSBmaWNoaWVyLgogICAgICAgIHNodXRpbC5jb3B5MihlbnZfcGF0aCwgcnVudGltZSAvICIuZW52IikKCiAgICAgICAgb3MuZW52aXJvblsiQ0hBUklPV19SVU5USU1FX1JPT1QiXSA9IHN0cihydW50aW1lKQogICAgICAgIG9zLmVudmlyb25bIkNIQVJJT1dfQlVORExFX1JPT1QiXSA9IHN0cihidW5kbGVfZGlyKCkpCgogICAgICAgIG9zLmNoZGlyKHJ1bnRpbWUpCiAgICAgICAgc3lzLnBhdGguaW5zZXJ0KDAsIHN0cihydW50aW1lKSkKCiAgICAgICAgYXBwX2ZpbGUgPSBydW50aW1lIC8gImFwcC5weSIKICAgICAgICBpZiBub3QgYXBwX2ZpbGUuZXhpc3RzKCk6CiAgICAgICAgICAgIHJhaXNlIEZpbGVOb3RGb3VuZEVycm9yKGYiYXBwLnB5IGFic2VudCBhcHLDqHMgZXh0cmFjdGlvbiA6IHthcHBfZmlsZX0iKQoKICAgICAgICBpbXBvcnQgcnVucHkKICAgICAgICBydW5weS5ydW5fcGF0aChzdHIoYXBwX2ZpbGUpLCBydW5fbmFtZT0iX19tYWluX18iKQogICAgZmluYWxseToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHN5bmNfdG9fcGVyc2lzdGVudChydW50aW1lLCBwZXJzaXN0ZW50KQogICAgICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgICAgIHBhc3MKICAgICAgICByZW1vdmVfdHJlZShydW50aW1lKQoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIG1haW4oKQo='

def fail(message):
    print("[ERREUR]", message)
    raise SystemExit(1)

def ensure_package(import_name, pip_name):
    try:
        __import__(import_name)
    except ImportError:
        print("[INFO] Installation :", pip_name)
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

def verify_project():
    print("\n=== 1. VERIFICATION DU PROJET ===")
    for path, label in (
        (ENTRY, "app.py"),
        (ROOT / "templates", "templates/"),
        (ROOT / "static", "static/"),
        (ICON_PNG, "iconsastoukastore.png"),
    ):
        if not path.exists():
            fail(f"{label} introuvable : {path}")
        print("[OK]", label)

def create_ico():
    print("\n=== 2. CREATION ICO ===")
    ensure_package("PIL", "Pillow")
    from PIL import Image
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(ICON_PNG) as src:
            image = src.convert("RGBA")
            print(f"[OK] Source : {image.width}x{image.height} {image.mode}")
            image.resize((256, 256), Image.Resampling.LANCZOS).save(
                ICO,
                format="ICO",
                sizes=[
                    (16,16),(24,24),(32,32),(48,48),
                    (64,64),(128,128),(256,256)
                ],
            )
        print("[OK] ICO :", ICO)
    except Exception as exc:
        fail(f"Création ICO impossible : {exc}")

def excluded(path):
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    if path.name in EXCLUDED_FILES:
        return True
    if path.suffix.lower() in {".exe", ".spec"}:
        return True
    return False

def build_payload():
    print("\n=== 3. EMBARQUEMENT COMPLET ===")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    PAYLOAD.unlink(missing_ok=True)

    count = 0
    total = 0
    with zipfile.ZipFile(
        PAYLOAD, "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file() or excluded(path):
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith("_build_sastoukastore_onefile_v2/"):
                continue
            if rel.startswith("dist/") or rel.startswith("build/"):
                continue
            if path.name.startswith(".env"):
                continue
            zf.write(path, rel)
            count += 1
            total += path.stat().st_size

        version = hashlib.sha256(
            f"{APP_NAME}|{datetime.now():%Y%m%d%H%M%S}|{total}".encode()
        ).hexdigest()[:16]
        zf.writestr("__SastoukaStore_BUILD_VERSION__.txt", version)

    print("[OK] Fichiers embarqués :", count)
    print("[OK] Taille source :", f"{total:,}", "octets")
    print("[OK] Payload :", PAYLOAD)

def create_launcher():
    print("\n=== 4. CREATION LAUNCHER ===")
    LAUNCHER.write_text(
        base64.b64decode(LAUNCHER_B64).decode("utf-8"),
        encoding="utf-8",
    )
    print("[OK] Launcher :", LAUNCHER)

def detect_third_party_imports():
    print("\n=== 5. DEPENDANCES ===")
    names = set()
    for path in ROOT.rglob("*.py"):
        if excluded(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    names.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module.split(".")[0])

    stdlib = set(sys.stdlib_module_names)
    third_party = []
    for name in sorted(names):
        if name in stdlib:
            continue
        try:
            spec = importlib.util.find_spec(name)
        except Exception:
            spec = None
        if spec and spec.origin:
            origin = str(spec.origin).lower()
            if "site-packages" in origin or "dist-packages" in origin:
                third_party.append(name)

    for name in third_party:
        print("    -", name)
    if not third_party:
        print("    (aucune)")
    return third_party

def check_pyinstaller():
    print("\n=== 6. PYINSTALLER ===")
    ensure_package("PyInstaller", "pyinstaller")
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        capture_output=True, text=True, check=True,
    )
    print("[OK] PyInstaller :", r.stdout.strip())

def build_exe(third_party):
    print("\n=== 7. BUILD ONEFILE ===")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build", ignore_errors=True)
    spec = ROOT / f"{APP_NAME}.spec"
    if spec.exists():
        try:
            spec.unlink()
        except PermissionError:
            fail(f"{spec.name} est verrouillé.")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--onefile", "--windowed",
        f"--name={APP_NAME}",
        f"--icon={ICO}",
        f"--add-data={PAYLOAD}{os.pathsep}.",
        "--hidden-import=flask",
        "--hidden-import=jinja2",
        "--hidden-import=werkzeug",
        "--hidden-import=dotenv",
        "--hidden-import=reportlab",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=sqlite3",
        "--collect-submodules=jinja2",
        "--collect-submodules=reportlab",
    ]

    known = {"flask","jinja2","werkzeug","dotenv","reportlab","PIL"}
    for name in third_party:
        cmd.append(f"--hidden-import={name}")
        if name not in known:
            cmd.append(f"--collect-submodules={name}")

    cmd.append(str(LAUNCHER))
    subprocess.check_call(cmd)

def final_check():
    exe = DIST_DIR / f"{APP_NAME}.exe"
    if not exe.exists():
        fail("SastoukaStore.exe n'a pas été créé.")
    size = exe.stat().st_size / (1024*1024)

    print("\n" + "="*78)
    print("SastoukaStore — BUILD INDEPENDANT TERMINE")
    print("="*78)
    print("[OK] EXE :", exe)
    print(f"[OK] Taille : {size:.1f} Mo")
    print("[OK] PyInstaller --onefile --windowed")
    print("[OK] Icône Windows intégrée")
    print("[OK] Code + templates + static embarqués")
    print("[OK] Premier lancement : SastoukaStore_DATA créé à côté de l'EXE")
    print("[OK] Aucun Python requis sur le PC client")
    print()
    print("Identifiant : SastoukaStore")
    print("Mot de passe : SastoukaStore123456")
    print("="*78)

def main():
    print("="*78)
    print("SastoukaStore — BUILD WINDOWS V2 — ONEFILE INDEPENDANT")
    print("="*78)
    print("[INFO] Projet :", ROOT)
    print("[INFO] Python :", sys.executable)
    verify_project()
    create_ico()
    build_payload()
    create_launcher()
    third_party = detect_third_party_imports()
    check_pyinstaller()
    build_exe(third_party)
    final_check()

if __name__ == "__main__":
    main()
