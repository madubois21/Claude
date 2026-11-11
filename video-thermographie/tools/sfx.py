#!/usr/bin/env python3
"""Bruitages construits pour la vidéo (déterministes, numpy) -> assets/audio/sfx/.

- typing-18.wav / typing-12.wav : frappe au clavier, une touche toutes les 90 ms (même cadence que l'affichage
  des lettres dans tools/build.py, TYPE_DT). Chaque touche est une vraie frappe découpée dans l'enregistrement
  typing.mp3 (11 touches différentes, jouées dans un ordre qui ne se répète pas) ; barre d'espace plus grave ;
- key-enter.wav : touche Entrée (la frappe la plus franche de l'enregistrement, un peu plus grave) ;
- validation-1.wav … validation-4.wav : son de validation des cases cochées du rapport (deux notes montantes,
  timbre doux de type marimba, un cran plus haut à chaque case : sol – la – si – ré, dans la tonalité de la musique) ;
- drone-buzz.wav : bourdonnement d'un drone quadrirotor (4 rotors légèrement désaccordés, sifflement des moteurs,
  souffle), qui traverse l'image de gauche à droite pendant le tracé du serpentin du logo.
Les instants des pics sont inscrits dans peaks.json (lu par tools/build.py pour caler chaque son sur l'image).

    python3 tools/sfx.py
"""
import json
import os
import subprocess

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "assets", "audio", "sfx")
SR = 48000
TYPE_DT = 0.09
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


def keystrokes():
    """Découpe les frappes de typing.mp3 : liste de (échantillon, indice du pic)."""
    x = read(os.path.join(SFX, "typing.mp3"))
    hop = int(0.005 * SR)
    env = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(env + 1e-9)
    onsets = []
    for i in range(2, len(db)):
        if db[i] - db[i - 2] > 9 and db[i] > -45 and (not onsets or i * 0.005 - onsets[-1] > 0.05):
            onsets.append(i * 0.005)
    keys = []
    for k, t in enumerate(onsets):
        a = max(0, int((t - 0.012) * SR))
        nxt = onsets[k + 1] if k + 1 < len(onsets) else t + 0.12
        b = min(len(x), int((min(nxt - 0.006, t + 0.12)) * SR))
        seg = x[a:b].copy()
        f_in, f_out = int(0.003 * SR), int(0.02 * SR)
        seg[:f_in] *= np.linspace(0, 1, f_in)
        seg[-f_out:] *= np.linspace(1, 0, f_out)
        seg /= np.max(np.abs(seg))
        keys.append((seg, int(np.argmax(np.abs(seg)))))
    return keys


def place(st, seg, peak_i, t, gain, pan):
    i0 = int(round(t * SR)) - peak_i
    seg = seg[: len(st) - i0] * gain
    st[i0:i0 + len(seg), 0] += seg * np.cos((pan + 1) * np.pi / 4)
    st[i0:i0 + len(seg), 1] += seg * np.sin((pan + 1) * np.pi / 4)


def typing():
    keys = keystrokes()
    rng = np.random.default_rng(1311)
    peaks = {}
    order = [3, 7, 1, 9, 5, 0, 8, 2, 10, 6, 4]
    for name, text in TEXTS.items():
        n = int((LEAD + len(text) * TYPE_DT + 0.4) * SR)
        st = np.zeros((n, 2))
        for i, ch in enumerate(text):
            seg, pk = keys[order[i % len(order)] % len(keys)]
            if ch == " ":  # barre d'espace : plus grave et plus longue
                seg = np.interp(np.arange(0, len(seg) - 1, 0.82), np.arange(len(seg)), seg)
                pk = int(pk / 0.82)
            t = LEAD + i * TYPE_DT + rng.uniform(-0.006, 0.006)
            place(st, seg, pk, t, rng.uniform(0.75, 1.0) * (1.1 if ch == " " else 1.0), rng.uniform(-0.2, 0.2))
        st *= 0.8 / np.max(np.abs(st))
        write(os.path.join(SFX, name), st)
        peaks[name] = LEAD
        print("wrote", name, f"({len(text)} touches, {len(keys)} frappes enregistrées)")
    # touche Entrée : la frappe la plus énergique, un peu plus grave
    energies = [np.sum(seg[: int(0.03 * SR)] ** 2) for seg, _ in keys]
    seg, pk = keys[int(np.argmax(energies))]
    seg = np.interp(np.arange(0, len(seg) - 1, 0.9), np.arange(len(seg)), seg)
    pk = int(pk / 0.9)
    st = np.zeros((int(0.35 * SR), 2))
    place(st, seg, pk, 0.05, 1.0, 0.0)
    st *= 0.8 / np.max(np.abs(st))
    write(os.path.join(SFX, "key-enter.wav"), st)
    peaks["key-enter.wav"] = 0.05
    print("wrote key-enter.wav")
    return peaks


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def validation():
    """Deux notes montantes, attaque nette et extinction rapide (≈ 0,4 s) : « c'est validé »."""
    peaks = {}
    for k, (a, b) in enumerate(((79, 86), (81, 88), (83, 90), (86, 91)), start=1):  # sol5-ré6, la5-mi6, si5-fa#6, ré6-sol6
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        out = np.zeros(n)
        for m, t0, g in ((a, 0.0, 0.75), (b, 0.075, 1.0)):
            tt = np.clip(t - t0, 0, None)
            on = t >= t0
            f = mtof(m)
            tone = (np.sin(2 * np.pi * f * tt) + 0.22 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt / 0.03)
                    + 0.08 * np.sin(2 * np.pi * 2 * f * tt))
            e = np.exp(-tt / 0.13) * np.minimum(1, tt / 0.002)
            out += np.where(on, tone * e * g, 0)
        out = soften(out, 7000)
        st = np.stack([out, out], axis=1)
        st *= 0.7 / np.max(np.abs(st))
        name = f"validation-{k}.wav"
        write(os.path.join(SFX, name), st)
        peaks[name] = 0.0
        print("wrote", name)
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
    peaks.update(validation())
    peaks.update(drone())
    json.dump(peaks, open(pk_path, "w"), indent=1)
    print("wrote peaks.json")
