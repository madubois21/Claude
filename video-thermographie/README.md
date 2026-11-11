# Fly Scan’Air — vidéo motion design « Le contrôle thermographique appliqué aux installations photovoltaïques »

Vidéo full motion design de 74,4 s (version 13), 16:9 (1920 × 1080, 30 i/s), pensée pour LinkedIn, déclinée en 9:16 et 1:1.
Elle s’ouvre sur un titre et se termine sur le logo et le slogan.
Réalisée avec [HyperFrames](https://hyperframes.heygen.com) : HTML + SVG + GSAP, rendus en MP4 image par image.

## Livrables

| Livrable | Emplacement |
| --- | --- |
| Vidéo finale MP4 HD (version LinkedIn 16:9) | `renders/FlyScanAir_thermographie_16x9.mp4` (1920 × 1080) |
| Déclinaison verticale 9:16 | `renders/FlyScanAir_thermographie_9x16.mp4` (1080 × 1920) |
| Déclinaison carrée 1:1 | `renders/FlyScanAir_thermographie_1x1.mp4` (1080 × 1080) |
| Projet source | `index.html` + `compositions/s0.html` … `s8.html` (16:9) ; `formats/9x16/` et `formats/1x1/` (projets autonomes des déclinaisons) |
| Assets graphiques | tout est vectoriel dans les scènes (aucune photo de panneau) ; logo : lettres vectorisées depuis le logo fourni (`assets/images/logo-flyscanair.png` → `assets/logo-letters.json`, par `tools/logo_trace.py`), serpentin et billes remesurés sur la même image ; police Comfortaa `assets/fonts/` |
| Voix off (FLORA, Gemini 3.1 Flash TTS, voix « Umbriel », fr-FR) | `assets/audio/vo/raw_XX.wav` (fichiers FLORA d’origine), `vo_01.wav` … `vo_07.wav` (nettoyés et placés par `tools/voiceover.py`) |
| Musique (originale, libre de droits) | `assets/audio/music.wav` (générée par `tools/music.py`) |
| Effets sonores | `assets/audio/sfx/` (voir `CREDITS.md`) ; frappe au clavier (vraies touches découpées dans `typing.mp3`), son de validation des cases et bourdonnement du drone construits par `tools/sfx.py` |
| Pictogrammes | Phosphor Icons, graisse bold (licence MIT, `assets/images/LICENSE-phosphor.txt`) : tracés dans `assets/icons-phosphor.json` |
| Captures | site web : `assets/images/site-flyscanair.jpg` ; page LinkedIn : `assets/images/linkedin-flyscanair.jpg` (recadrée sur la page entreprise, sans barre de notifications ni relation personnelle) |
| Fiche technique | `SPEC.md` ; note de revue : `REVIEW.md` |

Voix off en français (7 phrases, voix masculine grave « Umbriel ») ; la musique, à 0,85 (−1,4 dB), s’efface sous la voix
(0,28, soit −11 dB) et remonte dans les silences ; elle baisse aussi un peu (0,5) pendant la frappe au clavier.
Pas de voix sur le titre, la plateforme, la recherche et le logo final (phrases à écrire plus tard).
Les textes à l’écran portent toujours le message seuls, pour la lecture sans le son sur LinkedIn.

| Scène | Voix off |
| --- | --- |
| 1 | « Sur une toiture solaire, certains défauts restent totalement invisibles à l’œil nu. » |
| 2 | « Pourtant, ils font baisser le rendement, augmentent le risque d’incendie et fragilisent votre garantie. » |
| 3 | « Notre drone, équipé d’une caméra infrarouge, survole vos panneaux et révèle chaque échauffement. » |
| 4 | « Points chauds, diodes by-pass défectueuses, boîtes de jonction en surchauffe : chaque anomalie est localisée. » |
| 5 | « Vous recevez ensuite un rapport détaillé : chaque défaut y est décrit et qualifié, classé par niveau de gravité, avec l’action à mener. Un rapport aux normes, utile aussi auprès de votre assureur. » |

## Structure

| Scène | Fichier | Temps | Contenu |
| --- | --- | --- | --- |
| 0 — Titre | `compositions/s0.html` | 0 – 3,6 s | « Le contrôle *thermographique* appliqué aux installations photovoltaïques », centré, filet orange |
| 1 — Le problème invisible | `compositions/s1.html` | 3,6 – 10,8 s | bâtiment tracé, point chaud, « Certaines anomalies sont invisibles à l’œil nu. » |
| 2 — Les enjeux | `compositions/s2.html` | 10,8 – 17,4 s | l’installation du survol (7 × 3 modules, pas encore inspectée) au centre de l’écran ; six pictogrammes (perte de rendement, échauffement, défaut électrique, risque incendie, garantie, assurance) arrivent de loin en spirale, gravitent autour de l’installation (plus grands en passant devant) puis s’échappent ; la caméra se rapproche et la question « Comment détecter ces anomalies ? » s’affiche |
| 3 — Inspection drone | `compositions/s3.html` | 17,4 – 24 s | même champ, même cadre, même question (raccord sans coupure), puis drone + HUD, scan infrarouge, « Le scan infrarouge révèle chaque échauffement. » |
| 4 — Détection | `compositions/s4.html` | 24 – 31,2 s | zoom sur le module : point chaud (cellule fissurée), diode by-pass, boîte de jonction, désignés par des lignes de rappel |
| 5 — Rapport | `compositions/s5.html` | 31,2 – 47,4 s | trois pages : analyse détaillée (fiches « Défaut #1 » et « Défaut #2 »), résultats et gravité, couverture « Rapport d’inspection thermique » (tampon « Conforme IEC TS 62446-3 ») avec le lien « Accéder à votre installation » ; les quatre cases de la checklist se cochent (son de validation), puis le curseur arrive, clique sur le lien et la fenêtre de la plateforme s’ouvre depuis le lien |
| 6 — Plateforme en ligne | `compositions/s6.html` | 47,4 – 55,8 s | « Suivez votre installation sur notre plateforme en ligne. » : carte de l’installation à gauche, liste des anomalies en haut à droite, vues IR et RVB du module sélectionné en bas à droite (en 9:16 : carte en haut, puis liste, puis vues) ; deux clics (point chaud B5, puis module à vide C3) |
| 7 — Retrouvez-nous | `compositions/s7.html` | 55,8 – 66 s | barre de recherche (loupe), frappe de « www.flyscanair.com » → capture du site ; puis « Fly Scan’Air » → page LinkedIn |
| 8 — Logo | `compositions/s8.html` | 66 – 74,4 s | le serpentin du logo se trace (bruit de drone), le nom apparaît au centre, le logo remonte, slogan « Inspections techniques aériennes, *révélez l’invisible*. », tenus ≈ 3,5 s jusqu’à la dernière image |

La plateforme n’affiche aucun nom ni logo de logiciel : elle est appelée « plateforme en ligne », dessinée aux couleurs
et en typographie Fly Scan’Air ; les valeurs de la liste sont illustratives et cohérentes avec le rapport de la scène 5
(7 défauts, 5 modules impactés, mêmes catégories).

Charte : fond blanc, traits noirs fins, accent `#FF5700`, typographie Comfortaa (textes et logotype).
Vocabulaire technique des anomalies repris de la note technique Fly Scan’Air (norme IEC TS 62446-3).

## Modifier les textes

Chaque scène déclare ses textes comme variables (`data-composition-variables` sur sa racine) :
`s0-title`, `s1-title`, `s2-k0`…`s2-k5` (légendes des pictogrammes), `s3-q` (question), `s3-title`, `s4-title`,
`s4-l1`…`s4-l3` (« principal|précision »), `s5-t1`…`s5-t3`, `s5-i0`…`s5-i3`, `s6-title`, `s7-head`,
`s8-slogan`.
Dans un texte : `|` force un retour à la ligne, `*mot*` ou `*deux mots*` passe en orange.
Les lignes de la plateforme sont dans `S6_ROWS`, les recherches dans `S7_Q` (`tools/build.py`).

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
montées et impacts aux changements de scène ; respiration pendant le tracé du serpentin, retombée quand le nom
apparaît, accord final à 72 s ; `MUSIC_DEBUG=1` affiche l’équilibre par bande). Les sections sont dans `SECTIONS`.

`python3 tools/sfx.py` régénère la frappe au clavier (vraies frappes découpées dans `typing.mp3`, une touche toutes
les 90 ms comme l’affichage des lettres, `TYPE_DT`), la touche Entrée, le son de validation des quatre cases du
rapport (`validation-1.wav` … `validation-4.wav`) et le bourdonnement du drone de la scène 8.

`python3 tools/voiceover.py` retraite la voix off à partir des fichiers FLORA `raw_XX.wav` : coupe les silences,
raccourcit les pauses trop longues, accélère très légèrement certaines phrases (×1,03 à ×1,04, hauteur conservée),
normalise à −16 LUFS et écrit `assets/audio/vo/vo.json` (placement de chaque phrase). Les débuts de phrase se règlent
dans `LINES` en tête du script ; relancer ensuite `tools/build.py` (les trois formats) pour mettre à jour les pistes
et l’atténuation de la musique. Pour ajouter ou changer une phrase : la générer dans FLORA avec la même voix, déposer
le `raw_XX.wav`, l’ajouter à `LINES`, relancer les deux scripts.

## Déclinaisons 9:16 et 1:1

Mêmes dessins, textes, minutage, transitions, voix off, musique et effets sonores que le 16:9 : seule la mise en page
s’adapte au cadre (orbite complète en 16:9 ; en 9:16 et 1:1, trois pictogrammes sur l’arc du haut et trois sur l’arc du bas,
pour que les légendes ne passent jamais sur l’installation ; caméra qui suit le drone en scène 3, étiquettes de la
scène 4 sous le panneau, lien du rapport sur deux lignes, volets de la plateforme empilés en 9:16, slogan sur trois
lignes). Les réglages de mise en page sont dans `LAYOUTS` et `P0` … `P8` en tête de `tools/build.py`.

```bash
python3 tools/build.py 9x16      # régénère formats/9x16/
python3 tools/build.py 1x1       # régénère formats/1x1/
```

Chaque dossier de `formats/` est un projet HyperFrames autonome (ses propres `assets/`) : on y lance
`npx hyperframes preview`, `check` ou `render` comme à la racine.
