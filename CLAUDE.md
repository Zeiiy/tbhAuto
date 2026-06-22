# TBH Companion — guide projet (CLAUDE.md)

Compagnon pour le jeu **TaskBarHero** (PC, Windows) : aides d'auto-farming AFK +
assistant (timers de coffres, overlay). Tourne la nuit, jeu visible au premier plan.
Fonctions : **Auto Synthèse** (fusionne les bas grades), **Auto Coffre** (ouvre les
coffres), **Auto Ranger**, **Assistant** (timers) et **Overlay**.

> Nom **affiché** = « TBH Companion » (constante `APP_NAME` dans `gui.py`, rebrand du
> 2026-06-22) ; le fichier exe reste **`TBHBot.exe`** (l'updater/CI cherchent cet asset —
> le renommer casserait la maj auto). En interne le cœur reste un « bot » d'automatisation.

> `README.md` = doc **utilisateur** (comment utiliser l'app) ; ce `CLAUDE.md` = doc
> **technique** (architecture, internes). L'ancien duo web (`backend/main.py` FastAPI
> + `frontend/` React) est **legacy/obsolète** — ne pas le lancer.

## Architecture (depuis le 2026-06-17 : app native .exe)

- **`backend/bot/`** — cœur du bot, indépendant de l'UI :
  - `config.py` — toute la config + la calibration (valeurs par défaut).
  - `capture.py` — capture d'écran (mss) de la fenêtre du jeu. **mss thread-local**
    (le bot tourne dans un thread ; sinon crash `srcdc`).
  - `detector.py` — template matching OpenCV (`templates/`), **multi-échelle**
    (`Detector.scale`) ; `find/find_all` renvoient `(cx,cy,score,w,h)`.
  - `clicker.py` — **clics humains** : position tirée dans un disque (~30 % de la
    cible, jamais le même pixel), déplacement en **courbe de Bézier** (bornée) à
    vitesse variable + micro-tremblements ; clamp fenêtre.
  - `colors.py` — `GradeClassifier` : `classify_grid` (grade par cadre/centre dans
    la grille de synthèse), `has_content` (case pleine/vide, pour l'inventaire),
    `is_allowed`.
  - `synthesis.py` — cycle de synthèse (auto-fill + veto couleur).
  - `engine.py` — boucle principale, garde-fous, planification des actions.
  - `calib_store.py` — persistance `calibration.json` + overlay + échantillon HSV.
  - `log_watch.py` — `LogWatcher` (tail de `player.log`) + `classify_chest_key`,
    pour l'Assistant personnel (timers de coffres). Voir section dédiée.
  - `updater.py` — mise à jour auto via GitHub Releases (check/download/relance).
- **`backend/gui.py`** — **l'application** (customtkinter). Onglets *Contrôle* et
  *Calibrage*, bouton *Assistant personnel*, bouton de mise à jour. `APP_VERSION`
  y est défini. C'est le point d'entrée réel.
- **`backend/templates/`** — PNG des boutons (voir plus bas).
- **`backend/calibration.json`** — calibration persistée par l'UI ; **surcharge**
  les défauts de `config.py` quand présent (à côté de l'exe en mode build).
- **`backend/main.py` + `frontend/`** — ancien duo web, **legacy, ne pas lancer**
  (deux moteurs se battraient pour la souris).

## Lancer / construire

```powershell
cd backend
# Dev (fenêtre native) :
.\.venv\Scripts\python.exe gui.py
# Construire l'exe (un seul fichier -> dist\TBHBot.exe, ~68 Mo) :
.\build_exe.ps1
```
Dépendances : `requirements.txt` + `customtkinter pillow pyinstaller` dans `.venv`.

## Mise à jour automatique (GitHub Releases + CI) — depuis le 2026-06-19

Dépôt **public** `Zeiiy/tbhAuto` (constantes `GITHUB_OWNER/REPO` dans `updater.py`).

- **Côté app** (`updater.py` + `gui.py`) : au démarrage **et toutes les 30 min** (exe
  seulement), un thread interroge `…/releases/latest` ; si `tag_name` > `APP_VERSION`, un
  bouton ambre **« ↑ Mise à jour X.Y »** apparaît dans l'en-tête. Au clic (confirmation) :
  télécharge l'asset `TBHBot.exe` en `…\TBHBot.exe.new`, puis `stage_replace()` écrit un
  **.bat relais** détaché (le .bat boucle sur `move` jusqu'à ce que l'app quitte — un exe
  ne peut s'écraser tant qu'il tourne — puis se supprime), un message invite à rouvrir, et
  l'app se ferme. En **dev** (non-frozen) : désactivé.
- **PAS de relance auto** (décidé le 2026-06-20) : relancer un exe **onefile** juste après
  l'avoir réécrit échoue par intermittence — le bootloader extrait `python3xx.dll` pendant
  que l'antivirus scanne encore le fichier fraîchement écrit → *« failed to load Python DLL
  / module introuvable »*. Le lancement **manuel** (l'utilisateur rouvre l'exe) est fiable à
  100% (scan AV terminé). Donc on installe à la fermeture et l'utilisateur double-clique.
  (Diagnostic : ce n'est ni une var d'env `_MEI*/_PYI*` — testé —, ni réglé par un délai de
  3 s — testé v1.1.2/1.1.3 —, mais la course extraction/scan AV sur le relancement immédiat.)
- **Côté CI** (`.github/workflows/release.yml`) : sur un tag `v*`, un runner
  **windows-latest** installe les deps, lance PyInstaller (même commande que
  `build_exe.ps1`) et publie la release avec `TBHBot.exe` (action `softprops/action-gh-release`).

**Publier une nouvelle version** : bump `APP_VERSION` dans `gui.py` → commit → 
`git tag vX.Y.Z && git push origin vX.Y.Z`. Le CI build + release ; les exes déjà
installés proposent la maj. (La 1re version avec updater doit être installée une fois à la
main — fait pour v1.1.0.) Le build local `build_exe.ps1` reste utile pour tester avant tag.

## Calibration (fait le 2026-06-17)

- Fenêtre du jeu : titre exact **`TaskBarHero`** (sans espace), sur l'**écran 2**,
  calibrée à la taille **1455×1338**.
- **Déplacer** la fenêtre = OK (capture relative). **Redimensionner / autre PC** =
  **auto-calibrage par échelle** : `Capturer.scale()` = taille fenêtre actuelle /
  `calib_window_size` ; la géométrie (grilles via `_scan_grid`, onglets via
  `_do_tout_ranger`) et les templates (matching redimensionné via `Detector.scale`,
  réglé chaque cycle dans `engine`) s'adaptent automatiquement. Marche si l'UI scale
  uniformément. Plus de pause sur redimensionnement ; l'aperçu Calibrage affiche
  « auto-calibrage échelle ×N ».
- Géométrie dans `config.py` : `synthesis_grid_rect` (3×3), `stash_grid_rect` (7×7),
  `stash_page_tabs` (**repli uniquement** depuis le 2026-06-22 : les onglets sont
  désormais **détectés dynamiquement**, cf. section « Coffres & Tout Ranger » ; les 6
  coords y restent comme repli, recalibrées le 2026-06-22),
  `inventory_grid_rect` (7×3, dans le panneau HERO sous
  le perso). Éditable dans l'onglet *Calibrage*. Les **couleurs de grade ne sont PAS
  éditables/persistées** (code-only dans `config.py` — sinon un vieux `calibration.json`
  masquerait les corrections ; seule la géométrie + les réglages sont persistés).

### Prérequis avant un run (état écran)
- Fenêtre du jeu **au premier plan**, même taille (ou auto-échelle si différente).
- **Cube sur l'onglet « Synthèse »** (PAS « Alchimie ») — la grille/boutons y sont calibrés.
- **Stash** ouvert et **inventaire visible** (panneau HERO sous le perso) en même temps.
- Le **niveau de synthèse** (« Lv.XX ») : règle-le comme tu veux, le bot **n'y touche jamais**.

### Couleurs de grade — PIÈGE IMPORTANT
La détection de grade **diffère entre le stash et la grille de synthèse** :
- Stash : grade = couleur de **fond** du slot.
- Grille de synthèse : grade = couleur du **CADRE** de la case (pour vert+) ; le
  **commun a un cadre gris** indistinct d'une case vide → `classify_grid` tranche
  par la **luminosité du CENTRE** (item clair = commun, sinon vide).

Teintes mesurées **sur les cadres de la grille** (OpenCV H 0-179) + noms du jeu.
Ordre du jeu (bas→haut) : **gris < vert < bleu < orange < rouge < violet**.
| Couleur | H | Grade (nom jeu) | Défaut |
|---|---|---|---|
| gris | (centre clair) | common | ✅ |
| vert | ~50 | uncommon | ✅ |
| bleu | ~106 | rare | ✅ |
| orange | ~14 | **legendary** | ⛔ |
| rouge | ~0 (s'enroule ≥159) | **immortal** | ⛔ |
| violet | ~141 | **arcana** | ⛔ |

> Le bleu de la grille est **H106** (pas 78 — le 78 du stash était un autre item).
> `grade_colors` : rare (95,122), arcana (128,158), legendary=orange (8,22),
> immortal=rouge (≤12 ou ≥159, teinte rouge qui s'enroule autour de 0/179).
> Les grades fusionnés sont **cochables dans l'UI** (`synthesis_allowed_grades`) ;
> « Défaut » = cases pré-cochées. **Liste blanche** : tout grade non coché/inconnu = refusé.

## Synthèse (logique)

`synthesis.run_cycle()` :
1. Vide un résidu éventuel (case non `empty`) → `04_retour`.
2. Clique **« Remplissage automatique »** (`02_remplissage`) : le **jeu** remplit
   le grade le plus bas ayant ≥9 objets.
3. Relit la grille (`classify_grid`) et applique un **veto par liste blanche** :
   - **REFUS** si une case porte un grade **non coché / inconnu** →
     log `REFUS : grade(s) non selectionne(s)/inconnu(s) {...}` → `04_retour` ;
   - **REFUS** si la grille n'est pas pleine → log `REFUS : grille incomplete (X/9)` → `04_retour` ;
   - sinon **EXÉCUTE** (`03_execute`) → log `fusion OK : <grade> xN`.

Sécurité vérifiée (17 scénarios + balayage des 180 teintes) : seuls les grades
**cochés** fusionnent ; tout le reste est annulé. Le bot ne clique QUE des boutons
reconnus par template (auto-fill/exécuter/retour), tous **190+ px sous le curseur de
niveau** → il **ne change jamais le niveau** de synthèse (et le mouvement ne clique pas).

Le bot ne choisit jamais d'item lui-même. Pour **sécuriser des objets** : les
mettre dans la **Réserve** et décocher « Inclure les Objets de la Réserve », ou
les passer sur un autre type d'objet.

**Grades à fusionner = configurables** (cases à cocher dans l'UI → `synthesis_allowed_grades`,
défaut gris/vert/bleu). Comme l'auto-fill prend toujours le grade le plus bas ≥9,
décocher un grade fait que le bot **s'arrête** à ce niveau (les items de ce grade
s'accumulent). Garder coché le plus bas grade possédé, sinon rien ne fusionne.

## Coffres & Tout Ranger

- **Auto Coffre** : scruté **en continu** (le coffre n'apparaît que ~5 s),
  clic dès détection, cooldown 2 s. Templates `auto_chest_1` (normal) +
  `auto_chest_2` (élite). Détection par apparence (position unique gérée).
- **Auto Ranger** (feature indépendante) : vérifie d'abord l'**inventaire**
  (`inventory_grid_rect`, 7×3, détecté par **luminosité du centre** via
  `GradeClassifier.has_content` — PAS `classify_grid` qui donnait des faux positifs au
  bord). Vide → rien. Sinon clique « Tout Ranger » page par page et **re-vérifie
  l'inventaire après chaque page**, s'arrête dès qu'il est vide. Intervalle aléatoire (2-5 min).
- **Onglets de page DÉTECTÉS dynamiquement** (depuis le 2026-06-22) :
  `detector.find_stash_tabs(frame, band)` repère les onglets par leur **couleur de
  coffre brun/orange** (R≫B) dans une **bande dérivée de `stash_grid_rect`** (juste
  au-dessus du quadrillage, donc suit l'échelle, **aucune calibration du nombre
  d'onglets**). → marche avec **2, 6, 7… onglets** sur n'importe quel compte. Un segment
  brun **pleine largeur** (ex. panneau « Chasseur ») est rejeté (`max_w`). `ranger_pages`
  n'est plus qu'un **plafond optionnel** (`0` = AUTO = toutes les pages détectées, défaut) ;
  `stash_page_tabs` ne sert plus que de **repli** si la détection échoue (stash fermé).

## Assistant personnel (timers de coffres) — depuis le 2026-06-19

Fenêtre **détachable** (`AssistantWindow`, CTkToplevel dans `gui.py`), ouverte par le
bouton **« Assistant personnel »** de l'en-tête. Indépendante du bot : elle **ne clique
jamais** (le clic des coffres reste le travail d'Auto Coffre). Redimensionnable, petite,
déplaçable.

- **Source = LOG du jeu, pas la vision.** `backend/bot/log_watch.py` (`LogWatcher`) lit
  **en direct** (tail) `%USERPROFILE%\AppData\LocalLow\TesseractStudio\TaskbarHero\player.log`
  et repère les lignes `GetBoxCount Success Count : N // ItemKey : KEY`. Au démarrage on se
  place en **fin de fichier** (l'historique est ignoré). Le callback tourne dans le thread
  du watcher → passe par une **queue** lue dans la boucle `after` de la fenêtre (thread-safe Tk).
- **Lecture BINAIRE avec seek explicite (`open("rb")` + `seek(pos)` chaque passe)** — PIÈGE :
  le jeu garde `player.log` **ouvert** et y écrit ; en lecture *cross-process*, un `readline()`
  texte ne revoit PAS les octets ajoutés après avoir atteint l'EOF (état EOF mis en cache →
  « rien ne se passe »). On suit un offset d'octets, on lit `size-pos` à chaque tick, on
  bufferise la dernière ligne incomplète, et on gère troncature/rotation (relance du jeu).
- **Mécanique** : les coffres tombent **aléatoirement** (pas à chaque monstre/boss) mais ne
  sont *obtenables* qu'après un cooldown depuis le dernier loot (**normal 5 min, élite 7 min**
  → `chest_cooldowns_s`). À **chaque** acquisition de la clé d'un type, le compte à rebours
  **repart** ; affiche `M:SS` + barre, puis **« Obtenable »** (vert) à zéro.
- **`GetBoxCount` logue TOUS les gains de coffres** (drops, récompenses…), pas seulement les
  coffres temporisés. Le **TYPE vient du PRÉFIXE** (2 premiers chiffres de l'ItemKey), pas de
  la clé exacte : le **suffixe varie selon le grade du butin** (910401/910501/910651 sont tous
  le même coffre normal). `classify_chest_key()` applique : surcharge exacte `chest_key_map`
  (vide par défaut), sinon `chest_key_prefixes` = **`91`→normal** (monstres normaux),
  **`92`→élite** (boss de fin de run). `93xxxx` & co = ignorés (affichés « dernier : clé … »
  dans le statut). Ce classement est **CODE-ONLY** (non persisté, comme `grade_colors` —
  sinon un vieux `calibration.json` le masquerait).
- **Logique de timers extraite** dans `backend/bot/chest_timers.py` (`ChestTimers`) :
  encapsule le `LogWatcher` + l'état (cooldowns, dernier coffre) + `state(ctype, now)` →
  `('unset'|'idle'|'cooldown'|'ready', restant, total)`. **Partagée** par la fenêtre
  Assistant ET l'overlay (chacun sa propre instance/watcher ; lecture seule).
- **Fenêtre Assistant** (`AssistantWindow`, détachable) : DEUX modes, bascule
  Détaillé ↔ Compact (bouton), mémorisée dans `config.assistant_mode` :
  - **Détaillé** (défaut) : deux cartes (Élite or / Normal bleu) `M:SS` + barre + statut.
  - **Compact** : petite fenêtre, deux carrés LED `●` verte=obtenable / rouge=cooldown /
    grise=pas vu + mini timer.
- **Overlay façon Discord** (`OverlayWindow`, depuis le 2026-06-22) — fenêtre INDÉPENDANTE,
  pilotée **uniquement depuis l'onglet « Overlay » du menu principal** (PAS depuis l'Assistant) :
  - **Click-through + sans focus** : `_make_click_through()` pose `WS_EX_TRANSPARENT |
    NOACTIVATE | TOOLWINDOW | LAYERED` → les clics passent au jeu (overlay **non cliquable**)
    ET le jeu reste actif (**le bot ne se met pas en pause**). `overrideredirect` + `-topmost` + `-alpha`.
  - **Hauteur = barre des tâches** (work-area via `GetMonitorInfo`/`mss`), dans un **coin**
    (`tl/tr/bl/br`) d'un **écran** choisi, **largeur** + **offset X/Y** ajustables.
  - Réglages persistés : `overlay_enabled` / `overlay_monitor` / `_corner` / `_alpha` /
    `_width` / `_offset_x` / `_offset_y`. L'App crée/détruit l'`OverlayWindow` via l'interrupteur
    (`_toggle_overlay`/`_open_overlay`/`_close_overlay`) et applique les réglages à chaud
    (`OverlayWindow.refresh_settings()`). Réouvert au démarrage si `overlay_enabled`.
- **Nom affiché = « TBH Companion »** (constante `APP_NAME` dans `gui.py`, depuis le 2026-06-22) :
  rebrand d'affichage uniquement (titre/en-tête/fenêtres). **Le fichier exe reste `TBHBot.exe`**
  (l'updater/CI cherchent cet asset — le renommer casserait la maj auto des installs existantes).
- **Temps des étages = PAS POSSIBLE depuis les logs** (vérifié le 2026-06-22 sur les 39 Mo de
  `player.log`). Le jeu n'écrit AUCUN clear d'étage lisible : seuls les loots `GetBoxCount` le
  sont ; toute la logique d'étage (`StageManager`, `EStageType`, `MonsterSpawnManager`) n'apparaît
  que dans des **stack-traces obfusquées** (méthodes `iet`/`igw`/`koc`…) **sans valeurs** (ni n°
  d'étage, ni difficulté, ni durée). Les tags `[CoreTBH_DebugLog]` ne couvrent que login/seed/save.
  → Un onglet « derniers temps d'étage » ne pourrait venir QUE de la **vision** (OCR du « 3-8 » +
  difficulté + chrono entre changements d'étage) — non implémenté.
- **UI minimale, mapping fixé** dans `config.py` : pas de panneau d'apprentissage (corriger
  `chest_key_prefixes`/`chest_key_map` si un code diffère). Classement **CODE-ONLY** (cf. ci-dessus).

## Templates (`backend/templates/`)

- `sequences/synthese/` : `02_remplissage`, `03_execute` (bouton **bleu** actif),
  `04_retour`. Pas de `05_confirm` (ce jeu n'a pas de popup résultat).
- `auto_chest_1.png`, `auto_chest_2.png`, `tout_ranger.png`.
- Recapturer si l'UI du jeu change (mêmes coords/taille de fenêtre).

## Cadence & garde-fous

- Synthèse + Auto Ranger sur intervalle **aléatoire** (défaut 2-5 min) ; Coffres = continu.
- **Clics humains** (`clicker.py`) : point de clic tiré dans un **disque** (~30 % de la
  taille de la cible, jamais deux fois le même pixel) ; le curseur s'y rend en **courbe
  de Bézier** à vitesse variable (smoothstep) avec micro-tremblements ; `pyautogui.PAUSE=0`,
  délais gérés à la main. `detector.find/find_all` renvoient la taille (w,h) pour ce jitter.
  Le bouton « Remplissage auto » a un **déroulant à droite à éviter** → clic sur la **moitié
  gauche** (`synthesis._click_step(..., left_half=True)`).
- Garde-fous : failsafe coin haut-gauche, hotkey **Ctrl+Alt+K**, pause si jeu pas au
  premier plan / introuvable / **redimensionné** / frame noire, durée max, anti-veille.
- Boucle **résiliente** : une erreur ponctuelle met en pause et continue (ne tue pas
  le run nocturne).

## Conventions

- Code et logs en français (sans accents dans le code). Garder ce style.
- Après modif du cœur du bot, **rebuild l'exe** (`build_exe.ps1`) et relancer pour tester.
- Heads-up : un exe PyInstaller qui automate souris/clavier peut déclencher un faux
  positif antivirus.
