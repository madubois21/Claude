#!/usr/bin/env python3
"""Découpe une voix off lue d'une traite (une seule génération FLORA) en phrases : raw_01.wav … raw_NN.wav.

Les phrases sont celles de LINES dans tools/voiceover.py. Chaque coupure est placée au milieu d'une pause :
pour chaque frontière, on prend la pause qui maximise « longueur de la pause − 0,15 × écart à la position attendue »
(position attendue = proportion de caractères du texte déjà lu). Le script affiche les coupures et la durée de chaque
phrase pour vérification.

    python3 tools/voice_split.py chemin/vers/voix-complete.mp3
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voiceover import LINES, SR, VO_DIR, read_pcm, speech_runs, write_pcm  # noqa: E402


def main(src):
    x = read_pcm(src)
    dur = len(x) / SR
    runs = speech_runs(x, thr_db=-40.0)
    gaps = [((runs[k][1] + runs[k + 1][0]) / 2, runs[k + 1][0] - runs[k][1]) for k in range(len(runs) - 1)]
    texts = [t for *_, t in LINES]
    total = sum(len(t) for t in texts)
    t0, t1 = runs[0][0], runs[-1][1]
    cuts, used, acc = [], set(), 0
    for t in texts[:-1]:
        acc += len(t)
        expect = t0 + (t1 - t0) * acc / total
        best = max((g for g in range(len(gaps)) if g not in used and (not cuts or gaps[g][0] > cuts[-1])),
                   key=lambda g: gaps[g][1] - 0.15 * abs(gaps[g][0] - expect))
        used.add(best)
        cuts.append(gaps[best][0])
        print(f"coupure {len(cuts)} : {gaps[best][0]:6.2f} s (pause {gaps[best][1]:.2f} s, attendue vers {expect:5.2f} s)")
    bounds = [0.0] + cuts + [dur]
    for (vid, *_rest), a, b in zip(LINES, bounds[:-1], bounds[1:]):
        out = os.path.join(VO_DIR, f"raw_{vid}.wav")
        write_pcm(out, x[int(a * SR): int(b * SR)])
        print(f"raw_{vid}.wav : {a:6.2f} -> {b:6.2f} s ({b - a:4.2f} s)  {_rest[-1][:60]}")


if __name__ == "__main__":
    main(sys.argv[1])
