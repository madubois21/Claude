#!/usr/bin/env python3
"""Bruitages synthétisés pour la version 13 (déterministes, numpy) -> assets/audio/sfx/.

- typing-18.wav / typing-12.wav : frappe au clavier, une touche toutes les 75 ms (même cadence que
  l'affichage des lettres dans tools/build.py, TYPE_DT), à partir de l'échantillon key-press.mp3
  (hauteur et force légèrement variées d'une touche à l'autre, barre d'espace plus grave) ;
- drone-buzz.wav : bourdonnement d'un drone quadrirotor (4 rotors légèrement désaccordés, sifflement
  des moteurs, souffle), qui traverse l'image de gauche à droite pendant le tracé du serpentin du logo.
Les pics sont inscrits dans peaks.json (lu par tools/build.py pour caler chaque son sur l'image).

    python3 tools/sfx.py
"""
import json
import os
import subprocess

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "assets", "audio", "sfx")
SR = 48000
TYPE_DT = 0.075
LEAD = 0.1  # instant de la première touche dans le fichier
TEXTS = {"typing-18.wav": "www.flyscanair.com", "typing-12.wav": "Fly Scan'Air"}


def read(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(float)


def write(path, st):
    st = np.clip(st, -1, 1)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", path],
                   input=st.astype(np.float32).tobytes(), check=True)


def soften(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 2), len(x))


def typing():
    key = read(os.path.join(SFX, "key-press.mp3"))
    peak = int(np.argmax(np.abs(key)))
    key = key[: int(0.24 * SR)]
    fade = int(0.06 * SR)
    key[-fade:] *= np.linspace(1, 0, fade)
    rng = np.random.default_rng(1311)
    peaks = {}
    for name, text in TEXTS.items():
        n = int((LEAD + len(text) * TYPE_DT + 0.4) * SR)
        st = np.zeros((n, 2))
        for i, ch in enumerate(text):
            rate = 0.86 if ch == " " else rng.uniform(0.93, 1.08)  # hauteur
            gain = 1.0 if ch == " " else rng.uniform(0.7, 0.95)
            src = np.interp(np.arange(0, len(key) - 1, rate), np.arange(len(key)), key)
            t = LEAD + i * TYPE_DT + rng.uniform(-0.006, 0.006)
            i0 = int(round(t * SR)) - int(round(peak / rate))
            pan = rng.uniform(-0.25, 0.25)
            seg = src[: n - i0] * gain
            st[i0:i0 + len(seg), 0] += seg * np.cos((pan + 1) * np.pi / 4)
            st[i0:i0 + len(seg), 1] += seg * np.sin((pan + 1) * np.pi / 4)
        st *= 0.7 / np.max(np.abs(st))
        write(os.path.join(SFX, name), st)
        peaks[name] = LEAD
        print("wrote", name, f"({len(text)} touches)")
    return peaks


def drone(dur=2.75):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / dur
    rng = np.random.default_rng(7)
    f0 = 196 * (1 + 0.035 * np.sin(np.pi * x))  # le régime monte un peu au milieu du trajet
    out = np.zeros(n)
    for det, ph in ((1.0, 0.0), (1.013, 1.1), (0.988, 2.3), (1.021, 3.7)):  # quatre rotors
        phase = 2 * np.pi * np.cumsum(f0 * det) / SR + ph
        rotor = sum(np.sin(k * phase + 0.4 * k) / k ** 1.15 for k in range(1, 14))
        out += rotor * (1 + 0.18 * np.sin(2 * np.pi * (10.5 + det) * t + ph))
    whine = np.sin(2 * np.pi * np.cumsum(f0 * 8.2) / SR) * 0.07  # moteurs
    noise = rng.standard_normal(n)
    wash = soften(noise - soften(noise, 300), 2600) * 0.5
    sig = soften(out * 0.22 + whine + wash, 4200)
    e = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.6) ** 1.5
    sig *= e
    pan = -0.65 + 1.3 * x  # traverse l'image de gauche à droite, comme le serpentin
    st = np.stack([sig * np.cos((pan + 1) * np.pi / 4), sig * np.sin((pan + 1) * np.pi / 4)], axis=1)
    st *= 0.6 / np.max(np.abs(st))
    write(os.path.join(SFX, "drone-buzz.wav"), st)
    print("wrote drone-buzz.wav")
    return {"drone-buzz.wav": 0.0}


if __name__ == "__main__":
    pk_path = os.path.join(SFX, "peaks.json")
    peaks = json.load(open(pk_path)) if os.path.exists(pk_path) else {}
    peaks.update(typing())
    peaks.update(drone())
    json.dump(peaks, open(pk_path, "w"), indent=1)
    print("wrote peaks.json")
