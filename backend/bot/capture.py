import threading

import mss
import numpy as np
import cv2

try:
    import pygetwindow as gw
except Exception:
    gw = None


class Capturer:
    """Capture une region de l'ecran -> image OpenCV BGR.

    grab() renvoie (frame_bgr, offset_x, offset_y). L'offset = position absolue
    du coin haut-gauche, pour reconvertir des coords detectees en coords ecran.
    """

    def __init__(self, config):
        self.config = config
        # mss n'est PAS thread-safe : il faut une instance par thread (l'UI capture
        # dans le thread principal, le bot dans son thread worker) -> thread-local.
        self._local = threading.local()

    def _sct(self):
        s = getattr(self._local, "sct", None)
        if s is None:
            s = mss.mss()
            self._local.sct = s
        return s

    def get_window(self):
        """Renvoie l'objet fenetre du jeu (ou None).

        Le match de titre pygetwindow est insensible a la casse et par
        sous-chaine : un Explorateur ouvert sur le dossier du jeu matche aussi.
        On filtre donc les fenetres minimisees / hors-ecran et on garde la
        plus grande fenetre visible.
        """
        cfg = self.config
        if cfg.window_title and gw is not None:
            wins = [
                w for w in gw.getWindowsWithTitle(cfg.window_title)
                if w.visible and not w.isMinimized
                and w.left > -10000 and w.top > -10000
                and w.width > 0 and w.height > 0
            ]
            if wins:
                return max(wins, key=lambda w: w.width * w.height)
        return None

    def scale(self):
        """Facteur d'echelle (sx, sy) = fenetre actuelle / taille calibree.

        Sert a adapter geometrie ET templates a une autre resolution sans
        recalibrer. (1.0, 1.0) si la fenetre fait la taille de reference ou est
        introuvable.
        """
        cfg = self.config
        win = self.get_window()
        cw = cfg.calib_window_size
        if win and cw and cw[0] and cw[1] and win.width > 0 and win.height > 0:
            return (win.width / cw[0], win.height / cw[1])
        return (1.0, 1.0)

    def is_foreground(self):
        if gw is None:
            return True
        try:
            active = gw.getActiveWindow()
            win = self.get_window()
            if active is None or win is None:
                return False
            return active._hWnd == win._hWnd
        except Exception:
            return True

    def _resolve_region(self):
        cfg = self.config
        win = self.get_window()
        if win is not None and win.width > 0 and win.height > 0:
            return {"left": win.left, "top": win.top,
                    "width": win.width, "height": win.height}
        if cfg.region:
            l, t, w, h = cfg.region
            return {"left": l, "top": t, "width": w, "height": h}
        mon = self._sct().monitors[1]
        return {"left": mon["left"], "top": mon["top"],
                "width": mon["width"], "height": mon["height"]}

    def grab(self):
        region = self._resolve_region()
        raw = self._sct().grab(region)
        frame = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR)
        return frame, region["left"], region["top"]

    @staticmethod
    def is_black(frame, threshold):
        return float(frame.mean()) < threshold
