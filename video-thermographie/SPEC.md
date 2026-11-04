# SPEC — Inspection thermographique photovoltaïque par drone

Source : `Cahier_des_charges.pdf` (structure en 6 scènes, textes S1 et S2 imposés).
Choix validés avec le client : pas de voix off ; musique originale composée ; 16:9 seul pour ce premier passage.
Passage 8 : 58 s (rapport +3 s : fiches défaut n°1 et n°2, plan de localisation) ; anomalies au rendu thermique réaliste
(module de 8 x 6 cellules, sous-chaîne, cellule fissurée, boîte de jonction) désignées par des lignes de rappel, sans cercles ;
icônes S2 en trait de 6 px ; lettres du logo vectorisées depuis le logo fourni.
Passage 7 : voix off française ajoutée (FLORA, Gemini 3.1 Flash TTS, voix « Umbriel »), musique plus rythmée (batterie légère) ;
cercles de S4, pages 2 et 3 de S5 et message final de S7 recalés sur la voix.
Passage 5 : 54 s ; rapport en trois pages (défaut, résultats, couverture normée) ; planning des inspections.
Passage 4 : 45 s, 7 scènes (ajout plateforme en ligne et fin site web + LinkedIn), rapport « Conforme IEC TS 62446-3 »,
anomalies nommées selon la note technique, drone simplifié et balayage 1,5 s.
Passage 2 (retours client) : typographie Comfortaa partout ; slogan « Inspections techniques aériennes, révélez l’invisible. » ;
contact www.flyscanair.com · 06 22 80 57 69 · contact@flyscanair.com ; plus de cercle autour du drone ; « i » du logo sans point
(la bille rouge fait office de point) ; graphiques du client : rendement (%) janvier → juin en S2, production (kWh/an) en S5.

