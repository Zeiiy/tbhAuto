# Historique de session

## Session History

### 2026-06-16 22:46
- Lancement et test de l'application TaskBarHero (Path of Exile bot)
- Calibrage géométrique: ajout des rectangles et coordonnées de synthèse (3x3) et stash (7x7)
- Calibrage chromatique: affinage des valeurs H/S/V pour chaque rareté d'objet (common/uncommon/rare/legendary/immortal)
- Amélioration robustesse: filtrage des fenêtres minimisées/hors-écran dans `get_window()` + sélection fenêtre max par surface
- Renommage: "Taskbar Hero" → "TaskBarHero" pour cohérence (config.py)

### 2026-06-17 00:27
- Renommage "Taskbar Hero" → "TaskBarHero" (config.py) pour cohérence sans espace
- Amélioration robustesse get_window(): filtrage fenêtres minimisées/hors-écran + sélection par surface max (capture.py)
- Calibrage géométrique: ajout coordonnées synthesis_grid_rect (1121, 564, 182, 177) + stash_grid_rect (37, 515, 419, 412) à 7x7 (config.py)
- Calibrage chromatique: affinage H/S/V par rareté - common/uncommon/rare/legendary/immortal mesurées sur TaskBarHero (config.py)
- Amélioration synthèse: nettoyage auto résidus fusion dans grille avant remplissage (synthesis.py)
- Verrouillage calibration: ajout calib_window_size (1455x1338) + pause auto si redimensionnement (config.py + engine.py)
- Création documentation projet memory tbhauto-setup.md avec contraintes calibration et setup instructions

### 2026-06-16 23:40
- Création app native GUI (gui.py) avec customtkinter réutilisant 100% du moteur bot existant
- Création script de build PyInstaller réutilisable (build_exe.ps1) générant exe --onefile (67,8 MB)
- Configuration persistance: calibration.json stocké à côté de l'exe + chemins ressources/templates en absolu
- Tests intégration smoke: GUI lancée, capture+overlay+classification vérifiée, fermeture propre
- Exe finalisé et vérifié: bundling templates complet, modules critiques (mss/pynput/pyautogui/cv2/PIL) OK, app native fonctionnelle

