#!/usr/bin/env python3
"""Voix off (FLORA — Gemini 3.1 Flash TTS, voix « Umbriel », fr-FR) : téléchargement, nettoyage, placement.

1. télécharge chaque phrase générée dans FLORA (assets/audio/vo/raw_XX.wav) ;
2. coupe les silences de début et de fin, normalise à -16 LUFS (assets/audio/vo/vo_XX.wav) ;
3. place chaque phrase dans sa scène ; si une phrase dépasse sa fenêtre, elle est légèrement accélérée
   (au plus x1,12, hauteur conservée) ; écrit assets/audio/vo/vo.json, lu par tools/build.py
   (pistes voix + atténuation de la musique sous la voix).

    python3 tools/voiceover.py            # télécharge puis traite
    python3 tools/voiceover.py --offline  # retraite les fichiers raw_XX.wav déjà présents
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VO_DIR = os.path.join(ROOT, "assets", "audio", "vo")
BASE = "https://media.flora.ai/node-inputs/2026/11/3/px78199r2h4zbzqw7mjp0659jx8hgcac"

# (id, run FLORA, début de scène, décalage dans la scène, fin de fenêtre absolue, texte)
LINES = [
    ("01", "m170bcwv0qx4nt99xpssgpz26d8hhbf6", 0.0, 0.9, 7.0,
     "Sur une toiture solaire, certains défauts restent totalement invisibles à l'œil nu."),
    ("02", "m1727fhvadwgj3kx3gc2a2w52s8hhmpy", 7.2, 0.45, 13.6,
     "Pourtant, ils font baisser le rendement, augmentent le risque d'incendie et fragilisent votre garantie."),
    ("03", "m1701etqdmbs0cs3s05v0syex18hgww5", 13.8, 0.5, 20.2,
     "Notre drone, équipé d'une caméra infrarouge, survole vos panneaux et révèle chaque échauffement."),
    ("04", "m17e57pvwm0ppxntect1mewzf18hghmv", 20.4, 0.6, 27.4,
     "Points chauds, diodes by-pass défectueuses, boîtes de jonction en surchauffe : chaque anomalie est localisée."),
    ("05", "m178gqwz34r99kc08kxs3zhfw58hhs86", 27.6, 0.5, 31.9,
     "Vous recevez ensuite un rapport détaillé : chaque défaut y est décrit et qualifié,"),
    ("06", "m170f6ptnpv9z50g3qawwjke2h8hg17x", 31.8, 0.35, 36.0,
     "classé par niveau de gravité, avec l'action à mener."),
    ("07", "m179b0j2z3xd0b1gqx84jdhe458hhav1", 36.0, 0.5, 40.1,
     "Un rapport aux normes, utile aussi auprès de votre assureur."),
    ("08", "m176pmnebw024ntrcy79s25pe98hgcw9", 40.2, 0.45, 46.6,
     "Bientôt, retrouvez vos rapports et planifiez vos prochaines inspections sur notre plateforme en ligne."),
    ("09", "m175rswf9b4qmwa8wx9ert80n18hg994", 46.8, 1.55, 50.3,
     "Fly Scan'Air. Révélez l'invisible."),
    ("10", "m170jg4gxm1hh6f9ybp699ze158hh6ha", 46.8, 3.75, 53.9,
     "Faites contrôler votre installation : rendez-vous sur notre site."),
]
GAP = 0.15  # silence minimal entre deux phrases qui se suivent


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main():
    offline = "--offline" in sys.argv
    os.makedirs(VO_DIR, exist_ok=True)
    placed, prev_end = [], 0.0
    for vid, run, scene, off, win_end, text in LINES:
        raw = os.path.join(VO_DIR, f"raw_{vid}.wav")
        if not offline:
            urllib.request.urlretrieve(f"{BASE}/gen-{run}-0.wav", raw)
        trimmed = os.path.join(VO_DIR, f"trim_{vid}.wav")
        ff("-i", raw, "-af",
           "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,"
           "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
           trimmed)
        start = max(scene + off, prev_end + GAP)
        d = duration(trimmed)
        room = win_end - start
        tempo = 1.0
        if d > room:
            tempo = min(d / room, 1.12)
        out = os.path.join(VO_DIR, f"vo_{vid}.wav")
        chain = (f"atempo={tempo:.4f}," if tempo > 1.0 else "") + "loudnorm=I=-16:TP=-1.5:LRA=7"
        ff("-i", trimmed, "-af", chain, "-ar", "48000", "-ac", "2", out)
        os.remove(trimmed)
        d = duration(out)
        placed.append(dict(id=vid, file=f"assets/audio/vo/vo_{vid}.wav", start=round(start, 3), dur=round(d, 3),
                           tempo=round(tempo, 3), window_end=win_end, text=text))
        flag = "  <-- DÉPASSE" if start + d > win_end + 0.05 else ""
        print(f"vo_{vid}: {start:6.2f} -> {start + d:6.2f} s (fenêtre {win_end:5.1f}, tempo x{tempo:.2f}){flag}")
        prev_end = start + d
    json.dump(placed, open(os.path.join(VO_DIR, "vo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote assets/audio/vo/vo.json")


if __name__ == "__main__":
    main()
