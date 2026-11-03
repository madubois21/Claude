# REVIEW

## Passage 7b — correctif du tracé des panneaux (9:16 et 1:1)
- Défaut signalé : en scène 3, le contour de chaque panneau ne se traçait qu'aux trois quarts (bord droit et haut du bord
  gauche manquants), puis se complétait d'un coup à 1,6 s, après l'arrivée du drone.
- Cause : dans les SVG de zoom (traits « non-scaling-stroke »), Chromium pose les tirets à l'échelle de l'écran ; en 9:16
  et 1:1 la caméra de S3 agrandit le champ de ×1,08, le motif normalisé ne couvrait donc que 1/1,08 du contour.
- Correctif : le motif et le décalage des tracés sont multipliés par l'échelle de l'SVG (, calculé dans
  ). S3 : contours tracés en entier et en continu ; S4 : cercles tracés sur toute leur durée prévue
  (ils se fermaient trop tôt en 9:16/1:1). 16:9 inchangé (échelle 1, rendu identique).

## Passage 7 — voix off et musique
- Voix off française, 10 phrases générées dans FLORA (Gemini 3.1 Flash TTS, voix « Umbriel », fr-FR ; coût 0,13 $),
  fichiers d'origine conservés (`assets/audio/vo/raw_XX.wav`). Texte complet dans README.md.
- `tools/voiceover.py` : silences de début/fin coupés, pauses internes limitées à 0,24–0,30 s, phrases 4 à 7 et 10
  accélérées de 2 à 4 % (hauteur conservée), −16 LUFS. Environ 48 s de parole sur 55 s : la voix se termine à 53,6 s,
  avant la sortie en boucle (54 s), et reprend à 0,9 s.
- Image recalée sur la voix (seuls changements visuels, tous de minutage) :
  S4 les trois cercles se tracent quand la voix nomme le défaut (0,8 / 1,55 / 3,3 s au lieu de 1,4 / 2,3 / 3,2 s) ;
  S5 les champs du défaut n°1 apparaissent sur « chaque défaut y est décrit », la catégorie sur « qualifié »,
  page 2 tournée à 5,15 s (au lieu de 4,0 s), page 3 à 8,7 s (au lieu de 8,2 s) — le tampon « Conforme IEC TS 62446-3 »
  tombe sur « aux normes » ; S7 le message « Faites contrôler votre installation. » arrive 0,15 s plus tôt et reste
  0,15 s de plus. Bruitages déplacés avec leurs gestes.
- Musique plus rythmée : grosse caisse à la noire (S2 → S6, battement discret dès 2,4 s), clap léger sur 2 et 4 (S3 → S6),
  charleston en croches (+ doubles-croches fantômes dès S4), basse en croches dès S2, léger pompage des nappes.
  Mêmes accords, même tempo (100 BPM), même fin sur l'accord tenu et le logo.
- Mixage : la musique descend à 0,32 (−10 dB) sous la voix, remonte dans les vrais silences (fin de S1, fin de S2) et
  pour la sortie en boucle.
- `hyperframes check` : 0 erreur, 0 avertissement sur les trois formats.
- Rendus (trois formats) : 55,0 s, 30 i/s ; −15,9 LUFS intégré, crête vraie −1,8 dBTP ; la voix ressort d'environ 9 dB
  au-dessus de la musique. Images clés relues (cercles S4, pages S5, tampon, message S7, raccord de boucle).
- Son mesuré, **pas écouté** : à valider à l'écoute (équilibre voix / musique, naturel des légères accélérations).

## Passage 6 — finitions
- « Un rapport aux normes, pour agir rapidement. »
- Fin : « Suivez-nous sur LinkedIn » + linkedin.com/company/fly-scan-air (adresse fournie par le client).
- Boucle : à 54 s tout se retire (le serpentin et le navigateur se dé-tracent, la ligne de scan repasse à l'envers),
  puis la ligne de sol de la scène 1 se trace jusqu'à 38 % : la dernière image s'enchaîne sur la première.
  Durée 55 s ; la musique s'éteint sur cette sortie.
- Corrigé : identifiant en double (dégradé et texte du logo), le nom du logo ne disparaissait pas à la sortie.

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
