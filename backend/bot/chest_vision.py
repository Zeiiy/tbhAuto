"""Veilleur VISION des coffres pour les timers de l'Assistant (independant du bot).

Surveille EN DIRECT l'ecran du jeu (capture read-only) et detecte l'APPARITION
d'un coffre a l'ecran : auto_chest_1 -> normal, auto_chest_2 -> elite. A chaque
NOUVELLE apparition d'un type, appelle on_chest(ctype:str, ts:float). NE CLIQUE
JAMAIS, ne touche ni souris ni jeu : pure surveillance.

POURQUOI la vision et plus le log : jusqu'a la maj du jeu de juin 2026, l'Assistant
lisait player.log ("GetBoxCount Success Count : N // ItemKey : KEY") qui donnait le
moment ET le type du loot. La maj a SUPPRIME cette ligne (verifie : 0 occurrence dans
le Player.log de 294 Mo ; aucune cle 91xxxx/92xxxx ; seul reste un signal obfusque
sans type). La vision redonne les deux via les memes templates que l'Auto Coffre.

SEMANTIQUE : le timer repart a l'APPARITION du coffre (pas au clic). Un coffre
n'apparait que lorsque son cooldown est ecoule (il devient obtenable), donc
l'apparition est le bon top de depart du compte a rebours du prochain. Quand l'Auto
Coffre tourne, le clic suit l'apparition de <1 s -> apparition ~= loot. Quand le bot
est arrete, on n'a de toute facon rien a clic-er : l'apparition reste l'info utile.
"""
import time
import threading

from .capture import Capturer
from .detector import Detector

# basename du template (tel que stocke par Detector) -> type de coffre
CHEST_TEMPLATES = {
    "auto_chest_1.png": "normal",
    "auto_chest_2.png": "elite",
}


class ChestVisionWatcher:
    """Boucle de capture dediee (thread daemon) qui detecte l'apparition des coffres.

    Robuste : si la fenetre du jeu est absente / minimisee / l'ecran noir, on ne
    detecte rien (pas de faux positif) et on reessaie sans crasher. Detection de
    FRONT MONTANT par type avec re-armement (chest_vision_rearm_s) pour ne loguer
    qu'UNE fois par apparition malgre les ~5 s de presence a l'ecran et un eventuel
    scintillement du score de matching."""

    def __init__(self, config, on_chest, log=None):
        self.config = config
        self.on_chest = on_chest
        self._log = log or (lambda m: None)
        self.cap = Capturer(config)
        self.det = Detector(config)
        self.det.load()
        self._thread = None
        self._stop = threading.Event()
        self.status = "init"
        self.last_event = None       # (ctype, ts) du dernier coffre vu

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
        # Poll RAPIDE : quand l'Auto Coffre tourne, le coffre n'est visible que ~0.9 s
        # (le bot clique des qu'il le voit). Un poll <= 0.4 s garantit >=2 regards dans
        # cette fenetre -> on ne rate pas l'apparition.
        poll = max(0.25, float(getattr(self.config, "chest_vision_poll_s", 0.4)))
        # absence requise (s) avant de re-compter une apparition d'un meme type :
        # > a la duree de presence/scintillement, << au plus petit cooldown (300 s).
        rearm = max(2.0, float(getattr(self.config, "chest_vision_rearm_s", 8.0)))
        last_seen_present = {"normal": 0.0, "elite": 0.0}
        while not self._stop.is_set():
            try:
                if self.cap.get_window() is None:
                    self.status = "jeu introuvable"
                    self._stop.wait(1.5)
                    continue
                # auto-echelle des templates (comme l'engine, suit le redimensionnement)
                sx, sy = self.cap.scale()
                self.det.scale = (sx + sy) / 2.0
                frame, _ox, _oy = self.cap.grab()
                if Capturer.is_black(frame, self.config.black_frame_value_threshold):
                    self.status = "ecran noir"
                    self._stop.wait(poll)
                    continue

                found = self.det.find_each(frame, "auto_chest")
                now = time.time()
                present = {"normal": False, "elite": False}
                for name, ctype in CHEST_TEMPLATES.items():
                    if name in found:
                        present[ctype] = True

                for ctype in ("normal", "elite"):
                    if not present[ctype]:
                        continue
                    # front montant = ce type n'a pas ete vu depuis >= rearm
                    if now - last_seen_present[ctype] >= rearm:
                        self.last_event = (ctype, now)
                        try:
                            self.on_chest(ctype, now)
                        except Exception:
                            pass
                        self._log(f"[vision] coffre {ctype} apparu a l'ecran")
                    last_seen_present[ctype] = now

                self.status = "ok"
                self._stop.wait(poll)
            except Exception as e:
                self.status = f"err: {e}"
                self._stop.wait(1.5)
