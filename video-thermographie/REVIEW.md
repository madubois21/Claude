# REVIEW — passage 1 (16:9)

## Choix créatifs
- Structure, textes S1/S2 et 6 transitions repris du cahier des charges. Les textes des scènes 3 à 6 sont des propositions,
  modifiables comme variables : « Le scan infrarouge révèle chaque échauffement. », « Chaque anomalie est détectée et localisée. »,
  « Un rapport clair pour agir vite. », slogan provisoire « Rendre visible l’invisible. », message « Faites contrôler votre installation. ».
- Un seul monde dessiné, avec des raccords « causés » : la ligne de sol de S1 devient l’axe du graphique de S2 ; le zoom traversant de S3
  se pose en S4 ; le panneau de S4 rétrécit et devient la vignette du rapport S5 ; le point orange final de S5 devient la bille du logo S6.
- Logo Fly Scan’Air redessiné en vectoriel (le PNG n’est arrivé que comme aperçu dans la conversation, pas comme fichier) : serpentin gris
  tracé en direct, nom révélé par la même ligne de scan orange qu’en S3. Police : Fredoka 700, la plus proche disponible.
- Aucun chiffre inventé : pas de pourcentage de perte, pas de température.
- Musique originale (synthèse, 100 BPM), changements d’accords calés sur chaque scène ; 11 effets sonores ciblés.

## Mesuré / regardé
- `hyperframes check` : 0 erreur, 0 avertissement (lint, runtime, mise en page, contraste, rythme, audio).
- Planches de raccords : les 5 coupes sont continues (aucun saut visible à ±0,1 s).
- Planche téléphone (360 px) : titres lisibles ; étiquettes agrandies à 30–36 px après ce passage.
- Son : mesuré, **pas écouté**. Premier rendu à −17,3 LUFS (trop bas) → musique remontée à −15 LUFS (crête −1,5 dBTP) ;
  pics des effets calés une image après l’action à l’écran.
- Images décodées du MP4 vérifiées : polices chargées (Montserrat, Poppins, Fredoka), couleurs et tracés conformes.

## Corrigé pendant la revue
- Le tracé progressif sautait (GSAP arrondit `strokeDashoffset` en CSS) → animation de l’attribut SVG.
- Astérisques visibles dans « agir vite » → accents multi-mots.
- Reste de trait du HUD pendant le zoom S3 → masqué après retrait.
- Sortie S1 qui dépassait la coupe → raccourcie.
- Étiquette « Avant » posée sur la courbe → déplacée ; carton final recentré verticalement.
- GSAP chargé depuis un CDN bloqué au rendu → embarqué dans `assets/vendor/`.

## Point le plus faible
- S2 : le troisième terme « Défauts invisibles » s’allume avec le bouclier d’assurance, dont le lien n’est pas direct.
  Avec plus de temps : un troisième pictogramme discret (œil barré), ou le libellé « Garantie & assurance ».
- Le logo est une reconstitution : à valider face à l’original (ou fournir le fichier SVG/PNG pour un contrôle au pixel).

## Gardé volontairement
- Fin centrée (carton logo) : seul plan centré du film, les autres sont asymétriques.
- HUD sobre autour du drone (demandé par le cahier des charges, transition 5).