```text
GOAL:    le spectateur comprend qu'un défaut invisible coûte cher et qu'un survol thermique par drone le révèle ; il retient « faire contrôler son installation ».
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, MP4 H.264 (version LinkedIn).
TIME:    55,0 s x 30 = 1650 images, en boucle (passage 6 ; détail des coupes dans README.md). Musique 100 BPM : 1 temps = 0,6 s = 18 images, 1 mesure = 2,4 s.
         Coupes : S1 0–7,2 · S2 7,2–13,2 · S3 13,2–21,0 · S4 21,0–27,6 · S5 27,6–34,2 · S6 34,2–40,8.
LOOK:    fond #FFFFFF plat + trame de points Ø2 px #E4E4E7 au pas de 48 px (papier technique, aucun dégradé).
         Encre #111111 : traits de structure 2,5 px, détails 1,5 px, cellules 1 px #D4D4D8, fond de panneau #F3F3F4.
         Accent #FF5700 réservé à la chaleur et à l'action : points chauds, ligne de scan, cercles de détection,
         coches, courbe positive, séparateur final. Une seule zone orange dominante par plan.
         Vue thermique sobre : panneau #FFF1E8, cellules #FFD2BC, points chauds en dégradé radial #FF5700 → transparent.
         Titres Comfortaa 700, 64 px (5,9 % de la hauteur), interlignage 1,12, approche -1 %.
         Étiquettes et graduations Comfortaa 600, 28–36 px, #111111 ou #6B6B70. Rien sous 28 px.
         Logotype : Comfortaa 700 174 px + contour de 10 px du même dégradé (graisse du logo d’origine).
         Médium : schéma technique tracé à la plume. Tout apparaît par tracé (stroke-dashoffset), jamais par fondu global.
         Profondeur : une seule ombre, sous le rapport (0 18 px, flou 40 px, opacité 8 %). Pas de grain, pas de vignettage.
OBJECTS: bâtiment agricole/industriel en projection oblique (façade, pignon, toit monopente avec 6 x 3 panneaux à cellules) ;
         soleil trait (cercle + 8 rayons) ; graphique « Rendement (%) » du client (axes fléchés, graduations 80–100, mois Jan–Jun, grille pointillée,
         courbe grise « Saine » 98,2 → 95,2, courbe orange « Avec défauts » 98,2 → 85,2, zone de perte orange) ;
         flamme trait ; bouclier d'assurance avec coche ; champ de 7 x 3 panneaux vu de dessus (6 x 4 cellules chacun) ;
         drone quadrirotor vu de dessus (corps, 4 bras, 4 rotors, objectif IR orange) ; panneau zoomé avec cadre alu,
         cellules, rubans, boîte de jonction ; rapport A4 avec vignette du panneau, checklist ; histogramme « Production (kWh/an) » du client
         (Installation saine 20 000, Installation avec défauts ≈ 16 400).
MOTION:  arrivées expo.out / power4.out ; caméra et zooms power2.inOut ; sorties et zoom-traversant power3.in.
         Tracés : 0,5–0,9 s power2.inOut, décalés de 0,04–0,08 s. Mots : 0,067 s d'écart. Sorties 40–50 % plus courtes.
         Ressort du point final : back.out(1.4) (≈ amortissement 0,8). Aucune boucle de respiration sur les textes.
SHOTS:
  S1  0,0–7,2   La ligne de sol se trace, puis façade, pignon, toit, 18 panneaux (cascade), soleil. Un point chaud orange
                naît sur un panneau (1,2 s) puis pulse 2 fois. Titre mot à mot : « Certaines anomalies sont invisibles à
                l'œil nu. » lisible 3,0–6,5. Sortie : le bâtiment se dé-trace, seule la ligne de sol reste.
  S2  7,2–13,2  La ligne de sol devient l'axe X (morphing), l'axe Y monte, grille et graduations ; les courbes « Saine »
                et « Avec défauts » se tracent, la zone de perte orange se révèle. Flamme puis bouclier se tracent. Les 3 termes passent du gris à l'encre au rythme des visuels.
                Sortie : flou 8 px + fondu, mot par mot.
  S3  13,2–21,0 Le champ de panneaux se trace (vue de dessus). Le drone entre par la gauche (expo.out), HUD sans cercle :
                ligne de rappel « Caméra infrarouge », échelle froid/chaud. Le HUD se retire, le drone balaie de gauche
                à droite : la ligne de scan orange révèle la vue thermique et 4 anomalies. Titre « La thermographie rend
                visible l'invisible. » Sortie : le drone quitte le cadre, zoom traversant (power3.in) sur le panneau défectueux.
  S4  21,0–27,6 Le zoom se pose (power3.out) : le panneau remplit la moitié gauche, les rubans apparaissent. Point chaud
                pulsant ; trois cercles orange se tracent seuls avec leurs étiquettes : Point chaud, Cellule défectueuse,
                Défaut de connexion. Titre « Chaque anomalie est détectée et localisée. » Sortie : étiquettes en fondu,
                le panneau rétrécit et devient la vignette du rapport (transport).
  S5  27,6–34,2 La feuille se trace autour de la vignette, checklist cochée en orange (3 clics doux). À droite : titre
                « Un rapport clair pour agir vite. » et histogramme de production (barres qui montent).
                Sortie : tout se floute ; la barre orange se replie en point et glisse vers la bille du logo.
  S6  34,2–40,8 Le point devient la bille gauche du logo, le serpentin se trace, la ligne de scan révèle « Fly Scan’Aır »,
                la bille droite (point du i) apparaît. Slogan mot à mot, message, contact. Tenue ≥ 3,5 s. Fin sur l'accord résolu de la musique.
SOUND:   passage 7 : voix off fr-FR, 10 phrases (texte dans README.md), -16 LUFS, placée scène par scène et terminée avant la
         sortie en boucle (54 s) ; musique atténuée de 10 dB sous la voix ; batterie légère (grosse caisse à la noire de S2 à S6,
         clap sur 2 et 4 de S3 à S6, charleston en croches) et basse en croches. Ci-dessous, la conception d'origine.
         Musique originale 100 BPM, la mineur → do majeur : nappes douces + pulsation basse (S1–S2), arpège léger à
         l'entrée du drone (S3–S5), résolution lumineuse sur le rapport, accord final tenu (S6). Effets : whoosh court
         (entrée drone), whoosh long bas (scan), whoosh (zoom), 3 tics (cercles), 3 clics doux (coches), impact grave
         discret (logo). Mixage -16 LUFS, crête ≤ -1 dBTP.
BANNED:  fond sombre ; lueur, néon, particules ; dégradés violet/bleu ; verre ; tout centré ; tout en fondu+montée ;
         texte qui bouge pendant la lecture ; icônes dans des cercles ; trois cartes alignées ; logo dans un coin ;
         3D ; effets flashy ; chiffres inventés (seules les données des graphiques fournis par le client).
QA:      t=0 (vignette non vide) · 4,5 (bâtiment + point chaud + titre) · 11,5 (graphique + 2 icônes + 3 termes) ·
         15,6 (drone + HUD lisible) · 18,4 (scan à mi-course, thermique à gauche seulement) · 20,9/21,0 (raccord zoom) ·
         24,8 (3 cercles + étiquettes) · 27,5/27,6 (raccord vignette) · 32,0 (rapport complet) · 34,1/34,2 (raccord point) ·
         38,0 (carton final lisible).
```
