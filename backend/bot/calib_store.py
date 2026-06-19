"""Persistance + rendu de la calibration pour l'edition depuis l'app.

La calibration "source de verite" reste les valeurs par defaut de config.py ;
si un fichier calibration.json existe a cote de main.py, il les SURCHARGE
(ecrit par l'UI). On peut ainsi recalibrer sans toucher au code.
"""
import os
import sys
import json

import cv2
import numpy as np

from .colors import GradeClassifier

# calibration.json doit etre PERSISTANT et MODIFIABLE :
#  - exe PyInstaller (onefile) -> a cote de l'exe (pas dans _MEIPASS temporaire) ;
#  - dev -> dossier backend/.
if getattr(sys, "frozen", False):
    _base = os.path.dirname(sys.executable)
else:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIB_FILE = os.path.join(_base, "calibration.json")

# Champs de Config persistes = GEOMETRIE seulement. Les couleurs de grade
# (grade_colors) restent dans config.py (source de verite, non editables dans
# l'UI) : les persister ferait qu'un vieux calibration.json masque les corrections
# de code. Donc on ne les sauvegarde/charge PAS.
CALIB_FIELDS = [
    "calib_window_size",
    "synthesis_grid_rect", "synthesis_grid_rows", "synthesis_grid_cols",
    "stash_grid_rect", "stash_grid_rows", "stash_grid_cols",
    "stash_page_tabs",
    "inventory_grid_rect", "inventory_grid_rows", "inventory_grid_cols",
]
# Reglages d'exploitation modifiables depuis l'UI, persistes aussi.
# NB: le classement des coffres (chest_key_prefixes / chest_key_map) reste CODE-ONLY
# dans config.py (source de verite), comme grade_colors : pas persiste, pour qu'un
# vieux calibration.json ne masque pas les corrections de code.
SETTINGS_FIELDS = [
    "action_interval_ranges", "tout_ranger_interval_range",
    "ranger_pages", "synthesis_allowed_grades",
]
PERSIST_FIELDS = CALIB_FIELDS + SETTINGS_FIELDS

_LABELS = {"common": "GRY", "uncommon": "GRN", "rare": "BLU",
           "legendary": "PUR", "immortal": "ORG", "empty": ".", "unknown": "?"}
# Couleurs BGR (OpenCV) pour annoter chaque grade.
_COLORS = {"common": (200, 200, 200), "uncommon": (80, 220, 80), "rare": (230, 160, 40),
           "legendary": (200, 80, 200), "immortal": (40, 140, 240),
           "empty": (90, 90, 90), "unknown": (60, 60, 200)}


def to_dict(config):
    """Extrait calibration + reglages d'une Config -> dict JSON-serialisable."""
    return {k: getattr(config, k) for k in PERSIST_FIELDS}


def apply_dict(config, data):
    """Applique un dict (calibration + reglages) sur une Config (en place).

    Normalise les listes JSON en tuples la ou config.py attend des tuples.
    """
    for k in PERSIST_FIELDS:
        if k not in data or data[k] is None:
            continue
        v = data[k]
        if k in ("calib_window_size", "synthesis_grid_rect", "stash_grid_rect",
                 "inventory_grid_rect", "tout_ranger_interval_range"):
            v = tuple(v)
        elif k == "stash_page_tabs":
            v = [(int(a), int(b)) for a, b in v]
        elif k in ("synthesis_grid_rows", "synthesis_grid_cols",
                   "stash_grid_rows", "stash_grid_cols",
                   "inventory_grid_rows", "inventory_grid_cols"):
            v = int(v)
        elif k == "ranger_pages":
            v = int(v)
        elif k == "synthesis_allowed_grades":
            v = list(v)
        elif k == "action_interval_ranges":
            v = {kk: tuple(vv) for kk, vv in v.items()}
        # grade_colors : laisse le dict tel quel (les listes "h" marchent comme des tuples)
        setattr(config, k, v)


def load_into(config):
    """Charge calibration.json (s'il existe) dans la Config. Renvoie True si charge."""
    if not os.path.exists(CALIB_FILE):
        return False
    with open(CALIB_FILE, "r", encoding="utf-8") as f:
        apply_dict(config, json.load(f))
    return True


def save(config):
    """Ecrit la calibration courante dans calibration.json."""
    with open(CALIB_FILE, "w", encoding="utf-8") as f:
        json.dump(to_dict(config), f, indent=2)


def sample_hsv(frame, x, y, r=6):
    """HSV median d'un petit patch autour de (x,y) dans la frame (coords capture)."""
    h, w = frame.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return None
    patch = frame[max(0, y - r):y + r, max(0, x - r):x + r]
    if patch.size == 0:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    med = np.median(hsv, axis=0)
    return {"h": int(med[0]), "s": int(med[1]), "v": int(med[2])}


def render_overlay(config, frame):
    """Dessine grilles + onglets + grade detecte par cellule sur une copie de la frame.

    Applique l'echelle (auto-calibrage) deduite de la taille de la frame vs la
    taille calibree, pour que l'apercu colle a ce que fait reellement le bot.
    """
    img = frame.copy()
    g = GradeClassifier(config)
    H, W = frame.shape[:2]
    cw = config.calib_window_size
    sx = W / cw[0] if cw and cw[0] else 1.0
    sy = H / cw[1] if cw and cw[1] else 1.0

    def draw_grid(rect, rows, cols, grid_mode):
        if not rect:
            return
        rect = (rect[0] * sx, rect[1] * sy, rect[2] * sx, rect[3] * sy)
        x, y, w, h = (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 2)
        for cx, cy, (rx, ry, rw, rh) in GradeClassifier.cells_from_rect(rect, rows, cols):
            cell = frame[ry:ry + rh, rx:rx + rw]
            grd = g.classify_grid(cell) if grid_mode else g.classify(cell)
            col = _COLORS.get(grd, (255, 255, 255))
            cv2.rectangle(img, (rx, ry), (rx + rw, ry + rh), col, 1)
            lab = _LABELS.get(grd, "?")
            cv2.putText(img, lab, (rx + 3, cy + 4), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 3)
            cv2.putText(img, lab, (rx + 3, cy + 4), cv2.FONT_HERSHEY_PLAIN, 0.9, col, 1)

    draw_grid(config.synthesis_grid_rect, config.synthesis_grid_rows, config.synthesis_grid_cols, True)
    draw_grid(config.stash_grid_rect, config.stash_grid_rows, config.stash_grid_cols, False)
    for i, (tx, ty) in enumerate(config.stash_page_tabs or []):
        tx, ty = int(tx * sx), int(ty * sy)
        cv2.drawMarker(img, (tx, ty), (255, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.putText(img, str(i + 1), (tx - 5, ty - 12), cv2.FONT_HERSHEY_PLAIN, 1.1, (255, 0, 255), 2)
    return img
