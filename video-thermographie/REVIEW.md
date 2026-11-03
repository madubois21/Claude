# REVIEW

## Passage 5 — rythme et rapport
- Durée 45 s → 54 s (cahier : 50–55 s demandés par le client). Temps ajouté : rapport (6 → 12,6 s), graphique S2 et
  anomalies S4 (+0,6 s chacun), plateforme (+1,2 s). Scène 3 inchangée (balayage rapide conservé). Musique recalée.
- S5 inspirée du rapport type fourni (structure : analyse détaillée d'un défaut, résultats, catégorisation par gravité,
  couverture), redessinée dans la charte Fly Scan'Air (blanc, noir, dégradé gris → orange pour les 5 niveaux de gravité).
  Aucune mention du logiciel d'origine ni des données du client du rapport type (nom, site, mesures).
- Valeurs du rapport illustratives et cohérentes avec la vidéo : 7 défauts (anomalies visibles en S3), 5 modules,
  0/7 résolus, défaut n°1 « Point chaud (hot-spot) », ΔT 11,2 °C, MaxT 58 °C, catégorie 4.
- S6 : « Suivi de production » remplacé par « Inspections à venir » (frise Jan / Avr / Juil / Oct : passées en noir,
  prochaine en orange pulsant, suivante en gris). Mois illustratifs.
- `hyperframes check` : 0 erreur, 0 avertissement sur les trois formats.

## Passage 4 — retours client (rapport, plateforme, site, LinkedIn, anomalies, drone)
- Durée : 45,0 s (maximum du cahier des charges). Musique recalée sur les nouvelles scènes.
- S3 : drone simplifié (corps, deux bras, quatre rotors, objectif) ; balayage 2,7 s → 1,5 s ; entrée du drone plus vive.
- S3/S4 : signatures thermiques de la note technique : point chaud ponctuel (cellule fissurée), échauffement linéaire
  d'une chaîne (diode by-pass défectueuse), boîte de jonction en surchauffe ; module à vide (échauffement uniforme) dans le champ.
- S5 : « Rapport thermographique », tampon « Conforme IEC TS 62446-3 », titre « Un rapport aux normes, pour agir vite. »,
  ligne « Justificatif assurance » (note technique § 2.4).
- S6 (nouvelle) : la plateforme en ligne — le rapport rejoint la liste des rapports ; plan thermique, anomalies, suivi de
  production. Mention « Bientôt disponible » (plateforme en développement). Aucun chiffre ni adresse inventés.
- S7 : logo + slogan + message, puis navigateur dessiné avec la vraie capture du site (révélée par la ligne de scan,
  adresse tapée), logo LinkedIn officiel (bleu #0A66C2) et coordonnées. L'adresse exacte de la page LinkedIn n'a pas été
  fournie : seule la mention « Suivez-nous sur LinkedIn » est affichée.
- `hyperframes check` : 0 erreur, 0 avertissement sur les trois formats.

## Passage 3 — déclinaisons 9:16 et 1:1
- Version 16:9 inchangée : fichiers régénérés identiques à l’octet près (vérifié par `git diff`).
- Même film dans les deux cadres : mêmes dessins, textes, minutage, transitions, musique. Adaptations de mise en page
  seulement : blocs empilés ; en S3 la caméra suit le drone (le champ de panneaux ne tient pas en largeur) ;
  en S4 les étiquettes passent sous le panneau, reliées par des traits verticaux ; slogan sur 3 lignes, coordonnées
  sur 3 lignes ; en 1:1 le soleil de S1 passe à droite du titre pour ne pas le toucher.
- Tous les raccords conservés et recalculés par format (sol → axe, zoom traversant, vignette du rapport, point → bille).
- `hyperframes check` : 0 erreur, 0 avertissement sur chaque déclinaison (textes ≥ 28 px).

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
