#!/usr/bin/env python3
"""Musique originale (100 BPM, la mineur -> do majeur), calée sur les 6 scènes.

Synthèse additive déterministe (numpy) : nappes, basse pulsée, arpège, souffle.
Sortie : assets/audio/music.wav (48 kHz, stéréo), normalisée ensuite par ffmpeg.

    python3 tools/music.py
"""
import os
import subprocess
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
TOTAL = 58.0
BEAT = 0.6
N = int(TOTAL * SR)
rng = np.random.default_rng(20261102)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n)
    na, nr = int(a * sr), int(r * sr)
    na = min(na, n)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr > 0:
        nr = min(nr, n)
        e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


L = np.zeros(N)
Rch = np.zeros(N)


def add(sig, start, pan=0.0, gain=1.0):
    i0 = int(start * SR)
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    if i0 >= N:
        return
    sig = sig[: N - i0] * gain
    lg = np.cos((pan + 1) * np.pi / 4)
    rg = np.sin((pan + 1) * np.pi / 4)
    L[i0 : i0 + len(sig)] += sig * lg
    Rch[i0 : i0 + len(sig)] += sig * rg


# ------------------------------------------------------------------ harmony
#            start  end   bass  pad notes
CHORDS = [
    (0.0, 4.8, 45, [57, 60, 64, 71]),  # Am(add9)        S1 problème invisible
    (4.8, 7.2, 41, [57, 60, 64, 65]),  # Fmaj7
    (7.2, 9.6, 38, [57, 60, 62, 65]),  # Dm9             S2 risques
    (9.6, 12.6, 40, [57, 59, 64, 69]),  # Esus4
    (12.6, 13.8, 40, [56, 59, 64, 68]),  # E
    (13.8, 16.2, 45, [57, 60, 64, 69]),  # Am             S3 drone
    (16.2, 18.0, 41, [57, 60, 65, 69]),  # F
    (18.0, 19.2, 48, [55, 60, 64, 67]),  # C
    (19.2, 20.4, 43, [55, 59, 62, 67]),  # G
    (20.4, 22.8, 45, [57, 60, 64, 69]),  # Am             S4 détection
    (22.8, 25.2, 41, [57, 60, 65, 69]),  # F
    (25.2, 27.6, 43, [55, 60, 62, 67]),  # Gsus4
    (27.6, 30.0, 48, [55, 60, 64, 67, 72]),  # C           S5 rapport : défaut n°1
    (30.0, 32.4, 47, [55, 59, 62, 67, 71]),  # G/B
    (32.4, 34.2, 45, [57, 60, 64, 69, 72]),  # Am          défaut n°2
    (34.2, 36.0, 41, [57, 60, 65, 69, 72]),  # F
    (36.0, 37.8, 38, [57, 60, 62, 65, 72]),  # Dm9         résultats
    (37.8, 39.6, 41, [57, 60, 65, 69, 72]),  # F
    (39.6, 42.0, 48, [55, 60, 64, 67, 72]),  # C           couverture, norme
    (42.0, 43.2, 43, [55, 59, 62, 67, 71]),  # G
    (43.2, 45.6, 48, [55, 60, 64, 67, 72]),  # C           S6 plateforme
    (45.6, 47.4, 41, [57, 60, 65, 69, 72]),  # F
    (47.4, 49.8, 43, [55, 59, 62, 67, 71]),  # G
    (49.8, 58.0, 36, [55, 59, 64, 67, 74]),  # Cmaj9        S7 logo, site, LinkedIn
]


def pad_note(freq, dur, detune_c):
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    f = freq * 2 ** (detune_c / 1200)
    sig = np.zeros(n)
    for k in range(1, 14):
        if f * k > 9000:
            break
        sig += np.sin(2 * np.pi * f * k * t + k * 0.7) * (1.0 / k) * np.exp(-k / 3.2)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 0.23 * t + freq)
    return sig * trem * env_adsr(n, 0.7, 1.2)


