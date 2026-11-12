"""한 손 쥐기 시뮬레이션: 손잡이 모양별로 기기를 버티는 데 필요한 쥐는 힘을 구한다.

기기의 한쪽 끝을 한 손으로 쥔다. 손은 엄지(앞면), 엄지 뿌리 쪽 손바닥(옆 모서리), 손바닥(뒷면 가장자리),
네 손가락 끝의 7개 접촉점으로 기기를 누른다. 손가락은 넷 다 뒷면에 두거나(쥐는 법 A),
검지를 위 모서리에 걸고 새끼손가락으로 아래 모서리를 받칠 수 있다(쥐는 법 B). 각 접촉은 면을 누르는 힘과 마찰력만 낼 수 있다(당길 수 없다).
중력이 여러 방향에서 걸릴 때(기기를 어떤 자세로 들고 있든) 힘과 돌림힘의 평형을 만족하면서
누르는 힘의 합이 가장 작은 해를 선형계획으로 찾는다. 그 합이 "쥐는 힘"이다.

손잡이 융기는 뒷면에서의 높이 H(a, y)로 정의한다. a는 옆 모서리에서 안쪽으로 잰 거리.
  바깥 비탈: a0 → crest 에서 0 → h 로 매끄럽게 올라간다 (양 끝 기울기 0 → 본체에 접선으로 이어짐)
  안쪽 비탈: crest → crest + w_in 에서 h → 0 으로 내려간다 (손가락 끝이 걸리는 곳)
  손가락 골: 세로 방향으로 groove 비율만큼 높이가 물결친다 (손가락이 가로로 놓이는 골, 간격 19 mm)

사용: python3 grip.py  → grip.json, ../docs/img/grip-sim.png
"""
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).parent
W, Hh = 142.0, 70.0                 # 기기 폭, 높이
Z_FRONT, Z_BACK = 4.1, -8.2         # 앞면, 뒷면 높이 (PCB 앞면 = 0)
A0 = 4.0                            # 뒷면 평면이 시작되는 곳 (가장자리 곡면 안쪽)
LUMP_LEN, LUMP_FADE = 62.0, 22.0    # 융기의 세로 길이와 끝이 사그라드는 길이
GROOVE_PITCH = 19.0                 # 손가락 골 간격
BASE_MASS = 0.095                   # kg (배터리 포함 추정)
G = 9.81
HANDS = {"small": 160.0, "medium": 178.0, "large": 196.0}
WEIGHTS = {"small": 0.25, "medium": 0.5, "large": 0.25}


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def height(a, y, h, crest, w_in, groove=0.0):
    """뒷면에서 솟은 높이 (mm)."""
    a, y = np.asarray(a, float), np.asarray(y, float)
    p = np.where(a <= crest, smooth((a - A0) / (crest - A0)), 1 - smooth((a - crest) / w_in))
    q = 1 - smooth((np.abs(y + 1.0) - (LUMP_LEN / 2 - LUMP_FADE)) / LUMP_FADE)
    # 골의 바닥은 y = -1 ± 9.5, ± 28.5 (손가락 네 개의 자리)
    sc = 1 - groove * (0.5 + 0.5 * np.cos(2 * np.pi * (y + 1.0 - GROOVE_PITCH / 2) / GROOVE_PITCH))
    return h * p * q * sc


def back_contact(a, y, shape):
    """오른손 기준 뒷면 접촉점의 위치와, 손이 기기를 누르는 방향(면의 안쪽 법선)."""
    e = 0.25
    if shape[0] > 0:
        H = float(height(a, y, *shape))
        Ha = float(height(a + e, y, *shape) - height(a - e, y, *shape)) / (2 * e)
        Hy = float(height(a, y + e, *shape) - height(a, y - e, *shape)) / (2 * e)
    else:
        H = Ha = Hy = 0.0
    # 면: z = Z_BACK - H, x = W/2 - a.  누르는 방향 = (-g_x, -g_y, 1), g_x = +H_a, g_y = -H_y
    n = np.array([-Ha, Hy, 1.0])
    return np.array([W / 2 - a, y, Z_BACK - H]), n / np.linalg.norm(n)


