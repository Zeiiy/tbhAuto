# TBH Companion

Compagnon pour **TaskBarHero** (Windows) : un **assistant** (timers de coffres, overlay
façon Discord) doublé d'**aides d'auto-farming** pour tourner en AFK la nuit, le jeu
visible au premier plan. Application de bureau native (`TBHBot.exe`).

> Le nom affiché est **TBH Companion** ; le fichier reste `TBHBot.exe`.
> Doc technique détaillée (architecture, internes) : voir **`CLAUDE.md`**.

## Fonctions
- **Auto Synthèse** — laisse le jeu remplir (« Remplissage automatique ») puis **ne
  fusionne que les grades cochés** (gris/vert/bleu par défaut). Tout grade non coché
  ou inconnu (violet/orange/rouge…) est **refusé** — liste blanche, jamais de fusion
  non voulue.
- **Auto Coffre** — ouvre les coffres dès qu'ils apparaissent (surveillance continue).
- **Auto Ranger** — vérifie l'inventaire ; s'il y a des items, clique « Tout Ranger »
  page de stash par page jusqu'à ce que l'inventaire soit vide. Les **onglets de page
  sont détectés automatiquement** : marche quel que soit leur nombre (2, 6, 7…), sans
  recalibrage. (Plafond réglable, ou « Auto » = toutes les pages détectées.)
- **Assistant personnel** — fenêtre détachable (bouton en haut) qui **lit le log du jeu**
  et affiche un **compte à rebours** avant que chaque coffre soit de nouveau *obtenable*
  (normal 5 min, élite 7 min). Elle **ne clique pas** ; elle détecte le **loot réel** et son
  **type**. Deux modes (bouton de bascule) :
  - **Détaillé** : cartes Élite/Normal avec timer `M:SS`, barre de progression et statut.
  - **Compact** : petite fenêtre, deux carrés avec une **LED** verte (obtenable) /
    rouge (cooldown) / grise (pas encore vu).
- **Overlay** *(façon Discord)* — mini-barre **transparente, toujours au-dessus du jeu et
  NON cliquable** (les clics passent au jeu → le farm n'est pas interrompu). Affiche les
  LED + timers des coffres, à hauteur de la barre des tâches. Entièrement réglable depuis
  l'**onglet Overlay** : on/off, écran, coin, transparence, largeur, décalage.

## Lancer
Télécharge **`TBHBot.exe`** depuis la page **Releases** du dépôt
(<https://github.com/Zeiiy/tbhAuto/releases>) puis double-clique. Aucune installation requise.

L'antivirus peut bloquer un exe qui automate la souris → autorise-le si besoin.

### Mises à jour automatiques
L'app vérifie s'il existe une version plus récente (au démarrage et toutes les 30 min).
Si oui, un bouton **« ↑ Mise à jour X.Y »** apparaît en haut : clique-le → la nouvelle
version se télécharge, **l'app se ferme**, et tu n'as plus qu'à **rouvrir `TBHBot.exe`**
(double-clic) pour terminer. (Rien n'est installé sans ton clic.)

> Pourquoi rouvrir à la main ? Relancer l'app automatiquement juste après l'avoir
> remplacée peut faire râler l'antivirus (« failed to load Python DLL ») ; rouvrir
> soi-même est fiable à 100 %.

## Prérequis à l'écran (avant un run)
1. Fenêtre du jeu **au premier plan** (même taille que la calibration, sinon
   auto-ajustement par échelle).
2. **Cube sur l'onglet « Synthèse »** (pas « Alchimie »).
3. **Stash** ouvert et **inventaire visible** (panneau HERO, grille sous le perso).
4. **Niveau de synthèse** réglé comme tu veux — le bot **n'y touche jamais**.

## Utilisation
**Onglet Contrôle** : active les fonctions voulues, coche les grades à fusionner,
règle les intervalles (synthèse / ranger en minutes) et le nombre de pages de stash
(ou « Auto »), puis **▶ Démarrer**. Clique ensuite la fenêtre du jeu pour la mettre au
premier plan (le bot reprend automatiquement). Le **journal** montre chaque action et
chaque refus.

**Onglet Overlay** : active la mini-barre transparente au-dessus du jeu et choisis
l'**écran**, le **coin** (haut-gauche / haut-droite / bas-gauche / bas-droite), la
**transparence**, la **largeur** et le **décalage** fin. L'overlay n'attrape aucun clic :
tout passe au jeu, donc il n'interrompt jamais le farm.

**Onglet Calibrage** : aperçu en direct (grilles + grade détecté), clic sur l'image
pour échantillonner une couleur, et champs pour ré-ajuster les zones si besoin.

**Bouton Assistant personnel** (en haut) : ouvre la fenêtre des timers de coffres
(Élite et Normal). Elle ne réagit qu'aux loots faits **après** son ouverture, et indique
en bas le dernier coffre vu. Les coffres tombent au hasard, mais ne sont *obtenables*
qu'au bout du cooldown (normal 5 min, élite 7 min). Bascule Détaillé / Compact avec le
bouton en haut de la fenêtre.

## Garde-fous
- Arrêt d'urgence : **souris dans le coin haut-gauche** ou **Ctrl+Alt+K**.
- Pause auto si le jeu n'est pas au premier plan / introuvable / écran noir.
- Durée max configurable. Anti-veille pendant le run.
- L'**overlay ne met pas le farm en pause** : il reste au-dessus sans prendre le focus.

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
