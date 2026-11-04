#!/usr/bin/env python3
"""Voix off (FLORA — Gemini 3.1 Flash TTS, voix « Umbriel », fr-FR) : nettoyage et placement.

Les 10 phrases ont été générées dans FLORA puis déposées dans assets/audio/vo/raw_XX.wav (24 kHz mono).
Ce script, déterministe :
1. coupe les silences de début et de fin ;
2. raccourcit les pauses internes trop longues (au plus `pause` secondes, fondu de 12 ms aux raccords) ;
3. accélère légèrement si demandé (`tempo`, au plus x1,06 ici, hauteur conservée) ;
4. normalise à -16 LUFS (loudnorm en deux passes, linéaire), 48 kHz stéréo -> assets/audio/vo/vo_XX.wav ;
5. écrit assets/audio/vo/vo.json (début, durée, segments de parole), lu par tools/build.py
   (pistes voix + atténuation de la musique sous la voix).

    python3 tools/voiceover.py              # retraite les fichiers raw_XX.wav présents
    python3 tools/voiceover.py --download   # retélécharge d'abord les fichiers depuis FLORA
"""
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VO_DIR = os.path.join(ROOT, "assets", "audio", "vo")
BASE = "https://media.flora.ai/node-inputs/2026/11/3/px78199r2h4zbzqw7mjp0659jx8hgcac"
SR = 48000

# (id, run FLORA, début absolu (s), pause interne max (s), tempo, texte)
# Placement calé sur l'image : S1 0–7,2 · S2 7,2–13,8 · S3 13,8–31,8 (survol + « Le saviez-vous ? ») · S4 31,8–39,0 ·
# S5 39,0–56,4 · S6 56,4–63,0 · S7 63,0–73,2 (fin sur le site web et LinkedIn).
# Phrases 11 et 12 : repères pédagogiques de la note technique Fly Scan'Air (§ 3.2 : ≈ 600 W/m² ; § 2.1 : 0,5 % par degré).
LINES = [
    ("01", "m170bcwv0qx4nt99xpssgpz26d8hhbf6", 0.90, 0.30, 1.00,
     "Sur une toiture solaire, certains défauts restent totalement invisibles à l'œil nu."),
    ("02", "m1727fhvadwgj3kx3gc2a2w52s8hhmpy", 7.15, 0.30, 1.00,
     "Pourtant, ils font baisser le rendement, augmentent le risque d'incendie et fragilisent votre garantie."),
    ("03", "m1701etqdmbs0cs3s05v0syex18hgww5", 14.20, 0.30, 1.00,
     "Notre drone, équipé d'une caméra infrarouge, survole vos panneaux et révèle chaque échauffement."),
    ("11", "m176zqkkr1pa3q98st5heagk558hkg4a", 20.45, 0.30, 1.00,
     "La mesure se fait en plein soleil : dès six cents watts par mètre carré, chaque défaut se révèle."),
    ("12", "m17748jn99k90hy2nwp7c6edws8hk9rj", 25.65, 0.30, 1.00,
     "Chaque degré de trop coûte un demi pour cent de rendement : dix degrés, c'est déjà cinq pour cent de perte."),
    ("04", "m17e57pvwm0ppxntect1mewzf18hghmv", 32.05, 0.24, 1.03,
     "Points chauds, diodes by-pass défectueuses, boîtes de jonction en surchauffe : chaque anomalie est localisée."),
    ("05", "m178gqwz34r99kc08kxs3zhfw58hhs86", 41.40, 0.24, 1.04,
     "Vous recevez ensuite un rapport détaillé : chaque défaut y est décrit et qualifié,"),
    ("06", "m170f6ptnpv9z50g3qawwjke2h8hg17x", 47.35, 0.24, 1.04,
     "classé par niveau de gravité, avec l'action à mener."),
    ("07", "m179b0j2z3xd0b1gqx84jdhe458hhav1", 50.85, 0.24, 1.04,
     "Un rapport aux normes, utile aussi auprès de votre assureur."),
    ("08", "m176pmnebw024ntrcy79s25pe98hgcw9", 56.65, 0.30, 1.00,
     "Bientôt, retrouvez vos rapports et planifiez vos prochaines inspections sur notre plateforme en ligne."),
    ("09", "m175rswf9b4qmwa8wx9ert80n18hg994", 63.15, 0.26, 1.00,
     "Fly Scan'Air. Révélez l'invisible."),
    ("10", "m170jg4gxm1hh6f9ybp699ze158hh6ha", 66.40, 0.30, 1.02,
     "Faites contrôler votre installation : rendez-vous sur notre site."),
]
GAP = 0.15  # silence minimal entre deux phrases
END = 72.2  # la voix doit être terminée avant la dernière seconde


def ff(*args, capture=False):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "info" if capture else "error", "-y", *args],
                       check=True, capture_output=True, text=True)
    return r.stderr


def read_pcm(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def write_pcm(path, x):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-i", "-", path],
                   input=x.astype(np.float32).tobytes(), check=True)


