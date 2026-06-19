import os
import glob
import cv2


class Detector:
    """Charge les templates PNG et les recherche dans une frame.

    Convention multi-templates : tous les fichiers <action>*.png comptent pour
    l'action <action> (ex: auto_chest_1.png, auto_chest_2.png -> 'auto_chest').
    """

    def __init__(self, config):
        self.config = config
        self.templates = {}  # action -> list of (img, w, h, name)
        self.scale = 1.0     # echelle appliquee aux templates (auto-calibrage)

    def _scaled(self, img, w, h):
        """Renvoie (template, largeur, hauteur) redimensionne selon self.scale."""
        s = self.scale
        if abs(s - 1.0) <= 0.02:
            return img, w, h
        nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
        return cv2.resize(img, (nw, nh)), nw, nh

    def _add(self, action, path):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            return
        h, w = img.shape[:2]
        self.templates.setdefault(action, []).append((img, w, h, os.path.basename(path)))

    def load(self):
        self.templates.clear()
        base = self.config.templates_dir
        # templates/*.png  ->  action = nom sans suffixe _N
        for path in glob.glob(os.path.join(base, "*.png")):
            name = os.path.splitext(os.path.basename(path))[0]
            action = name.rsplit("_", 1)[0] if name.rsplit("_", 1)[-1].isdigit() else name
            self._add(action, path)
        # templates/sequences/<seq>/<step>.png  ->  action = "<seq>:<step>"
        for path in glob.glob(os.path.join(base, "sequences", "*", "*.png")):
            seq = os.path.basename(os.path.dirname(path))
            step = os.path.splitext(os.path.basename(path))[0]
            self._add(f"{seq}:{step}", path)

    def has(self, action):
        return action in self.templates and len(self.templates[action]) > 0

    def find(self, frame, action):
        """Meilleure occurrence : (cx, cy, score, w, h) ou None."""
        best = None
        for img, w, h, _ in self.templates.get(action, []):
            t, tw, th = self._scaled(img, w, h)
            if tw > frame.shape[1] or th > frame.shape[0]:
                continue
            res = cv2.matchTemplate(frame, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx >= self.config.match_threshold and (best is None or mx > best[2]):
                best = (loc[0] + tw // 2, loc[1] + th // 2, float(mx), tw, th)
        return best

    def find_all(self, frame, action, dedup_dist=18):
        """Toutes les occurrences au-dessus du seuil, dedupliquees."""
        import numpy as np
        hits = []
        for img, w, h, _ in self.templates.get(action, []):
            t, tw, th = self._scaled(img, w, h)
            if tw > frame.shape[1] or th > frame.shape[0]:
                continue
            res = cv2.matchTemplate(frame, t, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= self.config.match_threshold)
            for x, y in zip(xs, ys):
                hits.append((int(x + tw // 2), int(y + th // 2), float(res[y, x]), tw, th))
        hits.sort(key=lambda t: -t[2])
        kept = []
        for cx, cy, sc, tw, th in hits:
            if all(abs(cx - kx) > dedup_dist or abs(cy - ky) > dedup_dist for kx, ky, *_ in kept):
                kept.append((cx, cy, sc, tw, th))
        return kept
