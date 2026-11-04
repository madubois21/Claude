#!/usr/bin/env python3
"""Musique originale, version dynamique (passages 9 et 12) : électro-pop entraînante, 74,4 s.

Tempo 100 BPM (1 temps = 0,6 s) : toutes les coupes de la vidéo tombent sur un temps, et chaque scène
commence sur un temps fort. Mi mineur / sol majeur (Em – C – G – D).
- intro (S1) : arpège filtré qui s'ouvre, grosse caisse qui s'installe, montée vers la scène 2 ;
- scènes 2 à 5 : grosse caisse à la noire, clap sur 2 et 4, charleston en doubles-croches, basse en croches
  pompée par la grosse caisse, accords « stab » sur les contretemps, arpège ; impact et cymbale à chaque scène ;
- scène 6 : montée (roulement de caisse claire qui accélère, souffle qui monte, filtre qui s'ouvre) ;
- scène 7 : retombée sur le logo, puis cadence IV – V – I et accord final net à 71,4 s, qui résonne jusqu’à 74,4 s
  pendant que le site web et LinkedIn restent à l'écran.
Synthèse déterministe (numpy). Sortie : assets/audio/music.wav (48 kHz, stéréo), -16 LUFS (normalisation linéaire).

    python3 tools/music.py
"""
import os
import subprocess
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
TOTAL = 74.4
BEAT = 0.6
S16 = BEAT / 4
N = int(TOTAL * SR)
rng = np.random.default_rng(20261104)

