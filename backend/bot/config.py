from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple


@dataclass
class Config:
    # ===================== CAPTURE =====================
    # Capture la fenetre du jeu par son titre (le plus robuste).
    window_title: Optional[str] = "TaskBarHero"
    # Region fixe (left, top, width, height) si window_title introuvable. None = ecran principal.
    region: Optional[Tuple[int, int, int, int]] = None

    # ===================== TEMPLATES =====================
    templates_dir: str = "templates"
    match_threshold: float = 0.85

    # ===================== TIMING =====================
    scan_interval: float = 0.9         # pause entre deux passes de la boucle (s)
    scan_interval_jitter: float = 0.25 # +/- 25% de jitter aleatoire sur l'intervalle

    # ===================== CLIC (randomisation) =====================
    click_pos_jitter_px: int = 4       # rayon de jitter autour du centre detecte
    click_pre_delay: Tuple[float, float] = (0.04, 0.12)   # delai avant clic (min,max)
    click_post_delay: Tuple[float, float] = (0.15, 0.35)  # delai apres clic (min,max)
    move_duration: Tuple[float, float] = (0.08, 0.22)     # duree du deplacement souris
    use_directinput: bool = False      # True si pyautogui ne "prend" pas dans le jeu

    # Micro-pauses humaines : toutes les N actions, pause aleatoire.
    micro_pause_every: int = 25        # nombre d'actions
    micro_pause_range: Tuple[float, float] = (3.0, 9.0)

    # ===================== GARDE-FOUS NUIT =====================
    max_runtime_minutes: int = 600     # auto-stop apres X minutes (0 = illimite)
    keep_awake: bool = True            # empeche la veille ecran/PC pendant le run
    require_window_foreground: bool = True  # pause si la fenetre n'est pas au 1er plan
    black_frame_value_threshold: int = 12   # frame consideree "noire" sous cette valeur moyenne
    panic_hotkey: str = "ctrl+alt+k"   # arret d'urgence global (en plus du failsafe coin)

    # ===================== FEATURES =====================
    features_default: Dict[str, bool] = field(default_factory=lambda: {
        "auto_synthesis": False,
        "auto_chest": False,
        "auto_ranger": False,
    })
    # Intervalle ALEATOIRE (secondes) entre deux SYNTHESES : tire au hasard dans
    # [min, max] apres chaque tentative -> cadence non previsible. Les coffres, eux,
    # sont scrutes EN CONTINU (fenetre d'apparition ~5s), donc pas d'intervalle ici.
    action_interval_ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "auto_synthesis": (120.0, 300.0),   # 2 a 5 min
    })
    # Coffres : cooldown anti double-clic apres avoir clique un coffre (s).
    chest_click_cooldown_s: float = 2.0

    # ===================== ASSISTANT PERSONNEL (timers coffres) =====================
    # Mecanique du jeu : un coffre n'est lootable qu'apres un cooldown depuis le
    # dernier loot (normal 5 min, elite 7 min). L'assistant lit le LOG du jeu EN
    # DIRECT (player.log -> "GetBoxCount Success Count : N // ItemKey : KEY") pour
    # connaitre le moment EXACT du loot et le TYPE (via l'ItemKey), puis affiche le
    # compte a rebours avant "obtenable". Il ne touche JAMAIS la souris (le clic des
    # coffres reste le travail du bot Auto Coffre, s'il est active).
    chest_cooldowns_s: Dict[str, float] = field(default_factory=lambda: {
        "normal": 300.0,   # 5 min
        "elite": 420.0,    # 7 min
    })
    # Chemin du player.log de TaskBarHero. None => resolution auto (AppData/LocalLow).
    game_log_path: Optional[str] = None
    # Le TYPE de coffre est donne par le PREFIXE (2 premiers chiffres de l'ItemKey) ;
    # le suffixe varie selon le grade du butin (910401/910501/910651... = meme coffre).
    # Observe en jeu : 91xxxx = NORMAL (monstres normaux), 92xxxx = ELITE (boss de fin de
    # run). 93xxxx et autres = ignores. Source de verite = ce code (NON persiste, pour ne
    # pas etre masque par un vieux calibration.json, cf. grade_colors).
    chest_key_prefixes: Dict[str, str] = field(default_factory=lambda: {
        "91": "normal",
        "92": "elite",
    })
    # Surcharges EXACTES optionnelles (ItemKey complet -> type), prioritaires sur le
    # prefixe. Vide par defaut.
    chest_key_map: Dict[str, str] = field(default_factory=dict)
    # Periode de lecture (tail) du log par l'assistant (s).
    chest_log_poll_s: float = 0.7

    # ===================== SYNTHESE =====================
    # Grades a fusionner, dans l'ordre de priorite. Le bot ne touche QUE ceux-la.
    synthesis_allowed_grades: List[str] = field(default_factory=lambda: ["common", "uncommon", "rare"])
    synthesis_items_needed: int = 9
    synthesis_stash_pages: int = 6   # (actuellement inutilise par le code)
    # Apres K cycles de synthese sans progres (pas 9 items d'un grade autorise),
    # on espace fortement les essais pour ne pas boucler a vide.
    synthesis_max_idle_cycles: int = 3
    synthesis_idle_backoff_s: float = 120.0
    # Pages du stash (1..N) a NE PAS inspecter, pour securiser des objets qu'on y
    # range (ex: [4]). Le bot n'y navigue pas et n'y clique aucun item.
    stash_excluded_pages: List[int] = field(default_factory=list)

    # ===================== TOUT RANGER =====================
    # Clique periodiquement le bouton "Tout Ranger" du stash (range/collecte les
    # objets) sur un intervalle aleatoire, tant qu'Auto Synthese est actif.
    tout_ranger_enabled: bool = True
    tout_ranger_interval_range: Tuple[float, float] = (120.0, 300.0)  # 2 a 5 min
    # PLAFOND optionnel de pages a ranger avec "Tout Ranger". 0 = AUTO = toutes les
    # pages detectees (les onglets sont detectes dynamiquement, cf. _do_tout_ranger /
    # find_stash_tabs : marche avec 2, 6, 7... onglets sans calibration). >0 = limite.
    ranger_pages: int = 0

    # ===================== GEOMETRIE (a CALIBRER, coords relatives a la capture) =====================
    # Taille de la fenetre au moment de la calibration. Le bot se met en PAUSE si
    # la fenetre est redimensionnee (coords/templates plus valides -> recalibrer).
    # Le DEPLACEMENT de la fenetre, lui, est gere automatiquement (capture relative).
    calib_window_size: Optional[Tuple[int, int]] = (1455, 1338)

    # Grille de synthese 3x3 : rectangle englobant (x, y, w, h) dans la capture.
    # CALIBRE 2026-06-17 (fenetre 1455x1338, offset ecran 2814,165).
    synthesis_grid_rect: Optional[Tuple[int, int, int, int]] = (1121, 564, 182, 177)
    synthesis_grid_rows: int = 3
    synthesis_grid_cols: int = 3

    # Grille du stash : rectangle englobant + nb de lignes/colonnes. (CALIBRE : 7x7)
    stash_grid_rect: Optional[Tuple[int, int, int, int]] = (37, 515, 419, 412)
    stash_grid_rows: int = 7
    stash_grid_cols: int = 7

    # Coords (centre) des onglets de page du stash, dans la capture.
    # CALIBRE 2026-06-22 : 6 onglets debloques (largeur ~56 px, ecart regulier 63 px).
    # 7e onglet PAS ENCORE DEBLOQUE : se projette a x~430, meme y -> l'AJOUTER ici
    # ET passer ranger_pages a 7 une fois debloque. ATTENTION : la rangee se RE-CENTRE
    # quand un onglet s'ajoute (ancienne calib 4 onglets 54/124/188/248 -> 52/115/178/241),
    # donc si les clics tombent a cote apres deblocage, recapturer toute la rangee.
    stash_page_tabs: List[Tuple[int, int]] = field(
        default_factory=lambda: [(52, 458), (115, 458), (178, 458),
                                 (241, 458), (304, 458), (367, 458)])

    # Grille de l'INVENTAIRE (source des items que "Tout Ranger" range). CALIBRE.
    inventory_grid_rect: Optional[Tuple[int, int, int, int]] = (515, 679, 417, 180)
    inventory_grid_rows: int = 3
    inventory_grid_cols: int = 7

    # ===================== COULEURS DE GRADE (HSV OpenCV : H 0-179) =====================
    # Plages a AFFINER avec calibrate.py. "common" = faible saturation (gris/blanc).
    # CALIBRE 2026-06-17 sur les CADRES de la grille de synthese (teintes OpenCV) :
    #   gris (centre clair) | vert H~50 | bleu H~106 | violet/arcana H~141 |
    #   orange/legendary H~14 | rouge/immortal H~0.
    # AUTORISES = common/uncommon/rare. Liste blanche : tout le reste est rejete.
    # rare s'arrete a H122 (bleu~106) et arcana commence a H128 (violet~141).
    grade_colors: Dict[str, dict] = field(default_factory=lambda: {
        "common":    {"s_max": 40, "v_min": 75},                       # gris/blanc  (AUTORISE)
        "uncommon":  {"h": (40, 65),   "s_min": 70, "v_min": 50},      # vert   H~50  (AUTORISE)
        "rare":      {"h": (95, 122),  "s_min": 70, "v_min": 50},      # bleu   H~106 (AUTORISE)
        "arcana":    {"h": (128, 158), "s_min": 70, "v_min": 50},      # violet H~141 (INTERDIT)
        "legendary": {"h": (8, 22),    "s_min": 90, "v_min": 60},      # orange H~14  (INTERDIT)
        "immortal":  {"h": (0, 6),     "s_min": 90, "v_min": 60},      # rouge  H~0   (INTERDIT)
    })

    # ===================== DEBUG =====================
    debug: bool = False                # sauve des screenshots annotes dans logs/debug/
    logs_dir: str = "logs"