def speech_runs(x, thr_db=-38.0, min_sil=0.12, hop=0.01):
    """Segments de parole [(début, fin)] en secondes : silence = RMS sous `thr_db` pendant au moins `min_sil`."""
    h = int(hop * SR)
    nfr = len(x) // h
    rms = np.sqrt(np.mean(x[: nfr * h].reshape(nfr, h) ** 2, axis=1) + 1e-12)
    loud = 20 * np.log10(rms) > thr_db
    runs, i = [], 0
    while i < nfr:
        if loud[i]:
            j = i
            while j < nfr and loud[j]:
                j += 1
            runs.append([i * hop, j * hop])
            i = j
        else:
            i += 1
    merged = []
    for r in runs:  # fusionne les trous plus courts que min_sil (consonnes, souffle)
        if merged and r[0] - merged[-1][1] < min_sil:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return merged


def tighten(x, runs, max_pause, lead=0.04, tail=0.10, fade=0.012):
    """Garde la parole, borne chaque pause interne à `max_pause`, ajoute `lead`/`tail` de silence naturel."""
    f = int(fade * SR)
    ramp_in, ramp_out = np.linspace(0, 1, f), np.linspace(1, 0, f)
    out, segs, t = [], [], 0.0
    for k, (a, b) in enumerate(runs):
        pad_a = lead if k == 0 else 0.0
        pad_b = tail if k == len(runs) - 1 else 0.0
        if k > 0:
            gap = a - runs[k - 1][1]
            keep = min(gap, max_pause)
            # la pause conservée est prise sur le silence réel (souffle compris), à cheval sur les deux bords
            pad_a = keep / 2
            out[-1] = np.concatenate([out[-1], x[int(runs[k - 1][1] * SR): int((runs[k - 1][1] + keep / 2) * SR)]])
            t += keep / 2
        i0, i1 = max(int((a - pad_a) * SR), 0), min(int((b + pad_b) * SR), len(x))
        seg = x[i0:i1].copy()
        if len(seg) > 2 * f:
            seg[:f] *= ramp_in
            if k == len(runs) - 1:
                seg[-f:] *= ramp_out
        if out and len(out[-1]) > f:
            out[-1][-f:] *= ramp_out
        segs.append([round(t + pad_a, 3), round(t + (i1 - i0) / SR - pad_b, 3)])
        out.append(seg)
        t += (i1 - i0) / SR
    return np.concatenate(out), segs


def loudnorm(src, dst, tempo):
    pre = f"atempo={tempo:.4f}," if tempo != 1.0 else ""
    log = ff("-i", src, "-af", pre + "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-", capture=True)
    m = json.loads(log[log.rindex("{"): log.rindex("}") + 1])
    chain = (pre + f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
             f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ff("-i", src, "-af", chain, "-ar", str(SR), "-ac", "2", dst)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main():
    download = "--download" in sys.argv
    os.makedirs(VO_DIR, exist_ok=True)
    placed, prev_end, ok = [], 0.0, True
    for vid, run, start, max_pause, tempo, text in LINES:
        raw = os.path.join(VO_DIR, f"raw_{vid}.wav")
        if not download and not os.path.exists(raw):
            print(f"vo_{vid}: raw_{vid}.wav absent (à déposer depuis FLORA, run_{run}) : phrase ignorée")
            ok = False
            continue
        if download:
            urllib.request.urlretrieve(f"{BASE}/gen-{run}-0.wav", raw)
        x = read_pcm(raw)
        y, segs = tighten(x, speech_runs(x), max_pause)
        tight = os.path.join(VO_DIR, f"tight_{vid}.wav")
        write_pcm(tight, y)
        out = os.path.join(VO_DIR, f"vo_{vid}.wav")
        loudnorm(tight, out, tempo)
        os.remove(tight)
        d = duration(out)
        segs = [[round(start + a / tempo, 3), round(start + b / tempo, 3)] for a, b in segs]
        placed.append(dict(id=vid, file=f"assets/audio/vo/vo_{vid}.wav", start=start, dur=round(d, 3),
                           tempo=tempo, raw=round(len(x) / SR, 3), speech=segs, text=text))
        warn = ""
        if start < prev_end + GAP - 1e-6:
            warn, ok = "  <-- CHEVAUCHE la phrase précédente", False
        if start + d > END + 1e-6:
            warn, ok = "  <-- DÉPASSE la fin de la vidéo", False
        print(f"vo_{vid}: {start:6.2f} -> {start + d:6.2f} s  x{tempo:.2f}  "
              f"({len(x) / SR:4.2f} s brut -> {d:4.2f} s)  parole {' '.join(f'{a:.2f}-{b:.2f}' for a, b in segs)}{warn}")
        prev_end = start + d
    json.dump(placed, open(os.path.join(VO_DIR, "vo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote assets/audio/vo/vo.json" + ("" if ok else "  (avec des avertissements)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
