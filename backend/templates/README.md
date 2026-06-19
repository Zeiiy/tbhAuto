# Templates

Captures de boutons en PNG, recadrees serre. Capturees a fenetre/resolution de
calibration (1455x1338) ; le matching s'adapte ensuite par echelle (`Detector.scale`).

## `templates/`
- `auto_chest_1.png` — bouton coffre **normal** (un clic = un coffre ouvert).
- `auto_chest_2.png` — bouton coffre **elite**.
- `tout_ranger.png` — bouton « Tout Ranger » du stash (Auto Ranger).

## `templates/sequences/synthese/`
- `02_remplissage.png` — bouton « Remplissage automatique » (le **jeu** remplit la
  grille avec le grade le plus bas ayant >=9 objets). Clic sur la **moitie gauche**
  pour eviter le deroulant a droite.
- `03_execute.png` — bouton d'execution de la fusion (bouton **bleu** actif).
- `04_retour.png` — la petite fleche de retour (vide la grille).

> Pas de `05_confirm` : ce jeu n'a **pas** de popup resultat a fermer.
> Le bot ne clique QUE ces boutons reconnus par template (auto-fill / executer /
> retour), tous 190+ px sous le curseur de niveau → il ne change jamais le niveau.

## Reglages
- Faux positifs → monte `match_threshold` (0.90). Rien trouve → baisse (0.80).
- Recapturer si l'UI du jeu change (memes coords/taille de fenetre que la calibration).
