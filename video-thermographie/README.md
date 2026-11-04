# Fly Scan’Air — vidéo motion design « Inspection thermographique par drone »

Vidéo full motion design de 60 s, qui se termine sur le site web et LinkedIn, 16:9 (1920 × 1080, 30 i/s), pensée pour LinkedIn, déclinée en 9:16 et 1:1.
Réalisée avec [HyperFrames](https://hyperframes.heygen.com) : HTML + SVG + GSAP, rendus en MP4 image par image.

## Livrables

| Livrable | Emplacement |
| --- | --- |
| Vidéo finale MP4 HD (version LinkedIn 16:9) | `renders/FlyScanAir_thermographie_16x9.mp4` (1920 × 1080) |
| Déclinaison verticale 9:16 | `renders/FlyScanAir_thermographie_9x16.mp4` (1080 × 1920) |
| Déclinaison carrée 1:1 | `renders/FlyScanAir_thermographie_1x1.mp4` (1080 × 1080) |
| Projet source | `index.html` + `compositions/s1.html` … `s7.html` (16:9) ; `formats/9x16/` et `formats/1x1/` (projets autonomes des déclinaisons) |
| Assets graphiques | tout est vectoriel dans les scènes ; logo : lettres vectorisées depuis le logo fourni (`assets/images/logo-flyscanair.png` → `assets/logo-letters.json`, par `tools/logo_trace.py`), serpentin et billes remesurés sur la même image ; police Comfortaa `assets/fonts/` |
| Voix off (FLORA, Gemini 3.1 Flash TTS, voix « Umbriel », fr-FR) | `assets/audio/vo/raw_01.wav` … `raw_10.wav` (fichiers FLORA d’origine), `vo_01.wav` … `vo_10.wav` (nettoyés et placés par `tools/voiceover.py`) |
| Musique (originale, libre de droits) | `assets/audio/music.wav` (générée par `tools/music.py`) |
| Effets sonores | `assets/audio/sfx/` (voir `CREDITS.md`) |
| Icônes incendie et assurance | Phosphor Icons « fire » et « shield-check » (licence MIT, `assets/images/LICENSE-phosphor.txt`) |
| Capture du site, logo LinkedIn | `assets/images/site-flyscanair.jpg` ; logo LinkedIn : icône Font Awesome Free (CC BY 4.0, `assets/images/LICENSE-fontawesome.txt`) |
| Fiche technique | `SPEC.md` ; note de revue : `REVIEW.md` |

Voix off en français (10 phrases, voix masculine grave « Umbriel ») ; la musique, à 0,85 (−1,4 dB), s’efface sous la voix
(0,28, soit −11 dB) et remonte dans les silences. Les textes à l’écran portent toujours le message seuls, pour la lecture sans le son sur LinkedIn.

| Scène | Voix off |
| --- | --- |
| 1 | « Sur une toiture solaire, certains défauts restent totalement invisibles à l’œil nu. » |
| 2 | « Pourtant, ils font baisser le rendement, augmentent le risque d’incendie et fragilisent votre garantie. » |
| 3 | « Notre drone, équipé d’une caméra infrarouge, survole vos panneaux et révèle chaque échauffement. » |
| 4 | « Points chauds, diodes by-pass défectueuses, boîtes de jonction en surchauffe : chaque anomalie est localisée. » |
| 5 | « Vous recevez ensuite un rapport détaillé : chaque défaut y est décrit et qualifié, classé par niveau de gravité, avec l’action à mener. Un rapport aux normes, utile aussi auprès de votre assureur. » |
| 6 | « Bientôt, retrouvez vos rapports et planifiez vos prochaines inspections sur notre plateforme en ligne. » |
| 7 | « Fly Scan’Air. Révélez l’invisible. Faites contrôler votre installation : rendez-vous sur notre site. » |

## Structure

| Scène | Fichier | Temps | Contenu |
| --- | --- | --- | --- |
| 1 — Le problème invisible | `compositions/s1.html` | 0 – 7,2 s | bâtiment tracé, point chaud, « Certaines anomalies sont invisibles à l’œil nu. » |
| 2 — Les risques | `compositions/s2.html` | 7,2 – 13,8 s | graphique « Rendement (%) » (installation saine vs avec défauts), icônes incendie + assurance |
| 3 — Inspection drone | `compositions/s3.html` | 13,8 – 20,4 s | champ de panneaux, drone schématique + HUD, balayage thermique rapide (1,5 s) |
| 4 — Détection | `compositions/s4.html` | 20,4 – 27,6 s | zoom sur le module thermique (48 cellules) : point chaud (cellule fissurée), sous-chaîne échauffée (diode by-pass), boîte de jonction ; désignés par des lignes de rappel |
| 5 — Rapport | `compositions/s5.html` | 27,6 – 43,2 s | trois pages : analyse détaillée (vignette thermique avec cadre de détection et plan de localisation dans la page ; à côté, fiches « Défaut #1 » et « Défaut #2 » au format des rapports Fly Scan’Air : catégorie, statut, type, ΔT / MaxT, origine, action, note) ; résultats et gravité (+ histogramme production) ; couverture « Rapport d’inspection thermique » avec tampon « Conforme IEC TS 62446-3 » et checklist |
| 6 — Plateforme en ligne | `compositions/s6.html` | 43,2 – 49,8 s | le rapport rejoint la plateforme : plan thermique, rapports, planning des inspections à venir — « Bientôt disponible » |
| 7 — Fin | `compositions/s7.html` | 49,8 – 60 s | logo, slogan, message, puis site web (capture animée) + LinkedIn (linkedin.com/company/fly-scan-air) + coordonnées, tenus à l’écran jusqu’à la fin (≈ 4,8 s) |

Charte : fond blanc, traits noirs fins, accent `#FF5700`, typographie Comfortaa (textes et logotype).
Vocabulaire technique des anomalies repris de la note technique Fly Scan’Air (norme IEC TS 62446-3).

## Modifier les textes

Chaque scène déclare ses textes comme variables (`data-composition-variables` sur sa racine) :
`s1-title`, `s2-t1`…`s2-t3`, `s3-title`, `s4-title`, `s4-l1`…`s4-l3` (« principal|précision »), `s5-t1`…`s5-t3`,
`s5-i0`…`s5-i3`, `s6-title`, `s7-slogan`, `s7-msg`, `s7-url`, `s7-inname`, `s7-inurl`, `s7-contact` (éléments séparés par `|`).
La mention « Bientôt disponible » de la scène 6 se retire dans `tools/build.py` (élément `s6-tag`) au lancement de la plateforme.
Dans un texte : `|` force un retour à la ligne, `*mot*` ou `*deux mots*` passe en orange.

Les données des graphiques sont en tête de `tools/build.py` : `S2_SAINE`, `S2_DEFAUT` (rendement en %, par mois) et
`S5_BARS` (production en kWh/an).

## Commandes

```bash
npx hyperframes preview          # aperçu dans le navigateur (Studio)
npx hyperframes check            # vérifications (lint, mise en page, contraste, rythme, audio)
npx hyperframes render --quality delivery -o renders/FlyScanAir_thermographie_16x9.mp4
```

La géométrie (perspective du toit, champ de panneaux, raccords de zoom au pixel près) est calculée par
`tools/build.py`, qui écrit `index.html` et `compositions/*.html`. **Relancer `python3 tools/build.py`
écrase les HTML** : soit vous modifiez le script puis le relancez, soit vous retouchez directement les HTML
(dans Studio ou à la main) et vous ne relancez plus le script.

`python3 tools/logo_trace.py` revectorise les lettres du logo à partir de `assets/images/logo-flyscanair.png`
(nécessite `pip install potracer`) ; le résultat, `assets/logo-letters.json`, est lu par `tools/build.py`.

`python3 tools/music.py` régénère la musique (synthèse déterministe, électro-pop 100 BPM en mi mineur / sol majeur :
grosse caisse à la noire, clap, charleston en doubles-croches, basse pompée, accords sur les contretemps, arpège,
montées et impacts aux changements de scène, accord final à 57 s ; `MUSIC_DEBUG=1` affiche l’équilibre par bande).

`python3 tools/voiceover.py` retraite la voix off à partir des fichiers FLORA `raw_XX.wav` : coupe les silences,
raccourcit les pauses trop longues, accélère très légèrement certaines phrases (×1,02 à ×1,04, hauteur conservée),
normalise à −16 LUFS et écrit `assets/audio/vo/vo.json` (placement de chaque phrase). Les débuts de phrase se règlent
dans `LINES` en tête du script ; relancer ensuite `tools/build.py` (les trois formats) pour mettre à jour les pistes
et l’atténuation de la musique. Pour changer une phrase : la régénérer dans FLORA avec la même voix, remplacer le
`raw_XX.wav` correspondant, relancer les deux scripts.

## Déclinaisons 9:16 et 1:1

Mêmes dessins, textes, minutage, transitions, voix off, musique et effets sonores que le 16:9 : seule la mise en page
s’adapte au cadre (blocs empilés en vertical, caméra qui suit le drone en scène 3, étiquettes de la scène 4
placées sous le panneau, slogan et coordonnées sur plusieurs lignes). Les réglages de mise en page sont dans
`LAYOUTS` en tête de `tools/build.py`.

```bash
python3 tools/build.py 9x16      # régénère formats/9x16/
python3 tools/build.py 1x1       # régénère formats/1x1/
```

Chaque dossier de `formats/` est un projet HyperFrames autonome (ses propres `assets/`) : on y lance
`npx hyperframes preview`, `check` ou `render` comme à la racine.
