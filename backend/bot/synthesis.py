"""
Synthese par remplissage MANUEL controle par le grade.

Principe (puisqu'on ne peut pas bloquer les items en jeu) :
  1. Scanner le stash, classer chaque slot par grade (couleur).
  2. Pour le 1er grade autorise (common -> uncommon -> rare) qui a >= 9 items,
     clic-DROIT sur 9 de ces items -> ils vont dans la grille de synthese.
     (on traverse les pages du stash si besoin pour atteindre 9).
  3. GARDE-FOU : relire la grille ; n'EXECUTER que si les 9 slots sont d'un grade
     autorise. Sinon clic sur la fleche RETOUR pour vider la grille.
  4. Si aucun grade autorise n'a 9 items -> renvoyer "idle" (rien a faire).

Le bot ne clique JAMAIS sur du violet+ : il ne selectionne que les grades autorises.
Prerequis ecran : Stash ouvert ET Cube ouvert sur "Synthese" (vue multi-panneaux).
"""

import time

from .colors import GradeClassifier


SEQ = "synthese"  # dossier templates/sequences/synthese/


class Synthesis:
    def __init__(self, config, capturer, detector, clicker, log):
        self.config = config
        self.cap = capturer
        self.det = detector
        self.click = clicker
        self.log = log
        self.grader = GradeClassifier(config)

    # ---- helpers templates ----
    def _find(self, frame, step):
        return self.det.find(frame, f"{SEQ}:{step}")

    def _click_step(self, step, required=True, wait=0.6, left_half=False):
        frame, ox, oy = self.cap.grab()
        m = self._find(frame, step)
        if m is None:
            if required:
                self.log(f"[synth] etape '{step}' introuvable")
            return False
        cx, w, h = m[0], m[3], m[4]
        if left_half:
            # bouton avec une FLECHE/deroulant a droite -> on vise la moitie GAUCHE
            cx = m[0] - w * 0.25
            rad = int(w * 0.18)            # reste dans la moitie gauche
        else:
            rad = int(min(w, h) * 0.3)     # clic etale sur ~30% du bouton
        self.click.click(ox + cx, oy + m[1], radius=rad)
        time.sleep(wait)
        return True

    # ---- scan grille de synthese ----
    def _scan_grid(self):
        cfg = self.config
        if not cfg.synthesis_grid_rect:
            return None
        frame, _, _ = self.cap.grab()
        sx, sy = self.cap.scale()
        r = cfg.synthesis_grid_rect
        rect = (r[0] * sx, r[1] * sy, r[2] * sx, r[3] * sy)
        cells = self.grader.cells_from_rect(
            rect, cfg.synthesis_grid_rows, cfg.synthesis_grid_cols)
        grades = []
        for _, _, (x, y, w, h) in cells:
            grades.append(self.grader.classify_grid(frame[y:y+h, x:x+w]))
        return grades

    # ---- scan stash (page courante) ----
    def _scan_stash_page(self, frame, offx, offy):
        cfg = self.config
        if not cfg.stash_grid_rect:
            return []
        cells = self.grader.cells_from_rect(
            cfg.stash_grid_rect, cfg.stash_grid_rows, cfg.stash_grid_cols)
        out = []
        for cx, cy, (x, y, w, h) in cells:
            g = self.grader.classify(frame[y:y+h, x:x+w])
            out.append((offx + cx, offy + cy, g))
        return out

    def _goto_stash_page(self, idx):
        tabs = self.config.stash_page_tabs
        if 0 <= idx < len(tabs):
            tx, ty = tabs[idx]
            frame, ox, oy = self.cap.grab()
            self.click.click(ox + tx, oy + ty)
            time.sleep(0.5)

    # ---- cycle complet ----
    def run_cycle(self):
        """Renvoie 'fused' / 'idle' / 'aborted' / 'not_calibrated'.

        On laisse le JEU remplir via "Remplissage automatique" (il prend le grade
        le plus bas ayant >= 9 objets), puis on applique un VETO par couleur :
        on n'EXECUTE que si les 9 slots sont d'un grade autorise (gris/vert/bleu),
        sinon on ANNULE (RETOUR). Le bot ne choisit jamais d'item lui-meme : le
        garde-fou couleur empeche toute fusion de violet+ (ou de grille illisible).
        """
        cfg = self.config
        if not cfg.synthesis_grid_rect:
            self.log("[synth] grille de synthese non calibree -> skip")
            return "not_calibrated"

        needed = cfg.synthesis_items_needed

        # 1) Vider un eventuel residu (resultat d'une fusion precedente affiche
        #    dans un slot) AVANT de remplir. classify_grid lit une case vide
        #    'empty', donc tout slot non vide = residu a evacuer.
        residue = self._scan_grid() or []
        if any(g != "empty" for g in residue):
            self.log("[synth] residu dans la grille -> RETOUR")
            self._click_step("04_retour", required=False, wait=0.5)

        # 2) Remplissage automatique par le jeu (grade le plus bas ayant >= 9).
        #    left_half : le bouton a une fleche/deroulant a droite a eviter.
        if not self._click_step("02_remplissage", required=True, wait=0.9, left_half=True):
            return "aborted"

        # 3) Relire la grille et appliquer le VETO couleur (LISTE BLANCHE).
        grid = self._scan_grid() or []
        nonempty = [g for g in grid if g != "empty"]
        bad = [g for g in nonempty if not self.grader.is_allowed(g)]

        # 3a) Un grade non coche / inconnu present -> REFUS (rien ne fusionne).
        if bad:
            counts = {x: bad.count(x) for x in sorted(set(bad))}
            self.log(f"[synth] REFUS : grade(s) non selectionne(s)/inconnu(s) "
                     f"{counts} -> RETOUR (rien fusionne)")
            self._click_step("04_retour", required=False, wait=0.5)
            return "idle"
        # 3b) Grille pas pleine -> REFUS.
        if len(nonempty) < needed:
            self.log(f"[synth] REFUS : grille incomplete ({len(nonempty)}/{needed} "
                     f"slots) -> RETOUR")
            self._click_step("04_retour", required=False, wait=0.5)
            return "idle"
        # 3c) Les 9 slots sont pleins ET d'un grade coche -> EXECUTE.
        if self._click_step("03_execute", required=True, wait=1.0):
            self.log(f"[synth] fusion OK : {nonempty[0]} x{len(nonempty)}")
            self._click_step("05_confirm", required=False, wait=0.6)
            return "fused"
        return "aborted"
