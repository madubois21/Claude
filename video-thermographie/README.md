# Fly Scan’Air — vidéo motion design « Inspection thermographique par drone »

Vidéo full motion design de 40,8 s, 16:9 (1920 × 1080, 30 i/s), pensée pour LinkedIn.
Réalisée avec [HyperFrames](https://hyperframes.heygen.com) : HTML + SVG + GSAP, rendus en MP4 image par image.

## Livrables

| Livrable | Emplacement |
| --- | --- |
| Vidéo finale MP4 HD (version LinkedIn 16:9) | `renders/FlyScanAir_thermographie_16x9.mp4` |
| Projet source | `index.html` + `compositions/s1.html` … `s6.html` |
| Assets graphiques | tout est vectoriel dans les scènes ; logo redessiné en SVG dans `compositions/s6.html` ; police `assets/fonts/` |
| Musique (originale, libre de droits) | `assets/audio/music.wav` (générée par `tools/music.py`) |
| Effets sonores | `assets/audio/sfx/` (voir `CREDITS.md`) |
| Fiche technique | `SPEC.md` ; note de revue : `REVIEW.md` |

Pas de voix off (choix validé) : les textes à l’écran portent le message, ce qui convient aussi à la lecture sans le son sur LinkedIn.

## Structure

| Scène | Fichier | Temps | Contenu |
| --- | --- | --- | --- |
| 1 — Le problème invisible | `compositions/s1.html` | 0 – 7,2 s | bâtiment tracé, point chaud, « Certaines anomalies sont invisibles à l’œil nu. » |
| 2 — Les risques | `compositions/s2.html` | 7,2 – 13,2 s | le sol devient l’axe du graphique, rendement qui chute, icônes incendie + assurance |
| 3 — Inspection drone | `compositions/s3.html` | 13,2 – 21 s | champ de panneaux, drone + HUD, ligne de scan orange qui révèle la vue thermique |
| 4 — Détection | `compositions/s4.html` | 21 – 27,6 s | zoom sur le panneau, points chauds pulsants, défauts entourés automatiquement |
| 5 — Rapport | `compositions/s5.html` | 27,6 – 34,2 s | le panneau devient la vignette du rapport, checklist, courbe qui remonte |
| 6 — Call to action | `compositions/s6.html` | 34,2 – 40,8 s | le serpentin du logo se trace, le scan révèle « Fly Scan’Air », slogan + message |

Charte : fond blanc, traits noirs fins, accent `#FF5700`, Montserrat / Poppins (+ Fredoka pour le logotype).

## Modifier les textes

Chaque scène déclare ses textes comme variables (`data-composition-variables` sur sa racine) :
`s1-title`, `s2-t1`…`s2-t3`, `s3-title`, `s4-title`, `s4-l1`…`s4-l3`, `s5-title`, `s5-i0`…`s5-i2`,
`s6-slogan`, `s6-msg`, `s6-contact` (vide par défaut : ajoutez site web / téléphone).
Dans un texte : `|` force un retour à la ligne, `*mot*` ou `*deux mots*` passe en orange.

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

## Déclinaisons

Le 9:16 et le 1:1 ne sont pas encore faits (choix : valider d’abord le style en 16:9).
