# REVIEW

## Passage 2 — retours client
- Slogan : « Inspections techniques aériennes, révélez l’invisible. » (faute de frappe « ispections » corrigée), « l’invisible » en orange.
- Contact ajouté : www.flyscanair.com · 06 22 80 57 69 · contact@flyscanair.com (séparateurs orange).
- Typographie Comfortaa sur tous les textes et sur le logotype. Comfortaa Bold étant plus fine que les lettres du logo d’origine,
  le logotype reçoit un contour de 10 px du même dégradé pour retrouver la graisse de l’original.
- Logo : « Aır » sans point sur le i ; la bille rouge du serpentin est placée exactement au-dessus de la tige (position mesurée).
- Cercle (réticule) autour du drone supprimé ; la ligne de rappel « Caméra infrarouge » part maintenant du drone par la marge gauche.
- S2 : graphique « Rendement (%) » du client redessiné au trait (axes fléchés, graduations, grille pointillée, courbes
  « Saine » grise et « Avec défauts » orange, zone de perte orange). La ligne de sol de S1 devient toujours l’axe des temps.
- S5 : histogramme « Production (kWh/an) » du client (Installation saine / avec défauts), barres qui montent ;
  la barre orange se replie en point et devient la bille du logo (nouveau raccord S5 → S6).
- Valeurs lues sur l’image fournie : rendement 98,2 → 95,2 % (saine) et 98,2 → 85,2 % (avec défauts) ; production 20 000 et
  ≈ 16 400 kWh/an. À corriger dans `tools/build.py` (`S2_SAINE`, `S2_DEFAUT`, `S5_BARS`) si les chiffres exacts diffèrent.

## Mesuré / regardé (passage 2)
- `hyperframes check` : 0 erreur, 0 avertissement (lint, runtime, mise en page, contraste, rythme, audio).
- Planches de raccords et de temps forts relues ; raccord S5 → S6 continu (le point arrive sur la bille du logo).
- Son inchangé depuis le passage 1 : mesuré, **pas écouté**.

## Passage 1
- Choix : structure, textes S1/S2 et 6 transitions du cahier des charges ; textes S3–S5 proposés (modifiables en variables) ;
  un seul monde dessiné avec des raccords causés (sol → axe, zoom traversant, vignette du rapport, point → bille du logo) ;
  musique originale (100 BPM) + 11 effets sonores ciblés.
- Corrigé en revue : tracé progressif (attribut SVG au lieu du CSS arrondi par GSAP), accents multi-mots, reste de trait
  pendant le zoom S3, sortie S1 trop longue, carton final recentré, GSAP embarqué (CDN bloqué au rendu), musique remontée
  de −17,3 à −15 LUFS.

## Point le plus faible
- S2 : « Défauts invisibles » s’allume avec le bouclier d’assurance, dont le lien n’est pas direct.
- Le logo reste une reconstitution vectorielle : à valider face au fichier d’origine.

## Gardé volontairement
- Fin centrée (carton logo) : seul plan centré du film.
- HUD sobre (ligne de rappel + échelle froid/chaud) autour du drone, demandé par le cahier des charges (transition 5).
