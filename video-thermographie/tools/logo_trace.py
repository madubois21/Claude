#!/usr/bin/env python3
"""Vectorise les lettres du logo Fly Scan'Air fourni (assets/images/logo-flyscanair.png, 1280 x 452).

Les lettres (rouge -> orange, très saturées) sont séparées du serpentin gris et des deux billes rouges,
suréchantillonnées x4 puis tracées avec potrace (courbes de Bézier). Le tracé est écrit dans
assets/logo-letters.json, dans le repère de l'image d'origine, qui est aussi le repère du logo de
tools/build.py (serpentin, billes) : aucune mise à l'échelle n'est nécessaire.

    pip install potracer       # potrace en Python pur
    python3 tools/logo_trace.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

import potrace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "images", "logo-flyscanair.png")
OUT = os.path.join(ROOT, "assets", "logo-letters.json")
UP = 4  # suréchantillonnage avant tracé


def hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, s, mx


def components(mask):
    """Étiquetage 4-connexe simple (pile), renvoie la liste des composantes (ys, xs)."""
    seen = np.zeros(mask.shape, bool)
    comps = []
    hgt, wid = mask.shape
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        stack, ys, xs = [(y0, x0)], [], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            ys.append(y)
            xs.append(x)
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < hgt and 0 <= xx < wid and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    stack.append((yy, xx))
        comps.append((np.array(ys), np.array(xs)))
    return comps


def main():
    im = Image.open(SRC).convert("RGBA")
    a = np.asarray(im).astype(float) / 255
    rgb = a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])  # sur fond blanc
    h, s, v = hsv(rgb)
    warm = ((h < 50) | (h > 340)) & (s > 0.18)
    # « lettritude » continue : saturation, nulle hors des teintes chaudes
    sat = np.where(warm, s, 0)
    core = sat > 0.45
    balls, letters = [], np.zeros(core.shape, bool)
    for ys, xs in components(core):
        hh, ww = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        if len(ys) < 900 and 12 < hh < 34 and 12 < ww < 34:  # bille (sphère rouge du serpentin)
            balls.append(dict(cx=round(float(xs.min() + xs.max()) / 2, 1), cy=round(float(ys.min() + ys.max()) / 2, 1),
                              r=round(float((ww + hh) / 4), 1)))
        elif len(ys) > 40:
            letters[ys, xs] = True
    # zone utile autour des lettres (dilatée) pour ne garder que leurs bords anti-crénelés
    keep = letters.copy()
    for _ in range(3):
        keep = keep | np.roll(keep, 1, 0) | np.roll(keep, -1, 0) | np.roll(keep, 1, 1) | np.roll(keep, -1, 1)
    field = np.where(keep, sat, 0)
    big = Image.fromarray((field * 255).astype(np.uint8)).resize(
        (field.shape[1] * UP, field.shape[0] * UP), Image.BICUBIC)
    bits = np.asarray(big) > int(0.42 * 255)
    path = potrace.Bitmap(~bits).trace(  # potracer : pixels foncés (False) = formeturdsize=40, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                      alphamax=1.0, opticurve=True, opttolerance=0.2)
    f = lambda p: f"{p.x / UP:.2f} {p.y / UP:.2f}"
    d = []
    for curve in path:
        d.append("M" + f(curve.start_point))
        for seg in curve:
            if seg.is_corner:
                d.append("L" + f(seg.c) + "L" + f(seg.end_point))
            else:
                d.append("C" + f(seg.c1) + " " + f(seg.c2) + " " + f(seg.end_point))
        d.append("Z")
    ys, xs = np.nonzero(letters)
    data = dict(source="assets/images/logo-flyscanair.png", size=list(im.size), d="".join(d),
                bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                balls=sorted(balls, key=lambda b: b["cx"]))
    json.dump(data, open(OUT, "w"), indent=1)
    print(f"{len(path)} contours, bbox {data['bbox']}, billes {data['balls']} -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
