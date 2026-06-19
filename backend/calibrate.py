"""
Outil de calibration. Lance-le avec le jeu ouvert (Stash + Cube sur Synthese).

  python calibrate.py grab        # sauve une capture annotee (grille de coords)
  python calibrate.py colors X Y  # affiche la couleur HSV au point (X,Y) de la capture

Workflow :
  1. `python calibrate.py grab` -> ouvre logs/calib.png avec une grille de reperes.
  2. Lis dessus les rectangles (x,y,w,h) de la grille de synthese et du stash,
     et les coords des onglets de page. Reporte-les dans bot/config.py.
  3. `python calibrate.py colors X Y` sur un item de chaque grade (gris/vert/bleu/
     violet) pour caler les plages HSV dans grade_colors.
"""
import sys
import os
import cv2
import numpy as np

from bot.config import Config
from bot.capture import Capturer


def grab():
    cap = Capturer(Config())
    frame, ox, oy = cap.grab()
    h, w = frame.shape[:2]
    step = 50
    for x in range(0, w, step):
        cv2.line(frame, (x, 0), (x, h), (0, 80, 0), 1)
        cv2.putText(frame, str(x), (x + 1, 12), cv2.FONT_HERSHEY_PLAIN, 0.7, (0, 255, 0), 1)
    for y in range(0, h, step):
        cv2.line(frame, (0, y), (w, y), (0, 80, 0), 1)
        cv2.putText(frame, str(y), (1, y + 11), cv2.FONT_HERSHEY_PLAIN, 0.7, (0, 255, 0), 1)
    os.makedirs("logs", exist_ok=True)
    out = os.path.join("logs", "calib.png")
    cv2.imwrite(out, frame)
    print(f"Capture {w}x{h} (offset ecran {ox},{oy}) -> {out}")
    print("Coords lues sur cette image = relatives a la capture (a mettre dans config).")


def colors(x, y):
    cap = Capturer(Config())
    frame, _, _ = cap.grab()
    patch = frame[max(0, y-6):y+6, max(0, x-6):x+6]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    med = np.median(hsv, axis=0)
    print(f"Point ({x},{y}) -> HSV median H={med[0]:.0f} S={med[1]:.0f} V={med[2]:.0f}")
    print("Rappel: common=S faible ; vert H~35-85 ; bleu H~90-130 ; violet H~131-160.")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "grab":
        grab()
    elif len(sys.argv) == 4 and sys.argv[1] == "colors":
        colors(int(sys.argv[2]), int(sys.argv[3]))
    else:
        print(__doc__)