for start, end, bass, notes in CHORDS:
    dur = end - start
    for m in notes:
        for det, pan in ((-7, -0.55), (0, 0.0), (7, 0.55)):
            add(pad_note(mtof(m), dur, det), start - 0.15, pan, 0.052)

# ------------------------------------------------------------------ bass pulse
for start, end, bass, notes in CHORDS:
    f = mtof(bass)
    # S1: every 2 beats, S2-S6: 8ths (pulsation), S7: one long note
    if start < 7.2:
        step = BEAT * 2
    elif start < 49.8:
        step = BEAT / 2
    else:
        step = None
    if step is None:
        n = int((end - start) * SR)
        t = np.arange(n) / SR
        sig = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)) * env_adsr(n, 0.05, 2.5)
        add(sig, start, 0, 0.16)
        continue
    t0 = start
    while t0 < end - 1e-6:
        n = int(min(step * 1.8, end - t0 + 0.3) * SR)
        t = np.arange(n) / SR
        e = np.exp(-t / (step * 0.55)) * env_adsr(n, 0.006, 0.05)
        sig = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
        g = 0.2 if step >= BEAT else 0.13
        add(np.tanh(sig * 1.2) * e, t0, 0, g)
        t0 += step

# ------------------------------------------------------------------ arpeggio (drone -> report)
def pluck(freq, dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.32 * np.sin(2 * np.pi * 2 * freq * t) + 0.1 * np.sin(2 * np.pi * 3 * freq * t)
    return sig * np.exp(-t / 0.2) * env_adsr(n, 0.004, 0.05)


SIX = BEAT / 4
step_i = 0
for start, end, bass, notes in CHORDS:
    if start < 13.8 or start >= 49.8:
        continue
    tones = sorted(notes[:4])
    octave = 12 if start >= 27.6 else 0
    seq = [tones[0], tones[1], tones[2], tones[3], tones[0] + 12, tones[3], tones[2], tones[1]]
    t0 = start
    while t0 < end - 1e-6:
        m = seq[step_i % len(seq)] + octave
        accent = 1.0 if step_i % 4 == 0 else 0.72
        # fade the arpeggio in over the first bar of S3
        fade = min(1.0, (t0 - 13.8) / 2.4 + 0.25)
        add(pluck(mtof(m)), t0, 0.35 if step_i % 2 else -0.35, 0.085 * accent * fade)
        t0 += SIX
        step_i += 1

# ------------------------------------------------------------------ soft hats (S3-S5)
def hat(dur=0.08):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    hp = np.diff(np.concatenate([[0], noise]))  # crude high-pass
    t = np.arange(n) / SR
    return hp * np.exp(-t / 0.018)


t0 = 13.8 + BEAT / 2
while t0 < 49.8:
    add(hat(), t0, 0.2, 0.028)
    t0 += BEAT

# ------------------------------------------------------------------ swell into the logo
n = int(1.8 * SR)
t = np.arange(n) / SR
noise = rng.standard_normal(n)
# moving one-pole low-pass: cutoff rises 300 Hz -> 5 kHz
cut = 300 * (5000 / 300) ** (t / t[-1])
a = np.exp(-2 * np.pi * cut / SR)
y = np.zeros(n)
acc = 0.0
for i in range(n):
    acc = a[i] * acc + (1 - a[i]) * noise[i]
    y[i] = acc
swell = y * (t / t[-1]) ** 2 * env_adsr(n, 0.01, 0.12)
add(swell, 48.0, 0, 0.55)

# ------------------------------------------------------------------ reverb
def reverb(x, seconds=2.6, mix=0.24, seed=1):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / (seconds / 6.9))
    ir[: int(0.012 * SR)] = 0
    ir /= np.sqrt(np.sum(ir**2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.6


# ------------------------------------------------------------------ légère section rythmique
DL = np.zeros(N)
DR = np.zeros(N)


def dadd(sig, start, pan=0.0, gain=1.0):
    i0 = int(round(start * SR))
    if i0 >= N:
        return
    sig = sig[: N - i0] * gain
    DL[i0 : i0 + len(sig)] += sig * np.cos((pan + 1) * np.pi / 4)
    DR[i0 : i0 + len(sig)] += sig * np.sin((pan + 1) * np.pi / 4)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 46 + 90 * np.exp(-t / 0.032)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) + 0.25 * np.sin(2 * ph)
    click = rng.standard_normal(n) * np.exp(-t / 0.002) * 0.25
    return np.tanh((body * np.exp(-t / 0.22) + click) * 1.4)


def clap():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # passe-bande grossier : différence de deux passe-bas à un pôle
    def lp(x, fc):
        a = np.exp(-2 * np.pi * fc / SR)
        y = np.zeros_like(x)
        acc = 0.0
        for i in range(len(x)):
            acc = a * acc + (1 - a) * x[i]
            y[i] = acc
        return y
    bp = lp(noise, 4200) - lp(noise, 900)
    env = np.zeros(n)
    for d in (0.0, 0.011, 0.022):
        k = t >= d
        env[k] += np.exp(-(t[k] - d) / (0.008 if d < 0.02 else 0.11))
    return bp * env


def tick(decay=0.018):
    n = int(0.1 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = np.diff(np.concatenate([[0], noise]))
    hp = np.diff(np.concatenate([[0], hp]))
    return hp * np.exp(-t / decay)


K, C = kick(), clap()
beats = int(TOTAL / BEAT)
for b in range(beats):
    t0 = b * BEAT
    in_bar = b % 4
    if 2.4 <= t0 < 7.2 and in_bar in (0, 2):  # intro : battement discret
        dadd(K, t0, 0, 0.32)
    elif 7.2 <= t0 < 49.8:  # S2 -> S6 : pulsation à la noire
        dadd(K, t0, 0, 0.42)
    elif abs(t0 - 49.8) < 1e-6:  # dernier temps fort sur le logo
        dadd(K, t0, 0, 0.42)
    if 13.8 <= t0 < 49.8 and in_bar in (1, 3):  # clap discret sur 2 et 4
        dadd(C, t0, 0.1, 0.16)
for k in range(int(TOTAL / (BEAT / 4))):  # charleston : croches, doubles-croches fantômes
    t0 = k * BEAT / 4
    if not (7.2 <= t0 < 49.8):
        continue
    if k % 2 == 1:
        dadd(tick(), t0, 0.3, 0.05 if k % 4 == 2 else 0.035)
    elif t0 >= 20.4 and k % 4 != 0:
        dadd(tick(0.01), t0, -0.3, 0.016)
# léger « pompage » des nappes sur la grosse caisse (S2 -> S6)
pump = np.ones(N)
tt = np.arange(N) / SR
for b in range(beats):
    t0 = b * BEAT
    if 7.2 <= t0 < 49.8:
        i0 = int(t0 * SR)
        i1 = min(N, i0 + int(BEAT * SR))
        pump[i0:i1] *= 1 - 0.22 * np.exp(-(tt[i0:i1] - t0) / 0.12)

L = reverb(L, seed=11) * pump
Rch = reverb(Rch, seed=12) * pump
L = L + reverb(DL, seconds=1.2, mix=0.12, seed=21)
Rch = Rch + reverb(DR, seconds=1.2, mix=0.12, seed=22)

# ------------------------------------------------------------------ master
st = np.stack([L, Rch], axis=1)
fade_n = int(1.8 * SR)
st[-fade_n:] *= (np.cos(np.linspace(0, np.pi / 2, fade_n)) ** 2)[:, None]
st[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
st = np.tanh(st * 1.1) / np.tanh(1.1)
st /= np.max(np.abs(st)) * 1.12

raw = os.path.join(ROOT, "tools", ".music_raw.wav")
with wave.open(raw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())

out = os.path.join(ROOT, "assets", "audio", "music.wav")
subprocess.run(
    ["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-af", "loudnorm=I=-15.5:TP=-1.5:LRA=9", "-ar", str(SR), out],
    check=True,
)
os.remove(raw)
print("wrote", os.path.relpath(out, ROOT))
