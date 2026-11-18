#!/usr/bin/env python3
"""Musique de la version 21 : « Tech Background Music » (ElevenLabs Music v2.5, générée dans FLORA, instrumentale, 90 s).

La piste source est dans assets/audio/source/tech-background-music.mp3. Ce script :
1. repère la fin naturelle du morceau (dernier instant audible) ;
2. découpe la piste pour que cette fin tombe sur la dernière image de la vidéo (durée TOTAL de tools/build.py) :
   le début de la vidéo commence donc au milieu du morceau, avec une montée du son de 1 s ;
3. normalise à -16 LUFS (loudnorm en deux passes, linéaire) -> assets/audio/music.wav (48 kHz, stéréo).
Le niveau sous la voix et le reste du mixage sont réglés dans tools/build.py (piste « music », automation de volume).
tools/music.py (musique synthétisée des versions précédentes) n'est plus utilisé.

    python3 tools/music_import.py [durée totale, 76.4 par défaut]
"""
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "audio", "source", "tech-background-music.mp3")
OUT = os.path.join(ROOT, "assets", "audio", "music.wav")
SR = 48000
TOTAL = float(sys.argv[1]) if len(sys.argv) > 1 else 76.4
FADE_IN = 1.0


def main():
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SRC, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    hop = int(0.05 * SR)
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(rms + 1e-9)
    end = (np.nonzero(db > -50)[0][-1] + 1) * 0.05  # dernier instant audible
    start = max(0.0, end - TOTAL)
    print(f"source {len(x) / SR:.2f} s, fin audible {end:.2f} s -> extrait {start:.2f}–{start + TOTAL:.2f} s")
    tmp = os.path.join(ROOT, "tools", ".music_cut.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{TOTAL:.3f}", "-i", SRC,
                    "-af", f"afade=t=in:st=0:d={FADE_IN},afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6", "-ar", str(SR), "-ac", "2", tmp],
                   check=True)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    m = json.loads(log[log.rindex("{"): log.rindex("}") + 1])
    chain = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
             f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-af", chain, "-ar", str(SR), "-ac", "2", OUT], check=True)
    os.remove(tmp)
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
