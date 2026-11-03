# Fly Scan’Air — vidéo motion design « Inspection thermographique par drone »

Vidéo full motion design de 40,8 s, 16:9 (1920 × 1080, 30 i/s), pensée pour LinkedIn.
Réalisée avec [HyperFrames](https://hyperframes.heygen.com) : HTML + SVG + GSAP, rendus en MP4 image par image.

## Livrables

| Livrable | Emplacement |
| --- | --- |
| Vidéo finale MP4 HD (version LinkedIn 16:9) | `renders/FlyScanAir_thermographie_16x9.mp4` (1920 × 1080) |
| Déclinaison verticale 9:16 | `renders/FlyScanAir_thermographie_9x16.mp4` (1080 × 1920) |
| Déclinaison carrée 1:1 | `renders/FlyScanAir_thermographie_1x1.mp4` (1080 × 1080) |
| Projet source | `index.html` + `compositions/s1.html` … `s6.html` (16:9) ; `formats/9x16/` et `formats/1x1/` (projets autonomes des déclinaisons) |
| Assets graphiques | tout est vectoriel dans les scènes ; logo redessiné en SVG dans `compositions/s6.html` ; police Comfortaa `assets/fonts/` |
| Musique (originale, libre de droits) | `assets/audio/music.wav` (générée par `tools/music.py`) |
| Effets sonores | `assets/audio/sfx/` (voir `CREDITS.md`) |
| Fiche technique | `SPEC.md` ; note de revue : `REVIEW.md` |

Pas de voix off (choix validé) : les textes à l’écran portent le message, ce qui convient aussi à la lecture sans le son sur LinkedIn.

## Structure

| Scène | Fichier | Temps | Contenu |
| --- | --- | --- | --- |
| 1 — Le problème invisible | `compositions/s1.html` | 0 – 7,2 s | bâtiment tracé, point chaud, « Certaines anomalies sont invisibles à l’œil nu. » |
| 2 — Les risques | `compositions/s2.html` | 7,2 – 13,2 s | le sol devient l’axe du graphique « Rendement (%) » (installation saine vs avec défauts), icônes incendie + assurance |
| 3 — Inspection drone | `compositions/s3.html` | 13,2 – 21 s | champ de panneaux, drone + HUD, ligne de scan orange qui révèle la vue thermique |
| 4 — Détection | `compositions/s4.html` | 21 – 27,6 s | zoom sur le panneau, points chauds pulsants, défauts entourés automatiquement |
| 5 — Rapport | `compositions/s5.html` | 27,6 – 34,2 s | le panneau devient la vignette du rapport, checklist, histogramme « Production (kWh/an) » |
| 6 — Call to action | `compositions/s6.html` | 34,2 – 40,8 s | le serpentin du logo se trace, le scan révèle « Fly Scan’Air », slogan, message, site / téléphone / e-mail |

Charte : fond blanc, traits noirs fins, accent `#FF5700`, typographie Comfortaa (textes et logotype).

## Modifier les textes

Chaque scène déclare ses textes comme variables (`data-composition-variables` sur sa racine) :
`s1-title`, `s2-t1`…`s2-t3`, `s3-title`, `s4-title`, `s4-l1`…`s4-l3`, `s5-title`, `s5-i0`…`s5-i2`,
`s6-slogan`, `s6-msg`, `s6-contact` (éléments séparés par `|`).
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

`python3 tools/music.py` régénère la musique (synthèse déterministe, 100 BPM, la mineur → do majeur).

## Déclinaisons 9:16 et 1:1

Mêmes dessins, textes, minutage, transitions, musique et effets sonores que le 16:9 : seule la mise en page
s’adapte au cadre (blocs empilés en vertical, caméra qui suit le drone en scène 3, étiquettes de la scène 4
placées sous le panneau, slogan et coordonnées sur plusieurs lignes). Les réglages de mise en page sont dans
`LAYOUTS` en tête de `tools/build.py`.

```bash
python3 tools/build.py 9x16      # régénère formats/9x16/
python3 tools/build.py 1x1       # régénère formats/1x1/
```

Chaque dossier de `formats/` est un projet HyperFrames autonome (ses propres `assets/`) : on y lance
`npx hyperframes preview`, `check` ou `render` comme à la racine.
