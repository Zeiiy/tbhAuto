# TBH AFK Bot

Bot d'auto-farming pour **TaskBarHero** (Windows), conçu pour tourner en AFK la nuit,
le jeu visible au premier plan. Application de bureau native (`TBHBot.exe`).

> Doc technique détaillée (architecture, internes) : voir **`CLAUDE.md`**.

## Fonctions
- **Auto Synthèse** — laisse le jeu remplir (« Remplissage automatique ») puis **ne
  fusionne que les grades cochés** (gris/vert/bleu par défaut). Tout grade non coché
  ou inconnu (violet/orange/rouge…) est **refusé** — liste blanche, jamais de fusion
  non voulue.
- **Auto Coffre** — ouvre les coffres dès qu'ils apparaissent (surveillance continue).
- **Auto Ranger** — vérifie l'inventaire ; s'il y a des items, clique « Tout Ranger »
  page de stash par page jusqu'à ce que l'inventaire soit vide.
- **Assistant personnel** — fenêtre détachable (bouton en haut) qui **lit le log du jeu**
  et affiche un **compte à rebours** avant que chaque coffre soit de nouveau *obtenable*
  (normal 5 min, élite 7 min). Elle **ne clique pas** (c'est le bot qui ouvre les coffres) ;
  elle détecte le **loot réel** et son **type**.

## Lancer
Télécharge **`TBHBot.exe`** depuis la page **Releases** du dépôt
(<https://github.com/Zeiiy/tbhAuto/releases>) puis double-clique. Aucune installation requise.

L'antivirus peut bloquer un exe qui automate la souris → autorise-le si besoin.

### Mises à jour automatiques
Au démarrage, l'app vérifie s'il existe une version plus récente. Si oui, un bouton
**« ↑ Mise à jour X.Y »** apparaît en haut : clique-le, et l'app se met à jour et
redémarre toute seule. (Rien n'est installé sans ton clic.)

## Prérequis à l'écran (avant un run)
1. Fenêtre du jeu **au premier plan** (même taille que la calibration, sinon
   auto-ajustement par échelle).
2. **Cube sur l'onglet « Synthèse »** (pas « Alchimie »).
3. **Stash** ouvert et **inventaire visible** (panneau HERO, grille sous le perso).
4. **Niveau de synthèse** réglé comme tu veux — le bot **n'y touche jamais**.

## Utilisation
Onglet **Contrôle** : active les fonctions voulues, coche les grades à fusionner,
règle les intervalles (synthèse / ranger en minutes) et le nombre de pages de stash,
puis **▶ Démarrer**. Clique ensuite la fenêtre du jeu pour la mettre au premier plan
(le bot reprend automatiquement). Le **journal** montre chaque action et chaque refus.

Onglet **Calibrage** : aperçu en direct (grilles + grade détecté), clic sur l'image
pour échantillonner une couleur, et champs pour ré-ajuster les zones si besoin.

Bouton **Assistant personnel** (en haut) : ouvre la fenêtre des timers de coffres
(Élite et Normal, déjà reconnus). Elle ne réagit qu'aux loots faits **après** son
ouverture, et indique en bas le dernier coffre vu. Les coffres tombent au hasard,
mais ne sont *obtenables* qu'au bout du cooldown (normal 5 min, élite 7 min).

## Garde-fous
- Arrêt d'urgence : **souris dans le coin haut-gauche** ou **Ctrl+Alt+K**.
- Pause auto si le jeu n'est pas au premier plan / introuvable / écran noir.
- Durée max configurable. Anti-veille pendant le run.
- **Clics humanisés** : position étalée sur le bouton + déplacement de souris en
  courbe à vitesse variable (anti-détection).

## Reconstruire l'exe (développeurs)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt customtkinter pillow pyinstaller
.\build_exe.ps1            # -> dist\TBHBot.exe
# ou en dev, sans build :  .\.venv\Scripts\python.exe gui.py
```

## Avertissement
L'automatisation peut violer les CGU du jeu (risque de ban). À tes risques.