### 2026-06-16 23:45
- Capture complète des templates: 03_execute.png (bleu/actif), 04_retour.png, auto_chest_1.png (normal), auto_chest_2.png (élite)
- Validation détecteur: tous les templates matchent à score 1.000 aux bonnes positions écran
- Test de fusion en direct réussi: 9 communs → 1 peu commun (vert) via bouton Exécuter détecté
- Amélioration robustesse synthesis.py: garde-fou pour vider la grille avant chaque cycle (évite d'empiler sur un résultat)
- Confirmé: Auto Coffre et Auto Synthèse coexistent (coffres sous les panneaux, y≈1086-1147)

### 2026-06-16 23:48
- Diagnostic et correction bug "_thread._local' object has no attribute 'srcdc'" - mss n'est pas thread-safe (instance créée dans thread principal utilisée par worker thread)
- Correction thread-safety dans capture.py: instance mss par thread via thread-local storage
- Amélioration résilience engine.py: boucle catch erreurs, pause au lieu de crasher (crucial pour runs AFK toute nuit)
- Rebuild exe PyInstaller (67.8 MB) intégrant corrections + tests relancement bot OK

### 2026-06-17 00:49
- Test live du bot depuis exe: Auto Synthèse activée, reprise automatique détectée après focus jeu (pause/reprise normale)
- Corrigé: synthèse complète en direct - détection résidus grille → RETOUR, clic-droits remplissage, fusion 9→1 OK
- Exe native TBHBot.exe vérifié fonctionnel end-to-end: cycle complet bot automatisé, logs en direct, arrêt propre
- Architecture migration terminée: web app (obsolète) → exe native unique, zéro dépendances serveur, double-clic pour lancer

### 2026-06-17 00:16
- Correctif crash srcdc + résilience boucle: capture via thread worker (mss thread-safe), engine.py catch erreurs, runs AFK viables
- Implémentation des 4 demandes initiales: page 1 stash balayée (scan déterministe chaque onglet), Tout Ranger périodique, intervalles aléatoires 2-5 min (synthèse/coffres/Tout Ranger), pages stash protégeables
- Rework majeur synthèse mi-session: abandon scan manuel → Remplissage automatique (jeu remplit le grade le plus bas ≥9), veto couleur (annuler si suspecte), coffres en continu (scrutation 5s, clic immédiat)
- Templates capturés: "Tout Ranger" + "Remplissage automatique" (scores 1.000), modifications synthesis.py/engine.py/config.py/gui.py/calib_store.py
- Exe rebuildé (2:03) et relancé: testes integration OK (6 templates, imports, config, GUI, smoke-test)

### 2026-06-17 02:19
- Config bot/config.py: renommage action_intervals → action_interval_ranges (Tuple[float, float]), intervalles 120-300s (2-5 min) pour coffres et synthèse
- GUI gui.py: ajout séparation chemins persist_dir (logs/calibration à côté exe) vs resource_dir (templates bundlés en _MEIPASS)
- GUI gui.py: suppression ui inutiles - "Coffres (min)" + "Pages stash à sécuriser" (Coffres scrutés en continu hors UI), labels explicatifs ajoutés
- GUI gui.py: ajout helper _minmax() + refacto _apply_advanced/_load_advanced pour gestion min/max clean
- Bot engine.py: implémentation "Tout Ranger" multi-page - clic sur chaque onglet stash puis action rangement (log "Tout Ranger (toutes les pages)")
- Exe rebuild (67.8 MB) + relance: vérification imports, 6 templates chargés (coffres auto x2, synthèse x4), GUI OK, bot opérationnel

### 2026-06-17 02:25
- Refonte run_cycle synthesis.py: auto-fill + veto couleur (jeu remplit automatiquement, cancel si couleur suspecte détectée)
- Débuggage détection grille synthesis.py: correction logique _scan_grid() pour détecter carrés remplis (pas juste lecture GRADES)
- Vérification cohérence: config.py/gui.py/synthesis.py/engine.py alignés (coffres continu, synthèse auto, UI simplifiée)
- Exe rebuild + relance: 6 templates chargés, imports vérifiés, GUI et bot opérationnels, tests intégration OK

### 2026-06-17 02:31
- Correctif détection couleurs colors.py: amélioration robustesse détection HSV pour items gris/vert/bleu/autres en grille de synthèse
- Rework _scan_grid() synthesis.py: détection correcte des carrés remplis basée sur pixels RGB réels (pas interprétation GRADES)
- Tests couleur validés: grille 3x3 scannée correctement, items détectés par teinte (gris vert bleu) vs unknow pour invalide

### 2026-06-17 02:46
- Validation complète veto couleur: mesure directe teintes réelles en grille (vert H50, bleu H106, violet H141, orange H14, rouge H0)
- Correction calibration teintes: bleu rare (95-122), violet/arcana (128-158), orange/legendary et rouge/immortal tous rejetés (liste blanche)
- Correction noms grades: mapping exact arcana/legendary/immortal en accord avec jeu + teintes mesurées
- Rebuild et relance app: veto couleur validé end-to-end sur palette complète, sécurité par liste blanche (seuls gris/vert/bleu autorisés)
- Mise à jour memory: documentation mécanisme détection grille + vraies plages HSV pour chaque grade

### 2026-06-17 17:42
- Test live complet du bot: synthèse, coffres, tout ranger validés en jeu réel
- Mesure définitive HSV des grades: violet H141 (arcana), orange H14 (legendary), rouge H0 (immortal) — tous correctement rejetés
- Calibration grade_colors finalisée: common/uncommon/rare autorisés ; arcana/legendary/immortal refusés par liste blanche
- Mise à jour CLAUDE.md avec documentation complète: architecture, couleurs grades, logique synthèse, templates, cadence et sécurité
- Veto couleur validé end-to-end sur palette 6 grades (gris→vert→bleu→violet→orange→rouge)

### 2026-06-17 23:29
- Correction détection rouge (immortal) colors.py: ajout détection explicite aux deux extrémités plage H (H ≤ 12 ou H ≥ 159)
- Rouge était détecté comme "unknown" (quand même rejeté) → maintenant "immortal" pour clarté logs
- Rebuild exe PyInstaller avec correction: 67.8 MB, imports et 6 templates OK, veto couleur renforcé

### 2026-06-17 23:35-23:39
- Refactor calib_store.py: retrait grade_colors de CALIB_FIELDS (persistance) car c'est la source de vérité dans config.py (code), pas l'UI
- Évite qu'un ancien calibration.json masque les corrections de code sur les teintes
- Modifications gui.py, colors.py, build_exe.ps1 pour robustesse finals
- Auto Ranger: séparation complète de la synthèse (feature indépendant, cadence propre)

### 2026-06-18 00:37-23:47
- Implémentation auto-calibrage par échelle: `Capturer.scale()` (ratio actuel/calib_window_size) adapte géométrie grilles/onglets, `Detector.scale()` redimensionne templates OpenCV chaque cycle
- Géométrie dynamique en synthèse (_scan_grid, _do_tout_ranger) et affichage aperçu Calibrage "auto-calibrage échelle ×N"
- Suppression pause sur redimensionnement: marche si UI du jeu scale uniformément (relâche contraint size-locking précédent)
- Persistance selectiv: calibration.json persiste géométrie + settings (min/max), grade_colors reste code-only dans config.py (source vérité, échappe shadows json obsolètes)
- Rebuild exe PyInstaller (67.8 MB) + tests intégration: imports OK, 6 templates chargés, GUI scalable, bot résilient
- Mise à jour CLAUDE.md (section Calibration) et memory tbhauto-setup.md avec documentation complète auto-scaling

### 2026-06-18 00:10-00:14
- Ajout menu déroulant GUI pour nombre de pages du ranger (gui.py, config.py) - sélection dynamique 1-4 pages
- Ajout cases à cocher pour grades à fusionner en synthèse (gui.py, calib_store.py) - gris/vert/bleu cochable individuellement
- Implémentation persistance config: ranger_pages + synthesis_allowed_grades sauvés dans calibration.json (chargés au démarrage)
- Intégration dans engine.py: utilisation des grades cochés pour le veto couleur en synthèse
- Mise à jour CLAUDE.md documentation: règle clé "garde coché le grade le plus bas que tu as"

### 2026-06-18 00:22
- Implémentation intervalles aléatoires (config.py): action_interval_ranges (min, max) au lieu de fixed action_intervals, 120-300s (2-5 min) pour coffres/synthèse/Tout Ranger
- Feature "Tout Ranger": clic périodique sur bouton rangement stash (synthesis.py + engine.py + config.py) - rangement/collecte items avant synthèse
- Planification aléatoire (engine.py): remplacement simple timing par _next_due dict + _schedule() method, chaque action se reprogram sur sa plage [min,max]
- Pages stash exclues (config.py + synthesis.py): stash_excluded_pages permet sécuriser pages du stash (non visitées par bot)
- Thread-safety mss (capture.py): correction crash "srcdc" - instance mss par thread via thread-local storage
- Erreur handling résilience (engine.py): wrap boucle principale dans try/except - erreurs ponctuelles mettent pause/continue, failsafe toujours remonte

### 2026-06-18 02:15
- Clics adaptatifs (clicker.py): ajout paramètre optionnel `radius` à `click()` et `right_click()` - permet rayon de jitter personnalisé par appel
- Clics dimensionnels (synthesis.py): calcul du radius (~30% de la taille du bouton) basé sur la détection pour un jitter adapté à chaque cible
- Traitement bouton remplissage (synthesis.py): clic ciblé sur la moitié gauche du bouton (évite la flèche déroulante) avec radius réduit (18% de largeur)
- Rebuild exe PyInstaller (67.8 MB) avec clics humains renforcés: jitter adaptif par bouton + courbes Bézier + micro-tremblements

### 2026-06-18 04:27
- Mouvements humanisés complets (clicker.py): déplacement courbe Bézier avec vitesse variable (smoothstep) + micro-tremblements, jitter circulaire étalé sur 30% du bouton, jamais deux clics au même pixel (1177 positions sur 3000 tests)
- Sécurité 17 tests + balayage HSV: logique veto validée (tout grade non coché/inconnu → REFUS), isolation couleurs confirmée (vert H40-65, bleu H95-122 seuls autorisés, autres grades rejetés)
- UI améliorée: pastilles colorées par fonction, pill d'état (● Arrêté/En cours), grades colorés (Gris/Vert/Bleu/Orange/Rouge/Violet) dans le bon ordre, logs de refus détaillés
- Tout Ranger intelligent (engine.py, synthesis.py): vérifie inventaire grille 7×3 par luminosité centre, range page par page, re-vérifie après chaque page, s'arrête quand vide
- Config persistance: ranger_pages (menu déroulant 1-4), synthesis_allowed_grades (cases à cocher gris/vert/bleu/orange/rouge/violet), sauvegarde/chargement calibration.json
- Rebuild exe finale (04:26): 67.8 MB, tous fichiers bot/gui modifiés, tests intégration OK, prêt transfert autre PC

### 2026-06-18 04:38
- Lancement et test live de l'application TBHBot.exe
- Debugging et correctifs majeurs: engine.py, gui.py, config.py, synthesis.py réitérativement modifiés (104 édits total)
- Ajustements détection: couleurs grades, template matching, géométrie hero panel/inventaire
- Multiples rebuilds PyInstaller avec validations intégration (configs, templates, modules critiques)
- Exe finalisée: 67.8 MB, opérationnelle, prêt déploiement

### 2026-06-18 13:52
- Mouvements humanisés complets: déplacement courbe Bézier + vitesse variable (smoothstep) + micro-tremblements, jitter circulaire 30% du bouton (jamais même pixel)
- Auto-inventory check pour Tout Ranger: détection grille inventaire 7×3 par luminosité centre, range page par page avec re-vérification après chaque page
- Configuration persistante: ranger_pages (menu déroulant 1-4), synthesis_allowed_grades (cases à cocher gris/vert/bleu/orange/rouge/violet), sauvegarde/chargement calibration.json
- UI/UX améliorée: pastilles colorées par fonction, grades colorés dans l'ordre correct (gris/vert/bleu/orange/rouge/violet), pill d'état dynamique
- Limitation: synthèse doit rester au même niveau (pas de changement dynamique du niveau de synthèse pendant cycle)
- Rebuild exe finale (67.8 MB) avec toutes améliorations, tests intégration validés

### 2026-06-18 19:34
- Mise à jour CLAUDE.md: documentation technique complète (clics humains, auto-calibrage par échelle, géométrie dynamique grilles, onglet Synthèse requis, grades cochables avec ordre du jeu gris/vert/bleu/orange/rouge/violet, sécurité curseur niveau, logs refus détaillés, prérequis avant run)
- Réécriture README.md pour l'app native .exe (documentation utilisateur, ancienne version web obsolète remplacée)
- Synchronisation mémoire projet: liens vers docs repo (CLAUDE.md/README.md), suppression teintes obsolètes, structure allégée

### 2026-06-19 10:00
- Implémentation fenêtre détachable "Assistant personnel" avec timers coffres (source=log du jeu, pas vision)
- Création backend/bot/log_watch.py (LogWatcher): lecture directe player.log, détection GetBoxCount Success + mapping ItemKey (910501=normal/5min, 920501=élite/7min)
- Ajout AssistantWindow dans gui.py: deux cartes (Élite/Normal), timers M:SS + barre progression, panneau "Coffres récents" avec assignation boutons É/N/✕
- Persistance apprentissage: chest_key_map sauvé dans calibration.json (calib_store.py)
- Rebuild exe TBHBot.exe (67.8 MB) + documentation CLAUDE.md/README.md mise à jour feature Assistant personnel

### 2026-06-19 17:04
- Raffinement et test exhaustif du LogWatcher (log_watch.py): lecture binaire cross-process sécurisée (seek explicite), gestion EOF/rotation, bufferisation ligne incomplète, décodage UTF-16 robuste
- Implémentation complète fenêtre Assistant (gui.py): timers M:SS avec barre progression couleur (vert/rouge/gris), statut surveillance, détection ItemKey 91xxxx (normal) et 92xxxx (élite), classification prefix-based
- Configuration et persistance ItemKey mappings: chest_key_prefixes defaults (91=normal/5min, 92=élite/7min), chest_key_map (surcharge case par case), persistance calibration.json
- Tests intégration: _test_tail.py (regex GetBoxCount), _test_gui_smoke.py (window launch), _test_assistant.py (queue/timer logic), validations tail/GUI/prefix classification
- Rebuild TBHBot.exe (67.8 MB) avec LogWatcher et Assistant intégré + documentation CLAUDE.md section "Assistant personnel" finalisée

### 2026-06-19 → 2026-06-20 : système de mise à jour automatique
- Dépôt public GitHub `Zeiiy/tbhAuto` (git init, `.gitignore`, push) + CI GitHub Actions `.github/workflows/release.yml` : sur un tag `vX.Y.Z`, build PyInstaller sur runner windows-latest puis publication de la release avec `TBHBot.exe`.
- App : `updater.py` interroge `releases/latest` au démarrage ET toutes les 30 min ; bouton ambre « ↑ Mise à jour X.Y » dans l'en-tête (`gui.py`) ; au clic, téléchargement de l'asset puis remplacement de l'exe.
- Releases v1.1.0 → v1.1.5 publiées par le CI (1.1.0 = app + Assistant + auto-update ; 1.1.2 = re-check 30 min ; 1.1.4 = flux final ; 1.1.5 = vérification).

### 2026-06-20 : résolution du bug de relancement post-maj (« failed to load Python DLL / module introuvable »)
- Symptôme : le relancement AUTO de l'exe juste après remplacement échouait par intermittence ; le lancement MANUEL marchait toujours.
- Écarté par tests : ce n'était PAS les variables d'environnement (`_MEIPASS2`, `_PYI_APPLICATION_HOME_DIR`, `_PYI_ARCHIVE_FILE` mises à des valeurs bidons ne cassent rien), et le délai de 3 s (v1.1.2/v1.1.3) n'a PAS suffi.
- Cause réelle : course entre l'extraction de `python3xx.dll` par le bootloader onefile et le scan antivirus de l'exe fraîchement réécrit, lors du relancement immédiat.
- Solution (v1.1.4) : abandon du relancement auto. `updater.stage_replace()` installe le nouvel exe à la fermeture (bat relais qui fait `move` après l'arrêt de l'app, sans relance) ; l'utilisateur rouvre l'exe lui-même (lancement manuel = fiable à 100 %, scan AV terminé). v1.1.5 = vérification du flux, sans erreur.
- Docs `CLAUDE.md` / `README.md` mises à jour (pourquoi pas de relance auto).
