import os
import time
import random
import threading
import datetime
import logging

from .capture import Capturer
from .detector import Detector, find_stash_tabs
from .clicker import Clicker
from .synthesis import Synthesis
from .config import Config

try:
    import ctypes
except Exception:
    ctypes = None

try:
    from pynput import keyboard as pkeyboard
except Exception:
    pkeyboard = None

try:
    from pyautogui import FailSafeException
except Exception:
    class FailSafeException(Exception):
        pass

# Constantes Windows pour empecher la veille
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


class BotEngine:
    def __init__(self, config: Config, log):
        self.config = config
        self._ext_log = log
        self.cap = Capturer(config)
        self.det = Detector(config)
        self.clicker = Clicker(config)
        self.synth = Synthesis(config, self.cap, self.det, self.clicker, self.log)

        self._thread = None
        self._stop = threading.Event()
        self._paused = False
        self._last_action = {}
        self._next_due = {}
        self._last_chest = 0.0
        self._action_count = 0
        self._idle_cycles = 0
        self._started_at = None

        self.features = dict(config.features_default)
        self.counters = {"auto_synthesis": 0, "auto_chest": 0, "auto_ranger": 0}

        self._file_logger = None
        self._hotkey_listener = None

    # ---------------- logging ----------------
    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        if self._file_logger:
            self._file_logger.info(msg)
        self._ext_log(line)

    def _setup_file_logger(self):
        os.makedirs(self.config.logs_dir, exist_ok=True)
        fname = datetime.datetime.now().strftime("run_%Y%m%d_%H%M%S.log")
        lg = logging.getLogger(f"tbh.{fname}")
        lg.setLevel(logging.INFO)
        h = logging.FileHandler(os.path.join(self.config.logs_dir, fname), encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
        lg.addHandler(h)
        self._file_logger = lg

    # ---------------- control ----------------
    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def set_feature(self, name, enabled):
        if name in self.features:
            self.features[name] = bool(enabled)
            self.log(f"{name} -> {'ON' if enabled else 'OFF'}")

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self.running:
            self._stop.set()
            self.log("Arret demande...")

    # ---------------- hotkey / awake ----------------
    def _install_hotkey(self):
        if pkeyboard is None:
            return
        try:
            self._hotkey_listener = pkeyboard.GlobalHotKeys(
                {"<ctrl>+<alt>+k": self.stop})
            self._hotkey_listener.start()
        except Exception as e:
            self.log(f"Hotkey indisponible: {e}")

    def _set_awake(self, on):
        if ctypes is None or not hasattr(ctypes, "windll"):
            return
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else 0)
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            pass

    # ---------------- guards ----------------
    def _should_act(self):
        """Renvoie (ok, raison) selon fenetre/foreground/frame noire."""
        cfg = self.config
        win = self.cap.get_window()
        if win is None and cfg.window_title:
            return False, "fenetre du jeu introuvable"
        # Plus de pause sur redimensionnement : l'auto-calibrage par echelle
        # (cap.scale()) adapte geometrie et templates a la taille courante.
        if cfg.require_window_foreground and not self.cap.is_foreground():
            return False, "jeu pas au premier plan"
        return True, ""

    def _set_clicker_region(self):
        region = self.cap._resolve_region()
        self.clicker.set_region(region["left"], region["top"],
                                region["width"], region["height"])

    def _maybe_micro_pause(self):
        cfg = self.config
        if cfg.micro_pause_every and self._action_count and \
                self._action_count % cfg.micro_pause_every == 0:
            p = random.uniform(*cfg.micro_pause_range)
            self.log(f"micro-pause {p:.1f}s")
            time.sleep(p)

    def _jittered_interval(self):
        cfg = self.config
        j = cfg.scan_interval * cfg.scan_interval_jitter
        return max(0.1, cfg.scan_interval + random.uniform(-j, j))

    # ---------------- features ----------------
    def _schedule(self, action):
        """Reprogramme la prochaine occurrence d'une action a un instant aleatoire."""
        cfg = self.config
        if action == "tout_ranger":
            lo, hi = cfg.tout_ranger_interval_range
        else:
            lo, hi = cfg.action_interval_ranges.get(action, (120.0, 300.0))
        self._next_due[action] = time.time() + random.uniform(lo, hi)

    def _inventory_has_items(self):
        """True si l'inventaire (source de 'Tout Ranger') contient au moins un item."""
        cfg = self.config
        if not cfg.inventory_grid_rect:
            return True   # non calibre -> on suppose qu'il y en a (defaut)
        frame, _, _ = self.cap.grab()
        sx, sy = self.cap.scale()
        r = cfg.inventory_grid_rect
        rect = (r[0] * sx, r[1] * sy, r[2] * sx, r[3] * sy)
        g = self.synth.grader
        for _, _, (x, y, w, h) in g.cells_from_rect(rect, cfg.inventory_grid_rows,
                                                    cfg.inventory_grid_cols):
            if g.has_content(frame[y:y + h, x:x + w]):
                return True
        return False

    def _stash_tab_points(self, frame, sx, sy):
        """Centres (coords frame) des onglets de page du stash.

        DETECTES dynamiquement par couleur (cf. find_stash_tabs) : marche quel que
        soit le NOMBRE d'onglets (2, 6, 7...) sur n'importe quel compte, sans
        calibration. La BANDE de recherche est DERIVEE de stash_grid_rect (juste
        au-dessus du quadrillage) -> suit l'echelle. Repli sur les coords calibrees
        (stash_page_tabs) si la detection ne trouve rien (stash ferme p.ex.).
        """
        r = self.config.stash_grid_rect
        if r:
            gx, gy, gw, gh = r
            # bande centree sur la rangee d'onglets (centre ~ gy-57, hauteur ~45) :
            band = ((gx - 20) * sx, (gy - 80) * sy, (gw + 40) * sx, 45 * sy)
            pts = find_stash_tabs(frame, band)
            if pts:
                return pts, True
        # repli : anciennes coords calibrees, mises a l'echelle.
        pts = [(int(t[0] * sx), int(t[1] * sy)) for t in (self.config.stash_page_tabs or [])]
        return pts, False

    def _do_tout_ranger(self):
        """Range l'inventaire dans le stash, page par page, tant qu'il reste des items.

        1) inventaire vide -> rien a faire ;
        2) sinon, pour chaque onglet de page DETECTE : clique l'onglet puis
           'Tout Ranger', RE-VERIFIE l'inventaire ; des qu'il est vide, on s'arrete.
        Le nombre de pages s'adapte tout seul au stash (detection) ; ranger_pages
        ne sert que de PLAFOND optionnel (0 = toutes les pages detectees).
        """
        if not self._inventory_has_items():
            self.log("[ranger] inventaire vide -> rien a ranger")
            return False
        sx, sy = self.cap.scale()
        frame, ox, oy = self.cap.grab()
        targets, detected = self._stash_tab_points(frame, sx, sy)
        if detected:
            self.log(f"[ranger] {len(targets)} onglet(s) detecte(s)")
        elif targets:
            self.log("[ranger] onglets non detectes -> repli coords calibrees")
        cap_n = int(self.config.ranger_pages)
        if cap_n > 0:
            targets = targets[:cap_n]
        targets = targets or [None]   # [None] = onglets inconnus -> ranger page courante
        pages_done = 0
        for tab in targets:
            if self._stop.is_set():
                break
            frame, ox, oy = self.cap.grab()
            if tab is not None:
                self.clicker.click(ox + tab[0], oy + tab[1], radius=14)
                time.sleep(0.4)
                frame, ox, oy = self.cap.grab()
            m = self.det.find(frame, "tout_ranger")
            if m is None:
                continue
            rad = int(min(m[3], m[4]) * 0.3)
            self.clicker.click(ox + m[0], oy + m[1], radius=rad)
            time.sleep(0.5)
            pages_done += 1
            if not self._inventory_has_items():     # tout est range -> stop
                self.log("[ranger] inventaire vide -> stop")
                break
        if pages_done:
            self._action_count += 1
            self.counters["auto_ranger"] += 1
            self.log(f"Tout Ranger : {pages_done} page(s)")
            return True
        self.log("[ranger] bouton 'Tout Ranger' introuvable")
        return False

    def _do_auto_chest(self):
        frame, ox, oy = self.cap.grab()
        hits = self.det.find_all(frame, "auto_chest")
        if not hits:
            return False
        h0 = hits[0]
        rad = int(min(h0[3], h0[4]) * 0.3)
        self.clicker.click(ox + h0[0], oy + h0[1], radius=rad)
        self.counters["auto_chest"] += 1
        self._action_count += 1
        self.log(f"coffre ouvert ({self.counters['auto_chest']})")
        return True

    def _do_auto_synthesis(self):
        # La cadence est geree par l'intervalle aleatoire (action_interval_ranges),
        # plus besoin de back-off : un cycle infructueux attend juste le prochain.
        if self.synth.run_cycle() == "fused":
            self.counters["auto_synthesis"] += 1
            self._action_count += 1
            return True
        return False

    def _sleep_interruptible(self, seconds):
        end = time.time() + seconds
        while time.time() < end and not self._stop.is_set():
            time.sleep(0.5)

    # ---------------- main loop ----------------
    def _run(self):
        cfg = self.config
        self._setup_file_logger()
        self.log("Bot demarre")
        self._started_at = time.time()
        self._action_count = 0
        self._idle_cycles = 0
        # 1ere occurrence rapide (et un peu aleatoire) ; ensuite chaque action se
        # reprogramme sur sa plage [min,max]. Tout Ranger demarre un peu plus tard.
        now = self._started_at
        self._last_chest = 0.0
        self._next_due = {
            "auto_synthesis": now + random.uniform(3, 15),
            "tout_ranger": now + random.uniform(20, 60),
        }
        self.det.load()
        sx, sy = self.cap.scale()
        if abs(sx - 1) > 0.02 or abs(sy - 1) > 0.02:
            self.log(f"Auto-calibrage : echelle x{sx:.2f} y{sy:.2f} "
                     f"(fenetre != taille de reference)")
        self._install_hotkey()
        if cfg.keep_awake:
            self._set_awake(True)

        try:
            while not self._stop.is_set():
                # garde-fou duree max
                if cfg.max_runtime_minutes and \
                        (time.time() - self._started_at) > cfg.max_runtime_minutes * 60:
                    self.log("duree max atteinte -> arret")
                    break

                try:
                    ok, reason = self._should_act()
                    if not ok:
                        if not self._paused:
                            self.log(f"PAUSE: {reason}")
                            self._paused = True
                        self._sleep_interruptible(2.0)
                        continue
                    if self._paused:
                        self.log("REPRISE")
                        self._paused = False

                    self._set_clicker_region()
                    # Auto-calibrage : echelle templates a la taille de fenetre courante.
                    sx, sy = self.cap.scale()
                    self.det.scale = (sx + sy) / 2.0
                    frame, _, _ = self.cap.grab()
                    if Capturer.is_black(frame, cfg.black_frame_value_threshold):
                        self.log("frame noire -> attente")
                        self._sleep_interruptible(2.0)
                        continue

                    now = time.time()
                    # auto_chest : SCRUTE EN CONTINU (le coffre n'apparait que ~5s),
                    # clique des qu'il est detecte, avec un cooldown anti double-clic.
                    if self.features.get("auto_chest") and \
                            now - self._last_chest >= cfg.chest_click_cooldown_s:
                        if self._do_auto_chest():
                            self._last_chest = time.time()
                            self._maybe_micro_pause()

                    # Auto Ranger (range le stash, sur sa propre cadence)
                    if self.features.get("auto_ranger") and \
                            now >= self._next_due.get("tout_ranger", float("inf")):
                        self._do_tout_ranger()
                        self._schedule("tout_ranger")

                    # auto_synthesis (cadence aleatoire 2-5 min)
                    if self.features.get("auto_synthesis") and now >= self._next_due.get("auto_synthesis", 0):
                        self._do_auto_synthesis()
                        self._schedule("auto_synthesis")
                        self._maybe_micro_pause()

                    self._sleep_interruptible(self._jittered_interval())
                except FailSafeException:
                    raise  # failsafe = arret volontaire, on remonte
                except Exception as e:
                    # une erreur ponctuelle ne doit pas tuer le run nocturne :
                    # on logge, on souffle, et on continue.
                    self.log(f"Erreur (cycle ignore): {e}")
                    self._sleep_interruptible(2.0)
        except FailSafeException as e:
            self.log(f"FAILSAFE declenche: {e}")
        except Exception as e:
            self.log(f"Erreur boucle: {e}")
        finally:
            if cfg.keep_awake:
                self._set_awake(False)
            if self._hotkey_listener:
                try:
                    self._hotkey_listener.stop()
                except Exception:
                    pass
            self.log("Bot arrete")
