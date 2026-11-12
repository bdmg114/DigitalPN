"""한 손 쥐기 시뮬레이션을 3D 영상으로 만든다.

기기를 든 자세(중력 방향)를 천천히 바꿔 가며, 그 순간 평형을 이루는 최소 힘의 해를 접촉점마다 화살표로 그린다.
왼쪽은 얇은 기본형, 오른쪽은 손잡이형 후보. 오른쪽 막대는 네 가지 케이스의 값을 동시에 보여 준다.

사용: python3 grip_animate.py [small|medium|large] [마찰계수] [출력.mp4]
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from scipy.optimize import linprog

import grip as G

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
FPS, SECONDS = 30, 36
ARROW = 10.0         # 화살표 길이 mm / N


def solve(shape, hl, place, mu, gdir, mass):
    """평형을 이루는 최소 누름 힘의 해. 반환: (힘의 합, [(접촉점, 손이 기기에 주는 힘 벡터)])"""
    cs = G.contacts(shape, hl, place, mu)
    cols = [np.concatenate([e, np.cross(p, e) / 50.0]) for p, edges in cs for e in edges]
    A = np.array(cols).T
    com = np.array([0.0, 0.0, -2.5])
    f = mass * G.G * gdir
    b = -np.concatenate([f, np.cross(com, f) / 50.0])
    r = linprog(np.ones(A.shape[1]), A_eq=A, b_eq=b, bounds=(0, None), method="highs")
    if r.status != 0:
        return math.inf, []
    out, i = [], 0
    for p, edges in cs:
        k = len(edges)
        out.append((p, (r.x[i:i + k, None] * edges).sum(0)))
        i += k
    return float(r.fun), out


def gravity_path(u):
    """0~1 사이의 u에 대한 중력 방향(기기 기준)과 자세 이름. 대표 자세 사이를 부드럽게 잇는다."""
    keys = [(np.array([0, 0, -1.0]), "화면을 위로, 수평으로 듦"),
            (np.array([-1.0, 0, 0]), "쥔 쪽을 위로, 아래로 늘어뜨림"),
            (np.array([0, -1.0, 0]), "화면을 세워서 듦"),
            (np.array([0, 0, 1.0]), "화면을 아래로 (누워서 볼 때)"),
            (np.array([1.0, 0, 0]), "쥔 쪽을 아래로, 위로 세움"),
            (np.array([0, 0, -1.0]), "화면을 위로, 수평으로 듦")]
    n = len(keys) - 1
    seg = min(int(u * n), n - 1)
    t = u * n - seg
    hold = 0.3                                   # 각 자세에서 잠깐 머문다
    s = 0.0 if t < hold else (t - hold) / (1 - hold)
    s = s * s * (3 - 2 * s)
    a, b = keys[seg][0], keys[seg + 1][0]
    ang = math.acos(float(np.clip(a @ b, -1, 1)))
    if ang > math.pi - 1e-6:                     # 정반대면 y축을 거쳐 돈다
        d = math.cos(math.pi * s) * a + math.sin(math.pi * s) * np.array([0, -1.0, 0])
    else:
        d = (math.sin((1 - s) * ang) * a + math.sin(s * ang) * b) / math.sin(ang)
    return d / np.linalg.norm(d), keys[seg][1] if s < 0.5 else keys[seg + 1][1]


def draw_body(ax, shape):
    """기기 몸체: 뒷면 곡면(융기 포함)과 앞면."""
    x = np.linspace(-G.W / 2, G.W / 2, 72)
    y = np.linspace(-G.Hh / 2, G.Hh / 2, 36)
    X, Y = np.meshgrid(x, y)
    a = G.W / 2 - np.abs(X)
    Hgt = G.height(a, Y, *shape) if shape[0] > 0 else np.zeros_like(X)
    ax.plot_surface(X, Y, G.Z_BACK - Hgt, color="#8fa0b6", alpha=0.92, linewidth=0, antialiased=True,
                    shade=True, zorder=1, rcount=36, ccount=72)
    w, h = G.W / 2, G.Hh / 2
    front = [(-w, -h, G.Z_FRONT), (w, -h, G.Z_FRONT), (w, h, G.Z_FRONT), (-w, h, G.Z_FRONT)]
    ax.add_collection3d(Poly3DCollection([front], fc="#f0efec", ec=INK2, lw=0.8, alpha=0.35, zorder=2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ax.plot([sx * w] * 2, [sy * h] * 2, [G.Z_BACK, G.Z_FRONT], color=INK2, lw=0.6, zorder=2)
    for sy in (-1, 1):
        ax.plot([-w, w], [sy * h] * 2, [G.Z_BACK] * 2, color=INK2, lw=0.6, zorder=2)
    for sx in (-1, 1):
        ax.plot([sx * w] * 2, [-h, h], [G.Z_BACK] * 2, color=INK2, lw=0.6, zorder=2)


def main(hand="medium", mu=0.3, out=None):
    data = json.load(open(G.HERE / "grip.json"))
    hl = G.HANDS[hand]
    tup = lambda s: (s["h"], s["crest"], s["w_in"], s["groove"])
    cases = [("얇은 기본형", (0.0, 22.0, 9.0, 0.0))] + [
        ("손잡이형 " + p["name"][0], tup(p["shape"])) for p in data["picks"]]
    info = []
    for name, sh in cases:
        r = next(x for x in data["results"] if tup(x["shape"]) == sh and x["mu"] == G.MUS[0])
        place = tuple(r["hands"][hand]["place"])
        info.append(dict(name=name, shape=sh, place=place, mass=G.BASE_MASS + G.lump_mass(sh),
                         cap=G.capacity(G.span_at(r, hand)), span=G.span_at(r, hand)))
    slim_dry = next(x for x in data["results"] if x["shape"]["h"] == 0 and x["mu"] == 0.5)
    ref = slim_dry["hands"][hand]["worst"] / info[0]["cap"] / 100       # 얇은 기본형, 마른 손, 최악 자세 = 100
    show = [0, 2]                                                        # 3D로 그리는 두 가지: 기본형과 후보 B

    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=SURFACE)
    fig.text(0.02, 0.945, "DigitalPN 한 손 쥐기 시뮬레이션", fontsize=17, color=INK)
    fig.text(0.02, 0.905, f"손 길이 {hl:.0f} mm · 마찰계수 {mu:g} · 오른손으로 한쪽 끝을 쥠 · 뒤에서 본 모습 · "
                          "화살표 = 그 자세를 버티는 최소 힘 (길이가 힘의 크기)", fontsize=10.5, color=INK2)
    pose = fig.text(0.02, 0.035, "", fontsize=13, color=INK)
    for xx, c, lab in ((0.02, BLUE, "손가락"), (0.10, ORANGE, "엄지"), (0.165, AQUA, "손바닥"), (0.245, INK, "중력")):
        fig.text(xx, 0.085, "●", fontsize=11, color=c)
        fig.text(xx + 0.016, 0.085, lab, fontsize=10.5, color=INK2)

    axes, arrows = [], []
    for n, ci in enumerate(show):
        ax = fig.add_axes([-0.02 + 0.365 * n, 0.10, 0.40, 0.78], projection="3d", computed_zorder=False)
        ax.set_xlim(-80, 80)
        ax.set_ylim(-80, 80)
        ax.set_zlim(-60, 60)
        ax.set_box_aspect((160, 160, 120), zoom=1.12)
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        draw_body(ax, info[ci]["shape"])
        ax.text2D(0.5, 0.93, f"{info[ci]['name']}  (손가락 자리 두께 {info[ci]['span']:.1f} mm)", transform=ax.transAxes,
                  ha="center", fontsize=12.5, color=INK)
        lines = [ax.plot([], [], [], lw=3.2, solid_capstyle="round", zorder=6)[0] for _ in range(7)]
        heads = [ax.plot([], [], [], "o", ms=6, zorder=7)[0] for _ in range(7)]
        grav, = ax.plot([], [], [], color=INK, lw=2.6, zorder=8)
        gtip, = ax.plot([], [], [], "v", color=INK, ms=8, zorder=8)
        axes.append(ax)
        arrows.append((lines, heads, grav, gtip))

    # 막대: 네 케이스의 힘과 부담
    bars = []
    for k, (title, unit, xmax) in enumerate((("누르는 힘의 합", "N", 12.0), ("쥐는 부담 (힘 ÷ 그 두께에서 낼 수 있는 힘)", "", 260.0))):
        bx = fig.add_axes([0.74, 0.56 - 0.44 * k, 0.24, 0.26])
        bx.set_xlim(0, xmax)
        bx.set_ylim(-0.6, len(info) - 0.4)
        bx.invert_yaxis()
        bx.set_yticks(range(len(info)), [i["name"] for i in info], fontsize=10)
        bx.tick_params(length=0, labelsize=9, colors=INK2)
        for sp in ("top", "right", "left"):
            bx.spines[sp].set_visible(False)
        bx.spines["bottom"].set_color(GRID)
        bx.xaxis.grid(True, color=GRID, lw=0.6)
        bx.set_axisbelow(True)
        bx.set_title(title, loc="left", fontsize=11, color=INK)
        rects = bx.barh(range(len(info)), [0] * len(info), height=0.55,
                        color=[BLUE if i in show else "#86b6ef" for i in range(len(info))])
        labels = [bx.text(0, i, "", va="center", fontsize=9.5, color=INK2) for i in range(len(info))]
        bars.append((rects, labels, unit, xmax))
    fig.text(0.74, 0.045, "부담 100 = 얇은 기본형을 마른 손으로\n가장 힘든 자세에서 쥘 때", fontsize=9, color=INK2, linespacing=1.5)

    out = out or str(G.HERE.parent / "docs" / "video" / f"grip-{hand}.mp4")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "24"])
    colors = [ORANGE, AQUA, AQUA, BLUE, BLUE, BLUE, BLUE]      # 엄지, 손바닥 둘, 손가락 넷
    nframes = FPS * SECONDS
    with writer.saving(fig, out, dpi=100):
        for fi in range(nframes):
            u = fi / (nframes - 1)
            g, name = gravity_path(u)
            vals = []
            for ci, c in enumerate(info):
                tot, forces = solve(c["shape"], hl, c["place"], mu, g, c["mass"])
                vals.append((tot, tot / c["cap"] / ref))
                if ci in show:
                    lines, heads, grav, gtip = arrows[show.index(ci)]
                    for j, (p, f) in enumerate(forces):
                        q = p - f * ARROW                      # 화살표는 접촉점을 향해 들어온다
                        lines[j].set_data_3d([q[0], p[0]], [q[1], p[1]], [q[2], p[2]])
                        lines[j].set_color(colors[j])
                        heads[j].set_data_3d([p[0]], [p[1]], [p[2]])
                        heads[j].set_color(colors[j])
                    w = g * c["mass"] * G.G * ARROW
                    grav.set_data_3d([0, w[0]], [0, w[1]], [-2.5, -2.5 + w[2]])
                    gtip.set_data_3d([w[0]], [w[1]], [-2.5 + w[2]])
            for k, (rects, labels, unit, xmax) in enumerate(bars):
                for i, rct in enumerate(rects):
                    v = vals[i][k]
                    rct.set_width(min(v, xmax))
                    labels[i].set_text(f" {v:.1f} {unit}" if k == 0 else f" {v:.0f}")
                    labels[i].set_x(min(v, xmax * 0.86))
            for ax in axes:
                ax.view_init(elev=-38, azim=-68 + 18 * math.sin(2 * math.pi * u))
            pose.set_text(f"자세: {name}")
            writer.grab_frame()
    plt.close(fig)
    print(out, nframes, "frames")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "medium", float(a[1]) if len(a) > 1 else 0.3, a[2] if len(a) > 2 else None)
