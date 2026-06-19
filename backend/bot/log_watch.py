"""Lecture EN DIRECT du player.log de TaskBarHero (tail) pour l'Assistant personnel.

Repere les acquisitions de coffres logues par le jeu sous la forme :
    GetBoxCount Success Count : 1 // ItemKey : 910501
et appelle on_box(item_key:str, count:int, ts:float) a chaque occurrence NOUVELLE.
Ne touche a rien d'autre (ni souris, ni jeu) : c'est une simple surveillance.
"""
import os
import re
import time
import threading

# "GetBoxCount Success Count : <n> // ItemKey : <key>"
BOX_RE = re.compile(r"GetBoxCount\s+Success\s+Count\s*:\s*(\d+)\s*//\s*ItemKey\s*:\s*(\d+)")


def default_game_log_path():
    """Chemin par defaut du log Unity du jeu (AppData/LocalLow, Windows)."""
    return os.path.join(os.path.expanduser("~"), "AppData", "LocalLow",
                        "TesseractStudio", "TaskbarHero", "player.log")


def classify_chest_key(config, item_key):
    """Type de coffre ('normal'/'elite'/...) pour un ItemKey, ou None si non reconnu.

    1) surcharge EXACTE (config.chest_key_map) ; 2) sinon PREFIXE 2 chiffres
    (config.chest_key_prefixes : 91->normal, 92->elite). Le suffixe (grade du butin)
    n'importe pas : 910401/910501/910651 sont tous 'normal'.
    """
    key = str(item_key)
    exact = getattr(config, "chest_key_map", None) or {}
    if key in exact:
        return exact[key]
    prefixes = getattr(config, "chest_key_prefixes", None) or {}
    return prefixes.get(key[:2])


class LogWatcher:
    """Tail thread-safe du player.log : ne lit QUE les nouvelles lignes ecrites
    apres le demarrage (seek en fin de fichier), gere la rotation/troncature, et
    notifie chaque loot de coffre via on_box. Robuste : si le fichier est absent
    ou illisible, on reessaie sans crasher.
    """

    def __init__(self, config, on_box, log=None):
        self.config = config
        self.on_box = on_box
        self._log = log or (lambda m: None)
        self.path = getattr(config, "game_log_path", None) or default_game_log_path()
        self._thread = None
        self._stop = threading.Event()
        self.status = "init"
        self.last_event = None   # (item_key, ts)

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        # Lecture BINAIRE avec seek explicite a un offset suivi (pos) : en lecture
        # cross-process (le jeu garde player.log ouvert et y ecrit), un readline()
        # en mode texte ne revoit PAS les octets ajoutes apres avoir touche la fin du
        # fichier (etat EOF mis en cache). Le seek(pos) a chaque passe contourne ca.
        poll = max(0.2, float(getattr(self.config, "chest_log_poll_s", 0.7)))
        f = None
        pos = 0
        buf = b""
        try:
            while not self._stop.is_set():
                try:
                    if f is None:
                        if not os.path.exists(self.path):
                            self.status = "log introuvable"
                            self._stop.wait(1.5)
                            continue
                        f = open(self.path, "rb")
                        f.seek(0, os.SEEK_END)   # on ignore tout l'historique
                        pos = f.tell()
                        buf = b""
                        self.status = "ok"

                    try:
                        size = os.path.getsize(self.path)
                    except OSError:
                        size = pos
                    if size < pos:           # troncature/rotation (relance du jeu)
                        # le jeu a recree player.log : on rouvre et on se replace en fin
                        # (sinon on rejouerait tout l'historique du nouveau fichier).
                        try:
                            f.close()
                        except Exception:
                            pass
                        f = open(self.path, "rb")
                        f.seek(0, os.SEEK_END)
                        pos = f.tell()
                        buf = b""
                        size = pos
                    if size > pos:
                        f.seek(pos)
                        chunk = f.read(size - pos)   # uniquement le nouveau contenu
                        pos = f.tell()
                        buf += chunk
                        # garde la derniere ligne (potentiellement incomplete) pour la suite
                        *lines, buf = buf.split(b"\n")
                        for raw in lines:
                            m = BOX_RE.search(raw.decode("utf-8", "replace"))
                            if m:
                                cnt, key, ts = int(m.group(1)), m.group(2), time.time()
                                self.last_event = (key, ts)
                                try:
                                    self.on_box(key, cnt, ts)
                                except Exception:
                                    pass
                        self.status = "ok"
                    self._stop.wait(poll)
                except Exception as e:
                    self.status = f"err: {e}"
                    if f:
                        try:
                            f.close()
                        except Exception:
                            pass
                        f = None
                    self._stop.wait(1.5)
        finally:
            if f:
                try:
                    f.close()
                except Exception:
                    pass
