import time
import math
import random
import pyautogui

pyautogui.FAILSAFE = True  # souris au coin haut-gauche = arret d'urgence
pyautogui.PAUSE = 0        # on gere nous-memes tous les delais (mouvement + sleeps)

try:
    import pydirectinput
except Exception:
    pydirectinput = None


class Clicker:
    """Clics "humains" : position etalee dans la cible + deplacement en courbe.

    - Le point de clic est tire dans un DISQUE (rayon ~30% de la cible) -> jamais
      deux fois le meme pixel, reparti sur tout le bouton.
    - Le curseur s'y rend via une COURBE de Bezier a vitesse variable (lent au
      depart/arrivee) avec micro-tremblements -> imite un mouvement de main.
    """

    def __init__(self, config):
        self.config = config
        self._region = None  # (left, top, w, h) pour le clamp

    def set_region(self, left, top, w, h):
        self._region = (left, top, w, h)

    def _clamp(self, x, y):
        if not self._region:
            return x, y
        l, t, w, h = self._region
        x = min(max(x, l + 2), l + w - 2)
        y = min(max(y, t + 2), t + h - 2)
        return x, y

    def _jitter(self, x, y, radius):
        """Point aleatoire uniforme dans un disque de rayon `radius`."""
        radius = max(1.0, float(radius))
        r = radius * math.sqrt(random.random())
        a = random.uniform(0, 2 * math.pi)
        return x + r * math.cos(a), y + r * math.sin(a)

    def _sleep(self, rng):
        time.sleep(random.uniform(*rng))

    def _move_to(self, x, y):
        if self.config.use_directinput and pydirectinput is not None:
            pydirectinput.moveTo(int(x), int(y))
        else:
            pyautogui.moveTo(int(x), int(y))

    @staticmethod
    def _position():
        try:
            p = pyautogui.position()
            return float(p[0]), float(p[1])
        except Exception:
            return None

    def _human_move(self, x, y):
        """Deplace la souris jusqu'a (x,y) en courbe, vitesse variable (humain)."""
        start = self._position()
        if start is None:
            self._move_to(x, y)
            return
        sx, sy = start
        dist = math.hypot(x - sx, y - sy)
        if dist < 2:
            return
        steps = max(10, min(70, int(dist / 10)))
        # point de controle decale perpendiculairement -> courbure naturelle
        px, py = -(y - sy), (x - sx)
        plen = math.hypot(px, py) or 1.0
        off = random.uniform(-0.15, 0.15) * dist
        off = max(-60.0, min(60.0, off))   # courbe bornee : pas de grand detour
        cx = (sx + x) / 2 + px / plen * off
        cy = (sy + y) / 2 + py / plen * off
        total = random.uniform(0.12, 0.28) + dist * random.uniform(0.0005, 0.0011)
        for i in range(1, steps + 1):
            t = i / steps
            te = t * t * (3 - 2 * t)            # smoothstep : lent debut/fin
            bx = (1 - te) ** 2 * sx + 2 * (1 - te) * te * cx + te ** 2 * x
            by = (1 - te) ** 2 * sy + 2 * (1 - te) * te * cy + te ** 2 * y
            if i < steps:                        # micro-tremblement de la main
                bx += random.uniform(-1.3, 1.3)
                by += random.uniform(-1.3, 1.3)
            bx, by = self._clamp(bx, by)
            self._move_to(bx, by)
            time.sleep(total / steps * random.uniform(0.7, 1.3))

    def click(self, x, y, button="left", radius=None):
        cfg = self.config
        if radius is None:
            radius = cfg.click_pos_jitter_px
        tx, ty = self._jitter(x, y, radius)
        tx, ty = self._clamp(tx, ty)
        self._sleep(cfg.click_pre_delay)
        self._human_move(tx, ty)
        if cfg.use_directinput and pydirectinput is not None:
            pydirectinput.click(button=button)
        else:
            pyautogui.click(button=button)
        self._sleep(cfg.click_post_delay)

    def right_click(self, x, y, radius=None):
        self.click(x, y, button="right", radius=radius)
