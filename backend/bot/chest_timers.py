"""Suivi des cooldowns de coffres a partir de la VISION (apparition a l'ecran).

Encapsule le ChestVisionWatcher + l'etat (cooldowns par type, dernier coffre vu) et
expose un instantane lisible cote UI. Partage par la fenetre Assistant ET l'overlay :
ne touche JAMAIS souris/jeu, c'est de la pure surveillance.

NB : la source etait le player.log ("GetBoxCount ... ItemKey") jusqu'a ce qu'une maj
du jeu (juin 2026) supprime cette ligne. On detecte desormais l'apparition du coffre
a l'ecran (templates auto_chest_1=normal / auto_chest_2=elite) — cf. chest_vision.py.
"""
import time
import queue

from .chest_vision import ChestVisionWatcher, CHEST_TEMPLATES

# (cle interne, libelle court) — ordre d'affichage
CHEST_KINDS = ("elite", "normal")
# types geres par la vision (toujours normal + elite tant que les templates existent)
KNOWN_TYPES = set(CHEST_TEMPLATES.values())


class ChestTimers:
    def __init__(self, config):
        self.config = config
        self._events = queue.Queue()
        self.cooldown_end = {"normal": 0.0, "elite": 0.0}   # 0 = jamais vu
        self.last_seen = {"normal": 0.0, "elite": 0.0}
        self.last_box = None                                 # (ctype, ts)
        self.watcher = ChestVisionWatcher(config, on_chest=self._on_chest)

    def start(self):
        self.watcher.start()

    def stop(self):
        try:
            self.watcher.stop()
        except Exception:
            pass

    # callback dans le thread du watcher -> queue, drainee cote Tk (thread-safe)
    def _on_chest(self, ctype, ts):
        self._events.put((ctype, ts))

    def drain(self):
        """A appeler dans la boucle Tk avant de lire l'etat (applique les events)."""
        try:
            while True:
                ctype, ts = self._events.get_nowait()
                self._ingest(ctype, ts)
        except queue.Empty:
            pass

    def _ingest(self, ctype, ts):
        self.last_box = (ctype, ts)
        if ctype in self.cooldown_end:
            cd = float(self.config.chest_cooldowns_s.get(ctype, 300.0))
            self.cooldown_end[ctype] = ts + cd
            self.last_seen[ctype] = ts

    def mapped_types(self):
        return set(KNOWN_TYPES)

    def state(self, ctype, now=None):
        """Renvoie (etat, restant_s, total_s).

        etat : 'unset' (type non configure), 'idle' (jamais vu), 'cooldown', 'ready'.
        """
        now = time.time() if now is None else now
        total = float(self.config.chest_cooldowns_s.get(ctype, 300.0))
        if ctype not in self.mapped_types():
            return ("unset", 0.0, total)
        end = self.cooldown_end[ctype]
        if end <= 0:
            return ("idle", 0.0, total)
        rem = end - now
        return ("cooldown", rem, total) if rem > 0 else ("ready", 0.0, total)

    @property
    def status(self):
        return self.watcher.status if self.watcher else "—"
