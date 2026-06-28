import os
import glob
import cv2
import numpy as np


def find_stash_tabs(frame, band_rect, rb_min=25, r_min=60):
    """Detecte DYNAMIQUEMENT les onglets de page du stash (sans calibration du
    nombre d'onglets).

    Les onglets sont des icones de COFFRE brun/orange, regulierement espacees,
    dans 'band_rect' (x,y,w,h en coords frame : la bande juste au-dessus du
    quadrillage du stash). On les repere par leur COULEUR (R nettement > B), donc
    ca marche quel que soit le NOMBRE d'onglets (2, 6, 7...) et l'echelle, sur
    n'importe quel compte. Renvoie les centres (cx, cy) en coords frame, tries de
    gauche a droite. [] si rien (stash ferme / bande hors champ).
    """
    x, y, w, h = (int(round(v)) for v in band_rect)
    H, W = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return []
    sub = frame[y0:y1, x0:x1].astype(np.int16)
    bb, gg, rr = sub[..., 0], sub[..., 1], sub[..., 2]
    brown = ((rr - bb) > rb_min) & (rr > r_min)      # coffres brun/orange
    col = brown.sum(axis=0)                           # profil horizontal (par colonne)
    bh = y1 - y0
    if col.max() < max(4, 0.12 * bh):
        return []
    thr = max(4.0, 0.12 * bh)                         # colonne suffisamment "brune"
    on = col > thr
    bw = x1 - x0
    min_w = max(8, int(0.04 * bw))                    # largeur mini d'un onglet (anti-bruit)
    max_w = max(min_w + 1, int(0.30 * bw))            # au-dela = panneau brun pleine
    #                                                   largeur (ex parchemin "Chasseur"),
    #                                                   PAS un onglet -> ignore.
    centers, i, n = [], 0, len(on)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            if min_w <= j - i <= max_w:
                centers.append((x0 + (i + j) // 2, y0 + bh // 2))
            i = j
        else:
            i += 1
    return centers


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

    def find_each(self, frame, action):
        """Meilleure occurrence PAR template de l'action : {name: (cx,cy,score,w,h)}.

        find()/find_all() fusionnent toutes les variantes d'une action (ex.
        auto_chest_1 + auto_chest_2 -> action "auto_chest") et perdent QUEL template
        a matche. find_each garde le nom de fichier (ex. "auto_chest_1.png") en cle,
        ce qui permet de distinguer le coffre normal (auto_chest_1) de l'elite
        (auto_chest_2). Seuls les templates au-dessus du seuil apparaissent."""
        out = {}
        for img, w, h, name in self.templates.get(action, []):
            t, tw, th = self._scaled(img, w, h)
            if tw > frame.shape[1] or th > frame.shape[0]:
                continue
            res = cv2.matchTemplate(frame, t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx >= self.config.match_threshold:
                prev = out.get(name)
                if prev is None or mx > prev[2]:
                    out[name] = (loc[0] + tw // 2, loc[1] + th // 2, float(mx), tw, th)
        return out

    def find_all(self, frame, action, dedup_dist=18):
        """Toutes les occurrences au-dessus du seuil, dedupliquees."""
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
