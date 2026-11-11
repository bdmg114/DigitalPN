"""results.json 과 모델에서 문서용 그림을 만든다.  사용: python3 figures.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, Rectangle, Wedge
import numpy as np

from model import split_layout, slab_layout, evaluate, HANDS, corpus_keys, key_freq
from thumb import ThumbParams

OUT = Path(__file__).parent.parent / "docs" / "img"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SEQ = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": GRID, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})
HAND_LABEL = {"small": "small hand (160 mm)", "medium": "medium hand (178 mm)", "large": "large hand (196 mm)"}


def draw_device(ax, lay, res, title, show_bar=False):
    ax.add_patch(FancyBboxPatch((-lay.W / 2, -lay.H / 2), lay.W, lay.H, boxstyle="round,pad=0,rounding_size=7",
                                fc="#f0efec", ec=INK2, lw=0.8))
    if lay.name == "split":
        ax.add_patch(Rectangle((-17.6, -29.4), 35.2, 58.8, fc="white", ec=INK2, lw=0.6))
    D = res["D"]
    for lab, (x, y), w, a, d in zip(lay.labels, lay.xy, lay.wide, lay.ang, D):
        kw, kh = (w - 1) * lay.px + lay.px - 1.4, lay.py - 1.4
        col = "#d03b3b" if not np.isfinite(d) else SEQ(min(d, 1.0))
        r = Rectangle((-kw / 2, -kh / 2), kw, kh, fc=col, ec=SURFACE, lw=0.8)
        r.set_transform(matplotlib.transforms.Affine2D().rotate(a).translate(x, y) + ax.transData)
        ax.add_patch(r)
        if len(lab) == 1:
            ax.text(x, y, lab.upper(), ha="center", va="center", fontsize=5.5,
                    color="white" if (not np.isfinite(d) or d > 0.35) else INK)
    for side, g in enumerate(res["grips"]):
        sx = -1 if side == 0 else 1
        cx, cy = sx * g["cmc"][0], g["cmc"][1]
        ax.plot(cx, cy, "o", ms=4, color=INK, zorder=5)
        a0 = g["az"]                       # 안쪽이 0°, 위쪽이 +
        th = 180 - a0 if sx == 1 else a0   # 화면 좌표 각도
        ax.add_patch(Wedge((cx, cy), 0.53 * res["hl"], th - 26.5, th + 26.5, width=0.53 * res["hl"] - 0.33 * res["hl"],
                           fc="none", ec=INK2, lw=0.6, ls=(0, (3, 3))))
    ax.set_xlim(-135, 135)
    ax.set_ylim(-108, 42)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, loc="left", pad=2)


def fig_reach(designs, fname):
    fig, axes = plt.subplots(len(designs), 3, figsize=(11, 3.1 * len(designs)), squeeze=False)
    for i, (name, lay) in enumerate(designs):
        res = evaluate(lay)
        for j, h in enumerate(HANDS):
            res[h]["hl"] = HANDS[h]
            r = res[h]
            draw_device(axes[i][j], lay, r, f"{name} · {h} hand ({HANDS[h]:.0f} mm)")
            axes[i][j].text(-133, -100, f"{r['eff_kpm']:.0f} keys/min effective · {100 * r['err']:.1f}% errors · "
                                        f"mean strain {r['discomfort']:.2f}", fontsize=8, color=INK2)
    cax = fig.add_axes([0.36, 0.085, 0.28, 0.014])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=SEQ, norm=plt.Normalize(0, 1)), cax=cax, orientation="horizontal")
    cb.set_label("joint strain per key (0 = neutral posture, 1 = joints at their limits) · dot = thumb base joint, "
                 "dashed = joint-limit reach without moving the hand", fontsize=8)
    cb.outline.set_visible(False)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.13, wspace=0.02, hspace=0.05)
    fig.savefig(OUT / fname, dpi=170)
    plt.close(fig)


def fig_forms(rows, fname):
    """rows: [(label, result dict)]"""
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    y = np.arange(len(rows))[::-1]
    bh = 0.24
    for k, h in enumerate(HANDS):
        v = [r[h]["eff_kpm"] for _, r in rows]
        ax.barh(y + (1 - k) * (bh + 0.02), v, height=bh, color=SERIES[k], label=HAND_LABEL[h])
        for yi, vi in zip(y + (1 - k) * (bh + 0.02), v):
            ax.text(vi + 3, yi, f"{vi:.0f}", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, [l for l, _ in rows])
    ax.set_xlabel("effective keystrokes per minute (after error-correction time)")
    ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_xlim(0, max(r[h]["eff_kpm"] for _, r in rows for h in HANDS) * 1.12)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=8)
    ax.set_title("Simulated typing speed by form", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=170)
    plt.close(fig)


def fig_pitch(results, rot, R0, fname):
    sel = [r for r in results if r["name"] == "split" and r["rot"] == rot and r["R0"] == R0]
    pxs = sorted({r["px"] for r in sel})
    pys = sorted({r["py"] for r in sel})
    Z = np.full((len(pys), len(pxs)), np.nan)
    for r in sel:
        i, j = pys.index(r["py"]), pxs.index(r["px"])
        Z[i, j] = np.nanmax([Z[i, j], r["score"]])       # 세로 위치는 가장 좋은 것
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    im = ax.imshow(Z, origin="lower", cmap=SEQ, aspect="auto")
    for i in range(len(pys)):
        for j in range(len(pxs)):
            if np.isfinite(Z[i, j]):
                ax.text(j, i, f"{Z[i, j]:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if Z[i, j] > np.nanmean(Z) else INK)
            else:
                ax.text(j, i, "not run", ha="center", va="center", fontsize=6.5, color=INK2)
    ax.set_xticks(range(len(pxs)), [f"{v:g}" for v in pxs])
    ax.set_yticks(range(len(pys)), [f"{v:g}" for v in pys])
    ax.set_xlabel("column pitch (mm)")
    ax.set_ylabel("row pitch (mm)")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Effective keystrokes/min vs key pitch\n(split form, untilted, hand-size weighted)", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    results = json.load(open(Path(__file__).parent / "results.json"))
    base = split_layout(9.0, 9.5, 4.75)
    v02 = split_layout(9.0, 10.0, -6.0)
    v03 = split_layout(9.0, 10.0, -6.0, stagger=(-5, -5, -1, 3, 4))
    fig_reach([("v0.1 (flat grid, keys high)", base), ("v0.2 (flat grid, keys low)", v02),
               ("v0.3 (curved rows)", v03)], "sim-reach.png")
    fig_pitch(results, 0.0, None, "sim-pitch.png")
    bw = next(r for r in results if r["name"] == "wide")
    bp = next(r for r in results if r["name"] == "portrait")
    tilt = next(r for r in results if r["name"] == "split" and r["rot"] > 0)
    fig_forms([("portrait slab, keys at bottom\n(best: %g x %g mm)" % (bp["px"], bp["py"]), bp),
               ("split, whole cluster tilted or fanned\n(best: %g x %g mm, %g deg)" % (tilt["px"], tilt["py"], tilt["rot"]), tilt),
               ("split v0.1: flat 9.0 x 9.5 mm, keys high", evaluate(base)),
               ("split v0.2: flat 9.0 x 10.0 mm, keys low", evaluate(v02)),
               ("split v0.3: 9.0 x 10.0 mm, curved rows", evaluate(v03)),
               ("clusters joined, display on top\n(best: flat %g x %g mm)" % (bw["px"], bw["py"]), bw)],
              "sim-forms.png")
