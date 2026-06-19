"""Mise a jour automatique de l'app via GitHub Releases.

Au demarrage, l'app interroge la derniere release publique du depot ; si une
version plus recente existe, l'UI affiche un bouton pour l'installer. L'install
telecharge le nouvel exe et le met en place via un petit script relais (un exe ne
peut pas s'ecraser lui-meme tant qu'il tourne), puis relance l'app.

Ne fonctionne qu'en mode "frozen" (exe PyInstaller). En dev, check_for_update
renvoie quand meme la version dispo mais l'installation est desactivee.
"""
import os
import re
import sys
import json
import tempfile
import subprocess
import urllib.request

GITHUB_OWNER = "Zeiiy"
GITHUB_REPO = "tbhAuto"
API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
ASSET_NAME = "TBHBot.exe"


def _parse_version(s):
    """'v1.2.3' -> (1, 2, 3). Tuple vide -> (0,)."""
    nums = re.findall(r"\d+", s or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_frozen():
    return getattr(sys, "frozen", False)


def current_exe():
    return sys.executable if is_frozen() else os.path.abspath(sys.argv[0])


def check_for_update(current_version, timeout=6):
    """dict(version,url,notes,name) si une release PLUS RECENTE existe, sinon None.

    None aussi sur erreur reseau / pas de release / pas d'asset .exe.
    """
    try:
        req = urllib.request.Request(API_LATEST, headers={
            "User-Agent": "TBHBot-Updater",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception:
        return None
    tag = data.get("tag_name") or ""
    if _parse_version(tag) <= _parse_version(current_version):
        return None
    url = None
    for a in data.get("assets", []):
        if a.get("name", "").lower() == ASSET_NAME.lower():
            url = a.get("browser_download_url")
            break
    if not url:
        return None
    return {"version": tag.lstrip("vV"), "url": url,
            "notes": (data.get("body") or "").strip(),
            "name": data.get("name") or tag}


def download(url, dest, progress_cb=None, timeout=30):
    """Telecharge url -> dest. progress_cb(recu, total) optionnel. Renvoie dest."""
    req = urllib.request.Request(url, headers={"User-Agent": "TBHBot-Updater"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if progress_cb:
                    progress_cb(got, total)
    return dest


def stage_replace(new_exe):
    """Programme le remplacement de l'exe courant par new_exe APRES la fermeture de
    l'app, via un .bat relais detache. L'app doit quitter juste apres (le .bat boucle
    sur 'move' jusqu'a ce que l'exe soit libere), puis le .bat se supprime.

    NE relance PAS l'app : relancer un exe onefile juste apres l'avoir reecrit echoue
    de facon intermittente ('failed to load Python DLL' / 'module introuvable') car le
    bootloader extrait python3xx.dll pendant que l'antivirus scanne encore le fichier
    fraichement ecrit. Le lancement MANUEL (l'utilisateur rouvre l'exe) est fiable a
    100% car le scan AV est alors termine. On privilegie donc la fiabilite.
    """
    cur = current_exe()
    bat = os.path.join(tempfile.gettempdir(), "tbhbot_update.bat")
    script = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set TRIES=0\r\n"
        ":retry\r\n"
        f'move /y "{new_exe}" "{cur}" >nul 2>&1\r\n'
        "if not errorlevel 1 goto fin\r\n"
        "set /a TRIES+=1\r\n"
        "if %TRIES% geq 120 goto fin\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        "goto retry\r\n"
        ":fin\r\n"
        'del "%~f0"\r\n'
    )
    with open(bat, "w", encoding="ascii") as f:
        f.write(script)
    DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["cmd", "/c", bat], creationflags=DETACHED, close_fds=True)
