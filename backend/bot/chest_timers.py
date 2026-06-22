"""Suivi des cooldowns de coffres a partir du player.log.

Encapsule le LogWatcher + l'etat (cooldowns par type, dernier coffre vu) et expose
un instantane lisible cote UI. Partage par la fenetre Assistant ET l'overlay : ne
touche JAMAIS souris/jeu, c'est de la pure lecture du log.
"""
import time
import queue

from .log_watch import LogWatcher, classify_chest_key

# (cle interne, libelle court) — ordre d'affichage
CHEST_KINDS = ("elite", "normal")


class ChestTimers:
    def __init__(self, config):
        self.config = config
        self._events = queue.Queue()
        self.cooldown_end = {"normal": 0.0, "elite": 0.0}   # 0 = jamais vu
        self.last_seen = {"normal": 0.0, "elite": 0.0}
        self.last_box = None                                 # (item_key, ts)
        self.watcher = LogWatcher(config, on_box=self._on_box)

    def start(self):
        self.watcher.start()

    def stop(self):
        try:
            self.watcher.stop()
        except Exception:
            pass

    # callback dans le thread du watcher -> queue, drainee cote Tk (thread-safe)
    def _on_box(self, key, count, ts):
        self._events.put((key, ts))

    def drain(self):
        """A appeler dans la boucle Tk avant de lire l'etat (applique les events)."""
        try:
            while True:
                key, ts = self._events.get_nowait()
                self._ingest(key, ts)
        except queue.Empty:
            pass

    def _ingest(self, key, ts):
        self.last_box = (key, ts)
        ctype = classify_chest_key(self.config, key)
        if ctype in self.cooldown_end:
            cd = float(self.config.chest_cooldowns_s.get(ctype, 300.0))
            self.cooldown_end[ctype] = ts + cd
            self.last_seen[ctype] = ts

    def mapped_types(self):
        return (set(self.config.chest_key_prefixes.values())
                | set(self.config.chest_key_map.values()))

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