def cone(n, mu, k=8):
    """마찰 원뿔의 모서리 벡터들 (k, 3). 각 모서리의 법선 성분은 1."""
    t1 = np.cross(n, [0.0, 1.0, 0.0])
    if np.linalg.norm(t1) < 1e-6:
        t1 = np.cross(n, [1.0, 0.0, 0.0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    ang = np.arange(k) * 2 * math.pi / k
    return n[None, :] + mu * (np.cos(ang)[:, None] * t1 + np.sin(ang)[:, None] * t2)


def directions(skip_edges=False):
    """기기에 대한 중력 방향 26개 (축, 면 대각선, 꼭짓점 방향). skip_edges면 축과 꼭짓점 14개만."""
    d = [np.array(v, float) for v in itertools.product((-1, 0, 1), repeat=3)
         if any(v) and not (skip_edges and sum(map(abs, v)) == 2)]
    return [v / np.linalg.norm(v) for v in d]


DIRS, DIRS_FAST = directions(), directions(True)
NAMED = {"flat": np.array([0, 0, -1.0]),       # 화면이 위를 향하게 수평으로 듦 (반대쪽 끝이 처지려 함)
         "hang": np.array([-1.0, 0, 0]),       # 쥔 쪽이 위, 기기가 아래로 늘어짐 (빠져나가려 함)
         "upright": np.array([0, -1.0, 0])}    # 화면을 세워서 듦


def lump_mass(shape):
    h, crest, w_in = shape[:3]
    if h <= 0:
        return 0.0
    a = np.linspace(A0, crest + w_in, 80)
    y = np.linspace(-Hh / 2, Hh / 2, 80)
    A, Y = np.meshgrid(a, y)
    vol = height(A, Y, *shape).sum() * (a[1] - a[0]) * (y[1] - y[0])   # mm³, 한쪽
    return 2 * vol * 1e-9 * 1250 * 0.35      # 양쪽, PLA 밀도 × (외벽 + 채움 15% 어림)


def contacts(shape, hl, place, mu):
    """접촉점 목록 [(위치, 마찰 원뿔 모서리)].  place = (a_f, a_p, y_off, mode)"""
    a_f, a_p, y_off, mode = place
    pitch = 0.105 * hl                                        # 손가락 사이 간격
    out = []
    add = lambda p, n: out.append((np.asarray(p, float), cone(np.asarray(n, float), mu)))
    add([W / 2 - 0.13 * hl, -4, Z_FRONT], [0, 0, -1])         # 엄지 패드: 앞면을 누름
    add([W / 2, -8, -2], [-1, 0, 0])                          # 엄지 뿌리 쪽 손바닥: 옆 모서리를 안으로 밂
    add(*back_contact(a_p, -6 + y_off, shape))                # 손바닥: 뒷면 가장자리 쪽
    if mode == "A":                                           # 네 손가락 모두 뒷면
        for k in range(4):
            add(*back_contact(a_f, -1 + y_off + (1.5 - k) * pitch, shape))
    else:                                                     # 검지는 위 모서리, 새끼손가락은 아래 모서리
        add([W / 2 - 0.8 * a_f, Hh / 2, -2], [0, -1, 0])
        add(*back_contact(a_f, -1 + y_off + pitch / 2, shape))
        add(*back_contact(a_f, -1 + y_off - pitch / 2, shape))
        add([W / 2 - 0.7 * a_f, -Hh / 2, -2], [0, 1, 0])
    return out


def effort(shape, hl, place, mu, gdir, mass):
    """평형을 이루는 최소 누름 힘의 합 (N). 불가능하면 inf."""
    cs = contacts(shape, hl, place, mu)
    cols = [np.concatenate([e, np.cross(p, e) / 50.0]) for p, edges in cs for e in edges]   # 돌림힘 행은 크기를 맞춤
    A = np.array(cols).T
    com = np.array([0.0, 0.0, -2.5])
    f = mass * G * gdir
    b = -np.concatenate([f, np.cross(com, f) / 50.0])
    r = linprog(np.ones(A.shape[1]), A_eq=A, b_eq=b, bounds=(0, None), method="highs")
    return float(r.fun) if r.status == 0 else math.inf


def placements(hl):
    """손이 고를 수 있는 쥐는 법: (손가락 끝 a_f, 손바닥 a_p, 세로 위치, 방식)."""
    out = []
    for a_f in np.arange(0.11 * hl, 0.31 * hl + 0.1, 3.0):
        for a_p in (5.0, 13.0, 21.0):
            if a_p <= a_f - 8:
                for y_off in (-5.0, 0.0, 5.0):
                    for mode in "AB":
                        out.append((float(a_f), a_p, y_off, mode))
    return out


MUS = (0.3, 0.5, 0.15)      # 보통 / 마른 손 / 땀이나 물기로 미끄러운 손


def evaluate(shape):
    """손 크기별로 가장 편한 쥐는 법을 MUS[0]에서 고르고, 그 쥐는 법으로 각 마찰 조건의 쥐는 힘을 구한다."""
    mass = BASE_MASS + lump_mass(shape)
    chosen = {}
    for name, hl in HANDS.items():
        best = (math.inf, None)
        for pl in placements(hl):
            e = [effort(shape, hl, pl, MUS[0], d, mass) for d in DIRS_FAST]
            sc = float(np.mean(e)) + 0.5 * float(np.max(e)) if np.all(np.isfinite(e)) else 1e6
            if sc < best[0]:
                best = (sc, pl)
        chosen[name] = best[1]
    out = []
    for mu in MUS:
        res = {}
        for name, hl in HANDS.items():
            pl = chosen[name]
            e = np.array([effort(shape, hl, pl, mu, d, mass) for d in DIRS])
            e = np.where(np.isfinite(e), e, 99.0)
            res[name] = dict(place=list(pl), mean=float(np.mean(e)), worst=float(np.max(e)),
                             **{k: min(effort(shape, hl, pl, mu, v, mass), 99.0) for k, v in NAMED.items()})
        w = lambda k: sum(res[h][k] * WEIGHTS[h] for h in HANDS)
        out.append(dict(shape=dict(h=shape[0], crest=shape[1], w_in=shape[2], groove=shape[3]), mu=mu,
                        mass_g=round(1000 * mass, 1),
                        slope_deg=round(math.degrees(math.atan(1.5 * shape[0] / shape[2])), 1) if shape[0] else 0.0,
                        mean=w("mean"), worst=w("worst"), flat=w("flat"), hang=w("hang"), upright=w("upright"),
                        hands=res))
    return out


def job(shape):
    return evaluate(shape)


def shapes():
    out = [(0.0, 22.0, 9.0, 0.0)]
    for h, crest, w_in, g in itertools.product((3.0, 5.0, 7.0, 9.0, 11.0), (16.0, 24.0, 32.0, 40.0, 46.0), (7.0, 11.0), (0.0, 0.4)):
        if math.degrees(math.atan(1.5 * h / w_in)) <= 62:       # 너무 가파른 턱은 손가락 끝이 아프다
            out.append((h, crest, w_in, g))
    # 1차 탐색에서 마루가 안쪽일수록 좋았으므로 더 안쪽과 더 넓은 비탈을 추가 (골은 효과가 없어 제외)
    for h, crest, w_in in itertools.product((5.0, 7.0, 9.0, 11.0), (40.0, 46.0, 52.0, 58.0), (11.0, 15.0)):
        if (h, crest, w_in, 0.0) not in out:
            out.append((h, crest, w_in, 0.0))
    return out


def figure(res, picks):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.edgecolor": GRID, "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    tot = {}
    for r in res:
        k = json.dumps(r["shape"])
        t = tot.setdefault(k, dict(h=r["shape"]["h"], force=0.0, load=0.0))
        t["force"] += r["worst"] / 3
        t["load"] += r["rel_worst"] / 3
    for ax, key, title, yl in ((axes[0], "force", "Grip force needed (worst orientation)", "sum of pressing forces (N)"),
                               (axes[1], "load", "Same, relative to strength available at that thickness",
                                "relative load (slim case, dry hand = 100)")):
        ax.scatter([t["h"] for t in tot.values()], [t[key] for t in tot.values()], s=18, color="#86b6ef",
                   label="all shapes tried")
        for i, p in enumerate(picks):
            t = tot[json.dumps(p["shape"])]
            ax.scatter([t["h"]], [t[key]], s=70, color="#eb6834", zorder=3, label="selected candidates" if i == 0 else None)
            ax.annotate(p["name"], (t["h"], t[key]), textcoords="offset points", xytext=(7, 5), fontsize=9)
        ax.set_xlabel("grip swell height (mm) — 0 is the slim case")
        ax.set_ylabel(yl + ", mean of 3 friction levels")
        ax.set_title(title, loc="left")
        ax.yaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.set_ylim(0, None)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(HERE.parent / "docs" / "img" / "grip-sim.png", dpi=170)
    plt.close(fig)


def capacity(span):
    """쥐는 폭(mm)에 따른 낼 수 있는 힘의 비율. 약 48 mm에서 최대이고 얇은 판을 집을 때는 그 1/4 수준이라는
    악력계 연구의 일반적 경향을 종 모양 곡선으로 어림한 가정이다."""
    return math.exp(-((span - 48.0) / 30.0) ** 2)


def span_at(r, hand):
    """손가락 끝이 놓인 곳에서 앞면까지의 두께."""
    sh = r["shape"]
    a_f, _, y_off, _ = r["hands"][hand]["place"]
    h = float(height(a_f, -1 + y_off + 0.0525 * HANDS[hand], sh["h"], sh["crest"], sh["w_in"], sh["groove"])) if sh["h"] else 0.0
    return Z_FRONT - Z_BACK + h


def relative(r, k):
    """쥐는 힘을 그 두께에서 낼 수 있는 힘으로 나눈 값 (얇은 기본형의 마른 손 최악 조건 = 100)."""
    return sum(WEIGHTS[h] * r["hands"][h][k] / capacity(span_at(r, h)) for h in HANDS)


if __name__ == "__main__":
    import sys
    from multiprocessing import Pool
    res = json.load(open(HERE / "grip.json"))["results"] if "--reuse" in sys.argv else []     # 있는 결과는 다시 계산하지 않음
    have = {(r["shape"]["h"], r["shape"]["crest"], r["shape"]["w_in"], r["shape"]["groove"]) for r in res}
    todo = [sh for sh in shapes() if sh not in have]
    if todo:
        with Pool() as pool:
            res += [r for trio in pool.map(job, todo, chunksize=1) for r in trio]
    key = lambda r: json.dumps(r["shape"])
    by = {mu: {key(r): r for r in res if r["mu"] == mu} for mu in MUS}
    slim = next(k for k, r in by[0.5].items() if r["shape"]["h"] == 0)
    ref = relative(by[0.5][slim], "worst") / 100
    for r in res:
        r["rel_worst"] = relative(r, "worst") / ref
        r["rel_flat"] = relative(r, "flat") / ref
        r["span"] = {h: round(span_at(r, h), 1) for h in HANDS}
    force = lambda k: sum(by[mu][k]["worst"] for mu in MUS)          # 세 마찰 조건의 최악 힘 합 (N)
    load = lambda k: sum(by[mu][k]["rel_worst"] for mu in MUS)       # 같은 것을 악력 여유로 나눈 값
    picks = []
    for name, hs in (("A low", (3.0, 5.0)), ("B mid", (7.0,)), ("C high", (9.0, 11.0))):
        k = min((key(r) for r in by[0.5].values() if r["shape"]["h"] in hs), key=load)
        picks.append(dict(name=name, shape=json.loads(k)))
    json.dump(dict(results=res, picks=picks), open(HERE / "grip.json", "w"), indent=1)
    figure(res, picks)
    old = json.dumps(dict(h=9.0, crest=16.0, w_in=11.0, groove=0.0))    # 이전 설계에 가까운 "끝 가까이 둔 융기"
    for name, k in [("slim", slim)] + [(p["name"], json.dumps(p["shape"])) for p in picks] + [("edge9", old)]:
        r = by[0.5][k]
        print("%-7s %s slope %4.1f mass %5.1f g span %s" % (name, r["shape"], r["slope_deg"], r["mass_g"], r["span"]))
        for mu in (0.5, 0.3, 0.15):
            x = by[mu][k]
            print("    mu %.2f: N mean %5.2f worst %5.2f flat %5.2f hang %5.2f upright %5.2f | rel worst %5.1f flat %5.1f" % (
                mu, x["mean"], x["worst"], x["flat"], x["hang"], x["upright"], x["rel_worst"], x["rel_flat"]))
    rank_f, rank_l = sorted(by[0.5], key=force), sorted(by[0.5], key=load)
    print("by force:", [(json.loads(k)["h"], json.loads(k)["crest"], json.loads(k)["w_in"], json.loads(k)["groove"], round(force(k), 1)) for k in rank_f[:5]],
          "slim rank", rank_f.index(slim) + 1, "/", len(rank_f), "edge9 rank", rank_f.index(old) + 1)
    print("by load:", [(json.loads(k)["h"], json.loads(k)["crest"], json.loads(k)["w_in"], json.loads(k)["groove"], round(load(k), 1)) for k in rank_l[:5]],
          "slim rank", rank_l.index(slim) + 1, "edge9 rank", rank_l.index(old) + 1)
    by_crest = {}
    for k in by[0.5]:
        sh = json.loads(k)
        if sh["h"] == 7.0 and sh["groove"] == 0.0 and sh["w_in"] == 11.0:
            by_crest[sh["crest"]] = (round(force(k), 1), round(load(k), 1))
    print("h=7 by crest (force, load):", by_crest, "slim", round(force(slim), 1), round(load(slim), 1))
    g = [(round(load(k) - load(json.dumps(dict(json.loads(k), groove=0.0))), 1)) for k in by[0.5] if json.loads(k)["groove"] > 0]
    print("groove effect on load: mean %.1f min %.1f max %.1f" % (np.mean(g), min(g), max(g)))
