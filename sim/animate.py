"""타자 시뮬레이션을 3D 영상으로 만든다.

사용: python3 animate.py [small|medium|large] [v0.1|v0.2|v0.3] [출력.mp4]
모델이 계산한 그립, 키별 관절 자세, 누름 시각을 그대로 그린다(누름 사이의 움직임은 관절각 보간).
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import FancyBboxPatch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from model import (split_layout, key_freq, best_grip, profile, keystrokes, TypingParams, HANDS,
                   CHO, JUNG, JONG, HERE)
from thumb import ROLLS

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, SKIN = "#2a78d6", "#eb6834", "#c98f6b"
JAMO = dict(zip("qwertyuiopasdfghjklzxcvbnm", "ㅂㅈㄷㄱㅅㅛㅕㅑㅐㅔㅁㄴㅇㄹㅎㅗㅓㅏㅣㅋㅌㅊㅍㅠㅜㅡ"))
SPECIAL = {"BS": "지움", "ENT": "엔터", "LEFT": "◀", "RIGHT": "▶", "LANG": "한/영", "MENU": "메뉴", "TAB": "탭", ",": ",", ".": "."}
CHO_COMPAT = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
SLOWMO = 0.35
FPS = 30


# ── 자세 풀이: 표를 쓰지 않고 같은 식으로 직접 최소 불편도 자세를 찾는다 ──
def solve(p, roll, cmc, az_n, key, half_w, half_h, relax=1.0):
    L1, L2, L3 = p.L
    h = p.hand_length
    rho = math.radians(roll)
    tm = np.radians(np.arange(p.mcp[0], p.mcp[1] + 0.01, 0.5))[:, None]
    ti = np.radians(np.arange(p.ip[0], p.ip[1] + 0.01, 0.5))[None, :]
    A = L2 * np.cos(tm) + L3 * np.cos(tm + ti)
    B = L2 * np.sin(tm) + L3 * np.sin(tm + ti)
    Bz = B * math.cos(rho)
    zt = p.key_top + h * p.pad_thick + p.cmc_depth
    M = np.hypot(L1 + A, Bz)
    eps = np.arcsin(np.clip(zt / M, -1, 1)) + np.arctan2(Bz, L1 + A)
    ce, se = np.cos(eps), np.sin(eps)
    fwd = (L1 + A) * ce + Bz * se
    lat = -B * math.sin(rho)
    r = np.hypot(fwd, lat)
    gam = np.degrees(np.arctan2(lat, fwd))
    e_deg = np.degrees(eps)
    pitch = np.degrees(np.arcsin(np.clip(-(np.cos(tm + ti) * se - np.sin(tm + ti) * math.cos(rho) * ce), -1, 1)))
    ok = (M > zt) & (e_deg >= p.elev[0]) & (e_deg <= p.elev[1]) & (pitch >= p.pad_pitch[0]) & (pitch <= p.pad_pitch[1])
    d = key - cmc
    dist = math.hypot(*d)
    az_key = math.degrees(math.atan2(d[1], -d[0]))
    tx = (cmc[0] - half_w) / -d[0] if cmc[0] > half_w else 0.0
    ty = (-half_h - cmc[1]) / d[1] if cmc[1] < -half_h else 0.0
    d_edge = min(max(tx, ty, 0.0), 1.0) * dist
    mcp_r, mcp_z = L1 * ce, L1 * se - p.cmc_depth
    a2, b2 = L2 * np.cos(tm), L2 * np.sin(tm)
    ip_r = np.hypot((L1 + a2) * ce + b2 * math.cos(rho) * se, b2 * math.sin(rho))
    ip_z = (L1 + a2) * se - b2 * math.cos(rho) * ce - p.cmc_depth
    ok &= (mcp_r < d_edge) | (mcp_z >= h * p.mcp_half)
    ok &= (ip_r < d_edge) | (ip_z >= p.key_top + h * p.ip_half)
    smax = h * p.hand_shift * relax
    s = dist - r                                   # 손 전체를 키 방향으로 s 만큼 옮김
    daz = az_key - gam - az_n
    ok &= (np.abs(s) <= smax) & (np.abs(daz) <= p.az_half + 4 * (relax - 1))

    def dev(x, n, lo, hi):
        return ((x - n) / np.where(x >= n, hi - n, n - lo)) ** 2

    cost = (dev(e_deg, p.elev_neutral, *p.elev) + dev(np.degrees(tm), p.mcp_neutral, *p.mcp)
            + dev(np.degrees(ti), p.ip_neutral, *p.ip) + (daz / p.az_half) ** 2 + p.shift_cost * (s / smax) ** 2)
    cost = np.where(ok, cost, np.inf)
    i, j = np.unravel_index(np.argmin(cost), cost.shape)
    if not np.isfinite(cost[i, j]):
        return None
    u = d / dist
    return dict(shift=u * s[i, j], az=float(az_key - gam[i, j]), elev=float(e_deg[i, j]),
                mcp=float(np.degrees(tm[i, 0])), ip=float(np.degrees(ti[0, j])))


def fk(p, roll, cmc, q):
    """관절각 → [CMC, MCP, IP, 패드] 3D 점 (오른손 좌표)."""
    L1, L2, L3 = p.L
    rho, e = math.radians(roll), math.radians(q["elev"])
    tm, ti, az = math.radians(q["mcp"]), math.radians(q["ip"]), math.radians(q["az"])
    ce, se, cr, sr = math.cos(e), math.sin(e), math.cos(rho), math.sin(rho)
    fdir = np.array([-math.cos(az), math.sin(az)])
    ldir = np.array([math.sin(az), math.cos(az)])
    c = np.asarray(cmc) + np.asarray(q["shift"])
    pts = [np.array([c[0], c[1], -p.cmc_depth])]
    for a, b in ((0.0, 0.0), (L2 * math.cos(tm), L2 * math.sin(tm)),
                 (L2 * math.cos(tm) + L3 * math.cos(tm + ti), L2 * math.sin(tm) + L3 * math.sin(tm + ti))):
        f = (L1 + a) * ce + b * cr * se
        l = -b * sr
        z = (L1 + a) * se - b * cr * ce - p.cmc_depth
        xy = c + f * fdir + l * ldir
        pts.append(np.array([xy[0], xy[1], z]))
    return np.array(pts)


def timeline(lay, D, seq, tp=TypingParams()):
    """simulate()와 같은 규칙으로 누름 시각을 만든다. 반환: [(t_ms, 키 번호, 손)]"""
    W = min(lay.px, lay.py) - tp.cap_gap
    idx = {l: i for i, l in enumerate(lay.labels)}
    xy, hand = lay.xy, lay.hand
    pos = [xy[idx["d"]].copy(), xy[idx["k"]].copy()]
    last, t, prev = [0.0, 0.0], 0.0, 1
    ev = []
    for key in seq:
        k = idx["SPC_L"] if key == "SPC" and prev == 1 else idx["SPC_R"] if key == "SPC" else idx[key] if key in idx else idx[key.lower()]
        h = int(hand[k])
        dd = float(np.hypot(*(xy[k] - pos[h])))
        mt = (tp.a + tp.b * math.log2(dd / W + 1)) * (1 + tp.kappa * D[k])
        tk = last[h] + mt
        if h != prev:
            tk = max(tk, t + tp.t_min)
        t = tk
        last[h], pos[h], prev = t, xy[k].copy(), h
        ev.append((t, k, h))
    return ev


def typed_text(text, n):
    """글쇠 n개를 친 시점의 화면 글자 (조합 중인 글자 포함)."""
    out = ""
    for ch in text:
        ks = keystrokes(ch)
        if not ks:
            continue
        if n >= len(ks):
            out += " " if ch == "\n" else ch
            n -= len(ks)
            continue
        if n > 0:
            s = ord(ch) - 0xAC00
            c, v, j = s // 588, s % 588 // 28, s % 28
            nv = len(JUNG[v])
            if n == 1:
                out += CHO_COMPAT[c]
            else:
                vi = JUNG.index(JUNG[v][:min(n - 1, nv)])
                ji = JONG.index(JONG[j][:max(n - 1 - nv, 0)])
                out += chr(0xAC00 + (c * 21 + vi) * 28 + ji)
        break
    return out


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u ** 3 * (10 - 15 * u + 6 * u * u)       # 최소 저크 곡선


LAYOUTS = {
    "v0.1": lambda: split_layout(9.0, 9.5, 4.75),
    "v0.2": lambda: split_layout(9.0, 10.0, -6.0),
    "v0.3": lambda: split_layout(9.0, 10.0, -6.0, stagger=(-5, -5, -1, 3, 4)),
    "v0.5": lambda: split_layout(9.0, 10.0, -6.0, stagger=(-5, -5, -1, 3, 4), left_tab=True),
}
DESC = {"v0.1": "평면 격자, 키 위쪽", "v0.2": "평면 격자, 키 아래쪽", "v0.3": "곡선 배열", "v0.5": "곡선 배열 + TAB"}
KEY_FC = "#dfe7f2"


def main(hand="medium", ver="v0.3", out=None):
    lay = LAYOUTS[ver]()
    hl = HANDS[hand]
    p, _ = profile(hl)
    freq = key_freq(lay)
    text = (HERE / "corpus_ko.txt").read_text(encoding="utf-8").split("\n")[0] + "\n"
    seq = keystrokes(text)
    grips, D = [], np.zeros(len(lay.labels))
    for side in (0, 1):
        g, d = best_grip(lay, hl, side, freq)
        grips.append(g)
        D[lay.hand == side] = d
    D = np.where(np.isfinite(D), D, 1.0)
    mir = [np.array([-1, 1]), np.array([1, 1])]
    Q = {}
    for k in range(len(lay.labels)):
        s = int(lay.hand[k])
        for relax in (1.0, 1.5, 2.5, 4.0):          # 표의 반올림 때문에 못 푸는 경계 키는 조금 풀어 준다
            Q[k] = solve(p, grips[s]["roll"], np.array(grips[s]["cmc"]), grips[s]["az"], lay.xy[k] * mir[s],
                         lay.W / 2, lay.H / 2, relax)
            if Q[k]:
                break
    ev = timeline(lay, D, seq)
    idx = {l: i for i, l in enumerate(lay.labels)}
    per = [[(0.0, idx["d"])] + [(t, k) for t, k, h in ev if h == 0],
           [(0.0, idx["k"])] + [(t, k) for t, k, h in ev if h == 1]]
    T = ev[-1][0] + 600

    def pose(side, t):
        e = per[side]
        i = max(j for j in range(len(e)) if e[j][0] <= t)
        q0 = Q[e[i][1]]
        if i + 1 == len(e):
            return dict(q0)
        t0, t1, q1 = e[i][0], e[i + 1][0], Q[e[i + 1][1]]
        u = ease((t - t0 - 30) / max(t1 - t0 - 30, 1))
        q = {k: q0[k] + (q1[k] - q0[k]) * u for k in q0}
        q["elev"] += 3.0 * math.sin(math.pi * u)        # 이동 중에는 살짝 들어 올림
        return q

    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=SURFACE)
    fig.text(0.02, 0.945, f"DigitalPN {ver} 타자 시뮬레이션 ({DESC[ver]})", fontsize=17, color=INK)
    fig.text(0.02, 0.905, f"손 길이 {hl:.0f} mm · 모델 속도의 {SLOWMO:g}배속 · 굵은 선은 엄지(뿌리 관절 → 손허리뼈 → 첫마디 → 끝마디)",
             fontsize=10.5, color=INK2)
    stat = fig.text(0.02, 0.03, "", fontsize=12, color=INK)

    # ── 3D 보기 ──
    a3 = fig.add_axes([-0.06, -0.06, 0.78, 1.04], projection="3d", computed_zorder=False)
    a3.set_xlim(-100, 100)
    a3.set_ylim(-105, 40)
    a3.set_zlim(-15, 60)
    a3.set_box_aspect((200, 145, 75), zoom=1.42)
    a3.set_axis_off()
    a3.patch.set_alpha(0)
    w2, h2, zb = lay.W / 2, lay.H / 2, -12.0
    top = [(-w2, -h2, 0), (w2, -h2, 0), (w2, h2, 0), (-w2, h2, 0)]
    front = [(-w2, -h2, zb), (w2, -h2, zb), (w2, -h2, 0), (-w2, -h2, 0)]
    sides = [[(sx * w2, -h2, zb), (sx * w2, h2, zb), (sx * w2, h2, 0), (sx * w2, -h2, 0)] for sx in (-1, 1)]
    a3.add_collection3d(Poly3DCollection([front] + sides, fc="#cfcdc6", ec=INK2, lw=0.6, zorder=1))
    a3.add_collection3d(Poly3DCollection([top], fc="#f0efec", ec=INK2, lw=0.6, zorder=2))
    a3.add_collection3d(Poly3DCollection([[(-17.6, -29.4, 0.05), (17.6, -29.4, 0.05), (17.6, 29.4, 0.05),
                                           (-17.6, 29.4, 0.05)]], fc="white", ec=INK2, lw=0.6, zorder=3))
    key3 = []
    for (x, y), w in zip(lay.xy, lay.wide):
        kw, kh = (w - 1) * lay.px + lay.px - 1.6, lay.py - 1.6
        c = [(x - kw / 2, y - kh / 2), (x + kw / 2, y - kh / 2), (x + kw / 2, y + kh / 2), (x - kw / 2, y + kh / 2)]
        faces = [[(cx, cy, 1.0) for cx, cy in c]]
        faces += [[(c[i][0], c[i][1], 0), (c[(i + 1) % 4][0], c[(i + 1) % 4][1], 0),
                   (c[(i + 1) % 4][0], c[(i + 1) % 4][1], 1.0), (c[i][0], c[i][1], 1.0)] for i in range(4)]
        pc = Poly3DCollection(faces, fc=KEY_FC, ec="#aab6c8", lw=0.4, zorder=4)
        a3.add_collection3d(pc)
        key3.append(pc)
    th3 = []
    for side in (0, 1):
        sh, = a3.plot([], [], [], color="#b9b7b0", lw=5, alpha=0.6, solid_capstyle="round", zorder=5)   # 바닥 그림자
        fat, = a3.plot([], [], [], color=SKIN, lw=22, alpha=0.75, solid_capstyle="round", solid_joinstyle="round", zorder=6)
        bone, = a3.plot([], [], [], color=INK, lw=1.4, marker="o", ms=5, mfc=SURFACE, mec=INK, zorder=7)
        th3.append((sh, fat, bone))

    # ── 위에서 본 그림 ──
    ax = fig.add_axes([0.675, 0.50, 0.32, 0.37])
    ax.set_xlim(-lay.W / 2 - 4, lay.W / 2 + 4)
    ax.set_ylim(-lay.H / 2 - 4, lay.H / 2 + 4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((-lay.W / 2, -lay.H / 2), lay.W, lay.H, boxstyle="round,pad=0,rounding_size=7",
                                fc="#f0efec", ec=INK2, lw=1))
    ax.add_patch(Rectangle((-17.6, -29.4), 35.2, 58.8, fc="white", ec=INK2, lw=0.8))
    key2 = []
    for lab, (x, y), w in zip(lay.labels, lay.xy, lay.wide):
        kw, kh = (w - 1) * lay.px + lay.px - 1.6, lay.py - 1.6
        r = FancyBboxPatch((x - kw / 2, y - kh / 2), kw, kh, boxstyle="round,pad=0,rounding_size=1.2", fc=KEY_FC, ec="none")
        ax.add_patch(r)
        key2.append(r)
        ax.text(x, y, JAMO.get(lab, ""), ha="center", va="center", fontsize=7.5, color=INK)
    screen = ax.text(-15.8, 27.0, "", ha="left", va="top", fontsize=7.5, color=INK, linespacing=1.3)
    tips2 = [ax.plot([], [], "o", ms=7, color=BLUE, alpha=0.85)[0] for _ in (0, 1)]

    # ── 관절 게이지 ──
    spec = [("방위", "az", -p.az_half, p.az_half, 0.0), ("들림", "elev", *p.elev, p.elev_neutral),
            ("MCP 굽힘", "mcp", *p.mcp, p.mcp_neutral), ("IP 굽힘", "ip", *p.ip, p.ip_neutral)]
    gauges = []
    for side, x0 in ((0, 0.685), (1, 0.845)):
        fig.text(x0, 0.435, "왼손 엄지" if side == 0 else "오른손 엄지", fontsize=12, color=INK)
        for n, (name, key, lo, hi, neu) in enumerate(spec):
            ga = fig.add_axes([x0, 0.345 - 0.078 * n, 0.14, 0.026])
            ga.set_xlim(lo, hi)
            ga.set_ylim(0, 1)
            ga.axis("off")
            ga.add_patch(Rectangle((lo, 0.3), hi - lo, 0.4, fc=GRID, ec="none"))
            ga.plot([neu, neu], [0.05, 0.95], color=INK2, lw=1)
            mark, = ga.plot([neu], [0.5], "o", ms=9, color=BLUE)
            lab = fig.text(x0, 0.376 - 0.078 * n, "", fontsize=9.5, color=INK2)
            gauges.append((side, name, key, lo, hi, neu, mark, lab))
    fig.text(0.685, 0.045, "회색 막대 = 관절 가동범위 · 세로선 = 중립 자세\n주황 점 = 한계의 80% 이상", fontsize=9.5,
             color=INK2, linespacing=1.5)

    out = out or str(HERE.parent / "docs" / "video" / f"typing-{ver}-{hand}.mp4")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    writer = FFMpegWriter(fps=FPS, codec="libx264", extra_args=["-pix_fmt", "yuv420p", "-crf", "24"])
    nframes = int(T / 1000 / SLOWMO * FPS)
    with writer.saving(fig, out, dpi=100):
        for fidx in range(nframes):
            t = fidx / FPS * SLOWMO * 1000
            a3.view_init(elev=42, azim=-90 + 14 * math.sin(2 * math.pi * fidx / (FPS * 16)))   # 천천히 좌우로 도는 시점
            done = [e for e in ev if e[0] <= t]
            hot = {k for (tk, k, h) in done[-2:] if t - tk < 110}
            for k in range(len(key2)):
                c = ORANGE if k in hot else KEY_FC
                key2[k].set_facecolor(c)
                key3[k].set_facecolor(c)
            for side in (0, 1):
                q = pose(side, t)
                pts = fk(p, grips[side]["roll"], grips[side]["cmc"], q)
                pts[:, 0] *= mir[side][0]
                sh, fat, bone = th3[side]
                on = pts[1:]                                   # 손허리뼈 끝부터가 기기 위
                sh.set_data_3d([], [], [])
                fat.set_data_3d(pts[:, 0], pts[:, 1], pts[:, 2])
                bone.set_data_3d(pts[:, 0], pts[:, 1], pts[:, 2])
                tips2[side].set_data([pts[3, 0]], [pts[3, 1]])
                for (s, name, key, lo, hi, neu, mark, lab) in gauges:
                    if s != side:
                        continue
                    v = q[key] - (grips[side]["az"] if key == "az" else 0.0)
                    v = min(max(v, lo), hi)
                    frac = abs(v - neu) / ((hi - neu) if v >= neu else (neu - lo))
                    mark.set_data([v], [0.5])
                    mark.set_color(ORANGE if frac >= 0.8 else BLUE)
                    lab.set_text(f"{name}  {v:+.0f}°" if key == "az" else f"{name}  {v:.0f}°")
            s = typed_text(text, len(done))
            screen.set_text("\n".join(s[i:i + 7] for i in range(0, len(s), 7)) + "▏")
            rate = len(done) / (done[-1][0] / 60000) if len(done) > 3 else 0
            stat.set_text(f"모델 시간 {t / 1000:4.1f}초   글쇠 {len(done):3d}/{len(ev)}   " +
                          (f"{rate:3.0f}타/분 (오타 수정 시간 제외)" if rate else ""))
            writer.grab_frame()
    plt.close(fig)
    print(out, nframes, "frames")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "medium", a[1] if len(a) > 1 else "v0.3", a[2] if len(a) > 2 else None)
