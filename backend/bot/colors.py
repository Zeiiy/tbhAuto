import numpy as np
import cv2


class GradeClassifier:
    """Classe la rarete d'un slot d'apres sa couleur (bordure/fond).

    On echantillonne une couronne de pixels en bord de slot (la bordure de grade
    est generalement coloree), on prend la teinte/saturation dominante, et on
    compare aux plages configurees. Renvoie le nom du grade ou 'unknown'.
    """

    def __init__(self, config):
        self.config = config

    def _border_pixels(self, slot_bgr):
        h, w = slot_bgr.shape[:2]
        b = max(2, int(min(h, w) * 0.12))   # epaisseur de la couronne
        mask = np.zeros((h, w), dtype=bool)
        mask[:b, :] = True
        mask[-b:, :] = True
        mask[:, :b] = True
        mask[:, -b:] = True
        return slot_bgr[mask]

    def classify(self, slot_bgr):
        px = self._border_pixels(slot_bgr)
        if px.size == 0:
            return "unknown"
        hsv = cv2.cvtColor(px.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
        # On ignore les pixels tres sombres (fond noir du slot vide).
        bright = hsv[hsv[:, 2] > 40]
        if bright.shape[0] < max(5, int(0.05 * hsv.shape[0])):
            return "empty"
        h_med = float(np.median(bright[:, 0]))
        s_med = float(np.median(bright[:, 1]))
        v_med = float(np.median(bright[:, 2]))

        grades = self.config.grade_colors

        # common = faible saturation (gris/blanc)
        c = grades.get("common", {})
        if s_med <= c.get("s_max", 45) and v_med >= c.get("v_min", 70):
            return "common"

        # autres grades = par teinte
        best = None
        for name, spec in grades.items():
            if name == "common" or "h" not in spec:
                continue
            h_lo, h_hi = spec["h"]
            if h_lo <= h_med <= h_hi and s_med >= spec.get("s_min", 60) and v_med >= spec.get("v_min", 60):
                best = name
                break
        return best or "unknown"

    def classify_grid(self, cell_bgr):
        """Classe une case de la GRILLE DE SYNTHESE.

        Ici le grade n'est PAS un fond colore (comme dans le stash) : pour les
        grades superieurs c'est le CADRE de la case qui est colore ; le commun a
        un cadre gris (indistinct d'une case vide au bord). On procede donc :
          1) cadre colore (saturation elevee) -> grade par teinte du cadre ;
          2) cadre gris -> on regarde le CENTRE : item clair = commun, sinon vide.
        """
        h, w = cell_bgr.shape[:2]
        grades = self.config.grade_colors

        # 1) Cadre colore ? (couronne de bord, pixels assez clairs)
        border = self._border_pixels(cell_bgr)
        bhsv = cv2.cvtColor(border.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
        bb = bhsv[bhsv[:, 2] > 55]
        if bb.shape[0] >= 8 and float(np.median(bb[:, 1])) >= 55:
            h_med = float(np.median(bb[:, 0]))
            for name, spec in grades.items():
                if name == "common" or "h" not in spec:
                    continue
                lo, hi = spec["h"]
                if lo <= h_med <= hi:
                    return name
            # rouge (immortal) : la teinte rouge s'enroule autour de 0/179.
            if h_med <= 12 or h_med >= 159:
                return "immortal"
            return "unknown"   # cadre colore non reconnu -> refus (liste blanche)

        # 2) Cadre gris -> vide ou commun, distingues par le centre.
        m, n = int(w * 0.28), int(h * 0.28)
        center = cell_bgr[n:h - n, m:w - m]
        chsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV).reshape(-1, 3)
        cb = chsv[chsv[:, 2] > 65]
        if cb.shape[0] < 0.12 * chsv.shape[0]:
            return "empty"
        return "common"

    @staticmethod
    def has_content(cell_bgr, thresh=0.10):
        """True si la case contient un item : centre suffisamment clair.

        Robuste pour l'INVENTAIRE (case vide = centre noir -> 0 ; item = icone
        claire). Independant des cadres colores (contrairement a classify_grid).
        """
        h, w = cell_bgr.shape[:2]
        m, n = int(w * 0.25), int(h * 0.25)
        c = cell_bgr[n:h - n, m:w - m]
        if c.size == 0:
            return False
        gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
        return float((gray > 70).mean()) > thresh

    def is_allowed(self, grade):
        return grade in self.config.synthesis_allowed_grades

    @staticmethod
    def cells_from_rect(rect, rows, cols):
        """Decoupe un rectangle (x,y,w,h) en centres de cellules rows x cols.
        Renvoie une liste de (cx, cy, cell_rect)."""
        x, y, w, h = rect
        cw, ch = w / cols, h / rows
        cells = []
        for r in range(rows):
            for c in range(cols):
                cx = int(x + cw * (c + 0.5))
                cy = int(y + ch * (r + 0.5))
                cr = (int(x + cw * c), int(y + ch * r), int(cw), int(ch))
                cells.append((cx, cy, cr))
        return cells