# ------------------------------------------------------------------ structure (début, fin, type, un accord par mesure)
SECTIONS = [
    (0.0, 7.2, "intro", ["Em", "C", "D"]),  # S1 le problème invisible
    (7.2, 13.8, "drop", ["Em", "C", "G"]),  # S2 les risques
    (13.8, 20.4, "drive", ["Em", "C", "D"]),  # S3 drone
    (20.4, 33.0, "groove", ["G", "D", "Em", "C", "G"]),  # S3 « Le saviez-vous ? » (la voix explique)
    (33.0, 40.2, "drive", ["Em", "C", "D"]),  # S4 détection
    (40.2, 57.6, "groove", ["G", "D", "Em", "C", "G", "D", "Em", "C"]),  # S5 rapport
    (57.6, 64.2, "build", ["Em", "C", "D"]),  # S6 plateforme : montée
    (64.2, 71.4, "drop", ["G", "D", "C|D"]),  # S7 logo, site, LinkedIn
    (71.4, 74.4, "end", ["G"]),  # accord final tenu
]
CHORDS = {  # basse (MIDI), accord (MIDI)
    "Em": (40, [64, 67, 71]),
    "C": (36, [64, 67, 72]),
    "G": (43, [62, 67, 71]),
    "D": (38, [62, 66, 69]),
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_at(t):
    """Accord en cours au temps t (une mesure = 4 temps, comptée depuis le début de la section)."""
    for s0, s1, kind, bars in SECTIONS:
        if s0 - 1e-6 <= t < s1 - 1e-6:
            b = int((t - s0 + 1e-6) // (4 * BEAT))
            name = bars[min(b, len(bars) - 1)]
            if "|" in name:  # deux accords dans la mesure
                a, c = name.split("|")
                name = a if ((t - s0) % (4 * BEAT)) < 2 * BEAT - 1e-6 else c
            return name, kind, s0, s1
    return "G", "end", 71.4, TOTAL


# ------------------------------------------------------------------ bus
BUS = {k: np.zeros((N, 2)) for k in ("drums", "bass", "music", "fx")}


def add(bus, sig, start, pan=0.0, gain=1.0):
    i0 = int(round(start * SR))
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    if i0 >= N or len(sig) == 0:
        return
    sig = sig[: N - i0] * gain
    BUS[bus][i0 : i0 + len(sig), 0] += sig * np.cos((pan + 1) * np.pi / 4)
    BUS[bus][i0 : i0 + len(sig), 1] += sig * np.sin((pan + 1) * np.pi / 4)


def env(n, a, d=None, r=0.01):
    """Attaque a (s), décroissance exponentielle d (s) ou maintien, relâchement r (s)."""
    t = np.arange(n) / SR
    e = np.ones(n) if d is None else np.exp(-t / d)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    if na > 0:
        e[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr > 0:
        e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def onepole(x, fc):
    """Passe-bas à un pôle ; fc peut varier dans le temps (tableau)."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = a[i] * acc + (1 - a[i]) * x[i]
        y[i] = acc
    return y


def saw(freq, n, bright=8.0, phase=0.0):
    """Dent de scie additive (sans repliement), brillance réglée par l'atténuation des harmoniques."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 40):
        if freq * k > 15000:
            break
        out += np.sin(2 * np.pi * freq * k * t + phase * k) / k * np.exp(-(k - 1) / bright)
    return out


def square(freq, n, bright=6.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 30, 2):
        if freq * k > 15000:
            break
        out += np.sin(2 * np.pi * freq * k * t) / k * np.exp(-(k - 1) / bright)
    return out


# ------------------------------------------------------------------ batterie
def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 55 + 120 * np.exp(-t / 0.025)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.14)
    click = rng.standard_normal(n) * np.exp(-t / 0.0018) * 0.35
    return np.tanh((body + click) * 1.8) * env(n, 0.001, None, 0.03)


def clap():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    bp = onepole(noise, 5200) - onepole(noise, 1100)
    e = np.zeros(n)
    for d in (0.0, 0.009, 0.018, 0.027):
        k = t >= d
        e[k] += np.exp(-(t[k] - d) / (0.006 if d < 0.027 else 0.13))
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    return bp * e * 2.2 + tone


def snare(vel=1.0):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = noise - onepole(noise, 1500)
    return (hp * np.exp(-t / 0.07) + np.sin(2 * np.pi * 200 * t) * np.exp(-t / 0.04) * 0.8) * vel


def hat(open_=False):
    n = int((0.3 if open_ else 0.07) * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = noise - onepole(noise, 7000)
    metal = sum(np.sin(2 * np.pi * f * t) for f in (6100, 7350, 8420, 9870)) * 0.12
    return (hp + metal) * np.exp(-t / (0.11 if open_ else 0.018))


def crash(dur=2.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = noise - onepole(noise, 3500)
    metal = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((3870, 4930, 5610, 6720, 8110))) * 0.08
    return (hp + metal) * np.exp(-t / (dur / 4.5)) * env(n, 0.002, None, 0.2)


def impact():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 45 + 40 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.4)
    thump = onepole(rng.standard_normal(n), 400) * np.exp(-t / 0.05) * 3.0
    return np.tanh((boom + thump) * 1.4)


def riser(dur, f0=300.0, f1=9000.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / t[-1]
    fc = f0 * (f1 / f0) ** x
    noise = rng.standard_normal(n)
    y = onepole(noise, fc) - onepole(noise, fc * 0.25)
    return y * x ** 2.2 * env(n, 0.05, None, 0.02)


K, CL, CR_ = kick(), clap(), crash()
HC, HO = hat(False), hat(True)
IMP = impact()
REV_CRASH = crash(0.9)[::-1] * np.linspace(0, 1, int(0.9 * SR)) ** 2
SN = [snare(v) for v in (0.5, 0.67, 0.84, 1.0)]

kicks = []  # instants des grosses caisses (pour le pompage)
nbeats = int(round(TOTAL / BEAT))
for b in range(nbeats):
    t0 = round(b * BEAT, 6)
    _, kind, s0, s1 = chord_at(t0 + 1e-4)
    beat_in_bar = int(round((t0 - s0) / BEAT)) % 4
    last_beat = t0 + BEAT > s1 - 1e-6  # dernier temps de la section : roulement
    if kind == "intro":
        if t0 >= 2.4 and (t0 >= 4.8 or beat_in_bar in (0, 2)):
            add("drums", K, t0, 0, 0.25 if t0 < 4.8 else 0.33)
            kicks.append(t0)
        if t0 >= 2.4:
            add("drums", HC, t0 + BEAT / 2, 0.25, 0.022)
    elif kind in ("drop", "drive", "groove", "build"):
        cut_ = kind == "build" and t0 >= 63.0  # tout s'arrête juste avant la retombée sur le logo
        if not cut_:
            add("drums", K, t0, 0, 0.32)
            kicks.append(t0)
            for k in range(4):  # charleston en doubles-croches, accent sur le contretemps
                v = (0.028, 0.012, 0.023, 0.012)[k] * (0.8 if kind == "groove" else 1.0)
                add("drums", HC, t0 + k * S16, 0.3 if k % 2 else -0.2, v)
        if beat_in_bar in (1, 3) and kind != "build" and not last_beat:
            add("drums", CL, t0, 0.05, 0.22)
        if kind in ("drop", "drive"):
            add("drums", HO, t0 + BEAT / 2, -0.3, 0.02)
    elif kind == "end" and abs(t0 - 71.4) < 1e-6:
        add("drums", K, t0, 0, 0.42)
        kicks.append(t0)
    # roulement de fin de section (avant chaque nouvelle scène)
    if last_beat and kind in ("drop", "drive", "groove", "intro"):
        for k in range(4):
            add("drums", SN[k], t0 + k * S16, 0.1, 0.16)

# roulement qui accélère pendant la montée de la scène 6
for t0, end, step, v in ((57.6, 60.0, BEAT, 0.12), (60.0, 62.4, BEAT / 2, 0.15), (62.4, 63.6, S16, 0.18), (63.6, 64.2, S16 / 2, 0.22)):
    t = t0
    while t < end - 1e-6:
        prog = (t - 57.6) / 6.6
        add("drums", SN[min(3, int(prog * 4))], t, 0.1, 0.75 * (v + 0.12 * prog))
        t += step

# cymbales, impacts et montées aux changements de scène
for t0, big in ((7.2, True), (13.8, False), (33.0, True), (40.2, False), (57.6, False), (64.2, True), (71.4, True)):
    add("fx", CR_, t0, 0.2, 0.14 if big else 0.09)
    add("fx", IMP, t0, 0, 0.2 if big else 0.11)
    add("fx", REV_CRASH, t0 - 0.9, -0.2, 0.12)
for t0, gain in ((48.6, 0.08), (52.2, 0.08)):  # pages 2 et 3 du rapport
    add("fx", crash(1.4), t0, -0.25, gain)
add("fx", riser(2.4), 4.8, 0, 0.15)  # intro -> scène 2
add("fx", riser(6.6, 200, 11000), 57.6, 0, 0.22)  # grande montée -> logo

# ------------------------------------------------------------------ basse : croches pompées
t0 = 4.8
while t0 < 71.4 - 1e-6:
    name, kind, s0, s1 = chord_at(t0 + 1e-4)
    if kind == "build" and t0 >= 63.0:  # coupure avant la retombée
        t0 = round(t0 + BEAT / 2, 6)
        continue
    root = CHORDS[name][0]
    n = int(0.32 * SR)
    off = abs(((t0 - s0) / (BEAT / 2)) % 2 - 1) < 1e-6  # contretemps
    oct_ = 12 if (off and kind in ("drop", "drive")) else 0
    tt_ = np.arange(n) / SR
    body = saw(mtof(root + oct_), n, bright=5.5) * 0.8 + np.sin(2 * np.pi * mtof(root) * tt_) * (0.6 if not oct_ else 0.3)
    add("bass", np.tanh(body * 1.4) * env(n, 0.004, 0.16, 0.03), t0, 0, 0.2 if off else 0.14)
    t0 = round(t0 + BEAT / 2, 6)

# ------------------------------------------------------------------ accords
def stab(freq, n, bright=7.0):
    out = np.zeros(n)
    for det in (-14, -6, 0, 6, 14):
        out += saw(freq * 2 ** (det / 1200), n, bright, phase=det * 0.37)
    return out / 3.2


STAB_N = int(0.26 * SR)
STAB_E = env(STAB_N, 0.003, 0.09, 0.03)
stab_cache = {}
for b in range(nbeats * 2):  # contretemps des croches
    t0 = round(b * BEAT / 2, 6)
    name, kind, s0, s1 = chord_at(t0 + 1e-4)
    off = abs(((t0 - s0) / (BEAT / 2)) % 2 - 1) < 1e-6
    if not off or kind not in ("drop", "drive"):
        continue
    if name not in stab_cache:
        stab_cache[name] = sum(stab(mtof(m), STAB_N) for m in CHORDS[name][1]) * STAB_E
    add("music", stab_cache[name], t0, 0.0, 0.34)

# nappes : intro, rapport, montée, accord final
for s0, s1, kind, bars in SECTIONS:
    if kind not in ("intro", "groove", "build", "end"):
        continue
    t0 = s0
    while t0 < s1 - 1e-6:
        name, _, _, _ = chord_at(t0 + 1e-4)
        dur = min(4 * BEAT, s1 - t0) if kind != "end" else s1 - t0
        n = int((dur + (0.0 if kind == "end" else 0.5)) * SR)
        notes = CHORDS[name][1] + ([CHORDS[name][1][0] + 12, CHORDS[name][0] + 12] if kind == "end" else [])
        e = env(n, 0.004, 1.3, 0.3) if kind == "end" else env(n, 0.35, None, 0.45)
        gain = {"intro": 0.03, "groove": 0.11, "build": 0.1, "end": 0.2}[kind]
        sig = sum(stab(mtof(m), n, bright=6.0 if kind == "end" else 4.5) for m in notes)
        add("music", sig * e, t0, 0.0, gain)
        t0 = round(t0 + dur, 6)

# arpège en doubles-croches (intro filtrée, scènes 3-4 au premier plan, rapport en retrait)
PL_N = int(0.3 * SR)
PL_E = env(PL_N, 0.002, 0.085, 0.02)
pl_cache = {}
arp_i = 0
t0 = 0.0
while t0 < 71.4 - 1e-6:
    name, kind, s0, s1 = chord_at(t0 + 1e-4)
    tones = sorted(CHORDS[name][1])
    seq = [tones[0], tones[1], tones[2], tones[0] + 12, tones[2], tones[1], tones[0] + 12, tones[1] + 12]
    m = seq[arp_i % len(seq)] + 12
    if kind == "intro":
        gain, bright = 0.065 * (0.4 + 0.6 * t0 / 7.2), round(1.5 + 6 * t0 / 7.2, 1)  # le filtre s'ouvre
    elif kind == "drive":
        gain, bright = 0.17, 8.0
    elif kind == "drop":
        gain, bright = 0.13, 7.0
    elif kind == "groove":
        gain, bright = 0.1, 5.0
    else:  # build : l'arpège monte en intensité
        gain, bright = 0.065 + 0.08 * (t0 - 57.6) / 6.6, round(4 + 6 * (t0 - 57.6) / 6.6, 1)
    key = (m, bright)
    if key not in pl_cache:
        pl_cache[key] = square(mtof(m), PL_N, bright) * PL_E
    acc = 1.0 if arp_i % 4 == 0 else 0.75
    add("music", pl_cache[key], t0, -0.4 if arp_i % 2 else 0.4, gain * acc)
    t0 = round(t0 + S16, 6)
    arp_i += 1

# ------------------------------------------------------------------ pompage (la grosse caisse creuse la musique)
tt = np.arange(N) / SR
pump = np.ones(N)
for tk in kicks:
    i0, i1 = int(tk * SR), min(N, int((tk + BEAT) * SR))
    pump[i0:i1] = np.minimum(pump[i0:i1], 1 - 0.55 * np.exp(-(tt[i0:i1] - tk) / 0.11))
pump_b = 1 - (1 - pump) * 0.7


def reverb(x, seconds=2.2, mix=0.2, seed=1):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / (seconds / 6.9))
    ir[: int(0.01 * SR)] = 0
    ir /= np.sqrt(np.sum(ir**2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.5


music = BUS["music"] * pump[:, None]
# montée de la scène 6 : la musique est filtrée puis s'ouvre sur la retombée (filtre appliqué à la seule montée)
i0, i1 = int(57.6 * SR), int(64.2 * SR)
fc = 900 * (16000 / 900) ** np.linspace(0, 1, i1 - i0)
for c in (0, 1):
    music[i0:i1, c] = onepole(music[i0:i1, c], fc)
music = np.stack([reverb(music[:, 0], seed=11), reverb(music[:, 1], seed=12)], axis=1)
bass = BUS["bass"] * pump_b[:, None]
def soften(x, fc):
    """Passe-bas doux du premier ordre (|H| = 1 / sqrt(1 + (f/fc)^2)), appliqué en une seule FFT."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 2), len(x))


drums = np.stack([soften(reverb(BUS["drums"][:, c], 1.0, 0.08, 21 + c), 7000) for c in (0, 1)], axis=1)
fx = np.stack([soften(reverb(BUS["fx"][:, c], 2.8, 0.25, 31 + c), 6000) for c in (0, 1)], axis=1)
st = drums + bass + music + fx
if os.environ.get("MUSIC_DEBUG"):  # énergie par bande de chaque bus (réglage du mélange sans écoute)
    f = np.fft.rfftfreq(8192, 1 / SR)
    for name, x in (("drums", drums), ("bass", bass), ("music", music), ("fx", fx), ("mix", st)):
        m = x.mean(1)
        ps = sum(np.abs(np.fft.rfft(m[i:i + 8192] * np.hanning(8192))) ** 2 for i in range(0, len(m) - 8192, 4096))
        bands = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]
        print(f"{name:6s} " + "  ".join(f"{10 * np.log10(ps[(f >= a) & (f < b)].sum() + 1e-12):5.1f}" for a, b in bands)
              + "   | " + " ".join(f"{20 * np.log10(np.sqrt(np.mean(m[int(s0 * SR):int(s1 * SR)] ** 2)) + 1e-9):5.1f}" for s0, s1, _, _ in SECTIONS))

# ------------------------------------------------------------------ master
fade_n = int(0.9 * SR)
st[-fade_n:] *= (np.cos(np.linspace(0, np.pi / 2, fade_n)) ** 2)[:, None]
st[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
st = np.tanh(st * 1.15) / np.tanh(1.15)
st /= np.max(np.abs(st)) * 1.1

raw = os.path.join(ROOT, "tools", ".music_raw.wav")
with wave.open(raw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())

out = os.path.join(ROOT, "assets", "audio", "music.wav")
import json  # noqa: E402

log = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", raw, "-af", "loudnorm=I=-16:TP=-1.2:LRA=20:print_format=json",
                      "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
m = json.loads(log[log.rindex("{"): log.rindex("}") + 1])
chain = (f"loudnorm=I=-16:TP=-1.2:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
         f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
log = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", raw, "-af", chain, "-ar", str(SR), out],
                     capture_output=True, text=True, check=True).stderr
print("normalisation :", json.loads(log[log.rindex("{"): log.rindex("}") + 1])["normalization_type"])
os.remove(raw)
print("wrote", os.path.relpath(out, ROOT))
